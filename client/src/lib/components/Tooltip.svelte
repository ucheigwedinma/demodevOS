<script lang="ts">
  import type { Snippet } from "svelte";

  let {
    text,
    position = "right",
    children,
  }: {
    text: string;
    position?: "right" | "bottom";
    children: Snippet;
  } = $props();

  let visible = $state(false);
  let wrapperEl = $state<HTMLElement | null>(null);
  let coords = $state({ x: 0, y: 0 });

  function portal(node: HTMLElement) {
    document.body.appendChild(node);
    return {
      destroy() {
        node.remove();
      },
    };
  }

  function show() {
    const child = wrapperEl?.firstElementChild as HTMLElement | null;
    if (child) {
      const rect = child.getBoundingClientRect();
      if (position === "right") {
        coords = { x: rect.right + 6, y: rect.top + rect.height / 2 };
      } else {
        coords = { x: rect.left + rect.width / 2, y: rect.bottom + 6 };
      }
    }
    visible = true;
  }

  function hide() {
    visible = false;
  }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  bind:this={wrapperEl}
  onmouseenter={show}
  onmouseleave={hide}
  onfocusin={show}
  onfocusout={hide}
  class="inline-flex"
>
  {@render children()}
</div>

{#if visible}
  <div
    use:portal
    class="fixed z-9999 pointer-events-none"
    style="left: {coords.x}px; top: {coords.y}px; transform: {position === 'right' ? 'translateY(-50%)' : 'translateX(-50%)'};"
  >
    <div class="relative flex {position === 'right' ? 'flex-row items-center' : 'flex-col items-center'}">
      {#if position === "right"}
        <div class="w-1.5 h-1.5 bg-neutral-700 rotate-45 -mr-[3px]"></div>
      {:else}
        <div class="w-1.5 h-1.5 bg-neutral-700 rotate-45 -mb-[3px]"></div>
      {/if}
      <div class="px-2.5 py-1 bg-neutral-700 text-white text-xs font-medium rounded-lg whitespace-nowrap">
        {text}
      </div>
    </div>
  </div>
{/if}

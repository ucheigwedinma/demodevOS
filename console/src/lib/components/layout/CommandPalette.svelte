<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { navigation } from "$lib/navigation";

  let open = $state(false);
  let query = $state("");
  let selectedIndex = $state(0);
  let inputEl: HTMLInputElement | undefined = $state();

  interface SearchResult {
    label: string;
    module: string;
    moduleLabel: string;
    resource: string;
    path: string;
  }

  let allItems: SearchResult[] = $derived.by(() => {
    const items: SearchResult[] = [];
    for (const nav of navigation) {
      for (const child of nav.children) {
        if (child.isSection) continue;
        items.push({
          label: child.label,
          module: nav.module,
          moduleLabel: nav.label,
          resource: child.resource,
          path: `/${nav.module}/${child.resource}`,
        });
      }
    }
    return items;
  });

  let results = $derived.by(() => {
    if (!query.trim()) return allItems.slice(0, 12);
    const q = query.toLowerCase();
    return allItems.filter(
      (item) =>
        item.label.toLowerCase().includes(q) ||
        item.moduleLabel.toLowerCase().includes(q) ||
        item.resource.toLowerCase().includes(q)
    ).slice(0, 12);
  });

  function handleKeydown(e: KeyboardEvent) {
    if ((e.metaKey || e.ctrlKey) && e.key === "k") {
      e.preventDefault();
      open = !open;
      if (open) {
        query = "";
        selectedIndex = 0;
        requestAnimationFrame(() => inputEl?.focus());
      }
    }
    if (!open) return;
    if (e.key === "Escape") {
      open = false;
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      selectedIndex = Math.min(selectedIndex + 1, results.length - 1);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      selectedIndex = Math.max(selectedIndex - 1, 0);
    } else if (e.key === "Enter" && results[selectedIndex]) {
      e.preventDefault();
      navigate(results[selectedIndex]);
    }
  }

  function navigate(item: SearchResult) {
    open = false;
    query = "";
    goto(item.path);
  }

  onMount(() => {
    document.addEventListener("keydown", handleKeydown);
    return () => document.removeEventListener("keydown", handleKeydown);
  });
</script>

{#if open}
  <!-- Backdrop -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="fixed inset-0 bg-black/40 z-50 flex items-start justify-center pt-[15vh]"
    onkeydown={handleKeydown}
    onclick={() => { open = false; }}
  >
    <!-- Panel -->
    <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <div
      class="bg-white rounded-xl shadow-2xl border border-neutral-200 w-full max-w-lg overflow-hidden"
      onclick={(e) => e.stopPropagation()}
    >
      <!-- Search input -->
      <div class="flex items-center gap-3 px-4 py-3 border-b border-neutral-100">
        <svg class="w-4 h-4 text-neutral-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
        </svg>
        <input
          bind:this={inputEl}
          bind:value={query}
          oninput={() => { selectedIndex = 0; }}
          class="flex-1 text-sm outline-none placeholder:text-neutral-400"
          placeholder="Search resources..."
        />
        <kbd class="text-[10px] text-neutral-400 bg-neutral-100 rounded px-1.5 py-0.5 font-mono">ESC</kbd>
      </div>

      <!-- Results -->
      <div class="max-h-80 overflow-y-auto py-2">
        {#if results.length === 0}
          <p class="px-4 py-6 text-sm text-neutral-400 text-center">No results found</p>
        {:else}
          {#each results as item, i}
            <button
              class="w-full flex items-center gap-3 px-4 py-2 text-left text-sm transition-colors
                     {i === selectedIndex ? 'bg-neutral-100' : 'hover:bg-neutral-50'}"
              onclick={() => navigate(item)}
              onmouseenter={() => { selectedIndex = i; }}
            >
              <span class="font-medium text-neutral-900">{item.label}</span>
              <span class="text-neutral-400 text-xs">{item.moduleLabel}</span>
            </button>
          {/each}
        {/if}
      </div>
    </div>
  </div>
{/if}

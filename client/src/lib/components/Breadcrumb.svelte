<script lang="ts">
  interface BreadcrumbItem {
    label: string;
    href?: string;
  }

  let { items }: { items: BreadcrumbItem[] } = $props();
</script>

<nav aria-label="Breadcrumb" class="flex items-center gap-1.5 text-sm">
  {#each items as item, i}
    {#if i > 0}
      <svg class="w-3.5 h-3.5 text-neutral-300 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
      </svg>
    {/if}
    {#if item.href && i < items.length - 1}
      <a href={item.href} class="text-neutral-400 hover:text-neutral-700 transition-colors truncate">{item.label}</a>
    {:else}
      <span class="text-neutral-900 font-medium truncate">{item.label}</span>
    {/if}
  {/each}
</nav>

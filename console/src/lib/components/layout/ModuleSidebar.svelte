<script lang="ts">
  import { page } from "$app/stores";
  import { getNavItem } from "$lib/navigation";

  let currentModule = $derived(
    $page.params.module
      ?? ($page.url.pathname === "/" || $page.url.pathname.startsWith("/platform") ? "platform" : ""),
  );
  let currentResource = $derived($page.params.resource ?? "");
  let navItem = $derived(getNavItem(currentModule));
</script>

{#if navItem}
  <aside class="h-screen w-56 bg-neutral-50 border-r border-neutral-200 flex flex-col shrink-0">
    <!-- Module header -->
    <div class="px-4 py-4 border-b border-neutral-200">
      <h2 class="text-sm font-semibold text-neutral-900">{navItem.label}</h2>
    </div>

    <!-- Resource list -->
    <nav class="flex-1 overflow-y-auto px-2 py-2">
      {#each navItem.children as child}
        {#if child.isSection}
          <div class="px-3 pt-4 pb-1 first:pt-1">
            <span class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">{child.label}</span>
          </div>
        {:else}
          {@const childHref = child.path ?? `/${currentModule}/${child.resource}`}
          {@const isActive = child.path
            ? $page.url.pathname === child.path
            : currentResource === child.resource}
          <a
            href={childHref}
            class="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors
                   {isActive
                     ? 'bg-white text-neutral-900 font-medium shadow-sm'
                     : 'text-neutral-600 hover:text-neutral-900 hover:bg-white'}"
          >
            {child.label}
          </a>
        {/if}
      {/each}
    </nav>
  </aside>
{/if}

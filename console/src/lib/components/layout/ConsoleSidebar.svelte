<script lang="ts">
  import { page } from "$app/stores";
  import { navigation } from "$lib/navigation";
  import { consoleState } from "$lib/stores/console.svelte";

  let currentModule = $derived(
    $page.params.module
      ?? ($page.url.pathname === "/" || $page.url.pathname.startsWith("/platform") ? "platform" : ""),
  );
</script>

<aside class="h-screen w-14 bg-neutral-950 flex flex-col items-center py-4 border-r border-neutral-800 shrink-0">
  <!-- Brand -->
  <a href="/" class="mb-6">
    <span class="text-xs font-normal text-white">d</span><span class="text-xs font-bold text-neutral-400">OS</span>
  </a>

  <!-- Nav Icons -->
  <nav class="flex flex-col gap-1 flex-1">
    {#each navigation as item}
      <a
        href={item.children[0]?.path ?? `/${item.module}/${item.children[0]?.resource ?? ''}`}
        class="w-9 h-9 flex items-center justify-center rounded-lg transition-colors group relative
               {currentModule === item.module
                 ? 'bg-white/10 text-white'
                 : 'text-neutral-500 hover:text-white hover:bg-white/5'}"
        title={item.label}
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d={item.icon} />
        </svg>
        <!-- Tooltip -->
        <span class="absolute left-full ml-2 px-2 py-1 text-xs font-medium text-white bg-neutral-800 rounded-md
                     opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap transition-opacity z-50">
          {item.label}
        </span>
      </a>
    {/each}
  </nav>

  <!-- Bottom: user avatar placeholder -->
  <div class="mt-auto">
    <button
      class="w-8 h-8 rounded-full bg-neutral-700 text-neutral-300 text-xs font-semibold flex items-center justify-center"
    >
      A
    </button>
  </div>
</aside>

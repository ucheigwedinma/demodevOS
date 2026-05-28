<script lang="ts">
  import { page } from "$app/stores";
  import { auth } from "$lib/stores/auth.svelte";
  import { getNavItem } from "$lib/navigation";

  let currentModule = $derived($page.params.module ?? "platform");
  let currentResource = $derived($page.params.resource ?? "");
  let navItem = $derived(getNavItem(currentModule));
  let resourceLabel = $derived(
    navItem?.children.find((c) => c.resource === currentResource)?.label ?? currentResource
  );

  let showUserMenu = $state(false);
</script>

<header class="h-14 bg-white border-b border-neutral-200 flex items-center justify-between px-6 shrink-0">
  <!-- Breadcrumb -->
  <div class="flex items-center gap-2 text-sm">
    <span class="text-neutral-400">{navItem?.label ?? "Console"}</span>
    {#if resourceLabel}
      <svg class="w-4 h-4 text-neutral-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
      </svg>
      <span class="text-neutral-900 font-medium">{resourceLabel}</span>
    {/if}
  </div>

  <!-- Right side -->
  <div class="flex items-center gap-3">
    <div class="relative">
      <button
        onclick={() => showUserMenu = !showUserMenu}
        class="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-neutral-50 transition-colors"
      >
        <div class="w-7 h-7 rounded-full bg-neutral-900 text-white text-xs font-semibold flex items-center justify-center">
          {auth.user?.full_name?.charAt(0) ?? "?"}
        </div>
        <span class="text-sm text-neutral-700">{auth.user?.full_name ?? "Admin"}</span>
      </button>

      {#if showUserMenu}
        <div class="absolute right-0 top-full mt-1 w-48 bg-white rounded-xl shadow-lg border border-neutral-200 py-1 z-50">
          <div class="px-3 py-2 border-b border-neutral-100">
            <p class="text-xs text-neutral-500">{auth.user?.email}</p>
          </div>
          <button
            onclick={() => { showUserMenu = false; auth.logout(); }}
            class="w-full text-left px-3 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
          >
            Sign out
          </button>
        </div>
      {/if}
    </div>
  </div>
</header>

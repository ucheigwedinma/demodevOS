<script lang="ts">
  import "../app.css";
  import { onMount } from "svelte";
  import { page } from "$app/stores";
  import { auth } from "$lib/stores/auth.svelte";
  import { statusRegistry } from "$lib/stores/statusRegistry.svelte";
  import ConsoleSidebar from "$lib/components/layout/ConsoleSidebar.svelte";
  import ModuleSidebar from "$lib/components/layout/ModuleSidebar.svelte";
  import TopBar from "$lib/components/layout/TopBar.svelte";
  import Toaster from "$lib/components/ui/Toaster.svelte";
  import CommandPalette from "$lib/components/layout/CommandPalette.svelte";
  import type { Snippet } from "svelte";

  let { children }: { children: Snippet } = $props();

  let isLoginPage = $derived($page.url.pathname === "/login");

  onMount(async () => {
    const token = localStorage.getItem("access_token") || sessionStorage.getItem("access_token");
    if (!token && !isLoginPage) {
      window.location.href = "/login";
      return;
    }
    if (token) {
      await auth.load();
      statusRegistry.load();
    }
  });
</script>

{#if isLoginPage}
  {@render children()}
{:else if auth.loaded}
  <div class="flex h-screen overflow-hidden bg-white">
    <ConsoleSidebar />
    <ModuleSidebar />
    <div class="flex-1 flex flex-col overflow-hidden">
      <TopBar />
      <main class="flex-1 overflow-y-auto p-6">
        {@render children()}
      </main>
    </div>
  </div>
{:else}
  <div class="flex h-screen items-center justify-center">
    <div class="w-5 h-5 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div>
  </div>
{/if}

<Toaster />
<CommandPalette />

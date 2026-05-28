<script lang="ts">
  import { ws, type PresenceUser } from "$lib/stores/websocket.svelte";
  import { page } from "$app/stores";

  let expanded = $state(false);

  const users = $derived(ws.onlineUsers);
  const currentPath = $derived($page.url.pathname);

  // Users on the same page as me
  const usersOnThisPage = $derived(
    users.filter(u => u.page === currentPath)
  );

  function initials(name: string): string {
    return name
      .split(" ")
      .map(w => w[0])
      .join("")
      .toUpperCase()
      .slice(0, 2);
  }

  function pageLabel(p: string): string {
    if (!p) return "Unknown";
    const parts = p.split("/").filter(Boolean);
    if (parts.length === 0) return "Dashboard";
    return parts[parts.length - 1]
      .replace(/-/g, " ")
      .replace(/\b\w/g, c => c.toUpperCase());
  }

  const colors = [
    "bg-blue-500", "bg-emerald-500", "bg-amber-500", "bg-purple-500",
    "bg-rose-500", "bg-cyan-500", "bg-indigo-500", "bg-orange-500",
  ];

  function avatarColor(userId: number): string {
    return colors[userId % colors.length];
  }
</script>

{#if ws.connected && users.length > 0}
  <div class="relative">
    <!-- Compact: avatar stack -->
    <button
      onclick={() => (expanded = !expanded)}
      class="flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-neutral-400 hover:bg-white/10 transition-colors"
      title="{users.length} user{users.length !== 1 ? 's' : ''} online"
    >
      <div class="flex -space-x-2">
        {#each users.slice(0, 4) as user}
          <div
            class="h-6 w-6 rounded-full border-2 border-neutral-900 flex items-center justify-center text-[9px] font-bold text-white {avatarColor(user.user_id)}"
            title="{user.name} — {pageLabel(user.page)}"
          >
            {initials(user.name)}
          </div>
        {/each}
        {#if users.length > 4}
          <div class="h-6 w-6 rounded-full border-2 border-neutral-900 bg-neutral-700 flex items-center justify-center text-[9px] font-bold text-neutral-300">
            +{users.length - 4}
          </div>
        {/if}
      </div>
      <span class="text-[10px] font-medium text-neutral-500">{users.length}</span>
    </button>

    <!-- Expanded: full roster -->
    {#if expanded}
      <div class="absolute right-0 top-full mt-2 w-72 rounded-xl bg-white shadow-2xl border border-neutral-200 z-50 overflow-hidden">
        <div class="px-4 py-2.5 border-b border-neutral-100 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <h3 class="text-xs font-semibold text-neutral-900">{users.length} Online</h3>
          </div>
          {#if usersOnThisPage.length > 0}
            <span class="text-[10px] text-neutral-400">{usersOnThisPage.length} on this page</span>
          {/if}
        </div>

        <div class="max-h-64 overflow-y-auto divide-y divide-neutral-50">
          {#each users as user}
            <div class="flex items-center gap-3 px-4 py-2.5 {user.page === currentPath ? 'bg-indigo-50/50' : ''}">
              <div class="h-8 w-8 rounded-full flex items-center justify-center text-[10px] font-bold text-white {avatarColor(user.user_id)} shrink-0">
                {initials(user.name)}
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-neutral-900 truncate">{user.name}</p>
                <p class="text-[10px] text-neutral-400 truncate">
                  {#if user.page === currentPath}
                    <span class="text-indigo-600 font-semibold">Viewing this page</span>
                  {:else if user.page}
                    {pageLabel(user.page)}
                  {:else}
                    Online
                  {/if}
                </p>
              </div>
              <span class="h-2 w-2 rounded-full bg-emerald-500 shrink-0"></span>
            </div>
          {/each}
        </div>
      </div>
    {/if}
  </div>
{/if}

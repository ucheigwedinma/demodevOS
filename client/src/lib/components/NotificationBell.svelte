<script lang="ts">
  import { api } from "$lib/api";
  import { ws } from "$lib/stores/websocket.svelte";
  import { toast as toastStore } from "$lib/stores/toast.svelte";
  import { onboarding } from "$lib/stores/onboarding.svelte";
  import type { Notification, PaginatedResponse } from "$lib/types";
  import { onMount, onDestroy } from "svelte";

  let open = $state(false);
  let localUnreadCount = $state(0);
  let notifications = $state<Notification[]>([]);
  let badgePulse = $state(false);
  let prevCount = 0;

  // Prefer WebSocket count when connected, fall back to polled count
  const unreadCount = $derived(ws.connected ? ws.unreadCount : localUnreadCount);

  // Pulse the badge when count increases
  $effect(() => {
    const count = unreadCount;
    if (count > prevCount && prevCount >= 0) {
      badgePulse = true;
      setTimeout(() => { badgePulse = false; }, 1500);
    }
    prevCount = count;
  });

  // When a new notification arrives via WS: show toast + refresh dropdown
  $effect(() => {
    const notif = ws.lastNotification;
    if (!notif) return;

    // Show toast with exact backend content — never generic
    toastStore.notification(notif.title, notif.message, notif.severity, notif.link_url);

    // Refresh the dropdown if it's open
    if (open) fetchNotifications();
  });

  let loading = $state(false);
  let pollTimer: ReturnType<typeof setInterval> | undefined;

  async function fetchUnreadCount() {
    if (!onboarding.user) return;
    try {
      const data = await api.get<{ count: number }>("/notifications/unread-count/");
      localUnreadCount = data.count;
    } catch {
      // silently ignore
    }
  }

  async function fetchNotifications() {
    loading = true;
    try {
      const data = await api.get<PaginatedResponse<Notification>>("/notifications/", {
        page_size: "10",
      });
      notifications = data.results;
    } catch {
      // silently ignore
    } finally {
      loading = false;
    }
  }

  async function markRead(id: number) {
    try {
      await api.post<Notification>(`/notifications/${id}/read/`, {});
      notifications = notifications.map((n) =>
        n.id === id ? { ...n, is_read: true } : n
      );
      localUnreadCount = Math.max(0, localUnreadCount - 1);
      ws.markRead(id);
    } catch {
      // silently ignore
    }
  }

  async function markAllRead() {
    try {
      await api.post<{ updated: number }>("/notifications/mark-all-read/", {});
      notifications = notifications.map((n) => ({ ...n, is_read: true }));
      localUnreadCount = 0;
    } catch {
      // silently ignore
    }
  }

  function toggle() {
    open = !open;
    if (open) fetchNotifications();
  }

  function handleClickOutside(e: MouseEvent) {
    const target = e.target as HTMLElement;
    if (!target.closest(".notification-bell-root")) {
      open = false;
    }
  }

  function timeAgo(dateStr: string): string {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    if (days < 7) return `${days}d ago`;
    return new Date(dateStr).toLocaleDateString();
  }

  function severityColor(severity: string): string {
    switch (severity) {
      case "critical": return "bg-red-500";
      case "warning": return "bg-amber-500";
      default: return "bg-neutral-400";
    }
  }

  onMount(() => {
    fetchUnreadCount();
    // Poll less frequently when WebSocket is connected (fallback only)
    pollTimer = setInterval(() => {
      if (!ws.connected) fetchUnreadCount();
    }, 30_000);
    document.addEventListener("click", handleClickOutside, true);
  });

  onDestroy(() => {
    if (pollTimer) clearInterval(pollTimer);
    document.removeEventListener("click", handleClickOutside, true);
  });
</script>

<div class="relative notification-bell-root">
  <!-- WS connection indicator -->
  {#if ws.connected}
    <span class="absolute -bottom-0.5 left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full bg-emerald-400" title="Real-time connected"></span>
  {/if}
  <button
    onclick={toggle}
    class="p-2 rounded-lg transition-colors relative
           {open ? 'bg-white/15 text-white' : 'text-neutral-400 hover:bg-white/10 hover:text-neutral-300'}"
    aria-label="Notifications"
  >
    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
      <path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0" />
    </svg>
    {#if unreadCount > 0}
      <span class="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 flex items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white leading-none {badgePulse ? 'notification-badge-pulse' : ''}">
        {unreadCount > 99 ? "99+" : unreadCount}
      </span>
    {/if}
  </button>

  {#if open}
    <div class="absolute right-0 top-full mt-2 w-96 bg-white rounded-xl shadow-2xl border border-neutral-200 z-50 overflow-hidden notification-dropdown-enter">
      <!-- Header -->
      <div class="flex items-center justify-between px-4 py-3 border-b border-neutral-100">
        <div class="flex items-center gap-2">
          <h3 class="text-sm font-semibold text-neutral-900">Notifications</h3>
          {#if ws.connected}
            <span class="flex items-center gap-1 rounded-full bg-emerald-50 border border-emerald-200 px-1.5 py-0.5">
              <span class="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              <span class="text-[9px] font-semibold text-emerald-700">Live</span>
            </span>
          {/if}
        </div>
        {#if unreadCount > 0}
          <button
            onclick={markAllRead}
            class="text-xs font-medium text-neutral-500 hover:text-neutral-900 transition-colors"
          >
            Mark all as read
          </button>
        {/if}
      </div>

      <!-- List -->
      <div class="max-h-[400px] overflow-y-auto">
        {#if loading}
          <div class="py-10 text-center text-sm text-neutral-400">Loading...</div>
        {:else if notifications.length === 0}
          <div class="py-10 text-center">
            <svg class="mx-auto w-8 h-8 text-neutral-300 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0" />
            </svg>
            <p class="text-sm text-neutral-400">No notifications yet</p>
          </div>
        {:else}
          {#each notifications as notif (notif.id)}
            <a
              href="/notifications"
              onclick={() => { if (!notif.is_read) markRead(notif.id); open = false; }}
              class="flex gap-3 px-4 py-3 transition-colors hover:bg-neutral-50
                     {notif.is_read ? '' : 'bg-neutral-50/50'}"
            >
              <div class="mt-1.5 shrink-0">
                <div class="w-2 h-2 rounded-full {severityColor(notif.severity)}"></div>
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-neutral-900 {notif.is_read ? 'font-normal' : ''}">
                  {notif.title}
                </p>
                <p class="text-xs text-neutral-500 mt-0.5 line-clamp-2">{notif.message}</p>
                <p class="text-[11px] text-neutral-400 mt-1">{timeAgo(notif.created_at)}</p>
              </div>
              {#if !notif.is_read}
                <div class="mt-1.5 shrink-0">
                  <div class="w-1.5 h-1.5 rounded-full bg-neutral-900"></div>
                </div>
              {/if}
            </a>
          {/each}
        {/if}
      </div>

      <!-- Footer -->
      <div class="border-t border-neutral-100 px-4 py-2.5">
        <a
          href="/notifications"
          onclick={() => { open = false; }}
          class="block text-center text-xs font-medium text-neutral-500 hover:text-neutral-900 transition-colors"
        >
          View all notifications
        </a>
      </div>
    </div>
  {/if}
</div>

<style>
  .notification-dropdown-enter {
    animation: dropdownFade 0.15s ease-out both;
  }

  @keyframes dropdownFade {
    from {
      opacity: 0;
      transform: translateY(-4px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .notification-badge-pulse {
    animation: badgePulse 1.5s ease-out;
  }

  @keyframes badgePulse {
    0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
    30% { transform: scale(1.3); box-shadow: 0 0 0 6px rgba(239, 68, 68, 0); }
    60% { transform: scale(1); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
    80% { transform: scale(1.15); }
    100% { transform: scale(1); }
  }
</style>

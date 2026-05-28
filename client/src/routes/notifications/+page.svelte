<script lang="ts">
  import { api } from "$lib/api";
  import { onboarding } from "$lib/stores/onboarding.svelte";
  import type { Notification, PaginatedResponse, NotificationSeverity, NotificationCategory } from "$lib/types";

  let notifications = $state<Notification[]>([]);
  let loading = $state(true);
  let totalCount = $state(0);
  let currentPage = $state(1);
  let hasNext = $state(false);
  let hasPrev = $state(false);
  const pageSize = 20;

  // Filters
  let filterSeverity = $state<"" | NotificationSeverity>("");
  let filterCategory = $state<"" | NotificationCategory>("");
  let filterRead = $state<"" | "true" | "false">("");
  let scopeOrg = $state(false);

  let isAdmin = $derived(onboarding.user?.organization?.role === "admin");

  const severityOptions: { value: NotificationSeverity; label: string }[] = [
    { value: "info", label: "Info" },
    { value: "warning", label: "Warning" },
    { value: "critical", label: "Critical" },
  ];

  const categoryOptions: { value: NotificationCategory; label: string }[] = [
    { value: "system", label: "System" },
    { value: "budget_warning", label: "Budget Warning" },
    { value: "budget_exceeded", label: "Budget Exceeded" },
    { value: "budget_digest", label: "Budget Digest" },
    { value: "reports_ready", label: "Reports Ready" },
    { value: "workflow_pending", label: "Workflow Pending" },
    { value: "workflow_approved", label: "Workflow Approved" },
    { value: "workflow_rejected", label: "Workflow Rejected" },
    { value: "workflow_escalated", label: "Workflow Escalated" },
    { value: "workflow_sla_warning", label: "SLA Warning" },
    { value: "delegation_assigned", label: "Delegation Assigned" },
    { value: "delegation_expired", label: "Delegation Expired" },
  ];

  async function fetchNotifications() {
    loading = true;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        page_size: String(pageSize),
      };
      if (filterSeverity) params.severity = filterSeverity;
      if (filterCategory) params.category = filterCategory;
      if (filterRead) params.is_read = filterRead;
      if (scopeOrg && isAdmin) params.scope = "org";

      const data = await api.get<PaginatedResponse<Notification>>("/notifications/", params);
      notifications = data.results;
      totalCount = data.count;
      hasNext = !!data.next;
      hasPrev = !!data.previous;
    } catch {
      notifications = [];
    } finally {
      loading = false;
    }
  }

  async function markRead(id: number) {
    try {
      await api.post<Notification>(`/notifications/${id}/read/`, {});
      notifications = notifications.map((n) =>
        n.id === id ? { ...n, is_read: true, read_at: new Date().toISOString() } : n,
      );
    } catch {
      // silently ignore
    }
  }

  async function markAllRead() {
    try {
      await api.post<{ updated: number }>("/notifications/mark-all-read/", {});
      notifications = notifications.map((n) => ({ ...n, is_read: true, read_at: n.read_at ?? new Date().toISOString() }));
    } catch {
      // silently ignore
    }
  }

  function applyFilters() {
    currentPage = 1;
    fetchNotifications();
  }

  function clearFilters() {
    filterSeverity = "";
    filterCategory = "";
    filterRead = "";
    scopeOrg = false;
    currentPage = 1;
    fetchNotifications();
  }

  function goPage(p: number) {
    currentPage = p;
    fetchNotifications();
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
    return new Date(dateStr).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
  }

  function severityColor(severity: string): string {
    switch (severity) {
      case "critical": return "bg-red-500";
      case "warning": return "bg-amber-500";
      default: return "bg-neutral-400";
    }
  }

  function severityLabel(s: string): string {
    return s.charAt(0).toUpperCase() + s.slice(1);
  }

  function categoryLabel(c: string): string {
    return c.replace(/_/g, " ").replace(/\b\w/g, (ch) => ch.toUpperCase());
  }

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let hasActiveFilters = $derived(!!filterSeverity || !!filterCategory || !!filterRead || scopeOrg);
  let unreadOnPage = $derived(notifications.filter((n) => !n.is_read).length);

  $effect(() => {
    fetchNotifications();
  });
</script>

<svelte:head><title>Notifications | developerOS</title></svelte:head>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-start justify-between">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Notifications</h1>
      <p class="mt-1 text-sm text-neutral-500">
        {#if scopeOrg && isAdmin}
          All notifications across your organization
        {:else}
          Your notifications and alerts
        {/if}
      </p>
    </div>
    {#if unreadOnPage > 0 && !scopeOrg}
      <button
        onclick={markAllRead}
        class="text-sm font-medium text-neutral-500 hover:text-neutral-900 transition-colors"
      >
        Mark all as read
      </button>
    {/if}
  </div>

  <!-- Filters -->
  <div class="bg-white border border-neutral-200 rounded-xl p-4">
    <div class="flex items-center gap-3 flex-wrap">
      <select
        bind:value={filterSeverity}
        onchange={applyFilters}
        class="text-sm border border-neutral-200 rounded-lg px-3 py-1.5 text-neutral-700 bg-white focus:outline-none focus:ring-1 focus:ring-neutral-300"
      >
        <option value="">All Severities</option>
        {#each severityOptions as opt}
          <option value={opt.value}>{opt.label}</option>
        {/each}
      </select>

      <select
        bind:value={filterCategory}
        onchange={applyFilters}
        class="text-sm border border-neutral-200 rounded-lg px-3 py-1.5 text-neutral-700 bg-white focus:outline-none focus:ring-1 focus:ring-neutral-300"
      >
        <option value="">All Categories</option>
        {#each categoryOptions as opt}
          <option value={opt.value}>{opt.label}</option>
        {/each}
      </select>

      <select
        bind:value={filterRead}
        onchange={applyFilters}
        class="text-sm border border-neutral-200 rounded-lg px-3 py-1.5 text-neutral-700 bg-white focus:outline-none focus:ring-1 focus:ring-neutral-300"
      >
        <option value="">Read & Unread</option>
        <option value="false">Unread only</option>
        <option value="true">Read only</option>
      </select>

      {#if hasActiveFilters}
        <button
          onclick={clearFilters}
          class="text-xs font-medium text-neutral-400 hover:text-neutral-700 transition-colors {isAdmin ? '' : 'ml-auto'}"
        >
          Clear filters
        </button>
      {/if}
    </div>
  </div>

  <!-- List -->
  {#if loading}
    <div class="flex items-center justify-center py-24">
      <div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div>
    </div>
  {:else if notifications.length === 0}
    <div class="text-center py-24">
      <svg class="mx-auto w-10 h-10 text-neutral-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0" />
      </svg>
      <p class="text-sm text-neutral-500">No notifications found</p>
      {#if hasActiveFilters}
        <button onclick={clearFilters} class="mt-2 text-sm font-medium text-neutral-400 hover:text-neutral-700 transition-colors">
          Clear filters
        </button>
      {/if}
    </div>
  {:else}
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden divide-y divide-neutral-100">
      {#each notifications as notif (notif.id)}
        <div
          class="flex items-start gap-4 px-5 py-4 cursor-default select-text
                 {notif.is_read ? '' : 'bg-neutral-50/60'}"
        >
          <!-- Severity dot -->
          <div class="mt-1.5 shrink-0">
            <div class="w-2.5 h-2.5 rounded-full {severityColor(notif.severity)}"></div>
          </div>

          <!-- Content -->
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2">
              <p class="text-sm text-neutral-900 {notif.is_read ? '' : 'font-semibold'} truncate">
                {notif.title}
              </p>
              {#if !notif.is_read}
                <div class="w-1.5 h-1.5 rounded-full bg-neutral-900 shrink-0"></div>
              {/if}
            </div>
            <p class="text-sm text-neutral-500 mt-0.5 line-clamp-2">{notif.message}</p>

            <div class="flex items-center gap-3 mt-2">
              <span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-neutral-100 text-neutral-500">
                {categoryLabel(notif.category)}
              </span>
              <span class="text-[11px] text-neutral-400">{severityLabel(notif.severity)}</span>
              {#if scopeOrg && notif.recipient_name}
                <span class="text-[11px] text-neutral-400">{notif.recipient_name}</span>
              {/if}
            </div>
          </div>

          <!-- Timestamp -->
          <div class="shrink-0 text-right">
            <p class="text-xs text-neutral-400 whitespace-nowrap">{timeAgo(notif.created_at)}</p>
            {#if scopeOrg && notif.recipient_email}
              <p class="text-[11px] text-neutral-400 mt-0.5">{notif.recipient_email}</p>
            {/if}
          </div>
        </div>
      {/each}
    </div>

    <!-- Pagination -->
    {#if totalPages > 1}
      <div class="flex items-center justify-between mt-4">
        <p class="text-xs text-neutral-400 tabular-nums">
          {(currentPage - 1) * pageSize + 1}&ndash;{Math.min(currentPage * pageSize, totalCount)} of {totalCount}
        </p>
        <div class="flex items-center gap-1">
          <button
            onclick={() => goPage(currentPage - 1)}
            disabled={!hasPrev}
            class="px-3 py-1.5 text-sm font-medium rounded-lg border border-neutral-200 transition-colors
                   {hasPrev ? 'text-neutral-700 hover:bg-neutral-50' : 'text-neutral-300 cursor-not-allowed'}"
          >
            Previous
          </button>
          <span class="px-3 py-1.5 text-sm text-neutral-500 tabular-nums">
            {currentPage} / {totalPages}
          </span>
          <button
            onclick={() => goPage(currentPage + 1)}
            disabled={!hasNext}
            class="px-3 py-1.5 text-sm font-medium rounded-lg border border-neutral-200 transition-colors
                   {hasNext ? 'text-neutral-700 hover:bg-neutral-50' : 'text-neutral-300 cursor-not-allowed'}"
          >
            Next
          </button>
        </div>
      </div>
    {/if}
  {/if}
</div>

<script lang="ts">
  import { api } from "$lib/api";
  import { parsePortalError } from "$lib/partnerPortal";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    Notification,
    PaginatedResponse,
    PartnerPortalContextResponse,
  } from "$lib/types";

  let loading = $state(true);
  let context = $state<PartnerPortalContextResponse | null>(null);
  let rows = $state<Notification[]>([]);
  let page = $state(1);
  let pageSize = $state(20);
  let count = $state(0);
  let readFilter = $state("");

  const totalPages = $derived(Math.max(1, Math.ceil(count / pageSize)));

  function titleCase(value: string): string {
    return value
      .replaceAll("_", " ")
      .split(" ")
      .filter(Boolean)
      .map((part) => part[0]?.toUpperCase() + part.slice(1))
      .join(" ");
  }

  function fmtDate(value: string): string {
    return new Date(value).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  async function loadNotifications() {
    loading = true;
    try {
      if (!context) {
        context = await api.get<PartnerPortalContextResponse>("/partners/portal/context/");
      }
      if (context && !context.is_partner_user && !context.is_preview_mode) {
        rows = [];
        count = 0;
        return;
      }
      const response = await api.get<PaginatedResponse<Notification>>(
        "/partners/portal/notifications/",
        {
          page: String(page),
          page_size: String(pageSize),
          is_read: readFilter,
        },
      );
      rows = response.results;
      count = response.count;
    } catch (error) {
      toast.error("Load failed", parsePortalError(error, "Could not load portal notifications."));
    } finally {
      loading = false;
    }
  }

  function applyFilter() {
    page = 1;
    loadNotifications();
  }

  $effect(() => {
    loadNotifications();
  });
</script>

{#if context && !context.is_partner_user && !context.is_preview_mode}
  <div class="rounded-xl border border-amber-200 bg-amber-50 px-6 py-5">
    <h1 class="text-lg font-semibold text-amber-900">No notifications access yet</h1>
    <p class="mt-1 text-sm text-amber-800">Notification delivery starts after portal activation.</p>
  </div>
{:else}
  <div class="space-y-6">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-neutral-900">Notifications</h1>
        <p class="mt-1 text-sm text-neutral-500">SLA-driven alerts and communication updates</p>
      </div>
      <button
        onclick={() => loadNotifications()}
        class="rounded-lg border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
      >
        Refresh
      </button>
    </div>

    <div class="flex items-center justify-between rounded-xl border border-neutral-200 bg-white p-4">
      <div class="flex items-center gap-2">
        <select bind:value={readFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          <option value="">All notifications</option>
          <option value="false">Unread only</option>
          <option value="true">Read only</option>
        </select>
        <button
          onclick={() => applyFilter()}
          class="rounded-lg border border-neutral-900 bg-neutral-900 px-3 py-2 text-sm font-medium text-white hover:bg-neutral-800"
        >
          Apply
        </button>
      </div>
      <p class="text-sm text-neutral-600">Total {count}</p>
    </div>

    <div class="overflow-hidden rounded-xl border border-neutral-200 bg-white">
      {#if loading}
        <div class="flex items-center justify-center py-20">
          <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
        </div>
      {:else if rows.length === 0}
        <div class="px-6 py-16 text-center text-sm text-neutral-500">No notifications found.</div>
      {:else}
        <div class="divide-y divide-neutral-100">
          {#each rows as row (row.id)}
            <div class="px-5 py-4 {row.is_read ? 'bg-white' : 'bg-indigo-50/40'}">
              <div class="flex items-start justify-between gap-3">
                <div>
                  <p class="text-sm font-semibold text-neutral-900">{row.title}</p>
                  <p class="mt-1 text-sm text-neutral-700">{row.message}</p>
                  <p class="mt-2 text-xs text-neutral-500">{titleCase(row.category)} • {fmtDate(row.created_at)}</p>
                </div>
                <span class="rounded-full border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide {row.is_read ? 'border-neutral-200 text-neutral-500' : 'border-indigo-200 bg-indigo-100 text-indigo-700'}">
                  {row.is_read ? "Read" : "Unread"}
                </span>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>

    <div class="flex items-center justify-between rounded-xl border border-neutral-200 bg-white px-4 py-3 text-sm">
      <p class="text-neutral-600">Showing {(page - 1) * pageSize + (rows.length === 0 ? 0 : 1)}-{(page - 1) * pageSize + rows.length} of {count}</p>
      <div class="flex items-center gap-2">
        <button
          onclick={() => {
            if (page > 1) {
              page -= 1;
              loadNotifications();
            }
          }}
          class="rounded-lg border border-neutral-200 px-3 py-1.5 text-neutral-700 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-40"
          disabled={page <= 1}
        >
          Previous
        </button>
        <span class="text-neutral-600">Page {page} of {totalPages}</span>
        <button
          onclick={() => {
            if (page < totalPages) {
              page += 1;
              loadNotifications();
            }
          }}
          class="rounded-lg border border-neutral-200 px-3 py-1.5 text-neutral-700 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-40"
          disabled={page >= totalPages}
        >
          Next
        </button>
      </div>
    </div>
  </div>
{/if}

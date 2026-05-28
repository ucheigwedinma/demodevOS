<script lang="ts">
  import { api } from "$lib/api";
  import { parsePortalError } from "$lib/partnerPortal";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    PaginatedResponse,
    PartnerPortalCommunicationItem,
    PartnerPortalContextResponse,
  } from "$lib/types";

  let loading = $state(true);
  let context = $state<PartnerPortalContextResponse | null>(null);
  let rows = $state<PartnerPortalCommunicationItem[]>([]);
  let page = $state(1);
  let pageSize = $state(20);
  let count = $state(0);
  let query = $state("");
  let channel = $state("");
  let direction = $state("");

  const totalPages = $derived(Math.max(1, Math.ceil(count / pageSize)));

  function fmtDate(value: string): string {
    return new Date(value).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function titleCase(value: string): string {
    return value
      .replaceAll("_", " ")
      .split(" ")
      .filter(Boolean)
      .map((part) => part[0]?.toUpperCase() + part.slice(1))
      .join(" ");
  }

  async function loadCommunication() {
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
      const response = await api.get<PaginatedResponse<PartnerPortalCommunicationItem>>(
        "/partners/portal/communications/",
        {
          page: String(page),
          page_size: String(pageSize),
          q: query.trim(),
          channel,
          direction,
        },
      );
      rows = response.results;
      count = response.count;
    } catch (error) {
      toast.error("Load failed", parsePortalError(error, "Could not load portal communications."));
    } finally {
      loading = false;
    }
  }

  function applyFilters() {
    page = 1;
    loadCommunication();
  }

  $effect(() => {
    loadCommunication();
  });
</script>

{#if context && !context.is_partner_user && !context.is_preview_mode}
  <div class="rounded-xl border border-amber-200 bg-amber-50 px-6 py-5">
    <h1 class="text-lg font-semibold text-amber-900">No communication access yet</h1>
    <p class="mt-1 text-sm text-amber-800">Communication history appears after portal entitlement is active.</p>
  </div>
{:else}
  <div class="space-y-6">
    <div class="flex items-start justify-between gap-4">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-slate-700">Partners</p>
        <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Communication Center</h1>
        <p class="mt-1 text-sm text-neutral-500">Inbound/Outbound engagement timeline history for stakeholders.</p>
      </div>
      <button
        onclick={() => loadCommunication()}
        class="rounded-lg border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
      >
        Refresh
      </button>
    </div>

    <div class="grid grid-cols-1 gap-3 rounded-xl border border-neutral-200 bg-white p-4 md:grid-cols-4">
      <input
        bind:value={query}
        placeholder="Search subject or summary"
        class="rounded-lg border border-neutral-200 px-3 py-2 text-sm md:col-span-2"
      />
      <select bind:value={channel} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="">All channels</option>
        <option value="email">Email</option>
        <option value="whatsapp">WhatsApp</option>
        <option value="sms">SMS</option>
        <option value="phone">Phone</option>
        <option value="video_call">Video call</option>
        <option value="in_person">In-person</option>
      </select>
      <div class="flex gap-2">
        <select bind:value={direction} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          <option value="">All directions</option>
          <option value="outbound">Outbound</option>
          <option value="inbound">Inbound</option>
        </select>
        <button
          onclick={() => applyFilters()}
          class="rounded-lg border border-neutral-900 bg-neutral-900 px-3 py-2 text-sm font-medium text-white hover:bg-neutral-800"
        >
          Apply
        </button>
      </div>
    </div>

    <div class="overflow-hidden rounded-xl border border-neutral-200 bg-white">
      {#if loading}
        <div class="flex items-center justify-center py-20">
          <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
        </div>
      {:else if rows.length === 0}
        <div class="px-6 py-16 text-center text-sm text-neutral-500">No communication logs found.</div>
      {:else}
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-neutral-100 text-sm">
            <thead class="bg-neutral-50 text-xs uppercase tracking-wider text-neutral-500">
              <tr>
                <th class="px-4 py-3 text-left">Date</th>
                <th class="px-4 py-3 text-left">Lead</th>
                <th class="px-4 py-3 text-left">Channel</th>
                <th class="px-4 py-3 text-left">Direction</th>
                <th class="px-4 py-3 text-left">Summary</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each rows as row (row.id)}
                <tr>
                  <td class="px-4 py-3 text-neutral-700">{fmtDate(row.communicated_at)}</td>
                  <td class="px-4 py-3 text-neutral-700">{row.lead_name}</td>
                  <td class="px-4 py-3 text-neutral-700">{titleCase(row.channel)}</td>
                  <td class="px-4 py-3 text-neutral-700">{titleCase(row.direction)}</td>
                  <td class="px-4 py-3">
                    <p class="font-medium text-neutral-900">{row.subject || "(No subject)"}</p>
                    <p class="text-xs text-neutral-500 line-clamp-2">{row.summary || row.body || "--"}</p>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
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
              loadCommunication();
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
              loadCommunication();
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

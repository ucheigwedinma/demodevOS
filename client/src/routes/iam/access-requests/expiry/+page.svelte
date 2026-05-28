<script lang="ts">
  import { api } from "$lib/api";

  type AccessRequestItem = {
    id: number;
    kind: "role_grant" | "role_elevation" | "resource_access";
    kind_display: string;
    requester_name: string;
    requester_email: string;
    approver_name: string;
    requested_role_name: string;
    granted_valid_until: string | null;
    approval_decision_at: string | null;
  };
  type ExpiringResponse = {
    count: number;
    results: AccessRequestItem[];
    overview: { already_expired: number; within_days: number };
  };

  let items = $state<AccessRequestItem[]>([]);
  let alreadyExpired = $state(0);
  let totalCount = $state(0);
  let loading = $state(true);
  let withinDays = $state(7);

  const WINDOW_OPTIONS = [
    { v: 1, label: "24h" },
    { v: 3, label: "3 days" },
    { v: 7, label: "7 days" },
    { v: 30, label: "30 days" },
    { v: 90, label: "90 days" },
  ];

  function formatDate(d: string | null): string {
    if (!d) return "—";
    return new Date(d).toLocaleString("en-US", {
      month: "short", day: "numeric", year: "numeric",
      hour: "numeric", minute: "2-digit",
    });
  }

  function timeUntil(d: string | null): string {
    if (!d) return "—";
    const diff = new Date(d).getTime() - Date.now();
    if (diff <= 0) return "Expired";
    const days = Math.floor(diff / 86_400_000);
    const hours = Math.floor((diff % 86_400_000) / 3_600_000);
    if (days >= 1) return `${days}d ${hours}h`;
    if (hours >= 1) return `${hours}h`;
    return `${Math.floor((diff % 3_600_000) / 60_000)}m`;
  }

  async function fetchItems() {
    loading = true;
    try {
      const res = await api.get<ExpiringResponse>("/iam/access-requests/expiring/", {
        within_days: String(withinDays),
      });
      items = res.results;
      totalCount = res.count;
      alreadyExpired = res.overview.already_expired;
    } catch {
      items = [];
      totalCount = 0;
      alreadyExpired = 0;
    } finally {
      loading = false;
    }
  }

  $effect(() => { void withinDays; fetchItems(); });
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Access Expiry</h1>
    <p class="mt-1 text-sm text-neutral-500">
      Approved temporary grants approaching their expiry. The daily sweeper runs at 06:00 UTC
      and auto-revokes any grant whose window has passed.
    </p>
  </div>

  <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
    <div class="rounded-xl border border-neutral-200 bg-white p-5">
      <p class="text-xs font-medium text-yellow-600 uppercase tracking-wider">
        Expiring within {withinDays} {withinDays === 1 ? "day" : "days"}
      </p>
      <p class="mt-2 text-3xl font-bold text-neutral-900">{totalCount}</p>
    </div>
    <div class="rounded-xl border border-neutral-200 bg-white p-5">
      <p class="text-xs font-medium text-red-600 uppercase tracking-wider">Already expired (awaiting sweeper)</p>
      <p class="mt-2 text-3xl font-bold text-neutral-900">{alreadyExpired}</p>
    </div>
    <a href="/iam/access-requests/temporary"
      class="rounded-xl border border-neutral-200 bg-white p-5 hover:border-neutral-400 hover:shadow-sm transition-all">
      <p class="text-xs font-medium text-neutral-500 uppercase tracking-wider">All temporary grants</p>
      <p class="mt-2 text-sm text-neutral-700">View full list →</p>
    </a>
  </div>

  <div class="flex gap-2 flex-wrap items-center">
    <span class="text-sm font-medium text-neutral-600 mr-2">Show grants expiring in:</span>
    {#each WINDOW_OPTIONS as opt}
      <button onclick={() => (withinDays = opt.v)}
        class="rounded-lg px-4 py-2 text-sm font-medium transition-colors
               {withinDays === opt.v ? 'bg-neutral-800 text-white' : 'bg-white border border-neutral-200 text-neutral-600 hover:bg-neutral-50'}">
        {opt.label}
      </button>
    {/each}
  </div>

  <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
    {#if loading}
      <div class="p-16 text-center">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
      </div>
    {:else if items.length === 0}
      <div class="p-16 text-center">
        <h3 class="text-sm font-semibold text-neutral-800">All clear</h3>
        <p class="mt-1.5 text-sm text-neutral-500">No grants are expiring within the selected window.</p>
      </div>
    {:else}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50">
            <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">User</th>
            <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Role</th>
            <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Granted by</th>
            <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Expires at</th>
            <th class="px-5 py-3 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Time left</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each items as it}
            <tr class="hover:bg-neutral-50 transition-colors">
              <td class="px-5 py-4">
                <p class="font-medium text-neutral-800">{it.requester_name}</p>
                <p class="text-xs text-neutral-500">{it.requester_email}</p>
              </td>
              <td class="px-5 py-4 text-neutral-700">{it.requested_role_name || "—"}</td>
              <td class="px-5 py-4 text-neutral-700">{it.approver_name || "—"}</td>
              <td class="px-5 py-4 text-neutral-600 whitespace-nowrap">{formatDate(it.granted_valid_until)}</td>
              <td class="px-5 py-4 text-center">
                <span class="inline-flex items-center rounded-full bg-yellow-50 px-2.5 py-0.5 text-xs font-medium text-yellow-700">
                  {timeUntil(it.granted_valid_until)}
                </span>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>
</div>

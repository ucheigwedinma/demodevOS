<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";

  type DormantUser = {
    id: number;
    name: string;
    email: string;
    last_login: string | null;
    date_joined: string | null;
    role_name: string;
    user_status: string;
    days_since_login: number | null;
  };
  type DormantResponse = {
    count: number;
    results: DormantUser[];
    overview: {
      threshold_days: number;
      dormant: number;
      active: number;
      never_logged_in: number;
    };
  };

  let users = $state<DormantUser[]>([]);
  let totalCount = $state(0);
  let overview = $state({
    threshold_days: 60, dormant: 0, active: 0, never_logged_in: 0,
  });
  let loading = $state(true);
  let threshold = $state(60);
  let suspending = $state<number | null>(null);

  const THRESHOLD_OPTIONS = [
    { v: 30, label: "30 days" },
    { v: 60, label: "60 days" },
    { v: 90, label: "90 days" },
    { v: 180, label: "180 days" },
    { v: 365, label: "1 year" },
  ];

  function formatDate(d: string | null): string {
    if (!d) return "Never";
    return new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  async function fetchDormant() {
    loading = true;
    try {
      const res = await api.get<DormantResponse>("/iam/compliance/dormant-accounts/", {
        threshold_days: String(threshold),
      });
      users = res.results;
      totalCount = res.count;
      overview = res.overview;
    } catch {
      users = [];
      totalCount = 0;
    } finally {
      loading = false;
    }
  }

  async function suspend(userId: number) {
    suspending = userId;
    try {
      await api.post(`/iam/users/${userId}/suspend/`, {});
      toast.success("Suspended", "Account suspended.");
      await fetchDormant();
    } catch {
      toast.error("Action failed", "Could not suspend the account.");
    } finally {
      suspending = null;
    }
  }

  $effect(() => { void threshold; fetchDormant(); });
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Dormant Accounts</h1>
    <p class="mt-1 text-sm text-neutral-500">
      Active org users with no recent login activity. Suspend or review them per your account-lifecycle policy.
      Only currently-active users are listed; already-suspended accounts are excluded.
    </p>
  </div>

  <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
    <div class="rounded-xl border border-neutral-200 bg-white p-5">
      <p class="text-xs font-medium text-yellow-600 uppercase tracking-wider">
        Dormant ≥ {overview.threshold_days} days
      </p>
      <p class="mt-2 text-3xl font-bold text-neutral-900">{overview.dormant}</p>
    </div>
    <div class="rounded-xl border border-neutral-200 bg-white p-5">
      <p class="text-xs font-medium text-green-600 uppercase tracking-wider">Recently active</p>
      <p class="mt-2 text-3xl font-bold text-neutral-900">{overview.active}</p>
    </div>
    <div class="rounded-xl border border-neutral-200 bg-white p-5">
      <p class="text-xs font-medium text-red-600 uppercase tracking-wider">Never logged in</p>
      <p class="mt-2 text-3xl font-bold text-neutral-900">{overview.never_logged_in}</p>
    </div>
  </div>

  <div class="flex gap-2 flex-wrap items-center">
    <span class="text-sm font-medium text-neutral-600 mr-2">Inactivity threshold:</span>
    {#each THRESHOLD_OPTIONS as opt}
      <button onclick={() => (threshold = opt.v)}
        class="rounded-lg px-4 py-2 text-sm font-medium transition-colors
               {threshold === opt.v ? 'bg-neutral-800 text-white' : 'bg-white border border-neutral-200 text-neutral-600 hover:bg-neutral-50'}">
        {opt.label}
      </button>
    {/each}
  </div>

  <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
    {#if loading}
      <div class="p-16 text-center">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
      </div>
    {:else if users.length === 0}
      <div class="p-16 text-center">
        <h3 class="text-sm font-semibold text-neutral-800">No dormant accounts</h3>
        <p class="mt-1.5 text-sm text-neutral-500">All active users have logged in within the threshold.</p>
      </div>
    {:else}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50">
            <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">User</th>
            <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Role</th>
            <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Last login</th>
            <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Joined</th>
            <th class="px-5 py-3 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each users as u}
            <tr class="hover:bg-neutral-50 transition-colors">
              <td class="px-5 py-4">
                <p class="font-medium text-neutral-800">{u.name}</p>
                <p class="text-xs text-neutral-500">{u.email}</p>
              </td>
              <td class="px-5 py-4 text-neutral-700">{u.role_name || "—"}</td>
              <td class="px-5 py-4">
                <p class="text-neutral-600">{formatDate(u.last_login)}</p>
                {#if u.days_since_login !== null}
                  <p class="text-[11px] text-yellow-700">{u.days_since_login} days ago</p>
                {:else}
                  <p class="text-[11px] text-red-700">Never logged in</p>
                {/if}
              </td>
              <td class="px-5 py-4 text-neutral-600">{formatDate(u.date_joined)}</td>
              <td class="px-5 py-4 text-right">
                <button onclick={() => suspend(u.id)} disabled={suspending === u.id}
                  class="rounded-lg px-3 py-1.5 text-xs font-medium text-yellow-700 bg-yellow-50 hover:bg-yellow-100 transition-colors disabled:opacity-50">
                  {suspending === u.id ? "..." : "Suspend"}
                </button>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>
</div>

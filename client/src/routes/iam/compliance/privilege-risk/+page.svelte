<script lang="ts">
  import { api } from "$lib/api";

  type RiskRow = {
    user_id: number;
    name: string;
    email: string;
    role_name: string;
    permission_count: number;
    is_system_role: boolean;
    sensitive_permissions: boolean;
    days_since_login: number | null;
    recent_risky_events: number;
    score: number;
    tier: "low" | "medium" | "high" | "critical";
  };
  type RiskResponse = {
    count: number;
    results: RiskRow[];
    overview: { low: number; medium: number; high: number; critical: number };
  };

  let rows = $state<RiskRow[]>([]);
  let totalCount = $state(0);
  let overview = $state({ low: 0, medium: 0, high: 0, critical: 0 });
  let loading = $state(true);
  let tierFilter = $state<"" | "low" | "medium" | "high" | "critical">("");

  let visible = $derived(tierFilter ? rows.filter((r) => r.tier === tierFilter) : rows);

  function tierClasses(t: string): string {
    return ({
      low: "bg-neutral-100 text-neutral-600",
      medium: "bg-yellow-50 text-yellow-700",
      high: "bg-orange-50 text-orange-700",
      critical: "bg-red-50 text-red-700",
    } as Record<string, string>)[t];
  }

  function scoreBarColour(score: number): string {
    if (score >= 80) return "bg-red-500";
    if (score >= 60) return "bg-orange-500";
    if (score >= 30) return "bg-yellow-500";
    return "bg-neutral-400";
  }

  async function fetchRisk() {
    loading = true;
    try {
      const res = await api.get<RiskResponse>("/iam/compliance/privilege-risk/");
      rows = res.results;
      totalCount = res.count;
      overview = res.overview;
    } catch {
      rows = [];
      totalCount = 0;
    } finally {
      loading = false;
    }
  }

  $effect(() => { fetchRisk(); });
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Privilege Risk Analysis</h1>
    <p class="mt-1 text-sm text-neutral-500">
      Composite risk score per user (0–100) combining permission breadth, sensitivity (admin /
      configure / delete actions), system-role status, login staleness, and recent risky events
      (revoked grants, failed logins). Tune the inputs in
      <code class="text-xs bg-neutral-100 px-1.5 py-0.5 rounded">apps.accounts.iam_views.PrivilegeRiskView</code>.
    </p>
  </div>

  <div class="grid grid-cols-1 sm:grid-cols-4 gap-4">
    <button onclick={() => (tierFilter = tierFilter === "low" ? "" : "low")}
      class="rounded-xl border bg-white p-5 text-left transition-all
             {tierFilter === 'low' ? 'border-neutral-800 shadow-sm' : 'border-neutral-200 hover:border-neutral-400'}">
      <p class="text-xs font-medium text-neutral-500 uppercase tracking-wider">Low</p>
      <p class="mt-2 text-3xl font-bold text-neutral-900">{overview.low}</p>
    </button>
    <button onclick={() => (tierFilter = tierFilter === "medium" ? "" : "medium")}
      class="rounded-xl border bg-white p-5 text-left transition-all
             {tierFilter === 'medium' ? 'border-neutral-800 shadow-sm' : 'border-neutral-200 hover:border-neutral-400'}">
      <p class="text-xs font-medium text-yellow-700 uppercase tracking-wider">Medium</p>
      <p class="mt-2 text-3xl font-bold text-neutral-900">{overview.medium}</p>
    </button>
    <button onclick={() => (tierFilter = tierFilter === "high" ? "" : "high")}
      class="rounded-xl border bg-white p-5 text-left transition-all
             {tierFilter === 'high' ? 'border-neutral-800 shadow-sm' : 'border-neutral-200 hover:border-neutral-400'}">
      <p class="text-xs font-medium text-orange-700 uppercase tracking-wider">High</p>
      <p class="mt-2 text-3xl font-bold text-neutral-900">{overview.high}</p>
    </button>
    <button onclick={() => (tierFilter = tierFilter === "critical" ? "" : "critical")}
      class="rounded-xl border bg-white p-5 text-left transition-all
             {tierFilter === 'critical' ? 'border-neutral-800 shadow-sm' : 'border-neutral-200 hover:border-neutral-400'}">
      <p class="text-xs font-medium text-red-700 uppercase tracking-wider">Critical</p>
      <p class="mt-2 text-3xl font-bold text-neutral-900">{overview.critical}</p>
    </button>
  </div>

  {#if tierFilter}
    <p class="text-xs text-neutral-500">
      Showing only <span class="font-semibold">{tierFilter}</span> tier.
      <button class="underline underline-offset-2 hover:text-neutral-800" onclick={() => (tierFilter = "")}>Clear filter</button>
    </p>
  {/if}

  <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
    {#if loading}
      <div class="p-16 text-center">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
      </div>
    {:else if visible.length === 0}
      <div class="p-16 text-center">
        <h3 class="text-sm font-semibold text-neutral-800">No users in this tier</h3>
      </div>
    {:else}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50">
            <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">User</th>
            <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Role</th>
            <th class="px-5 py-3 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Permissions</th>
            <th class="px-5 py-3 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Stale</th>
            <th class="px-5 py-3 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Risky 30d</th>
            <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Score</th>
            <th class="px-5 py-3 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Tier</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each visible as r}
            <tr class="hover:bg-neutral-50 transition-colors">
              <td class="px-5 py-4">
                <p class="font-medium text-neutral-800">{r.name}</p>
                <p class="text-xs text-neutral-500 truncate">{r.email}</p>
              </td>
              <td class="px-5 py-4 text-neutral-700">
                {r.role_name || "—"}
                {#if r.is_system_role}
                  <span class="ml-1 inline-flex items-center rounded-full bg-neutral-800 px-1.5 py-0.5 text-[9px] font-medium text-white">SYS</span>
                {/if}
                {#if r.sensitive_permissions}
                  <span class="ml-1 inline-flex items-center rounded-full bg-orange-100 px-1.5 py-0.5 text-[9px] font-medium text-orange-700">⚠</span>
                {/if}
              </td>
              <td class="px-5 py-4 text-center text-neutral-700">{r.permission_count}</td>
              <td class="px-5 py-4 text-center text-neutral-600 text-xs">
                {r.days_since_login !== null ? `${r.days_since_login}d` : "Never"}
              </td>
              <td class="px-5 py-4 text-center">
                {#if r.recent_risky_events > 0}
                  <span class="inline-flex items-center rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700">
                    {r.recent_risky_events}
                  </span>
                {:else}
                  <span class="text-neutral-400">—</span>
                {/if}
              </td>
              <td class="px-5 py-4">
                <div class="flex items-center gap-2">
                  <span class="text-sm font-semibold text-neutral-800 w-8 text-right">{r.score}</span>
                  <div class="flex-1 h-1.5 bg-neutral-100 rounded-full overflow-hidden max-w-[100px]">
                    <div class="h-full {scoreBarColour(r.score)}" style="width: {r.score}%"></div>
                  </div>
                </div>
              </td>
              <td class="px-5 py-4 text-center">
                <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium {tierClasses(r.tier)}">
                  {r.tier}
                </span>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>

  <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-4 text-xs text-neutral-600">
    <p class="font-medium text-neutral-700 mb-1">Score composition (max 100)</p>
    <ul class="space-y-0.5 list-disc pl-5">
      <li>Permission breadth: 2 × count, capped at 40</li>
      <li>Sensitivity flag (admin / configure / delete): +20</li>
      <li>System role assigned: +10</li>
      <li>Stale-ness: +4 per 30 days since last login, capped at 20</li>
      <li>Recent risky events (revoked, auto-revoked, failed logins): +1 each, capped at 10</li>
    </ul>
  </div>
</div>

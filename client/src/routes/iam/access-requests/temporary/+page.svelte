<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";

  type AccessRequestItem = {
    id: number;
    kind: "role_grant" | "role_elevation" | "resource_access";
    kind_display: string;
    status: "pending" | "approved" | "rejected" | "expired" | "cancelled" | "revoked";
    status_display: string;
    requester_id: number;
    requester_name: string;
    requester_email: string;
    approver_name: string;
    requested_role_name: string;
    requested_resource: string;
    reason: string;
    granted_valid_until: string | null;
    approval_decision_at: string | null;
    created_at: string;
  };
  type AccessRequestListResponse = {
    count: number;
    results: AccessRequestItem[];
    overview: { pending: number; approved: number; rejected: number; to_approve: number };
  };

  let items = $state<AccessRequestItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let revoking = $state<number | null>(null);
  let confirmRevoke = $state<AccessRequestItem | null>(null);
  let revokeNotes = $state("");

  function formatDate(d: string | null): string {
    if (!d) return "—";
    return new Date(d).toLocaleString("en-US", {
      month: "short", day: "numeric", year: "numeric",
      hour: "numeric", minute: "2-digit",
    });
  }

  function timeUntil(d: string | null): { label: string; tone: "ok" | "soon" | "expired" } {
    if (!d) return { label: "Permanent", tone: "ok" };
    const now = Date.now();
    const t = new Date(d).getTime();
    const diff = t - now;
    if (diff <= 0) return { label: "Expired", tone: "expired" };
    const days = Math.floor(diff / 86_400_000);
    const hours = Math.floor((diff % 86_400_000) / 3_600_000);
    if (days >= 1) return { label: `${days}d ${hours}h`, tone: days <= 2 ? "soon" : "ok" };
    if (hours >= 1) return { label: `${hours}h`, tone: "soon" };
    const mins = Math.floor((diff % 3_600_000) / 60_000);
    return { label: `${mins}m`, tone: "soon" };
  }

  async function fetchItems() {
    loading = true;
    try {
      const res = await api.get<AccessRequestListResponse>("/iam/access-requests/", {
        scope: "temporary",
        status: "approved",
        page_size: "100",
      });
      items = res.results.sort((a, b) => {
        const ax = a.granted_valid_until ? new Date(a.granted_valid_until).getTime() : Infinity;
        const bx = b.granted_valid_until ? new Date(b.granted_valid_until).getTime() : Infinity;
        return ax - bx;
      });
      totalCount = res.count;
    } catch {
      items = [];
      totalCount = 0;
    } finally {
      loading = false;
    }
  }

  async function doRevoke() {
    if (!confirmRevoke) return;
    revoking = confirmRevoke.id;
    try {
      await api.post(`/iam/access-requests/${confirmRevoke.id}/revoke/`, { notes: revokeNotes });
      toast.success("Revoked", `Access for ${confirmRevoke.requester_name} cleared.`);
      confirmRevoke = null;
      revokeNotes = "";
      await fetchItems();
    } catch {
      toast.error("Action failed", "Could not revoke this grant.");
    } finally {
      revoking = null;
    }
  }

  $effect(() => { fetchItems(); });
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Temporary Access</h1>
    <p class="mt-1 text-sm text-neutral-500">
      All approved time-bound role grants. Sorted by expiry; the daily sweeper auto-revokes
      the assignment once <code class="text-xs bg-neutral-100 px-1.5 py-0.5 rounded">granted_valid_until</code> passes.
    </p>
  </div>

  <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
    {#if loading}
      <div class="p-16 text-center">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
      </div>
    {:else if items.length === 0}
      <div class="p-16 text-center">
        <h3 class="text-sm font-semibold text-neutral-800">No temporary grants</h3>
        <p class="mt-1.5 text-sm text-neutral-500">Approved temporary access will appear here.</p>
      </div>
    {:else}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50">
            <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">User</th>
            <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Role</th>
            <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Approved by</th>
            <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Approved at</th>
            <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Expires</th>
            <th class="px-5 py-3 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Time left</th>
            <th class="px-5 py-3 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each items as it}
            {@const tu = timeUntil(it.granted_valid_until)}
            <tr class="hover:bg-neutral-50 transition-colors">
              <td class="px-5 py-4">
                <p class="font-medium text-neutral-800">{it.requester_name}</p>
                <p class="text-xs text-neutral-500">{it.requester_email}</p>
              </td>
              <td class="px-5 py-4 text-neutral-700">{it.requested_role_name || "—"}</td>
              <td class="px-5 py-4 text-neutral-700">{it.approver_name || "—"}</td>
              <td class="px-5 py-4 text-neutral-600 whitespace-nowrap">{formatDate(it.approval_decision_at)}</td>
              <td class="px-5 py-4 text-neutral-600 whitespace-nowrap">{formatDate(it.granted_valid_until)}</td>
              <td class="px-5 py-4 text-center">
                <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium
                             {tu.tone === 'expired' ? 'bg-neutral-100 text-neutral-600' :
                              tu.tone === 'soon' ? 'bg-yellow-50 text-yellow-700' :
                              'bg-green-50 text-green-700'}">
                  {tu.label}
                </span>
              </td>
              <td class="px-5 py-4 text-right">
                <button onclick={() => { confirmRevoke = it; revokeNotes = ""; }}
                  disabled={revoking === it.id}
                  class="rounded-lg px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50">
                  Revoke now
                </button>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>
</div>

{#if confirmRevoke}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (confirmRevoke = null)} aria-label="Close"></button>
    <div class="relative w-full max-w-md rounded-2xl bg-white shadow-2xl border border-neutral-200 p-6">
      <h3 class="text-lg font-bold text-neutral-800">Revoke access</h3>
      <p class="mt-2 text-sm text-neutral-600">
        This will immediately remove the role <strong>{confirmRevoke.requested_role_name}</strong>
        from <strong>{confirmRevoke.requester_name}</strong>.
      </p>
      <label for="revoke-notes" class="block mt-4 text-xs font-medium text-neutral-700 mb-1.5">
        Notes <span class="font-normal text-neutral-500">(optional)</span>
      </label>
      <textarea id="revoke-notes" rows="3" bind:value={revokeNotes}
        placeholder="Why are you revoking?"
        class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 resize-none"></textarea>
      <div class="mt-5 flex items-center justify-end gap-3">
        <button onclick={() => (confirmRevoke = null)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
        <button onclick={doRevoke} disabled={revoking !== null}
          class="rounded-lg bg-red-600 px-5 py-2 text-sm font-semibold text-white hover:bg-red-700 transition-colors disabled:opacity-60">
          {revoking !== null ? "Revoking..." : "Revoke"}
        </button>
      </div>
    </div>
  </div>
{/if}

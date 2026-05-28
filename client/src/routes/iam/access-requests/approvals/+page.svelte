<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";

  type AccessRequestKind = "role_grant" | "role_elevation" | "resource_access";
  type AccessRequestStatus = "pending" | "approved" | "rejected" | "expired" | "cancelled" | "revoked";
  type AccessRequestItem = {
    id: number;
    kind: AccessRequestKind;
    kind_display: string;
    status: AccessRequestStatus;
    status_display: string;
    requester_id: number;
    requester_name: string;
    requester_email: string;
    requested_role_name: string;
    requested_resource: string;
    reason: string;
    requested_valid_until: string | null;
    granted_valid_until: string | null;
    request_expires_at: string | null;
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
  let actionInFlight = $state<number | null>(null);

  // Decision modal
  let decisionModal = $state<{ ar: AccessRequestItem; mode: "approve" | "reject" } | null>(null);
  let decisionNotes = $state("");
  let decisionExpires = $state("");

  function formatDate(d: string | null): string {
    if (!d) return "—";
    return new Date(d).toLocaleString("en-US", {
      month: "short", day: "numeric", year: "numeric",
      hour: "numeric", minute: "2-digit",
    });
  }

  async function fetchItems() {
    loading = true;
    try {
      const res = await api.get<AccessRequestListResponse>("/iam/access-requests/", {
        scope: "to_approve",
        page_size: "100",
      });
      items = res.results;
      totalCount = res.count;
    } catch {
      items = [];
      totalCount = 0;
    } finally {
      loading = false;
    }
  }

  function openDecision(ar: AccessRequestItem, mode: "approve" | "reject") {
    decisionModal = { ar, mode };
    decisionNotes = "";
    decisionExpires = ar.requested_valid_until ? ar.requested_valid_until.slice(0, 16) : "";
  }

  async function submitDecision() {
    if (!decisionModal) return;
    const { ar, mode } = decisionModal;
    actionInFlight = ar.id;
    try {
      const payload: Record<string, unknown> = { notes: decisionNotes };
      if (mode === "approve" && decisionExpires) {
        payload.granted_valid_until = new Date(decisionExpires).toISOString();
      }
      await api.post(`/iam/access-requests/${ar.id}/${mode}/`, payload);
      toast.success(mode === "approve" ? "Approved" : "Rejected", `Request #${ar.id} actioned.`);
      decisionModal = null;
      await fetchItems();
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error("Action failed", "Server rejected the decision. Check the notes / expiry and retry.");
      }
    } finally {
      actionInFlight = null;
    }
  }

  $effect(() => { fetchItems(); });
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Approval Queue</h1>
    <p class="mt-1 text-sm text-neutral-500">
      Pending access requests where you're the designated approver. Approve or reject each one with notes.
    </p>
  </div>

  <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
    {#if loading}
      <div class="p-16 text-center">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
      </div>
    {:else if items.length === 0}
      <div class="p-16 text-center">
        <h3 class="text-sm font-semibold text-neutral-800">Inbox zero</h3>
        <p class="mt-1.5 text-sm text-neutral-500">No requests are currently waiting on your decision.</p>
      </div>
    {:else}
      <ul class="divide-y divide-neutral-100">
        {#each items as it}
          <li class="p-5 hover:bg-neutral-50 transition-colors">
            <div class="flex items-start gap-4">
              <div class="w-10 h-10 rounded-full bg-neutral-100 flex items-center justify-center text-xs font-semibold text-neutral-600 shrink-0">
                {it.requester_name.split(" ").map((s) => s[0]).slice(0, 2).join("").toUpperCase()}
              </div>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <p class="font-semibold text-neutral-900">{it.requester_name}</p>
                  <span class="text-xs text-neutral-500">{it.requester_email}</span>
                  <span class="inline-flex items-center rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] font-medium text-neutral-600">
                    {it.kind_display}
                  </span>
                </div>
                <p class="mt-1 text-sm text-neutral-700">
                  {#if it.requested_role_name}
                    Requesting role <strong>{it.requested_role_name}</strong>
                  {:else if it.requested_resource}
                    Requesting access to <strong>{it.requested_resource}</strong>
                  {/if}
                  {#if it.requested_valid_until}
                    <span class="text-xs text-neutral-500 ml-2">
                      until {formatDate(it.requested_valid_until)}
                    </span>
                  {/if}
                </p>
                <p class="mt-2 text-sm text-neutral-600 italic">"{it.reason}"</p>
                <p class="mt-2 text-xs text-neutral-400">
                  Submitted {formatDate(it.created_at)}
                </p>
              </div>
              <div class="flex items-center gap-2 shrink-0">
                <button onclick={() => openDecision(it, "approve")} disabled={actionInFlight === it.id}
                  class="rounded-lg bg-green-600 px-4 py-2 text-sm font-semibold text-white hover:bg-green-700 transition-colors disabled:opacity-50">
                  Approve
                </button>
                <button onclick={() => openDecision(it, "reject")} disabled={actionInFlight === it.id}
                  class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors disabled:opacity-50">
                  Reject
                </button>
              </div>
            </div>
          </li>
        {/each}
      </ul>
    {/if}
  </div>
</div>

{#if decisionModal}
  {@const m = decisionModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (decisionModal = null)} aria-label="Close"></button>
    <div class="relative w-full max-w-md rounded-2xl bg-white shadow-2xl border border-neutral-200 p-6">
      <h3 class="text-lg font-bold text-neutral-800">
        {m.mode === "approve" ? "Approve" : "Reject"} request from {m.ar.requester_name}
      </h3>
      <p class="mt-1 text-sm text-neutral-500">
        {#if m.ar.requested_role_name}Role: <strong>{m.ar.requested_role_name}</strong>{:else if m.ar.requested_resource}Resource: <strong>{m.ar.requested_resource}</strong>{/if}
      </p>

      <div class="mt-5 space-y-4">
        {#if m.mode === "approve" && (m.ar.kind === "role_grant" || m.ar.kind === "role_elevation")}
          <div>
            <label for="approval-expires" class="block text-sm font-medium text-neutral-700 mb-1.5">
              Access valid until
              {#if m.ar.kind === "role_elevation"}
                <span class="text-red-500">*</span>
              {:else}
                <span class="text-xs font-normal text-neutral-500 ml-1">(empty = permanent)</span>
              {/if}
            </label>
            <input id="approval-expires" type="datetime-local" bind:value={decisionExpires}
              class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          </div>
        {/if}

        <div>
          <label for="approval-notes" class="block text-sm font-medium text-neutral-700 mb-1.5">
            Notes <span class="text-xs font-normal text-neutral-500 ml-1">(optional)</span>
          </label>
          <textarea id="approval-notes" rows="3" bind:value={decisionNotes}
            placeholder={m.mode === "approve" ? "Any conditions on this approval?" : "Why are you rejecting?"}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 resize-none"></textarea>
        </div>
      </div>

      <div class="mt-6 flex items-center justify-end gap-3">
        <button onclick={() => (decisionModal = null)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">Cancel</button>
        <button onclick={submitDecision} disabled={actionInFlight === m.ar.id}
          class="rounded-lg px-5 py-2 text-sm font-semibold text-white transition-colors disabled:opacity-60
                 {m.mode === 'approve' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'}">
          {actionInFlight === m.ar.id ? "..." : (m.mode === "approve" ? "Approve" : "Reject")}
        </button>
      </div>
    </div>
  </div>
{/if}

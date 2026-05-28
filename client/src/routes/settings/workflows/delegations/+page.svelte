<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { UserDelegationListItem, PaginatedResponse } from "$lib/types";

  let loading = $state(true);
  let delegations = $state<UserDelegationListItem[]>([]);
  let activeTab = $state<"active" | "expired" | "revoked">("active");
  let showCreate = $state(false);
  let creating = $state(false);

  let form = $state({
    delegator: "",
    delegate: "",
    starts_at: "",
    ends_at: "",
    reason: "",
  });

  async function loadDelegations() {
    loading = true;
    try {
      const data = await api.get<PaginatedResponse<UserDelegationListItem>>("/workflows/delegations/", { status: activeTab });
      delegations = data.results;
    } catch {
      toast.error("Load failed", "Could not load delegations.");
    } finally {
      loading = false;
    }
  }

  async function revokeDelegation(id: number) {
    try {
      await api.post(`/workflows/delegations/${id}/revoke/`, {});
      toast.success("Revoked", "Delegation has been revoked.");
      loadDelegations();
    } catch {
      toast.error("Error", "Could not revoke delegation.");
    }
  }

  function setTab(tab: typeof activeTab) {
    activeTab = tab;
    loadDelegations();
  }

  function formatDate(d: string) {
    return new Date(d).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  }

  function formatDateTime(d: string) {
    return new Date(d).toLocaleString(undefined, { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  }

  $effect(() => { loadDelegations(); });

  const STATUS_STYLES: Record<string, string> = {
    active: "bg-emerald-50 text-emerald-700",
    expired: "bg-neutral-100 text-neutral-500",
    revoked: "bg-red-50 text-red-600",
  };
</script>

<div>
  <!-- Header -->
  <div class="flex items-center justify-between mb-8">
    <div>
      <h2 class="text-xl font-semibold text-neutral-800">Delegations</h2>
      <p class="text-sm text-neutral-500 mt-1">Manage temporary delegation of approval authority for out-of-office routing.</p>
    </div>
  </div>

  <!-- Tabs -->
  <div class="flex items-center gap-1 mb-6 bg-neutral-100 rounded-lg p-1 w-fit">
    {#each (["active", "expired", "revoked"] as const) as tab}
      <button
        onclick={() => setTab(tab)}
        class="px-4 py-1.5 text-sm font-medium rounded-md capitalize transition-colors
               {activeTab === tab ? 'bg-white text-neutral-800 shadow-sm' : 'text-neutral-500 hover:text-neutral-700'}"
      >
        {tab}
      </button>
    {/each}
  </div>

  <!-- List -->
  {#if loading}
    <div class="flex items-center justify-center py-20">
      <div class="w-5 h-5 border-2 border-neutral-300 border-t-neutral-800 rounded-full animate-spin"></div>
    </div>
  {:else if delegations.length === 0}
    <div class="text-center py-20 bg-white border border-neutral-200 rounded-xl">
      <p class="text-sm text-neutral-500">No {activeTab} delegations found.</p>
    </div>
  {:else}
    <div class="space-y-3">
      {#each delegations as d}
        <div class="bg-white border border-neutral-200 rounded-xl p-5 flex items-center justify-between">
          <div class="flex items-center gap-6">
            <!-- Delegation arrow -->
            <div class="flex items-center gap-3">
              <div class="text-center">
                <p class="text-sm font-semibold text-neutral-800">{d.delegator_name}</p>
                <p class="text-[10px] text-neutral-400 uppercase tracking-wider">Delegator</p>
              </div>
              <svg class="w-5 h-5 text-neutral-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
              </svg>
              <div class="text-center">
                <p class="text-sm font-semibold text-neutral-800">{d.delegate_name}</p>
                <p class="text-[10px] text-neutral-400 uppercase tracking-wider">Delegate</p>
              </div>
            </div>

            <!-- Details -->
            <div class="border-l border-neutral-100 pl-6 flex items-center gap-4 text-xs text-neutral-500">
              <span>{formatDate(d.starts_at)} — {formatDate(d.ends_at)}</span>
              {#if d.role_scope_name}
                <span class="px-2 py-0.5 bg-neutral-50 rounded font-medium">{d.role_scope_name}</span>
              {/if}
              {#if d.reason}
                <span class="italic text-neutral-400">"{d.reason}"</span>
              {/if}
            </div>
          </div>

          <div class="flex items-center gap-3">
            <span class="text-[10px] font-semibold uppercase tracking-wider px-2.5 py-1 rounded-full {STATUS_STYLES[d.status]}">
              {d.status}
            </span>
            {#if d.status === "active"}
              <button
                onclick={() => revokeDelegation(d.id)}
                class="text-xs font-medium text-neutral-400 hover:text-red-600 transition-colors"
              >
                Revoke
              </button>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

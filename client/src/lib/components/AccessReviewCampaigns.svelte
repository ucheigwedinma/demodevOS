<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { RoleListItem, PaginatedResponse } from "$lib/types";

  type CampaignKind = "access_review" | "role_certification" | "dormant_review";
  type CampaignStatus = "draft" | "in_progress" | "completed" | "cancelled";

  type Campaign = {
    id: number;
    name: string;
    description: string;
    kind: CampaignKind;
    kind_display: string;
    status: CampaignStatus;
    status_display: string;
    target_role_id: number | null;
    target_role_name: string;
    starts_at: string | null;
    ends_at: string | null;
    completed_at: string | null;
    created_by_name: string;
    created_at: string;
    item_count: number;
    pending_count: number;
    approved_count: number;
    revoked_count: number;
  };

  type Item = {
    id: number;
    user_id: number;
    user_name: string;
    user_email: string;
    role_id: number | null;
    role_name: string;
    decision: "pending" | "approved" | "revoked" | "deferred";
    decision_display: string;
    decided_by_name: string;
    decided_at: string | null;
    notes: string;
    last_login: string | null;
    created_at: string;
  };

  type Props = {
    kind: CampaignKind;
    title: string;
    createLabel: string;
    sampleNames: string[];
  };

  let { kind, title, createLabel, sampleNames }: Props = $props();

  let campaigns = $state<Campaign[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);

  let showCreate = $state(false);
  let saving = $state(false);
  let roles = $state<RoleListItem[]>([]);
  let rolesLoading = $state(false);

  let form = $state({
    name: "",
    description: "",
    target_role_id: null as number | null,
    starts_at: "",
    ends_at: "",
  });

  // Detail drawer
  let openCampaign = $state<Campaign | null>(null);
  let items = $state<Item[]>([]);
  let itemsLoading = $state(false);
  let actionInFlight = $state<number | null>(null);

  // Dev fill
  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);
  let devIdx = 0;
  function devFill() {
    form.name = sampleNames[devIdx % sampleNames.length];
    devIdx++;
    form.description = "Quarterly review of " + form.name.toLowerCase() + ".";
    if (!form.target_role_id && roles.length) {
      form.target_role_id = roles[0].id;
    }
    const starts = new Date();
    const ends = new Date();
    ends.setDate(starts.getDate() + 14);
    form.starts_at = starts.toISOString().slice(0, 16);
    form.ends_at = ends.toISOString().slice(0, 16);
  }

  function formatDate(d: string | null): string {
    if (!d) return "—";
    return new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  function statusClasses(s: string): string {
    return ({
      draft: "bg-neutral-100 text-neutral-600",
      in_progress: "bg-blue-50 text-blue-700",
      completed: "bg-green-50 text-green-700",
      cancelled: "bg-neutral-100 text-neutral-500",
    } as Record<string, string>)[s] ?? "bg-neutral-100 text-neutral-600";
  }

  function decisionClasses(d: string): string {
    return ({
      pending: "bg-blue-50 text-blue-700",
      approved: "bg-green-50 text-green-700",
      revoked: "bg-red-50 text-red-700",
      deferred: "bg-yellow-50 text-yellow-700",
    } as Record<string, string>)[d] ?? "bg-neutral-100 text-neutral-600";
  }

  async function fetchCampaigns() {
    loading = true;
    try {
      const res = await api.get<{ count: number; results: Campaign[] }>(
        "/iam/compliance/access-reviews/",
        { kind, page_size: "50" },
      );
      campaigns = res.results;
      totalCount = res.count;
    } catch {
      campaigns = [];
      totalCount = 0;
    } finally {
      loading = false;
    }
  }

  async function loadRoles() {
    if (roles.length || rolesLoading) return;
    rolesLoading = true;
    try {
      const res = await api.get<PaginatedResponse<RoleListItem>>("/settings/roles/", {
        page_size: "200", ordering: "name",
      });
      roles = res.results;
    } catch {
      // non-fatal
    } finally {
      rolesLoading = false;
    }
  }

  async function openCreateModal() {
    showCreate = true;
    form = {
      name: "",
      description: "",
      target_role_id: null,
      starts_at: "",
      ends_at: "",
    };
    await loadRoles();
  }

  async function handleCreate() {
    if (!form.name.trim()) {
      toast.error("Validation", "Campaign name is required.");
      return;
    }
    saving = true;
    try {
      const payload: Record<string, unknown> = {
        kind,
        name: form.name.trim(),
        description: form.description.trim(),
      };
      if (form.target_role_id) payload.target_role_id = form.target_role_id;
      if (form.starts_at) payload.starts_at = new Date(form.starts_at).toISOString();
      if (form.ends_at) payload.ends_at = new Date(form.ends_at).toISOString();

      await api.post("/iam/compliance/access-reviews/", payload);
      toast.success("Created", "Campaign drafted.");
      showCreate = false;
      await fetchCampaigns();
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error("Create failed", "Please review the form.");
      }
    } finally {
      saving = false;
    }
  }

  async function changeStatus(c: Campaign, action: "start" | "complete" | "cancel") {
    actionInFlight = c.id;
    try {
      await api.post(`/iam/compliance/access-reviews/${c.id}/${action}/`, {});
      toast.success("Updated", `Campaign ${action}ed.`);
      await fetchCampaigns();
      if (openCampaign && openCampaign.id === c.id) {
        await openDetail(c);
      }
    } catch {
      toast.error("Action failed", `Could not ${action} the campaign.`);
    } finally {
      actionInFlight = null;
    }
  }

  async function openDetail(c: Campaign) {
    openCampaign = c;
    itemsLoading = true;
    items = [];
    try {
      const res = await api.get<{ count: number; results: Item[]; campaign: Campaign }>(
        `/iam/compliance/access-reviews/${c.id}/items/`,
      );
      items = res.results;
      openCampaign = res.campaign;
    } catch {
      toast.error("Load failed", "Could not load campaign items.");
    } finally {
      itemsLoading = false;
    }
  }

  async function decide(itemId: number, decision: "approved" | "revoked" | "deferred") {
    if (!openCampaign) return;
    try {
      await api.post(`/iam/compliance/access-reviews/${openCampaign.id}/items/${itemId}/decide/`, {
        decision,
      });
      toast.success("Recorded", `Marked as ${decision}.`);
      await openDetail(openCampaign);
    } catch {
      toast.error("Action failed", "Could not record the decision.");
    }
  }

  $effect(() => { fetchCampaigns(); });
</script>

<div class="space-y-6">
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900">{title}</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Schedule a campaign, populate it from a role's current assignees, then walk through each
        user with Approve / Revoke decisions. Revoked decisions also clear the user's role and
        emit an audit event.
      </p>
    </div>
    <button onclick={openCreateModal}
      class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-900 transition-colors">
      {createLabel}
    </button>
  </div>

  <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
    {#if loading}
      <div class="p-16 text-center">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
      </div>
    {:else if campaigns.length === 0}
      <div class="p-16 text-center">
        <h3 class="text-sm font-semibold text-neutral-800">No campaigns yet</h3>
        <p class="mt-1.5 text-sm text-neutral-500">Click {createLabel} to draft your first one.</p>
      </div>
    {:else}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50">
            <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Name</th>
            <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Target role</th>
            <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Window</th>
            <th class="px-5 py-3 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
            <th class="px-5 py-3 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Progress</th>
            <th class="px-5 py-3 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each campaigns as c}
            <tr class="hover:bg-neutral-50 transition-colors">
              <td class="px-5 py-4">
                <button onclick={() => openDetail(c)} class="font-medium text-neutral-800 hover:text-neutral-900 underline-offset-2 hover:underline text-left">
                  {c.name}
                </button>
                {#if c.description}
                  <p class="text-xs text-neutral-500 max-w-md truncate">{c.description}</p>
                {/if}
              </td>
              <td class="px-5 py-4 text-neutral-700">{c.target_role_name || "—"}</td>
              <td class="px-5 py-4 text-neutral-600 text-xs whitespace-nowrap">
                {formatDate(c.starts_at)} → {formatDate(c.ends_at)}
              </td>
              <td class="px-5 py-4 text-center">
                <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium {statusClasses(c.status)}">
                  {c.status_display}
                </span>
              </td>
              <td class="px-5 py-4 text-center">
                {#if c.item_count === 0}
                  <span class="text-xs text-neutral-500">—</span>
                {:else}
                  <span class="text-xs text-neutral-600">
                    {c.item_count - c.pending_count} / {c.item_count}
                  </span>
                  <div class="mt-1 mx-auto h-1 w-20 rounded-full bg-neutral-100 overflow-hidden">
                    <div class="h-full bg-neutral-700" style="width: {((c.item_count - c.pending_count) / c.item_count) * 100}%"></div>
                  </div>
                {/if}
              </td>
              <td class="px-5 py-4 text-right">
                <div class="flex items-center justify-end gap-1">
                  {#if c.status === "draft"}
                    <button onclick={() => changeStatus(c, "start")} disabled={actionInFlight === c.id}
                      class="rounded-lg px-3 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 transition-colors disabled:opacity-50">
                      Start
                    </button>
                  {:else if c.status === "in_progress"}
                    <button onclick={() => changeStatus(c, "complete")} disabled={actionInFlight === c.id}
                      class="rounded-lg px-3 py-1.5 text-xs font-medium text-green-700 bg-green-50 hover:bg-green-100 transition-colors disabled:opacity-50">
                      Complete
                    </button>
                    <button onclick={() => changeStatus(c, "cancel")} disabled={actionInFlight === c.id}
                      class="rounded-lg px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 transition-colors disabled:opacity-50">
                      Cancel
                    </button>
                  {/if}
                </div>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>
</div>

<!-- Create modal -->
{#if showCreate}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (showCreate = false)} aria-label="Close"></button>
    <div class="relative w-full max-w-lg rounded-2xl bg-white shadow-2xl border border-neutral-200">
      <div class="p-6 border-b border-neutral-100">
        <h2 class="text-lg font-bold text-neutral-800">{createLabel}</h2>
        <p class="text-xs text-neutral-500 mt-1">Drafts can be edited freely; once started, items get auto-populated from the target role.</p>
      </div>
      <div class="p-6 space-y-4">
        <div>
          <label for="ar-name" class="block text-sm font-medium text-neutral-700 mb-1.5">Name <span class="text-red-500">*</span></label>
          <input id="ar-name" type="text" bind:value={form.name} placeholder="e.g. Q1 2026 Finance Role Review"
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
        </div>
        <div>
          <label for="ar-desc" class="block text-sm font-medium text-neutral-700 mb-1.5">Description</label>
          <textarea id="ar-desc" rows="2" bind:value={form.description}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 resize-none"></textarea>
        </div>
        <div>
          <label for="ar-role" class="block text-sm font-medium text-neutral-700 mb-1.5">
            Target role
            <span class="text-xs font-normal text-neutral-500 ml-1">(auto-populates items)</span>
          </label>
          <select id="ar-role" bind:value={form.target_role_id}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800">
            <option value={null}>— No auto-populate —</option>
            {#each roles as r}<option value={r.id}>{r.name}{r.is_system ? " · System" : ""}</option>{/each}
          </select>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <label class="text-sm font-medium text-neutral-700 block">
            <span class="block mb-1.5">Window starts</span>
            <input type="datetime-local" bind:value={form.starts_at}
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          </label>
          <label class="text-sm font-medium text-neutral-700 block">
            <span class="block mb-1.5">Window ends</span>
            <input type="datetime-local" bind:value={form.ends_at}
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          </label>
        </div>
      </div>
      <div class="p-6 border-t border-neutral-100 flex items-center gap-3">
        {#if isDev}
          <button onclick={devFill} class="rounded-lg bg-orange-500 px-3 py-2.5 text-sm font-medium text-white hover:bg-orange-600 transition-colors mr-auto">
            Dev Fill
          </button>
        {/if}
        <button onclick={() => (showCreate = false)} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors ml-auto">
          Cancel
        </button>
        <button onclick={handleCreate} disabled={saving}
          class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-900 transition-colors disabled:opacity-60">
          {saving ? "Saving..." : "Create draft"}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- Detail drawer -->
{#if openCampaign}
  <div class="fixed inset-0 z-40 flex">
    <button class="flex-1 bg-black/40 backdrop-blur-sm" onclick={() => (openCampaign = null)} aria-label="Close"></button>
    <div class="w-full max-w-2xl bg-white shadow-2xl border-l border-neutral-200 overflow-y-auto">
      <div class="p-6 border-b border-neutral-100 flex items-start justify-between">
        <div>
          <h2 class="text-lg font-bold text-neutral-900">{openCampaign.name}</h2>
          <p class="mt-1 text-xs text-neutral-500">
            {openCampaign.kind_display} · {openCampaign.status_display} ·
            {openCampaign.item_count} items · {openCampaign.pending_count} pending
          </p>
        </div>
        <button onclick={() => (openCampaign = null)} class="text-neutral-400 hover:text-neutral-600 text-xl leading-none">×</button>
      </div>
      <div class="p-6">
        {#if itemsLoading}
          <div class="p-12 text-center">
            <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
          </div>
        {:else if items.length === 0}
          <p class="text-sm text-neutral-500 text-center">No items in this campaign yet.</p>
        {:else}
          <ul class="space-y-2">
            {#each items as it}
              <li class="rounded-lg border border-neutral-200 p-3">
                <div class="flex items-start justify-between gap-3">
                  <div class="min-w-0 flex-1">
                    <p class="font-medium text-sm text-neutral-800">{it.user_name}</p>
                    <p class="text-xs text-neutral-500 truncate">{it.user_email}</p>
                    {#if it.role_name}
                      <p class="mt-1 text-xs text-neutral-600">Role: <span class="font-medium">{it.role_name}</span></p>
                    {/if}
                    {#if it.last_login}
                      <p class="text-[11px] text-neutral-400">Last login {formatDate(it.last_login)}</p>
                    {:else}
                      <p class="text-[11px] text-yellow-700">Never logged in</p>
                    {/if}
                  </div>
                  <div class="text-right shrink-0">
                    <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium {decisionClasses(it.decision)}">
                      {it.decision_display}
                    </span>
                    {#if it.decided_by_name}
                      <p class="mt-1 text-[10px] text-neutral-400">by {it.decided_by_name}</p>
                    {/if}
                  </div>
                </div>
                {#if openCampaign.status === "in_progress" && it.decision === "pending"}
                  <div class="mt-3 flex items-center gap-2">
                    <button onclick={() => decide(it.id, "approved")} class="rounded-lg bg-green-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-green-700">
                      Approve
                    </button>
                    <button onclick={() => decide(it.id, "revoked")} class="rounded-lg bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-700">
                      Revoke
                    </button>
                    <button onclick={() => decide(it.id, "deferred")} class="rounded-lg border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-50">
                      Defer
                    </button>
                  </div>
                {/if}
              </li>
            {/each}
          </ul>
        {/if}
      </div>
    </div>
  </div>
{/if}

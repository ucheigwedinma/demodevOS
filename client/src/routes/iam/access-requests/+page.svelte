<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { RoleListItem, PaginatedResponse } from "$lib/types";

  type AccessRequestKind = "role_grant" | "role_elevation" | "resource_access";
  type AccessRequestStatus =
    | "pending" | "approved" | "rejected"
    | "expired" | "cancelled" | "revoked";
  type AccessRequestItem = {
    id: number;
    kind: AccessRequestKind;
    kind_display: string;
    status: AccessRequestStatus;
    status_display: string;
    requester_id: number;
    requester_name: string;
    requester_email: string;
    approver_id: number | null;
    approver_name: string;
    requested_role_id: number | null;
    requested_role_name: string;
    requested_resource: string;
    reason: string;
    requested_valid_until: string | null;
    granted_valid_until: string | null;
    request_expires_at: string | null;
    approval_decision_at: string | null;
    approval_notes: string;
    created_at: string;
  };
  type AccessRequestOverview = {
    pending: number;
    approved: number;
    rejected: number;
    to_approve: number;
  };
  type AccessRequestListResponse = {
    count: number;
    results: AccessRequestItem[];
    overview: AccessRequestOverview;
  };

  let items = $state<AccessRequestItem[]>([]);
  let overview = $state<AccessRequestOverview>({ pending: 0, approved: 0, rejected: 0, to_approve: 0 });
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  let statusFilter = $state("");
  let actionInFlight = $state<number | null>(null);

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));

  // Create modal
  let showCreate = $state(false);
  let saving = $state(false);
  let roles = $state<RoleListItem[]>([]);
  let rolesLoading = $state(false);

  let form = $state({
    kind: "role_grant" as AccessRequestKind,
    requested_role_id: null as number | null,
    requested_resource: "",
    reason: "",
    requested_valid_until: "",
    request_expires_at: "",
  });

  // Dev fill
  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);
  const REQUEST_SAMPLES = [
    { kind: "role_grant" as AccessRequestKind, reason: "Joining the procurement working group on Project Athena. Need read/write on procurement and reporting." },
    { kind: "role_elevation" as AccessRequestKind, reason: "Covering finance lead while she's on leave next week. Requesting Finance Controller for the duration." },
    { kind: "resource_access" as AccessRequestKind, reason: "Need access to the Pinewood Apartments tenant register to draft the renewal communications." },
  ];
  let requestDevIdx = 0;
  function devFill() {
    const s = REQUEST_SAMPLES[requestDevIdx % REQUEST_SAMPLES.length];
    requestDevIdx++;
    form.kind = s.kind;
    form.reason = s.reason;
    if (s.kind === "resource_access") {
      form.requested_resource = "Pinewood Apartments tenant register";
      form.requested_role_id = null;
    } else {
      form.requested_resource = "";
      form.requested_role_id = roles[0]?.id ?? null;
    }
    if (s.kind === "role_elevation") {
      const t = new Date();
      t.setHours(t.getHours() + 8);
      form.requested_valid_until = t.toISOString().slice(0, 16);
    }
  }

  function formatDate(dateStr: string | null): string {
    if (!dateStr) return "—";
    return new Date(dateStr).toLocaleString("en-US", {
      month: "short", day: "numeric", year: "numeric",
      hour: "numeric", minute: "2-digit",
    });
  }

  async function fetchItems() {
    loading = true;
    try {
      const params: Record<string, string> = {
        scope: "mine",
        page: String(currentPage),
        page_size: String(pageSize),
      };
      if (statusFilter) params.status = statusFilter;
      const res = await api.get<AccessRequestListResponse>("/iam/access-requests/", params);
      items = res.results;
      totalCount = res.count;
      overview = res.overview;
    } catch {
      items = [];
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
      // Non-fatal
    } finally {
      rolesLoading = false;
    }
  }

  async function openCreate() {
    showCreate = true;
    form = {
      kind: "role_grant",
      requested_role_id: null,
      requested_resource: "",
      reason: "",
      requested_valid_until: "",
      request_expires_at: "",
    };
    await loadRoles();
  }

  async function handleCreate() {
    if (!form.reason.trim() || form.reason.trim().length < 4) {
      toast.error("Validation", "Please describe why you need this access.");
      return;
    }
    if (form.kind !== "resource_access" && !form.requested_role_id) {
      toast.error("Validation", "Pick the role you're requesting.");
      return;
    }
    if (form.kind === "resource_access" && !form.requested_resource.trim()) {
      toast.error("Validation", "Describe the resource you need.");
      return;
    }
    if (form.kind === "role_elevation" && !form.requested_valid_until) {
      toast.error("Validation", "Elevation must specify when access expires.");
      return;
    }
    saving = true;
    try {
      const payload: Record<string, unknown> = {
        kind: form.kind,
        reason: form.reason.trim(),
      };
      if (form.requested_role_id) payload.requested_role_id = form.requested_role_id;
      if (form.requested_resource.trim()) payload.requested_resource = form.requested_resource.trim();
      if (form.requested_valid_until) payload.requested_valid_until = new Date(form.requested_valid_until).toISOString();
      if (form.request_expires_at) payload.request_expires_at = new Date(form.request_expires_at).toISOString();

      await api.post("/iam/access-requests/", payload);
      toast.success("Submitted", "Your access request has been logged.");
      showCreate = false;
      await fetchItems();
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error("Submit failed", "Please review the form and try again.");
      }
    } finally {
      saving = false;
    }
  }

  async function cancelRequest(id: number) {
    actionInFlight = id;
    try {
      await api.post(`/iam/access-requests/${id}/cancel/`, {});
      toast.success("Cancelled", "Request withdrawn.");
      await fetchItems();
    } catch {
      toast.error("Action failed", "Could not cancel request.");
    } finally {
      actionInFlight = null;
    }
  }

  $effect(() => { void statusFilter; void currentPage; fetchItems(); });

  const STATUS_TABS = [
    { value: "", label: "All" },
    { value: "pending", label: "Pending" },
    { value: "approved", label: "Approved" },
    { value: "rejected", label: "Rejected" },
    { value: "cancelled", label: "Cancelled" },
  ];

  function statusBadgeClasses(s: AccessRequestStatus): string {
    return {
      pending:   "bg-blue-50 text-blue-700",
      approved:  "bg-green-50 text-green-700",
      rejected:  "bg-red-50 text-red-700",
      expired:   "bg-neutral-100 text-neutral-600",
      cancelled: "bg-neutral-100 text-neutral-600",
      revoked:   "bg-yellow-50 text-yellow-700",
    }[s];
  }
</script>

<div class="space-y-6">
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900">Request Access</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Self-service access requests. Submit a new request below or track the status of existing ones.
      </p>
    </div>
    <button onclick={openCreate}
      class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-900 transition-colors">
      New Request
    </button>
  </div>

  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
    <div class="rounded-xl border border-neutral-200 bg-white p-5">
      <p class="text-xs font-medium text-blue-600 uppercase tracking-wider">Pending</p>
      <p class="mt-2 text-3xl font-bold text-neutral-900">{overview.pending}</p>
    </div>
    <div class="rounded-xl border border-neutral-200 bg-white p-5">
      <p class="text-xs font-medium text-green-600 uppercase tracking-wider">Approved</p>
      <p class="mt-2 text-3xl font-bold text-neutral-900">{overview.approved}</p>
    </div>
    <div class="rounded-xl border border-neutral-200 bg-white p-5">
      <p class="text-xs font-medium text-red-600 uppercase tracking-wider">Rejected</p>
      <p class="mt-2 text-3xl font-bold text-neutral-900">{overview.rejected}</p>
    </div>
    <a href="/iam/access-requests/approvals"
      class="rounded-xl border border-neutral-200 bg-white p-5 hover:border-neutral-400 hover:shadow-sm transition-all">
      <p class="text-xs font-medium text-neutral-500 uppercase tracking-wider">Awaiting your approval</p>
      <p class="mt-2 text-3xl font-bold text-neutral-900">{overview.to_approve}</p>
      <p class="mt-1 text-xs text-neutral-400">Click to review →</p>
    </a>
  </div>

  <div class="flex gap-2 flex-wrap">
    {#each STATUS_TABS as tab}
      <button onclick={() => { statusFilter = tab.value; currentPage = 1; }}
        class="rounded-lg px-4 py-2 text-sm font-medium transition-colors
               {statusFilter === tab.value ? 'bg-neutral-800 text-white' : 'bg-white border border-neutral-200 text-neutral-600 hover:bg-neutral-50'}">
        {tab.label}
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
        <h3 class="text-sm font-semibold text-neutral-800">No requests yet</h3>
        <p class="mt-1.5 text-sm text-neutral-500">Submit your first access request using the button above.</p>
      </div>
    {:else}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200">
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Submitted</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Kind</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Target</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Reason</th>
            <th class="px-5 py-3.5 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
            <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each items as it}
            <tr class="hover:bg-neutral-50 transition-colors">
              <td class="px-5 py-4 text-neutral-600 whitespace-nowrap">{formatDate(it.created_at)}</td>
              <td class="px-5 py-4 text-neutral-700">{it.kind_display}</td>
              <td class="px-5 py-4 text-neutral-700">
                {#if it.requested_role_name}{it.requested_role_name}{:else if it.requested_resource}{it.requested_resource}{:else}—{/if}
              </td>
              <td class="px-5 py-4 text-neutral-600 max-w-md truncate">{it.reason}</td>
              <td class="px-5 py-4 text-center">
                <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium {statusBadgeClasses(it.status)}">
                  {it.status_display}
                </span>
              </td>
              <td class="px-5 py-4 text-right">
                {#if it.status === "pending"}
                  <button onclick={() => cancelRequest(it.id)} disabled={actionInFlight === it.id}
                    class="rounded-lg px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 transition-colors disabled:opacity-50">
                    {actionInFlight === it.id ? "..." : "Cancel"}
                  </button>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>

  {#if totalCount > pageSize}
    <div class="flex items-center justify-between">
      <p class="text-sm text-neutral-400">Page {currentPage} of {totalPages} · {totalCount} total</p>
      <div class="flex items-center gap-1">
        <button onclick={() => currentPage--} disabled={currentPage <= 1} class="w-9 h-9 flex items-center justify-center border border-neutral-200 rounded-lg text-neutral-500 hover:bg-neutral-50 disabled:opacity-30 transition-colors" aria-label="Previous page">‹</button>
        <button onclick={() => currentPage++} disabled={currentPage >= totalPages} class="w-9 h-9 flex items-center justify-center border border-neutral-200 rounded-lg text-neutral-500 hover:bg-neutral-50 disabled:opacity-30 transition-colors" aria-label="Next page">›</button>
      </div>
    </div>
  {/if}
</div>

<!-- Create modal -->
{#if showCreate}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (showCreate = false)} aria-label="Close"></button>
    <div class="relative w-full max-w-xl rounded-2xl bg-white shadow-2xl border border-neutral-200 max-h-[90vh] flex flex-col">
      <div class="p-6 border-b border-neutral-100 shrink-0">
        <h2 class="text-lg font-bold text-neutral-800">New Access Request</h2>
        <p class="text-xs text-neutral-500 mt-1">An approver will review your request and decide.</p>
      </div>

      <div class="p-6 overflow-y-auto flex-1 min-h-0 space-y-4">
        <div>
          <label class="block text-sm font-medium text-neutral-700 mb-1.5">Kind</label>
          <div class="grid grid-cols-3 gap-2">
            {#each [
              { v: "role_grant", label: "Role grant", desc: "Add a role to my account" },
              { v: "role_elevation", label: "Elevation", desc: "Temporary stronger role" },
              { v: "resource_access", label: "Resource", desc: "Specific data or area" },
            ] as opt}
              <button type="button" onclick={() => (form.kind = opt.v as AccessRequestKind)}
                class="text-left rounded-lg border px-3 py-2.5 transition-colors
                       {form.kind === opt.v ? 'border-neutral-800 bg-neutral-50' : 'border-neutral-200 hover:border-neutral-400'}">
                <p class="text-sm font-medium text-neutral-800">{opt.label}</p>
                <p class="text-xs text-neutral-500 mt-0.5">{opt.desc}</p>
              </button>
            {/each}
          </div>
        </div>

        {#if form.kind !== "resource_access"}
          <div>
            <label for="ar-role" class="block text-sm font-medium text-neutral-700 mb-1.5">Role</label>
            <select id="ar-role" bind:value={form.requested_role_id}
              class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800">
              <option value={null}>— Pick a role —</option>
              {#if rolesLoading}<option disabled>Loading…</option>{/if}
              {#each roles as r}<option value={r.id}>{r.name}{r.is_system ? " · System" : ""}</option>{/each}
            </select>
          </div>
        {:else}
          <div>
            <label for="ar-resource" class="block text-sm font-medium text-neutral-700 mb-1.5">Resource</label>
            <input id="ar-resource" type="text" bind:value={form.requested_resource}
              placeholder="e.g. Pinewood Apartments tenant register"
              class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          </div>
        {/if}

        <div>
          <label for="ar-reason" class="block text-sm font-medium text-neutral-700 mb-1.5">Reason <span class="text-red-500">*</span></label>
          <textarea id="ar-reason" rows="3" bind:value={form.reason}
            placeholder="Why do you need this access?"
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 resize-none"></textarea>
        </div>

        {#if form.kind === "role_elevation" || form.kind === "role_grant"}
          <div>
            <label for="ar-valid-until" class="block text-sm font-medium text-neutral-700 mb-1.5">
              Access valid until
              <span class="text-xs font-normal text-neutral-500 ml-1">
                {form.kind === "role_elevation" ? "(required for elevation)" : "(leave empty for permanent grant)"}
              </span>
            </label>
            <input id="ar-valid-until" type="datetime-local" bind:value={form.requested_valid_until}
              class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          </div>
        {/if}
      </div>

      <div class="p-6 border-t border-neutral-100 flex items-center gap-3 shrink-0">
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
          {saving ? "Submitting..." : "Submit request"}
        </button>
      </div>
    </div>
  </div>
{/if}

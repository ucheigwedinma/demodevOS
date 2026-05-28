<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { RoleListItem, PaginatedResponse } from "$lib/types";

  type AccessRequestItem = {
    id: number;
    kind: "role_grant" | "role_elevation" | "resource_access";
    status: "pending" | "approved" | "rejected" | "expired" | "cancelled" | "revoked";
    status_display: string;
    requested_role_name: string;
    requested_valid_until: string | null;
    granted_valid_until: string | null;
    reason: string;
    created_at: string;
  };
  type AccessRequestListResponse = {
    count: number;
    results: AccessRequestItem[];
    overview: { pending: number; approved: number; rejected: number; to_approve: number };
  };

  let roles = $state<RoleListItem[]>([]);
  let rolesLoading = $state(true);
  let history = $state<AccessRequestItem[]>([]);
  let historyLoading = $state(true);

  let saving = $state(false);

  let form = $state({
    requested_role_id: null as number | null,
    duration_minutes: 60,
    reason: "",
  });

  const DURATION_OPTIONS = [
    { v: 15, label: "15 minutes" },
    { v: 60, label: "1 hour" },
    { v: 240, label: "4 hours" },
    { v: 480, label: "8 hours (workday)" },
    { v: 1440, label: "24 hours" },
  ];

  // Dev fill
  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);
  const ELEVATION_SAMPLES = [
    "Need to approve a stuck payment run that's blocking the contractor disbursement.",
    "Investigating a customer-reported data anomaly; need temporary admin to query the audit logs.",
    "Covering on-call shift while the platform admin is out — need elevation for emergency response.",
  ];
  let elevationDevIdx = 0;
  function devFill() {
    form.reason = ELEVATION_SAMPLES[elevationDevIdx % ELEVATION_SAMPLES.length];
    elevationDevIdx++;
    if (!form.requested_role_id && roles.length) {
      form.requested_role_id = roles[0].id;
    }
  }

  function formatDate(d: string | null): string {
    if (!d) return "—";
    return new Date(d).toLocaleString("en-US", {
      month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
    });
  }

  async function loadRoles() {
    rolesLoading = true;
    try {
      const res = await api.get<PaginatedResponse<RoleListItem>>("/settings/roles/", {
        page_size: "200", ordering: "name",
      });
      roles = res.results;
    } catch {
      toast.error("Load failed", "Could not load roles.");
    } finally {
      rolesLoading = false;
    }
  }

  async function loadHistory() {
    historyLoading = true;
    try {
      const res = await api.get<AccessRequestListResponse>("/iam/access-requests/", {
        scope: "mine",
        kind: "role_elevation",
        page_size: "10",
      });
      history = res.results;
    } catch {
      history = [];
    } finally {
      historyLoading = false;
    }
  }

  async function handleSubmit() {
    if (!form.requested_role_id) {
      toast.error("Validation", "Pick the role you need elevated access to.");
      return;
    }
    if (!form.reason.trim() || form.reason.trim().length < 4) {
      toast.error("Validation", "Describe why you need this elevation.");
      return;
    }
    saving = true;
    try {
      const expires = new Date(Date.now() + form.duration_minutes * 60_000);
      await api.post("/iam/access-requests/", {
        kind: "role_elevation",
        requested_role_id: form.requested_role_id,
        reason: form.reason.trim(),
        requested_valid_until: expires.toISOString(),
      });
      toast.success("Submitted", "Elevation request sent for approval.");
      form.reason = "";
      await loadHistory();
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error("Submit failed", "Server rejected the request.");
      }
    } finally {
      saving = false;
    }
  }

  $effect(() => {
    loadRoles();
    loadHistory();
  });

  function statusBadge(s: string): string {
    return ({
      pending: "bg-blue-50 text-blue-700",
      approved: "bg-green-50 text-green-700",
      rejected: "bg-red-50 text-red-700",
      expired: "bg-neutral-100 text-neutral-600",
      cancelled: "bg-neutral-100 text-neutral-600",
      revoked: "bg-yellow-50 text-yellow-700",
    } as Record<string, string>)[s] ?? "bg-neutral-100 text-neutral-600";
  }
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Privilege Elevation</h1>
    <p class="mt-1 text-sm text-neutral-500">
      Just-in-time elevated access ("sudo"). Pick a stronger role plus a duration; an approver
      decides whether to grant it. Approved elevations auto-expire on their schedule.
    </p>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
    <!-- Form (col 1-2) -->
    <div class="lg:col-span-2 rounded-xl border border-neutral-200 bg-white p-6 space-y-5">
      <div>
        <label for="elev-role" class="block text-sm font-medium text-neutral-700 mb-1.5">Role to elevate to</label>
        <select id="elev-role" bind:value={form.requested_role_id}
          class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800">
          <option value={null}>— Pick a role —</option>
          {#if rolesLoading}<option disabled>Loading…</option>{/if}
          {#each roles as r}<option value={r.id}>{r.name}{r.is_system ? " · System" : ""}</option>{/each}
        </select>
      </div>

      <div>
        <label class="block text-sm font-medium text-neutral-700 mb-2">Duration</label>
        <div class="grid grid-cols-2 sm:grid-cols-5 gap-2">
          {#each DURATION_OPTIONS as opt}
            <button type="button" onclick={() => (form.duration_minutes = opt.v)}
              class="rounded-lg border px-3 py-2.5 text-sm transition-colors
                     {form.duration_minutes === opt.v ? 'border-neutral-800 bg-neutral-50 font-semibold text-neutral-900' : 'border-neutral-200 text-neutral-600 hover:border-neutral-400'}">
              {opt.label}
            </button>
          {/each}
        </div>
      </div>

      <div>
        <label for="elev-reason" class="block text-sm font-medium text-neutral-700 mb-1.5">Reason <span class="text-red-500">*</span></label>
        <textarea id="elev-reason" rows="4" bind:value={form.reason}
          placeholder="Why do you need this elevation? What action will you take?"
          class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 resize-none"></textarea>
      </div>

      <div class="rounded-lg bg-neutral-50 border border-neutral-200 p-4 text-xs text-neutral-600">
        <p class="font-medium text-neutral-700 mb-1">What happens after submit</p>
        <ul class="list-disc pl-5 space-y-0.5">
          <li>An approver reviews and decides.</li>
          <li>If approved, the role activates immediately and auto-revokes after the duration.</li>
          <li>Every elevation is logged for audit (Cluster 6 audit feed).</li>
        </ul>
      </div>

      <div class="flex items-center gap-3 pt-2">
        {#if isDev}
          <button onclick={devFill} class="rounded-lg bg-orange-500 px-3 py-2.5 text-sm font-medium text-white hover:bg-orange-600 transition-colors mr-auto">Dev Fill</button>
        {/if}
        <button onclick={handleSubmit} disabled={saving}
          class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-900 transition-colors disabled:opacity-60 ml-auto">
          {saving ? "Requesting..." : "Request elevation"}
        </button>
      </div>
    </div>

    <!-- Recent elevations (col 3) -->
    <div class="rounded-xl border border-neutral-200 bg-white p-6">
      <h2 class="text-sm font-semibold text-neutral-800 mb-3">Your recent elevations</h2>
      {#if historyLoading}
        <div class="p-6 text-center text-sm text-neutral-400">Loading…</div>
      {:else if history.length === 0}
        <p class="text-sm text-neutral-500">No elevation requests yet.</p>
      {:else}
        <ul class="space-y-3">
          {#each history as h}
            <li class="rounded-lg border border-neutral-100 p-3">
              <div class="flex items-center justify-between gap-2">
                <p class="text-sm font-medium text-neutral-800 truncate">{h.requested_role_name || "—"}</p>
                <span class="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium {statusBadge(h.status)}">
                  {h.status_display}
                </span>
              </div>
              <p class="mt-1 text-xs text-neutral-500">{formatDate(h.created_at)}</p>
              {#if h.granted_valid_until && h.status === "approved"}
                <p class="mt-1 text-xs text-neutral-600">until {formatDate(h.granted_valid_until)}</p>
              {/if}
            </li>
          {/each}
        </ul>
      {/if}
    </div>
  </div>
</div>

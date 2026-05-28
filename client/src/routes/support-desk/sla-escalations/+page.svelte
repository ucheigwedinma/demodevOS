<script lang="ts">
  import { onMount } from "svelte";

  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    PaginatedResponse,
    SupportSlaEscalationTicket,
    SupportSlaEscalationsOverview,
    SupportSlaPolicy,
    SupportTicketPriority,
  } from "$lib/types";

  type QueueView = "all" | "at_risk" | "upcoming" | "breached" | "escalated";

  type PolicyDraft = {
    priority: SupportTicketPriority;
    priorityLabel: string;
    policyId: number | null;
    name: string;
    responseTargetHours: string;
    resolutionTargetHours: string;
    agentThreshold: string;
    managerThreshold: string;
    breachRole: string;
    notifyAssignedAgent: boolean;
    notifyManager: boolean;
    isActive: boolean;
  };

  const queueViews: Array<{ key: QueueView; label: string; helper: string }> = [
    { key: "all", label: "All Active", helper: "All open SLA-tracked tickets." },
    { key: "at_risk", label: "At Risk", helper: "Approaching SLA warning thresholds." },
    { key: "upcoming", label: "Upcoming", helper: "Due in next 24 hours." },
    { key: "breached", label: "Breached", helper: "SLA deadline missed." },
    { key: "escalated", label: "Escalated", helper: "Escalated to leadership path." },
  ];

  const enterpriseDefaults: Array<{
    priority: SupportTicketPriority;
    label: string;
    firstResponseHours: number;
    resolutionHours: number;
  }> = [
    { priority: "low", label: "Low", firstResponseHours: 24, resolutionHours: 72 },
    { priority: "medium", label: "Medium", firstResponseHours: 8, resolutionHours: 48 },
    { priority: "high", label: "High", firstResponseHours: 2, resolutionHours: 24 },
    { priority: "critical", label: "Critical", firstResponseHours: 0.5, resolutionHours: 4 },
  ];

  let loadingOverview = $state(true);
  let loadingPolicies = $state(true);
  let loadingQueue = $state(true);

  let actionKey = $state("");
  let errorMessage = $state("");

  let overview = $state<SupportSlaEscalationsOverview | null>(null);
  let policies = $state<SupportSlaPolicy[]>([]);
  let policyDrafts = $state<PolicyDraft[]>([]);
  let queueTickets = $state<SupportSlaEscalationTicket[]>([]);

  let activeQueueView = $state<QueueView>("all");
  let editingPriority = $state<SupportTicketPriority | null>(null);

  function parseError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      const fieldMessage = Object.values(error.fieldErrors).flat()[0];
      if (fieldMessage) return fieldMessage;
      if (typeof error.data.detail === "string") return error.data.detail;
    }
    return fallback;
  }

  function isBusy(key: string): boolean {
    return actionKey === key;
  }

  function toNumber(value: string | number): number {
    if (typeof value === "number") return value;
    const normalized = Number(value);
    return Number.isFinite(normalized) ? normalized : 0;
  }

  function formatDateTime(value: string | null): string {
    if (!value) return "-";
    return new Date(value).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function formatHoursLabel(hours: number): string {
    if (hours < 1) return `${Math.round(hours * 60)}m`;
    if (hours % 24 === 0) return `${Math.round(hours / 24)}d`;
    if (Number.isInteger(hours)) return `${hours}h`;
    const whole = Math.floor(hours);
    const mins = Math.round((hours - whole) * 60);
    if (whole === 0) return `${mins}m`;
    if (mins === 0) return `${whole}h`;
    return `${whole}h ${mins}m`;
  }

  function priorityBadgeClass(priority: SupportTicketPriority): string {
    if (priority === "critical") return "border-red-200 bg-red-50 text-red-700";
    if (priority === "high") return "border-orange-200 bg-orange-50 text-orange-700";
    if (priority === "medium") return "border-amber-200 bg-amber-50 text-amber-700";
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }

  function stageBadgeClass(stage: SupportSlaEscalationTicket["escalation_stage"]): string {
    if (stage === "breached") return "border-red-300 bg-red-50 text-red-700";
    if (stage === "escalated") return "border-rose-300 bg-rose-50 text-rose-700";
    if (stage === "manager_warning") return "border-orange-300 bg-orange-50 text-orange-700";
    if (stage === "agent_warning") return "border-amber-300 bg-amber-50 text-amber-700";
    return "border-emerald-300 bg-emerald-50 text-emerald-700";
  }

  function statusLabel(stage: SupportSlaEscalationTicket["escalation_stage"]): string {
    if (stage === "agent_warning") return "50% Warning";
    if (stage === "manager_warning") return "80% Warning";
    if (stage === "escalated") return "Escalated";
    if (stage === "breached") return "Breached";
    return "On Track";
  }

  function policyForPriority(
    sourcePolicies: SupportSlaPolicy[],
    priority: SupportTicketPriority,
  ): SupportSlaPolicy | null {
    const exact = sourcePolicies.find(
      (policy) => policy.priority === priority && policy.category === "",
    );
    if (exact) return exact;

    const scoped = sourcePolicies.find((policy) => policy.priority === priority);
    if (scoped) return scoped;

    const wildcard = sourcePolicies.find(
      (policy) => policy.priority === "" && policy.category === "",
    );
    return wildcard ?? null;
  }

  function buildPolicyDrafts(sourcePolicies: SupportSlaPolicy[]): PolicyDraft[] {
    return enterpriseDefaults.map((row) => {
      const matched = policyForPriority(sourcePolicies, row.priority);
      return {
        priority: row.priority,
        priorityLabel: row.label,
        policyId: matched?.id ?? null,
        name: matched?.name ?? `${row.label} Priority SLA`,
        responseTargetHours: String(toNumber(matched?.response_target_hours ?? row.firstResponseHours)),
        resolutionTargetHours: String(toNumber(matched?.resolution_target_hours ?? row.resolutionHours)),
        agentThreshold: String(matched?.agent_notify_threshold_percent ?? 50),
        managerThreshold: String(matched?.manager_notify_threshold_percent ?? 80),
        breachRole: matched?.breach_escalation_role ?? "director",
        notifyAssignedAgent: matched?.notify_assigned_agent ?? true,
        notifyManager: matched?.notify_manager ?? true,
        isActive: matched?.is_active ?? true,
      };
    });
  }

  function updatePolicyDraft(
    priority: SupportTicketPriority,
    patch: Partial<PolicyDraft>,
  ) {
    policyDrafts = policyDrafts.map((draft) =>
      draft.priority === priority ? { ...draft, ...patch } : draft,
    );
  }

  function isEditing(priority: SupportTicketPriority): boolean {
    return editingPriority === priority;
  }

  function beginEditing(priority: SupportTicketPriority) {
    editingPriority = priority;
  }

  function cancelEditing(priority: SupportTicketPriority) {
    const restored = buildPolicyDrafts(policies).find((draft) => draft.priority === priority);
    if (restored) updatePolicyDraft(priority, restored);
    if (editingPriority === priority) editingPriority = null;
  }

  function applyEnterpriseDefaultsToDrafts() {
    policyDrafts = policyDrafts.map((draft) => {
      const defaults = enterpriseDefaults.find((row) => row.priority === draft.priority)!;
      return {
        ...draft,
        responseTargetHours: String(defaults.firstResponseHours),
        resolutionTargetHours: String(defaults.resolutionHours),
        agentThreshold: "50",
        managerThreshold: "80",
        breachRole: "director",
        notifyAssignedAgent: true,
        notifyManager: true,
        isActive: true,
      };
    });
    toast.success(
      "Defaults applied",
      "Enterprise SLA defaults loaded into policy drafts.",
    );
  }

  async function loadOverview() {
    loadingOverview = true;
    try {
      overview = await api.get<SupportSlaEscalationsOverview>(
        "/support-desk/sla-escalations/overview/",
      );
    } catch (error) {
      overview = null;
      toast.error(
        "Overview unavailable",
        parseError(error, "Could not load SLA overview metrics."),
      );
    } finally {
      loadingOverview = false;
    }
  }

  async function loadPolicies() {
    loadingPolicies = true;
    try {
      const response = await api.get<PaginatedResponse<SupportSlaPolicy>>(
        "/support-desk/sla-escalations/policies/",
        { page_size: "200" },
      );
      policies = response.results;
      policyDrafts = buildPolicyDrafts(response.results);
      editingPriority = null;
    } catch (error) {
      policies = [];
      policyDrafts = buildPolicyDrafts([]);
      editingPriority = null;
      toast.error(
        "Policies unavailable",
        parseError(error, "Could not load SLA policy records."),
      );
    } finally {
      loadingPolicies = false;
    }
  }

  async function loadQueue() {
    loadingQueue = true;
    errorMessage = "";

    try {
      const params: Record<string, string> = {
        page_size: "50",
      };
      if (activeQueueView !== "all") params.queue = activeQueueView;

      const response = await api.get<PaginatedResponse<SupportSlaEscalationTicket>>(
        "/support-desk/sla-escalations/tickets/",
        params,
      );
      queueTickets = response.results;
    } catch (error) {
      queueTickets = [];
      errorMessage = parseError(error, "Could not load SLA escalation queue.");
    } finally {
      loadingQueue = false;
    }
  }

  function setQueueView(view: QueueView) {
    if (activeQueueView === view) return;
    activeQueueView = view;
    void loadQueue();
  }

  async function savePolicy(priority: SupportTicketPriority) {
    const draft = policyDrafts.find((item) => item.priority === priority);
    if (!draft) return;

    const responseHours = toNumber(draft.responseTargetHours);
    const resolutionHours = toNumber(draft.resolutionTargetHours);
    const agentThreshold = Math.round(toNumber(draft.agentThreshold));
    const managerThreshold = Math.round(toNumber(draft.managerThreshold));

    if (responseHours <= 0 || resolutionHours <= 0) {
      toast.error(
        "Invalid SLA target",
        "First response and resolution values must be greater than zero.",
      );
      return;
    }

    if (managerThreshold <= agentThreshold) {
      toast.error(
        "Invalid thresholds",
        "Manager threshold must be greater than agent threshold.",
      );
      return;
    }

    actionKey = `save-${priority}`;

    const payload = {
      name: draft.name.trim() || `${draft.priorityLabel} Priority SLA`,
      description: `${draft.priorityLabel} priority enterprise SLA policy`,
      category: "",
      priority: draft.priority,
      response_target_hours: responseHours,
      resolution_target_hours: resolutionHours,
      escalate_after_hours: 0,
      escalation_path: [],
      agent_notify_threshold_percent: agentThreshold,
      manager_notify_threshold_percent: managerThreshold,
      breach_escalation_role: draft.breachRole.trim() || "director",
      notify_assigned_agent: draft.notifyAssignedAgent,
      notify_manager: draft.notifyManager,
      is_active: draft.isActive,
    };

    try {
      if (draft.policyId) {
        await api.patch<SupportSlaPolicy>(
          `/support-desk/sla-escalations/policies/${draft.policyId}/`,
          payload,
        );
      } else {
        await api.post<SupportSlaPolicy>(
          "/support-desk/sla-escalations/policies/",
          payload,
        );
      }

      toast.success(
        "Policy saved",
        `${draft.priorityLabel} priority SLA policy saved successfully.`,
      );

      editingPriority = null;
      await Promise.all([loadPolicies(), loadOverview(), loadQueue()]);
    } catch (error) {
      toast.error("Save failed", parseError(error, "Could not save SLA policy."));
    } finally {
      actionKey = "";
    }
  }

  async function togglePolicyActive(policyId: number) {
    actionKey = `toggle-${policyId}`;
    try {
      await api.post<SupportSlaPolicy>(
        `/support-desk/sla-escalations/policies/${policyId}/toggle-active/`,
        {},
      );
      toast.success("Policy updated", "Policy activation state changed.");
      await Promise.all([loadPolicies(), loadOverview(), loadQueue()]);
    } catch (error) {
      toast.error(
        "Toggle failed",
        parseError(error, "Could not change policy activation state."),
      );
    } finally {
      actionKey = "";
    }
  }

  onMount(async () => {
    await Promise.all([loadOverview(), loadPolicies(), loadQueue()]);
  });
</script>

<div class="space-y-8">
  <section class="space-y-4">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div class="max-w-3xl">
        <h1 class="text-2xl font-bold text-neutral-800">SLA & Escalations</h1>
        <p class="mt-1 max-w-2xl text-sm text-neutral-500">
          Define response and resolution policies by priority and enforce escalation rules:
          50% warning to agent, 80% warning to manager, and automatic escalation to director on breach.
        </p>
      </div>

      <div class="grid w-full max-w-sm gap-3 sm:grid-cols-2">
        <div class="rounded-xl border border-neutral-200 bg-white px-4 py-4">
          <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Active Policies</p>
          <p class="mt-2 text-2xl font-semibold text-neutral-950">{overview?.active_policy_count ?? "--"}</p>
        </div>
        <div class="rounded-xl border border-neutral-200 bg-white px-4 py-4">
          <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Breaches</p>
          <p class="mt-2 text-2xl font-semibold text-neutral-950">{overview?.breached_ticket_count ?? "--"}</p>
        </div>
        <div class="rounded-xl border border-neutral-200 bg-white px-4 py-4">
          <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">50% Warnings</p>
          <p class="mt-2 text-2xl font-semibold text-neutral-950">{overview?.warning_50_count ?? "--"}</p>
        </div>
        <div class="rounded-xl border border-neutral-200 bg-white px-4 py-4">
          <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">80% Warnings</p>
          <p class="mt-2 text-2xl font-semibold text-neutral-950">{overview?.warning_80_count ?? "--"}</p>
        </div>
      </div>
    </div>
  </section>

  <section class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="text-lg font-semibold text-neutral-950">Enterprise Baseline Matrix</h2>
        <p class="mt-1 text-sm text-neutral-500">Priority based first-response and resolution targets.</p>
      </div>
      <button
        type="button"
        onclick={applyEnterpriseDefaultsToDrafts}
        class="rounded-xl border border-neutral-800 bg-neutral-800 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800"
      >
        Apply Defaults to Drafts
      </button>
    </div>

    <div class="mt-4 overflow-x-auto rounded-2xl border border-neutral-200">
      <table class="min-w-[700px] w-full">
        <thead class="bg-neutral-50">
          <tr>
            <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Priority</th>
            <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">First Response</th>
            <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Resolution</th>
          </tr>
        </thead>
        <tbody>
          {#each enterpriseDefaults as row}
            <tr class="border-b border-neutral-100 bg-white">
              <td class="px-4 py-3 text-sm font-semibold text-neutral-800">{row.label}</td>
              <td class="px-4 py-3 text-sm text-neutral-700">{formatHoursLabel(row.firstResponseHours)}</td>
              <td class="px-4 py-3 text-sm text-neutral-700">{formatHoursLabel(row.resolutionHours)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    <div class="mt-5 grid gap-3 md:grid-cols-3">
      <div class="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-4">
        <p class="text-xs font-semibold uppercase tracking-[0.14em] text-amber-700">Rule 1</p>
        <p class="mt-1 text-sm font-medium text-amber-900">If SLA 50% reached, notify assigned agent.</p>
      </div>
      <div class="rounded-2xl border border-orange-200 bg-orange-50 px-4 py-4">
        <p class="text-xs font-semibold uppercase tracking-[0.14em] text-orange-700">Rule 2</p>
        <p class="mt-1 text-sm font-medium text-orange-900">If SLA 80% reached, notify manager.</p>
      </div>
      <div class="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-4">
        <p class="text-xs font-semibold uppercase tracking-[0.14em] text-rose-700">Rule 3</p>
        <p class="mt-1 text-sm font-medium text-rose-900">If SLA breached, escalate to director.</p>
      </div>
    </div>
  </section>

  <div class="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,1.2fr)]">
    <section class="space-y-6">
      <article class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
        <h3 class="text-lg font-semibold text-neutral-950">Policy Configuration by Priority</h3>
        <p class="mt-1 text-sm text-neutral-500">Save one policy per priority for predictable enterprise enforcement.</p>

        <div class="mt-5 space-y-4">
          {#each policyDrafts as draft}
            <article class="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-4">
              <div class="flex flex-wrap items-center justify-between gap-3">
                <div class="flex items-center gap-2">
                  <span class={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${priorityBadgeClass(draft.priority)}`}>
                    {draft.priorityLabel}
                  </span>
                  {#if draft.policyId}
                    <span class="text-xs text-neutral-500">Policy #{draft.policyId}</span>
                  {/if}
                </div>
                <div class="flex items-center gap-2">
                  {#if draft.policyId}
                    <button
                      type="button"
                      onclick={() => togglePolicyActive(draft.policyId!)}
                      disabled={isBusy(`toggle-${draft.policyId}`)}
                      class={`rounded-xl px-3 py-1.5 text-xs font-semibold ${draft.isActive ? "border border-emerald-300 bg-emerald-50 text-emerald-700" : "border border-neutral-300 bg-white text-neutral-700"}`}
                    >
                      {isBusy(`toggle-${draft.policyId}`) ? "Updating..." : draft.isActive ? "Active" : "Inactive"}
                    </button>
                  {/if}
                  {#if isEditing(draft.priority)}
                    <button
                      type="button"
                      onclick={() => cancelEditing(draft.priority)}
                      class="rounded-xl border border-neutral-300 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-100"
                    >
                      Cancel
                    </button>
                  {:else}
                    <button
                      type="button"
                      onclick={() => beginEditing(draft.priority)}
                      class="rounded-xl border border-neutral-800 bg-neutral-800 px-3 py-1.5 text-xs font-semibold text-white hover:bg-neutral-800"
                    >
                      Edit
                    </button>
                  {/if}
                </div>
              </div>

              {#if isEditing(draft.priority)}
                <div class="mt-4 grid gap-3 sm:grid-cols-2">
                  <label class="block">
                    <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Policy Name</span>
                    <input
                      type="text"
                      value={draft.name}
                      oninput={(event) => updatePolicyDraft(draft.priority, { name: (event.currentTarget as HTMLInputElement).value })}
                      class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
                    />
                  </label>
                  <label class="block">
                    <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Breach Escalation Role</span>
                    <input
                      type="text"
                      value={draft.breachRole}
                      oninput={(event) => updatePolicyDraft(draft.priority, { breachRole: (event.currentTarget as HTMLInputElement).value })}
                      class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
                    />
                  </label>

                  <label class="block">
                    <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">First Response (hours)</span>
                    <input
                      type="number"
                      min="0.1"
                      step="0.1"
                      value={draft.responseTargetHours}
                      oninput={(event) => updatePolicyDraft(draft.priority, { responseTargetHours: (event.currentTarget as HTMLInputElement).value })}
                      class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
                    />
                  </label>
                  <label class="block">
                    <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Resolution (hours)</span>
                    <input
                      type="number"
                      min="0.1"
                      step="0.1"
                      value={draft.resolutionTargetHours}
                      oninput={(event) => updatePolicyDraft(draft.priority, { resolutionTargetHours: (event.currentTarget as HTMLInputElement).value })}
                      class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
                    />
                  </label>

                  <label class="block">
                    <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Agent Notify %</span>
                    <input
                      type="number"
                      min="1"
                      max="100"
                      step="1"
                      value={draft.agentThreshold}
                      oninput={(event) => updatePolicyDraft(draft.priority, { agentThreshold: (event.currentTarget as HTMLInputElement).value })}
                      class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
                    />
                  </label>
                  <label class="block">
                    <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Manager Notify %</span>
                    <input
                      type="number"
                      min="1"
                      max="100"
                      step="1"
                      value={draft.managerThreshold}
                      oninput={(event) => updatePolicyDraft(draft.priority, { managerThreshold: (event.currentTarget as HTMLInputElement).value })}
                      class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
                    />
                  </label>
                </div>

                <div class="mt-4 grid gap-3 sm:grid-cols-2">
                  <label class="inline-flex items-center gap-2 rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700">
                    <input
                      type="checkbox"
                      checked={draft.notifyAssignedAgent}
                      onchange={(event) => updatePolicyDraft(draft.priority, { notifyAssignedAgent: (event.currentTarget as HTMLInputElement).checked })}
                      class="rounded border-neutral-300"
                    />
                    Notify assigned agent
                  </label>
                  <label class="inline-flex items-center gap-2 rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700">
                    <input
                      type="checkbox"
                      checked={draft.notifyManager}
                      onchange={(event) => updatePolicyDraft(draft.priority, { notifyManager: (event.currentTarget as HTMLInputElement).checked })}
                      class="rounded border-neutral-300"
                    />
                    Notify manager
                  </label>
                </div>

                <button
                  type="button"
                  onclick={() => savePolicy(draft.priority)}
                  disabled={isBusy(`save-${draft.priority}`)}
                  class="mt-4 w-full rounded-xl border border-neutral-800 bg-neutral-800 px-4 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isBusy(`save-${draft.priority}`) ? "Saving..." : `Save ${draft.priorityLabel} Policy`}
                </button>
              {:else}
                <div class="mt-4 grid gap-3 sm:grid-cols-2">
                  <div class="rounded-xl border border-neutral-200 bg-white px-3 py-2">
                    <p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-400">Policy Name</p>
                    <p class="mt-1 text-sm font-medium text-neutral-800">{draft.name}</p>
                  </div>
                  <div class="rounded-xl border border-neutral-200 bg-white px-3 py-2">
                    <p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-400">Breach Escalation Role</p>
                    <p class="mt-1 text-sm font-medium text-neutral-800">{draft.breachRole || "--"}</p>
                  </div>
                  <div class="rounded-xl border border-neutral-200 bg-white px-3 py-2">
                    <p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-400">First Response</p>
                    <p class="mt-1 text-sm font-medium text-neutral-800">{formatHoursLabel(toNumber(draft.responseTargetHours))}</p>
                  </div>
                  <div class="rounded-xl border border-neutral-200 bg-white px-3 py-2">
                    <p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-400">Resolution</p>
                    <p class="mt-1 text-sm font-medium text-neutral-800">{formatHoursLabel(toNumber(draft.resolutionTargetHours))}</p>
                  </div>
                  <div class="rounded-xl border border-neutral-200 bg-white px-3 py-2">
                    <p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-400">Notify Thresholds</p>
                    <p class="mt-1 text-sm font-medium text-neutral-800">
                      Agent {Math.round(toNumber(draft.agentThreshold))}% • Manager {Math.round(toNumber(draft.managerThreshold))}%
                    </p>
                  </div>
                  <div class="rounded-xl border border-neutral-200 bg-white px-3 py-2">
                    <p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-400">Notifications</p>
                    <p class="mt-1 text-sm font-medium text-neutral-800">
                      Agent: {draft.notifyAssignedAgent ? "Yes" : "No"} • Manager: {draft.notifyManager ? "Yes" : "No"}
                    </p>
                  </div>
                </div>
              {/if}
            </article>
          {/each}
        </div>
      </article>
    </section>

    <section class="space-y-6">
      <article class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
        <h3 class="text-lg font-semibold text-neutral-950">SLA Escalation Queue</h3>
        <p class="mt-1 text-sm text-neutral-500">Live queue filtered by risk and escalation stage.</p>

        <div class="mt-4 flex flex-wrap gap-2">
          {#each queueViews as view}
            <button
              type="button"
              onclick={() => setQueueView(view.key)}
              class={`rounded-xl border px-3 py-2 text-sm font-semibold ${activeQueueView === view.key ? "border-neutral-800 bg-neutral-800 text-white" : "border-neutral-200 bg-neutral-50 text-neutral-700 hover:border-neutral-300 hover:bg-white"}`}
            >
              {view.label}
            </button>
          {/each}
        </div>

        <p class="mt-2 text-xs text-neutral-500">
          {queueViews.find((view) => view.key === activeQueueView)?.helper}
        </p>

        <div class="mt-5 overflow-hidden rounded-2xl border border-neutral-200">
          {#if loadingQueue}
            <div class="flex items-center justify-center py-14">
              <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-800"></div>
            </div>
          {:else if errorMessage}
            <div class="px-6 py-14 text-center">
              <h4 class="text-base font-semibold text-red-900">Queue unavailable</h4>
              <p class="mt-2 text-sm text-red-700">{errorMessage}</p>
              <button type="button" onclick={() => loadQueue()} class="mt-4 rounded-xl border border-red-300 bg-white px-4 py-2 text-sm font-semibold text-red-800 hover:bg-red-100">
                Retry
              </button>
            </div>
          {:else if queueTickets.length === 0}
            <div class="px-6 py-14 text-center">
              <h4 class="text-base font-semibold text-neutral-950">No tickets in this queue</h4>
              <p class="mt-2 text-sm text-neutral-500">No records match the selected SLA queue filter.</p>
            </div>
          {:else}
            <div class="overflow-x-auto">
              <table class="min-w-[1040px] w-full">
                <thead class="bg-neutral-50">
                  <tr>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Ticket</th>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Priority</th>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Stage</th>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Response SLA</th>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Resolution SLA</th>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Progress</th>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Overdue</th>
                  </tr>
                </thead>
                <tbody>
                  {#each queueTickets as ticket}
                    <tr class="border-b border-neutral-100 bg-white">
                      <td class="px-4 py-4">
                        <p class="text-sm font-semibold text-neutral-800">{ticket.ticket_id} • {ticket.subject}</p>
                        <p class="mt-1 text-xs text-neutral-500">{ticket.policy_name || "Default SLA"} • Due {formatDateTime(ticket.resolution_deadline)}</p>
                      </td>
                      <td class="px-4 py-4">
                        <span class={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${priorityBadgeClass(ticket.priority)}`}>
                          {ticket.priority_display}
                        </span>
                      </td>
                      <td class="px-4 py-4">
                        <span class={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${stageBadgeClass(ticket.escalation_stage)}`}>
                          {statusLabel(ticket.escalation_stage)}
                        </span>
                      </td>
                      <td class="px-4 py-4 text-sm text-neutral-700">
                        {ticket.first_response_target_display} ({ticket.first_response_progress_percent.toFixed(0)}%)
                      </td>
                      <td class="px-4 py-4 text-sm text-neutral-700">
                        {ticket.resolution_target_display}
                      </td>
                      <td class="px-4 py-4 text-sm text-neutral-700">
                        {ticket.resolution_progress_percent.toFixed(0)}%
                      </td>
                      <td class="px-4 py-4 text-sm text-neutral-700">
                        {#if ticket.overdue_hours !== null && ticket.overdue_hours > 0}
                          {ticket.overdue_hours.toFixed(2)}h
                        {:else}
                          --
                        {/if}
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {/if}
        </div>
      </article>

      <article class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
        <h3 class="text-lg font-semibold text-neutral-950">Current Effective Matrix</h3>
        <p class="mt-1 text-sm text-neutral-500">Derived from active policies by priority.</p>

        <div class="mt-4 space-y-2">
          {#each overview?.policy_matrix ?? [] as row}
            <div class="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <div class="flex items-center gap-2">
                  <span class={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${priorityBadgeClass(row.priority)}`}>
                    {row.priority_label}
                  </span>
                  <p class="text-sm font-semibold text-neutral-800">{row.policy_name}</p>
                </div>
                <p class="text-xs text-neutral-500">{row.breach_escalation_role} on breach</p>
              </div>
              <p class="mt-2 text-sm text-neutral-700">
                First response: {row.first_response_target_display} • Resolution: {row.resolution_target_display}
              </p>
              <p class="mt-1 text-xs text-neutral-500">
                Notify agent at {row.agent_notify_threshold_percent}% • manager at {row.manager_notify_threshold_percent}%
              </p>
            </div>
          {/each}
        </div>
      </article>
    </section>
  </div>
</div>

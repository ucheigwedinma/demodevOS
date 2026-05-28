<script lang="ts">
  import { onMount } from "svelte";

  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type {
    PaginatedResponse,
    SupportAutomationOverview,
    SupportAutomationRule,
    SupportAutomationRun,
    SupportAutomationTriggerType,
    SupportDeskTicketLookups,
  } from "$lib/types";

  type RuleDraft = {
    id: number | null;
    name: string;
    description: string;
    triggerType: SupportAutomationTriggerType;
    priority: string;
    runOncePerTicket: boolean;
    isActive: boolean;
    subjectContains: string;
    category: string;
    priorityCondition: string;
    statusCondition: string;
    statusChangedTo: string;
    slaBreachImminentHours: string;
    slaProgressGte: string;
    assignDepartmentId: string;
    assignAgentId: string;
    setPriority: string;
    setStatus: string;
    escalateToSupervisor: boolean;
    addInternalNote: string;
  };

  const triggerOptions: Array<{ key: SupportAutomationTriggerType; label: string }> = [
    { key: "ticket_created", label: "Ticket Creation" },
    { key: "ticket_updated", label: "Ticket Update" },
    { key: "sla_threshold", label: "SLA Threshold" },
    { key: "status_changed", label: "Status Change" },
  ];

  let loadingOverview = $state(true);
  let loadingRules = $state(true);
  let loadingRuns = $state(true);
  let loadingLookups = $state(true);
  let actionKey = $state("");

  let overview = $state<SupportAutomationOverview | null>(null);
  let rules = $state<SupportAutomationRule[]>([]);
  let runs = $state<SupportAutomationRun[]>([]);
  let lookups = $state<SupportDeskTicketLookups | null>(null);

  let selectedTriggerFilter = $state<"all" | SupportAutomationTriggerType>("all");

  let draft = $state<RuleDraft>(emptyDraft());

  function emptyDraft(): RuleDraft {
    return {
      id: null,
      name: "",
      description: "",
      triggerType: "ticket_created",
      priority: "100",
      runOncePerTicket: false,
      isActive: true,
      subjectContains: "",
      category: "",
      priorityCondition: "",
      statusCondition: "",
      statusChangedTo: "",
      slaBreachImminentHours: "",
      slaProgressGte: "",
      assignDepartmentId: "",
      assignAgentId: "",
      setPriority: "",
      setStatus: "",
      escalateToSupervisor: false,
      addInternalNote: "",
    };
  }

  function parseError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      const fieldMessage = Object.values(error.fieldErrors).flat()[0];
      if (fieldMessage) return fieldMessage;
      if (typeof error.data.detail === "string") return error.data.detail;
    }
    return fallback;
  }

  function formatDateTime(value: string | null): string {
    if (!value) return "--";
    return new Date(value).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function triggerBadgeClass(triggerType: SupportAutomationTriggerType): string {
    if (triggerType === "ticket_created") return "border-cyan-200 bg-cyan-50 text-cyan-700";
    if (triggerType === "ticket_updated") return "border-sky-200 bg-sky-50 text-sky-700";
    if (triggerType === "sla_threshold") return "border-orange-200 bg-orange-50 text-orange-700";
    return "border-violet-200 bg-violet-50 text-violet-700";
  }


  function mapRuleToDraft(rule: SupportAutomationRule): RuleDraft {
    const conditions = rule.conditions ?? {};
    const actions = rule.actions ?? {};

    return {
      id: rule.id,
      name: rule.name,
      description: rule.description || "",
      triggerType: rule.trigger_type,
      priority: String(rule.priority),
      runOncePerTicket: rule.run_once_per_ticket,
      isActive: rule.is_active,
      subjectContains: String(conditions.subject_contains ?? ""),
      category: String(conditions.category ?? ""),
      priorityCondition: String(conditions.priority ?? ""),
      statusCondition: String(conditions.status ?? ""),
      statusChangedTo: String(conditions.status_changed_to ?? ""),
      slaBreachImminentHours: String(conditions.sla_breach_imminent_hours ?? ""),
      slaProgressGte: String(conditions.sla_progress_gte ?? ""),
      assignDepartmentId: String(actions.assign_department_id ?? ""),
      assignAgentId: String(actions.assign_agent_id ?? ""),
      setPriority: String(actions.set_priority ?? ""),
      setStatus: String(actions.set_status ?? ""),
      escalateToSupervisor: Boolean(actions.escalate_to_supervisor),
      addInternalNote: String(actions.add_internal_note ?? ""),
    };
  }

  function buildPayloadFromDraft(currentDraft: RuleDraft) {
    const conditions: Record<string, unknown> = {};
    const actions: Record<string, unknown> = {};

    if (currentDraft.subjectContains.trim()) conditions.subject_contains = currentDraft.subjectContains.trim();
    if (currentDraft.category) conditions.category = currentDraft.category;
    if (currentDraft.priorityCondition) conditions.priority = currentDraft.priorityCondition;
    if (currentDraft.statusCondition) conditions.status = currentDraft.statusCondition;
    if (currentDraft.statusChangedTo) conditions.status_changed_to = currentDraft.statusChangedTo;
    if (currentDraft.slaBreachImminentHours.trim()) conditions.sla_breach_imminent_hours = Number(currentDraft.slaBreachImminentHours);
    if (currentDraft.slaProgressGte.trim()) conditions.sla_progress_gte = Number(currentDraft.slaProgressGte);

    if (currentDraft.assignDepartmentId) actions.assign_department_id = Number(currentDraft.assignDepartmentId);
    if (currentDraft.assignAgentId) actions.assign_agent_id = Number(currentDraft.assignAgentId);
    if (currentDraft.setPriority) actions.set_priority = currentDraft.setPriority;
    if (currentDraft.setStatus) actions.set_status = currentDraft.setStatus;
    if (currentDraft.escalateToSupervisor) actions.escalate_to_supervisor = true;
    if (currentDraft.addInternalNote.trim()) actions.add_internal_note = currentDraft.addInternalNote.trim();

    return {
      name: currentDraft.name.trim(),
      description: currentDraft.description.trim(),
      trigger_type: currentDraft.triggerType,
      priority: Number(currentDraft.priority) || 100,
      run_once_per_ticket: currentDraft.runOncePerTicket,
      is_active: currentDraft.isActive,
      conditions,
      actions,
    };
  }

  async function loadOverview() {
    loadingOverview = true;
    try {
      overview = await api.get<SupportAutomationOverview>("/support-desk/automation/overview/");
    } catch (error) {
      overview = null;
      toast.error("Automation overview unavailable", parseError(error, "Could not load automation overview."));
    } finally {
      loadingOverview = false;
    }
  }

  async function loadRules() {
    loadingRules = true;
    try {
      const params: Record<string, string> = { page_size: "200" };
      if (selectedTriggerFilter !== "all") params.trigger_type = selectedTriggerFilter;
      const response = await api.get<PaginatedResponse<SupportAutomationRule>>(
        "/support-desk/automation/rules/",
        params,
      );
      rules = response.results;
    } catch (error) {
      rules = [];
      toast.error("Rules unavailable", parseError(error, "Could not load automation rules."));
    } finally {
      loadingRules = false;
    }
  }

  async function loadRuns() {
    loadingRuns = true;
    try {
      const response = await api.get<PaginatedResponse<SupportAutomationRun>>(
        "/support-desk/automation/runs/",
        { page_size: "30" },
      );
      runs = response.results;
    } catch (error) {
      runs = [];
      toast.error("Runs unavailable", parseError(error, "Could not load automation run history."));
    } finally {
      loadingRuns = false;
    }
  }

  async function loadLookups() {
    loadingLookups = true;
    try {
      lookups = await api.get<SupportDeskTicketLookups>("/support-desk/tickets/lookups/");
    } catch (error) {
      lookups = null;
      toast.error("Lookups unavailable", parseError(error, "Could not load ticket lookups."));
    } finally {
      loadingLookups = false;
    }
  }

  function resetDraft() {
    draft = emptyDraft();
  }

  function applyTemplatePassword() {
    const itDepartment = lookups?.departments.find((dept) =>
      dept.name.toLowerCase().includes("it") || dept.name.toLowerCase().includes("technology"),
    );
    draft = {
      ...emptyDraft(),
      name: "Password Request Routing",
      description: "If subject contains password, route to IT Support and set medium priority.",
      triggerType: "ticket_created",
      subjectContains: "password",
      assignDepartmentId: itDepartment ? String(itDepartment.id) : "",
      setPriority: "medium",
      addInternalNote: "Automation applied: Password request routed to IT Support.",
    };
  }

  function applyTemplateFinance() {
    const financeDepartment = lookups?.departments.find((dept) =>
      dept.name.toLowerCase().includes("finance"),
    );
    draft = {
      ...emptyDraft(),
      name: "Finance Queue Routing",
      description: "If category is Billing/Finance, assign to finance support queue.",
      triggerType: "ticket_created",
      category: "billing",
      assignDepartmentId: financeDepartment ? String(financeDepartment.id) : "",
      addInternalNote: "Automation applied: Finance-related request routed to finance queue.",
    };
  }

  function applyTemplateSla() {
    draft = {
      ...emptyDraft(),
      name: "SLA Breach Imminent Escalation",
      description: "Escalate to supervisor when SLA deadline is close.",
      triggerType: "sla_threshold",
      slaBreachImminentHours: "1",
      escalateToSupervisor: true,
      setStatus: "escalated",
      addInternalNote: "Automation escalation triggered: SLA breach imminent.",
    };
  }

  async function saveRule() {
    if (!draft.name.trim()) {
      toast.error("Rule name required", "Provide a name for this automation rule.");
      return;
    }

    const payload = buildPayloadFromDraft(draft);
    if (Object.keys(payload.actions).length === 0) {
      toast.error("Action required", "Add at least one automation action.");
      return;
    }

    actionKey = "save-rule";
    try {
      if (draft.id) {
        await api.patch<SupportAutomationRule>(
          `/support-desk/automation/rules/${draft.id}/`,
          payload,
        );
        toast.success("Rule updated", "Automation rule changes were saved.");
      } else {
        await api.post<SupportAutomationRule>(
          "/support-desk/automation/rules/",
          payload,
        );
        toast.success("Rule created", "Automation rule was created.");
      }

      resetDraft();
      await Promise.all([loadRules(), loadOverview()]);
    } catch (error) {
      toast.error("Save failed", parseError(error, "Could not save automation rule."));
    } finally {
      actionKey = "";
    }
  }

  async function toggleRuleActive(ruleId: number) {
    actionKey = `toggle-${ruleId}`;
    try {
      await api.post<SupportAutomationRule>(
        `/support-desk/automation/rules/${ruleId}/toggle-active/`,
        {},
      );
      toast.success("Rule updated", "Automation rule activation state changed.");
      await Promise.all([loadRules(), loadOverview()]);
    } catch (error) {
      toast.error("Toggle failed", parseError(error, "Could not toggle automation rule."));
    } finally {
      actionKey = "";
    }
  }

  async function deleteRule(ruleId: number) {
    actionKey = `delete-${ruleId}`;
    try {
      await api.delete<void>(`/support-desk/automation/rules/${ruleId}/`);
      toast.success("Rule deleted", "Automation rule was deleted.");
      if (draft.id === ruleId) resetDraft();
      await Promise.all([loadRules(), loadOverview()]);
    } catch (error) {
      toast.error("Delete failed", parseError(error, "Could not delete automation rule."));
    } finally {
      actionKey = "";
    }
  }

  function editRule(rule: SupportAutomationRule) {
    draft = mapRuleToDraft(rule);
  }

  onMount(async () => {
    await Promise.all([loadOverview(), loadRules(), loadRuns(), loadLookups()]);
  });
</script>

<div class="space-y-8">
  <section class="space-y-4">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div class="max-w-3xl">
        <h1 class="text-2xl font-bold text-neutral-800">Automation Rules</h1>
        <p class="mt-1 max-w-2xl text-sm text-neutral-500">
          Configure automatic ticket handling for creation, updates, SLA thresholds, and status changes.
        </p>
      </div>

      <div class="grid w-full max-w-sm gap-3 sm:grid-cols-2">
        <div class="rounded-xl border border-neutral-200 bg-white px-4 py-4">
          <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Active Rules</p>
          <p class="mt-2 text-2xl font-semibold text-neutral-950">{overview?.active_rule_count ?? "--"}</p>
        </div>
        <div class="rounded-xl border border-neutral-200 bg-white px-4 py-4">
          <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Total Rules</p>
          <p class="mt-2 text-2xl font-semibold text-neutral-950">{overview?.total_rule_count ?? "--"}</p>
        </div>
        <div class="rounded-xl border border-neutral-200 bg-white px-4 py-4">
          <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Runs (24h)</p>
          <p class="mt-2 text-2xl font-semibold text-neutral-950">{overview?.recent_run_count ?? "--"}</p>
        </div>
        <div class="rounded-xl border border-neutral-200 bg-white px-4 py-4">
          <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Last Run</p>
          <p class="mt-2 text-sm font-semibold text-neutral-950">{formatDateTime(overview?.last_run_at ?? null)}</p>
        </div>
      </div>
    </div>
  </section>

  <div class="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
    <section class="space-y-6">
      <article class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 class="text-lg font-semibold text-neutral-950">Configured Rules</h2>
            <p class="mt-1 text-sm text-neutral-500">Ordered by trigger and rule priority.</p>
          </div>
          <select
            value={selectedTriggerFilter}
            onchange={(event) => {
              selectedTriggerFilter = (event.currentTarget as HTMLSelectElement).value as "all" | SupportAutomationTriggerType;
              void loadRules();
            }}
            class="rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
          >
            <option value="all">All Triggers</option>
            {#each triggerOptions as option}
              <option value={option.key}>{option.label}</option>
            {/each}
          </select>
        </div>

        <div class="mt-5 space-y-3">
          {#if loadingRules}
            <div class="flex items-center justify-center py-10">
              <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-800"></div>
            </div>
          {:else if rules.length === 0}
            <div class="rounded-2xl border border-dashed border-neutral-300 bg-neutral-50 px-4 py-8 text-center text-sm text-neutral-500">
              No automation rules yet.
            </div>
          {:else}
            {#each rules as rule}
              <article class="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-4">
                <div class="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p class="text-sm font-semibold text-neutral-800">{rule.name}</p>
                    <p class="mt-1 text-xs text-neutral-500">{rule.description || "No description provided."}</p>
                    <div class="mt-2 flex flex-wrap gap-2">
                      <span class={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${triggerBadgeClass(rule.trigger_type)}`}>
                        {rule.trigger_type_display}
                      </span>
                      <span class="inline-flex rounded-full border border-neutral-300 bg-white px-2.5 py-1 text-xs font-semibold text-neutral-700">
                        Priority {rule.priority}
                      </span>
                      {#if rule.run_once_per_ticket}
                        <span class="inline-flex rounded-full border border-neutral-300 bg-white px-2.5 py-1 text-xs font-semibold text-neutral-700">
                          Run Once / Ticket
                        </span>
                      {/if}
                    </div>
                  </div>

                  <div class="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onclick={() => toggleRuleActive(rule.id)}
                      disabled={actionKey === `toggle-${rule.id}`}
                      class={`rounded-lg border px-3 py-1.5 text-xs font-semibold ${
                        rule.is_active
                          ? "border-emerald-300 bg-emerald-50 text-emerald-700"
                          : "border-neutral-300 bg-white text-neutral-700"
                      }`}
                    >
                      {actionKey === `toggle-${rule.id}` ? "Updating..." : rule.is_active ? "Active" : "Inactive"}
                    </button>
                    <button
                      type="button"
                      onclick={() => editRule(rule)}
                      class="rounded-lg border border-neutral-300 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-100"
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      onclick={() => deleteRule(rule.id)}
                      disabled={actionKey === `delete-${rule.id}`}
                      class="rounded-lg border border-red-300 bg-white px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {actionKey === `delete-${rule.id}` ? "Deleting..." : "Delete"}
                    </button>
                  </div>
                </div>
              </article>
            {/each}
          {/if}
        </div>
      </article>

      <article class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
        <h2 class="text-lg font-semibold text-neutral-950">Recent Automation Runs</h2>
        <p class="mt-1 text-sm text-neutral-500">Execution trail for matched and failed rules.</p>

        <div class="mt-4 overflow-hidden rounded-2xl border border-neutral-200">
          {#if loadingRuns}
            <div class="flex items-center justify-center py-10">
              <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-800"></div>
            </div>
          {:else if runs.length === 0}
            <div class="px-4 py-10 text-center text-sm text-neutral-500">No automation runs recorded yet.</div>
          {:else}
            <div class="overflow-x-auto">
              <table class="min-w-[760px] w-full">
                <thead class="bg-neutral-50">
                  <tr>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Time</th>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Rule</th>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Ticket</th>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Status</th>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Summary</th>
                  </tr>
                </thead>
                <tbody>
                  {#each runs as run}
                    <tr class="border-b border-neutral-100 bg-white">
                      <td class="px-4 py-3 text-sm text-neutral-700">{formatDateTime(run.created_at)}</td>
                      <td class="px-4 py-3 text-sm text-neutral-700">
                        <p class="font-semibold text-neutral-800">{run.rule_name || "Deleted rule"}</p>
                        <p class="text-xs text-neutral-500">{run.trigger_type_display}</p>
                      </td>
                      <td class="px-4 py-3 text-sm text-neutral-700">
                        {#if run.ticket_ref}
                          <p class="font-semibold text-neutral-800">{run.ticket_ref}</p>
                          <p class="text-xs text-neutral-500">{run.ticket_subject}</p>
                        {:else}
                          --
                        {/if}
                      </td>
                      <td class="px-4 py-3">
                        <StatusBadge status={run.status} label={run.status_display} />
                      </td>
                      <td class="px-4 py-3 text-sm text-neutral-700">{run.summary || "--"}</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {/if}
        </div>
      </article>
    </section>

    <section class="space-y-6">
      <article class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <h2 class="text-lg font-semibold text-neutral-950">{draft.id ? "Edit Automation Rule" : "Create Automation Rule"}</h2>
          {#if draft.id}
            <button
              type="button"
              onclick={resetDraft}
              class="rounded-lg border border-neutral-300 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-100"
            >
              New Rule
            </button>
          {/if}
        </div>

        <div class="mt-4 grid gap-3 sm:grid-cols-3">
          <button type="button" onclick={applyTemplatePassword} class="rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-left text-sm text-neutral-700 hover:bg-white">
            <p class="font-semibold text-neutral-800">Password Routing</p>
            <p class="mt-1 text-xs">Subject contains "password" -> IT + medium priority.</p>
          </button>
          <button type="button" onclick={applyTemplateFinance} class="rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-left text-sm text-neutral-700 hover:bg-white">
            <p class="font-semibold text-neutral-800">Finance Queue</p>
            <p class="mt-1 text-xs">Billing/Finance category -> finance support queue.</p>
          </button>
          <button type="button" onclick={applyTemplateSla} class="rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-left text-sm text-neutral-700 hover:bg-white">
            <p class="font-semibold text-neutral-800">SLA Escalation</p>
            <p class="mt-1 text-xs">Imminent breach -> escalate to supervisor.</p>
          </button>
        </div>

        <div class="mt-5 space-y-3">
          <div class="grid gap-3 sm:grid-cols-2">
            <label class="block">
              <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Rule Name</span>
              <input
                type="text"
                value={draft.name}
                oninput={(event) => draft = { ...draft, name: (event.currentTarget as HTMLInputElement).value }}
                class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
              />
            </label>
            <label class="block">
              <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Trigger</span>
              <select
                value={draft.triggerType}
                onchange={(event) => draft = { ...draft, triggerType: (event.currentTarget as HTMLSelectElement).value as SupportAutomationTriggerType }}
                class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
              >
                {#each triggerOptions as option}
                  <option value={option.key}>{option.label}</option>
                {/each}
              </select>
            </label>
          </div>

          <label class="block">
            <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Description</span>
            <textarea
              rows="2"
              value={draft.description}
              oninput={(event) => draft = { ...draft, description: (event.currentTarget as HTMLTextAreaElement).value }}
              class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
            ></textarea>
          </label>

          <div class="grid gap-3 sm:grid-cols-3">
            <label class="block">
              <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Priority Order</span>
              <input
                type="number"
                min="1"
                value={draft.priority}
                oninput={(event) => draft = { ...draft, priority: (event.currentTarget as HTMLInputElement).value }}
                class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
              />
            </label>
            <label class="inline-flex items-center gap-2 rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm text-neutral-700">
              <input
                type="checkbox"
                checked={draft.runOncePerTicket}
                onchange={(event) => draft = { ...draft, runOncePerTicket: (event.currentTarget as HTMLInputElement).checked }}
                class="rounded border-neutral-300"
              />
              Run once per ticket
            </label>
            <label class="inline-flex items-center gap-2 rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm text-neutral-700">
              <input
                type="checkbox"
                checked={draft.isActive}
                onchange={(event) => draft = { ...draft, isActive: (event.currentTarget as HTMLInputElement).checked }}
                class="rounded border-neutral-300"
              />
              Rule is active
            </label>
          </div>

          <div class="rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
            <h3 class="text-sm font-semibold text-neutral-800">Conditions</h3>
            <div class="mt-3 grid gap-3 sm:grid-cols-2">
              <label class="block">
                <span class="mb-1 block text-xs text-neutral-500">Subject Contains</span>
                <input type="text" value={draft.subjectContains} oninput={(event) => draft = { ...draft, subjectContains: (event.currentTarget as HTMLInputElement).value }} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm" />
              </label>
              <label class="block">
                <span class="mb-1 block text-xs text-neutral-500">Category</span>
                <select value={draft.category} onchange={(event) => draft = { ...draft, category: (event.currentTarget as HTMLSelectElement).value }} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
                  <option value="">Any</option>
                  {#each lookups?.categories ?? [] as category}
                    <option value={category.key}>{category.label}</option>
                  {/each}
                </select>
              </label>
              <label class="block">
                <span class="mb-1 block text-xs text-neutral-500">Priority</span>
                <select value={draft.priorityCondition} onchange={(event) => draft = { ...draft, priorityCondition: (event.currentTarget as HTMLSelectElement).value }} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
                  <option value="">Any</option>
                  {#each lookups?.priorities ?? [] as priority}
                    <option value={priority.key}>{priority.label}</option>
                  {/each}
                </select>
              </label>
              <label class="block">
                <span class="mb-1 block text-xs text-neutral-500">Status</span>
                <select value={draft.statusCondition} onchange={(event) => draft = { ...draft, statusCondition: (event.currentTarget as HTMLSelectElement).value }} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
                  <option value="">Any</option>
                  {#each lookups?.statuses ?? [] as status}
                    <option value={status.key}>{status.label}</option>
                  {/each}
                </select>
              </label>
              <label class="block">
                <span class="mb-1 block text-xs text-neutral-500">Status Changed To</span>
                <select value={draft.statusChangedTo} onchange={(event) => draft = { ...draft, statusChangedTo: (event.currentTarget as HTMLSelectElement).value }} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
                  <option value="">Any</option>
                  {#each lookups?.statuses ?? [] as status}
                    <option value={status.key}>{status.label}</option>
                  {/each}
                </select>
              </label>
              <label class="block">
                <span class="mb-1 block text-xs text-neutral-500">SLA Breach Imminent (hours)</span>
                <input type="number" min="0" step="0.1" value={draft.slaBreachImminentHours} oninput={(event) => draft = { ...draft, slaBreachImminentHours: (event.currentTarget as HTMLInputElement).value }} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm" />
              </label>
              <label class="block sm:col-span-2">
                <span class="mb-1 block text-xs text-neutral-500">SLA Progress >= (%)</span>
                <input type="number" min="0" max="100" step="1" value={draft.slaProgressGte} oninput={(event) => draft = { ...draft, slaProgressGte: (event.currentTarget as HTMLInputElement).value }} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm" />
              </label>
            </div>
          </div>

          <div class="rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
            <h3 class="text-sm font-semibold text-neutral-800">Actions</h3>
            <div class="mt-3 grid gap-3 sm:grid-cols-2">
              <label class="block">
                <span class="mb-1 block text-xs text-neutral-500">Assign Department</span>
                <select value={draft.assignDepartmentId} onchange={(event) => draft = { ...draft, assignDepartmentId: (event.currentTarget as HTMLSelectElement).value }} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
                  <option value="">None</option>
                  {#each lookups?.departments ?? [] as department}
                    <option value={String(department.id)}>{department.name}</option>
                  {/each}
                </select>
              </label>
              <label class="block">
                <span class="mb-1 block text-xs text-neutral-500">Assign Agent</span>
                <select value={draft.assignAgentId} onchange={(event) => draft = { ...draft, assignAgentId: (event.currentTarget as HTMLSelectElement).value }} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
                  <option value="">None</option>
                  {#each lookups?.agents ?? [] as agent}
                    <option value={String(agent.id)}>{agent.label}</option>
                  {/each}
                </select>
              </label>
              <label class="block">
                <span class="mb-1 block text-xs text-neutral-500">Set Priority</span>
                <select value={draft.setPriority} onchange={(event) => draft = { ...draft, setPriority: (event.currentTarget as HTMLSelectElement).value }} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
                  <option value="">No change</option>
                  {#each lookups?.priorities ?? [] as priority}
                    <option value={priority.key}>{priority.label}</option>
                  {/each}
                </select>
              </label>
              <label class="block">
                <span class="mb-1 block text-xs text-neutral-500">Set Status</span>
                <select value={draft.setStatus} onchange={(event) => draft = { ...draft, setStatus: (event.currentTarget as HTMLSelectElement).value }} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
                  <option value="">No change</option>
                  {#each lookups?.statuses ?? [] as status}
                    <option value={status.key}>{status.label}</option>
                  {/each}
                </select>
              </label>
            </div>

            <label class="mt-3 inline-flex items-center gap-2 rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700">
              <input type="checkbox" checked={draft.escalateToSupervisor} onchange={(event) => draft = { ...draft, escalateToSupervisor: (event.currentTarget as HTMLInputElement).checked }} class="rounded border-neutral-300" />
              Escalate to supervisor
            </label>

            <label class="mt-3 block">
              <span class="mb-1 block text-xs text-neutral-500">Add Internal Note</span>
              <textarea rows="2" value={draft.addInternalNote} oninput={(event) => draft = { ...draft, addInternalNote: (event.currentTarget as HTMLTextAreaElement).value }} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"></textarea>
            </label>
          </div>

          <button
            type="button"
            onclick={saveRule}
            disabled={actionKey === "save-rule" || loadingLookups}
            class="w-full rounded-xl border border-neutral-800 bg-neutral-800 px-4 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {actionKey === "save-rule" ? "Saving..." : draft.id ? "Update Rule" : "Create Rule"}
          </button>
        </div>
      </article>
    </section>
  </div>
</div>

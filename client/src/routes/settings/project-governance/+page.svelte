<script lang="ts">
  import { onMount } from "svelte";
  import { api } from "$lib/api";
  import type {
    PaginatedResponse,
    ProjectGovernanceSettings,
    ProjectListItem,
    ProjectMilestoneApprovalRule,
    ProjectPhase,
    ProjectPhaseDependency,
    RoleListItem,
  } from "$lib/types";

  let settings = $state<ProjectGovernanceSettings | null>(null);
  let loading = $state(true);
  let saving = $state(false);
  let error = $state<string | null>(null);
  let success = $state(false);

  let projects = $state<ProjectListItem[]>([]);
  let roles = $state<RoleListItem[]>([]);
  let selectedProjectId = $state("");
  let loadingConfig = $state(false);
  let configError = $state<string | null>(null);

  let phaseOptions = $state<ProjectPhase[]>([]);
  let dependencyRows = $state<ProjectPhaseDependency[]>([]);
  let approvalRuleRows = $state<ProjectMilestoneApprovalRule[]>([]);

  let creatingDependency = $state(false);
  let creatingRule = $state(false);

  let dependencyForm = $state({
    predecessor_phase: "",
    successor_phase: "",
    dependency_type: "fs" as "fs" | "ss" | "ff" | "sf",
    lag_days: "0",
    notes: "",
  });

  let approvalRuleForm = $state({
    phase: "",
    required_role: "",
    sequence_order: "10",
    is_mandatory: true,
    is_active: true,
    notes: "",
  });

  const selectedProjectName = $derived(
    projects.find((project) => String(project.id) === selectedProjectId)?.name ?? "",
  );

  onMount(async () => {
    await Promise.all([
      loadSettings(),
      loadProjectOptions(),
      loadRoleOptions(),
    ]);
  });

  async function fetchCollection<T>(
    path: string,
    params: Record<string, string> = {},
  ): Promise<T[]> {
    const rows: T[] = [];
    let page = 1;
    while (true) {
      const payload = await api.get<PaginatedResponse<T> | T[]>(path, {
        ...params,
        page: String(page),
        page_size: params.page_size ?? "200",
      });
      if (Array.isArray(payload)) {
        if (page === 1) return payload;
        rows.push(...payload);
        break;
      }
      rows.push(...payload.results);
      if (!payload.next || payload.results.length === 0) break;
      page += 1;
    }
    return rows;
  }

  async function loadSettings() {
    loading = true;
    error = null;
    try {
      settings = await api.get("/settings/project-governance/");
    } catch (err: any) {
      error = err.response?.data?.detail || "Failed to load project governance settings";
    } finally {
      loading = false;
    }
  }

  async function loadProjectOptions() {
    try {
      projects = await fetchCollection<ProjectListItem>("/projects/", { ordering: "name" });
    } catch {
      projects = [];
    }
  }

  async function loadRoleOptions() {
    try {
      roles = await fetchCollection<RoleListItem>("/settings/roles/", { ordering: "name" });
    } catch {
      roles = [];
    }
  }

  async function loadProjectConfiguration(projectId: number) {
    loadingConfig = true;
    configError = null;
    try {
      const [phases, dependencies, approvalRules] = await Promise.all([
        fetchCollection<ProjectPhase>(`/projects/${projectId}/phases/`, { ordering: "sort_order" }),
        api.get<ProjectPhaseDependency[]>(`/projects/${projectId}/phase-dependencies/`),
        api.get<ProjectMilestoneApprovalRule[]>(`/projects/${projectId}/milestone-approval-rules/`),
      ]);
      phaseOptions = phases;
      dependencyRows = dependencies;
      approvalRuleRows = approvalRules;
    } catch (err: any) {
      phaseOptions = [];
      dependencyRows = [];
      approvalRuleRows = [];
      configError = err.response?.data?.detail || "Failed to load schedule configuration.";
    } finally {
      loadingConfig = false;
    }
  }

  async function createDependency() {
    if (!selectedProjectId) return;
    if (!dependencyForm.predecessor_phase || !dependencyForm.successor_phase) {
      configError = "Select both predecessor and successor phases.";
      return;
    }
    creatingDependency = true;
    configError = null;
    try {
      await api.post(`/projects/${selectedProjectId}/phase-dependencies/`, {
        predecessor_phase: Number(dependencyForm.predecessor_phase),
        successor_phase: Number(dependencyForm.successor_phase),
        dependency_type: dependencyForm.dependency_type,
        lag_days: Number(dependencyForm.lag_days || "0"),
        notes: dependencyForm.notes,
      });
      dependencyForm = {
        predecessor_phase: "",
        successor_phase: "",
        dependency_type: "fs",
        lag_days: "0",
        notes: "",
      };
      await loadProjectConfiguration(Number(selectedProjectId));
    } catch (err: any) {
      configError = err.response?.data?.detail || "Could not create phase dependency.";
    } finally {
      creatingDependency = false;
    }
  }

  async function deleteDependency(id: number) {
    if (!selectedProjectId) return;
    try {
      await api.delete(`/projects/${selectedProjectId}/phase-dependencies/${id}/`);
      await loadProjectConfiguration(Number(selectedProjectId));
    } catch (err: any) {
      configError = err.response?.data?.detail || "Could not delete phase dependency.";
    }
  }

  async function createApprovalRule() {
    if (!selectedProjectId) return;
    if (!approvalRuleForm.required_role) {
      configError = "Select a required role for the approval rule.";
      return;
    }
    creatingRule = true;
    configError = null;
    try {
      await api.post(`/projects/${selectedProjectId}/milestone-approval-rules/`, {
        phase: approvalRuleForm.phase ? Number(approvalRuleForm.phase) : null,
        required_role: Number(approvalRuleForm.required_role),
        sequence_order: Number(approvalRuleForm.sequence_order || "10"),
        is_mandatory: approvalRuleForm.is_mandatory,
        is_active: approvalRuleForm.is_active,
        notes: approvalRuleForm.notes,
      });
      approvalRuleForm = {
        phase: "",
        required_role: "",
        sequence_order: "10",
        is_mandatory: true,
        is_active: true,
        notes: "",
      };
      await loadProjectConfiguration(Number(selectedProjectId));
    } catch (err: any) {
      configError = err.response?.data?.detail || "Could not create milestone approval rule.";
    } finally {
      creatingRule = false;
    }
  }

  async function deleteApprovalRule(id: number) {
    if (!selectedProjectId) return;
    try {
      await api.delete(`/projects/${selectedProjectId}/milestone-approval-rules/${id}/`);
      await loadProjectConfiguration(Number(selectedProjectId));
    } catch (err: any) {
      configError = err.response?.data?.detail || "Could not delete approval rule.";
    }
  }

  async function save() {
    if (!settings) return;
    saving = true;
    error = null;
    success = false;
    try {
      settings = await api.patch("/settings/project-governance/", {
        stage_gate_enforcement_enabled: settings.stage_gate_enforcement_enabled,
        require_template_selection: settings.require_template_selection,
        risk_assessment_mandatory: settings.risk_assessment_mandatory,
      });
      success = true;
      setTimeout(() => (success = false), 3000);
    } catch (err: any) {
      error = err.response?.data?.detail || "Failed to save settings";
    } finally {
      saving = false;
    }
  }

  $effect(() => {
    const projectId = Number(selectedProjectId);
    if (!projectId) {
      phaseOptions = [];
      dependencyRows = [];
      approvalRuleRows = [];
      return;
    }
    loadProjectConfiguration(projectId);
  });
</script>

<div class="max-w-4xl">
  <div class="mb-8">
    <h1 class="text-2xl font-bold text-neutral-800 mb-2">Project Governance</h1>
    <p class="text-sm text-neutral-500">
      Configure project governance rules, template requirements, and risk assessment policies.
    </p>
  </div>

  {#if loading}
    <div class="bg-white rounded-xl border border-neutral-200 p-12 text-center">
      <div class="inline-block w-8 h-8 border-4 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
    </div>
  {:else if settings}
    <form class="space-y-8" onsubmit={(event) => { event.preventDefault(); save(); }}>
      <!-- Settings Card -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6">
        <h2 class="text-base font-semibold text-neutral-800 mb-6">Governance Controls</h2>

        <div class="space-y-6">
          <!-- Stage-Gate Enforcement -->
          <label class="flex items-start gap-4 cursor-pointer group">
            <input
              type="checkbox"
              bind:checked={settings.stage_gate_enforcement_enabled}
              class="mt-0.5 w-4 h-4 text-neutral-800 border-neutral-300 rounded focus:ring-neutral-800 focus:ring-offset-0"
            />
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-neutral-800 group-hover:text-neutral-700">
                Enforce stage-gate rules
              </p>
              <p class="text-sm text-neutral-500 mt-1">
                Require projects to pass stage-gate checkpoints before progressing to the next phase.
              </p>
            </div>
          </label>

          <!-- Template Selection Required -->
          <label class="flex items-start gap-4 cursor-pointer group">
            <input
              type="checkbox"
              bind:checked={settings.require_template_selection}
              class="mt-0.5 w-4 h-4 text-neutral-800 border-neutral-300 rounded focus:ring-neutral-800 focus:ring-offset-0"
            />
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-neutral-800 group-hover:text-neutral-700">
                Require template selection
              </p>
              <p class="text-sm text-neutral-500 mt-1">
                Require users to select a project template when creating a new project.
              </p>
            </div>
          </label>

          <!-- Risk Assessment Mandatory -->
          <label class="flex items-start gap-4 cursor-pointer group">
            <input
              type="checkbox"
              bind:checked={settings.risk_assessment_mandatory}
              class="mt-0.5 w-4 h-4 text-neutral-800 border-neutral-300 rounded focus:ring-neutral-800 focus:ring-offset-0"
            />
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-neutral-800 group-hover:text-neutral-700">
                Risk assessment mandatory
              </p>
              <p class="text-sm text-neutral-500 mt-1">
                Require project managers to complete risk assessments for all projects.
              </p>
            </div>
          </label>
        </div>
      </div>

      <!-- Quick Links -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6">
        <h2 class="text-base font-semibold text-neutral-800 mb-4">Related Settings</h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <a
            href="/settings/project-templates"
            class="flex items-center gap-3 px-4 py-3 border border-neutral-200 rounded-lg hover:border-neutral-800 hover:bg-neutral-50 transition-all group"
          >
            <svg class="w-5 h-5 text-neutral-400 group-hover:text-neutral-800" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
            </svg>
            <div class="flex-1 text-left">
              <p class="text-sm font-medium text-neutral-800">Project Templates</p>
              <p class="text-xs text-neutral-500">Manage development templates</p>
            </div>
          </a>

          <a
            href="/settings/stage-gates"
            class="flex items-center gap-3 px-4 py-3 border border-neutral-200 rounded-lg hover:border-neutral-800 hover:bg-neutral-50 transition-all group"
          >
            <svg class="w-5 h-5 text-neutral-400 group-hover:text-neutral-800" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
            </svg>
            <div class="flex-1 text-left">
              <p class="text-sm font-medium text-neutral-800">Stage Gates</p>
              <p class="text-xs text-neutral-500">Configure approval checkpoints</p>
            </div>
          </a>

          <a
            href="/settings/risk-framework"
            class="flex items-center gap-3 px-4 py-3 border border-neutral-200 rounded-lg hover:border-neutral-800 hover:bg-neutral-50 transition-all group"
          >
            <svg class="w-5 h-5 text-neutral-400 group-hover:text-neutral-800" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
            </svg>
            <div class="flex-1 text-left">
              <p class="text-sm font-medium text-neutral-800">Risk Framework</p>
              <p class="text-xs text-neutral-500">Manage risk categories & rules</p>
            </div>
          </a>
        </div>
      </div>

      <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-6">
        <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 class="text-base font-semibold text-neutral-800">Schedule Configuration (Settings Layer)</h2>
            <p class="mt-1 text-sm text-neutral-500">
              Configure dependency structure and milestone approval schema outside execution screens.
            </p>
          </div>
          <div class="sm:w-80">
            <!-- svelte-ignore a11y_label_has_associated_control -->
            <label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-neutral-500">Project Scope</label>
            <select
              bind:value={selectedProjectId}
              class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-800"
            >
              <option value="">Select project...</option>
              {#each projects as project}
                <option value={String(project.id)}>{project.name}</option>
              {/each}
            </select>
          </div>
        </div>

        {#if !selectedProjectId}
          <div class="rounded-lg border border-dashed border-neutral-300 bg-neutral-50 px-4 py-6 text-sm text-neutral-500">
            Select a project to manage dependency and approval configuration.
          </div>
        {:else if loadingConfig}
          <div class="flex items-center justify-center py-10">
            <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-800"></div>
          </div>
        {:else}
          <div class="rounded-lg border border-neutral-200 bg-neutral-50 px-4 py-3 text-xs text-neutral-600">
            Applying configuration for <span class="font-semibold text-neutral-800">{selectedProjectName}</span>.
          </div>

          <div class="grid grid-cols-1 gap-6 xl:grid-cols-2">
            <section class="rounded-xl border border-neutral-200 bg-white p-4">
              <h3 class="text-sm font-semibold text-neutral-800">Phase Dependency Schema</h3>
              <p class="mt-1 text-xs text-neutral-500">Defines predecessor/successor relationships for critical-path computation.</p>

              <div class="mt-4 grid grid-cols-1 gap-3">
                <select
                  bind:value={dependencyForm.predecessor_phase}
                  class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"
                >
                  <option value="">Predecessor phase</option>
                  {#each phaseOptions as phase}
                    <option value={String(phase.id)}>{phase.name}</option>
                  {/each}
                </select>
                <select
                  bind:value={dependencyForm.successor_phase}
                  class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"
                >
                  <option value="">Successor phase</option>
                  {#each phaseOptions as phase}
                    <option value={String(phase.id)}>{phase.name}</option>
                  {/each}
                </select>
                <div class="grid grid-cols-2 gap-3">
                  <select
                    bind:value={dependencyForm.dependency_type}
                    class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"
                  >
                    <option value="fs">Finish to Start</option>
                    <option value="ss">Start to Start</option>
                    <option value="ff">Finish to Finish</option>
                    <option value="sf">Start to Finish</option>
                  </select>
                  <input
                    type="number"
                    bind:value={dependencyForm.lag_days}
                    class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"
                    placeholder="Lag days"
                  />
                </div>
                <input
                  type="text"
                  bind:value={dependencyForm.notes}
                  class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"
                  placeholder="Notes (optional)"
                />
                <button
                  type="button"
                  onclick={createDependency}
                  disabled={creatingDependency}
                  class="rounded-lg bg-neutral-800 px-3 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
                >
                  {creatingDependency ? "Saving..." : "Add Dependency"}
                </button>
              </div>

              <div class="mt-4 overflow-x-auto">
                <table class="w-full min-w-[420px] text-xs">
                  <thead>
                    <tr class="border-b border-neutral-100 text-neutral-500">
                      <th class="py-2 text-left font-semibold">Predecessor</th>
                      <th class="py-2 text-left font-semibold">Successor</th>
                      <th class="py-2 text-left font-semibold">Type</th>
                      <th class="py-2 text-right font-semibold">Action</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-neutral-100">
                    {#if dependencyRows.length === 0}
                      <tr>
                        <td colspan="4" class="py-4 text-center text-neutral-400">No dependencies configured.</td>
                      </tr>
                    {:else}
                      {#each dependencyRows as row (row.id)}
                        <tr>
                          <td class="py-2 text-neutral-700">{row.predecessor_phase_name}</td>
                          <td class="py-2 text-neutral-700">{row.successor_phase_name}</td>
                          <td class="py-2 text-neutral-500 uppercase">{row.dependency_type} ({row.lag_days})</td>
                          <td class="py-2 text-right">
                            <button
                              type="button"
                              onclick={() => deleteDependency(row.id)}
                              class="rounded-md border border-rose-200 px-2 py-1 text-[11px] font-medium text-rose-600 hover:bg-rose-50"
                            >
                              Remove
                            </button>
                          </td>
                        </tr>
                      {/each}
                    {/if}
                  </tbody>
                </table>
              </div>
            </section>

            <section class="rounded-xl border border-neutral-200 bg-white p-4">
              <h3 class="text-sm font-semibold text-neutral-800">Milestone Approval Schema</h3>
              <p class="mt-1 text-xs text-neutral-500">Defines role-based approval chain used in operations.</p>

              <div class="mt-4 grid grid-cols-1 gap-3">
                <select
                  bind:value={approvalRuleForm.phase}
                  class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"
                >
                  <option value="">All phases</option>
                  {#each phaseOptions as phase}
                    <option value={String(phase.id)}>{phase.name}</option>
                  {/each}
                </select>
                <select
                  bind:value={approvalRuleForm.required_role}
                  class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"
                >
                  <option value="">Required role</option>
                  {#each roles as role}
                    <option value={String(role.id)}>{role.name}</option>
                  {/each}
                </select>
                <input
                  type="number"
                  bind:value={approvalRuleForm.sequence_order}
                  class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"
                  placeholder="Sequence order"
                />
                <div class="grid grid-cols-2 gap-3 text-xs text-neutral-600">
                  <label class="flex items-center gap-2">
                    <input type="checkbox" bind:checked={approvalRuleForm.is_mandatory} />
                    Mandatory
                  </label>
                  <label class="flex items-center gap-2">
                    <input type="checkbox" bind:checked={approvalRuleForm.is_active} />
                    Active
                  </label>
                </div>
                <input
                  type="text"
                  bind:value={approvalRuleForm.notes}
                  class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"
                  placeholder="Notes (optional)"
                />
                <button
                  type="button"
                  onclick={createApprovalRule}
                  disabled={creatingRule}
                  class="rounded-lg bg-neutral-800 px-3 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
                >
                  {creatingRule ? "Saving..." : "Add Approval Rule"}
                </button>
              </div>

              <div class="mt-4 overflow-x-auto">
                <table class="w-full min-w-[420px] text-xs">
                  <thead>
                    <tr class="border-b border-neutral-100 text-neutral-500">
                      <th class="py-2 text-left font-semibold">Phase</th>
                      <th class="py-2 text-left font-semibold">Role</th>
                      <th class="py-2 text-left font-semibold">Seq.</th>
                      <th class="py-2 text-right font-semibold">Action</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-neutral-100">
                    {#if approvalRuleRows.length === 0}
                      <tr>
                        <td colspan="4" class="py-4 text-center text-neutral-400">No approval rules configured.</td>
                      </tr>
                    {:else}
                      {#each approvalRuleRows as row (row.id)}
                        <tr>
                          <td class="py-2 text-neutral-700">{row.phase_name ?? "All phases"}</td>
                          <td class="py-2 text-neutral-700">{row.required_role_name}</td>
                          <td class="py-2 text-neutral-500 tabular-nums">{row.sequence_order}</td>
                          <td class="py-2 text-right">
                            <button
                              type="button"
                              onclick={() => deleteApprovalRule(row.id)}
                              class="rounded-md border border-rose-200 px-2 py-1 text-[11px] font-medium text-rose-600 hover:bg-rose-50"
                            >
                              Remove
                            </button>
                          </td>
                        </tr>
                      {/each}
                    {/if}
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        {/if}

        {#if configError}
          <div class="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">
            {configError}
          </div>
        {/if}
      </div>

      <!-- Action Buttons -->
      <div class="flex items-center justify-between">
        <div class="text-xs text-neutral-500">
          {#if settings.updated_at}
            Last updated: {new Date(settings.updated_at).toLocaleString()}
          {/if}
        </div>
        <div class="flex items-center gap-3">
          {#if success}
            <div class="flex items-center gap-2 text-sm text-green-700">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
              </svg>
              Settings saved
            </div>
          {/if}
          <button
            type="submit"
            disabled={saving}
            class="px-6 py-2.5 bg-neutral-800 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>

      {#if error}
        <div class="bg-red-50 border border-red-200 rounded-lg p-4">
          <p class="text-sm text-red-900">{error}</p>
        </div>
      {/if}
    </form>
  {/if}
</div>

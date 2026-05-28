<script lang="ts">
  import { onMount } from "svelte";
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import type {
    ConstructionSchedule,
    ConstructionScheduleResponse,
    ConstructionScheduleSectionNotes,
    ConstructionScheduleTimelineSections,
  } from "$lib/types";

  const defaultSectionNotes: ConstructionScheduleSectionNotes = {
    master_schedule: "",
    phase_schedules: "",
    lookahead_schedules: "",
    task_dependencies: "",
    critical_path: "",
    resource_assignments: "",
  };

  const defaultTimelineSections: ConstructionScheduleTimelineSections = {
    project_manager: "",
    task_assignees: "",
    site_workers: "",
  };

  let loading = $state(true);
  let refreshing = $state(false);
  let saving = $state(false);
  let error = $state("");

  let payload = $state<ConstructionScheduleResponse | null>(null);
  let selectedProject = $state("");
  let lookaheadWindowDays = $state(21);
  let notes = $state("");
  let sectionNotes = $state<ConstructionScheduleSectionNotes>({ ...defaultSectionNotes });
  let timelineSections = $state<ConstructionScheduleTimelineSections>({ ...defaultTimelineSections });

  function hydrateForm(schedule: ConstructionSchedule | null) {
    if (!schedule) {
      lookaheadWindowDays = 21;
      notes = "";
      sectionNotes = { ...defaultSectionNotes };
      timelineSections = { ...defaultTimelineSections };
      return;
    }

    lookaheadWindowDays = schedule.lookahead_window_days;
    notes = schedule.notes ?? "";
    sectionNotes = {
      ...defaultSectionNotes,
      ...schedule.section_notes,
    };
    timelineSections = {
      ...defaultTimelineSections,
      ...schedule.timeline_sections,
    };
  }

  function fmtDate(value: string | null): string {
    if (!value) return "--";
    const parsed = new Date(`${value}T00:00:00`);
    if (Number.isNaN(parsed.getTime())) return value;
    return parsed.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  function fmtStatus(value: string): string {
    return value
      .split("_")
      .map((chunk) => chunk.charAt(0).toUpperCase() + chunk.slice(1))
      .join(" ");
  }

  function statusPillClass(status: string): string {
    if (status === "completed") return "bg-emerald-100 text-emerald-800 border-emerald-200";
    if (status === "in_progress") return "bg-blue-100 text-blue-800 border-blue-200";
    if (status === "blocked") return "bg-rose-100 text-rose-800 border-rose-200";
    if (status === "critical") return "bg-rose-100 text-rose-800 border-rose-200";
    if (status === "high") return "bg-amber-100 text-amber-800 border-amber-200";
    if (status === "medium") return "bg-yellow-100 text-yellow-800 border-yellow-200";
    return "bg-neutral-100 text-neutral-700 border-neutral-200";
  }

  function buildParams(): Record<string, string> {
    const params: Record<string, string> = {};
    if (selectedProject) {
      params.project = selectedProject;
    }
    return params;
  }

  async function fetchSchedule(silent = false) {
    if (silent) {
      refreshing = true;
    } else {
      loading = true;
    }
    error = "";

    try {
      const res = await api.get<ConstructionScheduleResponse>(
        "/projects/construction/schedule/",
        buildParams(),
      );
      payload = res;
      selectedProject = res.filters.project ? String(res.filters.project) : "";
      hydrateForm(res.schedule);
      if (silent) toast.success("Refreshed", "Construction schedule data loaded.");
    } catch {
      payload = null;
      error = "Could not load Construction Schedule.";
      if (silent) toast.error("Load failed", "Could not load construction schedule.");
    } finally {
      loading = false;
      refreshing = false;
    }
  }

  async function saveChanges() {
    if (!selectedProject) {
      toast.error("Project required", "Select a project before saving schedule updates.");
      return;
    }

    saving = true;
    error = "";
    try {
      const res = await api.patch<{ schedule: ConstructionSchedule }>(
        "/projects/construction/schedule/",
        {
          project: Number(selectedProject),
          lookahead_window_days: lookaheadWindowDays,
          notes,
          section_notes: sectionNotes,
          timeline_sections: timelineSections,
        },
      );

      if (payload) {
        payload = {
          ...payload,
          filters: { project: Number(selectedProject) },
          schedule: res.schedule,
        };
      }
      hydrateForm(res.schedule);
      toast.success("Construction schedule saved", "Timeline updates have been recorded.");
    } catch {
      error = "Could not save Construction Schedule.";
      toast.error("Save failed", "Could not save construction schedule updates.");
    } finally {
      saving = false;
    }
  }

  onMount(() => {
    fetchSchedule();
  });

  const schedule = $derived(payload?.schedule ?? null);
  const phaseRows = $derived(schedule?.phase_schedules ?? []);
  const lookaheadRows = $derived(schedule?.lookahead_schedules.tasks ?? []);
  const dependencyRows = $derived(schedule?.task_dependencies ?? []);
  const criticalPathRows = $derived(schedule?.critical_path.phases ?? []);
  const examplePhases = $derived(schedule?.example_phases ?? []);
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
  </div>
{:else if error && !payload}
  <div class="rounded-xl border border-red-200 bg-red-50 px-5 py-4">
    <p class="text-sm font-medium text-red-700">{error}</p>
  </div>
{:else}
  <div class="space-y-6">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div class="flex flex-wrap items-start justify-between gap-4 w-full">
        <div>
          <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-green-500">Construction</p>
          <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Construction Schedule</h1>
          <p class="mt-1 text-sm text-neutral-500">Execution timeline with dependencies, critical path, and resource links.</p>
        </div>
        <button
          onclick={() => fetchSchedule(true)}
          class="rounded-lg border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
        >
          {refreshing ? "Refreshing..." : "Refresh"}
        </button>
      </div>
    </div>

    <div class="rounded-xl border border-neutral-200 bg-white p-4">
      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
        <label class="text-xs text-neutral-500">
          Project
          <select
            bind:value={selectedProject}
            class="mt-1 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
          >
            <option value="">Select project</option>
            {#each payload?.projects ?? [] as project}
              <option value={String(project.id)}>{project.name}</option>
            {/each}
          </select>
        </label>

        <label class="text-xs text-neutral-500">
          Lookahead Window (days)
          <input
            bind:value={lookaheadWindowDays}
            type="number"
            min="7"
            max="90"
            class="mt-1 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
          />
        </label>

        <div class="flex items-end gap-2">
          <button
            onclick={() => fetchSchedule(true)}
            class="flex-1 rounded-lg bg-neutral-900 px-3 py-2 text-sm font-medium text-white hover:bg-neutral-800"
          >
            Apply
          </button>
        </div>

        <div class="flex items-end gap-2">
          <button
            onclick={saveChanges}
            disabled={saving || !selectedProject}
            class="flex-1 rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save"}
          </button>
        </div>
      </div>
    </div>

    {#if schedule}
      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
        <div class="rounded-xl border border-sky-200 bg-sky-100 p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-sky-900">Task Completion</p>
          <p class="mt-1 text-xl font-bold text-sky-950 tabular-nums">
            {schedule.master_schedule.task_completion_percent.toFixed(1)}%
          </p>
        </div>
        <div class="rounded-xl border border-emerald-200 bg-emerald-100 p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-emerald-900">Critical Phases</p>
          <p class="mt-1 text-xl font-bold text-emerald-950 tabular-nums">{schedule.master_schedule.critical_phase_count}</p>
        </div>
        <div class="rounded-xl border border-amber-200 bg-amber-100 p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-amber-900">Lookahead Tasks</p>
          <p class="mt-1 text-xl font-bold text-amber-950 tabular-nums">{schedule.lookahead_schedules.tasks.length}</p>
        </div>
        <div class="rounded-xl border border-rose-200 bg-rose-100 p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-rose-900">Overdue Open Tasks</p>
          <p class="mt-1 text-xl font-bold text-rose-950 tabular-nums">{schedule.lookahead_schedules.overdue_open_tasks}</p>
        </div>
      </div>

      <div class="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <section class="rounded-xl border border-neutral-200 bg-white p-5">
          <h3 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Master Schedule</h3>
          <div class="mt-3 grid grid-cols-2 gap-3 text-sm">
            <p><span class="text-neutral-500">Planned Start:</span> <span class="font-medium text-neutral-900">{fmtDate(schedule.master_schedule.planned_start_date)}</span></p>
            <p><span class="text-neutral-500">Planned End:</span> <span class="font-medium text-neutral-900">{fmtDate(schedule.master_schedule.planned_end_date)}</span></p>
            <p><span class="text-neutral-500">Actual End:</span> <span class="font-medium text-neutral-900">{fmtDate(schedule.master_schedule.actual_end_date)}</span></p>
            <p><span class="text-neutral-500">Duration:</span> <span class="font-medium text-neutral-900 tabular-nums">{schedule.master_schedule.duration_days ?? "--"}</span></p>
            <p><span class="text-neutral-500">Phases:</span> <span class="font-medium text-neutral-900 tabular-nums">{schedule.master_schedule.phase_count}</span></p>
            <p><span class="text-neutral-500">Tasks:</span> <span class="font-medium text-neutral-900 tabular-nums">{schedule.master_schedule.task_count}</span></p>
          </div>
          <label class="mt-4 block text-xs text-neutral-500">
            Master schedule notes
            <textarea
              bind:value={sectionNotes.master_schedule}
              rows={3}
              class="mt-1 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
              placeholder="Add master schedule notes..."
            ></textarea>
          </label>
        </section>

        <section class="rounded-xl border border-neutral-200 bg-white p-5">
          <h3 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Linked Inputs</h3>
          <div class="mt-3 space-y-3 text-sm text-neutral-700">
            <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
              <p class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Procurement Deliveries</p>
              <p class="mt-1">Upcoming: <span class="font-semibold text-neutral-900 tabular-nums">{schedule.linked_sources.procurement_deliveries.upcoming}</span></p>
              <p>Overdue: <span class="font-semibold text-neutral-900 tabular-nums">{schedule.linked_sources.procurement_deliveries.overdue}</span></p>
              <p>Received: <span class="font-semibold text-neutral-900 tabular-nums">{schedule.linked_sources.procurement_deliveries.received}</span></p>
            </div>
            <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
              <p class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Labour Availability</p>
              <p class="mt-1">Active employees: <span class="font-semibold text-neutral-900 tabular-nums">{schedule.linked_sources.labour_availability.active_employees}</span></p>
              <p>Assigned to schedule: <span class="font-semibold text-neutral-900 tabular-nums">{schedule.linked_sources.labour_availability.assigned_to_schedule}</span></p>
              <p>Unassigned open tasks: <span class="font-semibold text-neutral-900 tabular-nums">{schedule.linked_sources.labour_availability.unassigned_open_tasks}</span></p>
            </div>
            <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
              <p class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Equipment Scheduling</p>
              <p class="mt-1">Allocated: <span class="font-semibold text-neutral-900 tabular-nums">{schedule.linked_sources.equipment_scheduling.allocated}</span></p>
              <p>Pending: <span class="font-semibold text-neutral-900 tabular-nums">{schedule.linked_sources.equipment_scheduling.pending}</span></p>
            </div>
          </div>
        </section>
      </div>

      <section class="rounded-xl border border-neutral-200 bg-white p-5">
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Phase Schedules</h3>
          <p class="text-xs text-neutral-500">{phaseRows.length} phase rows</p>
        </div>
        <div class="mt-4 overflow-x-auto">
          <table class="w-full min-w-[980px] text-sm">
            <thead>
              <tr class="border-b border-neutral-100 bg-neutral-50/80">
                <th class="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Phase</th>
                <th class="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Status</th>
                <th class="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Dates</th>
                <th class="px-4 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Tasks</th>
                <th class="px-4 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Planned</th>
                <th class="px-4 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Actual</th>
                <th class="px-4 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Progress</th>
                <th class="px-4 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Critical</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each phaseRows as row}
                <tr>
                  <td class="px-4 py-3 text-neutral-900 font-medium">{row.phase_name}</td>
                  <td class="px-4 py-3">
                    <span class={`inline-flex rounded-full border px-2 py-0.5 text-xs font-semibold ${statusPillClass(row.status)}`}>
                      {fmtStatus(row.status)}
                    </span>
                  </td>
                  <td class="px-4 py-3 text-neutral-600">
                    <p>{fmtDate(row.planned_start_date)} - {fmtDate(row.planned_end_date)}</p>
                    <p class="text-xs text-neutral-500">Duration: {row.duration_days ?? "--"} days</p>
                  </td>
                  <td class="px-4 py-3 text-right tabular-nums text-neutral-700">{row.task_count}</td>
                  <td class="px-4 py-3 text-right tabular-nums text-neutral-700">{currency.formatCompact(row.planned_budget)}</td>
                  <td class="px-4 py-3 text-right tabular-nums text-neutral-700">{currency.formatCompact(row.actual_cost)}</td>
                  <td class="px-4 py-3 text-right tabular-nums font-semibold text-neutral-900">{row.progress_percent.toFixed(1)}%</td>
                  <td class="px-4 py-3 text-right">
                    <span class={`inline-flex rounded-full border px-2 py-0.5 text-xs font-semibold ${row.is_critical_path ? "bg-rose-100 text-rose-800 border-rose-200" : "bg-neutral-100 text-neutral-600 border-neutral-200"}`}>
                      {row.is_critical_path ? `Yes (${row.slack_days}d slack)` : "No"}
                    </span>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
        <label class="mt-4 block text-xs text-neutral-500">
          Phase schedule notes
          <textarea
            bind:value={sectionNotes.phase_schedules}
            rows={3}
            class="mt-1 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
            placeholder="Add phase schedule notes..."
          ></textarea>
        </label>
      </section>

      <section class="rounded-xl border border-neutral-200 bg-white p-5">
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Lookahead Schedules</h3>
          <p class="text-xs text-neutral-500">Window: {schedule.lookahead_schedules.window_days} days</p>
        </div>
        {#if lookaheadRows.length === 0}
          <p class="mt-4 text-sm text-neutral-500">No tasks in the active lookahead window.</p>
        {:else}
          <div class="mt-4 overflow-x-auto">
            <table class="w-full min-w-[860px] text-sm">
              <thead>
                <tr class="border-b border-neutral-100 bg-neutral-50/80">
                  <th class="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Task</th>
                  <th class="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Phase</th>
                  <th class="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Assignee</th>
                  <th class="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Status</th>
                  <th class="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Due</th>
                  <th class="px-4 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Dependencies</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100">
                {#each lookaheadRows as row}
                  <tr>
                    <td class="px-4 py-3 text-neutral-900 font-medium">{row.task_name}</td>
                    <td class="px-4 py-3 text-neutral-600">{row.phase_name}</td>
                    <td class="px-4 py-3 text-neutral-600">{row.assignee}</td>
                    <td class="px-4 py-3">
                      <span class={`inline-flex rounded-full border px-2 py-0.5 text-xs font-semibold ${statusPillClass(row.status)}`}>
                        {fmtStatus(row.status)}
                      </span>
                    </td>
                    <td class="px-4 py-3 text-neutral-700">{fmtDate(row.due_date)}</td>
                    <td class="px-4 py-3 text-right tabular-nums text-neutral-700">{row.dependency_count}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
        <label class="mt-4 block text-xs text-neutral-500">
          Lookahead notes
          <textarea
            bind:value={sectionNotes.lookahead_schedules}
            rows={3}
            class="mt-1 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
            placeholder="Add lookahead notes..."
          ></textarea>
        </label>
      </section>

      <div class="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <section class="rounded-xl border border-neutral-200 bg-white p-5">
          <h3 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Task Dependencies</h3>
          {#if dependencyRows.length === 0}
            <p class="mt-3 text-sm text-neutral-500">No dependencies captured yet.</p>
          {:else}
            <div class="mt-3 max-h-64 overflow-auto rounded-lg border border-neutral-200">
              <table class="w-full text-sm">
                <thead class="bg-neutral-50">
                  <tr>
                    <th class="px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Scope</th>
                    <th class="px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">From</th>
                    <th class="px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">To</th>
                    <th class="px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Type</th>
                    <th class="px-3 py-2 text-right text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Lag (days)</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-neutral-100">
                  {#each dependencyRows as row}
                    <tr>
                      <td class="px-3 py-2 text-neutral-600">{row.scope}</td>
                      <td class="px-3 py-2 text-neutral-900">{row.from}</td>
                      <td class="px-3 py-2 text-neutral-900">{row.to}</td>
                      <td class="px-3 py-2 text-neutral-600 uppercase">{row.dependency_type}</td>
                      <td class="px-3 py-2 text-right tabular-nums text-neutral-700">{row.lag_days}</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {/if}
          <label class="mt-4 block text-xs text-neutral-500">
            Dependency notes
            <textarea
              bind:value={sectionNotes.task_dependencies}
              rows={3}
              class="mt-1 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
              placeholder="Add task dependency notes..."
            ></textarea>
          </label>
        </section>

        <section class="rounded-xl border border-neutral-200 bg-white p-5">
          <h3 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Critical Path</h3>
          {#if criticalPathRows.length === 0}
            <p class="mt-3 text-sm text-neutral-500">No critical path computed yet.</p>
          {:else}
            <div class="mt-3 space-y-2">
              {#each criticalPathRows as row}
                <div class="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-900">
                  <p class="font-semibold">{row.phase_name}</p>
                  <p class="text-xs">Slack: {row.slack_days} day(s)</p>
                </div>
              {/each}
            </div>
          {/if}
          <p class="mt-3 text-xs text-neutral-500">
            Total critical duration: <span class="font-semibold text-neutral-700 tabular-nums">{schedule.critical_path.total_duration_days}</span> day(s)
          </p>
          <label class="mt-3 block text-xs text-neutral-500">
            Critical path notes
            <textarea
              bind:value={sectionNotes.critical_path}
              rows={3}
              class="mt-1 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
              placeholder="Add critical path notes..."
            ></textarea>
          </label>
        </section>
      </div>

      <section class="rounded-xl border border-neutral-200 bg-white p-5">
        <h3 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Example Construction Phases</h3>
        <div class="mt-3 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-2">
          {#each examplePhases as item}
            <div class={`rounded-lg border px-3 py-2 text-sm ${item.present ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-neutral-200 bg-neutral-50 text-neutral-700"}`}>
              {item.name}
            </div>
          {/each}
        </div>
      </section>

      <section class="rounded-xl border border-neutral-200 bg-white p-5">
        <h3 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Resource Assignments</h3>
        <div class="mt-3 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3 text-sm">
          <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
            <p class="text-[10px] uppercase tracking-wider text-neutral-500">Project Manager</p>
            <p class="mt-1 font-semibold text-neutral-900">{schedule.resource_assignments.project_manager || "--"}</p>
          </div>
          <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
            <p class="text-[10px] uppercase tracking-wider text-neutral-500">Assigned Users</p>
            <p class="mt-1 font-semibold text-neutral-900 tabular-nums">{schedule.resource_assignments.assigned_user_count}</p>
          </div>
          <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
            <p class="text-[10px] uppercase tracking-wider text-neutral-500">Site Workers (Latest)</p>
            <p class="mt-1 font-semibold text-neutral-900 tabular-nums">{schedule.resource_assignments.site_workers_count}</p>
          </div>
          <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
            <p class="text-[10px] uppercase tracking-wider text-neutral-500">Equipment Allocated</p>
            <p class="mt-1 font-semibold text-neutral-900 tabular-nums">{schedule.resource_assignments.equipment_allocated_count}</p>
          </div>
        </div>
        <label class="mt-4 block text-xs text-neutral-500">
          Resource assignment notes
          <textarea
            bind:value={sectionNotes.resource_assignments}
            rows={3}
            class="mt-1 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
            placeholder="Add resource assignment notes..."
          ></textarea>
        </label>
      </section>

      <section class="rounded-xl border border-neutral-200 bg-white p-5">
        <h3 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Timeline Sections</h3>
        <p class="mt-1 text-xs text-neutral-500">
          Inputs from project managers, task assignees, and site workers.
        </p>
        <div class="mt-4 grid grid-cols-1 xl:grid-cols-3 gap-3">
          <label class="text-xs text-neutral-500">
            Project Manager Updates
            <textarea
              bind:value={timelineSections.project_manager}
              rows={6}
              class="mt-1 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
              placeholder="Project manager timeline updates..."
            ></textarea>
          </label>
          <label class="text-xs text-neutral-500">
            Task Assignee Updates
            <textarea
              bind:value={timelineSections.task_assignees}
              rows={6}
              class="mt-1 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
              placeholder="Task assignee timeline updates..."
            ></textarea>
          </label>
          <label class="text-xs text-neutral-500">
            Site Worker Updates
            <textarea
              bind:value={timelineSections.site_workers}
              rows={6}
              class="mt-1 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
              placeholder="Site worker timeline updates..."
            ></textarea>
          </label>
        </div>
        <label class="mt-4 block text-xs text-neutral-500">
          General schedule notes
          <textarea
            bind:value={notes}
            rows={3}
            class="mt-1 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
            placeholder="Additional schedule notes..."
          ></textarea>
        </label>
      </section>

      <div class="flex justify-end">
        <button
          onclick={saveChanges}
          disabled={saving || !selectedProject}
          class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {saving ? "Saving..." : "Save Construction Schedule"}
        </button>
      </div>
    {:else}
      <div class="rounded-xl border border-neutral-200 bg-white px-5 py-4">
        <p class="text-sm text-neutral-600">Select a project to load Construction Schedule.</p>
      </div>
    {/if}

    {#if error}
      <div class="rounded-xl border border-red-200 bg-red-50 px-5 py-4">
        <p class="text-sm font-medium text-red-700">{error}</p>
      </div>
    {/if}
  </div>
{/if}

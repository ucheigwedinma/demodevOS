<script lang="ts">
  import { api } from "$lib/api";
  import { currency } from "$lib/stores/currency.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DrawerShell from "$lib/components/DrawerShell.svelte";
  import type {
    ProjectListItem,
    ProjectPhase,
    ProjectMilestone,
    PaginatedResponse,
  } from "$lib/types";

  let loading = $state(true);
  let projects = $state<ProjectListItem[]>([]);
  let selectedProjectId = $state("");
  let phases = $state<ProjectPhase[]>([]);

  // Detail drawer
  let detailOpen = $state(false);
  let selectedPhase = $state<ProjectPhase | null>(null);
  let phaseMilestones = $state<ProjectMilestone[]>([]);
  let detailLoading = $state(false);

  const today = new Date().toISOString().split("T")[0];

  async function fetchProjects() {
    try {
      const res = await api.get<PaginatedResponse<ProjectListItem>>("/projects/", { page_size: "200", ordering: "name" });
      projects = res.results;
      if (projects.length > 0 && !selectedProjectId) {
        selectedProjectId = String(projects[0].id);
      }
    } catch { projects = []; }
  }

  async function fetchPhases() {
    if (!selectedProjectId) { phases = []; loading = false; return; }
    loading = true;
    try {
      const res = await api.get<PaginatedResponse<ProjectPhase>>(`/projects/${selectedProjectId}/phases/`, { page_size: "100", ordering: "sort_order" });
      phases = res.results;
    } catch { phases = []; }
    loading = false;
  }

  $effect(() => { fetchProjects(); });
  $effect(() => { void selectedProjectId; fetchPhases(); });

  async function openPhaseDetail(phase: ProjectPhase) {
    selectedPhase = phase;
    detailOpen = true;
    detailLoading = true;
    try {
      const res = await api.get<PaginatedResponse<ProjectMilestone>>(`/projects/${selectedProjectId}/phases/${phase.id}/milestones/`, { page_size: "100" });
      phaseMilestones = res.results;
    } catch { phaseMilestones = []; }
    detailLoading = false;
  }

  function fmtDate(v: string | null | undefined): string {
    if (!v) return "--";
    const d = new Date(v);
    return Number.isNaN(d.getTime()) ? "--" : d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  }

  function fmtC(v: string | number | null | undefined): string {
    if (!v || v === "0.00" || v === "0") return "--";
    return currency.formatCompact(v);
  }

  function daysBetween(start: string | null, end: string | null): number | null {
    if (!start || !end) return null;
    const s = new Date(start);
    const e = new Date(end);
    if (Number.isNaN(s.getTime()) || Number.isNaN(e.getTime())) return null;
    return Math.round((e.getTime() - s.getTime()) / 86400000);
  }

  function phaseStatusColor(status: string): string {
    if (status === "completed") return "bg-emerald-500";
    if (status === "in_progress") return "bg-blue-500";
    if (status === "skipped") return "bg-neutral-300";
    return "bg-neutral-200";
  }

  function phaseVarianceLabel(phase: ProjectPhase): { text: string; color: string } {
    const target = phase.revised_end_date || phase.baseline_end_date || phase.planned_end_date;
    if (!target) return { text: "", color: "" };
    if (phase.status === "completed" && phase.actual_end_date) {
      const diff = daysBetween(target, phase.actual_end_date);
      if (diff === null) return { text: "", color: "" };
      if (diff <= 0) return { text: `${Math.abs(diff)}d early`, color: "text-emerald-600" };
      return { text: `${diff}d late`, color: "text-red-600" };
    }
    if (phase.status === "in_progress") {
      const diff = daysBetween(today, target);
      if (diff === null) return { text: "", color: "" };
      if (diff < 0) return { text: `${Math.abs(diff)}d overdue`, color: "text-red-600" };
      return { text: `${diff}d remaining`, color: "text-neutral-500" };
    }
    return { text: "", color: "" };
  }

  // Timeline calculations
  function getTimelineRange(): { minDate: Date; maxDate: Date; totalDays: number } {
    let min = new Date();
    let max = new Date();
    let hasData = false;
    for (const p of phases) {
      const start = p.actual_start_date || p.planned_start_date || p.baseline_start_date;
      const end = p.actual_end_date || p.planned_end_date || p.baseline_end_date;
      if (start) {
        const d = new Date(start);
        if (!hasData || d < min) min = d;
        hasData = true;
      }
      if (end) {
        const d = new Date(end);
        if (!hasData || d > max) max = d;
        hasData = true;
      }
    }
    if (!hasData) {
      min = new Date();
      max = new Date(min.getTime() + 365 * 86400000);
    }
    // Pad 30 days on each side
    min = new Date(min.getTime() - 30 * 86400000);
    max = new Date(max.getTime() + 30 * 86400000);
    const totalDays = Math.max(1, Math.round((max.getTime() - min.getTime()) / 86400000));
    return { minDate: min, maxDate: max, totalDays };
  }

  function barPosition(start: string | null, end: string | null, range: ReturnType<typeof getTimelineRange>): { left: string; width: string } | null {
    if (!start || !end) return null;
    const s = new Date(start);
    const e = new Date(end);
    if (Number.isNaN(s.getTime()) || Number.isNaN(e.getTime())) return null;
    const startOffset = (s.getTime() - range.minDate.getTime()) / 86400000;
    const duration = Math.max(7, (e.getTime() - s.getTime()) / 86400000);
    const left = (startOffset / range.totalDays) * 100;
    const width = (duration / range.totalDays) * 100;
    return { left: `${Math.max(0, left)}%`, width: `${Math.min(width, 100 - Math.max(0, left))}%` };
  }

  function todayPosition(range: ReturnType<typeof getTimelineRange>): string {
    const t = new Date();
    const offset = (t.getTime() - range.minDate.getTime()) / 86400000;
    return `${(offset / range.totalDays) * 100}%`;
  }

  // Summary stats
  const totalPhases = $derived(phases.length);
  const completedPhases = $derived(phases.filter(p => p.status === "completed").length);
  const inProgressPhases = $derived(phases.filter(p => p.status === "in_progress").length);
  const overallProgress = $derived(totalPhases > 0 ? Math.round(completedPhases / totalPhases * 100) : 0);
  const activePhase = $derived(phases.find(p => p.status === "in_progress"));

  const projectPulse = $derived(() => {
    if (!activePhase) return { label: "No Active Phase", color: "text-neutral-400" };
    const target = activePhase.revised_end_date || activePhase.baseline_end_date || activePhase.planned_end_date;
    if (!target) return { label: "On Track", color: "text-emerald-600" };
    const diff = daysBetween(today, target);
    if (diff === null) return { label: "On Track", color: "text-emerald-600" };
    if (diff < 0) return { label: "Behind Schedule", color: "text-red-600" };
    if (diff < 14) return { label: "At Risk", color: "text-amber-600" };
    return { label: "On Track", color: "text-emerald-600" };
  });
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">Projects</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-900">Development Schedule</h1>
      <p class="mt-1 text-sm text-neutral-500">Executive timeline — phase lifecycle, milestones, and critical path oversight.</p>
    </div>
    <select bind:value={selectedProjectId} class="rounded-lg border border-neutral-200 bg-white px-4 py-2.5 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">Select Project</option>
      {#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}
    </select>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if !selectedProjectId}
    <div class="rounded-2xl border border-neutral-200 bg-white px-6 py-14 text-center"><p class="text-sm text-neutral-500">Select a project to view its development schedule.</p></div>
  {:else if phases.length === 0}
    <div class="rounded-2xl border border-neutral-200 bg-white px-6 py-14 text-center"><p class="text-sm text-neutral-500">No phases defined for this project.</p></div>
  {:else}
    <!-- Summary HUD -->
    {@const pulse = projectPulse()}
    <div class="grid grid-cols-2 gap-4 md:grid-cols-5">
      <div class="rounded-xl border border-neutral-200 bg-white p-4 text-center">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Total Phases</p>
        <p class="mt-1 text-2xl font-bold text-neutral-900 tabular-nums">{totalPhases}</p>
      </div>
      <div class="rounded-xl border border-emerald-100 bg-emerald-50 p-4 text-center">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-emerald-700">Completed</p>
        <p class="mt-1 text-2xl font-bold text-emerald-900 tabular-nums">{completedPhases}</p>
      </div>
      <div class="rounded-xl border border-blue-100 bg-blue-50 p-4 text-center">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-blue-700">In Progress</p>
        <p class="mt-1 text-2xl font-bold text-blue-900 tabular-nums">{inProgressPhases}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white p-4 text-center">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Progress</p>
        <p class="mt-1 text-2xl font-bold text-neutral-900 tabular-nums">{overallProgress}%</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white p-4 text-center">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Project Pulse</p>
        <p class="mt-1 text-lg font-bold {pulse.color}">{pulse.label}</p>
      </div>
    </div>

    <!-- Gantt Timeline -->
    {@const range = getTimelineRange()}
    <section class="rounded-2xl border border-neutral-200 bg-white overflow-hidden">
      <div class="border-b border-neutral-200 bg-neutral-50/60 px-5 py-3">
        <h2 class="text-sm font-semibold text-neutral-900">Development Roadmap</h2>
      </div>
      <div class="overflow-x-auto">
        <div class="min-w-[700px]">
          {#each phases as phase, idx}
            {@const planned = barPosition(phase.planned_start_date || phase.baseline_start_date, phase.planned_end_date || phase.baseline_end_date, range)}
            {@const actual = barPosition(phase.actual_start_date, phase.actual_end_date || (phase.status === "in_progress" ? today : null), range)}
            {@const variance = phaseVarianceLabel(phase)}
            <div class="flex items-center border-b border-neutral-100 last:border-b-0 hover:bg-neutral-50/50 cursor-pointer" onclick={() => openPhaseDetail(phase)}>
              <!-- Phase label -->
              <div class="w-[200px] shrink-0 px-4 py-3 border-r border-neutral-100">
                <p class="text-sm font-medium text-neutral-900 truncate">{phase.name}</p>
                <div class="flex items-center gap-2 mt-0.5">
                  <span class="inline-block h-2 w-2 rounded-full {phaseStatusColor(phase.status)}"></span>
                  <span class="text-[10px] text-neutral-500 capitalize">{phase.status.replace("_", " ")}</span>
                  {#if variance.text}<span class="text-[10px] font-semibold {variance.color}">{variance.text}</span>{/if}
                </div>
              </div>
              <!-- Bar area -->
              <div class="flex-1 relative h-12 mx-2">
                <!-- Today line -->
                <div class="absolute top-0 bottom-0 w-px bg-red-400 z-10" style="left: {todayPosition(range)}">
                  {#if idx === 0}<span class="absolute -top-0.5 -translate-x-1/2 text-[8px] font-semibold text-red-500">TODAY</span>{/if}
                </div>
                <!-- Planned bar (baseline) -->
                {#if planned}
                  <div class="absolute top-1.5 h-3.5 rounded-full bg-neutral-200 opacity-60" style="left: {planned.left}; width: {planned.width}"></div>
                {/if}
                <!-- Actual bar -->
                {#if actual}
                  <div class="absolute top-5 h-3.5 rounded-full {phase.status === 'completed' ? 'bg-emerald-500' : 'bg-blue-500'}" style="left: {actual.left}; width: {actual.width}"></div>
                {/if}
              </div>
            </div>
          {/each}
        </div>
      </div>
      <div class="flex items-center gap-4 px-5 py-2.5 bg-neutral-50/60 border-t border-neutral-200 text-[10px] text-neutral-500">
        <span class="flex items-center gap-1"><span class="inline-block w-3 h-2 rounded-full bg-neutral-200 opacity-60"></span> Planned</span>
        <span class="flex items-center gap-1"><span class="inline-block w-3 h-2 rounded-full bg-blue-500"></span> Actual (In Progress)</span>
        <span class="flex items-center gap-1"><span class="inline-block w-3 h-2 rounded-full bg-emerald-500"></span> Actual (Completed)</span>
        <span class="flex items-center gap-1"><span class="inline-block w-1 h-3 bg-red-400"></span> Today</span>
      </div>
    </section>

    <!-- Phase Management Table -->
    <section class="rounded-2xl border border-neutral-200 bg-white overflow-hidden">
      <div class="border-b border-neutral-200 bg-neutral-50/60 px-5 py-3">
        <h2 class="text-sm font-semibold text-neutral-900">Phase Management</h2>
      </div>
      <div class="overflow-x-auto">
        <table class="min-w-[900px] w-full">
          <thead class="bg-neutral-50">
            <tr>
              <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Phase</th>
              <th class="px-4 py-3 text-center text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Status</th>
              <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Target Start</th>
              <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Target End</th>
              <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Actual Start</th>
              <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Actual End</th>
              <th class="px-4 py-3 text-right text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Budget</th>
              <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Lead</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each phases as phase}
              {@const variance = phaseVarianceLabel(phase)}
              <tr class="hover:bg-neutral-50 cursor-pointer" onclick={() => openPhaseDetail(phase)}>
                <td class="px-4 py-3">
                  <p class="text-sm font-medium text-neutral-900">{phase.name}</p>
                  {#if variance.text}<p class="text-[10px] font-semibold {variance.color}">{variance.text}</p>{/if}
                </td>
                <td class="px-4 py-3 text-center"><StatusBadge status={phase.status} /></td>
                <td class="px-4 py-3 text-sm text-neutral-600">{fmtDate(phase.revised_start_date || phase.baseline_start_date || phase.planned_start_date)}</td>
                <td class="px-4 py-3 text-sm text-neutral-600">{fmtDate(phase.revised_end_date || phase.baseline_end_date || phase.planned_end_date)}</td>
                <td class="px-4 py-3 text-sm text-neutral-700 font-medium">{fmtDate(phase.actual_start_date)}</td>
                <td class="px-4 py-3 text-sm text-neutral-700 font-medium">{fmtDate(phase.actual_end_date)}</td>
                <td class="px-4 py-3 text-right text-sm font-semibold tabular-nums text-neutral-900">{fmtC(phase.planned_budget)}</td>
                <td class="px-4 py-3 text-sm text-neutral-600 truncate max-w-[140px]">{phase.phase_owner_role || "--"}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>
  {/if}
</div>

<!-- ═══════════ PHASE DETAIL DRAWER ═══════════ -->
<DrawerShell open={detailOpen} title="Phase Detail" subtitle={selectedPhase?.name ?? ""} width="max-w-2xl" onclose={() => (detailOpen = false)}>
  {#if selectedPhase}
    {@const drawerVariance = phaseVarianceLabel(selectedPhase)}
    <div class="p-6 space-y-5">
      <!-- Status & Variance -->
      <div class="flex items-center gap-3">
        <StatusBadge status={selectedPhase.status} />
        {#if drawerVariance.text}<span class="text-sm font-semibold {drawerVariance.color}">{drawerVariance.text}</span>{/if}
      </div>

      <!-- Dates Grid -->
      <div class="grid grid-cols-2 gap-3 md:grid-cols-4">
        <div class="rounded-lg border border-neutral-200 p-3">
          <p class="text-[9px] font-semibold uppercase text-neutral-400">Baseline Start</p>
          <p class="mt-1 text-sm font-medium text-neutral-900">{fmtDate(selectedPhase.baseline_start_date)}</p>
        </div>
        <div class="rounded-lg border border-neutral-200 p-3">
          <p class="text-[9px] font-semibold uppercase text-neutral-400">Baseline End</p>
          <p class="mt-1 text-sm font-medium text-neutral-900">{fmtDate(selectedPhase.baseline_end_date)}</p>
        </div>
        <div class="rounded-lg border border-blue-100 bg-blue-50 p-3">
          <p class="text-[9px] font-semibold uppercase text-blue-600">Actual Start</p>
          <p class="mt-1 text-sm font-bold text-blue-900">{fmtDate(selectedPhase.actual_start_date)}</p>
        </div>
        <div class="rounded-lg border border-blue-100 bg-blue-50 p-3">
          <p class="text-[9px] font-semibold uppercase text-blue-600">Actual End</p>
          <p class="mt-1 text-sm font-bold text-blue-900">{fmtDate(selectedPhase.actual_end_date)}</p>
        </div>
      </div>

      <!-- Budget -->
      <div class="grid grid-cols-3 gap-3">
        <div class="rounded-lg border border-neutral-200 p-3 text-center">
          <p class="text-[9px] font-semibold uppercase text-neutral-400">Planned Budget</p>
          <p class="mt-1 text-lg font-bold text-neutral-900 tabular-nums">{fmtC(selectedPhase.planned_budget)}</p>
        </div>
        <div class="rounded-lg border border-neutral-200 p-3 text-center">
          <p class="text-[9px] font-semibold uppercase text-neutral-400">Actual Cost</p>
          <p class="mt-1 text-lg font-bold tabular-nums {Number(selectedPhase.actual_cost) > Number(selectedPhase.planned_budget || 0) ? 'text-red-600' : 'text-emerald-600'}">{fmtC(selectedPhase.actual_cost)}</p>
        </div>
        <div class="rounded-lg border border-neutral-200 p-3 text-center">
          <p class="text-[9px] font-semibold uppercase text-neutral-400">Variance</p>
          <p class="mt-1 text-lg font-bold tabular-nums {Number(selectedPhase.budget_variance || 0) >= 0 ? 'text-emerald-600' : 'text-red-600'}">{fmtC(selectedPhase.budget_variance)}</p>
        </div>
      </div>

      <!-- Metadata -->
      <div class="grid grid-cols-2 gap-3 text-sm">
        <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Phase Lead</p><p class="text-neutral-900">{selectedPhase.phase_owner_role || "--"}</p></div>
        <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Est. Duration</p><p class="text-neutral-900">{selectedPhase.estimated_duration_days ? `${selectedPhase.estimated_duration_days} days` : "--"}</p></div>
        <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Tasks</p><p class="text-neutral-900">{selectedPhase.completed_task_count}/{selectedPhase.task_count}</p></div>
        <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Milestones</p><p class="text-neutral-900">{selectedPhase.milestone_count}</p></div>
      </div>

      {#if selectedPhase.objective}
        <div><p class="text-[10px] font-semibold uppercase text-neutral-400 mb-1">Objective</p><p class="text-sm text-neutral-700 whitespace-pre-line">{selectedPhase.objective}</p></div>
      {/if}

      {#if selectedPhase.schedule_revision_reason}
        <div class="rounded-lg border border-amber-200 bg-amber-50 p-3">
          <p class="text-[10px] font-semibold uppercase text-amber-700 mb-1">Schedule Revision Reason</p>
          <p class="text-sm text-amber-900">{selectedPhase.schedule_revision_reason}</p>
        </div>
      {/if}

      <!-- Key Deliverables -->
      {#if selectedPhase.deliverables && selectedPhase.deliverables.length > 0}
        <div>
          <p class="text-[10px] font-semibold uppercase text-neutral-400 mb-2">Key Deliverables</p>
          <ul class="space-y-1.5">
            {#each selectedPhase.deliverables as d}
              <li class="flex items-start gap-2 text-sm">
                <span class="mt-1 inline-block h-1.5 w-1.5 rounded-full shrink-0 {d.is_mandatory ? 'bg-red-400' : 'bg-neutral-300'}"></span>
                <div>
                  <p class="font-medium text-neutral-900">{d.name}</p>
                  {#if d.description}<p class="text-xs text-neutral-500">{d.description}</p>{/if}
                </div>
              </li>
            {/each}
          </ul>
        </div>
      {/if}

      <!-- Milestones -->
      <div>
        <p class="text-[10px] font-semibold uppercase text-neutral-400 mb-2">Milestones & Approvals</p>
        {#if detailLoading}
          <div class="flex items-center justify-center py-6"><div class="h-5 w-5 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
        {:else if phaseMilestones.length === 0}
          <p class="text-sm text-neutral-400 py-3">No milestones defined for this phase.</p>
        {:else}
          <div class="space-y-2">
            {#each phaseMilestones as ms}
              <div class="rounded-lg border border-neutral-200 p-3">
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-2">
                    {#if ms.is_completed}
                      <span class="flex h-5 w-5 rounded-full bg-emerald-100 items-center justify-center"><svg class="h-3 w-3 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" /></svg></span>
                    {:else}
                      <span class="inline-block h-5 w-5 rounded-full border-2 border-neutral-300"></span>
                    {/if}
                    <p class="text-sm font-medium text-neutral-900">{ms.name}</p>
                  </div>
                  {#if ms.approval_required}<span class="text-[9px] font-semibold rounded-full px-2 py-0.5 {ms.approval_status === 'approved' ? 'bg-emerald-100 text-emerald-800' : ms.approval_status === 'rejected' ? 'bg-red-100 text-red-800' : 'bg-amber-100 text-amber-800'}">{ms.approval_status.replace("_", " ")}</span>{/if}
                </div>
                <div class="mt-1.5 flex items-center gap-4 text-xs text-neutral-500">
                  <span>Target: {fmtDate(ms.revised_target_date || ms.target_date || ms.baseline_target_date)}</span>
                  {#if ms.completed_date}<span class="text-emerald-600 font-semibold">Completed: {fmtDate(ms.completed_date)}</span>{/if}
                  {#if ms.reference_code}<span class="text-neutral-400">{ms.reference_code}</span>{/if}
                </div>
                {#if ms.description}<p class="mt-1 text-xs text-neutral-500">{ms.description}</p>{/if}
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  {/if}
</DrawerShell>

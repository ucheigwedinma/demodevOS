<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { onMount } from "svelte";

  // --- Types ---
  interface TemplateListItem { id: number; name: string; template_type_display: string; }
  interface TaskSummary { id: number; name: string; reference_code: string; estimated_effort_hours: number | null; standard_duration_hours: number | null; assigned_role: string; category: string; }
  interface Activity { id: number; name: string; wbs_code: string; estimated_duration_days: number | null; sort_order: number; task_templates: TaskSummary[]; }
  interface Phase { id: number; name: string; sort_order: number; duration_days: number | null; activities: Activity[]; }
  interface Template { id: number; name: string; phases: Phase[]; }
  interface Dependency { id: number; from_node_id: string; to_node_id: string; dependency_type: string; lag_hours: number; }
  interface ResourceRole { role: string; capacity: number; daily_rate: number; }
  interface Holiday { name: string; month?: number; day?: number; date?: string; }
  interface ScheduleSettings {
    id: number; template: number;
    work_days: Record<string, boolean>;
    shift_start: string; shift_end: string; hours_per_day: number;
    public_holidays: Holiday[]; custom_holidays: Holiday[];
    rainy_season_buffer_enabled: boolean; rainy_season_buffer_pct: number;
    rainy_season_months: number[]; outdoor_task_categories: string[];
    resource_roles: ResourceRole[]; travel_buffer_hours: number;
    duration_scalar_pct: number; milestone_anchors: unknown[];
    work_days_per_week: number;
  }
  interface ScheduledNode {
    id: string; label: string; wbsCode: string; duration: number; scaledDuration: number;
    role: string; category: string;
    relativeStart: number; relativeEnd: number;
    onCriticalPath: boolean; float: number;
    allocated: number; capacity: number;
  }

  // --- State ---
  let loading = $state(true);
  let templates = $state<TemplateListItem[]>([]);
  let selectedTemplateId = $state<number | null>(null);
  let activeTemplate = $state<Template | null>(null);
  let dependencies = $state<Dependency[]>([]);
  let settings = $state<ScheduleSettings | null>(null);
  let settingsSaving = $state(false);
  let scheduledNodes = $state<ScheduledNode[]>([]);

  // What-if mode
  let whatIfActive = $state(false);
  let whatIfScalar = $state(100);

  // Delay Simulator
  let simDelayNodeId = $state("");
  let simDelayDays = $state(7);
  let simResult = $state<{
    originalDuration: number;
    newDuration: number;
    deltadays: number;
    costIncrease: number;
    affectedTasks: string[];
    resourceConflicts: string[];
    newCriticalPath: string[];
  } | null>(null);

  // Constraint Simulator
  let constraintRole = $state("");
  let constraintLimit = $state(1);
  let constraintResult = $state<{
    originalDuration: number;
    constrainedDuration: number;
    deltaDays: number;
    serializedTasks: { label: string; start: number; end: number }[];
    bottleneck: string;
  } | null>(null);

  function runConstraintSimulation() {
    if (!constraintRole || !activeTemplate || !settings) { constraintResult = null; return; }

    const hoursPerDay = settings.hours_per_day || 9;
    const scalar = effectiveScalar / 100;
    const originalDuration = projectDuration;

    // Collect tasks that use this role
    const roleTasks: { id: string; label: string; duration: number }[] = [];
    const otherTasks: { id: string; label: string; duration: number; start: number; end: number }[] = [];

    for (const node of scheduledNodes) {
      if (node.role.toLowerCase().includes(constraintRole.toLowerCase())) {
        roleTasks.push({ id: node.id, label: node.label, duration: node.scaledDuration });
      } else {
        otherTasks.push({ id: node.id, label: node.label, duration: node.scaledDuration, start: node.relativeStart, end: node.relativeEnd });
      }
    }

    if (roleTasks.length === 0) {
      constraintResult = { originalDuration: Math.round(originalDuration), constrainedDuration: Math.round(originalDuration), deltaDays: 0, serializedTasks: [], bottleneck: "No tasks use this resource." };
      return;
    }

    // With limit=N, only N tasks of this role can run in parallel
    // Serialize tasks into N lanes
    const lanes: number[] = Array(constraintLimit).fill(0); // each lane tracks when it becomes free
    const serialized: { label: string; start: number; end: number }[] = [];

    for (const task of roleTasks) {
      // Find the lane that frees up earliest
      const earliestLane = lanes.indexOf(Math.min(...lanes));
      const start = lanes[earliestLane];
      const end = start + task.duration;
      lanes[earliestLane] = end;
      serialized.push({ label: task.label, start, end });
    }

    const constrainedRoleEnd = Math.max(...lanes);
    // The constrained duration is the max of: role-constrained end + remaining non-role work, or original duration
    const constrainedDuration = Math.max(constrainedRoleEnd, originalDuration);
    const deltaDays = constrainedDuration - originalDuration;

    constraintResult = {
      originalDuration: Math.round(originalDuration),
      constrainedDuration: Math.round(constrainedDuration),
      deltaDays: Math.round(deltaDays),
      serializedTasks: serialized,
      bottleneck: deltaDays > 0
        ? `Limiting ${constraintRole} to ${constraintLimit} unit(s) creates a ${Math.round(deltaDays)}-day bottleneck.`
        : `${constraintLimit} unit(s) of ${constraintRole} is sufficient — no schedule impact.`,
    };
  }

  function runDelaySimulation() {
    if (!simDelayNodeId || !activeTemplate || !settings) { simResult = null; return; }

    const baseNodes = [...scheduledNodes];
    const originalDuration = projectDuration;
    const hoursPerDay = settings.hours_per_day || 9;
    const scalar = effectiveScalar / 100;

    // Rebuild nodes with the delay injected
    const simNodes: ScheduledNode[] = [];
    const simMap = new Map<string, ScheduledNode>();

    for (const phase of activeTemplate.phases) {
      for (const activity of phase.activities) {
        let baseDuration = activity.estimated_duration_days || 1;
        let scaledDur = Math.ceil(baseDuration * scalar);
        if (settings.rainy_season_buffer_enabled) {
          const isOutdoor = activity.task_templates.some(t =>
            (settings!.outdoor_task_categories || []).includes(t.category)
          );
          if (isOutdoor) scaledDur = Math.ceil(scaledDur * (1 + (settings!.rainy_season_buffer_pct || 0) / 100));
        }
        const nodeId = `act-${activity.id}`;
        // Inject delay
        if (nodeId === simDelayNodeId) {
          scaledDur += simDelayDays;
        }
        const node: ScheduledNode = {
          id: nodeId, label: activity.name,
          wbsCode: activity.wbs_code || `${phase.sort_order + 1}.${activity.sort_order + 1}`,
          duration: baseDuration, scaledDuration: scaledDur,
          role: activity.task_templates[0]?.assigned_role || "",
          category: activity.task_templates[0]?.category || "",
          relativeStart: 0, relativeEnd: scaledDur,
          onCriticalPath: false, float: 0,
          allocated: 0, capacity: 0,
        };
        simNodes.push(node);
        simMap.set(nodeId, node);
      }
    }

    // CPM forward pass
    const adjIn = new Map<string, { source: string; lag: number }[]>();
    const adjOut = new Map<string, { target: string; lag: number }[]>();
    for (const n of simNodes) { adjIn.set(n.id, []); adjOut.set(n.id, []); }
    for (const d of dependencies) {
      if (simMap.has(d.from_node_id) && simMap.has(d.to_node_id)) {
        adjOut.get(d.from_node_id)!.push({ target: d.to_node_id, lag: d.lag_hours / hoursPerDay });
        adjIn.get(d.to_node_id)!.push({ source: d.from_node_id, lag: d.lag_hours / hoursPerDay });
      }
    }
    // Topological sort
    const inDeg = new Map<string, number>();
    for (const n of simNodes) inDeg.set(n.id, 0);
    for (const d of dependencies) {
      if (simMap.has(d.to_node_id)) inDeg.set(d.to_node_id, (inDeg.get(d.to_node_id) || 0) + 1);
    }
    const queue: string[] = [];
    for (const [id, deg] of inDeg) { if (deg === 0) queue.push(id); }
    const sorted: string[] = [];
    while (queue.length > 0) {
      const c = queue.shift()!;
      sorted.push(c);
      for (const e of (adjOut.get(c) || [])) {
        const nd = (inDeg.get(e.target) || 1) - 1;
        inDeg.set(e.target, nd);
        if (nd === 0) queue.push(e.target);
      }
    }
    // Forward
    for (const id of sorted) {
      const node = simMap.get(id)!;
      let maxES = 0;
      for (const e of (adjIn.get(id) || [])) {
        const pred = simMap.get(e.source);
        if (pred) maxES = Math.max(maxES, pred.relativeEnd + e.lag);
      }
      node.relativeStart = maxES;
      node.relativeEnd = maxES + node.scaledDuration;
    }
    // Backward
    const newProjectDuration = Math.max(...simNodes.map(n => n.relativeEnd), 0);
    for (let i = sorted.length - 1; i >= 0; i--) {
      const node = simMap.get(sorted[i])!;
      let minLF = newProjectDuration;
      for (const e of (adjOut.get(node.id) || [])) {
        const succ = simMap.get(e.target);
        if (succ) minLF = Math.min(minLF, succ.relativeStart - e.lag);
      }
      const lf = (adjOut.get(node.id) || []).length === 0 ? newProjectDuration : minLF;
      const ls = lf - node.scaledDuration;
      node.float = Math.max(0, ls - node.relativeStart);
      node.onCriticalPath = node.float < 0.5;
    }

    // Find affected (shifted) tasks
    const affected: string[] = [];
    for (const sn of simNodes) {
      const orig = baseNodes.find(n => n.id === sn.id);
      if (orig && sn.relativeStart > orig.relativeStart && sn.id !== simDelayNodeId) {
        affected.push(sn.label);
      }
    }

    // Resource conflicts: roles that now have overlapping tasks
    const roleConflicts: string[] = [];
    const roleSlots = new Map<string, { label: string; start: number; end: number }[]>();
    for (const sn of simNodes) {
      if (!sn.role) continue;
      const key = sn.role.toLowerCase();
      const list = roleSlots.get(key) || [];
      // Check overlap with existing
      for (const existing of list) {
        if (sn.relativeStart < existing.end && sn.relativeEnd > existing.start) {
          roleConflicts.push(`${sn.role}: "${sn.label}" overlaps with "${existing.label}"`);
        }
      }
      list.push({ label: sn.label, start: sn.relativeStart, end: sn.relativeEnd });
      roleSlots.set(key, list);
    }

    // Cost increase: extra days × average daily rate from resource_roles
    const avgDailyRate = settings.resource_roles.length > 0
      ? settings.resource_roles.reduce((s, r) => s + Number(r.daily_rate) * Number(r.capacity), 0)
      : 0;
    const deltaDays = newProjectDuration - originalDuration;
    const costIncrease = Math.max(0, deltaDays * avgDailyRate);

    simResult = {
      originalDuration: Math.round(originalDuration),
      newDuration: Math.round(newProjectDuration),
      deltadays: Math.round(deltaDays),
      costIncrease,
      affectedTasks: affected,
      resourceConflicts: [...new Set(roleConflicts)],
      newCriticalPath: simNodes.filter(n => n.onCriticalPath).map(n => n.label),
    };
  }

  const DAY_LABELS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"] as const;
  const DAY_NAMES: Record<string, string> = { mon: "Mon", tue: "Tue", wed: "Wed", thu: "Thu", fri: "Fri", sat: "Sat", sun: "Sun" };

  // Computed
  const projectDuration = $derived(scheduledNodes.length > 0 ? Math.max(...scheduledNodes.map(n => n.relativeEnd)) : 0);
  const criticalCount = $derived(scheduledNodes.filter(n => n.onCriticalPath).length);
  const totalEffort = $derived(scheduledNodes.reduce((s, n) => s + n.scaledDuration, 0));
  const effectiveScalar = $derived(whatIfActive ? whatIfScalar : (settings?.duration_scalar_pct ?? 100));

  // Resource heatmap data
  const resourceHeatmap = $derived.by(() => {
    if (!settings) return [];
    return (settings.resource_roles || []).map(r => {
      const allocated = scheduledNodes.filter(n => n.role.toLowerCase().includes(r.role.toLowerCase())).reduce((s, n) => s + n.scaledDuration, 0);
      const capacity = r.capacity * projectDuration;
      const pct = capacity > 0 ? (allocated / capacity) * 100 : 0;
      return { role: r.role, capacity, allocated, pct, overAllocated: pct > 100, dailyRate: r.daily_rate };
    });
  });

  // Timeline scale
  const timelineWidth = $derived(Math.max(800, projectDuration * 32 + 200));

  // --- Load ---
  async function loadTemplates() {
    try {
      const res = await api.get<{ results: TemplateListItem[] }>("/settings/project-templates/", { page_size: "100", is_active: "true" });
      templates = res.results;
      if (templates.length > 0 && !selectedTemplateId) await selectTemplate(templates[0].id);
    } catch { toast.error("Load failed", "Could not load templates."); }
    finally { loading = false; }
  }

  async function selectTemplate(id: number) {
    selectedTemplateId = id;
    loading = true;
    try {
      const [tmpl, deps, sched] = await Promise.all([
        api.get<Template>(`/settings/project-templates/${id}/`),
        api.get<{ results: Dependency[] }>(`/settings/project-templates/${id}/dependencies/`, { page_size: "500" }),
        api.get<ScheduleSettings>(`/settings/project-templates/${id}/schedule-settings/`),
      ]);
      activeTemplate = tmpl;
      dependencies = deps.results;
      settings = sched;
      calculateSchedule();
    } catch { toast.error("Load failed", "Could not load template."); }
    finally { loading = false; }
  }

  // --- Scheduling Engine ---
  function calculateSchedule() {
    if (!activeTemplate || !settings) { scheduledNodes = []; return; }

    const scalar = effectiveScalar / 100;
    const allNodes: ScheduledNode[] = [];
    const nodeMap = new Map<string, ScheduledNode>();

    // Build nodes from activities
    for (const phase of activeTemplate.phases) {
      for (const activity of phase.activities) {
        const baseDuration = activity.estimated_duration_days || 1;
        let scaledDur = Math.ceil(baseDuration * scalar);

        // Apply rainy season buffer for outdoor categories
        if (settings.rainy_season_buffer_enabled) {
          const isOutdoor = activity.task_templates.some(t =>
            (settings!.outdoor_task_categories || []).includes(t.category)
          );
          if (isOutdoor) scaledDur = Math.ceil(scaledDur * (1 + (settings!.rainy_season_buffer_pct || 0) / 100));
        }

        const primaryRole = activity.task_templates[0]?.assigned_role || "";
        const primaryCat = activity.task_templates[0]?.category || "";

        const node: ScheduledNode = {
          id: `act-${activity.id}`, label: activity.name,
          wbsCode: activity.wbs_code || `${phase.sort_order + 1}.${activity.sort_order + 1}`,
          duration: baseDuration, scaledDuration: scaledDur,
          role: primaryRole, category: primaryCat,
          relativeStart: 0, relativeEnd: scaledDur,
          onCriticalPath: false, float: 0,
          allocated: 0, capacity: 0,
        };
        allNodes.push(node);
        nodeMap.set(node.id, node);
      }
    }

    // Forward pass (CPM with dependencies)
    const adjIn = new Map<string, { source: string; lag: number }[]>();
    const adjOut = new Map<string, { target: string; lag: number }[]>();
    for (const n of allNodes) { adjIn.set(n.id, []); adjOut.set(n.id, []); }
    for (const d of dependencies) {
      if (nodeMap.has(d.from_node_id) && nodeMap.has(d.to_node_id)) {
        adjOut.get(d.from_node_id)!.push({ target: d.to_node_id, lag: d.lag_hours / (settings!.hours_per_day || 9) });
        adjIn.get(d.to_node_id)!.push({ source: d.from_node_id, lag: d.lag_hours / (settings!.hours_per_day || 9) });
      }
    }

    // Topological sort
    const inDeg = new Map<string, number>();
    for (const n of allNodes) inDeg.set(n.id, 0);
    for (const d of dependencies) {
      if (nodeMap.has(d.to_node_id)) inDeg.set(d.to_node_id, (inDeg.get(d.to_node_id) || 0) + 1);
    }
    const queue: string[] = [];
    for (const [id, deg] of inDeg) { if (deg === 0) queue.push(id); }
    const sorted: string[] = [];
    while (queue.length > 0) {
      const c = queue.shift()!;
      sorted.push(c);
      for (const e of (adjOut.get(c) || [])) {
        const nd = (inDeg.get(e.target) || 1) - 1;
        inDeg.set(e.target, nd);
        if (nd === 0) queue.push(e.target);
      }
    }

    // Forward pass
    for (const id of sorted) {
      const node = nodeMap.get(id)!;
      let maxES = 0;
      for (const e of (adjIn.get(id) || [])) {
        const pred = nodeMap.get(e.source);
        if (pred) maxES = Math.max(maxES, pred.relativeEnd + e.lag);
      }
      node.relativeStart = maxES;
      node.relativeEnd = maxES + node.scaledDuration;
    }

    // Backward pass
    const projEnd = Math.max(...allNodes.map(n => n.relativeEnd), 0);
    for (let i = sorted.length - 1; i >= 0; i--) {
      const node = nodeMap.get(sorted[i])!;
      let minLF = projEnd;
      for (const e of (adjOut.get(node.id) || [])) {
        const succ = nodeMap.get(e.target);
        if (succ) minLF = Math.min(minLF, succ.relativeStart - e.lag);
      }
      const lf = (adjOut.get(node.id) || []).length === 0 ? projEnd : minLF;
      const ls = lf - node.scaledDuration;
      node.float = Math.max(0, ls - node.relativeStart);
      node.onCriticalPath = node.float < 0.5;
    }

    scheduledNodes = allNodes;
  }

  // Reactively recalculate when scalar changes
  $effect(() => {
    if (activeTemplate && settings) {
      void effectiveScalar;
      calculateSchedule();
    }
  });

  async function saveSettings() {
    if (!settings || !selectedTemplateId) return;
    settingsSaving = true;
    try {
      await api.patch(`/settings/project-templates/${selectedTemplateId}/schedule-settings/`, settings);
      toast.success("Settings saved", "Calendar and resource rules have been updated.");
    } catch { toast.error("Save failed", "Could not save schedule settings."); }
    finally { settingsSaving = false; }
  }

  // Resource role management
  function addRole() {
    if (!settings) return;
    settings.resource_roles = [...settings.resource_roles, { role: "", capacity: 1, daily_rate: 10000 }];
  }
  function removeRole(i: number) {
    if (!settings) return;
    settings.resource_roles = settings.resource_roles.filter((_, idx) => idx !== i);
  }

  // Custom holiday management
  let newHolidayName = $state("");
  let newHolidayDate = $state("");
  function addCustomHoliday() {
    if (!settings || !newHolidayName.trim() || !newHolidayDate) return;
    settings.custom_holidays = [...settings.custom_holidays, { name: newHolidayName.trim(), date: newHolidayDate }];
    newHolidayName = ""; newHolidayDate = "";
  }
  function removeCustomHoliday(i: number) {
    if (!settings) return;
    settings.custom_holidays = settings.custom_holidays.filter((_, idx) => idx !== i);
  }

  onMount(() => { loadTemplates(); });
</script>

<svelte:head><title>Scheduling Engine — Project Planner | developerOS</title></svelte:head>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">Project Planning</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Scheduling Engine</h1>
      <p class="mt-1 text-sm text-neutral-500">Define calendar rules, resource constraints, and generate relative timelines.</p>
    </div>
    <div class="flex gap-2">
      <button
        onclick={() => { whatIfActive = !whatIfActive; if (!whatIfActive) { whatIfScalar = settings?.duration_scalar_pct ?? 100; } }}
        class="rounded-lg border px-3.5 py-2 text-sm font-medium transition-colors {whatIfActive ? 'border-indigo-300 bg-indigo-50 text-indigo-700' : 'border-neutral-200 bg-white text-neutral-700 hover:bg-neutral-50'}"
      >
        {whatIfActive ? "Exit What-If" : "What-If Mode"}
      </button>
      <button
        onclick={saveSettings}
        disabled={settingsSaving}
        class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50"
      >
        {settingsSaving ? "Saving..." : "Save Settings"}
      </button>
    </div>
  </div>

  <!-- Template selector + KPIs -->
  <div class="flex flex-col gap-4 sm:flex-row sm:items-center">
    <div class="w-64">
      <select onchange={(e) => { const id = Number((e.target as HTMLSelectElement).value); if (id) selectTemplate(id); }} class="w-full rounded-lg border border-neutral-200 bg-white px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
        {#each templates as tmpl}
          <option value={tmpl.id} selected={tmpl.id === selectedTemplateId}>{tmpl.name}</option>
        {/each}
      </select>
    </div>
    <div class="flex gap-3">
      <div class="rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-center">
        <p class="text-lg font-bold text-neutral-900 tabular-nums">{projectDuration}<span class="text-xs font-normal text-neutral-400 ml-0.5">d</span></p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Duration</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-center">
        <p class="text-lg font-bold text-neutral-900 tabular-nums">{totalEffort}<span class="text-xs font-normal text-neutral-400 ml-0.5">d</span></p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Total Effort</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-center">
        <p class="text-lg font-bold tabular-nums {criticalCount > 0 ? 'text-red-600' : 'text-neutral-900'}">{criticalCount}</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Critical</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-center">
        <p class="text-lg font-bold text-neutral-900 tabular-nums">{settings?.work_days_per_week ?? 0}</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Work Days/Wk</p>
      </div>
    </div>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-16 text-sm text-neutral-400">Loading...</div>
  {:else if !settings}
    <div class="rounded-xl border border-neutral-200 bg-white p-12 text-center text-sm text-neutral-500">No template selected.</div>
  {:else}

    <!-- 1. Global Calendar & Work Rules -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <section class="rounded-xl border border-neutral-200 bg-white p-6">
        <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-4">Work Week & Shifts</h3>
        <div class="flex gap-2 mb-4">
          {#each DAY_LABELS as day}
            <label class="flex flex-col items-center gap-1 cursor-pointer">
              <input type="checkbox" bind:checked={settings.work_days[day]} class="rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900" />
              <span class="text-[10px] font-semibold text-neutral-500">{DAY_NAMES[day]}</span>
            </label>
          {/each}
        </div>
        <div class="grid grid-cols-3 gap-3">
          <label class="text-xs font-medium text-neutral-600"><span class="block mb-1">Shift Start</span><input type="time" bind:value={settings.shift_start} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
          <label class="text-xs font-medium text-neutral-600"><span class="block mb-1">Shift End</span><input type="time" bind:value={settings.shift_end} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
          <label class="text-xs font-medium text-neutral-600"><span class="block mb-1">Hours/Day</span><input type="number" bind:value={settings.hours_per_day} step="0.5" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm tabular-nums" /></label>
        </div>
      </section>

      <section class="rounded-xl border border-neutral-200 bg-white p-6">
        <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-4">Weather Buffers</h3>
        <label class="flex items-center gap-3 mb-3 cursor-pointer">
          <input type="checkbox" bind:checked={settings.rainy_season_buffer_enabled} class="rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900" />
          <span class="text-sm font-medium text-neutral-700">Enable rainy season buffer</span>
        </label>
        {#if settings.rainy_season_buffer_enabled}
          <label class="block text-xs font-medium text-neutral-600 mb-3">
            <span class="block mb-1">Buffer %</span>
            <div class="flex items-center gap-3">
              <input type="range" min="5" max="50" step="5" bind:value={settings.rainy_season_buffer_pct} class="flex-1 accent-neutral-900" />
              <span class="text-sm font-bold text-neutral-900 tabular-nums w-10 text-right">{settings.rainy_season_buffer_pct}%</span>
            </div>
          </label>
          <p class="text-[10px] text-neutral-400">Applied to outdoor tasks (categories: {(settings.outdoor_task_categories || []).join(", ")}) during months {(settings.rainy_season_months || []).join(", ")}.</p>
        {/if}
      </section>
    </div>

    <!-- Holidays -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <section class="rounded-xl border border-neutral-200 bg-white p-6">
        <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3">Nigerian Public Holidays</h3>
        <div class="flex flex-wrap gap-1.5">
          {#each settings.public_holidays as h}
            <span class="rounded-md bg-neutral-100 px-2.5 py-1 text-[10px] font-medium text-neutral-600">{h.name}</span>
          {/each}
        </div>
      </section>

      <section class="rounded-xl border border-neutral-200 bg-white p-6">
        <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3">Custom Holidays</h3>
        {#if settings.custom_holidays.length > 0}
          <div class="flex flex-wrap gap-1.5 mb-3">
            {#each settings.custom_holidays as h, i}
              <span class="inline-flex items-center gap-1 rounded-md bg-amber-50 border border-amber-200 px-2 py-0.5 text-[10px] font-medium text-amber-700">
                {h.name} ({h.date})<button onclick={() => removeCustomHoliday(i)} class="text-amber-400 hover:text-red-500">&times;</button>
              </span>
            {/each}
          </div>
        {/if}
        <div class="flex gap-2">
          <input bind:value={newHolidayName} class="flex-1 rounded-lg border border-neutral-200 px-2.5 py-1.5 text-xs" placeholder="Holiday name" />
          <input type="date" bind:value={newHolidayDate} class="rounded-lg border border-neutral-200 px-2.5 py-1.5 text-xs" />
          <button onclick={addCustomHoliday} class="rounded-lg bg-neutral-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-neutral-800">Add</button>
        </div>
      </section>
    </div>

    <!-- 2. Resource Leveling -->
    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest">Resource Capacity Heatmap</h3>
        <div class="flex items-center gap-3">
          <label class="text-xs font-medium text-neutral-600 flex items-center gap-2">
            Travel Buffer:
            <input type="number" bind:value={settings.travel_buffer_hours} step="0.5" class="w-16 rounded-lg border border-neutral-200 px-2 py-1 text-xs tabular-nums" />
            <span class="text-neutral-400">hrs</span>
          </label>
        </div>
      </div>
      <div class="space-y-3">
        {#each resourceHeatmap as r}
          <div class="flex items-center gap-3">
            <span class="w-32 text-xs font-medium text-neutral-700 truncate">{r.role}</span>
            <div class="flex-1 h-6 rounded-full bg-neutral-100 overflow-hidden relative">
              <div
                class="h-full rounded-full transition-all {r.overAllocated ? 'bg-red-400' : r.pct > 80 ? 'bg-amber-400' : 'bg-emerald-400'}"
                style="width: {Math.min(r.pct, 100)}%"
              ></div>
              {#if r.pct > 100}
                <div class="absolute inset-0 rounded-full border-2 border-red-400 animate-pulse"></div>
              {/if}
            </div>
            <span class="w-20 text-right text-xs tabular-nums {r.overAllocated ? 'font-bold text-red-600' : 'text-neutral-500'}">{r.pct.toFixed(0)}%</span>
            <span class="w-24 text-right text-[10px] text-neutral-400 tabular-nums">₦{r.dailyRate.toLocaleString()}/d</span>
          </div>
        {/each}
      </div>
      <div class="flex items-center gap-2 mt-4">
        <button onclick={addRole} class="rounded-lg border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50">+ Add Role</button>
      </div>
      {#if settings.resource_roles.length > 0}
        <div class="mt-3 overflow-x-auto rounded-lg border border-neutral-200">
          <table class="w-full text-xs">
            <thead><tr class="bg-neutral-50"><th class="px-3 py-1.5 text-left font-medium text-neutral-500">Role</th><th class="px-3 py-1.5 text-right font-medium text-neutral-500 w-20">Capacity</th><th class="px-3 py-1.5 text-right font-medium text-neutral-500 w-28">Daily Rate (₦)</th><th class="w-8"></th></tr></thead>
            <tbody class="divide-y divide-neutral-100">
              {#each settings.resource_roles as role, i}
                <tr>
                  <td class="px-3 py-1.5"><input bind:value={settings.resource_roles[i].role} class="w-full rounded border border-neutral-200 px-2 py-1 text-xs" /></td>
                  <td class="px-3 py-1.5"><input type="number" bind:value={settings.resource_roles[i].capacity} min="1" class="w-full rounded border border-neutral-200 px-2 py-1 text-xs text-right tabular-nums" /></td>
                  <td class="px-3 py-1.5"><input type="number" bind:value={settings.resource_roles[i].daily_rate} class="w-full rounded border border-neutral-200 px-2 py-1 text-xs text-right tabular-nums" /></td>
                  <td class="px-1 py-1.5"><button onclick={() => removeRole(i)} class="text-neutral-300 hover:text-red-500">&times;</button></td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </section>

    <!-- Duration Scalar (What-If) -->
    {#if whatIfActive}
      <section class="rounded-xl border border-indigo-200 bg-indigo-50/50 p-6" style="backdrop-filter: blur(10px)">
        <h3 class="text-[10px] font-semibold text-indigo-500 uppercase tracking-widest mb-3">What-If Simulator</h3>
        <p class="text-xs text-indigo-600 mb-3">Adjust the duration scalar to see how the timeline changes. This does not save — exit to discard.</p>
        <div class="flex items-center gap-4">
          <span class="text-xs text-indigo-500 w-12">Faster</span>
          <input type="range" min="50" max="200" step="5" bind:value={whatIfScalar} class="flex-1 accent-indigo-600" />
          <span class="text-xs text-indigo-500 w-12 text-right">Slower</span>
          <span class="text-lg font-bold text-indigo-700 tabular-nums w-16 text-center">{whatIfScalar}%</span>
        </div>
        <p class="mt-2 text-xs text-indigo-500 tabular-nums">Original: {Math.round(projectDuration * 100 / (whatIfScalar || 100))}d → Adjusted: {projectDuration}d ({whatIfScalar > 100 ? "+" : ""}{whatIfScalar - 100}%)</p>
      </section>

      <!-- Delay Simulator -->
      <section class="rounded-xl border border-amber-200 bg-amber-50/50 p-6" style="backdrop-filter: blur(25px)">
        <h3 class="text-[10px] font-semibold text-amber-600 uppercase tracking-widest mb-3">Delay Simulator</h3>
        <p class="text-xs text-amber-700 mb-4">Select a specific task, apply a delay, and see the cascade impact on completion date, cost, and resources.</p>

        <div class="flex flex-wrap items-end gap-3 mb-4">
          <label class="flex-1 min-w-[200px]">
            <span class="block text-[10px] font-semibold text-amber-600 uppercase mb-1">Task to Delay</span>
            <select bind:value={simDelayNodeId} class="w-full rounded-lg border border-amber-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500">
              <option value="">Select task...</option>
              {#each scheduledNodes as node}
                <option value={node.id}>{node.wbsCode} — {node.label}</option>
              {/each}
            </select>
          </label>
          <label class="w-28">
            <span class="block text-[10px] font-semibold text-amber-600 uppercase mb-1">Delay (days)</span>
            <input type="number" min="1" max="90" bind:value={simDelayDays} class="w-full rounded-lg border border-amber-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500" />
          </label>
          <button onclick={runDelaySimulation} disabled={!simDelayNodeId} class="rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-700 disabled:opacity-40">
            Simulate
          </button>
        </div>

        {#if simResult}
          <div class="space-y-4">
            <!-- Impact KPIs -->
            <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div class="rounded-xl border border-neutral-200 bg-white p-3 text-center">
                <p class="text-[9px] font-semibold text-neutral-400 uppercase">Original</p>
                <p class="text-lg font-bold text-neutral-900 tabular-nums">{simResult.originalDuration}d</p>
              </div>
              <div class="rounded-xl border {simResult.deltadays > 0 ? 'border-red-200 bg-red-50' : 'border-emerald-200 bg-emerald-50'} p-3 text-center">
                <p class="text-[9px] font-semibold {simResult.deltadays > 0 ? 'text-red-400' : 'text-emerald-400'} uppercase">New Duration</p>
                <p class="text-lg font-bold {simResult.deltadays > 0 ? 'text-red-700' : 'text-emerald-700'} tabular-nums">{simResult.newDuration}d</p>
                <p class="text-[10px] {simResult.deltadays > 0 ? 'text-red-500' : 'text-emerald-500'} font-semibold tabular-nums">
                  {simResult.deltadays > 0 ? '+' : ''}{simResult.deltadays}d
                </p>
              </div>
              <div class="rounded-xl border {simResult.costIncrease > 0 ? 'border-red-200 bg-red-50' : 'border-neutral-200 bg-white'} p-3 text-center">
                <p class="text-[9px] font-semibold {simResult.costIncrease > 0 ? 'text-red-400' : 'text-neutral-400'} uppercase">Cost Impact</p>
                <p class="text-lg font-bold {simResult.costIncrease > 0 ? 'text-red-700' : 'text-neutral-900'} tabular-nums">
                  {simResult.costIncrease > 0 ? `+${String.fromCharCode(8358)}${Math.round(simResult.costIncrease).toLocaleString()}` : 'No change'}
                </p>
              </div>
              <div class="rounded-xl border {simResult.resourceConflicts.length > 0 ? 'border-amber-200 bg-amber-50' : 'border-emerald-200 bg-emerald-50'} p-3 text-center">
                <p class="text-[9px] font-semibold {simResult.resourceConflicts.length > 0 ? 'text-amber-400' : 'text-emerald-400'} uppercase">Conflicts</p>
                <p class="text-lg font-bold {simResult.resourceConflicts.length > 0 ? 'text-amber-700' : 'text-emerald-700'} tabular-nums">
                  {simResult.resourceConflicts.length}
                </p>
              </div>
            </div>

            <!-- Affected Tasks -->
            {#if simResult.affectedTasks.length > 0}
              <div class="rounded-lg border border-neutral-200 bg-white p-4">
                <h4 class="text-[10px] font-semibold text-neutral-500 uppercase mb-2">Downstream Tasks Rescheduled ({simResult.affectedTasks.length})</h4>
                <div class="flex flex-wrap gap-1.5">
                  {#each simResult.affectedTasks as task}
                    <span class="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-0.5 text-[10px] font-medium text-amber-700">{task}</span>
                  {/each}
                </div>
              </div>
            {/if}

            <!-- Resource Conflicts -->
            {#if simResult.resourceConflicts.length > 0}
              <div class="rounded-lg border border-red-200 bg-red-50 p-4">
                <h4 class="text-[10px] font-semibold text-red-500 uppercase mb-2">Resource Conflicts</h4>
                <ul class="space-y-1">
                  {#each simResult.resourceConflicts as conflict}
                    <li class="text-xs text-red-700">{conflict}</li>
                  {/each}
                </ul>
              </div>
            {/if}

            <!-- New Critical Path -->
            <div class="rounded-lg border border-neutral-200 bg-white p-4">
              <h4 class="text-[10px] font-semibold text-neutral-500 uppercase mb-2">Critical Path ({simResult.newCriticalPath.length} tasks)</h4>
              <div class="flex flex-wrap gap-1.5">
                {#each simResult.newCriticalPath as task}
                  <span class="rounded-full border border-red-200 bg-red-50 px-2.5 py-0.5 text-[10px] font-medium text-red-700">{task}</span>
                {/each}
              </div>
            </div>
          </div>
        {/if}
      </section>

      <!-- Constraint Simulator -->
      <section class="rounded-xl border border-violet-200 bg-violet-50/50 p-6" style="backdrop-filter: blur(25px)">
        <h3 class="text-[10px] font-semibold text-violet-600 uppercase tracking-widest mb-3">Resource Constraint Simulator</h3>
        <p class="text-xs text-violet-700 mb-4">Limit a resource type and see how the schedule adjusts. E.g. "What if I only have 1 crane?"</p>

        <div class="flex flex-wrap items-end gap-3 mb-4">
          <label class="flex-1 min-w-[200px]">
            <span class="block text-[10px] font-semibold text-violet-600 uppercase mb-1">Resource / Role</span>
            <select bind:value={constraintRole} class="w-full rounded-lg border border-violet-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500">
              <option value="">Select resource...</option>
              {#each [...new Set(scheduledNodes.map(n => n.role).filter(Boolean))] as role}
                <option value={role}>{role}</option>
              {/each}
              {#if settings}
                {#each settings.resource_roles as r}
                  {#if !scheduledNodes.some(n => n.role === r.role)}
                    <option value={r.role}>{r.role} (from config)</option>
                  {/if}
                {/each}
              {/if}
            </select>
          </label>
          <label class="w-32">
            <span class="block text-[10px] font-semibold text-violet-600 uppercase mb-1">Max Available</span>
            <input type="number" min="1" max="20" bind:value={constraintLimit} class="w-full rounded-lg border border-violet-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500" />
          </label>
          <button onclick={runConstraintSimulation} disabled={!constraintRole} class="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-700 disabled:opacity-40">
            Simulate
          </button>
        </div>

        {#if constraintResult}
          <div class="space-y-4">
            <!-- Impact KPIs -->
            <div class="grid grid-cols-3 gap-3">
              <div class="rounded-xl border border-neutral-200 bg-white p-3 text-center">
                <p class="text-[9px] font-semibold text-neutral-400 uppercase">Original</p>
                <p class="text-lg font-bold text-neutral-900 tabular-nums">{constraintResult.originalDuration}d</p>
              </div>
              <div class="rounded-xl border {constraintResult.deltaDays > 0 ? 'border-red-200 bg-red-50' : 'border-emerald-200 bg-emerald-50'} p-3 text-center">
                <p class="text-[9px] font-semibold {constraintResult.deltaDays > 0 ? 'text-red-400' : 'text-emerald-400'} uppercase">Constrained</p>
                <p class="text-lg font-bold {constraintResult.deltaDays > 0 ? 'text-red-700' : 'text-emerald-700'} tabular-nums">{constraintResult.constrainedDuration}d</p>
                {#if constraintResult.deltaDays > 0}
                  <p class="text-[10px] text-red-500 font-semibold tabular-nums">+{constraintResult.deltaDays}d</p>
                {/if}
              </div>
              <div class="rounded-xl border border-violet-200 bg-violet-50 p-3 text-center">
                <p class="text-[9px] font-semibold text-violet-400 uppercase">Tasks Affected</p>
                <p class="text-lg font-bold text-violet-700 tabular-nums">{constraintResult.serializedTasks.length}</p>
              </div>
            </div>

            <!-- Bottleneck message -->
            <div class="rounded-lg border {constraintResult.deltaDays > 0 ? 'border-red-200 bg-red-50' : 'border-emerald-200 bg-emerald-50'} p-3">
              <p class="text-xs {constraintResult.deltaDays > 0 ? 'text-red-700' : 'text-emerald-700'} font-medium">{constraintResult.bottleneck}</p>
            </div>

            <!-- Serialized task timeline -->
            {#if constraintResult.serializedTasks.length > 0}
              <div class="rounded-lg border border-neutral-200 bg-white p-4">
                <h4 class="text-[10px] font-semibold text-neutral-500 uppercase mb-3">Serialized Task Sequence ({constraintLimit} lane{constraintLimit > 1 ? 's' : ''})</h4>
                <div class="space-y-1.5">
                  {#each constraintResult.serializedTasks as task, i}
                    {@const maxEnd = Math.max(...constraintResult.serializedTasks.map(t => t.end), 1)}
                    <div class="flex items-center gap-2">
                      <span class="text-[10px] text-neutral-500 w-32 truncate" title={task.label}>{task.label}</span>
                      <div class="flex-1 h-5 bg-neutral-50 rounded relative">
                        <div class="absolute top-0 h-full rounded bg-violet-400/70 flex items-center justify-center"
                          style="left: {task.start / maxEnd * 100}%; width: {Math.max(2, (task.end - task.start) / maxEnd * 100)}%">
                          <span class="text-[8px] font-semibold text-white truncate px-1">D{Math.round(task.start)}–D{Math.round(task.end)}</span>
                        </div>
                      </div>
                    </div>
                  {/each}
                </div>
              </div>
            {/if}
          </div>
        {/if}
      </section>
    {/if}

    <!-- 3. Scheduling Timeline (Relative) -->
    <section class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
      <div class="flex items-center justify-between border-b border-neutral-100 bg-neutral-50 px-5 py-3">
        <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest">Relative Timeline (Day 0 → Day {projectDuration})</h3>
        {#if !whatIfActive}
          <label class="flex items-center gap-2 text-xs font-medium text-neutral-600">
            Speed:
            <input type="range" min="50" max="200" step="5" bind:value={settings.duration_scalar_pct} class="w-32 accent-neutral-900" />
            <span class="tabular-nums w-10 text-right">{settings.duration_scalar_pct}%</span>
          </label>
        {/if}
      </div>

      <div class="overflow-x-auto p-4">
        <div style="width: {timelineWidth}px; position: relative; min-height: {scheduledNodes.length * 36 + 60}px">
          <!-- Day markers -->
          <div class="flex border-b border-neutral-100 mb-2" style="padding-left: 180px">
            {#each Array(Math.ceil(projectDuration) + 1) as _, d}
              {#if d % 5 === 0}
                <div class="text-[9px] text-neutral-400 tabular-nums" style="position: absolute; left: {180 + d * 32}px; top: 0">D{d}</div>
              {/if}
            {/each}
          </div>

          <!-- Task bars -->
          {#each scheduledNodes as node, i (node.id)}
            {@const barLeft = 180 + node.relativeStart * 32}
            {@const barWidth = Math.max(node.scaledDuration * 32, 16)}
            <div class="flex items-center" style="position: absolute; top: {30 + i * 36}px; left: 0; right: 0; height: 28px">
              <!-- Label -->
              <div class="w-[176px] shrink-0 pr-2 flex items-center gap-1.5 overflow-hidden">
                <span class="rounded bg-neutral-100 px-1 py-0.5 text-[9px] font-bold text-neutral-500 tabular-nums shrink-0">{node.wbsCode}</span>
                <span class="text-[11px] text-neutral-700 truncate font-medium">{node.label}</span>
              </div>
              <!-- Bar -->
              <div
                class="absolute h-6 rounded-md shadow-sm transition-all {node.onCriticalPath ? 'bg-red-500/90 border border-red-600' : 'bg-neutral-800/80 border border-neutral-700'}"
                style="left: {barLeft}px; width: {barWidth}px"
                title="{node.label} — Day {node.relativeStart} to {node.relativeEnd} (Float: {node.float}d)"
              >
                <span class="absolute inset-0 flex items-center justify-center text-[9px] font-bold text-white tabular-nums">{node.scaledDuration}d</span>
              </div>
              <!-- Float indicator -->
              {#if node.float > 0}
                <div
                  class="absolute h-6 rounded-md border border-dashed border-neutral-300 bg-neutral-100/40"
                  style="left: {barLeft + barWidth}px; width: {node.float * 32}px"
                  title="Float: {node.float}d"
                ></div>
              {/if}
            </div>
          {/each}

          <!-- Grid lines -->
          {#each Array(Math.ceil(projectDuration) + 1) as _, d}
            {#if d % 5 === 0}
              <div class="absolute top-0 bottom-0 border-l border-neutral-100" style="left: {180 + d * 32}px"></div>
            {/if}
          {/each}
        </div>
      </div>

      <!-- Legend -->
      <div class="border-t border-neutral-100 bg-neutral-50 px-5 py-2.5 flex items-center gap-5 text-[10px] text-neutral-500">
        <span class="flex items-center gap-1.5"><span class="inline-block w-4 h-3 rounded bg-neutral-800/80"></span> Standard</span>
        <span class="flex items-center gap-1.5"><span class="inline-block w-4 h-3 rounded bg-red-500/90"></span> Critical Path</span>
        <span class="flex items-center gap-1.5"><span class="inline-block w-4 h-3 rounded border border-dashed border-neutral-300 bg-neutral-100/40"></span> Float/Slack</span>
      </div>
    </section>

  {/if}
</div>

<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { onMount } from "svelte";

  // --- Types ---
  interface TaskSummary {
    id: number; name: string; assigned_role: string; estimated_effort_hours: number | null;
    standard_duration_hours: number | null; crew_size: number | null; equipment_type: string;
    required_materials: { item: string; quantity: string; unit: string; essential: boolean }[];
    category: string;
  }
  interface Activity { id: number; name: string; wbs_code: string; estimated_duration_days: number | null; sort_order: number; task_templates: TaskSummary[]; }
  interface Phase { id: number; name: string; sort_order: number; duration_days: number | null; activities: Activity[]; }
  interface Template { id: number; name: string; phases: Phase[]; }
  interface TemplateListItem { id: number; name: string; template_type_display: string; }
  interface Dependency { from_node_id: string; to_node_id: string; lag_hours: number; }
  interface ScheduleSettings { hours_per_day: number; resource_roles: { role: string; capacity: number; daily_rate: number }[]; }

  interface RoleAggregation {
    role: string; totalHours: number; taskCount: number; headcount: number;
    phases: string[]; peakPhase: string; dailyRate: number;
    totalCost: number;
  }
  interface EquipmentItem { type: string; taskCount: number; phases: string[]; }
  interface MaterialItem { item: string; totalQty: number; unit: string; essential: boolean; taskCount: number; }
  interface PhaseLoad { phase: string; roles: Record<string, number>; totalHours: number; }

  // --- State ---
  let loading = $state(true);
  let templates = $state<TemplateListItem[]>([]);
  let selectedTemplateId = $state<number | null>(null);
  let activeTemplate = $state<Template | null>(null);
  let schedSettings = $state<ScheduleSettings | null>(null);

  // Aggregated data
  let roleAggregations = $state<RoleAggregation[]>([]);
  let equipmentItems = $state<EquipmentItem[]>([]);
  let materialItems = $state<MaterialItem[]>([]);
  let phaseLoads = $state<PhaseLoad[]>([]);

  // Computed
  const totalManHours = $derived(roleAggregations.reduce((s, r) => s + r.totalHours, 0));
  const totalHeadcount = $derived(roleAggregations.reduce((s, r) => s + r.headcount, 0));
  const totalLaborCost = $derived(roleAggregations.reduce((s, r) => s + r.totalCost, 0));
  const uniqueEquipment = $derived(equipmentItems.length);
  const essentialMaterials = $derived(materialItems.filter(m => m.essential).length);
  const peakPhaseLoad = $derived(phaseLoads.length > 0 ? phaseLoads.reduce((max, p) => p.totalHours > max.totalHours ? p : max, phaseLoads[0]) : null);

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
      const [tmpl, sched] = await Promise.all([
        api.get<Template>(`/settings/project-templates/${id}/`),
        api.get<ScheduleSettings>(`/settings/project-templates/${id}/schedule-settings/`),
      ]);
      activeTemplate = tmpl;
      schedSettings = sched;
      aggregate();
    } catch { toast.error("Load failed", "Could not load template."); }
    finally { loading = false; }
  }

  // --- Aggregation Engine ---
  function aggregate() {
    if (!activeTemplate) return;

    const hoursPerDay = schedSettings?.hours_per_day || 9;
    const roleRates = new Map((schedSettings?.resource_roles || []).map(r => [r.role.toLowerCase(), r.daily_rate]));
    const roleCapacities = new Map((schedSettings?.resource_roles || []).map(r => [r.role.toLowerCase(), r.capacity]));

    // Flatten all tasks
    const allTasks: { task: TaskSummary; phaseName: string }[] = [];
    for (const phase of activeTemplate.phases) {
      for (const activity of phase.activities) {
        for (const task of activity.task_templates) {
          allTasks.push({ task, phaseName: phase.name });
        }
      }
    }

    // Role aggregation
    const roleMap = new Map<string, { hours: number; tasks: number; phases: Set<string>; crew: number }>();
    for (const { task, phaseName } of allTasks) {
      const role = task.assigned_role || "Unassigned";
      const entry = roleMap.get(role) || { hours: 0, tasks: 0, phases: new Set(), crew: 0 };
      entry.hours += task.estimated_effort_hours || 0;
      entry.tasks += 1;
      entry.phases.add(phaseName);
      entry.crew = Math.max(entry.crew, task.crew_size || 1);
      roleMap.set(role, entry);
    }

    roleAggregations = Array.from(roleMap.entries()).map(([role, data]) => {
      const phasesArr = Array.from(data.phases);
      const dailyRate = roleRates.get(role.toLowerCase()) || 0;
      const days = data.hours / hoursPerDay;
      return {
        role,
        totalHours: data.hours,
        taskCount: data.tasks,
        headcount: Math.max(data.crew, Math.ceil(data.hours / (hoursPerDay * 20))),
        phases: phasesArr,
        peakPhase: phasesArr[0] || "",
        dailyRate,
        totalCost: dailyRate * days,
      };
    }).sort((a, b) => b.totalHours - a.totalHours);

    // Equipment aggregation
    const equipMap = new Map<string, { tasks: number; phases: Set<string> }>();
    for (const { task, phaseName } of allTasks) {
      if (!task.equipment_type) continue;
      for (const eq of task.equipment_type.split(",").map(s => s.trim()).filter(Boolean)) {
        const entry = equipMap.get(eq) || { tasks: 0, phases: new Set() };
        entry.tasks += 1;
        entry.phases.add(phaseName);
        equipMap.set(eq, entry);
      }
    }
    equipmentItems = Array.from(equipMap.entries()).map(([type, data]) => ({
      type, taskCount: data.tasks, phases: Array.from(data.phases),
    })).sort((a, b) => b.taskCount - a.taskCount);

    // Material aggregation
    const matMap = new Map<string, { qty: number; unit: string; essential: boolean; tasks: number }>();
    for (const { task } of allTasks) {
      for (const mat of (task.required_materials || [])) {
        const key = `${mat.item}||${mat.unit}`;
        const entry = matMap.get(key) || { qty: 0, unit: mat.unit, essential: false, tasks: 0 };
        entry.qty += Number(mat.quantity) || 0;
        if (mat.essential) entry.essential = true;
        entry.tasks += 1;
        matMap.set(key, entry);
      }
    }
    materialItems = Array.from(matMap.entries()).map(([key, data]) => ({
      item: key.split("||")[0], totalQty: data.qty, unit: data.unit, essential: data.essential, taskCount: data.tasks,
    })).sort((a, b) => (a.essential === b.essential ? b.totalQty - a.totalQty : a.essential ? -1 : 1));

    // Phase load (for heatmap)
    const pLoadMap = new Map<string, { roles: Record<string, number>; total: number }>();
    for (const { task, phaseName } of allTasks) {
      const entry = pLoadMap.get(phaseName) || { roles: {}, total: 0 };
      const role = task.assigned_role || "Unassigned";
      entry.roles[role] = (entry.roles[role] || 0) + (task.estimated_effort_hours || 0);
      entry.total += task.estimated_effort_hours || 0;
      pLoadMap.set(phaseName, entry);
    }
    phaseLoads = Array.from(pLoadMap.entries()).map(([phase, data]) => ({
      phase, roles: data.roles, totalHours: data.total,
    }));
  }

  onMount(() => { loadTemplates(); });
</script>

<svelte:head><title>Resource Modeling — Project Planner | developerOS</title></svelte:head>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-700">Project Planning</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Resource Requirement Modeling</h1>
      <p class="mt-1 text-sm text-neutral-500">Consolidated requirements — not assignments. What is needed to execute the template.</p>
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
    <div class="flex gap-3 flex-wrap">
      <div class="rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-center">
        <p class="text-lg font-bold text-neutral-900 tabular-nums">{totalManHours.toLocaleString()}<span class="text-xs font-normal text-neutral-400 ml-0.5">h</span></p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Total Man-Hours</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-center">
        <p class="text-lg font-bold text-neutral-900 tabular-nums">{totalHeadcount}</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Headcount</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-center">
        <p class="text-lg font-bold text-neutral-900 tabular-nums">{uniqueEquipment}</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Equipment Types</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-center">
        <p class="text-lg font-bold text-neutral-900 tabular-nums">{materialItems.length}</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Material Lines</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-center">
        <p class="text-lg font-bold text-neutral-900 tabular-nums">₦{(totalLaborCost / 1000000).toFixed(1)}<span class="text-xs font-normal text-neutral-400">M</span></p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Est. Labor Cost</p>
      </div>
    </div>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-16 text-sm text-neutral-400">Loading...</div>
  {:else if !activeTemplate}
    <div class="rounded-xl border border-neutral-200 bg-white p-12 text-center text-sm text-neutral-500">No template selected.</div>
  {:else}

    <!-- Role Aggregation Table -->
    <section class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
      <div class="border-b border-neutral-100 bg-neutral-50 px-5 py-3">
        <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest">Role Aggregation — Human Capital Requirements</h3>
      </div>
      {#if roleAggregations.length > 0}
        <div class="overflow-x-auto">
          <table class="w-full text-xs">
            <thead>
              <tr class="border-b border-neutral-100">
                <th class="px-5 py-2.5 text-left font-medium text-neutral-500">Role / Skill</th>
                <th class="px-4 py-2.5 text-right font-medium text-neutral-500">Tasks</th>
                <th class="px-4 py-2.5 text-right font-medium text-neutral-500">Total Hours</th>
                <th class="px-4 py-2.5 text-right font-medium text-neutral-500">Headcount</th>
                <th class="px-4 py-2.5 text-right font-medium text-neutral-500">Daily Rate</th>
                <th class="px-4 py-2.5 text-right font-medium text-neutral-500">Est. Cost</th>
                <th class="px-4 py-2.5 text-left font-medium text-neutral-500">Active In</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-50">
              {#each roleAggregations as role}
                <tr class="hover:bg-neutral-50/50">
                  <td class="px-5 py-2.5 font-semibold text-neutral-900">{role.role}</td>
                  <td class="px-4 py-2.5 text-right tabular-nums text-neutral-600">{role.taskCount}</td>
                  <td class="px-4 py-2.5 text-right tabular-nums font-semibold text-neutral-900">{role.totalHours}h</td>
                  <td class="px-4 py-2.5 text-right">
                    <span class="rounded-full bg-neutral-900 px-2 py-0.5 text-[10px] font-bold text-white tabular-nums">{role.headcount}</span>
                  </td>
                  <td class="px-4 py-2.5 text-right tabular-nums text-neutral-500">{role.dailyRate > 0 ? `₦${role.dailyRate.toLocaleString()}` : "—"}</td>
                  <td class="px-4 py-2.5 text-right tabular-nums text-neutral-700 font-medium">{role.totalCost > 0 ? `₦${Math.round(role.totalCost).toLocaleString()}` : "—"}</td>
                  <td class="px-4 py-2.5">
                    <div class="flex flex-wrap gap-1">
                      {#each role.phases as phase}
                        <span class="rounded bg-neutral-100 px-1.5 py-0.5 text-[9px] font-medium text-neutral-500">{phase}</span>
                      {/each}
                    </div>
                  </td>
                </tr>
              {/each}
            </tbody>
            <tfoot>
              <tr class="border-t border-neutral-200 bg-neutral-50">
                <td class="px-5 py-2.5 font-bold text-neutral-900">Total</td>
                <td class="px-4 py-2.5 text-right tabular-nums font-bold text-neutral-900">{roleAggregations.reduce((s, r) => s + r.taskCount, 0)}</td>
                <td class="px-4 py-2.5 text-right tabular-nums font-bold text-neutral-900">{totalManHours}h</td>
                <td class="px-4 py-2.5 text-right tabular-nums font-bold text-neutral-900">{totalHeadcount}</td>
                <td class="px-4 py-2.5"></td>
                <td class="px-4 py-2.5 text-right tabular-nums font-bold text-neutral-900">₦{Math.round(totalLaborCost).toLocaleString()}</td>
                <td class="px-4 py-2.5"></td>
              </tr>
            </tfoot>
          </table>
        </div>
      {:else}
        <div class="p-8 text-center text-xs text-neutral-400">No tasks with assigned roles found. Define roles in Task Templates.</div>
      {/if}
    </section>

    <!-- Equipment & Materials side by side -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Equipment & Tooling -->
      <section class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
        <div class="border-b border-neutral-100 bg-neutral-50 px-5 py-3">
          <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest">Equipment & Tooling</h3>
        </div>
        {#if equipmentItems.length > 0}
          <div class="divide-y divide-neutral-50">
            {#each equipmentItems as eq}
              <div class="px-5 py-3 flex items-center justify-between">
                <div>
                  <p class="text-sm font-semibold text-neutral-900">{eq.type}</p>
                  <div class="flex gap-1 mt-1">
                    {#each eq.phases as phase}
                      <span class="rounded bg-neutral-100 px-1.5 py-0.5 text-[9px] font-medium text-neutral-500">{phase}</span>
                    {/each}
                  </div>
                </div>
                <span class="rounded-full bg-neutral-100 px-2.5 py-0.5 text-[10px] font-semibold text-neutral-600 tabular-nums">{eq.taskCount} task(s)</span>
              </div>
            {/each}
          </div>
        {:else}
          <div class="p-8 text-center text-xs text-neutral-400">No equipment types defined in task templates.</div>
        {/if}
      </section>

      <!-- Consolidated Material BoQ -->
      <section class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
        <div class="border-b border-neutral-100 bg-neutral-50 px-5 py-3 flex items-center justify-between">
          <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest">Consolidated Material BoQ</h3>
          <span class="text-[10px] text-neutral-400">{essentialMaterials} essential, {materialItems.length - essentialMaterials} optional</span>
        </div>
        {#if materialItems.length > 0}
          <div class="overflow-x-auto">
            <table class="w-full text-xs">
              <thead>
                <tr class="border-b border-neutral-100">
                  <th class="px-4 py-2 text-left font-medium text-neutral-500">Material</th>
                  <th class="px-4 py-2 text-right font-medium text-neutral-500">Total Qty</th>
                  <th class="px-4 py-2 text-left font-medium text-neutral-500">Unit</th>
                  <th class="px-4 py-2 text-center font-medium text-neutral-500">Essential</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-50">
                {#each materialItems as mat}
                  <tr class="hover:bg-neutral-50/50">
                    <td class="px-4 py-2 font-medium text-neutral-800">{mat.item}</td>
                    <td class="px-4 py-2 text-right tabular-nums font-semibold text-neutral-900">{mat.totalQty.toLocaleString()}</td>
                    <td class="px-4 py-2 text-neutral-500">{mat.unit}</td>
                    <td class="px-4 py-2 text-center">
                      <span class="rounded-full px-2 py-0.5 text-[9px] font-semibold {mat.essential ? 'bg-emerald-50 text-emerald-700' : 'bg-neutral-100 text-neutral-400'}">{mat.essential ? "Yes" : "No"}</span>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {:else}
          <div class="p-8 text-center text-xs text-neutral-400">No materials defined in task templates.</div>
        {/if}
      </section>
    </div>

    <!-- Utilization Heatmap -->
    <section class="rounded-xl border border-white/60 bg-white/70 p-6 shadow-sm" style="backdrop-filter: blur(8px)">
      <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-4">Resource Demand by Phase — Utilization Heatmap</h3>
      {#if phaseLoads.length > 0}
        {@const maxLoad = Math.max(...phaseLoads.map(p => p.totalHours), 1)}
        {@const allRoles = Array.from(new Set(phaseLoads.flatMap(p => Object.keys(p.roles))))}
        <div class="overflow-x-auto">
          <table class="w-full text-xs">
            <thead>
              <tr class="border-b border-neutral-200">
                <th class="px-4 py-2 text-left font-medium text-neutral-500 sticky left-0 bg-white/70 z-10" style="backdrop-filter: blur(8px)">Phase</th>
                {#each allRoles as role}
                  <th class="px-3 py-2 text-center font-medium text-neutral-500 min-w-[80px]">{role}</th>
                {/each}
                <th class="px-4 py-2 text-right font-bold text-neutral-700">Total</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each phaseLoads as pl}
                <tr>
                  <td class="px-4 py-2.5 font-semibold text-neutral-900 sticky left-0 bg-white/70 z-10" style="backdrop-filter: blur(8px)">
                    <div class="flex items-center gap-2">
                      {pl.phase}
                      {#if peakPhaseLoad && pl.phase === peakPhaseLoad.phase}
                        <span class="rounded-full bg-amber-100 px-1.5 py-0.5 text-[8px] font-bold text-amber-700 uppercase">Peak</span>
                      {/if}
                    </div>
                  </td>
                  {#each allRoles as role}
                    {@const hours = pl.roles[role] || 0}
                    {@const intensity = hours > 0 ? Math.min(hours / maxLoad, 1) : 0}
                    <td class="px-3 py-2.5 text-center">
                      {#if hours > 0}
                        <div class="mx-auto w-14 h-7 rounded-md flex items-center justify-center text-[10px] font-bold tabular-nums"
                          style="background-color: rgba(16, 185, 129, {0.15 + intensity * 0.7}); color: {intensity > 0.5 ? 'white' : 'rgb(6,95,70)'}"
                        >
                          {hours}h
                        </div>
                      {:else}
                        <span class="text-neutral-200">—</span>
                      {/if}
                    </td>
                  {/each}
                  <td class="px-4 py-2.5 text-right tabular-nums font-bold text-neutral-900">{pl.totalHours}h</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {:else}
        <div class="text-center text-xs text-neutral-400 py-8">No phase load data available. Add tasks with roles and effort estimates.</div>
      {/if}
    </section>

  {/if}
</div>

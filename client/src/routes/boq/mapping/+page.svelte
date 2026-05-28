<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { onMount } from "svelte";

  // --- Types ---
  interface BomOption { id: number; bom_number: string; name: string; project: number | null; project_name: string | null; total_estimated_cost: string; item_count: number; }
  interface BomItem { id: number; material_name: string; category: string; section: string; quantity: string; unit_of_measure: string; unit_cost: string; line_total: string; lead_time_days: number; supplier: string; }
  interface BomDetail { id: number; bom_number: string; name: string; project: number | null; project_name: string | null; items: BomItem[]; }
  interface ProjectOption { id: number; name: string; }
  interface Phase { id: number; name: string; sort_order: number; }
  interface Task { id: number; name: string; phase: number; start_date: string | null; end_date: string | null; status: string; }
  interface Mapping {
    id: number; bom: number; bom_item: number; bom_item_name: string; bom_item_unit: string;
    bom_item_unit_cost: string; bom_item_lead_time: number; bom_item_section: string;
    project: number; project_name: string; phase: number | null; phase_name: string | null;
    task: number | null; task_name: string | null; task_start_date: string | null;
    allocated_quantity: string; allocated_cost: string;
    delivery_deadline: string | null; material_status: string;
    has_lead_time_conflict: boolean; notes: string;
  }

  const MATERIAL_ICONS: Record<string, string> = { in_warehouse: "\uD83D\uDCE6", in_transit: "\uD83D\uDE9A", awaiting: "\u23F3" };

  // --- State ---
  let loading = $state(true);
  let boms = $state<BomOption[]>([]);
  let selectedBomId = $state<number | null>(null);
  let activeBom = $state<BomDetail | null>(null);
  let projects = $state<ProjectOption[]>([]);
  let selectedProjectId = $state<number | null>(null);
  let phases = $state<Phase[]>([]);
  let tasks = $state<Task[]>([]);
  let mappings = $state<Mapping[]>([]);

  // Mapping form
  let mappingItem = $state<BomItem | null>(null);
  let mappingPhase = $state("");
  let mappingTask = $state("");
  let mappingQty = $state("");
  let mappingDeadline = $state("");
  let mappingSaving = $state(false);

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  // --- Computed ---
  const mappedItemIds = $derived(new Set(mappings.map(m => m.bom_item)));
  const unmappedItems = $derived(activeBom ? activeBom.items.filter(i => !mappedItemIds.has(i.id)) : []);
  const mappedItems = $derived(activeBom ? activeBom.items.filter(i => mappedItemIds.has(i.id)) : []);

  const totalBudget = $derived(activeBom ? activeBom.items.reduce((s, i) => s + Number(i.line_total || 0), 0) : 0);
  const mappedBudget = $derived(mappings.reduce((s, m) => s + Number(m.allocated_cost || 0), 0));
  const mappedPct = $derived(totalBudget > 0 ? (mappedBudget / totalBudget) * 100 : 0);
  const conflictCount = $derived(mappings.filter(m => m.has_lead_time_conflict).length);

  const phaseTasks = $derived.by(() => {
    const map = new Map<number, { phase: Phase; tasks: Task[] }>();
    for (const p of phases) map.set(p.id, { phase: p, tasks: [] });
    for (const t of tasks) {
      const entry = map.get(t.phase);
      if (entry) entry.tasks.push(t);
    }
    return Array.from(map.values());
  });

  function fmt(n: number): string { return `\u20A6${Math.round(n).toLocaleString()}`; }

  function getMappingsForTask(taskId: number): Mapping[] {
    return mappings.filter(m => m.task === taskId);
  }

  function getMappingsForPhase(phaseId: number): Mapping[] {
    return mappings.filter(m => m.phase === phaseId && !m.task);
  }

  // --- API ---
  async function loadData() {
    loading = true;
    try {
      const [bomRes, projRes] = await Promise.all([
        api.get<{ results: BomOption[] }>("/bom/", { page_size: "100", status: "approved" }),
        api.get<{ results: ProjectOption[] }>("/projects/", { page_size: "100", fields: "id,name" }),
      ]);
      boms = bomRes.results;
      // Also include drafts for mapping
      const draftRes = await api.get<{ results: BomOption[] }>("/bom/", { page_size: "100", status: "draft" });
      boms = [...bomRes.results, ...draftRes.results];
      projects = projRes.results;
    } catch { toast.error("Load failed", "Could not load data."); }
    finally { loading = false; }
  }

  async function selectBom(id: number) {
    selectedBomId = id;
    try {
      activeBom = await api.get<BomDetail>(`/bom/${id}/`);
      // Auto-select project if BoQ is linked
      if (activeBom.project) {
        selectedProjectId = activeBom.project;
        await loadProjectSchedule(activeBom.project);
      }
      await loadMappings();
    } catch { toast.error("Load failed", "Could not load BoQ."); }
  }

  async function selectProject(id: number) {
    selectedProjectId = id;
    await loadProjectSchedule(id);
    await loadMappings();
  }

  async function loadProjectSchedule(projectId: number) {
    try {
      const [phaseRes, taskRes] = await Promise.all([
        api.get<{ results: Phase[] }>(`/projects/${projectId}/phases/`, { page_size: "50" }),
        api.get<{ results: Task[] }>(`/projects/${projectId}/tasks/`, { page_size: "200" }),
      ]);
      phases = phaseRes.results;
      tasks = taskRes.results;
    } catch { phases = []; tasks = []; }
  }

  async function loadMappings() {
    if (!selectedBomId) return;
    try {
      const params: Record<string, string> = { bom: String(selectedBomId), page_size: "500" };
      if (selectedProjectId) params.project = String(selectedProjectId);
      const res = await api.get<{ results: Mapping[] }>("/boq-mapping/", params);
      mappings = res.results;
    } catch { mappings = []; }
  }

  function startMapping(item: BomItem) {
    mappingItem = item;
    mappingQty = item.quantity;
    mappingPhase = "";
    mappingTask = "";
    mappingDeadline = "";
  }

  async function saveMapping() {
    if (!mappingItem || !selectedBomId || !selectedProjectId) return;
    mappingSaving = true;
    try {
      await api.post("/boq-mapping/", {
        bom: selectedBomId,
        bom_item: mappingItem.id,
        project: selectedProjectId,
        phase: mappingPhase ? Number(mappingPhase) : null,
        task: mappingTask ? Number(mappingTask) : null,
        allocated_quantity: Number(mappingQty) || 0,
        delivery_deadline: mappingDeadline || null,
      });
      toast.success("Mapped", `${mappingItem.material_name} linked to schedule.`);
      mappingItem = null;
      await loadMappings();
    } catch { toast.error("Failed", "Could not create mapping."); }
    finally { mappingSaving = false; }
  }

  async function deleteMapping(id: number) {
    try {
      await api.delete(`/boq-mapping/${id}/`);
      await loadMappings();
    } catch { toast.error("Failed", "Could not remove mapping."); }
  }

  async function updateMaterialStatus(id: number, status: string) {
    try {
      await api.patch(`/boq-mapping/${id}/`, { material_status: status });
      await loadMappings();
    } catch { toast.error("Failed", "Could not update status."); }
  }

  onMount(() => { loadData(); });
</script>

<svelte:head><title>BoQ Mapping | developerOS</title></svelte:head>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-700">Bill of Quantities</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Mapping</h1>
      <p class="mt-1 text-sm text-neutral-500">Assign every cost item to a specific task and timeline. The execution bridge between budget and schedule.</p>
    </div>
  </div>

  <!-- Selectors -->
  <div class="flex flex-wrap gap-3">
    <div class="w-64">
      <label class="block text-[10px] font-semibold text-neutral-400 uppercase tracking-wider mb-1">BoQ Source</label>
      <select onchange={(e) => { const id = Number((e.target as HTMLSelectElement).value); if (id) selectBom(id); }} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
        <option value="">Select BoQ...</option>
        {#each boms as bom}<option value={bom.id} selected={bom.id === selectedBomId}>{bom.bom_number} — {bom.name}</option>{/each}
      </select>
    </div>
    <div class="w-64">
      <label class="block text-[10px] font-semibold text-neutral-400 uppercase tracking-wider mb-1">Target Project</label>
      <select onchange={(e) => { const id = Number((e.target as HTMLSelectElement).value); if (id) selectProject(id); }} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
        <option value="">Select project...</option>
        {#each projects as p}<option value={p.id} selected={p.id === selectedProjectId}>{p.name}</option>{/each}
      </select>
    </div>
  </div>

  {#if !activeBom || !selectedProjectId}
    <div class="rounded-xl border border-neutral-200 bg-white p-12 text-center text-sm text-neutral-500">Select a BoQ and a project to begin mapping cost items to the schedule.</div>
  {:else}

    <!-- 3. Unmapped Audit Bar (sticky) -->
    <div class="rounded-xl border border-neutral-200 bg-white/80 px-5 py-4" style="backdrop-filter: blur(12px)">
      <div class="flex items-center gap-6">
        <div class="flex-1">
          <div class="flex items-center justify-between mb-1">
            <span class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Budget Mapped</span>
            <span class="text-xs font-bold tabular-nums {mappedPct >= 100 ? 'text-emerald-600' : mappedPct >= 50 ? 'text-blue-600' : 'text-amber-600'}">{mappedPct.toFixed(0)}%</span>
          </div>
          <div class="h-2.5 rounded-full bg-neutral-100 overflow-hidden">
            <div class="h-full rounded-full transition-all {mappedPct >= 100 ? 'bg-emerald-500' : mappedPct >= 50 ? 'bg-blue-500' : 'bg-amber-500'}" style="width: {Math.min(mappedPct, 100)}%"></div>
          </div>
        </div>
        <div class="text-center px-4">
          <p class="text-lg font-bold text-neutral-900 tabular-nums">{unmappedItems.length}</p>
          <p class="text-[9px] font-semibold text-neutral-400 uppercase">Unmapped</p>
        </div>
        <div class="text-center px-4">
          <p class="text-lg font-bold text-emerald-600 tabular-nums">{mappedItems.length}</p>
          <p class="text-[9px] font-semibold text-neutral-400 uppercase">Mapped</p>
        </div>
        <div class="text-center px-4">
          <p class="text-lg font-bold tabular-nums {conflictCount > 0 ? 'text-amber-600' : 'text-neutral-900'}">{conflictCount}</p>
          <p class="text-[9px] font-semibold text-neutral-400 uppercase">Conflicts</p>
        </div>
        <div class="text-right">
          <p class="text-[9px] text-emerald-600 uppercase tracking-wider font-semibold">Mapped Value</p>
          <p class="text-lg font-bold text-emerald-700 tabular-nums">{fmt(mappedBudget)}</p>
        </div>
      </div>
    </div>

    <!-- 1. Dual-Pane Workspace -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- LEFT: BoQ Source (Unmapped Items) -->
      <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
        <div class="border-b border-neutral-200 bg-neutral-800 px-5 py-3">
          <h3 class="text-[10px] font-semibold text-white uppercase tracking-widest">Unmapped BoQ Items ({unmappedItems.length})</h3>
        </div>
        <div class="max-h-[60vh] overflow-y-auto divide-y divide-neutral-50">
          {#each unmappedItems as item (item.id)}
            <div class="px-4 py-3 hover:bg-neutral-50/50 transition-colors group">
              <div class="flex items-start justify-between gap-2">
                <div class="flex-1 min-w-0">
                  <p class="text-xs font-bold text-neutral-900">{item.material_name}</p>
                  <p class="text-[10px] text-neutral-400 mt-0.5">{item.section} &middot; {Number(item.quantity).toLocaleString()} {item.unit_of_measure} &middot; {fmt(Number(item.line_total))}</p>
                  {#if item.lead_time_days > 0}<p class="text-[10px] text-amber-600 mt-0.5">{item.lead_time_days}d lead time</p>{/if}
                </div>
                <button onclick={() => startMapping(item)} class="shrink-0 rounded-lg bg-emerald-600 px-3 py-1.5 text-[10px] font-medium text-white hover:bg-emerald-700 opacity-0 group-hover:opacity-100 transition-opacity">Map</button>
              </div>
              {#if mappingItem?.id === item.id}
                <div class="mt-3 rounded-lg border border-emerald-200 bg-emerald-50/50 p-3 space-y-2">
                  <div class="grid grid-cols-2 gap-2">
                    <select bind:value={mappingPhase} onchange={() => { mappingTask = ""; }} class="rounded border border-neutral-200 px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-emerald-500">
                      <option value="">Select phase...</option>
                      {#each phases as p}<option value={String(p.id)}>{p.name}</option>{/each}
                    </select>
                    <select bind:value={mappingTask} class="rounded border border-neutral-200 px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-emerald-500">
                      <option value="">Select task...</option>
                      {#each tasks.filter(t => !mappingPhase || t.phase === Number(mappingPhase)) as t}<option value={String(t.id)}>{t.name}</option>{/each}
                    </select>
                  </div>
                  <div class="grid grid-cols-2 gap-2">
                    <input type="number" bind:value={mappingQty} class="rounded border border-neutral-200 px-2 py-1.5 text-xs tabular-nums focus:outline-none focus:ring-1 focus:ring-emerald-500" placeholder="Quantity" />
                    <input type="date" bind:value={mappingDeadline} class="rounded border border-neutral-200 px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-emerald-500" />
                  </div>
                  <div class="flex gap-2">
                    <button onclick={saveMapping} disabled={mappingSaving} class="rounded bg-emerald-600 px-3 py-1 text-[10px] font-medium text-white hover:bg-emerald-700 disabled:opacity-50">{mappingSaving ? "..." : "Confirm"}</button>
                    <button onclick={() => { mappingItem = null; }} class="rounded border border-neutral-200 px-3 py-1 text-[10px] text-neutral-500 hover:bg-neutral-50">Cancel</button>
                  </div>
                </div>
              {/if}
            </div>
          {/each}
          {#if unmappedItems.length === 0}
            <div class="px-4 py-8 text-center text-xs text-emerald-600">All items mapped!</div>
          {/if}
        </div>

        <!-- Mapped (frosted) -->
        {#if mappedItems.length > 0}
          <div class="border-t border-neutral-200 bg-neutral-50/80">
            <div class="px-5 py-2"><span class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Mapped ({mappedItems.length})</span></div>
            <div class="max-h-32 overflow-y-auto divide-y divide-neutral-50">
              {#each mappedItems as item (item.id)}
                <div class="px-4 py-2 opacity-50">
                  <p class="text-[10px] text-neutral-600">{item.material_name} &middot; {Number(item.quantity).toLocaleString()} {item.unit_of_measure}</p>
                </div>
              {/each}
            </div>
          </div>
        {/if}
      </div>

      <!-- RIGHT: Project Schedule -->
      <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
        <div class="border-b border-neutral-200 bg-neutral-800 px-5 py-3">
          <h3 class="text-[10px] font-semibold text-white uppercase tracking-widest">Project Schedule</h3>
        </div>
        <div class="max-h-[60vh] overflow-y-auto">
          {#each phaseTasks as { phase: ph, tasks: pTasks } (ph.id)}
            <div class="border-b border-neutral-100">
              <!-- Phase header -->
              <div class="px-5 py-2.5 bg-neutral-50 flex items-center justify-between">
                <span class="text-xs font-bold text-neutral-800 uppercase tracking-wider">{ph.name}</span>
                {#if getMappingsForPhase(ph.id).length > 0}
                  <span class="rounded-full bg-emerald-100 text-emerald-700 px-2 py-0.5 text-[9px] font-semibold tabular-nums">{getMappingsForPhase(ph.id).length} items</span>
                {/if}
              </div>
              <!-- Phase-level mappings -->
              {#each getMappingsForPhase(ph.id) as m (m.id)}
                <div class="px-6 py-1.5 bg-emerald-50/30 flex items-center justify-between text-[10px] border-l-2 border-l-emerald-400 ml-5">
                  <span class="text-neutral-700"><span class="font-medium">{m.bom_item_name}</span> &middot; {Number(m.allocated_quantity).toLocaleString()} {m.bom_item_unit}</span>
                  <div class="flex items-center gap-2">
                    <span>{MATERIAL_ICONS[m.material_status] || ""}</span>
                    {#if m.has_lead_time_conflict}<span class="text-amber-600 font-bold" title="Lead time conflict">!</span>{/if}
                    <button onclick={() => deleteMapping(m.id)} class="text-neutral-300 hover:text-red-500" aria-label="Remove">&times;</button>
                  </div>
                </div>
              {/each}
              <!-- Tasks -->
              {#each pTasks as t (t.id)}
                <div class="px-5 py-2 ml-4 border-l border-neutral-200">
                  <div class="flex items-center justify-between">
                    <div>
                      <p class="text-xs font-bold text-neutral-800">{t.name}</p>
                      {#if t.start_date}<p class="text-[10px] text-neutral-400">{t.start_date}{t.end_date ? ` → ${t.end_date}` : ""}</p>{/if}
                    </div>
                    {#if getMappingsForTask(t.id).length > 0}
                      <span class="rounded-full bg-emerald-100 text-emerald-700 px-2 py-0.5 text-[9px] font-semibold tabular-nums">{getMappingsForTask(t.id).length}</span>
                    {/if}
                  </div>
                  <!-- Task mappings -->
                  {#each getMappingsForTask(t.id) as m (m.id)}
                    <div class="mt-1 px-3 py-1.5 rounded-lg bg-emerald-50/50 border border-emerald-200 flex items-center justify-between text-[10px] {m.has_lead_time_conflict ? 'border-amber-400 bg-amber-50/50' : ''}">
                      <div>
                        <span class="font-medium text-neutral-800">{m.bom_item_name}</span>
                        <span class="text-neutral-400 ml-1">{Number(m.allocated_quantity).toLocaleString()} {m.bom_item_unit} &middot; {fmt(Number(m.allocated_cost))}</span>
                      </div>
                      <div class="flex items-center gap-1.5">
                        <select value={m.material_status} onchange={(e) => updateMaterialStatus(m.id, (e.target as HTMLSelectElement).value)} onclick={(e) => e.stopPropagation()} class="rounded border border-neutral-200 px-1 py-0.5 text-[9px] bg-white">
                          <option value="awaiting">{MATERIAL_ICONS.awaiting} Awaiting</option>
                          <option value="in_transit">{MATERIAL_ICONS.in_transit} In Transit</option>
                          <option value="in_warehouse">{MATERIAL_ICONS.in_warehouse} In Warehouse</option>
                        </select>
                        {#if m.has_lead_time_conflict}<span class="text-amber-600 font-bold" title="Lead time conflict: material may not arrive in time">!</span>{/if}
                        <button onclick={() => deleteMapping(m.id)} class="text-neutral-300 hover:text-red-500" aria-label="Remove">&times;</button>
                      </div>
                    </div>
                  {/each}
                </div>
              {/each}
            </div>
          {/each}
          {#if phaseTasks.length === 0}
            <div class="px-4 py-8 text-center text-xs text-neutral-400">No phases/tasks found for this project.</div>
          {/if}
        </div>
      </div>
    </div>

  {/if}
</div>

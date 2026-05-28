<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { onMount } from "svelte";

  // --- Types ---
  interface Activity { id: number; name: string; wbs_code: string; estimated_duration_days: number | null; estimated_effort_hours: number | null; sort_order: number; task_templates: TaskSummary[]; }
  interface TaskSummary { id: number; name: string; reference_code: string; estimated_effort_hours: number | null; standard_duration_hours: number | null; assigned_role: string; }
  interface Phase { id: number; name: string; sort_order: number; duration_days: number | null; activities: Activity[]; }
  interface Template { id: number; name: string; template_type_display: string; phases: Phase[]; }
  interface TemplateListItem { id: number; name: string; template_type_display: string; phase_count: number; }
  interface Dependency {
    id: number; template: number;
    from_activity: number | null; from_task: number | null;
    to_activity: number | null; to_task: number | null;
    from_node_id: string; to_node_id: string;
    from_label: string; to_label: string;
    dependency_type: string; dependency_type_display: string;
    lag_hours: number; strength: string; strength_display: string;
    risk_impact: number; notes: string;
  }

  interface GraphNode {
    id: string; label: string; wbsCode: string; duration: number;
    x: number; y: number; phaseIdx: number; type: "activity" | "task";
    dbId: number;
    // CPM fields
    es: number; ef: number; ls: number; lf: number; float: number;
    onCriticalPath: boolean;
  }

  // --- State ---
  let loading = $state(true);
  let templates = $state<TemplateListItem[]>([]);
  let selectedTemplateId = $state<number | null>(null);
  let activeTemplate = $state<Template | null>(null);
  let dependencies = $state<Dependency[]>([]);
  let nodes = $state<GraphNode[]>([]);

  // Controls
  let viewMode = $state<"network" | "gantt">("network");
  let showCriticalPath = $state(true);
  let autoSchedule = $state(true);

  // Connection mode
  let connectingFrom = $state<string | null>(null);

  // Relationship manager
  let showRelManager = $state(false);
  let relDrawerVisible = $state(false);
  let selectedDep = $state<Dependency | null>(null);
  let relForm = $state({ dependency_type: "fs", lag_hours: "0", strength: "hard", risk_impact: "5", notes: "" });
  let relSaving = $state(false);

  // Canvas
  let canvasEl = $state<HTMLDivElement | null>(null);
  let canvasWidth = $state(1200);
  let canvasHeight = $state(600);
  let zoom = $state(1);
  let panX = $state(0);
  let panY = $state(0);

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  // --- Computed ---
  const projectDuration = $derived(nodes.length > 0 ? Math.max(...nodes.map(n => n.ef)) : 0);
  const criticalNodes = $derived(nodes.filter(n => n.onCriticalPath));
  const totalFloat = $derived(nodes.reduce((sum, n) => sum + n.float, 0));

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
      const [tmpl, deps] = await Promise.all([
        api.get<Template>(`/settings/project-templates/${id}/`),
        api.get<{ results: Dependency[] }>(`/settings/project-templates/${id}/dependencies/`, { page_size: "500" }),
      ]);
      activeTemplate = tmpl;
      dependencies = deps.results;
      buildGraph();
    } catch { toast.error("Load failed", "Could not load template."); }
    finally { loading = false; }
  }

  // --- Graph building ---
  function buildGraph() {
    if (!activeTemplate) { nodes = []; return; }

    const allNodes: GraphNode[] = [];
    let col = 0;

    for (const phase of activeTemplate.phases) {
      let row = 0;
      for (const activity of phase.activities) {
        const dur = activity.estimated_duration_days || 1;
        allNodes.push({
          id: `act-${activity.id}`, label: activity.name, wbsCode: activity.wbs_code || `${phase.sort_order + 1}.${activity.sort_order + 1}`,
          duration: dur, x: 80 + col * 260, y: 80 + row * 120, phaseIdx: phase.sort_order,
          type: "activity", dbId: activity.id,
          es: 0, ef: 0, ls: 0, lf: 0, float: 0, onCriticalPath: false,
        });
        row++;
      }
      col++;
    }

    // Run CPM
    if (autoSchedule) runCPM(allNodes, dependencies);
    nodes = allNodes;

    // Size canvas
    if (allNodes.length > 0) {
      canvasWidth = Math.max(1200, Math.max(...allNodes.map(n => n.x)) + 300);
      canvasHeight = Math.max(600, Math.max(...allNodes.map(n => n.y)) + 200);
    }
  }

  // --- Critical Path Method ---
  function runCPM(graphNodes: GraphNode[], deps: Dependency[]) {
    const nodeMap = new Map(graphNodes.map(n => [n.id, n]));
    const adjOut = new Map<string, { target: string; lag: number }[]>();
    const adjIn = new Map<string, { source: string; lag: number }[]>();

    for (const n of graphNodes) {
      adjOut.set(n.id, []);
      adjIn.set(n.id, []);
    }

    for (const d of deps) {
      const from = d.from_node_id;
      const to = d.to_node_id;
      if (nodeMap.has(from) && nodeMap.has(to)) {
        adjOut.get(from)!.push({ target: to, lag: d.lag_hours / 24 });
        adjIn.get(to)!.push({ source: from, lag: d.lag_hours / 24 });
      }
    }

    // Topological sort (Kahn's)
    const inDegree = new Map<string, number>();
    for (const n of graphNodes) inDegree.set(n.id, 0);
    for (const d of deps) {
      if (nodeMap.has(d.to_node_id)) inDegree.set(d.to_node_id, (inDegree.get(d.to_node_id) || 0) + 1);
    }

    const queue: string[] = [];
    for (const [id, deg] of inDegree) { if (deg === 0) queue.push(id); }
    const sorted: string[] = [];

    while (queue.length > 0) {
      const current = queue.shift()!;
      sorted.push(current);
      for (const edge of (adjOut.get(current) || [])) {
        const newDeg = (inDegree.get(edge.target) || 1) - 1;
        inDegree.set(edge.target, newDeg);
        if (newDeg === 0) queue.push(edge.target);
      }
    }

    // Forward pass (ES, EF)
    for (const id of sorted) {
      const node = nodeMap.get(id)!;
      let maxES = 0;
      for (const edge of (adjIn.get(id) || [])) {
        const pred = nodeMap.get(edge.source);
        if (pred) maxES = Math.max(maxES, pred.ef + edge.lag);
      }
      node.es = maxES;
      node.ef = node.es + node.duration;
    }

    // Project duration
    const projectEnd = Math.max(...graphNodes.map(n => n.ef), 0);

    // Backward pass (LS, LF)
    for (let i = sorted.length - 1; i >= 0; i--) {
      const node = nodeMap.get(sorted[i])!;
      let minLF = projectEnd;
      for (const edge of (adjOut.get(node.id) || [])) {
        const succ = nodeMap.get(edge.target);
        if (succ) minLF = Math.min(minLF, succ.ls - edge.lag);
      }
      node.lf = (adjOut.get(node.id) || []).length === 0 ? projectEnd : minLF;
      node.ls = node.lf - node.duration;
      node.float = node.ls - node.es;
      node.onCriticalPath = Math.abs(node.float) < 0.01;
    }
  }

  // --- Dependency CRUD ---
  async function createDependency(fromId: string, toId: string) {
    if (!selectedTemplateId) return;
    const fromAct = fromId.startsWith("act-") ? Number(fromId.replace("act-", "")) : null;
    const fromTask = fromId.startsWith("task-") ? Number(fromId.replace("task-", "")) : null;
    const toAct = toId.startsWith("act-") ? Number(toId.replace("act-", "")) : null;
    const toTask = toId.startsWith("task-") ? Number(toId.replace("task-", "")) : null;

    try {
      await api.post(`/settings/project-templates/${selectedTemplateId}/dependencies/`, {
        template: selectedTemplateId,
        from_activity: fromAct, from_task: fromTask,
        to_activity: toAct, to_task: toTask,
        dependency_type: "fs", lag_hours: 0, strength: "hard", risk_impact: 5,
      });
      toast.success("Dependency created", "Connection has been added.");
      await selectTemplate(selectedTemplateId);
    } catch (err) {
      if (err instanceof ApiError) toast.error("Failed", Object.values(err.fieldErrors).flat().join(" ") || "Could not create dependency.");
      else toast.error("Failed", "Could not create dependency.");
    }
  }

  async function deleteDependency(depId: number) {
    if (!selectedTemplateId) return;
    try {
      await api.delete(`/settings/project-templates/${selectedTemplateId}/dependencies/${depId}/`);
      toast.success("Removed", "Dependency has been removed.");
      await selectTemplate(selectedTemplateId);
    } catch { toast.error("Failed", "Could not remove dependency."); }
  }

  function openRelManager(dep: Dependency) {
    selectedDep = dep;
    relForm = {
      dependency_type: dep.dependency_type, lag_hours: String(dep.lag_hours),
      strength: dep.strength, risk_impact: String(dep.risk_impact), notes: dep.notes,
    };
    showRelManager = true;
    requestAnimationFrame(() => { relDrawerVisible = true; });
  }

  function closeRelManager() {
    relDrawerVisible = false;
    setTimeout(() => { showRelManager = false; selectedDep = null; }, 300);
  }

  async function saveRelation() {
    if (!selectedDep || !selectedTemplateId) return;
    relSaving = true;
    try {
      await api.patch(`/settings/project-templates/${selectedTemplateId}/dependencies/${selectedDep.id}/`, {
        dependency_type: relForm.dependency_type,
        lag_hours: Number(relForm.lag_hours) || 0,
        strength: relForm.strength,
        risk_impact: Number(relForm.risk_impact) || 5,
        notes: relForm.notes,
      });
      toast.success("Updated", "Dependency relationship has been updated.");
      closeRelManager();
      await selectTemplate(selectedTemplateId);
    } catch { toast.error("Failed", "Could not update dependency."); }
    finally { relSaving = false; }
  }

  // --- Node interaction ---
  function startConnect(nodeId: string) {
    connectingFrom = nodeId;
  }

  function endConnect(nodeId: string) {
    if (connectingFrom && connectingFrom !== nodeId) {
      createDependency(connectingFrom, nodeId);
    }
    connectingFrom = null;
  }

  function cancelConnect() { connectingFrom = null; }

  // --- SVG helpers ---
  function edgePath(from: GraphNode, to: GraphNode): string {
    const x1 = from.x + 200;
    const y1 = from.y + 40;
    const x2 = to.x;
    const y2 = to.y + 40;
    const cx = (x1 + x2) / 2;
    return `M${x1},${y1} C${cx},${y1} ${cx},${y2} ${x2},${y2}`;
  }

  function edgeMidpoint(from: GraphNode, to: GraphNode): { x: number; y: number } {
    return { x: (from.x + 200 + to.x) / 2, y: (from.y + 40 + to.y + 40) / 2 };
  }

  onMount(() => { loadTemplates(); });
</script>

<svelte:head><title>Dependency Engine — Project Planner | developerOS</title></svelte:head>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="space-y-6" onkeydown={(e) => { if (e.key === "Escape") cancelConnect(); }}>
  <!-- 1. Engine Control Header -->
  <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">Project Planning</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Dependency Graph Engine</h1>
      <p class="mt-1 text-sm text-neutral-500">Define execution order, calculate critical path, and model parallel vs sequential work.</p>
    </div>
    <div class="flex flex-wrap gap-2">
      <!-- View toggle -->
      <div class="flex rounded-lg border border-neutral-200 bg-white overflow-hidden">
        <button onclick={() => (viewMode = "network")} class="px-3 py-2 text-xs font-medium transition-colors {viewMode === 'network' ? 'bg-neutral-900 text-white' : 'text-neutral-600 hover:bg-neutral-50'}">Network</button>
        <button onclick={() => (viewMode = "gantt")} class="px-3 py-2 text-xs font-medium transition-colors {viewMode === 'gantt' ? 'bg-neutral-900 text-white' : 'text-neutral-600 hover:bg-neutral-50'}">Gantt Logic</button>
      </div>
      <label class="flex items-center gap-2 rounded-lg border border-neutral-200 bg-white px-3 py-2 cursor-pointer">
        <input type="checkbox" bind:checked={autoSchedule} onchange={() => buildGraph()} class="rounded border-neutral-300" />
        <span class="text-xs font-medium text-neutral-700">Auto-Schedule</span>
      </label>
      <label class="flex items-center gap-2 rounded-lg border border-neutral-200 bg-white px-3 py-2 cursor-pointer">
        <input type="checkbox" bind:checked={showCriticalPath} class="rounded border-neutral-300" />
        <span class="text-xs font-medium text-neutral-700">Critical Path</span>
      </label>
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
        <p class="text-lg font-bold text-neutral-900 tabular-nums">{nodes.length}</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Nodes</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-center">
        <p class="text-lg font-bold text-neutral-900 tabular-nums">{dependencies.length}</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Links</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-center">
        <p class="text-lg font-bold tabular-nums {criticalNodes.length > 0 ? 'text-red-600' : 'text-neutral-900'}">{criticalNodes.length}</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Critical</p>
      </div>
    </div>
    {#if connectingFrom}
      <div class="ml-auto flex items-center gap-2 rounded-lg bg-indigo-50 border border-indigo-200 px-3 py-2">
        <span class="text-xs font-medium text-indigo-700">Click a target node to connect</span>
        <button onclick={cancelConnect} class="text-xs font-medium text-indigo-500 hover:text-indigo-800">Cancel</button>
      </div>
    {/if}
  </div>

  <!-- 2. Dependency Workspace (Network Canvas) -->
  {#if loading}
    <div class="flex items-center justify-center py-16 text-sm text-neutral-400">Loading graph...</div>
  {:else if nodes.length === 0}
    <div class="rounded-xl border border-neutral-200 bg-white p-12 text-center text-sm text-neutral-500">
      No activities found. Add activities in the WBS to build the dependency graph.
    </div>
  {:else}
    <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden relative">
      <div bind:this={canvasEl} class="overflow-auto" style="max-height: 70vh">
        <svg
          width={canvasWidth * zoom}
          height={canvasHeight * zoom}
          viewBox="0 0 {canvasWidth} {canvasHeight}"
          class="select-none"
          style="background: repeating-linear-gradient(90deg, transparent, transparent 39px, rgba(0,0,0,0.03) 39px, rgba(0,0,0,0.03) 40px), repeating-linear-gradient(0deg, transparent, transparent 39px, rgba(0,0,0,0.03) 39px, rgba(0,0,0,0.03) 40px)"
        >
          <!-- Phase background lanes -->
          {#if activeTemplate}
            {#each activeTemplate.phases as phase, pi}
              {@const phaseNodes = nodes.filter(n => n.phaseIdx === phase.sort_order)}
              {#if phaseNodes.length > 0}
                {@const minX = Math.min(...phaseNodes.map(n => n.x)) - 20}
                {@const maxY = Math.max(...phaseNodes.map(n => n.y)) + 100}
                <rect x={minX} y="20" width="240" height={maxY} rx="12" fill="rgba(0,0,0,0.02)" stroke="rgba(0,0,0,0.06)" stroke-width="1" />
                <text x={minX + 120} y="45" text-anchor="middle" class="text-[10px] font-semibold fill-neutral-400 uppercase" style="font-family: Raleway, sans-serif; letter-spacing: 0.1em">{phase.name}</text>
              {/if}
            {/each}
          {/if}

          <!-- Dependency edges -->
          {#each dependencies as dep (dep.id)}
            {@const fromNode = nodes.find(n => n.id === dep.from_node_id)}
            {@const toNode = nodes.find(n => n.id === dep.to_node_id)}
            {#if fromNode && toNode}
              {@const isCritical = showCriticalPath && fromNode.onCriticalPath && toNode.onCriticalPath}
              {@const mid = edgeMidpoint(fromNode, toNode)}
              <path
                d={edgePath(fromNode, toNode)}
                fill="none"
                stroke={isCritical ? "#dc2626" : "#94a3b8"}
                stroke-width={isCritical ? 2.5 : 1.5}
                stroke-dasharray={dep.dependency_type === "fs" ? "none" : "6,4"}
                marker-end="url(#arrowhead{isCritical ? '-critical' : ''})"
                class="transition-colors cursor-pointer hover:stroke-indigo-500"
                onclick={() => openRelManager(dep)}
                onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') openRelManager(dep); }}
                role="button"
                tabindex="0"
              />
              <!-- Edge label -->
              <g onclick={() => openRelManager(dep)} onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') openRelManager(dep); }} role="button" tabindex="0" class="cursor-pointer">
                <rect x={mid.x - 16} y={mid.y - 8} width="32" height="16" rx="4" fill="white" stroke={isCritical ? "#dc2626" : "#e2e8f0"} stroke-width="1" />
                <text x={mid.x} y={mid.y + 3} text-anchor="middle" class="text-[9px] font-bold" style="font-family: Raleway, sans-serif" fill={isCritical ? "#dc2626" : "#94a3b8"}>
                  {dep.dependency_type.toUpperCase()}{dep.lag_hours ? `+${dep.lag_hours}h` : ""}
                </text>
              </g>
            {/if}
          {/each}

          <!-- Arrowhead markers -->
          <defs>
            <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
              <path d="M0,0 L8,3 L0,6 Z" fill="#94a3b8" />
            </marker>
            <marker id="arrowhead-critical" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
              <path d="M0,0 L8,3 L0,6 Z" fill="#dc2626" />
            </marker>
          </defs>

          <!-- Activity nodes -->
          {#each nodes as node (node.id)}
            {@const isCritical = showCriticalPath && node.onCriticalPath}
            {@const isConnecting = connectingFrom === node.id}
            <g class="cursor-pointer" onclick={() => { if (connectingFrom) endConnect(node.id); }} onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { if (connectingFrom) endConnect(node.id); } }} role="button" tabindex="0">
              <!-- Node card -->
              <rect
                x={node.x} y={node.y} width="200" height="80" rx="10"
                fill="white" fill-opacity="0.92"
                stroke={isCritical ? "#dc2626" : isConnecting ? "#6366f1" : "#e2e8f0"}
                stroke-width={isCritical || isConnecting ? 2 : 1}
                filter="url(#shadow)"
                style="backdrop-filter: blur(8px)"
              />
              <!-- WBS code badge -->
              <rect x={node.x + 8} y={node.y + 8} width={node.wbsCode.length * 8 + 12} height="18" rx="4" fill={isCritical ? "#fef2f2" : "#f5f5f5"} />
              <text x={node.x + 14} y={node.y + 20} class="text-[10px] font-bold" style="font-family: Raleway, sans-serif" fill={isCritical ? "#dc2626" : "#737373"}>{node.wbsCode}</text>

              <!-- Duration badge -->
              <text x={node.x + 190} y={node.y + 20} text-anchor="end" class="text-[10px] font-semibold" style="font-family: Raleway, sans-serif" fill="#a3a3a3">{node.duration}d</text>

              <!-- Name -->
              <text x={node.x + 12} y={node.y + 42} class="text-[11px] font-semibold" style="font-family: Raleway, sans-serif" fill="#171717">
                {node.label.length > 24 ? node.label.slice(0, 22) + "…" : node.label}
              </text>

              <!-- Float / CPM info -->
              <text x={node.x + 12} y={node.y + 58} class="text-[9px]" style="font-family: Raleway, sans-serif" fill="#a3a3a3">
                ES:{node.es.toFixed(0)} EF:{node.ef.toFixed(0)} Float:{node.float.toFixed(0)}d
              </text>

              <!-- Critical path indicator -->
              {#if isCritical}
                <circle cx={node.x + 190} cy={node.y + 68} r="4" fill="#dc2626">
                  <animate attributeName="opacity" values="1;0.3;1" dur="2s" repeatCount="indefinite" />
                </circle>
              {/if}

              <!-- Connect button -->
              <g onclick={(e) => { e.stopPropagation(); startConnect(node.id); }} onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.stopPropagation(); startConnect(node.id); } }} role="button" tabindex="0" class="cursor-crosshair">
                <circle cx={node.x + 200} cy={node.y + 40} r="8" fill={isConnecting ? "#6366f1" : "#e5e7eb"} stroke="white" stroke-width="2" />
                <text x={node.x + 200} y={node.y + 43} text-anchor="middle" class="text-[8px] font-bold" fill={isConnecting ? "white" : "#9ca3af"}>+</text>
              </g>
            </g>
          {/each}

          <!-- Shadow filter -->
          <defs>
            <filter id="shadow" x="-5%" y="-5%" width="110%" height="110%">
              <feDropShadow dx="0" dy="2" stdDeviation="4" flood-opacity="0.08" />
            </filter>
          </defs>
        </svg>
      </div>

      <!-- Mini-map -->
      <div class="absolute bottom-3 right-3 rounded-lg border border-neutral-200 bg-white/90 p-2 shadow-sm" style="backdrop-filter: blur(4px)">
        <div class="flex items-center gap-2">
          <button onclick={() => { zoom = Math.max(0.3, zoom - 0.1); }} class="rounded px-1.5 py-0.5 text-xs text-neutral-500 hover:bg-neutral-100">−</button>
          <span class="text-[10px] text-neutral-400 tabular-nums w-10 text-center">{Math.round(zoom * 100)}%</span>
          <button onclick={() => { zoom = Math.min(2, zoom + 0.1); }} class="rounded px-1.5 py-0.5 text-xs text-neutral-500 hover:bg-neutral-100">+</button>
          <button onclick={() => { zoom = 1; }} class="rounded px-1.5 py-0.5 text-[10px] text-neutral-400 hover:bg-neutral-100">Reset</button>
        </div>
      </div>

      <!-- Legend -->
      <div class="absolute bottom-3 left-3 flex items-center gap-4 rounded-lg border border-neutral-200 bg-white/90 px-3 py-2 shadow-sm" style="backdrop-filter: blur(4px)">
        <span class="flex items-center gap-1.5 text-[10px] text-neutral-500"><span class="inline-block w-4 h-0.5 bg-neutral-400"></span> FS (Finish→Start)</span>
        <span class="flex items-center gap-1.5 text-[10px] text-neutral-500"><span class="inline-block w-4 h-0.5 border-t border-dashed border-neutral-400"></span> SS / FF / SF</span>
        <span class="flex items-center gap-1.5 text-[10px] text-red-500"><span class="inline-block w-4 h-0.5 bg-red-500"></span> Critical Path</span>
        <span class="flex items-center gap-1.5 text-[10px] text-neutral-500"><span class="inline-block w-2 h-2 rounded-full bg-neutral-200 border border-white"></span> Connect</span>
      </div>
    </div>

    <!-- Dependency List Table -->
    {#if dependencies.length > 0}
      <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
        <div class="px-5 py-3 border-b border-neutral-100 bg-neutral-50">
          <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest">Dependency Register ({dependencies.length})</h3>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-xs">
            <thead>
              <tr class="border-b border-neutral-100">
                <th class="px-4 py-2 text-left font-medium text-neutral-500">From</th>
                <th class="px-4 py-2 text-left font-medium text-neutral-500">To</th>
                <th class="px-4 py-2 text-center font-medium text-neutral-500">Type</th>
                <th class="px-4 py-2 text-right font-medium text-neutral-500">Lag</th>
                <th class="px-4 py-2 text-center font-medium text-neutral-500">Strength</th>
                <th class="px-4 py-2 text-center font-medium text-neutral-500">Risk</th>
                <th class="px-3 py-2 w-16"></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-50">
              {#each dependencies as dep (dep.id)}
                <tr class="hover:bg-neutral-50/50 cursor-pointer" onclick={() => openRelManager(dep)} onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') openRelManager(dep); }} tabindex="0">
                  <td class="px-4 py-2 font-medium text-neutral-800">{dep.from_label}</td>
                  <td class="px-4 py-2 font-medium text-neutral-800">{dep.to_label}</td>
                  <td class="px-4 py-2 text-center"><span class="rounded bg-neutral-100 px-1.5 py-0.5 font-mono font-bold text-neutral-600">{dep.dependency_type.toUpperCase()}</span></td>
                  <td class="px-4 py-2 text-right tabular-nums text-neutral-500">{dep.lag_hours}h</td>
                  <td class="px-4 py-2 text-center"><span class="rounded-full px-2 py-0.5 text-[10px] font-semibold {dep.strength === 'hard' ? 'bg-red-50 text-red-700' : 'bg-neutral-100 text-neutral-500'}">{dep.strength}</span></td>
                  <td class="px-4 py-2 text-center tabular-nums text-neutral-500">{dep.risk_impact}/10</td>
                  <td class="px-3 py-2">
                    <button onclick={(e) => { e.stopPropagation(); deleteDependency(dep.id); }} class="rounded p-1 text-neutral-300 hover:text-red-500 transition-colors" title="Delete">
                      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" /></svg>
                    </button>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </div>
    {/if}
  {/if}
</div>

<!-- 3. Relationship Manager Drawer -->
{#if showRelManager && selectedDep}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm transition-opacity duration-300" style="opacity: {relDrawerVisible ? 1 : 0}" onclick={closeRelManager} onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') closeRelManager(); }} role="button" tabindex="0"></div>
  <aside class="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col bg-white/95 backdrop-blur-xl shadow-2xl border-l border-neutral-200/60 transition-transform duration-300" style="transform: translateX({relDrawerVisible ? '0%' : '100%'})">
    <div class="flex items-center justify-between border-b border-neutral-100 px-6 py-4">
      <h2 class="text-base font-semibold text-neutral-900">Relationship Manager</h2>
      <button onclick={closeRelManager} class="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-900" aria-label="Close">
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
      </button>
    </div>

    <div class="flex-1 overflow-y-auto px-6 py-5 space-y-5">
      <!-- Connection summary -->
      <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-4">
        <div class="flex items-center gap-3">
          <div class="flex-1">
            <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">From</p>
            <p class="text-sm font-bold text-neutral-900 mt-0.5">{selectedDep.from_label}</p>
          </div>
          <svg class="w-5 h-5 text-neutral-300 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" /></svg>
          <div class="flex-1 text-right">
            <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">To</p>
            <p class="text-sm font-bold text-neutral-900 mt-0.5">{selectedDep.to_label}</p>
          </div>
        </div>
      </div>

      <!-- Dependency Type -->
      <label class="block text-sm font-medium text-neutral-700">
        <span class="mb-1.5 block text-xs">Dependency Type</span>
        <select bind:value={relForm.dependency_type} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
          <option value="fs">Finish-to-Start (FS)</option>
          <option value="ss">Start-to-Start (SS)</option>
          <option value="ff">Finish-to-Finish (FF)</option>
          <option value="sf">Start-to-Finish (SF)</option>
        </select>
      </label>

      <!-- Lag Time -->
      <label class="block text-sm font-medium text-neutral-700">
        <span class="mb-1.5 block text-xs">Lag / Lead Time (hours)</span>
        <input type="number" bind:value={relForm.lag_hours} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="0" />
        <p class="mt-1 text-[10px] text-neutral-400">Positive = delay (e.g., +24h drying time). Negative = lead time (overlap).</p>
      </label>

      <!-- Strength -->
      <label class="block text-sm font-medium text-neutral-700">
        <span class="mb-1.5 block text-xs">Dependency Strength</span>
        <select bind:value={relForm.strength} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
          <option value="hard">Hard — Physical constraint (cannot override)</option>
          <option value="soft">Soft — Preferred sequence (can be reordered)</option>
        </select>
      </label>

      <!-- Risk Impact -->
      <label class="block text-sm font-medium text-neutral-700">
        <span class="mb-1.5 block text-xs">Risk Impact (1–10)</span>
        <input type="range" min="1" max="10" bind:value={relForm.risk_impact} class="w-full accent-neutral-900" />
        <div class="flex justify-between text-[10px] text-neutral-400 mt-1">
          <span>Low risk</span>
          <span class="font-bold text-neutral-700">{relForm.risk_impact}</span>
          <span>High risk</span>
        </div>
      </label>

      <!-- Notes -->
      <label class="block text-sm font-medium text-neutral-700">
        <span class="mb-1.5 block text-xs">Notes</span>
        <textarea bind:value={relForm.notes} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none" placeholder="e.g., Concrete curing requires 48h minimum before formwork removal"></textarea>
      </label>
    </div>

    <div class="flex items-center justify-end gap-3 border-t border-neutral-100 px-6 py-4">
      <button onclick={() => { if (selectedDep) deleteDependency(selectedDep.id); closeRelManager(); }} class="mr-auto rounded-lg border border-red-200 px-3 py-2 text-xs font-medium text-red-600 hover:bg-red-50">Delete</button>
      <button onclick={closeRelManager} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      <button onclick={saveRelation} disabled={relSaving} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50">{relSaving ? "Saving..." : "Save"}</button>
    </div>
  </aside>
{/if}

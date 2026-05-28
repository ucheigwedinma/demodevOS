<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import { onMount } from "svelte";

  interface ReorderAlert { item_name: string; item_sku: string; warehouse: string; on_hand: string; reorder_level: string; }
  interface CategoryBreakdown { category: string; total_qty: string; total_value: string; }
  interface IssueSummary { id: number; issue_number: string; project_name: string; phase_name: string; warehouse_name: string; status: string; requested_by_name: string; requested_date: string; line_count: number; total_value: string; }
  interface WastageAlert { project: string; category: string; boq_estimate: string; issued_total: string; over_pct: number; severity: string; }
  interface CrewEfficiency { crew: string; total_issues: number; completed: number; efficiency_pct: number; }
  interface DashboardData {
    daily_issue_value: string; daily_issue_qty: string; daily_issue_count: number;
    open_requests: number;
    top_consumed_category: { category: string; total_qty: string; total_value: string } | null;
    category_breakdown: CategoryBreakdown[];
    reorder_alerts: ReorderAlert[];
    recent_issues: IssueSummary[];
    wastage_alerts: WastageAlert[];
    crew_efficiency: CrewEfficiency[];
  }
  interface IssueLine { id: number; item: number; item_name: string; item_sku: string; item_category: string; requested_quantity: string; issued_quantity: string; unit_of_measure: string; unit_cost: string; line_value: string; purpose: string; }
  interface IssueDetail extends IssueSummary { notes: string; purpose: string; cost_code: string; approved_by: string; approved_date: string | null; issued_by: string; issued_date: string | null; lines: IssueLine[]; }

  const STATUS_COLORS: Record<string, string> = {
    requested: "bg-amber-100 text-amber-700", approved: "bg-blue-100 text-blue-700",
    issued: "bg-emerald-100 text-emerald-700", partially_issued: "bg-yellow-100 text-yellow-700",
    rejected: "bg-red-100 text-red-700", cancelled: "bg-neutral-100 text-neutral-400",
  };

  let loading = $state(true);
  let data = $state<DashboardData | null>(null);

  // Detail drawer
  let showDetail = $state(false);
  let detail = $state<IssueDetail | null>(null);
  let detailLoading = $state(false);

  // Create modal
  let showCreate = $state(false);
  let createSaving = $state(false);
  let projects = $state<{ id: number; name: string }[]>([]);
  let phases = $state<{ id: number; name: string }[]>([]);
  let warehouses = $state<{ id: number; name: string }[]>([]);
  let items = $state<{ id: number; name: string; sku: string; default_unit_cost: string }[]>([]);
  let createForm = $state({ project: "", phase: "", warehouse: "", purpose: "", cost_code: "", notes: "", work_package: "", requesting_crew: "" as string, required_date: "" });
  let createLines = $state<{ item: string; requested_quantity: string; unit_of_measure: string; purpose: string; stock_on_hand: string; stock_status: string }[]>([]);
  let workPackages = $state<{ id: number; name: string }[]>([]);

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  // Material Issue Slip (MIS)
  let showMIS = $state(false);
  let misData = $state<IssueDetail | null>(null);

  function openMIS(issue: IssueDetail) {
    misData = issue;
    showMIS = true;
  }

  // Signature pad
  let sigCanvas = $state<HTMLCanvasElement | null>(null);
  let sigCtx = $state<CanvasRenderingContext2D | null>(null);
  let sigDrawing = $state(false);
  let sigSigned = $state(false);

  function initSignaturePad(canvas: HTMLCanvasElement) {
    sigCanvas = canvas;
    sigCtx = canvas.getContext("2d");
    if (!sigCtx) return;
    sigCtx.lineWidth = 2;
    sigCtx.lineCap = "round";
    sigCtx.strokeStyle = "#171717";

    const getPos = (e: MouseEvent | TouchEvent) => {
      const rect = canvas.getBoundingClientRect();
      const touch = "touches" in e ? e.touches[0] : e;
      return { x: touch.clientX - rect.left, y: touch.clientY - rect.top };
    };

    const start = (e: MouseEvent | TouchEvent) => {
      e.preventDefault();
      sigDrawing = true;
      const p = getPos(e);
      sigCtx!.beginPath();
      sigCtx!.moveTo(p.x, p.y);
    };
    const move = (e: MouseEvent | TouchEvent) => {
      if (!sigDrawing) return;
      e.preventDefault();
      const p = getPos(e);
      sigCtx!.lineTo(p.x, p.y);
      sigCtx!.stroke();
      sigSigned = true;
    };
    const end = () => { sigDrawing = false; };

    canvas.addEventListener("mousedown", start);
    canvas.addEventListener("mousemove", move);
    canvas.addEventListener("mouseup", end);
    canvas.addEventListener("mouseleave", end);
    canvas.addEventListener("touchstart", start, { passive: false });
    canvas.addEventListener("touchmove", move, { passive: false });
    canvas.addEventListener("touchend", end);
  }

  function clearSignature() {
    if (sigCtx && sigCanvas) {
      sigCtx.clearRect(0, 0, sigCanvas.width, sigCanvas.height);
      sigSigned = false;
    }
  }

  function getSignatureDataUrl(): string | null {
    if (!sigCanvas || !sigSigned) return null;
    return sigCanvas.toDataURL("image/png");
  }

  function printMIS() {
    const el = document.getElementById("mis-print-area");
    if (!el) return;
    const w = window.open("", "_blank", "width=800,height=600");
    if (!w) return;
    w.document.write(`<html><head><title>MIS — ${misData?.issue_number}</title><style>
      body { font-family: 'Raleway', Arial, sans-serif; padding: 24px; color: #1a1a1a; font-size: 12px; }
      table { width: 100%; border-collapse: collapse; margin: 16px 0; }
      th, td { border: 1px solid #d4d4d4; padding: 6px 10px; text-align: left; }
      th { background: #f5f5f5; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; }
      .sig-line { border-top: 1px solid #a3a3a3; padding-top: 6px; font-size: 10px; color: #737373; margin-top: 4px; }
      @media print { body { padding: 0; } }
    </style></head><body>${el.innerHTML}</body></html>`);
    w.document.close();
    w.print();
  }

  async function loadDashboard() {
    loading = true;
    try {
      data = await api.get<DashboardData>("/material-issues/dashboard/");
    } catch { toast.error("Load failed", "Could not load issue dashboard."); }
    finally { loading = false; }
  }

  async function loadOptions() {
    try {
      const [pRes, wRes, iRes] = await Promise.all([
        api.get<{ results: { id: number; name: string }[] }>("/projects/", { page_size: "100" }),
        api.get<{ results: { id: number; name: string }[] }>("/inventory/warehouses/", { page_size: "100" }),
        api.get<{ results: any[] }>("/inventory/items/", { page_size: "200", is_active: "true" }),
      ]);
      projects = pRes.results;
      warehouses = wRes.results;
      items = iRes.results.map((i: any) => ({ id: i.id, name: i.name, sku: i.sku, default_unit_cost: i.default_unit_cost || "0" }));
    } catch { /* optional */ }
  }

  async function loadPhases(projectId: string) {
    if (!projectId) { phases = []; workPackages = []; return; }
    try {
      const [phRes, wpRes] = await Promise.all([
        api.get<{ results: { id: number; name: string }[] }>(`/projects/${projectId}/phases/`, { page_size: "50" }),
        api.get<{ results: { id: number; name: string }[] }>(`/projects/work-packages/`, { project: projectId, page_size: "50" }),
      ]);
      phases = phRes.results;
      workPackages = wpRes.results;
    } catch { phases = []; workPackages = []; }
  }

  async function checkLineStock(idx: number) {
    const line = createLines[idx];
    if (!line.item || !createForm.warehouse) { line.stock_on_hand = "—"; line.stock_status = ""; return; }
    try {
      const res = await api.get<{ results: any[] }>("/inventory/stocks/", { item: line.item, warehouse: createForm.warehouse, page_size: "1" });
      if (res.results.length > 0) {
        const qty = Number(res.results[0].quantity_on_hand || 0);
        line.stock_on_hand = String(qty);
        line.stock_status = qty >= Number(line.requested_quantity) ? "sufficient" : qty > 0 ? "low" : "out";
      } else {
        line.stock_on_hand = "0";
        line.stock_status = "out";
      }
    } catch { line.stock_on_hand = "?"; line.stock_status = ""; }
    createLines = [...createLines]; // trigger reactivity
  }

  async function openDetail(id: number) {
    showDetail = true;
    detailLoading = true;
    try {
      detail = await api.get<IssueDetail>(`/material-issues/${id}/`);
    } catch { toast.error("Load failed", "Could not load issue details."); }
    finally { detailLoading = false; }
  }

  function addLine() {
    createLines = [...createLines, { item: "", requested_quantity: "1", unit_of_measure: "ea", purpose: "", stock_on_hand: "—", stock_status: "" }];
  }
  function removeLine(idx: number) {
    createLines = createLines.filter((_, i) => i !== idx);
  }

  async function createIssue() {
    if (!createForm.project || !createForm.warehouse) { toast.error("Required", "Project and warehouse are required."); return; }
    if (createLines.length === 0) { toast.error("Required", "Add at least one material line."); return; }
    createSaving = true;
    try {
      const payload: Record<string, unknown> = { ...createForm, project: Number(createForm.project), warehouse: Number(createForm.warehouse) };
      if (createForm.phase) payload.phase = Number(createForm.phase); else delete payload.phase;
      const created = await api.post<{ id: number; issue_number: string }>("/material-issues/", payload);
      for (const line of createLines) {
        if (!line.item) continue;
        const itemData = items.find(i => String(i.id) === line.item);
        await api.post(`/material-issues/${created.id}/lines/`, {
          item: Number(line.item),
          requested_quantity: Number(line.requested_quantity),
          unit_of_measure: line.unit_of_measure,
          unit_cost: itemData?.default_unit_cost || 0,
          purpose: line.purpose,
        });
      }
      toast.success("Created", `Issue ${created.issue_number} created with ${createLines.length} line(s).`);
      showCreate = false;
      createForm = { project: "", phase: "", warehouse: "", purpose: "", cost_code: "", notes: "" };
      createLines = [];
      await loadDashboard();
    } catch (err) {
      if (err instanceof ApiError) toast.error("Failed", Object.values(err.fieldErrors).flat().join(" ") || "Check the form.");
      else toast.error("Failed", "Could not create issue request.");
    } finally { createSaving = false; }
  }

  async function approveIssue() {
    if (!detail) return;
    try {
      await api.post(`/material-issues/${detail.id}/approve/`, {});
      toast.success("Approved", "Issue approved.");
      await openDetail(detail.id);
      await loadDashboard();
    } catch (err) {
      if (err instanceof ApiError) toast.error("Failed", err.data?.detail || "Cannot approve.");
      else toast.error("Failed", "Could not approve.");
    }
  }

  async function issueMaterials() {
    if (!detail) return;
    try {
      const res = await api.post<{ detail: string; issue: IssueDetail }>(`/material-issues/${detail.id}/issue-materials/`);
      toast.success("Issued", res.detail);
      const refreshed = await api.get<IssueDetail>(`/material-issues/${detail.id}/`);
      detail = refreshed;
      openMIS(refreshed);
      await loadDashboard();
    } catch (err) {
      if (err instanceof ApiError) toast.error("Failed", err.data?.detail || "Cannot issue.");
      else toast.error("Failed", "Could not issue materials.");
    }
  }

  function devFillIssue() {
    if (projects.length) createForm.project = String(projects[Math.floor(Math.random() * projects.length)].id);
    if (warehouses.length) createForm.warehouse = String(warehouses[Math.floor(Math.random() * warehouses.length)].id);
    createForm.purpose = ["Foundation blockwork — Zone A", "Roof truss installation", "MEP first fix — electrical", "Finishing works — tiling"][Math.floor(Math.random() * 4)];
    createForm.cost_code = `CC-${Math.floor(Math.random() * 900 + 100)}`;
    createForm.requesting_crew = ["Steel Fixers Team A", "Masons Team B", "Electricians Team C", "Plumbers Team D"][Math.floor(Math.random() * 4)];
    createForm.required_date = new Date(Date.now() + (Math.floor(Math.random() * 5) + 1) * 86400000).toISOString().split("T")[0];
    if (workPackages.length) createForm.work_package = String(workPackages[Math.floor(Math.random() * workPackages.length)].id);
    createLines = [];
    const count = Math.floor(Math.random() * 3) + 2;
    for (let i = 0; i < count && i < items.length; i++) {
      const item = items[Math.floor(Math.random() * items.length)];
      createLines.push({ item: String(item.id), requested_quantity: String(Math.floor(Math.random() * 50 + 5)), unit_of_measure: "ea", purpose: "", stock_on_hand: "—", stock_status: "" });
    }
  }

  $effect(() => {
    if (showMIS && sigCanvas && !sigCtx) {
      // Small delay to ensure canvas is rendered
      setTimeout(() => { if (sigCanvas) initSignaturePad(sigCanvas); }, 100);
    }
    if (!showMIS) { sigCtx = null; sigSigned = false; }
  });

  onMount(() => { loadDashboard(); loadOptions(); });
</script>

<svelte:head><title>Issue to Construction | developerOS</title></svelte:head>

<div class="space-y-5">
  <!-- Header -->
  <div class="flex items-start justify-between gap-3">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-pink-600">Material Management</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Issue to Construction</h1>
      <p class="mt-1 text-sm text-neutral-500">Track material outflow from warehouse to site. Prevents wastage, ensures BoQ-accurate consumption.</p>
    </div>
    <button onclick={() => { showCreate = true; addLine(); }} class="rounded-lg bg-pink-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-pink-700 shadow-sm whitespace-nowrap">+ New Issue Request</button>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-20"><div class="h-7 w-7 rounded-full border-2 border-neutral-200 border-t-neutral-900 animate-spin"></div></div>
  {:else if data}

    <!-- Issue Command Center (HUD) -->
    <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <!-- Daily Issue Volume -->
      <div class="rounded-xl border border-emerald-200 bg-emerald-50/80 p-4 text-center" style="backdrop-filter: blur(10px)">
        <p class="text-[9px] font-semibold text-emerald-400 uppercase tracking-wider">Daily Issue Volume</p>
        <p class="mt-1 text-lg font-bold text-emerald-700 tabular-nums">{currency.format(Number(data.daily_issue_value))}</p>
        <p class="text-[9px] text-emerald-400">{data.daily_issue_count} transaction(s) today</p>
      </div>

      <!-- Open Requests -->
      <div class="rounded-xl border {data.open_requests > 0 ? 'border-amber-300 bg-amber-50/80' : 'border-neutral-200 bg-white'} p-4 text-center {data.open_requests > 0 ? 'animate-pulse' : ''}" style="backdrop-filter: blur(10px)">
        <p class="text-[9px] font-semibold {data.open_requests > 0 ? 'text-amber-500' : 'text-neutral-400'} uppercase tracking-wider">Open Requests</p>
        <p class="mt-1 text-2xl font-bold {data.open_requests > 0 ? 'text-amber-700' : 'text-neutral-900'} tabular-nums">{data.open_requests}</p>
        <p class="text-[9px] {data.open_requests > 0 ? 'text-amber-400' : 'text-neutral-400'}">awaiting approval</p>
      </div>

      <!-- Top Consumed Category -->
      <div class="rounded-xl border border-neutral-200 bg-white/80 p-4 text-center" style="backdrop-filter: blur(10px)">
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Top Consumed</p>
        {#if data.top_consumed_category}
          <p class="mt-1 text-sm font-bold text-neutral-900 capitalize">{data.top_consumed_category.category.replace(/_/g, " ")}</p>
          <p class="text-[9px] text-neutral-400">{currency.format(Number(data.top_consumed_category.total_value))} (7d)</p>
        {:else}
          <p class="mt-1 text-sm text-neutral-400">No data</p>
        {/if}
      </div>

      <!-- Inventory Health -->
      <div class="rounded-xl border {data.reorder_alerts.length > 0 ? 'border-red-200 bg-red-50/80' : 'border-emerald-200 bg-emerald-50/80'} p-4 text-center" style="backdrop-filter: blur(10px)">
        <p class="text-[9px] font-semibold {data.reorder_alerts.length > 0 ? 'text-red-400' : 'text-emerald-400'} uppercase tracking-wider">Inventory Health</p>
        <p class="mt-1 text-2xl font-bold {data.reorder_alerts.length > 0 ? 'text-red-700' : 'text-emerald-700'} tabular-nums">{data.reorder_alerts.length}</p>
        <p class="text-[9px] {data.reorder_alerts.length > 0 ? 'text-red-400' : 'text-emerald-400'}">{data.reorder_alerts.length > 0 ? 'items at reorder' : 'all healthy'}</p>
      </div>
    </div>

    <!-- Reorder Alerts (if any) -->
    {#if data.reorder_alerts.length > 0}
      <div class="rounded-xl border border-red-200 bg-red-50/50 px-5 py-3" style="backdrop-filter: blur(12px)">
        <h3 class="text-[9px] font-bold text-red-500 uppercase tracking-widest mb-2">Reorder Alerts — Items Below Safety Stock</h3>
        <div class="flex flex-wrap gap-2">
          {#each data.reorder_alerts as alert}
            <span class="rounded-lg border border-red-200 bg-white px-3 py-1.5 text-[10px]">
              <span class="font-bold text-red-800">{alert.item_name}</span>
              <span class="text-red-500 ml-1">({alert.on_hand}/{alert.reorder_level})</span>
              <span class="text-neutral-400 ml-1">@ {alert.warehouse}</span>
            </span>
          {/each}
        </div>
      </div>
    {/if}

    <!-- Wastage Watcher -->
    {#if data.wastage_alerts.length > 0}
      <section class="rounded-xl border border-amber-300 bg-amber-50/50 overflow-hidden" style="backdrop-filter: blur(10px)">
        <div class="border-b border-amber-200 bg-amber-100/50 px-5 py-3 flex items-center gap-2">
          <svg class="h-4 w-4 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" /></svg>
          <h3 class="text-[10px] font-bold text-amber-700 uppercase tracking-widest">Wastage Watcher — Over-Consumption Alerts</h3>
        </div>
        <div class="divide-y divide-amber-100">
          {#each data.wastage_alerts as alert}
            <div class="px-5 py-3 flex items-center gap-4">
              <div class="shrink-0">
                <span class="inline-flex items-center justify-center h-10 w-10 rounded-full {alert.severity === 'critical' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}">
                  <span class="text-sm font-bold tabular-nums">+{alert.over_pct}%</span>
                </span>
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-sm {alert.severity === 'critical' ? 'text-red-800' : 'text-amber-800'} font-semibold">
                  Warning: {alert.over_pct}% Over-consumption on <span class="capitalize">{alert.category.replace(/_/g, " ")}</span>
                </p>
                <p class="text-[10px] text-amber-600 mt-0.5">
                  Project: {alert.project} | BoQ Estimate: {currency.format(Number(alert.boq_estimate))} | Issued: {currency.format(Number(alert.issued_total))}
                </p>
              </div>
              <span class="rounded-full px-2 py-0.5 text-[9px] font-bold uppercase shrink-0 {alert.severity === 'critical' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'}">{alert.severity}</span>
            </div>
          {/each}
        </div>
      </section>
    {/if}

    <!-- Crew Efficiency + Category Breakdown + Recent Issues -->
    {#if data.crew_efficiency.length > 0}
      <div class="grid gap-4 md:grid-cols-3">
        <!-- Crew Efficiency Chart -->
        <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden" style="backdrop-filter: blur(10px)">
          <div class="border-b border-neutral-100 bg-neutral-50 px-4 py-2.5">
            <h3 class="text-[9px] font-bold text-neutral-500 uppercase tracking-widest">Crew Efficiency — Issue to Completion</h3>
          </div>
          <div class="p-4 space-y-3">
            {#each data.crew_efficiency as crew}
              <div>
                <div class="flex items-center justify-between mb-1">
                  <span class="text-xs font-medium text-neutral-900 truncate">{crew.crew}</span>
                  <span class="text-[10px] font-bold tabular-nums {crew.efficiency_pct >= 80 ? 'text-emerald-700' : crew.efficiency_pct >= 50 ? 'text-amber-700' : 'text-red-700'}">{crew.efficiency_pct}%</span>
                </div>
                <div class="h-2 rounded-full bg-neutral-100 overflow-hidden">
                  <div class="h-full rounded-full transition-all {crew.efficiency_pct >= 80 ? 'bg-emerald-500' : crew.efficiency_pct >= 50 ? 'bg-amber-500' : 'bg-red-500'}" style="width: {crew.efficiency_pct}%"></div>
                </div>
                <p class="text-[9px] text-neutral-400 mt-0.5">{crew.completed}/{crew.total_issues} issues completed</p>
              </div>
            {/each}
          </div>
        </div>

        <!-- Category Breakdown (merged into this grid) -->
        <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
          <div class="border-b border-neutral-100 bg-neutral-50 px-4 py-2.5">
            <h3 class="text-[9px] font-bold text-neutral-500 uppercase tracking-widest">Consumption by Category (7d)</h3>
          </div>
          {#if data.category_breakdown.length === 0}
            <div class="p-4 text-center text-xs text-neutral-400">No issues this week.</div>
          {:else}
            <div class="divide-y divide-neutral-50 px-4">
              {#each data.category_breakdown as cat}
                <div class="py-2.5 flex items-center justify-between">
                  <span class="text-xs text-neutral-700 capitalize font-medium">{cat.category.replace(/_/g, " ")}</span>
                  <span class="text-xs font-bold text-neutral-900 tabular-nums">{currency.format(Number(cat.total_value))}</span>
                </div>
              {/each}
            </div>
          {/if}
        </div>

        <!-- Recent Issues (takes remaining space) -->
        <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
          <div class="border-b border-neutral-100 bg-neutral-50 px-4 py-2.5">
            <h3 class="text-[9px] font-bold text-neutral-500 uppercase tracking-widest">Recent Issues</h3>
          </div>
          <div class="divide-y divide-neutral-50 max-h-64 overflow-y-auto">
            {#each data.recent_issues.slice(0, 6) as issue}
              <button type="button" onclick={() => openDetail(issue.id)} class="w-full text-left px-4 py-2.5 hover:bg-neutral-50 transition-colors">
                <div class="flex items-center justify-between">
                  <span class="text-xs font-semibold text-neutral-900">{issue.issue_number}</span>
                  <span class="rounded-full border px-2 py-0.5 text-[9px] font-semibold {STATUS_COLORS[issue.status] || ''}">{issue.status.replace(/_/g, " ")}</span>
                </div>
                <p class="text-[10px] text-neutral-500 mt-0.5">{issue.project_name} | {currency.format(Number(issue.total_value || 0))}</p>
              </button>
            {/each}
          </div>
        </div>
      </div>
    {/if}

    <!-- Category Breakdown + Recent Issues (fallback if no crew data) -->
    {#if data.crew_efficiency.length === 0}
    <div class="grid gap-4 md:grid-cols-3">
      <!-- Category Breakdown -->
      <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
        <div class="border-b border-neutral-100 bg-neutral-50 px-4 py-2.5">
          <h3 class="text-[9px] font-bold text-neutral-500 uppercase tracking-widest">Consumption by Category (7d)</h3>
        </div>
        {#if data.category_breakdown.length === 0}
          <div class="p-4 text-center text-xs text-neutral-400">No issues this week.</div>
        {:else}
          <div class="divide-y divide-neutral-50 px-4">
            {#each data.category_breakdown as cat}
              <div class="py-2.5 flex items-center justify-between">
                <span class="text-xs text-neutral-700 capitalize font-medium">{cat.category.replace(/_/g, " ")}</span>
                <span class="text-xs font-bold text-neutral-900 tabular-nums">{currency.format(Number(cat.total_value))}</span>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Recent Issues -->
      <div class="md:col-span-2 rounded-xl border border-neutral-200 bg-white overflow-hidden">
        <div class="border-b border-neutral-100 bg-neutral-50 px-4 py-2.5">
          <h3 class="text-[9px] font-bold text-neutral-500 uppercase tracking-widest">Recent Issue Requests</h3>
        </div>
        {#if data.recent_issues.length === 0}
          <div class="p-6 text-center text-xs text-neutral-400">No issue requests yet.</div>
        {:else}
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead><tr class="border-b border-neutral-100">
                <th class="px-4 py-2 text-left text-[10px] font-semibold text-neutral-500 uppercase">Issue #</th>
                <th class="px-4 py-2 text-left text-[10px] font-semibold text-neutral-500 uppercase">Project</th>
                <th class="px-4 py-2 text-center text-[10px] font-semibold text-neutral-500 uppercase">Status</th>
                <th class="px-4 py-2 text-center text-[10px] font-semibold text-neutral-500 uppercase">Lines</th>
                <th class="px-4 py-2 text-right text-[10px] font-semibold text-neutral-500 uppercase">Value</th>
                <th class="px-4 py-2 text-right text-[10px] font-semibold text-neutral-500 uppercase">Date</th>
              </tr></thead>
              <tbody class="divide-y divide-neutral-50">
                {#each data.recent_issues as issue}
                  <tr class="cursor-pointer transition-colors {issue.status === 'issued' ? 'bg-emerald-50/50 hover:bg-emerald-50' : issue.status === 'approved' ? 'bg-blue-50/30 hover:bg-blue-50' : issue.status === 'requested' ? 'hover:bg-amber-50/30' : 'hover:bg-neutral-50'}" onclick={() => openDetail(issue.id)}>
                    <td class="px-4 py-2.5 font-semibold text-neutral-900">{issue.issue_number}</td>
                    <td class="px-4 py-2.5 text-neutral-700">{issue.project_name}</td>
                    <td class="px-4 py-2.5 text-center"><span class="rounded-full border px-2 py-0.5 text-[10px] font-semibold {STATUS_COLORS[issue.status] || ''}">{issue.status.replace(/_/g, " ")}</span></td>
                    <td class="px-4 py-2.5 text-center tabular-nums text-neutral-600">{issue.line_count}</td>
                    <td class="px-4 py-2.5 text-right font-semibold text-emerald-700 tabular-nums">{currency.format(Number(issue.total_value || 0))}</td>
                    <td class="px-4 py-2.5 text-right text-neutral-500 tabular-nums">{issue.requested_date}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </div>
    </div>
    {/if}

  {/if}
</div>

<!-- Detail Drawer -->
{#if showDetail && detail}
  <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <div class="fixed inset-0 z-50 flex justify-end bg-black/30" style="backdrop-filter: blur(4px)" onclick={() => { showDetail = false; detail = null; }}>
    <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
    <div class="w-full max-w-2xl bg-white shadow-2xl overflow-y-auto" onclick={(e) => e.stopPropagation()}>
      <div class="bg-neutral-900 px-5 py-4 flex items-start justify-between sticky top-0 z-10">
        <div>
          <h2 class="text-lg font-semibold text-white">{detail.issue_number}</h2>
          <p class="text-xs text-neutral-400 mt-0.5">{detail.project_name}{detail.phase_name ? ` — ${detail.phase_name}` : ''} | {detail.warehouse_name}</p>
          <div class="flex gap-2 mt-2">
            <span class="rounded-full border px-2.5 py-0.5 text-[10px] font-semibold {STATUS_COLORS[detail.status] || ''}">{detail.status.replace(/_/g, " ")}</span>
          </div>
        </div>
        <div class="flex items-center gap-2">
          {#if detail.status === "requested"}
            <button onclick={approveIssue} class="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700">Approve</button>
          {/if}
          {#if detail.status === "approved" || detail.status === "partially_issued"}
            <button onclick={issueMaterials} class="rounded-lg bg-pink-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-pink-700">Issue Materials</button>
          {/if}
          {#if detail.status === "issued" || detail.status === "partially_issued"}
            <button onclick={() => { if (detail) openMIS(detail); }} class="rounded-lg border border-neutral-600 px-3 py-1.5 text-xs font-semibold text-neutral-300 hover:bg-neutral-800">View Issue Slip</button>
          {/if}
          <button onclick={() => { showDetail = false; detail = null; }} class="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-800 hover:text-white" aria-label="Close">
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
          </button>
        </div>
      </div>

      {#if detailLoading}
        <div class="p-12 text-center text-sm text-neutral-400">Loading...</div>
      {:else}
        <div class="p-5 space-y-4">
          <div class="grid grid-cols-2 gap-3 sm:grid-cols-4 text-xs">
            <div><span class="text-[9px] text-neutral-400 uppercase font-semibold block">Requested By</span><span class="text-neutral-900">{detail.requested_by_name}</span></div>
            <div><span class="text-[9px] text-neutral-400 uppercase font-semibold block">Date</span><span class="text-neutral-900">{detail.requested_date}</span></div>
            <div><span class="text-[9px] text-neutral-400 uppercase font-semibold block">Cost Code</span><span class="text-neutral-900">{detail.cost_code || "—"}</span></div>
            <div><span class="text-[9px] text-neutral-400 uppercase font-semibold block">Approved By</span><span class="text-neutral-900">{detail.approved_by || "—"}</span></div>
          </div>
          {#if detail.purpose}<div><p class="text-[9px] text-neutral-400 uppercase font-semibold mb-1">Purpose</p><p class="text-sm text-neutral-700">{detail.purpose}</p></div>{/if}

          <!-- Lines -->
          <div class="rounded-lg border border-neutral-200 overflow-hidden">
            <table class="w-full text-sm">
              <thead><tr class="border-b border-neutral-100 bg-neutral-50">
                <th class="px-3 py-2 text-left text-[9px] font-semibold text-neutral-500 uppercase">Material</th>
                <th class="px-3 py-2 text-center text-[9px] font-semibold text-neutral-500 uppercase">Requested</th>
                <th class="px-3 py-2 text-center text-[9px] font-semibold text-neutral-500 uppercase">Issued</th>
                <th class="px-3 py-2 text-right text-[9px] font-semibold text-neutral-500 uppercase">Unit Cost</th>
                <th class="px-3 py-2 text-right text-[9px] font-semibold text-neutral-500 uppercase">Value</th>
              </tr></thead>
              <tbody class="divide-y divide-neutral-50">
                {#each detail.lines as line}
                  <tr>
                    <td class="px-3 py-2.5"><p class="font-medium text-neutral-900">{line.item_name}</p><p class="text-[9px] text-neutral-400">{line.item_sku}</p></td>
                    <td class="px-3 py-2.5 text-center tabular-nums">{line.requested_quantity}</td>
                    <td class="px-3 py-2.5 text-center tabular-nums {Number(line.issued_quantity) >= Number(line.requested_quantity) ? 'text-emerald-700 font-semibold' : Number(line.issued_quantity) > 0 ? 'text-amber-700' : 'text-neutral-400'}">{line.issued_quantity}</td>
                    <td class="px-3 py-2.5 text-right tabular-nums text-neutral-600">{currency.format(Number(line.unit_cost))}</td>
                    <td class="px-3 py-2.5 text-right font-semibold tabular-nums text-emerald-700">{currency.format(Number(line.line_value))}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>
      {/if}
    </div>
  </div>
{/if}

<!-- Create Modal -->
{#if showCreate}
  <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" style="backdrop-filter: blur(15px)" onclick={() => { showCreate = false; }}>
    <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
    <div class="w-full max-w-2xl max-h-[90vh] rounded-2xl bg-white shadow-2xl overflow-y-auto" onclick={(e) => e.stopPropagation()}>
      <div class="px-6 py-4 border-b border-neutral-100 flex items-start justify-between">
        <div>
          <h2 class="text-base font-semibold text-neutral-900">New Material Issue Request</h2>
          <p class="text-xs text-neutral-500 mt-0.5">Request materials from warehouse for construction site.</p>
        </div>
        <button type="button" onclick={() => toast.success("Scan", "Point camera at material pallet QR code to auto-populate.")} class="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs font-medium text-neutral-600 hover:bg-neutral-100 flex items-center gap-1.5" title="Scan QR code on material pallet">
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 4.875c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5A1.125 1.125 0 0 1 3.75 9.375v-4.5ZM3.75 14.625c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5a1.125 1.125 0 0 1-1.125-1.125v-4.5ZM13.5 4.875c0-.621.504-1.125 1.125-1.125h4.5c.621 0 1.125.504 1.125 1.125v4.5c0 .621-.504 1.125-1.125 1.125h-4.5A1.125 1.125 0 0 1 13.5 9.375v-4.5Z" /><path stroke-linecap="round" stroke-linejoin="round" d="M6.75 6.75h.75v.75h-.75v-.75ZM6.75 16.5h.75v.75h-.75v-.75ZM16.5 6.75h.75v.75h-.75v-.75ZM13.5 13.5h.75v.75h-.75v-.75ZM13.5 19.5h.75v.75h-.75v-.75ZM19.5 13.5h.75v.75h-.75v-.75ZM19.5 19.5h.75v.75h-.75v-.75ZM16.5 16.5h.75v.75h-.75v-.75Z" /></svg>
          Scan QR
        </button>
      </div>
      <div class="p-6 space-y-4">
        <div class="grid grid-cols-2 gap-3">
          <label class="block text-sm"><span class="mb-1 block text-xs font-medium text-neutral-700">Project *</span>
            <select bind:value={createForm.project} onchange={() => loadPhases(createForm.project)} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
              <option value="">Select project</option>
              {#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}
            </select>
          </label>
          <label class="block text-sm"><span class="mb-1 block text-xs font-medium text-neutral-700">Phase</span>
            <select bind:value={createForm.phase} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
              <option value="">Select phase</option>
              {#each phases as p}<option value={String(p.id)}>{p.name}</option>{/each}
            </select>
          </label>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <label class="block text-sm"><span class="mb-1 block text-xs font-medium text-neutral-700">Warehouse *</span>
            <select bind:value={createForm.warehouse} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
              <option value="">Select warehouse</option>
              {#each warehouses as w}<option value={String(w.id)}>{w.name}</option>{/each}
            </select>
          </label>
          <label class="block text-sm"><span class="mb-1 block text-xs font-medium text-neutral-700">Work Package</span>
            <select bind:value={createForm.work_package} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
              <option value="">Select work package</option>
              {#each workPackages as wp}<option value={String(wp.id)}>{wp.name}</option>{/each}
            </select>
          </label>
        </div>
        <div class="grid grid-cols-3 gap-3">
          <label class="block text-sm"><span class="mb-1 block text-xs font-medium text-neutral-700">Requesting Crew</span>
            <input type="text" bind:value={createForm.requesting_crew} placeholder="e.g. Steel Fixers Team A, Masons B"
              class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
            <p class="mt-0.5 text-[9px] text-neutral-400">Comma-separated team names</p>
          </label>
          <label class="block text-sm"><span class="mb-1 block text-xs font-medium text-neutral-700">Required Date</span>
            <input type="date" bind:value={createForm.required_date}
              class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" style="font-family: Raleway, sans-serif; font-weight: 300;" />
          </label>
          <label class="block text-sm"><span class="mb-1 block text-xs font-medium text-neutral-700">Cost Code</span>
            <input type="text" bind:value={createForm.cost_code} placeholder="CC-201" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </label>
        </div>
        <label class="block text-sm"><span class="mb-1 block text-xs font-medium text-neutral-700">Purpose / Activity</span>
          <input type="text" bind:value={createForm.purpose} placeholder="e.g. Foundation blockwork — Zone A" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        </label>

        <!-- Material Lines -->
        <div>
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-[10px] font-semibold text-neutral-500 uppercase tracking-widest">Material Lines ({createLines.length})</h3>
            <button type="button" onclick={addLine} class="rounded-md bg-neutral-900 px-2.5 py-1 text-[10px] font-semibold text-white hover:bg-neutral-800">+ Add Line</button>
          </div>
          <div class="space-y-2">
            {#each createLines as line, i}
              <div class="rounded-lg border border-neutral-200 p-3 space-y-2 {line.stock_status === 'out' ? 'bg-red-50/30 border-red-200' : line.stock_status === 'low' ? 'bg-amber-50/30 border-amber-200' : ''}">
                <div class="flex gap-2 items-end">
                  <label class="flex-1 text-sm"><span class="mb-1 block text-[9px] font-medium text-neutral-500">Material *</span>
                    <select bind:value={line.item} onchange={() => checkLineStock(i)} class="w-full rounded-lg border border-neutral-200 bg-white px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-neutral-900">
                      <option value="">Select material</option>
                      {#each items as item}<option value={String(item.id)}>{item.sku} — {item.name}</option>{/each}
                    </select>
                  </label>
                  <label class="w-20 text-sm"><span class="mb-1 block text-[9px] font-medium text-neutral-500">Qty *</span>
                    <input type="number" step="0.01" min="1" bind:value={line.requested_quantity} onchange={() => checkLineStock(i)} class="w-full rounded-lg border border-neutral-200 px-2 py-1.5 text-xs tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                  </label>
                  <label class="w-16 text-sm"><span class="mb-1 block text-[9px] font-medium text-neutral-500">Unit</span>
                    <input type="text" bind:value={line.unit_of_measure} class="w-full rounded-lg border border-neutral-200 px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                  </label>
                  <!-- Stock Check Indicator -->
                  <div class="w-20 text-center mb-0.5">
                    {#if line.stock_status === "sufficient"}
                      <span class="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-1 text-[9px] font-bold text-emerald-700">
                        <span class="inline-block h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
                        {line.stock_on_hand}
                      </span>
                    {:else if line.stock_status === "low"}
                      <span class="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-1 text-[9px] font-bold text-amber-700">
                        <span class="inline-block h-1.5 w-1.5 rounded-full bg-amber-500"></span>
                        {line.stock_on_hand}
                      </span>
                    {:else if line.stock_status === "out"}
                      <span class="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-1 text-[9px] font-bold text-red-700">
                        <span class="inline-block h-1.5 w-1.5 rounded-full bg-red-500"></span>
                        Out
                      </span>
                    {:else}
                      <span class="text-[9px] text-neutral-300">Stock</span>
                    {/if}
                  </div>
                  <button type="button" onclick={() => removeLine(i)} class="rounded-md p-1.5 text-neutral-400 hover:text-red-500 hover:bg-red-50 mb-0.5" title="Remove">
                    <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
                  </button>
                </div>
                {#if line.stock_status === "out"}
                  <p class="text-[9px] text-red-600 font-semibold">No stock available in selected warehouse. A purchase requisition may be needed.</p>
                {:else if line.stock_status === "low"}
                  <p class="text-[9px] text-amber-600 font-semibold">Partial stock available ({line.stock_on_hand} on hand). Requested qty exceeds available.</p>
                {/if}
              </div>
            {/each}
          </div>
        </div>
      </div>
      <div class="px-6 py-4 border-t border-neutral-100 flex justify-end gap-3">
        {#if isDev}<button type="button" onclick={devFillIssue} class="mr-auto rounded-lg bg-orange-500 px-3 py-2 text-xs font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
        <button onclick={() => { showCreate = false; }} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
        <button onclick={createIssue} disabled={createSaving} class="rounded-lg bg-pink-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-pink-700 disabled:opacity-50">{createSaving ? "Creating..." : "Submit Request"}</button>
      </div>
    </div>
  </div>
{/if}

<!-- Material Issue Slip (MIS) — Glassmorphic Document -->
{#if showMIS && misData}
  <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <div class="fixed inset-0 z-60 flex items-center justify-center bg-black/40 p-4" style="backdrop-filter: blur(8px)" onclick={() => { showMIS = false; misData = null; }}>
    <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
    <div class="w-full max-w-2xl max-h-[90vh] rounded-2xl bg-white/95 shadow-2xl overflow-hidden flex flex-col" style="backdrop-filter: blur(15px); border: 1px solid rgba(255,255,255,0.3);" onclick={(e) => e.stopPropagation()}>
      <!-- Header -->
      <div class="bg-neutral-900 px-6 py-4 flex items-center justify-between shrink-0">
        <div>
          <h2 class="text-lg font-semibold text-white">Material Issue Slip</h2>
          <p class="text-xs text-neutral-400 mt-0.5">{misData.issue_number}</p>
        </div>
        <div class="flex items-center gap-2">
          <button onclick={printMIS} class="rounded-lg bg-emerald-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700">Print / PDF</button>
          <button onclick={() => { showMIS = false; misData = null; }} class="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-800 hover:text-white" aria-label="Close">
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
          </button>
        </div>
      </div>

      <!-- Document Body -->
      <div class="flex-1 overflow-y-auto p-6">
        <div id="mis-print-area">
          <!-- Document Title -->
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px;">
            <div>
              <p style="font-size: 20px; font-weight: 800; color: #171717; letter-spacing: -0.5px;">MATERIAL ISSUE SLIP</p>
              <p style="font-size: 11px; color: #737373; margin-top: 2px;">Inventory Outflow Record</p>
            </div>
            <div style="text-align: right;">
              <p style="font-size: 16px; font-weight: 700; color: #171717; font-family: monospace;">{misData.issue_number}</p>
              <p style="font-size: 10px; color: #737373; margin-top: 2px;">Non-editable · System Generated</p>
            </div>
          </div>

          <!-- Info Grid -->
          <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin-bottom: 20px;">
            <div style="border: 1px solid #e5e5e5; border-radius: 8px; padding: 10px; background: rgba(250,250,250,0.8);">
              <p style="font-size: 9px; text-transform: uppercase; color: #a3a3a3; font-weight: 600;">Project</p>
              <p style="font-size: 13px; font-weight: 600; margin-top: 2px;">{misData.project_name}</p>
              {#if misData.phase_name}<p style="font-size: 10px; color: #737373;">{misData.phase_name}</p>{/if}
            </div>
            <div style="border: 1px solid #e5e5e5; border-radius: 8px; padding: 10px; background: rgba(250,250,250,0.8);">
              <p style="font-size: 9px; text-transform: uppercase; color: #a3a3a3; font-weight: 600;">Warehouse</p>
              <p style="font-size: 13px; font-weight: 600; margin-top: 2px;">{misData.warehouse_name}</p>
            </div>
            <div style="border: 1px solid #e5e5e5; border-radius: 8px; padding: 10px; background: rgba(250,250,250,0.8);">
              <p style="font-size: 9px; text-transform: uppercase; color: #a3a3a3; font-weight: 600;">Issue Date</p>
              <p style="font-size: 13px; font-weight: 600; margin-top: 2px;">{misData.issued_date || misData.requested_date}</p>
            </div>
          </div>

          <!-- Purpose -->
          {#if misData.purpose}
            <div style="border: 1px solid #e5e5e5; border-radius: 8px; padding: 10px; margin-bottom: 16px; background: rgba(250,250,250,0.8);">
              <p style="font-size: 9px; text-transform: uppercase; color: #a3a3a3; font-weight: 600;">Purpose / Work Activity</p>
              <p style="font-size: 12px; font-weight: 500; margin-top: 2px;">{misData.purpose}</p>
            </div>
          {/if}

          <!-- Issued Materials Table -->
          <table style="width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 11px;">
            <thead>
              <tr style="background: #f5f5f5;">
                <th style="border: 1px solid #d4d4d4; padding: 8px; text-align: left; font-size: 9px; text-transform: uppercase; letter-spacing: 0.5px;">#</th>
                <th style="border: 1px solid #d4d4d4; padding: 8px; text-align: left; font-size: 9px; text-transform: uppercase;">Material</th>
                <th style="border: 1px solid #d4d4d4; padding: 8px; text-align: center; font-size: 9px; text-transform: uppercase;">Requested</th>
                <th style="border: 1px solid #d4d4d4; padding: 8px; text-align: center; font-size: 9px; text-transform: uppercase; font-weight: 800;">Issued Qty</th>
                <th style="border: 1px solid #d4d4d4; padding: 8px; text-align: center; font-size: 9px; text-transform: uppercase;">Unit</th>
                <th style="border: 1px solid #d4d4d4; padding: 8px; text-align: right; font-size: 9px; text-transform: uppercase;">Unit Cost</th>
                <th style="border: 1px solid #d4d4d4; padding: 8px; text-align: right; font-size: 9px; text-transform: uppercase;">Value</th>
              </tr>
            </thead>
            <tbody>
              {#each misData.lines as line, idx}
                <tr>
                  <td style="border: 1px solid #e5e5e5; padding: 6px 8px; color: #a3a3a3;">{idx + 1}</td>
                  <td style="border: 1px solid #e5e5e5; padding: 6px 8px;">
                    <span style="font-weight: 500;">{line.item_name}</span>
                    <br><span style="font-size: 9px; color: #a3a3a3; font-family: monospace;">{line.item_sku}</span>
                  </td>
                  <td style="border: 1px solid #e5e5e5; padding: 6px 8px; text-align: center; font-variant-numeric: tabular-nums;">{line.requested_quantity}</td>
                  <td style="border: 1px solid #e5e5e5; padding: 6px 8px; text-align: center; font-variant-numeric: tabular-nums; font-weight: 800; font-size: 13px;">{line.issued_quantity}</td>
                  <td style="border: 1px solid #e5e5e5; padding: 6px 8px; text-align: center; color: #737373;">{line.unit_of_measure}</td>
                  <td style="border: 1px solid #e5e5e5; padding: 6px 8px; text-align: right; font-variant-numeric: tabular-nums;">{currency.format(Number(line.unit_cost))}</td>
                  <td style="border: 1px solid #e5e5e5; padding: 6px 8px; text-align: right; font-variant-numeric: tabular-nums; font-weight: 600;">{currency.format(Number(line.line_value))}</td>
                </tr>
              {/each}
            </tbody>
            <tfoot>
              <tr style="background: #f0fdf4;">
                <td colspan="6" style="border: 1px solid #d4d4d4; padding: 8px; text-align: right; font-weight: 700; font-size: 12px;">TOTAL ISSUE VALUE</td>
                <td style="border: 1px solid #d4d4d4; padding: 8px; text-align: right; font-weight: 700; font-size: 14px; color: #065f46; font-variant-numeric: tabular-nums;">{currency.format(Number(misData.total_value || 0))}</td>
              </tr>
            </tfoot>
          </table>

          <!-- Digital Paper Trail -->
          <div style="border: 1px solid rgba(200,200,200,0.5); border-radius: 10px; padding: 14px; margin: 20px 0; background: rgba(250,250,250,0.6); backdrop-filter: blur(4px);">
            <p style="font-size: 9px; text-transform: uppercase; color: #a3a3a3; font-weight: 600; letter-spacing: 1px; margin-bottom: 8px;">Digital Paper Trail</p>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 11px;">
              <div><span style="color: #a3a3a3;">Requested by:</span> <span style="font-weight: 600;">{misData.requested_by_name}</span></div>
              <div><span style="color: #a3a3a3;">Request date:</span> <span>{misData.requested_date}</span></div>
              <div><span style="color: #a3a3a3;">Approved by:</span> <span style="font-weight: 600;">{misData.approved_by || "—"}</span></div>
              <div><span style="color: #a3a3a3;">Approval date:</span> <span>{misData.approved_date || "—"}</span></div>
              <div><span style="color: #a3a3a3;">Issued by:</span> <span style="font-weight: 600;">{misData.issued_by || "—"}</span></div>
              <div><span style="color: #a3a3a3;">Issue date:</span> <span>{misData.issued_date || "—"}</span></div>
            </div>
          </div>

          <!-- Signature Lines (printable) -->
          <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 32px; margin-top: 36px;">
            <div>
              <div style="height: 40px;"></div>
              <div style="border-top: 1px solid #a3a3a3; padding-top: 6px;">
                <p style="font-size: 10px; color: #737373;">Store Manager</p>
                <p style="font-size: 11px; font-weight: 600; margin-top: 2px;">{misData.issued_by || ""}</p>
              </div>
            </div>
            <div>
              <div style="height: 40px;"></div>
              <div style="border-top: 1px solid #a3a3a3; padding-top: 6px;">
                <p style="font-size: 10px; color: #737373;">Site Supervisor</p>
              </div>
            </div>
            <div>
              <div style="height: 40px;"></div>
              <div style="border-top: 1px solid #a3a3a3; padding-top: 6px;">
                <p style="font-size: 10px; color: #737373;">Crew Lead</p>
                <p style="font-size: 10px; color: #a3a3a3; margin-top: 2px;">{new Date().toLocaleString()}</p>
              </div>
            </div>
          </div>

          <p style="text-align: center; font-size: 9px; color: #a3a3a3; margin-top: 28px;">Generated by <span style="font-weight: 400; color: #171717;">developer</span><span style="font-weight: 700; color: #a3a3a3;">OS</span> — {new Date().toLocaleDateString()}</p>
        </div>

        <!-- Interactive Signature Pad (not printed) -->
        <div class="mt-6 rounded-xl border border-neutral-200 bg-white/80 p-4" style="backdrop-filter: blur(12px); border: 1px solid rgba(200,200,200,0.4);">
          <div class="flex items-center justify-between mb-2">
            <h4 class="text-[10px] font-bold text-neutral-500 uppercase tracking-widest">Site Supervisor Sign-Off</h4>
            <div class="flex gap-2">
              {#if sigSigned}
                <span class="rounded-full bg-emerald-100 text-emerald-700 px-2 py-0.5 text-[9px] font-bold">Signed</span>
              {/if}
              <button type="button" onclick={clearSignature} class="rounded-md border border-neutral-200 px-2 py-1 text-[9px] font-medium text-neutral-500 hover:bg-neutral-50">Clear</button>
            </div>
          </div>
          <div class="rounded-lg border border-dashed {sigSigned ? 'border-emerald-300 bg-emerald-50/30' : 'border-neutral-300 bg-neutral-50'} overflow-hidden" style="touch-action: none;">
            <canvas
              width="520"
              height="120"
              class="w-full cursor-crosshair"
              style="height: 120px;"
              bind:this={sigCanvas}
            ></canvas>
          </div>
          <p class="text-[9px] text-neutral-400 mt-1.5">Draw signature above using mouse or finger (tablet/phone). This confirms material receipt at site.</p>
        </div>

        <!-- Stock Counter Summary -->
        {#if misData.lines.length > 0}
          <div class="mt-4 flex flex-wrap gap-2">
            {#each misData.lines as line}
              {@const issued = Number(line.issued_quantity)}
              {@const requested = Number(line.requested_quantity)}
              {@const fulfilled = issued >= requested}
              <div class="rounded-lg border {fulfilled ? 'border-emerald-200 bg-emerald-50' : 'border-amber-200 bg-amber-50'} px-3 py-2 text-center">
                <p class="text-[9px] font-semibold {fulfilled ? 'text-emerald-500' : 'text-amber-500'} uppercase truncate max-w-[100px]">{line.item_name}</p>
                <div class="flex items-baseline gap-1 justify-center mt-0.5">
                  <span class="text-sm font-bold {fulfilled ? 'text-emerald-700' : 'text-amber-700'} tabular-nums">{line.issued_quantity}</span>
                  <span class="text-[9px] text-neutral-400">/</span>
                  <span class="text-[10px] text-neutral-500 tabular-nums">{line.requested_quantity}</span>
                </div>
                <p class="text-[8px] {fulfilled ? 'text-emerald-500' : 'text-amber-500'} font-semibold">{fulfilled ? "Fulfilled" : "Partial"}</p>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}

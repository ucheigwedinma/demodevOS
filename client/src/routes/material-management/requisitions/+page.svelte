<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import { onMount } from "svelte";

  interface ReqLine { id: number; material: number | null; material_name: string; material_name_display: string; quantity: string; unit_of_measure: string; required_by_date: string | null; phase_area: string; line_justification: string; unit_cost: string; estimated_cost: string; available_stock: string; issued_quantity: string; issued_by: string; issued_at: string | null; sort_order: number; notes: string; }
  interface Comment { id: number; author_name: string; author_role: string; message: string; created_at: string; }
  interface AuditLog { id: number; action: string; field_changed: string; old_value: string; new_value: string; performed_by_name: string; performed_at: string; notes: string; }
  interface ReqListItem { id: number; requisition_id: string; project: number; project_name: string; phase: number | null; phase_name: string; status: string; urgency: string; site_location: string; requested_delivery_date: string | null; justification: string; cost_code: string; current_step: string; line_count: number; estimated_total: string; fulfilment_pct: number; created_by_name: string; created_at: string; }
  interface ReqDetail extends ReqListItem { delivery_instructions: string; submitted_at: string | null; approved_by_pm: string; approved_by_pm_at: string | null; approved_by_proc: string; approved_by_proc_at: string | null; fulfilled_by_store: string; fulfilled_at: string | null; rejected_by: string; rejected_at: string | null; rejection_reason: string; lines: ReqLine[]; comments: Comment[]; audit_logs: AuditLog[]; }
  interface ProjectOption { id: number; name: string; }
  interface PhaseOption { id: number; name: string; }

  const STATUS_COLORS: Record<string, string> = {
    draft: "bg-neutral-100 text-neutral-600", pending_se: "bg-blue-50 text-blue-700", pending_pm: "bg-indigo-50 text-indigo-700",
    pending_proc: "bg-violet-50 text-violet-700", pending_store: "bg-amber-50 text-amber-700",
    partially_fulfilled: "bg-yellow-50 text-yellow-700", fulfilled: "bg-emerald-50 text-emerald-700",
    needs_revision: "bg-orange-50 text-orange-700", rejected: "bg-red-50 text-red-700", cancelled: "bg-neutral-100 text-neutral-400",
  };
  const URGENCY_COLORS: Record<string, string> = {
    low: "bg-neutral-100 text-neutral-500", normal: "bg-blue-50 text-blue-600",
    high: "bg-amber-50 text-amber-700", critical: "bg-red-50 text-red-700",
  };
  const WORKFLOW_STEPS = ["site_engineer", "project_manager", "procurement", "store"];
  const STEP_LABELS: Record<string, string> = { site_engineer: "Site Engineer", project_manager: "Project Manager", procurement: "Procurement", store: "Store" };

  let loading = $state(true);
  let reqs = $state<ReqListItem[]>([]);
  let projects = $state<ProjectOption[]>([]);
  let statusFilter = $state("");
  let projectFilter = $state("");
  let urgencyFilter = $state("");
  let search = $state("");

  // Detail
  let detail = $state<ReqDetail | null>(null);
  let detailLoading = $state(false);
  let showDetail = $state(false);

  // Create
  let showCreate = $state(false);
  let createSaving = $state(false);
  let createForm = $state({ project: "", phase: "", urgency: "normal", site_location: "", requested_delivery_date: "", justification: "", cost_code: "", delivery_instructions: "" });
  let phases = $state<PhaseOption[]>([]);

  // Line add
  let showAddLine = $state(false);
  let lineSaving = $state(false);
  let lineForm = $state({ material_name: "", quantity: "1", unit_of_measure: "ea", unit_cost: "0", required_by_date: "", phase_area: "", line_justification: "", notes: "" });

  // Comment
  let newComment = $state("");
  let commentSaving = $state(false);

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  const filtered = $derived.by(() => {
    let list = reqs;
    if (statusFilter) list = list.filter(r => r.status === statusFilter);
    if (projectFilter) list = list.filter(r => String(r.project) === projectFilter);
    if (urgencyFilter) list = list.filter(r => r.urgency === urgencyFilter);
    if (search.trim()) { const q = search.trim().toLowerCase(); list = list.filter(r => r.requisition_id.toLowerCase().includes(q) || r.project_name.toLowerCase().includes(q) || r.site_location.toLowerCase().includes(q)); }
    return list;
  });

  const kpis = $derived.by(() => {
    const total = reqs.length;
    const pending = reqs.filter(r => r.status.startsWith("pending")).length;
    const fulfilled = reqs.filter(r => r.status === "fulfilled").length;
    const critical = reqs.filter(r => r.urgency === "critical" && r.status !== "fulfilled" && r.status !== "rejected" && r.status !== "cancelled").length;
    const totalValue = reqs.reduce((s, r) => s + Number(r.estimated_total || 0), 0);
    return { total, pending, fulfilled, critical, totalValue };
  });

  async function loadReqs() {
    loading = true;
    try {
      const [reqRes, projRes] = await Promise.all([
        api.get<{ results: ReqListItem[] }>("/material-requisitions/", { page_size: "200" }),
        api.get<{ results: ProjectOption[] }>("/projects/projects/", { page_size: "100", fields: "id,name" }),
      ]);
      reqs = reqRes.results;
      projects = projRes.results;
    } catch { toast.error("Load failed", "Could not load requisitions."); }
    finally { loading = false; }
  }

  async function openDetail(id: number) {
    detailLoading = true;
    showDetail = true;
    try {
      detail = await api.get<ReqDetail>(`/material-requisitions/${id}/`);
    } catch { toast.error("Load failed", "Could not load requisition detail."); }
    finally { detailLoading = false; }
  }

  async function loadPhases(projectId: string) {
    if (!projectId) { phases = []; return; }
    try {
      const res = await api.get<{ results: PhaseOption[] }>(`/projects/phases/`, { project: projectId, page_size: "50" });
      phases = res.results;
    } catch { phases = []; }
  }

  async function createReq() {
    if (!createForm.project) { toast.error("Required", "Select a project."); return; }
    createSaving = true;
    try {
      const payload: Record<string, unknown> = { ...createForm, project: Number(createForm.project) };
      if (createForm.phase) payload.phase = Number(createForm.phase);
      else delete payload.phase;
      if (!createForm.requested_delivery_date) delete payload.requested_delivery_date;
      const created = await api.post<ReqListItem>("/material-requisitions/", payload);
      toast.success("Created", `Requisition ${created.requisition_id} created.`);
      showCreate = false;
      createForm = { project: "", phase: "", urgency: "normal", site_location: "", requested_delivery_date: "", justification: "", cost_code: "", delivery_instructions: "" };
      await loadReqs();
      await openDetail(created.id);
    } catch (err) {
      if (err instanceof ApiError) toast.error("Failed", Object.values(err.fieldErrors).flat().join(" ") || "Check the form.");
      else toast.error("Failed", "Could not create requisition.");
    } finally { createSaving = false; }
  }

  async function addLine() {
    if (!detail || !lineForm.material_name.trim()) return;
    lineSaving = true;
    try {
      const payload: Record<string, unknown> = { ...lineForm, quantity: Number(lineForm.quantity), unit_cost: Number(lineForm.unit_cost) };
      if (!lineForm.required_by_date) delete payload.required_by_date;
      await api.post(`/material-requisitions/${detail.id}/lines/`, payload);
      toast.success("Added", "Line item added.");
      showAddLine = false;
      lineForm = { material_name: "", quantity: "1", unit_of_measure: "ea", unit_cost: "0", required_by_date: "", phase_area: "", line_justification: "", notes: "" };
      await openDetail(detail.id);
    } catch { toast.error("Failed", "Could not add line."); }
    finally { lineSaving = false; }
  }

  async function submitReq() {
    if (!detail) return;
    try {
      await api.post(`/material-requisitions/${detail.id}/submit/`, {});
      toast.success("Submitted", "Requisition submitted for approval.");
      await openDetail(detail.id);
      await loadReqs();
    } catch (err) {
      if (err instanceof ApiError) toast.error("Submit failed", err.data?.detail || "Check requirements.");
      else toast.error("Submit failed", "Could not submit.");
    }
  }

  async function approveReq() {
    if (!detail) return;
    try {
      await api.post(`/material-requisitions/${detail.id}/approve/`, {});
      toast.success("Approved", "Requisition approved.");
      await openDetail(detail.id);
      await loadReqs();
    } catch (err) {
      if (err instanceof ApiError) toast.error("Approve failed", err.data?.detail || "Cannot approve at this stage.");
      else toast.error("Approve failed", "Could not approve.");
    }
  }

  async function rejectReq() {
    if (!detail) return;
    const reason = prompt("Rejection reason:");
    if (!reason) return;
    try {
      await api.post(`/material-requisitions/${detail.id}/reject/`, { reason });
      toast.success("Rejected", "Requisition rejected.");
      await openDetail(detail.id);
      await loadReqs();
    } catch { toast.error("Failed", "Could not reject."); }
  }

  async function addComment() {
    if (!detail || !newComment.trim()) return;
    commentSaving = true;
    try {
      await api.post(`/material-requisitions/${detail.id}/comments/`, { message: newComment.trim() });
      newComment = "";
      await openDetail(detail.id);
    } catch { toast.error("Failed", "Could not add comment."); }
    finally { commentSaving = false; }
  }

  function devFillReq() {
    const locs = ["Abuja Site A — Zone 3", "Lekki Phase 2 — Block C", "Ikoyi Towers — Ground Floor", "Port Harcourt Estate — Section D"];
    const justs = ["Foundation blockwork — 2nd lift ready", "Roof truss installation begins next week", "MEP first fix — electrical conduits", "Finishing works — painting prep"];
    const idx = Math.floor(Math.random() * locs.length);
    createForm = { ...createForm, site_location: locs[idx], justification: justs[idx], urgency: ["normal", "high", "critical"][Math.floor(Math.random() * 3)], cost_code: `CC-${String(Math.floor(Math.random() * 900 + 100))}`, requested_delivery_date: new Date(Date.now() + 7 * 86400000).toISOString().split("T")[0] };
    if (projects.length) createForm.project = String(projects[Math.floor(Math.random() * projects.length)].id);
  }

  function devFillLine() {
    const mats = ["Portland Cement (50kg)", "12mm Rebar (12m)", "Granite Chippings (20mm)", "Sharp Sand", "Binding Wire", "10mm DC Cable", "4×2 Timber", "Roofing Sheets (0.45mm)"];
    const units = ["bags", "lengths", "tonnes", "tonnes", "kg", "meters", "pieces", "sheets"];
    const costs = [7500, 12000, 45000, 8000, 3500, 2200, 1800, 5500];
    const idx = Math.floor(Math.random() * mats.length);
    lineForm = { material_name: mats[idx], quantity: String(Math.floor(Math.random() * 50 + 10)), unit_of_measure: units[idx], unit_cost: String(costs[idx]), required_by_date: "", phase_area: `Zone ${String.fromCharCode(65 + Math.floor(Math.random() * 4))}`, line_justification: "", notes: "" };
  }

  function timeAgo(dateStr: string): string {
    const d = new Date(dateStr);
    const now = new Date();
    const diff = Math.floor((now.getTime() - d.getTime()) / 1000);
    if (diff < 60) return "just now";
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  }

  onMount(() => { loadReqs(); });
</script>

<svelte:head><title>Material Requisition (Site) | developerOS</title></svelte:head>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-700">Material Management</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Material Requisition (Site Requests)</h1>
      <p class="mt-1 text-sm text-neutral-500">Site teams request materials, routed through approval to procurement and stores.</p>
    </div>
    <button onclick={() => { showCreate = true; }} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800">+ New Requisition</button>
  </div>

  {#if loading}
    <p class="py-20 text-center text-sm text-neutral-400">Loading...</p>
  {:else}

    <!-- KPIs -->
    <div class="grid grid-cols-2 gap-3 sm:grid-cols-5">
      <div class="rounded-xl border border-neutral-200 bg-white p-4 text-center">
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Total</p>
        <p class="mt-1 text-2xl font-bold text-neutral-900 tabular-nums">{kpis.total}</p>
      </div>
      <div class="rounded-xl border border-amber-200 bg-amber-50 p-4 text-center">
        <p class="text-[9px] font-semibold text-amber-400 uppercase tracking-wider">Pending</p>
        <p class="mt-1 text-2xl font-bold text-amber-700 tabular-nums">{kpis.pending}</p>
      </div>
      <div class="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-center">
        <p class="text-[9px] font-semibold text-emerald-400 uppercase tracking-wider">Fulfilled</p>
        <p class="mt-1 text-2xl font-bold text-emerald-700 tabular-nums">{kpis.fulfilled}</p>
      </div>
      <div class="rounded-xl border {kpis.critical > 0 ? 'border-red-200 bg-red-50' : 'border-neutral-200 bg-white'} p-4 text-center">
        <p class="text-[9px] font-semibold {kpis.critical > 0 ? 'text-red-400' : 'text-neutral-400'} uppercase tracking-wider">Critical</p>
        <p class="mt-1 text-2xl font-bold {kpis.critical > 0 ? 'text-red-700' : 'text-neutral-900'} tabular-nums">{kpis.critical}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white p-4 text-center">
        <p class="text-[9px] font-semibold text-emerald-500 uppercase tracking-wider">Total Value</p>
        <p class="mt-1 text-lg font-bold text-emerald-700 tabular-nums">{currency.format(kpis.totalValue)}</p>
      </div>
    </div>

    <!-- Filters -->
    <div class="flex flex-wrap gap-2">
      <select bind:value={statusFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
        <option value="">All Statuses</option>
        <option value="draft">Draft</option>
        <option value="pending_pm">Pending PM</option>
        <option value="pending_proc">Pending Procurement</option>
        <option value="pending_store">Pending Store</option>
        <option value="partially_fulfilled">Partially Fulfilled</option>
        <option value="fulfilled">Fulfilled</option>
        <option value="rejected">Rejected</option>
      </select>
      <select bind:value={projectFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
        <option value="">All Projects</option>
        {#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}
      </select>
      <select bind:value={urgencyFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
        <option value="">All Urgencies</option>
        <option value="low">Low</option>
        <option value="normal">Normal</option>
        <option value="high">High</option>
        <option value="critical">Critical</option>
      </select>
      <input type="text" bind:value={search} placeholder="Search..." class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 flex-1 min-w-[150px]" />
    </div>

    <!-- Table -->
    <section class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-neutral-100 bg-neutral-50">
              <th class="px-4 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase">Req ID</th>
              <th class="px-4 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase">Project</th>
              <th class="px-4 py-2.5 text-center text-[10px] font-semibold text-neutral-500 uppercase">Urgency</th>
              <th class="px-4 py-2.5 text-center text-[10px] font-semibold text-neutral-500 uppercase">Status</th>
              <th class="px-4 py-2.5 text-center text-[10px] font-semibold text-neutral-500 uppercase">Step</th>
              <th class="px-4 py-2.5 text-center text-[10px] font-semibold text-neutral-500 uppercase">Lines</th>
              <th class="px-4 py-2.5 text-right text-[10px] font-semibold text-neutral-500 uppercase">Est. Value</th>
              <th class="px-4 py-2.5 text-center text-[10px] font-semibold text-neutral-500 uppercase">Delivery</th>
              <th class="px-4 py-2.5 text-right text-[10px] font-semibold text-neutral-500 uppercase">Created</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-50">
            {#each filtered as req}
              <tr class="hover:bg-neutral-50 cursor-pointer" onclick={() => openDetail(req.id)}>
                <td class="px-4 py-3 font-semibold text-neutral-900">{req.requisition_id}</td>
                <td class="px-4 py-3 text-neutral-700">{req.project_name}</td>
                <td class="px-4 py-3 text-center"><span class="rounded-full border px-2 py-0.5 text-[10px] font-semibold {URGENCY_COLORS[req.urgency] || ''}">{req.urgency}</span></td>
                <td class="px-4 py-3 text-center"><span class="rounded-full border px-2 py-0.5 text-[10px] font-semibold {STATUS_COLORS[req.status] || ''}">{req.status.replace(/_/g, ' ')}</span></td>
                <td class="px-4 py-3 text-center text-[10px] text-neutral-500">{STEP_LABELS[req.current_step] || req.current_step}</td>
                <td class="px-4 py-3 text-center tabular-nums text-neutral-600">{req.line_count}</td>
                <td class="px-4 py-3 text-right font-semibold text-neutral-900 tabular-nums">{currency.format(Number(req.estimated_total || 0))}</td>
                <td class="px-4 py-3 text-center text-neutral-500 tabular-nums">{req.requested_delivery_date || "—"}</td>
                <td class="px-4 py-3 text-right text-neutral-400 text-[10px]">{timeAgo(req.created_at)}</td>
              </tr>
            {:else}
              <tr><td colspan="9" class="px-4 py-8 text-center text-sm text-neutral-400">No requisitions found.</td></tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>

  {/if}
</div>

<!-- Detail Drawer -->
{#if showDetail && detail}
  <div class="fixed inset-0 z-50 flex justify-end bg-black/30" style="backdrop-filter: blur(4px)" onclick={() => { showDetail = false; detail = null; }}>
    <div class="w-full max-w-3xl bg-white shadow-2xl overflow-y-auto" onclick={(e) => e.stopPropagation()}>
      <!-- Dark Header -->
      <div class="bg-neutral-900 px-6 py-5 flex items-start justify-between">
        <div>
          <h2 class="text-lg font-semibold text-white">{detail.requisition_id}</h2>
          <p class="text-sm text-neutral-400 mt-0.5">{detail.project_name}{detail.phase_name ? ` — ${detail.phase_name}` : ''}</p>
          <div class="flex gap-2 mt-2">
            <span class="rounded-full border px-2.5 py-0.5 text-[10px] font-semibold {STATUS_COLORS[detail.status] || ''}">{detail.status.replace(/_/g, ' ')}</span>
            <span class="rounded-full border px-2.5 py-0.5 text-[10px] font-semibold {URGENCY_COLORS[detail.urgency] || ''}">{detail.urgency}</span>
          </div>
        </div>
        <div class="flex items-center gap-2">
          {#if detail.status === "draft" || detail.status === "needs_revision"}
            <button onclick={submitReq} class="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700">Submit</button>
          {/if}
          {#if detail.status === "pending_pm" || detail.status === "pending_proc"}
            <button onclick={approveReq} class="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700">Approve</button>
            <button onclick={rejectReq} class="rounded-lg bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-700">Reject</button>
          {/if}
          <button onclick={() => { showDetail = false; detail = null; }} class="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-800 hover:text-white" aria-label="Close">
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
          </button>
        </div>
      </div>

      <!-- Workflow Stepper -->
      <div class="px-6 py-4 border-b border-neutral-100 bg-neutral-50">
        <div class="flex items-center justify-between">
          {#each WORKFLOW_STEPS as step, i}
            {@const stepIdx = WORKFLOW_STEPS.indexOf(detail.current_step)}
            {@const isComplete = i < stepIdx || detail.status === "fulfilled"}
            {@const isCurrent = step === detail.current_step && detail.status !== "fulfilled" && detail.status !== "rejected"}
            <div class="flex items-center gap-2 {i < WORKFLOW_STEPS.length - 1 ? 'flex-1' : ''}">
              <div class="flex items-center justify-center h-7 w-7 rounded-full text-[10px] font-bold {isComplete ? 'bg-emerald-500 text-white' : isCurrent ? 'bg-indigo-600 text-white ring-2 ring-indigo-200' : 'bg-neutral-200 text-neutral-500'}">
                {#if isComplete}
                  <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" /></svg>
                {:else}
                  {i + 1}
                {/if}
              </div>
              <span class="text-[10px] font-semibold {isCurrent ? 'text-indigo-700' : isComplete ? 'text-emerald-700' : 'text-neutral-400'} hidden sm:inline">{STEP_LABELS[step]}</span>
              {#if i < WORKFLOW_STEPS.length - 1}
                <div class="flex-1 h-px {isComplete ? 'bg-emerald-300' : 'bg-neutral-200'} mx-2"></div>
              {/if}
            </div>
          {/each}
        </div>
      </div>

      <div class="px-6 py-5 space-y-6">
        <!-- Info Grid -->
        <div class="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div><p class="text-[9px] font-semibold text-neutral-400 uppercase">Site Location</p><p class="text-sm text-neutral-900 mt-0.5">{detail.site_location || "—"}</p></div>
          <div><p class="text-[9px] font-semibold text-neutral-400 uppercase">Delivery Date</p><p class="text-sm text-neutral-900 mt-0.5">{detail.requested_delivery_date || "—"}</p></div>
          <div><p class="text-[9px] font-semibold text-neutral-400 uppercase">Cost Code</p><p class="text-sm text-neutral-900 mt-0.5">{detail.cost_code || "—"}</p></div>
          <div><p class="text-[9px] font-semibold text-neutral-400 uppercase">Created By</p><p class="text-sm text-neutral-900 mt-0.5">{detail.created_by_name}</p></div>
        </div>

        {#if detail.justification}
          <div><p class="text-[9px] font-semibold text-neutral-400 uppercase mb-1">Justification</p><p class="text-sm text-neutral-700">{detail.justification}</p></div>
        {/if}

        <!-- Line Items -->
        <section>
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-[10px] font-semibold text-neutral-500 uppercase tracking-widest">Material Lines ({detail.lines.length})</h3>
            {#if detail.status === "draft" || detail.status === "needs_revision"}
              <button onclick={() => { showAddLine = true; }} class="rounded-lg bg-neutral-900 px-3 py-1.5 text-[10px] font-semibold text-white hover:bg-neutral-800">+ Add Line</button>
            {/if}
          </div>
          {#if detail.lines.length === 0}
            <p class="text-sm text-neutral-400 py-4 text-center">No material lines added yet.</p>
          {:else}
            <div class="rounded-lg border border-neutral-200 overflow-hidden">
              <table class="w-full text-sm">
                <thead><tr class="border-b border-neutral-100 bg-neutral-50">
                  <th class="px-3 py-2 text-left text-[9px] font-semibold text-neutral-500 uppercase">Material</th>
                  <th class="px-3 py-2 text-center text-[9px] font-semibold text-neutral-500 uppercase">Qty</th>
                  <th class="px-3 py-2 text-center text-[9px] font-semibold text-neutral-500 uppercase">Unit</th>
                  <th class="px-3 py-2 text-right text-[9px] font-semibold text-neutral-500 uppercase">Unit Cost</th>
                  <th class="px-3 py-2 text-right text-[9px] font-semibold text-neutral-500 uppercase">Total</th>
                  <th class="px-3 py-2 text-center text-[9px] font-semibold text-neutral-500 uppercase">Stock</th>
                  <th class="px-3 py-2 text-center text-[9px] font-semibold text-neutral-500 uppercase">Issued</th>
                </tr></thead>
                <tbody class="divide-y divide-neutral-50">
                  {#each detail.lines as line}
                    <tr class="hover:bg-neutral-50">
                      <td class="px-3 py-2.5 font-medium text-neutral-900">{line.material_name}</td>
                      <td class="px-3 py-2.5 text-center tabular-nums">{line.quantity}</td>
                      <td class="px-3 py-2.5 text-center text-neutral-500">{line.unit_of_measure}</td>
                      <td class="px-3 py-2.5 text-right tabular-nums">{currency.format(Number(line.unit_cost))}</td>
                      <td class="px-3 py-2.5 text-right font-semibold tabular-nums">{currency.format(Number(line.estimated_cost))}</td>
                      <td class="px-3 py-2.5 text-center tabular-nums {Number(line.available_stock) >= Number(line.quantity) ? 'text-emerald-600' : 'text-amber-600'}">{line.available_stock}</td>
                      <td class="px-3 py-2.5 text-center tabular-nums {Number(line.issued_quantity) >= Number(line.quantity) ? 'text-emerald-600 font-semibold' : ''}">{line.issued_quantity || "—"}</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {/if}
        </section>

        <!-- Comments -->
        <section>
          <h3 class="text-[10px] font-semibold text-neutral-500 uppercase tracking-widest mb-2">Comments ({detail.comments.length})</h3>
          <div class="space-y-2 mb-3 max-h-48 overflow-y-auto">
            {#each detail.comments as c}
              <div class="rounded-lg border border-neutral-100 bg-neutral-50 px-3 py-2">
                <div class="flex items-center justify-between">
                  <span class="text-xs font-semibold text-neutral-900">{c.author_name}</span>
                  <span class="text-[9px] text-neutral-400">{timeAgo(c.created_at)}</span>
                </div>
                <p class="text-xs text-neutral-700 mt-1">{c.message}</p>
              </div>
            {/each}
          </div>
          <div class="flex gap-2">
            <input type="text" bind:value={newComment} placeholder="Add a comment..." class="flex-1 rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" onkeydown={(e) => { if (e.key === 'Enter') addComment(); }} />
            <button onclick={addComment} disabled={commentSaving || !newComment.trim()} class="rounded-lg bg-neutral-900 px-3 py-2 text-xs font-medium text-white hover:bg-neutral-800 disabled:opacity-40">Send</button>
          </div>
        </section>

        <!-- Audit Log -->
        {#if detail.audit_logs.length > 0}
          <section>
            <h3 class="text-[10px] font-semibold text-neutral-500 uppercase tracking-widest mb-2">Audit Trail</h3>
            <div class="space-y-1.5 max-h-48 overflow-y-auto">
              {#each detail.audit_logs as log}
                <div class="flex items-start gap-2 text-[10px]">
                  <span class="mt-1 inline-block h-1.5 w-1.5 rounded-full bg-neutral-300 shrink-0"></span>
                  <div>
                    <span class="font-semibold text-neutral-700">{log.action}</span>
                    <span class="text-neutral-400"> by {log.performed_by_name} — {timeAgo(log.performed_at)}</span>
                    {#if log.notes}<p class="text-neutral-500 mt-0.5">{log.notes}</p>{/if}
                  </div>
                </div>
              {/each}
            </div>
          </section>
        {/if}
      </div>
    </div>
  </div>
{/if}

<!-- Create Modal -->
{#if showCreate}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" style="backdrop-filter: blur(4px)">
    <div class="w-full max-w-lg rounded-2xl border border-neutral-200 bg-white p-6 shadow-2xl">
      <h2 class="text-base font-semibold text-neutral-900 mb-4">New Material Requisition</h2>
      <div class="space-y-4">
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
          <label class="block text-sm"><span class="mb-1 block text-xs font-medium text-neutral-700">Urgency</span>
            <select bind:value={createForm.urgency} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
              <option value="low">Low</option><option value="normal">Normal</option><option value="high">High</option><option value="critical">Critical</option>
            </select>
          </label>
          <label class="block text-sm"><span class="mb-1 block text-xs font-medium text-neutral-700">Delivery Date</span>
            <input type="date" bind:value={createForm.requested_delivery_date} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </label>
        </div>
        <label class="block text-sm"><span class="mb-1 block text-xs font-medium text-neutral-700">Site Location</span>
          <input type="text" bind:value={createForm.site_location} placeholder="e.g. Lekki Phase 2 — Block C" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        </label>
        <label class="block text-sm"><span class="mb-1 block text-xs font-medium text-neutral-700">Justification</span>
          <textarea bind:value={createForm.justification} rows="2" placeholder="Why these materials are needed..." class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
        </label>
        <label class="block text-sm"><span class="mb-1 block text-xs font-medium text-neutral-700">Cost Code</span>
          <input type="text" bind:value={createForm.cost_code} placeholder="e.g. CC-201" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        </label>
      </div>
      <div class="mt-6 flex justify-end gap-3">
        {#if isDev}<button type="button" onclick={devFillReq} class="mr-auto rounded-lg bg-orange-500 px-3 py-2 text-xs font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
        <button onclick={() => { showCreate = false; }} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
        <button onclick={createReq} disabled={createSaving} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50">{createSaving ? "Creating..." : "Create"}</button>
      </div>
    </div>
  </div>
{/if}

<!-- Add Line Modal -->
{#if showAddLine}
  <div class="fixed inset-0 z-60 flex items-center justify-center bg-black/30 p-4" style="backdrop-filter: blur(4px)">
    <div class="w-full max-w-md rounded-2xl border border-neutral-200 bg-white p-6 shadow-2xl">
      <h2 class="text-base font-semibold text-neutral-900 mb-4">Add Material Line</h2>
      <div class="space-y-3">
        <label class="block text-sm"><span class="mb-1 block text-xs font-medium text-neutral-700">Material *</span>
          <input type="text" bind:value={lineForm.material_name} placeholder="e.g. Portland Cement (50kg)" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        </label>
        <div class="grid grid-cols-3 gap-3">
          <label class="block text-sm"><span class="mb-1 block text-xs font-medium text-neutral-700">Quantity *</span>
            <input type="number" step="0.01" bind:value={lineForm.quantity} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </label>
          <label class="block text-sm"><span class="mb-1 block text-xs font-medium text-neutral-700">Unit</span>
            <input type="text" bind:value={lineForm.unit_of_measure} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </label>
          <label class="block text-sm"><span class="mb-1 block text-xs font-medium text-neutral-700">Unit Cost</span>
            <input type="number" step="0.01" bind:value={lineForm.unit_cost} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </label>
        </div>
        <label class="block text-sm"><span class="mb-1 block text-xs font-medium text-neutral-700">Zone / Work Area</span>
          <input type="text" bind:value={lineForm.phase_area} placeholder="e.g. Zone A" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        </label>
      </div>
      <div class="mt-5 flex justify-end gap-3">
        {#if isDev}<button type="button" onclick={devFillLine} class="mr-auto rounded-lg bg-orange-500 px-3 py-2 text-xs font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
        <button onclick={() => { showAddLine = false; }} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
        <button onclick={addLine} disabled={lineSaving} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50">{lineSaving ? "Adding..." : "Add Line"}</button>
      </div>
    </div>
  </div>
{/if}

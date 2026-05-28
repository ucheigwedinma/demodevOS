<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DrawerShell from "$lib/components/DrawerShell.svelte";
  import type {
    DesignPhaseItem,
    DrawingListItem,
    DrawingDetail,
    DesignReviewMeetingItem,
    DrawingDiscipline,
    DrawingApprovalState,
    PaginatedResponse,
    ProjectListItem,
  } from "$lib/types";

  let tab = $state<"register" | "phases" | "meetings">("register");
  let loading = $state(true);
  let projects = $state<ProjectListItem[]>([]);
  let projectFilter = $state("");

  // Drawing register
  let drawings = $state<DrawingListItem[]>([]);
  let searchInput = $state("");
  let searchQuery = $state("");
  let disciplineFilter = $state("");
  let approvalFilter = $state("");
  let searchTimeout: ReturnType<typeof setTimeout> | undefined;

  // Design phases
  let phases = $state<DesignPhaseItem[]>([]);

  // Meetings
  let meetings = $state<DesignReviewMeetingItem[]>([]);

  // Detail drawer
  let detailOpen = $state(false);
  let detail = $state<DrawingDetail | null>(null);
  let detailLoading = $state(false);

  // Create drawing drawer
  let createOpen = $state(false);
  let saving = $state(false);
  let form = $state(defaultDrawingForm());

  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  function defaultDrawingForm() {
    return {
      project: "", design_phase: "", drawing_number: "", title: "",
      discipline: "architectural" as DrawingDiscipline,
      current_revision: "Rev A",
      approval_state: "draft" as DrawingApprovalState,
      scale: "", submitted_by: "", notes: "",
    };
  }

  function devFillDrawing() {
    form = {
      ...form,
      project: form.project || (projects.length > 0 ? String(projects[0].id) : ""),
      drawing_number: "ARCH-P1-001",
      title: "Ground Floor Plan — Residential Tower A",
      discipline: "architectural",
      current_revision: "Rev B",
      approval_state: "for_review",
      scale: "1:100",
      submitted_by: "Adesanya & Partners",
      notes: "Updated lobby layout per design review 2026-03-10. Column grid aligned with structural Rev B.",
    };
  }

  async function fetchDrawings() {
    loading = true;
    try {
      const params: Record<string, string> = { page_size: "200" };
      if (searchQuery) params.search = searchQuery;
      if (projectFilter) params.project = projectFilter;
      if (disciplineFilter) params.discipline = disciplineFilter;
      if (approvalFilter) params.approval_state = approvalFilter;

      const [res, projRes] = await Promise.all([
        api.get<PaginatedResponse<DrawingListItem>>("/projects/drawings/", params),
        projects.length === 0 ? api.get<PaginatedResponse<ProjectListItem>>("/projects/", { page_size: "200", ordering: "name" }) : Promise.resolve(null),
      ]);
      drawings = res.results;
      if (projRes) projects = projRes.results;
    } catch { drawings = []; }
    loading = false;
  }

  async function fetchPhases() {
    try {
      const params: Record<string, string> = { page_size: "100" };
      if (projectFilter) params.project = projectFilter;
      const res = await api.get<PaginatedResponse<DesignPhaseItem>>("/projects/design-phases/", params);
      phases = res.results;
    } catch { phases = []; }
  }

  async function fetchMeetings() {
    try {
      const params: Record<string, string> = { page_size: "100" };
      if (projectFilter) params.project = projectFilter;
      const res = await api.get<PaginatedResponse<DesignReviewMeetingItem>>("/projects/design-meetings/", params);
      meetings = res.results;
    } catch { meetings = []; }
  }

  $effect(() => { void searchQuery; void projectFilter; void disciplineFilter; void approvalFilter; fetchDrawings(); });
  $effect(() => { void projectFilter; if (tab === "phases") fetchPhases(); });
  $effect(() => { void projectFilter; if (tab === "meetings") fetchMeetings(); });

  function onSearchInput(e: Event) {
    searchInput = (e.target as HTMLInputElement).value;
    if (searchTimeout) clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => { searchQuery = searchInput.trim(); }, 250);
  }

  async function openDrawingDetail(id: number) {
    detailOpen = true;
    detailLoading = true;
    try { detail = await api.get<DrawingDetail>(`/projects/drawings/${id}/`); } catch { detail = null; }
    detailLoading = false;
  }

  async function saveDrawing(e: Event) {
    e.preventDefault();
    if (!form.project || !form.drawing_number.trim() || !form.title.trim()) {
      toast.error("Required", "Project, drawing number, and title are required.");
      return;
    }
    saving = true;
    try {
      await api.post("/projects/drawings/", {
        ...form,
        project: Number(form.project),
        design_phase: form.design_phase ? Number(form.design_phase) : null,
      });
      toast.success("Drawing registered", `${form.drawing_number} added.`);
      createOpen = false;
      form = defaultDrawingForm();
      await fetchDrawings();
    } catch (error) {
      const msg = error instanceof ApiError ? (Object.values(error.fieldErrors)[0]?.[0] ?? "Save failed.") : "Save failed.";
      toast.error("Save failed", msg);
    } finally { saving = false; }
  }

  function fmtDate(v: string | null | undefined): string { if (!v) return "--"; const d = new Date(v); return Number.isNaN(d.getTime()) ? "--" : d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }); }

  function approvalColor(s: string): string {
    if (s === "afc") return "bg-emerald-100 text-emerald-800";
    if (s === "approved_noted") return "bg-emerald-50 text-emerald-700";
    if (s === "for_review") return "bg-blue-100 text-blue-800";
    if (s === "revise_resubmit") return "bg-amber-100 text-amber-800";
    if (s === "superseded") return "bg-neutral-200 text-neutral-500";
    return "bg-neutral-100 text-neutral-600";
  }

  function phaseBarColor(status: string): string {
    if (status === "closed") return "bg-emerald-500";
    if (status === "in_progress") return "bg-blue-500";
    if (status === "in_review") return "bg-amber-500";
    return "bg-neutral-200";
  }
</script>

<div class="space-y-6">
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">Projects</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-900">Design Management</h1>
      <p class="mt-1 text-sm text-neutral-500">Drawing register, design phases, revision control, and review meetings.</p>
    </div>
    <div class="flex items-center gap-2">
      <select bind:value={projectFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
        <option value="">All Projects</option>
        {#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}
      </select>
      <button onclick={() => { form = defaultDrawingForm(); createOpen = true; }} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800">+ Add Drawing</button>
    </div>
  </div>

  <!-- Tabs -->
  <div class="flex gap-1 border-b border-neutral-200">
    {#each [["register", "Drawing Register"], ["phases", "Design Phases"], ["meetings", "Review Meetings"]] as [key, label]}
      <button onclick={() => { tab = key as typeof tab; }} class="px-4 py-2.5 text-sm font-semibold transition-colors border-b-2 -mb-px {tab === key ? 'text-neutral-900 border-neutral-900' : 'text-neutral-500 border-transparent hover:text-neutral-700'}">{label}</button>
    {/each}
  </div>

  {#if tab === "register"}
    <!-- Drawing Register Filters -->
    <div class="grid grid-cols-1 gap-3 xl:grid-cols-3">
      <input type="text" value={searchInput} oninput={onSearchInput} placeholder="Search drawing number, title..." class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
      <select bind:value={disciplineFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
        <option value="">All Disciplines</option>
        <option value="architectural">Architectural</option><option value="structural">Structural</option>
        <option value="mep_mechanical">MEP — Mechanical</option><option value="mep_electrical">MEP — Electrical</option><option value="mep_plumbing">MEP — Plumbing</option>
        <option value="civil">Civil</option><option value="landscape">Landscape</option><option value="interior">Interior</option><option value="other">Other</option>
      </select>
      <select bind:value={approvalFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
        <option value="">All States</option>
        <option value="draft">Draft</option><option value="for_review">For Review</option><option value="approved_noted">Approved as Noted</option>
        <option value="afc">AFC</option><option value="superseded">Superseded</option><option value="revise_resubmit">Revise & Resubmit</option>
      </select>
    </div>

    {#if loading}
      <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
    {:else if drawings.length === 0}
      <div class="rounded-2xl border border-neutral-200 bg-white px-6 py-14 text-center"><p class="text-sm text-neutral-500">No drawings found.</p></div>
    {:else}
      <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
        <div class="overflow-x-auto">
          <table class="min-w-[900px] w-full">
            <thead class="bg-neutral-50 border-b border-neutral-200">
              <tr>
                <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Drawing #</th>
                <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Title</th>
                <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Discipline</th>
                <th class="px-4 py-3 text-center text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Rev</th>
                <th class="px-4 py-3 text-center text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Status</th>
                <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Submitted By</th>
                <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Updated</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each drawings as d}
                <tr class="hover:bg-neutral-50 cursor-pointer {d.approval_state === 'superseded' ? 'opacity-50' : ''}" onclick={() => openDrawingDetail(d.id)}>
                  <td class="px-4 py-3 text-sm font-semibold text-neutral-900">{d.drawing_number}</td>
                  <td class="px-4 py-3 text-sm text-neutral-700 max-w-[240px] truncate">{d.title}</td>
                  <td class="px-4 py-3 text-xs text-neutral-600">{d.discipline_display}</td>
                  <td class="px-4 py-3 text-center text-sm font-bold text-neutral-900">{d.current_revision}</td>
                  <td class="px-4 py-3 text-center"><span class="inline-block rounded-full px-2.5 py-0.5 text-[10px] font-semibold {approvalColor(d.approval_state)}">{d.approval_state_display}</span></td>
                  <td class="px-4 py-3 text-sm text-neutral-600 max-w-[140px] truncate">{d.submitted_by || "--"}</td>
                  <td class="px-4 py-3 text-xs text-neutral-500">{fmtDate(d.last_updated)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </section>
    {/if}

  {:else if tab === "phases"}
    <!-- Design Phase Tracker -->
    {#if phases.length === 0}
      <div class="rounded-2xl border border-neutral-200 bg-white px-6 py-14 text-center"><p class="text-sm text-neutral-500">No design phases defined. Create them in the admin or via API.</p></div>
    {:else}
      <div class="space-y-3">
        {#each phases as phase}
          <div class="rounded-xl border border-neutral-200 bg-white p-5">
            <div class="flex items-center justify-between mb-3">
              <div class="flex items-center gap-3">
                <h3 class="text-sm font-semibold text-neutral-900">{phase.stage_display}</h3>
                <StatusBadge status={phase.status} />
              </div>
              <div class="flex items-center gap-3 text-xs text-neutral-500">
                <span>{phase.approved_deliverables}/{phase.total_deliverables} approved</span>
                {#if phase.closeout_checked}<span class="text-emerald-600 font-semibold">Gate Checked</span>{/if}
              </div>
            </div>
            <div class="h-2.5 w-full rounded-full bg-neutral-100 overflow-hidden">
              <div class="h-full rounded-full {phaseBarColor(phase.status)} transition-all" style="width: {phase.progress}%"></div>
            </div>
            <div class="flex items-center justify-between mt-1.5">
              <span class="text-[10px] text-neutral-400">{phase.progress}% complete</span>
            </div>
          </div>
        {/each}
      </div>
    {/if}

  {:else if tab === "meetings"}
    <!-- Design Review Meetings -->
    {#if meetings.length === 0}
      <div class="rounded-2xl border border-neutral-200 bg-white px-6 py-14 text-center"><p class="text-sm text-neutral-500">No design review meetings recorded.</p></div>
    {:else}
      <div class="space-y-3">
        {#each meetings as m}
          <div class="rounded-xl border border-neutral-200 bg-white p-5">
            <div class="flex items-center justify-between mb-2">
              <h3 class="text-sm font-semibold text-neutral-900">{m.title}</h3>
              <span class="text-xs text-neutral-400">{fmtDate(m.date)}</span>
            </div>
            {#if m.attendees}<p class="text-xs text-neutral-500 mb-2">Attendees: {m.attendees}</p>{/if}
            {#if m.key_decisions}<div class="mb-2"><p class="text-[10px] font-semibold uppercase text-neutral-400 mb-1">Key Decisions</p><p class="text-sm text-neutral-700 whitespace-pre-line">{m.key_decisions}</p></div>{/if}
            {#if m.action_items && m.action_items.length > 0}
              <div>
                <p class="text-[10px] font-semibold uppercase text-neutral-400 mb-1">Action Items</p>
                <ul class="space-y-1">
                  {#each m.action_items as ai}
                    <li class="flex items-center gap-2 text-xs">
                      <span class="h-1.5 w-1.5 rounded-full bg-blue-400 shrink-0"></span>
                      <span class="text-neutral-700">{ai.description}</span>
                      {#if ai.assigned_to}<span class="text-neutral-400">— {ai.assigned_to}</span>{/if}
                      {#if ai.due_date}<span class="text-amber-600 font-medium">Due: {fmtDate(ai.due_date)}</span>{/if}
                    </li>
                  {/each}
                </ul>
              </div>
            {/if}
            {#if m.recorded_by}<p class="text-[10px] text-neutral-400 mt-2">Recorded by: {m.recorded_by}</p>{/if}
          </div>
        {/each}
      </div>
    {/if}
  {/if}
</div>

<!-- ═══════════ DRAWING DETAIL DRAWER ═══════════ -->
<DrawerShell open={detailOpen} title="Drawing Detail" subtitle={detail ? `${detail.drawing_number} — ${detail.title}` : ""} width="max-w-2xl" onclose={() => (detailOpen = false)}>
  {#if detailLoading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if detail}
    <div class="p-6 space-y-5">
      <div class="flex items-center gap-3">
        <span class="inline-block rounded-full px-2.5 py-0.5 text-[10px] font-semibold {approvalColor(detail.approval_state)}">{detail.approval_state_display}</span>
        <span class="text-xs text-neutral-500">{detail.discipline_display}</span>
        <span class="text-sm font-bold text-neutral-900">{detail.current_revision}</span>
      </div>

      <div class="grid grid-cols-2 gap-3 text-sm">
        <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Drawing Number</p><p class="text-neutral-900 font-semibold">{detail.drawing_number}</p></div>
        <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Scale</p><p class="text-neutral-900">{detail.scale || "--"}</p></div>
        <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Submitted By</p><p class="text-neutral-900">{detail.submitted_by || "--"}</p></div>
        <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Last Updated</p><p class="text-neutral-900">{fmtDate(detail.last_updated)}</p></div>
        {#if detail.design_phase_stage}<div><p class="text-[10px] font-semibold uppercase text-neutral-400">Design Phase</p><p class="text-neutral-900">{detail.design_phase_stage}</p></div>{/if}
      </div>

      {#if detail.notes}<div><p class="text-[10px] font-semibold uppercase text-neutral-400 mb-1">Notes</p><p class="text-sm text-neutral-700 whitespace-pre-line">{detail.notes}</p></div>{/if}

      <!-- Revision History -->
      <div>
        <p class="text-[10px] font-semibold uppercase text-neutral-400 mb-2">Revision History</p>
        {#if detail.revisions.length === 0}
          <p class="text-sm text-neutral-400 py-3">No revision history recorded.</p>
        {:else}
          <div class="space-y-2">
            {#each detail.revisions as rev}
              <div class="rounded-lg border border-neutral-200 p-3">
                <div class="flex items-center justify-between mb-1">
                  <div class="flex items-center gap-2">
                    <span class="text-sm font-bold text-neutral-900">{rev.revision_code}</span>
                    <span class="inline-block rounded-full px-2 py-0.5 text-[9px] font-semibold {approvalColor(rev.approval_state)}">{rev.approval_state_display}</span>
                  </div>
                  <span class="text-xs text-neutral-400">{fmtDate(rev.submitted_date)}</span>
                </div>
                {#if rev.change_description}<p class="text-xs text-neutral-600">{rev.change_description}</p>{/if}
                <div class="flex items-center gap-3 mt-1 text-[10px] text-neutral-400">
                  {#if rev.submitted_by}<span>By: {rev.submitted_by}</span>{/if}
                  {#if rev.reviewed_by}<span>Reviewed: {rev.reviewed_by} ({fmtDate(rev.reviewed_date)})</span>{/if}
                </div>
                {#if rev.reviewer_comments}<p class="mt-1 text-xs text-amber-700 bg-amber-50 rounded p-1.5">{rev.reviewer_comments}</p>{/if}
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  {/if}
</DrawerShell>

<!-- ═══════════ CREATE DRAWING DRAWER ═══════════ -->
<DrawerShell open={createOpen} title="Register Drawing" subtitle="Add a new technical sheet to the register" width="max-w-xl" onclose={() => (createOpen = false)}>
  <form onsubmit={saveDrawing} class="p-6 space-y-4">
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Project *</span><select bind:value={form.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"><option value="">Select</option>{#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}</select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Discipline</span><select bind:value={form.discipline} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="architectural">Architectural</option><option value="structural">Structural</option>
        <option value="mep_mechanical">MEP — Mechanical</option><option value="mep_electrical">MEP — Electrical</option><option value="mep_plumbing">MEP — Plumbing</option>
        <option value="civil">Civil</option><option value="landscape">Landscape</option><option value="interior">Interior</option><option value="other">Other</option>
      </select></label>
    </div>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Drawing Number *</span><input bind:value={form.drawing_number} placeholder="e.g. ARCH-P1-001" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Revision</span><input bind:value={form.current_revision} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Title *</span><input bind:value={form.title} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <div class="grid grid-cols-3 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Scale</span><input bind:value={form.scale} placeholder="e.g. 1:100" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Approval State</span><select bind:value={form.approval_state} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="draft">Draft</option><option value="for_review">For Review</option><option value="approved_noted">Approved as Noted</option>
        <option value="afc">AFC</option><option value="revise_resubmit">Revise & Resubmit</option>
      </select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Submitted By</span><input bind:value={form.submitted_by} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Notes</span><textarea bind:value={form.notes} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <div class="flex justify-end gap-2 pt-2">
      <button type="button" onclick={() => (createOpen = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      {#if isDev}<button type="button" onclick={devFillDrawing} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
      <button type="submit" disabled={saving} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{saving ? "Saving..." : "Register Drawing"}</button>
    </div>
  </form>
</DrawerShell>

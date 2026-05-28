<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { useAutoRefresh } from "$lib/realtime.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DrawerShell from "$lib/components/DrawerShell.svelte";
  import DateInput from "$lib/components/DateInput.svelte";
  import type {
    RFIListItem,
    RFIDetail,
    RFIComment,
    RFIDiscipline,
    RFIUrgency,
    RFIStatus,
    RFISummary,
    PaginatedResponse,
    ProjectListItem,
  } from "$lib/types";

  // ── State ─────────────────────────────────────────────────────────────
  let rows = $state<RFIListItem[]>([]);
  let loading = $state(true);
  let totalCount = $state(0);
  let currentPage = $state(1);
  let searchInput = $state("");
  let searchQuery = $state("");
  let disciplineFilter = $state("");
  let urgencyFilter = $state("");
  let statusFilter = $state("");
  let searchTimeout: ReturnType<typeof setTimeout> | undefined;
  let summary = $state<RFISummary | null>(null);
  const pageSize = 15;

  // Detail drawer
  let detailOpen = $state(false);
  let detail = $state<RFIDetail | null>(null);
  let detailLoading = $state(false);
  let commentBody = $state("");
  let commentAuthor = $state("");
  let commentSaving = $state(false);

  // Create drawer
  let createOpen = $state(false);
  let saving = $state(false);
  let form = $state(defaultForm());

  // Shared
  let projects = $state<ProjectListItem[]>([]);
  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  function defaultForm() {
    return {
      project: "",
      subject: "",
      query: "",
      discipline: "other" as RFIDiscipline,
      urgency: "normal" as RFIUrgency,
      ball_in_court: "",
      proposed_solution: "",
      reference: "",
      location: "",
      submitted_by: "",
      response_sla_hours: "48",
      notes: "",
    };
  }

  // ── Dev Fill ──────────────────────────────────────────────────────────
  let devIdx = 0;
  const SAMPLES = [
    {
      subject: "Inverter clearance vs. battery rack position — Block C",
      query: "Drawing DWG-E-042 Rev B shows the inverter wall-mounted with 30cm clearance on all sides. However, the battery rack (as per DWG-E-045) is dimensioned to sit 15cm from the same wall. This creates a physical clash where the inverter's ventilation clearance zone overlaps with the battery rack footprint.\n\nPlease confirm:\n1. Can the battery rack be shifted 20cm towards the corridor wall?\n2. If yes, does this affect the cable tray routing shown in DWG-E-048?\n3. Is there an alternative inverter mounting position that maintains the required clearance?",
      discipline: "electrical" as RFIDiscipline,
      urgency: "high" as RFIUrgency,
      ball_in_court: "Lead Electrical Engineer",
      proposed_solution: "Shift battery rack 20cm left (towards corridor wall). Preliminary site measurement confirms adequate space. Cable tray routing may need minor adjustment at junction J-12.",
      reference: "DWG-E-042 Rev B, DWG-E-045 Rev A, Spec Section 26 41 00",
      location: "Block C, Level 2, Electrical Room ER-03",
      submitted_by: "Foreman Adamu Bello",
      notes: "Work on electrical room fit-out is paused pending resolution. Concrete plinths for battery rack already cast.",
    },
    {
      subject: "Foundation depth discrepancy at Grid Line F7-F9",
      query: "Structural drawing STR-101 Rev C specifies pad foundation depth at 1.8m below finished ground level for Grid Lines F7 through F9. However, the geotechnical report (GT-REP-2025-003, Page 14, Table 4.2) recommends a minimum founding depth of 2.4m in this zone due to expansive clay encountered during borehole BH-07.\n\nPlease advise:\n1. Should foundation depth be increased to 2.4m as per geotech recommendation?\n2. If yes, does this require redesign of the reinforcement schedule?\n3. Are there cost implications that need to be flagged to the QS?",
      discipline: "structural" as RFIDiscipline,
      urgency: "high" as RFIUrgency,
      ball_in_court: "Structural Design Engineer",
      proposed_solution: "Increase pad depth to 2.4m and add 150mm lean concrete blinding. Reinforcement to be confirmed by structural engineer before pour.",
      reference: "STR-101 Rev C, GT-REP-2025-003 (BH-07), BoQ Item 3.2.1",
      location: "Grid Lines F7-F9, South Wing",
      submitted_by: "Site Engineer Chidi Nwosu",
      notes: "Excavation at F7 has already reached 1.8m. Standing water observed at 2.0m — dewatering may be needed if depth is increased.",
    },
    {
      subject: "Fire-rated partition specification at Stairwell S2",
      query: "Architectural drawing ARC-204 calls for 'fire-rated partition' at Stairwell S2 but does not specify the fire rating duration. Building code requires minimum 2-hour rating for stairwell enclosures in buildings above 4 storeys.\n\nPlease confirm:\n1. Required fire rating (1-hour or 2-hour)?\n2. Preferred partition system (blockwork + plaster vs. proprietary dry-wall system)?\n3. Does the door schedule need updating for fire door specification?",
      discipline: "architectural" as RFIDiscipline,
      urgency: "normal" as RFIUrgency,
      ball_in_court: "Project Architect",
      proposed_solution: "Recommend 2-hour rated blockwork partition (200mm hollow blocks with fire-rated plaster) to match code requirements. Update door schedule to include FD120 fire doors.",
      reference: "ARC-204 Rev A, NBC 2006 Section 4.3, Door Schedule DS-01",
      location: "Stairwell S2, All Floors",
      submitted_by: "QC Inspector Aisha Bello",
      notes: "Blockwork at S2 Level 1 already completed without fire rating — may need remediation if spec confirms 2-hour requirement.",
    },
  ];

  function devFill() {
    const s = SAMPLES[devIdx % SAMPLES.length];
    devIdx++;
    form = {
      ...defaultForm(),
      project: form.project || (projects.length > 0 ? String(projects[0].id) : ""),
      subject: s.subject,
      query: s.query,
      discipline: s.discipline,
      urgency: s.urgency,
      ball_in_court: s.ball_in_court,
      proposed_solution: s.proposed_solution,
      reference: s.reference,
      location: s.location,
      submitted_by: s.submitted_by,
      notes: s.notes,
    };
  }

  // ── Data Fetching ─────────────────────────────────────────────────────

  async function fetchRFIs() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (searchQuery) params.search = searchQuery;
      if (disciplineFilter) params.discipline = disciplineFilter;
      if (urgencyFilter) params.urgency = urgencyFilter;
      if (statusFilter) params.status = statusFilter;
      const [res, sum] = await Promise.all([
        api.get<PaginatedResponse<RFIListItem>>("/projects/rfis/", params),
        summary ? Promise.resolve(summary) : api.get<RFISummary>("/projects/rfis/summary/"),
      ]);
      rows = res.results;
      totalCount = res.count;
      if (!summary) summary = sum;
    } catch { rows = []; totalCount = 0; }
    loading = false;
  }

  async function fetchProjects() {
    if (projects.length > 0) return;
    try {
      const res = await api.get<PaginatedResponse<ProjectListItem>>("/projects/", { page_size: "200", ordering: "name" });
      projects = res.results;
    } catch { /* noop */ }
  }

  $effect(() => {
    void searchQuery; void disciplineFilter; void urgencyFilter; void statusFilter; void currentPage;
    fetchRFIs();
    fetchProjects();
  });

  function onSearch(e: Event) {
    searchInput = (e.target as HTMLInputElement).value;
    if (searchTimeout) clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => { searchQuery = searchInput.trim(); currentPage = 1; }, 250);
  }

  // ── Detail ────────────────────────────────────────────────────────────

  async function openDetail(id: number) {
    detailOpen = true;
    detailLoading = true;
    commentBody = "";
    commentAuthor = "";
    try { detail = await api.get<RFIDetail>(`/projects/rfis/${id}/`); } catch { detail = null; }
    detailLoading = false;
  }

  async function postComment() {
    if (!detail || !commentBody.trim() || !commentAuthor.trim()) return;
    commentSaving = true;
    try {
      await api.post(`/projects/rfis/${detail.id}/comments/`, { author_name: commentAuthor, body: commentBody });
      detail = await api.get<RFIDetail>(`/projects/rfis/${detail.id}/`);
      commentBody = "";
      toast.success("Comment added", "");
    } catch { toast.error("Failed", "Could not post comment."); }
    commentSaving = false;
  }

  // ── Save ──────────────────────────────────────────────────────────────

  async function saveRFI(e: Event) {
    e.preventDefault();
    if (!form.subject.trim() || !form.project || !form.query.trim()) { toast.error("Validation", "Subject, project, and query are required."); return; }
    saving = true;
    try {
      await api.post("/projects/rfis/", {
        ...form,
        project: Number(form.project),
        response_sla_hours: Number(form.response_sla_hours) || 48,
      });
      toast.success("RFI submitted", `"${form.subject}" has been logged.`);
      createOpen = false;
      form = defaultForm();
      summary = null;
      await fetchRFIs();
    } catch (error) {
      const msg = error instanceof ApiError ? (Object.values(error.fieldErrors)[0]?.[0] ?? "Save failed.") : "Save failed.";
      toast.error("Save failed", msg);
    } finally { saving = false; }
  }

  // ── Helpers ───────────────────────────────────────────────────────────
  function fmtDate(v: string | null | undefined): string { if (!v) return "--"; const d = new Date(v); return Number.isNaN(d.getTime()) ? "--" : d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }); }

  const totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  const startRow = $derived(totalCount === 0 ? 0 : (currentPage - 1) * pageSize + 1);
  const endRow = $derived(Math.min(currentPage * pageSize, totalCount));

  function urgencyColor(u: string): string {
    switch (u) {
      case "high": return "bg-amber-100 text-amber-800 border-amber-200";
      case "normal": return "bg-neutral-100 text-neutral-600 border-neutral-200";
      case "low": return "bg-blue-100 text-blue-700 border-blue-200";
      default: return "bg-neutral-100 text-neutral-600 border-neutral-200";
    }
  }

  function daysOpenColor(days: number, sla: number): string {
    if (days * 24 > sla * 2) return "text-red-600 font-bold";
    if (days * 24 > sla) return "text-amber-600 font-semibold";
    return "text-neutral-500";
  }

  useAutoRefresh("RFI", fetchRFIs);
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">Construction</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-900">Requests for Information</h1>
      <p class="mt-1 text-sm text-neutral-500">Formal communication bridge between site and design — track questions, responses, and SLA compliance.</p>
    </div>
    <button onclick={() => { form = defaultForm(); createOpen = true; }} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800">+ Submit RFI</button>
  </div>

  <!-- Summary KPIs -->
  {#if summary}
    <div class="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
      <div class="rounded-xl border border-neutral-200 bg-white p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Total RFIs</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{summary.total}</p>
      </div>
      <div class="rounded-xl border border-blue-100 bg-blue-50 p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-blue-700">Open</p>
        <p class="mt-1 text-xl font-bold text-blue-900 tabular-nums">{summary.open}</p>
      </div>
      <div class="rounded-xl border border-amber-100 bg-amber-50 p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-amber-700">Overdue</p>
        <p class="mt-1 text-xl font-bold text-amber-900 tabular-nums">{summary.overdue}</p>
      </div>
      <div class="rounded-xl border border-red-100 bg-red-50 p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-red-700">Critical Open</p>
        <p class="mt-1 text-xl font-bold text-red-900 tabular-nums">{summary.critical_open}</p>
      </div>
      <div class="rounded-xl border border-indigo-100 bg-indigo-50 p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-indigo-700">Answered</p>
        <p class="mt-1 text-xl font-bold text-indigo-900 tabular-nums">{summary.answered}</p>
      </div>
      <div class="rounded-xl border border-emerald-100 bg-emerald-50 p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-emerald-700">Closed</p>
        <p class="mt-1 text-xl font-bold text-emerald-900 tabular-nums">{summary.closed}</p>
      </div>
    </div>
  {/if}

  <!-- Filters + Table -->
  <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
    <div class="border-b border-neutral-200 bg-linear-to-r from-neutral-50 via-white to-neutral-50 p-4">
      <div class="grid grid-cols-1 gap-3 xl:grid-cols-5">
        <input type="text" value={searchInput} oninput={onSearch} placeholder="Search RFI number, subject, ball-in-court..." class="xl:col-span-2 rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        <select bind:value={disciplineFilter} onchange={() => (currentPage = 1)} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
          <option value="">All Disciplines</option>
          <option value="structural">Structural</option>
          <option value="electrical">Electrical</option>
          <option value="mechanical">Mechanical</option>
          <option value="civil">Civil</option>
          <option value="architectural">Architectural</option>
          <option value="plumbing">Plumbing</option>
          <option value="fire">Fire Protection</option>
          <option value="procurement">Procurement</option>
          <option value="other">Other</option>
        </select>
        <select bind:value={urgencyFilter} onchange={() => (currentPage = 1)} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
          <option value="">All Urgencies</option>
          <option value="high">High — Work Stopped</option>
          <option value="normal">Normal</option>
          <option value="low">Low — Future Phase</option>
        </select>
        <select bind:value={statusFilter} onchange={() => (currentPage = 1)} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="open">Open</option>
          <option value="under_review">Under Review</option>
          <option value="answered">Answered</option>
          <option value="closed">Closed</option>
          <option value="void">Void</option>
        </select>
      </div>
    </div>

    {#if loading}
      <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
    {:else if rows.length === 0}
      <div class="px-6 py-14 text-center"><p class="text-sm text-neutral-500">No RFIs match the current filters.</p></div>
    {:else}
      <div class="overflow-x-auto">
        <table class="min-w-[1050px] w-full">
          <thead class="border-b border-neutral-200 bg-neutral-50">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">RFI #</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Subject</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Discipline</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Urgency</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Status</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Ball-in-Court</th>
              <th class="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-neutral-500">Days Open</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Submitted</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each rows as rfi}
              <tr class="hover:bg-neutral-50 cursor-pointer" onclick={() => openDetail(rfi.id)}>
                <td class="px-4 py-3 text-sm font-semibold text-neutral-900">{rfi.rfi_number}</td>
                <td class="px-4 py-3 text-sm text-neutral-900 max-w-[260px] truncate">{rfi.subject}</td>
                <td class="px-4 py-3 text-xs font-medium text-neutral-600">{rfi.discipline_display}</td>
                <td class="px-4 py-3"><span class="inline-block rounded-full border px-2 py-0.5 text-[10px] font-semibold {urgencyColor(rfi.urgency)}">{rfi.urgency_display}</span></td>
                <td class="px-4 py-3"><StatusBadge status={rfi.status} /></td>
                <td class="px-4 py-3 text-sm text-neutral-700 max-w-[160px] truncate">{rfi.ball_in_court || "--"}</td>
                <td class="px-4 py-3 text-center text-sm tabular-nums {daysOpenColor(rfi.days_open, rfi.response_sla_hours)}">{rfi.days_open}d</td>
                <td class="px-4 py-3 text-sm text-neutral-500">{fmtDate(rfi.submitted_date)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <div class="flex items-center justify-between border-t border-neutral-200 px-4 py-3">
        <p class="text-xs text-neutral-500">Showing <span class="font-semibold text-neutral-700">{startRow}</span>–<span class="font-semibold text-neutral-700">{endRow}</span> of <span class="font-semibold text-neutral-700">{totalCount}</span></p>
        <div class="flex items-center gap-2">
          <button onclick={() => (currentPage = Math.max(1, currentPage - 1))} disabled={currentPage <= 1} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 disabled:opacity-40">Previous</button>
          <span class="text-xs font-medium text-neutral-600">Page {currentPage} of {totalPages}</span>
          <button onclick={() => (currentPage = Math.min(totalPages, currentPage + 1))} disabled={currentPage >= totalPages} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 disabled:opacity-40">Next</button>
        </div>
      </div>
    {/if}
  </section>
</div>

<!-- ═══════════ RFI DETAIL DRAWER ═══════════ -->
<DrawerShell open={detailOpen} title={detail?.rfi_number ?? "RFI"} subtitle={detail?.subject ?? ""} width="max-w-2xl" onclose={() => (detailOpen = false)}>
  {#if detailLoading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if detail}
    <div class="p-6 space-y-5">
      <!-- Urgency + Status bar -->
      <div class="flex items-center justify-between rounded-lg border p-3 {detail.urgency === 'high' ? 'bg-amber-50 border-amber-200' : 'bg-neutral-50 border-neutral-200'}">
        <span class="inline-block rounded-full border px-2.5 py-0.5 text-[10px] font-semibold {urgencyColor(detail.urgency)}">{detail.urgency_display}</span>
        <div class="flex items-center gap-2">
          <StatusBadge status={detail.status} />
          <span class="text-xs tabular-nums {daysOpenColor(detail.days_open, detail.response_sla_hours)}">{detail.days_open} days open</span>
        </div>
      </div>

      <!-- Meta grid -->
      <div class="grid grid-cols-2 gap-4">
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Project</p><p class="text-sm text-neutral-900">{detail.project_name}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Discipline</p><p class="text-sm text-neutral-900">{detail.discipline_display}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Ball-in-Court</p><p class="text-sm font-semibold text-neutral-900">{detail.ball_in_court || "--"}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Reference</p><p class="text-sm text-neutral-900">{detail.reference || "--"}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Submitted By</p><p class="text-sm text-neutral-900">{detail.submitted_by || "--"}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Location</p><p class="text-sm text-neutral-900">{detail.location || "--"}</p></div>
      </div>

      <!-- The Query -->
      <div class="rounded-lg border border-blue-200 bg-blue-50/50 p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-blue-700 mb-2">The Query</p>
        <p class="text-sm text-neutral-800 whitespace-pre-line">{detail.query}</p>
      </div>

      {#if detail.proposed_solution}
        <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500 mb-2">Proposed Solution</p>
          <p class="text-sm text-neutral-700 whitespace-pre-line">{detail.proposed_solution}</p>
        </div>
      {/if}

      <!-- Response -->
      {#if detail.response}
        <div class="rounded-lg border border-emerald-200 bg-emerald-50/50 p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-emerald-700 mb-2">Official Response</p>
          <p class="text-sm text-neutral-800 whitespace-pre-line">{detail.response}</p>
          {#if detail.responded_by}
            <p class="mt-2 text-xs text-emerald-600">— {detail.responded_by}, {fmtDate(detail.responded_date)}</p>
          {/if}
        </div>
      {/if}

      <!-- Impact flags -->
      {#if detail.has_cost_impact || detail.has_schedule_impact}
        <div class="grid grid-cols-2 gap-3">
          {#if detail.has_cost_impact}
            <div class="rounded-lg border border-amber-200 bg-amber-50 p-3">
              <p class="text-[10px] font-semibold uppercase tracking-wider text-amber-700">Cost Impact</p>
              <p class="text-sm text-neutral-700 mt-1">{detail.cost_impact_notes || "Flagged — details pending"}</p>
            </div>
          {/if}
          {#if detail.has_schedule_impact}
            <div class="rounded-lg border border-amber-200 bg-amber-50 p-3">
              <p class="text-[10px] font-semibold uppercase tracking-wider text-amber-700">Schedule Impact</p>
              <p class="text-sm text-neutral-700 mt-1">{detail.schedule_impact_notes || "Flagged — details pending"}</p>
            </div>
          {/if}
        </div>
      {/if}

      {#if detail.notes}
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Notes</p><p class="text-sm text-neutral-700 whitespace-pre-line">{detail.notes}</p></div>
      {/if}

      <!-- Threaded Comments -->
      <div class="border-t border-neutral-200 pt-4">
        <p class="text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-3">Discussion ({detail.comments.length})</p>
        {#if detail.comments.length > 0}
          <div class="space-y-3 mb-4">
            {#each detail.comments as comment}
              <div class="rounded-lg border border-neutral-100 bg-neutral-50 p-3">
                <div class="flex items-center justify-between mb-1">
                  <span class="text-xs font-semibold text-neutral-700">{comment.author_name}</span>
                  <span class="text-[10px] text-neutral-400">{fmtDate(comment.created_at)}</span>
                </div>
                <p class="text-sm text-neutral-700 whitespace-pre-line">{comment.body}</p>
              </div>
            {/each}
          </div>
        {/if}

        <!-- Add comment -->
        <div class="space-y-2">
          <div class="grid grid-cols-2 gap-2">
            <input type="text" bind:value={commentAuthor} placeholder="Your name" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
          </div>
          <textarea bind:value={commentBody} rows="2" placeholder="Add a comment..." class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>
          <div class="flex justify-end">
            <button onclick={postComment} disabled={commentSaving || !commentBody.trim() || !commentAuthor.trim()} class="rounded-lg bg-neutral-900 px-4 py-1.5 text-xs font-semibold text-white hover:bg-neutral-800 disabled:opacity-40">
              {commentSaving ? "Posting..." : "Post Comment"}
            </button>
          </div>
        </div>
      </div>
    </div>
  {/if}
</DrawerShell>

<!-- ═══════════ RFI CREATE DRAWER ═══════════ -->
<DrawerShell open={createOpen} title="Submit RFI" subtitle="Request formal clarification from design or owners" width="max-w-xl" onclose={() => (createOpen = false)}>
  <form onsubmit={saveRFI} class="p-6 space-y-4">
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Subject *</span><input bind:value={form.subject} placeholder="e.g. Inverter clearance vs. battery rack position" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Project *</span><select bind:value={form.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"><option value="">Select</option>{#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}</select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Discipline</span><select bind:value={form.discipline} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="structural">Structural</option><option value="electrical">Electrical</option><option value="mechanical">Mechanical</option><option value="civil">Civil</option><option value="architectural">Architectural</option><option value="plumbing">Plumbing</option><option value="fire">Fire Protection</option><option value="procurement">Procurement</option><option value="other">Other</option>
      </select></label>
    </div>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Urgency</span><select bind:value={form.urgency} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="high">High — Work Stopped</option><option value="normal">Normal</option><option value="low">Low — Future Phase</option>
      </select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Ball-in-Court</span><input bind:value={form.ball_in_court} placeholder="e.g. Lead Electrical Engineer" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">The Query *</span><textarea bind:value={form.query} rows="5" placeholder="Describe the specific question or clarification needed..." class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Proposed Solution</span><textarea bind:value={form.proposed_solution} rows="3" placeholder="Suggest a fix to speed up the response..." class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Reference</span><input bind:value={form.reference} placeholder="Drawing #, BoQ line, spec section" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Location</span><input bind:value={form.location} placeholder="Block, level, grid line" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Submitted By</span><input bind:value={form.submitted_by} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Response SLA (hours)</span><input type="number" min="1" bind:value={form.response_sla_hours} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Notes</span><textarea bind:value={form.notes} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <div class="flex justify-end gap-2 pt-2">
      <button type="button" onclick={() => (createOpen = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      {#if isDev}<button type="button" onclick={devFill} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
      <button type="submit" disabled={saving} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{saving ? "Saving..." : "Submit RFI"}</button>
    </div>
  </form>
</DrawerShell>

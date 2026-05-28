<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DrawerShell from "$lib/components/DrawerShell.svelte";
  import type {
    ProjectAnnouncementItem,
    ProjectDecisionLogItem,
    StakeholderUpdateListItem,
    StakeholderUpdateDetail,
    AnnouncementPriority,
    AnnouncementAudience,
    PaginatedResponse,
    ProjectListItem,
  } from "$lib/types";

  let tab = $state<"feed" | "decisions" | "updates">("feed");
  let loading = $state(true);
  let projects = $state<ProjectListItem[]>([]);
  let projectFilter = $state("");
  let audienceFilter = $state("");

  // Feed
  let announcements = $state<ProjectAnnouncementItem[]>([]);

  // Decisions
  let decisions = $state<ProjectDecisionLogItem[]>([]);
  let decisionSearch = $state("");

  // Updates
  let updates = $state<StakeholderUpdateListItem[]>([]);
  let updateDetailOpen = $state(false);
  let updateDetail = $state<StakeholderUpdateDetail | null>(null);
  let updateDetailLoading = $state(false);

  // Create announcement
  let createOpen = $state(false);
  let saving = $state(false);
  let form = $state(defaultForm());

  // Create decision
  let createDecOpen = $state(false);
  let savingDec = $state(false);
  let decForm = $state(defaultDecForm());

  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  function defaultForm() {
    return {
      project: "", subject: "", body: "",
      priority: "normal" as AnnouncementPriority,
      audience: "all" as AnnouncementAudience,
      is_pinned: false, published_by: "",
    };
  }

  function defaultDecForm() {
    return {
      project: "", subject: "", description: "",
      decided_by: "", rationale: "",
      decision_date: new Date().toISOString().split("T")[0],
      meeting_reference: "", impact_modules: "" as string,
      notes: "",
    };
  }

  function devFillAnnouncement() {
    form = {
      ...form,
      project: form.project || (projects.length > 0 ? String(projects[0].id) : ""),
      subject: "Site Mobilization Confirmed — Phase 1 Commences Monday",
      body: "Following the successful Pre-Construction Gate review on Friday, site mobilization for Phase 1 has been approved. Julius Berger Nigeria will begin hoarding and temporary works from Monday 20th April.\n\nAll consultants are reminded to submit final AFC drawings by Thursday EOD.\n\nProject Manager: Engr. Chukwu will be on-site full time from next week.",
      priority: "high",
      audience: "all",
      is_pinned: true,
      published_by: "Project Director — Uche Igwedinma",
    };
  }

  function devFillDecision() {
    decForm = {
      ...decForm,
      project: decForm.project || (projects.length > 0 ? String(projects[0].id) : ""),
      subject: "Change from Central AC to Split Units — Tower A",
      description: "The Steering Committee has approved the switch from a central chilled water system to individual split AC units for all residential floors in Tower A.",
      decided_by: "Steering Committee",
      rationale: "Cost saving of 15% on MEP fit-out (approximately ₦45M). Reduced maintenance burden for facility management. Client survey indicated 72% preference for individual control.",
      decision_date: "2026-03-20",
      meeting_reference: "Monthly Steering Committee — March 2026",
      impact_modules: "Design,Budget,MEP",
      notes: "MEP consultant to issue revised drawings by April 5th. Budget adjustment to be reflected in next MCR.",
    };
  }

  async function fetchAnnouncements() {
    loading = true;
    try {
      const params: Record<string, string> = { page_size: "100" };
      if (projectFilter) params.project = projectFilter;
      if (audienceFilter) params.audience = audienceFilter;
      const [res, projRes] = await Promise.all([
        api.get<PaginatedResponse<ProjectAnnouncementItem>>("/projects/announcements/", params),
        projects.length === 0 ? api.get<PaginatedResponse<ProjectListItem>>("/projects/", { page_size: "200", ordering: "name" }) : Promise.resolve(null),
      ]);
      announcements = res.results;
      if (projRes) projects = projRes.results;
    } catch { announcements = []; }
    loading = false;
  }

  async function fetchDecisions() {
    try {
      const params: Record<string, string> = { page_size: "100" };
      if (projectFilter) params.project = projectFilter;
      if (decisionSearch.trim()) params.search = decisionSearch.trim();
      const res = await api.get<PaginatedResponse<ProjectDecisionLogItem>>("/projects/decisions/", params);
      decisions = res.results;
    } catch { decisions = []; }
  }

  async function fetchUpdates() {
    try {
      const params: Record<string, string> = { page_size: "100" };
      if (projectFilter) params.project = projectFilter;
      const res = await api.get<PaginatedResponse<StakeholderUpdateListItem>>("/projects/stakeholder-updates/", params);
      updates = res.results;
    } catch { updates = []; }
  }

  $effect(() => { void projectFilter; void audienceFilter; fetchAnnouncements(); });
  $effect(() => { void projectFilter; void decisionSearch; if (tab === "decisions") fetchDecisions(); });
  $effect(() => { void projectFilter; if (tab === "updates") fetchUpdates(); });

  async function openUpdateDetail(id: number) {
    updateDetailOpen = true;
    updateDetailLoading = true;
    try { updateDetail = await api.get<StakeholderUpdateDetail>(`/projects/stakeholder-updates/${id}/`); } catch { updateDetail = null; }
    updateDetailLoading = false;
  }

  async function saveAnnouncement(e: Event) {
    e.preventDefault();
    if (!form.project || !form.subject.trim()) { toast.error("Required", "Project and subject are required."); return; }
    saving = true;
    try {
      await api.post("/projects/announcements/", { ...form, project: Number(form.project) });
      toast.success("Published", `"${form.subject}" sent to ${form.audience}.`);
      createOpen = false;
      form = defaultForm();
      await fetchAnnouncements();
    } catch (error) {
      const msg = error instanceof ApiError ? (Object.values(error.fieldErrors)[0]?.[0] ?? "Failed.") : "Failed.";
      toast.error("Publish failed", msg);
    } finally { saving = false; }
  }

  async function saveDecision(e: Event) {
    e.preventDefault();
    if (!decForm.project || !decForm.subject.trim()) { toast.error("Required", "Project and subject are required."); return; }
    savingDec = true;
    try {
      await api.post("/projects/decisions/", {
        ...decForm,
        project: Number(decForm.project),
        impact_modules: decForm.impact_modules ? decForm.impact_modules.split(",").map(s => s.trim()) : [],
      });
      toast.success("Decision logged", `"${decForm.subject}" recorded.`);
      createDecOpen = false;
      decForm = defaultDecForm();
      await fetchDecisions();
    } catch (error) {
      const msg = error instanceof ApiError ? (Object.values(error.fieldErrors)[0]?.[0] ?? "Failed.") : "Failed.";
      toast.error("Save failed", msg);
    } finally { savingDec = false; }
  }

  function fmtDate(v: string | null | undefined): string { if (!v) return "--"; const d = new Date(v); return Number.isNaN(d.getTime()) ? "--" : d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }); }
  function fmtDateTime(v: string | null | undefined): string { if (!v) return "--"; const d = new Date(v); return Number.isNaN(d.getTime()) ? "--" : d.toLocaleString("en-US", { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }); }

  function priorityColor(p: string): string {
    if (p === "critical") return "border-l-red-500 bg-red-50/30";
    if (p === "high") return "border-l-amber-500 bg-amber-50/20";
    return "border-l-neutral-200";
  }

  function priorityBadge(p: string): string {
    if (p === "critical") return "bg-red-100 text-red-800";
    if (p === "high") return "bg-amber-100 text-amber-800";
    if (p === "low") return "bg-neutral-100 text-neutral-500";
    return "bg-neutral-100 text-neutral-600";
  }
</script>

<div class="space-y-6">
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">Projects</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-900">Communications</h1>
      <p class="mt-1 text-sm text-neutral-500">Announcements, decision log, and stakeholder updates — the project's system of record.</p>
    </div>
    <div class="flex items-center gap-2">
      <select bind:value={projectFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
        <option value="">All Projects</option>
        {#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}
      </select>
      {#if tab === "feed"}
        <button onclick={() => { form = defaultForm(); createOpen = true; }} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800">+ Announce</button>
      {:else if tab === "decisions"}
        <button onclick={() => { decForm = defaultDecForm(); createDecOpen = true; }} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800">+ Log Decision</button>
      {/if}
    </div>
  </div>

  <!-- Tabs -->
  <div class="flex gap-1 border-b border-neutral-200">
    {#each [["feed", "Announcements"], ["decisions", "Decision Log"], ["updates", "Stakeholder Updates"]] as [key, label]}
      <button onclick={() => (tab = key as typeof tab)} class="px-4 py-2.5 text-sm font-semibold transition-colors border-b-2 -mb-px {tab === key ? 'text-neutral-900 border-neutral-900' : 'text-neutral-500 border-transparent hover:text-neutral-700'}">{label}</button>
    {/each}
  </div>

  {#if tab === "feed"}
    <!-- Audience filter -->
    <div class="flex items-center gap-2">
      {#each [["", "All"], ["internal", "Internal"], ["external", "External"], ["investors", "Investors"], ["consultants", "Consultants"]] as [key, label]}
        <button onclick={() => (audienceFilter = key)} class="rounded-lg px-3 py-1.5 text-xs font-medium transition-colors {audienceFilter === key ? 'bg-neutral-900 text-white' : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200'}">{label}</button>
      {/each}
    </div>

    {#if loading}
      <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
    {:else if announcements.length === 0}
      <div class="rounded-2xl border border-neutral-200 bg-white px-6 py-14 text-center"><p class="text-sm text-neutral-500">No announcements.</p></div>
    {:else}
      <div class="space-y-3">
        {#each announcements as a}
          <div class="rounded-xl border border-neutral-200 bg-white p-5 border-l-4 {priorityColor(a.priority)}">
            <div class="flex items-start justify-between mb-2">
              <div class="flex items-center gap-2">
                {#if a.is_pinned}<span class="text-[9px] font-bold text-indigo-600 bg-indigo-50 rounded px-1.5 py-0.5">PINNED</span>{/if}
                <span class="inline-block rounded-full px-2 py-0.5 text-[9px] font-semibold {priorityBadge(a.priority)}">{a.priority_display}</span>
                <span class="text-[10px] text-neutral-400">{a.audience_display}</span>
              </div>
              <span class="text-xs text-neutral-400">{fmtDateTime(a.published_at)}</span>
            </div>
            <h3 class="text-sm font-semibold text-neutral-900 mb-1">{a.subject}</h3>
            <p class="text-sm text-neutral-700 whitespace-pre-line">{a.body}</p>
            {#if a.published_by}<p class="text-[10px] text-neutral-400 mt-2">— {a.published_by}</p>{/if}
          </div>
        {/each}
      </div>
    {/if}

  {:else if tab === "decisions"}
    <input type="text" bind:value={decisionSearch} oninput={() => {}} placeholder="Search decisions..." class="w-full max-w-md rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />

    {#if decisions.length === 0}
      <div class="rounded-2xl border border-neutral-200 bg-white px-6 py-14 text-center"><p class="text-sm text-neutral-500">No decisions logged.</p></div>
    {:else}
      <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
        <div class="overflow-x-auto">
          <table class="min-w-[800px] w-full">
            <thead class="bg-neutral-50 border-b border-neutral-200">
              <tr>
                <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">ID</th>
                <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Subject</th>
                <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Decided By</th>
                <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Date</th>
                <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Impact</th>
                <th class="px-4 py-3 text-center text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Status</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each decisions as d}
                <tr class="hover:bg-neutral-50 {d.status === 'superseded' ? 'opacity-50' : ''}">
                  <td class="px-4 py-3 text-sm font-semibold text-neutral-900">{d.decision_id}</td>
                  <td class="px-4 py-3">
                    <p class="text-sm font-medium text-neutral-900 max-w-[240px] truncate">{d.subject}</p>
                    {#if d.rationale}<p class="text-[10px] text-neutral-400 max-w-[240px] truncate mt-0.5">{d.rationale}</p>{/if}
                  </td>
                  <td class="px-4 py-3 text-sm text-neutral-600">{d.decided_by}</td>
                  <td class="px-4 py-3 text-sm text-neutral-600">{fmtDate(d.decision_date)}</td>
                  <td class="px-4 py-3">
                    <div class="flex flex-wrap gap-1">
                      {#each d.impact_modules as mod}
                        <span class="text-[9px] font-medium bg-indigo-50 text-indigo-700 rounded px-1.5 py-0.5">{mod}</span>
                      {/each}
                    </div>
                  </td>
                  <td class="px-4 py-3 text-center"><StatusBadge status={d.status} /></td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </section>
    {/if}

  {:else if tab === "updates"}
    {#if updates.length === 0}
      <div class="rounded-2xl border border-neutral-200 bg-white px-6 py-14 text-center"><p class="text-sm text-neutral-500">No stakeholder updates.</p></div>
    {:else}
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        {#each updates as u}
          <button class="w-full text-left rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow cursor-pointer" onclick={() => openUpdateDetail(u.id)}>
            <div class="flex items-start justify-between mb-2">
              <div>
                <p class="text-sm font-semibold text-neutral-900">{u.title}</p>
                <p class="text-xs text-neutral-500 mt-0.5">{u.frequency_display} — {fmtDate(u.report_date)}</p>
              </div>
              {#if u.sent_at}<span class="text-[9px] font-semibold text-emerald-600 bg-emerald-50 rounded px-1.5 py-0.5">SENT</span>{:else}<span class="text-[9px] font-semibold text-amber-600 bg-amber-50 rounded px-1.5 py-0.5">DRAFT</span>{/if}
            </div>
            <div class="flex items-center gap-4 text-xs text-neutral-500">
              <span>Group: {u.distribution_group || "--"}</span>
              <span>{u.recipient_count} recipient{u.recipient_count !== 1 ? "s" : ""}</span>
              <span class="text-emerald-600 font-semibold">{u.read_count} read</span>
            </div>
          </button>
        {/each}
      </div>
    {/if}
  {/if}
</div>

<!-- ═══════════ UPDATE DETAIL DRAWER ═══════════ -->
<DrawerShell open={updateDetailOpen} title="Stakeholder Update" subtitle={updateDetail?.title ?? ""} width="max-w-2xl" onclose={() => (updateDetailOpen = false)}>
  {#if updateDetailLoading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if updateDetail}
    <div class="p-6 space-y-5">
      <div class="flex items-center gap-3">
        <span class="text-xs font-semibold text-neutral-600 bg-neutral-100 rounded-full px-3 py-1">{updateDetail.frequency_display}</span>
        <span class="text-xs text-neutral-500">{fmtDate(updateDetail.report_date)}</span>
        {#if updateDetail.sent_at}<span class="text-xs font-semibold text-emerald-600">Sent: {fmtDateTime(updateDetail.sent_at)}</span>{/if}
      </div>

      {#if updateDetail.executive_summary}<div><p class="text-[10px] font-semibold uppercase text-neutral-400 mb-1">Executive Summary</p><p class="text-sm text-neutral-700 whitespace-pre-line">{updateDetail.executive_summary}</p></div>{/if}
      {#if updateDetail.schedule_status}<div><p class="text-[10px] font-semibold uppercase text-neutral-400 mb-1">Schedule Status</p><p class="text-sm text-neutral-700 whitespace-pre-line">{updateDetail.schedule_status}</p></div>{/if}
      {#if updateDetail.financial_status}<div><p class="text-[10px] font-semibold uppercase text-neutral-400 mb-1">Financial Status</p><p class="text-sm text-neutral-700 whitespace-pre-line">{updateDetail.financial_status}</p></div>{/if}
      {#if updateDetail.risk_blockers}<div class="rounded-lg border border-amber-200 bg-amber-50 p-3"><p class="text-[10px] font-semibold uppercase text-amber-700 mb-1">Risks & Blockers</p><p class="text-sm text-amber-900 whitespace-pre-line">{updateDetail.risk_blockers}</p></div>{/if}

      <!-- Recipients -->
      {#if updateDetail.recipients && updateDetail.recipients.length > 0}
        <div>
          <p class="text-[10px] font-semibold uppercase text-neutral-400 mb-2">Recipients ({updateDetail.recipients.length})</p>
          <div class="space-y-1.5">
            {#each updateDetail.recipients as r}
              <div class="flex items-center justify-between rounded-lg border border-neutral-100 p-2.5">
                <div>
                  <p class="text-sm font-medium text-neutral-900">{r.name}</p>
                  <p class="text-[10px] text-neutral-400">{r.email}</p>
                </div>
                {#if r.read}<span class="text-[9px] font-semibold text-emerald-600 bg-emerald-50 rounded px-1.5 py-0.5">READ</span>{:else}<span class="text-[9px] font-semibold text-neutral-400 bg-neutral-100 rounded px-1.5 py-0.5">UNREAD</span>{/if}
              </div>
            {/each}
          </div>
        </div>
      {/if}

      <div class="grid grid-cols-2 gap-3 text-sm">
        <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Distribution Group</p><p class="text-neutral-900">{updateDetail.distribution_group || "--"}</p></div>
        <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Prepared By</p><p class="text-neutral-900">{updateDetail.prepared_by || "--"}</p></div>
      </div>

      {#if updateDetail.notes}<div><p class="text-[10px] font-semibold uppercase text-neutral-400 mb-1">Notes</p><p class="text-sm text-neutral-700 whitespace-pre-line">{updateDetail.notes}</p></div>{/if}
    </div>
  {/if}
</DrawerShell>

<!-- ═══════════ CREATE ANNOUNCEMENT DRAWER ═══════════ -->
<DrawerShell open={createOpen} title="New Announcement" subtitle="Publish a project-wide update" width="max-w-md" onclose={() => (createOpen = false)}>
  <form onsubmit={saveAnnouncement} class="p-6 space-y-4">
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Project *</span><select bind:value={form.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"><option value="">Select</option>{#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}</select></label>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Subject *</span><input bind:value={form.subject} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Body *</span><textarea bind:value={form.body} rows="5" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Priority</span><select bind:value={form.priority} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="critical">Critical</option><option value="high">High</option><option value="normal">Normal</option><option value="low">Low</option>
      </select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Audience</span><select bind:value={form.audience} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="all">All Stakeholders</option><option value="internal">Internal Team</option><option value="external">External</option><option value="investors">Investors</option><option value="consultants">Consultants</option>
      </select></label>
    </div>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Published By</span><input bind:value={form.published_by} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label class="flex items-center gap-2 pt-6"><input type="checkbox" bind:checked={form.is_pinned} class="h-4 w-4 rounded border-neutral-300" /><span class="text-xs font-semibold text-neutral-600">Pin to top</span></label>
    </div>
    <div class="flex justify-end gap-2 pt-2">
      <button type="button" onclick={() => (createOpen = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      {#if isDev}<button type="button" onclick={devFillAnnouncement} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
      <button type="submit" disabled={saving} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{saving ? "Publishing..." : "Publish"}</button>
    </div>
  </form>
</DrawerShell>

<!-- ═══════════ CREATE DECISION DRAWER ═══════════ -->
<DrawerShell open={createDecOpen} title="Log Decision" subtitle="Record a formal project decision" width="max-w-md" onclose={() => (createDecOpen = false)}>
  <form onsubmit={saveDecision} class="p-6 space-y-4">
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Project *</span><select bind:value={decForm.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"><option value="">Select</option>{#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}</select></label>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Subject *</span><input bind:value={decForm.subject} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Description</span><textarea bind:value={decForm.description} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Decided By *</span><input bind:value={decForm.decided_by} placeholder="e.g. Steering Committee" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Date</span><input type="date" bind:value={decForm.decision_date} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Rationale</span><textarea bind:value={decForm.rationale} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Impact Modules (comma-separated)</span><input bind:value={decForm.impact_modules} placeholder="e.g. Design, Budget, MEP" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Meeting Reference</span><input bind:value={decForm.meeting_reference} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <div class="flex justify-end gap-2 pt-2">
      <button type="button" onclick={() => (createDecOpen = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      {#if isDev}<button type="button" onclick={devFillDecision} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
      <button type="submit" disabled={savingDec} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{savingDec ? "Saving..." : "Log Decision"}</button>
    </div>
  </form>
</DrawerShell>

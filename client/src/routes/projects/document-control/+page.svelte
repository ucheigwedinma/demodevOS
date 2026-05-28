<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DrawerShell from "$lib/components/DrawerShell.svelte";
  import type {
    ProjectDocumentListItem,
    ProjectDocumentDetail,
    MeetingMinutesItem,
    DocumentFolder,
    DocumentClassification,
    DocumentExecutionStatus,
    PaginatedResponse,
    ProjectListItem,
  } from "$lib/types";

  let tab = $state<"index" | "minutes">("index");
  let loading = $state(true);
  let projects = $state<ProjectListItem[]>([]);
  let projectFilter = $state("");

  // Documents
  let docs = $state<ProjectDocumentListItem[]>([]);
  let searchInput = $state("");
  let searchQuery = $state("");
  let folderFilter = $state("");
  let classFilter = $state("");
  let statusFilter = $state("");
  let searchTimeout: ReturnType<typeof setTimeout> | undefined;

  // Minutes
  let minutes = $state<MeetingMinutesItem[]>([]);

  // Detail
  let detailOpen = $state(false);
  let detail = $state<ProjectDocumentDetail | null>(null);
  let detailLoading = $state(false);
  let detailTab = $state<"metadata" | "versions" | "transmittals">("metadata");

  // Create
  let createOpen = $state(false);
  let saving = $state(false);
  let form = $state(defaultForm());

  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  function defaultForm() {
    return {
      project: "", title: "", folder: "other" as DocumentFolder,
      classification: "internal" as DocumentClassification,
      execution_status: "draft" as DocumentExecutionStatus,
      current_version: "v1", author: "", source: "",
      description: "", retention_years: "", expiry_date: "",
      linked_module: "", notes: "",
    };
  }

  function devFill() {
    form = {
      ...form,
      project: form.project || (projects.length > 0 ? String(projects[0].id) : ""),
      title: "Main Contractor Agreement — Julius Berger Nigeria Plc",
      folder: "02_legal",
      classification: "confidential",
      execution_status: "executed",
      current_version: "Final",
      author: "Aluko & Oyebode (Legal Counsel)",
      source: "Legal Counsel",
      description: "Executed contract for main shell and core works. Includes all amendments and addenda through March 2026.",
      retention_years: "10",
      expiry_date: "",
      linked_module: "Consultant: Julius Berger, Budget: Construction Cost",
      notes: "Original deed held in office safe. Scanned copy uploaded.",
    };
  }

  async function fetchDocs() {
    loading = true;
    try {
      const params: Record<string, string> = { page_size: "200" };
      if (searchQuery) params.search = searchQuery;
      if (projectFilter) params.project = projectFilter;
      if (folderFilter) params.folder = folderFilter;
      if (classFilter) params.classification = classFilter;
      if (statusFilter) params.execution_status = statusFilter;

      const [res, projRes] = await Promise.all([
        api.get<PaginatedResponse<ProjectDocumentListItem>>("/projects/documents/", params),
        projects.length === 0 ? api.get<PaginatedResponse<ProjectListItem>>("/projects/", { page_size: "200", ordering: "name" }) : Promise.resolve(null),
      ]);
      docs = res.results;
      if (projRes) projects = projRes.results;
    } catch { docs = []; }
    loading = false;
  }

  async function fetchMinutes() {
    try {
      const params: Record<string, string> = { page_size: "100" };
      if (projectFilter) params.project = projectFilter;
      const res = await api.get<PaginatedResponse<MeetingMinutesItem>>("/projects/meeting-minutes/", params);
      minutes = res.results;
    } catch { minutes = []; }
  }

  $effect(() => { void searchQuery; void projectFilter; void folderFilter; void classFilter; void statusFilter; fetchDocs(); });
  $effect(() => { void projectFilter; if (tab === "minutes") fetchMinutes(); });

  function onSearchInput(e: Event) {
    searchInput = (e.target as HTMLInputElement).value;
    if (searchTimeout) clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => { searchQuery = searchInput.trim(); }, 250);
  }

  async function openDetail(id: number) {
    detailOpen = true;
    detailLoading = true;
    detailTab = "metadata";
    try { detail = await api.get<ProjectDocumentDetail>(`/projects/documents/${id}/`); } catch { detail = null; }
    detailLoading = false;
  }

  async function saveDoc(e: Event) {
    e.preventDefault();
    if (!form.project || !form.title.trim()) { toast.error("Required", "Project and title are required."); return; }
    saving = true;
    try {
      await api.post("/projects/documents/", {
        ...form,
        project: Number(form.project),
        retention_years: form.retention_years ? Number(form.retention_years) : null,
        expiry_date: form.expiry_date || null,
      });
      toast.success("Document registered", `"${form.title}" added to the archive.`);
      createOpen = false;
      form = defaultForm();
      await fetchDocs();
    } catch (error) {
      const msg = error instanceof ApiError ? (Object.values(error.fieldErrors)[0]?.[0] ?? "Save failed.") : "Save failed.";
      toast.error("Save failed", msg);
    } finally { saving = false; }
  }

  function fmtDate(v: string | null | undefined): string { if (!v) return "--"; const d = new Date(v); return Number.isNaN(d.getTime()) ? "--" : d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }); }

  function classColor(c: string): string {
    if (c === "confidential") return "bg-red-100 text-red-800";
    if (c === "restricted") return "bg-red-200 text-red-900";
    if (c === "internal") return "bg-blue-100 text-blue-800";
    return "bg-neutral-100 text-neutral-600";
  }

  function execColor(s: string): string {
    if (s === "executed") return "bg-emerald-100 text-emerald-800";
    if (s === "approved") return "bg-emerald-50 text-emerald-700";
    if (s === "for_review") return "bg-blue-100 text-blue-800";
    if (s === "superseded") return "bg-neutral-200 text-neutral-500";
    if (s === "scanned") return "bg-indigo-100 text-indigo-700";
    return "bg-neutral-100 text-neutral-600";
  }

  // Group docs by folder for the sidebar counts
  const folderCounts = $derived(() => {
    const counts: Record<string, number> = {};
    for (const d of docs) {
      counts[d.folder] = (counts[d.folder] || 0) + 1;
    }
    return counts;
  });
</script>

<div class="space-y-6">
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">Projects</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-900">Document Control</h1>
      <p class="mt-1 text-sm text-neutral-500">Master archive — indexed, versioned, and searchable project records.</p>
    </div>
    <div class="flex items-center gap-2">
      <select bind:value={projectFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
        <option value="">All Projects</option>
        {#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}
      </select>
      <button onclick={() => { form = defaultForm(); createOpen = true; }} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800">+ Register Document</button>
    </div>
  </div>

  <!-- Tabs -->
  <div class="flex gap-1 border-b border-neutral-200">
    {#each [["index", "Document Index"], ["minutes", "Meeting Minutes"]] as [key, label]}
      <button onclick={() => (tab = key as typeof tab)} class="px-4 py-2.5 text-sm font-semibold transition-colors border-b-2 -mb-px {tab === key ? 'text-neutral-900 border-neutral-900' : 'text-neutral-500 border-transparent hover:text-neutral-700'}">{label}</button>
    {/each}
  </div>

  {#if tab === "index"}
    <!-- Filters -->
    <div class="grid grid-cols-1 gap-3 xl:grid-cols-4">
      <input type="text" value={searchInput} oninput={onSearchInput} placeholder="Search reference, title, author, linked module..." class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
      <select bind:value={folderFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
        <option value="">All Folders</option>
        <option value="01_feasibility">01 — Feasibility</option><option value="02_legal">02 — Legal</option><option value="03_design">03 — Design</option>
        <option value="04_permits">04 — Permits</option><option value="05_governance">05 — Governance</option><option value="06_financial">06 — Financial</option>
        <option value="07_procurement">07 — Procurement</option><option value="08_construction">08 — Construction</option><option value="09_hse">09 — HSE</option>
        <option value="10_closeout">10 — Closeout</option><option value="other">Other</option>
      </select>
      <select bind:value={classFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
        <option value="">All Classifications</option>
        <option value="public">Public</option><option value="internal">Internal</option><option value="confidential">Confidential</option><option value="restricted">Restricted</option>
      </select>
      <select bind:value={statusFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
        <option value="">All Statuses</option>
        <option value="draft">Draft</option><option value="for_review">For Review</option><option value="approved">Approved</option>
        <option value="executed">Executed</option><option value="scanned">Scanned</option><option value="superseded">Superseded</option>
      </select>
    </div>

    {#if loading}
      <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
    {:else if docs.length === 0}
      <div class="rounded-2xl border border-neutral-200 bg-white px-6 py-14 text-center"><p class="text-sm text-neutral-500">No documents found.</p></div>
    {:else}
      <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
        <div class="overflow-x-auto">
          <table class="min-w-[950px] w-full">
            <thead class="bg-neutral-50 border-b border-neutral-200">
              <tr>
                <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Ref</th>
                <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Title</th>
                <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Folder</th>
                <th class="px-4 py-3 text-center text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Class</th>
                <th class="px-4 py-3 text-center text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Status</th>
                <th class="px-4 py-3 text-center text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Ver</th>
                <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Author</th>
                <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Updated</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each docs as d}
                <tr class="hover:bg-neutral-50 cursor-pointer {d.is_expiring_soon ? 'bg-amber-50/30' : ''} {d.execution_status === 'superseded' ? 'opacity-50' : ''}" onclick={() => openDetail(d.id)}>
                  <td class="px-4 py-3 text-sm font-semibold text-neutral-900">{d.reference}</td>
                  <td class="px-4 py-3 text-sm text-neutral-700 max-w-[240px] truncate">
                    {d.title}
                    {#if d.is_expiring_soon}<span class="ml-1 text-[8px] font-bold text-amber-600 bg-amber-50 px-1 py-0.5 rounded">EXPIRING</span>{/if}
                  </td>
                  <td class="px-4 py-3 text-xs text-neutral-600">{d.folder_display}</td>
                  <td class="px-4 py-3 text-center"><span class="inline-block rounded-full px-2 py-0.5 text-[9px] font-semibold {classColor(d.classification)}">{d.classification_display}</span></td>
                  <td class="px-4 py-3 text-center"><span class="inline-block rounded-full px-2 py-0.5 text-[9px] font-semibold {execColor(d.execution_status)}">{d.execution_status_display}</span></td>
                  <td class="px-4 py-3 text-center text-sm font-bold text-neutral-900">{d.current_version}</td>
                  <td class="px-4 py-3 text-sm text-neutral-600 max-w-[120px] truncate">{d.author || "--"}</td>
                  <td class="px-4 py-3 text-xs text-neutral-500">{fmtDate(d.updated_at)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </section>
    {/if}

  {:else if tab === "minutes"}
    {#if minutes.length === 0}
      <div class="rounded-2xl border border-neutral-200 bg-white px-6 py-14 text-center"><p class="text-sm text-neutral-500">No meeting minutes found.</p></div>
    {:else}
      <div class="space-y-3">
        {#each minutes as m}
          <div class="rounded-xl border border-neutral-200 bg-white p-5">
            <div class="flex items-center justify-between mb-2">
              <div>
                <p class="text-sm font-semibold text-neutral-900">{m.title}</p>
                <p class="text-xs text-neutral-500">{m.series} — {fmtDate(m.date)}</p>
              </div>
              {#if m.recorded_by}<span class="text-[10px] text-neutral-400">By: {m.recorded_by}</span>{/if}
            </div>
            {#if m.attendees}<p class="text-xs text-neutral-500 mb-2">Attendees: {m.attendees}</p>{/if}
            {#if m.minutes_text}<p class="text-sm text-neutral-700 whitespace-pre-line mb-2 max-h-32 overflow-y-auto">{m.minutes_text}</p>{/if}
            {#if m.action_items && m.action_items.length > 0}
              <div>
                <p class="text-[10px] font-semibold uppercase text-neutral-400 mb-1">Action Items</p>
                <ul class="space-y-1">
                  {#each m.action_items as ai}
                    <li class="flex items-center gap-2 text-xs">
                      <span class="h-1.5 w-1.5 rounded-full shrink-0 {ai.status === 'done' ? 'bg-emerald-500' : 'bg-blue-400'}"></span>
                      <span class="text-neutral-700">{ai.description}</span>
                      {#if ai.assigned_to}<span class="text-neutral-400">— {ai.assigned_to}</span>{/if}
                      {#if ai.due_date}<span class="text-amber-600 font-medium">Due: {fmtDate(ai.due_date)}</span>{/if}
                    </li>
                  {/each}
                </ul>
              </div>
            {/if}
          </div>
        {/each}
      </div>
    {/if}
  {/if}
</div>

<!-- ═══════════ DETAIL DRAWER ═══════════ -->
<DrawerShell open={detailOpen} title="Document Profile" subtitle={detail ? `${detail.reference} — ${detail.title}` : ""} width="max-w-2xl" onclose={() => (detailOpen = false)}>
  {#if detailLoading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if detail}
    <div class="border-b border-neutral-200">
      <div class="flex gap-1 px-6 pt-4">
        {#each [["metadata", "Metadata"], ["versions", "Versions"], ["transmittals", "Transmittals"]] as [key, label]}
          <button onclick={() => (detailTab = key as typeof detailTab)} class="rounded-t-lg px-4 py-2 text-xs font-semibold transition-colors {detailTab === key ? 'bg-white text-neutral-900 border border-b-white border-neutral-200 -mb-px' : 'text-neutral-500 hover:text-neutral-700'}">{label}</button>
        {/each}
      </div>
    </div>

    <div class="p-6 space-y-5">
      {#if detailTab === "metadata"}
        <div class="flex items-center gap-3">
          <span class="inline-block rounded-full px-2.5 py-0.5 text-[10px] font-semibold {execColor(detail.execution_status)}">{detail.execution_status_display}</span>
          <span class="inline-block rounded-full px-2.5 py-0.5 text-[10px] font-semibold {classColor(detail.classification)}">{detail.classification_display}</span>
          <span class="text-sm font-bold text-neutral-900">{detail.current_version}</span>
          {#if detail.is_expiring_soon}<span class="text-[9px] font-bold text-amber-600 bg-amber-50 rounded px-1.5 py-0.5">EXPIRING SOON</span>{/if}
        </div>

        <div class="grid grid-cols-2 gap-3 text-sm">
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Folder</p><p class="text-neutral-900">{detail.folder_display}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Author</p><p class="text-neutral-900">{detail.author || "--"}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Source</p><p class="text-neutral-900">{detail.source || "--"}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Retention</p><p class="text-neutral-900">{detail.retention_years ? `${detail.retention_years} years` : "--"}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Expiry Date</p><p class="{detail.is_expiring_soon ? 'text-amber-600 font-semibold' : 'text-neutral-900'}">{fmtDate(detail.expiry_date)}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Linked Module</p><p class="text-neutral-900">{detail.linked_module || "--"}</p></div>
        </div>

        {#if detail.description}<div><p class="text-[10px] font-semibold uppercase text-neutral-400 mb-1">Description</p><p class="text-sm text-neutral-700 whitespace-pre-line">{detail.description}</p></div>{/if}
        {#if detail.notes}<div><p class="text-[10px] font-semibold uppercase text-neutral-400 mb-1">Notes</p><p class="text-sm text-neutral-700 whitespace-pre-line">{detail.notes}</p></div>{/if}

      {:else if detailTab === "versions"}
        {#if detail.versions.length === 0}
          <p class="text-sm text-neutral-400 text-center py-6">No version history recorded.</p>
        {:else}
          <div class="space-y-2">
            {#each detail.versions as v}
              <div class="rounded-lg border border-neutral-200 p-3 {v.is_current ? 'border-emerald-200 bg-emerald-50/30' : ''}">
                <div class="flex items-center justify-between mb-1">
                  <div class="flex items-center gap-2">
                    <span class="text-sm font-bold text-neutral-900">{v.version_label}</span>
                    {#if v.is_current}<span class="text-[9px] font-semibold text-emerald-600 bg-emerald-100 rounded px-1.5 py-0.5">CURRENT</span>{/if}
                  </div>
                  <span class="text-xs text-neutral-400">{fmtDate(v.uploaded_date)}</span>
                </div>
                {#if v.change_summary}<p class="text-xs text-neutral-600">{v.change_summary}</p>{/if}
                {#if v.uploaded_by}<p class="text-[10px] text-neutral-400 mt-1">By: {v.uploaded_by}</p>{/if}
              </div>
            {/each}
          </div>
        {/if}

      {:else if detailTab === "transmittals"}
        {#if detail.transmittals.length === 0}
          <p class="text-sm text-neutral-400 text-center py-6">No transmittals recorded.</p>
        {:else}
          <table class="w-full">
            <thead class="bg-neutral-50"><tr>
              <th class="px-3 py-2 text-left text-[10px] font-semibold uppercase text-neutral-500">Ref</th>
              <th class="px-3 py-2 text-left text-[10px] font-semibold uppercase text-neutral-500">Recipient</th>
              <th class="px-3 py-2 text-left text-[10px] font-semibold uppercase text-neutral-500">Purpose</th>
              <th class="px-3 py-2 text-left text-[10px] font-semibold uppercase text-neutral-500">Sent</th>
              <th class="px-3 py-2 text-center text-[10px] font-semibold uppercase text-neutral-500">Ack</th>
            </tr></thead>
            <tbody class="divide-y divide-neutral-100">
              {#each detail.transmittals as t}
                <tr>
                  <td class="px-3 py-2 text-sm font-medium text-neutral-900">{t.transmittal_ref || "--"}</td>
                  <td class="px-3 py-2 text-sm text-neutral-700">{t.recipient}</td>
                  <td class="px-3 py-2 text-xs text-neutral-600">{t.purpose_display}</td>
                  <td class="px-3 py-2 text-sm text-neutral-600">{fmtDate(t.sent_date)}</td>
                  <td class="px-3 py-2 text-center">
                    {#if t.acknowledged}
                      <span class="text-emerald-600 text-xs font-semibold">{fmtDate(t.acknowledged_date)}</span>
                    {:else}
                      <span class="text-amber-600 text-xs font-semibold">Pending</span>
                    {/if}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}
      {/if}
    </div>
  {/if}
</DrawerShell>

<!-- ═══════════ CREATE DRAWER ═══════════ -->
<DrawerShell open={createOpen} title="Register Document" subtitle="Add a new record to the archive" width="max-w-xl" onclose={() => (createOpen = false)}>
  <form onsubmit={saveDoc} class="p-6 space-y-4">
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Project *</span><select bind:value={form.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"><option value="">Select</option>{#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}</select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Folder</span><select bind:value={form.folder} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="01_feasibility">01 — Feasibility</option><option value="02_legal">02 — Legal</option><option value="03_design">03 — Design</option>
        <option value="04_permits">04 — Permits</option><option value="05_governance">05 — Governance</option><option value="06_financial">06 — Financial</option>
        <option value="07_procurement">07 — Procurement</option><option value="08_construction">08 — Construction</option><option value="09_hse">09 — HSE</option>
        <option value="10_closeout">10 — Closeout</option><option value="other">Other</option>
      </select></label>
    </div>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Title *</span><input bind:value={form.title} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <div class="grid grid-cols-3 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Classification</span><select bind:value={form.classification} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="public">Public</option><option value="internal">Internal</option><option value="confidential">Confidential</option><option value="restricted">Restricted</option>
      </select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Execution Status</span><select bind:value={form.execution_status} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="draft">Draft</option><option value="for_review">For Review</option><option value="approved">Approved</option>
        <option value="executed">Executed</option><option value="scanned">Scanned</option>
      </select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Version</span><input bind:value={form.current_version} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Author</span><input bind:value={form.author} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Source</span><input bind:value={form.source} placeholder="e.g. Legal Counsel" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Retention (years)</span><input type="number" bind:value={form.retention_years} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Expiry Date</span><input type="date" bind:value={form.expiry_date} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Description</span><textarea bind:value={form.description} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Linked Module</span><input bind:value={form.linked_module} placeholder="e.g. Consultant: Adesanya, Permit: PRM-00012" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <div class="flex justify-end gap-2 pt-2">
      <button type="button" onclick={() => (createOpen = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      {#if isDev}<button type="button" onclick={devFill} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
      <button type="submit" disabled={saving} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{saving ? "Saving..." : "Register"}</button>
    </div>
  </form>
</DrawerShell>

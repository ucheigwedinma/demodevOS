<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { useAutoRefresh } from "$lib/realtime.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DrawerShell from "$lib/components/DrawerShell.svelte";
  import type {
    ProjectPermitListItem,
    ProjectPermitDetail,
    PermitSummary,
    PermitType,
    PermitStatus,
    PaginatedResponse,
    ProjectListItem,
  } from "$lib/types";

  let rows = $state<ProjectPermitListItem[]>([]);
  let summary = $state<PermitSummary | null>(null);
  let loading = $state(true);
  let projects = $state<ProjectListItem[]>([]);
  let searchInput = $state("");
  let searchQuery = $state("");
  let projectFilter = $state("");
  let typeFilter = $state("");
  let statusFilter = $state("");
  let criticalOnly = $state(false);
  let searchTimeout: ReturnType<typeof setTimeout> | undefined;

  let detailOpen = $state(false);
  let detail = $state<ProjectPermitDetail | null>(null);
  let detailLoading = $state(false);
  let detailTab = $state<"overview" | "submissions" | "queries">("overview");

  let createOpen = $state(false);
  let saving = $state(false);
  let form = $state(defaultForm());

  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  function defaultForm() {
    return {
      project: "", name: "", permit_type: "building" as PermitType,
      status: "not_started" as PermitStatus, is_critical_path: false,
      authority_name: "", authority_contact: "", authority_portal: "",
      application_date: "", expected_approval_date: "",
      expiry_date: "", application_fee: "", notes: "",
    };
  }

  function devFill() {
    form = {
      ...form,
      project: form.project || (projects.length > 0 ? String(projects[0].id) : ""),
      name: "Building Permit — Phase 1 Superstructure",
      permit_type: "building",
      status: "under_review",
      is_critical_path: true,
      authority_name: "Lagos State Physical Planning Permit Authority (LASPPPA)",
      authority_contact: "Engr. Adeoye — Desk Officer, Zone C",
      authority_portal: "",
      application_date: "2026-01-15",
      expected_approval_date: "2026-04-15",
      expiry_date: "",
      application_fee: "2500000",
      notes: "Structural drawings submitted Rev 02. Awaiting structural adequacy review from LABSCA. Fire safety clearance pending — dependency.",
    };
  }

  async function fetchData() {
    loading = true;
    try {
      const params: Record<string, string> = { page_size: "100" };
      if (searchQuery) params.search = searchQuery;
      if (projectFilter) params.project = projectFilter;
      if (typeFilter) params.permit_type = typeFilter;
      if (statusFilter) params.status = statusFilter;
      if (criticalOnly) params.is_critical_path = "true";

      const [res, sumRes, projRes] = await Promise.all([
        api.get<PaginatedResponse<ProjectPermitListItem>>("/projects/permits/", params),
        api.get<PermitSummary>("/projects/permits/summary/"),
        projects.length === 0 ? api.get<PaginatedResponse<ProjectListItem>>("/projects/", { page_size: "200", ordering: "name" }) : Promise.resolve(null),
      ]);
      rows = res.results;
      summary = sumRes;
      if (projRes) projects = projRes.results;
    } catch { rows = []; }
    loading = false;
  }

  $effect(() => { void searchQuery; void projectFilter; void typeFilter; void statusFilter; void criticalOnly; fetchData(); });

  function onSearchInput(e: Event) {
    searchInput = (e.target as HTMLInputElement).value;
    if (searchTimeout) clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => { searchQuery = searchInput.trim(); }, 250);
  }

  async function openDetail(id: number) {
    detailOpen = true;
    detailLoading = true;
    detailTab = "overview";
    try { detail = await api.get<ProjectPermitDetail>(`/projects/permits/${id}/`); } catch { detail = null; }
    detailLoading = false;
  }

  async function savePermit(e: Event) {
    e.preventDefault();
    if (!form.project || !form.name.trim()) { toast.error("Required", "Project and permit name are required."); return; }
    saving = true;
    try {
      await api.post("/projects/permits/", {
        ...form,
        project: Number(form.project),
        application_date: form.application_date || null,
        expected_approval_date: form.expected_approval_date || null,
        expiry_date: form.expiry_date || null,
        application_fee: form.application_fee || "0",
      });
      toast.success("Permit added", `"${form.name}" registered.`);
      createOpen = false;
      form = defaultForm();
      await fetchData();
    } catch (error) {
      const msg = error instanceof ApiError ? (Object.values(error.fieldErrors)[0]?.[0] ?? "Save failed.") : "Save failed.";
      toast.error("Save failed", msg);
    } finally { saving = false; }
  }

  function fmtDate(v: string | null | undefined): string { if (!v) return "--"; const d = new Date(v); return Number.isNaN(d.getTime()) ? "--" : d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }); }
  function fmtC(v: string | number | null | undefined): string { if (!v || v === "0.00" || v === "0") return "--"; return currency.formatCompact(v); }

  function permitStatusColor(status: string, isDelayed: boolean): string {
    if (isDelayed) return "bg-red-100 text-red-800 border-red-200";
    if (status === "approved" || status === "renewed") return "bg-emerald-100 text-emerald-800 border-emerald-200";
    if (status === "conditional") return "bg-emerald-50 text-emerald-700 border-emerald-200";
    if (status === "clarification") return "bg-amber-100 text-amber-800 border-amber-200";
    if (status === "rejected") return "bg-red-100 text-red-800 border-red-200";
    if (status === "expired") return "bg-neutral-200 text-neutral-600 border-neutral-300";
    if (status === "under_review") return "bg-blue-100 text-blue-800 border-blue-200";
    return "bg-neutral-100 text-neutral-600 border-neutral-200";
  }

  useAutoRefresh("Permit", fetchData);
</script>

<div class="space-y-6">
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">Projects</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-900">Approvals & Permits</h1>
      <p class="mt-1 text-sm text-neutral-500">Regulatory control center — track permits, submissions, and authority queries.</p>
    </div>
    <button onclick={() => { form = defaultForm(); createOpen = true; }} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800">+ Add Permit</button>
  </div>

  <!-- Status Board -->
  {#if summary}
    <div class="grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-7">
      <div class="rounded-xl border border-neutral-200 bg-white p-3.5 text-center">
        <p class="text-[9px] font-semibold uppercase tracking-wider text-neutral-500">Total</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{summary.total}</p>
      </div>
      <div class="rounded-xl border border-amber-100 bg-amber-50 p-3.5 text-center">
        <p class="text-[9px] font-semibold uppercase tracking-wider text-amber-700">Pending</p>
        <p class="mt-1 text-xl font-bold text-amber-900 tabular-nums">{summary.pending}</p>
      </div>
      <div class="rounded-xl border border-emerald-100 bg-emerald-50 p-3.5 text-center">
        <p class="text-[9px] font-semibold uppercase tracking-wider text-emerald-700">Approved</p>
        <p class="mt-1 text-xl font-bold text-emerald-900 tabular-nums">{summary.approved}</p>
      </div>
      <div class="rounded-xl border border-red-100 bg-red-50 p-3.5 text-center">
        <p class="text-[9px] font-semibold uppercase tracking-wider text-red-700">Rejected</p>
        <p class="mt-1 text-xl font-bold text-red-900 tabular-nums">{summary.rejected}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-3.5 text-center">
        <p class="text-[9px] font-semibold uppercase tracking-wider text-neutral-500">Expired</p>
        <p class="mt-1 text-xl font-bold text-neutral-700 tabular-nums">{summary.expired}</p>
      </div>
      <div class="rounded-xl border border-red-200 bg-red-50 p-3.5 text-center">
        <p class="text-[9px] font-semibold uppercase tracking-wider text-red-700">Delayed</p>
        <p class="mt-1 text-xl font-bold text-red-900 tabular-nums">{summary.delayed}</p>
      </div>
      <div class="rounded-xl border border-indigo-100 bg-indigo-50 p-3.5 text-center">
        <p class="text-[9px] font-semibold uppercase tracking-wider text-indigo-700">Critical Path</p>
        <p class="mt-1 text-xl font-bold text-indigo-900 tabular-nums">{summary.critical_path_pending}</p>
      </div>
    </div>
  {/if}

  <!-- Filters -->
  <div class="grid grid-cols-1 gap-3 xl:grid-cols-5">
    <input type="text" value={searchInput} oninput={onSearchInput} placeholder="Search reference, name, authority..." class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
    <select bind:value={projectFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Projects</option>
      {#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}
    </select>
    <select bind:value={typeFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Types</option>
      <option value="environmental">Environmental (EIA)</option><option value="planning">Planning Permission</option><option value="building">Building Permit</option>
      <option value="fire_safety">Fire Safety</option><option value="utility_water">Water</option><option value="utility_power">Power</option>
      <option value="utility_sewer">Sewer/Drainage</option><option value="road_closure">Road Closure</option><option value="occupancy">Certificate of Occupancy</option><option value="other">Other</option>
    </select>
    <select bind:value={statusFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Statuses</option>
      <option value="not_started">Not Started</option><option value="application_filed">Filed</option><option value="under_review">Under Review</option>
      <option value="clarification">Clarification</option><option value="approved">Approved</option><option value="conditional">Conditional</option>
      <option value="rejected">Rejected</option><option value="expired">Expired</option><option value="renewed">Renewed</option>
    </select>
    <label class="flex items-center gap-2 text-sm text-neutral-700">
      <input type="checkbox" bind:checked={criticalOnly} class="h-4 w-4 rounded border-neutral-300" />
      Critical Path Only
    </label>
  </div>

  <!-- Permits Table -->
  {#if loading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if rows.length === 0}
    <div class="rounded-2xl border border-neutral-200 bg-white px-6 py-14 text-center"><p class="text-sm text-neutral-500">No permits found.</p></div>
  {:else}
    <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
      <div class="overflow-x-auto">
        <table class="min-w-[1000px] w-full">
          <thead class="bg-neutral-50 border-b border-neutral-200">
            <tr>
              <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Reference</th>
              <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Permit</th>
              <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Type</th>
              <th class="px-4 py-3 text-center text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Status</th>
              <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Authority</th>
              <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Applied</th>
              <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Expected</th>
              <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Expiry</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each rows as p}
              <tr class="hover:bg-neutral-50 cursor-pointer {p.is_delayed ? 'bg-red-50/30' : ''}" onclick={() => openDetail(p.id)}>
                <td class="px-4 py-3 text-sm font-semibold text-neutral-900">
                  {p.reference}
                  {#if p.is_critical_path}<span class="ml-1 text-[8px] font-bold text-indigo-600 bg-indigo-50 px-1 py-0.5 rounded">CP</span>{/if}
                </td>
                <td class="px-4 py-3">
                  <p class="text-sm font-medium text-neutral-900 max-w-[220px] truncate">{p.name}</p>
                  {#if p.depends_on_name}<p class="text-[10px] text-neutral-400 mt-0.5">Depends on: {p.depends_on_name}</p>{/if}
                </td>
                <td class="px-4 py-3 text-xs text-neutral-600">{p.permit_type_display}</td>
                <td class="px-4 py-3 text-center">
                  <span class="inline-block rounded-full border px-2.5 py-0.5 text-[10px] font-semibold {permitStatusColor(p.status, p.is_delayed)}">
                    {p.is_delayed ? "DELAYED" : p.status_display}
                  </span>
                </td>
                <td class="px-4 py-3 text-sm text-neutral-600 max-w-[160px] truncate">{p.authority_name || "--"}</td>
                <td class="px-4 py-3 text-sm text-neutral-600">{fmtDate(p.application_date)}</td>
                <td class="px-4 py-3 text-sm text-neutral-600">{fmtDate(p.expected_approval_date)}</td>
                <td class="px-4 py-3 text-sm {p.days_until_expiry !== null && p.days_until_expiry <= 30 ? 'text-red-600 font-semibold' : 'text-neutral-600'}">
                  {fmtDate(p.expiry_date)}
                  {#if p.days_until_expiry !== null && p.days_until_expiry <= 30 && p.days_until_expiry > 0}<span class="text-[9px]"> ({p.days_until_expiry}d)</span>{/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>
  {/if}
</div>

<!-- ═══════════ DETAIL DRAWER ═══════════ -->
<DrawerShell open={detailOpen} title="Permit Detail" subtitle={detail ? `${detail.reference} — ${detail.name}` : ""} width="max-w-2xl" onclose={() => (detailOpen = false)}>
  {#if detailLoading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if detail}
    <div class="border-b border-neutral-200">
      <div class="flex gap-1 px-6 pt-4">
        {#each [["overview", "Overview"], ["submissions", "Submissions"], ["queries", "Queries"]] as [key, label]}
          <button onclick={() => (detailTab = key as typeof detailTab)} class="rounded-t-lg px-4 py-2 text-xs font-semibold transition-colors {detailTab === key ? 'bg-white text-neutral-900 border border-b-white border-neutral-200 -mb-px' : 'text-neutral-500 hover:text-neutral-700'}">{label}</button>
        {/each}
      </div>
    </div>

    <div class="p-6 space-y-5">
      {#if detailTab === "overview"}
        <div class="flex items-center gap-3">
          <span class="inline-block rounded-full border px-2.5 py-0.5 text-[10px] font-semibold {permitStatusColor(detail.status, detail.is_delayed)}">
            {detail.is_delayed ? "DELAYED" : detail.status_display}
          </span>
          <span class="text-xs text-neutral-500">{detail.permit_type_display}</span>
          {#if detail.is_critical_path}<span class="text-[9px] font-bold text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded">Critical Path</span>{/if}
        </div>

        <div class="grid grid-cols-2 gap-3 text-sm">
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Authority</p><p class="text-neutral-900 font-medium">{detail.authority_name || "--"}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Contact</p><p class="text-neutral-900">{detail.authority_contact || "--"}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Application Date</p><p class="text-neutral-900">{fmtDate(detail.application_date)}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Expected Approval</p><p class="text-neutral-900 {detail.is_delayed ? 'text-red-600 font-semibold' : ''}">{fmtDate(detail.expected_approval_date)}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Actual Approval</p><p class="text-neutral-900 font-medium">{fmtDate(detail.actual_approval_date)}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Expiry</p><p class="{detail.days_until_expiry !== null && detail.days_until_expiry <= 30 ? 'text-red-600 font-semibold' : 'text-neutral-900'}">{fmtDate(detail.expiry_date)} {detail.days_until_expiry !== null ? `(${detail.days_until_expiry}d)` : ""}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Application Fee</p><p class="text-neutral-900">{fmtC(detail.application_fee)} {detail.fee_paid ? "(Paid)" : "(Unpaid)"}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Certificate Ref</p><p class="text-neutral-900">{detail.approval_certificate_ref || "--"}</p></div>
        </div>

        {#if detail.conditions}<div class="rounded-lg border border-amber-200 bg-amber-50 p-3"><p class="text-[10px] font-semibold uppercase text-amber-700 mb-1">Conditions</p><p class="text-sm text-amber-900 whitespace-pre-line">{detail.conditions}</p></div>{/if}
        {#if detail.rejection_reason}<div class="rounded-lg border border-red-200 bg-red-50 p-3"><p class="text-[10px] font-semibold uppercase text-red-700 mb-1">Rejection Reason</p><p class="text-sm text-red-900 whitespace-pre-line">{detail.rejection_reason}</p></div>{/if}
        {#if detail.notes}<div><p class="text-[10px] font-semibold uppercase text-neutral-400 mb-1">Notes</p><p class="text-sm text-neutral-700 whitespace-pre-line">{detail.notes}</p></div>{/if}

      {:else if detailTab === "submissions"}
        {#if detail.submissions.length === 0}
          <p class="text-sm text-neutral-400 text-center py-6">No submissions recorded.</p>
        {:else}
          <div class="space-y-3">
            {#each detail.submissions as sub}
              <div class="rounded-lg border border-neutral-200 p-3">
                <div class="flex items-center justify-between mb-1">
                  <p class="text-sm font-semibold text-neutral-900">{sub.version} — {sub.description}</p>
                  <span class="text-xs text-neutral-400">{fmtDate(sub.submission_date)}</span>
                </div>
                {#if sub.documents_list}<p class="text-xs text-neutral-600 mt-1">{sub.documents_list}</p>{/if}
                {#if sub.submitted_by}<p class="text-[10px] text-neutral-400 mt-1">By: {sub.submitted_by}</p>{/if}
                {#if sub.authority_receipt_ref}<p class="text-[10px] text-neutral-500 mt-0.5">Receipt: {sub.authority_receipt_ref}</p>{/if}
              </div>
            {/each}
          </div>
        {/if}

      {:else if detailTab === "queries"}
        {#if detail.queries.length === 0}
          <p class="text-sm text-neutral-400 text-center py-6">No queries from authority.</p>
        {:else}
          <div class="space-y-3">
            {#each detail.queries as q}
              <div class="rounded-lg border border-neutral-200 p-3">
                <div class="flex items-center justify-between mb-1">
                  <div class="flex items-center gap-2">
                    <StatusBadge status={q.status} />
                    <p class="text-sm font-semibold text-neutral-900">{q.subject}</p>
                  </div>
                  <span class="text-xs text-neutral-400">{fmtDate(q.query_date)}</span>
                </div>
                {#if q.description}<p class="text-xs text-neutral-600 mt-1">{q.description}</p>{/if}
                {#if q.assigned_consultant}<p class="text-[10px] text-indigo-600 mt-1 font-medium">Assigned: {q.assigned_consultant}</p>{/if}
                {#if q.response}
                  <div class="mt-2 rounded-md bg-emerald-50 p-2">
                    <p class="text-[10px] font-semibold text-emerald-700">Response ({fmtDate(q.response_date)}):</p>
                    <p class="text-xs text-emerald-900 mt-0.5">{q.response}</p>
                  </div>
                {/if}
              </div>
            {/each}
          </div>
        {/if}
      {/if}
    </div>
  {/if}
</DrawerShell>

<!-- ═══════════ CREATE DRAWER ═══════════ -->
<DrawerShell open={createOpen} title="Add Permit" subtitle="Register a regulatory requirement" width="max-w-xl" onclose={() => (createOpen = false)}>
  <form onsubmit={savePermit} class="p-6 space-y-4">
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Project *</span><select bind:value={form.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"><option value="">Select</option>{#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}</select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Type</span><select bind:value={form.permit_type} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="environmental">Environmental (EIA)</option><option value="planning">Planning Permission</option><option value="building">Building Permit</option>
        <option value="fire_safety">Fire Safety</option><option value="utility_water">Water</option><option value="utility_power">Power</option>
        <option value="utility_sewer">Sewer/Drainage</option><option value="road_closure">Road Closure</option><option value="occupancy">Certificate of Occupancy</option><option value="other">Other</option>
      </select></label>
    </div>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Permit Name *</span><input bind:value={form.name} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Authority</span><input bind:value={form.authority_name} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Contact</span><input bind:value={form.authority_contact} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Application Date</span><input type="date" bind:value={form.application_date} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Expected Approval</span><input type="date" bind:value={form.expected_approval_date} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Application Fee</span><input type="number" step="0.01" bind:value={form.application_fee} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label class="flex items-center gap-2 pt-6">
        <input type="checkbox" bind:checked={form.is_critical_path} class="h-4 w-4 rounded border-neutral-300" />
        <span class="text-xs font-semibold text-neutral-600">Critical Path</span>
      </label>
    </div>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Notes</span><textarea bind:value={form.notes} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <div class="flex justify-end gap-2 pt-2">
      <button type="button" onclick={() => (createOpen = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      {#if isDev}<button type="button" onclick={devFill} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
      <button type="submit" disabled={saving} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{saving ? "Saving..." : "Add Permit"}</button>
    </div>
  </form>
</DrawerShell>

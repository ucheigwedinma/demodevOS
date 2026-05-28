<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { useAutoRefresh } from "$lib/realtime.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DrawerShell from "$lib/components/DrawerShell.svelte";
  import type {
    StageGateListItem,
    StageGateDetail,
    StageGateSummary,
    PaginatedResponse,
    ProjectListItem,
  } from "$lib/types";

  let gates = $state<StageGateListItem[]>([]);
  let summary = $state<StageGateSummary | null>(null);
  let loading = $state(true);
  let projects = $state<ProjectListItem[]>([]);
  let projectFilter = $state("");

  let detailOpen = $state(false);
  let detail = $state<StageGateDetail | null>(null);
  let detailLoading = $state(false);

  let createOpen = $state(false);
  let saving = $state(false);
  let form = $state(defaultForm());

  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  const GATE_TYPE_OPTIONS = [
    { value: "feasibility", label: "Feasibility Gate", sort: 1 },
    { value: "investment_approval", label: "Investment Approval Gate", sort: 2 },
    { value: "pre_construction", label: "Pre-Construction Gate", sort: 3 },
    { value: "design_completion", label: "Design Completion Gate", sort: 4 },
    { value: "procurement_completion", label: "Procurement Completion Gate", sort: 5 },
    { value: "construction_midpoint", label: "Construction Midpoint Gate", sort: 6 },
    { value: "practical_completion", label: "Practical Completion Gate", sort: 7 },
    { value: "testing_commissioning", label: "Testing & Commissioning Gate", sort: 8 },
    { value: "handover", label: "Handover Gate", sort: 9 },
    { value: "closeout", label: "Closeout Gate", sort: 10 },
    { value: "custom", label: "Custom Gate", sort: 99 },
  ] as const;

  function defaultForm() {
    return {
      project: "", gate_type: "custom", name: "", description: "",
      status: "locked", sort_order: "0",
      scheduled_review_date: "", baseline_date: "",
      decided_by: "", notes: "",
    };
  }

  function onGateTypeChange() {
    const selected = GATE_TYPE_OPTIONS.find(g => g.value === form.gate_type);
    if (selected && form.gate_type !== "custom") {
      form.name = selected.label;
      form.sort_order = String(selected.sort);
    }
  }

  function devFill() {
    form = {
      project: form.project || (projects.length > 0 ? String(projects[0].id) : ""),
      gate_type: "pre_construction",
      name: "Pre-Construction Gate",
      description: "All design and regulatory prerequisites must be met before site mobilization can commence. This gate validates that financing is secured, permits are in hand, and the main contractor is appointed.",
      status: "under_review",
      sort_order: "2",
      scheduled_review_date: "2026-04-15",
      baseline_date: "2026-04-01",
      decided_by: "Investment Committee",
      notes: "Design development drawings at Rev C. Pending fire safety clearance from LASG. GTBank facility letter received — awaiting board ratification.",
    };
  }

  async function fetchData() {
    loading = true;
    try {
      const params: Record<string, string> = { page_size: "100" };
      if (projectFilter) params.project = projectFilter;
      const summaryParams: Record<string, string> = {};
      if (projectFilter) summaryParams.project = projectFilter;

      const [res, sumRes, projRes] = await Promise.all([
        api.get<PaginatedResponse<StageGateListItem>>("/projects/stage-gates/", params),
        api.get<StageGateSummary>("/projects/stage-gates/summary/", summaryParams),
        projects.length === 0 ? api.get<PaginatedResponse<ProjectListItem>>("/projects/", { page_size: "200", ordering: "name" }) : Promise.resolve(null),
      ]);
      gates = res.results;
      summary = sumRes;
      if (projRes) projects = projRes.results;
    } catch { gates = []; }
    loading = false;
  }

  $effect(() => { void projectFilter; fetchData(); });

  async function openDetail(id: number) {
    detailOpen = true;
    detailLoading = true;
    try { detail = await api.get<StageGateDetail>(`/projects/stage-gates/${id}/`); } catch { detail = null; }
    detailLoading = false;
  }

  async function saveGate(e: Event) {
    e.preventDefault();
    if (!form.project || !form.name.trim()) { toast.error("Required", "Project and gate name are required."); return; }
    saving = true;
    try {
      await api.post("/projects/stage-gates/", {
        ...form,
        project: Number(form.project),
        sort_order: Number(form.sort_order) || 0,
        scheduled_review_date: form.scheduled_review_date || null,
        baseline_date: form.baseline_date || null,
        prerequisite_milestones: [],
      });
      toast.success("Gate created", `"${form.name}" registered.`);
      createOpen = false;
      form = defaultForm();
      await fetchData();
    } catch (error) {
      const msg = error instanceof ApiError ? (Object.values(error.fieldErrors)[0]?.[0] ?? "Save failed.") : "Save failed.";
      toast.error("Save failed", msg);
    } finally { saving = false; }
  }

  function fmtDate(v: string | null | undefined): string { if (!v) return "--"; const d = new Date(v); return Number.isNaN(d.getTime()) ? "--" : d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }); }

  function gateIcon(status: string): { icon: string; color: string } {
    if (status === "open") return { icon: "checkmark", color: "text-emerald-500" };
    if (status === "conditional") return { icon: "checkmark", color: "text-amber-500" };
    if (status === "under_review") return { icon: "clock", color: "text-blue-500" };
    if (status === "failed") return { icon: "x", color: "text-red-500" };
    return { icon: "lock", color: "text-neutral-400" };
  }

  function gateBarColor(status: string): string {
    if (status === "open") return "bg-emerald-500";
    if (status === "conditional") return "bg-amber-500";
    if (status === "under_review") return "bg-blue-500";
    if (status === "failed") return "bg-red-500";
    return "bg-neutral-200";
  }

  useAutoRefresh("StageGate", fetchData);
</script>

<div class="space-y-6">
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">Projects</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-900">Milestones & Stage Gates</h1>
      <p class="mt-1 text-sm text-neutral-500">Formal gatekeeping — prerequisites, approvals, and compliance enforcement.</p>
    </div>
    <div class="flex items-center gap-2">
      <select bind:value={projectFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
        <option value="">All Projects</option>
        {#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}
      </select>
      <button onclick={() => { form = defaultForm(); createOpen = true; }} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800">+ Add Gate</button>
    </div>
  </div>

  <!-- Summary KPIs -->
  {#if summary}
    <div class="grid grid-cols-2 gap-3 md:grid-cols-5">
      <div class="rounded-xl border border-neutral-200 bg-white p-3.5 text-center">
        <p class="text-[9px] font-semibold uppercase tracking-wider text-neutral-500">Total Gates</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{summary.total}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-3.5 text-center">
        <p class="text-[9px] font-semibold uppercase tracking-wider text-neutral-500">Locked</p>
        <p class="mt-1 text-xl font-bold text-neutral-700 tabular-nums">{summary.locked}</p>
      </div>
      <div class="rounded-xl border border-blue-100 bg-blue-50 p-3.5 text-center">
        <p class="text-[9px] font-semibold uppercase tracking-wider text-blue-700">Under Review</p>
        <p class="mt-1 text-xl font-bold text-blue-900 tabular-nums">{summary.under_review}</p>
      </div>
      <div class="rounded-xl border border-emerald-100 bg-emerald-50 p-3.5 text-center">
        <p class="text-[9px] font-semibold uppercase tracking-wider text-emerald-700">Passed</p>
        <p class="mt-1 text-xl font-bold text-emerald-900 tabular-nums">{summary.passed}</p>
      </div>
      <div class="rounded-xl border border-red-100 bg-red-50 p-3.5 text-center">
        <p class="text-[9px] font-semibold uppercase tracking-wider text-red-700">Overdue</p>
        <p class="mt-1 text-xl font-bold text-red-900 tabular-nums">{summary.overdue}</p>
      </div>
    </div>
  {/if}

  {#if loading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if gates.length === 0}
    <div class="rounded-2xl border border-neutral-200 bg-white px-6 py-14 text-center"><p class="text-sm text-neutral-500">No stage gates defined.</p></div>
  {:else}
    <!-- Gate Progress Flow -->
    <section class="rounded-2xl border border-neutral-200 bg-white p-5 overflow-x-auto">
      <h2 class="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-4">Gate Progress</h2>
      <div class="flex items-center gap-0 min-w-[500px]">
        {#each gates as gate, idx}
          {@const gi = gateIcon(gate.status)}
          <div class="flex items-center {idx < gates.length - 1 ? 'flex-1' : ''}">
            <!-- Gate node -->
            <button class="flex flex-col items-center gap-1.5 cursor-pointer group" onclick={() => openDetail(gate.id)}>
              <div class="h-10 w-10 rounded-full border-2 flex items-center justify-center transition-all group-hover:scale-110 {gate.status === 'open' || gate.status === 'conditional' ? 'border-emerald-500 bg-emerald-50' : gate.status === 'under_review' ? 'border-blue-500 bg-blue-50' : gate.status === 'failed' ? 'border-red-500 bg-red-50' : 'border-neutral-300 bg-neutral-50'}">
                {#if gi.icon === "checkmark"}
                  <svg class="h-5 w-5 {gi.color}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" /></svg>
                {:else if gi.icon === "clock"}
                  <svg class="h-5 w-5 {gi.color}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>
                {:else if gi.icon === "x"}
                  <svg class="h-5 w-5 {gi.color}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
                {:else}
                  <svg class="h-4 w-4 {gi.color}" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 1a4.5 4.5 0 0 0-4.5 4.5V9H5a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6a2 2 0 0 0-2-2h-.5V5.5A4.5 4.5 0 0 0 10 1Zm3 8V5.5a3 3 0 1 0-6 0V9h6Z" clip-rule="evenodd" /></svg>
                {/if}
              </div>
              <p class="text-[10px] font-semibold text-neutral-700 text-center max-w-[100px] leading-tight">{gate.name}</p>
              {#if gate.is_overdue}<p class="text-[9px] font-bold text-red-600">OVERDUE</p>{/if}
            </button>
            <!-- Connector line -->
            {#if idx < gates.length - 1}
              <div class="flex-1 h-0.5 mx-2 {gateBarColor(gate.status)}"></div>
            {/if}
          </div>
        {/each}
      </div>
    </section>

    <!-- Gates Table -->
    <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
      <div class="overflow-x-auto">
        <table class="min-w-[800px] w-full">
          <thead class="bg-neutral-50 border-b border-neutral-200">
            <tr>
              <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Gate</th>
              <th class="px-4 py-3 text-center text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Status</th>
              <th class="px-4 py-3 text-center text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Prerequisites</th>
              <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Scheduled</th>
              <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Decision</th>
              <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Decided By</th>
              <th class="px-4 py-3 text-center text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Delay</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each gates as gate}
              <tr class="hover:bg-neutral-50 cursor-pointer {gate.is_overdue ? 'bg-red-50/30' : ''}" onclick={() => openDetail(gate.id)}>
                <td class="px-4 py-3">
                  <p class="text-sm font-medium text-neutral-900">{gate.name}</p>
                  <div class="flex items-center gap-1.5 mt-0.5">
                    {#if gate.gate_type && gate.gate_type !== "custom"}<span class="text-[9px] font-medium text-neutral-400">{gate.gate_type_display}</span>{/if}
                    {#if gate.financial_release_triggered}<span class="text-[9px] font-semibold text-indigo-600 bg-indigo-50 rounded px-1 py-0.5">Financial Release</span>{/if}
                  </div>
                </td>
                <td class="px-4 py-3 text-center"><StatusBadge status={gate.status} /></td>
                <td class="px-4 py-3 text-center">
                  <span class="text-sm font-semibold {gate.prerequisites_met ? 'text-emerald-600' : 'text-amber-600'}">
                    {gate.prerequisites_met ? "Met" : "Pending"}
                  </span>
                  <span class="text-[10px] text-neutral-400 ml-1">({gate.prerequisite_count})</span>
                </td>
                <td class="px-4 py-3 text-sm text-neutral-600">{fmtDate(gate.scheduled_review_date)}</td>
                <td class="px-4 py-3 text-sm text-neutral-700 font-medium">{fmtDate(gate.decision_date)}</td>
                <td class="px-4 py-3 text-sm text-neutral-600 max-w-[120px] truncate">{gate.decided_by || "--"}</td>
                <td class="px-4 py-3 text-center text-sm font-semibold tabular-nums {gate.delay_days > 0 ? 'text-red-600' : 'text-neutral-400'}">
                  {gate.delay_days > 0 ? `${gate.delay_days}d` : "--"}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>

    <!-- Upcoming Gates -->
    {#if summary && summary.upcoming.length > 0}
      <section class="rounded-2xl border border-neutral-200 bg-white p-5">
        <h2 class="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-3">Upcoming Gates (Next 90 Days)</h2>
        <div class="space-y-2">
          {#each summary.upcoming as u}
            <div class="flex items-center justify-between rounded-lg border border-neutral-100 p-3">
              <p class="text-sm font-medium text-neutral-900">{u.name}</p>
              <div class="flex items-center gap-3">
                <StatusBadge status={u.status} />
                <span class="text-xs text-neutral-500">{fmtDate(u.scheduled_review_date)}</span>
              </div>
            </div>
          {/each}
        </div>
      </section>
    {/if}
  {/if}
</div>

<!-- ═══════════ DETAIL DRAWER ═══════════ -->
<DrawerShell open={detailOpen} title="Stage Gate" subtitle={detail?.name ?? ""} width="max-w-2xl" onclose={() => (detailOpen = false)}>
  {#if detailLoading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if detail}
    <div class="p-6 space-y-5">
      <div class="flex items-center gap-3">
        <StatusBadge status={detail.status} />
        {#if detail.is_overdue}<span class="text-xs font-bold text-red-600">OVERDUE</span>{/if}
        {#if detail.prerequisites_met}<span class="text-xs font-semibold text-emerald-600">Prerequisites Met</span>{:else}<span class="text-xs font-semibold text-amber-600">Prerequisites Pending</span>{/if}
      </div>

      {#if detail.description}<p class="text-sm text-neutral-700">{detail.description}</p>{/if}

      <!-- Dates -->
      <div class="grid grid-cols-2 gap-3 md:grid-cols-4">
        <div class="rounded-lg border border-neutral-200 p-3">
          <p class="text-[9px] font-semibold uppercase text-neutral-400">Baseline</p>
          <p class="mt-1 text-sm font-medium text-neutral-900">{fmtDate(detail.baseline_date)}</p>
        </div>
        <div class="rounded-lg border border-neutral-200 p-3">
          <p class="text-[9px] font-semibold uppercase text-neutral-400">Scheduled Review</p>
          <p class="mt-1 text-sm font-medium {detail.is_overdue ? 'text-red-600' : 'text-neutral-900'}">{fmtDate(detail.scheduled_review_date)}</p>
        </div>
        <div class="rounded-lg border border-neutral-200 p-3">
          <p class="text-[9px] font-semibold uppercase text-neutral-400">Actual Review</p>
          <p class="mt-1 text-sm font-medium text-neutral-900">{fmtDate(detail.actual_review_date)}</p>
        </div>
        <div class="rounded-lg border border-neutral-200 p-3">
          <p class="text-[9px] font-semibold uppercase text-neutral-400">Decision Date</p>
          <p class="mt-1 text-sm font-bold text-neutral-900">{fmtDate(detail.decision_date)}</p>
        </div>
      </div>

      <!-- Decision Info -->
      <div class="grid grid-cols-2 gap-3 text-sm">
        <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Decided By</p><p class="text-neutral-900">{detail.decided_by || "--"}</p></div>
        <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Delay</p><p class="{detail.delay_days > 0 ? 'text-red-600 font-semibold' : 'text-neutral-400'}">{detail.delay_days > 0 ? `${detail.delay_days} days` : "None"}</p></div>
      </div>

      {#if detail.conditions}
        <div class="rounded-lg border border-amber-200 bg-amber-50 p-3">
          <p class="text-[10px] font-semibold uppercase text-amber-700 mb-1">Conditions</p>
          <p class="text-sm text-amber-900 whitespace-pre-line">{detail.conditions}</p>
        </div>
      {/if}

      {#if detail.rejection_reason}
        <div class="rounded-lg border border-red-200 bg-red-50 p-3">
          <p class="text-[10px] font-semibold uppercase text-red-700 mb-1">Rejection Reason</p>
          <p class="text-sm text-red-900 whitespace-pre-line">{detail.rejection_reason}</p>
        </div>
      {/if}

      <!-- Prerequisites -->
      <div>
        <p class="text-[10px] font-semibold uppercase text-neutral-400 mb-2">Prerequisite Milestones ({detail.prerequisite_milestones_detail.length})</p>
        {#if detail.prerequisite_milestones_detail.length === 0}
          <p class="text-sm text-neutral-400 py-2">No prerequisites defined.</p>
        {:else}
          <div class="space-y-1.5">
            {#each detail.prerequisite_milestones_detail as ms}
              <div class="flex items-center gap-3 rounded-lg border border-neutral-100 p-2.5">
                {#if ms.is_completed}
                  <svg class="h-5 w-5 text-emerald-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>
                {:else}
                  <span class="h-5 w-5 rounded-full border-2 border-neutral-300 shrink-0"></span>
                {/if}
                <div class="flex-1">
                  <p class="text-sm font-medium text-neutral-900">{ms.name}</p>
                  <p class="text-[10px] text-neutral-400">{ms.reference_code ? `${ms.reference_code} — ` : ""}Target: {fmtDate(ms.target_date)}{ms.completed_date ? ` — Completed: ${fmtDate(ms.completed_date)}` : ""}</p>
                </div>
              </div>
            {/each}
          </div>
        {/if}
        {#if detail.prerequisite_notes}
          <p class="text-xs text-neutral-500 mt-2">{detail.prerequisite_notes}</p>
        {/if}
      </div>

      <!-- Variance & Recovery -->
      {#if detail.delay_root_cause}
        <div><p class="text-[10px] font-semibold uppercase text-neutral-400 mb-1">Delay Root Cause</p><p class="text-sm text-neutral-700 whitespace-pre-line">{detail.delay_root_cause}</p></div>
      {/if}
      {#if detail.recovery_plan}
        <div><p class="text-[10px] font-semibold uppercase text-neutral-400 mb-1">Recovery Plan</p><p class="text-sm text-neutral-700 whitespace-pre-line">{detail.recovery_plan}</p></div>
      {/if}

      <!-- Financial Release -->
      {#if detail.financial_release_triggered}
        <div class="rounded-lg border border-indigo-200 bg-indigo-50 p-3">
          <p class="text-[10px] font-semibold uppercase text-indigo-700 mb-1">Financial Release Triggered</p>
          <p class="text-sm text-indigo-900">{detail.financial_release_notes || "Next financing tranche released upon passing this gate."}</p>
        </div>
      {/if}

      {#if detail.notes}<div><p class="text-[10px] font-semibold uppercase text-neutral-400 mb-1">Notes</p><p class="text-sm text-neutral-700 whitespace-pre-line">{detail.notes}</p></div>{/if}
    </div>
  {/if}
</DrawerShell>

<!-- ═══════════ CREATE DRAWER ═══════════ -->
<DrawerShell open={createOpen} title="Add Stage Gate" subtitle="Define a formal project gate" width="max-w-md" onclose={() => (createOpen = false)}>
  <form onsubmit={saveGate} class="p-6 space-y-4">
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Project *</span><select bind:value={form.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"><option value="">Select</option>{#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}</select></label>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Gate Type</span>
      <select bind:value={form.gate_type} onchange={onGateTypeChange} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        {#each GATE_TYPE_OPTIONS as opt}<option value={opt.value}>{opt.label}</option>{/each}
      </select>
    </label>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Gate Name *</span><input bind:value={form.name} placeholder="e.g. Pre-Construction Gate" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Description</span><textarea bind:value={form.description} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Status</span><select bind:value={form.status} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="locked">Locked</option><option value="under_review">Under Review</option><option value="open">Open (Passed)</option><option value="conditional">Conditional</option><option value="failed">Failed</option>
      </select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Sort Order</span><input type="number" bind:value={form.sort_order} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Scheduled Review</span><input type="date" bind:value={form.scheduled_review_date} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Baseline Date</span><input type="date" bind:value={form.baseline_date} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Decided By</span><input bind:value={form.decided_by} placeholder="e.g. Investment Committee" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Notes</span><textarea bind:value={form.notes} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <div class="flex justify-end gap-2 pt-2">
      <button type="button" onclick={() => (createOpen = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      {#if isDev}<button type="button" onclick={devFill} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
      <button type="submit" disabled={saving} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{saving ? "Saving..." : "Create Gate"}</button>
    </div>
  </form>
</DrawerShell>

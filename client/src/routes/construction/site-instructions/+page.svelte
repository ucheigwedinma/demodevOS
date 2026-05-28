<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { useAutoRefresh } from "$lib/realtime.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DrawerShell from "$lib/components/DrawerShell.svelte";
  import DateInput from "$lib/components/DateInput.svelte";
  import type {
    SiteInstructionListItem,
    SiteInstructionDetail,
    SIInstructionType,
    SIPriority,
    SIStatus,
    SISummary,
    PaginatedResponse,
    ProjectListItem,
  } from "$lib/types";

  // ── State ─────────────────────────────────────────────────────────────
  let rows = $state<SiteInstructionListItem[]>([]);
  let loading = $state(true);
  let totalCount = $state(0);
  let currentPage = $state(1);
  let searchInput = $state("");
  let searchQuery = $state("");
  let typeFilter = $state("");
  let priorityFilter = $state("");
  let statusFilter = $state("");
  let searchTimeout: ReturnType<typeof setTimeout> | undefined;
  let summary = $state<SISummary | null>(null);
  const pageSize = 15;

  // Detail drawer
  let detailOpen = $state(false);
  let detail = $state<SiteInstructionDetail | null>(null);
  let detailLoading = $state(false);

  // Create drawer
  let createOpen = $state(false);
  let saving = $state(false);
  let form = $state(defaultForm());

  let projects = $state<ProjectListItem[]>([]);
  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  function defaultForm() {
    return {
      project: "",
      title: "",
      description: "",
      instruction_type: "technical" as SIInstructionType,
      priority: "normal" as SIPriority,
      status: "draft" as SIStatus,
      location: "",
      cost_code: "",
      has_financial_impact: false,
      estimated_cost_impact: "",
      schedule_impact_days: "0",
      issued_by: "",
      issued_date: new Date().toISOString().slice(0, 10),
      compliance_deadline: "",
      notes: "",
    };
  }

  // ── Dev Fill ──────────────────────────────────────────────────────────
  let devIdx = 0;
  const SAMPLES = [
    {
      title: "Relocate Roofing Group B to North Wall",
      description: "Due to revised structural loading analysis (ref: STR-REV-042), the roofing membrane attachment points for Group B must be shifted 450mm north of the original position shown on DWG-R-015 Rev A.\n\nThe contractor shall:\n1. Remove existing anchor bolts at Grid Lines G4-G8 (north side)\n2. Re-drill anchor points at revised coordinates per markup DWG-R-015 Rev B\n3. Apply waterproof sealant to all vacated anchor holes\n4. Complete relocation before waterproofing membrane installation\n5. Submit photo evidence of completed relocation for QC sign-off",
      instruction_type: "design_change" as SIInstructionType,
      priority: "high" as SIPriority,
      location: "Block A, Roof Level, Grid Lines G4-G8",
      cost_code: "5.3.2 — Roofing Works",
      has_financial_impact: true,
      estimated_cost_impact: "420000",
      schedule_impact_days: "2",
      issued_by: "Engr. Adewale Okonkwo — Lead Structural Engineer",
      compliance_deadline: "2026-04-02",
      notes: "This instruction supersedes verbal instruction given on 24 Mar. Formal variation to be raised if cost exceeds ₦500,000.",
    },
    {
      title: "Immediate cessation of concrete pour — Column D12",
      description: "Concrete pour at Column D12 (Level 4) must be stopped immediately. QC inspection has identified that the rebar cage does not match the approved reinforcement schedule REI-L4-D12 Rev C.\n\nSpecifically:\n- Longitudinal bars: 6×Y25 installed vs 8×Y32 specified\n- Stirrup spacing: 200mm installed vs 150mm specified at column head\n\nThe contractor shall:\n1. STOP all concrete placement at D12 immediately\n2. Remove any concrete already placed in the last 2 hours (if not set)\n3. Strip formwork and expose rebar cage for re-inspection\n4. Correct reinforcement to match REI-L4-D12 Rev C\n5. Request re-inspection before any further concrete work at D12",
      instruction_type: "urgent_corrective" as SIInstructionType,
      priority: "urgent" as SIPriority,
      location: "Block B, Level 4, Column D12",
      cost_code: "3.1.4 — Reinforced Concrete",
      has_financial_impact: true,
      estimated_cost_impact: "850000",
      schedule_impact_days: "4",
      issued_by: "Engr. Funke Adeyemi — Project Manager",
      compliance_deadline: "2026-03-25",
      notes: "Safety critical — incorrect reinforcement poses structural risk. NCR to be raised against concrete subcontractor. All similar columns (D10-D14) to be audited.",
    },
    {
      title: "Install temporary dewatering at Basement B2 excavation",
      description: "Groundwater ingress at Basement B2 excavation face (south wall) is exceeding 50 litres/minute. This exceeds the tolerance for safe working conditions and threatens foundation preparation quality.\n\nThe contractor shall:\n1. Mobilise submersible pump (min 100 L/min capacity) to south sump pit\n2. Install perforated drainage pipe along south wall base (15m length)\n3. Direct discharge to designated settlement tank at ground level\n4. Monitor water levels every 4 hours and log readings\n5. Maintain dewatering until lean concrete blinding is complete",
      instruction_type: "technical" as SIInstructionType,
      priority: "high" as SIPriority,
      location: "Basement B2, South Excavation Face",
      cost_code: "2.1.3 — Earthworks & Dewatering",
      has_financial_impact: true,
      estimated_cost_impact: "275000",
      schedule_impact_days: "1",
      issued_by: "Engr. Chidi Nwosu — Site Engineer",
      compliance_deadline: "2026-03-26",
      notes: "Pump hire cost to be borne by main contractor per clause 14.3 of subcontract. If groundwater persists beyond 7 days, geotechnical consultant to be engaged.",
    },
  ];

  function devFill() {
    const s = SAMPLES[devIdx % SAMPLES.length];
    devIdx++;
    form = {
      ...defaultForm(),
      project: form.project || (projects.length > 0 ? String(projects[0].id) : ""),
      title: s.title,
      description: s.description,
      instruction_type: s.instruction_type,
      priority: s.priority,
      location: s.location,
      cost_code: s.cost_code,
      has_financial_impact: s.has_financial_impact,
      estimated_cost_impact: s.estimated_cost_impact,
      schedule_impact_days: s.schedule_impact_days,
      issued_by: s.issued_by,
      compliance_deadline: s.compliance_deadline,
      notes: s.notes,
    };
  }

  // ── Data Fetching ─────────────────────────────────────────────────────

  async function fetchSIs() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (searchQuery) params.search = searchQuery;
      if (typeFilter) params.instruction_type = typeFilter;
      if (priorityFilter) params.priority = priorityFilter;
      if (statusFilter) params.status = statusFilter;
      const [res, sum] = await Promise.all([
        api.get<PaginatedResponse<SiteInstructionListItem>>("/projects/site-instructions/", params),
        summary ? Promise.resolve(summary) : api.get<SISummary>("/projects/site-instructions/summary/"),
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
    void searchQuery; void typeFilter; void priorityFilter; void statusFilter; void currentPage;
    fetchSIs();
    fetchProjects();
  });

  function onSearch(e: Event) {
    searchInput = (e.target as HTMLInputElement).value;
    if (searchTimeout) clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => { searchQuery = searchInput.trim(); currentPage = 1; }, 250);
  }

  async function openDetail(id: number) {
    detailOpen = true;
    detailLoading = true;
    try { detail = await api.get<SiteInstructionDetail>(`/projects/site-instructions/${id}/`); } catch { detail = null; }
    detailLoading = false;
  }

  async function saveSI(e: Event) {
    e.preventDefault();
    if (!form.title.trim() || !form.project) { toast.error("Validation", "Title and project are required."); return; }
    saving = true;
    try {
      await api.post("/projects/site-instructions/", {
        ...form,
        project: Number(form.project),
        estimated_cost_impact: form.estimated_cost_impact || "0",
        schedule_impact_days: Number(form.schedule_impact_days) || 0,
        issued_date: form.issued_date || null,
        compliance_deadline: form.compliance_deadline || null,
      });
      toast.success("Site Instruction issued", `"${form.title}" has been created.`);
      createOpen = false;
      form = defaultForm();
      summary = null;
      await fetchSIs();
    } catch (error) {
      const msg = error instanceof ApiError ? (Object.values(error.fieldErrors)[0]?.[0] ?? "Save failed.") : "Save failed.";
      toast.error("Save failed", msg);
    } finally { saving = false; }
  }

  // ── Helpers ───────────────────────────────────────────────────────────
  function fmtDate(v: string | null | undefined): string { if (!v) return "--"; const d = new Date(v); return Number.isNaN(d.getTime()) ? "--" : d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }); }
  function fmtCurrency(v: string | number | null | undefined): string { if (!v || v === "0.00") return "--"; return currency.format(v); }
  const totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  const startRow = $derived(totalCount === 0 ? 0 : (currentPage - 1) * pageSize + 1);
  const endRow = $derived(Math.min(currentPage * pageSize, totalCount));

  function priorityColor(p: string): string {
    switch (p) {
      case "urgent": return "bg-red-100 text-red-800 border-red-200";
      case "high": return "bg-amber-100 text-amber-800 border-amber-200";
      case "normal": return "bg-neutral-100 text-neutral-600 border-neutral-200";
      case "low": return "bg-blue-100 text-blue-700 border-blue-200";
      default: return "bg-neutral-100 text-neutral-600 border-neutral-200";
    }
  }

  // Audit trail steps
  function auditSteps(si: SiteInstructionDetail): { label: string; date: string | null; done: boolean }[] {
    return [
      { label: "Drafted", date: si.created_at, done: true },
      { label: "Issued", date: si.issued_date, done: !!si.issued_date },
      { label: "Acknowledged", date: si.acknowledged_date ? si.acknowledged_date.slice(0, 10) : null, done: !!si.acknowledged_date },
      { label: "Completed", date: si.completed_date, done: !!si.completed_date },
      { label: "Verified", date: si.verified_date, done: !!si.verified_date },
    ];
  }

  useAutoRefresh("SiteInstruction", fetchSIs);
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">Construction</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-900">Site Instructions</h1>
      <p class="mt-1 text-sm text-neutral-500">Authoritative directives from design to site — legally binding, tracked to completion.</p>
    </div>
    <button onclick={() => { form = defaultForm(); createOpen = true; }} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800">+ Issue Instruction</button>
  </div>

  <!-- Summary KPIs -->
  {#if summary}
    <div class="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
      <div class="rounded-xl border border-neutral-200 bg-white p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Total SIs</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{summary.total}</p>
      </div>
      <div class="rounded-xl border border-blue-100 bg-blue-50 p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-blue-700">Open</p>
        <p class="mt-1 text-xl font-bold text-blue-900 tabular-nums">{summary.open}</p>
      </div>
      <div class="rounded-xl border border-amber-100 bg-amber-50 p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-amber-700">Pending Signature</p>
        <p class="mt-1 text-xl font-bold text-amber-900 tabular-nums">{summary.pending_acknowledgement}</p>
      </div>
      <div class="rounded-xl border border-red-100 bg-red-50 p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-red-700">Overdue</p>
        <p class="mt-1 text-xl font-bold text-red-900 tabular-nums">{summary.overdue}</p>
      </div>
      <div class="rounded-xl border border-rose-100 bg-rose-50 p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-rose-700">Financial Impact</p>
        <p class="mt-1 text-xl font-bold text-rose-900 tabular-nums">{summary.with_financial_impact}</p>
      </div>
      <div class="rounded-xl border border-emerald-100 bg-emerald-50 p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-emerald-700">Completed</p>
        <p class="mt-1 text-xl font-bold text-emerald-900 tabular-nums">{summary.completed}</p>
      </div>
    </div>
  {/if}

  <!-- Filters + Table -->
  <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
    <div class="border-b border-neutral-200 bg-linear-to-r from-neutral-50 via-white to-neutral-50 p-4">
      <div class="grid grid-cols-1 gap-3 xl:grid-cols-5">
        <input type="text" value={searchInput} oninput={onSearch} placeholder="Search SI number, title, issued by..." class="xl:col-span-2 rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        <select bind:value={typeFilter} onchange={() => (currentPage = 1)} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
          <option value="">All Types</option>
          <option value="safety">Safety</option>
          <option value="quality">Quality</option>
          <option value="variation">Variation</option>
          <option value="urgent_corrective">Urgent Corrective</option>
          <option value="technical">Technical</option>
          <option value="design_change">Design Change</option>
          <option value="other">Other</option>
        </select>
        <select bind:value={priorityFilter} onchange={() => (currentPage = 1)} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
          <option value="">All Priorities</option>
          <option value="urgent">Urgent</option>
          <option value="high">High</option>
          <option value="normal">Normal</option>
          <option value="low">Low</option>
        </select>
        <select bind:value={statusFilter} onchange={() => (currentPage = 1)} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="issued">Issued</option>
          <option value="acknowledged">Acknowledged</option>
          <option value="in_progress">In Progress</option>
          <option value="completed">Completed</option>
          <option value="verified">Verified</option>
          <option value="closed">Closed</option>
        </select>
      </div>
    </div>

    {#if loading}
      <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
    {:else if rows.length === 0}
      <div class="px-6 py-14 text-center"><p class="text-sm text-neutral-500">No site instructions match the current filters.</p></div>
    {:else}
      <div class="overflow-x-auto">
        <table class="min-w-[1050px] w-full">
          <thead class="border-b border-neutral-200 bg-neutral-50">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">SI #</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Title</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Type</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Priority</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Status</th>
              <th class="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-neutral-500">Cost Impact</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Issued By</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Deadline</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each rows as si}
              <tr class="hover:bg-neutral-50 cursor-pointer" onclick={() => openDetail(si.id)}>
                <td class="px-4 py-3 text-sm font-semibold text-neutral-900">{si.si_number}</td>
                <td class="px-4 py-3 text-sm text-neutral-900 max-w-[240px] truncate">{si.title}</td>
                <td class="px-4 py-3 text-xs font-medium text-neutral-600">{si.instruction_type_display}</td>
                <td class="px-4 py-3"><span class="inline-block rounded-full border px-2 py-0.5 text-[10px] font-semibold {priorityColor(si.priority)}">{si.priority_display}</span></td>
                <td class="px-4 py-3"><StatusBadge status={si.status} /></td>
                <td class="px-4 py-3 text-center">
                  {#if si.has_financial_impact}
                    <span class="text-xs font-semibold text-rose-600">{fmtCurrency(si.estimated_cost_impact)}</span>
                  {:else}
                    <span class="text-xs text-neutral-400">--</span>
                  {/if}
                </td>
                <td class="px-4 py-3 text-sm text-neutral-600 max-w-[150px] truncate">{si.issued_by || "--"}</td>
                <td class="px-4 py-3 text-sm text-neutral-500">{fmtDate(si.compliance_deadline)}</td>
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

<!-- ═══════════ SI DETAIL DRAWER ═══════════ -->
<DrawerShell open={detailOpen} title={detail?.si_number ?? "SI"} subtitle={detail?.title ?? ""} width="max-w-2xl" onclose={() => (detailOpen = false)}>
  {#if detailLoading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if detail}
    <div class="p-6 space-y-5">
      <!-- Priority + Status bar -->
      <div class="flex items-center justify-between rounded-lg border p-3 {detail.priority === 'urgent' ? 'bg-red-50 border-red-200' : detail.priority === 'high' ? 'bg-amber-50 border-amber-200' : 'bg-neutral-50 border-neutral-200'}">
        <span class="inline-block rounded-full border px-2.5 py-0.5 text-[10px] font-semibold {priorityColor(detail.priority)}">{detail.priority_display}</span>
        <div class="flex items-center gap-2">
          <span class="text-xs font-medium text-neutral-600">{detail.instruction_type_display}</span>
          <StatusBadge status={detail.status} />
        </div>
      </div>

      <!-- Audit Trail Timeline -->
      <div class="flex items-center gap-1 overflow-x-auto py-2">
        {#each auditSteps(detail) as step, idx}
          <div class="flex items-center gap-1 shrink-0">
            <div class="flex flex-col items-center">
              <div class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold {step.done ? 'bg-emerald-500 text-white' : 'bg-neutral-200 text-neutral-400'}">{idx + 1}</div>
              <p class="text-[9px] font-medium mt-1 {step.done ? 'text-neutral-900' : 'text-neutral-400'}">{step.label}</p>
              {#if step.date}<p class="text-[8px] text-neutral-400">{fmtDate(step.date)}</p>{/if}
            </div>
            {#if idx < auditSteps(detail).length - 1}
              <div class="w-8 h-0.5 {step.done ? 'bg-emerald-400' : 'bg-neutral-200'} mt-[-14px]"></div>
            {/if}
          </div>
        {/each}
      </div>

      <!-- Meta grid -->
      <div class="grid grid-cols-2 gap-4">
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Project</p><p class="text-sm text-neutral-900">{detail.project_name}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Location</p><p class="text-sm text-neutral-900">{detail.location || "--"}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Issued By</p><p class="text-sm text-neutral-900">{detail.issued_by || "--"}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Compliance Deadline</p><p class="text-sm text-neutral-900">{fmtDate(detail.compliance_deadline)}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Cost Code</p><p class="text-sm text-neutral-900">{detail.cost_code || "--"}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Acknowledged By</p><p class="text-sm text-neutral-900">{detail.acknowledged_by || "Pending"}</p></div>
      </div>

      <!-- Directive -->
      <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500 mb-2">Directive</p>
        <p class="text-sm text-neutral-800 whitespace-pre-line font-medium">{detail.description || "--"}</p>
      </div>

      <!-- Financial Impact -->
      {#if detail.has_financial_impact}
        <div class="grid grid-cols-2 gap-3">
          <div class="rounded-lg border border-rose-200 bg-rose-50 p-3 text-center">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-rose-700">Estimated Cost Impact</p>
            <p class="text-lg font-bold text-rose-900 tabular-nums mt-1">{fmtCurrency(detail.estimated_cost_impact)}</p>
          </div>
          <div class="rounded-lg border border-amber-200 bg-amber-50 p-3 text-center">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-amber-700">Schedule Impact</p>
            <p class="text-lg font-bold text-amber-900 tabular-nums mt-1">{detail.schedule_impact_days} days</p>
          </div>
        </div>
      {/if}

      <!-- Contractor Response -->
      {#if detail.contractor_remarks || detail.contractor_timeline_impact}
        <div class="rounded-lg border border-blue-200 bg-blue-50/50 p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-blue-700 mb-2">Contractor Response</p>
          {#if detail.contractor_timeline_impact}
            <p class="text-xs font-semibold text-amber-700 mb-1">Timeline impact flagged — Estimated cost: {fmtCurrency(detail.contractor_estimated_cost)}</p>
          {/if}
          {#if detail.contractor_remarks}
            <p class="text-sm text-neutral-700 whitespace-pre-line">{detail.contractor_remarks}</p>
          {/if}
        </div>
      {/if}

      <!-- Linked Variation -->
      {#if detail.linked_variation_number}
        <div class="rounded-lg border border-indigo-200 bg-indigo-50 p-3 flex items-center justify-between">
          <div>
            <p class="text-[10px] font-semibold uppercase tracking-wider text-indigo-700">Linked Variation</p>
            <p class="text-sm font-semibold text-indigo-900 mt-0.5">{detail.linked_variation_number}</p>
          </div>
          <a href="/projects/variations" class="text-xs font-medium text-indigo-600 hover:text-indigo-800">View Variations</a>
        </div>
      {/if}

      {#if detail.notes}<div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Notes</p><p class="text-sm text-neutral-700 whitespace-pre-line">{detail.notes}</p></div>{/if}
    </div>
  {/if}
</DrawerShell>

<!-- ═══════════ SI CREATE DRAWER ═══════════ -->
<DrawerShell open={createOpen} title="Issue Site Instruction" subtitle="Create an authoritative directive to the site team" width="max-w-xl" onclose={() => (createOpen = false)}>
  <form onsubmit={saveSI} class="p-6 space-y-4">
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Title *</span><input bind:value={form.title} placeholder="e.g. Relocate Roofing Group B to North Wall" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Project *</span><select bind:value={form.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"><option value="">Select</option>{#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}</select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Type</span><select bind:value={form.instruction_type} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="safety">Safety</option><option value="quality">Quality</option><option value="variation">Variation</option><option value="urgent_corrective">Urgent Corrective</option><option value="technical">Technical</option><option value="design_change">Design Change</option><option value="other">Other</option>
      </select></label>
    </div>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Priority</span><select bind:value={form.priority} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="urgent">Urgent — Immediate Action</option><option value="high">High</option><option value="normal">Normal</option><option value="low">Low</option>
      </select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Location</span><input bind:value={form.location} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Detailed Directive</span><textarea bind:value={form.description} rows="5" placeholder="Technical steps the contractor must follow..." class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Cost Code</span><input bind:value={form.cost_code} placeholder="e.g. 5.3.2 — Roofing Works" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Issued By</span><input bind:value={form.issued_by} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Issue Date</span><DateInput bind:value={form.issued_date} /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Compliance Deadline</span><DateInput bind:value={form.compliance_deadline} /></label>
    </div>
    <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-3 space-y-3">
      <label class="flex items-center gap-2"><input type="checkbox" bind:checked={form.has_financial_impact} class="rounded" /><span class="text-xs font-semibold text-neutral-600">Has Financial Impact</span></label>
      {#if form.has_financial_impact}
        <div class="grid grid-cols-2 gap-4">
          <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Estimated Cost</span><input type="number" step="0.01" bind:value={form.estimated_cost_impact} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
          <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Schedule Impact (days)</span><input type="number" min="0" bind:value={form.schedule_impact_days} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
        </div>
      {/if}
    </div>
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Notes</span><textarea bind:value={form.notes} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <div class="flex justify-end gap-2 pt-2">
      <button type="button" onclick={() => (createOpen = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      {#if isDev}<button type="button" onclick={devFill} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
      <button type="submit" disabled={saving} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{saving ? "Saving..." : "Issue Instruction"}</button>
    </div>
  </form>
</DrawerShell>

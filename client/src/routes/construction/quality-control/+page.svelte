<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { useAutoRefresh } from "$lib/realtime.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DrawerShell from "$lib/components/DrawerShell.svelte";
  import DateInput from "$lib/components/DateInput.svelte";
  import type {
    QualityPlanListItem,
    QualityPlanDetail,
    QualityCheckTemplate,
    QualityPlanApprovalStatus,
    QualityCheckEvidenceType,
    NCRListItem,
    NCRDetail,
    NCRSeverity,
    NCRRootCause,
    NCRStatus,
    QCDashboard,
    NCRSummary,
    ProjectExecutionInspection,
    ProjectExecutionInspectionSummary,
    PaginatedResponse,
    ProjectListItem,
  } from "$lib/types";

  // ── Tab State ─────────────────────────────────────────────────────────
  type Tab = "dashboard" | "plans" | "inspections" | "ncrs";
  let activeTab = $state<Tab>("dashboard");

  // ── Dashboard ─────────────────────────────────────────────────────────
  let dashboard = $state<QCDashboard | null>(null);
  let dashLoading = $state(true);

  // ── Quality Plans ─────────────────────────────────────────────────────
  let plans = $state<QualityPlanListItem[]>([]);
  let plansLoading = $state(true);
  let plansTotalCount = $state(0);
  let plansPage = $state(1);
  let plansSearch = $state("");
  let plansSearchInput = $state("");
  let plansStatusFilter = $state("");
  let planSearchTimeout: ReturnType<typeof setTimeout> | undefined;

  // Plan Detail Drawer
  let planDetailOpen = $state(false);
  let planDetailId = $state<number | null>(null);
  let planDetail = $state<QualityPlanDetail | null>(null);
  let planDetailLoading = $state(false);

  // Plan Create Drawer
  let planCreateOpen = $state(false);
  let planSaving = $state(false);
  let planForm = $state(defaultPlanForm());
  let checkRows = $state<CheckRow[]>([]);

  // ── Inspections (moved from field ops) ────────────────────────────────
  let inspections = $state<ProjectExecutionInspection[]>([]);
  let inspectionsLoading = $state(true);
  let inspectionsTotalCount = $state(0);
  let inspectionsPage = $state(1);
  let inspectionsSearch = $state("");
  let inspectionsSearchInput = $state("");
  let inspectionsStatusFilter = $state("");
  let inspectionsTypeFilter = $state("");
  let inspectionSearchTimeout: ReturnType<typeof setTimeout> | undefined;
  let inspectionSummary = $state<ProjectExecutionInspectionSummary | null>(null);

  // ── NCRs ──────────────────────────────────────────────────────────────
  let ncrs = $state<NCRListItem[]>([]);
  let ncrsLoading = $state(true);
  let ncrsTotalCount = $state(0);
  let ncrsPage = $state(1);
  let ncrsSearch = $state("");
  let ncrsSearchInput = $state("");
  let ncrsSeverityFilter = $state("");
  let ncrsStatusFilter = $state("");
  let ncrSearchTimeout: ReturnType<typeof setTimeout> | undefined;
  let ncrSummary = $state<NCRSummary | null>(null);

  // NCR Detail Drawer
  let ncrDetailOpen = $state(false);
  let ncrDetailId = $state<number | null>(null);
  let ncrDetail = $state<NCRDetail | null>(null);
  let ncrDetailLoading = $state(false);

  // NCR Create Drawer
  let ncrCreateOpen = $state(false);
  let ncrSaving = $state(false);
  let ncrForm = $state(defaultNCRForm());

  // Shared
  let projects = $state<ProjectListItem[]>([]);
  const pageSize = 15;
  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  // ── Defaults ──────────────────────────────────────────────────────────

  interface CheckRow {
    inspection_point: string;
    requirement_standard: string;
    evidence_type: QualityCheckEvidenceType;
    is_critical: boolean;
  }

  function defaultPlanForm() {
    return {
      name: "",
      description: "",
      project: "",
      compliance_standards: "",
      review_cycle: "quarterly",
      approval_status: "draft" as QualityPlanApprovalStatus,
      approved_by: "",
      approved_date: "",
      next_review_date: "",
      revision: "1",
      notes: "",
    };
  }

  function defaultNCRForm() {
    return {
      project: "",
      inspection: "",
      title: "",
      description: "",
      severity: "minor" as NCRSeverity,
      root_cause: "workmanship" as NCRRootCause,
      status: "open" as NCRStatus,
      location: "",
      raised_by: "",
      assigned_to: "",
      rectification_plan: "",
      rectification_due_date: "",
      cost_impact: "",
      schedule_impact_days: "0",
      notes: "",
    };
  }

  function addCheckRow() {
    checkRows = [...checkRows, { inspection_point: "", requirement_standard: "", evidence_type: "pass_fail", is_critical: false }];
  }

  function removeCheckRow(idx: number) {
    checkRows = checkRows.filter((_, i) => i !== idx);
  }

  // ── Dev Fill ──────────────────────────────────────────────────────────
  let planDevIdx = 0;
  const PLAN_SAMPLES = [
    {
      name: "Residential Tower QC Plan",
      description: "Comprehensive quality control plan covering structural, MEP, and finishes for high-rise residential construction.",
      compliance_standards: "NIS 87:2000 (Nigerian Structural Concrete Code), ISO 9001:2015, BS EN 1992 (Eurocode 2)",
      review_cycle: "quarterly",
      approval_status: "draft" as QualityPlanApprovalStatus,
      approved_by: "Engr. Adewale Okonkwo",
      approved_date: "",
      next_review_date: "2026-06-30",
      revision: "1",
      notes: "First revision — aligned with updated NIS standards for 2026.",
      checks: [
        { inspection_point: "Structural Concrete Strength", requirement_standard: "Minimum 25 N/mm² at 28 days per NIS 87:2000", evidence_type: "numerical" as QualityCheckEvidenceType, is_critical: true },
        { inspection_point: "Rebar Cover & Spacing", requirement_standard: "Min 40mm cover, max 150mm spacing per BS EN 1992", evidence_type: "photo" as QualityCheckEvidenceType, is_critical: true },
        { inspection_point: "Formwork Alignment", requirement_standard: "Plumb within ±5mm per 3m height", evidence_type: "numerical" as QualityCheckEvidenceType, is_critical: false },
        { inspection_point: "MEP Conduit Routing", requirement_standard: "No clashes with structural members, min 25mm from rebar", evidence_type: "pass_fail" as QualityCheckEvidenceType, is_critical: false },
        { inspection_point: "Waterproofing Membrane", requirement_standard: "Full coverage, min 150mm overlap at joints", evidence_type: "photo" as QualityCheckEvidenceType, is_critical: true },
      ],
    },
    {
      name: "Commercial Office Complex QC Plan",
      description: "Quality assurance framework for Grade A office buildings covering curtain wall systems, HVAC, and fire safety compliance.",
      compliance_standards: "ISO 9001:2015, ASHRAE 90.1, Nigerian Fire Safety Code, BS 8110",
      review_cycle: "monthly",
      approval_status: "draft" as QualityPlanApprovalStatus,
      approved_by: "Engr. Funke Adeyemi",
      approved_date: "",
      next_review_date: "2026-04-30",
      revision: "1",
      notes: "Requires sign-off from Fire Safety consultant before activation.",
      checks: [
        { inspection_point: "Curtain Wall Seal Integrity", requirement_standard: "No air/water leakage under 600Pa pressure test", evidence_type: "document" as QualityCheckEvidenceType, is_critical: true },
        { inspection_point: "Fire Stopping at Floor Edges", requirement_standard: "2-hour rated fire stop at every slab/curtain wall junction", evidence_type: "photo" as QualityCheckEvidenceType, is_critical: true },
        { inspection_point: "HVAC Ductwork Insulation", requirement_standard: "R-value ≥ 6 per ASHRAE 90.1", evidence_type: "numerical" as QualityCheckEvidenceType, is_critical: false },
        { inspection_point: "Elevator Shaft Alignment", requirement_standard: "Plumb within ±10mm full height", evidence_type: "numerical" as QualityCheckEvidenceType, is_critical: true },
      ],
    },
  ];

  function devFillPlan() {
    const sample = PLAN_SAMPLES[planDevIdx % PLAN_SAMPLES.length];
    planDevIdx++;
    planForm = {
      name: sample.name,
      description: sample.description,
      project: planForm.project || (projects.length > 0 ? String(projects[0].id) : ""),
      compliance_standards: sample.compliance_standards,
      review_cycle: sample.review_cycle,
      approval_status: sample.approval_status,
      approved_by: sample.approved_by,
      approved_date: sample.approved_date,
      next_review_date: sample.next_review_date,
      revision: sample.revision,
      notes: sample.notes,
    };
    checkRows = sample.checks.map((c) => ({ ...c }));
  }

  let ncrDevIdx = 0;
  const NCR_SAMPLES = [
    {
      title: "Exposed rebar at Column C7 — Level 3",
      description: "During routine inspection, exposed reinforcement bar was found protruding from column C7 at Level 3. Concrete cover is less than 15mm (required: 40mm minimum). Risk of corrosion and structural compromise.",
      severity: "critical" as NCRSeverity,
      root_cause: "workmanship" as NCRRootCause,
      location: "Block A, Level 3, Column C7",
      raised_by: "Engr. Chidi Nwosu",
      assigned_to: "Foreman Ibrahim Musa",
      rectification_plan: "1. Chip away loose concrete around exposed area\n2. Apply anti-rust treatment to rebar\n3. Install corrective formwork\n4. Pour repair mortar (min 40mm cover)\n5. Cure for 7 days before removing formwork",
      rectification_due_date: "2026-04-05",
      cost_impact: "185000",
      schedule_impact_days: "3",
      notes: "Photographic evidence attached. Similar issue noted at C9 — monitor closely.",
    },
    {
      title: "Waterproofing membrane overlap below standard",
      description: "Waterproofing membrane at basement level B2 shows overlap of only 80mm at several joints. Specification requires minimum 150mm overlap. Discovered during pre-pour inspection.",
      severity: "major" as NCRSeverity,
      root_cause: "workmanship" as NCRRootCause,
      location: "Basement B2, North Wall",
      raised_by: "QC Inspector Aisha Bello",
      assigned_to: "Subcontractor: WaterSeal Nigeria Ltd",
      rectification_plan: "1. Mark all non-compliant joints\n2. Peel back membrane edges\n3. Apply primer and re-lay with 150mm minimum overlap\n4. Conduct water ponding test (48 hours)\n5. Document with photos before backfill",
      rectification_due_date: "2026-04-10",
      cost_impact: "95000",
      schedule_impact_days: "2",
      notes: "Subcontractor notified. Backfill on hold until rectification verified.",
    },
  ];

  function devFillNCR() {
    const sample = NCR_SAMPLES[ncrDevIdx % NCR_SAMPLES.length];
    ncrDevIdx++;
    ncrForm = {
      project: ncrForm.project || (projects.length > 0 ? String(projects[0].id) : ""),
      inspection: "",
      title: sample.title,
      description: sample.description,
      severity: sample.severity,
      root_cause: sample.root_cause,
      status: "open",
      location: sample.location,
      raised_by: sample.raised_by,
      assigned_to: sample.assigned_to,
      rectification_plan: sample.rectification_plan,
      rectification_due_date: sample.rectification_due_date,
      cost_impact: sample.cost_impact,
      schedule_impact_days: sample.schedule_impact_days,
      notes: sample.notes,
    };
  }

  // ── Data Fetching ─────────────────────────────────────────────────────

  async function fetchDashboard() {
    dashLoading = true;
    try {
      dashboard = await api.get<QCDashboard>("/projects/quality-control/dashboard/");
    } catch {
      dashboard = null;
    }
    dashLoading = false;
  }

  async function fetchProjects() {
    if (projects.length > 0) return;
    try {
      const res = await api.get<PaginatedResponse<ProjectListItem>>("/projects/", { page_size: "200", ordering: "name" });
      projects = res.results;
    } catch { /* noop */ }
  }

  async function fetchPlans() {
    plansLoading = true;
    try {
      const params: Record<string, string> = { page: String(plansPage), page_size: String(pageSize) };
      if (plansSearch) params.search = plansSearch;
      if (plansStatusFilter) params.approval_status = plansStatusFilter;
      const res = await api.get<PaginatedResponse<QualityPlanListItem>>("/projects/quality-plans/", params);
      plans = res.results;
      plansTotalCount = res.count;
    } catch {
      plans = [];
      plansTotalCount = 0;
    }
    plansLoading = false;
  }

  async function fetchInspections() {
    inspectionsLoading = true;
    try {
      const params: Record<string, string> = { page: String(inspectionsPage), page_size: String(pageSize) };
      if (inspectionsSearch) params.search = inspectionsSearch;
      if (inspectionsStatusFilter) params.status = inspectionsStatusFilter;
      if (inspectionsTypeFilter) params.inspection_type = inspectionsTypeFilter;
      const [res, summary] = await Promise.all([
        api.get<PaginatedResponse<ProjectExecutionInspection>>("/projects/field-operations/quality-inspections/", params),
        inspectionSummary ? Promise.resolve(inspectionSummary) : api.get<ProjectExecutionInspectionSummary>("/projects/field-operations/quality-inspections/summary/"),
      ]);
      inspections = res.results;
      inspectionsTotalCount = res.count;
      if (!inspectionSummary) inspectionSummary = summary;
    } catch {
      inspections = [];
      inspectionsTotalCount = 0;
    }
    inspectionsLoading = false;
  }

  async function fetchNCRs() {
    ncrsLoading = true;
    try {
      const params: Record<string, string> = { page: String(ncrsPage), page_size: String(pageSize) };
      if (ncrsSearch) params.search = ncrsSearch;
      if (ncrsSeverityFilter) params.severity = ncrsSeverityFilter;
      if (ncrsStatusFilter) params.status = ncrsStatusFilter;
      const [res, summary] = await Promise.all([
        api.get<PaginatedResponse<NCRListItem>>("/projects/ncrs/", params),
        ncrSummary ? Promise.resolve(ncrSummary) : api.get<NCRSummary>("/projects/ncrs/summary/"),
      ]);
      ncrs = res.results;
      ncrsTotalCount = res.count;
      if (!ncrSummary) ncrSummary = summary;
    } catch {
      ncrs = [];
      ncrsTotalCount = 0;
    }
    ncrsLoading = false;
  }

  // Tab-driven data loading
  $effect(() => {
    if (activeTab === "dashboard") fetchDashboard();
  });

  $effect(() => {
    if (activeTab === "plans") {
      void plansSearch;
      void plansStatusFilter;
      void plansPage;
      fetchPlans();
      fetchProjects();
    }
  });

  $effect(() => {
    if (activeTab === "inspections") {
      void inspectionsSearch;
      void inspectionsStatusFilter;
      void inspectionsTypeFilter;
      void inspectionsPage;
      fetchInspections();
    }
  });

  $effect(() => {
    if (activeTab === "ncrs") {
      void ncrsSearch;
      void ncrsSeverityFilter;
      void ncrsStatusFilter;
      void ncrsPage;
      fetchNCRs();
      fetchProjects();
    }
  });

  // Load dashboard on mount
  $effect(() => { fetchDashboard(); });

  // ── Search Handlers ───────────────────────────────────────────────────

  function onPlanSearch(e: Event) {
    plansSearchInput = (e.target as HTMLInputElement).value;
    if (planSearchTimeout) clearTimeout(planSearchTimeout);
    planSearchTimeout = setTimeout(() => { plansSearch = plansSearchInput.trim(); plansPage = 1; }, 250);
  }

  function onInspectionSearch(e: Event) {
    inspectionsSearchInput = (e.target as HTMLInputElement).value;
    if (inspectionSearchTimeout) clearTimeout(inspectionSearchTimeout);
    inspectionSearchTimeout = setTimeout(() => { inspectionsSearch = inspectionsSearchInput.trim(); inspectionsPage = 1; }, 250);
  }

  function onNCRSearch(e: Event) {
    ncrsSearchInput = (e.target as HTMLInputElement).value;
    if (ncrSearchTimeout) clearTimeout(ncrSearchTimeout);
    ncrSearchTimeout = setTimeout(() => { ncrsSearch = ncrsSearchInput.trim(); ncrsPage = 1; }, 250);
  }

  // ── Detail Drawers ────────────────────────────────────────────────────

  async function openPlanDetail(id: number) {
    planDetailId = id;
    planDetailOpen = true;
    planDetailLoading = true;
    try {
      planDetail = await api.get<QualityPlanDetail>(`/projects/quality-plans/${id}/`);
    } catch {
      planDetail = null;
    }
    planDetailLoading = false;
  }

  async function openNCRDetail(id: number) {
    ncrDetailId = id;
    ncrDetailOpen = true;
    ncrDetailLoading = true;
    try {
      ncrDetail = await api.get<NCRDetail>(`/projects/ncrs/${id}/`);
    } catch {
      ncrDetail = null;
    }
    ncrDetailLoading = false;
  }

  // ── Save Handlers ─────────────────────────────────────────────────────

  async function savePlan(e: Event) {
    e.preventDefault();
    if (!planForm.name.trim()) { toast.error("Validation", "Plan name is required."); return; }
    planSaving = true;
    try {
      const payload: Record<string, unknown> = {
        ...planForm,
        project: planForm.project ? Number(planForm.project) : null,
        revision: Number(planForm.revision) || 1,
        approved_date: planForm.approved_date || null,
        next_review_date: planForm.next_review_date || null,
      };
      const created = await api.post<QualityPlanListItem>("/projects/quality-plans/", payload);

      // Create check templates (non-blocking — plan is already saved)
      let checkErrors = 0;
      for (const row of checkRows) {
        if (!row.inspection_point.trim()) continue;
        try {
          await api.post(`/projects/quality-plans/${created.id}/checks/`, row);
        } catch {
          checkErrors++;
        }
      }

      if (checkErrors > 0) {
        toast.success("Quality Plan created", `"${planForm.name}" saved, but ${checkErrors} check template(s) failed to save.`);
      } else {
        toast.success("Quality Plan created", `"${planForm.name}" has been saved.`);
      }
      planCreateOpen = false;
      planForm = defaultPlanForm();
      checkRows = [];
      await fetchPlans();
    } catch (error) {
      if (error instanceof ApiError) {
        const firstField = Object.values(error.fieldErrors)[0]?.[0];
        toast.error("Save failed", firstField ?? "Could not save quality plan.");
      } else {
        toast.error("Save failed", "Could not save quality plan.");
      }
    } finally {
      planSaving = false;
    }
  }

  async function saveNCR(e: Event) {
    e.preventDefault();
    if (!ncrForm.title.trim() || !ncrForm.project) {
      toast.error("Validation", "Title and project are required.");
      return;
    }
    ncrSaving = true;
    try {
      const payload: Record<string, unknown> = {
        ...ncrForm,
        project: Number(ncrForm.project),
        inspection: ncrForm.inspection ? Number(ncrForm.inspection) : null,
        cost_impact: ncrForm.cost_impact || "0",
        schedule_impact_days: Number(ncrForm.schedule_impact_days) || 0,
        rectification_due_date: ncrForm.rectification_due_date || null,
      };
      await api.post("/projects/ncrs/", payload);
      toast.success("NCR raised", `"${ncrForm.title}" has been logged.`);
      ncrCreateOpen = false;
      ncrForm = defaultNCRForm();
      ncrSummary = null;
      await fetchNCRs();
    } catch (error) {
      if (error instanceof ApiError) {
        const firstField = Object.values(error.fieldErrors)[0]?.[0];
        toast.error("Save failed", firstField ?? "Could not save NCR.");
      } else {
        toast.error("Save failed", "Could not save NCR.");
      }
    } finally {
      ncrSaving = false;
    }
  }

  // ── Helpers ───────────────────────────────────────────────────────────

  function fmtDate(value: string | null | undefined): string {
    if (!value) return "--";
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return "--";
    return d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  }

  function fmtCurrency(value: string | number | null | undefined): string {
    if (!value) return "--";
    return currency.format(value);
  }

  function totalPages(count: number): number {
    return Math.max(1, Math.ceil(count / pageSize));
  }

  function severityColor(severity: NCRSeverity): string {
    switch (severity) {
      case "critical": return "bg-red-100 text-red-800";
      case "major": return "bg-orange-100 text-orange-800";
      case "minor": return "bg-neutral-100 text-neutral-600";
      case "observation": return "bg-blue-100 text-blue-700";
      default: return "bg-neutral-100 text-neutral-600";
    }
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: "dashboard", label: "Dashboard" },
    { key: "plans", label: "Quality Plans" },
    { key: "inspections", label: "Site Inspections" },
    { key: "ncrs", label: "NCRs" },
  ];

  useAutoRefresh(["QualityInspection", "NCR"], fetchPlans);
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">Construction</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-900">Execution Quality Control</h1>
      <p class="mt-1 text-sm text-neutral-500">Inspection plans, site checks, and non-conformance tracking.</p>
    </div>
  </div>

  <!-- Tab Bar -->
  <div class="border-b border-neutral-200">
    <nav class="-mb-px flex gap-6">
      {#each tabs as tab}
        <button
          class="whitespace-nowrap border-b-2 px-1 pb-3 text-sm font-medium transition-colors {activeTab === tab.key ? 'border-neutral-900 text-neutral-900' : 'border-transparent text-neutral-500 hover:border-neutral-300 hover:text-neutral-700'}"
          onclick={() => (activeTab = tab.key)}
        >
          {tab.label}
        </button>
      {/each}
    </nav>
  </div>

  <!-- ═════════════════ DASHBOARD TAB ═════════════════ -->
  {#if activeTab === "dashboard"}
    {#if dashLoading}
      <div class="flex items-center justify-center py-16">
        <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
      </div>
    {:else if dashboard}
      <div class="grid grid-cols-2 gap-4 md:grid-cols-4">
        <div class="rounded-xl border border-emerald-100 bg-emerald-50 p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-emerald-700">First-Time Pass Rate</p>
          <p class="mt-1 text-2xl font-bold text-emerald-900 tabular-nums">{dashboard.first_time_pass_rate}%</p>
          <p class="mt-0.5 text-xs text-emerald-600">Goal: &gt;90%</p>
        </div>
        <div class="rounded-xl border border-blue-100 bg-blue-50 p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-blue-700">Total Inspections</p>
          <p class="mt-1 text-2xl font-bold text-blue-900 tabular-nums">{dashboard.total_inspections}</p>
          <p class="mt-0.5 text-xs text-blue-600">{dashboard.passed_inspections} passed / {dashboard.failed_inspections} failed</p>
        </div>
        <div class="rounded-xl border border-rose-100 bg-rose-50 p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-rose-700">Open NCRs</p>
          <p class="mt-1 text-2xl font-bold text-rose-900 tabular-nums">{dashboard.open_ncrs}</p>
          <p class="mt-0.5 text-xs text-rose-600">{dashboard.critical_ncrs} critical</p>
        </div>
        <div class="rounded-xl border border-indigo-100 bg-indigo-50 p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-indigo-700">Active QC Plans</p>
          <p class="mt-1 text-2xl font-bold text-indigo-900 tabular-nums">{dashboard.active_plans}</p>
          {#if dashboard.plans_due_review > 0}
            <p class="mt-0.5 text-xs text-amber-600 font-semibold">{dashboard.plans_due_review} due for review</p>
          {:else}
            <p class="mt-0.5 text-xs text-indigo-600">All plans current</p>
          {/if}
        </div>
      </div>

      <!-- Top Recurring Defects -->
      {#if dashboard.top_defects.length > 0}
        <section class="rounded-2xl border border-neutral-200 bg-white p-6">
          <h3 class="text-sm font-semibold text-neutral-900 mb-4">Top Recurring Defect Causes</h3>
          <div class="space-y-3">
            {#each dashboard.top_defects as defect}
              {@const maxCount = Math.max(...dashboard!.top_defects.map(d => d.count))}
              <div class="flex items-center gap-3">
                <p class="w-40 text-sm text-neutral-700 truncate">{defect.label}</p>
                <div class="flex-1 h-6 bg-neutral-100 rounded-full overflow-hidden">
                  <div
                    class="h-full bg-blue-500 rounded-full transition-all"
                    style="width: {maxCount > 0 ? (defect.count / maxCount) * 100 : 0}%"
                  ></div>
                </div>
                <span class="text-sm font-semibold text-neutral-900 w-8 text-right tabular-nums">{defect.count}</span>
              </div>
            {/each}
          </div>
        </section>
      {/if}
    {/if}

  <!-- ═════════════════ QUALITY PLANS TAB ═════════════════ -->
  {:else if activeTab === "plans"}
    <div class="flex items-center justify-between gap-3 mb-4">
      <div class="flex items-center gap-3 flex-1">
        <input type="text" value={plansSearchInput} oninput={onPlanSearch} placeholder="Search plans..."
          class="w-64 rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        <select bind:value={plansStatusFilter} onchange={() => (plansPage = 1)}
          class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="in_review">In Review</option>
          <option value="approved">Approved</option>
          <option value="superseded">Superseded</option>
          <option value="archived">Archived</option>
        </select>
      </div>
      <button onclick={() => { planForm = defaultPlanForm(); checkRows = []; planCreateOpen = true; }}
        class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800">
        + New Quality Plan
      </button>
    </div>

    <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
      {#if plansLoading}
        <div class="flex items-center justify-center py-16">
          <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
        </div>
      {:else if plans.length === 0}
        <div class="px-6 py-14 text-center">
          <p class="text-sm text-neutral-500">No quality plans found.</p>
        </div>
      {:else}
        <div class="overflow-x-auto">
          <table class="min-w-[800px] w-full">
            <thead class="border-b border-neutral-200 bg-neutral-50">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Plan #</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Name</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Project</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Status</th>
                <th class="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-neutral-500">Checks</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Review Cycle</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Next Review</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each plans as plan}
                <tr class="hover:bg-neutral-50 cursor-pointer" onclick={() => openPlanDetail(plan.id)}>
                  <td class="px-4 py-3 text-sm font-semibold text-neutral-900">{plan.plan_number}</td>
                  <td class="px-4 py-3 text-sm text-neutral-900">{plan.name}</td>
                  <td class="px-4 py-3 text-sm text-neutral-600">{plan.project_name ?? "Template"}</td>
                  <td class="px-4 py-3"><StatusBadge status={plan.approval_status} /></td>
                  <td class="px-4 py-3 text-center text-sm font-semibold tabular-nums text-neutral-700">{plan.check_count}</td>
                  <td class="px-4 py-3 text-sm text-neutral-600">{plan.review_cycle_display}</td>
                  <td class="px-4 py-3 text-sm text-neutral-500">{fmtDate(plan.next_review_date)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>

        <div class="flex items-center justify-between border-t border-neutral-200 px-4 py-3">
          <p class="text-xs text-neutral-500">
            Showing <span class="font-semibold text-neutral-700">{(plansPage - 1) * pageSize + 1}</span>–<span class="font-semibold text-neutral-700">{Math.min(plansPage * pageSize, plansTotalCount)}</span> of <span class="font-semibold text-neutral-700">{plansTotalCount}</span>
          </p>
          <div class="flex items-center gap-2">
            <button onclick={() => (plansPage = Math.max(1, plansPage - 1))} disabled={plansPage <= 1} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 disabled:opacity-40">Previous</button>
            <span class="text-xs font-medium text-neutral-600">Page {plansPage} of {totalPages(plansTotalCount)}</span>
            <button onclick={() => (plansPage = Math.min(totalPages(plansTotalCount), plansPage + 1))} disabled={plansPage >= totalPages(plansTotalCount)} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 disabled:opacity-40">Next</button>
          </div>
        </div>
      {/if}
    </section>

  <!-- ═════════════════ INSPECTIONS TAB ═════════════════ -->
  {:else if activeTab === "inspections"}
    <!-- Summary KPIs -->
    {#if inspectionSummary}
      <div class="grid grid-cols-2 gap-4 md:grid-cols-4 mb-4">
        <div class="rounded-xl border border-neutral-200 bg-white p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Total</p>
          <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{inspectionSummary.total}</p>
        </div>
        <div class="rounded-xl border border-blue-100 bg-blue-50 p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-blue-700">Open</p>
          <p class="mt-1 text-xl font-bold text-blue-900 tabular-nums">{inspectionSummary.open}</p>
        </div>
        <div class="rounded-xl border border-rose-100 bg-rose-50 p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-rose-700">Failed</p>
          <p class="mt-1 text-xl font-bold text-rose-900 tabular-nums">{inspectionSummary.failed}</p>
        </div>
        <div class="rounded-xl border border-amber-100 bg-amber-50 p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-amber-700">Due Actions</p>
          <p class="mt-1 text-xl font-bold text-amber-900 tabular-nums">{inspectionSummary.due_actions}</p>
        </div>
      </div>
    {/if}

    <div class="flex items-center gap-3 mb-4">
      <input type="text" value={inspectionsSearchInput} oninput={onInspectionSearch} placeholder="Search inspections..."
        class="w-64 rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900" />
      <select bind:value={inspectionsStatusFilter} onchange={() => (inspectionsPage = 1)}
        class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
        <option value="">All Statuses</option>
        <option value="planned">Planned</option>
        <option value="in_progress">In Progress</option>
        <option value="passed">Passed</option>
        <option value="failed">Failed</option>
        <option value="blocked">Blocked</option>
        <option value="closed">Closed</option>
      </select>
      <select bind:value={inspectionsTypeFilter} onchange={() => (inspectionsPage = 1)}
        class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
        <option value="">All Types</option>
        <option value="material_receipt">Material Receipt</option>
        <option value="workmanship">Workmanship</option>
        <option value="mep">MEP</option>
        <option value="finishes">Finishes</option>
        <option value="safety_quality">Safety & Quality</option>
        <option value="pre_handover">Pre-Handover</option>
        <option value="other">Other</option>
      </select>
    </div>

    <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
      {#if inspectionsLoading}
        <div class="flex items-center justify-center py-16">
          <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
        </div>
      {:else if inspections.length === 0}
        <div class="px-6 py-14 text-center">
          <p class="text-sm text-neutral-500">No inspections found.</p>
        </div>
      {:else}
        <div class="overflow-x-auto">
          <table class="min-w-[900px] w-full">
            <thead class="border-b border-neutral-200 bg-neutral-50">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Date</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Inspection #</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Project</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Type</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Status</th>
                <th class="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-neutral-500">Score</th>
                <th class="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-neutral-500">Findings</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Inspector</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each inspections as ins}
                <tr class="hover:bg-neutral-50">
                  <td class="px-4 py-3 text-sm text-neutral-500">{fmtDate(ins.inspected_on)}</td>
                  <td class="px-4 py-3 text-sm font-semibold text-neutral-900">{ins.inspection_number}</td>
                  <td class="px-4 py-3 text-sm text-neutral-700">{ins.project_name}</td>
                  <td class="px-4 py-3 text-xs font-medium text-neutral-600 capitalize">{ins.inspection_type.replace(/_/g, " ")}</td>
                  <td class="px-4 py-3"><StatusBadge status={ins.status} /></td>
                  <td class="px-4 py-3 text-center text-sm font-semibold tabular-nums {ins.overall_score && Number(ins.overall_score) < 70 ? 'text-red-600' : 'text-neutral-900'}">
                    {ins.overall_score ? `${ins.overall_score}%` : "--"}
                  </td>
                  <td class="px-4 py-3 text-center">
                    {#if ins.critical_findings > 0}
                      <span class="inline-block px-1.5 py-0.5 text-[10px] font-semibold bg-red-100 text-red-700 rounded mr-1">{ins.critical_findings}C</span>
                    {/if}
                    {#if ins.major_findings > 0}
                      <span class="inline-block px-1.5 py-0.5 text-[10px] font-semibold bg-orange-100 text-orange-700 rounded mr-1">{ins.major_findings}M</span>
                    {/if}
                    {#if ins.minor_findings > 0}
                      <span class="inline-block px-1.5 py-0.5 text-[10px] font-semibold bg-neutral-100 text-neutral-600 rounded">{ins.minor_findings}m</span>
                    {/if}
                    {#if ins.critical_findings === 0 && ins.major_findings === 0 && ins.minor_findings === 0}
                      <span class="text-xs text-neutral-400">--</span>
                    {/if}
                  </td>
                  <td class="px-4 py-3 text-sm text-neutral-600">{ins.inspector_name || "--"}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>

        <div class="flex items-center justify-between border-t border-neutral-200 px-4 py-3">
          <p class="text-xs text-neutral-500">
            Showing <span class="font-semibold text-neutral-700">{(inspectionsPage - 1) * pageSize + 1}</span>–<span class="font-semibold text-neutral-700">{Math.min(inspectionsPage * pageSize, inspectionsTotalCount)}</span> of <span class="font-semibold text-neutral-700">{inspectionsTotalCount}</span>
          </p>
          <div class="flex items-center gap-2">
            <button onclick={() => (inspectionsPage = Math.max(1, inspectionsPage - 1))} disabled={inspectionsPage <= 1} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 disabled:opacity-40">Previous</button>
            <span class="text-xs font-medium text-neutral-600">Page {inspectionsPage} of {totalPages(inspectionsTotalCount)}</span>
            <button onclick={() => (inspectionsPage = Math.min(totalPages(inspectionsTotalCount), inspectionsPage + 1))} disabled={inspectionsPage >= totalPages(inspectionsTotalCount)} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 disabled:opacity-40">Next</button>
          </div>
        </div>
      {/if}
    </section>

  <!-- ═════════════════ NCR TAB ═════════════════ -->
  {:else if activeTab === "ncrs"}
    <!-- NCR Summary KPIs -->
    {#if ncrSummary}
      <div class="grid grid-cols-2 gap-4 md:grid-cols-5 mb-4">
        <div class="rounded-xl border border-neutral-200 bg-white p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Total NCRs</p>
          <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{ncrSummary.total}</p>
        </div>
        <div class="rounded-xl border border-rose-100 bg-rose-50 p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-rose-700">Open</p>
          <p class="mt-1 text-xl font-bold text-rose-900 tabular-nums">{ncrSummary.open}</p>
        </div>
        <div class="rounded-xl border border-red-100 bg-red-50 p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-red-700">Critical Open</p>
          <p class="mt-1 text-xl font-bold text-red-900 tabular-nums">{ncrSummary.critical_open}</p>
        </div>
        <div class="rounded-xl border border-amber-100 bg-amber-50 p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-amber-700">Overdue</p>
          <p class="mt-1 text-xl font-bold text-amber-900 tabular-nums">{ncrSummary.overdue}</p>
        </div>
        <div class="rounded-xl border border-emerald-100 bg-emerald-50 p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-emerald-700">Closed This Month</p>
          <p class="mt-1 text-xl font-bold text-emerald-900 tabular-nums">{ncrSummary.closed_this_month}</p>
        </div>
      </div>
    {/if}

    <div class="flex items-center justify-between gap-3 mb-4">
      <div class="flex items-center gap-3 flex-1">
        <input type="text" value={ncrsSearchInput} oninput={onNCRSearch} placeholder="Search NCRs..."
          class="w-64 rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        <select bind:value={ncrsSeverityFilter} onchange={() => (ncrsPage = 1)}
          class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
          <option value="">All Severities</option>
          <option value="critical">Critical / Safety</option>
          <option value="major">Major</option>
          <option value="minor">Minor / Cosmetic</option>
          <option value="observation">Observation</option>
        </select>
        <select bind:value={ncrsStatusFilter} onchange={() => (ncrsPage = 1)}
          class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900">
          <option value="">All Statuses</option>
          <option value="open">Open</option>
          <option value="under_review">Under Review</option>
          <option value="rectification">Rectification</option>
          <option value="verification">Verification</option>
          <option value="closed">Closed</option>
          <option value="accepted">Accepted</option>
        </select>
      </div>
      <button onclick={() => { ncrForm = defaultNCRForm(); ncrCreateOpen = true; }}
        class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800">
        + Raise NCR
      </button>
    </div>

    <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
      {#if ncrsLoading}
        <div class="flex items-center justify-center py-16">
          <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
        </div>
      {:else if ncrs.length === 0}
        <div class="px-6 py-14 text-center">
          <p class="text-sm text-neutral-500">No NCRs found.</p>
        </div>
      {:else}
        <div class="overflow-x-auto">
          <table class="min-w-[950px] w-full">
            <thead class="border-b border-neutral-200 bg-neutral-50">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">NCR #</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Title</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Project</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Severity</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Root Cause</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Status</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Assigned To</th>
                <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Due Date</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each ncrs as ncr}
                <tr class="hover:bg-neutral-50 cursor-pointer" onclick={() => openNCRDetail(ncr.id)}>
                  <td class="px-4 py-3 text-sm font-semibold text-neutral-900">{ncr.ncr_number}</td>
                  <td class="px-4 py-3 text-sm text-neutral-900 max-w-[240px] truncate">{ncr.title}</td>
                  <td class="px-4 py-3 text-sm text-neutral-600">{ncr.project_name}</td>
                  <td class="px-4 py-3">
                    <span class="inline-block px-2 py-0.5 text-[10px] font-semibold rounded-full {severityColor(ncr.severity)}">{ncr.severity_display}</span>
                  </td>
                  <td class="px-4 py-3 text-xs text-neutral-600">{ncr.root_cause_display}</td>
                  <td class="px-4 py-3"><StatusBadge status={ncr.status} /></td>
                  <td class="px-4 py-3 text-sm text-neutral-600">{ncr.assigned_to || "--"}</td>
                  <td class="px-4 py-3 text-sm text-neutral-500">{fmtDate(ncr.rectification_due_date)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>

        <div class="flex items-center justify-between border-t border-neutral-200 px-4 py-3">
          <p class="text-xs text-neutral-500">
            Showing <span class="font-semibold text-neutral-700">{(ncrsPage - 1) * pageSize + 1}</span>–<span class="font-semibold text-neutral-700">{Math.min(ncrsPage * pageSize, ncrsTotalCount)}</span> of <span class="font-semibold text-neutral-700">{ncrsTotalCount}</span>
          </p>
          <div class="flex items-center gap-2">
            <button onclick={() => (ncrsPage = Math.max(1, ncrsPage - 1))} disabled={ncrsPage <= 1} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 disabled:opacity-40">Previous</button>
            <span class="text-xs font-medium text-neutral-600">Page {ncrsPage} of {totalPages(ncrsTotalCount)}</span>
            <button onclick={() => (ncrsPage = Math.min(totalPages(ncrsTotalCount), ncrsPage + 1))} disabled={ncrsPage >= totalPages(ncrsTotalCount)} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 disabled:opacity-40">Next</button>
          </div>
        </div>
      {/if}
    </section>
  {/if}
</div>

<!-- ═════════════════ QUALITY PLAN DETAIL DRAWER ═════════════════ -->
<DrawerShell open={planDetailOpen} title={planDetail?.plan_number ?? "Quality Plan"} subtitle={planDetail?.name ?? ""} width="max-w-xl" onclose={() => (planDetailOpen = false)}>
  {#if planDetailLoading}
    <div class="flex items-center justify-center py-16">
      <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
    </div>
  {:else if planDetail}
    <div class="p-6 space-y-5">
      <div class="grid grid-cols-2 gap-4">
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Status</p>
          <StatusBadge status={planDetail.approval_status} />
        </div>
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Review Cycle</p>
          <p class="text-sm text-neutral-900">{planDetail.review_cycle_display}</p>
        </div>
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Project</p>
          <p class="text-sm text-neutral-900">{planDetail.project_name ?? "Template (no project)"}</p>
        </div>
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Revision</p>
          <p class="text-sm text-neutral-900">Rev {planDetail.revision}</p>
        </div>
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Approved By</p>
          <p class="text-sm text-neutral-900">{planDetail.approved_by || "--"}</p>
        </div>
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Next Review</p>
          <p class="text-sm text-neutral-900">{fmtDate(planDetail.next_review_date)}</p>
        </div>
      </div>

      {#if planDetail.compliance_standards}
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Compliance Standards</p>
          <p class="text-sm text-neutral-700 whitespace-pre-line">{planDetail.compliance_standards}</p>
        </div>
      {/if}

      {#if planDetail.description}
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Description</p>
          <p class="text-sm text-neutral-700 whitespace-pre-line">{planDetail.description}</p>
        </div>
      {/if}

      <!-- Check Templates -->
      {#if planDetail.check_templates.length > 0}
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-2">Inspection Checks ({planDetail.check_templates.length})</p>
          <div class="divide-y divide-neutral-100 rounded-lg border border-neutral-200">
            {#each planDetail.check_templates as check}
              <div class="px-4 py-3 flex items-start gap-3">
                <span class="text-xs font-semibold text-neutral-500 shrink-0 mt-0.5">{check.check_id}</span>
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-neutral-900">{check.inspection_point}</p>
                  {#if check.requirement_standard}
                    <p class="text-xs text-neutral-500 mt-0.5">{check.requirement_standard}</p>
                  {/if}
                </div>
                <div class="flex items-center gap-2 shrink-0">
                  <span class="text-[10px] font-medium px-2 py-0.5 rounded-full bg-neutral-100 text-neutral-600">{check.evidence_type_display}</span>
                  {#if check.is_critical}
                    <span class="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-red-100 text-red-700">CRITICAL</span>
                  {/if}
                </div>
              </div>
            {/each}
          </div>
        </div>
      {/if}

      {#if planDetail.notes}
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Notes</p>
          <p class="text-sm text-neutral-700 whitespace-pre-line">{planDetail.notes}</p>
        </div>
      {/if}
    </div>
  {/if}
</DrawerShell>

<!-- ═════════════════ QUALITY PLAN CREATE DRAWER ═════════════════ -->
<DrawerShell open={planCreateOpen} title="New Quality Plan" subtitle="Define inspection strategy and check points" width="max-w-xl" onclose={() => (planCreateOpen = false)}>
  <form onsubmit={savePlan} class="p-6 space-y-4">
    <label class="block">
      <span class="mb-1 block text-xs font-semibold text-neutral-600">Plan Name *</span>
      <input bind:value={planForm.name} placeholder="e.g. Residential Tower QC Plan" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
    </label>

    <div class="grid grid-cols-2 gap-4">
      <label>
        <span class="mb-1 block text-xs font-semibold text-neutral-600">Project</span>
        <select bind:value={planForm.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          <option value="">None (Template)</option>
          {#each projects as project}
            <option value={String(project.id)}>{project.name}</option>
          {/each}
        </select>
      </label>
      <label>
        <span class="mb-1 block text-xs font-semibold text-neutral-600">Review Cycle</span>
        <select bind:value={planForm.review_cycle} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          <option value="weekly">Weekly</option>
          <option value="fortnightly">Fortnightly</option>
          <option value="monthly">Monthly</option>
          <option value="quarterly">Quarterly</option>
          <option value="biannual">Bi-Annual</option>
          <option value="annual">Annual</option>
          <option value="as_needed">As Needed</option>
        </select>
      </label>
    </div>

    <label class="block">
      <span class="mb-1 block text-xs font-semibold text-neutral-600">Compliance Standards</span>
      <textarea bind:value={planForm.compliance_standards} rows="2" placeholder="e.g. ISO 9001:2015, NIS 87:2000" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>
    </label>

    <label class="block">
      <span class="mb-1 block text-xs font-semibold text-neutral-600">Description</span>
      <textarea bind:value={planForm.description} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>
    </label>

    <div class="grid grid-cols-2 gap-4">
      <label>
        <span class="mb-1 block text-xs font-semibold text-neutral-600">Approved By</span>
        <input bind:value={planForm.approved_by} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
      </label>
      <label>
        <span class="mb-1 block text-xs font-semibold text-neutral-600">Next Review Date</span>
        <DateInput bind:value={planForm.next_review_date} />
      </label>
    </div>

    <label class="block">
      <span class="mb-1 block text-xs font-semibold text-neutral-600">Notes</span>
      <textarea bind:value={planForm.notes} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>
    </label>

    <!-- Inspection Check Templates -->
    <div>
      <div class="flex items-center justify-between mb-2">
        <span class="text-xs font-semibold text-neutral-600">Inspection Check Points</span>
        <button type="button" onclick={addCheckRow} class="rounded-md bg-neutral-100 px-3 py-1 text-xs font-medium text-neutral-700 hover:bg-neutral-200">+ Add Check</button>
      </div>
      {#if checkRows.length > 0}
        <div class="space-y-3">
          {#each checkRows as row, idx}
            <div class="rounded-lg border border-neutral-200 p-3 space-y-2 relative">
              <button type="button" onclick={() => removeCheckRow(idx)} class="absolute top-2 right-2 text-neutral-400 hover:text-red-500 text-xs" aria-label="Remove check">X</button>
              <input bind:value={row.inspection_point} placeholder="Inspection point (e.g. Rebar Cover & Spacing)" class="w-full rounded-md border border-neutral-200 px-3 py-1.5 text-sm" />
              <input bind:value={row.requirement_standard} placeholder="Requirement / standard" class="w-full rounded-md border border-neutral-200 px-3 py-1.5 text-sm" />
              <div class="flex items-center gap-3">
                <select bind:value={row.evidence_type} class="rounded-md border border-neutral-200 bg-white px-2 py-1.5 text-xs">
                  <option value="pass_fail">Pass / Fail</option>
                  <option value="numerical">Numerical Entry</option>
                  <option value="photo">Photo Upload</option>
                  <option value="text">Text / Notes</option>
                  <option value="document">Document Upload</option>
                </select>
                <label class="flex items-center gap-1.5 text-xs text-neutral-600">
                  <input type="checkbox" bind:checked={row.is_critical} class="rounded" />
                  Critical
                </label>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>

    <div class="flex justify-end gap-2 pt-2">
      <button type="button" onclick={() => (planCreateOpen = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      {#if isDev}
        <button type="button" onclick={devFillPlan} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>
      {/if}
      <button type="submit" disabled={planSaving} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">
        {planSaving ? "Saving..." : "Create Plan"}
      </button>
    </div>
  </form>
</DrawerShell>

<!-- ═════════════════ NCR DETAIL DRAWER ═════════════════ -->
<DrawerShell open={ncrDetailOpen} title={ncrDetail?.ncr_number ?? "NCR"} subtitle={ncrDetail?.title ?? ""} width="max-w-xl" onclose={() => (ncrDetailOpen = false)}>
  {#if ncrDetailLoading}
    <div class="flex items-center justify-center py-16">
      <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
    </div>
  {:else if ncrDetail}
    <div class="p-6 space-y-5">
      <!-- Severity banner -->
      <div class="rounded-lg p-3 {ncrDetail.severity === 'critical' ? 'bg-red-50 border border-red-200' : ncrDetail.severity === 'major' ? 'bg-orange-50 border border-orange-200' : 'bg-neutral-50 border border-neutral-200'}">
        <div class="flex items-center justify-between">
          <span class="text-xs font-semibold uppercase {ncrDetail.severity === 'critical' ? 'text-red-700' : ncrDetail.severity === 'major' ? 'text-orange-700' : 'text-neutral-600'}">{ncrDetail.severity_display}</span>
          <StatusBadge status={ncrDetail.status} />
        </div>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Project</p>
          <p class="text-sm text-neutral-900">{ncrDetail.project_name}</p>
        </div>
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Root Cause</p>
          <p class="text-sm text-neutral-900">{ncrDetail.root_cause_display}</p>
        </div>
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Location</p>
          <p class="text-sm text-neutral-900">{ncrDetail.location || "--"}</p>
        </div>
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Inspection</p>
          <p class="text-sm text-neutral-900">{ncrDetail.inspection_number ?? "--"}</p>
        </div>
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Raised By</p>
          <p class="text-sm text-neutral-900">{ncrDetail.raised_by || "--"}</p>
        </div>
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Raised Date</p>
          <p class="text-sm text-neutral-900">{fmtDate(ncrDetail.raised_date)}</p>
        </div>
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Assigned To</p>
          <p class="text-sm text-neutral-900">{ncrDetail.assigned_to || "--"}</p>
        </div>
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Rectification Due</p>
          <p class="text-sm text-neutral-900">{fmtDate(ncrDetail.rectification_due_date)}</p>
        </div>
      </div>

      <!-- Cost / Schedule Impact -->
      <div class="grid grid-cols-2 gap-4">
        <div class="rounded-lg border border-neutral-200 p-3 text-center">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Cost Impact</p>
          <p class="text-lg font-bold text-neutral-900 tabular-nums">{fmtCurrency(ncrDetail.cost_impact)}</p>
        </div>
        <div class="rounded-lg border border-neutral-200 p-3 text-center">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Schedule Impact</p>
          <p class="text-lg font-bold text-neutral-900 tabular-nums">{ncrDetail.schedule_impact_days} days</p>
        </div>
      </div>

      {#if ncrDetail.description}
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Description</p>
          <p class="text-sm text-neutral-700 whitespace-pre-line">{ncrDetail.description}</p>
        </div>
      {/if}

      {#if ncrDetail.rectification_plan}
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Rectification Plan</p>
          <p class="text-sm text-neutral-700 whitespace-pre-line">{ncrDetail.rectification_plan}</p>
        </div>
      {/if}

      {#if ncrDetail.verification_notes}
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Verification Notes</p>
          <p class="text-sm text-neutral-700 whitespace-pre-line">{ncrDetail.verification_notes}</p>
        </div>
      {/if}

      {#if ncrDetail.notes}
        <div>
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Notes</p>
          <p class="text-sm text-neutral-700 whitespace-pre-line">{ncrDetail.notes}</p>
        </div>
      {/if}
    </div>
  {/if}
</DrawerShell>

<!-- ═════════════════ NCR CREATE DRAWER ═════════════════ -->
<DrawerShell open={ncrCreateOpen} title="Raise NCR" subtitle="Log a non-conformance report" width="max-w-xl" onclose={() => (ncrCreateOpen = false)}>
  <form onsubmit={saveNCR} class="p-6 space-y-4">
    <label class="block">
      <span class="mb-1 block text-xs font-semibold text-neutral-600">Title *</span>
      <input bind:value={ncrForm.title} placeholder="e.g. Exposed rebar at Column C7" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
    </label>

    <div class="grid grid-cols-2 gap-4">
      <label>
        <span class="mb-1 block text-xs font-semibold text-neutral-600">Project *</span>
        <select bind:value={ncrForm.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          <option value="">Select project</option>
          {#each projects as project}
            <option value={String(project.id)}>{project.name}</option>
          {/each}
        </select>
      </label>
      <label>
        <span class="mb-1 block text-xs font-semibold text-neutral-600">Location</span>
        <input bind:value={ncrForm.location} placeholder="Block A, Level 3" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
      </label>
    </div>

    <div class="grid grid-cols-2 gap-4">
      <label>
        <span class="mb-1 block text-xs font-semibold text-neutral-600">Severity</span>
        <select bind:value={ncrForm.severity} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          <option value="critical">Critical / Safety</option>
          <option value="major">Major</option>
          <option value="minor">Minor / Cosmetic</option>
          <option value="observation">Observation</option>
        </select>
      </label>
      <label>
        <span class="mb-1 block text-xs font-semibold text-neutral-600">Root Cause</span>
        <select bind:value={ncrForm.root_cause} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          <option value="material_defect">Material Defect</option>
          <option value="workmanship">Workmanship</option>
          <option value="design_error">Design Error</option>
          <option value="weather">Weather / Environmental</option>
          <option value="equipment">Equipment Failure</option>
          <option value="process">Process Non-compliance</option>
          <option value="other">Other</option>
        </select>
      </label>
    </div>

    <label class="block">
      <span class="mb-1 block text-xs font-semibold text-neutral-600">Description</span>
      <textarea bind:value={ncrForm.description} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>
    </label>

    <div class="grid grid-cols-2 gap-4">
      <label>
        <span class="mb-1 block text-xs font-semibold text-neutral-600">Raised By</span>
        <input bind:value={ncrForm.raised_by} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
      </label>
      <label>
        <span class="mb-1 block text-xs font-semibold text-neutral-600">Assigned To</span>
        <input bind:value={ncrForm.assigned_to} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
      </label>
    </div>

    <label class="block">
      <span class="mb-1 block text-xs font-semibold text-neutral-600">Rectification Plan</span>
      <textarea bind:value={ncrForm.rectification_plan} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>
    </label>

    <div class="grid grid-cols-3 gap-4">
      <label>
        <span class="mb-1 block text-xs font-semibold text-neutral-600">Due Date</span>
        <DateInput bind:value={ncrForm.rectification_due_date} />
      </label>
      <label>
        <span class="mb-1 block text-xs font-semibold text-neutral-600">Cost Impact</span>
        <input type="number" step="0.01" bind:value={ncrForm.cost_impact} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
      </label>
      <label>
        <span class="mb-1 block text-xs font-semibold text-neutral-600">Schedule Impact (days)</span>
        <input type="number" bind:value={ncrForm.schedule_impact_days} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
      </label>
    </div>

    <label class="block">
      <span class="mb-1 block text-xs font-semibold text-neutral-600">Notes</span>
      <textarea bind:value={ncrForm.notes} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>
    </label>

    <div class="flex justify-end gap-2 pt-2">
      <button type="button" onclick={() => (ncrCreateOpen = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      {#if isDev}
        <button type="button" onclick={devFillNCR} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>
      {/if}
      <button type="submit" disabled={ncrSaving} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">
        {ncrSaving ? "Saving..." : "Raise NCR"}
      </button>
    </div>
  </form>
</DrawerShell>

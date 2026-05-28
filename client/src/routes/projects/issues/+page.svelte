<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    PaginatedResponse,
    ProjectDailySiteReport,
    ProjectFieldEscalation,
    ProjectFieldEscalationSummary,
    ProjectIssueCategory,
    ProjectIssueType,
    ProjectListItem,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  type IssueForm = {
    project: string;
    source_report: string;
    issue_date: string;
    issue_category: ProjectIssueCategory;
    issue_type: ProjectIssueType;
    title: string;
    description: string;
    location: string;
    weather_condition: "" | "clear" | "cloudy" | "rain" | "storm" | "windy" | "other";
    weather_delay_hours: string;
    estimated_schedule_impact_days: string;
    estimated_cost_impact: string;
    impact_summary: string;
    root_cause: string;
    immediate_action: string;
    severity: "info" | "review" | "action_required" | "escalation";
    status: "open" | "acknowledged" | "in_progress" | "resolved" | "closed";
    owner_name: string;
    due_date: string;
    resolution_notes: string;
  };

  const ISSUE_CATEGORY_OPTIONS: Array<{ value: ProjectIssueCategory; label: string }> = [
    { value: "weather", label: "Weather" },
    { value: "safety", label: "Safety" },
    { value: "quality", label: "Quality" },
    { value: "schedule", label: "Schedule" },
    { value: "cost", label: "Cost" },
    { value: "workforce", label: "Workforce" },
    { value: "procurement", label: "Procurement" },
    { value: "equipment", label: "Equipment" },
    { value: "design", label: "Design" },
    { value: "compliance", label: "Compliance" },
    { value: "logistics", label: "Logistics" },
    { value: "community", label: "Community" },
    { value: "operations", label: "Operations" },
    { value: "external", label: "External" },
    { value: "other", label: "Other" },
  ];

  const ISSUE_TYPE_OPTIONS: Array<{ value: ProjectIssueType; label: string; category: ProjectIssueCategory }> = [
    { value: "weather_delay", label: "Weather Delay", category: "weather" },
    { value: "extreme_rain_flooding", label: "Extreme Rain / Flooding", category: "weather" },
    { value: "high_wind", label: "High Wind", category: "weather" },
    { value: "lightning_storm", label: "Lightning Storm", category: "weather" },
    { value: "extreme_heat", label: "Extreme Heat", category: "weather" },
    { value: "material_shortage", label: "Material Shortage", category: "procurement" },
    { value: "material_damage", label: "Material Damage", category: "procurement" },
    { value: "late_delivery", label: "Late Delivery", category: "procurement" },
    { value: "vendor_non_performance", label: "Vendor Non-Performance", category: "procurement" },
    { value: "subcontractor_non_performance", label: "Subcontractor Non-Performance", category: "procurement" },
    { value: "workforce_shortage", label: "Workforce Shortage", category: "workforce" },
    { value: "labor_dispute", label: "Labor Dispute", category: "workforce" },
    { value: "equipment_breakdown", label: "Equipment Breakdown", category: "equipment" },
    { value: "equipment_unavailable", label: "Equipment Unavailable", category: "equipment" },
    { value: "quality_defect", label: "Quality Defect", category: "quality" },
    { value: "rework_required", label: "Rework Required", category: "quality" },
    { value: "inspection_failure", label: "Inspection Failure", category: "quality" },
    { value: "test_failure", label: "Test Failure", category: "quality" },
    { value: "safety_incident", label: "Safety Incident", category: "safety" },
    { value: "near_miss", label: "Near Miss", category: "safety" },
    { value: "accident_injury", label: "Accident / Injury", category: "safety" },
    { value: "security_breach", label: "Security Breach", category: "safety" },
    { value: "theft_vandalism", label: "Theft / Vandalism", category: "safety" },
    { value: "design_change", label: "Design Change", category: "design" },
    { value: "drawing_conflict", label: "Drawing Conflict", category: "design" },
    { value: "rfi_pending", label: "RFI Pending", category: "design" },
    { value: "permit_hold", label: "Permit Hold", category: "compliance" },
    { value: "regulatory_stop_notice", label: "Regulatory Stop Notice", category: "compliance" },
    { value: "environmental_non_compliance", label: "Environmental Non-Compliance", category: "compliance" },
    { value: "access_restriction", label: "Access Restriction", category: "logistics" },
    { value: "traffic_logistics", label: "Traffic / Logistics Constraint", category: "logistics" },
    { value: "utility_outage", label: "Utility Outage", category: "operations" },
    { value: "community_complaint", label: "Community Complaint", category: "community" },
    { value: "scope_change", label: "Scope Change", category: "schedule" },
    { value: "schedule_slippage", label: "Schedule Slippage", category: "schedule" },
    { value: "cost_overrun", label: "Cost Overrun", category: "cost" },
    { value: "payment_delay", label: "Payment Delay", category: "cost" },
    { value: "it_system_outage", label: "IT System Outage", category: "operations" },
    { value: "data_loss", label: "Data Loss", category: "operations" },
    { value: "handover_defect", label: "Handover Defect", category: "quality" },
    { value: "force_majeure", label: "Force Majeure", category: "external" },
    { value: "general_site_issue", label: "General Site Issue", category: "operations" },
    { value: "other", label: "Other", category: "other" },
  ];

  const SEVERITY_OPTIONS = [
    { value: "info", label: "Info" },
    { value: "review", label: "Review" },
    { value: "action_required", label: "Action Required" },
    { value: "escalation", label: "Escalation" },
  ] as const;

  const STATUS_OPTIONS = [
    { value: "open", label: "Open" },
    { value: "acknowledged", label: "Acknowledged" },
    { value: "in_progress", label: "In Progress" },
    { value: "resolved", label: "Resolved" },
    { value: "closed", label: "Closed" },
  ] as const;

  const WEATHER_OPTIONS: Array<{ value: IssueForm["weather_condition"]; label: string }> = [
    { value: "", label: "Not specified" },
    { value: "clear", label: "Clear" },
    { value: "cloudy", label: "Cloudy" },
    { value: "rain", label: "Rain" },
    { value: "storm", label: "Storm" },
    { value: "windy", label: "Windy" },
    { value: "other", label: "Other" },
  ];

  const today = new Date().toISOString().slice(0, 10);
  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  let loading = $state(true);
  let saving = $state(false);
  let showForm = $state(false);

  let projects = $state<ProjectListItem[]>([]);
  let siteReports = $state<ProjectDailySiteReport[]>([]);
  let issues = $state<ProjectFieldEscalation[]>([]);
  let summary = $state<ProjectFieldEscalationSummary>({
    total: 0,
    open: 0,
    critical: 0,
    overdue: 0,
    weather_issues: 0,
    weather_delay_hours_total: "0.00",
  });

  let filterProject = $state("");
  let filterStatus = $state("");
  let filterSeverity = $state("");
  let filterCategory = $state("");
  let filterType = $state("");
  let search = $state("");
  let sort = $state("date_desc");
  let page = $state(1);
  let pageSize = $state(10);
  let expandedIssueRowId = $state<number | null>(null);

  let files = $state<File[]>([]);

  let form = $state<IssueForm>({
    project: "",
    source_report: "",
    issue_date: today,
    issue_category: "operations",
    issue_type: "general_site_issue",
    title: "",
    description: "",
    location: "",
    weather_condition: "",
    weather_delay_hours: "0",
    estimated_schedule_impact_days: "",
    estimated_cost_impact: "",
    impact_summary: "",
    root_cause: "",
    immediate_action: "",
    severity: "review",
    status: "open",
    owner_name: "",
    due_date: "",
    resolution_notes: "",
  });

  function resetForm() {
    form = {
      project: filterProject || "",
      source_report: "",
      issue_date: today,
      issue_category: "operations",
      issue_type: "general_site_issue",
      title: "",
      description: "",
      location: "",
      weather_condition: "",
      weather_delay_hours: "0",
      estimated_schedule_impact_days: "",
      estimated_cost_impact: "",
      impact_summary: "",
      root_cause: "",
      immediate_action: "",
      severity: "review",
      status: "open",
      owner_name: "",
      due_date: "",
      resolution_notes: "",
    };
    files = [];
  }

  const ISSUE_SAMPLES: IssueForm[] = [
    {
      project: "",
      source_report: "",
      issue_date: today,
      issue_category: "quality",
      issue_type: "rework_required",
      title: "Concrete slab cracking on Level 3 — rework required",
      description: "Visible surface cracks (>0.3 mm) observed on the Level 3 east wing slab after formwork was stripped. Crack pattern suggests premature drying or inadequate curing. Structural engineer has been notified to assess whether cracks are cosmetic or structural.",
      location: "Building A — Level 3, East Wing",
      weather_condition: "clear",
      weather_delay_hours: "0",
      estimated_schedule_impact_days: "4",
      estimated_cost_impact: "28500.00",
      impact_summary: "4-day delay to Level 3 finishes schedule. Cost includes epoxy injection repair and additional curing materials. May push handover milestone by 2 days if structural assessment requires further intervention.",
      root_cause: "Inadequate wet curing — protective sheeting was removed after only 2 days instead of the specified 7-day curing period. High ambient temperature (38°C) accelerated moisture loss.",
      immediate_action: "Area cordoned off. Structural engineer inspection scheduled. Curing protocol reminder issued to all concrete crews. Temporary wet hessian applied to affected areas.",
      severity: "action_required",
      status: "open",
      owner_name: "Ahmed Al-Rashid",
      due_date: new Date(Date.now() + 5 * 86400000).toISOString().slice(0, 10),
      resolution_notes: "",
    },
    {
      project: "",
      source_report: "",
      issue_date: today,
      issue_category: "weather",
      issue_type: "extreme_rain_flooding",
      title: "Flash flooding halts excavation works — pumping in progress",
      description: "Unexpected heavy rainfall (85 mm in 3 hours) caused flooding in the basement excavation pit. Water level rose approximately 1.2 m above the working platform. All excavation and shoring works suspended. Dewatering pumps deployed.",
      location: "Basement Excavation — Zone B2",
      weather_condition: "storm",
      weather_delay_hours: "16",
      estimated_schedule_impact_days: "3",
      estimated_cost_impact: "12000.00",
      impact_summary: "Full-day work stoppage for excavation crews. Dewatering expected to take 12-16 hours. Soil condition reassessment needed before work resumes. Potential 3-day delay to piling schedule.",
      root_cause: "Unseasonable storm system — weather forecast predicted only light showers. Site drainage capacity exceeded by volume of rainfall.",
      immediate_action: "3 submersible pumps deployed. Excavation perimeter berms reinforced. All personnel evacuated from pit. Geotechnical engineer contacted to assess soil stability post-drainage.",
      severity: "escalation",
      status: "open",
      owner_name: "Fatima Okonkwo",
      due_date: new Date(Date.now() + 2 * 86400000).toISOString().slice(0, 10),
      resolution_notes: "",
    },
    {
      project: "",
      source_report: "",
      issue_date: today,
      issue_category: "safety",
      issue_type: "near_miss",
      title: "Unsecured scaffolding plank falls from height — near miss",
      description: "A loose scaffolding board (2.4 m timber plank) fell from the Level 5 scaffolding platform to ground level during wind gusts. No personnel were injured. The plank landed in a restricted-access zone approximately 2 m from a pedestrian walkway.",
      location: "Building B — West Elevation, Level 5 Scaffold",
      weather_condition: "windy",
      weather_delay_hours: "2",
      estimated_schedule_impact_days: "1",
      estimated_cost_impact: "3500.00",
      impact_summary: "Scaffolding inspection required before work can resume at height. Half-day delay while all scaffolding on west elevation is re-inspected and secured. Safety stand-down meeting for all crews.",
      root_cause: "Scaffolding plank not properly secured with toe-boards and clamps. End-of-shift inspection protocol was not followed by the scaffold crew on the previous day.",
      immediate_action: "Area below scaffold cordoned off. Full scaffold inspection initiated. Toolbox talk on scaffold safety conducted for all crews. Incident reported to HSE manager. Near-miss form completed.",
      severity: "escalation",
      status: "acknowledged",
      owner_name: "James Mwangi",
      due_date: new Date(Date.now() + 1 * 86400000).toISOString().slice(0, 10),
      resolution_notes: "",
    },
  ];

  let issueDevIdx = 0;

  function devFillIssue() {
    const sample = ISSUE_SAMPLES[issueDevIdx % ISSUE_SAMPLES.length];
    issueDevIdx++;
    form = {
      ...sample,
      project: form.project || (projects.length > 0 ? String(projects[0].id) : ""),
    };
  }

  function parseId(value: string): number | null {
    const parsed = Number.parseInt(value, 10);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
  }

  function toDecimal(value: string, fallback = "0"): string {
    const raw = value.trim();
    if (!raw) return fallback;
    const parsed = Number(raw);
    if (!Number.isFinite(parsed) || parsed < 0) return fallback;
    return parsed.toFixed(2);
  }

  function toNullableDecimal(value: string): string | null {
    const raw = value.trim();
    if (!raw) return null;
    const parsed = Number(raw);
    if (!Number.isFinite(parsed) || parsed < 0) return null;
    return parsed.toFixed(2);
  }

  function parseApiError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      const detail = error.data["detail"];
      if (typeof detail === "string" && detail.trim().length > 0) return detail;
      const firstField = Object.values(error.fieldErrors)[0]?.[0];
      if (firstField) return firstField;
    }
    return fallback;
  }

  async function fetchAllPages<T>(endpoint: string, params: Record<string, string> = {}): Promise<T[]> {
    const rows: T[] = [];
    let nextPage = 1;

    while (nextPage > 0) {
      const payload = await api.get<PaginatedResponse<T>>(endpoint, {
        ...params,
        page: String(nextPage),
      });
      rows.push(...(payload.results ?? []));
      if (!payload.next || payload.results.length === 0) break;
      nextPage += 1;
    }

    return rows;
  }

  async function loadData() {
    loading = true;
    try {
      const [projectRows, issueRows, summaryPayload, reportRows] = await Promise.all([
        fetchAllPages<ProjectListItem>("/projects/", { ordering: "name", page_size: "200" }),
        fetchAllPages<ProjectFieldEscalation>("/projects/issues/", {
          ordering: "-issue_date",
          page_size: "200",
        }),
        api.get<ProjectFieldEscalationSummary>("/projects/issues/summary/"),
        fetchAllPages<ProjectDailySiteReport>("/projects/field-operations/reports/", {
          ordering: "-report_date",
          page_size: "200",
        }),
      ]);

      projects = projectRows;
      issues = issueRows;
      summary = {
        ...summary,
        ...summaryPayload,
      };
      siteReports = reportRows;
    } catch (error) {
      toast.error("Load failed", parseApiError(error, "Could not load issues data."));
    } finally {
      loading = false;
    }
  }

  async function uploadSupportingFiles(issueId: number): Promise<boolean> {
    for (const file of files) {
      const payload = new FormData();
      payload.append("file", file);
      payload.append("caption", file.name);
      try {
        await api.upload(`/projects/issues/${issueId}/upload-supporting-file/`, payload);
      } catch {
        return false;
      }
    }
    return true;
  }

  async function createIssue(event: Event) {
    event.preventDefault();
    const projectId = parseId(form.project);
    if (!projectId) {
      toast.error("Project required", "Select a project before logging an issue.");
      return;
    }

    if (!form.title.trim()) {
      toast.error("Title required", "Enter an issue title.");
      return;
    }

    saving = true;
    try {
      const created = await api.post<ProjectFieldEscalation>("/projects/issues/", {
        project: projectId,
        source_report: parseId(form.source_report),
        issue_date: form.issue_date || today,
        issue_category: form.issue_category,
        issue_type: form.issue_type,
        title: form.title.trim(),
        description: form.description.trim(),
        location: form.location.trim(),
        weather_condition: form.weather_condition,
        weather_delay_hours: toDecimal(form.weather_delay_hours),
        estimated_schedule_impact_days: toNullableDecimal(form.estimated_schedule_impact_days),
        estimated_cost_impact: toNullableDecimal(form.estimated_cost_impact),
        impact_summary: form.impact_summary.trim(),
        root_cause: form.root_cause.trim(),
        immediate_action: form.immediate_action.trim(),
        severity: form.severity,
        status: form.status,
        owner_name: form.owner_name.trim(),
        due_date: form.due_date || null,
        resolution_notes: form.resolution_notes.trim(),
      });

      if (files.length > 0) {
        const uploaded = await uploadSupportingFiles(created.id);
        if (!uploaded) {
          toast.error("Files not uploaded", "Issue was saved, but one or more files failed to upload.");
        }
      }

      toast.success("Issue created", "Project issue has been logged.");
      showForm = false;
      resetForm();
      await loadData();
    } catch (error) {
      toast.error("Save failed", parseApiError(error, "Could not save issue."));
    } finally {
      saving = false;
    }
  }

  function onFilesSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    files = Array.from(input.files ?? []);
  }

  const reportsForProject = $derived.by(() => {
    if (!form.project) return [];
    return siteReports
      .filter((row) => String(row.project) === form.project)
      .sort((a, b) => b.report_date.localeCompare(a.report_date));
  });

  const issueTypeOptionsForCategory = $derived.by(() => {
    return ISSUE_TYPE_OPTIONS.filter(
      (option) => option.category === form.issue_category || option.value === "other",
    );
  });

  $effect(() => {
    const isValid = issueTypeOptionsForCategory.some((option) => option.value === form.issue_type);
    if (!isValid) {
      form.issue_type = issueTypeOptionsForCategory[0]?.value ?? "other";
    }
  });

  const filteredRows = $derived.by(() => {
    let rows = issues.filter((row) => {
      if (filterProject && String(row.project) !== filterProject) return false;
      if (filterStatus && row.status !== filterStatus) return false;
      if (filterSeverity && row.severity !== filterSeverity) return false;
      if (filterCategory && row.issue_category !== filterCategory) return false;
      if (filterType && row.issue_type !== filterType) return false;
      if (!search.trim()) return true;
      const needle = search.trim().toLowerCase();
      const haystack = `${row.project_name} ${row.title} ${row.description} ${row.owner_name} ${row.location}`.toLowerCase();
      return haystack.includes(needle);
    });

    rows = [...rows].sort((a, b) => {
      if (sort === "date_asc") return a.issue_date.localeCompare(b.issue_date);
      if (sort === "severity_desc") return b.severity.localeCompare(a.severity);
      if (sort === "weather_delay_desc") {
        return Number(b.weather_delay_hours || 0) - Number(a.weather_delay_hours || 0);
      }
      return b.issue_date.localeCompare(a.issue_date);
    });

    return rows;
  });

  const totalPages = $derived(Math.max(1, Math.ceil(filteredRows.length / pageSize)));

  $effect(() => {
    if (page > totalPages) page = totalPages;
    if (page < 1) page = 1;
  });

  const start = $derived(filteredRows.length === 0 ? 0 : (page - 1) * pageSize + 1);
  const end = $derived(Math.min(filteredRows.length, page * pageSize));
  const pageRows = $derived(filteredRows.slice(start - 1, end));

  $effect(() => {
    void pageRows;
    if (expandedIssueRowId !== null && !pageRows.some((row) => row.id === expandedIssueRowId)) {
      expandedIssueRowId = null;
    }
  });

  function badgeClass(status: string): string {
    switch (status) {
      case "open":
        return "border-blue-200 bg-blue-50 text-blue-700";
      case "acknowledged":
        return "border-violet-200 bg-violet-50 text-violet-700";
      case "in_progress":
        return "border-amber-200 bg-amber-50 text-amber-700";
      case "resolved":
        return "border-emerald-200 bg-emerald-50 text-emerald-700";
      case "closed":
        return "border-neutral-200 bg-neutral-100 text-neutral-600";
      default:
        return "border-neutral-200 bg-neutral-50 text-neutral-600";
    }
  }

  function severityClass(severity: string): string {
    switch (severity) {
      case "escalation":
        return "text-red-700";
      case "action_required":
        return "text-orange-700";
      case "review":
        return "text-amber-700";
      default:
        return "text-neutral-700";
    }
  }

  function fmtDate(value: string | null | undefined): string {
    if (!value) return "--";
    return new Date(`${value}T00:00:00`).toLocaleDateString();
  }

  function labelize(value: string): string {
    return value.replaceAll("_", " ").replace(/\b\w/g, (ch) => ch.toUpperCase());
  }

  function toggleIssueRow(rowId: number) {
    expandedIssueRowId = expandedIssueRowId === rowId ? null : rowId;
  }

  onMount(() => {
    loadData();
  });
</script>

<svelte:head>
  <title>Projects | Issues</title>
</svelte:head>

<div class="space-y-5">
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-violet-600">Projects</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-900">Issues</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Log weather delays, incidents, and execution issues across projects using a structured taxonomy.
      </p>
    </div>
    <button
      onclick={() => {
        resetForm();
        showForm = true;
      }}
      class="rounded-lg bg-neutral-900 px-3.5 py-2 text-sm font-medium text-white hover:bg-neutral-800"
    >
      + New Issue
    </button>
  </div>

  <section class="rounded-2xl border border-neutral-200 bg-white px-5 py-4 shadow-sm">
    <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
      <div class="rounded-xl border border-blue-100 bg-blue-50 p-3">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-blue-700">Total Issues</p>
        <p class="mt-1 text-2xl font-bold text-blue-900 tabular-nums">{summary.total}</p>
      </div>
      <div class="rounded-xl border border-violet-100 bg-violet-50 p-3">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-violet-700">Open</p>
        <p class="mt-1 text-2xl font-bold text-violet-900 tabular-nums">{summary.open}</p>
      </div>
      <div class="rounded-xl border border-rose-100 bg-rose-50 p-3">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-rose-700">Critical</p>
        <p class="mt-1 text-2xl font-bold text-rose-900 tabular-nums">{summary.critical}</p>
      </div>
      <div class="rounded-xl border border-amber-100 bg-amber-50 p-3">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-amber-700">Overdue</p>
        <p class="mt-1 text-2xl font-bold text-amber-900 tabular-nums">{summary.overdue}</p>
      </div>
      <div class="rounded-xl border border-cyan-100 bg-cyan-50 p-3">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-cyan-700">Weather Issues</p>
        <p class="mt-1 text-2xl font-bold text-cyan-900 tabular-nums">{summary.weather_issues ?? 0}</p>
      </div>
      <div class="rounded-xl border border-orange-100 bg-orange-50 p-3">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-orange-700">Delay Hours</p>
        <p class="mt-1 text-2xl font-bold text-orange-900 tabular-nums">{summary.weather_delay_hours_total ?? "0.00"}</p>
      </div>
    </div>
  </section>

  <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-sm">
    <div class="border-b border-neutral-200 px-4 py-4">
      <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
        <input
          type="text"
          bind:value={search}
          placeholder="Search title, project, owner, location"
          class="xl:col-span-2 rounded-lg border border-neutral-200 px-3 py-2 text-sm"
        />
        <select bind:value={filterProject} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          <option value="">All Projects</option>
          {#each projects as project}
            <option value={String(project.id)}>{project.name}</option>
          {/each}
        </select>
        <select bind:value={filterCategory} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          <option value="">All Categories</option>
          {#each ISSUE_CATEGORY_OPTIONS as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
        <select bind:value={filterType} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          <option value="">All Issue Types</option>
          {#each ISSUE_TYPE_OPTIONS as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
        <div class="grid grid-cols-3 gap-2">
          <select bind:value={filterStatus} class="rounded-lg border border-neutral-200 bg-white px-2 py-2 text-sm">
            <option value="">Status</option>
            {#each STATUS_OPTIONS as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
          <select bind:value={filterSeverity} class="rounded-lg border border-neutral-200 bg-white px-2 py-2 text-sm">
            <option value="">Severity</option>
            {#each SEVERITY_OPTIONS as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
          <select bind:value={sort} class="rounded-lg border border-neutral-200 bg-white px-2 py-2 text-sm">
            <option value="date_desc">Newest</option>
            <option value="date_asc">Oldest</option>
            <option value="severity_desc">Severity</option>
            <option value="weather_delay_desc">Delay Hours</option>
          </select>
        </div>
      </div>
    </div>

    {#if loading}
      <div class="flex items-center justify-center py-12">
        <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
      </div>
    {:else if filteredRows.length === 0}
      <div class="px-6 py-12 text-center text-sm text-neutral-500">No issues match the current filters.</div>
    {:else}
      <div class="overflow-x-auto">
        <table class="min-w-[860px] w-full text-sm">
          <thead class="border-b border-neutral-100 bg-neutral-50">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Date</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Project</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Issue</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Severity</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Status</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Details</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each pageRows as row (row.id)}
              <tr class="hover:bg-neutral-50">
                <td class="px-4 py-3 text-neutral-600">{fmtDate(row.issue_date)}</td>
                <td class="px-4 py-3 text-neutral-900">{row.project_name}</td>
                <td class="px-4 py-3 text-neutral-700">
                  <p class="font-medium text-neutral-900">{row.title}</p>
                  {#if row.location}
                    <p class="text-xs text-neutral-500">{row.location}</p>
                  {/if}
                </td>
                <td class={`px-4 py-3 font-medium ${severityClass(row.severity)}`}>{labelize(row.severity)}</td>
                <td class="px-4 py-3">
                  <span class={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${badgeClass(row.status)}`}>
                    {labelize(row.status)}
                  </span>
                </td>
                <td class="px-4 py-3 text-right">
                  <button
                    type="button"
                    onclick={() => toggleIssueRow(row.id)}
                    aria-expanded={expandedIssueRowId === row.id}
                    aria-label={expandedIssueRowId === row.id ? "Collapse row details" : "Expand row details"}
                    class="inline-flex items-center text-xs font-semibold text-neutral-700 hover:text-neutral-900"
                  >
                    <span class={`transition-transform ${expandedIssueRowId === row.id ? "rotate-180" : ""}`}>▾</span>
                  </button>
                </td>
              </tr>
              {#if expandedIssueRowId === row.id}
                <tr class="bg-neutral-50/70">
                  <td colspan="6" class="px-4 pb-4 pt-0">
                    <div class="grid gap-3 pt-3 md:grid-cols-3">
                      <div class="rounded-lg border border-neutral-200 bg-white p-3">
                        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Category / Type</p>
                        <p class="mt-1 text-sm font-medium text-neutral-900">{labelize(row.issue_category)}</p>
                        <p class="mt-1 text-xs text-neutral-600">{labelize(row.issue_type)}</p>
                      </div>
                      <div class="rounded-lg border border-neutral-200 bg-white p-3">
                        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Owner</p>
                        <p class="mt-1 text-sm font-medium text-neutral-900">{row.owner_name || "--"}</p>
                      </div>
                      <div class="rounded-lg border border-neutral-200 bg-white p-3">
                        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Delay / Due</p>
                        <p class="mt-1 text-sm font-medium tabular-nums text-neutral-900">{row.weather_delay_hours} hrs</p>
                        <p class="mt-1 text-xs text-neutral-600">Due: {fmtDate(row.due_date)}</p>
                        {#if row.is_overdue}
                          <p class="mt-1 text-xs font-semibold text-rose-600">Overdue</p>
                        {/if}
                      </div>
                      <div class="rounded-lg border border-neutral-200 bg-white p-3 md:col-span-3">
                        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Context</p>
                        <div class="mt-2 grid gap-2 text-xs md:grid-cols-2">
                          <p><span class="font-semibold text-neutral-700">Location:</span> {row.location || "--"}</p>
                          <p><span class="font-semibold text-neutral-700">Weather:</span> {row.weather_condition ? labelize(row.weather_condition) : "--"}</p>
                          <p><span class="font-semibold text-neutral-700">Issue Date:</span> {fmtDate(row.issue_date)}</p>
                          <p><span class="font-semibold text-neutral-700">Source Report:</span> {fmtDate(row.source_report_date)}</p>
                          <p><span class="font-semibold text-neutral-700">Schedule Impact:</span> {row.estimated_schedule_impact_days ? `${row.estimated_schedule_impact_days} day(s)` : "--"}</p>
                          <p><span class="font-semibold text-neutral-700">Cost Impact:</span> {row.estimated_cost_impact || "--"}</p>
                        </div>
                      </div>
                      <div class="rounded-lg border border-neutral-200 bg-white p-3 md:col-span-3">
                        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Notes</p>
                        <div class="mt-2 grid gap-2 text-xs md:grid-cols-2">
                          <p><span class="font-semibold text-neutral-700">Description:</span> {row.description || "--"}</p>
                          <p><span class="font-semibold text-neutral-700">Impact Summary:</span> {row.impact_summary || "--"}</p>
                          <p><span class="font-semibold text-neutral-700">Root Cause:</span> {row.root_cause || "--"}</p>
                          <p><span class="font-semibold text-neutral-700">Immediate Action:</span> {row.immediate_action || "--"}</p>
                          <p class="md:col-span-2"><span class="font-semibold text-neutral-700">Resolution Notes:</span> {row.resolution_notes || "--"}</p>
                        </div>
                      </div>
                      <div class="rounded-lg border border-neutral-200 bg-white p-3 md:col-span-3">
                        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Actions</p>
                        <button onclick={() => goto(`/projects/${row.project}`)} class="mt-1 text-xs font-medium text-neutral-700 hover:text-neutral-900 hover:underline">
                          Open
                        </button>
                      </div>
                    </div>
                  </td>
                </tr>
              {/if}
            {/each}
          </tbody>
        </table>
      </div>
      <div class="flex items-center justify-between border-t border-neutral-100 px-4 py-3">
        <div class="flex items-center gap-3">
          <p class="text-xs text-neutral-500">Showing {start}-{end} of {filteredRows.length}</p>
          <select bind:value={pageSize} class="rounded-md border border-neutral-200 bg-white px-2 py-1 text-xs text-neutral-600">
            <option value={10}>10 / page</option>
            <option value={20}>20 / page</option>
            <option value={50}>50 / page</option>
          </select>
        </div>
        <div class="flex items-center gap-2">
          <button
            onclick={() => (page = Math.max(1, page - 1))}
            disabled={page === 1}
            class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 disabled:opacity-40"
          >
            Previous
          </button>
          <span class="text-xs text-neutral-600">Page {page} of {totalPages}</span>
          <button
            onclick={() => (page = Math.min(totalPages, page + 1))}
            disabled={page === totalPages}
            class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 disabled:opacity-40"
          >
            Next
          </button>
        </div>
      </div>
    {/if}
  </section>
</div>

<!-- New Issue Drawer -->
{#if showForm}
  <button class="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm" onclick={() => (showForm = false)} aria-label="Close drawer"></button>
  <aside class="fixed inset-y-0 right-0 z-50 flex w-full max-w-xl flex-col bg-white shadow-2xl border-l border-neutral-200">
    <div class="flex items-center justify-between border-b border-neutral-100 px-6 py-4">
      <h2 class="text-base font-semibold text-neutral-900">New Issue</h2>
      <button onclick={() => (showForm = false)} class="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-900 transition-colors" aria-label="Close">
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <form onsubmit={createIssue} class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
      <div class="grid grid-cols-2 gap-3">
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block text-xs">Project</span>
          <select bind:value={form.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
            <option value="">Select project</option>
            {#each projects as project}
              <option value={String(project.id)}>{project.name}</option>
            {/each}
          </select>
        </label>
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block text-xs">Source Report</span>
          <select bind:value={form.source_report} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
            <option value="">No source report</option>
            {#each reportsForProject as report}
              <option value={String(report.id)}>{report.report_date} - {labelize(report.shift)}</option>
            {/each}
          </select>
        </label>
      </div>

      <div class="grid grid-cols-3 gap-3">
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block text-xs">Issue Date</span>
          <DateInput bind:value={form.issue_date} />
        </label>
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block text-xs">Category</span>
          <select bind:value={form.issue_category} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
            {#each ISSUE_CATEGORY_OPTIONS as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </label>
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block text-xs">Type</span>
          <select bind:value={form.issue_type} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
            {#each issueTypeOptionsForCategory as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </label>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block text-xs">Title</span>
          <input type="text" bind:value={form.title} placeholder="Issue title" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        </label>
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block text-xs">Location</span>
          <input type="text" bind:value={form.location} placeholder="Location / zone" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        </label>
      </div>

      <label class="block text-sm font-medium text-neutral-700">
        <span class="mb-1.5 block text-xs">Description</span>
        <textarea bind:value={form.description} rows="3" placeholder="Issue description" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
      </label>

      <div class="grid grid-cols-3 gap-3">
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block text-xs">Weather</span>
          <select bind:value={form.weather_condition} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
            {#each WEATHER_OPTIONS as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </label>
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block text-xs">Weather Delay (hrs)</span>
          <input type="number" min="0" step="0.25" bind:value={form.weather_delay_hours} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        </label>
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block text-xs">Schedule Impact (days)</span>
          <input type="number" min="0" step="0.25" bind:value={form.estimated_schedule_impact_days} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        </label>
      </div>

      <div class="grid grid-cols-3 gap-3">
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block text-xs">Cost Impact (₦)</span>
          <input type="number" min="0" step="0.01" bind:value={form.estimated_cost_impact} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        </label>
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block text-xs">Severity</span>
          <select bind:value={form.severity} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
            {#each SEVERITY_OPTIONS as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </label>
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block text-xs">Status</span>
          <select bind:value={form.status} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
            {#each STATUS_OPTIONS as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </label>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block text-xs">Owner</span>
          <input type="text" bind:value={form.owner_name} placeholder="Owner" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        </label>
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block text-xs">Due Date</span>
          <DateInput bind:value={form.due_date} />
        </label>
      </div>

      <label class="block text-sm font-medium text-neutral-700">
        <span class="mb-1.5 block text-xs">Impact Summary</span>
        <textarea bind:value={form.impact_summary} rows="2" placeholder="Impact summary" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
      </label>

      <label class="block text-sm font-medium text-neutral-700">
        <span class="mb-1.5 block text-xs">Root Cause</span>
        <textarea bind:value={form.root_cause} rows="2" placeholder="Root cause analysis" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
      </label>

      <label class="block text-sm font-medium text-neutral-700">
        <span class="mb-1.5 block text-xs">Immediate Action</span>
        <textarea bind:value={form.immediate_action} rows="2" placeholder="Immediate action taken" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
      </label>

      <label class="block text-sm font-medium text-neutral-700">
        <span class="mb-1.5 block text-xs">Resolution Notes</span>
        <textarea bind:value={form.resolution_notes} rows="2" placeholder="Resolution notes" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
      </label>

      <label class="flex min-h-10 cursor-pointer items-center rounded-lg border border-dashed border-neutral-300 bg-neutral-50 px-3 py-3 text-xs text-neutral-600">
        <input type="file" multiple class="hidden" onchange={onFilesSelected} />
        <span>{files.length > 0 ? `${files.length} file(s) selected` : "Attach supporting files"}</span>
      </label>
    </form>

    <div class="flex items-center justify-end gap-3 border-t border-neutral-100 px-6 py-4">
      {#if isDev}
        <button type="button" onclick={devFillIssue} class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>
      {/if}
      <button type="button" onclick={() => (showForm = false)} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      <button type="button" onclick={createIssue} disabled={saving} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50">
        {saving ? "Saving..." : "Save Issue"}
      </button>
    </div>
  </aside>
{/if}

<script lang="ts">
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import type {
    PaginatedResponse,
    ProjectDeliveryConfirmation,
    ProjectDeliveryConfirmationSummary,
    ProjectDailySiteReport,
    ProjectExecutionInspection,
    ProjectExecutionInspectionSummary,
    ProjectFieldEscalation,
    ProjectFieldEscalationSummary,
    ProjectListItem,
    ProjectWorkforceLog,
    ProjectWorkforceSetupOptions,
    ProjectWorkforceSetupEmployee,
    ProjectWorkforceSetupContractor,
    ProjectWorkforceSetupTask,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  const SHIFT_OPTIONS = [
    { value: "day", label: "Day" },
    { value: "night", label: "Night" },
    { value: "full_day", label: "Full Day" },
  ] as const;

  const ATTENDANCE_OPTIONS = [
    { value: "present", label: "Present" },
    { value: "absent", label: "Absent" },
    { value: "late", label: "Late" },
    { value: "half_day", label: "Half Day" },
    { value: "excused", label: "Excused" },
  ] as const;

  const WEATHER_OPTIONS = [
    { value: "clear", label: "Clear" },
    { value: "cloudy", label: "Cloudy" },
    { value: "rain", label: "Rain" },
    { value: "storm", label: "Storm" },
    { value: "windy", label: "Windy" },
    { value: "other", label: "Other" },
  ] as const;

  const REPORT_STATUS_OPTIONS = [
    { value: "draft", label: "Draft" },
    { value: "submitted", label: "Submitted" },
    { value: "reviewed", label: "Reviewed" },
    { value: "closed", label: "Closed" },
  ] as const;

  const DELIVERY_STATUS_OPTIONS = [
    { value: "pending", label: "Pending" },
    { value: "inspected", label: "Inspected" },
    { value: "accepted", label: "Accepted" },
    { value: "partially_accepted", label: "Partially Accepted" },
    { value: "rejected", label: "Rejected" },
  ] as const;

  const ESCALATION_SEVERITY_OPTIONS = [
    { value: "info", label: "Info" },
    { value: "review", label: "Review" },
    { value: "action_required", label: "Action Required" },
    { value: "escalation", label: "Escalation" },
  ] as const;

  const ESCALATION_STATUS_OPTIONS = [
    { value: "open", label: "Open" },
    { value: "acknowledged", label: "Acknowledged" },
    { value: "in_progress", label: "In Progress" },
    { value: "resolved", label: "Resolved" },
    { value: "closed", label: "Closed" },
  ] as const;

  const INSPECTION_TYPE_OPTIONS = [
    { value: "material_receipt", label: "Material Receipt" },
    { value: "workmanship", label: "Workmanship" },
    { value: "mep", label: "MEP Installation" },
    { value: "finishes", label: "Finishes" },
    { value: "safety_quality", label: "Safety & Quality" },
    { value: "pre_handover", label: "Pre-Handover" },
    { value: "other", label: "Other" },
  ] as const;

  const INSPECTION_STATUS_OPTIONS = [
    { value: "planned", label: "Planned" },
    { value: "in_progress", label: "In Progress" },
    { value: "passed", label: "Passed" },
    { value: "failed", label: "Failed" },
    { value: "blocked", label: "Blocked" },
    { value: "closed", label: "Closed" },
  ] as const;

  const CHECKLIST_RESULT_OPTIONS = [
    { value: "pass", label: "Pass" },
    { value: "fail", label: "Fail" },
    { value: "hold", label: "Hold" },
    { value: "na", label: "N/A" },
  ] as const;

  const today = new Date().toISOString().slice(0, 10);
  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);
  const severityRank: Record<string, number> = {
    info: 1,
    review: 2,
    action_required: 3,
    escalation: 4,
  };

  let loading = $state(true);
  let saving = $state(false);

  // Project detail modal (instead of redirect)
  let showProjectModal = $state(false);
  let projectModalData = $state<{ id: number; name: string; status: string; start_date: string | null; target_end_date: string | null; budget: string | null; description: string } | null>(null);
  let projectModalLoading = $state(false);

  async function openProjectModal(projectId: number) {
    showProjectModal = true;
    projectModalLoading = true;
    try {
      const p = await api.get<any>(`/projects/${projectId}/`);
      projectModalData = {
        id: p.id,
        name: p.name,
        status: p.status,
        start_date: p.start_date,
        target_end_date: p.target_end_date,
        budget: p.budget,
        description: p.description || "",
      };
    } catch { toast.error("Load failed", "Could not load project details."); }
    finally { projectModalLoading = false; }
  }

  let projects = $state<ProjectListItem[]>([]);
  let workforceLogs = $state<ProjectWorkforceLog[]>([]);
  let workforceEmployees = $state<ProjectWorkforceSetupEmployee[]>([]);
  let workforceContractors = $state<ProjectWorkforceSetupContractor[]>([]);
  let workforceTasks = $state<ProjectWorkforceSetupTask[]>([]);
  let siteReports = $state<ProjectDailySiteReport[]>([]);
  let deliveryConfirmations = $state<ProjectDeliveryConfirmation[]>([]);
  let qualityInspections = $state<ProjectExecutionInspection[]>([]);
  let escalations = $state<ProjectFieldEscalation[]>([]);
  let deliverySummary = $state<ProjectDeliveryConfirmationSummary>({
    total: 0,
    on_time: 0,
    late: 0,
    pending_inspection: 0,
    partial_acceptance: 0,
    rejected: 0,
    accepted: 0,
    open_late_delivery_escalations: 0,
  });
  let inspectionSummary = $state<ProjectExecutionInspectionSummary>({
    total: 0,
    open: 0,
    failed: 0,
    due_actions: 0,
  });
  let escalationSummary = $state<ProjectFieldEscalationSummary>({
    total: 0,
    open: 0,
    critical: 0,
    overdue: 0,
  });

  let projectFilter = $state("");

  let showWorkforceForm = $state(false);
  let showReportForm = $state(false);
  let showInspectionForm = $state(false);
  let showEscalationForm = $state(false);
  let workforceSupportingFiles = $state<File[]>([]);
  let inspectionSupportingFiles = $state<File[]>([]);
  let escalationSupportingFiles = $state<File[]>([]);

  let workforceForm = $state({
    project: "",
    worker_id: "",
    employee: "",
    trade: "",
    contractor: "",
    report_date: today,
    daily_attendance: "present",
    shift: "day",
    task_assigned: "",
    productivity: "",
    overtime_hours: "0",
    laborers_count: "0",
    skilled_count: "0",
    supervisors_count: "0",
    subcontractors_count: "0",
    equipment_operators_count: "0",
    notes: "",
  });

  let reportForm = $state({
    project: "",
    report_date: today,
    shift: "day",
    weather: "clear",
    weather_notes: "",
    weather_delay_hours: "0",
    progress_percent: "0",
    laborers_count: "0",
    skilled_count: "0",
    supervisors_count: "0",
    subcontractors_count: "0",
    equipment_operators_count: "0",
    workforce_summary: "",
    work_completed: "",
    planned_next_day: "",
    equipment_used: "",
    materials_delivered: "",
    materials_consumed: "",
    material_updates: "",
    visitors_log: "",
    instructions_issued: "",
    safety_observations: "",
    quality_observations: "",
    incidents: "",
    blockers: "",
    status: "draft",
    escalation_required: false,
  });
  let reportPhotoFiles = $state<File[]>([]);

  let inspectionForm = $state({
    project: "",
    phase: "",
    source_report: "",
    inspection_type: "workmanship",
    status: "planned",
    inspected_on: today,
    shift: "day",
    work_package: "",
    location: "",
    inspector_name: "",
    inspector_role: "",
    overall_score: "",
    critical_findings: "0",
    major_findings: "0",
    minor_findings: "0",
    observations: "",
    corrective_actions: "",
    due_date: "",
  });
  let inspectionChecklistRows = $state([
    {
      checklist_group: "Civil",
      checklist_item: "",
      result: "pass",
      remarks: "",
      action_owner: "",
      action_due_date: "",
      resolved_on: "",
    },
  ]);

  let escalationForm = $state({
    project: "",
    source_report: "",
    title: "",
    description: "",
    severity: "review",
    status: "open",
    owner_name: "",
    due_date: "",
    resolution_notes: "",
  });

  // Workforce table controls
  let workforceSearch = $state("");
  let workforceShiftFilter = $state("");
  let workforceSort = $state<"date_desc" | "date_asc" | "headcount_desc" | "project_asc">("date_desc");
  let workforcePage = $state(1);
  let workforcePageSize = $state(10);
  let expandedWorkforceRowId = $state<number | null>(null);

  // Site reports table controls
  let reportsSearch = $state("");
  let reportsStatusFilter = $state("");
  let reportsWeatherFilter = $state("");
  let reportsSort = $state<"date_desc" | "date_asc" | "progress_desc" | "progress_asc">("date_desc");
  let reportsPage = $state(1);
  let reportsPageSize = $state(10);
  let expandedReportRowId = $state<number | null>(null);

  // Delivery confirmations table controls
  let deliveriesSearch = $state("");
  let deliveriesStatusFilter = $state("");
  let deliveriesLateFilter = $state<"" | "late" | "on_time">("");
  let deliveriesSort = $state<"date_desc" | "date_asc" | "delay_desc" | "project_asc">("date_desc");
  let deliveriesPage = $state(1);
  let deliveriesPageSize = $state(10);

  // Quality inspections table controls
  let inspectionsSearch = $state("");
  let inspectionsStatusFilter = $state("");
  let inspectionsTypeFilter = $state("");
  let inspectionsSort = $state<"date_desc" | "date_asc" | "status_asc" | "score_desc">("date_desc");
  let inspectionsPage = $state(1);
  let inspectionsPageSize = $state(10);

  // Escalations table controls
  let escalationsSearch = $state("");
  let escalationsStatusFilter = $state("");
  let escalationsSeverityFilter = $state("");
  let escalationsSort = $state<"created_desc" | "created_asc" | "due_asc" | "severity_desc">("created_desc");
  let escalationsPage = $state(1);
  let escalationsPageSize = $state(10);
  let expandedEscalationRowId = $state<number | null>(null);

  function fmtDate(value: string | null | undefined): string {
    if (!value) return "--";
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return "--";
    return parsed.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  function dateKey(value: string | null | undefined): number {
    if (!value) return 0;
    const parsed = new Date(value).getTime();
    return Number.isNaN(parsed) ? 0 : parsed;
  }

  function decimalKey(value: string | number | null | undefined): number {
    if (typeof value === "number") return Number.isFinite(value) ? value : 0;
    if (typeof value === "string") {
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : 0;
    }
    return 0;
  }

  function toInt(value: string): number {
    const parsed = Number.parseInt(value, 10);
    return Number.isNaN(parsed) ? 0 : Math.max(0, parsed);
  }

  function toDecimal(value: string): string {
    const parsed = Number.parseFloat(value);
    if (Number.isNaN(parsed) || parsed < 0) return "0";
    return String(parsed);
  }

  function toNullableDecimal(value: string): string | null {
    const trimmed = value.trim();
    if (!trimmed) return null;
    const parsed = Number.parseFloat(trimmed);
    if (Number.isNaN(parsed) || parsed < 0) return null;
    return String(parsed);
  }

  function parseProjectId(value: string): number | null {
    const parsed = Number.parseInt(value, 10);
    return Number.isNaN(parsed) ? null : parsed;
  }

  function parseApiError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      if (typeof error.data?.detail === "string") return error.data.detail;
      const firstField = Object.values(error.fieldErrors)[0]?.[0];
      if (firstField) return firstField;
      if (error.status === 403) return "You do not have permission for this action.";
    }
    return fallback;
  }

  async function fetchAllPages<T>(
    endpoint: string,
    params: Record<string, string> = {},
    maxPages = 50,
  ): Promise<T[]> {
    const rows: T[] = [];
    let page = 1;

    while (page <= maxPages) {
      const payload = await api.get<PaginatedResponse<T> | T[]>(endpoint, {
        ...params,
        page: String(page),
      });
      if (Array.isArray(payload)) {
        rows.push(...payload);
        break;
      }
      rows.push(...(payload.results ?? []));
      if (!payload.next || payload.results.length === 0) break;
      page += 1;
    }

    return rows;
  }

  async function loadFieldOpsData() {
    loading = true;
    try {
      const [
        projectRows,
        workforceRows,
        workforceSetupOptions,
        reportRows,
        deliveryRows,
        inspectionRows,
        escalationRows,
        deliverySummaryPayload,
        inspectionSummaryPayload,
        escalationSummaryPayload,
      ] = await Promise.all([
        fetchAllPages<ProjectListItem>("/projects/", {
          ordering: "name",
          page_size: "200",
        }),
        fetchAllPages<ProjectWorkforceLog>("/projects/field-operations/workforce/", {
          ordering: "-report_date",
          page_size: "200",
        }),
        api.get<ProjectWorkforceSetupOptions>("/projects/field-operations/workforce/setup-options/"),
        fetchAllPages<ProjectDailySiteReport>("/projects/field-operations/reports/", {
          ordering: "-report_date",
          page_size: "200",
        }),
        fetchAllPages<ProjectDeliveryConfirmation>("/projects/field-operations/deliveries/", {
          ordering: "-received_date",
          page_size: "200",
        }),
        fetchAllPages<ProjectExecutionInspection>("/projects/field-operations/quality-inspections/", {
          ordering: "-inspected_on",
          page_size: "200",
        }),
        fetchAllPages<ProjectFieldEscalation>("/projects/field-operations/escalations/", {
          ordering: "-created_at",
          page_size: "200",
        }),
        api.get<ProjectDeliveryConfirmationSummary>("/projects/field-operations/deliveries/summary/"),
        api.get<ProjectExecutionInspectionSummary>("/projects/field-operations/quality-inspections/summary/"),
        api.get<ProjectFieldEscalationSummary>("/projects/field-operations/escalations/summary/"),
      ]);

      projects = projectRows;
      workforceLogs = workforceRows;
      workforceEmployees = workforceSetupOptions.employees ?? [];
      workforceContractors = workforceSetupOptions.contractors ?? [];
      workforceTasks = workforceSetupOptions.tasks ?? [];
      siteReports = reportRows;
      deliveryConfirmations = deliveryRows;
      qualityInspections = inspectionRows;
      escalations = escalationRows;
      deliverySummary = deliverySummaryPayload;
      inspectionSummary = inspectionSummaryPayload;
      escalationSummary = escalationSummaryPayload;
    } catch (error) {
      toast.error("Load failed", parseApiError(error, "Could not load field operations data."));
    } finally {
      loading = false;
    }
  }

  function resetWorkforceForm() {
    workforceForm = {
      project: projectFilter || "",
      worker_id: "",
      employee: "",
      trade: "",
      contractor: "",
      report_date: today,
      daily_attendance: "present",
      shift: "day",
      task_assigned: "",
      productivity: "",
      overtime_hours: "0",
      laborers_count: "0",
      skilled_count: "0",
      supervisors_count: "0",
      subcontractors_count: "0",
      equipment_operators_count: "0",
      notes: "",
    };
    workforceSupportingFiles = [];
  }

  function resetReportForm() {
    reportForm = {
      project: projectFilter || "",
      report_date: today,
      shift: "day",
      weather: "clear",
      weather_notes: "",
      weather_delay_hours: "0",
      progress_percent: "0",
      laborers_count: "0",
      skilled_count: "0",
      supervisors_count: "0",
      subcontractors_count: "0",
      equipment_operators_count: "0",
      workforce_summary: "",
      work_completed: "",
      planned_next_day: "",
      equipment_used: "",
      materials_delivered: "",
      materials_consumed: "",
      material_updates: "",
      visitors_log: "",
      instructions_issued: "",
      safety_observations: "",
      quality_observations: "",
      incidents: "",
      blockers: "",
      status: "draft",
      escalation_required: false,
    };
    reportPhotoFiles = [];
  }

  function resetInspectionForm() {
    inspectionForm = {
      project: projectFilter || "",
      phase: "",
      source_report: "",
      inspection_type: "workmanship",
      status: "planned",
      inspected_on: today,
      shift: "day",
      work_package: "",
      location: "",
      inspector_name: "",
      inspector_role: "",
      overall_score: "",
      critical_findings: "0",
      major_findings: "0",
      minor_findings: "0",
      observations: "",
      corrective_actions: "",
      due_date: "",
    };
    inspectionChecklistRows = [
      {
        checklist_group: "Civil",
        checklist_item: "",
        result: "pass",
        remarks: "",
        action_owner: "",
        action_due_date: "",
        resolved_on: "",
      },
    ];
    inspectionSupportingFiles = [];
  }

  function resetEscalationForm() {
    escalationForm = {
      project: projectFilter || "",
      source_report: "",
      title: "",
      description: "",
      severity: "review",
      status: "open",
      owner_name: "",
      due_date: "",
      resolution_notes: "",
    };
    escalationSupportingFiles = [];
  }

  const INSPECTION_SAMPLES = [
    { work_package: "Concrete Works", location: "Block A – Ground Floor Slab", inspector_name: "Ahmed Khan", inspector_role: "QA Engineer", observations: "Concrete finish acceptable. Minor honeycombing observed on column C4 base – non-structural. Vibration records reviewed and satisfactory.", corrective_actions: "Patch and grout column C4 base. Re-inspect in 48 hours.", overall_score: "78", critical_findings: "0", major_findings: "1", minor_findings: "2" },
    { work_package: "Structural Steel", location: "Block B – Level 2 Frame", inspector_name: "Sarah Mills", inspector_role: "Structural Inspector", observations: "Beam-to-column connections checked – torque values within spec. Minor paint damage on 3 connection plates from erection.", corrective_actions: "Touch-up paint on damaged connection plates within 7 days.", overall_score: "92", critical_findings: "0", major_findings: "0", minor_findings: "3" },
    { work_package: "Waterproofing", location: "Basement Level -1", inspector_name: "James Osei", inspector_role: "Envelope Specialist", observations: "Membrane lapped correctly with 150mm overlap. One area near lift pit shows insufficient adhesion – 2m² affected.", corrective_actions: "Strip and re-apply membrane in affected area. Flood test before backfill.", overall_score: "65", critical_findings: "1", major_findings: "0", minor_findings: "1" },
  ];
  let inspectionSampleIdx = 0;

  function devFillInspection() {
    const proj = projects.length > 0 ? String(projects[0].id) : "";
    const sample = INSPECTION_SAMPLES[inspectionSampleIdx % INSPECTION_SAMPLES.length];
    inspectionSampleIdx++;
    const due = new Date(); due.setDate(due.getDate() + 7);
    inspectionForm = {
      ...inspectionForm,
      project: proj,
      inspection_type: ["workmanship", "safety_quality", "material_receipt", "mep"][inspectionSampleIdx % 4] as any,
      status: "in_progress",
      inspected_on: today,
      shift: "day",
      work_package: sample.work_package,
      location: sample.location,
      inspector_name: sample.inspector_name,
      inspector_role: sample.inspector_role,
      overall_score: sample.overall_score,
      critical_findings: sample.critical_findings,
      major_findings: sample.major_findings,
      minor_findings: sample.minor_findings,
      observations: sample.observations,
      corrective_actions: sample.corrective_actions,
      due_date: due.toISOString().slice(0, 10),
    };
    inspectionChecklistRows = [
      { checklist_group: "Civil", checklist_item: "Concrete cover to reinforcement (min 40mm)", result: "pass", remarks: "Checked with cover meter – 42mm avg", action_owner: "", action_due_date: "", resolved_on: "" },
      { checklist_group: "Civil", checklist_item: "Surface finish free from honeycombing", result: "fail", remarks: "Honeycombing at column C4 base", action_owner: sample.inspector_name, action_due_date: due.toISOString().slice(0, 10), resolved_on: "" },
      { checklist_group: "Safety", checklist_item: "Edge protection in place at open edges", result: "pass", remarks: "All barriers secure", action_owner: "", action_due_date: "", resolved_on: "" },
    ];
  }

  const WORKFORCE_SAMPLES = [
    { worker_id: "WK-1001", trade: "Masonry", attendance: "present", productivity: "86", overtime: "1.5", laborers: "18", skilled: "12", supervisors: "3", subcontractors: "8", operators: "4", notes: "Full complement on site. Concrete pour team mobilised for ground floor slab. Night shift stood down due to completed formwork ahead of schedule." },
    { worker_id: "WK-1002", trade: "Steel Fixing", attendance: "present", productivity: "91", overtime: "2.0", laborers: "22", skilled: "15", supervisors: "4", subcontractors: "10", operators: "6", notes: "Peak workforce for structural frame erection. Additional steel fixers from subcontractor mobilised. Two operators on tower crane rotation." },
    { worker_id: "WK-1003", trade: "Finishing", attendance: "late", productivity: "72", overtime: "0", laborers: "10", skilled: "8", supervisors: "2", subcontractors: "5", operators: "2", notes: "Reduced workforce – finishing phase. Painters and tilers on internal units. Electricians completing second-fix in Block A." },
  ];
  let workforceSampleIdx = 0;

  function devFillWorkforce() {
    const proj = projects.length > 0 ? String(projects[0].id) : "";
    const sample = WORKFORCE_SAMPLES[workforceSampleIdx % WORKFORCE_SAMPLES.length];
    const employee = workforceEmployees.length > 0 ? String(workforceEmployees[workforceSampleIdx % workforceEmployees.length].id) : "";
    const contractor = workforceContractors.length > 0 ? String(workforceContractors[workforceSampleIdx % workforceContractors.length].id) : "";
    const task = workforceTasks.find((row) => String(row.project) === proj) ?? workforceTasks[0];
    workforceSampleIdx++;
    workforceForm = {
      ...workforceForm,
      project: proj,
      worker_id: sample.worker_id,
      employee,
      trade: sample.trade,
      contractor,
      report_date: today,
      daily_attendance: sample.attendance as any,
      shift: ["day", "night", "full_day"][workforceSampleIdx % 3] as any,
      task_assigned: task ? String(task.id) : "",
      productivity: sample.productivity,
      overtime_hours: sample.overtime,
      laborers_count: sample.laborers,
      skilled_count: sample.skilled,
      supervisors_count: sample.supervisors,
      subcontractors_count: sample.subcontractors,
      equipment_operators_count: sample.operators,
      notes: sample.notes,
    };
  }

  const REPORT_SAMPLES = [
    {
      work_completed: "Ground floor slab poured in Zones 1-3 (240m³). Power-float finish achieved. Curing compound applied. Formwork stripped from Level 1 columns in Block B.",
      planned_next_day: "Complete slab pour Zones 4-5. Begin Level 2 column setting-out. Continue Block B beam installation.",
      workforce_summary: "42 workers on site including 6 concrete gang, 8 steel fixers, 4 carpenters.",
      laborers_count: "24",
      skilled_count: "10",
      supervisors_count: "4",
      subcontractors_count: "2",
      equipment_operators_count: "2",
      equipment_used: "1 tower crane, 2 concrete vibrators, 1 boom pump.",
      materials_delivered: "6 ready-mix concrete trucks, 1 rebar truck (2.5 tons), 120 bags of cement.",
      materials_consumed: "Concrete 240m³, cement 120 bags, rebar 2.5 tons.",
      material_updates: "Ready-mix delivery on schedule – 6 trucks dispatched. Rebar stock adequate for 5 more days. Formwork panels returned from Block A.",
      visitors_log: "Building control inspector and client representative visited the slab pour.",
      instructions_issued: "Increase curing inspection frequency to every 4 hours.",
      safety_observations: "All personnel wearing correct PPE. Banksman in position during all crane lifts. Near-miss reported: loose scaffolding board on Level 2 – secured immediately.",
      quality_observations: "Concrete slump test: 120mm (within 100-150mm spec). Cube samples taken: 6 sets for 7-day and 28-day testing.",
      incidents: "",
      blockers: "Awaiting building control inspection for foundation sign-off – scheduled for tomorrow AM.",
      weather: "clear",
      weather_notes: "",
      progress_percent: "34",
    },
    {
      work_completed: "Roof waterproofing membrane applied to Block A (Phase 1). Internal partitions erected on Level 3, Zones A-D. First-fix plumbing completed in Block B ground floor.",
      planned_next_day: "Continue roof membrane Block A Phase 2. Start Level 3 MEP rough-in. Block B plumbing pressure test.",
      workforce_summary: "38 workers on site. Roofing subcontractor team of 6 mobilised.",
      laborers_count: "18",
      skilled_count: "12",
      supervisors_count: "3",
      subcontractors_count: "3",
      equipment_operators_count: "2",
      equipment_used: "2 boom lifts, 1 scaffolding truck, 4 power cutters.",
      materials_delivered: "Waterproofing membrane 500m², partition studs 220 units, PVC pipes 300m.",
      materials_consumed: "Membrane 420m², studs 180 units, PVC pipes 210m.",
      material_updates: "Waterproofing membrane: 800m² remaining (sufficient). Partition studs running low – delivery expected Thursday.",
      visitors_log: "Fire consultant and electrical subcontractor supervisor visited for coordination walk.",
      instructions_issued: "Prioritize leak-test signoff before closing ceiling sections.",
      safety_observations: "Toolbox talk on working at height conducted. Harness checks completed for all roof workers.",
      quality_observations: "Membrane lap joints inspected – all meeting 150mm minimum. Partition plumb check passed.",
      incidents: "Minor first aid: cut finger during stud cutting – treated on site.",
      blockers: "",
      weather: "cloudy",
      weather_notes: "Overcast but dry. No impact on works.",
      progress_percent: "62",
    },
  ];
  let reportSampleIdx = 0;

  function devFillReport() {
    const proj = projects.length > 0 ? String(projects[0].id) : "";
    const sample = REPORT_SAMPLES[reportSampleIdx % REPORT_SAMPLES.length];
    reportSampleIdx++;
    reportForm = {
      ...reportForm,
      project: proj,
      report_date: today,
      shift: "day",
      weather: sample.weather,
      weather_notes: sample.weather_notes,
      weather_delay_hours: "0",
      progress_percent: sample.progress_percent,
      laborers_count: sample.laborers_count,
      skilled_count: sample.skilled_count,
      supervisors_count: sample.supervisors_count,
      subcontractors_count: sample.subcontractors_count,
      equipment_operators_count: sample.equipment_operators_count,
      workforce_summary: sample.workforce_summary,
      work_completed: sample.work_completed,
      planned_next_day: sample.planned_next_day,
      equipment_used: sample.equipment_used,
      materials_delivered: sample.materials_delivered,
      materials_consumed: sample.materials_consumed,
      material_updates: sample.material_updates,
      visitors_log: sample.visitors_log,
      instructions_issued: sample.instructions_issued,
      safety_observations: sample.safety_observations,
      quality_observations: sample.quality_observations,
      incidents: sample.incidents,
      blockers: sample.blockers,
      status: "draft",
      escalation_required: false,
    };
  }

  const ESCALATION_SAMPLES = [
    { title: "Concrete strength below specification – Block A slab", description: "7-day cube test results for Block A ground floor slab returned 18.2 MPa against a 20 MPa requirement. 28-day results pending but early indication suggests potential non-compliance with C30/37 design mix.", severity: "action_required", owner_name: "Dr. Mensah (Structural)", resolution_notes: "" },
    { title: "Subcontractor non-attendance – Electrical first-fix", description: "Electrical subcontractor failed to mobilise for third consecutive day citing labour shortage. First-fix programme now 5 days behind schedule. MEP coordinator unable to get firm commitment on return date.", severity: "escalation", owner_name: "James Osei (PM)", resolution_notes: "" },
    { title: "Unauthorised design change by site foreman", description: "Site foreman instructed bricklayers to reduce cavity width from 100mm to 75mm to accommodate pipework clash. Change not approved through RFI process. Approximately 15m² of blockwork affected.", severity: "action_required", owner_name: "Sarah Mills (QA)", resolution_notes: "" },
  ];
  let escalationSampleIdx = 0;

  function devFillEscalation() {
    const proj = projects.length > 0 ? String(projects[0].id) : "";
    const sample = ESCALATION_SAMPLES[escalationSampleIdx % ESCALATION_SAMPLES.length];
    escalationSampleIdx++;
    const due = new Date(); due.setDate(due.getDate() + 3);
    escalationForm = {
      ...escalationForm,
      project: proj,
      title: sample.title,
      description: sample.description,
      severity: sample.severity,
      status: "open",
      owner_name: sample.owner_name,
      due_date: due.toISOString().slice(0, 10),
      resolution_notes: sample.resolution_notes,
    };
  }

  function onReportPhotosSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    reportPhotoFiles = Array.from(input.files ?? []);
  }

  function onWorkforceSupportingFilesSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    workforceSupportingFiles = Array.from(input.files ?? []);
  }

  function onInspectionSupportingFilesSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    inspectionSupportingFiles = Array.from(input.files ?? []);
  }

  function onEscalationSupportingFilesSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    escalationSupportingFiles = Array.from(input.files ?? []);
  }

  function addInspectionChecklistRow() {
    inspectionChecklistRows = [
      ...inspectionChecklistRows,
      {
        checklist_group: "",
        checklist_item: "",
        result: "pass",
        remarks: "",
        action_owner: "",
        action_due_date: "",
        resolved_on: "",
      },
    ];
  }

  function removeInspectionChecklistRow(index: number) {
    if (inspectionChecklistRows.length <= 1) return;
    inspectionChecklistRows = inspectionChecklistRows.filter((_, idx) => idx !== index);
  }

  async function createWorkforceLog(event: Event) {
    event.preventDefault();
    const projectId = parseProjectId(workforceForm.project);
    if (!projectId) {
      toast.error("Project required", "Select a project before saving workforce data.");
      return;
    }

    saving = true;
    try {
      const created = await api.post<ProjectWorkforceLog>("/projects/field-operations/workforce/", {
        project: projectId,
        worker_id: workforceForm.worker_id.trim(),
        employee: parseProjectId(workforceForm.employee),
        trade: workforceForm.trade.trim(),
        contractor: parseProjectId(workforceForm.contractor),
        report_date: workforceForm.report_date || today,
        daily_attendance: workforceForm.daily_attendance,
        shift: workforceForm.shift,
        task_assigned: parseProjectId(workforceForm.task_assigned),
        productivity: toNullableDecimal(workforceForm.productivity),
        overtime_hours: toDecimal(workforceForm.overtime_hours),
        laborers_count: toInt(workforceForm.laborers_count),
        skilled_count: toInt(workforceForm.skilled_count),
        supervisors_count: toInt(workforceForm.supervisors_count),
        subcontractors_count: toInt(workforceForm.subcontractors_count),
        equipment_operators_count: toInt(workforceForm.equipment_operators_count),
        notes: workforceForm.notes.trim(),
      });
      if (workforceSupportingFiles.length > 0) {
        const uploadOk = await uploadSupportingFiles(
          `/projects/field-operations/workforce/${created.id}/upload-supporting-file/`,
          workforceSupportingFiles,
        );
        if (!uploadOk) {
          toast.error(
            "Files not uploaded",
            "Workforce log was saved, but supporting files failed to upload.",
          );
        }
      }
      toast.success("Workforce log saved", "Daily workforce entry has been recorded.");
      showWorkforceForm = false;
      resetWorkforceForm();
      await loadFieldOpsData();
    } catch (error) {
      toast.error("Save failed", parseApiError(error, "Could not save workforce log."));
    } finally {
      saving = false;
    }
  }

  async function createSiteReport(event: Event) {
    event.preventDefault();
    const projectId = parseProjectId(reportForm.project);
    if (!projectId) {
      toast.error("Project required", "Select a project before saving a site report.");
      return;
    }

    saving = true;
    try {
      const created = await api.post<ProjectDailySiteReport>("/projects/field-operations/reports/", {
        project: projectId,
        report_date: reportForm.report_date || today,
        shift: reportForm.shift,
        weather: reportForm.weather,
        weather_notes: reportForm.weather_notes.trim(),
        weather_delay_hours: toDecimal(reportForm.weather_delay_hours),
        progress_percent: toDecimal(reportForm.progress_percent),
        laborers_count: toInt(reportForm.laborers_count),
        skilled_count: toInt(reportForm.skilled_count),
        supervisors_count: toInt(reportForm.supervisors_count),
        subcontractors_count: toInt(reportForm.subcontractors_count),
        equipment_operators_count: toInt(reportForm.equipment_operators_count),
        workforce_summary: reportForm.workforce_summary.trim(),
        work_completed: reportForm.work_completed.trim(),
        planned_next_day: reportForm.planned_next_day.trim(),
        equipment_used: reportForm.equipment_used.trim(),
        materials_delivered: reportForm.materials_delivered.trim(),
        materials_consumed: reportForm.materials_consumed.trim(),
        material_updates: reportForm.material_updates.trim(),
        visitors_log: reportForm.visitors_log.trim(),
        instructions_issued: reportForm.instructions_issued.trim(),
        safety_observations: reportForm.safety_observations.trim(),
        quality_observations: reportForm.quality_observations.trim(),
        incidents: reportForm.incidents.trim(),
        blockers: reportForm.blockers.trim(),
        status: reportForm.status,
        escalation_required: reportForm.escalation_required,
      });

      if (reportPhotoFiles.length > 0) {
        for (const file of reportPhotoFiles) {
          const payload = new FormData();
          payload.append("image", file);
          payload.append("caption", "");
          await api.upload(`/projects/field-operations/reports/${created.id}/upload-photo/`, payload);
        }
      }

      toast.success("Report submitted", "Daily site report has been captured.");
      showReportForm = false;
      resetReportForm();
      await loadFieldOpsData();
    } catch (error) {
      toast.error("Save failed", parseApiError(error, "Could not save daily site report."));
    } finally {
      saving = false;
    }
  }

  async function createQualityInspection(event: Event) {
    event.preventDefault();
    const projectId = parseProjectId(inspectionForm.project);
    if (!projectId) {
      toast.error("Project required", "Select a project before saving an inspection.");
      return;
    }
    if (!inspectionForm.inspector_name.trim()) {
      toast.error("Inspector required", "Provide inspector name.");
      return;
    }

    const checklistPayload = inspectionChecklistRows
      .map((row, index) => ({
        sort_order: index,
        checklist_group: row.checklist_group.trim(),
        checklist_item: row.checklist_item.trim(),
        result: row.result,
        remarks: row.remarks.trim(),
        action_owner: row.action_owner.trim(),
        action_due_date: row.action_due_date || null,
        resolved_on: row.resolved_on || null,
      }))
      .filter((row) => row.checklist_item.length > 0);

    saving = true;
    try {
      const created = await api.post<ProjectExecutionInspection>("/projects/field-operations/quality-inspections/", {
        project: projectId,
        phase: parseProjectId(inspectionForm.phase),
        source_report: parseProjectId(inspectionForm.source_report),
        inspection_type: inspectionForm.inspection_type,
        status: inspectionForm.status,
        inspected_on: inspectionForm.inspected_on || today,
        shift: inspectionForm.shift,
        work_package: inspectionForm.work_package.trim(),
        location: inspectionForm.location.trim(),
        inspector_name: inspectionForm.inspector_name.trim(),
        inspector_role: inspectionForm.inspector_role.trim(),
        overall_score: toNullableDecimal(inspectionForm.overall_score),
        critical_findings: toInt(inspectionForm.critical_findings),
        major_findings: toInt(inspectionForm.major_findings),
        minor_findings: toInt(inspectionForm.minor_findings),
        observations: inspectionForm.observations.trim(),
        corrective_actions: inspectionForm.corrective_actions.trim(),
        due_date: inspectionForm.due_date || null,
        checklist_items: checklistPayload,
      });

      if (inspectionSupportingFiles.length > 0) {
        const uploadOk = await uploadSupportingFiles(
          `/projects/field-operations/quality-inspections/${created.id}/upload-supporting-file/`,
          inspectionSupportingFiles,
        );
        if (!uploadOk) {
          toast.error(
            "Files not uploaded",
            "Inspection was saved, but supporting files failed to upload.",
          );
        }
      }

      toast.success("Inspection saved", "Execution quality inspection has been logged.");
      showInspectionForm = false;
      resetInspectionForm();
      await loadFieldOpsData();
    } catch (error) {
      toast.error("Save failed", parseApiError(error, "Could not save quality inspection."));
    } finally {
      saving = false;
    }
  }

  async function createEscalation(event: Event) {
    event.preventDefault();
    const projectId = parseProjectId(escalationForm.project);
    if (!projectId) {
      toast.error("Project required", "Select a project before creating an escalation.");
      return;
    }

    saving = true;
    try {
      const created = await api.post<ProjectFieldEscalation>("/projects/field-operations/escalations/", {
        project: projectId,
        source_report: parseProjectId(escalationForm.source_report),
        title: escalationForm.title.trim(),
        description: escalationForm.description.trim(),
        severity: escalationForm.severity,
        status: escalationForm.status,
        owner_name: escalationForm.owner_name.trim(),
        due_date: escalationForm.due_date || null,
        resolution_notes: escalationForm.resolution_notes.trim(),
      });
      if (escalationSupportingFiles.length > 0) {
        const uploadOk = await uploadSupportingFiles(
          `/projects/field-operations/escalations/${created.id}/upload-supporting-file/`,
          escalationSupportingFiles,
        );
        if (!uploadOk) {
          toast.error(
            "Files not uploaded",
            "Escalation was saved, but supporting files failed to upload.",
          );
        }
      }
      toast.success("Escalation created", "Field escalation has been logged.");
      showEscalationForm = false;
      resetEscalationForm();
      await loadFieldOpsData();
    } catch (error) {
      toast.error("Save failed", parseApiError(error, "Could not create escalation."));
    } finally {
      saving = false;
    }
  }

  const reportsForEscalationProject = $derived.by(() => {
    if (!escalationForm.project) return [];
    return siteReports
      .filter((report) => String(report.project) === escalationForm.project)
      .sort((a, b) => b.report_date.localeCompare(a.report_date));
  });

  const reportsForInspectionProject = $derived.by(() => {
    if (!inspectionForm.project) return [];
    return siteReports
      .filter((report) => String(report.project) === inspectionForm.project)
      .sort((a, b) => b.report_date.localeCompare(a.report_date));
  });

  const tasksForSelectedWorkforceProject = $derived.by(() => {
    const selectedProject = workforceForm.project || projectFilter;
    if (!selectedProject) return workforceTasks;
    return workforceTasks.filter((task) => String(task.project) === selectedProject);
  });

  const workforceTodayCount = $derived(workforceLogs.filter((row) => row.report_date === today).length);
  const reportsTodayCount = $derived(siteReports.filter((row) => row.report_date === today).length);

  const filteredWorkforceRows = $derived.by(() => {
    let rows = workforceLogs.filter((row) => {
      if (projectFilter && String(row.project) !== projectFilter) return false;
      if (workforceShiftFilter && row.shift !== workforceShiftFilter) return false;
      if (!workforceSearch.trim()) return true;
      const needle = workforceSearch.trim().toLowerCase();
      const haystack = `${row.project_name} ${row.worker_id} ${row.employee_name ?? ""} ${row.trade} ${row.contractor_name ?? ""} ${row.task_assigned_name ?? ""} ${row.daily_attendance} ${row.shift} ${row.notes}`.toLowerCase();
      return haystack.includes(needle);
    });

    rows = [...rows].sort((a, b) => {
      if (workforceSort === "date_asc") return dateKey(a.report_date) - dateKey(b.report_date);
      if (workforceSort === "headcount_desc") return b.total_headcount - a.total_headcount;
      if (workforceSort === "project_asc") return a.project_name.localeCompare(b.project_name);
      return dateKey(b.report_date) - dateKey(a.report_date);
    });

    return rows;
  });

  const filteredReportRows = $derived.by(() => {
    let rows = siteReports.filter((row) => {
      if (projectFilter && String(row.project) !== projectFilter) return false;
      if (reportsStatusFilter && row.status !== reportsStatusFilter) return false;
      if (reportsWeatherFilter && row.weather !== reportsWeatherFilter) return false;
      if (!reportsSearch.trim()) return true;
      const needle = reportsSearch.trim().toLowerCase();
      const haystack = `${row.project_name} ${row.work_completed} ${row.blockers} ${row.weather}`.toLowerCase();
      return haystack.includes(needle);
    });

    rows = [...rows].sort((a, b) => {
      if (reportsSort === "date_asc") return dateKey(a.report_date) - dateKey(b.report_date);
      if (reportsSort === "progress_desc") return decimalKey(b.progress_percent) - decimalKey(a.progress_percent);
      if (reportsSort === "progress_asc") return decimalKey(a.progress_percent) - decimalKey(b.progress_percent);
      return dateKey(b.report_date) - dateKey(a.report_date);
    });

    return rows;
  });

  const filteredDeliveryRows = $derived.by(() => {
    let rows = deliveryConfirmations.filter((row) => {
      if (projectFilter && String(row.project) !== projectFilter) return false;
      if (deliveriesStatusFilter && row.status !== deliveriesStatusFilter) return false;
      if (deliveriesLateFilter === "late" && !row.is_late) return false;
      if (deliveriesLateFilter === "on_time" && row.is_late) return false;
      if (!deliveriesSearch.trim()) return true;
      const needle = deliveriesSearch.trim().toLowerCase();
      const haystack =
        `${row.project_name ?? ""} ${row.po_number} ${row.grn_number} ${row.vendor_name} ${row.delivery_note_number} ${row.received_by}`.toLowerCase();
      return haystack.includes(needle);
    });

    rows = [...rows].sort((a, b) => {
      if (deliveriesSort === "date_asc") return dateKey(a.received_date) - dateKey(b.received_date);
      if (deliveriesSort === "delay_desc") return (b.delay_days || 0) - (a.delay_days || 0);
      if (deliveriesSort === "project_asc") return (a.project_name ?? "").localeCompare(b.project_name ?? "");
      return dateKey(b.received_date) - dateKey(a.received_date);
    });

    return rows;
  });

  const filteredInspectionRows = $derived.by(() => {
    let rows = qualityInspections.filter((row) => {
      if (projectFilter && String(row.project) !== projectFilter) return false;
      if (inspectionsStatusFilter && row.status !== inspectionsStatusFilter) return false;
      if (inspectionsTypeFilter && row.inspection_type !== inspectionsTypeFilter) return false;
      if (!inspectionsSearch.trim()) return true;
      const needle = inspectionsSearch.trim().toLowerCase();
      const haystack = `${row.project_name} ${row.inspection_number} ${row.inspector_name} ${row.work_package} ${row.location}`.toLowerCase();
      return haystack.includes(needle);
    });

    rows = [...rows].sort((a, b) => {
      if (inspectionsSort === "date_asc") return dateKey(a.inspected_on) - dateKey(b.inspected_on);
      if (inspectionsSort === "status_asc") return a.status.localeCompare(b.status);
      if (inspectionsSort === "score_desc") return decimalKey(b.overall_score) - decimalKey(a.overall_score);
      return dateKey(b.inspected_on) - dateKey(a.inspected_on);
    });

    return rows;
  });

  const filteredEscalationRows = $derived.by(() => {
    let rows = escalations.filter((row) => {
      if (projectFilter && String(row.project) !== projectFilter) return false;
      if (escalationsStatusFilter && row.status !== escalationsStatusFilter) return false;
      if (escalationsSeverityFilter && row.severity !== escalationsSeverityFilter) return false;
      if (!escalationsSearch.trim()) return true;
      const needle = escalationsSearch.trim().toLowerCase();
      const haystack = `${row.project_name} ${row.title} ${row.description} ${row.owner_name}`.toLowerCase();
      return haystack.includes(needle);
    });

    rows = [...rows].sort((a, b) => {
      if (escalationsSort === "created_asc") return dateKey(a.created_at) - dateKey(b.created_at);
      if (escalationsSort === "due_asc") return dateKey(a.due_date) - dateKey(b.due_date);
      if (escalationsSort === "severity_desc") return (severityRank[b.severity] || 0) - (severityRank[a.severity] || 0);
      return dateKey(b.created_at) - dateKey(a.created_at);
    });

    return rows;
  });

  const workforceTotalPages = $derived(Math.max(1, Math.ceil(filteredWorkforceRows.length / workforcePageSize)));
  const workforceStart = $derived(filteredWorkforceRows.length === 0 ? 0 : (workforcePage - 1) * workforcePageSize + 1);
  const workforceEnd = $derived(Math.min(workforcePage * workforcePageSize, filteredWorkforceRows.length));
  const workforcePageRows = $derived(filteredWorkforceRows.slice((workforcePage - 1) * workforcePageSize, workforcePage * workforcePageSize));

  const reportsTotalPages = $derived(Math.max(1, Math.ceil(filteredReportRows.length / reportsPageSize)));
  const reportsStart = $derived(filteredReportRows.length === 0 ? 0 : (reportsPage - 1) * reportsPageSize + 1);
  const reportsEnd = $derived(Math.min(reportsPage * reportsPageSize, filteredReportRows.length));
  const reportsPageRows = $derived(filteredReportRows.slice((reportsPage - 1) * reportsPageSize, reportsPage * reportsPageSize));

  const deliveriesTotalPages = $derived(Math.max(1, Math.ceil(filteredDeliveryRows.length / deliveriesPageSize)));
  const deliveriesStart = $derived(filteredDeliveryRows.length === 0 ? 0 : (deliveriesPage - 1) * deliveriesPageSize + 1);
  const deliveriesEnd = $derived(Math.min(deliveriesPage * deliveriesPageSize, filteredDeliveryRows.length));
  const deliveriesPageRows = $derived(
    filteredDeliveryRows.slice((deliveriesPage - 1) * deliveriesPageSize, deliveriesPage * deliveriesPageSize),
  );

  const inspectionsTotalPages = $derived(Math.max(1, Math.ceil(filteredInspectionRows.length / inspectionsPageSize)));
  const inspectionsStart = $derived(filteredInspectionRows.length === 0 ? 0 : (inspectionsPage - 1) * inspectionsPageSize + 1);
  const inspectionsEnd = $derived(Math.min(inspectionsPage * inspectionsPageSize, filteredInspectionRows.length));
  const inspectionsPageRows = $derived(
    filteredInspectionRows.slice((inspectionsPage - 1) * inspectionsPageSize, inspectionsPage * inspectionsPageSize),
  );

  const escalationsTotalPages = $derived(Math.max(1, Math.ceil(filteredEscalationRows.length / escalationsPageSize)));
  const escalationsStart = $derived(filteredEscalationRows.length === 0 ? 0 : (escalationsPage - 1) * escalationsPageSize + 1);
  const escalationsEnd = $derived(Math.min(escalationsPage * escalationsPageSize, filteredEscalationRows.length));
  const escalationsPageRows = $derived(
    filteredEscalationRows.slice((escalationsPage - 1) * escalationsPageSize, escalationsPage * escalationsPageSize),
  );

  function reportStatusClass(status: string): string {
    if (status === "draft") return "bg-neutral-100 text-neutral-700 border-neutral-200";
    if (status === "submitted") return "bg-blue-50 text-blue-700 border-blue-100";
    if (status === "reviewed") return "bg-emerald-50 text-emerald-700 border-emerald-100";
    return "bg-amber-50 text-amber-700 border-amber-100";
  }

  function deliveryStatusClass(status: string): string {
    if (status === "pending") return "bg-neutral-100 text-neutral-700 border-neutral-200";
    if (status === "inspected") return "bg-blue-50 text-blue-700 border-blue-100";
    if (status === "accepted") return "bg-emerald-50 text-emerald-700 border-emerald-100";
    if (status === "partially_accepted") return "bg-amber-50 text-amber-700 border-amber-100";
    return "bg-rose-50 text-rose-700 border-rose-100";
  }

  function inspectionStatusClass(status: string): string {
    if (status === "planned") return "bg-neutral-100 text-neutral-700 border-neutral-200";
    if (status === "in_progress") return "bg-blue-50 text-blue-700 border-blue-100";
    if (status === "passed") return "bg-emerald-50 text-emerald-700 border-emerald-100";
    if (status === "failed") return "bg-rose-50 text-rose-700 border-rose-100";
    if (status === "blocked") return "bg-amber-50 text-amber-700 border-amber-100";
    return "bg-violet-50 text-violet-700 border-violet-100";
  }

  function escalationSeverityClass(severity: string): string {
    if (severity === "info") return "bg-sky-50 text-sky-700 border-sky-100";
    if (severity === "review") return "bg-blue-50 text-blue-700 border-blue-100";
    if (severity === "action_required") return "bg-amber-50 text-amber-700 border-amber-100";
    return "bg-rose-50 text-rose-700 border-rose-100";
  }

  function escalationStatusClass(status: string): string {
    if (status === "open") return "bg-rose-50 text-rose-700 border-rose-100";
    if (status === "acknowledged") return "bg-blue-50 text-blue-700 border-blue-100";
    if (status === "in_progress") return "bg-amber-50 text-amber-700 border-amber-100";
    if (status === "resolved") return "bg-emerald-50 text-emerald-700 border-emerald-100";
    return "bg-neutral-100 text-neutral-700 border-neutral-200";
  }

  function toggleWorkforceRow(rowId: number) {
    expandedWorkforceRowId = expandedWorkforceRowId === rowId ? null : rowId;
  }

  function toggleReportRow(rowId: number) {
    expandedReportRowId = expandedReportRowId === rowId ? null : rowId;
  }

  function toggleEscalationRow(rowId: number) {
    expandedEscalationRowId = expandedEscalationRowId === rowId ? null : rowId;
  }

  async function uploadSupportingFiles(endpoint: string, files: File[]): Promise<boolean> {
    try {
      for (const file of files) {
        const payload = new FormData();
        payload.append("file", file);
        payload.append("caption", file.name);
        await api.upload(endpoint, payload);
      }
      return true;
    } catch {
      return false;
    }
  }

  $effect(() => {
    if (showWorkforceForm && !workforceForm.project && projectFilter) workforceForm.project = projectFilter;
    if (showReportForm && !reportForm.project && projectFilter) reportForm.project = projectFilter;
    if (showInspectionForm && !inspectionForm.project && projectFilter) inspectionForm.project = projectFilter;
    if (showEscalationForm && !escalationForm.project && projectFilter) escalationForm.project = projectFilter;
  });

  $effect(() => {
    void projectFilter;
    void workforceSearch;
    void workforceShiftFilter;
    void workforceSort;
    void workforcePageSize;
    workforcePage = 1;
  });

  $effect(() => {
    void projectFilter;
    void reportsSearch;
    void reportsStatusFilter;
    void reportsWeatherFilter;
    void reportsSort;
    void reportsPageSize;
    reportsPage = 1;
  });

  $effect(() => {
    void projectFilter;
    void deliveriesSearch;
    void deliveriesStatusFilter;
    void deliveriesLateFilter;
    void deliveriesSort;
    void deliveriesPageSize;
    deliveriesPage = 1;
  });

  $effect(() => {
    void projectFilter;
    void inspectionsSearch;
    void inspectionsStatusFilter;
    void inspectionsTypeFilter;
    void inspectionsSort;
    void inspectionsPageSize;
    inspectionsPage = 1;
  });

  $effect(() => {
    void projectFilter;
    void escalationsSearch;
    void escalationsStatusFilter;
    void escalationsSeverityFilter;
    void escalationsSort;
    void escalationsPageSize;
    escalationsPage = 1;
  });

  $effect(() => {
    void workforceTotalPages;
    if (workforcePage > workforceTotalPages) workforcePage = workforceTotalPages;
  });

  $effect(() => {
    void workforcePageRows;
    if (expandedWorkforceRowId !== null && !workforcePageRows.some((row) => row.id === expandedWorkforceRowId)) {
      expandedWorkforceRowId = null;
    }
  });

  $effect(() => {
    void reportsTotalPages;
    if (reportsPage > reportsTotalPages) reportsPage = reportsTotalPages;
  });

  $effect(() => {
    void reportsPageRows;
    if (expandedReportRowId !== null && !reportsPageRows.some((row) => row.id === expandedReportRowId)) {
      expandedReportRowId = null;
    }
  });

  $effect(() => {
    void deliveriesTotalPages;
    if (deliveriesPage > deliveriesTotalPages) deliveriesPage = deliveriesTotalPages;
  });

  $effect(() => {
    void inspectionsTotalPages;
    if (inspectionsPage > inspectionsTotalPages) inspectionsPage = inspectionsTotalPages;
  });

  $effect(() => {
    void escalationsTotalPages;
    if (escalationsPage > escalationsTotalPages) escalationsPage = escalationsTotalPages;
  });

  $effect(() => {
    void escalationsPageRows;
    if (expandedEscalationRowId !== null && !escalationsPageRows.some((row) => row.id === expandedEscalationRowId)) {
      expandedEscalationRowId = null;
    }
  });

  $effect(() => {
    loadFieldOpsData();
    resetWorkforceForm();
    resetReportForm();
    resetInspectionForm();
    resetEscalationForm();
  });
</script>

<div class="space-y-8">
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-700">Construction</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Field Operations</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Workforce management, daily site reporting, and operational escalations.
      </p>
    </div>
    <button
      onclick={loadFieldOpsData}
      class="rounded-lg border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
    >
      Refresh
    </button>
  </div>

  <div class="grid grid-cols-2 gap-4 lg:grid-cols-5">
    <div class="rounded-xl border border-indigo-100 bg-indigo-50 p-4">
      <p class="text-[10px] font-semibold uppercase tracking-wider text-indigo-700">Workforce Logs Today</p>
      <p class="mt-1 text-2xl font-bold text-indigo-900 tabular-nums">{workforceTodayCount}</p>
    </div>
    <div class="rounded-xl border border-blue-100 bg-blue-50 p-4">
      <p class="text-[10px] font-semibold uppercase tracking-wider text-blue-700">Site Reports Today</p>
      <p class="mt-1 text-2xl font-bold text-blue-900 tabular-nums">{reportsTodayCount}</p>
    </div>
    <div class="rounded-xl border border-rose-100 bg-rose-50 p-4">
      <p class="text-[10px] font-semibold uppercase tracking-wider text-rose-700">Late Deliveries</p>
      <p class="mt-1 text-2xl font-bold text-rose-900 tabular-nums">{deliverySummary.late}</p>
    </div>
    <div class="rounded-xl border border-orange-100 bg-orange-50 p-4">
      <p class="text-[10px] font-semibold uppercase tracking-wider text-orange-700">Pending Delivery Inspection</p>
      <p class="mt-1 text-2xl font-bold text-orange-900 tabular-nums">{deliverySummary.pending_inspection}</p>
    </div>
    <div class="rounded-xl border border-amber-100 bg-amber-50 p-4">
      <p class="text-[10px] font-semibold uppercase tracking-wider text-amber-700">Open Escalations</p>
      <p class="mt-1 text-2xl font-bold text-amber-900 tabular-nums">{escalationSummary.open}</p>
    </div>
    <div class="rounded-xl border border-rose-100 bg-rose-50 p-4">
      <p class="text-[10px] font-semibold uppercase tracking-wider text-rose-700">Critical Escalations</p>
      <p class="mt-1 text-2xl font-bold text-rose-900 tabular-nums">{escalationSummary.critical}</p>
    </div>
    <div class="rounded-xl border border-amber-100 bg-amber-50 p-4">
      <p class="text-[10px] font-semibold uppercase tracking-wider text-amber-700">Failed Inspections</p>
      <p class="mt-1 text-2xl font-bold text-amber-900 tabular-nums">{inspectionSummary.failed}</p>
    </div>
    <div class="rounded-xl border border-orange-100 bg-orange-50 p-4">
      <p class="text-[10px] font-semibold uppercase tracking-wider text-orange-700">Corrective Actions Due</p>
      <p class="mt-1 text-2xl font-bold text-orange-900 tabular-nums">{inspectionSummary.due_actions}</p>
    </div>
    <div class="rounded-xl border border-red-100 bg-red-50 p-4">
      <p class="text-[10px] font-semibold uppercase tracking-wider text-red-700">Open Late Delivery Escalations</p>
      <p class="mt-1 text-2xl font-bold text-red-900 tabular-nums">{deliverySummary.open_late_delivery_escalations}</p>
    </div>
  </div>

  <section class="rounded-2xl border border-neutral-200 bg-white p-4 sm:p-5">
    <div class="grid gap-3 md:grid-cols-3">
      <div class="md:col-span-2">
        <label for="field-ops-project-scope" class="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-neutral-500">Project Scope</label>
        <select
          id="field-ops-project-scope"
          bind:value={projectFilter}
          class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
        >
          <option value="">All Projects</option>
          {#each projects as project}
            <option value={String(project.id)}>{project.name}</option>
          {/each}
        </select>
      </div>
      <div class="flex items-end">
        <button
          onclick={() => {
            projectFilter = "";
            workforceSearch = "";
            workforceShiftFilter = "";
            reportsSearch = "";
            reportsStatusFilter = "";
            reportsWeatherFilter = "";
            deliveriesSearch = "";
            deliveriesStatusFilter = "";
            deliveriesLateFilter = "";
            escalationsSearch = "";
            escalationsStatusFilter = "";
            escalationsSeverityFilter = "";
          }}
          class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm font-medium text-neutral-600 hover:bg-neutral-100"
        >
          Reset Filters
        </button>
      </div>
    </div>
  </section>

  <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-sm">
    <div class="border-b border-neutral-200 px-4 py-4">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Delivery Confirmations</h2>
          <p class="mt-0.5 text-xs text-neutral-500">
            Procurement goods-receipt confirmations synchronized to site operations for delivery tracking and delay control.
          </p>
        </div>
      </div>
      <div class="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <input
          type="text"
          bind:value={deliveriesSearch}
          placeholder="Search deliveries..."
          class="xl:col-span-2 rounded-lg border border-neutral-200 px-3 py-2 text-sm"
        />
        <select bind:value={deliveriesStatusFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          <option value="">All Statuses</option>
          {#each DELIVERY_STATUS_OPTIONS as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
        <select bind:value={deliveriesLateFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          <option value="">All Timing</option>
          <option value="on_time">On Time</option>
          <option value="late">Late</option>
        </select>
        <div class="grid grid-cols-2 gap-2">
          <select bind:value={deliveriesSort} class="rounded-lg border border-neutral-200 bg-white px-2 py-2 text-sm">
            <option value="date_desc">Newest</option>
            <option value="date_asc">Oldest</option>
            <option value="delay_desc">Delay High</option>
            <option value="project_asc">Project A-Z</option>
          </select>
          <select bind:value={deliveriesPageSize} class="rounded-lg border border-neutral-200 bg-white px-2 py-2 text-sm">
            <option value={10}>10 / page</option>
            <option value={20}>20 / page</option>
            <option value={50}>50 / page</option>
          </select>
        </div>
      </div>
    </div>

    {#if loading}
      <div class="flex items-center justify-center py-12">
        <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
      </div>
    {:else if filteredDeliveryRows.length === 0}
      <div class="px-6 py-12 text-center text-sm text-neutral-500">No delivery confirmations match current filters.</div>
    {:else}
      <div class="overflow-x-auto">
        <table class="min-w-[1180px] w-full text-sm">
          <thead class="border-b border-neutral-100 bg-neutral-50">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Received</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Expected</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Project</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">PO / GRN</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Vendor</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Status</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Accepted Qty</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Rejected Qty</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Delay</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each deliveriesPageRows as row (row.id)}
              <tr class="hover:bg-neutral-50">
                <td class="px-4 py-3 text-neutral-600">{fmtDate(row.received_date)}</td>
                <td class="px-4 py-3 text-neutral-600">{fmtDate(row.expected_delivery_date)}</td>
                <td class="px-4 py-3 text-neutral-900">{row.project_name || "--"}</td>
                <td class="px-4 py-3 text-neutral-900">
                  <p class="font-medium">{row.po_number}</p>
                  <p class="mt-0.5 text-xs text-neutral-500">{row.grn_number}</p>
                </td>
                <td class="px-4 py-3 text-neutral-600">{row.vendor_name}</td>
                <td class="px-4 py-3">
                  <span class={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${deliveryStatusClass(row.status)}`}>
                    {row.status.replaceAll("_", " ")}
                  </span>
                </td>
                <td class="px-4 py-3 text-right tabular-nums text-neutral-700">{row.accepted_quantity}</td>
                <td class="px-4 py-3 text-right tabular-nums text-neutral-700">{row.rejected_quantity}</td>
                <td class="px-4 py-3 text-neutral-600">
                  {#if row.is_late}
                    <span class="font-medium text-rose-700">{row.delay_days} day(s) late</span>
                  {:else}
                    <span class="text-emerald-700">On time</span>
                  {/if}
                </td>
                <td class="px-4 py-3 text-right">
                  {#if row.project}
                    <button onclick={() => openProjectModal(row.project)} class="text-xs font-medium text-neutral-600 hover:text-indigo-700">View Project</button>
                  {:else}
                    <span class="text-xs text-neutral-400">--</span>
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      <div class="flex items-center justify-between border-t border-neutral-100 px-4 py-3">
        <p class="text-xs text-neutral-500">Showing {deliveriesStart}-{deliveriesEnd} of {filteredDeliveryRows.length}</p>
        <div class="flex items-center gap-2">
          <button onclick={() => (deliveriesPage = Math.max(1, deliveriesPage - 1))} disabled={deliveriesPage === 1} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 disabled:opacity-40">Previous</button>
          <span class="text-xs text-neutral-600">Page {deliveriesPage} of {deliveriesTotalPages}</span>
          <button onclick={() => (deliveriesPage = Math.min(deliveriesTotalPages, deliveriesPage + 1))} disabled={deliveriesPage === deliveriesTotalPages} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 disabled:opacity-40">Next</button>
        </div>
      </div>
    {/if}
  </section>

  <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-sm">
    <div class="border-b border-neutral-200 px-4 py-4">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Execution Quality Inspections</h2>
          <p class="mt-0.5 text-xs text-neutral-500">Dedicated site execution inspections with checklist logs and corrective actions.</p>
        </div>
        <button
          onclick={() => {
            resetInspectionForm();
            showInspectionForm = !showInspectionForm;
          }}
          class="rounded-lg bg-neutral-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-neutral-800"
        >
          {showInspectionForm ? "Close Form" : "+ New Inspection"}
        </button>
      </div>
      <div class="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <input type="text" bind:value={inspectionsSearch} placeholder="Search inspections..." class="xl:col-span-2 rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
        <select bind:value={inspectionsStatusFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          <option value="">All Statuses</option>
          {#each INSPECTION_STATUS_OPTIONS as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
        <select bind:value={inspectionsTypeFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          <option value="">All Types</option>
          {#each INSPECTION_TYPE_OPTIONS as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
        <div class="grid grid-cols-2 gap-2">
          <select bind:value={inspectionsSort} class="rounded-lg border border-neutral-200 bg-white px-2 py-2 text-sm">
            <option value="date_desc">Newest</option>
            <option value="date_asc">Oldest</option>
            <option value="status_asc">Status</option>
            <option value="score_desc">Score High</option>
          </select>
          <select bind:value={inspectionsPageSize} class="rounded-lg border border-neutral-200 bg-white px-2 py-2 text-sm">
            <option value={10}>10 / page</option>
            <option value={20}>20 / page</option>
            <option value={50}>50 / page</option>
          </select>
        </div>
      </div>
    </div>

    {#if showInspectionForm}
      <form onsubmit={createQualityInspection} class="grid gap-3 border-b border-neutral-200 bg-neutral-50 px-4 py-4 md:grid-cols-3">
        <select bind:value={inspectionForm.project} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          <option value="">Select project</option>
          {#each projects as project}
            <option value={String(project.id)}>{project.name}</option>
          {/each}
        </select>
        <select bind:value={inspectionForm.source_report} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          <option value="">No source site report</option>
          {#each reportsForInspectionProject as report}
            <option value={String(report.id)}>{report.report_date} - {report.shift} - {report.status}</option>
          {/each}
        </select>
        <select bind:value={inspectionForm.inspection_type} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          {#each INSPECTION_TYPE_OPTIONS as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
        <select bind:value={inspectionForm.status} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          {#each INSPECTION_STATUS_OPTIONS as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
        <DateInput bind:value={inspectionForm.inspected_on} />
        <select bind:value={inspectionForm.shift} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          {#each SHIFT_OPTIONS as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
        <input type="text" bind:value={inspectionForm.work_package} placeholder="Work package" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
        <input type="text" bind:value={inspectionForm.location} placeholder="Inspection location" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
        <input type="text" bind:value={inspectionForm.inspector_name} placeholder="Inspector name" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
        <input type="text" bind:value={inspectionForm.inspector_role} placeholder="Inspector role" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
        <input type="number" min="0" max="100" step="0.1" bind:value={inspectionForm.overall_score} placeholder="Overall score %" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
        <DateInput bind:value={inspectionForm.due_date} />
        <input type="number" min="0" bind:value={inspectionForm.critical_findings} placeholder="Critical findings" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
        <input type="number" min="0" bind:value={inspectionForm.major_findings} placeholder="Major findings" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
        <input type="number" min="0" bind:value={inspectionForm.minor_findings} placeholder="Minor findings" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
        <textarea bind:value={inspectionForm.observations} rows="2" placeholder="Inspection observations" class="md:col-span-2 rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>
        <textarea bind:value={inspectionForm.corrective_actions} rows="2" placeholder="Corrective action summary" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>

        <div class="md:col-span-3 rounded-lg border border-neutral-200 bg-white p-3">
          <div class="mb-2 flex items-center justify-between">
            <p class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Checklist Items</p>
            <button type="button" onclick={addInspectionChecklistRow} class="rounded-md border border-neutral-200 px-2.5 py-1 text-xs font-medium text-neutral-600 hover:bg-neutral-100">+ Add Row</button>
          </div>
          <div class="space-y-2">
            {#each inspectionChecklistRows as row, index (index)}
              <div class="grid gap-2 rounded-lg border border-neutral-100 p-2 md:grid-cols-6">
                <input type="text" bind:value={inspectionChecklistRows[index].checklist_group} placeholder="Group" class="rounded-lg border border-neutral-200 px-2 py-1.5 text-xs" />
                <input type="text" bind:value={inspectionChecklistRows[index].checklist_item} placeholder="Checklist item" class="md:col-span-2 rounded-lg border border-neutral-200 px-2 py-1.5 text-xs" />
                <select bind:value={inspectionChecklistRows[index].result} class="rounded-lg border border-neutral-200 bg-white px-2 py-1.5 text-xs">
                  {#each CHECKLIST_RESULT_OPTIONS as option}
                    <option value={option.value}>{option.label}</option>
                  {/each}
                </select>
                <input type="text" bind:value={inspectionChecklistRows[index].action_owner} placeholder="Action owner" class="rounded-lg border border-neutral-200 px-2 py-1.5 text-xs" />
                <div class="flex gap-1">
                  <DateInput bind:value={inspectionChecklistRows[index].action_due_date} />
                  <button type="button" onclick={() => removeInspectionChecklistRow(index)} class="rounded-md border border-rose-200 px-2 text-xs font-medium text-rose-600 hover:bg-rose-50">X</button>
                </div>
                <textarea bind:value={inspectionChecklistRows[index].remarks} rows="2" placeholder="Remarks" class="md:col-span-6 rounded-lg border border-neutral-200 px-2 py-1.5 text-xs"></textarea>
              </div>
            {/each}
          </div>
        </div>

        <label class="md:col-span-2 rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700">
          <span class="block text-xs font-semibold uppercase tracking-wider text-neutral-500">Supporting Photos/Documents</span>
          <input type="file" multiple onchange={onInspectionSupportingFilesSelected} class="mt-2 w-full text-sm" />
          {#if inspectionSupportingFiles.length > 0}
            <p class="mt-2 text-xs text-neutral-500">{inspectionSupportingFiles.length} file(s) selected</p>
          {/if}
        </label>
        <div class="flex items-end justify-end gap-2">
          {#if isDev}
            <button type="button" onclick={devFillInspection} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>
          {/if}
          <button
            type="submit"
            disabled={saving}
            class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save Inspection"}
          </button>
        </div>
      </form>
    {/if}

    {#if loading}
      <div class="flex items-center justify-center py-12">
        <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
      </div>
    {:else if filteredInspectionRows.length === 0}
      <div class="px-6 py-12 text-center text-sm text-neutral-500">No execution inspections match current filters.</div>
    {:else}
      <div class="overflow-x-auto">
        <table class="min-w-[1180px] w-full text-sm">
          <thead class="border-b border-neutral-100 bg-neutral-50">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Date</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Inspection #</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Project</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Type</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Status</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Score</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Findings</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Pending Actions</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each inspectionsPageRows as row (row.id)}
              <tr class="hover:bg-neutral-50">
                <td class="px-4 py-3 text-neutral-600">{fmtDate(row.inspected_on)}</td>
                <td class="px-4 py-3 text-neutral-900 font-medium">{row.inspection_number}</td>
                <td class="px-4 py-3 text-neutral-900">
                  <p>{row.project_name}</p>
                  {#if row.work_package}
                    <p class="mt-0.5 text-xs text-neutral-500">{row.work_package}</p>
                  {/if}
                </td>
                <td class="px-4 py-3 text-neutral-600 capitalize">{row.inspection_type.replaceAll("_", " ")}</td>
                <td class="px-4 py-3">
                  <span class={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${inspectionStatusClass(row.status)}`}>
                    {row.status.replaceAll("_", " ")}
                  </span>
                </td>
                <td class="px-4 py-3 text-right tabular-nums text-neutral-700">{row.overall_score ? `${row.overall_score}%` : "--"}</td>
                <td class="px-4 py-3 text-right tabular-nums text-neutral-700">
                  C:{row.critical_findings} M:{row.major_findings} m:{row.minor_findings}
                </td>
                <td class="px-4 py-3 text-right tabular-nums text-neutral-700">{row.pending_actions_count}</td>
                <td class="px-4 py-3 text-right">
                  <button onclick={() => openProjectModal(row.project)} class="text-xs font-medium text-neutral-600 hover:text-indigo-700">View Project</button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      <div class="flex items-center justify-between border-t border-neutral-100 px-4 py-3">
        <p class="text-xs text-neutral-500">Showing {inspectionsStart}-{inspectionsEnd} of {filteredInspectionRows.length}</p>
        <div class="flex items-center gap-2">
          <button onclick={() => (inspectionsPage = Math.max(1, inspectionsPage - 1))} disabled={inspectionsPage === 1} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 disabled:opacity-40">Previous</button>
          <span class="text-xs text-neutral-600">Page {inspectionsPage} of {inspectionsTotalPages}</span>
          <button onclick={() => (inspectionsPage = Math.min(inspectionsTotalPages, inspectionsPage + 1))} disabled={inspectionsPage === inspectionsTotalPages} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 disabled:opacity-40">Next</button>
        </div>
      </div>
    {/if}
  </section>

  <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-sm">
    <div class="border-b border-neutral-200 px-4 py-4">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Workforce Management</h2>
          <p class="mt-0.5 text-xs text-neutral-500">Track deployed headcount by role per project, date, and shift.</p>
        </div>
        <button
          onclick={() => {
            resetWorkforceForm();
            showWorkforceForm = !showWorkforceForm;
          }}
          class="rounded-lg bg-neutral-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-neutral-800"
        >
          {showWorkforceForm ? "Close Form" : "+ New Workforce Log"}
        </button>
      </div>
      <div class="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <input
          type="text"
          bind:value={workforceSearch}
          placeholder="Search workforce logs..."
          class="xl:col-span-2 rounded-lg border border-neutral-200 px-3 py-2 text-sm"
        />
        <select bind:value={workforceShiftFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          <option value="">All Shifts</option>
          {#each SHIFT_OPTIONS as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
        <div class="grid grid-cols-2 gap-2">
          <select bind:value={workforceSort} class="rounded-lg border border-neutral-200 bg-white px-2 py-2 text-sm">
            <option value="date_desc">Newest</option>
            <option value="date_asc">Oldest</option>
            <option value="headcount_desc">Headcount</option>
            <option value="project_asc">Project A-Z</option>
          </select>
          <select bind:value={workforcePageSize} class="rounded-lg border border-neutral-200 bg-white px-2 py-2 text-sm">
            <option value={10}>10 / page</option>
            <option value={20}>20 / page</option>
            <option value={50}>50 / page</option>
          </select>
        </div>
      </div>
    </div>

    {#if showWorkforceForm}
      <form onsubmit={createWorkforceLog} class="grid gap-3 border-b border-neutral-200 bg-neutral-50 px-4 py-4 md:grid-cols-4">
        <label>
          <span class="mb-1 block text-xs font-medium text-neutral-600">Project</span>
          <select bind:value={workforceForm.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
            <option value="">Select project</option>
            {#each projects as project}
              <option value={String(project.id)}>{project.name}</option>
            {/each}
          </select>
        </label>
        <label>
          <span class="mb-1 block text-xs font-medium text-neutral-600">Worker ID</span>
          <input type="text" bind:value={workforceForm.worker_id} placeholder="e.g. EMP-1001 / CT-44" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
        </label>
        <label>
          <span class="mb-1 block text-xs font-medium text-neutral-600">Trade</span>
          <input type="text" bind:value={workforceForm.trade} placeholder="e.g. Masonry" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
        </label>
        <label>
          <span class="mb-1 block text-xs font-medium text-neutral-600">Contractor</span>
          <select bind:value={workforceForm.contractor} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
            <option value="">Select contractor</option>
            {#each workforceContractors as contractor}
              <option value={String(contractor.id)}>{contractor.name}</option>
            {/each}
          </select>
        </label>
        <label>
          <span class="mb-1 block text-xs font-medium text-neutral-600">HR Employee (Integration)</span>
          <select bind:value={workforceForm.employee} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
            <option value="">Select HR employee</option>
            {#each workforceEmployees as employee}
              <option value={String(employee.id)}>{employee.name} ({employee.employment_status})</option>
            {/each}
          </select>
        </label>
        <label>
          <span class="mb-1 block text-xs font-medium text-neutral-600">Report Date</span>
          <DateInput bind:value={workforceForm.report_date} />
        </label>
        <label>
          <span class="mb-1 block text-xs font-medium text-neutral-600">Daily Attendance</span>
          <select bind:value={workforceForm.daily_attendance} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
            {#each ATTENDANCE_OPTIONS as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </label>
        <label>
          <span class="mb-1 block text-xs font-medium text-neutral-600">Shift</span>
          <select bind:value={workforceForm.shift} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
            {#each SHIFT_OPTIONS as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </label>
        <label>
          <span class="mb-1 block text-xs font-medium text-neutral-600">Task Assigned</span>
          <select bind:value={workforceForm.task_assigned} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
            <option value="">Select task</option>
            {#each tasksForSelectedWorkforceProject as task}
              <option value={String(task.id)}>{task.name}{task.project_name ? ` (${task.project_name})` : ""}</option>
            {/each}
          </select>
        </label>
        <label>
          <span class="mb-1 block text-xs font-medium text-neutral-600">Productivity</span>
          <input type="number" min="0" step="0.01" bind:value={workforceForm.productivity} placeholder="Units / score / %" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
        </label>
        <label>
          <span class="mb-1 block text-xs font-medium text-neutral-600">Overtime (hours)</span>
          <input type="number" min="0" step="0.25" bind:value={workforceForm.overtime_hours} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
        </label>
        <div class="hidden md:block"></div>

        <label>
          <span class="mb-1 block text-xs font-medium text-neutral-600">Laborers Count</span>
          <input type="number" min="0" bind:value={workforceForm.laborers_count} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
        </label>
        <label>
          <span class="mb-1 block text-xs font-medium text-neutral-600">Skilled Workers Count</span>
          <input type="number" min="0" bind:value={workforceForm.skilled_count} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
        </label>
        <label>
          <span class="mb-1 block text-xs font-medium text-neutral-600">Supervisors Count</span>
          <input type="number" min="0" bind:value={workforceForm.supervisors_count} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
        </label>
        <label>
          <span class="mb-1 block text-xs font-medium text-neutral-600">Subcontractors Count</span>
          <input type="number" min="0" bind:value={workforceForm.subcontractors_count} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
        </label>
        <label>
          <span class="mb-1 block text-xs font-medium text-neutral-600">Equipment Operators Count</span>
          <input type="number" min="0" bind:value={workforceForm.equipment_operators_count} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
        </label>

        <label class="md:col-span-3">
          <span class="mb-1 block text-xs font-medium text-neutral-600">Notes</span>
          <textarea bind:value={workforceForm.notes} rows="2" placeholder="Attendance issues, productivity context..." class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>
        </label>
        <label class="md:col-span-3 rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700">
          <span class="block text-xs font-semibold uppercase tracking-wider text-neutral-500">Supporting Photos/Documents</span>
          <input type="file" multiple onchange={onWorkforceSupportingFilesSelected} class="mt-2 w-full text-sm" />
          {#if workforceSupportingFiles.length > 0}
            <p class="mt-2 text-xs text-neutral-500">{workforceSupportingFiles.length} file(s) selected</p>
          {/if}
        </label>
        <div class="flex items-end justify-end gap-2">
          {#if isDev}
            <button type="button" onclick={devFillWorkforce} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>
          {/if}
          <button
            type="submit"
            disabled={saving}
            class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save Workforce Log"}
          </button>
        </div>
      </form>
    {/if}

    {#if loading}
      <div class="flex items-center justify-center py-12">
        <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
      </div>
    {:else if filteredWorkforceRows.length === 0}
      <div class="px-6 py-12 text-center text-sm text-neutral-500">No workforce logs match current filters.</div>
    {:else}
      <div class="overflow-x-auto">
        <table class="min-w-[760px] w-full text-sm">
          <thead class="border-b border-neutral-100 bg-neutral-50">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Date</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Project</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Shift</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Details</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each workforcePageRows as row (row.id)}
              <tr class="hover:bg-neutral-50">
                <td class="px-4 py-3 text-neutral-600">{fmtDate(row.report_date)}</td>
                <td class="px-4 py-3">
                  <button
                    onclick={() => openProjectModal(row.project)}
                    class="font-semibold text-neutral-900 hover:text-indigo-700 hover:underline"
                  >
                    {row.project_name}
                  </button>
                </td>
                <td class="px-4 py-3 text-neutral-600 capitalize">{row.shift.replace("_", " ")}</td>
                <td class="px-4 py-3 text-right">
                  <button
                    type="button"
                    onclick={() => toggleWorkforceRow(row.id)}
                    aria-expanded={expandedWorkforceRowId === row.id}
                    aria-label={expandedWorkforceRowId === row.id ? "Collapse row details" : "Expand row details"}
                    class="inline-flex items-center text-xs font-semibold text-neutral-700 hover:text-neutral-900"
                  >
                    <span class={`transition-transform ${expandedWorkforceRowId === row.id ? "rotate-180" : ""}`}>▾</span>
                  </button>
                </td>
              </tr>
              {#if expandedWorkforceRowId === row.id}
                <tr class="bg-neutral-50/70">
                  <td colspan="4" class="px-4 pb-4 pt-0">
                    <div class="grid gap-3 pt-3 md:grid-cols-4">
                      <div class="rounded-lg border border-neutral-200 bg-white p-3">
                        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Headcount</p>
                        <p class="mt-1 text-lg font-bold tabular-nums text-neutral-900">{row.total_headcount}</p>
                      </div>
                      <div class="rounded-lg border border-neutral-200 bg-white p-3 md:col-span-2">
                        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Workforce Breakdown</p>
                        <p class="mt-1 text-xs leading-5 text-neutral-700">
                          Laborers: {row.laborers_count} | Skilled: {row.skilled_count} | Supervisors: {row.supervisors_count} | Subcontractors: {row.subcontractors_count} | Operators: {row.equipment_operators_count}
                        </p>
                      </div>
                      <div class="rounded-lg border border-neutral-200 bg-white p-3">
                        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Attendance</p>
                        <p class="mt-1 text-sm font-medium capitalize text-neutral-900">{row.daily_attendance.replaceAll("_", " ")}</p>
                      </div>
                      <div class="rounded-lg border border-neutral-200 bg-white p-3 md:col-span-2">
                        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Worker & Assignment</p>
                        <div class="mt-1 grid gap-1 text-xs text-neutral-700">
                          <p><span class="font-semibold text-neutral-800">Worker ID:</span> {row.worker_id || "--"}</p>
                          <p><span class="font-semibold text-neutral-800">Trade:</span> {row.trade || "--"}</p>
                          <p><span class="font-semibold text-neutral-800">Contractor:</span> {row.contractor_name || "--"}</p>
                          <p><span class="font-semibold text-neutral-800">Task Assigned:</span> {row.task_assigned_name || "--"}</p>
                        </div>
                      </div>
                      <div class="rounded-lg border border-neutral-200 bg-white p-3">
                        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Performance</p>
                        <div class="mt-1 grid gap-1 text-xs text-neutral-700">
                          <p><span class="font-semibold text-neutral-800">Productivity:</span> {row.productivity || "--"}</p>
                          <p><span class="font-semibold text-neutral-800">Overtime:</span> {Number(row.overtime_hours) > 0 ? `${row.overtime_hours}h` : "--"}</p>
                        </div>
                      </div>
                      <div class="rounded-lg border border-neutral-200 bg-white p-3 md:col-span-4">
                        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Integrations</p>
                        <div class="mt-1 grid gap-1 text-xs text-neutral-700 md:grid-cols-3">
                          <p><span class="font-semibold text-neutral-800">HR:</span> {row.employee_name ? `${row.employee_name} (${row.hr_employment_status ?? "--"})` : "Not linked"}</p>
                          <p><span class="font-semibold text-neutral-800">Payroll:</span> {row.payroll_status}{row.latest_payslip_period_end ? ` (last period: ${fmtDate(row.latest_payslip_period_end)})` : ""}</p>
                          <p><span class="font-semibold text-neutral-800">Safety Training:</span> {row.safety_training_status}</p>
                        </div>
                      </div>
                      <div class="rounded-lg border border-neutral-200 bg-white p-3 md:col-span-4">
                        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Notes</p>
                        <p class="mt-1 text-sm text-neutral-700">{row.notes || "--"}</p>
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
        <p class="text-xs text-neutral-500">Showing {workforceStart}-{workforceEnd} of {filteredWorkforceRows.length}</p>
        <div class="flex items-center gap-2">
          <button onclick={() => (workforcePage = Math.max(1, workforcePage - 1))} disabled={workforcePage === 1} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 disabled:opacity-40">Previous</button>
          <span class="text-xs text-neutral-600">Page {workforcePage} of {workforceTotalPages}</span>
          <button onclick={() => (workforcePage = Math.min(workforceTotalPages, workforcePage + 1))} disabled={workforcePage === workforceTotalPages} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 disabled:opacity-40">Next</button>
        </div>
      </div>
    {/if}
  </section>

  <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-sm">
    <div class="border-b border-neutral-200 px-4 py-4">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Daily Site Reports</h2>
          <p class="mt-0.5 text-xs text-neutral-500">Capture execution progress, weather impact, quality observations, and photo evidence.</p>
        </div>
        <button
          onclick={() => {
            resetReportForm();
            showReportForm = true;
          }}
          class="rounded-lg bg-neutral-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-neutral-800"
        >
          + New Site Report
        </button>
      </div>
      <div class="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <input type="text" bind:value={reportsSearch} placeholder="Search site reports..." class="xl:col-span-2 rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
        <select bind:value={reportsStatusFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          <option value="">All Statuses</option>
          {#each REPORT_STATUS_OPTIONS as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
        <select bind:value={reportsWeatherFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          <option value="">All Weather</option>
          {#each WEATHER_OPTIONS as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
        <div class="grid grid-cols-2 gap-2">
          <select bind:value={reportsSort} class="rounded-lg border border-neutral-200 bg-white px-2 py-2 text-sm">
            <option value="date_desc">Newest</option>
            <option value="date_asc">Oldest</option>
            <option value="progress_desc">Progress High</option>
            <option value="progress_asc">Progress Low</option>
          </select>
          <select bind:value={reportsPageSize} class="rounded-lg border border-neutral-200 bg-white px-2 py-2 text-sm">
            <option value={10}>10 / page</option>
            <option value={20}>20 / page</option>
            <option value={50}>50 / page</option>
          </select>
        </div>
      </div>
    </div>

    {#if loading}
      <div class="flex items-center justify-center py-12">
        <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
      </div>
    {:else if filteredReportRows.length === 0}
      <div class="px-6 py-12 text-center text-sm text-neutral-500">No daily site reports match current filters.</div>
    {:else}
      <div class="overflow-x-auto">
        <table class="min-w-[860px] w-full text-sm">
          <thead class="border-b border-neutral-100 bg-neutral-50">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Date</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Project</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Shift</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Progress</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Status</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Escalation</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Details</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each reportsPageRows as row (row.id)}
              <tr class="hover:bg-neutral-50">
                <td class="px-4 py-3 text-neutral-600">{fmtDate(row.report_date)}</td>
                <td class="px-4 py-3 text-neutral-900">{row.project_name}</td>
                <td class="px-4 py-3 text-neutral-600 capitalize">{row.shift.replace("_", " ")}</td>
                <td class="px-4 py-3 text-right font-semibold tabular-nums text-neutral-900">{row.progress_percent}%</td>
                <td class="px-4 py-3">
                  <span class={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${reportStatusClass(row.status)}`}>
                    {row.status.replace("_", " ")}
                  </span>
                </td>
                <td class="px-4 py-3 text-neutral-600">{row.escalation_required ? "Required" : "No"}</td>
                <td class="px-4 py-3 text-right">
                  <button
                    type="button"
                    onclick={() => toggleReportRow(row.id)}
                    aria-expanded={expandedReportRowId === row.id}
                    aria-label={expandedReportRowId === row.id ? "Collapse row details" : "Expand row details"}
                    class="inline-flex items-center text-xs font-semibold text-neutral-700 hover:text-neutral-900"
                  >
                    <span class={`transition-transform ${expandedReportRowId === row.id ? "rotate-180" : ""}`}>▾</span>
                  </button>
                </td>
              </tr>
              {#if expandedReportRowId === row.id}
                <tr class="bg-neutral-50/70">
                  <td colspan="7" class="px-4 pb-4 pt-0">
                    <div class="grid gap-3 pt-3 md:grid-cols-3">
                      <div class="rounded-lg border border-neutral-200 bg-white p-3">
                        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Weather</p>
                        <p class="mt-1 text-sm font-medium capitalize text-neutral-900">{row.weather}</p>
                        <p class="mt-1 text-xs text-neutral-600">
                          Delay: {Number(row.weather_delay_hours) > 0 ? `${row.weather_delay_hours}h` : "None"}
                        </p>
                        <p class="mt-1 text-xs text-neutral-600">{row.weather_notes || "--"}</p>
                      </div>
                      <div class="rounded-lg border border-neutral-200 bg-white p-3">
                        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Photos</p>
                        <p class="mt-1 text-lg font-bold tabular-nums text-neutral-900">{row.photo_count}</p>
                        <p class="mt-1 text-xs text-neutral-600">{row.photo_count === 1 ? "upload" : "uploads"}</p>
                      </div>
                      <div class="rounded-lg border border-neutral-200 bg-white p-3">
                        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Actions</p>
                        <button
                          onclick={() => openProjectModal(row.project)}
                          class="mt-1 text-xs font-medium text-neutral-700 hover:text-indigo-700 hover:underline"
                        >
                          View Project
                        </button>
                      </div>
                      <div class="rounded-lg border border-neutral-200 bg-white p-3 md:col-span-3">
                        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Notes</p>
                        <div class="mt-2 grid gap-2 text-xs md:grid-cols-2">
                          <p class="md:col-span-2">
                            <span class="font-semibold text-neutral-700">Trade Counts:</span>
                            Laborers: {row.laborers_count} | Skilled: {row.skilled_count} | Supervisors: {row.supervisors_count} | Subcontractors: {row.subcontractors_count} | Operators: {row.equipment_operators_count}
                          </p>
                          <p><span class="font-semibold text-neutral-700">Workforce Summary:</span> {row.workforce_summary || "--"}</p>
                          <p><span class="font-semibold text-neutral-700">Work Completed:</span> {row.work_completed || "--"}</p>
                          <p><span class="font-semibold text-neutral-700">Plan Next Day:</span> {row.planned_next_day || "--"}</p>
                          <p><span class="font-semibold text-neutral-700">Equipment Used:</span> {row.equipment_used || "--"}</p>
                          <p><span class="font-semibold text-neutral-700">Materials Delivered:</span> {row.materials_delivered || "--"}</p>
                          <p><span class="font-semibold text-neutral-700">Materials Consumed:</span> {row.materials_consumed || "--"}</p>
                          <p><span class="font-semibold text-neutral-700">Material Updates:</span> {row.material_updates || "--"}</p>
                          <p><span class="font-semibold text-neutral-700">Visitors Log:</span> {row.visitors_log || "--"}</p>
                          <p><span class="font-semibold text-neutral-700">Instructions Issued:</span> {row.instructions_issued || "--"}</p>
                          <p><span class="font-semibold text-neutral-700">Quality Observations:</span> {row.quality_observations || "--"}</p>
                          <p><span class="font-semibold text-neutral-700">Safety Observations:</span> {row.safety_observations || "--"}</p>
                          <p><span class="font-semibold text-neutral-700">Incidents:</span> {row.incidents || "--"}</p>
                          <p><span class="font-semibold text-neutral-700">Blockers:</span> {row.blockers || "--"}</p>
                        </div>
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
        <p class="text-xs text-neutral-500">Showing {reportsStart}-{reportsEnd} of {filteredReportRows.length}</p>
        <div class="flex items-center gap-2">
          <button onclick={() => (reportsPage = Math.max(1, reportsPage - 1))} disabled={reportsPage === 1} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 disabled:opacity-40">Previous</button>
          <span class="text-xs text-neutral-600">Page {reportsPage} of {reportsTotalPages}</span>
          <button onclick={() => (reportsPage = Math.min(reportsTotalPages, reportsPage + 1))} disabled={reportsPage === reportsTotalPages} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 disabled:opacity-40">Next</button>
        </div>
      </div>
    {/if}
  </section>

  <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-sm">
    <div class="border-b border-neutral-200 px-4 py-4">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Escalations</h2>
          <p class="mt-0.5 text-xs text-neutral-500">Capture field issues requiring cross-functional action.</p>
        </div>
        <button
          onclick={() => {
            resetEscalationForm();
            showEscalationForm = !showEscalationForm;
          }}
          class="rounded-lg bg-neutral-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-neutral-800"
        >
          {showEscalationForm ? "Close Form" : "+ New Escalation"}
        </button>
      </div>
      <div class="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <input type="text" bind:value={escalationsSearch} placeholder="Search escalations..." class="xl:col-span-2 rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
        <select bind:value={escalationsStatusFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          <option value="">All Statuses</option>
          {#each ESCALATION_STATUS_OPTIONS as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
        <select bind:value={escalationsSeverityFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          <option value="">All Severities</option>
          {#each ESCALATION_SEVERITY_OPTIONS as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
        <div class="grid grid-cols-2 gap-2">
          <select bind:value={escalationsSort} class="rounded-lg border border-neutral-200 bg-white px-2 py-2 text-sm">
            <option value="created_desc">Newest</option>
            <option value="created_asc">Oldest</option>
            <option value="due_asc">Due Date</option>
            <option value="severity_desc">Severity</option>
          </select>
          <select bind:value={escalationsPageSize} class="rounded-lg border border-neutral-200 bg-white px-2 py-2 text-sm">
            <option value={10}>10 / page</option>
            <option value={20}>20 / page</option>
            <option value={50}>50 / page</option>
          </select>
        </div>
      </div>
    </div>

    {#if showEscalationForm}
      <form onsubmit={createEscalation} class="grid gap-3 border-b border-neutral-200 bg-neutral-50 px-4 py-4 md:grid-cols-3">
        <select bind:value={escalationForm.project} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          <option value="">Select project</option>
          {#each projects as project}
            <option value={String(project.id)}>{project.name}</option>
          {/each}
        </select>
        <select bind:value={escalationForm.source_report} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          <option value="">No source report</option>
          {#each reportsForEscalationProject as report}
            <option value={String(report.id)}>{report.report_date} - {report.shift} - {report.status}</option>
          {/each}
        </select>
        <input type="text" bind:value={escalationForm.title} placeholder="Escalation title" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
        <textarea bind:value={escalationForm.description} rows="2" placeholder="Description" class="md:col-span-2 rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>
        <input type="text" bind:value={escalationForm.owner_name} placeholder="Owner name" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
        <select bind:value={escalationForm.severity} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          {#each ESCALATION_SEVERITY_OPTIONS as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
        <select bind:value={escalationForm.status} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          {#each ESCALATION_STATUS_OPTIONS as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
        <DateInput bind:value={escalationForm.due_date} />
        <textarea bind:value={escalationForm.resolution_notes} rows="2" placeholder="Resolution notes (optional)" class="md:col-span-2 rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>
        <label class="md:col-span-2 rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700">
          <span class="block text-xs font-semibold uppercase tracking-wider text-neutral-500">Supporting Photos/Documents</span>
          <input type="file" multiple onchange={onEscalationSupportingFilesSelected} class="mt-2 w-full text-sm" />
          {#if escalationSupportingFiles.length > 0}
            <p class="mt-2 text-xs text-neutral-500">{escalationSupportingFiles.length} file(s) selected</p>
          {/if}
        </label>
        <div class="flex items-end justify-end gap-2">
          {#if isDev}
            <button type="button" onclick={devFillEscalation} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>
          {/if}
          <button
            type="submit"
            disabled={saving}
            class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save Escalation"}
          </button>
        </div>
      </form>
    {/if}

    {#if loading}
      <div class="flex items-center justify-center py-12">
        <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
      </div>
    {:else if filteredEscalationRows.length === 0}
      <div class="px-6 py-12 text-center text-sm text-neutral-500">No escalations match current filters.</div>
    {:else}
      <div class="overflow-x-auto">
        <table class="min-w-[860px] w-full text-sm">
          <thead class="border-b border-neutral-100 bg-neutral-50">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Created</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Project</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Title</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Severity</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Status</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Details</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each escalationsPageRows as row (row.id)}
              <tr class="hover:bg-neutral-50">
                <td class="px-4 py-3 text-neutral-600">{fmtDate(row.created_at)}</td>
                <td class="px-4 py-3 text-neutral-900">{row.project_name}</td>
                <td class="px-4 py-3 text-neutral-900">
                  <p class="font-medium">{row.title}</p>
                </td>
                <td class="px-4 py-3">
                  <span class={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${escalationSeverityClass(row.severity)}`}>
                    {row.severity.replace("_", " ")}
                  </span>
                </td>
                <td class="px-4 py-3">
                  <span class={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${escalationStatusClass(row.status)}`}>
                    {row.status.replace("_", " ")}
                  </span>
                </td>
                <td class="px-4 py-3 text-right">
                  <button
                    type="button"
                    onclick={() => toggleEscalationRow(row.id)}
                    aria-expanded={expandedEscalationRowId === row.id}
                    aria-label={expandedEscalationRowId === row.id ? "Collapse row details" : "Expand row details"}
                    class="inline-flex items-center text-xs font-semibold text-neutral-700 hover:text-neutral-900"
                  >
                    <span class={`transition-transform ${expandedEscalationRowId === row.id ? "rotate-180" : ""}`}>▾</span>
                  </button>
                </td>
              </tr>
              {#if expandedEscalationRowId === row.id}
                <tr class="bg-neutral-50/70">
                  <td colspan="6" class="px-4 pb-4 pt-0">
                    <div class="grid gap-3 pt-3 md:grid-cols-3">
                      <div class="rounded-lg border border-neutral-200 bg-white p-3">
                        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Owner</p>
                        <p class="mt-1 text-sm font-medium text-neutral-900">{row.owner_name || "--"}</p>
                      </div>
                      <div class="rounded-lg border border-neutral-200 bg-white p-3">
                        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Due Date</p>
                        <p class="mt-1 text-sm font-medium text-neutral-900">{fmtDate(row.due_date)}</p>
                        {#if row.is_overdue}
                          <p class="mt-1 text-xs font-semibold text-rose-600">Overdue</p>
                        {/if}
                      </div>
                      <div class="rounded-lg border border-neutral-200 bg-white p-3">
                        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Actions</p>
                        <button
                          onclick={() => openProjectModal(row.project)}
                          class="mt-1 text-xs font-medium text-neutral-700 hover:text-indigo-700 hover:underline"
                        >
                          View Project
                        </button>
                      </div>
                      <div class="rounded-lg border border-neutral-200 bg-white p-3 md:col-span-3">
                        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Context</p>
                        <div class="mt-2 grid gap-2 text-xs md:grid-cols-2">
                          <p><span class="font-semibold text-neutral-700">Source Report:</span> {fmtDate(row.source_report_date)}</p>
                          <p><span class="font-semibold text-neutral-700">Location:</span> {row.location || "--"}</p>
                          <p><span class="font-semibold text-neutral-700">Issue Category:</span> {row.issue_category.replaceAll("_", " ")}</p>
                          <p><span class="font-semibold text-neutral-700">Issue Type:</span> {row.issue_type.replaceAll("_", " ")}</p>
                          <p><span class="font-semibold text-neutral-700">Weather:</span> {row.weather_condition || "--"}</p>
                          <p><span class="font-semibold text-neutral-700">Weather Delay:</span> {Number(row.weather_delay_hours) > 0 ? `${row.weather_delay_hours}h` : "--"}</p>
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
                    </div>
                  </td>
                </tr>
              {/if}
            {/each}
          </tbody>
        </table>
      </div>
      <div class="flex items-center justify-between border-t border-neutral-100 px-4 py-3">
        <p class="text-xs text-neutral-500">Showing {escalationsStart}-{escalationsEnd} of {filteredEscalationRows.length}</p>
        <div class="flex items-center gap-2">
          <button onclick={() => (escalationsPage = Math.max(1, escalationsPage - 1))} disabled={escalationsPage === 1} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 disabled:opacity-40">Previous</button>
          <span class="text-xs text-neutral-600">Page {escalationsPage} of {escalationsTotalPages}</span>
          <button onclick={() => (escalationsPage = Math.min(escalationsTotalPages, escalationsPage + 1))} disabled={escalationsPage === escalationsTotalPages} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 disabled:opacity-40">Next</button>
        </div>
      </div>
    {/if}
  </section>
</div>

{#if showReportForm}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-neutral-900/55 p-4 backdrop-blur-[1px]">
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="daily-site-report-modal-title"
      class="max-h-[92vh] w-full max-w-6xl overflow-y-auto rounded-2xl border border-neutral-200 bg-white shadow-2xl"
    >
      <div class="flex items-start justify-between gap-4 border-b border-neutral-200 px-5 py-4 sm:px-6">
        <div>
          <h3 id="daily-site-report-modal-title" class="text-base font-semibold text-neutral-900">New Daily Site Report</h3>
          <p class="mt-1 text-xs text-neutral-500">Capture execution progress, weather impact, observations, and evidence.</p>
        </div>
        <button
          type="button"
          onclick={() => (showReportForm = false)}
          class="rounded-lg border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-50"
        >
          Close
        </button>
      </div>

      <form onsubmit={createSiteReport} class="space-y-4 px-5 py-5 sm:px-6">
        <div class="grid gap-3 md:grid-cols-3">
          <label>
            <span class="mb-1 block text-xs font-medium text-neutral-600">Project</span>
            <select bind:value={reportForm.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
              <option value="">Select project</option>
              {#each projects as project}
                <option value={String(project.id)}>{project.name}</option>
              {/each}
            </select>
          </label>
          <label>
            <span class="mb-1 block text-xs font-medium text-neutral-600">Report Date</span>
            <DateInput bind:value={reportForm.report_date} />
          </label>
          <label>
            <span class="mb-1 block text-xs font-medium text-neutral-600">Shift</span>
            <select bind:value={reportForm.shift} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
              {#each SHIFT_OPTIONS as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </label>

          <label>
            <span class="mb-1 block text-xs font-medium text-neutral-600">Weather</span>
            <select bind:value={reportForm.weather} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
              {#each WEATHER_OPTIONS as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </label>
          <label>
            <span class="mb-1 block text-xs font-medium text-neutral-600">Weather Delay Hours</span>
            <input
              type="number"
              min="0"
              step="0.25"
              bind:value={reportForm.weather_delay_hours}
              placeholder="Weather delay hours"
              class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"
            />
          </label>
          <label>
            <span class="mb-1 block text-xs font-medium text-neutral-600">Progress (%)</span>
            <input
              type="number"
              min="0"
              max="100"
              step="0.1"
              bind:value={reportForm.progress_percent}
              placeholder="Progress %"
              class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"
            />
          </label>

          <label>
            <span class="mb-1 block text-xs font-medium text-neutral-600">Laborers Count</span>
            <input type="number" min="0" bind:value={reportForm.laborers_count} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
          </label>
          <label>
            <span class="mb-1 block text-xs font-medium text-neutral-600">Skilled Workers Count</span>
            <input type="number" min="0" bind:value={reportForm.skilled_count} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
          </label>
          <label>
            <span class="mb-1 block text-xs font-medium text-neutral-600">Supervisors Count</span>
            <input type="number" min="0" bind:value={reportForm.supervisors_count} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
          </label>
          <label>
            <span class="mb-1 block text-xs font-medium text-neutral-600">Subcontractors Count</span>
            <input type="number" min="0" bind:value={reportForm.subcontractors_count} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
          </label>
          <label>
            <span class="mb-1 block text-xs font-medium text-neutral-600">Equipment Operators Count</span>
            <input type="number" min="0" bind:value={reportForm.equipment_operators_count} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
          </label>
          <div></div>

          <label>
            <span class="mb-1 block text-xs font-medium text-neutral-600">Workforce Summary</span>
            <textarea bind:value={reportForm.workforce_summary} rows="2" placeholder="Workforce summary" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>
          </label>
          <label>
            <span class="mb-1 block text-xs font-medium text-neutral-600">Work Completed</span>
            <textarea bind:value={reportForm.work_completed} rows="2" placeholder="Work completed today" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>
          </label>
          <label>
            <span class="mb-1 block text-xs font-medium text-neutral-600">Plan Next Day</span>
            <textarea bind:value={reportForm.planned_next_day} rows="2" placeholder="Plan for next day" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>
          </label>
          <label>
            <span class="mb-1 block text-xs font-medium text-neutral-600">Equipment Used</span>
            <textarea bind:value={reportForm.equipment_used} rows="2" placeholder="Equipment used today" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>
          </label>
          <label>
            <span class="mb-1 block text-xs font-medium text-neutral-600">Materials Delivered</span>
            <textarea bind:value={reportForm.materials_delivered} rows="2" placeholder="Materials delivered today" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>
          </label>
          <label>
            <span class="mb-1 block text-xs font-medium text-neutral-600">Materials Consumed</span>
            <textarea bind:value={reportForm.materials_consumed} rows="2" placeholder="Materials consumed today" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>
          </label>
          <label>
            <span class="mb-1 block text-xs font-medium text-neutral-600">Material Updates</span>
            <textarea bind:value={reportForm.material_updates} rows="2" placeholder="Material updates" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>
          </label>
          <label>
            <span class="mb-1 block text-xs font-medium text-neutral-600">Visitors Log</span>
            <textarea bind:value={reportForm.visitors_log} rows="2" placeholder="Visitors on site today" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>
          </label>
          <label>
            <span class="mb-1 block text-xs font-medium text-neutral-600">Instructions Issued</span>
            <textarea bind:value={reportForm.instructions_issued} rows="2" placeholder="Site instructions issued today" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>
          </label>
          <label>
            <span class="mb-1 block text-xs font-medium text-neutral-600">Quality Observations</span>
            <textarea bind:value={reportForm.quality_observations} rows="2" placeholder="Quality observations" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>
          </label>
          <label>
            <span class="mb-1 block text-xs font-medium text-neutral-600">Safety Observations</span>
            <textarea bind:value={reportForm.safety_observations} rows="2" placeholder="Safety observations" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>
          </label>
          <label>
            <span class="mb-1 block text-xs font-medium text-neutral-600">Incidents</span>
            <textarea bind:value={reportForm.incidents} rows="2" placeholder="Incidents" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>
          </label>
          <label>
            <span class="mb-1 block text-xs font-medium text-neutral-600">Blockers / Delays</span>
            <textarea bind:value={reportForm.blockers} rows="2" placeholder="Blockers / delays" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>
          </label>
          <label>
            <span class="mb-1 block text-xs font-medium text-neutral-600">Weather Notes</span>
            <textarea bind:value={reportForm.weather_notes} rows="2" placeholder="Weather notes" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea>
          </label>

          <label>
            <span class="mb-1 block text-xs font-medium text-neutral-600">Status</span>
            <select bind:value={reportForm.status} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
              {#each REPORT_STATUS_OPTIONS as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </label>
          <label>
            <span class="mb-1 block text-xs font-medium text-neutral-600">Escalation</span>
            <span class="inline-flex w-full items-center gap-2 rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700">
              <input type="checkbox" bind:checked={reportForm.escalation_required} class="h-4 w-4 rounded border-neutral-300" />
              Escalation required
            </span>
          </label>
          <div></div>

          <label class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700 md:col-span-3">
            <span class="block text-xs font-semibold uppercase tracking-wider text-neutral-500">Photo Uploads</span>
            <input type="file" multiple onchange={onReportPhotosSelected} class="mt-2 w-full text-sm" />
            {#if reportPhotoFiles.length > 0}
              <p class="mt-2 text-xs text-neutral-500">{reportPhotoFiles.length} file(s) selected</p>
            {/if}
          </label>
        </div>

        <div class="flex items-center justify-end gap-2 border-t border-neutral-200 pt-4">
          <button
            type="button"
            onclick={() => (showReportForm = false)}
            class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
          >
            Cancel
          </button>
          {#if isDev}
            <button type="button" onclick={devFillReport} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>
          {/if}
          <button
            type="submit"
            disabled={saving}
            class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save Site Report"}
          </button>
        </div>
      </form>
    </div>
  </div>
{/if}

<!-- Project Detail Modal -->
{#if showProjectModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" style="backdrop-filter: blur(4px)" onclick={() => { showProjectModal = false; projectModalData = null; }} onkeydown={(e) => { if (e.key === "Escape") { showProjectModal = false; projectModalData = null; }}} role="presentation">
    <div class="w-full max-w-lg rounded-2xl bg-white shadow-2xl overflow-hidden" onclick={(e) => e.stopPropagation()} onkeydown={() => {}} role="dialog" aria-modal="true" tabindex="-1">
      <!-- Dark Header -->
      <div class="bg-neutral-900 px-6 py-4 flex items-start justify-between">
        <div>
          <h2 class="text-lg font-semibold text-white">{projectModalData?.name || "Loading..."}</h2>
          {#if projectModalData}
            <span class="mt-1 inline-block rounded-full border border-neutral-600 px-2.5 py-0.5 text-[10px] font-semibold text-neutral-300 capitalize">{projectModalData.status.replace(/_/g, " ")}</span>
          {/if}
        </div>
        <button onclick={() => { showProjectModal = false; projectModalData = null; }} class="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-800 hover:text-white" aria-label="Close">
          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
        </button>
      </div>

      {#if projectModalLoading}
        <div class="p-8 text-center text-sm text-neutral-400">Loading project details...</div>
      {:else if projectModalData}
        <div class="p-6 space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
              <p class="text-[9px] font-semibold text-neutral-400 uppercase">Start Date</p>
              <p class="mt-1 text-sm font-semibold text-neutral-900 tabular-nums">{projectModalData.start_date || "Not set"}</p>
            </div>
            <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
              <p class="text-[9px] font-semibold text-neutral-400 uppercase">Target End</p>
              <p class="mt-1 text-sm font-semibold text-neutral-900 tabular-nums">{projectModalData.target_end_date || "Not set"}</p>
            </div>
          </div>
          {#if projectModalData.budget}
            <div class="rounded-lg border border-emerald-200 bg-emerald-50 p-3">
              <p class="text-[9px] font-semibold text-emerald-500 uppercase">Budget</p>
              <p class="mt-1 text-lg font-bold text-emerald-700 tabular-nums">{currency.format(Number(projectModalData.budget))}</p>
            </div>
          {/if}
          {#if projectModalData.description}
            <div>
              <p class="text-[9px] font-semibold text-neutral-400 uppercase mb-1">Description</p>
              <p class="text-sm text-neutral-700">{projectModalData.description}</p>
            </div>
          {/if}
        </div>
      {/if}
    </div>
  </div>
{/if}

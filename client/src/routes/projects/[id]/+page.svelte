<script lang="ts">
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { canCreateRepositoryDocument } from "$lib/permissions";
  import { toast } from "$lib/stores/toast.svelte";
  import Breadcrumb from "$lib/components/Breadcrumb.svelte";
  import AddDocumentModal from "$lib/components/documents/AddDocumentModal.svelte";
  import DocumentDetailDrawer from "$lib/components/documents/DocumentDetailDrawer.svelte";
  import DocumentRecordsTable from "$lib/components/documents/DocumentRecordsTable.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import { onboarding } from "$lib/stores/onboarding.svelte";
  import { PROJECT_TAB_MODULE_MAP, isModuleEnabled } from "$lib/modules";
  import type {
    Project, ProjectPhase, ProjectMilestone, ProjectTask,
    ProjectCostEntry, ProjectTimelineData, ProjectType, LandStatus, PaginatedResponse,
    ProjectSetupConfigItem,
  } from "$lib/types";
  import ProjectTimeline from "$lib/components/ProjectTimeline.svelte";
  import PropertyMap from "$lib/components/PropertyMap.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DateInput from "$lib/components/DateInput.svelte";

  const projectId = $derived($page.params.id);

  let project = $state<Project | null>(null);
  let setupConfig = $state<ProjectSetupConfigItem | null>(null);
  let loading = $state(true);
  let activeTab = $state<"overview" | "phases" | "milestones" | "tasks" | "costs" | "documents" | "timeline" | "cap_table" | "distributions">("overview");

  // Data loaded per-tab
  let milestonesByPhase = $state<Record<number, ProjectMilestone[]>>({});
  let tasksByPhase = $state<Record<number, ProjectTask[]>>({});
  let costsByPhase = $state<Record<number, ProjectCostEntry[]>>({});
  let timelineData = $state<ProjectTimelineData | null>(null);
  let showAddDocumentModal = $state(false);
  let documentDrawerId = $state<number | null>(null);
  let documentsRefreshKey = $state(0);
  const canAddRepositoryDocument = $derived(canCreateRepositoryDocument());

  const enabledModules = $derived(onboarding.enabledModules);

  const allTabs = [
    { key: "overview" as const, label: "Overview" },
    { key: "phases" as const, label: "Phases" },
    { key: "milestones" as const, label: "Milestones" },
    { key: "tasks" as const, label: "Tasks" },
    { key: "costs" as const, label: "Costs" },
    { key: "documents" as const, label: "Documents" },
    { key: "cap_table" as const, label: "Cap Table" },
    { key: "distributions" as const, label: "Distributions" },
    { key: "timeline" as const, label: "Timeline" },
  ];

  const tabs = $derived(
    allTabs.filter((t) => isModuleEnabled(enabledModules, PROJECT_TAB_MODULE_MAP[t.key]))
  );

  const costCategoryLabels: Record<string, string> = {
    materials: "Materials",
    labor: "Labor",
    permits: "Permits & Fees",
    equipment: "Equipment",
    subcontractor: "Subcontractor",
    other: "Other",
  };

  const projectTypeLabels: Record<ProjectType, string> = {
    residential: "Residential",
    mixed_use: "Mixed-Use",
    commercial: "Commercial",
    infrastructure: "Infrastructure",
  };

  const landStatusLabels: Record<string, string> = {
    freehold: "Freehold",
    leasehold: "Leasehold",
    under_contract: "Under Contract",
    to_acquire: "To Acquire",
    joint_venture: "Joint Venture",
  };

  $effect(() => {
    void projectId;
    loadProject();
    loadSetupConfig();
    loadEntityTemplates();
  });

  async function loadProject() {
    loading = true;
    try {
      project = await api.get<Project>(`/projects/${projectId}/`);
    } catch (err) {
      console.error("[projects/detail] loadProject failed:", err);
      project = null;
    }
    loading = false;
  }

  async function loadSetupConfig() {
    try {
      const res = await api.get<PaginatedResponse<ProjectSetupConfigItem>>("/projects/setup/", { project: String(projectId) });
      setupConfig = res.results[0] ?? null;
    } catch {
      setupConfig = null;
    }
  }

  type RecommendedAction = { title: string; description: string; cta: string; href: string; tone: "indigo" | "amber" | "emerald" };

  const recommendedAction = $derived.by((): RecommendedAction | null => {
    if (!project) return null;
    // 1. Kickoff not yet complete
    if (setupConfig && !setupConfig.is_complete) {
      return {
        title: "Continue project kickoff",
        description: `Pick up at "${setupConfig.current_step_display}" to finish kicking off this project.`,
        cta: "Continue Kickoff",
        href: "/projects/project-setup",
        tone: "amber",
      };
    }
    // 2. BoQ baseline not yet initialized
    if (setupConfig && !setupConfig.boq_initialized) {
      return {
        title: "Initialize BoQ baseline",
        description: "Build the Bill of Quantities baseline so procurement, payroll, and field operations have something to attach costs to.",
        cta: "Open Budget & Cost",
        href: "/projects/budget-cost",
        tone: "indigo",
      };
    }
    // 3. No phases defined yet
    if (project.phases.length === 0) {
      return {
        title: "Define project phases",
        description: "Break the work into phases and milestones — this becomes the WBS that drives scheduling and stage gates.",
        cta: "Add Phases",
        href: "/projects/phases-milestones",
        tone: "indigo",
      };
    }
    // 4. Still planning — push toward feasibility validation before flipping to execution
    if (project.status === "planning") {
      return {
        title: "Validate feasibility & viability",
        description: "Formalize the business case (IRR, demand, risk) before flipping this project into active execution.",
        cta: "Open Feasibility",
        href: "/projects/feasibility-viability",
        tone: "indigo",
      };
    }
    // 5. Active project, fully initialized — nudge toward stage gate reviews
    if (project.status === "in_progress" && project.phases.length > 0) {
      return {
        title: "Drive stage gate reviews",
        description: "Use stage gate reviews to formally close each phase before advancing to the next.",
        cta: "Open Stage Gates",
        href: "/projects/milestones-stage-gates",
        tone: "emerald",
      };
    }
    return null;
  });

  function fmt(value: string | null): string {
    if (!value) return "\u2014";
    return currency.formatCompact(value);
  }

  function fmtDate(value: string | null): string {
    if (!value) return "\u2014";
    return new Date(value).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  }

  function ownershipTotal(value: Project["ownership_allocations"]): number {
    if (!value || value.length === 0) return 0;
    return value.reduce((sum, row) => sum + Number(row.ownership_percentage || 0), 0);
  }

  function apiErrorDetail(err: unknown): string {
    if (err instanceof ApiError) {
      if (err.status >= 500) return "A server error occurred. Please try again or contact support.";
      const detail = err.data?.detail;
      if (typeof detail === "string" && detail.trim().length > 0) return detail;
      if (err.fieldErrors) {
        const msgs = Object.entries(err.fieldErrors)
          .map(([field, errors]) => `${field.replace(/_/g, " ")}: ${errors[0]}`)
          .slice(0, 2);
        if (msgs.length) return msgs.join(". ");
      }
      if (err.status === 403) return "You do not have permission for this action.";
      if (err.status === 404) return "Resource not found.";
    }
    return "An unexpected error occurred. Please try again.";
  }

  function listRows<T>(payload: PaginatedResponse<T> | T[]): T[] {
    if (Array.isArray(payload)) return payload;
    return payload.results ?? [];
  }

  async function deleteProject() {
    if (!confirm("Delete this project and all its phases, milestones, tasks, and costs?")) return;
    try {
      await api.delete(`/projects/${projectId}/`);
      toast.success("Project deleted", "The project has been permanently removed");
      goto("/projects");
    } catch (err) {
      toast.error("Failed to delete project", apiErrorDetail(err));
    }
  }

  // --- Dev helpers ---
  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  // --- Entity templates (for Add pickers) ---
  interface RACIEntry { task: string; responsible: string; accountable: string; consulted: string; informed: string }
  interface KeyTask { name: string; description: string }
  interface Deliverable { name: string; description: string; is_mandatory: boolean }
  interface ResourceReq { type: string; description: string; quantity: string }
  interface PhaseRisk { risk: string; likelihood: string; impact: string; mitigation: string }
  interface SuccessMetric { metric: string; target: string; measurement_method: string }
  interface ExitCriterion { criterion: string; verification_method: string }

  interface PhaseTemplateDef {
    id: number; name: string; description: string; weight: number; budget_pct: string;
    objective: string; estimated_duration_days: number | null; phase_owner_role: string;
    raci_matrix: RACIEntry[]; approval_authority: string;
    key_tasks: KeyTask[]; deliverables: Deliverable[]; out_of_scope: string;
    resource_requirements: ResourceReq[]; phase_risks: PhaseRisk[]; budget_notes: string;
    success_metrics: SuccessMetric[]; exit_criteria: ExitCriterion[]; lessons_learned_prompt: string;
  }
  interface MilestoneSuccessCriterion { criterion: string; verification_method: string }
  interface MilestoneDeliverable { name: string; description: string; is_mandatory: boolean }
  interface MilestoneDependencyLink { milestone: string; dependency_type: string; lag_days: number }
  interface MilestoneStakeholder { role: string; notification_trigger: string }
  interface MilestoneTemplateDef {
    id: number; name: string; description: string; sort_order: number; phase_sort_order: number;
    reference_code: string; typical_offset_days: number | null;
    success_criteria: MilestoneSuccessCriterion[]; key_deliverables: MilestoneDeliverable[];
    predecessors: MilestoneDependencyLink[]; successors: MilestoneDependencyLink[];
    owner_role: string; approver_role: string; stakeholders_to_notify: MilestoneStakeholder[];
  }
  interface TaskCollaborator { role: string; responsibility: string }
  interface TaskDependencyLink { task: string; dependency_type: string; lag_days: number }
  interface TaskDoDItem { criterion: string; is_required: boolean }
  interface TaskTool { name: string; description: string }
  interface TaskRefLink { title: string; url: string }
  interface TaskTemplateDef {
    id: number; name: string; description: string; assigned_role: string; priority: string;
    sort_order: number; phase_sort_order: number;
    reference_code: string; reviewer_role: string; collaborators: TaskCollaborator[];
    estimated_effort_hours: number | null;
    predecessors: TaskDependencyLink[]; successors: TaskDependencyLink[];
    definition_of_done: TaskDoDItem[];
    tools_required: TaskTool[]; reference_links: TaskRefLink[];
  }

  let phaseTemplates = $state<PhaseTemplateDef[]>([]);
  let milestoneTemplates = $state<MilestoneTemplateDef[]>([]);
  let taskTemplates = $state<TaskTemplateDef[]>([]);
  let selectedPhaseTemplate = $state<PhaseTemplateDef | null>(null);
  let expandedPhases = $state<Record<number, boolean>>({});
  let expandedMilestones = $state<Record<number, boolean>>({});
  let expandedTasks = $state<Record<number, boolean>>({});

  function togglePhaseExpanded(id: number) {
    expandedPhases = { ...expandedPhases, [id]: !expandedPhases[id] };
  }
  function toggleMilestoneExpanded(id: number) {
    expandedMilestones = { ...expandedMilestones, [id]: !expandedMilestones[id] };
  }
  function toggleTaskExpanded(id: number) {
    expandedTasks = { ...expandedTasks, [id]: !expandedTasks[id] };
  }

  function phaseHasSections(p: ProjectPhase): boolean {
    return !!(p.objective || p.phase_owner_role || p.raci_matrix?.length || p.approval_authority || p.key_tasks?.length || p.deliverables?.length || p.out_of_scope || p.resource_requirements?.length || p.phase_risks?.length || p.budget_notes || p.success_metrics?.length || p.exit_criteria?.length || p.lessons_learned_prompt);
  }
  function milestoneHasSections(m: ProjectMilestone): boolean {
    return !!(m.reference_code || m.typical_offset_days || m.success_criteria?.length || m.key_deliverables?.length || m.predecessors?.length || m.successors?.length || m.owner_role || m.approver_role || m.stakeholders_to_notify?.length);
  }
  function taskHasSections(t: ProjectTask): boolean {
    return !!(t.reference_code || t.reviewer_role || t.collaborators?.length || t.estimated_effort_hours || t.predecessors?.length || t.successors?.length || t.definition_of_done?.length || t.tools_required?.length || t.reference_links?.length);
  }

  let selectedMilestoneTemplate = $state<MilestoneTemplateDef | null>(null);
  let selectedTaskTemplate = $state<TaskTemplateDef | null>(null);

  async function loadEntityTemplates() {
    const [p, m, t] = await Promise.all([
      api.get<PhaseTemplateDef[]>("/settings/entity-templates/phases/"),
      api.get<MilestoneTemplateDef[]>("/settings/entity-templates/milestones/"),
      api.get<TaskTemplateDef[]>("/settings/entity-templates/tasks/"),
    ]);
    phaseTemplates = p;
    milestoneTemplates = m;
    taskTemplates = t;
  }

  function applyPhaseTemplate(id: number) {
    const tmpl = phaseTemplates.find(t => t.id === id);
    if (!tmpl) { selectedPhaseTemplate = null; return; }
    selectedPhaseTemplate = tmpl;
    phaseForm = {
      ...phaseForm,
      name: tmpl.name,
      description: tmpl.description,
      weight: String(tmpl.weight),
      // Section data transferred to phase
      objective: tmpl.objective,
      estimated_duration_days: tmpl.estimated_duration_days != null ? String(tmpl.estimated_duration_days) : "",
      phase_owner_role: tmpl.phase_owner_role,
      raci_matrix: tmpl.raci_matrix,
      approval_authority: tmpl.approval_authority,
      key_tasks: tmpl.key_tasks,
      deliverables: tmpl.deliverables,
      out_of_scope: tmpl.out_of_scope,
      resource_requirements: tmpl.resource_requirements,
      phase_risks: tmpl.phase_risks,
      budget_notes: tmpl.budget_notes,
      success_metrics: tmpl.success_metrics,
      exit_criteria: tmpl.exit_criteria,
      lessons_learned_prompt: tmpl.lessons_learned_prompt,
    };
  }

  function applyMilestoneTemplate(id: number) {
    const tmpl = milestoneTemplates.find(t => t.id === id);
    if (!tmpl) { selectedMilestoneTemplate = null; return; }
    selectedMilestoneTemplate = tmpl;
    milestoneForm = {
      ...milestoneForm,
      name: tmpl.name,
      reference_code: tmpl.reference_code || "",
      typical_offset_days: tmpl.typical_offset_days ?? "",
      success_criteria: tmpl.success_criteria?.map(c => ({ ...c })) ?? [],
      key_deliverables: tmpl.key_deliverables?.map(d => ({ ...d })) ?? [],
      predecessors: tmpl.predecessors?.map(p => ({ ...p })) ?? [],
      successors: tmpl.successors?.map(s => ({ ...s })) ?? [],
      owner_role: tmpl.owner_role || "",
      approver_role: tmpl.approver_role || "",
      stakeholders_to_notify: tmpl.stakeholders_to_notify?.map(s => ({ ...s })) ?? [],
    };
  }

  function applyTaskTemplate(id: number) {
    const tmpl = taskTemplates.find(t => t.id === id);
    if (!tmpl) { selectedTaskTemplate = null; return; }
    selectedTaskTemplate = tmpl;
    taskForm = {
      ...taskForm,
      name: tmpl.name,
      assigned_to: tmpl.assigned_role,
      reference_code: tmpl.reference_code || "",
      reviewer_role: tmpl.reviewer_role || "",
      collaborators: tmpl.collaborators?.map(c => ({ ...c })) ?? [],
      estimated_effort_hours: tmpl.estimated_effort_hours ?? "",
      predecessors: tmpl.predecessors?.map(p => ({ ...p })) ?? [],
      successors: tmpl.successors?.map(s => ({ ...s })) ?? [],
      definition_of_done: tmpl.definition_of_done?.map(d => ({ ...d })) ?? [],
      tools_required: tmpl.tools_required?.map(t => ({ ...t })) ?? [],
      reference_links: tmpl.reference_links?.map(r => ({ ...r })) ?? [],
    };
  }

  // --- Phase CRUD ---
  let showPhaseForm = $state(false);
  let editingPhase = $state<ProjectPhase | null>(null);
  let phaseSupportingFiles = $state<File[]>([]);
  let phaseForm = $state({
    name: "", description: "", sort_order: "0", status: "not_started",
    planned_start_date: "", planned_end_date: "",
    actual_start_date: "", actual_end_date: "",
    planned_budget: "", weight: "1",
    // Section fields
    objective: "", estimated_duration_days: "" as string, phase_owner_role: "",
    raci_matrix: [] as RACIEntry[], approval_authority: "",
    key_tasks: [] as KeyTask[], deliverables: [] as Deliverable[], out_of_scope: "",
    resource_requirements: [] as ResourceReq[], phase_risks: [] as PhaseRisk[], budget_notes: "",
    success_metrics: [] as SuccessMetric[], exit_criteria: [] as ExitCriterion[], lessons_learned_prompt: "",
  });

  const emptyPhaseForm = () => ({
    name: "", description: "", sort_order: String(project?.phases.length ?? 0), status: "not_started",
    planned_start_date: "", planned_end_date: "", actual_start_date: "", actual_end_date: "",
    planned_budget: "", weight: "1",
    objective: "", estimated_duration_days: "" as string, phase_owner_role: "",
    raci_matrix: [] as RACIEntry[], approval_authority: "",
    key_tasks: [] as KeyTask[], deliverables: [] as Deliverable[], out_of_scope: "",
    resource_requirements: [] as ResourceReq[], phase_risks: [] as PhaseRisk[], budget_notes: "",
    success_metrics: [] as SuccessMetric[], exit_criteria: [] as ExitCriterion[], lessons_learned_prompt: "",
  });

  // --- Array helpers for phase section forms ---
  function addRaciRow() { phaseForm.raci_matrix = [...phaseForm.raci_matrix, { task: "", responsible: "", accountable: "", consulted: "", informed: "" }]; }
  function removeRaciRow(i: number) { phaseForm.raci_matrix = phaseForm.raci_matrix.filter((_: any, idx: number) => idx !== i); }
  function addKeyTask() { phaseForm.key_tasks = [...phaseForm.key_tasks, { name: "", description: "" }]; }
  function removeKeyTask(i: number) { phaseForm.key_tasks = phaseForm.key_tasks.filter((_: any, idx: number) => idx !== i); }
  function addDeliverable() { phaseForm.deliverables = [...phaseForm.deliverables, { name: "", description: "", is_mandatory: false }]; }
  function removeDeliverable(i: number) { phaseForm.deliverables = phaseForm.deliverables.filter((_: any, idx: number) => idx !== i); }
  function addResource() { phaseForm.resource_requirements = [...phaseForm.resource_requirements, { type: "human", description: "", quantity: "" }]; }
  function removeResource(i: number) { phaseForm.resource_requirements = phaseForm.resource_requirements.filter((_: any, idx: number) => idx !== i); }
  function addRisk() { phaseForm.phase_risks = [...phaseForm.phase_risks, { risk: "", likelihood: "medium", impact: "medium", mitigation: "" }]; }
  function removeRisk(i: number) { phaseForm.phase_risks = phaseForm.phase_risks.filter((_: any, idx: number) => idx !== i); }
  function addMetric() { phaseForm.success_metrics = [...phaseForm.success_metrics, { metric: "", target: "", measurement_method: "" }]; }
  function removeMetric(i: number) { phaseForm.success_metrics = phaseForm.success_metrics.filter((_: any, idx: number) => idx !== i); }
  function addExitCriterion() { phaseForm.exit_criteria = [...phaseForm.exit_criteria, { criterion: "", verification_method: "" }]; }
  function removeExitCriterion(i: number) { phaseForm.exit_criteria = phaseForm.exit_criteria.filter((_: any, idx: number) => idx !== i); }

  function openAddPhase() {
    editingPhase = null;
    phaseSupportingFiles = [];
    selectedPhaseTemplate = null;
    phaseForm = emptyPhaseForm();
    showPhaseForm = true;
  }

  function openEditPhase(p: ProjectPhase) {
    editingPhase = p;
    phaseSupportingFiles = [];
    selectedPhaseTemplate = null;
    phaseForm = {
      name: p.name, description: p.description, sort_order: String(p.sort_order), status: p.status,
      planned_start_date: p.planned_start_date ?? "", planned_end_date: p.planned_end_date ?? "",
      actual_start_date: p.actual_start_date ?? "", actual_end_date: p.actual_end_date ?? "",
      planned_budget: p.planned_budget ?? "", weight: String(p.weight),
      objective: p.objective ?? "", estimated_duration_days: p.estimated_duration_days != null ? String(p.estimated_duration_days) : "",
      phase_owner_role: p.phase_owner_role ?? "",
      raci_matrix: p.raci_matrix ?? [], approval_authority: p.approval_authority ?? "",
      key_tasks: p.key_tasks ?? [], deliverables: p.deliverables ?? [], out_of_scope: p.out_of_scope ?? "",
      resource_requirements: p.resource_requirements ?? [], phase_risks: p.phase_risks ?? [], budget_notes: p.budget_notes ?? "",
      success_metrics: p.success_metrics ?? [], exit_criteria: p.exit_criteria ?? [], lessons_learned_prompt: p.lessons_learned_prompt ?? "",
    };
    showPhaseForm = true;
  }

  async function savePhase() {
    try {
      const payload = {
        ...phaseForm,
        sort_order: Number(phaseForm.sort_order),
        weight: Number(phaseForm.weight),
        planned_start_date: phaseForm.planned_start_date || null,
        planned_end_date: phaseForm.planned_end_date || null,
        actual_start_date: phaseForm.actual_start_date || null,
        actual_end_date: phaseForm.actual_end_date || null,
        planned_budget: phaseForm.planned_budget || null,
        estimated_duration_days: phaseForm.estimated_duration_days ? Number(phaseForm.estimated_duration_days) : null,
      };
      let savedPhase: ProjectPhase;
      if (editingPhase) {
        savedPhase = await api.patch<ProjectPhase>(`/projects/${projectId}/phases/${editingPhase.id}/`, payload);
        toast.success("Phase updated", `"${phaseForm.name}" has been saved`);
      } else {
        savedPhase = await api.post<ProjectPhase>(`/projects/${projectId}/phases/`, payload);
        toast.success("Phase added", `"${phaseForm.name}" has been created`);
      }
      if (phaseSupportingFiles.length > 0) {
        const uploadOk = await uploadSupportingFiles(
          `/projects/${projectId}/phases/${savedPhase.id}/upload-supporting-file/`,
          phaseSupportingFiles,
        );
        if (!uploadOk) {
          toast.error(
            "Files not uploaded",
            "Phase was saved, but supporting files failed to upload.",
          );
        }
      }
      showPhaseForm = false;
      phaseSupportingFiles = [];
      loadProject();
    } catch (err) {
      toast.error("Failed to save phase", apiErrorDetail(err));
    }
  }

  async function deletePhase(phaseId: number) {
    if (!confirm("Delete this phase and all its milestones, tasks, and costs?")) return;
    try {
      await api.delete(`/projects/${projectId}/phases/${phaseId}/`);
      toast.success("Phase deleted", "The phase has been permanently removed");
      loadProject();
    } catch (err) {
      toast.error("Failed to delete phase", apiErrorDetail(err));
    }
  }

  const PHASE_TEMPLATES = [
    { name: "Pre-Construction", description: "Site surveys, soil tests, EIA, permits, and regulatory approvals.", budget: "500000", weight: "1" },
    { name: "Foundation & Substructure", description: "Excavation, piling, foundation slabs, and waterproofing.", budget: "3500000", weight: "2" },
    { name: "Superstructure", description: "Structural frame, columns, beams, floor slabs, and stairwells.", budget: "8000000", weight: "3" },
    { name: "Envelope & Roofing", description: "External walls, cladding, glazing, and roof installation.", budget: "4000000", weight: "2" },
    { name: "MEP Rough-In", description: "Mechanical, electrical, and plumbing first-fix installations.", budget: "5000000", weight: "2" },
    { name: "Interior Fit-Out", description: "Partitions, flooring, painting, joinery, and finishes.", budget: "6000000", weight: "3" },
    { name: "Commissioning & Handover", description: "Testing, snagging, compliance certification, and client handover.", budget: "1000000", weight: "1" },
  ];
  let phaseTemplateIndex = 0;

  function devFillPhase() {
    const tmpl = PHASE_TEMPLATES[phaseTemplateIndex % PHASE_TEMPLATES.length];
    phaseTemplateIndex++;
    const today = new Date();
    const offset = (phaseTemplateIndex - 1) * 60;
    const start = new Date(today); start.setDate(start.getDate() + offset);
    const end = new Date(start); end.setDate(end.getDate() + 59);
    const fmt = (d: Date) => d.toISOString().slice(0, 10);
    phaseForm.name = tmpl.name;
    phaseForm.description = tmpl.description;
    phaseForm.sort_order = String(project?.phases.length ?? 0);
    phaseForm.status = "not_started";
    phaseForm.planned_start_date = fmt(start);
    phaseForm.planned_end_date = fmt(end);
    phaseForm.actual_start_date = "";
    phaseForm.actual_end_date = "";
    phaseForm.planned_budget = tmpl.budget;
    phaseForm.weight = tmpl.weight;
    phaseForm.objective = `Complete all ${tmpl.name.toLowerCase()} activities within budget and timeline.`;
    phaseForm.estimated_duration_days = "60";
    phaseForm.phase_owner_role = "Project Manager";
    phaseForm.raci_matrix = [];
    phaseForm.approval_authority = "";
    phaseForm.key_tasks = [];
    phaseForm.deliverables = [];
    phaseForm.out_of_scope = "";
    phaseForm.resource_requirements = [];
    phaseForm.phase_risks = [];
    phaseForm.budget_notes = "";
    phaseForm.success_metrics = [];
    phaseForm.exit_criteria = [];
    phaseForm.lessons_learned_prompt = "";
  }

  // --- Milestones ---
  function emptyMilestoneForm() {
    return {
      name: "", target_date: "", phase_id: 0,
      reference_code: "", typical_offset_days: "" as string | number,
      success_criteria: [] as MilestoneSuccessCriterion[],
      key_deliverables: [] as MilestoneDeliverable[],
      predecessors: [] as MilestoneDependencyLink[],
      successors: [] as MilestoneDependencyLink[],
      owner_role: "", approver_role: "",
      stakeholders_to_notify: [] as MilestoneStakeholder[],
    };
  }
  let milestoneForm = $state(emptyMilestoneForm());
  let showMilestoneForm = $state(false);
  let editingMilestone = $state<ProjectMilestone | null>(null);
  let milestoneSupportingFiles = $state<File[]>([]);

  // Milestone array helpers
  function addMsSuccessCriterion() { milestoneForm.success_criteria = [...milestoneForm.success_criteria, { criterion: "", verification_method: "" }]; }
  function removeMsSuccessCriterion(i: number) { milestoneForm.success_criteria = milestoneForm.success_criteria.filter((_: any, idx: number) => idx !== i); }
  function addMsDeliverable() { milestoneForm.key_deliverables = [...milestoneForm.key_deliverables, { name: "", description: "", is_mandatory: false }]; }
  function removeMsDeliverable(i: number) { milestoneForm.key_deliverables = milestoneForm.key_deliverables.filter((_: any, idx: number) => idx !== i); }
  function addMsPredecessor() { milestoneForm.predecessors = [...milestoneForm.predecessors, { milestone: "", dependency_type: "finish_to_start", lag_days: 0 }]; }
  function removeMsPredecessor(i: number) { milestoneForm.predecessors = milestoneForm.predecessors.filter((_: any, idx: number) => idx !== i); }
  function addMsSuccessor() { milestoneForm.successors = [...milestoneForm.successors, { milestone: "", dependency_type: "finish_to_start", lag_days: 0 }]; }
  function removeMsSuccessor(i: number) { milestoneForm.successors = milestoneForm.successors.filter((_: any, idx: number) => idx !== i); }
  function addMsStakeholder() { milestoneForm.stakeholders_to_notify = [...milestoneForm.stakeholders_to_notify, { role: "", notification_trigger: "on_completion" }]; }
  function removeMsStakeholder(i: number) { milestoneForm.stakeholders_to_notify = milestoneForm.stakeholders_to_notify.filter((_: any, idx: number) => idx !== i); }

  const MILESTONE_TEMPLATES = [
    "Site clearance complete",
    "Piling works complete",
    "Foundation slab poured",
    "Ground floor structural frame complete",
    "Roof slab cast",
    "Building envelope watertight",
    "MEP rough-in signed off",
    "Internal partitions complete",
    "Final fit-out inspection",
    "Practical completion certificate issued",
    "Defects liability period start",
    "Client handover",
  ];
  let milestoneTemplateIndex = 0;

  function devFillMilestone() {
    const name = MILESTONE_TEMPLATES[milestoneTemplateIndex % MILESTONE_TEMPLATES.length];
    milestoneTemplateIndex++;
    const target = new Date();
    target.setDate(target.getDate() + milestoneTemplateIndex * 14);
    milestoneForm = {
      ...milestoneForm,
      name,
      target_date: target.toISOString().slice(0, 10),
    };
  }

  async function loadMilestones() {
    if (!project) return;
    const result: Record<number, ProjectMilestone[]> = {};
    for (const phase of project.phases) {
      try {
        const res = await api.get<PaginatedResponse<ProjectMilestone> | ProjectMilestone[]>(
          `/projects/${projectId}/phases/${phase.id}/milestones/`,
        );
        result[phase.id] = listRows(res);
      } catch {
        result[phase.id] = [];
      }
    }
    milestonesByPhase = result;
  }

  $effect(() => {
    if (activeTab === "milestones" && project) {
      loadMilestones();
    }
  });

  function openAddMilestone(phaseId: number) {
    editingMilestone = null;
    milestoneForm = { ...emptyMilestoneForm(), phase_id: phaseId };
    milestoneSupportingFiles = [];
    selectedMilestoneTemplate = null;
    showMilestoneForm = true;
  }

  function openEditMilestone(phaseId: number, ms: ProjectMilestone) {
    editingMilestone = ms;
    selectedMilestoneTemplate = null;
    milestoneSupportingFiles = [];
    milestoneForm = {
      name: ms.name,
      target_date: ms.target_date ?? "",
      phase_id: phaseId,
      reference_code: ms.reference_code ?? "",
      typical_offset_days: ms.typical_offset_days != null ? ms.typical_offset_days : "",
      success_criteria: ms.success_criteria?.map((c: any) => ({ ...c })) ?? [],
      key_deliverables: ms.key_deliverables?.map((d: any) => ({ ...d })) ?? [],
      predecessors: ms.predecessors?.map((p: any) => ({ ...p })) ?? [],
      successors: ms.successors?.map((s: any) => ({ ...s })) ?? [],
      owner_role: ms.owner_role ?? "",
      approver_role: ms.approver_role ?? "",
      stakeholders_to_notify: ms.stakeholders_to_notify?.map((s: any) => ({ ...s })) ?? [],
    };
    showMilestoneForm = true;
  }

  async function saveMilestone() {
    try {
      const payload = {
        name: milestoneForm.name,
        target_date: milestoneForm.target_date || null,
        reference_code: milestoneForm.reference_code,
        typical_offset_days: milestoneForm.typical_offset_days !== "" ? Number(milestoneForm.typical_offset_days) : null,
        success_criteria: milestoneForm.success_criteria,
        key_deliverables: milestoneForm.key_deliverables,
        predecessors: milestoneForm.predecessors,
        successors: milestoneForm.successors,
        owner_role: milestoneForm.owner_role,
        approver_role: milestoneForm.approver_role,
        stakeholders_to_notify: milestoneForm.stakeholders_to_notify,
      };
      let savedMilestone: ProjectMilestone;
      if (editingMilestone) {
        savedMilestone = await api.patch<ProjectMilestone>(
          `/projects/${projectId}/phases/${milestoneForm.phase_id}/milestones/${editingMilestone.id}/`,
          payload,
        );
        toast.success("Milestone updated", `"${milestoneForm.name}" has been saved`);
      } else {
        savedMilestone = await api.post<ProjectMilestone>(
          `/projects/${projectId}/phases/${milestoneForm.phase_id}/milestones/`,
          payload,
        );
        toast.success("Milestone added", `"${milestoneForm.name}" has been created`);
      }
      if (milestoneSupportingFiles.length > 0) {
        const uploadOk = await uploadSupportingFiles(
          `/projects/${projectId}/phases/${milestoneForm.phase_id}/milestones/${savedMilestone.id}/upload-supporting-file/`,
          milestoneSupportingFiles,
        );
        if (!uploadOk) {
          toast.error(
            "Files not uploaded",
            "Milestone was saved, but supporting files failed to upload.",
          );
        }
      }
      showMilestoneForm = false;
      milestoneSupportingFiles = [];
      loadMilestones();
      loadProject();
    } catch (err) {
      toast.error("Failed to save milestone", apiErrorDetail(err));
    }
  }

  async function toggleMilestone(phaseId: number, milestone: ProjectMilestone) {
    try {
      const completed = !milestone.is_completed;
      await api.patch(`/projects/${projectId}/phases/${phaseId}/milestones/${milestone.id}/`, {
        is_completed: completed,
        completed_date: completed ? new Date().toISOString().slice(0, 10) : null,
      });
      loadMilestones();
    } catch (err) {
      toast.error("Failed to update milestone", apiErrorDetail(err));
    }
  }

  async function deleteMilestone(phaseId: number, milestoneId: number) {
    if (!confirm("Delete this milestone?")) return;
    try {
      await api.delete(`/projects/${projectId}/phases/${phaseId}/milestones/${milestoneId}/`);
      toast.success("Milestone deleted", "The milestone has been removed");
      loadMilestones();
      loadProject();
    } catch (err) {
      toast.error("Failed to delete milestone", apiErrorDetail(err));
    }
  }

  // --- Tasks ---
  let showTaskForm = $state(false);
  let editingTask = $state<ProjectTask | null>(null);
  function emptyTaskForm() {
    return {
      name: "", assigned_to: "", due_date: "", status: "pending", phase_id: 0,
      reference_code: "", reviewer_role: "",
      collaborators: [] as TaskCollaborator[],
      estimated_effort_hours: "" as string | number,
      predecessors: [] as TaskDependencyLink[],
      successors: [] as TaskDependencyLink[],
      definition_of_done: [] as TaskDoDItem[],
      tools_required: [] as TaskTool[],
      reference_links: [] as TaskRefLink[],
    };
  }
  let taskForm = $state(emptyTaskForm());
  let taskSupportingFiles = $state<File[]>([]);

  // Task array helpers
  function addTaskCollaborator() { taskForm.collaborators = [...taskForm.collaborators, { role: "", responsibility: "" }]; }
  function removeTaskCollaborator(i: number) { taskForm.collaborators = taskForm.collaborators.filter((_: any, idx: number) => idx !== i); }
  function addTaskPredecessor() { taskForm.predecessors = [...taskForm.predecessors, { task: "", dependency_type: "finish_to_start", lag_days: 0 }]; }
  function removeTaskPredecessor(i: number) { taskForm.predecessors = taskForm.predecessors.filter((_: any, idx: number) => idx !== i); }
  function addTaskSuccessor() { taskForm.successors = [...taskForm.successors, { task: "", dependency_type: "finish_to_start", lag_days: 0 }]; }
  function removeTaskSuccessor(i: number) { taskForm.successors = taskForm.successors.filter((_: any, idx: number) => idx !== i); }
  function addTaskDoD() { taskForm.definition_of_done = [...taskForm.definition_of_done, { criterion: "", is_required: true }]; }
  function removeTaskDoD(i: number) { taskForm.definition_of_done = taskForm.definition_of_done.filter((_: any, idx: number) => idx !== i); }
  function addTaskTool() { taskForm.tools_required = [...taskForm.tools_required, { name: "", description: "" }]; }
  function removeTaskTool(i: number) { taskForm.tools_required = taskForm.tools_required.filter((_: any, idx: number) => idx !== i); }
  function addTaskRefLink() { taskForm.reference_links = [...taskForm.reference_links, { title: "", url: "" }]; }
  function removeTaskRefLink(i: number) { taskForm.reference_links = taskForm.reference_links.filter((_: any, idx: number) => idx !== i); }

  const TASK_TEMPLATES = [
    { name: "Mobilise site team and secure perimeter", assignee: "Site Manager" },
    { name: "Survey and set out foundation grid lines", assignee: "Land Surveyor" },
    { name: "Excavate to formation level", assignee: "Earthworks Foreman" },
    { name: "Install reinforcement cages for pile caps", assignee: "Steel Fixer Lead" },
    { name: "Pour and cure ground floor slab", assignee: "Concrete Foreman" },
    { name: "Erect structural columns to first floor", assignee: "Structural Engineer" },
    { name: "Install formwork for upper floor slabs", assignee: "Carpentry Foreman" },
    { name: "Lay external block walls and cavity insulation", assignee: "Masonry Foreman" },
    { name: "Run first-fix electrical conduits and back-boxes", assignee: "Electrical Lead" },
    { name: "Install first-fix plumbing and soil stacks", assignee: "Plumbing Lead" },
    { name: "Fit window and door frames", assignee: "Joinery Lead" },
    { name: "Apply screed to all floor areas", assignee: "Finishing Foreman" },
    { name: "Paint internal walls and ceilings", assignee: "Painting Contractor" },
    { name: "Commission fire alarm and sprinkler systems", assignee: "Fire Safety Officer" },
    { name: "Complete snagging list and final inspection", assignee: "QA Manager" },
  ];
  let taskTemplateIndex = 0;

  function devFillTask() {
    const tmpl = TASK_TEMPLATES[taskTemplateIndex % TASK_TEMPLATES.length];
    taskTemplateIndex++;
    const due = new Date();
    due.setDate(due.getDate() + taskTemplateIndex * 7);
    taskForm = {
      ...taskForm,
      name: tmpl.name,
      assigned_to: tmpl.assignee,
      due_date: due.toISOString().slice(0, 10),
      status: "pending",
    };
  }

  async function loadTasks() {
    if (!project) return;
    const result: Record<number, ProjectTask[]> = {};
    for (const phase of project.phases) {
      try {
        const res = await api.get<PaginatedResponse<ProjectTask> | ProjectTask[]>(
          `/projects/${projectId}/phases/${phase.id}/tasks/`,
        );
        result[phase.id] = listRows(res);
      } catch {
        result[phase.id] = [];
      }
    }
    tasksByPhase = result;
  }

  $effect(() => {
    if (activeTab === "tasks" && project) {
      loadTasks();
    }
  });

  function openAddTask(phaseId: number) {
    editingTask = null;
    taskForm = { ...emptyTaskForm(), phase_id: phaseId };
    taskSupportingFiles = [];
    selectedTaskTemplate = null;
    showTaskForm = true;
  }

  function openEditTask(phaseId: number, t: ProjectTask) {
    editingTask = t;
    selectedTaskTemplate = null;
    taskSupportingFiles = [];
    taskForm = {
      name: t.name,
      assigned_to: t.assigned_to ?? "",
      due_date: t.due_date ?? "",
      status: t.status ?? "pending",
      phase_id: phaseId,
      reference_code: t.reference_code ?? "",
      reviewer_role: t.reviewer_role ?? "",
      collaborators: t.collaborators?.map((c: any) => ({ ...c })) ?? [],
      estimated_effort_hours: t.estimated_effort_hours != null ? t.estimated_effort_hours : "",
      predecessors: t.predecessors?.map((p: any) => ({ ...p })) ?? [],
      successors: t.successors?.map((s: any) => ({ ...s })) ?? [],
      definition_of_done: t.definition_of_done?.map((d: any) => ({ ...d })) ?? [],
      tools_required: t.tools_required?.map((tl: any) => ({ ...tl })) ?? [],
      reference_links: t.reference_links?.map((r: any) => ({ ...r })) ?? [],
    };
    showTaskForm = true;
  }

  async function saveTask() {
    try {
      const payload = {
        name: taskForm.name,
        assigned_to: taskForm.assigned_to,
        due_date: taskForm.due_date || null,
        status: taskForm.status,
        reference_code: taskForm.reference_code,
        reviewer_role: taskForm.reviewer_role,
        collaborators: taskForm.collaborators,
        estimated_effort_hours: taskForm.estimated_effort_hours !== "" ? Number(taskForm.estimated_effort_hours) : null,
        predecessors: taskForm.predecessors,
        successors: taskForm.successors,
        definition_of_done: taskForm.definition_of_done,
        tools_required: taskForm.tools_required,
        reference_links: taskForm.reference_links,
      };
      let savedTask: ProjectTask;
      if (editingTask) {
        savedTask = await api.patch<ProjectTask>(
          `/projects/${projectId}/phases/${taskForm.phase_id}/tasks/${editingTask.id}/`,
          payload,
        );
        toast.success("Task updated", `"${taskForm.name}" has been saved`);
      } else {
        savedTask = await api.post<ProjectTask>(
          `/projects/${projectId}/phases/${taskForm.phase_id}/tasks/`,
          payload,
        );
        toast.success("Task added", `"${taskForm.name}" has been created`);
      }
      if (taskSupportingFiles.length > 0) {
        const uploadOk = await uploadSupportingFiles(
          `/projects/${projectId}/phases/${taskForm.phase_id}/tasks/${savedTask.id}/upload-supporting-file/`,
          taskSupportingFiles,
        );
        if (!uploadOk) {
          toast.error(
            "Files not uploaded",
            "Task was saved, but supporting files failed to upload.",
          );
        }
      }
      showTaskForm = false;
      taskSupportingFiles = [];
      loadTasks();
      loadProject();
    } catch (err) {
      toast.error("Failed to save task", apiErrorDetail(err));
    }
  }

  async function quickUpdateTaskStatus(phaseId: number, task: ProjectTask, newStatus: string) {
    try {
      await api.patch(`/projects/${projectId}/phases/${phaseId}/tasks/${task.id}/`, {
        status: newStatus,
        completed_date: newStatus === "completed" ? new Date().toISOString().slice(0, 10) : null,
      });
      loadTasks();
    } catch (err) {
      toast.error("Failed to update task", apiErrorDetail(err));
    }
  }

  async function deleteTask(phaseId: number, taskId: number) {
    if (!confirm("Delete this task?")) return;
    try {
      await api.delete(`/projects/${projectId}/phases/${phaseId}/tasks/${taskId}/`);
      toast.success("Task deleted", "The task has been removed");
      loadTasks();
      loadProject();
    } catch (err) {
      toast.error("Failed to delete task", apiErrorDetail(err));
    }
  }

  // --- Costs ---
  let showCostForm = $state(false);
  let costForm = $state({ description: "", amount: "", date: "", category: "other", vendor: "", reference_number: "", phase_id: 0 });
  let costSupportingFiles = $state<File[]>([]);

  const COST_TEMPLATES = [
    { description: "Bulk cement delivery (OPC 42.5)", amount: "185000", category: "materials", vendor: "Dangote Cement" },
    { description: "Reinforcement steel bars 16mm", amount: "420000", category: "materials", vendor: "BUA Steel" },
    { description: "Excavation and earthworks labour", amount: "310000", category: "labor", vendor: "Groundforce Ltd" },
    { description: "Building permit application fee", amount: "75000", category: "permits", vendor: "Municipal Authority" },
    { description: "Tower crane hire — monthly", amount: "650000", category: "equipment", vendor: "CraneRent Africa" },
    { description: "Electrical rough-in subcontract", amount: "540000", category: "subcontractor", vendor: "Voltex Electrical" },
    { description: "Plumbing first-fix subcontract", amount: "380000", category: "subcontractor", vendor: "AquaFlow Systems" },
    { description: "Ready-mix concrete 30 MPa (40 m³)", amount: "280000", category: "materials", vendor: "LafargeHolcim" },
    { description: "Scaffold erection and rental", amount: "195000", category: "equipment", vendor: "SafeScaff Co" },
    { description: "Environmental impact assessment fee", amount: "120000", category: "permits", vendor: "GreenAudit Consultants" },
    { description: "Painting and finishing labour", amount: "260000", category: "labor", vendor: "Dulux Pro Applicators" },
    { description: "Fire alarm system installation", amount: "475000", category: "subcontractor", vendor: "FireGuard Solutions" },
  ];
  let costTemplateIndex = 0;

  function devFillCost() {
    const tmpl = COST_TEMPLATES[costTemplateIndex % COST_TEMPLATES.length];
    costTemplateIndex++;
    const date = new Date();
    date.setDate(date.getDate() - Math.floor(Math.random() * 30));
    const ref = `INV-${String(costTemplateIndex).padStart(4, "0")}`;
    costForm = {
      ...costForm,
      description: tmpl.description,
      amount: tmpl.amount,
      date: date.toISOString().slice(0, 10),
      category: tmpl.category,
      vendor: tmpl.vendor,
      reference_number: ref,
    };
  }

  async function loadCosts() {
    if (!project) return;
    const result: Record<number, ProjectCostEntry[]> = {};
    for (const phase of project.phases) {
      try {
        const res = await api.get<PaginatedResponse<ProjectCostEntry> | ProjectCostEntry[]>(
          `/projects/${projectId}/phases/${phase.id}/costs/`,
        );
        result[phase.id] = listRows(res);
      } catch {
        result[phase.id] = [];
      }
    }
    costsByPhase = result;
  }

  $effect(() => {
    if (activeTab === "costs" && project) {
      loadCosts();
    }
  });

  function openAddCost(phaseId: number) {
    costForm = { description: "", amount: "", date: new Date().toISOString().slice(0, 10), category: "other", vendor: "", reference_number: "", phase_id: phaseId };
    costSupportingFiles = [];
    showCostForm = true;
  }

  async function saveCost() {
    try {
      const costEntry = await api.post<ProjectCostEntry>(`/projects/${projectId}/phases/${costForm.phase_id}/costs/`, {
        description: costForm.description,
        amount: costForm.amount,
        date: costForm.date,
        category: costForm.category,
        vendor: costForm.vendor,
        reference_number: costForm.reference_number,
      });
      if (costSupportingFiles.length > 0) {
        const uploadOk = await uploadSupportingFiles(
          `/projects/${projectId}/phases/${costForm.phase_id}/costs/${costEntry.id}/upload-supporting-file/`,
          costSupportingFiles,
        );
        if (!uploadOk) {
          toast.error(
            "Files not uploaded",
            "Cost entry was saved, but supporting files failed to upload.",
          );
        }
      }
      toast.success("Cost entry added", `"${costForm.description}" — ${currency.format(costForm.amount)}`);
      showCostForm = false;
      costSupportingFiles = [];
      loadCosts();
      loadProject();
    } catch (err) {
      toast.error("Failed to save cost entry", apiErrorDetail(err));
    }
  }

  async function deleteCost(phaseId: number, costId: number) {
    if (!confirm("Delete this cost entry?")) return;
    try {
      await api.delete(`/projects/${projectId}/phases/${phaseId}/costs/${costId}/`);
      toast.success("Cost entry deleted", "The cost entry has been removed");
      loadCosts();
      loadProject();
    } catch (err) {
      toast.error("Failed to delete cost entry", apiErrorDetail(err));
    }
  }

  // --- Timeline ---
  async function loadTimeline() {
    try {
      timelineData = await api.get<ProjectTimelineData>(`/projects/${projectId}/timeline/`);
    } catch {
      timelineData = null;
    }
  }

  $effect(() => {
    if (activeTab === "timeline" && project) {
      loadTimeline();
    }
  });

  function handleProjectDocumentCreated() {
    documentsRefreshKey += 1;
  }

  type SupportingUploadTarget = "phase" | "milestone" | "task" | "cost";

  function onSupportingFilesSelected(event: Event, target: SupportingUploadTarget) {
    const input = event.target as HTMLInputElement;
    const files = Array.from(input.files ?? []);
    if (target === "phase") phaseSupportingFiles = files;
    if (target === "milestone") milestoneSupportingFiles = files;
    if (target === "task") taskSupportingFiles = files;
    if (target === "cost") costSupportingFiles = files;
  }

  async function uploadSupportingFiles(endpoint: string, files: File[]): Promise<boolean> {
    try {
      for (const file of files) {
        const payload = new FormData();
        payload.append("file", file);
        payload.append("caption", file.name);
        await api.upload(endpoint, payload);
      }
      toast.success("Files uploaded", `${files.length} supporting file(s) uploaded successfully.`);
      return true;
    } catch (err) {
      console.error("Supporting file upload failed:", err);
      return false;
    }
  }
</script>

{#snippet sectionDisplay(d: any)}
  {#if d.objective || d.estimated_duration_days || d.phase_owner_role}
    <div>
      <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-1.5">A — Overview</p>
      {#if d.objective}
        <p class="text-sm text-neutral-600 leading-relaxed">{d.objective}</p>
      {/if}
      {#if d.estimated_duration_days || d.phase_owner_role}
        <div class="flex flex-wrap gap-2 mt-2">
          {#if d.estimated_duration_days}
            <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-neutral-100 text-neutral-600">
              <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>
              {d.estimated_duration_days} days
            </span>
          {/if}
          {#if d.phase_owner_role}
            <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-neutral-100 text-neutral-600">
              <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" /></svg>
              {d.phase_owner_role}
            </span>
          {/if}
        </div>
      {/if}
    </div>
  {/if}

  {#if d.raci_matrix?.length || d.approval_authority}
    <div>
      <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-1.5">B — Governance</p>
      {#if d.raci_matrix?.length}
        <div class="overflow-x-auto rounded-lg border border-neutral-200">
          <table class="w-full text-xs">
            <thead><tr class="bg-neutral-100">
              <th class="px-3 py-1.5 text-left font-medium text-neutral-500">Task</th>
              <th class="px-3 py-1.5 text-center font-medium text-neutral-500">R</th>
              <th class="px-3 py-1.5 text-center font-medium text-neutral-500">A</th>
              <th class="px-3 py-1.5 text-center font-medium text-neutral-500">C</th>
              <th class="px-3 py-1.5 text-center font-medium text-neutral-500">I</th>
            </tr></thead>
            <tbody class="bg-white divide-y divide-neutral-100">
              {#each d.raci_matrix as row}
                <tr>
                  <td class="px-3 py-1.5 text-neutral-900 font-medium">{row.task}</td>
                  <td class="px-3 py-1.5 text-center text-neutral-600">{row.responsible}</td>
                  <td class="px-3 py-1.5 text-center text-neutral-600">{row.accountable}</td>
                  <td class="px-3 py-1.5 text-center text-neutral-600">{row.consulted}</td>
                  <td class="px-3 py-1.5 text-center text-neutral-600">{row.informed}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
      {#if d.approval_authority}
        <p class="mt-2 text-xs text-neutral-500"><span class="font-medium text-neutral-600">Approval authority:</span> {d.approval_authority}</p>
      {/if}
    </div>
  {/if}

  {#if d.key_tasks?.length || d.deliverables?.length || d.out_of_scope}
    <div>
      <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-1.5">C — Scope & Deliverables</p>
      {#if d.key_tasks?.length}
        <div class="mb-3">
          <p class="text-[10px] font-medium text-neutral-500 uppercase mb-1">Key Tasks</p>
          <ul class="space-y-0.5">
            {#each d.key_tasks as task, i}
              <li class="flex gap-2 text-xs">
                <span class="text-neutral-300 tabular-nums w-4 shrink-0">{i + 1}.</span>
                <span class="text-neutral-700"><span class="font-medium text-neutral-900">{task.name}</span>{#if task.description} — {task.description}{/if}</span>
              </li>
            {/each}
          </ul>
        </div>
      {/if}
      {#if d.deliverables?.length}
        <div class="mb-3">
          <p class="text-[10px] font-medium text-neutral-500 uppercase mb-1">Deliverables</p>
          <div class="flex flex-wrap gap-1.5">
            {#each d.deliverables as del}
              <span class="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs {del.is_mandatory ? 'bg-neutral-900 text-white' : 'bg-neutral-100 text-neutral-600'}">
                {del.name}{#if del.is_mandatory}<span class="text-[9px] opacity-60 ml-0.5">REQ</span>{/if}
              </span>
            {/each}
          </div>
        </div>
      {/if}
      {#if d.out_of_scope}
        <div>
          <p class="text-[10px] font-medium text-neutral-500 uppercase mb-1">Out of Scope</p>
          <p class="text-xs text-neutral-500 italic border-l-2 border-neutral-200 pl-3">{d.out_of_scope}</p>
        </div>
      {/if}
    </div>
  {/if}

  {#if d.resource_requirements?.length || d.phase_risks?.length || d.budget_notes}
    <div>
      <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-1.5">D — Resources & Risk</p>
      {#if d.resource_requirements?.length}
        <div class="mb-3">
          <p class="text-[10px] font-medium text-neutral-500 uppercase mb-1">Resources</p>
          <div class="grid grid-cols-2 gap-1.5">
            {#each d.resource_requirements as req}
              <div class="flex items-center gap-2 px-2.5 py-1.5 rounded-md bg-neutral-50 border border-neutral-100 text-xs">
                <span class="text-[10px] font-semibold uppercase tracking-wide text-neutral-400 shrink-0">{req.type}</span>
                <span class="text-neutral-700 truncate">{req.description}</span>
                {#if req.quantity}<span class="ml-auto text-neutral-400 tabular-nums shrink-0">{req.quantity}</span>{/if}
              </div>
            {/each}
          </div>
        </div>
      {/if}
      {#if d.phase_risks?.length}
        <div class="mb-3">
          <p class="text-[10px] font-medium text-neutral-500 uppercase mb-1">Risks</p>
          <div class="overflow-x-auto rounded-lg border border-neutral-200">
            <table class="w-full text-xs">
              <thead><tr class="bg-neutral-100">
                <th class="px-3 py-1.5 text-left font-medium text-neutral-500">Risk</th>
                <th class="px-3 py-1.5 text-center font-medium text-neutral-500 w-20">Likelihood</th>
                <th class="px-3 py-1.5 text-center font-medium text-neutral-500 w-20">Impact</th>
                <th class="px-3 py-1.5 text-left font-medium text-neutral-500">Mitigation</th>
              </tr></thead>
              <tbody class="bg-white divide-y divide-neutral-100">
                {#each d.phase_risks as risk}
                  <tr>
                    <td class="px-3 py-1.5 text-neutral-900">{risk.risk}</td>
                    <td class="px-3 py-1.5 text-center"><span class="inline-flex px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase {risk.likelihood === 'high' ? 'bg-red-50 text-red-600' : risk.likelihood === 'medium' ? 'bg-amber-50 text-amber-600' : 'bg-green-50 text-green-600'}">{risk.likelihood}</span></td>
                    <td class="px-3 py-1.5 text-center"><span class="inline-flex px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase {risk.impact === 'high' ? 'bg-red-50 text-red-600' : risk.impact === 'medium' ? 'bg-amber-50 text-amber-600' : 'bg-green-50 text-green-600'}">{risk.impact}</span></td>
                    <td class="px-3 py-1.5 text-neutral-500">{risk.mitigation}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>
      {/if}
      {#if d.budget_notes}
        <p class="text-xs text-neutral-500"><span class="font-medium text-neutral-600">Budget notes:</span> {d.budget_notes}</p>
      {/if}
    </div>
  {/if}

  {#if d.success_metrics?.length || d.exit_criteria?.length || d.lessons_learned_prompt}
    <div>
      <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-1.5">E — Quality & Completion</p>
      {#if d.success_metrics?.length}
        <div class="mb-3">
          <p class="text-[10px] font-medium text-neutral-500 uppercase mb-1">Success Metrics</p>
          <div class="overflow-x-auto rounded-lg border border-neutral-200">
            <table class="w-full text-xs">
              <thead><tr class="bg-neutral-100">
                <th class="px-3 py-1.5 text-left font-medium text-neutral-500">Metric</th>
                <th class="px-3 py-1.5 text-left font-medium text-neutral-500">Target</th>
                <th class="px-3 py-1.5 text-left font-medium text-neutral-500">Measurement</th>
              </tr></thead>
              <tbody class="bg-white divide-y divide-neutral-100">
                {#each d.success_metrics as m}
                  <tr>
                    <td class="px-3 py-1.5 text-neutral-900 font-medium">{m.metric}</td>
                    <td class="px-3 py-1.5 text-neutral-600">{m.target}</td>
                    <td class="px-3 py-1.5 text-neutral-500">{m.measurement_method}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>
      {/if}
      {#if d.exit_criteria?.length}
        <div class="mb-3">
          <p class="text-[10px] font-medium text-neutral-500 uppercase mb-1">Exit Criteria</p>
          <ul class="space-y-1">
            {#each d.exit_criteria as ec}
              <li class="flex items-start gap-2 text-xs">
                <svg class="w-3.5 h-3.5 text-neutral-300 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>
                <span><span class="text-neutral-900">{ec.criterion}</span>{#if ec.verification_method}<span class="text-neutral-400"> — {ec.verification_method}</span>{/if}</span>
              </li>
            {/each}
          </ul>
        </div>
      {/if}
      {#if d.lessons_learned_prompt}
        <div>
          <p class="text-[10px] font-medium text-neutral-500 uppercase mb-1">Lessons Learned</p>
          <p class="text-xs text-neutral-500 italic border-l-2 border-neutral-200 pl-3">{d.lessons_learned_prompt}</p>
        </div>
      {/if}
    </div>
  {/if}
{/snippet}

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
  </div>
{:else if !project}
  <div class="py-24 text-center">
    <p class="text-neutral-400 text-sm">Project not found</p>
    <a href="/projects" class="inline-block mt-3 text-sm font-medium text-neutral-900 hover:underline">Back to projects</a>
  </div>
{:else}
  <!-- Header -->
  <div class="mb-6">
    <Breadcrumb items={[{ label: "Projects", href: "/projects" }, { label: project.name }]} />
    <div class="flex items-start justify-between mt-3">
      <div>
        <div class="flex items-center gap-3">
          <h1 class="text-2xl font-bold text-neutral-900">{project.name}</h1>
          <StatusBadge status={project.status} />
        </div>
        <p class="text-sm text-neutral-400 mt-1">
          {#if project.property}
            <a href="/properties/{project.property}" class="hover:text-neutral-600 transition-colors">
              {project.property_name ?? "Linked property"}
            </a>
          {:else}
            <span>Unlinked property</span>
          {/if}
          {#if project.project_manager}
            <span class="mx-1.5">&middot;</span> Managed by {project.project_manager}
          {/if}
        </p>
      </div>
      <div class="flex gap-2">
        <a href="/projects/{projectId}/edit" class="px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors">Edit</a>
        <button onclick={deleteProject} class="px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium text-red-600 hover:bg-red-50 transition-colors">Delete</button>
      </div>
    </div>

    <!-- Progress bar -->
    <div class="flex items-center gap-3 mt-4">
      <div class="flex-1 bg-neutral-100 rounded-full h-2">
        <div class="bg-neutral-900 h-2 rounded-full transition-all" style="width: {project.progress}%"></div>
      </div>
      <span class="text-sm font-medium text-neutral-900 tabular-nums">{project.progress}%</span>
    </div>
  </div>

  <!-- Recommended next step -->
  {#if recommendedAction}
    <div class="mb-6 rounded-2xl border p-4 sm:p-5 {recommendedAction.tone === 'amber' ? 'border-amber-200 bg-amber-50' : recommendedAction.tone === 'emerald' ? 'border-emerald-200 bg-emerald-50' : 'border-indigo-200 bg-indigo-50'}">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div class="flex items-start gap-3 min-w-0">
          <div class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full {recommendedAction.tone === 'amber' ? 'bg-amber-100 text-amber-700' : recommendedAction.tone === 'emerald' ? 'bg-emerald-100 text-emerald-700' : 'bg-indigo-100 text-indigo-700'}">
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </div>
          <div class="min-w-0">
            <p class="text-[10px] font-semibold uppercase tracking-wider {recommendedAction.tone === 'amber' ? 'text-amber-700' : recommendedAction.tone === 'emerald' ? 'text-emerald-700' : 'text-indigo-700'}">Recommended Next Step</p>
            <p class="mt-1 text-base font-semibold text-neutral-900">{recommendedAction.title}</p>
            <p class="mt-1 text-sm text-neutral-600">{recommendedAction.description}</p>
          </div>
        </div>
        <a href={recommendedAction.href} class="inline-flex items-center gap-2 rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 shrink-0">
          {recommendedAction.cta}
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
          </svg>
        </a>
      </div>
    </div>
  {/if}

  <!-- Tabs -->
  <div class="border-b border-neutral-200 mb-6">
    <nav class="flex gap-6">
      {#each tabs as tab}
        <button
          onclick={() => (activeTab = tab.key)}
          class="pb-3 text-sm font-medium border-b-2 transition-colors
                 {activeTab === tab.key
                   ? 'border-neutral-900 text-neutral-900'
                   : 'border-transparent text-neutral-400 hover:text-neutral-600'}"
        >
          {tab.label}
          {#if tab.key === "phases" && project.phases.length > 0}
            <span class="ml-1.5 text-xs text-neutral-400">{project.phases.length}</span>
          {/if}
        </button>
      {/each}
    </nav>
  </div>

  <!-- TAB: Overview -->
  {#if activeTab === "overview"}
    <div class="grid md:grid-cols-2 gap-6">
      <!-- Details -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-4">
        <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Details</h3>
        <div class="space-y-3 text-sm">
          <div class="flex justify-between"><span class="text-neutral-400">Status</span><StatusBadge status={project.status} /></div>
          <div class="flex justify-between"><span class="text-neutral-400">Project Type</span><span class="text-neutral-900">{projectTypeLabels[project.project_type]}</span></div>
          {#if project.number_of_units !== null}
            <div class="flex justify-between"><span class="text-neutral-400">Number of Units</span><span class="text-neutral-900">{project.number_of_units}</span></div>
          {/if}
          <div class="flex justify-between">
            <span class="text-neutral-400">Property</span>
            {#if project.property}
              <a href="/properties/{project.property}" class="text-neutral-900 hover:underline">
                {project.property_name ?? "Linked property"}
              </a>
            {:else}
              <span class="text-neutral-900">Unlinked property</span>
            {/if}
          </div>
          {#if project.location}
            <div class="flex justify-between"><span class="text-neutral-400">Location</span><span class="text-neutral-900">{project.location}</span></div>
          {/if}
          <div class="flex justify-between"><span class="text-neutral-400">Manager</span><span class="text-neutral-900">{project.project_manager || "\u2014"}</span></div>
        </div>
      </div>

      <!-- Map -->
      {#if project.map_available}
        <div class="md:col-span-2">
          <PropertyMap
            latitude={Number(project.gps_latitude)}
            longitude={Number(project.gps_longitude)}
          />
        </div>
      {/if}

      <!-- Entity & Ownership -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-4">
        <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Entity & Land</h3>
        <div class="space-y-3 text-sm">
          <div class="flex justify-between"><span class="text-neutral-400">SPV / Entity</span><span class="text-neutral-900">{project.spv_entity || "\u2014"}</span></div>
          {#if project.land_status}
            <div class="flex justify-between"><span class="text-neutral-400">Land Status</span><span class="text-neutral-900">{landStatusLabels[project.land_status] || project.land_status}</span></div>
          {/if}
          {#if project.ownership_allocations && project.ownership_allocations.length > 0}
            <div>
              <span class="text-neutral-400 block mb-2">Ownership Structure</span>
              <div class="space-y-1.5">
                {#each project.ownership_allocations as allocation}
                  <div class="flex items-center justify-between text-neutral-900">
                    <span>{allocation.party_name}</span>
                    <span class="tabular-nums">{allocation.ownership_percentage}%</span>
                  </div>
                {/each}
              </div>
              <div class="flex items-center justify-between mt-2 pt-2 border-t border-neutral-100">
                <span class="text-neutral-500">Allocated</span>
                <span class="tabular-nums font-medium">{ownershipTotal(project.ownership_allocations).toFixed(2)}%</span>
              </div>
            </div>
          {:else if project.ownership_structure}
            <div>
              <span class="text-neutral-400 block mb-1">Ownership Structure</span>
              <p class="text-neutral-900 whitespace-pre-line">{project.ownership_structure}</p>
            </div>
          {/if}
        </div>
      </div>

      <!-- Key Dates -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-4">
        <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Key Dates</h3>
        <div class="space-y-3 text-sm">
          <div class="flex justify-between"><span class="text-neutral-400">Start Date</span><span class="text-neutral-900">{fmtDate(project.start_date)}</span></div>
          <div class="flex justify-between"><span class="text-neutral-400">Target End</span><span class="text-neutral-900">{fmtDate(project.target_end_date)}</span></div>
          {#if project.actual_end_date}
            <div class="flex justify-between"><span class="text-neutral-400">Actual End</span><span class="text-neutral-900">{fmtDate(project.actual_end_date)}</span></div>
          {/if}
          <div class="flex justify-between"><span class="text-neutral-400">Land Acquisition</span><span class="text-neutral-900">{fmtDate(project.land_acquisition_date)}</span></div>
          <div class="flex justify-between"><span class="text-neutral-400">Permit Approval</span><span class="text-neutral-900">{fmtDate(project.permit_approval_date)}</span></div>
          <div class="flex justify-between"><span class="text-neutral-400">Construction Start</span><span class="text-neutral-900">{fmtDate(project.construction_start_date)}</span></div>
        </div>
      </div>

      <!-- Budget & Financials -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-4">
        <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Budget & Financials</h3>
        <div class="space-y-3 text-sm">
          <div class="flex justify-between"><span class="text-neutral-400">Approved Budget</span><span class="text-neutral-900 tabular-nums">{fmt(project.budget)}</span></div>
          <div class="flex justify-between"><span class="text-neutral-400">Target IRR</span><span class="text-neutral-900 tabular-nums">{project.target_irr ? `${project.target_irr}%` : "\u2014"}</span></div>
          <div class="flex justify-between"><span class="text-neutral-400">Total Planned</span><span class="text-neutral-900 tabular-nums">{fmt(project.total_planned_budget)}</span></div>
          <div class="flex justify-between"><span class="text-neutral-400">Total Actual</span><span class="text-neutral-900 tabular-nums">{fmt(project.total_actual_cost)}</span></div>
          <div class="flex justify-between border-t border-neutral-100 pt-3">
            <span class="text-neutral-400 font-medium">Variance</span>
            <span class="tabular-nums font-semibold {Number(project.total_budget_variance) >= 0 ? 'text-green-600' : 'text-red-600'}">{fmt(project.total_budget_variance)}</span>
          </div>
        </div>
      </div>

      <!-- RACI Matrix Summary -->
      {#if Object.keys(project.raci_summary).length > 0}
        <div class="bg-white rounded-xl border border-neutral-200 p-6 md:col-span-2">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">RACI Summary</h3>
          <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {#each Object.entries(project.raci_summary) as [role, level]}
              <div class="flex items-center gap-2 px-3 py-2 rounded-lg bg-neutral-50">
                <span class="text-sm font-medium text-neutral-900">{role}</span>
                <span class="text-xs text-neutral-500">{level}</span>
              </div>
            {/each}
          </div>
        </div>
      {/if}

      <!-- Phase Progress -->
      {#if project.phases.length > 0}
        <div class="bg-white rounded-xl border border-neutral-200 p-6 md:col-span-2">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Phase Progress</h3>
          <div class="space-y-3">
            {#each project.phases as phase}
              <div class="flex items-center gap-4">
                <span class="text-sm text-neutral-600 w-40 truncate">{phase.name}</span>
                <div class="flex-1 bg-neutral-100 rounded-full h-1.5">
                  <div
                    class="h-1.5 rounded-full transition-all {phase.status === 'completed' ? 'bg-neutral-900' : phase.status === 'in_progress' ? 'bg-neutral-500' : 'bg-neutral-200'}"
                    style="width: {phase.status === 'completed' ? 100 : phase.status === 'in_progress' ? 50 : 0}%"
                  ></div>
                </div>
                <StatusBadge status={phase.status} />
              </div>
            {/each}
          </div>
        </div>
      {/if}

      {#if project.description}
        <div class="bg-white rounded-xl border border-neutral-200 p-6 md:col-span-2">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-3">Description</h3>
          <p class="text-sm text-neutral-600 leading-relaxed whitespace-pre-line">{project.description}</p>
        </div>
      {/if}
    </div>
  {/if}

  <!-- TAB: Phases -->
  {#if activeTab === "phases"}
    <div class="space-y-4">
      <div class="flex justify-end">
        <button onclick={openAddPhase} class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors">+ Add Phase</button>
      </div>

      {#if showPhaseForm}
        <!-- Phase Modal Backdrop -->
        <div class="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 backdrop-blur-sm p-4 pt-12 pb-12">
        <div class="relative w-full max-w-3xl rounded-xl bg-white shadow-2xl p-6">
          <button
            type="button"
            onclick={() => { showPhaseForm = false; phaseSupportingFiles = []; }}
            class="absolute top-4 right-4 rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
            aria-label="Close"
          >
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">{editingPhase ? "Edit Phase" : "New Phase"}</h3>
          {#if !editingPhase && phaseTemplates.length > 0}
            <div class="mb-4">
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Use template</span>
                <select onchange={(e) => { const v = Number((e.target as HTMLSelectElement).value); if (v) applyPhaseTemplate(v); }} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 bg-white">
                  <option value="0">Select a phase template...</option>
                  {#each phaseTemplates as tmpl}
                    <option value={tmpl.id}>{tmpl.name}</option>
                  {/each}
                </select>
              </label>
            </div>
          {/if}
          <div class="grid grid-cols-3 gap-4">
            <div class="col-span-2">
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Name</span>
                <input bind:value={phaseForm.name} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="e.g. Foundation" />
              </label>
            </div>
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Status</span>
                <select bind:value={phaseForm.status} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
                  <option value="not_started">Not Started</option>
                  <option value="in_progress">In Progress</option>
                  <option value="completed">Completed</option>
                  <option value="skipped">Skipped</option>
                </select>
              </label>
            </div>
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Planned Start</span>
                <DateInput bind:value={phaseForm.planned_start_date} />
              </label>
            </div>
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Planned End</span>
                <DateInput bind:value={phaseForm.planned_end_date} />
              </label>
            </div>
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Planned Budget</span>
                <input bind:value={phaseForm.planned_budget} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="0.00" />
              </label>
            </div>
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Actual Start</span>
                <DateInput bind:value={phaseForm.actual_start_date} />
              </label>
            </div>
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Actual End</span>
                <DateInput bind:value={phaseForm.actual_end_date} />
              </label>
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block">
                  <span class="block text-xs font-medium text-neutral-500 mb-1">Weight</span>
                  <input bind:value={phaseForm.weight} type="number" min="1" class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                </label>
              </div>
              <div>
                <label class="block">
                  <span class="block text-xs font-medium text-neutral-500 mb-1">Order</span>
                  <input bind:value={phaseForm.sort_order} type="number" min="0" class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                </label>
              </div>
            </div>
          </div>

          <!-- Section A: Overview & Metadata -->
          <div class="mt-5 pt-4 border-t border-neutral-100">
            <h4 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3">A — Overview & Metadata</h4>
            <div class="space-y-3">
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Objective</span>
                <textarea bind:value={phaseForm.objective} rows="2" class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none" placeholder="Primary goal of this phase"></textarea>
              </label>
              <div class="grid grid-cols-2 gap-4">
                <label class="block">
                  <span class="block text-xs font-medium text-neutral-500 mb-1">Estimated Duration (days)</span>
                  <input type="number" bind:value={phaseForm.estimated_duration_days} min="0" class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="e.g. 90" />
                </label>
                <label class="block">
                  <span class="block text-xs font-medium text-neutral-500 mb-1">Phase Owner Role</span>
                  <input bind:value={phaseForm.phase_owner_role} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="e.g. Project Manager" />
                </label>
              </div>
            </div>
          </div>

          <!-- Section B: Governance & Stakeholders -->
          <div class="mt-5 pt-4 border-t border-neutral-100">
            <h4 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3">B — Governance & Stakeholders</h4>
            <div class="space-y-3">
              <div>
                <div class="flex items-center justify-between mb-1.5">
                  <span class="text-xs font-medium text-neutral-500">RACI Matrix</span>
                  <button type="button" onclick={addRaciRow} class="text-[10px] text-neutral-400 hover:text-neutral-900 transition-colors uppercase tracking-wide">+ Add Row</button>
                </div>
                {#if phaseForm.raci_matrix.length > 0}
                  <div class="overflow-x-auto rounded-lg border border-neutral-200">
                    <table class="w-full text-xs">
                      <thead>
                        <tr class="bg-neutral-50">
                          <th class="px-2 py-1.5 text-left font-medium text-neutral-500">Task</th>
                          <th class="px-2 py-1.5 text-left font-medium text-neutral-500 w-28">Responsible</th>
                          <th class="px-2 py-1.5 text-left font-medium text-neutral-500 w-28">Accountable</th>
                          <th class="px-2 py-1.5 text-left font-medium text-neutral-500 w-28">Consulted</th>
                          <th class="px-2 py-1.5 text-left font-medium text-neutral-500 w-28">Informed</th>
                          <th class="w-8"></th>
                        </tr>
                      </thead>
                      <tbody class="divide-y divide-neutral-100">
                        {#each phaseForm.raci_matrix as _, i}
                          <tr>
                            <td class="px-1 py-1"><input bind:value={phaseForm.raci_matrix[i].task} class="w-full px-2 py-1 border border-neutral-200 rounded text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900" placeholder="Task name" /></td>
                            <td class="px-1 py-1"><input bind:value={phaseForm.raci_matrix[i].responsible} class="w-full px-2 py-1 border border-neutral-200 rounded text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900" placeholder="Role" /></td>
                            <td class="px-1 py-1"><input bind:value={phaseForm.raci_matrix[i].accountable} class="w-full px-2 py-1 border border-neutral-200 rounded text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900" placeholder="Role" /></td>
                            <td class="px-1 py-1"><input bind:value={phaseForm.raci_matrix[i].consulted} class="w-full px-2 py-1 border border-neutral-200 rounded text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900" placeholder="Role" /></td>
                            <td class="px-1 py-1"><input bind:value={phaseForm.raci_matrix[i].informed} class="w-full px-2 py-1 border border-neutral-200 rounded text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900" placeholder="Role" /></td>
                            <td class="px-1 py-1 text-center"><button type="button" onclick={() => removeRaciRow(i)} class="text-neutral-300 hover:text-red-500 transition-colors">&times;</button></td>
                          </tr>
                        {/each}
                      </tbody>
                    </table>
                  </div>
                {/if}
              </div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Approval Authority</span>
                <textarea bind:value={phaseForm.approval_authority} rows="2" class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none" placeholder="Who approves phase completion"></textarea>
              </label>
            </div>
          </div>

          <!-- Section C: Scope & Deliverables -->
          <div class="mt-5 pt-4 border-t border-neutral-100">
            <h4 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3">C — Scope & Deliverables</h4>
            <div class="space-y-4">
              <div>
                <div class="flex items-center justify-between mb-1.5">
                  <span class="text-xs font-medium text-neutral-500">Key Tasks</span>
                  <button type="button" onclick={addKeyTask} class="text-[10px] text-neutral-400 hover:text-neutral-900 transition-colors uppercase tracking-wide">+ Add Task</button>
                </div>
                {#if phaseForm.key_tasks.length > 0}
                  <div class="space-y-2">
                    {#each phaseForm.key_tasks as _, i}
                      <div class="flex gap-2 items-start">
                        <span class="text-xs text-neutral-300 tabular-nums mt-2 w-4 shrink-0">{i + 1}.</span>
                        <input bind:value={phaseForm.key_tasks[i].name} class="flex-1 px-2 py-1.5 border border-neutral-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900" placeholder="Task name" />
                        <input bind:value={phaseForm.key_tasks[i].description} class="flex-2 px-2 py-1.5 border border-neutral-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900" placeholder="Description" />
                        <button type="button" onclick={() => removeKeyTask(i)} class="text-neutral-300 hover:text-red-500 transition-colors mt-1.5">&times;</button>
                      </div>
                    {/each}
                  </div>
                {/if}
              </div>
              <div>
                <div class="flex items-center justify-between mb-1.5">
                  <span class="text-xs font-medium text-neutral-500">Deliverables</span>
                  <button type="button" onclick={addDeliverable} class="text-[10px] text-neutral-400 hover:text-neutral-900 transition-colors uppercase tracking-wide">+ Add Deliverable</button>
                </div>
                {#if phaseForm.deliverables.length > 0}
                  <div class="space-y-2">
                    {#each phaseForm.deliverables as _, i}
                      <div class="flex gap-2 items-start">
                        <input bind:value={phaseForm.deliverables[i].name} class="flex-1 px-2 py-1.5 border border-neutral-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900" placeholder="Deliverable name" />
                        <input bind:value={phaseForm.deliverables[i].description} class="flex-2 px-2 py-1.5 border border-neutral-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900" placeholder="Description" />
                        <label class="flex items-center gap-1 shrink-0 mt-1.5">
                          <input type="checkbox" bind:checked={phaseForm.deliverables[i].is_mandatory} class="w-3.5 h-3.5 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900" />
                          <span class="text-[10px] text-neutral-400 uppercase">Req</span>
                        </label>
                        <button type="button" onclick={() => removeDeliverable(i)} class="text-neutral-300 hover:text-red-500 transition-colors mt-1.5">&times;</button>
                      </div>
                    {/each}
                  </div>
                {/if}
              </div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Out of Scope</span>
                <textarea bind:value={phaseForm.out_of_scope} rows="2" class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none" placeholder="What will not be addressed in this phase"></textarea>
              </label>
            </div>
          </div>

          <!-- Section D: Resources & Risk -->
          <div class="mt-5 pt-4 border-t border-neutral-100">
            <h4 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3">D — Resources & Risk</h4>
            <div class="space-y-4">
              <div>
                <div class="flex items-center justify-between mb-1.5">
                  <span class="text-xs font-medium text-neutral-500">Resource Requirements</span>
                  <button type="button" onclick={addResource} class="text-[10px] text-neutral-400 hover:text-neutral-900 transition-colors uppercase tracking-wide">+ Add Resource</button>
                </div>
                {#if phaseForm.resource_requirements.length > 0}
                  <div class="space-y-2">
                    {#each phaseForm.resource_requirements as _, i}
                      <div class="flex gap-2 items-start">
                        <select bind:value={phaseForm.resource_requirements[i].type} class="w-24 px-2 py-1.5 border border-neutral-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900 bg-white shrink-0">
                          <option value="human">Human</option>
                          <option value="financial">Financial</option>
                          <option value="technical">Technical</option>
                        </select>
                        <input bind:value={phaseForm.resource_requirements[i].description} class="flex-2 px-2 py-1.5 border border-neutral-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900" placeholder="Description" />
                        <input bind:value={phaseForm.resource_requirements[i].quantity} class="w-20 px-2 py-1.5 border border-neutral-200 rounded-lg text-xs tabular-nums focus:outline-none focus:ring-1 focus:ring-neutral-900" placeholder="Qty" />
                        <button type="button" onclick={() => removeResource(i)} class="text-neutral-300 hover:text-red-500 transition-colors mt-1.5">&times;</button>
                      </div>
                    {/each}
                  </div>
                {/if}
              </div>
              <div>
                <div class="flex items-center justify-between mb-1.5">
                  <span class="text-xs font-medium text-neutral-500">Phase Risks</span>
                  <button type="button" onclick={addRisk} class="text-[10px] text-neutral-400 hover:text-neutral-900 transition-colors uppercase tracking-wide">+ Add Risk</button>
                </div>
                {#if phaseForm.phase_risks.length > 0}
                  <div class="space-y-2">
                    {#each phaseForm.phase_risks as _, i}
                      <div class="flex gap-2 items-start">
                        <input bind:value={phaseForm.phase_risks[i].risk} class="flex-2 px-2 py-1.5 border border-neutral-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900" placeholder="Risk description" />
                        <select bind:value={phaseForm.phase_risks[i].likelihood} class="w-24 px-2 py-1.5 border border-neutral-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900 bg-white shrink-0">
                          <option value="low">Low</option>
                          <option value="medium">Medium</option>
                          <option value="high">High</option>
                        </select>
                        <select bind:value={phaseForm.phase_risks[i].impact} class="w-24 px-2 py-1.5 border border-neutral-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900 bg-white shrink-0">
                          <option value="low">Low</option>
                          <option value="medium">Medium</option>
                          <option value="high">High</option>
                        </select>
                        <input bind:value={phaseForm.phase_risks[i].mitigation} class="flex-2 px-2 py-1.5 border border-neutral-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900" placeholder="Mitigation plan" />
                        <button type="button" onclick={() => removeRisk(i)} class="text-neutral-300 hover:text-red-500 transition-colors mt-1.5">&times;</button>
                      </div>
                    {/each}
                  </div>
                {/if}
              </div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Budget Notes</span>
                <textarea bind:value={phaseForm.budget_notes} rows="2" class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none" placeholder="Budget constraints or notes"></textarea>
              </label>
            </div>
          </div>

          <!-- Section E: Quality & Completion -->
          <div class="mt-5 pt-4 border-t border-neutral-100">
            <h4 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3">E — Quality & Completion</h4>
            <div class="space-y-4">
              <div>
                <div class="flex items-center justify-between mb-1.5">
                  <span class="text-xs font-medium text-neutral-500">Success Metrics</span>
                  <button type="button" onclick={addMetric} class="text-[10px] text-neutral-400 hover:text-neutral-900 transition-colors uppercase tracking-wide">+ Add Metric</button>
                </div>
                {#if phaseForm.success_metrics.length > 0}
                  <div class="space-y-2">
                    {#each phaseForm.success_metrics as _, i}
                      <div class="flex gap-2 items-start">
                        <input bind:value={phaseForm.success_metrics[i].metric} class="flex-1 px-2 py-1.5 border border-neutral-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900" placeholder="Metric" />
                        <input bind:value={phaseForm.success_metrics[i].target} class="flex-1 px-2 py-1.5 border border-neutral-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900" placeholder="Target" />
                        <input bind:value={phaseForm.success_metrics[i].measurement_method} class="flex-1 px-2 py-1.5 border border-neutral-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900" placeholder="Measurement method" />
                        <button type="button" onclick={() => removeMetric(i)} class="text-neutral-300 hover:text-red-500 transition-colors mt-1.5">&times;</button>
                      </div>
                    {/each}
                  </div>
                {/if}
              </div>
              <div>
                <div class="flex items-center justify-between mb-1.5">
                  <span class="text-xs font-medium text-neutral-500">Exit Criteria</span>
                  <button type="button" onclick={addExitCriterion} class="text-[10px] text-neutral-400 hover:text-neutral-900 transition-colors uppercase tracking-wide">+ Add Criterion</button>
                </div>
                {#if phaseForm.exit_criteria.length > 0}
                  <div class="space-y-2">
                    {#each phaseForm.exit_criteria as _, i}
                      <div class="flex gap-2 items-start">
                        <input bind:value={phaseForm.exit_criteria[i].criterion} class="flex-2 px-2 py-1.5 border border-neutral-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900" placeholder="Criterion" />
                        <input bind:value={phaseForm.exit_criteria[i].verification_method} class="flex-1 px-2 py-1.5 border border-neutral-200 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-neutral-900" placeholder="Verification method" />
                        <button type="button" onclick={() => removeExitCriterion(i)} class="text-neutral-300 hover:text-red-500 transition-colors mt-1.5">&times;</button>
                      </div>
                    {/each}
                  </div>
                {/if}
              </div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Lessons Learned Prompt</span>
                <textarea bind:value={phaseForm.lessons_learned_prompt} rows="2" class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none" placeholder="Guidance for retrospective"></textarea>
              </label>
            </div>
          </div>

          <div class="mt-4 rounded-lg border border-neutral-200 bg-neutral-50 p-3">
            <label class="block">
              <span class="block text-xs font-medium text-neutral-500 mb-1">Supporting Photos/Documents</span>
              <input
                type="file"
                multiple
                onchange={(event) => onSupportingFilesSelected(event, "phase")}
                class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"
              />
            </label>
            {#if phaseSupportingFiles.length > 0}
              <p class="mt-2 text-xs text-neutral-500">{phaseSupportingFiles.length} file(s) selected.</p>
            {/if}
          </div>
          <div class="flex gap-3 mt-4">
            <button onclick={savePhase} class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors">{editingPhase ? "Save" : "Add Phase"}</button>
            <button onclick={() => {
              showPhaseForm = false;
              phaseSupportingFiles = [];
            }} class="px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors">Cancel</button>
            {#if isDev && !editingPhase}
              <button onclick={devFillPhase} class="ml-auto px-4 py-2 bg-orange-500 text-white rounded-lg text-sm font-medium hover:bg-orange-600 transition-colors">Dev Fill</button>
            {/if}
          </div>
        </div>
        </div>
      {/if}

      {#if project.phases.length === 0 && !showPhaseForm}
        <div class="bg-white rounded-xl border border-neutral-200 p-12 text-center">
          <p class="text-neutral-400 text-sm">No phases yet. Add your first project phase to start tracking progress.</p>
        </div>
      {:else}
        <div class="space-y-3">
          {#each project.phases as phase}
            <div class="bg-white rounded-xl border border-neutral-200 p-5">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                  <span class="text-sm font-medium text-neutral-900">{phase.name}</span>
                  <StatusBadge status={phase.status} />
                  <span class="text-xs text-neutral-400">Weight: {phase.weight}</span>
                </div>
                <div class="flex items-center gap-3">
                  {#if phaseHasSections(phase)}
                    <button onclick={() => togglePhaseExpanded(phase.id)} class="text-xs text-neutral-400 hover:text-neutral-900 transition-colors">{expandedPhases[phase.id] ? 'Hide details' : 'Details'}</button>
                  {/if}
                  <button onclick={() => openEditPhase(phase)} class="text-xs text-neutral-400 hover:text-neutral-900 transition-colors">Edit</button>
                  <button onclick={() => deletePhase(phase.id)} class="text-xs text-neutral-400 hover:text-red-600 transition-colors">Delete</button>
                </div>
              </div>
              <div class="flex items-center gap-6 mt-3 text-xs text-neutral-400">
                <span>Planned: {fmtDate(phase.planned_start_date)} — {fmtDate(phase.planned_end_date)}</span>
                {#if phase.actual_start_date}
                  <span>Actual: {fmtDate(phase.actual_start_date)} — {fmtDate(phase.actual_end_date)}</span>
                {/if}
                <span>Budget: {fmt(phase.planned_budget)}</span>
                <span>Actual: {fmt(phase.cost_total ?? String(phase.actual_cost))}</span>
                <span>Tasks: {phase.completed_task_count}/{phase.task_count}</span>
                <span>Milestones: {phase.milestone_count}</span>
              </div>
              {#if expandedPhases[phase.id] && phaseHasSections(phase)}
                <div class="mt-4 pt-4 border-t border-neutral-100 space-y-4">
                  {@render sectionDisplay(phase)}
                </div>
              {/if}
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}

  <!-- TAB: Milestones -->
  {#if activeTab === "milestones"}
    <div class="space-y-6">
      {#if project.phases.length === 0}
        <div class="bg-white rounded-xl border border-neutral-200 p-12 text-center">
          <p class="text-neutral-400 text-sm">Add phases first, then create milestones within each phase.</p>
        </div>
      {:else}
        {#each project.phases as phase}
          <div>
            <div class="flex items-center justify-between mb-3">
              <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">{phase.name}</h3>
              <button onclick={() => openAddMilestone(phase.id)} class="text-xs text-neutral-400 hover:text-neutral-900 transition-colors">+ Add Milestone</button>
            </div>

            {#if showMilestoneForm && milestoneForm.phase_id === phase.id}
              <div class="bg-white rounded-xl border border-neutral-200 p-4 mb-3">
                {#if !editingMilestone && milestoneTemplates.length > 0}
                  <div class="mb-3">
                    <span class="block text-xs font-medium text-neutral-500 mb-1">Use template</span>
                    <select onchange={(e) => { const v = Number((e.target as HTMLSelectElement).value); applyMilestoneTemplate(v); }} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 bg-white">
                      <option value="0">Select a milestone template...</option>
                      {#each milestoneTemplates as tmpl}
                        <option value={tmpl.id}>{tmpl.name}</option>
                      {/each}
                    </select>
                    {#if selectedMilestoneTemplate}
                      <p class="mt-1.5 text-xs text-neutral-500 leading-relaxed">{selectedMilestoneTemplate.description}</p>
                    {/if}
                  </div>
                {/if}
                <!-- Section A: Milestone Identification -->
                <h4 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3 mt-1">Section A — Milestone Identification</h4>
                <div class="grid grid-cols-3 gap-4">
                  <div class="col-span-2">
                    <label class="block text-xs font-medium text-neutral-500 mb-1">Milestone Name</label>
                    <input bind:value={milestoneForm.name} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="Milestone name" />
                  </div>
                  <div>
                    <label class="block text-xs font-medium text-neutral-500 mb-1">Reference Code</label>
                    <input bind:value={milestoneForm.reference_code} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="e.g. MS-001" />
                  </div>
                </div>

                <!-- Section B: Scheduling & Status -->
                <h4 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3 mt-6">Section B — Scheduling & Status</h4>
                <div class="grid grid-cols-3 gap-4">
                  <div>
                    <label class="block text-xs font-medium text-neutral-500 mb-1">Target Date</label>
                    <DateInput bind:value={milestoneForm.target_date} />
                  </div>
                  <div>
                    <label class="block text-xs font-medium text-neutral-500 mb-1">Typical Offset (days from phase start)</label>
                    <input type="number" bind:value={milestoneForm.typical_offset_days} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="e.g. 14" />
                  </div>
                </div>

                <!-- Section C: Completion Requirements -->
                <h4 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3 mt-6">Section C — Completion Requirements</h4>

                <!-- Success Criteria -->
                <div class="mb-4">
                  <label class="block text-xs font-medium text-neutral-500 mb-2">Success Criteria</label>
                  {#each milestoneForm.success_criteria as _, i}
                    <div class="flex gap-2 mb-2 items-start">
                      <input bind:value={milestoneForm.success_criteria[i].criterion} placeholder="Criterion" class="flex-1 px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                      <input bind:value={milestoneForm.success_criteria[i].verification_method} placeholder="Verification method" class="flex-1 px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                      <button onclick={() => removeMsSuccessCriterion(i)} class="px-2 py-2 text-neutral-400 hover:text-red-500 text-sm">✕</button>
                    </div>
                  {/each}
                  <button onclick={addMsSuccessCriterion} class="text-xs text-neutral-500 hover:text-neutral-900 transition-colors">+ Add criterion</button>
                </div>

                <!-- Key Deliverables -->
                <div class="mb-4">
                  <label class="block text-xs font-medium text-neutral-500 mb-2">Key Deliverables</label>
                  {#each milestoneForm.key_deliverables as _, i}
                    <div class="flex gap-2 mb-2 items-start">
                      <input bind:value={milestoneForm.key_deliverables[i].name} placeholder="Deliverable name" class="w-1/4 px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                      <input bind:value={milestoneForm.key_deliverables[i].description} placeholder="Description" class="flex-1 px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                      <label class="flex items-center gap-1 text-xs text-neutral-500 whitespace-nowrap py-2">
                        <input type="checkbox" bind:checked={milestoneForm.key_deliverables[i].is_mandatory} class="w-3.5 h-3.5 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900" /> Mandatory
                      </label>
                      <button onclick={() => removeMsDeliverable(i)} class="px-2 py-2 text-neutral-400 hover:text-red-500 text-sm">✕</button>
                    </div>
                  {/each}
                  <button onclick={addMsDeliverable} class="text-xs text-neutral-500 hover:text-neutral-900 transition-colors">+ Add deliverable</button>
                </div>

                <!-- Predecessors -->
                <div class="mb-4">
                  <label class="block text-xs font-medium text-neutral-500 mb-2">Dependency Links — Predecessors</label>
                  {#each milestoneForm.predecessors as _, i}
                    <div class="flex gap-2 mb-2 items-start">
                      <input bind:value={milestoneForm.predecessors[i].milestone} placeholder="Predecessor milestone" class="flex-1 px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                      <select bind:value={milestoneForm.predecessors[i].dependency_type} class="w-40 px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 bg-white">
                        <option value="finish_to_start">Finish to Start</option>
                        <option value="start_to_start">Start to Start</option>
                        <option value="finish_to_finish">Finish to Finish</option>
                        <option value="start_to_finish">Start to Finish</option>
                      </select>
                      <input type="number" bind:value={milestoneForm.predecessors[i].lag_days} placeholder="Lag" class="w-20 px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                      <button onclick={() => removeMsPredecessor(i)} class="px-2 py-2 text-neutral-400 hover:text-red-500 text-sm">✕</button>
                    </div>
                  {/each}
                  <button onclick={addMsPredecessor} class="text-xs text-neutral-500 hover:text-neutral-900 transition-colors">+ Add predecessor</button>
                </div>

                <!-- Successors -->
                <div class="mb-4">
                  <label class="block text-xs font-medium text-neutral-500 mb-2">Dependency Links — Successors</label>
                  {#each milestoneForm.successors as _, i}
                    <div class="flex gap-2 mb-2 items-start">
                      <input bind:value={milestoneForm.successors[i].milestone} placeholder="Successor milestone" class="flex-1 px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                      <select bind:value={milestoneForm.successors[i].dependency_type} class="w-40 px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 bg-white">
                        <option value="finish_to_start">Finish to Start</option>
                        <option value="start_to_start">Start to Start</option>
                        <option value="finish_to_finish">Finish to Finish</option>
                        <option value="start_to_finish">Start to Finish</option>
                      </select>
                      <input type="number" bind:value={milestoneForm.successors[i].lag_days} placeholder="Lag" class="w-20 px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                      <button onclick={() => removeMsSuccessor(i)} class="px-2 py-2 text-neutral-400 hover:text-red-500 text-sm">✕</button>
                    </div>
                  {/each}
                  <button onclick={addMsSuccessor} class="text-xs text-neutral-500 hover:text-neutral-900 transition-colors">+ Add successor</button>
                </div>

                <!-- Section D: Accountability & Approval -->
                <h4 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3 mt-6">Section D — Accountability & Approval</h4>
                <div class="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <label class="block text-xs font-medium text-neutral-500 mb-1">Owner Role</label>
                    <input bind:value={milestoneForm.owner_role} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="e.g. Site Manager" />
                  </div>
                  <div>
                    <label class="block text-xs font-medium text-neutral-500 mb-1">Approver Role</label>
                    <input bind:value={milestoneForm.approver_role} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="e.g. Project Manager" />
                  </div>
                </div>

                <!-- Stakeholders to Notify -->
                <div class="mb-4">
                  <label class="block text-xs font-medium text-neutral-500 mb-2">Stakeholders to Notify</label>
                  {#each milestoneForm.stakeholders_to_notify as _, i}
                    <div class="flex gap-2 mb-2 items-start">
                      <input bind:value={milestoneForm.stakeholders_to_notify[i].role} placeholder="Stakeholder role" class="flex-1 px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                      <select bind:value={milestoneForm.stakeholders_to_notify[i].notification_trigger} class="w-44 px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 bg-white">
                        <option value="on_completion">On Completion</option>
                        <option value="on_delay">On Delay</option>
                        <option value="on_risk">On Risk</option>
                        <option value="always">Always</option>
                      </select>
                      <button onclick={() => removeMsStakeholder(i)} class="px-2 py-2 text-neutral-400 hover:text-red-500 text-sm">✕</button>
                    </div>
                  {/each}
                  <button onclick={addMsStakeholder} class="text-xs text-neutral-500 hover:text-neutral-900 transition-colors">+ Add stakeholder</button>
                </div>

                <!-- Supporting Files -->
                <div class="mt-4 rounded-lg border border-neutral-200 bg-neutral-50 p-3">
                  <label class="block">
                    <span class="block text-xs font-medium text-neutral-500 mb-1">Supporting Photos/Documents</span>
                    <input
                      type="file"
                      multiple
                      onchange={(event) => onSupportingFilesSelected(event, "milestone")}
                      class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"
                    />
                  </label>
                  {#if milestoneSupportingFiles.length > 0}
                    <p class="mt-2 text-xs text-neutral-500">{milestoneSupportingFiles.length} file(s) selected.</p>
                  {/if}
                </div>
                <div class="flex gap-3 mt-3">
                  <button onclick={saveMilestone} class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors">{editingMilestone ? "Save" : "Add"}</button>
                  <button onclick={() => {
                    showMilestoneForm = false;
                    milestoneSupportingFiles = [];
                  }} class="px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors">Cancel</button>
                  {#if isDev && !editingMilestone}
                    <button onclick={devFillMilestone} class="ml-auto px-4 py-2 bg-orange-500 text-white rounded-lg text-sm font-medium hover:bg-orange-600 transition-colors">Dev Fill</button>
                  {/if}
                </div>
              </div>
            {/if}

            {#if (milestonesByPhase[phase.id] ?? []).length === 0}
              <div class="bg-white rounded-xl border border-neutral-200 p-6 text-center">
                <p class="text-neutral-400 text-xs">No milestones in this phase</p>
              </div>
            {:else}
              <div class="bg-white rounded-xl border border-neutral-200 divide-y divide-neutral-100">
                {#each milestonesByPhase[phase.id] ?? [] as milestone}
                  <div class="px-5 py-3">
                    <div class="flex items-center justify-between">
                      <div class="flex items-center gap-3">
                        <input
                          type="checkbox"
                          checked={milestone.is_completed}
                          onchange={() => toggleMilestone(phase.id, milestone)}
                          class="w-4 h-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900 cursor-pointer"
                        />
                        <span class="text-sm {milestone.is_completed ? 'text-neutral-400 line-through' : 'text-neutral-900'}">{milestone.name}</span>
                        {#if milestone.reference_code}
                          <span class="text-[10px] text-neutral-400 font-mono">{milestone.reference_code}</span>
                        {/if}
                      </div>
                      <div class="flex items-center gap-4">
                        <span class="text-xs text-neutral-400">{fmtDate(milestone.target_date)}</span>
                        {#if milestone.completed_date}
                          <span class="text-xs text-neutral-400">Completed {fmtDate(milestone.completed_date)}</span>
                        {/if}
                        {#if milestoneHasSections(milestone)}
                          <button onclick={() => toggleMilestoneExpanded(milestone.id)} class="text-xs text-neutral-400 hover:text-neutral-900 transition-colors">{expandedMilestones[milestone.id] ? 'Hide details' : 'Details'}</button>
                        {/if}
                        <button onclick={() => openEditMilestone(phase.id, milestone)} class="text-xs text-neutral-400 hover:text-neutral-900 transition-colors">Edit</button>
                        <button onclick={() => deleteMilestone(phase.id, milestone.id)} class="text-xs text-neutral-400 hover:text-red-600 transition-colors">Delete</button>
                      </div>
                    </div>
                    {#if expandedMilestones[milestone.id] && milestoneHasSections(milestone)}
                      <div class="mt-3 pt-3 border-t border-neutral-100 space-y-3">
                        {#if milestone.reference_code || milestone.typical_offset_days}
                          <div>
                            <h5 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-1">Section A — Milestone Identification</h5>
                            <div class="flex gap-6 text-xs text-neutral-600">
                              {#if milestone.reference_code}<span>Code: <strong>{milestone.reference_code}</strong></span>{/if}
                              {#if milestone.typical_offset_days}<span>Typical offset: <strong>{milestone.typical_offset_days} days</strong></span>{/if}
                            </div>
                          </div>
                        {/if}
                        {#if milestone.success_criteria?.length || milestone.key_deliverables?.length || milestone.predecessors?.length || milestone.successors?.length}
                          <div>
                            <h5 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-1">Section C — Completion Requirements</h5>
                            {#if milestone.success_criteria?.length}
                              <p class="text-[10px] font-medium text-neutral-500 mb-1">Success Criteria</p>
                              <ul class="text-xs text-neutral-600 list-disc list-inside mb-2">
                                {#each milestone.success_criteria as sc}
                                  <li>{sc.criterion} <span class="text-neutral-400">— {sc.verification_method}</span></li>
                                {/each}
                              </ul>
                            {/if}
                            {#if milestone.key_deliverables?.length}
                              <p class="text-[10px] font-medium text-neutral-500 mb-1">Key Deliverables</p>
                              <ul class="text-xs text-neutral-600 list-disc list-inside mb-2">
                                {#each milestone.key_deliverables as d}
                                  <li>{d.name}{d.is_mandatory ? ' (mandatory)' : ''} <span class="text-neutral-400">— {d.description}</span></li>
                                {/each}
                              </ul>
                            {/if}
                            {#if milestone.predecessors?.length}
                              <p class="text-[10px] font-medium text-neutral-500 mb-1">Predecessors</p>
                              <ul class="text-xs text-neutral-600 list-disc list-inside mb-2">
                                {#each milestone.predecessors as p}
                                  <li>{p.milestone} <span class="text-neutral-400">({p.dependency_type}{p.lag_days ? `, +${p.lag_days}d` : ''})</span></li>
                                {/each}
                              </ul>
                            {/if}
                            {#if milestone.successors?.length}
                              <p class="text-[10px] font-medium text-neutral-500 mb-1">Successors</p>
                              <ul class="text-xs text-neutral-600 list-disc list-inside mb-2">
                                {#each milestone.successors as s}
                                  <li>{s.milestone} <span class="text-neutral-400">({s.dependency_type}{s.lag_days ? `, +${s.lag_days}d` : ''})</span></li>
                                {/each}
                              </ul>
                            {/if}
                          </div>
                        {/if}
                        {#if milestone.owner_role || milestone.approver_role || milestone.stakeholders_to_notify?.length}
                          <div>
                            <h5 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-1">Section D — Accountability & Approval</h5>
                            <div class="flex gap-6 text-xs text-neutral-600 mb-1">
                              {#if milestone.owner_role}<span>Owner: <strong>{milestone.owner_role}</strong></span>{/if}
                              {#if milestone.approver_role}<span>Approver: <strong>{milestone.approver_role}</strong></span>{/if}
                            </div>
                            {#if milestone.stakeholders_to_notify?.length}
                              <p class="text-[10px] font-medium text-neutral-500 mb-1">Stakeholders</p>
                              <ul class="text-xs text-neutral-600 list-disc list-inside">
                                {#each milestone.stakeholders_to_notify as st}
                                  <li>{st.role} <span class="text-neutral-400">({st.notification_trigger})</span></li>
                                {/each}
                              </ul>
                            {/if}
                          </div>
                        {/if}
                      </div>
                    {/if}
                  </div>
                {/each}
              </div>
            {/if}
          </div>
        {/each}
      {/if}
    </div>
  {/if}

  <!-- TAB: Tasks -->
  {#if activeTab === "tasks"}
    <div class="space-y-6">
      {#if project.phases.length === 0}
        <div class="bg-white rounded-xl border border-neutral-200 p-12 text-center">
          <p class="text-neutral-400 text-sm">Add phases first, then create tasks within each phase.</p>
        </div>
      {:else}
        {#each project.phases as phase}
          <div>
            <div class="flex items-center justify-between mb-3">
              <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">{phase.name}</h3>
              <button onclick={() => openAddTask(phase.id)} class="text-xs text-neutral-400 hover:text-neutral-900 transition-colors">+ Add Task</button>
            </div>

            {#if showTaskForm && taskForm.phase_id === phase.id}
              <div class="bg-white rounded-xl border border-neutral-200 p-4 mb-3">
                {#if !editingTask && taskTemplates.length > 0}
                  <div class="mb-3">
                    <span class="block text-xs font-medium text-neutral-500 mb-1">Use template</span>
                    <select onchange={(e) => { const v = Number((e.target as HTMLSelectElement).value); applyTaskTemplate(v); }} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 bg-white">
                      <option value="0">Select a task template...</option>
                      {#each taskTemplates as tmpl}
                        <option value={tmpl.id}>{tmpl.name} — {tmpl.assigned_role} ({tmpl.priority})</option>
                      {/each}
                    </select>
                    {#if selectedTaskTemplate}
                      <div class="mt-1.5 flex items-start gap-2">
                        <span class="inline-flex shrink-0 items-center rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide {selectedTaskTemplate.priority === 'critical' ? 'bg-red-100 text-red-700' : selectedTaskTemplate.priority === 'high' ? 'bg-orange-100 text-orange-700' : selectedTaskTemplate.priority === 'medium' ? 'bg-yellow-100 text-yellow-700' : 'bg-neutral-100 text-neutral-500'}">{selectedTaskTemplate.priority}</span>
                        <p class="text-xs text-neutral-500 leading-relaxed">{selectedTaskTemplate.description}</p>
                      </div>
                    {/if}
                  </div>
                {/if}
                <!-- Section A: Task Definition & Context -->
                <h4 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3 mt-1">Section A — Task Definition & Context</h4>
                <div class="grid grid-cols-4 gap-4">
                  <div class="col-span-2">
                    <label class="block text-xs font-medium text-neutral-500 mb-1">Task Name</label>
                    <input bind:value={taskForm.name} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="Task name" />
                  </div>
                  <div>
                    <label class="block text-xs font-medium text-neutral-500 mb-1">Reference Code</label>
                    <input bind:value={taskForm.reference_code} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="e.g. TASK-101" />
                  </div>
                  <div>
                    <label class="block text-xs font-medium text-neutral-500 mb-1">Due Date</label>
                    <DateInput bind:value={taskForm.due_date} />
                  </div>
                </div>

                <!-- Section B: Assignment & Ownership -->
                <h4 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3 mt-6">Section B — Assignment & Ownership</h4>
                <div class="grid grid-cols-3 gap-4 mb-4">
                  <div>
                    <label class="block text-xs font-medium text-neutral-500 mb-1">Assignee</label>
                    <input bind:value={taskForm.assigned_to} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="Assigned to" />
                  </div>
                  <div>
                    <label class="block text-xs font-medium text-neutral-500 mb-1">Reviewer / Approver</label>
                    <input bind:value={taskForm.reviewer_role} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="e.g. Project Manager" />
                  </div>
                </div>
                <div class="mb-4">
                  <label class="block text-xs font-medium text-neutral-500 mb-2">Collaborators</label>
                  {#each taskForm.collaborators as _, i}
                    <div class="flex gap-2 mb-2 items-start">
                      <input bind:value={taskForm.collaborators[i].role} placeholder="Role" class="w-1/3 px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                      <input bind:value={taskForm.collaborators[i].responsibility} placeholder="Responsibility" class="flex-1 px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                      <button onclick={() => removeTaskCollaborator(i)} class="px-2 py-2 text-neutral-400 hover:text-red-500 text-sm">✕</button>
                    </div>
                  {/each}
                  <button onclick={addTaskCollaborator} class="text-xs text-neutral-500 hover:text-neutral-900 transition-colors">+ Add collaborator</button>
                </div>

                <!-- Section C: Scheduling & Effort -->
                <h4 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3 mt-6">Section C — Scheduling & Effort</h4>
                <div class="grid grid-cols-3 gap-4">
                  <div>
                    <label class="block text-xs font-medium text-neutral-500 mb-1">Estimated Effort (hours)</label>
                    <input type="number" bind:value={taskForm.estimated_effort_hours} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="e.g. 40" />
                  </div>
                </div>

                <!-- Section D: Execution Details -->
                <h4 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3 mt-6">Section D — Execution Details</h4>

                <!-- Definition of Done -->
                <div class="mb-4">
                  <label class="block text-xs font-medium text-neutral-500 mb-2">Definition of Done</label>
                  {#each taskForm.definition_of_done as _, i}
                    <div class="flex gap-2 mb-2 items-start">
                      <input bind:value={taskForm.definition_of_done[i].criterion} placeholder="Criterion" class="flex-1 px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                      <label class="flex items-center gap-1 text-xs text-neutral-500 whitespace-nowrap py-2">
                        <input type="checkbox" bind:checked={taskForm.definition_of_done[i].is_required} class="w-3.5 h-3.5 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900" /> Required
                      </label>
                      <button onclick={() => removeTaskDoD(i)} class="px-2 py-2 text-neutral-400 hover:text-red-500 text-sm">✕</button>
                    </div>
                  {/each}
                  <button onclick={addTaskDoD} class="text-xs text-neutral-500 hover:text-neutral-900 transition-colors">+ Add criterion</button>
                </div>

                <!-- Predecessors -->
                <div class="mb-4">
                  <label class="block text-xs font-medium text-neutral-500 mb-2">Dependencies — Predecessors</label>
                  {#each taskForm.predecessors as _, i}
                    <div class="flex gap-2 mb-2 items-start">
                      <input bind:value={taskForm.predecessors[i].task} placeholder="Predecessor task" class="flex-1 px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                      <select bind:value={taskForm.predecessors[i].dependency_type} class="w-40 px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 bg-white">
                        <option value="finish_to_start">Finish to Start</option>
                        <option value="start_to_start">Start to Start</option>
                        <option value="finish_to_finish">Finish to Finish</option>
                        <option value="start_to_finish">Start to Finish</option>
                      </select>
                      <input type="number" bind:value={taskForm.predecessors[i].lag_days} placeholder="Lag" class="w-20 px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                      <button onclick={() => removeTaskPredecessor(i)} class="px-2 py-2 text-neutral-400 hover:text-red-500 text-sm">✕</button>
                    </div>
                  {/each}
                  <button onclick={addTaskPredecessor} class="text-xs text-neutral-500 hover:text-neutral-900 transition-colors">+ Add predecessor</button>
                </div>

                <!-- Successors -->
                <div class="mb-4">
                  <label class="block text-xs font-medium text-neutral-500 mb-2">Dependencies — Successors</label>
                  {#each taskForm.successors as _, i}
                    <div class="flex gap-2 mb-2 items-start">
                      <input bind:value={taskForm.successors[i].task} placeholder="Successor task" class="flex-1 px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                      <select bind:value={taskForm.successors[i].dependency_type} class="w-40 px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 bg-white">
                        <option value="finish_to_start">Finish to Start</option>
                        <option value="start_to_start">Start to Start</option>
                        <option value="finish_to_finish">Finish to Finish</option>
                        <option value="start_to_finish">Start to Finish</option>
                      </select>
                      <input type="number" bind:value={taskForm.successors[i].lag_days} placeholder="Lag" class="w-20 px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                      <button onclick={() => removeTaskSuccessor(i)} class="px-2 py-2 text-neutral-400 hover:text-red-500 text-sm">✕</button>
                    </div>
                  {/each}
                  <button onclick={addTaskSuccessor} class="text-xs text-neutral-500 hover:text-neutral-900 transition-colors">+ Add successor</button>
                </div>

                <!-- Section E: Resources & Attachments -->
                <h4 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3 mt-6">Section E — Resources & Attachments</h4>

                <!-- Tools Required -->
                <div class="mb-4">
                  <label class="block text-xs font-medium text-neutral-500 mb-2">Tools Required</label>
                  {#each taskForm.tools_required as _, i}
                    <div class="flex gap-2 mb-2 items-start">
                      <input bind:value={taskForm.tools_required[i].name} placeholder="Tool name" class="w-1/3 px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                      <input bind:value={taskForm.tools_required[i].description} placeholder="Description" class="flex-1 px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                      <button onclick={() => removeTaskTool(i)} class="px-2 py-2 text-neutral-400 hover:text-red-500 text-sm">✕</button>
                    </div>
                  {/each}
                  <button onclick={addTaskTool} class="text-xs text-neutral-500 hover:text-neutral-900 transition-colors">+ Add tool</button>
                </div>

                <!-- Reference Links -->
                <div class="mb-4">
                  <label class="block text-xs font-medium text-neutral-500 mb-2">Reference Links</label>
                  {#each taskForm.reference_links as _, i}
                    <div class="flex gap-2 mb-2 items-start">
                      <input bind:value={taskForm.reference_links[i].title} placeholder="Link title" class="w-1/3 px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                      <input bind:value={taskForm.reference_links[i].url} placeholder="URL" class="flex-1 px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                      <button onclick={() => removeTaskRefLink(i)} class="px-2 py-2 text-neutral-400 hover:text-red-500 text-sm">✕</button>
                    </div>
                  {/each}
                  <button onclick={addTaskRefLink} class="text-xs text-neutral-500 hover:text-neutral-900 transition-colors">+ Add link</button>
                </div>

                <!-- Supporting Files -->
                <div class="mt-4 rounded-lg border border-neutral-200 bg-neutral-50 p-3">
                  <label class="block">
                    <span class="block text-xs font-medium text-neutral-500 mb-1">Supporting Photos/Documents</span>
                    <input
                      type="file"
                      multiple
                      onchange={(event) => onSupportingFilesSelected(event, "task")}
                      class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"
                    />
                  </label>
                  {#if taskSupportingFiles.length > 0}
                    <p class="mt-2 text-xs text-neutral-500">{taskSupportingFiles.length} file(s) selected.</p>
                  {/if}
                </div>
                <div class="flex gap-3 mt-3">
                  <button onclick={saveTask} class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors">{editingTask ? "Save" : "Add"}</button>
                  <button onclick={() => {
                    showTaskForm = false;
                    taskSupportingFiles = [];
                  }} class="px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors">Cancel</button>
                  {#if isDev && !editingTask}
                    <button onclick={devFillTask} class="ml-auto px-4 py-2 bg-orange-500 text-white rounded-lg text-sm font-medium hover:bg-orange-600 transition-colors">Dev Fill</button>
                  {/if}
                </div>
              </div>
            {/if}

            {#if (tasksByPhase[phase.id] ?? []).length === 0}
              <div class="bg-white rounded-xl border border-neutral-200 p-6 text-center">
                <p class="text-neutral-400 text-xs">No tasks in this phase</p>
              </div>
            {:else}
              <div class="bg-white rounded-xl border border-neutral-200 divide-y divide-neutral-100">
                {#each tasksByPhase[phase.id] ?? [] as task}
                  <div class="px-5 py-3">
                    <div class="flex items-center justify-between">
                      <div class="flex items-center gap-3">
                        <span class="text-sm text-neutral-900">{task.name}</span>
                        {#if task.reference_code}
                          <span class="text-[10px] text-neutral-400 font-mono">{task.reference_code}</span>
                        {/if}
                        {#if task.assigned_to}
                          <span class="text-xs text-neutral-400">{task.assigned_to}</span>
                        {/if}
                      </div>
                      <div class="flex items-center gap-4">
                        <span class="text-xs text-neutral-400">{fmtDate(task.due_date)}</span>
                        <select
                          value={task.status}
                          onchange={(e) => quickUpdateTaskStatus(phase.id, task, (e.target as HTMLSelectElement).value)}
                          class="px-2 py-1 border border-neutral-200 rounded text-xs focus:outline-none focus:ring-2 focus:ring-neutral-900"
                        >
                          <option value="pending">Pending</option>
                          <option value="in_progress">In Progress</option>
                          <option value="completed">Completed</option>
                        </select>
                        {#if taskHasSections(task)}
                          <button onclick={() => toggleTaskExpanded(task.id)} class="text-xs text-neutral-400 hover:text-neutral-900 transition-colors">{expandedTasks[task.id] ? 'Hide details' : 'Details'}</button>
                        {/if}
                        <button onclick={() => openEditTask(phase.id, task)} class="text-xs text-neutral-400 hover:text-neutral-900 transition-colors">Edit</button>
                        <button onclick={() => deleteTask(phase.id, task.id)} class="text-xs text-neutral-400 hover:text-red-600 transition-colors">Delete</button>
                      </div>
                    </div>
                    {#if expandedTasks[task.id] && taskHasSections(task)}
                      <div class="mt-3 pt-3 border-t border-neutral-100 space-y-3">
                        {#if task.reference_code || task.estimated_effort_hours}
                          <div>
                            <h5 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-1">Section A — Task Definition</h5>
                            <div class="flex gap-6 text-xs text-neutral-600">
                              {#if task.reference_code}<span>Code: <strong>{task.reference_code}</strong></span>{/if}
                              {#if task.estimated_effort_hours}<span>Estimated effort: <strong>{task.estimated_effort_hours}h</strong></span>{/if}
                            </div>
                          </div>
                        {/if}
                        {#if task.reviewer_role || task.collaborators?.length}
                          <div>
                            <h5 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-1">Section B — Assignment & Ownership</h5>
                            {#if task.reviewer_role}
                              <p class="text-xs text-neutral-600 mb-1">Reviewer: <strong>{task.reviewer_role}</strong></p>
                            {/if}
                            {#if task.collaborators?.length}
                              <p class="text-[10px] font-medium text-neutral-500 mb-1">Collaborators</p>
                              <ul class="text-xs text-neutral-600 list-disc list-inside">
                                {#each task.collaborators as c}
                                  <li>{c.role} <span class="text-neutral-400">— {c.responsibility}</span></li>
                                {/each}
                              </ul>
                            {/if}
                          </div>
                        {/if}
                        {#if task.definition_of_done?.length || task.predecessors?.length || task.successors?.length}
                          <div>
                            <h5 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-1">Section D — Execution Details</h5>
                            {#if task.definition_of_done?.length}
                              <p class="text-[10px] font-medium text-neutral-500 mb-1">Definition of Done</p>
                              <ul class="text-xs text-neutral-600 list-disc list-inside mb-2">
                                {#each task.definition_of_done as d}
                                  <li>{d.criterion} {d.is_required ? '' : '<span class="text-neutral-400">(optional)</span>'}</li>
                                {/each}
                              </ul>
                            {/if}
                            {#if task.predecessors?.length}
                              <p class="text-[10px] font-medium text-neutral-500 mb-1">Predecessors</p>
                              <ul class="text-xs text-neutral-600 list-disc list-inside mb-2">
                                {#each task.predecessors as p}
                                  <li>{p.task} <span class="text-neutral-400">({p.dependency_type}{p.lag_days ? `, +${p.lag_days}d` : ''})</span></li>
                                {/each}
                              </ul>
                            {/if}
                            {#if task.successors?.length}
                              <p class="text-[10px] font-medium text-neutral-500 mb-1">Successors</p>
                              <ul class="text-xs text-neutral-600 list-disc list-inside mb-2">
                                {#each task.successors as s}
                                  <li>{s.task} <span class="text-neutral-400">({s.dependency_type}{s.lag_days ? `, +${s.lag_days}d` : ''})</span></li>
                                {/each}
                              </ul>
                            {/if}
                          </div>
                        {/if}
                        {#if task.tools_required?.length || task.reference_links?.length}
                          <div>
                            <h5 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-1">Section E — Resources & Attachments</h5>
                            {#if task.tools_required?.length}
                              <p class="text-[10px] font-medium text-neutral-500 mb-1">Tools Required</p>
                              <ul class="text-xs text-neutral-600 list-disc list-inside mb-2">
                                {#each task.tools_required as tool}
                                  <li>{tool.name} <span class="text-neutral-400">— {tool.description}</span></li>
                                {/each}
                              </ul>
                            {/if}
                            {#if task.reference_links?.length}
                              <p class="text-[10px] font-medium text-neutral-500 mb-1">Reference Links</p>
                              <ul class="text-xs text-neutral-600 list-disc list-inside">
                                {#each task.reference_links as link}
                                  <li><a href={link.url} target="_blank" rel="noopener noreferrer" class="underline hover:text-neutral-900">{link.title}</a></li>
                                {/each}
                              </ul>
                            {/if}
                          </div>
                        {/if}
                      </div>
                    {/if}
                  </div>
                {/each}
              </div>
            {/if}
          </div>
        {/each}
      {/if}
    </div>
  {/if}

  <!-- TAB: Costs -->
  {#if activeTab === "costs"}
    <div class="space-y-6">
      <!-- Summary -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6">
        <div class="grid grid-cols-3 gap-6 text-center">
          <div>
            <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Total Planned</p>
            <p class="text-lg font-semibold text-neutral-900 tabular-nums mt-1">{fmt(project.total_planned_budget)}</p>
          </div>
          <div>
            <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Total Actual</p>
            <p class="text-lg font-semibold text-neutral-900 tabular-nums mt-1">{fmt(project.total_actual_cost)}</p>
          </div>
          <div>
            <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Variance</p>
            <p class="text-lg font-semibold tabular-nums mt-1 {Number(project.total_budget_variance) >= 0 ? 'text-green-600' : 'text-red-600'}">{fmt(project.total_budget_variance)}</p>
          </div>
        </div>
      </div>

      {#if project.phases.length === 0}
        <div class="bg-white rounded-xl border border-neutral-200 p-12 text-center">
          <p class="text-neutral-400 text-sm">Add phases first, then track costs within each phase.</p>
        </div>
      {:else}
        {#each project.phases as phase}
          <div>
            <div class="flex items-center justify-between mb-3">
              <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">{phase.name}
                <span class="font-normal text-neutral-400 normal-case tracking-normal ml-2">Budget: {fmt(phase.planned_budget)}</span>
              </h3>
              <button onclick={() => openAddCost(phase.id)} class="text-xs text-neutral-400 hover:text-neutral-900 transition-colors">+ Add Cost</button>
            </div>

            {#if showCostForm && costForm.phase_id === phase.id}
              <div class="bg-white rounded-xl border border-neutral-200 p-4 mb-3">
                <div class="grid grid-cols-3 gap-4">
                  <div>
                    <input bind:value={costForm.description} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="Description" />
                  </div>
                  <div>
                    <input bind:value={costForm.amount} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="Amount" />
                  </div>
                  <div>
                    <DateInput bind:value={costForm.date} />
                  </div>
                  <div>
                    <select bind:value={costForm.category} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
                      <option value="materials">Materials</option>
                      <option value="labor">Labor</option>
                      <option value="permits">Permits & Fees</option>
                      <option value="equipment">Equipment</option>
                      <option value="subcontractor">Subcontractor</option>
                      <option value="other">Other</option>
                    </select>
                  </div>
                  <div>
                    <input bind:value={costForm.vendor} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="Vendor" />
                  </div>
                  <div>
                    <input bind:value={costForm.reference_number} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="Reference #" />
                  </div>
                </div>
                <div class="mt-3 rounded-lg border border-neutral-200 bg-neutral-50 p-3">
                  <label class="block">
                    <span class="block text-xs font-medium text-neutral-500 mb-1">Supporting Photos/Documents</span>
                    <input
                      type="file"
                      multiple
                      onchange={(event) => onSupportingFilesSelected(event, "cost")}
                      class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"
                    />
                  </label>
                  {#if costSupportingFiles.length > 0}
                    <p class="mt-2 text-xs text-neutral-500">{costSupportingFiles.length} file(s) selected.</p>
                  {/if}
                </div>
                <div class="flex gap-3 mt-3">
                  <button onclick={saveCost} class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors">Add</button>
                  <button onclick={() => {
                    showCostForm = false;
                    costSupportingFiles = [];
                  }} class="px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors">Cancel</button>
                  {#if isDev}
                    <button onclick={devFillCost} class="ml-auto px-4 py-2 bg-orange-500 text-white rounded-lg text-sm font-medium hover:bg-orange-600 transition-colors">Dev Fill</button>
                  {/if}
                </div>
              </div>
            {/if}

            {#if (costsByPhase[phase.id] ?? []).length === 0}
              <div class="bg-white rounded-xl border border-neutral-200 p-6 text-center">
                <p class="text-neutral-400 text-xs">No cost entries in this phase</p>
              </div>
            {:else}
              <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
                <table class="w-full text-sm">
                  <thead>
                    <tr class="border-b border-neutral-200">
                      <th class="px-4 py-2.5 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Description</th>
                      <th class="px-4 py-2.5 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Category</th>
                      <th class="px-4 py-2.5 text-right text-xs font-medium text-neutral-400 uppercase tracking-wider">Amount</th>
                      <th class="px-4 py-2.5 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Date</th>
                      <th class="px-4 py-2.5 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Vendor</th>
                      <th class="px-4 py-2.5 text-right text-xs font-medium text-neutral-400 uppercase tracking-wider"></th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-neutral-100">
                    {#each costsByPhase[phase.id] ?? [] as cost}
                      <tr>
                        <td class="px-4 py-2.5 text-neutral-900">{cost.description}</td>
                        <td class="px-4 py-2.5"><span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-neutral-100 text-neutral-600">{costCategoryLabels[cost.category]}</span></td>
                        <td class="px-4 py-2.5 text-right text-neutral-900 tabular-nums">{fmt(cost.amount)}</td>
                        <td class="px-4 py-2.5 text-neutral-500">{fmtDate(cost.date)}</td>
                        <td class="px-4 py-2.5 text-neutral-500">{cost.vendor || "\u2014"}</td>
                        <td class="px-4 py-2.5 text-right">
                          <button onclick={() => deleteCost(phase.id, cost.id)} class="text-xs text-neutral-400 hover:text-red-600 transition-colors">Delete</button>
                        </td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </div>
            {/if}
          </div>
        {/each}
      {/if}
    </div>
  {/if}

  <!-- TAB: Timeline -->
  {#if activeTab === "documents"}
    {#if canAddRepositoryDocument}
      <div class="mb-3 flex justify-end">
        <button
          onclick={() => (showAddDocumentModal = true)}
          class="inline-flex items-center rounded-lg bg-neutral-900 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-neutral-800"
        >
          + Add Document
        </button>
      </div>
    {/if}
    <DocumentRecordsTable
      title="Project Documents"
      subtitle="Auto-filtered document repository view for this project."
      query={{ project: Number(projectId) }}
      refreshKey={documentsRefreshKey}
      pageSize={14}
      emptyMessage="No repository documents are linked to this project yet."
      onRowClick={(row) => (documentDrawerId = row.id)}
    />
    <DocumentDetailDrawer
      open={documentDrawerId !== null}
      documentId={documentDrawerId}
      refPath={`/projects/${projectId}`}
      onclose={() => (documentDrawerId = null)}
    />
    {#if canAddRepositoryDocument}
      <AddDocumentModal
        open={showAddDocumentModal}
        initialProjectId={project?.id ?? Number(projectId)}
        lockProject={true}
        onclose={() => (showAddDocumentModal = false)}
        oncreated={handleProjectDocumentCreated}
      />
    {/if}
  {/if}

  <!-- TAB: Cap Table -->
  {#if activeTab === "cap_table"}
    <div class="bg-white rounded-xl border border-neutral-200 p-6">
      <p class="text-sm text-neutral-600 mb-4">
        Manage investor equity ownership and capital contributions for this project.
      </p>
      <a
        href={`/projects/${projectId}/cap-table`}
        class="inline-flex items-center px-4 py-2 bg-neutral-900 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
      >
        Open Cap Table
      </a>
    </div>
  {/if}

  <!-- TAB: Distributions -->
  {#if activeTab === "distributions"}
    <div class="bg-white rounded-xl border border-neutral-200 p-6">
      <p class="text-sm text-neutral-600 mb-4">
        View and manage waterfall distributions to investors for this project.
      </p>
      <a
        href={`/projects/${projectId}/distributions`}
        class="inline-flex items-center px-4 py-2 bg-neutral-900 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
      >
        Open Distributions
      </a>
    </div>
  {/if}

  <!-- TAB: Timeline -->
  {#if activeTab === "timeline"}
    {#if timelineData}
      <ProjectTimeline data={timelineData} />
    {:else}
      <div class="bg-white rounded-xl border border-neutral-200 p-12 text-center">
        <p class="text-neutral-400 text-sm">Loading timeline...</p>
      </div>
    {/if}
  {/if}
{/if}

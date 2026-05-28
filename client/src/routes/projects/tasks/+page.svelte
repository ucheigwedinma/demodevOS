<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { currency } from "$lib/stores/currency.svelte";
  import { onboarding } from "$lib/stores/onboarding.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type {
    PaginatedResponse,
    ProjectTask,
    ProjectTaskComment,
    ProjectWorkPackage,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  type TaskViewScope = "personal" | "team" | "cross_project";
  type TaskStatus = "pending" | "in_progress" | "completed";
  type TaskPriority = "low" | "medium" | "high" | "critical";
  type SlaFilter = "" | "breached" | "at_risk" | "on_track" | "completed" | "not_configured";

  type TaskSetupOptions = {
    projects: { id: number; name: string }[];
    phases: { id: number; project: number; project_name: string; name: string; status: string }[];
    documents: { id: number; project: number | null; title: string; document_number: string; status: string }[];
    contracts: { id: number; project: number; variation_number: string; title: string; status: string }[];
    risks: { id: number; project: number; title: string; severity: string; status: string }[];
    users: { id: number; email: string; full_name: string; role_name: string | null }[];
  };

  type WorkPackageSetupOptions = {
    projects: { id: number; name: string }[];
    phases: { id: number; project: number; project_name: string; name: string; status: string }[];
    contractors: { id: number; name: string; category: string; compliance_status: string }[];
    drawings: { id: number; project: number | null; title: string; document_number: string; status: string }[];
    purchase_orders: {
      id: number;
      project: number | null;
      po_number: string;
      status: string;
      vendor_name: string;
      expected_delivery_date: string | null;
      total_amount: string;
    }[];
    cost_entries: {
      id: number;
      project: number;
      phase: number;
      phase_name: string;
      description: string;
      amount: string;
      category: string;
      date: string;
    }[];
    inspections: {
      id: number;
      project: number;
      inspection_number: string;
      status: string;
      inspected_on: string;
      work_package: string;
      inspector_name: string;
    }[];
    examples: string[];
  };

  type TaskFormState = {
    project_id: string;
    phase_id: string;
    name: string;
    description: string;
    work_package: string;
    reference_code: string;
    status: TaskStatus;
    priority: TaskPriority;
    assigned_to: string;
    assigned_user: string;
    assigned_external_ref: string;
    reviewer_role: string;
    collaborators: { role: string; responsibility: string }[];
    estimated_effort_hours: string;
    predecessors: { task: string; dependency_type: string; lag_days: number }[];
    successors: { task: string; dependency_type: string; lag_days: number }[];
    definition_of_done: { criterion: string; is_required: boolean }[];
    tools_required: { name: string; description: string }[];
    reference_links: { title: string; url: string }[];
    due_date: string;
    sla_target_at: string;
    sort_order: string;
    linked_documents: number[];
    linked_variation_orders: number[];
    linked_risks: number[];
  };

  type WorkPackageFormState = {
    project_id: string;
    phase_id: string;
    package_id: string;
    name: string;
    scope_description: string;
    contractor_id: string;
    budget: string;
    start_date: string;
    end_date: string;
    boq_items_text: string;
    quality_requirements: string;
    safety_requirements: string;
    inspection_plan: string;
    drawings: number[];
    linked_purchase_orders: number[];
    linked_cost_entries: number[];
    linked_contractors: number[];
    linked_inspections: number[];
  };

  let loading = $state(true);
  let setupLoading = $state(true);
  let saving = $state(false);
  let tasks = $state<ProjectTask[]>([]);
  let totalCount = $state(0);
  let currentPage = $state(1);
  let pageSize = $state(20);

  let viewScope = $state<TaskViewScope>("cross_project");
  let searchInput = $state("");
  let searchQuery = $state("");
  let projectFilter = $state("");
  let phaseFilter = $state("");
  let statusFilter = $state<"" | TaskStatus>("");
  let priorityFilter = $state<"" | TaskPriority>("");
  let slaFilter = $state<SlaFilter>("");
  let ordering = $state("-updated_at");

  let showTaskModal = $state(false);
  let editingTask = $state<ProjectTask | null>(null);
  let taskSupportingFiles = $state<File[]>([]);

  let commentsTask = $state<ProjectTask | null>(null);
  let commentsLoading = $state(false);
  let commentsPosting = $state(false);
  let comments = $state<ProjectTaskComment[]>([]);
  let newComment = $state("");

  let activeTab = $state<"tasks" | "work_packages">("tasks");

  let workPackagesLoading = $state(true);
  let workPackageSetupLoading = $state(true);
  let workPackageSaving = $state(false);
  let workPackages = $state<ProjectWorkPackage[]>([]);
  let workPackageTotalCount = $state(0);
  let workPackagePage = $state(1);
  let workPackagePageSize = $state(20);
  let workPackageSearchInput = $state("");
  let workPackageSearchQuery = $state("");
  let workPackageProjectFilter = $state("");
  let workPackagePhaseFilter = $state("");
  let workPackageContractorFilter = $state("");
  let workPackageOrdering = $state("-updated_at");
  let showWorkPackageModal = $state(false);
  let editingWorkPackage = $state<ProjectWorkPackage | null>(null);

  let setupOptions = $state<TaskSetupOptions>({
    projects: [],
    phases: [],
    documents: [],
    contracts: [],
    risks: [],
    users: [],
  });

  let workPackageSetupOptions = $state<WorkPackageSetupOptions>({
    projects: [],
    phases: [],
    contractors: [],
    drawings: [],
    purchase_orders: [],
    cost_entries: [],
    inspections: [],
    examples: [],
  });

  let taskForm = $state<TaskFormState>({
    project_id: "",
    phase_id: "",
    name: "",
    description: "",
    work_package: "",
    reference_code: "",
    status: "pending",
    priority: "medium",
    assigned_to: "",
    assigned_user: "",
    assigned_external_ref: "",
    reviewer_role: "",
    collaborators: [],
    estimated_effort_hours: "",
    predecessors: [],
    successors: [],
    definition_of_done: [],
    tools_required: [],
    reference_links: [],
    due_date: "",
    sla_target_at: "",
    sort_order: "0",
    linked_documents: [],
    linked_variation_orders: [],
    linked_risks: [],
  });

  let workPackageForm = $state<WorkPackageFormState>({
    project_id: "",
    phase_id: "",
    package_id: "",
    name: "",
    scope_description: "",
    contractor_id: "",
    budget: "",
    start_date: "",
    end_date: "",
    boq_items_text: "",
    quality_requirements: "",
    safety_requirements: "",
    inspection_plan: "",
    drawings: [],
    linked_purchase_orders: [],
    linked_cost_entries: [],
    linked_contractors: [],
    linked_inspections: [],
  });

  let searchTimeout: ReturnType<typeof setTimeout> | undefined;
  let fetchToken = 0;
  let setupFetchToken = 0;
  let workPackageSearchTimeout: ReturnType<typeof setTimeout> | undefined;
  let workPackageFetchToken = 0;
  let workPackageSetupFetchToken = 0;

  const totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  const startItem = $derived(totalCount === 0 ? 0 : (currentPage - 1) * pageSize + 1);
  const endItem = $derived(Math.min(currentPage * pageSize, totalCount));
  const workPackageTotalPages = $derived(Math.max(1, Math.ceil(workPackageTotalCount / workPackagePageSize)));
  const workPackageStartItem = $derived(
    workPackageTotalCount === 0 ? 0 : (workPackagePage - 1) * workPackagePageSize + 1
  );
  const workPackageEndItem = $derived(Math.min(workPackagePage * workPackagePageSize, workPackageTotalCount));
  const currentUserId = $derived(onboarding.user?.id ?? null);

  const priorityBadge: Record<TaskPriority, string> = {
    low: "bg-neutral-100 text-neutral-700 border-neutral-200",
    medium: "bg-amber-50 text-amber-700 border-amber-100",
    high: "bg-orange-50 text-orange-700 border-orange-100",
    critical: "bg-rose-50 text-rose-700 border-rose-100",
  };

  const priorityLabel: Record<TaskPriority, string> = {
    low: "Low",
    medium: "Medium",
    high: "High",
    critical: "Critical",
  };

  const slaBadge: Record<string, string> = {
    breached: "bg-rose-50 text-rose-700 border-rose-100",
    at_risk: "bg-amber-50 text-amber-700 border-amber-100",
    on_track: "bg-emerald-50 text-emerald-700 border-emerald-100",
    completed: "bg-blue-50 text-blue-700 border-blue-100",
    not_configured: "bg-neutral-100 text-neutral-600 border-neutral-200",
  };

  const filteredPhaseOptions = $derived.by(() => {
    if (!projectFilter) return setupOptions.phases;
    const projectId = Number(projectFilter);
    return setupOptions.phases.filter((phase) => phase.project === projectId);
  });

  const formPhaseOptions = $derived.by(() => {
    if (!taskForm.project_id) return [] as TaskSetupOptions["phases"];
    const projectId = Number(taskForm.project_id);
    return setupOptions.phases.filter((phase) => phase.project === projectId);
  });

  const formDocumentOptions = $derived.by(() => {
    if (!taskForm.project_id) return [] as TaskSetupOptions["documents"];
    const projectId = Number(taskForm.project_id);
    return setupOptions.documents.filter((row) => row.project === null || row.project === projectId);
  });

  const formContractOptions = $derived.by(() => {
    if (!taskForm.project_id) return [] as TaskSetupOptions["contracts"];
    const projectId = Number(taskForm.project_id);
    return setupOptions.contracts.filter((row) => row.project === projectId);
  });

  const formRiskOptions = $derived.by(() => {
    if (!taskForm.project_id) return [] as TaskSetupOptions["risks"];
    const projectId = Number(taskForm.project_id);
    return setupOptions.risks.filter((row) => row.project === projectId);
  });

  const workPackageFilteredPhaseOptions = $derived.by(() => {
    if (!workPackageProjectFilter) return workPackageSetupOptions.phases;
    const projectId = Number(workPackageProjectFilter);
    return workPackageSetupOptions.phases.filter((phase) => phase.project === projectId);
  });

  const workPackageFormPhaseOptions = $derived.by(() => {
    if (!workPackageForm.project_id) return [] as WorkPackageSetupOptions["phases"];
    const projectId = Number(workPackageForm.project_id);
    return workPackageSetupOptions.phases.filter((phase) => phase.project === projectId);
  });

  const workPackageFormDrawings = $derived.by(() => {
    if (!workPackageForm.project_id) return [] as WorkPackageSetupOptions["drawings"];
    const projectId = Number(workPackageForm.project_id);
    return workPackageSetupOptions.drawings.filter((row) => row.project === null || row.project === projectId);
  });

  const workPackageFormPurchaseOrders = $derived.by(() => {
    if (!workPackageForm.project_id) return [] as WorkPackageSetupOptions["purchase_orders"];
    const projectId = Number(workPackageForm.project_id);
    return workPackageSetupOptions.purchase_orders.filter((row) => row.project === projectId);
  });

  const workPackageFormCostEntries = $derived.by(() => {
    if (!workPackageForm.project_id) return [] as WorkPackageSetupOptions["cost_entries"];
    const projectId = Number(workPackageForm.project_id);
    return workPackageSetupOptions.cost_entries.filter((row) => row.project === projectId);
  });

  const workPackageFormInspections = $derived.by(() => {
    if (!workPackageForm.project_id) return [] as WorkPackageSetupOptions["inspections"];
    const projectId = Number(workPackageForm.project_id);
    return workPackageSetupOptions.inspections.filter((row) => row.project === projectId);
  });

  const personalTaskCount = $derived(
    currentUserId ? tasks.filter((task) => task.assigned_user === currentUserId).length : 0
  );
  const breachedTaskCount = $derived(tasks.filter((task) => task.sla_status === "breached").length);
  const dueSoonCount = $derived(
    tasks.filter((task) => {
      if (!task.due_date || task.status === "completed") return false;
      const days = daysUntil(task.due_date);
      return days !== null && days >= 0 && days <= 7;
    }).length
  );
  const workPackageTotalBudget = $derived(
    workPackages.reduce((sum, row) => sum + Number(row.budget || 0), 0)
  );
  const workPackageEndingSoon = $derived(
    workPackages.filter((row) => {
      if (!row.end_date) return false;
      const days = daysUntil(row.end_date);
      return days !== null && days >= 0 && days <= 14;
    }).length
  );
  const workPackageInspectionLinkedCount = $derived(
    workPackages.filter((row) => row.linked_modules.inspections.count > 0).length
  );

  function listRows<T>(payload: PaginatedResponse<T> | T[]): T[] {
    if (Array.isArray(payload)) return payload;
    return payload.results ?? [];
  }

  function apiErrorDetail(err: unknown, fallback = "Please try again later"): string {
    if (err instanceof ApiError) {
      const detail = err.data?.detail;
      if (typeof detail === "string" && detail.trim().length > 0) return detail;
      if (err.fieldErrors) {
        const first = Object.entries(err.fieldErrors)[0];
        if (first) return `${first[0]}: ${first[1][0]}`;
      }
    }
    return fallback;
  }

  function formatDate(value: string | null): string {
    if (!value) return "--";
    return new Date(value).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  function formatDateTime(value: string | null): string {
    if (!value) return "--";
    return new Date(value).toLocaleString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function toDatetimeLocalInput(value: string | null): string {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    date.setMinutes(date.getMinutes() - date.getTimezoneOffset());
    return date.toISOString().slice(0, 16);
  }

  function toIsoDatetime(value: string): string | null {
    const trimmed = value.trim();
    if (!trimmed) return null;
    const date = new Date(trimmed);
    if (Number.isNaN(date.getTime())) return null;
    return date.toISOString();
  }

  function daysUntil(value: string | null): number | null {
    if (!value) return null;
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    const target = new Date(value);
    target.setHours(0, 0, 0, 0);
    if (Number.isNaN(target.getTime())) return null;
    return Math.ceil((target.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  }

  function formatSeconds(seconds: number | null): string {
    if (seconds === null) return "--";
    if (seconds <= 0) return "Expired";
    const abs = Math.abs(seconds);
    const days = Math.floor(abs / 86400);
    const hours = Math.floor((abs % 86400) / 3600);
    const minutes = Math.floor((abs % 3600) / 60);
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  }

  function buildTaskParams(page = currentPage): Record<string, string> {
    const params: Record<string, string> = {
      page: String(page),
      page_size: String(pageSize),
      ordering,
      view_scope: viewScope,
    };
    if (searchQuery) params.search = searchQuery;
    if (projectFilter) params.project = projectFilter;
    if (phaseFilter) params.phase = phaseFilter;
    if (statusFilter) params.status = statusFilter;
    if (priorityFilter) params.priority = priorityFilter;
    if (slaFilter) params.sla_status = slaFilter;
    return params;
  }

  async function fetchTasks() {
    loading = true;
    const token = ++fetchToken;
    try {
      const response = await api.get<PaginatedResponse<ProjectTask>>("/projects/tasks/", buildTaskParams());
      if (token !== fetchToken) return;
      tasks = response.results;
      totalCount = response.count;
      const maxPage = Math.max(1, Math.ceil(response.count / pageSize));
      if (currentPage > maxPage) currentPage = maxPage;
    } catch (err) {
      if (token !== fetchToken) return;
      tasks = [];
      totalCount = 0;
      toast.error("Load failed", apiErrorDetail(err, "Could not load tasks and work packages"));
    } finally {
      if (token === fetchToken) loading = false;
    }
  }

  async function fetchSetupOptions() {
    setupLoading = true;
    const token = ++setupFetchToken;
    try {
      const data = await api.get<TaskSetupOptions>("/projects/tasks/setup-options/");
      if (token !== setupFetchToken) return;
      setupOptions = data;
    } catch (err) {
      if (token !== setupFetchToken) return;
      setupOptions = {
        projects: [],
        phases: [],
        documents: [],
        contracts: [],
        risks: [],
        users: [],
      };
      toast.error("Load failed", apiErrorDetail(err, "Could not load task setup options"));
    } finally {
      if (token === setupFetchToken) setupLoading = false;
    }
  }

  function resetTaskForm(defaultProject = projectFilter) {
    taskForm = {
      project_id: defaultProject || "",
      phase_id: "",
      name: "",
      description: "",
      work_package: "",
      reference_code: "",
      status: "pending",
      priority: "medium",
      assigned_to: "",
      assigned_user: "",
      assigned_external_ref: "",
      reviewer_role: "",
      collaborators: [],
      estimated_effort_hours: "",
      predecessors: [],
      successors: [],
      definition_of_done: [],
      tools_required: [],
      reference_links: [],
      due_date: "",
      sla_target_at: "",
      sort_order: "0",
      linked_documents: [],
      linked_variation_orders: [],
      linked_risks: [],
    };
    taskSupportingFiles = [];
  }

  function openEditTask(task: ProjectTask) {
    editingTask = task;
    taskForm = {
      project_id: String(task.project),
      phase_id: String(task.phase),
      name: task.name,
      description: task.description || "",
      work_package: task.work_package || "",
      reference_code: task.reference_code || "",
      status: task.status,
      priority: task.priority,
      assigned_to: task.assigned_to || "",
      assigned_user: task.assigned_user ? String(task.assigned_user) : "",
      assigned_external_ref: task.assigned_external_ref || "",
      reviewer_role: task.reviewer_role || "",
      collaborators: (task.collaborators ?? []).map((entry) => ({
        role: entry.role ?? "",
        responsibility: entry.responsibility ?? "",
      })),
      estimated_effort_hours: task.estimated_effort_hours ?? "",
      predecessors: (task.predecessors ?? []).map((entry) => ({
        task: entry.task ?? "",
        dependency_type: entry.dependency_type ?? "finish_to_start",
        lag_days: Number(entry.lag_days ?? 0),
      })),
      successors: (task.successors ?? []).map((entry) => ({
        task: entry.task ?? "",
        dependency_type: entry.dependency_type ?? "finish_to_start",
        lag_days: Number(entry.lag_days ?? 0),
      })),
      definition_of_done: (task.definition_of_done ?? []).map((entry) => ({
        criterion: entry.criterion ?? "",
        is_required: entry.is_required ?? true,
      })),
      tools_required: (task.tools_required ?? []).map((entry) => ({
        name: entry.name ?? "",
        description: entry.description ?? "",
      })),
      reference_links: (task.reference_links ?? []).map((entry) => ({
        title: entry.title ?? "",
        url: entry.url ?? "",
      })),
      due_date: task.due_date || "",
      sla_target_at: toDatetimeLocalInput(task.sla_target_at),
      sort_order: String(task.sort_order ?? 0),
      linked_documents: [...(task.linked_documents ?? [])],
      linked_variation_orders: [...(task.linked_variation_orders ?? [])],
      linked_risks: [...(task.linked_risks ?? [])],
    };
    taskSupportingFiles = [];
    showTaskModal = true;
  }

  function toggleLinkedId(field: "linked_documents" | "linked_variation_orders" | "linked_risks", id: number) {
    const current = taskForm[field];
    const exists = current.includes(id);
    taskForm[field] = exists ? current.filter((entry) => entry !== id) : [...current, id];
  }

  function addTaskCollaborator() {
    taskForm.collaborators = [...taskForm.collaborators, { role: "", responsibility: "" }];
  }

  function removeTaskCollaborator(index: number) {
    taskForm.collaborators = taskForm.collaborators.filter((_, i) => i !== index);
  }

  function addTaskPredecessor() {
    taskForm.predecessors = [
      ...taskForm.predecessors,
      { task: "", dependency_type: "finish_to_start", lag_days: 0 },
    ];
  }

  function removeTaskPredecessor(index: number) {
    taskForm.predecessors = taskForm.predecessors.filter((_, i) => i !== index);
  }

  function addTaskSuccessor() {
    taskForm.successors = [
      ...taskForm.successors,
      { task: "", dependency_type: "finish_to_start", lag_days: 0 },
    ];
  }

  function removeTaskSuccessor(index: number) {
    taskForm.successors = taskForm.successors.filter((_, i) => i !== index);
  }

  function addTaskDoD() {
    taskForm.definition_of_done = [...taskForm.definition_of_done, { criterion: "", is_required: true }];
  }

  function removeTaskDoD(index: number) {
    taskForm.definition_of_done = taskForm.definition_of_done.filter((_, i) => i !== index);
  }

  function addTaskTool() {
    taskForm.tools_required = [...taskForm.tools_required, { name: "", description: "" }];
  }

  function removeTaskTool(index: number) {
    taskForm.tools_required = taskForm.tools_required.filter((_, i) => i !== index);
  }

  function addTaskRefLink() {
    taskForm.reference_links = [...taskForm.reference_links, { title: "", url: "" }];
  }

  function removeTaskRefLink(index: number) {
    taskForm.reference_links = taskForm.reference_links.filter((_, i) => i !== index);
  }

  function onSupportingFilesSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    taskSupportingFiles = Array.from(input.files ?? []);
  }

  async function uploadSupportingFiles(taskId: number): Promise<boolean> {
    if (!taskSupportingFiles.length) return true;
    try {
      for (const file of taskSupportingFiles) {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("caption", file.name);
        await api.upload(`/projects/tasks/${taskId}/upload-supporting-file/`, formData);
      }
      return true;
    } catch {
      return false;
    }
  }

  async function saveTask() {
    if (!taskForm.phase_id) {
      toast.error("Validation error", "Please select a phase");
      return;
    }
    saving = true;
    try {
      const payload = {
        phase: Number(taskForm.phase_id),
        name: taskForm.name.trim(),
        description: taskForm.description.trim(),
        work_package: taskForm.work_package.trim(),
        reference_code: taskForm.reference_code.trim(),
        status: taskForm.status,
        priority: taskForm.priority,
        assigned_to: taskForm.assigned_to.trim(),
        assigned_user: taskForm.assigned_user ? Number(taskForm.assigned_user) : null,
        assigned_external_ref: taskForm.assigned_external_ref.trim(),
        reviewer_role: taskForm.reviewer_role.trim(),
        collaborators: taskForm.collaborators
          .map((entry) => ({
            role: entry.role.trim(),
            responsibility: entry.responsibility.trim(),
          }))
          .filter((entry) => entry.role || entry.responsibility),
        estimated_effort_hours: taskForm.estimated_effort_hours !== ""
          ? Number(taskForm.estimated_effort_hours)
          : null,
        predecessors: taskForm.predecessors
          .map((entry) => ({
            task: entry.task.trim(),
            dependency_type: entry.dependency_type,
            lag_days: Number(entry.lag_days || 0),
          }))
          .filter((entry) => entry.task),
        successors: taskForm.successors
          .map((entry) => ({
            task: entry.task.trim(),
            dependency_type: entry.dependency_type,
            lag_days: Number(entry.lag_days || 0),
          }))
          .filter((entry) => entry.task),
        definition_of_done: taskForm.definition_of_done
          .map((entry) => ({
            criterion: entry.criterion.trim(),
            is_required: entry.is_required,
          }))
          .filter((entry) => entry.criterion),
        tools_required: taskForm.tools_required
          .map((entry) => ({
            name: entry.name.trim(),
            description: entry.description.trim(),
          }))
          .filter((entry) => entry.name || entry.description),
        reference_links: taskForm.reference_links
          .map((entry) => ({
            title: entry.title.trim(),
            url: entry.url.trim(),
          }))
          .filter((entry) => entry.title || entry.url),
        due_date: taskForm.due_date || null,
        sla_target_at: toIsoDatetime(taskForm.sla_target_at),
        sort_order: Number(taskForm.sort_order || "0"),
        linked_documents: taskForm.linked_documents,
        linked_variation_orders: taskForm.linked_variation_orders,
        linked_risks: taskForm.linked_risks,
      };

      let saved: ProjectTask;
      if (editingTask) {
        saved = await api.patch<ProjectTask>(`/projects/tasks/${editingTask.id}/`, payload);
        toast.success("Task updated", `${payload.name} has been saved`);
      } else {
        saved = await api.post<ProjectTask>("/projects/tasks/", payload);
        toast.success("Task created", `${payload.name} has been added`);
      }

      const uploadOk = await uploadSupportingFiles(saved.id);
      if (!uploadOk) {
        toast.error(
          "Evidence upload failed",
          "Task was saved, but completion evidence upload failed."
        );
      }

      showTaskModal = false;
      taskSupportingFiles = [];
      await fetchTasks();
    } catch (err) {
      toast.error("Save failed", apiErrorDetail(err, "Could not save task"));
    } finally {
      saving = false;
    }
  }

  async function updateTaskStatus(task: ProjectTask, status: TaskStatus) {
    try {
      await api.patch(`/projects/tasks/${task.id}/`, {
        status,
        completed_date: status === "completed" ? new Date().toISOString().slice(0, 10) : null,
      });
      await fetchTasks();
    } catch (err) {
      toast.error("Update failed", apiErrorDetail(err, "Could not update task status"));
    }
  }

  async function deleteTask(task: ProjectTask) {
    if (!confirm(`Delete "${task.name}"?`)) return;
    try {
      await api.delete(`/projects/tasks/${task.id}/`);
      toast.success("Task deleted", "Task has been removed");
      await fetchTasks();
    } catch (err) {
      toast.error("Delete failed", apiErrorDetail(err, "Could not delete task"));
    }
  }

  async function openComments(task: ProjectTask) {
    commentsTask = task;
    commentsLoading = true;
    newComment = "";
    try {
      const response = await api.get<PaginatedResponse<ProjectTaskComment> | ProjectTaskComment[]>(
        `/projects/tasks/${task.id}/comments/`
      );
      comments = listRows(response);
    } catch (err) {
      comments = [];
      toast.error("Load failed", apiErrorDetail(err, "Could not load task comments"));
    } finally {
      commentsLoading = false;
    }
  }

  async function postComment() {
    if (!commentsTask) return;
    const body = newComment.trim();
    if (!body) return;
    commentsPosting = true;
    try {
      const created = await api.post<ProjectTaskComment>(`/projects/tasks/${commentsTask.id}/comments/`, {
        comment: body,
      });
      comments = [...comments, created];
      newComment = "";
      await fetchTasks();
    } catch (err) {
      toast.error("Comment failed", apiErrorDetail(err, "Could not post comment"));
    } finally {
      commentsPosting = false;
    }
  }

  function onSearchInput(event: Event) {
    searchInput = (event.target as HTMLInputElement).value;
    if (searchTimeout) clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      searchQuery = searchInput.trim();
      currentPage = 1;
    }, 250);
  }

  function resetFilters() {
    searchInput = "";
    searchQuery = "";
    projectFilter = "";
    phaseFilter = "";
    statusFilter = "";
    priorityFilter = "";
    slaFilter = "";
    viewScope = "cross_project";
    ordering = "-updated_at";
    currentPage = 1;
  }

  function buildWorkPackageParams(page = workPackagePage): Record<string, string> {
    const params: Record<string, string> = {
      page: String(page),
      page_size: String(workPackagePageSize),
      ordering: workPackageOrdering,
    };
    if (workPackageSearchQuery) params.search = workPackageSearchQuery;
    if (workPackageProjectFilter) params.project = workPackageProjectFilter;
    if (workPackagePhaseFilter) params.phase = workPackagePhaseFilter;
    if (workPackageContractorFilter) params.contractor = workPackageContractorFilter;
    return params;
  }

  async function fetchWorkPackages() {
    workPackagesLoading = true;
    const token = ++workPackageFetchToken;
    try {
      const response = await api.get<PaginatedResponse<ProjectWorkPackage>>(
        "/projects/work-packages/",
        buildWorkPackageParams(),
      );
      if (token !== workPackageFetchToken) return;
      workPackages = response.results;
      workPackageTotalCount = response.count;
      const maxPage = Math.max(1, Math.ceil(response.count / workPackagePageSize));
      if (workPackagePage > maxPage) workPackagePage = maxPage;
    } catch (err) {
      if (token !== workPackageFetchToken) return;
      workPackages = [];
      workPackageTotalCount = 0;
      toast.error("Load failed", apiErrorDetail(err, "Could not load work packages"));
    } finally {
      if (token === workPackageFetchToken) workPackagesLoading = false;
    }
  }

  async function fetchWorkPackageSetupOptions() {
    workPackageSetupLoading = true;
    const token = ++workPackageSetupFetchToken;
    try {
      const params = workPackageProjectFilter ? { project: workPackageProjectFilter } : undefined;
      const data = await api.get<WorkPackageSetupOptions>("/projects/work-packages/setup-options/", params);
      if (token !== workPackageSetupFetchToken) return;
      workPackageSetupOptions = data;
    } catch (err) {
      if (token !== workPackageSetupFetchToken) return;
      workPackageSetupOptions = {
        projects: [],
        phases: [],
        contractors: [],
        drawings: [],
        purchase_orders: [],
        cost_entries: [],
        inspections: [],
        examples: [],
      };
      toast.error("Load failed", apiErrorDetail(err, "Could not load work package setup options"));
    } finally {
      if (token === workPackageSetupFetchToken) workPackageSetupLoading = false;
    }
  }

  function resetWorkPackageForm(defaultProject = workPackageProjectFilter) {
    workPackageForm = {
      project_id: defaultProject || "",
      phase_id: "",
      package_id: "",
      name: "",
      scope_description: "",
      contractor_id: "",
      budget: "",
      start_date: "",
      end_date: "",
      boq_items_text: "",
      quality_requirements: "",
      safety_requirements: "",
      inspection_plan: "",
      drawings: [],
      linked_purchase_orders: [],
      linked_cost_entries: [],
      linked_contractors: [],
      linked_inspections: [],
    };
  }

  function toggleWorkPackageLinkedId(
    field:
      | "drawings"
      | "linked_purchase_orders"
      | "linked_cost_entries"
      | "linked_contractors"
      | "linked_inspections",
    id: number,
  ) {
    const current = workPackageForm[field];
    const exists = current.includes(id);
    workPackageForm[field] = exists ? current.filter((entry) => entry !== id) : [...current, id];
  }

  const isDev = $derived(typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname));

  const WP_SAMPLES = [
    {
      name: "Structural Concrete Works",
      scope_description: "Supply, pour and cure all reinforced concrete elements including foundations, columns, beams, slabs, and retaining walls per structural drawings rev. C. Includes formwork, rebar fixing, and concrete testing (cube tests at 7/28 days).",
      budget: "185000000",
      start_date: "2026-04-01",
      end_date: "2026-09-30",
      boq_items_text: "Concrete Grade 40 — 2,400 m³\nReinforcement Steel Y16-Y32 — 380 tonnes\nFormwork (plywood + props) — 9,200 m²\nConcrete pump hire — 45 days\nCube testing (7 & 28 day) — 320 samples",
      quality_requirements: "Concrete slump 75-100mm. Cube strength ≥ 40 N/mm² at 28 days. Rebar cover per BS 8110. Third-party lab testing for every 50 m³ batch. NDT on 10% of columns.",
      safety_requirements: "Working-at-height permit for all slab pours above 3m. Exclusion zone during crane lifts. PPE: hard hat, steel-toe boots, high-vis vest mandatory. Toolbox talk before each pour. Spotter required for concrete pump boom.",
      inspection_plan: "Hold Point 1: Rebar inspection before each pour (structural engineer sign-off).\nHold Point 2: Pre-pour checklist (formwork alignment, cover blocks, inserts).\nWitness Point: Concrete slump test at point of discharge.\nMilestone: 28-day cube results logged before next phase proceeds.",
    },
    {
      name: "Mechanical & Electrical Rough-In",
      scope_description: "First-fix installation of all M&E services including conduit runs, cable trays, distribution boards, plumbing risers, drainage stacks, HVAC ductwork, and fire protection piping. Coordination with structural openings and sleeve requirements.",
      budget: "92000000",
      start_date: "2026-06-15",
      end_date: "2026-10-31",
      boq_items_text: "Electrical conduit (20-50mm) — 14,000 LM\nCable tray (300mm) — 2,800 LM\nPVC drainage pipe (110mm) — 1,600 LM\nCopper pipe (15-54mm) — 3,200 LM\nHVAC ductwork (GI sheet) — 4,500 m²\nFire sprinkler piping — 2,100 LM",
      quality_requirements: "Conduit bends max 270° cumulative between pull points. Pipe joints pressure-tested at 1.5x working pressure for 2 hours. Ductwork leak class B per DW/144. All penetrations fire-stopped to 2-hour rating.",
      safety_requirements: "Lock-out/tag-out for all live electrical work. Hot-work permit for soldering and welding. Confined space entry procedure for riser shafts. Scaffold inspection tag current before any elevated M&E work.",
      inspection_plan: "Hold Point: Pressure test sign-off before concealment.\nWitness Point: Fire-stop installation at every floor penetration.\nMilestone: Services coordination BIM clash report — zero critical clashes before rough-in starts.\nFinal: As-built mark-ups submitted within 5 days of completion.",
    },
    {
      name: "External Envelope & Façade",
      scope_description: "Supply and install curtain wall system, aluminium cladding panels, glazing units, weatherproofing sealants, and external render/paint finish. Includes scaffold access, hoist hire, and waste removal for façade zone.",
      budget: "145000000",
      start_date: "2026-07-01",
      end_date: "2026-12-15",
      boq_items_text: "Curtain wall system (unitised) — 3,200 m²\nAluminium composite panels — 1,800 m²\nDouble-glazed units (6/12/6) — 2,400 m²\nStructural silicone sealant — 6,800 LM\nExternal render (20mm) — 4,200 m²\nScaffold hire — 7 months",
      quality_requirements: "Curtain wall air infiltration ≤ 1.5 m³/hr/m² at 600 Pa. Water penetration nil at 600 Pa static. Thermal U-value ≤ 1.6 W/m²K. Mock-up panel approved before production run. Colour consistency ΔE ≤ 1.0.",
      safety_requirements: "Full perimeter edge protection before façade panels removed from scaffold. Tethered tools above 3m. Wind speed monitoring — cease crane-lifted panel installation above 35 km/h. Daily scaffold inspection by competent person.",
      inspection_plan: "Hold Point: Mock-up panel factory acceptance test.\nHold Point: First-panel installation sign-off (alignment, sealant bead, anchor torque).\nWitness Point: Water-spray test per AAMA 501.1 on 10% of installed bays.\nMilestone: Practical weather-tightness achieved before internal fit-out starts.",
    },
    {
      name: "Earthworks & Site Preparation",
      scope_description: "Bulk excavation to formation level, cut-and-fill earthworks, compaction to 95% MDD, dewatering, temporary shoring, and disposal of surplus spoil. Includes setting out, site clearance, and temporary access roads.",
      budget: "68000000",
      start_date: "2026-03-15",
      end_date: "2026-05-30",
      boq_items_text: "Bulk excavation — 18,000 m³\nFill and compact (laterite) — 6,500 m³\nDewatering (wellpoints) — 60 days\nSheet piling (temporary) — 320 LM\nSpoil disposal (off-site) — 11,500 m³\nTemporary access road (gravel) — 850 m²",
      quality_requirements: "Compaction ≥ 95% Modified Proctor (MDD). CBR ≥ 30% at formation level. Plate load test every 500 m². Excavation tolerances ± 50mm from design level. Geotechnical engineer approval at each bench level.",
      safety_requirements: "Excavation > 1.2m depth requires shoring or 1:1 batter. Banksman for all plant movements. Daily trench inspection before entry. Dewatering pump fuel stored in bunded area. Dust suppression in dry weather.",
      inspection_plan: "Hold Point: Formation level approval by geotechnical engineer.\nWitness Point: Compaction test at every 300mm lift.\nMilestone: Dewatering system operational before excavation below water table.\nFinal: As-built survey of formation levels submitted to structural engineer.",
    },
  ];

  let wpDevIdx = 0;
  function devFillWorkPackage() {
    const sample = WP_SAMPLES[wpDevIdx % WP_SAMPLES.length];
    wpDevIdx++;
    workPackageForm = {
      ...workPackageForm,
      name: sample.name,
      scope_description: sample.scope_description,
      budget: sample.budget,
      start_date: sample.start_date,
      end_date: sample.end_date,
      boq_items_text: sample.boq_items_text,
      quality_requirements: sample.quality_requirements,
      safety_requirements: sample.safety_requirements,
      inspection_plan: sample.inspection_plan,
    };
  }

  function openCreateWorkPackage() {
    editingWorkPackage = null;
    resetWorkPackageForm();
    showWorkPackageModal = true;
  }

  function openEditWorkPackage(workPackage: ProjectWorkPackage) {
    editingWorkPackage = workPackage;
    workPackageForm = {
      project_id: String(workPackage.project),
      phase_id: workPackage.phase ? String(workPackage.phase) : "",
      package_id: workPackage.package_id ?? "",
      name: workPackage.name,
      scope_description: workPackage.scope_description || "",
      contractor_id: workPackage.contractor ? String(workPackage.contractor) : "",
      budget: workPackage.budget || "",
      start_date: workPackage.start_date || "",
      end_date: workPackage.end_date || "",
      boq_items_text: (workPackage.boq_items ?? []).join("\n"),
      quality_requirements: workPackage.quality_requirements || "",
      safety_requirements: workPackage.safety_requirements || "",
      inspection_plan: workPackage.inspection_plan || "",
      drawings: [...(workPackage.drawings ?? [])],
      linked_purchase_orders: [...(workPackage.linked_purchase_orders ?? [])],
      linked_cost_entries: [...(workPackage.linked_cost_entries ?? [])],
      linked_contractors: [...(workPackage.linked_contractors ?? [])],
      linked_inspections: [...(workPackage.linked_inspections ?? [])],
    };
    showWorkPackageModal = true;
  }

  async function saveWorkPackage() {
    if (!workPackageForm.project_id) {
      toast.error("Validation error", "Please select a project");
      return;
    }
    if (!workPackageForm.name.trim()) {
      toast.error("Validation error", "Please provide a work package name");
      return;
    }

    workPackageSaving = true;
    try {
      const payload = {
        project: Number(workPackageForm.project_id),
        phase: workPackageForm.phase_id ? Number(workPackageForm.phase_id) : null,
        package_id: workPackageForm.package_id.trim() || null,
        name: workPackageForm.name.trim(),
        scope_description: workPackageForm.scope_description.trim(),
        contractor: workPackageForm.contractor_id ? Number(workPackageForm.contractor_id) : null,
        boq_items: workPackageForm.boq_items_text
          .split("\n")
          .map((line) => line.trim())
          .filter(Boolean),
        budget: workPackageForm.budget || "0",
        start_date: workPackageForm.start_date || null,
        end_date: workPackageForm.end_date || null,
        drawings: workPackageForm.drawings,
        quality_requirements: workPackageForm.quality_requirements.trim(),
        safety_requirements: workPackageForm.safety_requirements.trim(),
        inspection_plan: workPackageForm.inspection_plan.trim(),
        linked_purchase_orders: workPackageForm.linked_purchase_orders,
        linked_cost_entries: workPackageForm.linked_cost_entries,
        linked_contractors: workPackageForm.linked_contractors,
        linked_inspections: workPackageForm.linked_inspections,
      };

      if (editingWorkPackage) {
        await api.patch<ProjectWorkPackage>(
          `/projects/work-packages/${editingWorkPackage.id}/`,
          payload,
        );
        toast.success("Work package updated", `${payload.name} has been saved`);
      } else {
        await api.post<ProjectWorkPackage>("/projects/work-packages/", payload);
        toast.success("Work package created", `${payload.name} has been added`);
      }

      showWorkPackageModal = false;
      await fetchWorkPackages();
    } catch (err) {
      toast.error("Save failed", apiErrorDetail(err, "Could not save work package"));
    } finally {
      workPackageSaving = false;
    }
  }

  async function deleteWorkPackage(workPackage: ProjectWorkPackage) {
    if (!confirm(`Delete work package "${workPackage.name}"?`)) return;
    try {
      await api.delete(`/projects/work-packages/${workPackage.id}/`);
      toast.success("Work package deleted", "Work package has been removed");
      await fetchWorkPackages();
    } catch (err) {
      toast.error("Delete failed", apiErrorDetail(err, "Could not delete work package"));
    }
  }

  function onWorkPackageSearchInput(event: Event) {
    workPackageSearchInput = (event.target as HTMLInputElement).value;
    if (workPackageSearchTimeout) clearTimeout(workPackageSearchTimeout);
    workPackageSearchTimeout = setTimeout(() => {
      workPackageSearchQuery = workPackageSearchInput.trim();
      workPackagePage = 1;
    }, 250);
  }

  function resetWorkPackageFilters() {
    workPackageSearchInput = "";
    workPackageSearchQuery = "";
    workPackageProjectFilter = "";
    workPackagePhaseFilter = "";
    workPackageContractorFilter = "";
    workPackageOrdering = "-updated_at";
    workPackagePage = 1;
  }

  $effect(() => {
    void currentPage;
    void pageSize;
    void viewScope;
    void searchQuery;
    void projectFilter;
    void phaseFilter;
    void statusFilter;
    void priorityFilter;
    void slaFilter;
    void ordering;
    fetchTasks();
  });

  $effect(() => {
    fetchSetupOptions();
  });

  $effect(() => {
    if (!phaseFilter) return;
    if (filteredPhaseOptions.some((phase) => String(phase.id) === phaseFilter)) return;
    phaseFilter = "";
  });

  $effect(() => {
    if (!taskForm.project_id || !taskForm.phase_id) return;
    const valid = formPhaseOptions.some((phase) => String(phase.id) === taskForm.phase_id);
    if (!valid) taskForm.phase_id = "";
  });

  $effect(() => {
    void workPackagePage;
    void workPackagePageSize;
    void workPackageSearchQuery;
    void workPackageProjectFilter;
    void workPackagePhaseFilter;
    void workPackageContractorFilter;
    void workPackageOrdering;
    fetchWorkPackages();
  });

  $effect(() => {
    fetchWorkPackageSetupOptions();
  });

  $effect(() => {
    if (!workPackagePhaseFilter) return;
    if (workPackageFilteredPhaseOptions.some((phase) => String(phase.id) === workPackagePhaseFilter)) return;
    workPackagePhaseFilter = "";
  });

  $effect(() => {
    if (!workPackageForm.project_id || !workPackageForm.phase_id) return;
    const valid = workPackageFormPhaseOptions.some((phase) => String(phase.id) === workPackageForm.phase_id);
    if (!valid) workPackageForm.phase_id = "";
  });
</script>

<svelte:head>
  <title>Construction | Tasks &amp; Work Packages</title>
</svelte:head>

<div class="space-y-6">
  <section>
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-violet-500">Construction</p>
        <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Tasks &amp; Work Packages</h1>
        <p class="mt-1 text-sm text-neutral-500">
          {#if activeTab === "tasks"}
            Cross-project execution tracking with SLA timers, linked documents/contracts/risks, and collaboration comments.
          {:else}
            Construction work packages with scope, BOQ, quality/safety controls, and cross-module links.
          {/if}
        </p>
      </div>
      {#if activeTab === "work_packages"}
        <button
          onclick={openCreateWorkPackage}
          class="inline-flex items-center rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-neutral-800"
        >
          + New Work Package
        </button>
      {/if}
    </div>

    <div class="mt-5 inline-flex rounded-xl border border-neutral-200 bg-neutral-50 p-1">
      <button
        onclick={() => (activeTab = "tasks")}
        class="rounded-lg px-4 py-2 text-sm font-semibold transition {activeTab === 'tasks' ? 'bg-white text-neutral-900 shadow-sm' : 'text-neutral-600 hover:text-neutral-900'}"
      >
        Tasks
      </button>
      <button
        onclick={() => (activeTab = "work_packages")}
        class="rounded-lg px-4 py-2 text-sm font-semibold transition {activeTab === 'work_packages' ? 'bg-white text-neutral-900 shadow-sm' : 'text-neutral-600 hover:text-neutral-900'}"
      >
        Work Packages
      </button>
    </div>

    <div class="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {#if activeTab === "tasks"}
        <article class="rounded-xl border border-blue-100 bg-blue-50/70 p-4">
          <p class="text-[11px] font-semibold uppercase tracking-wider text-blue-700">Total Tasks</p>
          <p class="mt-1 text-xl font-bold text-blue-900 tabular-nums">{totalCount}</p>
        </article>
        <article class="rounded-xl border border-emerald-100 bg-emerald-50/70 p-4">
          <p class="text-[11px] font-semibold uppercase tracking-wider text-emerald-700">My Tasks</p>
          <p class="mt-1 text-xl font-bold text-emerald-900 tabular-nums">{personalTaskCount}</p>
        </article>
        <article class="rounded-xl border border-rose-100 bg-rose-50/70 p-4">
          <p class="text-[11px] font-semibold uppercase tracking-wider text-rose-700">SLA Breached</p>
          <p class="mt-1 text-xl font-bold text-rose-900 tabular-nums">{breachedTaskCount}</p>
        </article>
        <article class="rounded-xl border border-amber-100 bg-amber-50/70 p-4">
          <p class="text-[11px] font-semibold uppercase tracking-wider text-amber-700">Due in 7 Days</p>
          <p class="mt-1 text-xl font-bold text-amber-900 tabular-nums">{dueSoonCount}</p>
        </article>
      {:else}
        <article class="rounded-xl border border-blue-100 bg-blue-50/70 p-4">
          <p class="text-[11px] font-semibold uppercase tracking-wider text-blue-700">Work Packages</p>
          <p class="mt-1 text-xl font-bold text-blue-900 tabular-nums">{workPackageTotalCount}</p>
        </article>
        <article class="rounded-xl border border-emerald-100 bg-emerald-50/70 p-4">
          <p class="text-[11px] font-semibold uppercase tracking-wider text-emerald-700">Total Budget</p>
          <p class="mt-1 text-xl font-bold text-emerald-900 tabular-nums">{currency.formatCompact(workPackageTotalBudget)}</p>
        </article>
        <article class="rounded-xl border border-amber-100 bg-amber-50/70 p-4">
          <p class="text-[11px] font-semibold uppercase tracking-wider text-amber-700">Ending in 14 Days</p>
          <p class="mt-1 text-xl font-bold text-amber-900 tabular-nums">{workPackageEndingSoon}</p>
        </article>
        <article class="rounded-xl border border-rose-100 bg-rose-50/70 p-4">
          <p class="text-[11px] font-semibold uppercase tracking-wider text-rose-700">Inspection Linked</p>
          <p class="mt-1 text-xl font-bold text-rose-900 tabular-nums">{workPackageInspectionLinkedCount}</p>
        </article>
      {/if}
    </div>
  </section>

  {#if activeTab === "tasks"}
  <section class="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
    <div class="flex flex-wrap items-center gap-2">
      <button
        onclick={() => {
          viewScope = "cross_project";
          currentPage = 1;
        }}
        class="rounded-full border px-3 py-1.5 text-xs font-semibold transition {viewScope === 'cross_project' ? 'border-neutral-900 bg-neutral-900 text-white' : 'border-neutral-200 bg-white text-neutral-600 hover:border-neutral-300'}"
      >
        Cross-Project
      </button>
      <button
        onclick={() => {
          viewScope = "team";
          currentPage = 1;
        }}
        class="rounded-full border px-3 py-1.5 text-xs font-semibold transition {viewScope === 'team' ? 'border-neutral-900 bg-neutral-900 text-white' : 'border-neutral-200 bg-white text-neutral-600 hover:border-neutral-300'}"
      >
        Team View
      </button>
      <button
        onclick={() => {
          viewScope = "personal";
          currentPage = 1;
        }}
        class="rounded-full border px-3 py-1.5 text-xs font-semibold transition {viewScope === 'personal' ? 'border-neutral-900 bg-neutral-900 text-white' : 'border-neutral-200 bg-white text-neutral-600 hover:border-neutral-300'}"
      >
        Personal View
      </button>
    </div>

    <div class="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-6">
      <label class="block">
        <span class="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-neutral-500">Search</span>
        <input
          value={searchInput}
          oninput={onSearchInput}
          placeholder="Task, project, assignee..."
          class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none"
        />
      </label>
      <label class="block">
        <span class="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-neutral-500">Project</span>
        <select
          bind:value={projectFilter}
          class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none"
          onchange={() => {
            phaseFilter = "";
            currentPage = 1;
          }}
          disabled={setupLoading}
        >
          <option value="">All Projects</option>
          {#each setupOptions.projects as project}
            <option value={String(project.id)}>{project.name}</option>
          {/each}
        </select>
      </label>
      <label class="block">
        <span class="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-neutral-500">Phase</span>
        <select
          bind:value={phaseFilter}
          class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none"
          onchange={() => (currentPage = 1)}
          disabled={setupLoading}
        >
          <option value="">All Phases</option>
          {#each filteredPhaseOptions as phase}
            <option value={String(phase.id)}>{phase.project_name} • {phase.name}</option>
          {/each}
        </select>
      </label>
      <label class="block">
        <span class="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-neutral-500">Status</span>
        <select
          bind:value={statusFilter}
          class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none"
          onchange={() => (currentPage = 1)}
        >
          <option value="">All Statuses</option>
          <option value="pending">Pending</option>
          <option value="in_progress">In Progress</option>
          <option value="completed">Completed</option>
        </select>
      </label>
      <label class="block">
        <span class="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-neutral-500">Priority</span>
        <select
          bind:value={priorityFilter}
          class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none"
          onchange={() => (currentPage = 1)}
        >
          <option value="">All Priorities</option>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="critical">Critical</option>
        </select>
      </label>
      <label class="block">
        <span class="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-neutral-500">SLA</span>
        <select
          bind:value={slaFilter}
          class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none"
          onchange={() => (currentPage = 1)}
        >
          <option value="">All SLA States</option>
          <option value="breached">Breached</option>
          <option value="at_risk">At Risk</option>
          <option value="on_track">On Track</option>
          <option value="completed">Completed</option>
          <option value="not_configured">Not Configured</option>
        </select>
      </label>
    </div>

    <div class="mt-3 flex flex-wrap items-center justify-between gap-3">
      <div class="flex items-center gap-2">
        <label for="tasks-sort" class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Sort</label>
        <select
          id="tasks-sort"
          bind:value={ordering}
          class="rounded-lg border border-neutral-200 px-3 py-1.5 text-sm focus:border-neutral-400 focus:outline-none"
        >
          <option value="-updated_at">Recently Updated</option>
          <option value="-created_at">Newest</option>
          <option value="due_date">Due Date (Asc)</option>
          <option value="-due_date">Due Date (Desc)</option>
          <option value="priority">Priority (Asc)</option>
          <option value="-priority">Priority (Desc)</option>
          <option value="sla_target_at">SLA Target (Asc)</option>
          <option value="-sla_target_at">SLA Target (Desc)</option>
        </select>
      </div>
      <button
        onclick={resetFilters}
        class="rounded-lg border border-neutral-200 px-3 py-1.5 text-sm font-medium text-neutral-600 transition hover:bg-neutral-50"
      >
        Reset Filters
      </button>
    </div>
  </section>

  <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-sm">
    <div class="flex items-center justify-between border-b border-neutral-200 px-5 py-4">
      <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Task Register</h2>
      <p class="text-xs text-neutral-500">Showing {startItem}-{endItem} of {totalCount}</p>
    </div>

    {#if loading}
      <div class="p-10 text-center text-sm text-neutral-500">Loading tasks...</div>
    {:else if tasks.length === 0}
      <div class="p-10 text-center text-sm text-neutral-500">No tasks found for the selected filters.</div>
    {:else}
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-neutral-200 text-sm">
          <thead class="bg-neutral-50">
            <tr>
              <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Task</th>
              <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Project / Phase</th>
              <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Priority</th>
              <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Assignee</th>
              <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Due / SLA</th>
              <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Links</th>
              <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Status</th>
              <th class="px-5 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each tasks as task (task.id)}
              <tr class="align-top">
                <td class="px-5 py-4">
                  <p class="font-semibold text-neutral-900">{task.name}</p>
                  {#if task.reference_code}
                    <p class="mt-1 text-[11px] font-mono text-neutral-500">{task.reference_code}</p>
                  {/if}
                  {#if task.work_package}
                    <p class="mt-1 inline-flex rounded border border-neutral-200 bg-neutral-50 px-2 py-0.5 text-[11px] font-medium text-neutral-600">
                      {task.work_package}
                    </p>
                  {/if}
                  {#if task.description}
                    <p class="mt-2 line-clamp-2 max-w-[24rem] text-xs text-neutral-500">{task.description}</p>
                  {/if}
                </td>
                <td class="px-5 py-4">
                  <p class="font-medium text-neutral-800">{task.project_name}</p>
                  <p class="mt-1 text-xs text-neutral-500">{task.phase_name}</p>
                </td>
                <td class="px-5 py-4">
                  <span class="inline-flex rounded border px-2 py-1 text-xs font-semibold {priorityBadge[task.priority]}">
                    {priorityLabel[task.priority]}
                  </span>
                </td>
                <td class="px-5 py-4">
                  <p class="font-medium text-neutral-800">{task.assigned_user_name ?? task.assigned_to ?? "--"}</p>
                  {#if task.assigned_external_ref}
                    <p class="mt-1 text-xs text-neutral-500">External: {task.assigned_external_ref}</p>
                  {/if}
                </td>
                <td class="px-5 py-4">
                  <p class="text-xs font-medium text-neutral-700">Due: {formatDate(task.due_date)}</p>
                  <div class="mt-1">
                    <span class="inline-flex rounded border px-2 py-1 text-xs font-semibold {slaBadge[task.sla_status] ?? slaBadge.not_configured}">
                      {task.sla_status.replace("_", " ")}
                    </span>
                  </div>
                  <p class="mt-1 text-xs text-neutral-500">
                    Target: {formatDateTime(task.sla_target_at)} • {formatSeconds(task.sla_time_remaining_seconds)}
                  </p>
                </td>
                <td class="px-5 py-4 text-xs text-neutral-600">
                  <p>Docs: {task.linked_documents.length}</p>
                  <p class="mt-1">Contracts: {task.linked_variation_orders.length}</p>
                  <p class="mt-1">Risks: {task.linked_risks.length}</p>
                </td>
                <td class="px-5 py-4">
                  <select
                    value={task.status}
                    onchange={(event) => updateTaskStatus(task, (event.target as HTMLSelectElement).value as TaskStatus)}
                    class="rounded-lg border border-neutral-200 px-2 py-1.5 text-xs font-medium focus:border-neutral-400 focus:outline-none"
                  >
                    <option value="pending">Pending</option>
                    <option value="in_progress">In Progress</option>
                    <option value="completed">Completed</option>
                  </select>
                  <div class="mt-2">
                    <StatusBadge status={task.status} />
                  </div>
                </td>
                <td class="px-5 py-4">
                  <div class="flex justify-end gap-2">
                    <button
                      onclick={() => openComments(task)}
                      class="rounded-md border border-neutral-200 px-2.5 py-1.5 text-xs font-medium text-neutral-600 transition hover:bg-neutral-50"
                    >
                      Comments ({task.comments_count})
                    </button>
                    <button
                      onclick={() => openEditTask(task)}
                      class="rounded-md border border-neutral-200 px-2.5 py-1.5 text-xs font-medium text-neutral-600 transition hover:bg-neutral-50"
                    >
                      Edit
                    </button>
                    <button
                      onclick={() => deleteTask(task)}
                      class="rounded-md border border-rose-200 px-2.5 py-1.5 text-xs font-medium text-rose-700 transition hover:bg-rose-50"
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}

    <div class="flex flex-wrap items-center justify-between border-t border-neutral-200 px-5 py-3">
      <p class="text-xs text-neutral-500">Page {currentPage} of {totalPages}</p>
      <div class="flex items-center gap-2">
        <button
          onclick={() => (currentPage = Math.max(1, currentPage - 1))}
          class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 transition hover:bg-neutral-50 disabled:opacity-40"
          disabled={currentPage <= 1}
        >
          Prev
        </button>
        <button
          onclick={() => (currentPage = Math.min(totalPages, currentPage + 1))}
          class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 transition hover:bg-neutral-50 disabled:opacity-40"
          disabled={currentPage >= totalPages}
        >
          Next
        </button>
        <select
          bind:value={pageSize}
          class="rounded-md border border-neutral-200 px-2 py-1.5 text-xs font-medium text-neutral-600 focus:border-neutral-400 focus:outline-none"
          onchange={() => {
            currentPage = 1;
          }}
        >
          <option value={10}>10</option>
          <option value={20}>20</option>
          <option value={50}>50</option>
          <option value={100}>100</option>
        </select>
      </div>
    </div>
  </section>
  {:else}
  <section class="rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm">
    <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
      <label class="block">
        <span class="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-neutral-500">Search</span>
        <input
          value={workPackageSearchInput}
          oninput={onWorkPackageSearchInput}
          placeholder="Package ID, scope, contractor..."
          class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none"
        />
      </label>
      <label class="block">
        <span class="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-neutral-500">Project</span>
        <select
          bind:value={workPackageProjectFilter}
          class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none"
          onchange={() => {
            workPackagePhaseFilter = "";
            workPackagePage = 1;
          }}
          disabled={workPackageSetupLoading}
        >
          <option value="">All Projects</option>
          {#each workPackageSetupOptions.projects as project}
            <option value={String(project.id)}>{project.name}</option>
          {/each}
        </select>
      </label>
      <label class="block">
        <span class="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-neutral-500">Phase</span>
        <select
          bind:value={workPackagePhaseFilter}
          class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none"
          onchange={() => (workPackagePage = 1)}
          disabled={workPackageSetupLoading}
        >
          <option value="">All Phases</option>
          {#each workPackageFilteredPhaseOptions as phase}
            <option value={String(phase.id)}>{phase.project_name} • {phase.name}</option>
          {/each}
        </select>
      </label>
      <label class="block">
        <span class="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-neutral-500">Contractor</span>
        <select
          bind:value={workPackageContractorFilter}
          class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none"
          onchange={() => (workPackagePage = 1)}
          disabled={workPackageSetupLoading}
        >
          <option value="">All Contractors</option>
          {#each workPackageSetupOptions.contractors as contractor}
            <option value={String(contractor.id)}>{contractor.name}</option>
          {/each}
        </select>
      </label>
      <label class="block">
        <span class="mb-1 block text-[11px] font-semibold uppercase tracking-wide text-neutral-500">Sort</span>
        <select
          bind:value={workPackageOrdering}
          class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none"
          onchange={() => (workPackagePage = 1)}
        >
          <option value="-updated_at">Recently Updated</option>
          <option value="-created_at">Newest</option>
          <option value="start_date">Start Date (Asc)</option>
          <option value="-start_date">Start Date (Desc)</option>
          <option value="end_date">End Date (Asc)</option>
          <option value="-end_date">End Date (Desc)</option>
          <option value="-budget">Budget (Desc)</option>
        </select>
      </label>
    </div>
    <div class="mt-3 flex justify-end">
      <button
        onclick={resetWorkPackageFilters}
        class="rounded-lg border border-neutral-200 px-3 py-1.5 text-sm font-medium text-neutral-600 transition hover:bg-neutral-50"
      >
        Reset Filters
      </button>
    </div>
  </section>

  <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-sm">
    <div class="flex items-center justify-between border-b border-neutral-200 px-5 py-4">
      <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Work Package Register</h2>
      <p class="text-xs text-neutral-500">
        Showing {workPackageStartItem}-{workPackageEndItem} of {workPackageTotalCount}
      </p>
    </div>

    {#if workPackagesLoading}
      <div class="p-10 text-center text-sm text-neutral-500">Loading work packages...</div>
    {:else if workPackages.length === 0}
      <div class="p-10 text-center text-sm text-neutral-500">No work packages found for the selected filters.</div>
    {:else}
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-neutral-200 text-sm">
          <thead class="bg-neutral-50">
            <tr>
              <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">ID / Scope</th>
              <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Project / Phase</th>
              <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Contractor</th>
              <th class="px-5 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Budget</th>
              <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Schedule</th>
              <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Requirements</th>
              <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Links</th>
              <th class="px-5 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each workPackages as workPackage (workPackage.id)}
              <tr class="align-top">
                <td class="px-5 py-4">
                  <p class="font-semibold text-neutral-900">{workPackage.package_id ?? "--"}</p>
                  <p class="mt-1 text-sm font-medium text-neutral-800">{workPackage.name}</p>
                  {#if workPackage.scope_description}
                    <p class="mt-2 line-clamp-2 max-w-[24rem] text-xs text-neutral-500">{workPackage.scope_description}</p>
                  {/if}
                </td>
                <td class="px-5 py-4">
                  <p class="font-medium text-neutral-800">{workPackage.project_name}</p>
                  <p class="mt-1 text-xs text-neutral-500">{workPackage.phase_name ?? "--"}</p>
                </td>
                <td class="px-5 py-4">
                  <p class="font-medium text-neutral-800">{workPackage.contractor_name ?? "--"}</p>
                  <p class="mt-1 text-xs text-neutral-500">Drawings: {workPackage.drawings.length}</p>
                </td>
                <td class="px-5 py-4 text-right">
                  <p class="font-semibold tabular-nums text-neutral-900">{currency.formatCompact(Number(workPackage.budget || 0))}</p>
                </td>
                <td class="px-5 py-4 text-xs text-neutral-600">
                  <p>Start: {formatDate(workPackage.start_date)}</p>
                  <p class="mt-1">End: {formatDate(workPackage.end_date)}</p>
                </td>
                <td class="px-5 py-4 text-xs text-neutral-600">
                  <p>Quality: {workPackage.quality_requirements ? "Set" : "Not set"}</p>
                  <p class="mt-1">Safety: {workPackage.safety_requirements ? "Set" : "Not set"}</p>
                  <p class="mt-1">Inspection Plan: {workPackage.inspection_plan ? "Set" : "Not set"}</p>
                </td>
                <td class="px-5 py-4 text-xs text-neutral-600">
                  <p>Procurement: {workPackage.linked_modules.procurement.purchase_orders}</p>
                  <p class="mt-1">Finance: {workPackage.linked_modules.finance.cost_entries}</p>
                  <p class="mt-1">Contractors: {workPackage.linked_modules.contractors.count}</p>
                  <p class="mt-1">Inspections: {workPackage.linked_modules.inspections.count}</p>
                </td>
                <td class="px-5 py-4">
                  <div class="flex justify-end gap-2">
                    <button
                      onclick={() => openEditWorkPackage(workPackage)}
                      class="rounded-md border border-neutral-200 px-2.5 py-1.5 text-xs font-medium text-neutral-600 transition hover:bg-neutral-50"
                    >
                      Edit
                    </button>
                    <button
                      onclick={() => deleteWorkPackage(workPackage)}
                      class="rounded-md border border-rose-200 px-2.5 py-1.5 text-xs font-medium text-rose-700 transition hover:bg-rose-50"
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}

    <div class="flex flex-wrap items-center justify-between border-t border-neutral-200 px-5 py-3">
      <p class="text-xs text-neutral-500">Page {workPackagePage} of {workPackageTotalPages}</p>
      <div class="flex items-center gap-2">
        <button
          onclick={() => (workPackagePage = Math.max(1, workPackagePage - 1))}
          class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 transition hover:bg-neutral-50 disabled:opacity-40"
          disabled={workPackagePage <= 1}
        >
          Prev
        </button>
        <button
          onclick={() => (workPackagePage = Math.min(workPackageTotalPages, workPackagePage + 1))}
          class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 transition hover:bg-neutral-50 disabled:opacity-40"
          disabled={workPackagePage >= workPackageTotalPages}
        >
          Next
        </button>
        <select
          bind:value={workPackagePageSize}
          class="rounded-md border border-neutral-200 px-2 py-1.5 text-xs font-medium text-neutral-600 focus:border-neutral-400 focus:outline-none"
          onchange={() => {
            workPackagePage = 1;
          }}
        >
          <option value={10}>10</option>
          <option value={20}>20</option>
          <option value={50}>50</option>
          <option value={100}>100</option>
        </select>
      </div>
    </div>
  </section>
  {/if}
</div>

{#if showTaskModal}
  <div class="fixed inset-0 z-40 flex items-center justify-center bg-neutral-900/40 p-4">
    <div class="max-h-[90vh] w-full max-w-5xl overflow-y-auto rounded-2xl border border-neutral-200 bg-white p-6 shadow-2xl">
      <div class="flex items-start justify-between">
        <div>
          <h3 class="text-lg font-semibold text-neutral-900">
            {editingTask ? "Edit Task" : "Create Task"}
          </h3>
          <p class="mt-1 text-sm text-neutral-500">
            Configure work package, assignee, SLA target, supporting links, and completion evidence.
          </p>
        </div>
        <button
          onclick={() => {
            showTaskModal = false;
            taskSupportingFiles = [];
          }}
          class="rounded-lg border border-neutral-200 px-3 py-1.5 text-sm text-neutral-600 transition hover:bg-neutral-50"
        >
          Close
        </button>
      </div>

      <div class="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <label class="block">
          <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Project</span>
          <select
            bind:value={taskForm.project_id}
            class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none"
            disabled={setupLoading}
            onchange={() => {
              taskForm.phase_id = "";
              taskForm.linked_documents = [];
              taskForm.linked_variation_orders = [];
              taskForm.linked_risks = [];
            }}
          >
            <option value="">Select project</option>
            {#each setupOptions.projects as project}
              <option value={String(project.id)}>{project.name}</option>
            {/each}
          </select>
        </label>
        <label class="block">
          <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Phase</span>
          <select
            bind:value={taskForm.phase_id}
            class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none"
          >
            <option value="">Select phase</option>
            {#each formPhaseOptions as phase}
              <option value={String(phase.id)}>{phase.name}</option>
            {/each}
          </select>
        </label>
        <label class="block">
          <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Priority</span>
          <select bind:value={taskForm.priority} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none">
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        </label>
        <label class="block">
          <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Status</span>
          <select bind:value={taskForm.status} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none">
            <option value="pending">Pending</option>
            <option value="in_progress">In Progress</option>
            <option value="completed">Completed</option>
          </select>
        </label>

        <label class="block md:col-span-2">
          <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Task Name</span>
          <input bind:value={taskForm.name} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none" placeholder="e.g. Foundation reinforcement" />
        </label>
        <label class="block md:col-span-2">
          <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Work Package</span>
          <input bind:value={taskForm.work_package} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none" placeholder="e.g. Structural Works" />
        </label>
        <label class="block">
          <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Reference Code</span>
          <input bind:value={taskForm.reference_code} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none" placeholder="e.g. TASK-101" />
        </label>
        <label class="block">
          <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Reviewer / Approver</span>
          <input bind:value={taskForm.reviewer_role} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none" placeholder="e.g. Project Manager" />
        </label>

        <label class="block">
          <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Assigned User</span>
          <select bind:value={taskForm.assigned_user} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none">
            <option value="">Unassigned</option>
            {#each setupOptions.users as user}
              <option value={String(user.id)}>{user.full_name}{user.role_name ? ` • ${user.role_name}` : ""}</option>
            {/each}
          </select>
        </label>
        <label class="block">
          <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Assigned Label</span>
          <input bind:value={taskForm.assigned_to} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none" placeholder="Optional display name" />
        </label>
        <label class="block">
          <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">External Ref</span>
          <input bind:value={taskForm.assigned_external_ref} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none" placeholder="AD/ERP/ITSM reference" />
        </label>
        <label class="block">
          <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Sort Order</span>
          <input type="number" min="0" bind:value={taskForm.sort_order} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none" />
        </label>

        <label class="block">
          <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Due Date</span>
          <DateInput bind:value={taskForm.due_date} />
        </label>
        <label class="block">
          <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">SLA Target</span>
          <input type="datetime-local" bind:value={taskForm.sla_target_at} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none" />
        </label>
        <label class="block">
          <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Estimated Effort (Hours)</span>
          <input type="number" min="0" step="0.1" bind:value={taskForm.estimated_effort_hours} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none" />
        </label>
      </div>

      <label class="mt-4 block">
        <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Description</span>
        <textarea
          bind:value={taskForm.description}
          rows="3"
          class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none"
          placeholder="Execution notes, acceptance criteria, blockers..."
        ></textarea>
      </label>

      <div class="mt-5 grid gap-4 lg:grid-cols-2">
        <article class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
          <div class="flex items-center justify-between">
            <p class="text-xs font-semibold uppercase tracking-wide text-neutral-600">Collaborators</p>
            <button onclick={addTaskCollaborator} class="text-xs font-medium text-neutral-600 hover:text-neutral-900">+ Add</button>
          </div>
          <div class="mt-2 space-y-2">
            {#if taskForm.collaborators.length === 0}
              <p class="text-xs text-neutral-400">No collaborators set.</p>
            {:else}
              {#each taskForm.collaborators as collaborator, i}
                <div class="flex gap-2">
                  <input bind:value={collaborator.role} placeholder="Role" class="w-2/5 rounded-lg border border-neutral-200 bg-white px-2 py-1.5 text-xs focus:border-neutral-400 focus:outline-none" />
                  <input bind:value={collaborator.responsibility} placeholder="Responsibility" class="flex-1 rounded-lg border border-neutral-200 bg-white px-2 py-1.5 text-xs focus:border-neutral-400 focus:outline-none" />
                  <button onclick={() => removeTaskCollaborator(i)} class="rounded border border-neutral-200 px-2 py-1 text-xs text-neutral-500 hover:bg-neutral-100">Remove</button>
                </div>
              {/each}
            {/if}
          </div>
        </article>

        <article class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
          <div class="flex items-center justify-between">
            <p class="text-xs font-semibold uppercase tracking-wide text-neutral-600">Definition of Done</p>
            <button onclick={addTaskDoD} class="text-xs font-medium text-neutral-600 hover:text-neutral-900">+ Add</button>
          </div>
          <div class="mt-2 space-y-2">
            {#if taskForm.definition_of_done.length === 0}
              <p class="text-xs text-neutral-400">No criteria set.</p>
            {:else}
              {#each taskForm.definition_of_done as item, i}
                <div class="flex gap-2">
                  <input bind:value={item.criterion} placeholder="Criterion" class="flex-1 rounded-lg border border-neutral-200 bg-white px-2 py-1.5 text-xs focus:border-neutral-400 focus:outline-none" />
                  <label class="flex items-center gap-1 rounded-lg border border-neutral-200 bg-white px-2 py-1 text-xs text-neutral-600">
                    <input type="checkbox" bind:checked={item.is_required} class="h-3.5 w-3.5 rounded border-neutral-300 text-neutral-900" />
                    Required
                  </label>
                  <button onclick={() => removeTaskDoD(i)} class="rounded border border-neutral-200 px-2 py-1 text-xs text-neutral-500 hover:bg-neutral-100">Remove</button>
                </div>
              {/each}
            {/if}
          </div>
        </article>

        <article class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
          <div class="flex items-center justify-between">
            <p class="text-xs font-semibold uppercase tracking-wide text-neutral-600">Predecessors</p>
            <button onclick={addTaskPredecessor} class="text-xs font-medium text-neutral-600 hover:text-neutral-900">+ Add</button>
          </div>
          <div class="mt-2 space-y-2">
            {#if taskForm.predecessors.length === 0}
              <p class="text-xs text-neutral-400">No predecessor tasks.</p>
            {:else}
              {#each taskForm.predecessors as item, i}
                <div class="grid grid-cols-6 gap-2">
                  <input bind:value={item.task} placeholder="Task" class="col-span-3 rounded-lg border border-neutral-200 bg-white px-2 py-1.5 text-xs focus:border-neutral-400 focus:outline-none" />
                  <select bind:value={item.dependency_type} class="col-span-2 rounded-lg border border-neutral-200 bg-white px-2 py-1.5 text-xs focus:border-neutral-400 focus:outline-none">
                    <option value="finish_to_start">Finish to Start</option>
                    <option value="start_to_start">Start to Start</option>
                    <option value="finish_to_finish">Finish to Finish</option>
                    <option value="start_to_finish">Start to Finish</option>
                  </select>
                  <input type="number" bind:value={item.lag_days} class="rounded-lg border border-neutral-200 bg-white px-2 py-1.5 text-xs focus:border-neutral-400 focus:outline-none" placeholder="Lag" />
                  <button onclick={() => removeTaskPredecessor(i)} class="col-span-6 justify-self-end rounded border border-neutral-200 px-2 py-1 text-xs text-neutral-500 hover:bg-neutral-100">Remove</button>
                </div>
              {/each}
            {/if}
          </div>
        </article>

        <article class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
          <div class="flex items-center justify-between">
            <p class="text-xs font-semibold uppercase tracking-wide text-neutral-600">Successors</p>
            <button onclick={addTaskSuccessor} class="text-xs font-medium text-neutral-600 hover:text-neutral-900">+ Add</button>
          </div>
          <div class="mt-2 space-y-2">
            {#if taskForm.successors.length === 0}
              <p class="text-xs text-neutral-400">No successor tasks.</p>
            {:else}
              {#each taskForm.successors as item, i}
                <div class="grid grid-cols-6 gap-2">
                  <input bind:value={item.task} placeholder="Task" class="col-span-3 rounded-lg border border-neutral-200 bg-white px-2 py-1.5 text-xs focus:border-neutral-400 focus:outline-none" />
                  <select bind:value={item.dependency_type} class="col-span-2 rounded-lg border border-neutral-200 bg-white px-2 py-1.5 text-xs focus:border-neutral-400 focus:outline-none">
                    <option value="finish_to_start">Finish to Start</option>
                    <option value="start_to_start">Start to Start</option>
                    <option value="finish_to_finish">Finish to Finish</option>
                    <option value="start_to_finish">Start to Finish</option>
                  </select>
                  <input type="number" bind:value={item.lag_days} class="rounded-lg border border-neutral-200 bg-white px-2 py-1.5 text-xs focus:border-neutral-400 focus:outline-none" placeholder="Lag" />
                  <button onclick={() => removeTaskSuccessor(i)} class="col-span-6 justify-self-end rounded border border-neutral-200 px-2 py-1 text-xs text-neutral-500 hover:bg-neutral-100">Remove</button>
                </div>
              {/each}
            {/if}
          </div>
        </article>

        <article class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
          <div class="flex items-center justify-between">
            <p class="text-xs font-semibold uppercase tracking-wide text-neutral-600">Tools Required</p>
            <button onclick={addTaskTool} class="text-xs font-medium text-neutral-600 hover:text-neutral-900">+ Add</button>
          </div>
          <div class="mt-2 space-y-2">
            {#if taskForm.tools_required.length === 0}
              <p class="text-xs text-neutral-400">No tools listed.</p>
            {:else}
              {#each taskForm.tools_required as tool, i}
                <div class="flex gap-2">
                  <input bind:value={tool.name} placeholder="Tool" class="w-2/5 rounded-lg border border-neutral-200 bg-white px-2 py-1.5 text-xs focus:border-neutral-400 focus:outline-none" />
                  <input bind:value={tool.description} placeholder="Description" class="flex-1 rounded-lg border border-neutral-200 bg-white px-2 py-1.5 text-xs focus:border-neutral-400 focus:outline-none" />
                  <button onclick={() => removeTaskTool(i)} class="rounded border border-neutral-200 px-2 py-1 text-xs text-neutral-500 hover:bg-neutral-100">Remove</button>
                </div>
              {/each}
            {/if}
          </div>
        </article>

        <article class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
          <div class="flex items-center justify-between">
            <p class="text-xs font-semibold uppercase tracking-wide text-neutral-600">Reference Links</p>
            <button onclick={addTaskRefLink} class="text-xs font-medium text-neutral-600 hover:text-neutral-900">+ Add</button>
          </div>
          <div class="mt-2 space-y-2">
            {#if taskForm.reference_links.length === 0}
              <p class="text-xs text-neutral-400">No reference links listed.</p>
            {:else}
              {#each taskForm.reference_links as link, i}
                <div class="flex gap-2">
                  <input bind:value={link.title} placeholder="Title" class="w-2/5 rounded-lg border border-neutral-200 bg-white px-2 py-1.5 text-xs focus:border-neutral-400 focus:outline-none" />
                  <input bind:value={link.url} placeholder="URL" class="flex-1 rounded-lg border border-neutral-200 bg-white px-2 py-1.5 text-xs focus:border-neutral-400 focus:outline-none" />
                  <button onclick={() => removeTaskRefLink(i)} class="rounded border border-neutral-200 px-2 py-1 text-xs text-neutral-500 hover:bg-neutral-100">Remove</button>
                </div>
              {/each}
            {/if}
          </div>
        </article>
      </div>

      <div class="mt-5 grid gap-4 lg:grid-cols-3">
        <article class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
          <p class="text-xs font-semibold uppercase tracking-wide text-neutral-600">Linked Documents</p>
          <div class="mt-2 max-h-48 space-y-1 overflow-y-auto rounded-lg border border-neutral-200 bg-white p-2">
            {#if formDocumentOptions.length === 0}
              <p class="text-xs text-neutral-400">No documents available for selected project.</p>
            {:else}
              {#each formDocumentOptions as row}
                <label class="flex items-start gap-2 rounded px-1 py-1 text-xs text-neutral-700 hover:bg-neutral-50">
                  <input
                    type="checkbox"
                    checked={taskForm.linked_documents.includes(row.id)}
                    onchange={() => toggleLinkedId("linked_documents", row.id)}
                    class="mt-0.5 h-3.5 w-3.5 rounded border-neutral-300 text-neutral-900"
                  />
                  <span>{row.document_number} • {row.title}</span>
                </label>
              {/each}
            {/if}
          </div>
        </article>

        <article class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
          <p class="text-xs font-semibold uppercase tracking-wide text-neutral-600">Linked Contracts</p>
          <div class="mt-2 max-h-48 space-y-1 overflow-y-auto rounded-lg border border-neutral-200 bg-white p-2">
            {#if formContractOptions.length === 0}
              <p class="text-xs text-neutral-400">No contract records available for selected project.</p>
            {:else}
              {#each formContractOptions as row}
                <label class="flex items-start gap-2 rounded px-1 py-1 text-xs text-neutral-700 hover:bg-neutral-50">
                  <input
                    type="checkbox"
                    checked={taskForm.linked_variation_orders.includes(row.id)}
                    onchange={() => toggleLinkedId("linked_variation_orders", row.id)}
                    class="mt-0.5 h-3.5 w-3.5 rounded border-neutral-300 text-neutral-900"
                  />
                  <span>{row.variation_number} • {row.title}</span>
                </label>
              {/each}
            {/if}
          </div>
        </article>

        <article class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
          <p class="text-xs font-semibold uppercase tracking-wide text-neutral-600">Linked Risks</p>
          <div class="mt-2 max-h-48 space-y-1 overflow-y-auto rounded-lg border border-neutral-200 bg-white p-2">
            {#if formRiskOptions.length === 0}
              <p class="text-xs text-neutral-400">No risk records available for selected project.</p>
            {:else}
              {#each formRiskOptions as row}
                <label class="flex items-start gap-2 rounded px-1 py-1 text-xs text-neutral-700 hover:bg-neutral-50">
                  <input
                    type="checkbox"
                    checked={taskForm.linked_risks.includes(row.id)}
                    onchange={() => toggleLinkedId("linked_risks", row.id)}
                    class="mt-0.5 h-3.5 w-3.5 rounded border-neutral-300 text-neutral-900"
                  />
                  <span>{row.title} • {row.severity}</span>
                </label>
              {/each}
            {/if}
          </div>
        </article>
      </div>

      <div class="mt-4 rounded-xl border border-neutral-200 bg-neutral-50 p-3">
        <label class="block">
          <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Completion Evidence Upload</span>
          <input
            type="file"
            multiple
            onchange={onSupportingFilesSelected}
            class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"
          />
        </label>
        {#if taskSupportingFiles.length > 0}
          <p class="mt-2 text-xs text-neutral-500">{taskSupportingFiles.length} supporting file(s) selected.</p>
        {/if}
      </div>

      <div class="mt-5 flex items-center justify-end gap-3">
        <button
          onclick={() => {
            showTaskModal = false;
            taskSupportingFiles = [];
          }}
          class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-600 transition hover:bg-neutral-50"
        >
          Cancel
        </button>
        <button
          onclick={saveTask}
          disabled={saving}
          class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-neutral-800 disabled:opacity-60"
        >
          {saving ? "Saving..." : editingTask ? "Save Task" : "Create Task"}
        </button>
      </div>
    </div>
  </div>
{/if}

{#if showWorkPackageModal}
  <div class="fixed inset-0 z-40 flex items-center justify-center bg-neutral-900/40 p-4">
    <div class="max-h-[90vh] w-full max-w-6xl overflow-y-auto rounded-2xl border border-neutral-200 bg-white p-6 shadow-2xl">
      <div class="flex items-start justify-between">
        <div>
          <h3 class="text-lg font-semibold text-neutral-900">
            {editingWorkPackage ? "Edit Work Package" : "Create Work Package"}
          </h3>
          <p class="mt-1 text-sm text-neutral-500">
            Draft standardized work packages for predictable project delivery.
          </p>
        </div>
        <button
          onclick={() => {
            showWorkPackageModal = false;
          }}
          class="rounded-lg border border-neutral-200 px-3 py-1.5 text-sm text-neutral-600 transition hover:bg-neutral-50"
        >
          Close
        </button>
      </div>

      <div class="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <label class="block">
          <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Project</span>
          <select
            bind:value={workPackageForm.project_id}
            class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none"
            disabled={workPackageSetupLoading}
            onchange={() => {
              workPackageForm.phase_id = "";
              workPackageForm.drawings = [];
              workPackageForm.linked_purchase_orders = [];
              workPackageForm.linked_cost_entries = [];
              workPackageForm.linked_inspections = [];
            }}
          >
            <option value="">Select project</option>
            {#each workPackageSetupOptions.projects as project}
              <option value={String(project.id)}>{project.name}</option>
            {/each}
          </select>
        </label>
        <label class="block">
          <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Phase</span>
          <select
            bind:value={workPackageForm.phase_id}
            class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none"
          >
            <option value="">Optional phase</option>
            {#each workPackageFormPhaseOptions as phase}
              <option value={String(phase.id)}>{phase.name}</option>
            {/each}
          </select>
        </label>
        <label class="block">
          <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Work Package ID</span>
          <input
            bind:value={workPackageForm.package_id}
            class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none"
            placeholder="Auto-generated if blank"
          />
        </label>
        <label class="block">
          <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Contractor</span>
          <select bind:value={workPackageForm.contractor_id} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none">
            <option value="">Select contractor</option>
            {#each workPackageSetupOptions.contractors as contractor}
              <option value={String(contractor.id)}>{contractor.name}</option>
            {/each}
          </select>
        </label>

        <label class="block md:col-span-2">
          <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Work Package Name</span>
          <input
            bind:value={workPackageForm.name}
            class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none"
            placeholder="e.g. Structural concrete"
          />
        </label>
        <label class="block">
          <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Budget</span>
          <input
            type="number"
            min="0"
            step="0.01"
            bind:value={workPackageForm.budget}
            class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none"
            placeholder="0.00"
          />
        </label>
        <label class="block">
          <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Start Date</span>
          <DateInput bind:value={workPackageForm.start_date} />
        </label>
        <label class="block">
          <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">End Date</span>
          <DateInput bind:value={workPackageForm.end_date} />
        </label>
      </div>

      {#if workPackageSetupOptions.examples.length > 0}
        <div class="mt-4">
          <p class="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-500">Examples</p>
          <div class="flex flex-wrap gap-2">
            {#each workPackageSetupOptions.examples as example}
              <button
                onclick={() => (workPackageForm.name = example)}
                class="rounded-full border border-neutral-200 bg-neutral-50 px-3 py-1 text-xs font-medium text-neutral-600 transition hover:border-neutral-300 hover:bg-neutral-100"
              >
                {example}
              </button>
            {/each}
          </div>
        </div>
      {/if}

      <label class="mt-4 block">
        <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Scope Description</span>
        <textarea
          bind:value={workPackageForm.scope_description}
          rows="3"
          class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none"
          placeholder="Detailed package scope..."
        ></textarea>
      </label>

      <label class="mt-4 block">
        <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">BOQ Items (one per line)</span>
        <textarea
          bind:value={workPackageForm.boq_items_text}
          rows="4"
          class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none"
          placeholder="Reinforcement steel&#10;C30 concrete supply&#10;Formwork accessories"
        ></textarea>
      </label>

      <div class="mt-4 grid gap-4 md:grid-cols-3">
        <label class="block">
          <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Quality Requirements</span>
          <textarea
            bind:value={workPackageForm.quality_requirements}
            rows="4"
            class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none"
            placeholder="Quality criteria and hold points..."
          ></textarea>
        </label>
        <label class="block">
          <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Safety Requirements</span>
          <textarea
            bind:value={workPackageForm.safety_requirements}
            rows="4"
            class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none"
            placeholder="Safety controls and PPE requirements..."
          ></textarea>
        </label>
        <label class="block">
          <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Inspection Plan</span>
          <textarea
            bind:value={workPackageForm.inspection_plan}
            rows="4"
            class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none"
            placeholder="Inspection frequency, checks, and sign-off flow..."
          ></textarea>
        </label>
      </div>

      <div class="mt-5 grid gap-4 lg:grid-cols-5">
        <article class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
          <p class="text-xs font-semibold uppercase tracking-wide text-neutral-600">Drawings</p>
          <div class="mt-2 max-h-44 space-y-1 overflow-y-auto rounded-lg border border-neutral-200 bg-white p-2">
            {#if workPackageFormDrawings.length === 0}
              <p class="text-xs text-neutral-400">No drawings available for selected project.</p>
            {:else}
              {#each workPackageFormDrawings as row}
                <label class="flex items-start gap-2 rounded px-1 py-1 text-xs text-neutral-700 hover:bg-neutral-50">
                  <input
                    type="checkbox"
                    checked={workPackageForm.drawings.includes(row.id)}
                    onchange={() => toggleWorkPackageLinkedId("drawings", row.id)}
                    class="mt-0.5 h-3.5 w-3.5 rounded border-neutral-300 text-neutral-900"
                  />
                  <span>{row.document_number} • {row.title}</span>
                </label>
              {/each}
            {/if}
          </div>
        </article>

        <article class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
          <p class="text-xs font-semibold uppercase tracking-wide text-neutral-600">Procurement</p>
          <div class="mt-2 max-h-44 space-y-1 overflow-y-auto rounded-lg border border-neutral-200 bg-white p-2">
            {#if workPackageFormPurchaseOrders.length === 0}
              <p class="text-xs text-neutral-400">No purchase orders for selected project.</p>
            {:else}
              {#each workPackageFormPurchaseOrders as row}
                <label class="flex items-start gap-2 rounded px-1 py-1 text-xs text-neutral-700 hover:bg-neutral-50">
                  <input
                    type="checkbox"
                    checked={workPackageForm.linked_purchase_orders.includes(row.id)}
                    onchange={() => toggleWorkPackageLinkedId("linked_purchase_orders", row.id)}
                    class="mt-0.5 h-3.5 w-3.5 rounded border-neutral-300 text-neutral-900"
                  />
                  <span>{row.po_number || `PO-${row.id}`} • {row.vendor_name}</span>
                </label>
              {/each}
            {/if}
          </div>
        </article>

        <article class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
          <p class="text-xs font-semibold uppercase tracking-wide text-neutral-600">Finance</p>
          <div class="mt-2 max-h-44 space-y-1 overflow-y-auto rounded-lg border border-neutral-200 bg-white p-2">
            {#if workPackageFormCostEntries.length === 0}
              <p class="text-xs text-neutral-400">No cost entries for selected project.</p>
            {:else}
              {#each workPackageFormCostEntries as row}
                <label class="flex items-start gap-2 rounded px-1 py-1 text-xs text-neutral-700 hover:bg-neutral-50">
                  <input
                    type="checkbox"
                    checked={workPackageForm.linked_cost_entries.includes(row.id)}
                    onchange={() => toggleWorkPackageLinkedId("linked_cost_entries", row.id)}
                    class="mt-0.5 h-3.5 w-3.5 rounded border-neutral-300 text-neutral-900"
                  />
                  <span>{row.phase_name} • {row.description}</span>
                </label>
              {/each}
            {/if}
          </div>
        </article>

        <article class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
          <p class="text-xs font-semibold uppercase tracking-wide text-neutral-600">Contractors</p>
          <div class="mt-2 max-h-44 space-y-1 overflow-y-auto rounded-lg border border-neutral-200 bg-white p-2">
            {#if workPackageSetupOptions.contractors.length === 0}
              <p class="text-xs text-neutral-400">No contractors available.</p>
            {:else}
              {#each workPackageSetupOptions.contractors as row}
                <label class="flex items-start gap-2 rounded px-1 py-1 text-xs text-neutral-700 hover:bg-neutral-50">
                  <input
                    type="checkbox"
                    checked={workPackageForm.linked_contractors.includes(row.id)}
                    onchange={() => toggleWorkPackageLinkedId("linked_contractors", row.id)}
                    class="mt-0.5 h-3.5 w-3.5 rounded border-neutral-300 text-neutral-900"
                  />
                  <span>{row.name}</span>
                </label>
              {/each}
            {/if}
          </div>
        </article>

        <article class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
          <p class="text-xs font-semibold uppercase tracking-wide text-neutral-600">Inspections</p>
          <div class="mt-2 max-h-44 space-y-1 overflow-y-auto rounded-lg border border-neutral-200 bg-white p-2">
            {#if workPackageFormInspections.length === 0}
              <p class="text-xs text-neutral-400">No inspections for selected project.</p>
            {:else}
              {#each workPackageFormInspections as row}
                <label class="flex items-start gap-2 rounded px-1 py-1 text-xs text-neutral-700 hover:bg-neutral-50">
                  <input
                    type="checkbox"
                    checked={workPackageForm.linked_inspections.includes(row.id)}
                    onchange={() => toggleWorkPackageLinkedId("linked_inspections", row.id)}
                    class="mt-0.5 h-3.5 w-3.5 rounded border-neutral-300 text-neutral-900"
                  />
                  <span>{row.inspection_number || `INSP-${row.id}`} • {row.inspector_name}</span>
                </label>
              {/each}
            {/if}
          </div>
        </article>
      </div>

      <div class="mt-5 flex items-center justify-end gap-3">
        <button
          onclick={() => {
            showWorkPackageModal = false;
          }}
          class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-600 transition hover:bg-neutral-50"
        >
          Cancel
        </button>
        {#if isDev}
          <button
            type="button"
            onclick={devFillWorkPackage}
            class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600"
          >
            Dev Fill
          </button>
        {/if}
        <button
          onclick={saveWorkPackage}
          disabled={workPackageSaving}
          class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-neutral-800 disabled:opacity-60"
        >
          {workPackageSaving ? "Saving..." : editingWorkPackage ? "Save Work Package" : "Create Work Package"}
        </button>
      </div>
    </div>
  </div>
{/if}

{#if commentsTask}
  <div class="fixed inset-0 z-50 flex justify-end bg-neutral-900/35">
    <div class="h-full w-full max-w-xl border-l border-neutral-200 bg-white shadow-2xl">
      <div class="flex items-start justify-between border-b border-neutral-200 px-5 py-4">
        <div>
          <h3 class="text-base font-semibold text-neutral-900">Task Comments</h3>
          <p class="mt-1 text-xs text-neutral-500">{commentsTask.name}</p>
        </div>
        <button
          onclick={() => {
            commentsTask = null;
            comments = [];
            newComment = "";
          }}
          class="rounded-lg border border-neutral-200 px-3 py-1.5 text-sm text-neutral-600 transition hover:bg-neutral-50"
        >
          Close
        </button>
      </div>

      <div class="h-[calc(100%-9.5rem)] overflow-y-auto px-5 py-4">
        {#if commentsLoading}
          <p class="text-sm text-neutral-500">Loading comments...</p>
        {:else if comments.length === 0}
          <p class="text-sm text-neutral-500">No comments yet.</p>
        {:else}
          <div class="space-y-3">
            {#each comments as comment (comment.id)}
              <article class="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
                <div class="flex items-center justify-between gap-2">
                  <p class="text-xs font-semibold text-neutral-700">{comment.author_name ?? "Unknown user"}</p>
                  <p class="text-[11px] text-neutral-500">{formatDateTime(comment.created_at)}</p>
                </div>
                <p class="mt-2 whitespace-pre-wrap text-sm text-neutral-700">{comment.comment}</p>
              </article>
            {/each}
          </div>
        {/if}
      </div>

      <div class="border-t border-neutral-200 px-5 py-4">
        <textarea
          bind:value={newComment}
          rows="3"
          class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none"
          placeholder="Write task comment..."
        ></textarea>
        <div class="mt-3 flex justify-end">
          <button
            onclick={postComment}
            disabled={commentsPosting || newComment.trim().length === 0}
            class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-neutral-800 disabled:opacity-60"
          >
            {commentsPosting ? "Posting..." : "Post Comment"}
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}

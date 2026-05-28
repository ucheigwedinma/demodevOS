<script lang="ts">
  import { onMount } from "svelte";

  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";

  interface TaskTemplateSummary {
    id: number;
    name: string;
    description: string;
    assigned_role: string;
    priority: string;
    sort_order: number;
    reference_code: string;
    estimated_effort_hours: number | null;
  }

  interface Activity {
    id: number;
    name: string;
    description: string;
    sort_order: number;
    estimated_duration_days: number | null;
    estimated_effort_hours: number | null;
    wbs_code: string;
    task_templates: TaskTemplateSummary[];
  }

  interface Phase {
    id: number;
    name: string;
    description: string;
    sort_order: number;
    duration_days: number | null;
    weight: number;
    activities: Activity[];
  }

  interface ProjectTemplate {
    id: number;
    name: string;
    template_type: string;
    template_type_display: string;
    description: string;
    is_active: boolean;
    is_system: boolean;
    phases: Phase[];
    created_at: string;
    updated_at: string;
  }

  interface TemplateListItem {
    id: number;
    name: string;
    template_type: string;
    template_type_display: string;
    description: string;
    is_active: boolean;
    is_system: boolean;
    phase_count: number;
    created_at: string;
  }

  interface ActivityForm {
    name: string;
    description: string;
    sort_order: string;
    estimated_duration_days: string;
    estimated_effort_hours: string;
    wbs_code: string;
  }

  interface TaskDetailForm {
    name: string;
    description: string;
    assigned_role: string;
    priority: string;
    estimated_effort_hours: string;
    reference_code: string;
    duration_days: string;
    required_materials: string;
    equipment_type: string;
    output_unit: string;
    is_milestone: boolean;
    predecessors: string;
    resource_tags: string;
  }

  interface WbsRow {
    type: "phase" | "activity" | "task";
    depth: number;
    wbsCode: string;
    name: string;
    role: string;
    effort: string;
    dependencies: string;
    phaseId: number;
    activityId?: number;
    taskId?: number;
    hasChildren: boolean;
    collapsed: boolean;
  }

  function createActivityForm(): ActivityForm {
    return {
      name: "",
      description: "",
      sort_order: "0",
      estimated_duration_days: "",
      estimated_effort_hours: "",
      wbs_code: "",
    };
  }

  function createTaskDetailForm(): TaskDetailForm {
    return {
      name: "",
      description: "",
      assigned_role: "",
      priority: "medium",
      estimated_effort_hours: "",
      reference_code: "",
      duration_days: "",
      required_materials: "",
      equipment_type: "",
      output_unit: "",
      is_milestone: false,
      predecessors: "",
      resource_tags: "",
    };
  }

  function buildWbsRows(
    template: ProjectTemplate | null,
    phaseCollapseState: Set<number>,
    activityCollapseState: Set<number>
  ): WbsRow[] {
    if (!template) return [];

    const rows: WbsRow[] = [];

    for (const phase of template.phases) {
      const phaseCode = `${phase.sort_order + 1}.0`;
      const phaseEffort = phase.activities.reduce((sum: number, activity: Activity) => {
        const taskEffort = activity.task_templates.reduce(
          (taskSum: number, task: TaskTemplateSummary) => taskSum + (task.estimated_effort_hours ?? 0),
          0
        );
        return sum + (activity.estimated_effort_hours ?? 0) + taskEffort;
      }, 0);
      const phaseCollapsed = phaseCollapseState.has(phase.id);

      rows.push({
        type: "phase",
        depth: 0,
        wbsCode: phaseCode,
        name: phase.name,
        role: "",
        effort: phaseEffort > 0 ? `${phaseEffort}h` : "—",
        dependencies: "—",
        phaseId: phase.id,
        hasChildren: phase.activities.length > 0,
        collapsed: phaseCollapsed,
      });

      if (phaseCollapsed) continue;

      for (const activity of phase.activities) {
        const activityCode = activity.wbs_code || `${phase.sort_order + 1}.${activity.sort_order + 1}`;
        const activityEffort =
          (activity.estimated_effort_hours ?? 0) +
          activity.task_templates.reduce(
            (sum: number, task: TaskTemplateSummary) => sum + (task.estimated_effort_hours ?? 0),
            0
          );
        const activityCollapsed = activityCollapseState.has(activity.id);

        rows.push({
          type: "activity",
          depth: 1,
          wbsCode: activityCode,
          name: activity.name,
          role: "",
          effort: activityEffort > 0 ? `${activityEffort}h` : "—",
          dependencies: "—",
          phaseId: phase.id,
          activityId: activity.id,
          hasChildren: activity.task_templates.length > 0,
          collapsed: activityCollapsed,
        });

        if (activityCollapsed) continue;

        for (const task of activity.task_templates) {
          const taskCode = task.reference_code || `${activityCode}.${task.sort_order + 1}`;
          rows.push({
            type: "task",
            depth: 2,
            wbsCode: taskCode,
            name: task.name,
            role: task.assigned_role || "—",
            effort: task.estimated_effort_hours ? `${task.estimated_effort_hours}h` : "—",
            dependencies: "—",
            phaseId: phase.id,
            activityId: activity.id,
            taskId: task.id,
            hasChildren: false,
            collapsed: false,
          });
        }
      }
    }

    return rows;
  }

  interface BlueprintListItem { id: number; name: string; status: string; status_display: string; phase_count: number; }

  let loading = $state(true);
  let templates = $state<TemplateListItem[]>([]);
  let blueprints = $state<BlueprintListItem[]>([]);
  let selectedTemplateId = $state<number | null>(null);
  let selectedBlueprintId = $state<number | null>(null);
  let activeTemplate = $state<ProjectTemplate | null>(null);
  let activeSource = $state<"template" | "blueprint">("template");
  let templateLoading = $state(false);

  let showActivityModal = $state(false);
  let activitySaving = $state(false);
  let activityPhaseId = $state<number | null>(null);
  let activityForm = $state<ActivityForm>(createActivityForm());

  let showTaskDrawer = $state(false);
  let taskDrawerVisible = $state(false);
  let selectedTask = $state<TaskTemplateSummary | null>(null);
  let selectedTaskPhaseId = $state<number | null>(null);
  let selectedTaskActivityId = $state<number | null>(null);
  let taskDetailForm = $state<TaskDetailForm>(createTaskDetailForm());
  let taskSaving = $state(false);

  let totalPhases = $state(0);
  let totalActivities = $state(0);
  let totalTasks = $state(0);
  let estimatedDuration = $state(0);

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  let collapsedPhases = $state(new Set<number>());
  let collapsedActivities = $state(new Set<number>());
  let wbsRows = $state<WbsRow[]>([]);

  $effect(() => {
    const phases = activeTemplate?.phases ?? [];
    totalPhases = phases.length;
    totalActivities = phases.reduce(
      (sum: number, phase: Phase) => sum + phase.activities.length, 0
    );
    totalTasks = phases.reduce((sum: number, phase: Phase) => {
      return sum + phase.activities.reduce(
        (activitySum: number, activity: Activity) => activitySum + activity.task_templates.length, 0
      );
    }, 0);
    estimatedDuration = phases.reduce(
      (sum: number, phase: Phase) => sum + (phase.duration_days || 0), 0
    );
    wbsRows = buildWbsRows(activeTemplate, collapsedPhases, collapsedActivities);
  });

  function openTaskDrawer(task: TaskTemplateSummary, phaseId?: number, activityId?: number) {
    selectedTask = task;
    selectedTaskPhaseId = phaseId ?? null;
    selectedTaskActivityId = activityId ?? null;
    taskDetailForm = {
      ...createTaskDetailForm(),
      name: task.name,
      description: task.description,
      assigned_role: task.assigned_role,
      priority: task.priority || "medium",
      estimated_effort_hours: task.estimated_effort_hours
        ? String(task.estimated_effort_hours)
        : "",
      reference_code: task.reference_code || "",
      resource_tags: task.assigned_role || "",
    };
    showTaskDrawer = true;
    requestAnimationFrame(() => {
      taskDrawerVisible = true;
    });
  }

  function closeTaskDrawer() {
    taskDrawerVisible = false;
    setTimeout(() => {
      showTaskDrawer = false;
      selectedTask = null;
    }, 300);
  }

  function handleTemplateChange(event: Event) {
    const id = Number((event.target as HTMLSelectElement).value);
    if (id) {
      void selectTemplate(id);
    }
  }

  function handleActivitySubmit(event: SubmitEvent) {
    event.preventDefault();
    void saveActivity();
  }

  function handleTaskRowClick(taskId: number | undefined) {
    if (!taskId || !activeTemplate) return;

    const task = activeTemplate.phases
      .flatMap((phase: Phase) => phase.activities)
      .flatMap((activity: Activity) => activity.task_templates)
      .find((templateTask: TaskTemplateSummary) => templateTask.id === taskId);

    if (task) {
      openTaskDrawer(task);
    }
  }

  function togglePhase(id: number) {
    const next = new Set(collapsedPhases);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    collapsedPhases = next;
  }

  function toggleActivity(id: number) {
    const next = new Set(collapsedActivities);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    collapsedActivities = next;
  }

  async function saveTaskDetail() {
    if (!selectedTask) return;

    taskSaving = true;
    try {
      const isBlueprint = activeSource === "blueprint" && selectedBlueprintId;
      const taskUrl = isBlueprint && selectedTaskPhaseId && selectedTaskActivityId
        ? `/projects/blueprints/${selectedBlueprintId}/phases/${selectedTaskPhaseId}/activities/${selectedTaskActivityId}/tasks/${selectedTask.id}/`
        : `/settings/entity-templates/tasks/${selectedTask.id}/`;
      await api.patch(taskUrl, {
        name: taskDetailForm.name.trim(),
        description: taskDetailForm.description.trim(),
        assigned_role: taskDetailForm.assigned_role.trim(),
        priority: taskDetailForm.priority,
        estimated_effort_hours: taskDetailForm.estimated_effort_hours
          ? Number(taskDetailForm.estimated_effort_hours)
          : null,
        reference_code: taskDetailForm.reference_code.trim(),
      });
      toast.success(
        "Task updated",
        `"${taskDetailForm.name}" has been saved.`
      );
      closeTaskDrawer();
      if (selectedTemplateId) await selectTemplate(selectedTemplateId);
      else if (selectedBlueprintId) await selectBlueprint(selectedBlueprintId);
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error(
          "Save failed",
          Object.values(err.fieldErrors).flat().join(" ") || "Check the form."
        );
      } else {
        toast.error("Save failed", "Could not save task.");
      }
    } finally {
      taskSaving = false;
    }
  }

  async function loadTemplates() {
    loading = true;
    try {
      const [tmplRes, bpRes] = await Promise.all([
        api.get<{ results: TemplateListItem[] }>("/settings/project-templates/", { page_size: "100", is_active: "true" }),
        api.get<{ results: BlueprintListItem[] }>("/projects/blueprints/", { page_size: "100" }),
      ]);
      templates = tmplRes.results;
      blueprints = bpRes.results;
      if (templates.length > 0 && !selectedTemplateId && !selectedBlueprintId) {
        await selectTemplate(templates[0].id);
      }
    } catch {
      toast.error("Load failed", "Could not load data.");
    } finally {
      loading = false;
    }
  }

  async function selectBlueprint(id: number) {
    selectedBlueprintId = id;
    selectedTemplateId = null;
    activeSource = "blueprint";
    templateLoading = true;
    try {
      const bp = await api.get<BlueprintDetail>(`/projects/blueprints/${id}/`);
      // Map blueprint structure to the same shape as ProjectTemplate for the WBS grid
      activeTemplate = {
        id: bp.id,
        name: bp.name,
        template_type: "",
        template_type_display: "Blueprint",
        description: bp.description,
        is_active: true,
        is_system: false,
        phases: bp.phases.map(p => ({
          ...p,
          activities: p.activities.map(a => ({
            ...a,
            task_templates: a.tasks,
          })),
        })),
        created_at: "",
        updated_at: "",
      };
    } catch {
      activeTemplate = null;
      toast.error("Load failed", "Could not load blueprint details.");
    } finally {
      templateLoading = false;
    }
  }

  async function selectTemplate(id: number) {
    selectedTemplateId = id;
    selectedBlueprintId = null;
    activeSource = "template";
    templateLoading = true;
    try {
      activeTemplate = await api.get<ProjectTemplate>(
        `/settings/project-templates/${id}/`
      );
    } catch {
      activeTemplate = null;
      toast.error("Load failed", "Could not load template details.");
    } finally {
      templateLoading = false;
    }
  }

  let editingActivityId = $state<number | null>(null);

  // Save as Master Template
  let showSaveTemplateModal = $state(false);
  let saveTemplateName = $state("");
  let saveTemplateType = $state("residential");
  let saveTemplateSaving = $state(false);

  async function saveAsMasterTemplate() {
    if (!selectedBlueprintId || !saveTemplateName.trim()) {
      toast.error("Missing data", "Template name is required.");
      return;
    }
    saveTemplateSaving = true;
    try {
      const res = await api.post<{ template_id: number; name: string; phases: number; activities: number }>(
        `/projects/blueprints/${selectedBlueprintId}/save-as-template/`,
        { name: saveTemplateName.trim(), template_type: saveTemplateType },
      );
      toast.success("Template created", `"${res.name}" saved with ${res.phases} phases and ${res.activities} activities.`);
      showSaveTemplateModal = false;
      saveTemplateName = "";
      // Reload templates list so it appears in the dropdown
      const tmplRes = await api.get<{ results: TemplateListItem[] }>("/settings/project-templates/", { page_size: "100", is_active: "true" });
      templates = tmplRes.results;
    } catch (err) {
      if (err instanceof ApiError) {
        const msg = Object.values(err.fieldErrors).flat().join(" ") || err.message;
        toast.error("Save failed", msg);
      } else {
        toast.error("Save failed", "Could not create template.");
      }
    } finally {
      saveTemplateSaving = false;
    }
  }

  // Add / edit phase on blueprint (inline editor)
  let addPhaseName = $state("");
  let addPhaseSaving = $state(false);
  let editingPhaseId = $state<number | null>(null);
  let editingPhaseName = $state("");

  function startEditPhase(phaseId: number, currentName: string) {
    if (activeSource !== "blueprint") return;
    editingPhaseId = phaseId;
    editingPhaseName = currentName;
  }

  async function saveEditPhase() {
    if (!selectedBlueprintId || editingPhaseId === null) return;
    const trimmed = editingPhaseName.trim();
    if (!trimmed) { editingPhaseId = null; return; }
    try {
      await api.patch(`/projects/blueprints/${selectedBlueprintId}/phases/${editingPhaseId}/`, { name: trimmed });
      editingPhaseId = null;
      await selectBlueprint(selectedBlueprintId);
    } catch (err) {
      if (err instanceof ApiError) toast.error("Save failed", Object.values(err.fieldErrors).flat().join(" ") || "Could not rename phase.");
      else toast.error("Save failed", "Could not rename phase.");
    }
  }

  function cancelEditPhase() {
    editingPhaseId = null;
    editingPhaseName = "";
  }

  async function deletePhase(phaseId: number, phaseName: string) {
    if (!selectedBlueprintId) return;
    if (!confirm(`Delete phase "${phaseName}"? Activities and tasks under it will also be removed.`)) return;
    try {
      await api.delete(`/projects/blueprints/${selectedBlueprintId}/phases/${phaseId}/`);
      await selectBlueprint(selectedBlueprintId);
    } catch (err) {
      if (err instanceof ApiError) toast.error("Delete failed", (err.data?.detail as string) || "Could not delete phase.");
      else toast.error("Delete failed", "Could not delete phase.");
    }
  }

  async function addPhase() {
    if (!selectedBlueprintId || !addPhaseName.trim()) {
      toast.error("Required", "Phase name is required.");
      return;
    }
    addPhaseSaving = true;
    try {
      const existing = activeTemplate?.phases ?? [];
      const sortOrder = existing.length;
      const weight = existing.length === 0 ? 100 : Math.max(1, Math.round(100 / (existing.length + 1)));
      await api.post(`/projects/blueprints/${selectedBlueprintId}/phases/`, {
        name: addPhaseName.trim(),
        sort_order: sortOrder,
        weight,
        duration_days: null,
      });
      addPhaseName = "";
      await selectBlueprint(selectedBlueprintId);
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error("Save failed", Object.values(err.fieldErrors).flat().join(" ") || "Could not add phase.");
      } else {
        toast.error("Save failed", "Could not add phase.");
      }
    } finally {
      addPhaseSaving = false;
    }
  }

  // Add task to activity
  let showAddTaskModal = $state(false);
  let addTaskActivityId = $state<number | null>(null);
  let addTaskPhaseId = $state<number | null>(null);
  let addTaskSaving = $state(false);
  let addTaskMode = $state<"custom" | "library">("library");
  let addTaskForm = $state({ name: "", description: "", assigned_role: "", estimated_effort_hours: "", reference_code: "" });
  let taskLibrary = $state<TaskTemplateSummary[]>([]);
  let taskLibrarySearch = $state("");
  let taskLibraryLoading = $state(false);

  const filteredLibrary = $derived.by(() => {
    if (!taskLibrarySearch.trim()) return taskLibrary;
    const q = taskLibrarySearch.trim().toLowerCase();
    return taskLibrary.filter((t: TaskTemplateSummary) => t.name.toLowerCase().includes(q) || t.assigned_role.toLowerCase().includes(q));
  });

  async function openAddTask(activityId: number, phaseId: number) {
    addTaskActivityId = activityId;
    addTaskPhaseId = phaseId;
    addTaskMode = "library";
    addTaskForm = { name: "", description: "", assigned_role: "", estimated_effort_hours: "", reference_code: "" };
    taskLibrarySearch = "";
    showAddTaskModal = true;
    // Load task template library
    if (taskLibrary.length === 0) {
      taskLibraryLoading = true;
      try {
        const res = await api.get<TaskTemplateSummary[]>("/settings/entity-templates/tasks/");
        taskLibrary = Array.isArray(res) ? res : (res as any).results || [];
      } catch { /* ignore */ }
      finally { taskLibraryLoading = false; }
    }
  }

  async function linkTaskTemplate(taskId: number) {
    if (!addTaskActivityId) return;
    addTaskSaving = true;
    try {
      const source = taskLibrary.find((t: TaskTemplateSummary) => t.id === taskId);
      if (!source) { addTaskSaving = false; return; }

      const isBlueprint = activeSource === "blueprint" && selectedBlueprintId;
      const taskPayload = {
        name: `${source.name}`,
        description: source.description || "",
        assigned_role: source.assigned_role || "",
        estimated_effort_hours: source.estimated_effort_hours,
        reference_code: source.reference_code || "",
        ...(isBlueprint ? {} : { activity: addTaskActivityId }),
      };
      const taskUrl = isBlueprint
        ? `/projects/blueprints/${selectedBlueprintId}/phases/${addTaskPhaseId}/activities/${addTaskActivityId}/tasks/`
        : "/settings/entity-templates/tasks/";

      await api.post(taskUrl, taskPayload);
      toast.success("Task added", `"${source.name}" has been added to the activity.`);
      showAddTaskModal = false;
      if (selectedTemplateId) await selectTemplate(selectedTemplateId);
      else if (selectedBlueprintId) await selectBlueprint(selectedBlueprintId);
    } catch (err) {
      if (err instanceof ApiError) {
        const msg = Object.values(err.fieldErrors).flat().join(" ");
        if (msg.toLowerCase().includes("already exists") || msg.toLowerCase().includes("unique")) {
          const source = taskLibrary.find((t: TaskTemplateSummary) => t.id === taskId);
          if (source) {
            const isBlueprint = activeSource === "blueprint" && selectedBlueprintId;
            const retryUrl = isBlueprint
              ? `/projects/blueprints/${selectedBlueprintId}/phases/${addTaskPhaseId}/activities/${addTaskActivityId}/tasks/`
              : "/settings/entity-templates/tasks/";
            try {
              await api.post(retryUrl, {
                name: `${source.name} (${Date.now().toString(36)})`,
                description: source.description || "",
                assigned_role: source.assigned_role || "",
                estimated_effort_hours: source.estimated_effort_hours,
                reference_code: source.reference_code || "",
                ...(isBlueprint ? {} : { activity: addTaskActivityId }),
              });
              toast.success("Task added", `"${source.name}" has been added to the activity.`);
              showAddTaskModal = false;
              if (selectedTemplateId) await selectTemplate(selectedTemplateId);
              else if (selectedBlueprintId) await selectBlueprint(selectedBlueprintId);
              return;
            } catch { /* fall through */ }
          }
        }
        toast.error("Add failed", msg || "Could not add task.");
      } else toast.error("Add failed", "Could not add task to activity.");
    } finally { addTaskSaving = false; }
  }

  async function saveAddTask() {
    if (!addTaskActivityId || !addTaskForm.name.trim()) {
      toast.error("Missing data", "Task name is required.");
      return;
    }
    addTaskSaving = true;
    try {
      const isBlueprint = activeSource === "blueprint" && selectedBlueprintId;
      const taskUrl = isBlueprint
        ? `/projects/blueprints/${selectedBlueprintId}/phases/${addTaskPhaseId}/activities/${addTaskActivityId}/tasks/`
        : "/settings/entity-templates/tasks/";
      await api.post(taskUrl, {
        name: addTaskForm.name.trim(),
        description: addTaskForm.description.trim(),
        assigned_role: addTaskForm.assigned_role.trim(),
        estimated_effort_hours: addTaskForm.estimated_effort_hours ? Number(addTaskForm.estimated_effort_hours) : null,
        reference_code: addTaskForm.reference_code.trim(),
        ...(isBlueprint ? {} : { activity: addTaskActivityId }),
      });
      toast.success("Task added", `"${addTaskForm.name}" has been added to the activity.`);
      showAddTaskModal = false;
      if (selectedTemplateId) await selectTemplate(selectedTemplateId);
      else if (selectedBlueprintId) await selectBlueprint(selectedBlueprintId);
    } catch (err) {
      if (err instanceof ApiError) toast.error("Save failed", Object.values(err.fieldErrors).flat().join(" ") || "Check the form.");
      else toast.error("Save failed", "Could not save task.");
    } finally {
      addTaskSaving = false;
    }
  }

  function openAddActivity(phaseId: number) {
    editingActivityId = null;
    activityPhaseId = phaseId;
    const phase = activeTemplate?.phases.find(
      (phaseItem: Phase) => phaseItem.id === phaseId
    );
    activityForm = {
      ...createActivityForm(),
      sort_order: String(phase?.activities.length ?? 0),
    };
    showActivityModal = true;
  }

  function openEditActivity(phaseId: number, activityId: number) {
    const phase = activeTemplate?.phases.find((p: Phase) => p.id === phaseId);
    const activity = phase?.activities.find((a: Activity) => a.id === activityId);
    if (!activity) return;
    editingActivityId = activityId;
    activityPhaseId = phaseId;
    activityForm = {
      name: activity.name,
      description: activity.description,
      sort_order: String(activity.sort_order),
      estimated_duration_days: activity.estimated_duration_days ? String(activity.estimated_duration_days) : "",
      estimated_effort_hours: activity.estimated_effort_hours ? String(activity.estimated_effort_hours) : "",
      wbs_code: activity.wbs_code || "",
    };
    showActivityModal = true;
  }

  async function saveActivity() {
    if (!activityPhaseId || !activityForm.name.trim()) {
      toast.error("Missing data", "Activity name is required.");
      return;
    }

    activitySaving = true;
    const payload = {
      name: activityForm.name.trim(),
      description: activityForm.description.trim(),
      sort_order: Number(activityForm.sort_order) || 0,
      estimated_duration_days: activityForm.estimated_duration_days ? Number(activityForm.estimated_duration_days) : null,
      estimated_effort_hours: activityForm.estimated_effort_hours ? Number(activityForm.estimated_effort_hours) : null,
      wbs_code: activityForm.wbs_code.trim(),
      phase: activityPhaseId,
    };
    try {
      const isBlueprint = activeSource === "blueprint" && selectedBlueprintId;
      const baseUrl = isBlueprint
        ? `/projects/blueprints/${selectedBlueprintId}/phases/${activityPhaseId}/activities`
        : `/settings/project-templates/phases/${activityPhaseId}/activities`;

      if (editingActivityId) {
        await api.patch(`${baseUrl}/${editingActivityId}/`, payload);
        toast.success("Activity updated", `"${activityForm.name}" has been saved.`);
      } else {
        await api.post(`${baseUrl}/`, payload);
        toast.success("Activity added", `"${activityForm.name}" has been added to the WBS.`);
      }
      showActivityModal = false;
      if (selectedTemplateId) await selectTemplate(selectedTemplateId);
      else if (selectedBlueprintId) await selectBlueprint(selectedBlueprintId);
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error(
          "Save failed",
          Object.values(err.fieldErrors).flat().join(" ") || "Check the form."
        );
      } else {
        toast.error("Save failed", "Could not save activity.");
      }
    } finally {
      activitySaving = false;
    }
  }

  async function deleteActivity(phaseId: number, activityId: number) {
    try {
      const isBlueprint = activeSource === "blueprint" && selectedBlueprintId;
      const url = isBlueprint
        ? `/projects/blueprints/${selectedBlueprintId}/phases/${phaseId}/activities/${activityId}/`
        : `/settings/project-templates/phases/${phaseId}/activities/${activityId}/`;
      await api.delete(url);
      toast.success("Deleted", "Activity removed from the WBS.");
      if (selectedTemplateId) await selectTemplate(selectedTemplateId);
      else if (selectedBlueprintId) await selectBlueprint(selectedBlueprintId);
    } catch {
      toast.error("Delete failed", "Could not remove activity.");
    }
  }

  async function autoNumberWbs() {
    if (!activeTemplate) return;
    const isBlueprint = activeSource === "blueprint" && selectedBlueprintId;

    for (const phase of activeTemplate.phases) {
      const phaseIndex = phase.sort_order + 1;
      for (let i = 0; i < phase.activities.length; i += 1) {
        const activity = phase.activities[i];
        const wbsCode = `${phaseIndex}.${i + 1}`;
        if (activity.wbs_code !== wbsCode) {
          try {
            const url = isBlueprint
              ? `/projects/blueprints/${selectedBlueprintId}/phases/${phase.id}/activities/${activity.id}/`
              : `/settings/project-templates/phases/${phase.id}/activities/${activity.id}/`;
            await api.patch(url, {
                wbs_code: wbsCode,
              }
            );
          } catch {
            // Continue numbering the rest of the WBS.
          }
        }
      }
    }

    toast.success("WBS numbered", "All activities have been auto-numbered.");
    if (selectedTemplateId) await selectTemplate(selectedTemplateId);
    else if (selectedBlueprintId) await selectBlueprint(selectedBlueprintId);
  }

  function devFillActivity() {
    const names = [
      "Site Clearing & Preparation",
      "Excavation & Earthworks",
      "Formwork & Reinforcement",
      "Concrete Pouring",
      "Curing & Finishing",
      "Waterproofing & Backfill",
      "MEP Rough-In Coordination",
      "Quality Inspection Hold Point",
    ];
    const index = Math.floor(Math.random() * names.length);
    activityForm.name = names[index];
    activityForm.description = `${names[index]} — standard construction activity for this phase.`;
    activityForm.estimated_duration_days = String(
      Math.floor(Math.random() * 14) + 3
    );
    activityForm.estimated_effort_hours = String(
      Math.floor(Math.random() * 200) + 40
    );
    activityForm.sort_order = String(Math.floor(Math.random() * 10));
  }

  onMount(() => {
    void loadTemplates();
  });
</script>

<svelte:head><title>Project Planner — WBS | developerOS</title></svelte:head>

<div class="space-y-6">
  <!-- A. WBS Planning Header -->
  <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">
        {#if activeSource === "blueprint"}
          <a href="/projects/blueprints" class="hover:text-indigo-700">Planning &amp; Library</a>
          <span class="text-neutral-300"> › </span>
          <a href="/projects/blueprints" class="hover:text-indigo-700">Blueprints</a>
        {:else}
          Planning &amp; Library
        {/if}
      </p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">
        {#if activeSource === "blueprint" && activeTemplate}
          {activeTemplate.name}
        {:else}
          Work Breakdown Structure
        {/if}
      </h1>
      <p class="mt-1 text-sm text-neutral-500">
        {#if activeSource === "blueprint"}
          Build the work breakdown structure for this blueprint — phases, activities, and tasks.
        {:else}
          Decompose project templates into phases, activities, and tasks for execution planning.
        {/if}
      </p>
    </div>
    <div class="flex flex-wrap gap-2">
      <button
        onclick={autoNumberWbs}
        disabled={!activeTemplate || totalActivities === 0}
        class="rounded-lg border border-neutral-200 bg-white px-3.5 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed"
      >
        Auto-Number Tasks
      </button>
      <button
        onclick={() => { showSaveTemplateModal = true; }}
        disabled={activeSource !== "blueprint" || !selectedBlueprintId || totalPhases === 0}
        class="rounded-lg border border-neutral-200 bg-white px-3.5 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed"
        title={activeSource !== "blueprint" ? "Select a blueprint to save as template" : ""}
      >
        Save as Master Template
      </button>
    </div>
  </div>

  <!-- Source Selector -->
  <div class="flex flex-col gap-4 sm:flex-row sm:items-center">
    <div class="flex-1">
      <label for="project-template-select" class="block text-xs font-medium text-neutral-500 mb-1">Template</label>
      <select
        id="project-template-select"
        onchange={handleTemplateChange}
        class="w-full rounded-lg border px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 {activeSource === 'template' ? 'border-neutral-900 bg-neutral-50' : 'border-neutral-200 bg-white'}"
      >
        <option value="" disabled selected={!selectedTemplateId}>Select a template...</option>
        {#each templates as tmpl}
          <option value={tmpl.id} selected={tmpl.id === selectedTemplateId}>
            {tmpl.name} ({tmpl.template_type_display})
          </option>
        {/each}
      </select>
    </div>
    <div class="flex-1">
      <label for="project-blueprint-select" class="block text-xs font-medium text-neutral-500 mb-1">Blueprint</label>
      <select
        id="project-blueprint-select"
        onchange={(e) => { const id = Number((e.target as HTMLSelectElement).value); if (id) selectBlueprint(id); }}
        class="w-full rounded-lg border px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 {activeSource === 'blueprint' ? 'border-emerald-600 bg-emerald-50' : 'border-neutral-200 bg-white'}"
      >
        <option value="" disabled selected={!selectedBlueprintId}>Select a blueprint...</option>
        {#each blueprints as bp}
          <option value={bp.id} selected={bp.id === selectedBlueprintId}>
            {bp.name} ({bp.status_display})
          </option>
        {/each}
      </select>
    </div>

    <!-- KPI Cards -->
    {#if activeTemplate}
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div class="rounded-xl border border-neutral-200 bg-white px-4 py-3 text-center">
          <p class="text-2xl font-bold text-neutral-900 tabular-nums">{totalPhases}</p>
          <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider mt-1">Phases</p>
        </div>
        <div class="rounded-xl border border-neutral-200 bg-white px-4 py-3 text-center">
          <p class="text-2xl font-bold text-neutral-900 tabular-nums">{totalActivities}</p>
          <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider mt-1">Activities</p>
        </div>
        <div class="rounded-xl border border-neutral-200 bg-white px-4 py-3 text-center">
          <p class="text-2xl font-bold text-neutral-900 tabular-nums">{totalTasks}</p>
          <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider mt-1">Tasks</p>
        </div>
        <div class="rounded-xl border border-neutral-200 bg-white px-4 py-3 text-center">
          <p class="text-2xl font-bold text-neutral-900 tabular-nums">{estimatedDuration}</p>
          <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider mt-1">Est. Days</p>
        </div>
      </div>
    {/if}
  </div>

  <!-- Hierarchical WBS Grid -->
  {#if loading || templateLoading}
    <div class="flex items-center justify-center py-16 text-sm text-neutral-400">Loading WBS...</div>
  {:else if !activeTemplate}
    <div class="rounded-xl border border-neutral-200 bg-white p-12 text-center text-sm text-neutral-500">
      Select a template or blueprint above to begin building the WBS.
    </div>
  {:else if activeTemplate.phases.length === 0}
    <div class="rounded-xl border border-neutral-200 bg-white p-8">
      {#if activeSource === "blueprint"}
        <div class="text-center mb-6">
          <p class="text-base font-semibold text-neutral-900">Your blueprint is empty</p>
          <p class="mt-1 text-sm text-neutral-500">Add a phase to start building the work breakdown structure.</p>
        </div>
        <div class="max-w-md mx-auto flex gap-2">
          <input
            type="text"
            bind:value={addPhaseName}
            placeholder="e.g. Site preparation"
            onkeydown={(e) => { if (e.key === 'Enter') addPhase(); }}
            class="flex-1 rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
          />
          <button
            onclick={addPhase}
            disabled={addPhaseSaving || !addPhaseName.trim()}
            class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50"
          >
            {addPhaseSaving ? "Adding..." : "Add Phase"}
          </button>
        </div>
        <p class="mt-4 text-center text-xs text-neutral-400">Tip: start with high-level phases (e.g. Pre-construction, Substructure, Superstructure, MEP, Finishing). You can add activities and tasks inside each phase later.</p>
      {:else}
        <div class="text-center text-sm text-neutral-500">
          This template has no phases. Add phases in Settings &rarr; Project Templates to build the WBS.
        </div>
      {/if}
    </div>
  {:else}
    <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-neutral-200 bg-neutral-50">
              <th class="px-5 py-3 text-left text-[10px] font-semibold text-neutral-500 uppercase tracking-wider w-24">WBS Code</th>
              <th class="px-4 py-3 text-left text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Task / Deliverable Name</th>
              <th class="px-4 py-3 text-left text-[10px] font-semibold text-neutral-500 uppercase tracking-wider w-40">Role / Skill Required</th>
              <th class="px-4 py-3 text-right text-[10px] font-semibold text-neutral-500 uppercase tracking-wider w-28">Est. Man-Hours</th>
              <th class="px-4 py-3 text-left text-[10px] font-semibold text-neutral-500 uppercase tracking-wider w-28">Dependencies</th>
              <th class="px-3 py-3 w-20"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each wbsRows as row, i (row.wbsCode + "-" + i)}
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <tr
                class="transition-colors {row.type === 'phase' ? 'bg-neutral-200/60 hover:bg-neutral-200/80' : row.type === 'activity' ? 'hover:bg-neutral-50/50 cursor-pointer' : 'hover:bg-neutral-50/30 cursor-pointer'}"
                onclick={row.type === "task" && row.taskId ? () => {
                  const task = activeTemplate?.phases
                    .flatMap((p: Phase) => p.activities)
                    .flatMap((a: Activity) => a.task_templates)
                    .find((t: TaskTemplateSummary) => t.id === row.taskId);
                  if (task) openTaskDrawer(task, row.phaseId, row.activityId);
                } : row.type === "activity" && row.activityId ? () => {
                  openEditActivity(row.phaseId, row.activityId!);
                } : undefined}>
                <!-- WBS Code -->
                <td class="px-5 py-2.5 tabular-nums">
                  <span class="rounded px-1.5 py-0.5 text-xs font-mono {row.type === 'phase' ? 'bg-neutral-900 text-white font-bold' : row.type === 'activity' ? 'bg-neutral-200 text-neutral-700 font-semibold' : 'text-neutral-400'}">
                    {row.wbsCode}
                  </span>
                </td>

                <!-- Name with indent + collapse toggle -->
                <td class="px-4 py-2.5">
                  <div class="flex items-center" style="padding-left: {row.depth * 24}px">
                    {#if row.hasChildren}
                      <button
                        type="button"
                        onclick={(e) => {
                          e.stopPropagation();
                          if (row.type === "phase") togglePhase(row.phaseId);
                          else if (row.type === "activity" && row.activityId) toggleActivity(row.activityId);
                        }}
                        class="mr-2 flex h-5 w-5 shrink-0 items-center justify-center rounded text-neutral-400 hover:bg-neutral-200 hover:text-neutral-700 transition-colors"
                        aria-label={row.collapsed ? "Expand" : "Collapse"}
                      >
                        <svg class="h-3.5 w-3.5 transition-transform {row.collapsed ? '' : 'rotate-90'}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                          <path stroke-linecap="round" stroke-linejoin="round" d="m9 6 6 6-6 6" />
                        </svg>
                      </button>
                    {:else}
                      <span class="mr-2 flex h-5 w-5 shrink-0 items-center justify-center">
                        <span class="block h-1.5 w-1.5 rounded-full {row.type === 'task' ? 'bg-neutral-300' : 'bg-transparent'}"></span>
                      </span>
                    {/if}
                    {#if row.type === "phase" && activeSource === "blueprint" && editingPhaseId === row.phaseId}
                      <input
                        bind:value={editingPhaseName}
                        onblur={saveEditPhase}
                        onkeydown={(e) => { if (e.key === 'Enter') saveEditPhase(); else if (e.key === 'Escape') cancelEditPhase(); }}
                        class="font-bold text-neutral-900 bg-white border border-neutral-300 rounded px-1.5 py-0.5 text-sm outline-none focus:ring-2 focus:ring-neutral-900"
                      />
                    {:else}
                      <button
                        type="button"
                        onclick={(e) => { e.stopPropagation(); if (row.type === 'phase' && activeSource === 'blueprint') startEditPhase(row.phaseId, row.name); }}
                        class="{row.type === 'phase' ? 'font-bold text-neutral-900' : row.type === 'activity' ? 'font-semibold text-neutral-800' : 'text-neutral-600'} text-left {row.type === 'phase' && activeSource === 'blueprint' ? 'hover:underline cursor-text' : 'cursor-default'}"
                      >
                        {row.name}
                      </button>
                    {/if}
                  </div>
                </td>

                <!-- Role -->
                <td class="px-4 py-2.5 text-xs text-neutral-500">{row.role}</td>

                <!-- Effort -->
                <td class="px-4 py-2.5 text-right text-xs tabular-nums {row.type === 'phase' ? 'font-bold text-neutral-900' : row.type === 'activity' ? 'font-semibold text-neutral-700' : 'text-neutral-500'}">
                  {row.effort}
                </td>

                <!-- Dependencies -->
                <td class="px-4 py-2.5 text-xs text-neutral-400">{row.dependencies}</td>

                <!-- Actions -->
                <td class="px-3 py-2.5">
                  <div class="flex items-center justify-end gap-1">
                    {#if row.type === "phase"}
                      <button
                        onclick={() => openAddActivity(row.phaseId)}
                        class="rounded-md bg-neutral-900 px-2.5 py-1 text-[10px] font-semibold text-white hover:bg-neutral-800 transition-colors"
                        title="Add activity to this phase"
                      >
                        + Activity
                      </button>
                      {#if activeSource === "blueprint"}
                        <button
                          onclick={(e) => { e.stopPropagation(); deletePhase(row.phaseId, row.name); }}
                          class="rounded-md border border-neutral-200 px-1.5 py-1 text-neutral-400 hover:text-red-600 hover:border-red-200 transition-colors"
                          title="Delete phase"
                        >
                          <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                            <path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166M14.5 5.625l-.55-1.5a1.875 1.875 0 0 0-1.756-1.25h-.388a1.875 1.875 0 0 0-1.756 1.25l-.55 1.5M4.5 5.625h15" />
                          </svg>
                        </button>
                      {/if}
                    {:else if row.type === "activity" && row.activityId}
                      <button
                        onclick={(e) => { e.stopPropagation(); openAddTask(row.activityId!, row.phaseId); }}
                        class="rounded-md border border-neutral-200 px-2 py-0.5 text-[10px] font-medium text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900 transition-colors"
                        title="Add task to this activity"
                      >
                        + Task
                      </button>
                      <button
                        onclick={(e) => { e.stopPropagation(); deleteActivity(row.phaseId, row.activityId!); }}
                        class="rounded p-1 text-neutral-300 hover:text-red-500 transition-colors"
                        title="Delete activity"
                      >
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                          <path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                        </svg>
                      </button>
                    {/if}
                  </div>
                </td>
              </tr>
            {/each}

            {#if wbsRows.length === 0}
              <tr>
                <td colspan="6" class="px-5 py-12 text-center text-sm text-neutral-400">
                  No activities defined yet. Click "+ Activity" on any phase to begin decomposing the WBS.
                </td>
              </tr>
            {/if}
          </tbody>
        </table>
      </div>

      <!-- Footer summary -->
      <div class="border-t border-neutral-200 bg-neutral-50 px-5 py-2.5 flex items-center justify-between text-xs text-neutral-500">
        <span>{wbsRows.length} row(s) &middot; {totalPhases} phase(s) &middot; {totalActivities} activit{totalActivities === 1 ? "y" : "ies"} &middot; {totalTasks} task(s)</span>
        <span class="tabular-nums font-semibold text-neutral-700">Total est: {estimatedDuration} days</span>
      </div>
    </div>

    {#if activeSource === "blueprint"}
      <div class="mt-4 flex gap-2">
        <input
          type="text"
          bind:value={addPhaseName}
          placeholder="Add another phase..."
          onkeydown={(e) => { if (e.key === 'Enter') addPhase(); }}
          class="flex-1 rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
        />
        <button
          onclick={addPhase}
          disabled={addPhaseSaving || !addPhaseName.trim()}
          class="rounded-lg border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50 disabled:opacity-50"
        >
          {addPhaseSaving ? "Adding..." : "+ Add Phase"}
        </button>
      </div>
    {/if}
  {/if}

  <!-- WBS Logic Flow -->
  {#if activeTemplate && activeTemplate.phases.length > 0 && !loading && !templateLoading}
    <div class="rounded-xl border border-neutral-200 bg-white p-6 overflow-x-auto">
      <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-5">WBS Decomposition Flow</h3>

      <div class="flex flex-col items-center gap-0 min-w-[600px]">
        <!-- Project Root -->
        <div class="rounded-lg border-2 border-neutral-900 bg-neutral-900 px-5 py-2.5 text-sm font-bold text-white shadow-sm">
          {activeTemplate.name}
        </div>
        <div class="w-px h-5 bg-neutral-300"></div>

        <!-- Phase branches -->
        <div class="relative w-full">
          <!-- Horizontal connector line -->
          {#if activeTemplate.phases.length > 1}
            <div class="absolute top-0 left-1/2 -translate-x-1/2 h-px bg-neutral-300" style="width: {Math.min((activeTemplate.phases.length - 1) * 220, 880)}px"></div>
          {/if}

          <div class="flex justify-center gap-6 flex-wrap">
            {#each activeTemplate.phases as phase, pi (phase.id)}
              <div class="flex flex-col items-center gap-0 min-w-[180px] max-w-[220px]">
                <!-- Vertical connector from horizontal line -->
                <div class="w-px h-4 bg-neutral-300"></div>

                <!-- Phase node -->
                <div class="w-full rounded-lg border border-neutral-400 bg-neutral-200 px-4 py-2 text-center shadow-sm">
                  <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Phase {pi + 1}</p>
                  <p class="text-xs font-bold text-neutral-900 mt-0.5 leading-tight">{phase.name}</p>
                  {#if phase.duration_days}
                    <p class="text-[10px] text-neutral-400 mt-1 tabular-nums">{phase.duration_days}d</p>
                  {/if}
                </div>

                <!-- Activities under this phase -->
                {#if phase.activities.length > 0}
                  <div class="w-px h-3 bg-neutral-200"></div>
                  <div class="flex flex-col items-center gap-1.5 w-full">
                    {#each phase.activities as activity (activity.id)}
                      <div class="w-full rounded-md border border-neutral-200 bg-white px-3 py-1.5 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
                        <div class="flex items-center gap-2">
                          {#if activity.wbs_code}
                            <span class="rounded bg-neutral-100 px-1.5 py-0.5 text-[9px] font-bold text-neutral-500 tabular-nums shrink-0">{activity.wbs_code}</span>
                          {/if}
                          <p class="text-[11px] font-semibold text-neutral-700 leading-tight truncate">{activity.name}</p>
                        </div>

                        <!-- Tasks under this activity -->
                        {#if activity.task_templates.length > 0}
                          <div class="mt-1.5 space-y-0.5 border-l-2 border-neutral-100 pl-2.5 ml-1">
                            {#each activity.task_templates.slice(0, 4) as task (task.id)}
                              <div class="flex items-center gap-1.5">
                                <span class="block h-1 w-1 rounded-full bg-neutral-300 shrink-0"></span>
                                <span class="text-[10px] text-neutral-500 truncate">{task.name}</span>
                                {#if task.estimated_effort_hours}
                                  <span class="text-[9px] text-neutral-300 tabular-nums shrink-0 ml-auto">{task.estimated_effort_hours}h</span>
                                {/if}
                              </div>
                            {/each}
                            {#if activity.task_templates.length > 4}
                              <p class="text-[9px] text-neutral-400 pl-2.5">+{activity.task_templates.length - 4} more</p>
                            {/if}
                          </div>
                        {/if}
                      </div>
                    {/each}
                  </div>
                {:else}
                  <div class="w-px h-3 bg-neutral-100"></div>
                  <p class="text-[9px] text-neutral-300 italic">No activities</p>
                {/if}
              </div>
            {/each}
          </div>
        </div>

        <!-- Legend -->
        <div class="flex items-center gap-5 mt-6 pt-4 border-t border-neutral-100 w-full justify-center">
          <span class="flex items-center gap-1.5 text-[10px] text-neutral-500">
            <span class="inline-block w-3 h-3 rounded bg-neutral-900"></span> Project
          </span>
          <span class="flex items-center gap-1.5 text-[10px] text-neutral-500">
            <span class="inline-block w-3 h-3 rounded border border-neutral-400 bg-neutral-200"></span> Phase
          </span>
          <span class="flex items-center gap-1.5 text-[10px] text-neutral-500">
            <span class="inline-block w-3 h-3 rounded border border-neutral-200 bg-white shadow-sm"></span> Activity
          </span>
          <span class="flex items-center gap-1.5 text-[10px] text-neutral-500">
            <span class="inline-block w-1.5 h-1.5 rounded-full bg-neutral-300"></span> Task
          </span>
        </div>
      </div>
    </div>
  {/if}
</div>

<!-- Task Detail Drawer -->
{#if showTaskDrawer}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm transition-opacity duration-300"
    style="opacity: {taskDrawerVisible ? 1 : 0}"
    role="button"
    tabindex="0"
    onclick={closeTaskDrawer}
    onkeydown={(event) => {
      if (event.key === "Escape" || event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        closeTaskDrawer();
      }
    }}
  ></div>
  <aside
    class="fixed inset-y-0 right-0 z-50 flex w-full max-w-xl flex-col bg-white/95 backdrop-blur-xl shadow-2xl border-l border-neutral-200/60 transition-transform duration-300"
    style="transform: translateX({taskDrawerVisible ? '0%' : '100%'})"
  >
    <!-- Header -->
    <div class="flex items-center justify-between border-b border-neutral-100 px-6 py-4">
      <div>
        <h2 class="text-base font-semibold text-neutral-900">Task Configuration</h2>
        {#if selectedTask?.reference_code}
          <p class="text-xs text-neutral-400 font-mono mt-0.5">{selectedTask.reference_code}</p>
        {/if}
      </div>
      <button onclick={closeTaskDrawer} class="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-900 transition-colors" aria-label="Close">
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- Body -->
    <div class="flex-1 overflow-y-auto px-6 py-5 space-y-5">
      <!-- Identity -->
      <section>
        <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3">Identity</h3>
        <div class="grid grid-cols-2 gap-3">
          <label class="col-span-2 text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block text-xs">Task Name</span>
            <input bind:value={taskDetailForm.name} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </label>
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block text-xs">Reference Code</span>
            <input bind:value={taskDetailForm.reference_code} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="TASK-101" />
          </label>
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block text-xs">Priority</span>
            <select bind:value={taskDetailForm.priority} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </label>
        </div>
        <label class="block mt-3 text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block text-xs">Description</span>
          <textarea bind:value={taskDetailForm.description} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none" placeholder="Scope and acceptance criteria"></textarea>
        </label>
      </section>

      <!-- Scheduling & Effort -->
      <section>
        <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3">Scheduling & Effort</h3>
        <div class="grid grid-cols-2 gap-3">
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block text-xs">Duration (days)</span>
            <input type="number" bind:value={taskDetailForm.duration_days} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="0" />
          </label>
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block text-xs">Est. Man-Hours</span>
            <input type="number" bind:value={taskDetailForm.estimated_effort_hours} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="0" />
          </label>
        </div>
        <label class="block mt-3 text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block text-xs">Predecessors</span>
          <input bind:value={taskDetailForm.predecessors} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="e.g. 1.1, 1.2 (Finish-to-Start)" />
          <p class="mt-1 text-[10px] text-neutral-400">Comma-separated WBS codes of tasks that must complete first.</p>
        </label>
      </section>

      <!-- Resources -->
      <section>
        <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3">Resources</h3>
        <div class="grid grid-cols-2 gap-3">
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block text-xs">Required Role / Skill</span>
            <input bind:value={taskDetailForm.assigned_role} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="e.g. Electrician" />
          </label>
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block text-xs">Resource Tags</span>
            <input bind:value={taskDetailForm.resource_tags} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="e.g. Roofer, Crane Operator" />
            <p class="mt-1 text-[10px] text-neutral-400">Comma-separated skill tags for resource matching.</p>
          </label>
        </div>
        <label class="block mt-3 text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block text-xs">Equipment Type</span>
          <input bind:value={taskDetailForm.equipment_type} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="e.g. Excavator, Tower Crane, Concrete Pump" />
        </label>
      </section>

      <!-- Materials & Output -->
      <section>
        <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3">Materials & Output</h3>
        <label class="block text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block text-xs">Required Materials (abstract)</span>
          <textarea bind:value={taskDetailForm.required_materials} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none" placeholder="e.g. 100m DC Cable, 40 Mounting Rails, 500kg Rebar"></textarea>
          <p class="mt-1 text-[10px] text-neutral-400">Material types and approximate quantities. Specific procurement links are made at execution time.</p>
        </label>
        <label class="block mt-3 text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block text-xs">Output Unit</span>
          <input bind:value={taskDetailForm.output_unit} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="e.g. m², linear meters, units installed, kg placed" />
          <p class="mt-1 text-[10px] text-neutral-400">The unit of measure used to track progress and productivity.</p>
        </label>
      </section>

      <!-- Milestone Toggle -->
      <section>
        <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3">Governance</h3>
        <label class="flex items-center gap-3 rounded-lg border border-neutral-200 px-4 py-3 cursor-pointer hover:bg-neutral-50 transition-colors">
          <input type="checkbox" bind:checked={taskDetailForm.is_milestone} class="rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900" />
          <div>
            <span class="text-sm font-medium text-neutral-700">Mark as Project Milestone</span>
            <p class="text-[10px] text-neutral-400 mt-0.5">This task represents a critical checkpoint that requires formal sign-off before the project can proceed.</p>
          </div>
        </label>
      </section>
    </div>

    <!-- Footer -->
    <div class="flex items-center justify-end gap-3 border-t border-neutral-100 px-6 py-4">
      <button onclick={closeTaskDrawer} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      <button
        onclick={saveTaskDetail}
        disabled={taskSaving}
        class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
      >
        {taskSaving ? "Saving..." : "Save Task"}
      </button>
    </div>
  </aside>
{/if}

<!-- Activity Modal -->
{#if showActivityModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
    <div class="relative w-full max-w-lg rounded-xl bg-white shadow-2xl p-6">
      <button
        type="button"
        onclick={() => (showActivityModal = false)}
        class="absolute top-4 right-4 rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        aria-label="Close"
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>

      <h3 class="text-base font-semibold text-neutral-900 mb-4">{editingActivityId ? "Edit Activity" : "Add Activity"}</h3>

      <form onsubmit={(e) => { e.preventDefault(); saveActivity(); }} class="space-y-4">
        <label class="block text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Activity Name</span>
          <input bind:value={activityForm.name} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="e.g. Excavation & Earthworks" />
        </label>
        <label class="block text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Description</span>
          <textarea bind:value={activityForm.description} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="Scope of this activity"></textarea>
        </label>
        <div class="grid grid-cols-3 gap-3">
          <label class="block text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Duration (days)</span>
            <input type="number" bind:value={activityForm.estimated_duration_days} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="0" />
          </label>
          <label class="block text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Effort (hours)</span>
            <input type="number" bind:value={activityForm.estimated_effort_hours} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="0" />
          </label>
          <label class="block text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">WBS Code</span>
            <input bind:value={activityForm.wbs_code} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="1.2" />
          </label>
        </div>

        <div class="flex items-center justify-end gap-3 pt-2">
          {#if isDev}
            <button type="button" onclick={devFillActivity} class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>
          {/if}
          <button
            type="button"
            onclick={() => (showActivityModal = false)}
            class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={activitySaving}
            class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
          >
            {activitySaving ? "Saving..." : editingActivityId ? "Save Activity" : "Add Activity"}
          </button>
        </div>
      </form>
    </div>
  </div>
{/if}

<!-- Add Task Modal -->
{#if showAddTaskModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
    <div class="relative w-full max-w-md rounded-xl bg-white shadow-2xl p-6">
      <button
        type="button"
        onclick={() => (showAddTaskModal = false)}
        class="absolute top-4 right-4 rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        aria-label="Close"
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>

      <h3 class="text-base font-semibold text-neutral-900 mb-4">Add Task to Activity</h3>

      <!-- Tab switcher -->
      <div class="flex rounded-lg border border-neutral-200 overflow-hidden mb-4">
        <button onclick={() => (addTaskMode = "library")} class="flex-1 px-3 py-2 text-xs font-medium transition-colors {addTaskMode === 'library' ? 'bg-neutral-900 text-white' : 'text-neutral-600 hover:bg-neutral-50'}">From Library</button>
        <button onclick={() => (addTaskMode = "custom")} class="flex-1 px-3 py-2 text-xs font-medium transition-colors {addTaskMode === 'custom' ? 'bg-neutral-900 text-white' : 'text-neutral-600 hover:bg-neutral-50'}">Create Custom</button>
      </div>

      {#if addTaskMode === "library"}
        <!-- Library picker -->
        <input bind:value={taskLibrarySearch} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="Search task templates..." />
        {#if taskLibraryLoading}
          <p class="text-center text-xs text-neutral-400 py-6">Loading library...</p>
        {:else if filteredLibrary.length === 0}
          <p class="text-center text-xs text-neutral-400 py-6">{taskLibrarySearch ? "No templates match your search." : "No task templates in the library yet."}</p>
        {:else}
          <div class="max-h-64 overflow-y-auto space-y-1">
            {#each filteredLibrary as task (task.id)}
              <button
                type="button"
                onclick={() => linkTaskTemplate(task.id)}
                disabled={addTaskSaving}
                class="w-full flex items-center justify-between gap-3 rounded-lg border border-neutral-200 px-3 py-2.5 text-left transition-colors hover:border-neutral-400 hover:bg-neutral-50 disabled:opacity-50"
              >
                <div class="min-w-0 flex-1">
                  <p class="text-sm font-medium text-neutral-900 truncate">{task.name}</p>
                  <div class="flex gap-2 mt-0.5">
                    {#if task.assigned_role}<span class="text-[10px] text-neutral-500">{task.assigned_role}</span>{/if}
                    {#if task.estimated_effort_hours}<span class="text-[10px] text-neutral-400 tabular-nums">{task.estimated_effort_hours}h</span>{/if}
                    {#if task.reference_code}<span class="text-[10px] text-neutral-400 font-mono">{task.reference_code}</span>{/if}
                  </div>
                </div>
                <span class="shrink-0 text-[10px] font-medium text-neutral-400">+ Add</span>
              </button>
            {/each}
          </div>
        {/if}
        <div class="flex justify-end mt-3">
          <button type="button" onclick={() => (showAddTaskModal = false)} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
        </div>
      {:else}
        <!-- Custom task form -->
        <form onsubmit={(e) => { e.preventDefault(); saveAddTask(); }} class="space-y-3">
          <label class="block text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block text-xs">Task Name</span>
            <input bind:value={addTaskForm.name} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="e.g. Dig Trench" />
          </label>
          <label class="block text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block text-xs">Description</span>
            <textarea bind:value={addTaskForm.description} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none" placeholder="Task scope and acceptance criteria"></textarea>
          </label>
          <div class="grid grid-cols-3 gap-3">
            <label class="text-sm font-medium text-neutral-700">
              <span class="mb-1.5 block text-xs">Required Role</span>
              <input bind:value={addTaskForm.assigned_role} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="e.g. Mason" />
            </label>
            <label class="text-sm font-medium text-neutral-700">
              <span class="mb-1.5 block text-xs">Effort (hours)</span>
              <input type="number" bind:value={addTaskForm.estimated_effort_hours} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="0" />
            </label>
            <label class="text-sm font-medium text-neutral-700">
              <span class="mb-1.5 block text-xs">Reference Code</span>
              <input bind:value={addTaskForm.reference_code} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="TASK-101" />
            </label>
          </div>

          <div class="flex items-center justify-end gap-3 pt-2">
            {#if isDev}
              <button type="button" onclick={() => {
                const names = ["Dig Trench", "Soil Removal", "Backfill & Compact", "Install Rebar Cage", "Pour Concrete", "Cure & Inspect", "Apply Waterproofing", "Survey & Mark Out"];
                const roles = ["Machine Operator", "Labourer", "Civil Foreman", "Steel Fixer", "Concrete Worker", "Site Engineer", "Waterproofing Tech", "Surveyor"];
                const idx = Math.floor(Math.random() * names.length);
                addTaskForm.name = names[idx];
                addTaskForm.description = `Standard procedure for ${names[idx].toLowerCase()}. Follow method statement and safety protocols.`;
                addTaskForm.assigned_role = roles[idx];
                addTaskForm.estimated_effort_hours = String(Math.floor(Math.random() * 16) + 2);
                addTaskForm.reference_code = `TSK-${Math.floor(Math.random() * 900) + 100}`;
              }} class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>
            {/if}
            <button type="button" onclick={() => (showAddTaskModal = false)} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
            <button type="submit" disabled={addTaskSaving} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50">
              {addTaskSaving ? "Saving..." : "Add Task"}
            </button>
          </div>
        </form>
      {/if}
    </div>
  </div>
{/if}

<!-- Save as Master Template Modal -->
{#if showSaveTemplateModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
    <div class="relative w-full max-w-md rounded-xl bg-white shadow-2xl p-6">
      <button
        type="button"
        onclick={() => (showSaveTemplateModal = false)}
        class="absolute top-4 right-4 rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        aria-label="Close"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/></svg>
      </button>
      <h3 class="text-lg font-semibold text-neutral-900 mb-1">Save as Master Template</h3>
      <p class="text-sm text-neutral-500 mb-5">Create a reusable project template from this blueprint's WBS structure.</p>
      <form onsubmit={(e) => { e.preventDefault(); void saveAsMasterTemplate(); }}>
        <div class="space-y-4">
          <div>
            <label for="tmpl-name" class="block text-sm font-medium text-neutral-700 mb-1">Template Name</label>
            <input
              id="tmpl-name"
              type="text"
              bind:value={saveTemplateName}
              placeholder="e.g. Standard Residential Build"
              required
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-900 focus:ring-1 focus:ring-neutral-900 focus:outline-none"
            />
          </div>
          <div>
            <label for="tmpl-type" class="block text-sm font-medium text-neutral-700 mb-1">Template Type</label>
            <select
              id="tmpl-type"
              bind:value={saveTemplateType}
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-900 focus:ring-1 focus:ring-neutral-900 focus:outline-none"
            >
              <option value="residential">Residential</option>
              <option value="mixed_use">Mixed-Use</option>
              <option value="commercial">Commercial</option>
              <option value="infrastructure">Infrastructure</option>
            </select>
          </div>
          {#if activeTemplate}
            <div class="rounded-lg bg-neutral-50 px-4 py-3 text-sm text-neutral-600">
              This will copy <span class="font-medium text-neutral-900">{totalPhases}</span> phases,
              <span class="font-medium text-neutral-900">{totalActivities}</span> activities, and
              <span class="font-medium text-neutral-900">{totalTasks}</span> tasks into the new template.
            </div>
          {/if}
        </div>
        <div class="mt-6 flex justify-end gap-3">
          <button type="button" onclick={() => (showSaveTemplateModal = false)} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
          <button type="submit" disabled={saveTemplateSaving || !saveTemplateName.trim()} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50">
            {saveTemplateSaving ? "Saving..." : "Create Template"}
          </button>
        </div>
      </form>
    </div>
  </div>
{/if}

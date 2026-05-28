<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    PaginatedResponse,
    ProjectListItem,
    ProjectMilestone,
    ProjectPhase,
    ProjectPhaseStatus,
    ProjectTimelineData,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  type MilestoneFilter = "" | "completed" | "pending" | "overdue" | "due_30";

  type PhaseRow = {
    key: string;
    projectId: number;
    projectName: string;
    phaseId: number;
    phaseName: string;
    status: ProjectPhaseStatus;
    baselineStartDate: string | null;
    baselineEndDate: string | null;
    revisedStartDate: string | null;
    revisedEndDate: string | null;
    slackDays: number | null;
    isCriticalPath: boolean;
    plannedStartDate: string | null;
    plannedEndDate: string | null;
    actualStartDate: string | null;
    actualEndDate: string | null;
    milestoneCount: number;
    completedMilestoneCount: number;
  };

  type MilestoneRow = {
    key: string;
    projectId: number;
    projectName: string;
    phaseId: number;
    phaseName: string;
    phaseStatus: ProjectPhaseStatus;
    milestoneId: number;
    milestoneName: string;
    targetDate: string | null;
    baselineTargetDate: string | null;
    revisedTargetDate: string | null;
    scheduleVarianceDays: number | null;
    completedDate: string | null;
    isCompleted: boolean;
    approvalRequired: boolean;
    approvalStatus: "not_required" | "pending" | "approved" | "rejected";
    daysToTarget: number | null;
  };

  const phaseStatusLabel: Record<ProjectPhaseStatus, string> = {
    not_started: "Not Started",
    in_progress: "In Progress",
    completed: "Completed",
    skipped: "Skipped",
  };

  const phaseStatusBadge: Record<ProjectPhaseStatus, string> = {
    not_started: "bg-neutral-100 text-neutral-700 border-neutral-200",
    in_progress: "bg-blue-50 text-blue-700 border-blue-100",
    completed: "bg-emerald-50 text-emerald-700 border-emerald-100",
    skipped: "bg-amber-50 text-amber-700 border-amber-100",
  };

  let loading = $state(true);
  let projects = $state<ProjectListItem[]>([]);
  let phaseRows = $state<PhaseRow[]>([]);
  let milestoneRows = $state<MilestoneRow[]>([]);

  let searchInput = $state("");
  let searchQuery = $state("");
  let projectFilter = $state("");
  let phaseStatusFilter = $state<"" | ProjectPhaseStatus>("");
  let milestoneFilter = $state<MilestoneFilter>("");

  let phasePage = $state(1);
  let phasePageSize = $state(10);
  let milestonePage = $state(1);
  let milestonePageSize = $state(10);
  let viewMode = $state<"table" | "kanban" | "gantt">("table");
  let approvalBusy = $state<Record<string, boolean>>({});
  let actionLoading = $state(false);
  let actionSaving = $state(false);

  let phaseCommentingRow = $state<PhaseRow | null>(null);
  let phaseCommentText = $state("");
  let milestoneCommentingRow = $state<MilestoneRow | null>(null);
  let milestoneCommentText = $state("");

  let editingPhaseRow = $state<PhaseRow | null>(null);
  let editingMilestoneRow = $state<MilestoneRow | null>(null);
  let editingMilestoneCompletedDate = $state<string | null>(null);

  let editPhaseForm = $state<{
    name: string;
    status: ProjectPhaseStatus;
    planned_start_date: string;
    planned_end_date: string;
  }>({
    name: "",
    status: "not_started",
    planned_start_date: "",
    planned_end_date: "",
  });

  let editMilestoneForm = $state<{
    name: string;
    target_date: string;
    is_completed: boolean;
  }>({
    name: "",
    target_date: "",
    is_completed: false,
  });

  let fetchToken = 0;
  let searchTimeout: ReturnType<typeof setTimeout> | undefined;

  function todayIsoDate(): string {
    return new Date().toISOString().slice(0, 10);
  }

  function fmtDate(value: string | null): string {
    if (!value) return "--";
    return new Date(value).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  function daysUntil(value: string | null): number | null {
    if (!value) return null;
    const now = new Date();
    now.setHours(0, 0, 0, 0);

    const target = new Date(value);
    target.setHours(0, 0, 0, 0);

    if (Number.isNaN(target.getTime())) return null;

    const diff = target.getTime() - now.getTime();
    return Math.ceil(diff / (1000 * 60 * 60 * 24));
  }

  function parseDateMillis(value: string | null): number {
    if (!value) return Number.MAX_SAFE_INTEGER;
    const parsed = new Date(value).getTime();
    return Number.isNaN(parsed) ? Number.MAX_SAFE_INTEGER : parsed;
  }

  function milestoneState(row: MilestoneRow): MilestoneFilter {
    if (row.isCompleted) return "completed";
    if (row.daysToTarget !== null && row.daysToTarget < 0) return "overdue";
    if (row.daysToTarget !== null && row.daysToTarget <= 30) return "due_30";
    return "pending";
  }

  function milestoneStateLabel(row: MilestoneRow): string {
    const state = milestoneState(row);
    if (state === "completed") return "Completed";
    if (state === "overdue") return "Overdue";
    if (state === "due_30") return "Due <= 30d";
    return "Pending";
  }

  function milestoneStateClass(row: MilestoneRow): string {
    const state = milestoneState(row);
    if (state === "completed") return "bg-emerald-50 text-emerald-700 border-emerald-100";
    if (state === "overdue") return "bg-rose-50 text-rose-700 border-rose-100";
    if (state === "due_30") return "bg-amber-50 text-amber-700 border-amber-100";
    return "bg-neutral-100 text-neutral-700 border-neutral-200";
  }

  function approvalStatusLabel(status: MilestoneRow["approvalStatus"]): string {
    if (status === "approved") return "Approved";
    if (status === "rejected") return "Rejected";
    if (status === "pending") return "Pending";
    return "Not Required";
  }

  function approvalStatusClass(status: MilestoneRow["approvalStatus"]): string {
    if (status === "approved") return "bg-emerald-50 text-emerald-700 border-emerald-100";
    if (status === "rejected") return "bg-rose-50 text-rose-700 border-rose-100";
    if (status === "pending") return "bg-amber-50 text-amber-700 border-amber-100";
    return "bg-neutral-100 text-neutral-600 border-neutral-200";
  }

  function milestoneActionKey(row: MilestoneRow): string {
    return `${row.projectId}-${row.phaseId}-${row.milestoneId}`;
  }

  function phaseProgress(row: PhaseRow): number {
    if (row.milestoneCount === 0) return 0;
    return Math.round((row.completedMilestoneCount / row.milestoneCount) * 100);
  }

  function resetFilters() {
    searchInput = "";
    searchQuery = "";
    projectFilter = "";
    phaseStatusFilter = "";
    milestoneFilter = "";
    phasePage = 1;
    milestonePage = 1;
  }

  function onSearchInput(event: Event) {
    searchInput = (event.target as HTMLInputElement).value;
    if (searchTimeout) clearTimeout(searchTimeout);

    searchTimeout = setTimeout(() => {
      searchQuery = searchInput.trim().toLowerCase();
      phasePage = 1;
      milestonePage = 1;
    }, 250);
  }

  async function fetchAllProjects(): Promise<ProjectListItem[]> {
    const rows: ProjectListItem[] = [];
    let page = 1;
    const pageSize = 200;

    while (true) {
      const res = await api.get<PaginatedResponse<ProjectListItem>>("/projects/", {
        page: String(page),
        page_size: String(pageSize),
        ordering: "name",
      });

      rows.push(...res.results);

      if (!res.next || res.results.length === 0) break;
      page += 1;
    }

    return rows;
  }

  async function fetchTimelineSnapshots(projectList: ProjectListItem[]): Promise<ProjectTimelineData[]> {
    const timelines: ProjectTimelineData[] = [];
    const concurrency = 8;
    let failed = 0;

    for (let idx = 0; idx < projectList.length; idx += concurrency) {
      const chunk = projectList.slice(idx, idx + concurrency);
      const chunkRows = await Promise.all(
        chunk.map(async (project) => {
          try {
            return await api.get<ProjectTimelineData>(`/projects/${project.id}/timeline/`);
          } catch {
            failed += 1;
            return null;
          }
        }),
      );

      for (const item of chunkRows) {
        if (item) timelines.push(item);
      }
    }

    if (failed > 0) {
      const suffix = failed === 1 ? "project timeline failed" : "project timelines failed";
      toast.error("Partial data", `${failed} ${suffix} to load.`);
    }

    return timelines;
  }

  function buildRows(
    projectList: ProjectListItem[],
    timelines: ProjectTimelineData[],
  ): { phases: PhaseRow[]; milestones: MilestoneRow[] } {
    const projectNames = new Map(projectList.map((project) => [project.id, project.name]));
    const phases: PhaseRow[] = [];
    const milestones: MilestoneRow[] = [];

    for (const timeline of timelines) {
      const projectId = timeline.project.id;
      const projectName = projectNames.get(projectId) ?? timeline.project.name;

      for (const phase of timeline.phases) {
        const completedMilestoneCount = phase.milestones.filter((milestone) => milestone.is_completed).length;

        phases.push({
          key: `${projectId}-${phase.id}`,
          projectId,
          projectName,
          phaseId: phase.id,
          phaseName: phase.name,
          status: phase.status,
          baselineStartDate: phase.baseline_start_date,
          baselineEndDate: phase.baseline_end_date,
          revisedStartDate: phase.revised_start_date,
          revisedEndDate: phase.revised_end_date,
          slackDays: phase.slack_days,
          isCriticalPath: phase.is_critical_path,
          plannedStartDate: phase.planned_start_date,
          plannedEndDate: phase.planned_end_date,
          actualStartDate: phase.actual_start_date,
          actualEndDate: phase.actual_end_date,
          milestoneCount: phase.milestones.length,
          completedMilestoneCount,
        });

        for (const milestone of phase.milestones) {
          const baselineTarget = milestone.baseline_target_date ?? milestone.target_date;
          const revisedTarget = milestone.revised_target_date ?? milestone.target_date;
          milestones.push({
            key: `${projectId}-${phase.id}-${milestone.id}`,
            projectId,
            projectName,
            phaseId: phase.id,
            phaseName: phase.name,
            phaseStatus: phase.status,
            milestoneId: milestone.id,
            milestoneName: milestone.name,
            targetDate: milestone.target_date,
            baselineTargetDate: milestone.baseline_target_date,
            revisedTargetDate: milestone.revised_target_date,
            scheduleVarianceDays:
              baselineTarget && revisedTarget
                ? Math.ceil((new Date(revisedTarget).getTime() - new Date(baselineTarget).getTime()) / (1000 * 60 * 60 * 24))
                : null,
            completedDate: milestone.completed_date,
            isCompleted: milestone.is_completed,
            approvalRequired: milestone.approval_required,
            approvalStatus: milestone.approval_status,
            daysToTarget: daysUntil(milestone.target_date),
          });
        }
      }
    }

    phases.sort((a, b) => {
      if (a.projectName !== b.projectName) return a.projectName.localeCompare(b.projectName);
      return parseDateMillis(a.plannedEndDate) - parseDateMillis(b.plannedEndDate);
    });

    milestones.sort((a, b) => {
      if (a.isCompleted !== b.isCompleted) return a.isCompleted ? 1 : -1;
      const dayDelta = (a.daysToTarget ?? Number.MAX_SAFE_INTEGER) - (b.daysToTarget ?? Number.MAX_SAFE_INTEGER);
      if (dayDelta !== 0) return dayDelta;
      if (a.projectName !== b.projectName) return a.projectName.localeCompare(b.projectName);
      return a.phaseName.localeCompare(b.phaseName);
    });

    return { phases, milestones };
  }

  async function loadPageData() {
    loading = true;
    const token = ++fetchToken;

    try {
      const projectList = await fetchAllProjects();
      const timelines = await fetchTimelineSnapshots(projectList);
      if (token !== fetchToken) return;

      const rows = buildRows(projectList, timelines);

      projects = projectList;
      phaseRows = rows.phases;
      milestoneRows = rows.milestones;
    } catch {
      if (token !== fetchToken) return;
      projects = [];
      phaseRows = [];
      milestoneRows = [];
      toast.error("Load failed", "Could not load phases and milestones.");
    } finally {
      if (token === fetchToken) loading = false;
    }
  }

  async function submitMilestoneApproval(row: MilestoneRow) {
    const actionKey = milestoneActionKey(row);
    approvalBusy[actionKey] = true;
    try {
      await api.post(
        `/projects/${row.projectId}/phases/${row.phaseId}/milestones/${row.milestoneId}/submit-approval/`,
        {},
      );
      toast.success("Submitted", "Milestone approval workflow has been started.");
      await loadPageData();
    } catch {
      toast.error("Submit failed", "Could not submit milestone for approval.");
    } finally {
      approvalBusy[actionKey] = false;
    }
  }

  async function decideMilestoneApproval(row: MilestoneRow, decision: "approved" | "rejected") {
    const actionKey = milestoneActionKey(row);
    approvalBusy[actionKey] = true;
    try {
      await api.post(
        `/projects/${row.projectId}/phases/${row.phaseId}/milestones/${row.milestoneId}/decide-approval/`,
        { decision },
      );
      toast.success(
        decision === "approved" ? "Approved" : "Rejected",
        `Milestone marked as ${decision}.`,
      );
      await loadPageData();
    } catch {
      toast.error("Decision failed", "Could not record approval decision.");
    } finally {
      approvalBusy[actionKey] = false;
    }
  }

  async function openPhaseComments(row: PhaseRow) {
    actionLoading = true;
    try {
      const phase = await api.get<ProjectPhase>(`/projects/${row.projectId}/phases/${row.phaseId}/`);
      phaseCommentText = phase.description ?? "";
      phaseCommentingRow = row;
    } catch (err) {
      toast.error("Load failed", "Could not load phase comments.");
    } finally {
      actionLoading = false;
    }
  }

  async function savePhaseComments() {
    if (!phaseCommentingRow) return;

    actionSaving = true;
    try {
      await api.patch(
        `/projects/${phaseCommentingRow.projectId}/phases/${phaseCommentingRow.phaseId}/`,
        { description: phaseCommentText },
      );
      toast.success("Comments saved", "Phase comments updated.");
      phaseCommentingRow = null;
      phaseCommentText = "";
      await loadPageData();
    } catch (err) {
      toast.error("Save failed", "Could not save phase comments.");
    } finally {
      actionSaving = false;
    }
  }

  async function openMilestoneComments(row: MilestoneRow) {
    actionLoading = true;
    try {
      const milestone = await api.get<ProjectMilestone>(
        `/projects/${row.projectId}/phases/${row.phaseId}/milestones/${row.milestoneId}/`,
      );
      milestoneCommentText = milestone.description ?? "";
      milestoneCommentingRow = row;
    } catch (err) {
      toast.error("Load failed", "Could not load milestone comments.");
    } finally {
      actionLoading = false;
    }
  }

  async function saveMilestoneComments() {
    if (!milestoneCommentingRow) return;

    actionSaving = true;
    try {
      await api.patch(
        `/projects/${milestoneCommentingRow.projectId}/phases/${milestoneCommentingRow.phaseId}/milestones/${milestoneCommentingRow.milestoneId}/`,
        { description: milestoneCommentText },
      );
      toast.success("Comments saved", "Milestone comments updated.");
      milestoneCommentingRow = null;
      milestoneCommentText = "";
      await loadPageData();
    } catch (err) {
      toast.error("Save failed", "Could not save milestone comments.");
    } finally {
      actionSaving = false;
    }
  }

  async function openPhaseEdit(row: PhaseRow) {
    actionLoading = true;
    try {
      const phase = await api.get<ProjectPhase>(`/projects/${row.projectId}/phases/${row.phaseId}/`);
      editPhaseForm = {
        name: phase.name,
        status: phase.status,
        planned_start_date: phase.planned_start_date ?? "",
        planned_end_date: phase.planned_end_date ?? "",
      };
      editingPhaseRow = row;
    } catch (err) {
      toast.error("Load failed", "Could not load phase details.");
    } finally {
      actionLoading = false;
    }
  }

  async function savePhaseEdit() {
    if (!editingPhaseRow) return;
    if (!editPhaseForm.name.trim()) {
      toast.error("Validation failed", "Phase name is required.");
      return;
    }

    actionSaving = true;
    try {
      await api.patch(`/projects/${editingPhaseRow.projectId}/phases/${editingPhaseRow.phaseId}/`, {
        name: editPhaseForm.name.trim(),
        status: editPhaseForm.status,
        planned_start_date: editPhaseForm.planned_start_date || null,
        planned_end_date: editPhaseForm.planned_end_date || null,
      });
      toast.success("Phase updated", "Phase changes saved.");
      editingPhaseRow = null;
      await loadPageData();
    } catch (err) {
      toast.error("Save failed", "Could not update phase.");
    } finally {
      actionSaving = false;
    }
  }

  async function deletePhase(row: PhaseRow) {
    if (!confirm(`Delete phase "${row.phaseName}"?`)) return;

    actionSaving = true;
    try {
      await api.delete(`/projects/${row.projectId}/phases/${row.phaseId}/`);
      toast.success("Phase deleted", "The phase has been removed.");
      await loadPageData();
    } catch (err) {
      toast.error("Delete failed", "Could not delete phase.");
    } finally {
      actionSaving = false;
    }
  }

  async function openMilestoneEdit(row: MilestoneRow) {
    actionLoading = true;
    try {
      const milestone = await api.get<ProjectMilestone>(
        `/projects/${row.projectId}/phases/${row.phaseId}/milestones/${row.milestoneId}/`,
      );
      editMilestoneForm = {
        name: milestone.name,
        target_date: milestone.target_date ?? "",
        is_completed: milestone.is_completed,
      };
      editingMilestoneCompletedDate = milestone.completed_date;
      editingMilestoneRow = row;
    } catch (err) {
      toast.error("Load failed", "Could not load milestone details.");
    } finally {
      actionLoading = false;
    }
  }

  async function saveMilestoneEdit() {
    if (!editingMilestoneRow) return;
    if (!editMilestoneForm.name.trim()) {
      toast.error("Validation failed", "Milestone name is required.");
      return;
    }

    const completedDate = editMilestoneForm.is_completed
      ? editingMilestoneCompletedDate || todayIsoDate()
      : null;

    actionSaving = true;
    try {
      await api.patch(
        `/projects/${editingMilestoneRow.projectId}/phases/${editingMilestoneRow.phaseId}/milestones/${editingMilestoneRow.milestoneId}/`,
        {
          name: editMilestoneForm.name.trim(),
          target_date: editMilestoneForm.target_date || null,
          is_completed: editMilestoneForm.is_completed,
          completed_date: completedDate,
        },
      );
      toast.success("Milestone updated", "Milestone changes saved.");
      editingMilestoneRow = null;
      editingMilestoneCompletedDate = null;
      await loadPageData();
    } catch (err) {
      toast.error("Save failed", "Could not update milestone.");
    } finally {
      actionSaving = false;
    }
  }

  async function deleteMilestone(row: MilestoneRow) {
    if (!confirm(`Delete milestone "${row.milestoneName}"?`)) return;

    actionSaving = true;
    try {
      await api.delete(`/projects/${row.projectId}/phases/${row.phaseId}/milestones/${row.milestoneId}/`);
      toast.success("Milestone deleted", "The milestone has been removed.");
      await loadPageData();
    } catch (err) {
      toast.error("Delete failed", "Could not delete milestone.");
    } finally {
      actionSaving = false;
    }
  }

  const projectOptions = $derived.by(() => {
    return [...projects].sort((a, b) => a.name.localeCompare(b.name));
  });

  const filteredPhases = $derived.by(() => {
    return phaseRows.filter((row) => {
      if (projectFilter && String(row.projectId) !== projectFilter) return false;
      if (phaseStatusFilter && row.status !== phaseStatusFilter) return false;
      if (!searchQuery) return true;

      const haystack = `${row.projectName} ${row.phaseName}`.toLowerCase();
      return haystack.includes(searchQuery);
    });
  });

  const filteredMilestones = $derived.by(() => {
    return milestoneRows.filter((row) => {
      if (projectFilter && String(row.projectId) !== projectFilter) return false;
      if (phaseStatusFilter && row.phaseStatus !== phaseStatusFilter) return false;
      if (milestoneFilter && milestoneState(row) !== milestoneFilter) return false;

      if (!searchQuery) return true;

      const haystack = `${row.projectName} ${row.phaseName} ${row.milestoneName}`.toLowerCase();
      return haystack.includes(searchQuery);
    });
  });

  const hasFilters = $derived(
    Boolean(searchQuery || projectFilter || phaseStatusFilter || milestoneFilter),
  );

  const totalPhases = $derived(phaseRows.length);
  const completedPhases = $derived(phaseRows.filter((row) => row.status === "completed").length);

  const totalMilestones = $derived(milestoneRows.length);
  const completedMilestones = $derived(milestoneRows.filter((row) => row.isCompleted).length);
  const overdueMilestones = $derived(
    milestoneRows.filter((row) => !row.isCompleted && row.daysToTarget !== null && row.daysToTarget < 0).length,
  );
  const dueSoonMilestones = $derived(
    milestoneRows.filter(
      (row) => !row.isCompleted && row.daysToTarget !== null && row.daysToTarget >= 0 && row.daysToTarget <= 30,
    ).length,
  );
  const criticalPathPhases = $derived(
    phaseRows.filter((row) => row.isCriticalPath).length,
  );

  const kanbanColumns = $derived.by(() => {
    const columns: Record<MilestoneFilter, MilestoneRow[]> = {
      "": [],
      completed: [],
      pending: [],
      overdue: [],
      due_30: [],
    };
    for (const row of filteredMilestones) {
      columns[milestoneState(row)].push(row);
    }
    return columns;
  });

  function safeDateMillis(value: string | null): number | null {
    if (!value) return null;
    const millis = new Date(value).getTime();
    return Number.isNaN(millis) ? null : millis;
  }

  const ganttRange = $derived.by(() => {
    const millis: number[] = [];
    for (const row of filteredPhases) {
      for (const value of [
        row.baselineStartDate,
        row.baselineEndDate,
        row.revisedStartDate,
        row.revisedEndDate,
        row.plannedStartDate,
        row.plannedEndDate,
        row.actualStartDate,
        row.actualEndDate,
      ]) {
        const parsed = safeDateMillis(value);
        if (parsed !== null) millis.push(parsed);
      }
    }
    if (millis.length === 0) return { min: Date.now(), max: Date.now() + 86400000 };
    return { min: Math.min(...millis), max: Math.max(...millis) };
  });

  function ganttLeft(value: string | null): number {
    const point = safeDateMillis(value);
    const span = Math.max(1, ganttRange.max - ganttRange.min);
    if (point === null) return 0;
    return ((point - ganttRange.min) / span) * 100;
  }

  function ganttWidth(start: string | null, end: string | null): number {
    const startPoint = safeDateMillis(start);
    const endPoint = safeDateMillis(end ?? start);
    const span = Math.max(1, ganttRange.max - ganttRange.min);
    if (startPoint === null || endPoint === null) return 0;
    return Math.max(1.5, ((Math.max(endPoint, startPoint) - startPoint) / span) * 100);
  }

  const phaseTotalPages = $derived(Math.max(1, Math.ceil(filteredPhases.length / phasePageSize)));
  const milestoneTotalPages = $derived(Math.max(1, Math.ceil(filteredMilestones.length / milestonePageSize)));

  const phaseStart = $derived(filteredPhases.length === 0 ? 0 : (phasePage - 1) * phasePageSize + 1);
  const phaseEnd = $derived(Math.min(phasePage * phasePageSize, filteredPhases.length));
  const milestoneStart = $derived(filteredMilestones.length === 0 ? 0 : (milestonePage - 1) * milestonePageSize + 1);
  const milestoneEnd = $derived(Math.min(milestonePage * milestonePageSize, filteredMilestones.length));

  const phasePageRows = $derived(
    filteredPhases.slice((phasePage - 1) * phasePageSize, phasePage * phasePageSize),
  );

  const milestonePageRows = $derived(
    filteredMilestones.slice((milestonePage - 1) * milestonePageSize, milestonePage * milestonePageSize),
  );

  $effect(() => {
    void projectFilter;
    void phaseStatusFilter;
    void milestoneFilter;
    void searchQuery;

    phasePage = 1;
    milestonePage = 1;
  });

  $effect(() => {
    void phaseTotalPages;
    if (phasePage > phaseTotalPages) phasePage = phaseTotalPages;
  });

  $effect(() => {
    void milestoneTotalPages;
    if (milestonePage > milestoneTotalPages) milestonePage = milestoneTotalPages;
  });

  $effect(() => {
    loadPageData();
  });
</script>

<div class="space-y-6">
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-700">Projects</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-900">Phases &amp; Milestones</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Cross-project tracker for execution phases, milestone health, and delivery timing.
      </p>
    </div>

    <button
      onclick={() => loadPageData()}
      class="rounded-lg border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
    >
      Refresh
    </button>
  </div>

  <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
    <div class="border-b border-neutral-200 bg-linear-to-r from-neutral-50 via-white to-neutral-50 p-4 sm:p-5">
      <div class="grid grid-cols-1 gap-3 xl:grid-cols-4">
        <input
          type="text"
          placeholder="Search project, phase, milestone..."
          value={searchInput}
          oninput={onSearchInput}
          class="xl:col-span-2 rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
        />

        <select
          bind:value={projectFilter}
          class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
        >
          <option value="">All Projects</option>
          {#each projectOptions as project}
            <option value={String(project.id)}>{project.name}</option>
          {/each}
        </select>

        <select
          bind:value={phaseStatusFilter}
          class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
        >
          <option value="">All Phase Statuses</option>
          <option value="not_started">Not Started</option>
          <option value="in_progress">In Progress</option>
          <option value="completed">Completed</option>
          <option value="skipped">Skipped</option>
        </select>
      </div>

      <div class="mt-3 flex flex-wrap items-center gap-2">
        <select
          bind:value={milestoneFilter}
          class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
        >
          <option value="">All Milestones</option>
          <option value="pending">Pending</option>
          <option value="due_30">Due in 30 Days</option>
          <option value="overdue">Overdue</option>
          <option value="completed">Completed</option>
        </select>

        <select
          value={String(phasePageSize)}
          onchange={(event) => {
            phasePageSize = Number((event.target as HTMLSelectElement).value);
            phasePage = 1;
          }}
          class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
        >
          <option value="10">10 phases / page</option>
          <option value="20">20 phases / page</option>
          <option value="50">50 phases / page</option>
        </select>

        <select
          value={String(milestonePageSize)}
          onchange={(event) => {
            milestonePageSize = Number((event.target as HTMLSelectElement).value);
            milestonePage = 1;
          }}
          class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
        >
          <option value="10">10 milestones / page</option>
          <option value="20">20 milestones / page</option>
          <option value="50">50 milestones / page</option>
        </select>

        {#if hasFilters}
          <button
            onclick={resetFilters}
            class="rounded-lg border border-neutral-200 px-3 py-2 text-sm font-medium text-neutral-600 hover:bg-neutral-50"
          >
            Reset Filters
          </button>
        {/if}

        <div class="ml-auto inline-flex rounded-lg border border-neutral-200 bg-white p-1">
          <button
            onclick={() => (viewMode = "table")}
            class="rounded-md px-3 py-1.5 text-xs font-semibold uppercase tracking-wider {viewMode === 'table' ? 'bg-neutral-900 text-white' : 'text-neutral-600 hover:bg-neutral-50'}"
          >
            Table
          </button>
          <button
            onclick={() => (viewMode = "kanban")}
            class="rounded-md px-3 py-1.5 text-xs font-semibold uppercase tracking-wider {viewMode === 'kanban' ? 'bg-neutral-900 text-white' : 'text-neutral-600 hover:bg-neutral-50'}"
          >
            Kanban
          </button>
          <button
            onclick={() => (viewMode = "gantt")}
            class="rounded-md px-3 py-1.5 text-xs font-semibold uppercase tracking-wider {viewMode === 'gantt' ? 'bg-neutral-900 text-white' : 'text-neutral-600 hover:bg-neutral-50'}"
          >
            Gantt
          </button>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-2 gap-4 p-4 sm:grid-cols-3 xl:grid-cols-7">
      <div class="rounded-xl border border-neutral-200 border-t-4 border-t-indigo-500 bg-white p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Total Phases</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{totalPhases}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 border-t-4 border-t-emerald-500 bg-white p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Completed Phases</p>
        <p class="mt-1 text-xl font-bold text-emerald-600 tabular-nums">{completedPhases}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 border-t-4 border-t-sky-500 bg-white p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Total Milestones</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{totalMilestones}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 border-t-4 border-t-teal-500 bg-white p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Completed Milestones</p>
        <p class="mt-1 text-xl font-bold text-teal-600 tabular-nums">{completedMilestones}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 border-t-4 border-t-rose-500 bg-white p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Overdue Milestones</p>
        <p class="mt-1 text-xl font-bold text-rose-600 tabular-nums">{overdueMilestones}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 border-t-4 border-t-amber-500 bg-white p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Due in 30 Days</p>
        <p class="mt-1 text-xl font-bold text-amber-600 tabular-nums">{dueSoonMilestones}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 border-t-4 border-t-fuchsia-500 bg-white p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Critical Path Phases</p>
        <p class="mt-1 text-xl font-bold text-fuchsia-700 tabular-nums">{criticalPathPhases}</p>
      </div>
    </div>
  </section>

  {#if loading}
    <div class="flex items-center justify-center py-20">
      <div class="h-7 w-7 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
    </div>
  {:else}
    {#if viewMode === "table"}
      <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
        <div class="flex items-center justify-between border-b border-neutral-100 px-5 py-4">
          <div>
            <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Phase Register</h2>
            <p class="mt-0.5 text-xs text-neutral-500">Showing {phaseStart}-{phaseEnd} of {filteredPhases.length}</p>
          </div>
        </div>

        {#if filteredPhases.length === 0}
          <div class="py-16 text-center text-sm text-neutral-400">No phases found for the current filter set.</div>
        {:else}
          <div class="overflow-x-auto">
            <table class="w-full min-w-[1220px] text-sm">
              <thead>
                <tr class="border-b border-neutral-100 bg-neutral-50/80">
                  <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Project</th>
                  <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Phase</th>
                  <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Status</th>
                  <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Milestones</th>
                  <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Baseline vs Revised</th>
                  <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Critical Path</th>
                  <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Progress</th>
                  <th class="px-5 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Action</th>
                </tr>
              </thead>

              <tbody class="divide-y divide-neutral-100">
                {#each phasePageRows as row (row.key)}
                  {@const progress = phaseProgress(row)}
                  <tr class="bg-white hover:bg-neutral-50 transition-colors">
                    <td class="px-5 py-4 text-neutral-700">{row.projectName}</td>
                    <td class="px-5 py-4">
                      <p class="font-medium text-neutral-900">{row.phaseName}</p>
                      <p class="mt-0.5 text-xs text-neutral-500">ID: {row.phaseId}</p>
                    </td>
                    <td class="px-5 py-4">
                      <span class="inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold {phaseStatusBadge[row.status]}">
                        {phaseStatusLabel[row.status]}
                      </span>
                    </td>
                    <td class="px-5 py-4 text-neutral-700 tabular-nums">
                      {row.completedMilestoneCount}/{row.milestoneCount}
                    </td>
                    <td class="px-5 py-4 text-neutral-600">
                      <p>{fmtDate(row.baselineStartDate)} to {fmtDate(row.baselineEndDate)}</p>
                      <p class="mt-0.5 text-xs text-neutral-400">rev {fmtDate(row.revisedStartDate)} to {fmtDate(row.revisedEndDate)}</p>
                    </td>
                    <td class="px-5 py-4">
                      {#if row.isCriticalPath}
                        <span class="inline-flex items-center rounded-full border border-fuchsia-200 bg-fuchsia-50 px-2.5 py-1 text-xs font-semibold text-fuchsia-700">
                          Critical
                        </span>
                      {:else}
                        <span class="inline-flex items-center rounded-full border border-neutral-200 bg-neutral-100 px-2.5 py-1 text-xs font-medium text-neutral-600">
                          Slack {row.slackDays ?? "--"}d
                        </span>
                      {/if}
                    </td>
                    <td class="px-5 py-4">
                      <div class="flex items-center gap-2">
                        <div class="h-2 w-24 overflow-hidden rounded-full bg-neutral-100">
                          <div
                            class="h-2 rounded-full {progress >= 80 ? 'bg-emerald-500' : progress >= 40 ? 'bg-blue-600' : 'bg-amber-500'}"
                            style="width: {Math.min(Math.max(progress, 0), 100)}%"
                          ></div>
                        </div>
                        <span class="text-xs font-medium text-neutral-600 tabular-nums">{progress}%</span>
                      </div>
                    </td>
                    <td class="px-5 py-4">
                      <div class="flex justify-end gap-2">
                        <button
                          onclick={() => openPhaseComments(row)}
                          disabled={actionLoading || actionSaving}
                          class="rounded-md border border-neutral-200 px-2.5 py-1.5 text-xs font-medium text-neutral-600 transition hover:bg-neutral-50 disabled:opacity-50"
                        >
                          Comments
                        </button>
                        <button
                          onclick={() => openPhaseEdit(row)}
                          disabled={actionLoading || actionSaving}
                          class="rounded-md border border-neutral-200 px-2.5 py-1.5 text-xs font-medium text-neutral-600 transition hover:bg-neutral-50 disabled:opacity-50"
                        >
                          Edit
                        </button>
                        <button
                          onclick={() => deletePhase(row)}
                          disabled={actionLoading || actionSaving}
                          class="rounded-md border border-rose-200 px-2.5 py-1.5 text-xs font-medium text-rose-700 transition hover:bg-rose-50 disabled:opacity-50"
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

          <div class="flex items-center justify-between border-t border-neutral-100 px-5 py-3.5">
            <p class="text-sm text-neutral-500">Page {phasePage} of {phaseTotalPages}</p>
            <div class="flex items-center gap-1.5">
              <button
                onclick={() => (phasePage = Math.max(1, phasePage - 1))}
                disabled={phasePage === 1}
                class="rounded-lg border border-neutral-200 px-2.5 py-1.5 text-sm text-neutral-600 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Prev
              </button>
              <button
                onclick={() => (phasePage = Math.min(phaseTotalPages, phasePage + 1))}
                disabled={phasePage === phaseTotalPages}
                class="rounded-lg border border-neutral-200 px-2.5 py-1.5 text-sm text-neutral-600 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        {/if}
      </section>

      <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
        <div class="flex items-center justify-between border-b border-neutral-100 px-5 py-4">
          <div>
            <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Milestone Board</h2>
            <p class="mt-0.5 text-xs text-neutral-500">Showing {milestoneStart}-{milestoneEnd} of {filteredMilestones.length}</p>
          </div>
        </div>

        {#if filteredMilestones.length === 0}
          <div class="py-16 text-center text-sm text-neutral-400">No milestones found for the current filter set.</div>
        {:else}
          <div class="overflow-x-auto">
            <table class="w-full min-w-[1320px] text-sm">
              <thead>
                <tr class="border-b border-neutral-100 bg-neutral-50/80">
                  <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Project</th>
                  <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Phase</th>
                  <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Milestone</th>
                  <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Target</th>
                  <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">State</th>
                  <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Approval</th>
                  <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Schedule Delta</th>
                  <th class="px-5 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Action</th>
                </tr>
              </thead>

              <tbody class="divide-y divide-neutral-100">
                {#each milestonePageRows as row (row.key)}
                  {@const actionKey = milestoneActionKey(row)}
                  <tr class="bg-white hover:bg-neutral-50 transition-colors">
                    <td class="px-5 py-4 text-neutral-700">{row.projectName}</td>
                    <td class="px-5 py-4">
                      <p class="font-medium text-neutral-900">{row.phaseName}</p>
                      <p class="mt-0.5 text-xs text-neutral-500">{phaseStatusLabel[row.phaseStatus]}</p>
                    </td>
                    <td class="px-5 py-4">
                      <p class="font-medium text-neutral-900">{row.milestoneName}</p>
                      <p class="mt-0.5 text-xs text-neutral-500">ID: {row.milestoneId}</p>
                    </td>
                    <td class="px-5 py-4 text-neutral-600">
                      <p>{fmtDate(row.targetDate)}</p>
                      {#if row.isCompleted}
                        <p class="mt-0.5 text-xs text-neutral-400">completed {fmtDate(row.completedDate)}</p>
                      {/if}
                    </td>
                    <td class="px-5 py-4">
                      <span class="inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold {milestoneStateClass(row)}">
                        {milestoneStateLabel(row)}
                      </span>
                    </td>
                    <td class="px-5 py-4">
                      <span class="inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold {approvalStatusClass(row.approvalStatus)}">
                        {approvalStatusLabel(row.approvalStatus)}
                      </span>
                    </td>
                    <td class="px-5 py-4 text-neutral-600">
                      {#if row.scheduleVarianceDays === null}
                        <span class="text-xs text-neutral-400">--</span>
                      {:else if row.scheduleVarianceDays === 0}
                        <span class="text-xs text-emerald-600 font-medium">On baseline</span>
                      {:else}
                        <span class="text-xs font-medium {row.scheduleVarianceDays > 0 ? 'text-rose-600' : 'text-emerald-700'}">
                          {row.scheduleVarianceDays > 0 ? "+" : ""}{row.scheduleVarianceDays}d
                        </span>
                      {/if}
                    </td>
                    <td class="px-5 py-4 text-right">
                      <div class="inline-flex flex-wrap items-center justify-end gap-1.5">
                        {#if row.approvalStatus === "not_required"}
                          <button
                            onclick={() => submitMilestoneApproval(row)}
                            disabled={approvalBusy[actionKey]}
                            class="rounded-lg border border-neutral-200 px-2.5 py-1.5 text-[11px] font-semibold text-neutral-700 hover:bg-neutral-50 disabled:opacity-50"
                          >
                            Submit
                          </button>
                        {:else if row.approvalStatus === "pending"}
                          <button
                            onclick={() => decideMilestoneApproval(row, "approved")}
                            disabled={approvalBusy[actionKey]}
                            class="rounded-lg border border-emerald-200 bg-emerald-50 px-2.5 py-1.5 text-[11px] font-semibold text-emerald-700 hover:bg-emerald-100 disabled:opacity-50"
                          >
                            Approve
                          </button>
                          <button
                            onclick={() => decideMilestoneApproval(row, "rejected")}
                            disabled={approvalBusy[actionKey]}
                            class="rounded-lg border border-rose-200 bg-rose-50 px-2.5 py-1.5 text-[11px] font-semibold text-rose-700 hover:bg-rose-100 disabled:opacity-50"
                          >
                            Reject
                          </button>
                        {/if}
                        <button
                          onclick={() => openMilestoneComments(row)}
                          disabled={actionLoading || actionSaving}
                          class="rounded-md border border-neutral-200 px-2.5 py-1.5 text-[11px] font-medium text-neutral-600 transition hover:bg-neutral-50 disabled:opacity-50"
                        >
                          Comments
                        </button>
                        <button
                          onclick={() => openMilestoneEdit(row)}
                          disabled={actionLoading || actionSaving}
                          class="rounded-md border border-neutral-200 px-2.5 py-1.5 text-[11px] font-medium text-neutral-600 transition hover:bg-neutral-50 disabled:opacity-50"
                        >
                          Edit
                        </button>
                        <button
                          onclick={() => deleteMilestone(row)}
                          disabled={actionLoading || actionSaving}
                          class="rounded-md border border-rose-200 px-2.5 py-1.5 text-[11px] font-medium text-rose-700 transition hover:bg-rose-50 disabled:opacity-50"
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

          <div class="flex items-center justify-between border-t border-neutral-100 px-5 py-3.5">
            <p class="text-sm text-neutral-500">Page {milestonePage} of {milestoneTotalPages}</p>
            <div class="flex items-center gap-1.5">
              <button
                onclick={() => (milestonePage = Math.max(1, milestonePage - 1))}
                disabled={milestonePage === 1}
                class="rounded-lg border border-neutral-200 px-2.5 py-1.5 text-sm text-neutral-600 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Prev
              </button>
              <button
                onclick={() => (milestonePage = Math.min(milestoneTotalPages, milestonePage + 1))}
                disabled={milestonePage === milestoneTotalPages}
                class="rounded-lg border border-neutral-200 px-2.5 py-1.5 text-sm text-neutral-600 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        {/if}
      </section>
    {:else if viewMode === "kanban"}
      <section class="grid grid-cols-1 gap-4 xl:grid-cols-4">
        <div class="rounded-2xl border border-neutral-200 bg-white">
          <div class="border-b border-neutral-100 px-4 py-3">
            <p class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Pending</p>
            <p class="mt-0.5 text-xs text-neutral-400">{kanbanColumns.pending.length} milestones</p>
          </div>
          <div class="space-y-2 p-3">
            {#if kanbanColumns.pending.length === 0}
              <p class="py-8 text-center text-xs text-neutral-400">No pending milestones.</p>
            {:else}
              {#each kanbanColumns.pending as row (row.key)}
                <article class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
                  <p class="text-xs font-semibold text-neutral-900">{row.milestoneName}</p>
                  <p class="mt-0.5 text-[11px] text-neutral-500">{row.projectName} • {row.phaseName}</p>
                  <p class="mt-2 text-[11px] text-neutral-500">Target {fmtDate(row.targetDate)}</p>
                </article>
              {/each}
            {/if}
          </div>
        </div>

        <div class="rounded-2xl border border-amber-200 bg-white">
          <div class="border-b border-amber-100 px-4 py-3">
            <p class="text-xs font-semibold uppercase tracking-wider text-amber-700">Due in 30d</p>
            <p class="mt-0.5 text-xs text-amber-500">{kanbanColumns.due_30.length} milestones</p>
          </div>
          <div class="space-y-2 p-3">
            {#if kanbanColumns.due_30.length === 0}
              <p class="py-8 text-center text-xs text-neutral-400">No due-soon milestones.</p>
            {:else}
              {#each kanbanColumns.due_30 as row (row.key)}
                <article class="rounded-xl border border-amber-200 bg-amber-50 p-3">
                  <p class="text-xs font-semibold text-neutral-900">{row.milestoneName}</p>
                  <p class="mt-0.5 text-[11px] text-neutral-500">{row.projectName} • {row.phaseName}</p>
                  <p class="mt-2 text-[11px] text-amber-700">{row.daysToTarget ?? 0}d remaining</p>
                </article>
              {/each}
            {/if}
          </div>
        </div>

        <div class="rounded-2xl border border-rose-200 bg-white">
          <div class="border-b border-rose-100 px-4 py-3">
            <p class="text-xs font-semibold uppercase tracking-wider text-rose-700">Overdue</p>
            <p class="mt-0.5 text-xs text-rose-500">{kanbanColumns.overdue.length} milestones</p>
          </div>
          <div class="space-y-2 p-3">
            {#if kanbanColumns.overdue.length === 0}
              <p class="py-8 text-center text-xs text-neutral-400">No overdue milestones.</p>
            {:else}
              {#each kanbanColumns.overdue as row (row.key)}
                <article class="rounded-xl border border-rose-200 bg-rose-50 p-3">
                  <p class="text-xs font-semibold text-neutral-900">{row.milestoneName}</p>
                  <p class="mt-0.5 text-[11px] text-neutral-500">{row.projectName} • {row.phaseName}</p>
                  <p class="mt-2 text-[11px] text-rose-700">{Math.abs(row.daysToTarget ?? 0)}d overdue</p>
                </article>
              {/each}
            {/if}
          </div>
        </div>

        <div class="rounded-2xl border border-emerald-200 bg-white">
          <div class="border-b border-emerald-100 px-4 py-3">
            <p class="text-xs font-semibold uppercase tracking-wider text-emerald-700">Completed</p>
            <p class="mt-0.5 text-xs text-emerald-500">{kanbanColumns.completed.length} milestones</p>
          </div>
          <div class="space-y-2 p-3">
            {#if kanbanColumns.completed.length === 0}
              <p class="py-8 text-center text-xs text-neutral-400">No completed milestones.</p>
            {:else}
              {#each kanbanColumns.completed as row (row.key)}
                <article class="rounded-xl border border-emerald-200 bg-emerald-50 p-3">
                  <p class="text-xs font-semibold text-neutral-900">{row.milestoneName}</p>
                  <p class="mt-0.5 text-[11px] text-neutral-500">{row.projectName} • {row.phaseName}</p>
                  <p class="mt-2 text-[11px] text-emerald-700">Completed {fmtDate(row.completedDate)}</p>
                </article>
              {/each}
            {/if}
          </div>
        </div>
      </section>
    {:else}
      <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
        <div class="border-b border-neutral-100 px-5 py-4">
          <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Gantt Schedule View</h2>
          <p class="mt-0.5 text-xs text-neutral-500">Baseline (gray), revised (blue), actual (dark). Critical path rows are highlighted.</p>
        </div>
        {#if filteredPhases.length === 0}
          <div class="py-16 text-center text-sm text-neutral-400">No phases found for the current filter set.</div>
        {:else}
          <div class="space-y-3 p-5">
            {#each filteredPhases as row (row.key)}
              <div class="grid grid-cols-[220px_1fr] items-center gap-4">
                <div>
                  <p class="text-xs font-semibold text-neutral-900">{row.phaseName}</p>
                  <p class="text-[11px] text-neutral-500">{row.projectName}</p>
                </div>
                <div class="relative h-14 rounded-xl border {row.isCriticalPath ? 'border-fuchsia-200 bg-fuchsia-50/40' : 'border-neutral-200 bg-neutral-50'}">
                  <div
                    class="absolute top-3 h-1.5 rounded-full bg-neutral-300"
                    style="left: {ganttLeft(row.baselineStartDate)}%; width: {ganttWidth(row.baselineStartDate, row.baselineEndDate)}%;"
                  ></div>
                  <div
                    class="absolute top-6 h-2 rounded-full {row.isCriticalPath ? 'bg-fuchsia-500' : 'bg-blue-600'}"
                    style="left: {ganttLeft(row.revisedStartDate || row.plannedStartDate)}%; width: {ganttWidth(row.revisedStartDate || row.plannedStartDate, row.revisedEndDate || row.plannedEndDate)}%;"
                  ></div>
                  <div
                    class="absolute top-10 h-1.5 rounded-full bg-neutral-900"
                    style="left: {ganttLeft(row.actualStartDate)}%; width: {ganttWidth(row.actualStartDate, row.actualEndDate)}%;"
                  ></div>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </section>
    {/if}
  {/if}
</div>

{#if phaseCommentingRow}
  <div class="fixed inset-0 z-40 flex items-center justify-center bg-neutral-900/40 p-4">
    <div class="w-full max-w-2xl rounded-xl border border-neutral-200 bg-white p-5 shadow-xl">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h3 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Phase Comments</h3>
          <p class="mt-1 text-xs text-neutral-500">{phaseCommentingRow.projectName} • {phaseCommentingRow.phaseName}</p>
        </div>
        <button
          onclick={() => {
            phaseCommentingRow = null;
            phaseCommentText = "";
          }}
          class="rounded-md border border-neutral-200 px-2.5 py-1 text-xs font-medium text-neutral-600 hover:bg-neutral-50"
        >
          Close
        </button>
      </div>

      <label class="mt-4 block text-xs font-medium text-neutral-500">
        Notes
        <textarea
          bind:value={phaseCommentText}
          rows={6}
          class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-900"
          placeholder="Add phase comments..."
        ></textarea>
      </label>

      <div class="mt-4 flex justify-end gap-2">
        <button
          onclick={() => {
            phaseCommentingRow = null;
            phaseCommentText = "";
          }}
          class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-50"
        >
          Cancel
        </button>
        <button
          onclick={savePhaseComments}
          disabled={actionSaving}
          class="rounded-md bg-neutral-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
        >
          {actionSaving ? "Saving..." : "Save Comments"}
        </button>
      </div>
    </div>
  </div>
{/if}

{#if milestoneCommentingRow}
  <div class="fixed inset-0 z-40 flex items-center justify-center bg-neutral-900/40 p-4">
    <div class="w-full max-w-2xl rounded-xl border border-neutral-200 bg-white p-5 shadow-xl">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h3 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Milestone Comments</h3>
          <p class="mt-1 text-xs text-neutral-500">{milestoneCommentingRow.projectName} • {milestoneCommentingRow.milestoneName}</p>
        </div>
        <button
          onclick={() => {
            milestoneCommentingRow = null;
            milestoneCommentText = "";
          }}
          class="rounded-md border border-neutral-200 px-2.5 py-1 text-xs font-medium text-neutral-600 hover:bg-neutral-50"
        >
          Close
        </button>
      </div>

      <label class="mt-4 block text-xs font-medium text-neutral-500">
        Notes
        <textarea
          bind:value={milestoneCommentText}
          rows={6}
          class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-900"
          placeholder="Add milestone comments..."
        ></textarea>
      </label>

      <div class="mt-4 flex justify-end gap-2">
        <button
          onclick={() => {
            milestoneCommentingRow = null;
            milestoneCommentText = "";
          }}
          class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-50"
        >
          Cancel
        </button>
        <button
          onclick={saveMilestoneComments}
          disabled={actionSaving}
          class="rounded-md bg-neutral-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
        >
          {actionSaving ? "Saving..." : "Save Comments"}
        </button>
      </div>
    </div>
  </div>
{/if}

{#if editingPhaseRow}
  <div class="fixed inset-0 z-40 flex items-center justify-center bg-neutral-900/40 p-4">
    <div class="w-full max-w-xl rounded-xl border border-neutral-200 bg-white p-5 shadow-xl">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h3 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Edit Phase</h3>
          <p class="mt-1 text-xs text-neutral-500">{editingPhaseRow.projectName} • ID {editingPhaseRow.phaseId}</p>
        </div>
        <button
          onclick={() => {
            editingPhaseRow = null;
          }}
          class="rounded-md border border-neutral-200 px-2.5 py-1 text-xs font-medium text-neutral-600 hover:bg-neutral-50"
        >
          Close
        </button>
      </div>

      <div class="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
        <label class="md:col-span-2 text-xs font-medium text-neutral-500">
          Name
          <input
            bind:value={editPhaseForm.name}
            type="text"
            class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-900"
          />
        </label>
        <label class="text-xs font-medium text-neutral-500">
          Status
          <select
            bind:value={editPhaseForm.status}
            class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-900"
          >
            <option value="not_started">Not Started</option>
            <option value="in_progress">In Progress</option>
            <option value="completed">Completed</option>
            <option value="skipped">Skipped</option>
          </select>
        </label>
        <label class="text-xs font-medium text-neutral-500">
          Planned Start
          <DateInput bind:value={editPhaseForm.planned_start_date} />
        </label>
        <label class="text-xs font-medium text-neutral-500">
          Planned End
          <DateInput bind:value={editPhaseForm.planned_end_date} />
        </label>
      </div>

      <div class="mt-4 flex justify-end gap-2">
        <button
          onclick={() => {
            editingPhaseRow = null;
          }}
          class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-50"
        >
          Cancel
        </button>
        <button
          onclick={savePhaseEdit}
          disabled={actionSaving}
          class="rounded-md bg-neutral-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
        >
          {actionSaving ? "Saving..." : "Save Changes"}
        </button>
      </div>
    </div>
  </div>
{/if}

{#if editingMilestoneRow}
  <div class="fixed inset-0 z-40 flex items-center justify-center bg-neutral-900/40 p-4">
    <div class="w-full max-w-xl rounded-xl border border-neutral-200 bg-white p-5 shadow-xl">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h3 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Edit Milestone</h3>
          <p class="mt-1 text-xs text-neutral-500">{editingMilestoneRow.projectName} • ID {editingMilestoneRow.milestoneId}</p>
        </div>
        <button
          onclick={() => {
            editingMilestoneRow = null;
            editingMilestoneCompletedDate = null;
          }}
          class="rounded-md border border-neutral-200 px-2.5 py-1 text-xs font-medium text-neutral-600 hover:bg-neutral-50"
        >
          Close
        </button>
      </div>

      <div class="mt-4 grid grid-cols-1 gap-3">
        <label class="text-xs font-medium text-neutral-500">
          Name
          <input
            bind:value={editMilestoneForm.name}
            type="text"
            class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-900"
          />
        </label>
        <label class="text-xs font-medium text-neutral-500">
          Target Date
          <DateInput bind:value={editMilestoneForm.target_date} />
        </label>
        <label class="inline-flex items-center gap-2 rounded-lg border border-neutral-200 px-3 py-2 text-sm text-neutral-700">
          <input
            type="checkbox"
            bind:checked={editMilestoneForm.is_completed}
            class="h-4 w-4 rounded border-neutral-300"
          />
          Mark milestone as completed
        </label>
      </div>

      <div class="mt-4 flex justify-end gap-2">
        <button
          onclick={() => {
            editingMilestoneRow = null;
            editingMilestoneCompletedDate = null;
          }}
          class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-50"
        >
          Cancel
        </button>
        <button
          onclick={saveMilestoneEdit}
          disabled={actionSaving}
          class="rounded-md bg-neutral-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
        >
          {actionSaving ? "Saving..." : "Save Changes"}
        </button>
      </div>
    </div>
  </div>
{/if}

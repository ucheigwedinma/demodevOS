<script lang="ts">
  import { api } from "$lib/api";
  import GroupedBarChart from "$lib/components/charts/GroupedBarChart.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import type {
    PaginatedResponse,
    ProjectCostEntry,
    Project,
    ProjectListItem,
    ProjectPhase,
    ProjectPhaseStatus,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  type VarianceFilter = "" | "overspend" | "under_budget" | "on_target";

  type ProjectBudgetRow = {
    id: number;
    name: string;
    propertyName: string;
    manager: string;
    status: ProjectListItem["status"];
    phaseCount: number;
    budget: number;
    planned: number;
    actual: number;
    variance: number;
    utilizationPct: number;
    costEntryCount: number;
  };

  type PhaseCostRow = {
    key: string;
    projectId: number;
    projectName: string;
    phaseId: number;
    phaseName: string;
    status: ProjectPhaseStatus;
    planned: number;
    actual: number;
    variance: number;
    costEntryCount: number;
  };

  type CostLedgerRow = {
    key: string;
    projectId: number;
    projectName: string;
    phaseId: number;
    phaseName: string;
    costId: number;
    description: string;
    amount: number;
    date: string;
    category: ProjectCostEntry["category"];
    vendor: string;
    referenceNumber: string;
  };

  const projectStatusLabel: Record<ProjectListItem["status"], string> = {
    planning: "Planning",
    in_progress: "In Progress",
    on_hold: "On Hold",
    completed: "Completed",
  };

  const projectStatusBadge: Record<ProjectListItem["status"], string> = {
    planning: "bg-blue-50 text-blue-700 border-blue-100",
    in_progress: "bg-emerald-50 text-emerald-700 border-emerald-100",
    on_hold: "bg-amber-50 text-amber-700 border-amber-100",
    completed: "bg-neutral-100 text-neutral-700 border-neutral-200",
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
  let budgetRows = $state<ProjectBudgetRow[]>([]);
  let phaseRows = $state<PhaseCostRow[]>([]);
  let costLedgerRows = $state<CostLedgerRow[]>([]);

  let searchInput = $state("");
  let searchQuery = $state("");
  let projectFilter = $state("");
  let projectStatusFilter = $state<"" | ProjectListItem["status"]>("");
  let phaseStatusFilter = $state<"" | ProjectPhaseStatus>("");
  let varianceFilter = $state<VarianceFilter>("");

  let projectPage = $state(1);
  let phasePage = $state(1);
  let costPage = $state(1);
  let projectPageSize = $state(10);
  let phasePageSize = $state(10);
  let costPageSize = $state(10);
  let expandedBudgetRowId = $state<number | null>(null);

  let fetchToken = 0;
  let searchTimeout: ReturnType<typeof setTimeout> | undefined;
  let actionLoading = $state(false);
  let actionSaving = $state(false);

  let projectCommentingRow = $state<ProjectBudgetRow | null>(null);
  let projectCommentText = $state("");

  let editingProjectRow = $state<ProjectBudgetRow | null>(null);
  let editProjectForm = $state<{
    name: string;
    status: ProjectListItem["status"];
    project_manager: string;
    budget: string;
  }>({
    name: "",
    status: "planning",
    project_manager: "",
    budget: "",
  });

  let phaseCommentingRow = $state<PhaseCostRow | null>(null);
  let phaseCommentText = $state("");

  let editingPhaseRow = $state<PhaseCostRow | null>(null);
  let editPhaseForm = $state<{
    name: string;
    status: ProjectPhaseStatus;
    planned_budget: string;
  }>({
    name: "",
    status: "not_started",
    planned_budget: "",
  });

  let costCommentingRow = $state<CostLedgerRow | null>(null);
  let costCommentText = $state("");

  let editingCostRow = $state<CostLedgerRow | null>(null);
  let editCostForm = $state<{
    description: string;
    date: string;
    category: ProjectCostEntry["category"];
    vendor: string;
    reference_number: string;
    amount: string;
  }>({
    description: "",
    date: "",
    category: "other",
    vendor: "",
    reference_number: "",
    amount: "",
  });

  function toNumber(value: unknown): number {
    if (typeof value === "number") return Number.isFinite(value) ? value : 0;
    if (typeof value === "string") {
      const parsed = Number(value.replace(/,/g, ""));
      return Number.isFinite(parsed) ? parsed : 0;
    }
    return 0;
  }

  function fmtCurrency(amount: number): string {
    return currency.formatCompact(amount);
  }

  function fmtVariance(amount: number): string {
    const abs = fmtCurrency(Math.abs(amount));
    return `${amount >= 0 ? "+" : "-"}${abs}`;
  }

  function fmtPct(value: number): string {
    return `${Math.max(0, value).toFixed(1)}%`;
  }

  function normalizeVariance(value: number): number {
    return Math.abs(value) < 0.01 ? 0 : value;
  }

  function phaseMapKey(projectId: number, phaseId: number): string {
    return `${projectId}-${phaseId}`;
  }

  function extractResults<T>(payload: PaginatedResponse<T> | T[]): T[] {
    if (Array.isArray(payload)) return payload;
    return payload.results ?? [];
  }

  function hasNextPage<T>(payload: PaginatedResponse<T> | T[]): boolean {
    if (Array.isArray(payload)) return false;
    return Boolean(payload.next);
  }

  async function fetchAllRows<T>(endpoint: string): Promise<T[]> {
    const rows: T[] = [];
    let page = 1;

    while (true) {
      const payload = await api.get<PaginatedResponse<T> | T[]>(endpoint, {
        page: String(page),
      });

      const pageRows = extractResults(payload);
      rows.push(...pageRows);

      if (!hasNextPage(payload) || pageRows.length === 0) break;
      page += 1;
    }

    return rows;
  }

  function parseDateMillis(value: string): number {
    const parsed = new Date(value).getTime();
    if (Number.isNaN(parsed)) return 0;
    return parsed;
  }

  function fmtDate(value: string): string {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return "--";
    return parsed.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  function onSearchInput(event: Event) {
    searchInput = (event.target as HTMLInputElement).value;
    if (searchTimeout) clearTimeout(searchTimeout);

    searchTimeout = setTimeout(() => {
      searchQuery = searchInput.trim().toLowerCase();
      projectPage = 1;
      phasePage = 1;
      costPage = 1;
    }, 250);
  }

  function resetFilters() {
    searchInput = "";
    searchQuery = "";
    projectFilter = "";
    projectStatusFilter = "";
    phaseStatusFilter = "";
    varianceFilter = "";
    projectPage = 1;
    phasePage = 1;
    costPage = 1;
  }

  async function fetchAllProjects(): Promise<ProjectListItem[]> {
    const rows = await fetchAllRows<ProjectListItem>("/projects/");
    rows.sort((a, b) => a.name.localeCompare(b.name));
    return rows;
  }

  async function fetchPhaseSnapshots(projectList: ProjectListItem[]): Promise<Map<number, ProjectPhase[]>> {
    const map = new Map<number, ProjectPhase[]>();
    const concurrency = 8;
    let failed = 0;

    for (let idx = 0; idx < projectList.length; idx += concurrency) {
      const chunk = projectList.slice(idx, idx + concurrency);
      const rows = await Promise.all(
        chunk.map(async (project) => {
          try {
            const phases = await fetchAllRows<ProjectPhase>(`/projects/${project.id}/phases/`);
            return { projectId: project.id, phases };
          } catch {
            failed += 1;
            return { projectId: project.id, phases: [] };
          }
        }),
      );

      for (const row of rows) {
        map.set(row.projectId, row.phases);
      }
    }

    if (failed > 0) {
      const suffix = failed === 1 ? "project phase feed failed" : "project phase feeds failed";
      toast.error("Partial data", `${failed} ${suffix} to load.`);
    }

    return map;
  }

  async function fetchCostSnapshots(
    projectList: ProjectListItem[],
    phaseMap: Map<number, ProjectPhase[]>,
  ): Promise<Map<string, ProjectCostEntry[]>> {
    const map = new Map<string, ProjectCostEntry[]>();
    const concurrency = 4;
    let failed = 0;

    for (let idx = 0; idx < projectList.length; idx += concurrency) {
      const chunk = projectList.slice(idx, idx + concurrency);
      const projectRows = await Promise.all(
        chunk.map(async (project) => {
          const phases = phaseMap.get(project.id) ?? [];
          const phaseRows = await Promise.all(
            phases.map(async (phase) => {
              const key = phaseMapKey(project.id, phase.id);
              try {
                const costs = await fetchAllRows<ProjectCostEntry>(`/projects/${project.id}/phases/${phase.id}/costs/`);
                return { key, costs };
              } catch {
                failed += 1;
                return { key, costs: [] };
              }
            }),
          );
          return phaseRows;
        }),
      );

      for (const rows of projectRows) {
        for (const row of rows) {
          map.set(row.key, row.costs);
        }
      }
    }

    if (failed > 0) {
      const suffix = failed === 1 ? "phase cost feed failed" : "phase cost feeds failed";
      toast.error("Partial data", `${failed} ${suffix} to load.`);
    }

    return map;
  }

  function buildRows(
    projectList: ProjectListItem[],
    phaseMap: Map<number, ProjectPhase[]>,
    costMap: Map<string, ProjectCostEntry[]>,
  ) {
    const nextBudgetRows: ProjectBudgetRow[] = [];
    const nextPhaseRows: PhaseCostRow[] = [];
    const nextCostLedgerRows: CostLedgerRow[] = [];

    for (const project of projectList) {
      const phases = phaseMap.get(project.id) ?? [];

      let planned = 0;
      let actual = 0;
      let costEntryCount = 0;

      for (const phase of phases) {
        const phaseKey = phaseMapKey(project.id, phase.id);
        const phaseEntries = costMap.get(phaseKey) ?? [];
        const phasePlanned = toNumber(phase.planned_budget);
        const entriesActual = phaseEntries.reduce((sum, entry) => sum + toNumber(entry.amount), 0);
        const phaseActual = phaseEntries.length > 0 ? entriesActual : toNumber(phase.cost_total ?? phase.actual_cost);
        costEntryCount += phaseEntries.length;

        planned += phasePlanned;
        actual += phaseActual;

        nextPhaseRows.push({
          key: phaseKey,
          projectId: project.id,
          projectName: project.name,
          phaseId: phase.id,
          phaseName: phase.name,
          status: phase.status,
          planned: phasePlanned,
          actual: phaseActual,
          variance: normalizeVariance(phasePlanned - phaseActual),
          costEntryCount: phaseEntries.length,
        });

        for (const entry of phaseEntries) {
          nextCostLedgerRows.push({
            key: `${phaseKey}-${entry.id}`,
            projectId: project.id,
            projectName: project.name,
            phaseId: phase.id,
            phaseName: phase.name,
            costId: entry.id,
            description: entry.description,
            amount: toNumber(entry.amount),
            date: entry.date,
            category: entry.category,
            vendor: entry.vendor,
            referenceNumber: entry.reference_number,
          });
        }
      }

      const variance = normalizeVariance(planned - actual);
      const utilizationPct = planned > 0 ? (actual / planned) * 100 : 0;

      nextBudgetRows.push({
        id: project.id,
        name: project.name,
        propertyName: project.property_name ?? "Unlinked property",
        manager: project.project_manager,
        status: project.status,
        phaseCount: phases.length,
        budget: toNumber(project.budget),
        planned,
        actual,
        variance,
        utilizationPct,
        costEntryCount,
      });
    }

    nextBudgetRows.sort((a, b) => b.actual - a.actual);
    nextPhaseRows.sort((a, b) => Math.abs(b.variance) - Math.abs(a.variance));
    nextCostLedgerRows.sort((a, b) => {
      const dateDelta = parseDateMillis(b.date) - parseDateMillis(a.date);
      if (dateDelta !== 0) return dateDelta;
      return b.amount - a.amount;
    });

    return { nextBudgetRows, nextPhaseRows, nextCostLedgerRows };
  }

  async function loadPageData() {
    loading = true;
    const token = ++fetchToken;

    try {
      const projectList = await fetchAllProjects();
      const phaseMap = await fetchPhaseSnapshots(projectList);
      const costMap = await fetchCostSnapshots(projectList, phaseMap);
      if (token !== fetchToken) return;

      const rows = buildRows(projectList, phaseMap, costMap);
      projects = projectList;
      budgetRows = rows.nextBudgetRows;
      phaseRows = rows.nextPhaseRows;
      costLedgerRows = rows.nextCostLedgerRows;
    } catch {
      if (token !== fetchToken) return;
      projects = [];
      budgetRows = [];
      phaseRows = [];
      costLedgerRows = [];
      toast.error("Load failed", "Could not load budget and cost data.");
    } finally {
      if (token === fetchToken) loading = false;
    }
  }

  async function openProjectComments(row: ProjectBudgetRow) {
    actionLoading = true;
    try {
      const project = await api.get<Project>(`/projects/${row.id}/`);
      projectCommentText = project.description ?? "";
      projectCommentingRow = row;
    } catch {
      toast.error("Load failed", "Could not load project comments.");
    } finally {
      actionLoading = false;
    }
  }

  async function saveProjectComments() {
    if (!projectCommentingRow) return;

    actionSaving = true;
    try {
      await api.patch(`/projects/${projectCommentingRow.id}/`, {
        description: projectCommentText,
      });
      toast.success("Comments saved", "Project comments updated.");
      projectCommentingRow = null;
      projectCommentText = "";
      await loadPageData();
    } catch {
      toast.error("Save failed", "Could not save project comments.");
    } finally {
      actionSaving = false;
    }
  }

  async function openProjectEdit(row: ProjectBudgetRow) {
    actionLoading = true;
    try {
      const project = await api.get<Project>(`/projects/${row.id}/`);
      editProjectForm = {
        name: project.name,
        status: project.status,
        project_manager: project.project_manager ?? "",
        budget: project.budget ?? "",
      };
      editingProjectRow = row;
    } catch {
      toast.error("Load failed", "Could not load project details.");
    } finally {
      actionLoading = false;
    }
  }

  async function saveProjectEdit() {
    if (!editingProjectRow) return;

    const nextName = editProjectForm.name.trim();
    if (!nextName) {
      toast.error("Validation failed", "Project name is required.");
      return;
    }

    actionSaving = true;
    try {
      await api.patch(`/projects/${editingProjectRow.id}/`, {
        name: nextName,
        status: editProjectForm.status,
        project_manager: editProjectForm.project_manager.trim(),
        budget: editProjectForm.budget.trim() || null,
      });
      toast.success("Project updated", "Project changes saved.");
      editingProjectRow = null;
      await loadPageData();
    } catch {
      toast.error("Save failed", "Could not update project.");
    } finally {
      actionSaving = false;
    }
  }

  async function deleteProject(row: ProjectBudgetRow) {
    if (!confirm(`Delete project "${row.name}"?`)) return;

    actionSaving = true;
    try {
      await api.delete(`/projects/${row.id}/`);
      toast.success("Project deleted", "The project has been removed.");
      await loadPageData();
    } catch {
      toast.error("Delete failed", "Could not delete project.");
    } finally {
      actionSaving = false;
    }
  }

  async function openPhaseCostComments(row: PhaseCostRow) {
    actionLoading = true;
    try {
      const phase = await api.get<ProjectPhase>(`/projects/${row.projectId}/phases/${row.phaseId}/`);
      phaseCommentText = phase.description ?? "";
      phaseCommentingRow = row;
    } catch {
      toast.error("Load failed", "Could not load phase comments.");
    } finally {
      actionLoading = false;
    }
  }

  async function savePhaseCostComments() {
    if (!phaseCommentingRow) return;

    actionSaving = true;
    try {
      await api.patch(`/projects/${phaseCommentingRow.projectId}/phases/${phaseCommentingRow.phaseId}/`, {
        description: phaseCommentText,
      });
      toast.success("Comments saved", "Phase comments updated.");
      phaseCommentingRow = null;
      phaseCommentText = "";
      await loadPageData();
    } catch {
      toast.error("Save failed", "Could not save phase comments.");
    } finally {
      actionSaving = false;
    }
  }

  async function openPhaseCostEdit(row: PhaseCostRow) {
    actionLoading = true;
    try {
      const phase = await api.get<ProjectPhase>(`/projects/${row.projectId}/phases/${row.phaseId}/`);
      editPhaseForm = {
        name: phase.name,
        status: phase.status,
        planned_budget: phase.planned_budget ?? "",
      };
      editingPhaseRow = row;
    } catch {
      toast.error("Load failed", "Could not load phase details.");
    } finally {
      actionLoading = false;
    }
  }

  async function savePhaseCostEdit() {
    if (!editingPhaseRow) return;

    const nextName = editPhaseForm.name.trim();
    if (!nextName) {
      toast.error("Validation failed", "Phase name is required.");
      return;
    }

    actionSaving = true;
    try {
      await api.patch(`/projects/${editingPhaseRow.projectId}/phases/${editingPhaseRow.phaseId}/`, {
        name: nextName,
        status: editPhaseForm.status,
        planned_budget: editPhaseForm.planned_budget.trim() || null,
      });
      toast.success("Phase updated", "Phase changes saved.");
      editingPhaseRow = null;
      await loadPageData();
    } catch {
      toast.error("Save failed", "Could not update phase.");
    } finally {
      actionSaving = false;
    }
  }

  async function deletePhaseCostRow(row: PhaseCostRow) {
    if (!confirm(`Delete phase "${row.phaseName}"?`)) return;

    actionSaving = true;
    try {
      await api.delete(`/projects/${row.projectId}/phases/${row.phaseId}/`);
      toast.success("Phase deleted", "The phase has been removed.");
      await loadPageData();
    } catch {
      toast.error("Delete failed", "Could not delete phase.");
    } finally {
      actionSaving = false;
    }
  }

  async function openCostLedgerComments(row: CostLedgerRow) {
    actionLoading = true;
    try {
      const costEntry = await api.get<ProjectCostEntry>(
        `/projects/${row.projectId}/phases/${row.phaseId}/costs/${row.costId}/`,
      );
      costCommentText = costEntry.description ?? "";
      costCommentingRow = row;
    } catch {
      toast.error("Load failed", "Could not load cost entry comments.");
    } finally {
      actionLoading = false;
    }
  }

  async function saveCostLedgerComments() {
    if (!costCommentingRow) return;

    actionSaving = true;
    try {
      await api.patch(
        `/projects/${costCommentingRow.projectId}/phases/${costCommentingRow.phaseId}/costs/${costCommentingRow.costId}/`,
        { description: costCommentText },
      );
      toast.success("Comments saved", "Cost entry comments updated.");
      costCommentingRow = null;
      costCommentText = "";
      await loadPageData();
    } catch {
      toast.error("Save failed", "Could not save cost entry comments.");
    } finally {
      actionSaving = false;
    }
  }

  async function openCostLedgerEdit(row: CostLedgerRow) {
    actionLoading = true;
    try {
      const costEntry = await api.get<ProjectCostEntry>(
        `/projects/${row.projectId}/phases/${row.phaseId}/costs/${row.costId}/`,
      );
      editCostForm = {
        description: costEntry.description ?? "",
        date: costEntry.date ?? "",
        category: costEntry.category,
        vendor: costEntry.vendor ?? "",
        reference_number: costEntry.reference_number ?? "",
        amount: costEntry.amount ?? "",
      };
      editingCostRow = row;
    } catch {
      toast.error("Load failed", "Could not load cost entry details.");
    } finally {
      actionLoading = false;
    }
  }

  async function saveCostLedgerEdit() {
    if (!editingCostRow) return;
    if (!editCostForm.description.trim()) {
      toast.error("Validation failed", "Description is required.");
      return;
    }

    actionSaving = true;
    try {
      await api.patch(
        `/projects/${editingCostRow.projectId}/phases/${editingCostRow.phaseId}/costs/${editingCostRow.costId}/`,
        {
          description: editCostForm.description.trim(),
          date: editCostForm.date,
          category: editCostForm.category,
          vendor: editCostForm.vendor.trim(),
          reference_number: editCostForm.reference_number.trim(),
          amount: editCostForm.amount.trim(),
        },
      );
      toast.success("Cost entry updated", "Cost entry changes saved.");
      editingCostRow = null;
      await loadPageData();
    } catch {
      toast.error("Save failed", "Could not update cost entry.");
    } finally {
      actionSaving = false;
    }
  }

  async function deleteCostLedgerEntry(row: CostLedgerRow) {
    if (!confirm(`Delete cost entry #${row.costId}?`)) return;

    actionSaving = true;
    try {
      await api.delete(`/projects/${row.projectId}/phases/${row.phaseId}/costs/${row.costId}/`);
      toast.success("Cost entry deleted", "The cost entry has been removed.");
      await loadPageData();
    } catch {
      toast.error("Delete failed", "Could not delete cost entry.");
    } finally {
      actionSaving = false;
    }
  }

  function toggleBudgetRow(rowId: number) {
    expandedBudgetRowId = expandedBudgetRowId === rowId ? null : rowId;
  }

  const projectOptions = $derived.by(() => {
    return [...projects].sort((a, b) => a.name.localeCompare(b.name));
  });

  const filteredBudgetRows = $derived.by(() => {
    return budgetRows.filter((row) => {
      if (projectFilter && String(row.id) !== projectFilter) return false;
      if (projectStatusFilter && row.status !== projectStatusFilter) return false;
      if (varianceFilter === "overspend" && row.variance >= 0) return false;
      if (varianceFilter === "under_budget" && row.variance <= 0) return false;
      if (varianceFilter === "on_target" && row.variance !== 0) return false;

      if (!searchQuery) return true;
      const haystack = `${row.name} ${row.propertyName} ${row.manager}`.toLowerCase();
      return haystack.includes(searchQuery);
    });
  });

  const filteredPhaseRows = $derived.by(() => {
    return phaseRows.filter((row) => {
      if (projectFilter && String(row.projectId) !== projectFilter) return false;
      if (phaseStatusFilter && row.status !== phaseStatusFilter) return false;
      if (varianceFilter === "overspend" && row.variance >= 0) return false;
      if (varianceFilter === "under_budget" && row.variance <= 0) return false;
      if (varianceFilter === "on_target" && row.variance !== 0) return false;

      if (!searchQuery) return true;
      const haystack = `${row.projectName} ${row.phaseName}`.toLowerCase();
      return haystack.includes(searchQuery);
    });
  });

  const phaseRowsByKey = $derived.by(() => {
    const map = new Map<string, PhaseCostRow>();
    for (const row of phaseRows) {
      map.set(row.key, row);
    }
    return map;
  });

  const filteredCostLedgerRows = $derived.by(() => {
    return costLedgerRows.filter((row) => {
      if (projectFilter && String(row.projectId) !== projectFilter) return false;

      const phaseKey = phaseMapKey(row.projectId, row.phaseId);
      const phaseInfo = phaseRowsByKey.get(phaseKey);

      if (phaseStatusFilter && (!phaseInfo || phaseInfo.status !== phaseStatusFilter)) return false;

      if (varianceFilter && phaseInfo) {
        if (varianceFilter === "overspend" && phaseInfo.variance >= 0) return false;
        if (varianceFilter === "under_budget" && phaseInfo.variance <= 0) return false;
        if (varianceFilter === "on_target" && phaseInfo.variance !== 0) return false;
      }

      if (!searchQuery) return true;

      const haystack = [
        row.projectName,
        row.phaseName,
        row.description,
        row.vendor,
        row.referenceNumber,
        row.category,
      ]
        .join(" ")
        .toLowerCase();

      return haystack.includes(searchQuery);
    });
  });

  const hasFilters = $derived(
    Boolean(searchQuery || projectFilter || projectStatusFilter || phaseStatusFilter || varianceFilter),
  );

  const totalPlanned = $derived(
    filteredBudgetRows.reduce((sum, row) => sum + row.planned, 0),
  );

  const totalActual = $derived(
    filteredBudgetRows.reduce((sum, row) => sum + row.actual, 0),
  );

  const totalVariance = $derived(
    filteredBudgetRows.reduce((sum, row) => sum + row.variance, 0),
  );

  const overspendProjectCount = $derived(
    filteredBudgetRows.filter((row) => row.variance < 0).length,
  );

  const avgUtilization = $derived.by(() => {
    const rows = filteredBudgetRows.filter((row) => row.planned > 0);
    if (rows.length === 0) return 0;
    return rows.reduce((sum, row) => sum + row.utilizationPct, 0) / rows.length;
  });

  const totalCostEntries = $derived(filteredCostLedgerRows.length);

  const budgetChartData = $derived(
    [...filteredBudgetRows]
      .sort((a, b) => b.actual - a.actual)
      .slice(0, 8)
      .map((row) => ({
        label: row.name,
        value1: row.planned,
        value2: row.actual,
      })),
  );

  const projectTotalPages = $derived(Math.max(1, Math.ceil(filteredBudgetRows.length / projectPageSize)));
  const phaseTotalPages = $derived(Math.max(1, Math.ceil(filteredPhaseRows.length / phasePageSize)));
  const costTotalPages = $derived(Math.max(1, Math.ceil(filteredCostLedgerRows.length / costPageSize)));

  const projectStart = $derived(filteredBudgetRows.length === 0 ? 0 : (projectPage - 1) * projectPageSize + 1);
  const projectEnd = $derived(Math.min(projectPage * projectPageSize, filteredBudgetRows.length));

  const phaseStart = $derived(filteredPhaseRows.length === 0 ? 0 : (phasePage - 1) * phasePageSize + 1);
  const phaseEnd = $derived(Math.min(phasePage * phasePageSize, filteredPhaseRows.length));
  const costStart = $derived(filteredCostLedgerRows.length === 0 ? 0 : (costPage - 1) * costPageSize + 1);
  const costEnd = $derived(Math.min(costPage * costPageSize, filteredCostLedgerRows.length));

  const projectPageRows = $derived(
    filteredBudgetRows.slice((projectPage - 1) * projectPageSize, projectPage * projectPageSize),
  );

  const phasePageRows = $derived(
    filteredPhaseRows.slice((phasePage - 1) * phasePageSize, phasePage * phasePageSize),
  );

  const costPageRows = $derived(
    filteredCostLedgerRows.slice((costPage - 1) * costPageSize, costPage * costPageSize),
  );

  $effect(() => {
    void projectFilter;
    void projectStatusFilter;
    void phaseStatusFilter;
    void varianceFilter;
    void searchQuery;

    projectPage = 1;
    phasePage = 1;
    costPage = 1;
  });

  $effect(() => {
    void projectTotalPages;
    if (projectPage > projectTotalPages) projectPage = projectTotalPages;
  });

  $effect(() => {
    void phaseTotalPages;
    if (phasePage > phaseTotalPages) phasePage = phaseTotalPages;
  });

  $effect(() => {
    void costTotalPages;
    if (costPage > costTotalPages) costPage = costTotalPages;
  });

  $effect(() => {
    if (expandedBudgetRowId !== null && !projectPageRows.some((row) => row.id === expandedBudgetRowId)) {
      expandedBudgetRowId = null;
    }
  });

  $effect(() => {
    loadPageData();
  });
</script>

<div class="space-y-6">
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-blue-600">Projects</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-900">Budget &amp; Cost</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Portfolio-wide view of planned spend, actual cost, and variance by project and phase.
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
          placeholder="Search project, property, manager, phase..."
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
          bind:value={varianceFilter}
          class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
        >
          <option value="">All Variance States</option>
          <option value="overspend">Overspend</option>
          <option value="under_budget">Under Budget</option>
          <option value="on_target">On Target</option>
        </select>
      </div>

      <div class="mt-3 flex flex-wrap items-center gap-2">
        <select
          bind:value={projectStatusFilter}
          class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
        >
          <option value="">All Project Statuses</option>
          <option value="planning">Planning</option>
          <option value="in_progress">In Progress</option>
          <option value="on_hold">On Hold</option>
          <option value="completed">Completed</option>
        </select>

        <select
          bind:value={phaseStatusFilter}
          class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
        >
          <option value="">All Phase Statuses</option>
          <option value="not_started">Not Started</option>
          <option value="in_progress">In Progress</option>
          <option value="completed">Completed</option>
          <option value="skipped">Skipped</option>
        </select>

        <select
          value={String(projectPageSize)}
          onchange={(event) => {
            projectPageSize = Number((event.target as HTMLSelectElement).value);
            projectPage = 1;
          }}
          class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
        >
          <option value="10">10 projects / page</option>
          <option value="20">20 projects / page</option>
          <option value="50">50 projects / page</option>
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
          value={String(costPageSize)}
          onchange={(event) => {
            costPageSize = Number((event.target as HTMLSelectElement).value);
            costPage = 1;
          }}
          class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
        >
          <option value="10">10 costs / page</option>
          <option value="20">20 costs / page</option>
          <option value="50">50 costs / page</option>
        </select>

        {#if hasFilters}
          <button
            onclick={resetFilters}
            class="rounded-lg border border-neutral-200 px-3 py-2 text-sm font-medium text-neutral-600 hover:bg-neutral-50"
          >
            Reset Filters
          </button>
        {/if}
      </div>
    </div>

    <div class="grid grid-cols-2 gap-4 p-4 sm:grid-cols-3 xl:grid-cols-6">
      <div class="rounded-xl border border-neutral-200 border-t-4 border-t-sky-500 bg-white p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Planned Spend</p>
        <p class="mt-1 text-lg font-bold text-neutral-900 tabular-nums">{fmtCurrency(totalPlanned)}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 border-t-4 border-t-indigo-500 bg-white p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Actual Cost</p>
        <p class="mt-1 text-lg font-bold text-neutral-900 tabular-nums">{fmtCurrency(totalActual)}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 border-t-4 border-t-violet-500 bg-white p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Portfolio Variance</p>
        <p class="mt-1 text-lg font-bold tabular-nums {totalVariance >= 0 ? 'text-emerald-600' : 'text-rose-600'}">
          {fmtVariance(totalVariance)}
        </p>
      </div>
      <div class="rounded-xl border border-neutral-200 border-t-4 border-t-rose-500 bg-white p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Overspend Projects</p>
        <p class="mt-1 text-lg font-bold text-rose-600 tabular-nums">{overspendProjectCount}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 border-t-4 border-t-emerald-500 bg-white p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Avg Utilization</p>
        <p class="mt-1 text-lg font-bold text-emerald-600 tabular-nums">{fmtPct(avgUtilization)}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 border-t-4 border-t-amber-500 bg-white p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Cost Entries</p>
        <p class="mt-1 text-lg font-bold text-neutral-900 tabular-nums">{totalCostEntries}</p>
      </div>
    </div>
  </section>

  {#if loading}
    <div class="flex items-center justify-center py-20">
      <div class="h-7 w-7 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
    </div>
  {:else}
    <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white p-6">
      <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Planned vs Actual by Project</h2>
      <p class="mt-1 text-xs text-neutral-500">Top 8 projects by actual cost (based on current filters)</p>
      <div class="mt-4 overflow-hidden">
        <GroupedBarChart
          data={budgetChartData}
          value1Key="value1"
          value2Key="value2"
          label1="Planned"
          label2="Actual"
          color1="#bfdbfe"
          color2="#2563eb"
          formatValue={fmtCurrency}
          height={340}
        />
      </div>
    </section>

    <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
      <div class="flex items-center justify-between border-b border-neutral-100 px-5 py-4">
        <div>
          <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Project Budget Register</h2>
          <p class="mt-0.5 text-xs text-neutral-500">Showing {projectStart}-{projectEnd} of {filteredBudgetRows.length}</p>
        </div>
      </div>

      {#if filteredBudgetRows.length === 0}
        <div class="py-16 text-center text-sm text-neutral-400">No project budget rows found for the current filters.</div>
      {:else}
        <div class="overflow-x-auto">
          <table class="w-full min-w-[980px] text-sm">
            <thead>
              <tr class="border-b border-neutral-100 bg-neutral-50/80">
                <th class="px-5 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Details</th>
                <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Project</th>
                <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Status</th>
                <th class="px-5 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Budget</th>
                <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Utilization</th>
                <th class="px-5 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Action</th>
              </tr>
            </thead>

            <tbody class="divide-y divide-neutral-100">
              {#each projectPageRows as row (row.id)}
                <tr class="bg-white hover:bg-neutral-50 transition-colors">
                  <td class="px-5 py-4 text-right">
                    <button
                      type="button"
                      onclick={() => toggleBudgetRow(row.id)}
                      aria-expanded={expandedBudgetRowId === row.id}
                      aria-label={expandedBudgetRowId === row.id ? "Collapse row details" : "Expand row details"}
                      class="inline-flex items-center text-xs font-semibold text-neutral-700 hover:text-neutral-900"
                    >
                      <span class={`transition-transform ${expandedBudgetRowId === row.id ? "rotate-180" : ""}`}>▾</span>
                    </button>
                  </td>
                  <td class="px-5 py-4">
                    <p class="font-medium text-neutral-900">{row.name}</p>
                    <p class="mt-0.5 text-xs text-neutral-500">{row.propertyName} {row.manager ? `· ${row.manager}` : ""}</p>
                  </td>
                  <td class="px-5 py-4">
                    <span class="inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold {projectStatusBadge[row.status]}">
                      {projectStatusLabel[row.status]}
                    </span>
                  </td>
                  <td class="px-5 py-4 text-right font-medium text-neutral-700 tabular-nums">{fmtCurrency(row.budget)}</td>
                  <td class="px-5 py-4">
                    <div class="flex items-center gap-2">
                      <div class="h-2 w-24 overflow-hidden rounded-full bg-neutral-100">
                        <div
                          class="h-2 rounded-full {row.utilizationPct > 100 ? 'bg-rose-500' : row.utilizationPct >= 80 ? 'bg-amber-500' : 'bg-emerald-500'}"
                          style="width: {Math.min(Math.max(row.utilizationPct, 0), 100)}%"
                        ></div>
                      </div>
                      <span class="text-xs font-medium text-neutral-600 tabular-nums">{fmtPct(row.utilizationPct)}</span>
                    </div>
                  </td>
                  <td class="px-5 py-4">
                    <div class="flex justify-end gap-2">
                      <button
                        onclick={() => openProjectComments(row)}
                        disabled={actionLoading || actionSaving}
                        class="rounded-md border border-neutral-200 px-2.5 py-1.5 text-xs font-medium text-neutral-600 transition hover:bg-neutral-50 disabled:opacity-50"
                      >
                        Comments
                      </button>
                      <button
                        onclick={() => openProjectEdit(row)}
                        disabled={actionLoading || actionSaving}
                        class="rounded-md border border-neutral-200 px-2.5 py-1.5 text-xs font-medium text-neutral-600 transition hover:bg-neutral-50 disabled:opacity-50"
                      >
                        Edit
                      </button>
                      <button
                        onclick={() => deleteProject(row)}
                        disabled={actionLoading || actionSaving}
                        class="rounded-md border border-rose-200 px-2.5 py-1.5 text-xs font-medium text-rose-700 transition hover:bg-rose-50 disabled:opacity-50"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
                {#if expandedBudgetRowId === row.id}
                  <tr class="bg-neutral-50/70">
                    <td colspan="6" class="px-5 pb-4 pt-0">
                      <div class="grid gap-3 pt-3 md:grid-cols-2 xl:grid-cols-4">
                        <div class="rounded-lg border border-neutral-200 bg-white p-3">
                          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Cost Entries</p>
                          <p class="mt-1 text-sm font-semibold text-neutral-900 tabular-nums">{row.costEntryCount}</p>
                        </div>
                        <div class="rounded-lg border border-neutral-200 bg-white p-3">
                          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Planned</p>
                          <p class="mt-1 text-sm font-semibold text-neutral-900 tabular-nums">{fmtCurrency(row.planned)}</p>
                        </div>
                        <div class="rounded-lg border border-neutral-200 bg-white p-3">
                          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Actual</p>
                          <p class="mt-1 text-sm font-semibold text-neutral-900 tabular-nums">{fmtCurrency(row.actual)}</p>
                        </div>
                        <div class="rounded-lg border border-neutral-200 bg-white p-3">
                          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Variance</p>
                          <p class="mt-1 text-sm font-semibold tabular-nums {row.variance >= 0 ? 'text-emerald-600' : 'text-rose-600'}">
                            {fmtVariance(row.variance)}
                          </p>
                        </div>
                      </div>
                    </td>
                  </tr>
                {/if}
              {/each}
            </tbody>
          </table>
        </div>

        <div class="flex items-center justify-between border-t border-neutral-100 px-5 py-3.5">
          <p class="text-sm text-neutral-500">Page {projectPage} of {projectTotalPages}</p>
          <div class="flex items-center gap-1.5">
            <button
              onclick={() => (projectPage = Math.max(1, projectPage - 1))}
              disabled={projectPage === 1}
              class="rounded-lg border border-neutral-200 px-2.5 py-1.5 text-sm text-neutral-600 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Prev
            </button>
            <button
              onclick={() => (projectPage = Math.min(projectTotalPages, projectPage + 1))}
              disabled={projectPage === projectTotalPages}
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
          <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Phase Cost Register</h2>
          <p class="mt-0.5 text-xs text-neutral-500">Showing {phaseStart}-{phaseEnd} of {filteredPhaseRows.length}</p>
        </div>
      </div>

      {#if filteredPhaseRows.length === 0}
        <div class="py-16 text-center text-sm text-neutral-400">No phase cost rows found for the current filters.</div>
      {:else}
        <div class="overflow-x-auto">
          <table class="w-full min-w-[1050px] text-sm">
            <thead>
              <tr class="border-b border-neutral-100 bg-neutral-50/80">
                <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Project</th>
                <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Phase</th>
                <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Status</th>
                <th class="px-5 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Cost Entries</th>
                <th class="px-5 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Planned</th>
                <th class="px-5 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Actual</th>
                <th class="px-5 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Variance</th>
                <th class="px-5 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Action</th>
              </tr>
            </thead>

            <tbody class="divide-y divide-neutral-100">
              {#each phasePageRows as row (row.key)}
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
                  <td class="px-5 py-4 text-right font-medium text-neutral-700 tabular-nums">{row.costEntryCount}</td>
                  <td class="px-5 py-4 text-right font-medium text-neutral-900 tabular-nums">{fmtCurrency(row.planned)}</td>
                  <td class="px-5 py-4 text-right font-medium text-neutral-900 tabular-nums">{fmtCurrency(row.actual)}</td>
                  <td class="px-5 py-4 text-right font-semibold tabular-nums {row.variance >= 0 ? 'text-emerald-600' : 'text-rose-600'}">
                    {fmtVariance(row.variance)}
                  </td>
                  <td class="px-5 py-4">
                    <div class="flex justify-end gap-2">
                      <button
                        onclick={() => openPhaseCostComments(row)}
                        disabled={actionLoading || actionSaving}
                        class="rounded-md border border-neutral-200 px-2.5 py-1.5 text-xs font-medium text-neutral-600 transition hover:bg-neutral-50 disabled:opacity-50"
                      >
                        Comments
                      </button>
                      <button
                        onclick={() => openPhaseCostEdit(row)}
                        disabled={actionLoading || actionSaving}
                        class="rounded-md border border-neutral-200 px-2.5 py-1.5 text-xs font-medium text-neutral-600 transition hover:bg-neutral-50 disabled:opacity-50"
                      >
                        Edit
                      </button>
                      <button
                        onclick={() => deletePhaseCostRow(row)}
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
          <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Cost Ledger (All Entries)</h2>
          <p class="mt-0.5 text-xs text-neutral-500">Showing {costStart}-{costEnd} of {filteredCostLedgerRows.length}</p>
        </div>
      </div>

      {#if filteredCostLedgerRows.length === 0}
        <div class="py-16 text-center text-sm text-neutral-400">No cost entries found for the current filters.</div>
      {:else}
        <div class="overflow-x-auto">
          <table class="w-full min-w-[1250px] text-sm">
            <thead>
              <tr class="border-b border-neutral-100 bg-neutral-50/80">
                <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Date</th>
                <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Project</th>
                <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Phase</th>
                <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Description</th>
                <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Category</th>
                <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Vendor</th>
                <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Reference</th>
                <th class="px-5 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Amount</th>
                <th class="px-5 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Action</th>
              </tr>
            </thead>

            <tbody class="divide-y divide-neutral-100">
              {#each costPageRows as row (row.key)}
                <tr class="bg-white hover:bg-neutral-50 transition-colors">
                  <td class="px-5 py-4 text-neutral-600">{fmtDate(row.date)}</td>
                  <td class="px-5 py-4 text-neutral-700">{row.projectName}</td>
                  <td class="px-5 py-4 text-neutral-700">{row.phaseName}</td>
                  <td class="px-5 py-4">
                    <p class="font-medium text-neutral-900">{row.description}</p>
                    <p class="mt-0.5 text-xs text-neutral-500">Entry #{row.costId}</p>
                  </td>
                  <td class="px-5 py-4">
                    <span class="inline-flex items-center rounded-full border border-neutral-200 bg-neutral-50 px-2.5 py-1 text-xs font-medium text-neutral-700 capitalize">
                      {row.category.replace("_", " ")}
                    </span>
                  </td>
                  <td class="px-5 py-4 text-neutral-700">{row.vendor || "--"}</td>
                  <td class="px-5 py-4 text-neutral-700">{row.referenceNumber || "--"}</td>
                  <td class="px-5 py-4 text-right font-medium text-neutral-900 tabular-nums">{fmtCurrency(row.amount)}</td>
                  <td class="px-5 py-4">
                    <div class="flex justify-end gap-2">
                      <button
                        onclick={() => openCostLedgerComments(row)}
                        disabled={actionLoading || actionSaving}
                        class="rounded-md border border-neutral-200 px-2.5 py-1.5 text-xs font-medium text-neutral-600 transition hover:bg-neutral-50 disabled:opacity-50"
                      >
                        Comments
                      </button>
                      <button
                        onclick={() => openCostLedgerEdit(row)}
                        disabled={actionLoading || actionSaving}
                        class="rounded-md border border-neutral-200 px-2.5 py-1.5 text-xs font-medium text-neutral-600 transition hover:bg-neutral-50 disabled:opacity-50"
                      >
                        Edit
                      </button>
                      <button
                        onclick={() => deleteCostLedgerEntry(row)}
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
          <p class="text-sm text-neutral-500">Page {costPage} of {costTotalPages}</p>
          <div class="flex items-center gap-1.5">
            <button
              onclick={() => (costPage = Math.max(1, costPage - 1))}
              disabled={costPage === 1}
              class="rounded-lg border border-neutral-200 px-2.5 py-1.5 text-sm text-neutral-600 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Prev
            </button>
            <button
              onclick={() => (costPage = Math.min(costTotalPages, costPage + 1))}
              disabled={costPage === costTotalPages}
              class="rounded-lg border border-neutral-200 px-2.5 py-1.5 text-sm text-neutral-600 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      {/if}
    </section>
  {/if}
</div>

{#if projectCommentingRow}
  <div class="fixed inset-0 z-40 flex items-center justify-center bg-neutral-900/40 p-4">
    <div class="w-full max-w-2xl rounded-xl border border-neutral-200 bg-white p-5 shadow-xl">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h3 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Project Comments</h3>
          <p class="mt-1 text-xs text-neutral-500">{projectCommentingRow.name}</p>
        </div>
        <button
          onclick={() => {
            projectCommentingRow = null;
            projectCommentText = "";
          }}
          class="rounded-md border border-neutral-200 px-2.5 py-1 text-xs font-medium text-neutral-600 hover:bg-neutral-50"
        >
          Close
        </button>
      </div>

      <label class="mt-4 block text-xs font-medium text-neutral-500">
        Notes
        <textarea
          bind:value={projectCommentText}
          rows={6}
          class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-900"
          placeholder="Add project comments..."
        ></textarea>
      </label>

      <div class="mt-4 flex justify-end gap-2">
        <button
          onclick={() => {
            projectCommentingRow = null;
            projectCommentText = "";
          }}
          class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-50"
        >
          Cancel
        </button>
        <button
          onclick={saveProjectComments}
          disabled={actionSaving}
          class="rounded-md bg-neutral-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
        >
          {actionSaving ? "Saving..." : "Save Comments"}
        </button>
      </div>
    </div>
  </div>
{/if}

{#if editingProjectRow}
  <div class="fixed inset-0 z-40 flex items-center justify-center bg-neutral-900/40 p-4">
    <div class="w-full max-w-xl rounded-xl border border-neutral-200 bg-white p-5 shadow-xl">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h3 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Edit Project</h3>
          <p class="mt-1 text-xs text-neutral-500">{editingProjectRow.name}</p>
        </div>
        <button
          onclick={() => {
            editingProjectRow = null;
          }}
          class="rounded-md border border-neutral-200 px-2.5 py-1 text-xs font-medium text-neutral-600 hover:bg-neutral-50"
        >
          Close
        </button>
      </div>

      <div class="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
        <label class="md:col-span-2 text-xs font-medium text-neutral-500">
          Project Name
          <input
            bind:value={editProjectForm.name}
            type="text"
            class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-900"
          />
        </label>
        <label class="text-xs font-medium text-neutral-500">
          Status
          <select
            bind:value={editProjectForm.status}
            class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-900"
          >
            <option value="planning">Planning</option>
            <option value="in_progress">In Progress</option>
            <option value="on_hold">On Hold</option>
            <option value="completed">Completed</option>
          </select>
        </label>
        <label class="text-xs font-medium text-neutral-500">
          Manager
          <input
            bind:value={editProjectForm.project_manager}
            type="text"
            class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-900"
          />
        </label>
        <label class="md:col-span-2 text-xs font-medium text-neutral-500">
          Total Project Budget
          <input
            bind:value={editProjectForm.budget}
            type="text"
            inputmode="decimal"
            class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-900"
          />
        </label>
      </div>

      <div class="mt-4 flex justify-end gap-2">
        <button
          onclick={() => {
            editingProjectRow = null;
          }}
          class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-50"
        >
          Cancel
        </button>
        <button
          onclick={saveProjectEdit}
          disabled={actionSaving}
          class="rounded-md bg-neutral-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
        >
          {actionSaving ? "Saving..." : "Save Changes"}
        </button>
      </div>
    </div>
  </div>
{/if}

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
          onclick={savePhaseCostComments}
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
          <p class="mt-1 text-xs text-neutral-500">{editingPhaseRow.projectName} • {editingPhaseRow.phaseName}</p>
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
          Phase Name
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
          Planned Budget
          <input
            bind:value={editPhaseForm.planned_budget}
            type="text"
            inputmode="decimal"
            class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-900"
          />
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
          onclick={savePhaseCostEdit}
          disabled={actionSaving}
          class="rounded-md bg-neutral-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
        >
          {actionSaving ? "Saving..." : "Save Changes"}
        </button>
      </div>
    </div>
  </div>
{/if}

{#if costCommentingRow}
  <div class="fixed inset-0 z-40 flex items-center justify-center bg-neutral-900/40 p-4">
    <div class="w-full max-w-2xl rounded-xl border border-neutral-200 bg-white p-5 shadow-xl">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h3 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Cost Entry Comments</h3>
          <p class="mt-1 text-xs text-neutral-500">Entry #{costCommentingRow.costId} • {costCommentingRow.projectName}</p>
        </div>
        <button
          onclick={() => {
            costCommentingRow = null;
            costCommentText = "";
          }}
          class="rounded-md border border-neutral-200 px-2.5 py-1 text-xs font-medium text-neutral-600 hover:bg-neutral-50"
        >
          Close
        </button>
      </div>

      <label class="mt-4 block text-xs font-medium text-neutral-500">
        Notes
        <textarea
          bind:value={costCommentText}
          rows={6}
          class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-900"
          placeholder="Add cost entry comments..."
        ></textarea>
      </label>

      <div class="mt-4 flex justify-end gap-2">
        <button
          onclick={() => {
            costCommentingRow = null;
            costCommentText = "";
          }}
          class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-50"
        >
          Cancel
        </button>
        <button
          onclick={saveCostLedgerComments}
          disabled={actionSaving}
          class="rounded-md bg-neutral-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
        >
          {actionSaving ? "Saving..." : "Save Comments"}
        </button>
      </div>
    </div>
  </div>
{/if}

{#if editingCostRow}
  <div class="fixed inset-0 z-40 flex items-center justify-center bg-neutral-900/40 p-4">
    <div class="w-full max-w-xl rounded-xl border border-neutral-200 bg-white p-5 shadow-xl">
      <div class="flex items-start justify-between gap-4">
        <div>
          <h3 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Edit Cost Entry</h3>
          <p class="mt-1 text-xs text-neutral-500">Entry #{editingCostRow.costId} • {editingCostRow.projectName}</p>
        </div>
        <button
          onclick={() => {
            editingCostRow = null;
          }}
          class="rounded-md border border-neutral-200 px-2.5 py-1 text-xs font-medium text-neutral-600 hover:bg-neutral-50"
        >
          Close
        </button>
      </div>

      <div class="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
        <label class="md:col-span-2 text-xs font-medium text-neutral-500">
          Description
          <input
            bind:value={editCostForm.description}
            type="text"
            class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-900"
          />
        </label>
        <label class="text-xs font-medium text-neutral-500">
          Date
          <DateInput bind:value={editCostForm.date} />
        </label>
        <label class="text-xs font-medium text-neutral-500">
          Category
          <select
            bind:value={editCostForm.category}
            class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-900"
          >
            <option value="materials">Materials</option>
            <option value="labor">Labor</option>
            <option value="permits">Permits</option>
            <option value="equipment">Equipment</option>
            <option value="subcontractor">Subcontractor</option>
            <option value="other">Other</option>
          </select>
        </label>
        <label class="text-xs font-medium text-neutral-500">
          Vendor
          <input
            bind:value={editCostForm.vendor}
            type="text"
            class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-900"
          />
        </label>
        <label class="text-xs font-medium text-neutral-500">
          Reference
          <input
            bind:value={editCostForm.reference_number}
            type="text"
            class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-900"
          />
        </label>
        <label class="md:col-span-2 text-xs font-medium text-neutral-500">
          Amount
          <input
            bind:value={editCostForm.amount}
            type="text"
            inputmode="decimal"
            class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-900"
          />
        </label>
      </div>

      <div class="mt-4 flex justify-end gap-2">
        <button
          onclick={() => {
            editingCostRow = null;
          }}
          class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-50"
        >
          Cancel
        </button>
        <button
          onclick={saveCostLedgerEdit}
          disabled={actionSaving}
          class="rounded-md bg-neutral-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
        >
          {actionSaving ? "Saving..." : "Save Changes"}
        </button>
      </div>
    </div>
  </div>
{/if}

<script lang="ts">
  import { ApiError, api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { useLiveKpis } from "$lib/realtime.svelte";
  import LiveBadge from "$lib/components/LiveBadge.svelte";
  import type {
    OrgChartAssignedUser,
    OrgChartDepartment,
    OrgChartDivision,
    OrgChartTeam,
  } from "$lib/types";

  type OrgChartDisplayTypeKey =
    | "top_down_tree"
    | "left_to_right_tree"
    | "swimlane"
    | "radial"
    | "matrix"
    | "network";

  type OrgChartDisplayType = {
    key: OrgChartDisplayTypeKey;
    name: string;
    description: string;
  };

  let divisions = $state<OrgChartDivision[]>([]);
  let loading = $state(true);
  let savingReportingLine = $state(false);
  let statusMessage = $state("");
  let statusError = $state("");

  let expandedDivisions = $state<Set<number>>(new Set());
  let expandedDepts = $state<Set<number>>(new Set());
  let expandedTeams = $state<Set<number>>(new Set());
  let expandedUsers = $state<Set<number>>(new Set());

  let dragUserId = $state<number | null>(null);
  let dropTargetUserId = $state<number | null>(null);
  let topLevelDropActive = $state(false);
  let activeDisplayType = $state<OrgChartDisplayTypeKey>("top_down_tree");
  let exportingDisplayType = $state<OrgChartDisplayTypeKey | "">("");

  const orgChartDisplayTypes: OrgChartDisplayType[] = [
    {
      key: "top_down_tree",
      name: "Top-Down Tree",
      description: "Classic hierarchical structure from leadership down to teams and roles.",
    },
    {
      key: "left_to_right_tree",
      name: "Left-to-Right Tree",
      description: "Horizontal hierarchy suited for wide organizational structures.",
    },
    {
      key: "swimlane",
      name: "Swimlane Chart",
      description: "Departments displayed in lanes with roles and reporting grouped by lane.",
    },
    {
      key: "radial",
      name: "Radial Chart",
      description: "Leadership at center with reporting lines radiating outward.",
    },
    {
      key: "matrix",
      name: "Matrix Chart",
      description: "Functional and project reporting overlays for dual-reporting teams.",
    },
    {
      key: "network",
      name: "Network Graph",
      description: "Node-link structure for cross-functional collaboration and acting roles.",
    },
  ];

  async function fetchOrgChart() {
    loading = true;
    statusError = "";
    try {
      divisions = await api.get<OrgChartDivision[]>("/hr/org-chart/");
      expandedDivisions = new Set(divisions.map((division) => division.id));
    } catch {
      divisions = [];
      statusError = "Unable to load the organizational chart.";
    } finally {
      loading = false;
    }
  }

  function toggleDivision(id: number) {
    const next = new Set(expandedDivisions);
    next.has(id) ? next.delete(id) : next.add(id);
    expandedDivisions = next;
  }

  function toggleDept(id: number) {
    const next = new Set(expandedDepts);
    next.has(id) ? next.delete(id) : next.add(id);
    expandedDepts = next;
  }

  function toggleTeam(id: number) {
    const next = new Set(expandedTeams);
    next.has(id) ? next.delete(id) : next.add(id);
    expandedTeams = next;
  }

  function toggleUserDetails(userId: number) {
    const next = new Set(expandedUsers);
    next.has(userId) ? next.delete(userId) : next.add(userId);
    expandedUsers = next;
  }

  function expandAll() {
    expandedDivisions = new Set(divisions.map((division) => division.id));
    const deptIds: number[] = [];
    const teamIds: number[] = [];
    for (const division of divisions) {
      for (const department of division.departments) {
        deptIds.push(department.id);
        for (const team of department.teams) {
          teamIds.push(team.id);
        }
      }
    }
    expandedDepts = new Set(deptIds);
    expandedTeams = new Set(teamIds);
  }

  function collapseAll() {
    expandedDivisions = new Set();
    expandedDepts = new Set();
    expandedTeams = new Set();
  }

  function formatEmploymentType(value: string): string {
    return value
      .split("_")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  }

  function statusTone(status: string): string {
    if (status === "completed") return "text-emerald-700 bg-emerald-100";
    if (status === "in_progress") return "text-amber-700 bg-amber-100";
    return "text-neutral-600 bg-neutral-200";
  }

  function employeeStatusTone(status: string): string {
    if (status === "vacant") return "text-rose-700 bg-rose-100";
    if (status === "acting") return "text-amber-700 bg-amber-100";
    return "text-emerald-700 bg-emerald-100";
  }

  function employeeStatusLabel(status: string): string {
    if (status === "vacant") return "Vacant";
    if (status === "acting") return "Acting";
    return "Assigned";
  }

  function getDraggedUserId(event: DragEvent): number | null {
    const primary = event.dataTransfer?.getData("application/x-org-user-id");
    const fallback = event.dataTransfer?.getData("text/plain");
    const raw = primary || fallback;
    if (!raw) return null;
    const parsed = Number(raw);
    if (!Number.isInteger(parsed) || parsed <= 0) return null;
    return parsed;
  }

  function handleNodeDragStart(event: DragEvent, userId: number) {
    if (savingReportingLine) return;
    dragUserId = userId;
    statusMessage = "";
    statusError = "";
    event.dataTransfer?.setData("application/x-org-user-id", String(userId));
    event.dataTransfer?.setData("text/plain", String(userId));
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = "move";
    }
  }

  function clearDragState() {
    dragUserId = null;
    dropTargetUserId = null;
    topLevelDropActive = false;
  }

  function handleManagerDragOver(event: DragEvent, managerUserId: number) {
    if (savingReportingLine) return;
    const incomingUserId = dragUserId ?? getDraggedUserId(event);
    if (!incomingUserId || incomingUserId === managerUserId) return;
    event.preventDefault();
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = "move";
    }
    dropTargetUserId = managerUserId;
    topLevelDropActive = false;
  }

  function handleManagerDragLeave(managerUserId: number) {
    if (dropTargetUserId === managerUserId) {
      dropTargetUserId = null;
    }
  }

  async function handleManagerDrop(event: DragEvent, managerUserId: number) {
    event.preventDefault();
    const incomingUserId = dragUserId ?? getDraggedUserId(event);
    clearDragState();
    if (!incomingUserId || incomingUserId === managerUserId) return;
    await assignReportingLine(incomingUserId, managerUserId);
  }

  function handleTopLevelDragOver(event: DragEvent) {
    if (savingReportingLine) return;
    const incomingUserId = dragUserId ?? getDraggedUserId(event);
    if (!incomingUserId) return;
    event.preventDefault();
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = "move";
    }
    topLevelDropActive = true;
    dropTargetUserId = null;
  }

  function handleTopLevelDragLeave() {
    topLevelDropActive = false;
  }

  async function handleTopLevelDrop(event: DragEvent) {
    event.preventDefault();
    const incomingUserId = dragUserId ?? getDraggedUserId(event);
    clearDragState();
    if (!incomingUserId) return;
    await assignReportingLine(incomingUserId, null);
  }

  async function assignReportingLine(userId: number, reportsTo: number | null) {
    savingReportingLine = true;
    statusMessage = "";
    statusError = "";
    try {
      await api.patch(`/hr/reporting-lines/${userId}/`, { reports_to: reportsTo });
      statusMessage = reportsTo
        ? "Reporting line updated successfully."
        : "Reporting line removed successfully.";
      await fetchOrgChart();
    } catch (error) {
      if (error instanceof ApiError) {
        const detail = typeof error.data.detail === "string" ? error.data.detail : "";
        statusError = detail || "Unable to update reporting line.";
      } else {
        statusError = "Unable to update reporting line.";
      }
    } finally {
      savingReportingLine = false;
    }
  }

  function orgChartSummary() {
    let departmentCount = 0;
    let teamCount = 0;
    let positionCount = 0;
    let vacantPositionCount = 0;
    for (const division of divisions) {
      departmentCount += division.departments.length;
      for (const department of division.departments) {
        teamCount += department.teams.length;
        positionCount += department.positions.length;
        vacantPositionCount += department.positions.filter((position) => position.is_vacant).length;
        for (const team of department.teams) {
          positionCount += team.positions.length;
          vacantPositionCount += team.positions.filter((position) => position.is_vacant).length;
        }
      }
    }
    return { departmentCount, teamCount, positionCount, vacantPositionCount };
  }

  function teamEmployeeCount(team: OrgChartTeam): number {
    return team.positions.reduce(
      (count, position) => count + position.assigned_users.length,
      0,
    );
  }

  function departmentMetrics(department: OrgChartDepartment) {
    const directPositionCount = department.positions.length;
    const directEmployeeCount = department.positions.reduce(
      (count, position) => count + position.assigned_users.length,
      0,
    );
    const directVacantCount = department.positions.filter(
      (position) => position.is_vacant,
    ).length;

    let teamPositionCount = 0;
    let teamEmployeeCountTotal = 0;
    let teamVacantCount = 0;
    for (const team of department.teams) {
      teamPositionCount += team.positions.length;
      teamEmployeeCountTotal += teamEmployeeCount(team);
      teamVacantCount += team.positions.filter((position) => position.is_vacant).length;
    }

    return {
      teamCount: department.teams.length,
      positionCount: directPositionCount + teamPositionCount,
      employeeCount: directEmployeeCount + teamEmployeeCountTotal,
      vacantCount: directVacantCount + teamVacantCount,
    };
  }

  function divisionMetrics(division: OrgChartDivision) {
    let teamCount = 0;
    let positionCount = 0;
    let employeeCount = 0;
    let vacantCount = 0;
    for (const department of division.departments) {
      const metrics = departmentMetrics(department);
      teamCount += metrics.teamCount;
      positionCount += metrics.positionCount;
      employeeCount += metrics.employeeCount;
      vacantCount += metrics.vacantCount;
    }
    return {
      departmentCount: division.departments.length,
      teamCount,
      positionCount,
      employeeCount,
      vacantCount,
    };
  }

  function selectedDisplayTypeName(key: OrgChartDisplayTypeKey): string {
    return orgChartDisplayTypes.find((mode) => mode.key === key)?.name ?? key;
  }

  function flattenOrgChartRows() {
    const rows: Array<{
      division: string;
      department: string;
      team: string;
      position: string;
      employee: string;
      employeeStatus: string;
      directReports: number;
      projectAssignments: number;
    }> = [];

    for (const division of divisions) {
      for (const department of division.departments) {
        for (const team of department.teams) {
          for (const position of team.positions) {
            if (position.assigned_users.length === 0) {
              rows.push({
                division: division.name,
                department: department.name,
                team: team.name,
                position: position.title,
                employee: "Vacant",
                employeeStatus: "vacant",
                directReports: 0,
                projectAssignments: 0,
              });
              continue;
            }

            for (const employee of position.assigned_users) {
              rows.push({
                division: division.name,
                department: department.name,
                team: team.name,
                position: position.title,
                employee: employee.name,
                employeeStatus: employee.is_acting ? "acting" : "assigned",
                directReports: employee.direct_report_count,
                projectAssignments: employee.project_assignment_count,
              });
            }
          }
        }

        for (const position of department.positions) {
          if (position.assigned_users.length === 0) {
            rows.push({
              division: division.name,
              department: department.name,
              team: "Direct Position",
              position: position.title,
              employee: "Vacant",
              employeeStatus: "vacant",
              directReports: 0,
              projectAssignments: 0,
            });
            continue;
          }

          for (const employee of position.assigned_users) {
            rows.push({
              division: division.name,
              department: department.name,
              team: "Direct Position",
              position: position.title,
              employee: employee.name,
              employeeStatus: employee.is_acting ? "acting" : "assigned",
              directReports: employee.direct_report_count,
              projectAssignments: employee.project_assignment_count,
            });
          }
        }
      }
    }

    return rows;
  }

  async function exportDisplayTypePdf(displayType: OrgChartDisplayTypeKey) {
    if (loading || exportingDisplayType) return;
    exportingDisplayType = displayType;

    try {
      const [{ jsPDF }, autoTableModule] = await Promise.all([
        import("jspdf"),
        import("jspdf-autotable"),
      ]);
      const autoTable = autoTableModule.default;
      const doc = new jsPDF({
        orientation: "landscape",
        unit: "pt",
        format: "a4",
      });

      const rows = flattenOrgChartRows();
      const summaryData = orgChartSummary();
      const displayTypeLabel = selectedDisplayTypeName(displayType);

      doc.setFontSize(14);
      doc.text("Organizational Chart Export", 24, 30);
      doc.setFontSize(10);
      doc.setTextColor(90);
      doc.text(`Display Type: ${displayTypeLabel}`, 24, 48);
      doc.text(`Generated: ${new Date().toLocaleString()}`, 24, 64);
      doc.text(
        `Departments: ${summaryData.departmentCount}   Teams: ${summaryData.teamCount}   Positions: ${summaryData.positionCount}   Vacant: ${summaryData.vacantPositionCount}`,
        24,
        80,
      );

      if (rows.length > 0) {
        autoTable(doc, {
          startY: 94,
          head: [[
            "Division",
            "Department",
            "Team/Unit",
            "Position",
            "Employee",
            "Status",
            "Direct Reports",
            "Projects",
          ]],
          body: rows.map((row) => [
            row.division,
            row.department,
            row.team,
            row.position,
            row.employee,
            row.employeeStatus,
            String(row.directReports),
            String(row.projectAssignments),
          ]),
          theme: "grid",
          styles: {
            fontSize: 8,
            cellPadding: 4,
          },
          headStyles: {
            fillColor: [17, 24, 39],
            textColor: 255,
            fontStyle: "bold",
          },
          alternateRowStyles: {
            fillColor: [249, 250, 251],
          },
          margin: { left: 20, right: 20 },
        });
      } else {
        doc.setTextColor(110);
        doc.text("No organizational rows to export.", 24, 110);
      }

      const dateStamp = new Date().toISOString().slice(0, 10);
      doc.save(`org-chart-${displayType}-${dateStamp}.pdf`);
      toast.success("PDF exported", `${displayTypeLabel} org chart PDF downloaded.`);
    } catch {
      toast.error("Export failed", "Unable to export org chart PDF.");
    } finally {
      exportingDisplayType = "";
    }
  }

  const levelBadge: Record<string, string> = {
    intern: "bg-neutral-100 text-neutral-500",
    junior: "bg-sky-100 text-sky-700",
    mid: "bg-indigo-100 text-indigo-700",
    senior: "bg-violet-100 text-violet-700",
    lead: "bg-amber-100 text-amber-700",
    manager: "bg-emerald-100 text-emerald-700",
    director: "bg-cyan-100 text-cyan-700",
    vp: "bg-teal-100 text-teal-700",
    c_suite: "bg-rose-100 text-rose-700",
  };

  const levelLabel: Record<string, string> = {
    intern: "Intern",
    junior: "Junior",
    mid: "Mid",
    senior: "Senior",
    lead: "Lead",
    manager: "Manager",
    director: "Director",
    vp: "VP",
    c_suite: "C-Suite",
  };

  $effect(() => {
    fetchOrgChart();
  });

  const live = useLiveKpis(
    ["Employee", "LeaveRequest"],
    fetchOrgChart,
    { debounceMs: 3000 },
  );

  const summary = $derived(orgChartSummary());
  const matrixRows = $derived(flattenOrgChartRows());
</script>

<div class="max-w-7xl mx-auto">

  <div class="flex flex-wrap items-start justify-between gap-4 mb-6">
    <div>
      <div class="flex items-center gap-2">
        <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-violet-600">Human Resources</p>
        <LiveBadge refreshing={live.refreshing} />
      </div>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Organizational Chart</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Drag an employee card onto another employee to update reporting lines.
      </p>
    </div>
    <div class="flex items-center gap-2">
      {#if activeDisplayType === "top_down_tree"}
        <button
          onclick={expandAll}
          class="px-3 py-1.5 text-xs font-medium text-neutral-600 bg-white border border-neutral-200 rounded-lg hover:bg-neutral-50 transition-colors"
        >Expand all</button>
        <button
          onclick={collapseAll}
          class="px-3 py-1.5 text-xs font-medium text-neutral-600 bg-white border border-neutral-200 rounded-lg hover:bg-neutral-50 transition-colors"
        >Collapse all</button>
      {:else}
        <span class="inline-flex items-center rounded-lg border border-neutral-200 bg-white px-3 py-1.5 text-xs font-medium text-neutral-600">
          View mode: {selectedDisplayTypeName(activeDisplayType)}
        </span>
      {/if}
    </div>
  </div>

  <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
    <div class="rounded-lg border border-sky-200 bg-sky-50 px-3 py-2">
      <p class="text-[11px] uppercase tracking-wide text-sky-700">Departments</p>
      <p class="text-lg font-semibold text-sky-900">{summary.departmentCount}</p>
    </div>
    <div class="rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2">
      <p class="text-[11px] uppercase tracking-wide text-indigo-700">Teams</p>
      <p class="text-lg font-semibold text-indigo-900">{summary.teamCount}</p>
    </div>
    <div class="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2">
      <p class="text-[11px] uppercase tracking-wide text-emerald-700">Positions</p>
      <p class="text-lg font-semibold text-emerald-900">{summary.positionCount}</p>
    </div>
    <div class="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2">
      <p class="text-[11px] uppercase tracking-wide text-rose-700">Vacant</p>
      <p class="text-lg font-semibold text-rose-900">{summary.vacantPositionCount}</p>
    </div>
  </div>

  <section class="mb-5 rounded-xl border border-neutral-200 bg-white p-4">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 class="text-sm font-semibold text-neutral-900">Org Chart Display Types</h2>
        <p class="mt-1 text-xs text-neutral-500">
          Select a display mode and export it to PDF.
        </p>
      </div>
      <button
        type="button"
        onclick={() => exportDisplayTypePdf(activeDisplayType)}
        disabled={loading || !!exportingDisplayType}
        class="inline-flex items-center gap-2 rounded-lg border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
      >
        {#if exportingDisplayType === activeDisplayType}
          Exporting...
        {:else}
          Export Active PDF
        {/if}
      </button>
    </div>

    <div class="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
      {#each orgChartDisplayTypes as displayType}
        <article class="rounded-lg border p-3 {activeDisplayType === displayType.key ? 'border-neutral-900 bg-neutral-50' : 'border-neutral-200 bg-white'}">
          <div class="flex items-start justify-between gap-2">
            <div>
              <h3 class="text-sm font-semibold text-neutral-900">{displayType.name}</h3>
              <p class="mt-1 text-xs leading-5 text-neutral-500">{displayType.description}</p>
            </div>
            {#if activeDisplayType === displayType.key}
              <span class="inline-flex rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider bg-neutral-900 text-white">Active</span>
            {/if}
          </div>

          <div class="mt-3 flex items-center gap-2">
            <button
              type="button"
              onclick={() => (activeDisplayType = displayType.key)}
              class="rounded-md border border-neutral-200 px-2.5 py-1 text-xs font-medium text-neutral-700 hover:bg-neutral-50 transition-colors"
            >
              Use Mode
            </button>
            <button
              type="button"
              onclick={() => exportDisplayTypePdf(displayType.key)}
              disabled={loading || !!exportingDisplayType}
              class="rounded-md border border-neutral-200 px-2.5 py-1 text-xs font-medium text-neutral-700 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50 transition-colors"
            >
              {#if exportingDisplayType === displayType.key}
                Exporting...
              {:else}
                Export PDF
              {/if}
            </button>
          </div>
        </article>
      {/each}
    </div>

    <p class="mt-3 text-[11px] text-neutral-400">
      Changing mode updates the on-screen chart and the exported PDF format.
    </p>
  </section>

  {#if activeDisplayType === "top_down_tree"}
    <div
      class="mb-5 rounded-lg border-2 border-dashed px-4 py-3 text-sm transition-colors {topLevelDropActive ? 'border-sky-400 bg-sky-50 text-sky-700' : 'border-neutral-200 bg-white text-neutral-500'}"
      role="region"
      aria-label="Top-level reporting line drop zone"
      ondragover={handleTopLevelDragOver}
      ondragleave={handleTopLevelDragLeave}
      ondrop={handleTopLevelDrop}
    >
      Drop here to clear a reporting line and place employee at top level.
    </div>
  {/if}

  {#if statusMessage}
    <p class="mb-3 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{statusMessage}</p>
  {/if}
  {#if statusError}
    <p class="mb-3 rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{statusError}</p>
  {/if}

  {#if loading}
    <div class="flex items-center justify-center py-24">
      <div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div>
    </div>
  {:else if divisions.length === 0}
    <div class="text-center py-20 rounded-xl border border-neutral-200 bg-white">
      <p class="text-sm text-neutral-500">No organizational data available.</p>
    </div>
  {:else if activeDisplayType === "top_down_tree"}
    <div class="space-y-4">
      {#each divisions as division}
        <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
          <button
            onclick={() => toggleDivision(division.id)}
            class="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-neutral-50 transition-colors"
          >
            <svg class="w-4 h-4 text-neutral-400 shrink-0 transition-transform {expandedDivisions.has(division.id) ? 'rotate-90' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" /></svg>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <span class="font-semibold text-neutral-900">{division.name}</span>
                {#if division.code}
                  <span class="text-xs font-mono text-neutral-400">{division.code}</span>
                {/if}
              </div>
              {#if division.head_name}
                <p class="text-xs text-neutral-500 mt-0.5">Head: {division.head_name}</p>
              {/if}
            </div>
            <span class="text-xs text-neutral-400">{division.departments.length} dept{division.departments.length !== 1 ? "s" : ""}</span>
          </button>

          {#if expandedDivisions.has(division.id)}
            <div class="border-t border-neutral-100">
              {#each division.departments as department}
                <div class="ml-6 border-l-2 border-neutral-200">
                  <button
                    onclick={() => toggleDept(department.id)}
                    class="w-full flex items-center gap-3 px-5 py-3 text-left hover:bg-neutral-50 transition-colors"
                  >
                    <svg class="w-3.5 h-3.5 text-neutral-400 shrink-0 transition-transform {expandedDepts.has(department.id) ? 'rotate-90' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" /></svg>
                    <div class="flex-1 min-w-0">
                      <div class="flex items-center gap-2">
                        <span class="font-medium text-neutral-800 text-sm">{department.name}</span>
                        {#if department.code}
                          <span class="text-xs font-mono text-neutral-400">{department.code}</span>
                        {/if}
                      </div>
                      {#if department.head_name}
                        <p class="text-xs text-neutral-500 mt-0.5">Head: {department.head_name}</p>
                      {/if}
                    </div>
                    <span class="text-xs text-neutral-400">{department.teams.length} team{department.teams.length !== 1 ? "s" : ""}</span>
                  </button>

                  {#if expandedDepts.has(department.id)}
                    <div class="border-t border-neutral-50 pb-3">
                      {#each department.teams as team}
                        <div class="ml-6 border-l-2 border-neutral-100">
                          <button
                            onclick={() => toggleTeam(team.id)}
                            class="w-full flex items-center gap-3 px-5 py-2.5 text-left hover:bg-neutral-50 transition-colors"
                          >
                            <svg class="w-3 h-3 text-neutral-300 shrink-0 transition-transform {expandedTeams.has(team.id) ? 'rotate-90' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" /></svg>
                            <div class="flex-1 min-w-0">
                              <span class="text-sm text-neutral-700">{team.name}</span>
                              {#if team.lead_name}
                                <span class="text-xs text-neutral-400 ml-2">Lead: {team.lead_name}</span>
                              {/if}
                            </div>
                            <span class="text-xs text-neutral-400">{team.positions.length} position{team.positions.length !== 1 ? "s" : ""}</span>
                          </button>

                          {#if expandedTeams.has(team.id)}
                            <div class="ml-8 space-y-2 pb-3 pr-4">
                              {#each team.positions as position}
                                <div class="rounded-lg border p-3 {position.is_vacant ? 'border-rose-300 bg-rose-50' : 'border-neutral-200 bg-neutral-50'}">
                                  <div class="flex flex-wrap items-center justify-between gap-2">
                                    <div class="flex items-center gap-2">
                                      <span class="font-medium text-neutral-900 text-sm">{position.title}</span>
                                      {#if position.code}
                                        <span class="font-mono text-[11px] text-neutral-500">{position.code}</span>
                                      {/if}
                                    </div>
                                    <div class="flex items-center gap-2">
                                      <span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium {levelBadge[position.level] ?? 'bg-neutral-100 text-neutral-500'}">{levelLabel[position.level] ?? position.level}</span>
                                      <span class="text-[11px] text-neutral-500">{formatEmploymentType(position.employment_type)}</span>
                                      {#if position.is_vacant}
                                        <span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-rose-100 text-rose-700">Vacant</span>
                                      {/if}
                                    </div>
                                  </div>

                                  {#if position.assigned_users.length === 0}
                                    <p class="mt-2 text-xs text-rose-700">No active employee assigned.</p>
                                  {:else}
                                    <div class="mt-2 space-y-2">
                                      {#each position.assigned_users as employee}
                                        {@render OrgNode({
                                          employee,
                                          savingReportingLine,
                                          dragUserId,
                                          dropTargetUserId,
                                          expandedUsers,
                                          statusTone,
                                          onToggleDetails: toggleUserDetails,
                                          onDragStart: handleNodeDragStart,
                                          onDragEnd: clearDragState,
                                          onDragOver: handleManagerDragOver,
                                          onDragLeave: handleManagerDragLeave,
                                          onDrop: handleManagerDrop,
                                        })}
                                      {/each}
                                    </div>
                                  {/if}
                                </div>
                              {/each}
                            </div>
                          {/if}
                        </div>
                      {/each}

                      {#if department.positions.length > 0}
                        <div class="ml-6 pr-4">
                          <p class="mt-2 mb-2 text-xs font-medium text-neutral-400 uppercase tracking-wider">Direct Positions</p>
                          <div class="space-y-2">
                            {#each department.positions as position}
                              <div class="rounded-lg border p-3 {position.is_vacant ? 'border-rose-300 bg-rose-50' : 'border-neutral-200 bg-neutral-50'}">
                                <div class="flex flex-wrap items-center justify-between gap-2">
                                  <div class="flex items-center gap-2">
                                    <span class="font-medium text-neutral-900 text-sm">{position.title}</span>
                                    {#if position.code}
                                      <span class="font-mono text-[11px] text-neutral-500">{position.code}</span>
                                    {/if}
                                  </div>
                                  <div class="flex items-center gap-2">
                                    <span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium {levelBadge[position.level] ?? 'bg-neutral-100 text-neutral-500'}">{levelLabel[position.level] ?? position.level}</span>
                                    <span class="text-[11px] text-neutral-500">{formatEmploymentType(position.employment_type)}</span>
                                    {#if position.is_vacant}
                                      <span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-rose-100 text-rose-700">Vacant</span>
                                    {/if}
                                  </div>
                                </div>

                                {#if position.assigned_users.length === 0}
                                  <p class="mt-2 text-xs text-rose-700">No active employee assigned.</p>
                                {:else}
                                  <div class="mt-2 space-y-2">
                                    {#each position.assigned_users as employee}
                                      {@render OrgNode({
                                        employee,
                                        savingReportingLine,
                                        dragUserId,
                                        dropTargetUserId,
                                        expandedUsers,
                                        statusTone,
                                        onToggleDetails: toggleUserDetails,
                                        onDragStart: handleNodeDragStart,
                                        onDragEnd: clearDragState,
                                        onDragOver: handleManagerDragOver,
                                        onDragLeave: handleManagerDragLeave,
                                        onDrop: handleManagerDrop,
                                      })}
                                    {/each}
                                  </div>
                                {/if}
                              </div>
                            {/each}
                          </div>
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
    </div>
  {:else if activeDisplayType === "left_to_right_tree"}
    <div class="overflow-x-auto pb-1">
      <div class="inline-flex min-w-full items-start gap-4">
        {#each divisions as division}
          {@const metrics = divisionMetrics(division)}
          <section class="w-[320px] shrink-0 overflow-hidden rounded-xl border border-neutral-200 bg-white">
            <header class="border-b border-neutral-100 px-4 py-3">
              <p class="text-sm font-semibold text-neutral-900">{division.name}</p>
              <p class="mt-1 text-xs text-neutral-500">
                {metrics.departmentCount} departments · {metrics.employeeCount} staff
              </p>
            </header>
            <div class="space-y-3 p-3">
              {#each division.departments as department}
                {@const departmentSummary = departmentMetrics(department)}
                <article class="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
                  <div class="flex items-start justify-between gap-2">
                    <h3 class="text-xs font-semibold text-neutral-900">{department.name}</h3>
                    <span class="text-[11px] text-neutral-500">
                      {departmentSummary.employeeCount} staff
                    </span>
                  </div>
                  <p class="mt-1 text-[11px] text-neutral-500">
                    {departmentSummary.positionCount} positions · {departmentSummary.teamCount} teams · {departmentSummary.vacantCount} vacant
                  </p>
                  <div class="mt-2 flex flex-wrap gap-1.5">
                    {#if department.teams.length === 0}
                      <span class="inline-flex rounded bg-neutral-200 px-2 py-0.5 text-[10px] text-neutral-600">
                        No teams configured
                      </span>
                    {:else}
                      {#each department.teams as team}
                        <span class="inline-flex rounded border border-neutral-200 bg-white px-2 py-0.5 text-[10px] text-neutral-600">
                          {team.name} ({team.positions.length})
                        </span>
                      {/each}
                    {/if}
                  </div>
                </article>
              {/each}
            </div>
          </section>
        {/each}
      </div>
    </div>
  {:else if activeDisplayType === "swimlane"}
    <div class="space-y-4">
      {#each divisions as division}
        <section class="overflow-hidden rounded-xl border border-neutral-200 bg-white">
          <header class="border-b border-neutral-100 px-4 py-3">
            <h2 class="text-sm font-semibold text-neutral-900">{division.name}</h2>
            <p class="mt-1 text-xs text-neutral-500">
              Department lanes with teams grouped by work stream.
            </p>
          </header>
          <div class="space-y-2 p-3">
            {#each division.departments as department}
              {@const departmentSummary = departmentMetrics(department)}
              <article class="grid gap-2 rounded-lg border border-neutral-200 bg-neutral-50 p-3 md:grid-cols-[220px_1fr]">
                <div>
                  <h3 class="text-xs font-semibold text-neutral-900">{department.name}</h3>
                  <p class="mt-1 text-[11px] text-neutral-500">
                    {departmentSummary.positionCount} positions · {departmentSummary.employeeCount} assigned
                  </p>
                </div>
                <div class="flex flex-wrap gap-2">
                  {#if department.teams.length === 0}
                    <span class="inline-flex items-center rounded border border-neutral-200 bg-white px-2 py-1 text-[11px] text-neutral-500">
                      No teams configured
                    </span>
                  {:else}
                    {#each department.teams as team}
                      <div class="rounded-md border border-neutral-200 bg-white px-2 py-1.5 text-xs">
                        <p class="font-medium text-neutral-800">{team.name}</p>
                        <p class="text-neutral-500">
                          {team.positions.length} positions · {teamEmployeeCount(team)} assigned
                        </p>
                      </div>
                    {/each}
                  {/if}
                </div>
              </article>
            {/each}
          </div>
        </section>
      {/each}
    </div>
  {:else if activeDisplayType === "radial"}
    <div class="rounded-xl border border-neutral-200 bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.16),transparent_55%),radial-gradient(circle_at_bottom,rgba(167,139,250,0.14),transparent_60%)] p-6">
      <div class="mx-auto flex h-36 w-36 items-center justify-center rounded-full border border-neutral-900 bg-neutral-900 text-center text-white shadow-sm">
        <div>
          <p class="text-xs uppercase tracking-[0.18em] text-neutral-300">Center</p>
          <p class="mt-1 text-sm font-semibold">Organization</p>
        </div>
      </div>
      <div class="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {#each divisions as division}
          {@const metrics = divisionMetrics(division)}
          <article class="rounded-lg border border-neutral-200 bg-white/90 p-3 shadow-sm backdrop-blur">
            <h3 class="text-sm font-semibold text-neutral-900">{division.name}</h3>
            <p class="mt-1 text-xs text-neutral-500">
              {metrics.departmentCount} departments · {metrics.teamCount} teams
            </p>
            <div class="mt-2 grid grid-cols-2 gap-2 text-[11px] text-neutral-600">
              <p>Positions: <span class="font-semibold text-neutral-800">{metrics.positionCount}</span></p>
              <p>Assigned: <span class="font-semibold text-neutral-800">{metrics.employeeCount}</span></p>
              <p>Vacant: <span class="font-semibold text-rose-700">{metrics.vacantCount}</span></p>
              <p>Head: <span class="font-semibold text-neutral-800">{division.head_name ?? "N/A"}</span></p>
            </div>
          </article>
        {/each}
      </div>
    </div>
  {:else if activeDisplayType === "matrix"}
    <div class="overflow-x-auto rounded-xl border border-neutral-200 bg-white">
      <table class="min-w-full divide-y divide-neutral-200 text-xs">
        <thead class="bg-neutral-50 text-neutral-600">
          <tr>
            <th class="px-3 py-2 text-left font-semibold">Division</th>
            <th class="px-3 py-2 text-left font-semibold">Department</th>
            <th class="px-3 py-2 text-left font-semibold">Team / Unit</th>
            <th class="px-3 py-2 text-left font-semibold">Position</th>
            <th class="px-3 py-2 text-left font-semibold">Employee</th>
            <th class="px-3 py-2 text-left font-semibold">Status</th>
            <th class="px-3 py-2 text-left font-semibold">Direct Reports</th>
            <th class="px-3 py-2 text-left font-semibold">Projects</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#if matrixRows.length === 0}
            <tr>
              <td colspan="8" class="px-3 py-6 text-center text-neutral-500">No rows available.</td>
            </tr>
          {:else}
            {#each matrixRows as row}
              <tr class="hover:bg-neutral-50">
                <td class="px-3 py-2 text-neutral-700">{row.division}</td>
                <td class="px-3 py-2 text-neutral-700">{row.department}</td>
                <td class="px-3 py-2 text-neutral-700">{row.team}</td>
                <td class="px-3 py-2 text-neutral-700">{row.position}</td>
                <td class="px-3 py-2 text-neutral-800 font-medium">{row.employee}</td>
                <td class="px-3 py-2">
                  <span class="inline-flex rounded px-1.5 py-0.5 text-[10px] font-semibold {employeeStatusTone(row.employeeStatus)}">
                    {employeeStatusLabel(row.employeeStatus)}
                  </span>
                </td>
                <td class="px-3 py-2 text-neutral-700">{row.directReports}</td>
                <td class="px-3 py-2 text-neutral-700">{row.projectAssignments}</td>
              </tr>
            {/each}
          {/if}
        </tbody>
      </table>
    </div>
  {:else}
    <div class="space-y-4">
      {#each divisions as division}
        {@const metrics = divisionMetrics(division)}
        <section class="rounded-xl border border-neutral-200 bg-white p-4">
          <div class="flex flex-wrap items-center justify-between gap-2">
            <div class="inline-flex items-center gap-2 rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-xs font-semibold text-sky-700">
              <span class="h-2 w-2 rounded-full bg-sky-500"></span>
              {division.name}
            </div>
            <p class="text-xs text-neutral-500">
              {metrics.departmentCount} connections · {metrics.employeeCount} members
            </p>
          </div>
          <div class="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {#each division.departments as department}
              {@const departmentSummary = departmentMetrics(department)}
              <article class="relative rounded-lg border border-neutral-200 bg-neutral-50 p-3">
                <span class="absolute -left-2 top-1/2 hidden h-px w-2 bg-neutral-300 xl:block"></span>
                <p class="text-xs font-semibold text-neutral-900">{department.name}</p>
                <p class="mt-1 text-[11px] text-neutral-500">
                  {departmentSummary.employeeCount} staff · {departmentSummary.teamCount} teams
                </p>
                <div class="mt-2 flex flex-wrap gap-1">
                  {#each department.teams as team}
                    <span class="inline-flex rounded border border-neutral-200 bg-white px-1.5 py-0.5 text-[10px] text-neutral-600">
                      {team.name}
                    </span>
                  {/each}
                </div>
              </article>
            {/each}
          </div>
        </section>
      {/each}
    </div>
  {/if}
</div>

{#snippet OrgNode({
  employee,
  savingReportingLine,
  dragUserId,
  dropTargetUserId,
  expandedUsers,
  statusTone,
  onToggleDetails,
  onDragStart,
  onDragEnd,
  onDragOver,
  onDragLeave,
  onDrop,
}: {
  employee: OrgChartAssignedUser;
  savingReportingLine: boolean;
  dragUserId: number | null;
  dropTargetUserId: number | null;
  expandedUsers: Set<number>;
  statusTone: (status: string) => string;
  onToggleDetails: (userId: number) => void;
  onDragStart: (event: DragEvent, userId: number) => void;
  onDragEnd: () => void;
  onDragOver: (event: DragEvent, userId: number) => void;
  onDragLeave: (userId: number) => void;
  onDrop: (event: DragEvent, userId: number) => Promise<void>;
})}
  <div
    draggable={!savingReportingLine}
    role="group"
    aria-label="Employee org chart node"
    ondragstart={(event) => onDragStart(event, employee.id)}
    ondragend={onDragEnd}
    ondragover={(event) => onDragOver(event, employee.id)}
    ondragleave={() => onDragLeave(employee.id)}
    ondrop={(event) => onDrop(event, employee.id)}
    class="rounded-md border p-2.5 bg-white transition-colors {dropTargetUserId === employee.id ? 'border-sky-500 bg-sky-50' : dragUserId === employee.id ? 'border-indigo-300 bg-indigo-50' : 'border-neutral-200'}"
  >
    <div class="flex flex-wrap items-start justify-between gap-2">
      <div>
        <p class="text-sm font-semibold text-neutral-800">{employee.name}</p>
        <p class="text-xs text-neutral-500">{employee.title} · {employee.department_name}</p>
      </div>
      <div class="flex items-center gap-1">
        {#if employee.is_acting}
          <span class="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold bg-amber-100 text-amber-700">Acting</span>
        {/if}
        {#if employee.project_assignment_count > 0}
          <span class="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold bg-sky-100 text-sky-700">{employee.project_assignment_count} projects</span>
        {/if}
      </div>
    </div>

    <div class="mt-2 grid grid-cols-1 md:grid-cols-2 gap-1.5 text-xs text-neutral-600">
      <p>Direct reports: <span class="font-semibold text-neutral-800">{employee.direct_report_count}</span></p>
      <p>{employee.email || "No email"}</p>
      <p>{employee.phone || "No phone"}</p>
      <p>{employee.office_location || "No location"}</p>
    </div>

    <button
      type="button"
      onclick={() => onToggleDetails(employee.id)}
      class="mt-2 text-[11px] font-medium text-neutral-600 hover:text-neutral-900"
    >
      {expandedUsers.has(employee.id) ? "Hide details" : "Show details"}
    </button>

    {#if expandedUsers.has(employee.id)}
      <div class="mt-2 rounded-md border border-neutral-200 bg-neutral-50 p-2.5">
        <dl class="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
          <div>
            <dt class="text-neutral-500">Salary band</dt>
            <dd class="text-neutral-800">{employee.salary_band ?? "Not configured"}</dd>
          </div>
          <div>
            <dt class="text-neutral-500">Employment type</dt>
            <dd class="text-neutral-800">{employee.employment_type.split("_").map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(" ")}</dd>
          </div>
          <div>
            <dt class="text-neutral-500">Location</dt>
            <dd class="text-neutral-800">{employee.office_location || "Not set"}</dd>
          </div>
          <div>
            <dt class="text-neutral-500">Acting roles</dt>
            <dd class="text-neutral-800">{employee.acting_roles.length ? employee.acting_roles.join(", ") : "None"}</dd>
          </div>
        </dl>

        <div class="mt-2">
          <p class="text-[11px] font-medium text-neutral-500 mb-1">Project assignments</p>
          {#if employee.project_assignments.length === 0}
            <p class="text-xs text-neutral-500">No linked assignments.</p>
          {:else}
            <div class="space-y-1.5">
              {#each employee.project_assignments as assignment}
                <div class="rounded border border-neutral-200 bg-white px-2 py-1.5 text-xs">
                  <p class="font-medium text-neutral-700">{assignment.project_name}</p>
                  <p class="text-neutral-600">{assignment.task_name}</p>
                  <div class="mt-1 flex flex-wrap items-center gap-1">
                    <span class="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-medium {statusTone(assignment.status)}">{assignment.status.replace("_", " ")}</span>
                    {#if assignment.due_date}
                      <span class="text-[10px] text-neutral-500">Due {assignment.due_date}</span>
                    {/if}
                  </div>
                </div>
              {/each}
            </div>
          {/if}
        </div>
      </div>
    {/if}
  </div>
{/snippet}

<script lang="ts">
  import { goto } from "$app/navigation";
  import { onMount } from "svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import { fetchAllPages, toAmount } from "$lib/contracts";
  import { api } from "$lib/api";
  import { PREVIEW_PAYROLL_DASHBOARD_DATA, PREVIEW_PAYSLIP_DETAILS } from "$lib/payrollDashboardPreview";
  import PayslipPreview from "$lib/components/payroll/PayslipPreview.svelte";
  import BankExport from "$lib/components/payroll/BankExport.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import { useLiveKpis } from "$lib/realtime.svelte";
  import LiveBadge from "$lib/components/LiveBadge.svelte";
  import type {
    BonusListItem,
    DeductionListItem,
    EmployeeDirectoryItem,
    PayslipDetail,
    PayslipListItem,
    PayrollRunListItem,
    ProjectListItem,
    ProjectWorkforceLog,
    TaxRecordListItem,
  } from "$lib/types";

  type LoadMode = "live" | "preview";
  type AllocationStatus = "verified" | "pending" | "approved" | "processing" | "review";
  type PaymentStageKey = "pending" | "processing" | "disbursed";

  type AllocationRow = {
    id: string;
    label: string;
    role: string;
    primaryProject: string;
    projectLocation: string;
    monthlyNet: number;
    allocationPercent: number | null;
    status: AllocationStatus;
    statusLabel: string;
    notes: string;
    tags: string[];
    payslipId: number | null;
    headcount: number;
    estimated: boolean;
  };

  type BatchControl = {
    title: string;
    description: string;
    total: number;
    countLabel: string;
    tone: "good" | "warn" | "review" | "neutral";
    footnote: string;
    ctaLabel: string;
    ctaHref: string;
  };

  type WorkflowStage = {
    label: string;
    description: string;
    value: string;
    state: "complete" | "active" | "blocked";
    tone: "good" | "warn" | "review" | "neutral";
  };

  type ProjectBreakdown = {
    name: string;
    value: number;
    ratio: number;
    color: string;
    location: string;
  };

  type BurnInsight = {
    projectName: string;
    location: string;
    monthlyLabor: number;
    budget: number;
    ratio: number;
    modeledVariance: number;
    overtimeHours: number;
    alert: string | null;
    trend: number[];
    tone: "good" | "warn" | "review";
  };

  type BankExportRow = {
    employeeName: string;
    employeeId: string;
    amount: number;
    narration: string;
    projectName: string;
    runName: string;
    bankName: string;
    accountNumber: string;
    accountType: string;
    bankCode: string;
  };

  const MAX_PAGES = 10;
  const AUTO_REFRESH_MS = 60_000;
  const LABOR_MODEL_SHARE = 0.12;
  const CREW_NET_FACTOR = 0.38;
  const HQ_HINTS = ["hq", "head office", "office", "admin", "finance"];
  const MANAGEMENT_HINTS = ["manager", "lead", "director", "head"];
  const ACTIVE_EMPLOYMENT_STATUSES = new Set(["active", "probation", "notice_period", "on_leave"]);
  const PROJECT_COLORS = ["#111827", "#0f766e", "#f97316", "#ec4899", "#2563eb", "#7c3aed"];

  let loading = $state(true);
  let refreshing = $state(false);
  let loadMessage = $state("");
  let dataMode = $state<LoadMode>("live");
  let lastSyncedAt = $state<Date | null>(null);

  let employees = $state<EmployeeDirectoryItem[]>([]);
  let payrollRuns = $state<PayrollRunListItem[]>([]);
  let payslips = $state<PayslipListItem[]>([]);
  let taxRecords = $state<TaxRecordListItem[]>([]);
  let deductions = $state<DeductionListItem[]>([]);
  let bonuses = $state<BonusListItem[]>([]);
  let workforceLogs = $state<ProjectWorkforceLog[]>([]);
  let projects = $state<ProjectListItem[]>([]);

  let payslipPreviewOpen = $state(false);
  let selectedPayslip = $state<PayslipDetail | null>(null);
  let selectedEmployeeLabel = $state("");
  let selectedProjectLabel = $state("");
  let previewLoading = $state(false);

  let refreshTimer: ReturnType<typeof setInterval> | null = null;

  function isLocalPreviewAllowed(): boolean {
    if (typeof window === "undefined") return false;
    return ["localhost", "127.0.0.1"].includes(window.location.hostname);
  }

  function getSettledValue<T>(result: PromiseSettledResult<T>, fallback: T): T {
    return result.status === "fulfilled" ? result.value : fallback;
  }

  function parseDate(value: string | null | undefined): Date | null {
    if (!value) return null;
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  function monthKey(value: string | null | undefined): string {
    return value ? value.slice(0, 7) : "";
  }

  function monthLabel(key: string): string {
    if (!key) return "Current Period";
    const [year, month] = key.split("-").map(Number);
    const date = new Date(year, (month || 1) - 1, 1);
    return new Intl.DateTimeFormat("en-NG", {
      month: "long",
      year: "numeric",
    }).format(date);
  }

  function shortDate(value: string | null | undefined): string {
    const date = parseDate(value);
    if (!date) return "N/A";
    return new Intl.DateTimeFormat("en-NG", {
      day: "numeric",
      month: "short",
    }).format(date);
  }

  function formatCurrency(value: number, digits = 0): string {
    return new Intl.NumberFormat("en-NG", {
      style: "currency",
      currency: currency.config.code || "NGN",
      minimumFractionDigits: digits,
      maximumFractionDigits: digits === 0 ? 0 : 2,
    }).format(Number.isFinite(value) ? value : 0);
  }

  function formatPercent(value: number, digits = 0): string {
    return `${value.toFixed(digits)}%`;
  }

  function isHqLocation(location: string | null | undefined): boolean {
    const normalized = (location ?? "").trim().toLowerCase();
    return HQ_HINTS.some((hint) => normalized.includes(hint));
  }

  function isManagementRole(role: string | null | undefined): boolean {
    const normalized = (role ?? "").trim().toLowerCase();
    return MANAGEMENT_HINTS.some((hint) => normalized.includes(hint));
  }

  function monthsBetween(start: string | null | undefined, end: string | null | undefined): number {
    const startDate = parseDate(start);
    const endDate = parseDate(end) ?? new Date();
    if (!startDate) return 12;
    const total = (endDate.getFullYear() - startDate.getFullYear()) * 12 + (endDate.getMonth() - startDate.getMonth()) + 1;
    return Math.max(1, total);
  }

  function modeledMonthlyLaborBudget(project: ProjectListItem | undefined): number {
    if (!project) return 0;
    const budget = toAmount(project.budget);
    if (budget <= 0) return 0;
    return (budget * LABOR_MODEL_SHARE) / monthsBetween(project.start_date, project.target_end_date ?? project.actual_end_date);
  }

  function computeTimelineMonths(count = 6): string[] {
    const months: string[] = [];
    const cursor = new Date();
    cursor.setDate(1);
    for (let index = count - 1; index >= 0; index -= 1) {
      const current = new Date(cursor);
      current.setMonth(cursor.getMonth() - index);
      months.push(current.toISOString().slice(0, 7));
    }
    return months;
  }

  function relativeSyncLabel(date: Date | null): string {
    if (!date) return "Never";
    const elapsed = Date.now() - date.getTime();
    if (elapsed < 60_000) return "Just now";
    if (elapsed < 3_600_000) return `${Math.round(elapsed / 60_000)} min ago`;
    return `${Math.round(elapsed / 3_600_000)} hr ago`;
  }

  function buildSparkline(points: number[]): string {
    if (!points.length) return "";
    const max = Math.max(...points, 1);
    const min = Math.min(...points);
    const range = max - min || 1;
    return points
      .map((point, index) => {
        const x = points.length === 1 ? 50 : (index / (points.length - 1)) * 100;
        const y = 30 - (((point - min) / range) * 22 + 4);
        return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
      })
      .join(" ");
  }

  function deriveStatus(
    payrollStatus: ProjectWorkforceLog["payroll_status"] | "group",
    payslipStatus: PayslipListItem["status"] | null,
    anonymous = false,
  ): { key: AllocationStatus; label: string } {
    if (anonymous && payrollStatus === "not_linked") return { key: "review", label: "Manual Review" };
    if (payrollStatus === "pending" || payslipStatus === "draft") return { key: "pending", label: "Pending" };
    if (payslipStatus === "generated") return { key: "processing", label: "Processing" };
    if (payslipStatus === "sent") return { key: "approved", label: "Approved" };
    if (payslipStatus === "acknowledged") return { key: "verified", label: "Verified" };
    if (payrollStatus === "group") return { key: "processing", label: "Processing" };
    return { key: "verified", label: "Verified" };
  }

  function aggregateGroupStatus(groupPayslips: PayslipListItem[]): { key: AllocationStatus; label: string } {
    if (groupPayslips.some((item) => item.status === "draft")) return { key: "pending", label: "Pending" };
    if (groupPayslips.some((item) => item.status === "generated")) return { key: "processing", label: "Processing" };
    if (groupPayslips.some((item) => item.status === "sent")) return { key: "approved", label: "Approved" };
    return { key: "verified", label: "Verified" };
  }

  function statusClasses(status: AllocationStatus): string {
    if (status === "verified") return "bg-emerald-100 text-emerald-700 border border-emerald-200";
    if (status === "approved") return "bg-emerald-50 text-emerald-700 border border-emerald-200";
    if (status === "pending") return "bg-orange-100 text-orange-700 border border-orange-200";
    if (status === "review") return "bg-sky-100 text-sky-700 border border-sky-200";
    return "bg-neutral-100 text-neutral-700 border border-neutral-200";
  }

  function stageClasses(state: WorkflowStage["state"], tone: WorkflowStage["tone"]): string {
    if (state === "blocked") return "border-orange-200 bg-orange-50";
    if (tone === "good") return "border-emerald-200 bg-emerald-50";
    if (tone === "review") return "border-sky-200 bg-sky-50";
    return "border-neutral-200 bg-white";
  }

  function segmentClasses(stage: { active: boolean; complete: boolean }): string {
    if (stage.complete) return "bg-emerald-500 text-white";
    if (stage.active) return "bg-neutral-900 text-white";
    return "bg-neutral-50 text-neutral-400 border border-neutral-200";
  }

  async function loadDashboard(background = false) {
    if (background) {
      refreshing = true;
    } else {
      loading = true;
    }

    const results = await Promise.allSettled([
      fetchAllPages<EmployeeDirectoryItem>("/hr/employee-records/", { page_size: "200" }, MAX_PAGES),
      fetchAllPages<PayrollRunListItem>("/hr/payroll-runs/", { page_size: "200" }, MAX_PAGES),
      fetchAllPages<PayslipListItem>("/hr/payslips/", { page_size: "200" }, MAX_PAGES),
      fetchAllPages<TaxRecordListItem>("/hr/tax-records/", { page_size: "200" }, MAX_PAGES),
      fetchAllPages<DeductionListItem>("/hr/deductions/", { page_size: "200" }, MAX_PAGES),
      fetchAllPages<BonusListItem>("/hr/bonuses/", { page_size: "200" }, MAX_PAGES),
      fetchAllPages<ProjectWorkforceLog>("/projects/field-operations/workforce/", { page_size: "200" }, MAX_PAGES),
      fetchAllPages<ProjectListItem>("/projects/", { page_size: "200", ordering: "name" }, MAX_PAGES),
    ]);

    const liveEmployees = getSettledValue(results[0], []);
    const liveRuns = getSettledValue(results[1], []);
    const livePayslips = getSettledValue(results[2], []);
    const liveTaxRecords = getSettledValue(results[3], []);
    const liveDeductions = getSettledValue(results[4], []);
    const liveBonuses = getSettledValue(results[5], []);
    const liveWorkforce = getSettledValue(results[6], []);
    const liveProjects = getSettledValue(results[7], []);

    const noLiveDashboardData =
      liveRuns.length === 0 &&
      livePayslips.length === 0 &&
      liveTaxRecords.length === 0 &&
      liveWorkforce.length === 0;

    if (noLiveDashboardData && isLocalPreviewAllowed()) {
      employees = PREVIEW_PAYROLL_DASHBOARD_DATA.employees;
      payrollRuns = PREVIEW_PAYROLL_DASHBOARD_DATA.payrollRuns;
      payslips = PREVIEW_PAYROLL_DASHBOARD_DATA.payslips;
      taxRecords = PREVIEW_PAYROLL_DASHBOARD_DATA.taxRecords;
      deductions = PREVIEW_PAYROLL_DASHBOARD_DATA.deductions;
      bonuses = PREVIEW_PAYROLL_DASHBOARD_DATA.bonuses;
      workforceLogs = PREVIEW_PAYROLL_DASHBOARD_DATA.workforceLogs;
      projects = PREVIEW_PAYROLL_DASHBOARD_DATA.projects;
      dataMode = "preview";
      loadMessage = "Preview data is active because no live payroll history was found on localhost yet.";
    } else {
      employees = liveEmployees;
      payrollRuns = liveRuns;
      payslips = livePayslips;
      taxRecords = liveTaxRecords;
      deductions = liveDeductions;
      bonuses = liveBonuses;
      workforceLogs = liveWorkforce;
      projects = liveProjects;
      dataMode = "live";
      loadMessage = results.some((result) => result.status === "rejected")
        ? "Some live sources did not respond, so insights are based on the records currently available."
        : "";
    }

    lastSyncedAt = new Date();
    refreshing = false;
    loading = false;
  }

  async function openPayslipPreview(row: AllocationRow) {
    if (!row.payslipId) {
      toast.error("Payslip not ready", "This payroll line has no generated payslip to preview yet.");
      return;
    }

    selectedEmployeeLabel = row.label;
    selectedProjectLabel = row.primaryProject;
    payslipPreviewOpen = true;
    previewLoading = true;
    selectedPayslip = null;

    if (dataMode === "preview" && PREVIEW_PAYSLIP_DETAILS[row.payslipId]) {
      selectedPayslip = PREVIEW_PAYSLIP_DETAILS[row.payslipId];
      previewLoading = false;
      return;
    }

    try {
      selectedPayslip = await api.get<PayslipDetail>(`/hr/payslips/${row.payslipId}/`);
    } catch {
      payslipPreviewOpen = false;
      toast.error("Preview unavailable", "Could not load the detailed payslip right now.");
    } finally {
      previewLoading = false;
    }
  }

  function closePayslipPreview() {
    payslipPreviewOpen = false;
    selectedPayslip = null;
    previewLoading = false;
  }

  function goToPayrollRuns() {
    void goto("/hr/payroll-processing");
  }

  function goTo(path: string) {
    void goto(path);
  }

  onMount(() => {
    void loadDashboard();
    refreshTimer = setInterval(() => {
      void loadDashboard(true);
    }, AUTO_REFRESH_MS);

    return () => {
      if (refreshTimer) clearInterval(refreshTimer);
    };
  });

  const live = useLiveKpis(
    ["Employee"],
    () => loadDashboard(true),
    { debounceMs: 5000 },
  );

  let employeeMap = $derived.by(() => new Map<number, EmployeeDirectoryItem>(employees.map((item) => [item.id, item])));
  let projectMap = $derived.by(() => new Map<number, ProjectListItem>(projects.map((item) => [item.id, item])));

  let sortedPayrollRuns = $derived.by(() =>
    [...payrollRuns].sort((left, right) => {
      const leftDate = parseDate(left.period_end ?? left.run_date)?.getTime() ?? 0;
      const rightDate = parseDate(right.period_end ?? right.run_date)?.getTime() ?? 0;
      return rightDate - leftDate;
    })
  );

  let sortedPayslips = $derived.by(() =>
    [...payslips].sort((left, right) => {
      const leftDate = parseDate(left.period_end)?.getTime() ?? 0;
      const rightDate = parseDate(right.period_end)?.getTime() ?? 0;
      return rightDate - leftDate;
    })
  );

  let reportingPeriodKey = $derived.by(() => {
    const latestPayslipPeriod = sortedPayslips[0]?.period_end;
    if (latestPayslipPeriod) return monthKey(latestPayslipPeriod);
    const latestRunPeriod = sortedPayrollRuns[0]?.period_end ?? sortedPayrollRuns[0]?.run_date;
    return monthKey(latestRunPeriod || new Date().toISOString());
  });

  let reportingPeriodLabel = $derived(monthLabel(reportingPeriodKey));

  let currentPeriodPayslips = $derived.by(() =>
    payslips.filter((item) => monthKey(item.period_end) === reportingPeriodKey)
  );

  let currentPeriodRuns = $derived.by(() =>
    payrollRuns.filter((item) => monthKey(item.period_end ?? item.run_date) === reportingPeriodKey)
  );

  let latestPayslipByEmployee = $derived.by(() => {
    const lookup = new Map<number, PayslipListItem>();
    for (const payslip of sortedPayslips) {
      if (!lookup.has(payslip.employee)) lookup.set(payslip.employee, payslip);
    }
    return lookup;
  });

  let primaryProjectByEmployee = $derived.by(() => new Map<number, string>());

  let activeEmployees = $derived.by(() =>
    employees.filter((employee) => ACTIVE_EMPLOYMENT_STATUSES.has(employee.employment_status))
  );

  let anonymousCrewHeadcount = $derived.by(() => {
    const latestByGroup = new Map<string, ProjectWorkforceLog>();
    for (const log of workforceLogs) {
      if (log.employee || log.total_headcount <= 0) continue;
      const key = `${log.project}-${log.trade}`;
      const current = latestByGroup.get(key);
      if (!current || (parseDate(log.report_date)?.getTime() ?? 0) > (parseDate(current.report_date)?.getTime() ?? 0)) {
        latestByGroup.set(key, log);
      }
    }
    let total = 0;
    for (const log of latestByGroup.values()) total += log.total_headcount;
    return total;
  });

  let workforceRecent = $derived.by(() => {
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - 45);
    return workforceLogs.filter((log) => {
      const date = parseDate(log.report_date);
      return date ? date >= cutoff : false;
    });
  });

  let currentAverageNetPay = $derived.by(() => {
    if (currentPeriodPayslips.length > 0) {
      return currentPeriodPayslips.reduce((sum, item) => sum + toAmount(item.net_salary), 0) / currentPeriodPayslips.length;
    }
    const latestRun = sortedPayrollRuns.find((item) => item.status !== "cancelled");
    const headcount = Math.max(activeEmployees.length, 1);
    return latestRun ? toAmount(latestRun.total_net) / headcount : 0;
  });

  let crewHeadRate = $derived(currentAverageNetPay * CREW_NET_FACTOR);

  let allocationRows = $derived.by(() => {
    const rows: AllocationRow[] = [];
    const employeeGroups = new Map<number, ProjectWorkforceLog[]>();
    const crewGroups = new Map<string, ProjectWorkforceLog[]>();

    for (const log of workforceRecent) {
      if (log.employee) {
        const group = employeeGroups.get(log.employee) ?? [];
        group.push(log);
        employeeGroups.set(log.employee, group);
      } else if (log.total_headcount > 0) {
        const key = `${log.project}-${log.trade}`;
        const group = crewGroups.get(key) ?? [];
        group.push(log);
        crewGroups.set(key, group);
      }
    }

    const workforceEmployeeIds = new Set<number>();

    for (const [employeeId, logs] of employeeGroups.entries()) {
      workforceEmployeeIds.add(employeeId);
      const sortedLogs = [...logs].sort((left, right) =>
        (parseDate(right.report_date)?.getTime() ?? 0) - (parseDate(left.report_date)?.getTime() ?? 0)
      );
      const latestLog = sortedLogs[0];
      const employee = employeeMap.get(employeeId);
      const payslip = latestPayslipByEmployee.get(employeeId) ?? null;

      const touchesByProject = new Map<string, number>();
      for (const log of sortedLogs) {
        touchesByProject.set(log.project_name, (touchesByProject.get(log.project_name) ?? 0) + 1);
      }

      let primaryProject = latestLog.project_name;
      let primaryTouches = 1;
      for (const [projectName, touchCount] of touchesByProject.entries()) {
        if (touchCount > primaryTouches) {
          primaryProject = projectName;
          primaryTouches = touchCount;
        }
      }

      const allocationPercent = Math.round((primaryTouches / Math.max(sortedLogs.length, 1)) * 100);
      const project = projects.find((item) => item.name === primaryProject);

      let monthlyNet = payslip ? toAmount(payslip.net_salary) : toAmount(latestLog.latest_payslip_net_salary);
      let estimated = false;
      if (monthlyNet <= 0) {
        monthlyNet = currentAverageNetPay * (isHqLocation(employee?.office_location) ? 0.82 : 0.94);
        estimated = true;
      }

      const status = deriveStatus(latestLog.payroll_status, payslip?.status ?? null);
      rows.push({
        id: `employee-${employeeId}`,
        label: employee?.full_name ?? latestLog.employee_name ?? `Employee ${employeeId}`,
        role: employee?.job_title || employee?.position_title || latestLog.trade || "Payroll Profile",
        primaryProject,
        projectLocation: project?.location || employee?.office_location || "Location pending",
        monthlyNet,
        allocationPercent,
        status: status.key,
        statusLabel: status.label,
        notes: latestLog.notes || `${sortedLogs.length} recent allocation touchpoint${sortedLogs.length === 1 ? "" : "s"}.`,
        tags: [employee?.department_name, employee?.office_location].filter(Boolean) as string[],
        payslipId: payslip?.id ?? null,
        headcount: 1,
        estimated,
      });
    }

    for (const logs of crewGroups.values()) {
      const sortedLogs = [...logs].sort((left, right) =>
        (parseDate(right.report_date)?.getTime() ?? 0) - (parseDate(left.report_date)?.getTime() ?? 0)
      );
      const latestLog = sortedLogs[0];
      const project = projectMap.get(latestLog.project);
      const headcount = latestLog.total_headcount || 0;
      const status = deriveStatus(latestLog.payroll_status, null, true);

      rows.push({
        id: `crew-${latestLog.project}-${latestLog.trade}`,
        label: `${latestLog.trade || "Site Crew"} (${headcount})`,
        role: latestLog.shift === "full_day" ? "Weekly Site Wages" : "Labor Pool",
        primaryProject: latestLog.project_name,
        projectLocation: project?.location || "Site location",
        monthlyNet: crewHeadRate * headcount,
        allocationPercent: 100,
        status: status.key,
        statusLabel: status.label,
        notes: latestLog.notes || "Linked to site attendance and labor capture.",
        tags: ["Crew allocation", latestLog.shift.replaceAll("_", " ")],
        payslipId: null,
        headcount,
        estimated: true,
      });
    }

    const leftoverPayslips = currentPeriodPayslips.filter((item) => !workforceEmployeeIds.has(item.employee));
    const groupedLeftovers = new Map<string, PayslipListItem[]>();
    for (const payslip of leftoverPayslips) {
      const employee = employeeMap.get(payslip.employee);
      const key = isHqLocation(employee?.office_location) ? "hq-operations" : `employee-${payslip.employee}`;
      const group = groupedLeftovers.get(key) ?? [];
      group.push(payslip);
      groupedLeftovers.set(key, group);
    }

    for (const [key, groupPayslips] of groupedLeftovers.entries()) {
      const leadPayslip = groupPayslips[0];
      const employee = employeeMap.get(leadPayslip.employee);
      const totalNet = groupPayslips.reduce((sum, item) => sum + toAmount(item.net_salary), 0);
      const grouped = key === "hq-operations" && groupPayslips.length > 1;
      const status = aggregateGroupStatus(groupPayslips);

      rows.push({
        id: key,
        label: grouped ? `Admin Staff (${groupPayslips.length})` : employee?.full_name ?? leadPayslip.employee_name,
        role: grouped ? "Shared Services" : employee?.job_title || "HQ Payroll",
        primaryProject: grouped ? "HQ Operations" : employee?.office_location || "HQ Operations",
        projectLocation: employee?.office_location || "HQ Operations",
        monthlyNet: totalNet,
        allocationPercent: null,
        status: status.key,
        statusLabel: status.label,
        notes: grouped ? "Grouped shared-services payroll with no direct site allocation." : "Direct support payroll line.",
        tags: [employee?.department_name || "Operations", employee?.office_location || "HQ"].filter(Boolean),
        payslipId: grouped ? null : leadPayslip.id,
        headcount: groupPayslips.length,
        estimated: false,
      });
    }

    rows.sort((left, right) => right.monthlyNet - left.monthlyNet);
    return rows;
  });

  let allocationPreviewRows = $derived(allocationRows.slice(0, 8));

  let headcount = $derived(activeEmployees.length + anonymousCrewHeadcount);
  let monthlyOutflow = $derived.by(() =>
    allocationRows.reduce((sum, row) => sum + row.monthlyNet, 0) || currentPeriodRuns.reduce((sum, item) => sum + toAmount(item.total_net), 0)
  );

  let pendingTimeInputs = $derived.by(() => {
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - 14);
    return workforceLogs.filter((log) => {
      const date = parseDate(log.report_date);
      if (!date || date < cutoff) return false;
      return log.payroll_status !== "synced";
    });
  });

  let payrollBlocked = $derived(pendingTimeInputs.length > 0);

  let paymentStages = $derived.by(() => {
    const pendingCount = currentPeriodRuns.filter((item) => item.status === "draft").length + pendingTimeInputs.length;
    const processingCount =
      currentPeriodRuns.filter((item) => item.status === "processing").length +
      currentPeriodPayslips.filter((item) => item.status === "generated" || item.status === "sent").length;
    const disbursedCount =
      currentPeriodRuns.filter((item) => item.status === "completed").length +
      currentPeriodPayslips.filter((item) => item.status === "acknowledged").length;

    const activeKey: PaymentStageKey =
      pendingCount > 0 ? "pending" : processingCount > 0 ? "processing" : "disbursed";

    return [
      {
        key: "pending" as const,
        label: "Pending",
        count: pendingCount,
        active: activeKey === "pending",
        complete: activeKey !== "pending",
      },
      {
        key: "processing" as const,
        label: "Processing",
        count: processingCount,
        active: activeKey === "processing",
        complete: activeKey === "disbursed",
      },
      {
        key: "disbursed" as const,
        label: "Disbursed",
        count: disbursedCount,
        active: activeKey === "disbursed",
        complete: false,
      },
    ];
  });

  let paymentProgressPercent = $derived.by(() => {
    const activeStage = paymentStages.findIndex((item) => item.active);
    return [26, 62, 100][Math.max(activeStage, 0)] ?? 26;
  });

  let statutoryLiability = $derived.by(() => {
    const taxBalance = taxRecords
      .filter((item) => item.filing_status !== "paid")
      .reduce((sum, item) => sum + toAmount(item.balance), 0);
    const pensionAndTax = deductions
      .filter((item) => item.is_active && (item.deduction_type === "tax" || item.deduction_type === "pension"))
      .reduce((sum, item) => sum + toAmount(item.amount), 0);
    return taxBalance + pensionAndTax;
  });

  let statutoryCount = $derived.by(() =>
    taxRecords.filter((item) => item.filing_status !== "paid").length +
    deductions.filter((item) => item.is_active && (item.deduction_type === "tax" || item.deduction_type === "pension")).length
  );

  let projectBreakdown = $derived.by(() => {
    const grouped = new Map<string, { value: number; location: string }>();
    for (const row of allocationRows) {
      const ratio = (row.allocationPercent ?? 100) / 100;
      const amount = row.monthlyNet * ratio;
      const current = grouped.get(row.primaryProject) ?? { value: 0, location: row.projectLocation };
      current.value += amount;
      current.location = current.location || row.projectLocation;
      grouped.set(row.primaryProject, current);
    }

    return [...grouped.entries()]
      .map(([name, payload], index) => ({
        name,
        value: payload.value,
        ratio: monthlyOutflow > 0 ? payload.value / monthlyOutflow : 0,
        color: PROJECT_COLORS[index % PROJECT_COLORS.length],
        location: payload.location,
      }))
      .sort((left, right) => right.value - left.value);
  });

  let projectSegments = $derived.by(() => {
    const radius = 58;
    const circumference = 2 * Math.PI * radius;
    let offset = 0;

    return projectBreakdown.slice(0, 5).map((item) => {
      const length = circumference * item.ratio;
      const segment = {
        ...item,
        dasharray: `${length} ${circumference - length}`,
        dashoffset: -offset,
      };
      offset += length;
      return segment;
    });
  });

  let capitalizedProjectRatio = $derived.by(() => {
    const projectOnly = projectBreakdown
      .filter((item) => item.name !== "HQ Operations")
      .reduce((sum, item) => sum + item.value, 0);
    return monthlyOutflow > 0 ? (projectOnly / monthlyOutflow) * 100 : 0;
  });

  let bankExportRows = $derived.by(() => {
    const rows: BankExportRow[] = [];
    const employeeProjectMap = new Map<number, string>();
    for (const row of allocationRows) {
      if (!row.payslipId) continue;
      const employee = currentPeriodPayslips.find((item) => item.id === row.payslipId)?.employee;
      if (employee && !employeeProjectMap.has(employee)) {
        employeeProjectMap.set(employee, row.primaryProject);
      }
    }

    for (const payslip of currentPeriodPayslips) {
      const employee = employeeMap.get(payslip.employee);
      rows.push({
        employeeName: payslip.employee_name,
        employeeId: employee?.employee_id ?? "",
        amount: toAmount(payslip.net_salary),
        narration: `${reportingPeriodLabel} payroll`,
        projectName: employeeProjectMap.get(payslip.employee) ?? employee?.office_location ?? "HQ Operations",
        runName: payslip.payroll_run_name ?? reportingPeriodLabel,
        bankName: "",
        accountNumber: "",
        accountType: "Salary",
        bankCode: "",
      });
    }
    return rows;
  });

  let batchControls = $derived.by(() => {
    const monthlySalaryPayout = currentPeriodPayslips
      .filter((item) => {
        const employee = employeeMap.get(item.employee);
        return isHqLocation(employee?.office_location) || isManagementRole(employee?.job_title);
      })
      .reduce((sum, item) => sum + toAmount(item.net_salary), 0);

    const monthlySalaryCount = currentPeriodPayslips.filter((item) => {
      const employee = employeeMap.get(item.employee);
      return isHqLocation(employee?.office_location) || isManagementRole(employee?.job_title);
    }).length;

    const weeklyCrewRows = allocationRows.filter((row) => row.label.includes("Crew"));
    const weeklySiteWages = weeklyCrewRows.reduce((sum, row) => sum + row.monthlyNet / 4, 0);
    const weeklyHeadcount = weeklyCrewRows.reduce((sum, row) => sum + row.headcount, 0);

    const currentMonthBonuses = bonuses
      .filter((item) => monthKey(item.date) === reportingPeriodKey && item.status !== "cancelled")
      .reduce((sum, item) => sum + toAmount(item.amount), 0);
    const currentMonthBonusCount = bonuses.filter((item) => monthKey(item.date) === reportingPeriodKey && item.status !== "cancelled").length;

    return [
      {
        title: "Monthly Salaries",
        description: "Fixed HQ and management payroll committed for the cycle.",
        total: monthlySalaryPayout,
        countLabel: `${monthlySalaryCount} staff line${monthlySalaryCount === 1 ? "" : "s"}`,
        tone: "neutral" as const,
        footnote: monthlySalaryCount > 0 ? "Anchored by HQ and leadership payroll." : "No fixed payroll lines landed in this period yet.",
        ctaLabel: "Open Payroll Runs",
        ctaHref: "/hr/payroll-processing",
      },
      {
        title: "Weekly Site Wages",
        description: "Casual labor and contractor wages tied to field attendance capture.",
        total: weeklySiteWages,
        countLabel: `${weeklyHeadcount} field staff`,
        tone: payrollBlocked ? "warn" as const : "good" as const,
        footnote: payrollBlocked
          ? `${pendingTimeInputs.length} pending time input${pendingTimeInputs.length === 1 ? "" : "s"} still block payroll release.`
          : "All tracked site time inputs are clear for payroll release.",
        ctaLabel: "Open Time Inputs",
        ctaHref: "/payroll/time-inputs",
      },
      {
        title: "Ad-hoc Bonuses",
        description: "Performance and milestone incentives waiting for payroll inclusion.",
        total: currentMonthBonuses,
        countLabel: `${currentMonthBonusCount} bonus item${currentMonthBonusCount === 1 ? "" : "s"}`,
        tone: currentMonthBonusCount > 0 ? "review" as const : "neutral" as const,
        footnote: currentMonthBonusCount > 0 ? "Milestone incentives are flowing into the batch queue." : "No ad-hoc bonus items were posted for this period.",
        ctaLabel: "Open Bonuses",
        ctaHref: "/hr/bonuses",
      },
    ];
  });

  let workflowStages = $derived.by(() => {
    const projectAllocatedLines = allocationRows.filter((row) => row.primaryProject !== "HQ Operations").length;
    const readyPayslips = currentPeriodPayslips.filter((item) => item.status === "sent" || item.status === "acknowledged").length;

    return [
      {
        label: "Time Capture",
        description: "Field attendance and time inputs land in the payroll queue.",
        value: pendingTimeInputs.length > 0 ? `${pendingTimeInputs.length} waiting` : "All clear",
        state: pendingTimeInputs.length > 0 ? "blocked" : "complete",
        tone: pendingTimeInputs.length > 0 ? "warn" : "good",
      },
      {
        label: "Project Allocation",
        description: "Labor is capitalized to live sites and HQ support buckets.",
        value: `${projectAllocatedLines} active lines`,
        state: projectAllocatedLines > 0 ? "active" : "blocked",
        tone: projectAllocatedLines > 0 ? "review" : "warn",
      },
      {
        label: "Statutory Check",
        description: "PAYE, PenCom, and filing balances are consolidated before release.",
        value: statutoryCount > 0 ? formatCurrency(statutoryLiability) : "No dues",
        state: statutoryCount > 0 ? "active" : "complete",
        tone: statutoryCount > 0 ? "review" : "good",
      },
      {
        label: "Bank Disbursement",
        description: "Payslips, approval traces, and export schedules are staged for treasury.",
        value: `${readyPayslips}/${currentPeriodPayslips.length || 0} ready`,
        state: readyPayslips === currentPeriodPayslips.length && currentPeriodPayslips.length > 0 ? "complete" : "active",
        tone: readyPayslips === currentPeriodPayslips.length && currentPeriodPayslips.length > 0 ? "good" : "neutral",
      },
    ];
  });

  let timelineMonths = $derived(computeTimelineMonths(6));

  let portfolioModeledMonthlyBudget = $derived.by(() =>
    projects.reduce((sum, project) => sum + modeledMonthlyLaborBudget(project), 0)
  );

  let laborTrendPoints = $derived.by(() => {
    const totalsByMonth = new Map<string, number>();
    if (payrollRuns.length > 0) {
      for (const run of payrollRuns) {
        const key = monthKey(run.period_end ?? run.run_date);
        totalsByMonth.set(key, (totalsByMonth.get(key) ?? 0) + toAmount(run.total_net));
      }
    } else {
      for (const payslip of payslips) {
        const key = monthKey(payslip.period_end);
        totalsByMonth.set(key, (totalsByMonth.get(key) ?? 0) + toAmount(payslip.net_salary));
      }
    }

    const denominator = portfolioModeledMonthlyBudget || monthlyOutflow || 1;
    return timelineMonths.map((key) => ((totalsByMonth.get(key) ?? monthlyOutflow) / denominator) * 100);
  });

  let burnInsights = $derived.by(() => {
    const countsByMonthAndProject = new Map<string, number>();
    for (const log of workforceRecent) {
      const key = `${monthKey(log.report_date)}::${log.project_name}`;
      countsByMonthAndProject.set(key, (countsByMonthAndProject.get(key) ?? 0) + 1);
    }

    const overtimeByProject = new Map<string, number>();
    for (const log of workforceRecent) {
      overtimeByProject.set(log.project_name, (overtimeByProject.get(log.project_name) ?? 0) + toAmount(log.overtime_hours));
    }

    return projectBreakdown
      .map((entry) => {
        const project = [...projects].find((item) => item.name === entry.name);
        if (!project) return null;

        const budget = toAmount(project.budget);
        const modeled = modeledMonthlyLaborBudget(project);
        const variance = modeled > 0 ? ((entry.value - modeled) / modeled) * 100 : 0;
        const overtimeHours = overtimeByProject.get(entry.name) ?? 0;

        const trend = timelineMonths.map((key) => {
          const monthTouches = countsByMonthAndProject.get(`${key}::${entry.name}`) ?? 0;
          const baselineTouches = countsByMonthAndProject.get(`${reportingPeriodKey}::${entry.name}`) ?? 1;
          if (monthTouches === 0) return entry.value * 0.45;
          return entry.value * (monthTouches / baselineTouches);
        });

        let tone: "good" | "warn" | "review" = "good";
        let alert: string | null = null;
        if (variance > 15) {
          tone = "warn";
          alert = `${entry.name} is ${formatPercent(variance, 0)} above its modeled monthly labor allowance.`;
        } else if (overtimeHours > 40) {
          tone = "review";
          alert = `${entry.name} logged ${overtimeHours.toFixed(0)} overtime hours and needs budget review.`;
        }

        return {
          projectName: entry.name,
          location: project.location,
          monthlyLabor: entry.value,
          budget,
          ratio: budget > 0 ? (entry.value / budget) * 100 : 0,
          modeledVariance: variance,
          overtimeHours,
          alert,
          trend,
          tone,
        };
      })
      .filter((item): item is BurnInsight => Boolean(item))
      .sort((left, right) => right.monthlyLabor - left.monthlyLabor)
      .slice(0, 3);
  });

  let activeBurnAlerts = $derived(burnInsights.filter((item) => item.alert));
</script>

<svelte:head>
  <title>Payroll Dashboard | developerOS</title>
</svelte:head>

{#if loading}
  <div class="mx-auto flex min-h-[60vh] max-w-7xl items-center justify-center">
    <div class="flex items-center gap-3 rounded-full border border-neutral-200 bg-white px-5 py-3 text-sm text-neutral-600 shadow-sm">
      <div class="h-4 w-4 rounded-full border-2 border-neutral-300 border-t-neutral-900 animate-spin"></div>
      Building the payroll command center...
    </div>
  </div>
{:else}
  <div class="space-y-4 overflow-x-clip">
    <!-- Page header — matches the standard dashboard pattern -->
    <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">Dashboard</p>
        <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Payroll Dashboard</h1>
        <p class="mt-1 max-w-2xl text-sm text-neutral-500">
          A labor-capitalization command center for payroll health, project allocation, statutory exposure, and disbursement readiness.
        </p>
        <div class="mt-3 flex flex-wrap items-center gap-2 text-xs text-neutral-500">
          <LiveBadge refreshing={live.refreshing} />
          {#if dataMode === "preview"}
            <span class="rounded-full border border-rose-200 bg-rose-50 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-rose-700">
              Preview Data
            </span>
          {/if}
          <span class="rounded-full border border-neutral-200 bg-white px-3 py-1">Period: {reportingPeriodLabel}</span>
          <span class="rounded-full border border-neutral-200 bg-white px-3 py-1">Auto refresh: 60 sec</span>
          <span class="rounded-full border border-neutral-200 bg-white px-3 py-1">Last sync: {relativeSyncLabel(lastSyncedAt)}</span>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <button
          type="button"
          class="inline-flex items-center gap-2 rounded-full border border-neutral-300 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-700 transition hover:border-neutral-400"
          onclick={() => void loadDashboard(true)}
          disabled={refreshing}
        >
          <svg class={`h-3.5 w-3.5 ${refreshing ? "animate-spin" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.75">
            <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992V4.356m-1.636 14.288A9 9 0 1 1 21 12.003" />
          </svg>
          {refreshing ? "Refreshing..." : "Refresh"}
        </button>

        <button
          type="button"
          class="inline-flex items-center gap-2 rounded-full border border-neutral-300 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-700 transition hover:border-neutral-400"
          onclick={goToPayrollRuns}
        >
          Payroll Runs
        </button>

        <button
          type="button"
          class="inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-xs font-semibold text-white transition disabled:cursor-not-allowed disabled:opacity-45 {payrollBlocked ? 'bg-neutral-500' : 'bg-neutral-900 hover:bg-neutral-800'}"
          onclick={goToPayrollRuns}
          disabled={payrollBlocked}
        >
          <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.75">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          Run Payroll
        </button>
      </div>
    </div>

    <!-- KPI grid (flattened out of the old hero) -->
    <div class="grid gap-4 xl:grid-cols-4">
      <div class="rounded-2xl border border-neutral-200 bg-white p-5">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Total Monthly Outflow</p>
        <p class="mt-3 text-2xl font-bold tracking-tight text-neutral-900 tabular-nums">{formatCurrency(monthlyOutflow)}</p>
        <p class="mt-2 text-xs text-neutral-500">
          Monthly labor commitment spanning active sites, HQ support, and payroll batches.
        </p>
      </div>

      <div class="rounded-2xl border border-neutral-200 bg-white p-5">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Headcount</p>
        <p class="mt-3 text-2xl font-bold tracking-tight text-neutral-900 tabular-nums">{headcount}</p>
        <p class="mt-2 text-xs text-neutral-500">
          {activeEmployees.length} active staff plus {anonymousCrewHeadcount} site crew currently flowing through the labor stack.
        </p>
      </div>

      <div class="rounded-2xl border border-neutral-200 bg-white p-5">
        <div class="flex items-center justify-between gap-4">
          <div>
            <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Payment Status</p>
            <p class="mt-2 text-sm font-semibold text-neutral-900">Pending to Disbursed</p>
          </div>
          <span class="rounded-full border border-neutral-200 bg-neutral-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-neutral-600">
            {paymentStages.find((item) => item.active)?.label}
          </span>
        </div>

        <div class="mt-4 h-2.5 overflow-hidden rounded-full bg-neutral-100">
          <div
            class="h-full rounded-full bg-linear-to-r from-orange-400 via-neutral-900 to-emerald-500 transition-all duration-700"
            style={`width: ${paymentProgressPercent}%`}
          ></div>
        </div>

        <div class="mt-3 grid grid-cols-3 gap-1.5">
          {#each paymentStages as stage}
            <div class={`rounded-lg px-2 py-2 text-center text-[10px] font-semibold uppercase tracking-wider ${segmentClasses(stage)}`}>
              <p>{stage.label}</p>
              <p class="mt-1 text-sm tracking-normal">{stage.count}</p>
            </div>
          {/each}
        </div>
      </div>

      <div class="rounded-2xl border border-orange-200 bg-orange-50 p-5">
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="text-[10px] font-semibold uppercase tracking-wider text-orange-600">Tax and Pension Liability</p>
            <p class="mt-3 text-2xl font-bold tracking-tight text-orange-900 tabular-nums">{formatCurrency(statutoryLiability)}</p>
          </div>
          <span class="rounded-full border border-orange-200 bg-white px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-orange-700">
            {statutoryCount} due
          </span>
        </div>
        <p class="mt-2 text-xs text-orange-800/90">
          Outstanding PAYE, pension, and filing balances due in this reporting cycle.
        </p>
      </div>
    </div>

    <div class="grid gap-6 xl:grid-cols-[minmax(0,1.55fr)_minmax(0,0.95fr)] xl:items-start">
      <div class="min-w-0 space-y-6">
      <section class="min-w-0 rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
        <div class="flex flex-col gap-4 border-b border-neutral-200 pb-5 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-neutral-400">Project-Labor Allocation Grid</p>
            <h2 class="mt-2 text-lg font-semibold text-neutral-950">Capitalized payroll by project and role</h2>
            <p class="mt-2 text-sm leading-6 text-neutral-500">
              Click an individual line to preview the linked payslip. Higher-opacity net pay values guide the eye.
            </p>
          </div>

          <div class="flex flex-wrap items-center gap-2 text-sm text-neutral-500">
            <span class="rounded-full border border-neutral-200 bg-white px-3 py-1.5">
              {allocationRows.length} active cost lines
            </span>
            <span class="rounded-full border border-neutral-200 bg-white px-3 py-1.5">
              {formatPercent(capitalizedProjectRatio, 0)} capitalized to projects
            </span>
          </div>
        </div>

        <div class="mt-5 overflow-x-auto">
          <table class="min-w-full text-sm">
            <thead>
              <tr class="text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">
                <th class="px-4 py-3">Employee / Role</th>
                <th class="px-4 py-3">Primary Project</th>
                <th class="px-4 py-3 text-right">Monthly Net</th>
                <th class="px-4 py-3 text-right">Allocation %</th>
                <th class="px-4 py-3 text-right">Status</th>
              </tr>
            </thead>
            <tbody>
              {#each allocationPreviewRows as row}
                <tr class="border-t border-neutral-200 align-top">
                  <td class="px-4 py-4">
                    <button
                      type="button"
                      class="group text-left disabled:cursor-default"
                      onclick={() => openPayslipPreview(row)}
                      disabled={!row.payslipId}
                    >
                      <span class="text-base font-semibold tracking-tight text-neutral-950 transition group-hover:text-neutral-700">
                        {row.label}
                      </span>
                    </button>
                    <p class="mt-1 text-sm text-neutral-600">{row.role}</p>
                    <div class="mt-2 flex flex-wrap gap-2">
                      {#each row.tags as tag}
                        <span class="rounded-full bg-neutral-100/80 px-2.5 py-1 text-xs font-light text-neutral-500">{tag}</span>
                      {/each}
                      {#if row.estimated}
                        <span class="rounded-full bg-orange-100/80 px-2.5 py-1 text-xs font-semibold text-orange-600">Est.</span>
                      {/if}
                    </div>
                  </td>

                  <td class="px-4 py-4">
                    <p class="text-base font-medium text-neutral-900">{row.primaryProject}</p>
                    <p class="mt-1 text-sm font-light text-neutral-500">{row.projectLocation}</p>
                    <p class="mt-2 text-sm leading-6 text-neutral-500">{row.notes}</p>
                  </td>

                  <td class="px-4 py-4 text-right">
                    <p class="text-sm font-semibold tabular-nums text-neutral-900">{formatCurrency(row.monthlyNet)}</p>
                  </td>

                  <td class="px-4 py-4 text-right text-sm font-semibold text-neutral-900">
                    {#if row.allocationPercent === null}
                      <span class="text-neutral-400">--</span>
                    {:else}
                      {row.allocationPercent}%
                    {/if}
                  </td>

                  <td class="px-4 py-4 text-right">
                    <span class={`inline-flex rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${statusClasses(row.status)}`}>
                      {row.statusLabel}
                    </span>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </section>

      <section class="min-w-0 rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-neutral-400">Payroll Cycles and Batch Controls</p>
            <h2 class="mt-2 text-lg font-semibold text-neutral-950">Frequency-aware batch management</h2>
          </div>
          <button
            type="button"
            class="rounded-2xl border border-neutral-200 bg-white px-4 py-3 text-sm font-semibold text-neutral-800 transition hover:border-neutral-400 hover:text-neutral-950"
            onclick={goToPayrollRuns}
          >
            Open Payroll Batches
          </button>
        </div>

        <div class="mt-5 grid gap-4 lg:grid-cols-3">
          {#each batchControls as card}
            <article class={`rounded-2xl border px-5 py-5 ${card.tone === "warn" ? "border-orange-200 bg-orange-50" : card.tone === "good" ? "border-emerald-200 bg-emerald-50" : card.tone === "review" ? "border-sky-200 bg-sky-50" : "border-neutral-200 bg-white"}`}>
              <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">{card.title}</p>
              <p class="mt-2 text-xl font-bold tracking-tight text-neutral-900 tabular-nums">{formatCurrency(card.total)}</p>
              <p class="mt-2 text-sm font-medium text-neutral-700">{card.countLabel}</p>
              <p class="mt-3 text-sm leading-6 text-neutral-600">{card.description}</p>
              <p class="mt-4 text-sm leading-6 text-neutral-500">{card.footnote}</p>
              <button
                type="button"
                class="mt-5 inline-flex items-center gap-2 rounded-2xl border border-neutral-200 bg-white px-4 py-3 text-sm font-semibold text-neutral-800 transition hover:border-neutral-400 hover:text-neutral-950"
                onclick={() => goTo(card.ctaHref)}
              >
                {card.ctaLabel}
              </button>
            </article>
          {/each}
        </div>
      </section>

      <section class="min-w-0 rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-neutral-400">Payroll and Labor Cost Workflow</p>
            <h2 class="mt-2 text-lg font-semibold text-neutral-950">From time input to bank disbursement</h2>
          </div>
          <span class="rounded-full border border-neutral-200 bg-white px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.2em] text-neutral-500">
            Live automation
          </span>
        </div>

        <div class="mt-6 space-y-4">
          {#each workflowStages as stage, index}
            <div class={`rounded-2xl border p-4 ${stageClasses(stage.state, stage.tone)}`}>
              <div class="flex items-start gap-4">
                <div class={`mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-sm font-semibold ${stage.state === "blocked" ? "bg-orange-500 text-white" : stage.tone === "good" ? "bg-emerald-500 text-white" : stage.tone === "review" ? "bg-sky-500 text-white" : "bg-neutral-900 text-white"}`}>
                  {index + 1}
                </div>
                <div class="min-w-0 flex-1">
                  <div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <p class="text-base font-semibold tracking-tight text-neutral-950">{stage.label}</p>
                      <p class="mt-1 text-sm leading-6 text-neutral-600">{stage.description}</p>
                    </div>
                    <p class="text-sm font-semibold text-neutral-900">{stage.value}</p>
                  </div>
                </div>
              </div>
            </div>
          {/each}
        </div>
      </section>
      </div>

      <div class="min-w-0 space-y-6">
        <section class="rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
          <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-neutral-400">Project Breakdown</p>
          <div class="mt-4 flex flex-col items-center gap-6">
            <div class="relative h-52 w-52 shrink-0">
              <svg viewBox="0 0 160 160" class="h-full w-full -rotate-90">
                <circle cx="80" cy="80" r="58" fill="none" stroke="rgba(226,232,240,0.8)" stroke-width="18"></circle>
                {#each projectSegments as segment}
                  <circle
                    cx="80"
                    cy="80"
                    r="58"
                    fill="none"
                    stroke={segment.color}
                    stroke-width="18"
                    stroke-linecap="round"
                    stroke-dasharray={segment.dasharray}
                    stroke-dashoffset={segment.dashoffset}
                  ></circle>
                {/each}
              </svg>
              <div class="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
                <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Capitalized</p>
                <p class="mt-1 text-2xl font-bold tracking-tight text-neutral-900 tabular-nums">{formatPercent(capitalizedProjectRatio, 0)}</p>
                <p class="mt-0.5 text-xs text-neutral-500">of payroll outflow</p>
              </div>
            </div>

            <div class="w-full space-y-3">
              {#each projectBreakdown.slice(0, 5) as item}
                <div class="flex items-center justify-between gap-3 rounded-2xl border border-neutral-200 bg-white px-4 py-3">
                  <div class="flex min-w-0 items-center gap-3">
                    <span class="h-3 w-3 shrink-0 rounded-full" style={`background: ${item.color}`}></span>
                    <div class="min-w-0">
                      <p class="truncate font-medium text-neutral-900">{item.name}</p>
                      <p class="truncate text-xs text-neutral-500">{item.location}</p>
                    </div>
                  </div>
                  <div class="shrink-0 text-right">
                    <p class="font-semibold tabular-nums text-neutral-950">{formatCurrency(item.value)}</p>
                    <p class="text-xs tabular-nums text-neutral-500">{formatPercent(item.ratio * 100, 0)}</p>
                  </div>
                </div>
              {/each}
            </div>
          </div>
        </section>

        <section class="rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
          <div class="flex flex-col gap-4 border-b border-neutral-200 pb-5">
            <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-neutral-400">Project Burn Insight</p>
            <div class="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p class="text-2xl font-bold tracking-tight text-neutral-900 tabular-nums">
                  {formatPercent((monthlyOutflow / Math.max(portfolioModeledMonthlyBudget, 1)) * 100, 0)}
                </p>
                <p class="mt-2 text-sm text-neutral-500">
                  Labor-to-modeled budget ratio across the current project portfolio.
                </p>
              </div>
              <div class="rounded-full border border-neutral-200 bg-white px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.2em] text-neutral-500">
                Modeled labor share: 12%
              </div>
            </div>

            <svg viewBox="0 0 100 32" class="mt-2 h-20 w-full overflow-visible">
              <path d={buildSparkline(laborTrendPoints)} fill="none" stroke="#111827" stroke-width="2.5" stroke-linecap="round"></path>
              <path d={buildSparkline(laborTrendPoints)} fill="url(#laborArea)" stroke="none" opacity="0.12"></path>
              <defs>
                <linearGradient id="laborArea" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stop-color="#111827"></stop>
                  <stop offset="100%" stop-color="#111827" stop-opacity="0"></stop>
                </linearGradient>
              </defs>
            </svg>
          </div>

          <div class="mt-5 space-y-4">
            {#each burnInsights as insight}
              <div class={`rounded-2xl border px-4 py-4 ${insight.tone === "warn" ? "border-orange-200 bg-orange-50" : insight.tone === "review" ? "border-sky-200 bg-sky-50" : "border-emerald-200 bg-emerald-50"}`}>
                <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <p class="text-base font-semibold tracking-tight text-neutral-950">{insight.projectName}</p>
                    <p class="mt-1 text-sm text-neutral-500">{insight.location}</p>
                  </div>
                  <div class="text-left sm:text-right">
                    <p class="text-sm font-semibold text-neutral-950">{formatCurrency(insight.monthlyLabor)}</p>
                    <p class="text-xs text-neutral-500">{formatPercent(insight.ratio, 2)} of EDC</p>
                  </div>
                </div>

                <svg viewBox="0 0 100 24" class="mt-4 h-14 w-full">
                  <path d={buildSparkline(insight.trend)} fill="none" stroke={insight.tone === "warn" ? "#f97316" : insight.tone === "review" ? "#0284c7" : "#059669"} stroke-width="2.4" stroke-linecap="round"></path>
                </svg>

                <div class="mt-3 flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.16em] text-neutral-500">
                  <span class="rounded-full bg-white px-3 py-1">Budget {formatCurrency(insight.budget)}</span>
                  <span class="rounded-full bg-white px-3 py-1">Variance {formatPercent(insight.modeledVariance, 0)}</span>
                  <span class="rounded-full bg-white px-3 py-1">Overtime {insight.overtimeHours.toFixed(0)} hr</span>
                </div>

                {#if insight.alert}
                  <p class="mt-3 text-sm leading-6 text-neutral-700">{insight.alert}</p>
                {/if}
              </div>
            {/each}

            {#if activeBurnAlerts.length === 0}
              <div class="rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                No project is currently outrunning its modeled monthly labor allowance.
              </div>
            {/if}
          </div>
        </section>

        <BankExport
          rows={bankExportRows}
          currencyCode={currency.config.code || "NGN"}
          periodLabel={reportingPeriodLabel}
          previewMode={dataMode === "preview"}
        />
      </div>
    </div>
  </div>

  <PayslipPreview
    open={payslipPreviewOpen}
    loading={previewLoading}
    payslip={selectedPayslip}
    employeeLabel={selectedEmployeeLabel}
    projectName={selectedProjectLabel}
    currencyCode={currency.config.code || "NGN"}
    onClose={closePayslipPreview}
  />
{/if}

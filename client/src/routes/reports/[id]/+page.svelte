<script lang="ts">
  import { page } from "$app/stores";
  import { ApiError, api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    PaginatedResponse,
    ReportOutputFormat,
    ReportRunRecord,
    ReportSavedView,
    ReportSubscription,
    ReportSubscriptionDeliveryChannel,
    ReportSubscriptionFrequency,
    ReportTemplate,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  type ReportFilterState = {
    date_from: string;
    date_to: string;
    department: string;
    location: string;
    employment_type: string;
  };

  type EmployeeStatus = "Active" | "On Leave" | "Probation";
  type EmployeeRecord = {
    id: number;
    employee_code: string;
    employee_name: string;
    department: string;
    location: string;
    employment_type: string;
    status: EmployeeStatus;
    job_title: string;
    manager: string;
    hire_date: string;
  };

  type PivotMode = "employees" | "department" | "location" | "employment_type";
  type PivotDimension = Exclude<PivotMode, "employees">;
  type ChartMode = "bar" | "line" | "donut";
  type SortDirection = "asc" | "desc";

  type EmployeeColumnKey =
    | "employee_code"
    | "employee_name"
    | "department"
    | "location"
    | "employment_type"
    | "status"
    | "job_title";
  type PivotColumnKey = "group" | "headcount" | "active" | "on_leave" | "probation";
  type SortColumn = EmployeeColumnKey | PivotColumnKey;

  type TableColumn = {
    key: SortColumn;
    label: string;
    align?: "left" | "right";
  };

  type EmployeeColumnFilterState = {
    employee_name: string;
    department: string;
    location: string;
    employment_type: string;
    status: string;
  };

  type EmployeeColumnVisibility = Record<EmployeeColumnKey, boolean>;

  type SavedViewSettings = {
    chart_type?: ChartMode;
    pivot_mode?: PivotMode;
    column_filters?: EmployeeColumnFilterState;
    drill_department?: string | null;
  };

  type PivotRow = {
    group: string;
    headcount: number;
    active: number;
    on_leave: number;
    probation: number;
  };

  type ChartPoint = {
    label: string;
    value: number;
  };

  type LinePoint = {
    x: number;
    y: number;
    label: string;
    value: number;
  };

  type ReportRunAction = "run" | "export";

  const reportId = $derived(Number($page.params.id || "0"));

  const departmentOptions = ["All Departments", "HR", "Finance", "Operations", "Projects"];
  const locationOptions = ["All Locations", "HQ", "Lagos", "Abuja", "Remote"];
  const employmentTypeOptions = ["All Types", "full_time", "part_time", "contract", "intern"];

  const subscriptionFrequencies: { value: ReportSubscriptionFrequency; label: string }[] = [
    { value: "daily", label: "Daily" },
    { value: "weekly", label: "Weekly" },
    { value: "monthly", label: "Monthly" },
  ];

  const subscriptionDeliveryOptions: {
    value: ReportSubscriptionDeliveryChannel;
    label: string;
    description: string;
  }[] = [
    { value: "email", label: "Email", description: "Send report output to recipients." },
    { value: "in_app", label: "In-app notification", description: "Send notification inside the app." },
    { value: "dashboard_widget", label: "Dashboard widget", description: "Pin report status on dashboard." },
  ];

  const pivotModes: { value: PivotMode; label: string }[] = [
    { value: "employees", label: "Employees" },
    { value: "department", label: "Department Pivot" },
    { value: "location", label: "Location Pivot" },
    { value: "employment_type", label: "Employment Type Pivot" },
  ];

  const chartModes: { value: ChartMode; label: string }[] = [
    { value: "bar", label: "Bar" },
    { value: "line", label: "Line" },
    { value: "donut", label: "Donut" },
  ];

  const employeeColumns: TableColumn[] = [
    { key: "employee_code", label: "Employee ID" },
    { key: "employee_name", label: "Employee" },
    { key: "department", label: "Department" },
    { key: "location", label: "Location" },
    { key: "employment_type", label: "Employment Type" },
    { key: "status", label: "Status" },
    { key: "job_title", label: "Role" },
  ];

  const pivotColumns: TableColumn[] = [
    { key: "group", label: "Group" },
    { key: "headcount", label: "Headcount", align: "right" },
    { key: "active", label: "Active", align: "right" },
    { key: "on_leave", label: "On Leave", align: "right" },
    { key: "probation", label: "Probation", align: "right" },
  ];

  const defaultEmployeeColumnVisibility: EmployeeColumnVisibility = {
    employee_code: true,
    employee_name: true,
    department: true,
    location: true,
    employment_type: true,
    status: true,
    job_title: true,
  };

  const employeeSeed: EmployeeRecord[] = [
    { id: 1, employee_code: "EMP-1001", employee_name: "Amina Yusuf", department: "HR", location: "HQ", employment_type: "full_time", status: "Active", job_title: "HR Business Partner", manager: "Samuel Obi", hire_date: "2021-03-18" },
    { id: 2, employee_code: "EMP-1002", employee_name: "Ibrahim Bello", department: "Finance", location: "Lagos", employment_type: "full_time", status: "Active", job_title: "Finance Analyst", manager: "Tina Nwosu", hire_date: "2020-11-05" },
    { id: 3, employee_code: "EMP-1003", employee_name: "Adaeze Okafor", department: "Operations", location: "Abuja", employment_type: "contract", status: "Probation", job_title: "Operations Coordinator", manager: "Femi Thomas", hire_date: "2025-01-14" },
    { id: 4, employee_code: "EMP-1004", employee_name: "Daniel Akin", department: "Projects", location: "HQ", employment_type: "full_time", status: "Active", job_title: "Project Planner", manager: "Maya Dada", hire_date: "2019-06-27" },
    { id: 5, employee_code: "EMP-1005", employee_name: "Grace Eze", department: "HR", location: "Remote", employment_type: "part_time", status: "On Leave", job_title: "Talent Specialist", manager: "Samuel Obi", hire_date: "2022-09-02" },
    { id: 6, employee_code: "EMP-1006", employee_name: "Victor Onoja", department: "Finance", location: "HQ", employment_type: "full_time", status: "Active", job_title: "Budget Controller", manager: "Tina Nwosu", hire_date: "2018-04-11" },
    { id: 7, employee_code: "EMP-1007", employee_name: "Kemi Folarin", department: "Operations", location: "Lagos", employment_type: "full_time", status: "Active", job_title: "Service Manager", manager: "Femi Thomas", hire_date: "2023-02-10" },
    { id: 8, employee_code: "EMP-1008", employee_name: "Olaide Martins", department: "Projects", location: "Remote", employment_type: "contract", status: "Active", job_title: "Site Engineer", manager: "Maya Dada", hire_date: "2024-07-22" },
    { id: 9, employee_code: "EMP-1009", employee_name: "Pauline Udo", department: "Finance", location: "Abuja", employment_type: "intern", status: "Probation", job_title: "Finance Intern", manager: "Tina Nwosu", hire_date: "2025-09-01" },
    { id: 10, employee_code: "EMP-1010", employee_name: "Yemi Oyetola", department: "HR", location: "Lagos", employment_type: "full_time", status: "Active", job_title: "Learning Lead", manager: "Samuel Obi", hire_date: "2020-01-15" },
    { id: 11, employee_code: "EMP-1011", employee_name: "Nkechi Umeh", department: "Projects", location: "Abuja", employment_type: "full_time", status: "Active", job_title: "Project Controls Officer", manager: "Maya Dada", hire_date: "2021-12-03" },
    { id: 12, employee_code: "EMP-1012", employee_name: "Sodiq Raji", department: "Operations", location: "HQ", employment_type: "full_time", status: "On Leave", job_title: "Operations Supervisor", manager: "Femi Thomas", hire_date: "2017-08-09" },
    { id: 13, employee_code: "EMP-1013", employee_name: "Ruth Ekanem", department: "Finance", location: "Remote", employment_type: "part_time", status: "Active", job_title: "Payroll Officer", manager: "Tina Nwosu", hire_date: "2023-11-13" },
    { id: 14, employee_code: "EMP-1014", employee_name: "Tobi Adegoke", department: "Projects", location: "Lagos", employment_type: "full_time", status: "Active", job_title: "Construction Lead", manager: "Maya Dada", hire_date: "2019-10-21" },
    { id: 15, employee_code: "EMP-1015", employee_name: "Fatima Hassan", department: "HR", location: "Abuja", employment_type: "contract", status: "Active", job_title: "Recruitment Consultant", manager: "Samuel Obi", hire_date: "2024-03-06" },
    { id: 16, employee_code: "EMP-1016", employee_name: "Emeka Chukwu", department: "Operations", location: "Remote", employment_type: "full_time", status: "Probation", job_title: "Logistics Specialist", manager: "Femi Thomas", hire_date: "2025-05-20" },
    { id: 17, employee_code: "EMP-1017", employee_name: "Janet Sanni", department: "Finance", location: "HQ", employment_type: "full_time", status: "Active", job_title: "Compliance Accountant", manager: "Tina Nwosu", hire_date: "2022-06-17" },
    { id: 18, employee_code: "EMP-1018", employee_name: "Uche Mba", department: "Projects", location: "HQ", employment_type: "intern", status: "Active", job_title: "Project Intern", manager: "Maya Dada", hire_date: "2025-10-04" },
    { id: 19, employee_code: "EMP-1019", employee_name: "Mariam Lawal", department: "HR", location: "HQ", employment_type: "full_time", status: "Active", job_title: "People Operations Specialist", manager: "Samuel Obi", hire_date: "2021-07-30" },
    { id: 20, employee_code: "EMP-1020", employee_name: "Chinedu Agbo", department: "Operations", location: "Abuja", employment_type: "full_time", status: "Active", job_title: "Service Quality Officer", manager: "Femi Thomas", hire_date: "2020-05-12" },
  ];

  const chartPalette = ["#111827", "#374151", "#4b5563", "#6b7280", "#9ca3af", "#d1d5db"];

  let loading = $state(true);
  let running = $state(false);
  let savingView = $state(false);
  let savingSubscription = $state(false);
  let sharing = $state(false);
  let exportingFormat = $state<ReportOutputFormat | null>(null);

  let report = $state<ReportTemplate | null>(null);
  let latestRun = $state<ReportRunRecord | null>(null);
  let runs = $state<ReportRunRecord[]>([]);
  let savedViews = $state<ReportSavedView[]>([]);
  let subscriptions = $state<ReportSubscription[]>([]);

  let selectedSavedViewId = $state("");
  let outputFormat = $state<ReportOutputFormat>("pdf");

  let filters = $state<ReportFilterState>({
    date_from: "",
    date_to: "",
    department: "All Departments",
    location: "All Locations",
    employment_type: "All Types",
  });

  let viewName = $state("");
  let subscriptionFrequency = $state<ReportSubscriptionFrequency>("weekly");
  let subscriptionDeliveryChannels = $state<ReportSubscriptionDeliveryChannel[]>(["email"]);
  let subscriptionRecipients = $state("");

  let pivotMode = $state<PivotMode>("employees");
  let chartMode = $state<ChartMode>("bar");
  let sortColumn = $state<SortColumn>("employee_name");
  let sortDirection = $state<SortDirection>("asc");
  let drillDepartment = $state<string | null>(null);
  let selectedEmployeeId = $state<number | null>(null);

  let columnFilters = $state<EmployeeColumnFilterState>({
    employee_name: "",
    department: "All",
    location: "All",
    employment_type: "All",
    status: "All",
  });

  let employeeColumnVisibility = $state<EmployeeColumnVisibility>({ ...defaultEmployeeColumnVisibility });

  const exportBlocked = $derived(Boolean(report?.confidentiality_restrict_download));
  const printBlocked = $derived(Boolean(report?.confidentiality_restrict_printing));
  const confidentialityLabelName = $derived(report?.confidentiality_label_name || "Not classified");

  function unwrapList<T>(payload: PaginatedResponse<T> | T[]): T[] {
    return Array.isArray(payload) ? payload : (payload?.results ?? []);
  }

  function formatDateTime(value: string | null): string {
    if (!value) return "N/A";
    return new Date(value).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function formatDateOnly(value: string): string {
    return new Date(value).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function runDuration(run: ReportRunRecord | null): string {
    if (!run?.started_at || !run?.completed_at) return "N/A";
    const started = new Date(run.started_at).getTime();
    const completed = new Date(run.completed_at).getTime();
    const seconds = Math.max(0, Math.round((completed - started) / 1000));
    return `${seconds}s`;
  }

  function formatEmploymentType(value: string): string {
    if (!value) return "N/A";
    return value
      .split("_")
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" ");
  }

  function toFilterPayload(): Record<string, string> {
    const payload: Record<string, string> = {};
    if (filters.date_from) payload.date_from = filters.date_from;
    if (filters.date_to) payload.date_to = filters.date_to;
    if (filters.department && filters.department !== "All Departments") payload.department = filters.department;
    if (filters.location && filters.location !== "All Locations") payload.location = filters.location;
    if (filters.employment_type && filters.employment_type !== "All Types") {
      payload.employment_type = filters.employment_type;
    }
    return payload;
  }

  function readFilterValue(obj: Record<string, unknown>, key: string, fallback = ""): string {
    const value = obj[key];
    if (typeof value === "string") return value;
    if (value === null || value === undefined) return fallback;
    return String(value);
  }

  function readObject(value: unknown): Record<string, unknown> | null {
    if (typeof value !== "object" || value === null || Array.isArray(value)) return null;
    return value as Record<string, unknown>;
  }

  function isChartMode(value: unknown): value is ChartMode {
    return value === "bar" || value === "line" || value === "donut";
  }

  function isPivotMode(value: unknown): value is PivotMode {
    return value === "employees" || value === "department" || value === "location" || value === "employment_type";
  }

  function readColumnFilters(value: unknown): EmployeeColumnFilterState | null {
    const data = readObject(value);
    if (!data) return null;

    return {
      employee_name: readFilterValue(data, "employee_name"),
      department: readFilterValue(data, "department", "All") || "All",
      location: readFilterValue(data, "location", "All") || "All",
      employment_type: readFilterValue(data, "employment_type", "All") || "All",
      status: readFilterValue(data, "status", "All") || "All",
    };
  }

  function readColumnVisibility(value: unknown): EmployeeColumnVisibility | null {
    const data = readObject(value);
    if (!data) return null;

    const next = { ...defaultEmployeeColumnVisibility };
    for (const key of Object.keys(defaultEmployeeColumnVisibility) as EmployeeColumnKey[]) {
      const item = data[key];
      if (typeof item === "boolean") {
        next[key] = item;
      }
    }

    if (!Object.values(next).some(Boolean)) {
      next.employee_name = true;
    }
    return next;
  }

  function buildSavedViewFilters(): Record<string, unknown> {
    return {
      ...toFilterPayload(),
      view_settings: {
        chart_type: chartMode,
        pivot_mode: pivotMode,
        column_filters: columnFilters,
        drill_department: drillDepartment,
      } satisfies SavedViewSettings,
    };
  }

  function buildColumnVisibilityPayload(): Record<string, unknown> {
    return {
      employee_columns: employeeColumnVisibility,
    };
  }

  function applySavedView(view: ReportSavedView) {
    const data = view.filters ?? {};
    filters = {
      date_from: readFilterValue(data, "date_from"),
      date_to: readFilterValue(data, "date_to"),
      department: readFilterValue(data, "department", "All Departments") || "All Departments",
      location: readFilterValue(data, "location", "All Locations") || "All Locations",
      employment_type: readFilterValue(data, "employment_type", "All Types") || "All Types",
    };

    const settingsData = readObject((data as Record<string, unknown>).view_settings);
    if (settingsData) {
      if (isChartMode(settingsData.chart_type)) chartMode = settingsData.chart_type;
      if (isPivotMode(settingsData.pivot_mode)) pivotMode = settingsData.pivot_mode;

      const savedColumnFilters = readColumnFilters(settingsData.column_filters);
      if (savedColumnFilters) {
        columnFilters = savedColumnFilters;
      }

      if (typeof settingsData.drill_department === "string") {
        drillDepartment = settingsData.drill_department;
      } else if (settingsData.drill_department === null) {
        drillDepartment = null;
      }
    }

    const visibilityObj = readObject(view.column_visibility)?.employee_columns;
    const savedVisibility = readColumnVisibility(visibilityObj);
    if (savedVisibility) {
      employeeColumnVisibility = savedVisibility;
    }
  }

  function sortIndicator(column: SortColumn): string {
    if (sortColumn !== column) return "";
    return sortDirection === "asc" ? "↑" : "↓";
  }

  function toggleSort(column: SortColumn) {
    if (sortColumn === column) {
      sortDirection = sortDirection === "asc" ? "desc" : "asc";
      return;
    }
    sortColumn = column;
    sortDirection = "asc";
  }

  function valueForSort(row: EmployeeRecord | PivotRow, key: SortColumn): string | number {
    const value = (row as Record<string, unknown>)[key];
    if (typeof value === "number" || typeof value === "string") return value;
    return "";
  }

  function sortRows<T extends EmployeeRecord | PivotRow>(rows: T[], key: SortColumn, direction: SortDirection): T[] {
    return [...rows].sort((left, right) => {
      const a = valueForSort(left, key);
      const b = valueForSort(right, key);

      let comparison = 0;
      if (typeof a === "number" && typeof b === "number") {
        comparison = a - b;
      } else {
        comparison = String(a).localeCompare(String(b), undefined, { sensitivity: "base" });
      }
      return direction === "asc" ? comparison : -comparison;
    });
  }

  function buildPivotRows(rows: EmployeeRecord[], groupBy: PivotDimension): PivotRow[] {
    const map = new Map<string, PivotRow>();

    for (const row of rows) {
      const group = row[groupBy];
      const existing = map.get(group);
      if (existing) {
        existing.headcount += 1;
        if (row.status === "Active") existing.active += 1;
        if (row.status === "On Leave") existing.on_leave += 1;
        if (row.status === "Probation") existing.probation += 1;
      } else {
        map.set(group, {
          group,
          headcount: 1,
          active: row.status === "Active" ? 1 : 0,
          on_leave: row.status === "On Leave" ? 1 : 0,
          probation: row.status === "Probation" ? 1 : 0,
        });
      }
    }

    return Array.from(map.values());
  }

  function activePivotDimension(mode: PivotMode): PivotDimension {
    if (mode === "employees") return "department";
    return mode;
  }

  function formatPivotGroup(dimension: PivotDimension, value: string): string {
    if (dimension === "employment_type") return formatEmploymentType(value);
    return value;
  }

  function uniqueValues(
    rows: EmployeeRecord[],
    key: "department" | "location" | "employment_type" | "status",
  ): string[] {
    const values = new Set<string>();
    for (const row of rows) values.add(String(row[key]));
    return Array.from(values).sort((left, right) => left.localeCompare(right));
  }

  function resetInteractiveState() {
    pivotMode = "employees";
    chartMode = "bar";
    sortColumn = "employee_name";
    sortDirection = "asc";
    drillDepartment = null;
    selectedEmployeeId = null;
    employeeColumnVisibility = { ...defaultEmployeeColumnVisibility };
    resetColumnFilters();
  }

  function resetColumnFilters() {
    columnFilters = {
      employee_name: "",
      department: "All",
      location: "All",
      employment_type: "All",
      status: "All",
    };
    drillDepartment = null;
    selectedEmployeeId = null;
  }

  function setEmployeeColumnVisibility(column: EmployeeColumnKey, nextValue: boolean) {
    const visibleCount = Object.values(employeeColumnVisibility).filter(Boolean).length;
    if (!nextValue && visibleCount <= 1 && employeeColumnVisibility[column]) {
      toast.warning("At least one column required", "Keep at least one employee column visible.");
      return;
    }

    employeeColumnVisibility = {
      ...employeeColumnVisibility,
      [column]: nextValue,
    };
  }

  function drillIntoDepartment(department: string) {
    drillDepartment = department;
    pivotMode = "employees";
    sortColumn = "employee_name";
    sortDirection = "asc";
    toast.info("Drill-down applied", `Showing employees in ${department}.`);
  }

  function drillIntoGroup(group: string) {
    if (pivotMode === "department") {
      drillIntoDepartment(group);
      return;
    }

    if (pivotMode === "location") {
      columnFilters = { ...columnFilters, location: group };
      pivotMode = "employees";
      sortColumn = "employee_name";
      sortDirection = "asc";
      toast.info("Drill-down applied", `Showing employees in ${group}.`);
      return;
    }

    if (pivotMode === "employment_type") {
      columnFilters = { ...columnFilters, employment_type: group };
      pivotMode = "employees";
      sortColumn = "employee_name";
      sortDirection = "asc";
      toast.info("Drill-down applied", `Showing ${formatEmploymentType(group)} employees.`);
    }
  }

  function clearDrillDown() {
    drillDepartment = null;
    toast.info("Drill-down cleared", "Showing all departments in current filters.");
  }

  async function loadExecutionScreen() {
    if (!reportId || Number.isNaN(reportId)) {
      loading = false;
      return;
    }

    loading = true;
    try {
      const [templatePayload, savedViewsPayload, subscriptionsPayload, runsPayload] = await Promise.all([
        api.get<ReportTemplate>(`/settings/report-templates/${reportId}/`),
        api.get<PaginatedResponse<ReportSavedView> | ReportSavedView[]>("/settings/report-saved-views/", {
          report_template: String(reportId),
          ordering: "-updated_at",
        }),
        api.get<PaginatedResponse<ReportSubscription> | ReportSubscription[]>("/settings/report-subscriptions/", {
          report_template: String(reportId),
          ordering: "-updated_at",
        }),
        api.get<PaginatedResponse<ReportRunRecord> | ReportRunRecord[]>("/settings/report-runs/", {
          report_template: String(reportId),
          ordering: "-created_at",
        }),
      ]);

      report = templatePayload;
      outputFormat = templatePayload.output_format || "pdf";

      savedViews = unwrapList(savedViewsPayload);
      subscriptions = unwrapList(subscriptionsPayload);
      runs = unwrapList(runsPayload);
      latestRun = runs[0] ?? null;

      const preferredSubscription =
        subscriptions.find((item) => item.frequency === subscriptionFrequency) ?? subscriptions[0] ?? null;
      if (preferredSubscription) {
        subscriptionFrequency = preferredSubscription.frequency;
        subscriptionDeliveryChannels =
          preferredSubscription.delivery_channels?.length > 0
            ? [...preferredSubscription.delivery_channels]
            : ["email"];
        subscriptionRecipients = preferredSubscription.recipients.join(", ");
      } else {
        subscriptionDeliveryChannels = ["email"];
        subscriptionRecipients = "";
      }

      resetInteractiveState();

      const savedViewIdParam = Number($page.url.searchParams.get("savedView") || "0");
      const selectedView =
        savedViews.find((item) => item.id === savedViewIdParam) ??
        savedViews.find((item) => item.is_default) ??
        savedViews[0];

      if (selectedView) {
        selectedSavedViewId = String(selectedView.id);
        applySavedView(selectedView);
      } else {
        selectedSavedViewId = "";
      }
    } catch {
      toast.error("Load failed", "Could not load report execution screen.");
    } finally {
      loading = false;
    }
  }

  async function runReport(
    formatOverride?: ReportOutputFormat,
    requestedAction: ReportRunAction = "run",
  ) {
    if (!report) return;
    running = true;
    try {
      const payload: Record<string, unknown> = {
        filters: toFilterPayload(),
        requested_action: requestedAction,
      };
      if (requestedAction === "export") {
        payload.output_format = formatOverride ?? outputFormat;
      }
      if (selectedSavedViewId) payload.saved_view_id = Number(selectedSavedViewId);

      const run = await api.post<ReportRunRecord>(`/settings/report-templates/${report.id}/run/`, payload);
      latestRun = run;
      runs = [run, ...runs.filter((item) => item.id !== run.id)];
      resetInteractiveState();
      toast.success("Report queued", `${report.name} run completed with status ${run.status_display}.`);
    } catch (error) {
      if (error instanceof ApiError) {
        const message =
          error.fieldErrors.output_format?.[0] ||
          error.fieldErrors.non_field_errors?.[0] ||
          "Could not execute report.";
        toast.error("Run failed", message);
      } else {
        toast.error("Run failed", "Could not execute report.");
      }
    } finally {
      running = false;
    }
  }

  async function exportResult(format: ReportOutputFormat) {
    if (!report) return;
    if (exportBlocked) {
      toast.error(
        "Export blocked",
        `${confidentialityLabelName} policy disables file export for this report.`,
      );
      return;
    }
    exportingFormat = format;
    try {
      await runReport(format, "export");
    } finally {
      exportingFormat = null;
    }
  }

  function printResult() {
    if (!report) return;
    if (printBlocked) {
      toast.error(
        "Printing blocked",
        `${confidentialityLabelName} policy disables printing for this report.`,
      );
      return;
    }
    if (typeof window === "undefined") return;
    window.print();
    toast.success("Print opened", "Print dialog opened for report results.");
  }

  async function saveCurrentView() {
    if (!report) return;
    const name = viewName.trim();
    if (!name) {
      toast.error("Missing name", "Enter a view name before saving.");
      return;
    }

    savingView = true;
    try {
      const payload = {
        name,
        report_template: report.id,
        filters: buildSavedViewFilters(),
        column_visibility: buildColumnVisibilityPayload(),
        rows_per_page: 25,
        is_default: savedViews.length === 0,
        is_active: true,
      };
      const created = await api.post<ReportSavedView>("/settings/report-saved-views/", payload);
      savedViews = [created, ...savedViews.filter((item) => item.id !== created.id)];
      selectedSavedViewId = String(created.id);
      viewName = "";
      toast.success("View saved", `${created.name} is now available in saved views.`);
    } catch (error) {
      if (error instanceof ApiError && error.fieldErrors.name?.length) {
        toast.error("Save failed", error.fieldErrors.name[0]);
      } else {
        toast.error("Save failed", "Could not save view.");
      }
    } finally {
      savingView = false;
    }
  }

  function parseRecipients(input: string): string[] {
    return input
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function toggleSubscriptionDeliveryChannel(channel: ReportSubscriptionDeliveryChannel) {
    if (subscriptionDeliveryChannels.includes(channel)) {
      subscriptionDeliveryChannels = subscriptionDeliveryChannels.filter((item) => item !== channel);
      return;
    }
    subscriptionDeliveryChannels = [...subscriptionDeliveryChannels, channel];
  }

  async function subscribeToReport() {
    if (!report) return;

    if (subscriptionDeliveryChannels.length === 0) {
      toast.error("Missing delivery", "Select at least one delivery channel.");
      return;
    }

    const recipients = subscriptionDeliveryChannels.includes("email")
      ? parseRecipients(subscriptionRecipients)
      : [];
    if (subscriptionDeliveryChannels.includes("email") && recipients.length === 0) {
      toast.error("Missing recipients", "Enter at least one recipient email for Email delivery.");
      return;
    }

    savingSubscription = true;
    const createPayload = {
      report_template: report.id,
      frequency: subscriptionFrequency,
      output_format: outputFormat,
      recipients,
      delivery_channels: subscriptionDeliveryChannels,
      is_active: true,
    };

    try {
      const created = await api.post<ReportSubscription>("/settings/report-subscriptions/", createPayload);
      subscriptions = [created, ...subscriptions.filter((item) => item.id !== created.id)];
      toast.success("Subscription saved", `${created.frequency_display} subscription is active.`);
      return;
    } catch (error) {
      const existing = subscriptions.find((item) => item.frequency === subscriptionFrequency);
      if (!existing) {
        toast.error("Subscribe failed", "Could not create subscription.");
        savingSubscription = false;
        return;
      }

      try {
        const updated = await api.patch<ReportSubscription>(
          `/settings/report-subscriptions/${existing.id}/`,
          {
            frequency: subscriptionFrequency,
            output_format: outputFormat,
            recipients,
            delivery_channels: subscriptionDeliveryChannels,
            is_active: true,
          },
        );
        subscriptions = [updated, ...subscriptions.filter((item) => item.id !== updated.id)];
        toast.success("Subscription updated", `${updated.frequency_display} subscription refreshed.`);
      } catch (patchError) {
        if (
          patchError instanceof ApiError &&
          (patchError.fieldErrors.recipients?.length || patchError.fieldErrors.delivery_channels?.length)
        ) {
          toast.error(
            "Subscribe failed",
            patchError.fieldErrors.recipients?.[0] ??
              patchError.fieldErrors.delivery_channels?.[0] ??
              "Could not create or update subscription.",
          );
        } else if (
          error instanceof ApiError &&
          (error.fieldErrors.recipients?.length || error.fieldErrors.delivery_channels?.length)
        ) {
          toast.error(
            "Subscribe failed",
            error.fieldErrors.recipients?.[0] ??
              error.fieldErrors.delivery_channels?.[0] ??
              "Could not create or update subscription.",
          );
        } else {
          toast.error("Subscribe failed", "Could not create or update subscription.");
        }
      } finally {
        savingSubscription = false;
      }
      return;
    } finally {
      savingSubscription = false;
    }
  }

  async function shareReport() {
    sharing = true;
    try {
      if (typeof window === "undefined") return;
      await navigator.clipboard.writeText(window.location.href);
      toast.success("Link copied", "Report link copied to clipboard.");
    } catch {
      toast.error("Share failed", "Could not copy report link.");
    } finally {
      sharing = false;
    }
  }

  const scopedEmployees = $derived.by<EmployeeRecord[]>(() => {
    if (!latestRun) return [];

    let rows = [...employeeSeed];

    if (filters.department !== "All Departments") {
      rows = rows.filter((row) => row.department === filters.department);
    }
    if (filters.location !== "All Locations") {
      rows = rows.filter((row) => row.location === filters.location);
    }
    if (filters.employment_type !== "All Types") {
      rows = rows.filter((row) => row.employment_type === filters.employment_type);
    }

    if (drillDepartment) {
      rows = rows.filter((row) => row.department === drillDepartment);
    }

    if (columnFilters.employee_name.trim()) {
      const query = columnFilters.employee_name.trim().toLowerCase();
      rows = rows.filter(
        (row) =>
          row.employee_name.toLowerCase().includes(query) ||
          row.employee_code.toLowerCase().includes(query),
      );
    }

    if (columnFilters.department !== "All") {
      rows = rows.filter((row) => row.department === columnFilters.department);
    }
    if (columnFilters.location !== "All") {
      rows = rows.filter((row) => row.location === columnFilters.location);
    }
    if (columnFilters.employment_type !== "All") {
      rows = rows.filter((row) => row.employment_type === columnFilters.employment_type);
    }
    if (columnFilters.status !== "All") {
      rows = rows.filter((row) => row.status === columnFilters.status);
    }

    return rows;
  });

  const departmentFilterOptions = $derived.by(() => ["All", ...uniqueValues(employeeSeed, "department")]);
  const locationFilterOptions = $derived.by(() => ["All", ...uniqueValues(employeeSeed, "location")]);
  const employmentTypeFilterOptions = $derived.by(() => ["All", ...uniqueValues(employeeSeed, "employment_type")]);
  const statusFilterOptions = $derived.by(() => ["All", ...uniqueValues(employeeSeed, "status")]);

  const selectedEmployee = $derived.by(() => {
    if (selectedEmployeeId === null) return null;
    return scopedEmployees.find((row) => row.id === selectedEmployeeId) ?? null;
  });

  const pivotRows = $derived.by<PivotRow[]>(() => {
    if (pivotMode === "employees") return [];
    return buildPivotRows(scopedEmployees, pivotMode);
  });

  const sortedEmployees = $derived.by<EmployeeRecord[]>(() => {
    const employeeSortKey: SortColumn = employeeColumns.some((column) => column.key === sortColumn)
      ? sortColumn
      : "employee_name";
    return sortRows(scopedEmployees, employeeSortKey, sortDirection);
  });

  const sortedPivotRows = $derived.by<PivotRow[]>(() => {
    const pivotSortKey: SortColumn = pivotColumns.some((column) => column.key === sortColumn)
      ? sortColumn
      : "headcount";
    return sortRows(pivotRows, pivotSortKey, sortDirection);
  });

  const visibleEmployeeColumns = $derived.by<TableColumn[]>(() => {
    return employeeColumns.filter((column) => {
      const key = column.key as EmployeeColumnKey;
      return employeeColumnVisibility[key] !== false;
    });
  });

  const activeTableColumns = $derived.by<TableColumn[]>(() => {
    return pivotMode === "employees" ? visibleEmployeeColumns : pivotColumns;
  });

  const tableRowCount = $derived.by(() => {
    return pivotMode === "employees" ? sortedEmployees.length : sortedPivotRows.length;
  });

  const activePivotLabel = $derived.by(() => {
    return pivotModes.find((mode) => mode.value === pivotMode)?.label ?? "Employees";
  });

  const drillHint = $derived.by(() => {
    if (pivotMode === "department") return "Department -> click -> view employees";
    if (pivotMode === "location") return "Location -> click -> filter employees";
    if (pivotMode === "employment_type") return "Employment Type -> click -> filter employees";
    return "Employee -> click -> open profile";
  });

  const chartPoints = $derived.by<ChartPoint[]>(() => {
    const dimension = activePivotDimension(pivotMode);
    const source =
      pivotMode === "employees"
        ? buildPivotRows(scopedEmployees, "department")
        : sortedPivotRows;

    return source.map((row) => ({
      label: formatPivotGroup(dimension, row.group),
      value: row.headcount,
    }));
  });

  const chartMax = $derived.by(() => {
    return Math.max(...chartPoints.map((item) => item.value), 1);
  });

  const chartTotal = $derived.by(() => {
    return chartPoints.reduce((sum, item) => sum + item.value, 0);
  });

  const lineGeometry = $derived.by<LinePoint[]>(() => {
    if (chartPoints.length === 0) return [];

    const width = 360;
    const height = 150;
    const xStep = chartPoints.length > 1 ? width / (chartPoints.length - 1) : 0;

    return chartPoints.map((point, index) => ({
      x: chartPoints.length > 1 ? index * xStep : width / 2,
      y: height - (point.value / chartMax) * (height - 18) - 9,
      label: point.label,
      value: point.value,
    }));
  });

  const linePath = $derived.by(() => {
    return lineGeometry.map((point) => `${point.x},${point.y}`).join(" ");
  });

  const donutGradient = $derived.by(() => {
    if (chartTotal === 0) return "conic-gradient(#e5e7eb 0deg 360deg)";

    let angle = 0;
    const segments: string[] = [];
    chartPoints.forEach((point, index) => {
      const slice = (point.value / chartTotal) * 360;
      const start = angle;
      const end = angle + slice;
      segments.push(`${chartPalette[index % chartPalette.length]} ${start}deg ${end}deg`);
      angle = end;
    });

    return `conic-gradient(${segments.join(", ")})`;
  });

  const summaryText = $derived.by(() => {
    const baseline = String(
      latestRun?.result_summary?.message || "Run accepted and processed by the centralized reporting workspace.",
    );

    const context: string[] = [];
    if (drillDepartment) context.push(`department drill-down: ${drillDepartment}`);
    if (columnFilters.employee_name.trim()) {
      context.push(`name filter: ${columnFilters.employee_name.trim()}`);
    }
    if (pivotMode !== "employees") context.push(`pivot view: ${activePivotLabel}`);
    context.push(`chart: ${chartMode}`);

    if (context.length === 0) return baseline;
    return `${baseline} Interactive scope -> ${context.join(" | ")}.`;
  });

  $effect(() => {
    const validColumns = activeTableColumns.map((column) => column.key);
    if (!validColumns.includes(sortColumn)) {
      if (pivotMode === "employees") {
        sortColumn = (visibleEmployeeColumns[0]?.key as SortColumn) ?? "employee_name";
        sortDirection = "asc";
      } else {
        sortColumn = "headcount";
        sortDirection = "desc";
      }
    }
  });

  $effect(() => {
    void reportId;
    void $page.url.search;
    void loadExecutionScreen();
  });
</script>

{#if loading}
  <div class="rounded-xl border border-neutral-200 bg-white p-8 text-sm text-neutral-500">
    Loading report execution screen...
  </div>
{:else if !report}
  <div class="rounded-xl border border-red-200 bg-red-50 p-8 text-sm text-red-700">
    Report not found.
  </div>
{:else}
  <div class="space-y-6">
    <section class="rounded-xl border border-neutral-200 bg-white p-5">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Report</p>
          <h1 class="mt-1 text-2xl font-bold text-neutral-900">{report.name}</h1>
          <p class="mt-2 text-sm text-neutral-600">{report.description || "No description provided."}</p>
        </div>
        <a
          href="/reports"
          class="inline-flex items-center gap-2 rounded-lg border border-neutral-300 px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
        >
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
          </svg>
          Back to Library
        </a>
      </div>
      <div class="mt-4 grid grid-cols-1 gap-2 text-xs text-neutral-600 sm:grid-cols-2 lg:grid-cols-4">
        <p><span class="font-semibold text-neutral-800">Module:</span> {report.module_source_display}</p>
        <p><span class="font-semibold text-neutral-800">Owner:</span> {report.owner_name || "Unassigned"}</p>
        <p><span class="font-semibold text-neutral-800">Confidentiality:</span> {report.confidentiality_label_name || "Not classified"}</p>
        <p><span class="font-semibold text-neutral-800">Simple Builder:</span> {report.allow_simple_builder ? "Allowed" : "Restricted"}</p>
      </div>
    </section>

    <section class="rounded-xl border border-neutral-200 bg-white p-5">
      <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-700">Filters</h2>
      <div class="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        <label class="text-xs font-medium text-neutral-600">
          Date Range (From)
          <DateInput bind:value={filters.date_from} />
        </label>
        <label class="text-xs font-medium text-neutral-600">
          Date Range (To)
          <DateInput bind:value={filters.date_to} />
        </label>
        <label class="text-xs font-medium text-neutral-600">
          Department
          <select bind:value={filters.department} class="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm text-neutral-800">
            {#each departmentOptions as option}
              <option value={option}>{option}</option>
            {/each}
          </select>
        </label>
        <label class="text-xs font-medium text-neutral-600">
          Location
          <select bind:value={filters.location} class="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm text-neutral-800">
            {#each locationOptions as option}
              <option value={option}>{option}</option>
            {/each}
          </select>
        </label>
        <label class="text-xs font-medium text-neutral-600">
          Employment Type
          <select bind:value={filters.employment_type} class="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm text-neutral-800">
            {#each employmentTypeOptions as option}
              <option value={option}>{option === "All Types" ? option : formatEmploymentType(option)}</option>
            {/each}
          </select>
        </label>
        <label class="text-xs font-medium text-neutral-600">
          Saved View
          <select
            bind:value={selectedSavedViewId}
            class="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm text-neutral-800"
            onchange={() => {
              const selected = savedViews.find((item) => item.id === Number(selectedSavedViewId));
              if (selected) applySavedView(selected);
            }}
          >
            <option value="">Select a saved view...</option>
            {#each savedViews as view}
              <option value={String(view.id)}>{view.name}</option>
            {/each}
          </select>
        </label>
      </div>

      <div class="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <label class="text-xs font-medium text-neutral-600">
          Output Format
          <select bind:value={outputFormat} class="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm text-neutral-800 sm:min-w-[180px]">
            <option value="pdf">PDF</option>
            <option value="xlsx">Excel</option>
            <option value="csv">CSV</option>
            <option value="pdf_xlsx">PDF + Excel</option>
          </select>
        </label>
        <button
          type="button"
          onclick={() => runReport()}
          disabled={running}
          class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {running ? "Running..." : "Run Report"}
        </button>
      </div>
    </section>

    {#if latestRun}
      <section class="rounded-xl border border-neutral-200 bg-white p-5 space-y-5">
        <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-700">Results</h2>
          <div class="flex flex-wrap items-center gap-2">
            <span class="text-xs font-semibold text-neutral-500 uppercase tracking-wider">Export</span>
            <button
              type="button"
              onclick={() => exportResult("pdf")}
              disabled={exportingFormat !== null || exportBlocked}
              class="rounded-lg border border-neutral-300 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50 disabled:opacity-60"
            >
              {exportingFormat === "pdf" ? "Exporting..." : "PDF"}
            </button>
            <button
              type="button"
              onclick={() => exportResult("xlsx")}
              disabled={exportingFormat !== null || exportBlocked}
              class="rounded-lg border border-neutral-300 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50 disabled:opacity-60"
            >
              {exportingFormat === "xlsx" ? "Exporting..." : "Excel"}
            </button>
            <button
              type="button"
              onclick={() => exportResult("csv")}
              disabled={exportingFormat !== null || exportBlocked}
              class="rounded-lg border border-neutral-300 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50 disabled:opacity-60"
            >
              {exportingFormat === "csv" ? "Exporting..." : "CSV"}
            </button>
            <button
              type="button"
              onclick={printResult}
              disabled={printBlocked}
              class="rounded-lg border border-neutral-300 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50 disabled:opacity-60"
            >
              Print
            </button>
          </div>
        </div>

        {#if exportBlocked || printBlocked}
          <p class="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
            Export policy: {confidentialityLabelName}
            {exportBlocked ? " disables file downloads." : ""}
            {printBlocked ? " disables printing." : ""}
          </p>
        {/if}

        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
            <p class="text-[11px] uppercase tracking-wider text-neutral-500">Visible Records</p>
            <p class="mt-1 text-xl font-bold text-neutral-900">{tableRowCount}</p>
          </div>
          <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
            <p class="text-[11px] uppercase tracking-wider text-neutral-500">Run Status</p>
            <p class="mt-1 text-xl font-bold text-neutral-900">{latestRun.status_display}</p>
          </div>
          <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
            <p class="text-[11px] uppercase tracking-wider text-neutral-500">Last Run</p>
            <p class="mt-1 text-sm font-semibold text-neutral-900">{formatDateTime(latestRun.created_at)}</p>
          </div>
          <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
            <p class="text-[11px] uppercase tracking-wider text-neutral-500">Duration</p>
            <p class="mt-1 text-xl font-bold text-neutral-900">{runDuration(latestRun)}</p>
          </div>
        </div>

        <article class="rounded-lg border border-neutral-200 bg-neutral-50 p-4 space-y-4">
          <div class="grid grid-cols-1 gap-3 lg:grid-cols-3">
            <label class="text-xs font-medium text-neutral-600">
              Pivot View
              <select bind:value={pivotMode} class="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm text-neutral-800">
                {#each pivotModes as mode}
                  <option value={mode.value}>{mode.label}</option>
                {/each}
              </select>
            </label>
            <div class="text-xs text-neutral-600">
              <p class="font-medium">Current Hint</p>
              <p class="mt-2 rounded-lg border border-neutral-200 bg-white px-3 py-2 text-neutral-700">{drillHint}</p>
            </div>
            <div class="flex items-end justify-start lg:justify-end">
              <button
                type="button"
                onclick={resetColumnFilters}
                class="rounded-lg border border-neutral-300 bg-white px-3 py-2 text-xs font-semibold text-neutral-700 hover:bg-neutral-100"
              >
                Clear Column Filters
              </button>
            </div>
          </div>

          <div class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-5">
            <label class="text-xs font-medium text-neutral-600">
              Employee Search
              <input
                type="text"
                bind:value={columnFilters.employee_name}
                placeholder="Name or ID"
                class="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm text-neutral-800"
              />
            </label>
            <label class="text-xs font-medium text-neutral-600">
              Department Column
              <select bind:value={columnFilters.department} class="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm text-neutral-800">
                {#each departmentFilterOptions as option}
                  <option value={option}>{option}</option>
                {/each}
              </select>
            </label>
            <label class="text-xs font-medium text-neutral-600">
              Location Column
              <select bind:value={columnFilters.location} class="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm text-neutral-800">
                {#each locationFilterOptions as option}
                  <option value={option}>{option}</option>
                {/each}
              </select>
            </label>
            <label class="text-xs font-medium text-neutral-600">
              Employment Type Column
              <select bind:value={columnFilters.employment_type} class="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm text-neutral-800">
                {#each employmentTypeFilterOptions as option}
                  <option value={option}>{option === "All" ? option : formatEmploymentType(option)}</option>
                {/each}
              </select>
            </label>
            <label class="text-xs font-medium text-neutral-600">
              Status Column
              <select bind:value={columnFilters.status} class="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm text-neutral-800">
                {#each statusFilterOptions as option}
                  <option value={option}>{option}</option>
                {/each}
              </select>
            </label>
          </div>

          <div class="rounded-lg border border-neutral-200 bg-white p-3">
            <p class="text-xs font-medium text-neutral-600">Columns (saved with view)</p>
            <div class="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-4">
              {#each employeeColumns as column}
                <label class="inline-flex items-center gap-2 text-xs text-neutral-700">
                  <input
                    type="checkbox"
                    checked={employeeColumnVisibility[column.key as EmployeeColumnKey]}
                    onchange={(event) => {
                      const target = event.currentTarget as HTMLInputElement;
                      setEmployeeColumnVisibility(column.key as EmployeeColumnKey, target.checked);
                    }}
                    class="rounded border-neutral-300"
                  />
                  <span>{column.label}</span>
                </label>
              {/each}
            </div>
          </div>

          {#if drillDepartment}
            <div class="flex items-center justify-between rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-800">
              <p>Drill-down active: {drillDepartment} department</p>
              <button type="button" onclick={clearDrillDown} class="font-semibold text-emerald-700 hover:text-emerald-900">Clear drill-down</button>
            </div>
          {/if}
        </article>

        <div class="grid grid-cols-1 gap-4 xl:grid-cols-[1.8fr_1fr]">
          <article class="rounded-lg border border-neutral-200 overflow-hidden">
            <header class="border-b border-neutral-200 px-4 py-3 flex items-center justify-between gap-3">
              <div>
                <h3 class="text-sm font-semibold text-neutral-900">Table</h3>
                <p class="text-xs text-neutral-500">Sorting and drill-down are enabled.</p>
              </div>
              <span class="text-xs text-neutral-500">View: {activePivotLabel}</span>
            </header>

            <div class="overflow-x-auto">
              <table class="min-w-full text-sm">
                <thead class="bg-neutral-50">
                  <tr>
                    {#each activeTableColumns as column}
                      <th
                        class="px-4 py-2 font-medium text-neutral-600"
                        class:text-right={column.align === "right"}
                        class:text-left={column.align !== "right"}
                      >
                        <button
                          type="button"
                          onclick={() => toggleSort(column.key)}
                          class="inline-flex items-center gap-1 hover:text-neutral-900"
                        >
                          {column.label}
                          {#if sortIndicator(column.key)}
                            <span class="text-[11px] text-neutral-400">{sortIndicator(column.key)}</span>
                          {/if}
                        </button>
                      </th>
                    {/each}
                  </tr>
                </thead>
                <tbody>
                  {#if pivotMode === "employees"}
                    {#if sortedEmployees.length === 0}
                      <tr class="border-t border-neutral-100">
                        <td colspan={activeTableColumns.length} class="px-4 py-6 text-center text-neutral-500">No rows match the current filters.</td>
                      </tr>
                    {:else}
                      {#each sortedEmployees as row}
                        <tr class="border-t border-neutral-100 hover:bg-neutral-50/70">
                          {#each activeTableColumns as column}
                            {#if column.key === "employee_code"}
                              <td class="px-4 py-2 text-neutral-700">{row.employee_code}</td>
                            {:else if column.key === "employee_name"}
                              <td class="px-4 py-2 text-neutral-900">
                                <button
                                  type="button"
                                  onclick={() => {
                                    selectedEmployeeId = row.id;
                                  }}
                                  class="font-semibold hover:text-neutral-700"
                                >
                                  {row.employee_name}
                                </button>
                              </td>
                            {:else if column.key === "department"}
                              <td class="px-4 py-2 text-neutral-700">
                                <button
                                  type="button"
                                  onclick={() => drillIntoDepartment(row.department)}
                                  class="rounded bg-neutral-100 px-2 py-0.5 text-xs font-medium text-neutral-700 hover:bg-neutral-200"
                                >
                                  {row.department}
                                </button>
                              </td>
                            {:else if column.key === "location"}
                              <td class="px-4 py-2 text-neutral-700">{row.location}</td>
                            {:else if column.key === "employment_type"}
                              <td class="px-4 py-2 text-neutral-700">{formatEmploymentType(row.employment_type)}</td>
                            {:else if column.key === "status"}
                              <td class="px-4 py-2 text-neutral-700">
                                <span class="rounded bg-neutral-100 px-2 py-0.5 text-xs font-medium text-neutral-700">{row.status}</span>
                              </td>
                            {:else if column.key === "job_title"}
                              <td class="px-4 py-2 text-neutral-700">{row.job_title}</td>
                            {/if}
                          {/each}
                        </tr>
                      {/each}
                    {/if}
                  {:else}
                    {#if sortedPivotRows.length === 0}
                      <tr class="border-t border-neutral-100">
                        <td colspan={pivotColumns.length} class="px-4 py-6 text-center text-neutral-500">No grouped rows available for this view.</td>
                      </tr>
                    {:else}
                      {#each sortedPivotRows as row}
                        <tr class="border-t border-neutral-100 hover:bg-neutral-50/70">
                          <td class="px-4 py-2 text-neutral-900">
                            <button
                              type="button"
                              onclick={() => drillIntoGroup(row.group)}
                              class="font-semibold hover:text-neutral-700"
                            >
                              {formatPivotGroup(activePivotDimension(pivotMode), row.group)}
                            </button>
                          </td>
                          <td class="px-4 py-2 text-right text-neutral-700">{row.headcount}</td>
                          <td class="px-4 py-2 text-right text-neutral-700">{row.active}</td>
                          <td class="px-4 py-2 text-right text-neutral-700">{row.on_leave}</td>
                          <td class="px-4 py-2 text-right text-neutral-700">{row.probation}</td>
                        </tr>
                      {/each}
                    {/if}
                  {/if}
                </tbody>
              </table>
            </div>
          </article>

          <article class="rounded-lg border border-neutral-200 p-4">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <div>
                <h3 class="text-sm font-semibold text-neutral-900">Charts</h3>
                <p class="mt-1 text-xs text-neutral-500">Switch chart style for the current report view.</p>
              </div>
              <div class="flex items-center gap-1 rounded-lg border border-neutral-200 bg-white p-1">
                {#each chartModes as mode}
                  <button
                    type="button"
                    onclick={() => (chartMode = mode.value)}
                    class="rounded-md px-2.5 py-1 text-xs font-semibold transition-colors {chartMode === mode.value ? 'bg-neutral-900 text-white' : 'text-neutral-600 hover:bg-neutral-100'}"
                  >
                    {mode.label}
                  </button>
                {/each}
              </div>
            </div>

            {#if chartPoints.length === 0}
              <p class="mt-6 text-sm text-neutral-500">Run a report to render chart data.</p>
            {:else if chartMode === "bar"}
              <div class="mt-4 space-y-2">
                {#each chartPoints as point, index}
                  <div>
                    <div class="mb-1 flex items-center justify-between text-xs text-neutral-600">
                      <span>{point.label}</span>
                      <span>{point.value}</span>
                    </div>
                    <div class="h-2 w-full rounded-full bg-neutral-200">
                      <div
                        class="h-2 rounded-full"
                        style={`width: ${Math.max(6, Math.round((point.value / chartMax) * 100))}%; background-color: ${chartPalette[index % chartPalette.length]};`}
                      ></div>
                    </div>
                  </div>
                {/each}
              </div>
            {:else if chartMode === "line"}
              <div class="mt-4">
                <svg viewBox="0 0 360 160" class="h-48 w-full" role="img" aria-label="Line chart preview">
                  <polyline points={linePath} fill="none" stroke="#111827" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
                  {#each lineGeometry as point}
                    <circle cx={point.x} cy={point.y} r="3.8" fill="#111827" />
                  {/each}
                </svg>
                <div class="mt-3 grid grid-cols-2 gap-2 text-xs text-neutral-600">
                  {#each chartPoints as point}
                    <div class="flex items-center justify-between rounded border border-neutral-200 px-2 py-1">
                      <span>{point.label}</span>
                      <span class="font-semibold text-neutral-800">{point.value}</span>
                    </div>
                  {/each}
                </div>
              </div>
            {:else}
              <div class="mt-4 flex flex-col gap-4 sm:flex-row sm:items-center">
                <div class="relative mx-auto h-40 w-40">
                  <div class="h-40 w-40 rounded-full" style={`background: ${donutGradient};`}></div>
                  <div class="absolute left-1/2 top-1/2 flex h-20 w-20 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-neutral-200 bg-white text-xs font-semibold text-neutral-700">
                    {chartTotal}
                  </div>
                </div>
                <div class="w-full space-y-2">
                  {#each chartPoints as point, index}
                    <div class="flex items-center justify-between text-xs text-neutral-600">
                      <div class="flex items-center gap-2">
                        <span class="h-2.5 w-2.5 rounded-full" style={`background-color: ${chartPalette[index % chartPalette.length]};`}></span>
                        <span>{point.label}</span>
                      </div>
                      <span class="font-semibold text-neutral-800">
                        {point.value}
                        ({chartTotal === 0 ? "0%" : `${Math.round((point.value / chartTotal) * 100)}%`})
                      </span>
                    </div>
                  {/each}
                </div>
              </div>
            {/if}
          </article>
        </div>

        <article class="rounded-lg border border-neutral-200 p-4">
          <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <h3 class="text-sm font-semibold text-neutral-900">Drill-down Profile</h3>
            {#if selectedEmployee}
              <a
                href={`/iam/users/profiles?employee=${selectedEmployee.id}`}
                class="inline-flex items-center gap-1 rounded-lg border border-neutral-300 px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-50"
              >
                Open Profile
                <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5H19.5m0 0V10.5m0-6L10.5 13.5" />
                  <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 13.5V18A1.5 1.5 0 0 1 18 19.5H6A1.5 1.5 0 0 1 4.5 18V6A1.5 1.5 0 0 1 6 4.5h4.5" />
                </svg>
              </a>
            {/if}
          </div>

          {#if selectedEmployee}
            <div class="mt-3 grid grid-cols-1 gap-3 text-sm text-neutral-700 sm:grid-cols-2 lg:grid-cols-4">
              <p><span class="font-semibold text-neutral-900">Employee:</span> {selectedEmployee.employee_name}</p>
              <p><span class="font-semibold text-neutral-900">ID:</span> {selectedEmployee.employee_code}</p>
              <p><span class="font-semibold text-neutral-900">Department:</span> {selectedEmployee.department}</p>
              <p><span class="font-semibold text-neutral-900">Location:</span> {selectedEmployee.location}</p>
              <p><span class="font-semibold text-neutral-900">Employment:</span> {formatEmploymentType(selectedEmployee.employment_type)}</p>
              <p><span class="font-semibold text-neutral-900">Status:</span> {selectedEmployee.status}</p>
              <p><span class="font-semibold text-neutral-900">Role:</span> {selectedEmployee.job_title}</p>
              <p><span class="font-semibold text-neutral-900">Manager:</span> {selectedEmployee.manager}</p>
              <p><span class="font-semibold text-neutral-900">Hire Date:</span> {formatDateOnly(selectedEmployee.hire_date)}</p>
            </div>
          {:else}
            <p class="mt-3 text-sm text-neutral-600">Select an employee in the table to drill into profile-level details.</p>
          {/if}
        </article>

        <article class="rounded-lg border border-neutral-200 p-4">
          <h3 class="text-sm font-semibold text-neutral-900">Summary</h3>
          <p class="mt-2 text-sm text-neutral-700">{summaryText}</p>
          <p class="mt-2 text-xs text-neutral-500">
            Trigger: {latestRun.trigger_display} · Output: {latestRun.output_format_display} · Completed: {formatDateTime(latestRun.completed_at)} · Rows from run: {latestRun.row_count}
          </p>
        </article>

        <div class="grid grid-cols-1 gap-4 xl:grid-cols-3">
          <article class="rounded-lg border border-neutral-200 p-4">
            <h3 class="text-sm font-semibold text-neutral-900">Save View</h3>
            <p class="mt-2 text-xs text-neutral-600">Saves current filters, selected columns, and chart type.</p>
            <input
              type="text"
              bind:value={viewName}
              placeholder="e.g. HR - Q1 Headcount"
              class="mt-3 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
            />
            <button
              type="button"
              onclick={saveCurrentView}
              disabled={savingView}
              class="mt-3 rounded-lg bg-neutral-900 px-3 py-2 text-xs font-semibold text-white hover:bg-neutral-800 disabled:opacity-60"
            >
              {savingView ? "Saving..." : "Save View"}
            </button>
          </article>

          <article class="rounded-lg border border-neutral-200 p-4">
            <h3 class="text-sm font-semibold text-neutral-900">Subscribe</h3>
            <p class="mt-2 text-xs text-neutral-600">
              Personal dispatch rule for this report. Admin dispatches remain organization-level.
            </p>
            <select bind:value={subscriptionFrequency} class="mt-3 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm">
              {#each subscriptionFrequencies as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
            <div class="mt-3 space-y-2">
              {#each subscriptionDeliveryOptions as option}
                <label class="flex items-start gap-2 rounded-lg border border-neutral-200 bg-neutral-50 px-2.5 py-2 text-xs text-neutral-700">
                  <input
                    type="checkbox"
                    checked={subscriptionDeliveryChannels.includes(option.value)}
                    onchange={() => toggleSubscriptionDeliveryChannel(option.value)}
                  />
                  <span>
                    <span class="font-semibold text-neutral-900">{option.label}</span>
                    <span class="mt-0.5 block text-[11px] text-neutral-500">{option.description}</span>
                  </span>
                </label>
              {/each}
            </div>
            <input
              type="text"
              bind:value={subscriptionRecipients}
              placeholder="emails separated by commas"
              class="mt-3 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm"
            />
            <p class="mt-1 text-[11px] text-neutral-500">Recipients are required only when Email delivery is selected.</p>
            <button
              type="button"
              onclick={subscribeToReport}
              disabled={savingSubscription}
              class="mt-3 rounded-lg bg-neutral-900 px-3 py-2 text-xs font-semibold text-white hover:bg-neutral-800 disabled:opacity-60"
            >
              {savingSubscription ? "Saving..." : "Subscribe"}
            </button>
          </article>

          <article class="rounded-lg border border-neutral-200 p-4">
            <h3 class="text-sm font-semibold text-neutral-900">Share</h3>
            <p class="mt-2 text-xs text-neutral-600">Share this report execution link with teammates.</p>
            <button
              type="button"
              onclick={shareReport}
              disabled={sharing}
              class="mt-3 rounded-lg border border-neutral-300 px-3 py-2 text-xs font-semibold text-neutral-700 hover:bg-neutral-50 disabled:opacity-60"
            >
              {sharing ? "Sharing..." : "Share"}
            </button>
          </article>
        </div>
      </section>
    {/if}
  </div>
{/if}

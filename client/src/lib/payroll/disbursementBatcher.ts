import { toAmount } from "$lib/contracts";
import type {
  BonusListItem,
  DeductionListItem,
  EmployeeDirectoryItem,
  PayslipListItem,
  PayrollRunListItem,
  ProjectListItem,
  ProjectWorkforceLog,
  TaxRecordListItem,
} from "$lib/types";

export type DisbursementBatchKey = "staff_salaries" | "site_wages" | "statutory_remittances";
export type DisbursementRowStatus = "ready" | "pending" | "hold" | "processing" | "settled" | "bounced";
export type DisbursementValidationState = "valid" | "warning" | "review";
export type DisbursementFundingType = "capitalized" | "expensed" | "statutory";

export interface DisbursementBanking {
  bankName: string;
  accountNumber: string;
  bankCode: string;
  paymentMethod: string;
  verified: boolean;
  sourceLabel: string;
}

export interface DisbursementQueueRow {
  id: string;
  batchKey: DisbursementBatchKey;
  beneficiaryName: string;
  beneficiarySecondary: string;
  roleLabel: string;
  projectName: string;
  projectCode: string;
  projectLocation: string;
  netAmount: number;
  status: DisbursementRowStatus;
  statusLabel: string;
  validationState: DisbursementValidationState;
  validationLabel: string;
  banking: DisbursementBanking;
  notes: string;
  runName: string;
  periodLabel: string;
  headcount: number;
  capitalizedAmount: number;
  expensedAmount: number;
  fundingType: DisbursementFundingType;
  overtimeHours: number;
  allocationPercent: number | null;
  employeeId: number | null;
  employeeCode: string | null;
  payslipId: number | null;
  requiresArchive: boolean;
  receiptArchiveLabel: string;
  sourceLabel: string;
  priorityTone: "mint" | "orange" | "blue" | "neutral" | "red";
  projectBudget: number;
  bonusPending: number;
}

export interface DisbursementBatch {
  key: DisbursementBatchKey;
  label: string;
  description: string;
  cadence: string;
  rows: DisbursementQueueRow[];
  total: number;
  capitalizedTotal: number;
  expensedTotal: number;
}

export interface BuildPayrollDisbursementInput {
  previewMode: boolean;
  employees: EmployeeDirectoryItem[];
  payrollRuns: PayrollRunListItem[];
  payslips: PayslipListItem[];
  taxRecords: TaxRecordListItem[];
  deductions: DeductionListItem[];
  bonuses: BonusListItem[];
  workforceLogs: ProjectWorkforceLog[];
  projects: ProjectListItem[];
}

export interface BuildPayrollDisbursementResult {
  reportingPeriodKey: string;
  reportingPeriodLabel: string;
  currentAverageNetPay: number;
  crewHeadRate: number;
  batches: DisbursementBatch[];
}

type EmployeeProjectInsight = {
  projectName: string;
  projectCode: string;
  projectLocation: string;
  projectBudget: number;
  overtimeHours: number;
  allocationPercent: number | null;
};

const ACTIVE_EMPLOYMENT_STATUSES = new Set(["active", "probation", "notice_period", "on_leave"]);
const HQ_HINTS = ["hq", "head office", "office", "operations", "admin", "finance"];
const MANAGEMENT_HINTS = ["manager", "lead", "director", "head"];
const CREW_NET_FACTOR = 0.38;
const PREVIEW_BANKS = ["Zenith Bank", "GTBank", "Access Bank", "UBA", "First Bank", "Fidelity Bank"];
const BANK_CODES: Record<string, string> = {
  "Zenith Bank": "057",
  GTBank: "058",
  "Access Bank": "044",
  UBA: "033",
  "First Bank": "011",
  "Fidelity Bank": "070",
};

function parseDate(value: string | null | undefined): Date | null {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function monthKey(value: string | null | undefined): string {
  return value ? value.slice(0, 7) : "";
}

function monthLabel(key: string): string {
  if (!key) return "Current Period";
  const [year, month] = key.split("-").map(Number);
  return new Intl.DateTimeFormat("en-NG", {
    month: "long",
    year: "numeric",
  }).format(new Date(year, (month || 1) - 1, 1));
}

function isHqLocation(location: string | null | undefined): boolean {
  const normalized = (location ?? "").trim().toLowerCase();
  return HQ_HINTS.some((hint) => normalized.includes(hint));
}

function isManagementRole(role: string | null | undefined): boolean {
  const normalized = (role ?? "").trim().toLowerCase();
  return MANAGEMENT_HINTS.some((hint) => normalized.includes(hint));
}

function titleize(value: string): string {
  return value
    .split("_")
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

function statusLabel(status: DisbursementRowStatus): string {
  switch (status) {
    case "ready":
      return "Ready";
    case "pending":
      return "Pending";
    case "hold":
      return "Hold";
    case "processing":
      return "Processing";
    case "settled":
      return "Settled";
    case "bounced":
      return "Bounced";
    default:
      return titleize(status);
  }
}

export function maskAccount(accountNumber: string): string {
  if (!accountNumber) return "Awaiting secure registry";
  if (accountNumber.length <= 4) return accountNumber;
  return `...${accountNumber.slice(-4)}`;
}

export function projectCodeFor(projectName: string): string {
  const normalized = projectName.trim().toLowerCase();
  if (!normalized) return "HQ-Ops";
  if (normalized.includes("victoria island")) return "VI-Towers";
  if (normalized.includes("lekki phase 1")) return "LEK-Ph1";
  if (normalized.includes("abuja hub")) return "ABJ-Hub";
  if (normalized.includes("statutory")) return "Statutory";
  if (normalized.includes("hq")) return "HQ-Ops";
  const tokens = projectName.replace(/[^A-Za-z0-9 ]/g, "").split(/\s+/).filter(Boolean);
  if (!tokens.length) return "HQ-Ops";
  return tokens
    .slice(0, 3)
    .map((token, index) => token.slice(0, index === 0 ? 3 : 2))
    .join("-")
    .toUpperCase();
}

function previewBanking(employee: EmployeeDirectoryItem): DisbursementBanking {
  const bankName = PREVIEW_BANKS[(employee.id - 1) % PREVIEW_BANKS.length];
  const accountNumber = `${String(4000000000 + employee.id * 711).slice(0, 10)}`.padEnd(10, "0");
  return {
    bankName,
    accountNumber,
    bankCode: BANK_CODES[bankName] ?? "",
    paymentMethod: employee.employment_type === "contract" ? "Third-party Payroll Provider" : "Transfer",
    verified: true,
    sourceLabel: "Preview bank registry",
  };
}

function liveBankingPlaceholder(employee: EmployeeDirectoryItem): DisbursementBanking {
  return {
    bankName: "",
    accountNumber: "",
    bankCode: "",
    paymentMethod: employee.employment_type === "contract" ? "Third-party Payroll Provider" : "Transfer",
    verified: false,
    sourceLabel: "Secure payroll registry pending",
  };
}

function latestPeriodKey(payrollRuns: PayrollRunListItem[], payslips: PayslipListItem[]): string {
  const sortedPayslips = [...payslips].sort((left, right) =>
    (parseDate(right.period_end)?.getTime() ?? 0) - (parseDate(left.period_end)?.getTime() ?? 0)
  );
  if (sortedPayslips[0]?.period_end) return monthKey(sortedPayslips[0].period_end);

  const sortedRuns = [...payrollRuns].sort((left, right) =>
    (parseDate(right.period_end ?? right.run_date)?.getTime() ?? 0) - (parseDate(left.period_end ?? left.run_date)?.getTime() ?? 0)
  );
  if (sortedRuns[0]?.period_end || sortedRuns[0]?.run_date) {
    return monthKey(sortedRuns[0].period_end ?? sortedRuns[0].run_date);
  }

  return new Date().toISOString().slice(0, 7);
}

function currentAverageNetPay(
  currentPeriodPayslips: PayslipListItem[],
  payrollRuns: PayrollRunListItem[],
  activeEmployeeCount: number
): number {
  if (currentPeriodPayslips.length > 0) {
    return currentPeriodPayslips.reduce((sum, item) => sum + toAmount(item.net_salary), 0) / currentPeriodPayslips.length;
  }

  const sortedRuns = [...payrollRuns].sort((left, right) =>
    (parseDate(right.period_end ?? right.run_date)?.getTime() ?? 0) - (parseDate(left.period_end ?? left.run_date)?.getTime() ?? 0)
  );
  const latestRun = sortedRuns.find((item) => item.status !== "cancelled");
  if (!latestRun) return 0;
  return toAmount(latestRun.total_net) / Math.max(activeEmployeeCount, 1);
}

function buildEmployeeProjectInsight(
  employeeId: number,
  workforceLogs: ProjectWorkforceLog[],
  employee: EmployeeDirectoryItem | undefined,
  projects: Map<number, ProjectListItem>
): EmployeeProjectInsight {
  const recentCutoff = new Date();
  recentCutoff.setDate(recentCutoff.getDate() - 45);

  const logs = workforceLogs.filter((item) => {
    if (item.employee !== employeeId) return false;
    const reportDate = parseDate(item.report_date);
    return reportDate ? reportDate >= recentCutoff : false;
  });

  if (!logs.length) {
    const fallbackProject = isHqLocation(employee?.office_location) ? "HQ Operations" : employee?.office_location || "HQ Operations";
    return {
      projectName: fallbackProject,
      projectCode: projectCodeFor(fallbackProject),
      projectLocation: employee?.office_location || "Head Office",
      projectBudget: 0,
      overtimeHours: 0,
      allocationPercent: employee && isManagementRole(employee.job_title) ? 100 : null,
    };
  }

  const touchesByProject = new Map<number, { name: string; touches: number; overtimeHours: number }>();
  for (const log of logs) {
    const key = log.project;
    const current = touchesByProject.get(key) ?? {
      name: log.project_name,
      touches: 0,
      overtimeHours: 0,
    };
    current.touches += 1;
    current.overtimeHours += toAmount(log.overtime_hours);
    touchesByProject.set(key, current);
  }

  let selectedProjectId = logs[0].project;
  let selectedProjectName = logs[0].project_name;
  let selectedTouches = 0;
  let totalOvertime = 0;

  for (const [projectId, payload] of touchesByProject.entries()) {
    totalOvertime += payload.overtimeHours;
    if (payload.touches > selectedTouches) {
      selectedProjectId = projectId;
      selectedProjectName = payload.name;
      selectedTouches = payload.touches;
    }
  }

  const project = projects.get(selectedProjectId);
  return {
    projectName: selectedProjectName,
    projectCode: projectCodeFor(selectedProjectName),
    projectLocation: project?.location || employee?.office_location || "Location pending",
    projectBudget: toAmount(project?.budget),
    overtimeHours: totalOvertime,
    allocationPercent: Math.round((selectedTouches / Math.max(logs.length, 1)) * 100),
  };
}

function summarizeBatch(key: DisbursementBatchKey, label: string, description: string, cadence: string, rows: DisbursementQueueRow[]): DisbursementBatch {
  return {
    key,
    label,
    description,
    cadence,
    rows,
    total: rows.reduce((sum, item) => sum + item.netAmount, 0),
    capitalizedTotal: rows.reduce((sum, item) => sum + item.capitalizedAmount, 0),
    expensedTotal: rows.reduce((sum, item) => sum + item.expensedAmount, 0),
  };
}

export function buildPayrollDisbursementBatches({
  previewMode,
  employees,
  payrollRuns,
  payslips,
  taxRecords,
  deductions,
  bonuses,
  workforceLogs,
  projects,
}: BuildPayrollDisbursementInput): BuildPayrollDisbursementResult {
  const reportingPeriodKey = latestPeriodKey(payrollRuns, payslips);
  const reportingPeriodLabel = monthLabel(reportingPeriodKey);
  const activeEmployees = employees.filter((employee) => ACTIVE_EMPLOYMENT_STATUSES.has(employee.employment_status));
  const currentPeriodPayslips = payslips.filter((item) => monthKey(item.period_end) === reportingPeriodKey);
  const currentPeriodRuns = payrollRuns.filter((item) => monthKey(item.period_end ?? item.run_date) === reportingPeriodKey);
  const currentPeriodBonuses = bonuses.filter((item) => monthKey(item.date) === reportingPeriodKey);
  const currentAverage = currentAverageNetPay(currentPeriodPayslips, payrollRuns, activeEmployees.length);
  const crewHeadRate = currentAverage * CREW_NET_FACTOR;

  const employeeMap = new Map(employees.map((item) => [item.id, item]));
  const projectMap = new Map(projects.map((item) => [item.id, item]));
  const pendingBonusByEmployee = new Map<number, number>();

  for (const item of currentPeriodBonuses) {
    if (item.status !== "pending") continue;
    pendingBonusByEmployee.set(item.employee, (pendingBonusByEmployee.get(item.employee) ?? 0) + toAmount(item.amount));
  }

  const staffRows = currentPeriodPayslips.flatMap<DisbursementQueueRow>((payslip) => {
      const employee = employeeMap.get(payslip.employee);
      if (!employee) return [];

      const projectInsight = buildEmployeeProjectInsight(employee.id, workforceLogs, employee, projectMap);
      const banking = previewMode ? previewBanking(employee) : liveBankingPlaceholder(employee);
      const pendingBonus = pendingBonusByEmployee.get(employee.id) ?? 0;
      const missingSecureRegistry = !banking.bankName || !banking.accountNumber;
      const overtimeAlert = projectInsight.overtimeHours >= 12;
      const validationState = missingSecureRegistry ? "review" : pendingBonus > 0 || overtimeAlert ? "warning" : "valid";
      const validationLabel = missingSecureRegistry
        ? "Secure account sync pending"
        : pendingBonus > 0
          ? "Bonus adjustment awaiting sign-off"
          : overtimeAlert
            ? "Overtime above labor cap"
            : "All accounts validated";
      const status: DisbursementRowStatus = missingSecureRegistry
        ? "hold"
        : payslip.status === "generated" || payslip.status === "draft"
          ? "pending"
          : payslip.status === "sent"
            ? "processing"
            : "ready";
      const amount = toAmount(payslip.net_salary);
      const capitalized = projectInsight.projectName === "HQ Operations" ? 0 : amount;
      const expensed = projectInsight.projectName === "HQ Operations" ? amount : 0;

      return [{
        id: `staff-${payslip.id}`,
        batchKey: "staff_salaries",
        beneficiaryName: payslip.employee_name,
        beneficiarySecondary: employee.employee_id,
        roleLabel: employee.position_title ?? employee.job_title ?? "Payroll profile",
        projectName: projectInsight.projectName,
        projectCode: projectInsight.projectCode,
        projectLocation: projectInsight.projectLocation,
        netAmount: amount,
        status,
        statusLabel: statusLabel(status),
        validationState,
        validationLabel,
        banking,
        notes: missingSecureRegistry
          ? "Bank account details are still redacted from the live HR registry and must be released before upload."
          : pendingBonus > 0
            ? `Pending bonus of ${pendingBonus.toLocaleString("en-NG")} is excluded until milestone sign-off is complete.`
            : overtimeAlert
              ? "Recent site overtime crossed the internal burn threshold and should be checked before disbursement."
              : "Ready for final finance verification and bank release.",
        runName: payslip.payroll_run_name ?? currentPeriodRuns[0]?.name ?? `${reportingPeriodLabel} payroll`,
        periodLabel: reportingPeriodLabel,
        headcount: 1,
        capitalizedAmount: capitalized,
        expensedAmount: expensed,
        fundingType: capitalized > 0 ? "capitalized" : "expensed",
        overtimeHours: projectInsight.overtimeHours,
        allocationPercent: projectInsight.allocationPercent,
        employeeId: employee.id,
        employeeCode: employee.employee_id,
        payslipId: payslip.id,
        requiresArchive: true,
        receiptArchiveLabel: "Attach settlement notice to payroll profile",
        sourceLabel: banking.sourceLabel,
        priorityTone: missingSecureRegistry ? "blue" : pendingBonus > 0 || overtimeAlert ? "orange" : "mint",
        projectBudget: projectInsight.projectBudget,
        bonusPending: pendingBonus,
      }];
    });

  const recentCutoff = new Date();
  recentCutoff.setDate(recentCutoff.getDate() - 45);

  const crewGroups = new Map<string, ProjectWorkforceLog[]>();
  for (const log of workforceLogs) {
    if (log.employee || log.total_headcount <= 0) continue;
    const reportDate = parseDate(log.report_date);
    if (!reportDate || reportDate < recentCutoff) continue;
    const key = `${log.project}-${log.trade}`;
    const group = crewGroups.get(key) ?? [];
    group.push(log);
    crewGroups.set(key, group);
  }

  const siteWageRows: DisbursementQueueRow[] = [...crewGroups.values()].map((logs) => {
    const sorted = [...logs].sort((left, right) =>
      (parseDate(right.report_date)?.getTime() ?? 0) - (parseDate(left.report_date)?.getTime() ?? 0)
    );
    const latest = sorted[0];
    const headcount = latest.total_headcount || 0;
    const project = projectMap.get(latest.project);
    const weeklyAmount = (crewHeadRate * headcount) / 4;
    const overtimeHours = sorted.reduce((sum, item) => sum + toAmount(item.overtime_hours), 0);
    const requiresManualReview = latest.payroll_status !== "synced" || overtimeHours >= 72;
    const status: DisbursementRowStatus = requiresManualReview ? "pending" : "ready";

    return {
      id: `site-${latest.project}-${latest.trade.replace(/\s+/g, "-").toLowerCase()}`,
      batchKey: "site_wages",
      beneficiaryName: `${latest.trade || "Site Crew"} (${headcount})`,
      beneficiarySecondary: latest.shift.replaceAll("_", " "),
      roleLabel: "Weekly Site Wages",
      projectName: latest.project_name,
      projectCode: projectCodeFor(latest.project_name),
      projectLocation: project?.location || "Site location",
      netAmount: weeklyAmount,
      status,
      statusLabel: statusLabel(status),
      validationState: requiresManualReview ? "review" : "valid",
      validationLabel: requiresManualReview ? "Split sheet still pending" : "Crew roster validated",
      banking: {
        bankName: "Multi-Batch",
        accountNumber: "",
        bankCode: "",
        paymentMethod: "Bulk Transfer Schedule",
        verified: !requiresManualReview,
        sourceLabel: "Site attendance allocation",
      },
      notes: requiresManualReview
        ? "Attendance has landed, but the crew split sheet and supervisor approval must be completed before upload."
        : "Crew batch is aligned to the latest attendance sweep and ready for treasury release.",
      runName: `Week-linked site wage pack`,
      periodLabel: reportingPeriodLabel,
      headcount,
      capitalizedAmount: weeklyAmount,
      expensedAmount: 0,
      fundingType: "capitalized",
      overtimeHours,
      allocationPercent: 100,
      employeeId: null,
      employeeCode: latest.worker_id,
      payslipId: null,
      requiresArchive: false,
      receiptArchiveLabel: "Archive bank success note to site wage register",
      sourceLabel: "Attendance and workforce logs",
      priorityTone: requiresManualReview ? "blue" : "mint",
      projectBudget: toAmount(project?.budget),
      bonusPending: 0,
    };
  });

  const totalTaxDeductions = deductions
    .filter((item) => item.deduction_type === "tax" && item.is_active)
    .reduce((sum, item) => sum + toAmount(item.amount), 0);
  const totalPensionDeductions = deductions
    .filter((item) => item.deduction_type === "pension" && item.is_active)
    .reduce((sum, item) => sum + toAmount(item.amount), 0);
  const totalNhfDeductions = deductions
    .filter((item) => item.is_active && (item.name.toLowerCase().includes("nhf") || item.name.toLowerCase().includes("housing fund")))
    .reduce((sum, item) => sum + toAmount(item.amount), 0);
  const totalTaxRecordBalance = taxRecords.reduce((sum, item) => sum + toAmount(item.balance), 0);

  const payeLiability = Math.max(totalTaxDeductions, totalTaxRecordBalance);
  const pensionEmployerShare = totalPensionDeductions * 1.25;
  const pensionLiability = totalPensionDeductions + pensionEmployerShare;

  const statutoryRows = ([
    {
      id: "statutory-paye",
      batchKey: "statutory_remittances",
      beneficiaryName: "FIRS / State PAYE",
      beneficiarySecondary: "Government remittance",
      roleLabel: "PAYE liability",
      projectName: "Statutory",
      projectCode: "Statutory",
      projectLocation: "Regulatory clearing",
      netAmount: payeLiability,
      status: payeLiability > 0 ? "ready" : "hold",
      statusLabel: statusLabel(payeLiability > 0 ? "ready" : "hold"),
      validationState: payeLiability > 0 ? "valid" : "review",
      validationLabel: payeLiability > 0 ? "Portal schedule complete" : "No tax liability loaded",
      banking: {
        bankName: "FIRS Portal",
        accountNumber: "",
        bankCode: "",
        paymentMethod: "e-Remittance",
        verified: payeLiability > 0,
        sourceLabel: "Tax and deduction ledger",
      },
      notes: "PAYE combines tax record balances and payroll tax deductions for the current cycle.",
      runName: `${reportingPeriodLabel} statutory remittance`,
      periodLabel: reportingPeriodLabel,
      headcount: activeEmployees.length,
      capitalizedAmount: 0,
      expensedAmount: payeLiability,
      fundingType: "statutory",
      overtimeHours: 0,
      allocationPercent: null,
      employeeId: null,
      employeeCode: null,
      payslipId: null,
      requiresArchive: false,
      receiptArchiveLabel: "Archive proof of tax remittance",
      sourceLabel: "Tax and deduction ledger",
      priorityTone: payeLiability > 0 ? "mint" : "orange",
      projectBudget: 0,
      bonusPending: 0,
    },
    {
      id: "statutory-pension",
      batchKey: "statutory_remittances",
      beneficiaryName: "PenCom / PFA Remittance",
      beneficiarySecondary: "Employee + employer split",
      roleLabel: "Pension liability",
      projectName: "Statutory",
      projectCode: "Statutory",
      projectLocation: "Retirement compliance",
      netAmount: pensionLiability,
      status: pensionLiability > 0 ? "ready" : "hold",
      statusLabel: statusLabel(pensionLiability > 0 ? "ready" : "hold"),
      validationState: pensionLiability > 0 ? "valid" : "review",
      validationLabel: pensionLiability > 0 ? "8% / 10% split mapped" : "No pension liability loaded",
      banking: {
        bankName: "PFA Gateway",
        accountNumber: "",
        bankCode: "",
        paymentMethod: "Portal Upload",
        verified: pensionLiability > 0,
        sourceLabel: "Pension contribution tracker",
      },
      notes: "Includes employee pension deductions and modeled 10% employer contribution share.",
      runName: `${reportingPeriodLabel} statutory remittance`,
      periodLabel: reportingPeriodLabel,
      headcount: activeEmployees.length,
      capitalizedAmount: 0,
      expensedAmount: pensionLiability,
      fundingType: "statutory",
      overtimeHours: 0,
      allocationPercent: null,
      employeeId: null,
      employeeCode: null,
      payslipId: null,
      requiresArchive: false,
      receiptArchiveLabel: "Archive pension submission acknowledgement",
      sourceLabel: "Pension contribution tracker",
      priorityTone: pensionLiability > 0 ? "mint" : "orange",
      projectBudget: 0,
      bonusPending: 0,
    },
    {
      id: "statutory-nhf",
      batchKey: "statutory_remittances",
      beneficiaryName: "National Housing Fund",
      beneficiarySecondary: "Housing contribution",
      roleLabel: "NHF contribution",
      projectName: "Statutory",
      projectCode: "Statutory",
      projectLocation: "Housing compliance",
      netAmount: totalNhfDeductions,
      status: totalNhfDeductions > 0 ? "ready" : "hold",
      statusLabel: statusLabel(totalNhfDeductions > 0 ? "ready" : "hold"),
      validationState: totalNhfDeductions > 0 ? "valid" : "review",
      validationLabel: totalNhfDeductions > 0 ? "Contribution file loaded" : "No NHF contribution in this cycle",
      banking: {
        bankName: "NHF Portal",
        accountNumber: "",
        bankCode: "",
        paymentMethod: "Portal Upload",
        verified: totalNhfDeductions > 0,
        sourceLabel: "NHF deduction tracker",
      },
      notes: "This row appears only when NHF deductions are active in the compensation stack.",
      runName: `${reportingPeriodLabel} statutory remittance`,
      periodLabel: reportingPeriodLabel,
      headcount: activeEmployees.length,
      capitalizedAmount: 0,
      expensedAmount: totalNhfDeductions,
      fundingType: "statutory",
      overtimeHours: 0,
      allocationPercent: null,
      employeeId: null,
      employeeCode: null,
      payslipId: null,
      requiresArchive: false,
      receiptArchiveLabel: "Archive NHF submission acknowledgement",
      sourceLabel: "NHF deduction tracker",
      priorityTone: totalNhfDeductions > 0 ? "mint" : "orange",
      projectBudget: 0,
      bonusPending: 0,
    },
  ] as DisbursementQueueRow[]).filter((item) => item.netAmount > 0);

  return {
    reportingPeriodKey,
    reportingPeriodLabel,
    currentAverageNetPay: currentAverage,
    crewHeadRate,
    batches: [
      summarizeBatch(
        "staff_salaries",
        "Staff Salaries",
        "Named payroll profiles moving from approved payroll into bank execution.",
        "Monthly",
        staffRows,
      ),
      summarizeBatch(
        "site_wages",
        "Site Wages",
        "Attendance-linked crew payouts staged for bulk upload and supervisor sign-off.",
        "Weekly",
        siteWageRows,
      ),
      summarizeBatch(
        "statutory_remittances",
        "Statutory Remittances",
        "PAYE, pension, and NHF obligations prepared for regulatory submission.",
        "Monthly",
        statutoryRows,
      ),
    ],
  };
}

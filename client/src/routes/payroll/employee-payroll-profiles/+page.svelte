<script lang="ts">
  import { goto } from "$app/navigation";
  import { onMount } from "svelte";
  import { api } from "$lib/api";
  import AllocationSlider from "$lib/components/payroll/AllocationSlider.svelte";
  import { fetchAllPages, toAmount } from "$lib/contracts";
  import { PREVIEW_PAYROLL_DASHBOARD_DATA, PREVIEW_PAYSLIP_DETAILS } from "$lib/payrollDashboardPreview";
  import {
    calculatePayrollProfileTotals,
    type PayrollProfileCalculationResult,
  } from "$lib/payroll/deductionLogic";
  import { currency } from "$lib/stores/currency.svelte";
  import { onboarding } from "$lib/stores/onboarding.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    AllowanceListItem,
    BonusListItem,
    CompensationRecord,
    DeductionListItem,
    EmployeeDirectoryItem,
    EmployeeRecord,
    HRDocument,
    PayslipDetail,
    PayslipListItem,
    ProjectListItem,
    ProjectWorkforceLog,
    TaxRecordListItem,
  } from "$lib/types";

  type LoadMode = "live" | "preview";
  type ProfileStatusTone = "good" | "warn" | "muted" | "review";
  type SectionKey = "overview" | "earnings" | "compliance" | "allocation" | "banking" | "documents" | "history";

  type AllocationDraftItem = {
    projectId: number | null;
    name: string;
    location: string;
    ratio: number;
    logs: number;
  };

  type PayrollProfile = {
    employee: EmployeeDirectoryItem;
    compensation: CompensationRecord | null;
    allowances: AllowanceListItem[];
    deductions: DeductionListItem[];
    bonuses: BonusListItem[];
    payslips: PayslipListItem[];
    latestPayslip: PayslipListItem | null;
    taxRecords: TaxRecordListItem[];
    documents: HRDocument[];
    workforce: ProjectWorkforceLog[];
    allocationBase: AllocationDraftItem[];
    primaryProjectName: string;
    primaryProjectLocation: string;
    primaryProjectRatio: number;
    statusTone: ProfileStatusTone;
    statusLabel: string;
    employmentStatusLabel: string;
    attentionNote: string;
    currentNet: number;
    currentGross: number;
    statutoryMonthly: number;
    statutoryExposure: number;
    pendingBonusTotal: number;
    overtimeHours: number;
    overtimeRate: number;
    billableRate: number;
    documentCount: number;
    modeled: PayrollProfileCalculationResult;
  };

  type EarningsRow = {
    label: string;
    amount: number | null;
    frequency: string;
    detail: string;
    tone: "neutral" | "good" | "warn";
  };

  type VaultItem = {
    id: string;
    title: string;
    kind: string;
    subtitle: string;
    date: string | null;
    href: string | null;
    tone: "neutral" | "good" | "warn";
    actionLabel: string;
  };

  type HistoryItem = {
    id: string;
    label: string;
    description: string;
    date: string | null;
    tone: "neutral" | "good" | "warn";
  };

  type BankingMetadata = {
    bankName: string;
    accountNumber: string;
    accountName: string;
    paymentMethod: string;
    tin: string;
    verified: boolean;
    sourceLabel: string;
  };

  const MAX_PAGES = 10;
  const PROFILES_PER_PAGE = 10;
  const ACTIVE_EMPLOYMENT_STATUSES = new Set(["active", "probation", "notice_period", "on_leave"]);
  const HQ_HINTS = ["hq", "head office", "operations", "admin", "finance"];
  const BANKS = ["GTBank", "Zenith Bank", "Access Bank", "UBA", "First Bank"];
  const SECTION_ITEMS: { key: SectionKey; label: string; caption: string }[] = [
    { key: "overview", label: "Vital Signs", caption: "Identity and take-home view" },
    { key: "earnings", label: "Earnings", caption: "Base, allowances, and bonuses" },
    { key: "compliance", label: "Compliance", caption: "Tax, pension, NHF, and loans" },
    { key: "allocation", label: "Allocation", caption: "Project splits and labor costing" },
    { key: "banking", label: "Banking", caption: "Disbursement and secure metadata" },
    { key: "documents", label: "Documents", caption: "Contracts, payslips, and TCC" },
    { key: "history", label: "History", caption: "Compensation and payroll trail" },
  ];

  let loading = $state(true);
  let refreshing = $state(false);
  let dataMode = $state<LoadMode>("live");
  let lastSyncedAt = $state<Date | null>(null);

  let employees = $state<EmployeeDirectoryItem[]>([]);
  let compensationRecords = $state<CompensationRecord[]>([]);
  let allowances = $state<AllowanceListItem[]>([]);
  let deductions = $state<DeductionListItem[]>([]);
  let bonuses = $state<BonusListItem[]>([]);
  let payslips = $state<PayslipListItem[]>([]);
  let taxRecords = $state<TaxRecordListItem[]>([]);
  let workforceLogs = $state<ProjectWorkforceLog[]>([]);
  let projects = $state<ProjectListItem[]>([]);
  let documents = $state<HRDocument[]>([]);

  let searchQuery = $state("");
  let statusFilter = $state("all");
  let projectFilter = $state("all");
  let currentPage = $state(1);

  let drawerOpen = $state(false);
  let drawerLoading = $state(false);
  let selectedEmployeeId = $state<number | null>(null);
  let selectedEmployeeDetail = $state<EmployeeRecord | null>(null);
  let selectedPayslipDetail = $state<PayslipDetail | null>(null);
  let allocationDraft = $state<AllocationDraftItem[]>([]);
  let allocationSeededFor = $state<number | null>(null);
  let includeNhf = $state(false);
  let includePendingBonus = $state(false);
  let sensitiveVisible = $state(false);
  let drawerBodyEl = $state<HTMLElement | null>(null);

  function isLocalPreviewAllowed(): boolean {
    if (typeof window === "undefined") return false;
    return ["localhost", "127.0.0.1"].includes(window.location.hostname);
  }

  function getSettledValue<T>(result: PromiseSettledResult<T>, fallback: T): T {
    return result.status === "fulfilled" ? result.value : fallback;
  }

  function parseDate(value: string | null | undefined): Date | null {
    if (!value) return null;
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }

  function formatCurrency(value: number): string {
    return new Intl.NumberFormat("en-NG", {
      style: "currency",
      currency: currency.config.code || "NGN",
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(Number.isFinite(value) ? value : 0);
  }

  function formatDate(value: string | null | undefined): string {
    const parsed = parseDate(value);
    if (!parsed) return "Not available";
    return new Intl.DateTimeFormat("en-NG", {
      day: "numeric",
      month: "short",
      year: "numeric",
    }).format(parsed);
  }

  function shortDate(value: string | null | undefined): string {
    const parsed = parseDate(value);
    if (!parsed) return "N/A";
    return new Intl.DateTimeFormat("en-NG", {
      day: "numeric",
      month: "short",
    }).format(parsed);
  }

  function relativeSyncLabel(date: Date | null): string {
    if (!date) return "Never";
    const delta = Date.now() - date.getTime();
    if (delta < 60_000) return "Just now";
    if (delta < 3_600_000) return `${Math.round(delta / 60_000)} min ago`;
    return `${Math.round(delta / 3_600_000)} hr ago`;
  }

  function employmentStatusLabel(status: string | null | undefined): string {
    switch (status) {
      case "active":
        return "Active";
      case "on_leave":
        return "On Leave";
      case "probation":
        return "Probation";
      case "notice_period":
        return "Notice Period";
      case "terminated":
        return "Terminated";
      case "resigned":
        return "Resigned";
      default:
        return "Inactive";
    }
  }

  function employmentStatusClasses(status: string | null | undefined): string {
    if (status === "active") return "bg-emerald-100 text-emerald-700";
    if (status === "probation") return "bg-sky-100 text-sky-700";
    if (status === "on_leave") return "bg-neutral-200 text-neutral-600";
    return "bg-neutral-200 text-neutral-500";
  }

  function sectionButtonClasses(key: SectionKey, activeProfile: boolean): string {
    if (!activeProfile) return "border-white/40 bg-white/60 text-neutral-500";
    return "border-emerald-200 bg-emerald-50/80 text-emerald-700";
  }

  function isHqLocation(location: string | null | undefined): boolean {
    const normalized = (location ?? "").trim().toLowerCase();
    return HQ_HINTS.some((hint) => normalized.includes(hint));
  }

  function hasNhfDeduction(items: DeductionListItem[]): boolean {
    return items.some((item) => item.name.toLowerCase().includes("nhf") || item.name.toLowerCase().includes("housing fund"));
  }

  function monthLabel(key: string): string {
    if (!key) return "Current";
    const [year, month] = key.split("-").map(Number);
    return new Intl.DateTimeFormat("en-NG", {
      month: "long",
      year: "numeric",
    }).format(new Date(year, (month || 1) - 1, 1));
  }

  function normalizePercentages(values: number[]): number[] {
    if (!values.length) return [];
    const positive = values.map((value) => Math.max(0, value));
    const total = positive.reduce((sum, value) => sum + value, 0);
    if (total <= 0) {
      return positive.map((_, index) => (index === 0 ? 100 : 0));
    }
    const exact = positive.map((value) => (value / total) * 100);
    const rounded = exact.map((value) => Math.floor(value));
    let remainder = 100 - rounded.reduce((sum, value) => sum + value, 0);
    const ranked = exact
      .map((value, index) => ({ index, remainder: value - rounded[index] }))
      .sort((left, right) => right.remainder - left.remainder);
    for (let cursor = 0; cursor < remainder; cursor += 1) {
      rounded[ranked[cursor % ranked.length].index] += 1;
    }
    return rounded;
  }

  function deriveOvertimeRate(employee: EmployeeDirectoryItem): number {
    const roleText = `${employee.job_title} ${employee.position_title ?? ""}`.toLowerCase();
    if (roleText.includes("manager") || roleText.includes("director") || roleText.includes("lead")) return 2.0;
    if (roleText.includes("engineer") || roleText.includes("coordinator") || roleText.includes("site") || roleText.includes("survey")) return 1.5;
    if (isHqLocation(employee.office_location)) return 1.25;
    return 1.35;
  }

  function deriveBillableRate(monthlyValue: number, employee: EmployeeDirectoryItem): number {
    const hourlyBase = monthlyValue > 0 ? monthlyValue / 173 : 0;
    const markup = isHqLocation(employee.office_location) ? 1.15 : 1.35;
    return hourlyBase * markup;
  }

  function buildPreviewCompensation(): CompensationRecord[] {
    return PREVIEW_PAYROLL_DASHBOARD_DATA.employees.map((employee) => {
      const payslip = PREVIEW_PAYROLL_DASHBOARD_DATA.payslips.find((item) => item.employee === employee.id) ?? null;
      const detail = payslip ? PREVIEW_PAYSLIP_DETAILS[payslip.id] ?? null : null;
      const approvedBonus = PREVIEW_PAYROLL_DASHBOARD_DATA.bonuses
        .filter((item) => item.employee === employee.id && (item.status === "approved" || item.status === "paid"))
        .reduce((sum, item) => sum + toAmount(item.amount), 0);
      const base = toAmount(detail?.basic_salary) || Math.round((toAmount(payslip?.gross_salary) || 0) * 0.68);
      const allowancePool = toAmount(detail?.total_allowances) || Math.round(base * 0.18);
      const totalPackage = base + allowancePool + approvedBonus;
      return {
        id: 8000 + employee.id,
        user: employee.user_id,
        user_name: employee.full_name,
        effective_date: employee.hire_date ?? "2026-01-01",
        end_date: null,
        base_salary: base.toFixed(2),
        currency: "NGN",
        pay_frequency: "monthly",
        allowances: allowancePool.toFixed(2),
        bonus: approvedBonus.toFixed(2),
        total_package: totalPackage.toFixed(2),
        status: "active",
        approved_by: null,
        approved_by_name: null,
        approved_at: PREVIEW_PAYROLL_DASHBOARD_DATA.payrollRuns[0]?.run_date ?? null,
        notes: "Preview compensation package generated from payroll dashboard seed data.",
        created_at: PREVIEW_PAYROLL_DASHBOARD_DATA.payrollRuns[0]?.created_at ?? "2026-03-25T09:00:00Z",
        updated_at: PREVIEW_PAYROLL_DASHBOARD_DATA.payrollRuns[0]?.updated_at ?? "2026-03-25T09:00:00Z",
      };
    });
  }

  function buildPreviewAllowances(): AllowanceListItem[] {
    const rows: AllowanceListItem[] = [];
    for (const employee of PREVIEW_PAYROLL_DASHBOARD_DATA.employees) {
      const payslip = PREVIEW_PAYROLL_DASHBOARD_DATA.payslips.find((item) => item.employee === employee.id) ?? null;
      const detail = payslip ? PREVIEW_PAYSLIP_DETAILS[payslip.id] ?? null : null;
      const allowancePool = toAmount(detail?.total_allowances) || toAmount(buildPreviewCompensation().find((item) => item.user === employee.user_id)?.allowances);
      if (allowancePool <= 0) continue;
      const split = isHqLocation(employee.office_location)
        ? [
            ["housing", "Housing Allowance", 0.5, false],
            ["transport", "Fleet / Transport", 0.2, false],
            ["phone", "Phone and Data", 0.12, true],
            ["medical", "Medical Support", 0.18, false],
          ]
        : [
            ["housing", "Housing Allowance", 0.45, false],
            ["transport", "Transport / Fleet", 0.25, false],
            ["meal", "Meal Support", 0.1, true],
            ["medical", "Medical Support", 0.2, false],
          ];
      split.forEach(([type, label, ratio, taxable], index) => {
        rows.push({
          id: employee.id * 100 + index + 1,
          employee: employee.id,
          employee_name: employee.full_name,
          allowance_type: type as AllowanceListItem["allowance_type"],
          name: label as string,
          amount: (allowancePool * Number(ratio)).toFixed(2),
          currency: "NGN",
          frequency: "monthly",
          is_taxable: Boolean(taxable),
          is_active: true,
          created_at: employee.created_at,
          updated_at: employee.updated_at,
        });
      });
    }
    return rows;
  }

  function buildPreviewDocuments(): HRDocument[] {
    const items: HRDocument[] = [];
    for (const employee of PREVIEW_PAYROLL_DASHBOARD_DATA.employees) {
      items.push({
        id: 9000 + employee.id,
        user: employee.user_id,
        user_name: employee.full_name,
        title: `${employee.full_name} Employment Contract`,
        category: "contract",
        file: "",
        file_size: 0,
        description: "Signed employment contract kept in the payroll vault.",
        uploaded_by: null,
        uploaded_by_name: null,
        created_at: employee.hire_date ?? employee.created_at,
        updated_at: employee.updated_at,
      });
      items.push({
        id: 9500 + employee.id,
        user: employee.user_id,
        user_name: employee.full_name,
        title: `${employee.full_name} Salary Review Letter`,
        category: "compensation",
        file: "",
        file_size: 0,
        description: "Compensation review memo generated for payroll preview mode.",
        uploaded_by: null,
        uploaded_by_name: null,
        created_at: employee.updated_at,
        updated_at: employee.updated_at,
      });
    }
    return items;
  }

  function buildPreviewBanking(employee: EmployeeDirectoryItem, projectName: string): BankingMetadata {
    const bankName = BANKS[(employee.id - 1) % BANKS.length];
    const accountNumber = `${String(4000000000 + employee.id * 711).slice(0, 10)}`.padEnd(10, "0");
    const paymentMethod = employee.employment_type === "contract" ? "Third-party Payroll Provider" : "Transfer";
    const tin = `TIN-${String(employee.user_id).padStart(6, "0")}`;
    return {
      bankName,
      accountNumber,
      accountName: employee.full_name,
      paymentMethod,
      tin,
      verified: projectName !== "HQ Operations",
      sourceLabel: "Preview registry",
    };
  }

  function maskAccount(accountNumber: string): string {
    if (!accountNumber) return "Not available";
    if (accountNumber.length <= 4) return accountNumber;
    return `${accountNumber.slice(0, 2)}${"*".repeat(Math.max(0, accountNumber.length - 4))}${accountNumber.slice(-2)}`;
  }

  function maskTin(value: string): string {
    if (!value) return "Not available";
    if (value.length <= 4) return value;
    return `${value.slice(0, 4)}${"*".repeat(Math.max(0, value.length - 6))}${value.slice(-2)}`;
  }

  function buildAllocationBase(
    employee: EmployeeDirectoryItem,
    employeeLogs: ProjectWorkforceLog[],
    portfolio: ProjectListItem[],
    currentNet: number
  ): AllocationDraftItem[] {
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - 60);
    const freshLogs = employeeLogs.filter((log) => {
      const reportDate = parseDate(log.report_date);
      return reportDate && reportDate >= cutoff;
    });
    if (!freshLogs.length) {
      return [
        {
          projectId: null,
          name: isHqLocation(employee.office_location) ? "HQ Operations" : employee.office_location || "HQ Operations",
          location: employee.office_location || "Head Office",
          ratio: 100,
          logs: 0,
        },
      ];
    }
    const grouped = new Map<string, { projectId: number | null; name: string; location: string; logs: number }>();
    for (const log of freshLogs) {
      const project = portfolio.find((item) => item.id === log.project) ?? null;
      const key = `${log.project}:${log.project_name}`;
      const current = grouped.get(key) ?? {
        projectId: project?.id ?? null,
        name: log.project_name,
        location: project?.location ?? employee.office_location,
        logs: 0,
      };
      current.logs += 1;
      grouped.set(key, current);
    }
    const groups = [...grouped.values()].sort((left, right) => right.logs - left.logs);
    const ratios = normalizePercentages(groups.map((item) => item.logs));
    return groups.map((item, index) => ({
      ...item,
      ratio: ratios[index],
      logs: item.logs || Math.max(1, Math.round(currentNet / 100000)),
    }));
  }

  function buildEarningsRows(profile: PayrollProfile | null, payslipDetail: PayslipDetail | null): EarningsRow[] {
    if (!profile) return [];
    const rows: EarningsRow[] = [];
    const baseSalary = toAmount(payslipDetail?.basic_salary) || toAmount(profile.compensation?.base_salary) || profile.modeled.baseSalary;
    rows.push({
      label: "Base Salary",
      amount: baseSalary,
      frequency: "Monthly",
      detail: "Fixed",
      tone: "neutral",
    });

    if (profile.allowances.length > 0) {
      for (const item of profile.allowances) {
        rows.push({
          label: item.name,
          amount: toAmount(item.amount),
          frequency: item.frequency === "one_time" ? "One-Time" : item.frequency.charAt(0).toUpperCase() + item.frequency.slice(1),
          detail: item.is_taxable ? "Taxable" : "Fixed",
          tone: "good",
        });
      }
    } else {
      const allowancePool = toAmount(payslipDetail?.total_allowances) || toAmount(profile.compensation?.allowances);
      if (allowancePool > 0) {
        rows.push({
          label: "Structured Allowances",
          amount: allowancePool,
          frequency: "Monthly",
          detail: "Auto-stacked",
          tone: "good",
        });
      }
    }

    for (const item of profile.bonuses) {
      rows.push({
        label: item.bonus_type === "project" ? "Project Bonus" : `${item.bonus_type.charAt(0).toUpperCase()}${item.bonus_type.slice(1)} Bonus`,
        amount: toAmount(item.amount),
        frequency: "Per Milestone",
        detail: item.status === "pending" ? "Pending review" : item.status === "paid" ? "Receipt logged" : "Approved",
        tone: item.status === "pending" ? "warn" : "neutral",
      });
    }

    return rows;
  }

  function buildVaultItems(profile: PayrollProfile | null): VaultItem[] {
    if (!profile) return [];
    const items: VaultItem[] = [];

    for (const doc of profile.documents) {
      items.push({
        id: `doc-${doc.id}`,
        title: doc.title,
        kind: doc.category || "document",
        subtitle: doc.description || "Uploaded payroll support file.",
        date: doc.updated_at,
        href: doc.file || null,
        tone: doc.category === "contract" ? "good" : "neutral",
        actionLabel: doc.file ? "Open file" : "Managed in HR Documents",
      });
    }

    for (const payslip of profile.payslips.slice(0, 4)) {
      items.push({
        id: `payslip-${payslip.id}`,
        title: `${monthLabel(payslip.period_end.slice(0, 7))} Payslip`,
        kind: "payslip",
        subtitle: payslip.payroll_run_name ?? "Payroll archive entry",
        date: payslip.period_end,
        href: null,
        tone: payslip.status === "acknowledged" ? "good" : "neutral",
        actionLabel: "Open payslip module",
      });
    }

    for (const record of profile.taxRecords.filter((item) => item.filing_status === "filed" || item.filing_status === "paid")) {
      items.push({
        id: `tax-${record.id}`,
        title: `Tax Clearance ${record.fiscal_year}`,
        kind: "tax clearance",
        subtitle: `${record.tax_type.replace("_", " ")} record ${record.filing_status}`,
        date: record.updated_at,
        href: null,
        tone: record.filing_status === "paid" ? "good" : "neutral",
        actionLabel: "Open tax records",
      });
    }

    if (items.length === 0 && dataMode === "preview") {
      items.push({
        id: `preview-contract-${profile.employee.id}`,
        title: `${profile.employee.full_name} Employment Contract`,
        kind: "contract",
        subtitle: "Preview contract packet generated from payroll seed data.",
        date: profile.employee.hire_date,
        href: null,
        tone: "good",
        actionLabel: "Open HR Documents",
      });
    }

    return items
      .sort((left, right) => {
        const rightTime = parseDate(right.date)?.getTime() ?? 0;
        const leftTime = parseDate(left.date)?.getTime() ?? 0;
        return rightTime - leftTime;
      })
      .slice(0, 8);
  }

  function buildHistoryItems(profile: PayrollProfile | null): HistoryItem[] {
    if (!profile) return [];
    const items: HistoryItem[] = [];
    if (profile.compensation) {
      items.push({
        id: `comp-${profile.compensation.id}`,
        label: "Compensation set",
        description: `${formatCurrency(toAmount(profile.compensation.total_package))} total package activated.`,
        date: profile.compensation.effective_date,
        tone: "neutral",
      });
    }

    for (const payslip of profile.payslips.slice(0, 4)) {
      items.push({
        id: `hp-${payslip.id}`,
        label: "Payslip processed",
        description: `${formatCurrency(toAmount(payslip.net_salary))} net pay in ${monthLabel(payslip.period_end.slice(0, 7))}.`,
        date: payslip.period_end,
        tone: payslip.status === "acknowledged" ? "good" : "neutral",
      });
    }

    for (const bonus of profile.bonuses.slice(0, 3)) {
      items.push({
        id: `hb-${bonus.id}`,
        label: "Bonus movement",
        description: `${formatCurrency(toAmount(bonus.amount))} ${bonus.bonus_type} bonus is ${bonus.status}.`,
        date: bonus.date,
        tone: bonus.status === "pending" ? "warn" : "good",
      });
    }

    for (const record of profile.taxRecords.slice(0, 2)) {
      items.push({
        id: `ht-${record.id}`,
        label: "Tax filing updated",
        description: `${record.tax_type.replace("_", " ")} is ${record.filing_status} with ${formatCurrency(toAmount(record.balance))} balance.`,
        date: record.updated_at,
        tone: toAmount(record.balance) > 0 ? "warn" : "good",
      });
    }

    for (const doc of profile.documents.slice(0, 2)) {
      items.push({
        id: `hd-${doc.id}`,
        label: "Vault file refreshed",
        description: doc.title,
        date: doc.updated_at,
        tone: "neutral",
      });
    }

    return items
      .sort((left, right) => {
        const rightTime = parseDate(right.date)?.getTime() ?? 0;
        const leftTime = parseDate(left.date)?.getTime() ?? 0;
        return rightTime - leftTime;
      })
      .slice(0, 10);
  }

  async function loadProfiles({ silent = false } = {}) {
    if (silent) refreshing = true;
    else loading = true;
    try {
      const results = await Promise.allSettled([
        fetchAllPages<EmployeeDirectoryItem>("/hr/employee-records/", { page_size: "200" }, MAX_PAGES),
        fetchAllPages<CompensationRecord>("/hr/compensation-records/", { page_size: "200" }, MAX_PAGES),
        fetchAllPages<AllowanceListItem>("/hr/allowances/", { page_size: "200" }, MAX_PAGES),
        fetchAllPages<DeductionListItem>("/hr/deductions/", { page_size: "200" }, MAX_PAGES),
        fetchAllPages<BonusListItem>("/hr/bonuses/", { page_size: "200" }, MAX_PAGES),
        fetchAllPages<PayslipListItem>("/hr/payslips/", { page_size: "200" }, MAX_PAGES),
        fetchAllPages<TaxRecordListItem>("/hr/tax-records/", { page_size: "200" }, MAX_PAGES),
        fetchAllPages<ProjectWorkforceLog>("/projects/field-operations/workforce/", { page_size: "200" }, MAX_PAGES),
        fetchAllPages<ProjectListItem>("/projects/", { page_size: "200" }, MAX_PAGES),
        fetchAllPages<HRDocument>("/hr/hr-documents/", { page_size: "200" }, MAX_PAGES),
      ]);

      const liveEmployees = getSettledValue(results[0], []);
      const liveCompensation = getSettledValue(results[1], []);
      const liveAllowances = getSettledValue(results[2], []);
      const liveDeductions = getSettledValue(results[3], []);
      const liveBonuses = getSettledValue(results[4], []);
      const livePayslips = getSettledValue(results[5], []);
      const liveTaxRecords = getSettledValue(results[6], []);
      const liveWorkforce = getSettledValue(results[7], []);
      const liveProjects = getSettledValue(results[8], []);
      const liveDocuments = getSettledValue(results[9], []);

      const usePreview = isLocalPreviewAllowed() && liveEmployees.length === 0 && livePayslips.length === 0;
      dataMode = usePreview ? "preview" : "live";

      if (usePreview) {
        employees = PREVIEW_PAYROLL_DASHBOARD_DATA.employees;
        compensationRecords = buildPreviewCompensation();
        allowances = buildPreviewAllowances();
        deductions = PREVIEW_PAYROLL_DASHBOARD_DATA.deductions;
        bonuses = PREVIEW_PAYROLL_DASHBOARD_DATA.bonuses;
        payslips = PREVIEW_PAYROLL_DASHBOARD_DATA.payslips;
        taxRecords = PREVIEW_PAYROLL_DASHBOARD_DATA.taxRecords;
        workforceLogs = PREVIEW_PAYROLL_DASHBOARD_DATA.workforceLogs;
        projects = PREVIEW_PAYROLL_DASHBOARD_DATA.projects;
        documents = buildPreviewDocuments();
      } else {
        employees = liveEmployees;
        compensationRecords = liveCompensation;
        allowances = liveAllowances;
        deductions = liveDeductions;
        bonuses = liveBonuses;
        payslips = livePayslips;
        taxRecords = liveTaxRecords;
        workforceLogs = liveWorkforce;
        projects = liveProjects;
        documents = liveDocuments;
      }

      lastSyncedAt = new Date();
    } catch {
      toast.error("Payroll profiles unavailable", "Could not load the employee payroll profile workspace.");
    } finally {
      loading = false;
      refreshing = false;
    }
  }

  async function openProfile(profile: PayrollProfile) {
    drawerOpen = true;
    drawerLoading = true;
    selectedEmployeeId = profile.employee.id;
    selectedEmployeeDetail = null;
    selectedPayslipDetail = null;
    sensitiveVisible = false;

    try {
      const detailRequest = api.get<EmployeeRecord>(`/hr/employee-records/${profile.employee.id}/`);
      const payslipRequest = profile.latestPayslip
        ? dataMode === "preview" && PREVIEW_PAYSLIP_DETAILS[profile.latestPayslip.id]
          ? Promise.resolve(PREVIEW_PAYSLIP_DETAILS[profile.latestPayslip.id])
          : api.get<PayslipDetail>(`/hr/payslips/${profile.latestPayslip.id}/`)
        : Promise.resolve(null);

      const [detailResult, payslipResult] = await Promise.allSettled([detailRequest, payslipRequest]);
      selectedEmployeeDetail = getSettledValue(detailResult, null);
      selectedPayslipDetail = getSettledValue(payslipResult, null);
    } catch {
      toast.error("Profile detail unavailable", "The payroll profile opened, but some detail blocks could not be refreshed.");
    } finally {
      drawerLoading = false;
    }
  }

  function closeProfile() {
    drawerOpen = false;
    drawerLoading = false;
    selectedEmployeeId = null;
    selectedEmployeeDetail = null;
    selectedPayslipDetail = null;
    allocationDraft = [];
    allocationSeededFor = null;
    includeNhf = false;
    includePendingBonus = false;
    sensitiveVisible = false;
  }

  function jumpToSection(key: SectionKey) {
    const target = drawerBodyEl?.querySelector<HTMLElement>(`[data-section="${key}"]`);
    target?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function rebalanceAllocation(index: number, nextValue: number) {
    if (!allocationDraft.length) return;
    if (allocationDraft.length === 1) {
      allocationDraft = [{ ...allocationDraft[0], ratio: 100 }];
      return;
    }
    const clamped = Math.max(0, Math.min(100, Math.round(nextValue)));
    const current = allocationDraft.map((item) => item.ratio);
    const otherTotal = current.reduce((sum, value, cursor) => (cursor === index ? sum : sum + value), 0);
    const remaining = 100 - clamped;
    const rebalanced = current.map((value, cursor) => {
      if (cursor === index) return clamped;
      if (otherTotal <= 0) return remaining / (current.length - 1);
      return (value / otherTotal) * remaining;
    });
    const normalized = normalizePercentages(rebalanced);
    allocationDraft = allocationDraft.map((item, cursor) => ({ ...item, ratio: normalized[cursor] }));
  }

  function resetAllocationDraft() {
    if (!selectedProfile) return;
    allocationDraft = selectedProfile.allocationBase.map((item) => ({ ...item }));
  }

  const compensationByUser = $derived.by(() => {
    const map = new Map<number, CompensationRecord>();
    for (const record of [...compensationRecords].sort((left, right) => {
      const rightDate = parseDate(right.effective_date)?.getTime() ?? 0;
      const leftDate = parseDate(left.effective_date)?.getTime() ?? 0;
      if (rightDate !== leftDate) return rightDate - leftDate;
      return right.updated_at.localeCompare(left.updated_at);
    })) {
      if (!map.has(record.user)) map.set(record.user, record);
    }
    return map;
  });

  const allowancesByEmployee = $derived.by(() => {
    const map = new Map<number, AllowanceListItem[]>();
    for (const item of allowances) {
      const bucket = map.get(item.employee) ?? [];
      bucket.push(item);
      map.set(item.employee, bucket);
    }
    return map;
  });

  const deductionsByEmployee = $derived.by(() => {
    const map = new Map<number, DeductionListItem[]>();
    for (const item of deductions) {
      const bucket = map.get(item.employee) ?? [];
      bucket.push(item);
      map.set(item.employee, bucket);
    }
    return map;
  });

  const bonusesByEmployee = $derived.by(() => {
    const map = new Map<number, BonusListItem[]>();
    for (const item of bonuses) {
      const bucket = map.get(item.employee) ?? [];
      bucket.push(item);
      map.set(item.employee, bucket);
    }
    return map;
  });

  const payslipsByEmployee = $derived.by(() => {
    const map = new Map<number, PayslipListItem[]>();
    for (const item of payslips) {
      const bucket = map.get(item.employee) ?? [];
      bucket.push(item);
      map.set(item.employee, bucket);
    }
    for (const [employeeId, bucket] of map) {
      bucket.sort((left, right) => {
        const rightDate = parseDate(right.period_end)?.getTime() ?? 0;
        const leftDate = parseDate(left.period_end)?.getTime() ?? 0;
        if (rightDate !== leftDate) return rightDate - leftDate;
        return right.updated_at.localeCompare(left.updated_at);
      });
      map.set(employeeId, bucket);
    }
    return map;
  });

  const taxByEmployee = $derived.by(() => {
    const map = new Map<number, TaxRecordListItem[]>();
    for (const item of taxRecords) {
      const bucket = map.get(item.employee) ?? [];
      bucket.push(item);
      map.set(item.employee, bucket);
    }
    for (const [employeeId, bucket] of map) {
      bucket.sort((left, right) => right.updated_at.localeCompare(left.updated_at));
      map.set(employeeId, bucket);
    }
    return map;
  });

  const documentsByUser = $derived.by(() => {
    const map = new Map<number, HRDocument[]>();
    for (const item of documents) {
      const bucket = map.get(item.user) ?? [];
      bucket.push(item);
      map.set(item.user, bucket);
    }
    for (const [userId, bucket] of map) {
      bucket.sort((left, right) => right.updated_at.localeCompare(left.updated_at));
      map.set(userId, bucket);
    }
    return map;
  });

  const workforceByEmployee = $derived.by(() => {
    const map = new Map<number, ProjectWorkforceLog[]>();
    for (const item of workforceLogs) {
      if (!item.employee) continue;
      const bucket = map.get(item.employee) ?? [];
      bucket.push(item);
      map.set(item.employee, bucket);
    }
    for (const [employeeId, bucket] of map) {
      bucket.sort((left, right) => {
        const rightDate = parseDate(right.report_date)?.getTime() ?? 0;
        const leftDate = parseDate(left.report_date)?.getTime() ?? 0;
        return rightDate - leftDate;
      });
      map.set(employeeId, bucket);
    }
    return map;
  });

  const payrollProfiles = $derived.by(() => {
    return employees
      .map((employee) => {
        const compensation = compensationByUser.get(employee.user_id) ?? null;
        const employeeAllowances = allowancesByEmployee.get(employee.id) ?? [];
        const employeeDeductions = deductionsByEmployee.get(employee.id) ?? [];
        const employeeBonuses = bonusesByEmployee.get(employee.id) ?? [];
        const employeePayslips = payslipsByEmployee.get(employee.id) ?? [];
        const latestPayslip = employeePayslips[0] ?? null;
        const employeeTax = taxByEmployee.get(employee.id) ?? [];
        const employeeDocs = documentsByUser.get(employee.user_id) ?? [];
        const employeeWorkforce = workforceByEmployee.get(employee.id) ?? [];

        const modeled = calculatePayrollProfileTotals({
          compensation,
          allowances: employeeAllowances,
          deductions: employeeDeductions,
          bonuses: employeeBonuses,
          taxRecords: employeeTax,
          includeNhf: hasNhfDeduction(employeeDeductions),
          includePendingBonus: false,
        });

        const currentNet = latestPayslip ? toAmount(latestPayslip.net_salary) : modeled.netPay;
        const currentGross = latestPayslip ? toAmount(latestPayslip.gross_salary) : modeled.grossPay;
        const allocationBase = buildAllocationBase(employee, employeeWorkforce, projects, currentNet);
        const primaryProject = allocationBase[0] ?? {
          projectId: null,
          name: "HQ Operations",
          location: employee.office_location,
          ratio: 100,
          logs: 0,
        };

        const pendingBonusTotal = employeeBonuses
          .filter((item) => item.status === "pending")
          .reduce((sum, item) => sum + toAmount(item.amount), 0);
        const statutoryExposure = employeeTax.reduce((sum, item) => sum + toAmount(item.balance), 0) + modeled.statutoryDeductions;
        const overtimeHours = employeeWorkforce.reduce((sum, item) => sum + toAmount(item.overtime_hours), 0);
        const manualReview = !latestPayslip || pendingBonusTotal > 0 || statutoryExposure > modeled.statutoryDeductions || employeeWorkforce.some((item) => item.payroll_status === "pending");

        let statusTone: ProfileStatusTone = "good";
        let statusLabel = "Verified";
        if (!ACTIVE_EMPLOYMENT_STATUSES.has(employee.employment_status)) {
          statusTone = "muted";
          statusLabel = "Inactive";
        } else if (employee.employment_status === "on_leave") {
          statusTone = "muted";
          statusLabel = "On Leave";
        } else if (manualReview) {
          statusTone = pendingBonusTotal > 0 || statutoryExposure > modeled.statutoryDeductions ? "warn" : "review";
          statusLabel = "Manual Review";
        }

        let attentionNote = "Profile aligned with the current payroll cycle.";
        if (!latestPayslip) attentionNote = "First payslip has not been generated yet for this employee.";
        else if (pendingBonusTotal > 0) attentionNote = "Project bonus is still pending and may alter take-home pay.";
        else if (statutoryExposure > modeled.statutoryDeductions) attentionNote = "Tax or pension exposure needs follow-up this cycle.";
        else if (allocationBase.length > 1) attentionNote = "Labor cost is being split across multiple active projects.";

        const documentCount =
          employeeDocs.length +
          Math.min(employeePayslips.length, 4) +
          employeeTax.filter((item) => item.filing_status === "filed" || item.filing_status === "paid").length;

        return {
          employee,
          compensation,
          allowances: employeeAllowances,
          deductions: employeeDeductions,
          bonuses: employeeBonuses,
          payslips: employeePayslips,
          latestPayslip,
          taxRecords: employeeTax,
          documents: employeeDocs,
          workforce: employeeWorkforce,
          allocationBase,
          primaryProjectName: primaryProject.name,
          primaryProjectLocation: primaryProject.location,
          primaryProjectRatio: primaryProject.ratio,
          statusTone,
          statusLabel,
          employmentStatusLabel: employmentStatusLabel(employee.employment_status),
          attentionNote,
          currentNet,
          currentGross,
          statutoryMonthly: modeled.statutoryDeductions,
          statutoryExposure,
          pendingBonusTotal,
          overtimeHours,
          overtimeRate: deriveOvertimeRate(employee),
          billableRate: deriveBillableRate(toAmount(compensation?.total_package) || currentGross, employee),
          documentCount,
          modeled,
        } satisfies PayrollProfile;
      })
      .sort((left, right) => {
        if (left.statusTone === right.statusTone) return right.currentNet - left.currentNet;
        const rank = { warn: 0, review: 1, good: 2, muted: 3 };
        return rank[left.statusTone] - rank[right.statusTone];
      });
  });

  const projectOptions = $derived.by(() => {
    return [...new Set(payrollProfiles.map((item) => item.primaryProjectName))].sort();
  });

  const filteredProfiles = $derived.by(() => {
    const query = searchQuery.trim().toLowerCase();
    return payrollProfiles.filter((profile) => {
      const matchesQuery =
        !query ||
        profile.employee.full_name.toLowerCase().includes(query) ||
        profile.employee.employee_id.toLowerCase().includes(query) ||
        profile.primaryProjectName.toLowerCase().includes(query) ||
        (profile.employee.department_name ?? "").toLowerCase().includes(query) ||
        profile.employee.job_title.toLowerCase().includes(query);

      const matchesStatus =
        statusFilter === "all"
          ? true
          : statusFilter === "needs_review"
            ? profile.statusTone === "warn" || profile.statusTone === "review"
            : profile.employee.employment_status === statusFilter;

      const matchesProject = projectFilter === "all" ? true : profile.primaryProjectName === projectFilter;
      return matchesQuery && matchesStatus && matchesProject;
    });
  });

  const totalPages = $derived(Math.max(1, Math.ceil(filteredProfiles.length / PROFILES_PER_PAGE)));
  const pagedProfiles = $derived.by(() => {
    const start = (currentPage - 1) * PROFILES_PER_PAGE;
    return filteredProfiles.slice(start, start + PROFILES_PER_PAGE);
  });

  const totalMonthlyNet = $derived(payrollProfiles.reduce((sum, profile) => sum + profile.currentNet, 0));
  const activeHeadcount = $derived(payrollProfiles.filter((item) => ACTIVE_EMPLOYMENT_STATUSES.has(item.employee.employment_status)).length);
  const activeProjectProfiles = $derived(
    payrollProfiles.filter((item) => item.primaryProjectName !== "HQ Operations" && ACTIVE_EMPLOYMENT_STATUSES.has(item.employee.employment_status)).length
  );
  const statutoryExposureTotal = $derived(payrollProfiles.reduce((sum, profile) => sum + profile.statutoryExposure, 0));
  const profilesNeedingReview = $derived(payrollProfiles.filter((item) => item.statusTone === "warn" || item.statusTone === "review").length);

  const selectedProfile = $derived.by(() => payrollProfiles.find((item) => item.employee.id === selectedEmployeeId) ?? null);
  const canRevealSensitive = $derived(
    Boolean(onboarding.user?.is_superuser || onboarding.user?.organization?.role === "admin")
  );

  const selectedCalculation = $derived.by(() => {
    if (!selectedProfile) return null;
    return calculatePayrollProfileTotals({
      compensation: selectedProfile.compensation,
      allowances: selectedProfile.allowances,
      deductions: selectedProfile.deductions,
      bonuses: selectedProfile.bonuses,
      taxRecords: selectedProfile.taxRecords,
      includeNhf,
      includePendingBonus,
    });
  });

  const selectedEarningsRows = $derived.by(() => buildEarningsRows(selectedProfile, selectedPayslipDetail));
  const selectedVault = $derived.by(() => buildVaultItems(selectedProfile));
  const selectedHistory = $derived.by(() => buildHistoryItems(selectedProfile));
  const selectedBanking = $derived.by(() => {
    if (!selectedProfile || dataMode !== "preview") return null;
    return buildPreviewBanking(selectedProfile.employee, selectedProfile.primaryProjectName);
  });

  const selectedLoanEstimate = $derived.by(() => {
    if (!selectedCalculation) return 0;
    return selectedCalculation.loanRepayment * 8;
  });

  const selectedAllocationTotal = $derived(
    allocationDraft.reduce((sum, item) => sum + item.ratio, 0)
  );

  $effect(() => {
    if (currentPage > totalPages) currentPage = 1;
  });

  $effect(() => {
    if (selectedProfile && selectedProfile.employee.id !== allocationSeededFor) {
      allocationDraft = selectedProfile.allocationBase.map((item) => ({ ...item }));
      includeNhf = hasNhfDeduction(selectedProfile.deductions);
      includePendingBonus = false;
      allocationSeededFor = selectedProfile.employee.id;
    }
  });

  onMount(() => {
    loadProfiles();
  });
</script>

<svelte:head>
  <title>Employee Payroll Profiles | developerOS</title>
</svelte:head>

{#if loading}
  <div class="mx-auto flex min-h-[60vh] max-w-7xl items-center justify-center">
    <div class="flex items-center gap-3 rounded-full border border-neutral-200 bg-white/85 px-5 py-3 text-sm text-neutral-600 shadow-sm">
      <div class="h-4 w-4 rounded-full border-2 border-neutral-300 border-t-neutral-900 animate-spin"></div>
      Loading employee payroll profiles...
    </div>
  </div>
{:else}
  <div class="space-y-4 overflow-x-clip">
    <!-- Page header — matches the dashboard pattern -->
    <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">
          <a href="/payroll" class="hover:text-indigo-700">Payroll</a>
          <span class="text-neutral-300"> › </span>
          <span class="text-indigo-600">Employee Profiles</span>
        </p>
        <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Employee Payroll Profiles</h1>
        <p class="mt-1 max-w-2xl text-sm text-neutral-500">
          Command layer unifying HR identity, project cost allocation, statutory exposure, and disbursement readiness.
        </p>
        {#if dataMode === "preview"}
          <div class="mt-3 inline-flex items-center gap-2 rounded-full border border-neutral-200 bg-neutral-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-neutral-500">
            Preview Data
          </div>
        {/if}
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <button
          onclick={() => goto("/payroll")}
          class="inline-flex items-center gap-2 rounded-2xl border border-neutral-200 bg-white px-4 py-2.5 text-sm font-semibold text-neutral-700 transition hover:border-neutral-400 hover:text-neutral-950"
        >
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
          </svg>
          Payroll Dashboard
        </button>
        <button
          onclick={() => loadProfiles({ silent: true })}
          disabled={refreshing}
          class="inline-flex items-center gap-2 rounded-2xl bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-neutral-800 disabled:opacity-50"
        >
          <svg class={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992V4.356m-1.636 14.288A9 9 0 1 1 21 12.003" />
          </svg>
          {refreshing ? "Refreshing..." : "Sync Profiles"}
        </button>
      </div>
    </div>

    <!-- KPI grid -->
    <div class="grid gap-4 xl:grid-cols-4">
      <article class="min-w-0 rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Net Pay Snapshot</p>
        <p class="mt-3 text-2xl font-bold tracking-tight tabular-nums text-neutral-900">{formatCurrency(totalMonthlyNet)}</p>
        <p class="mt-2 text-sm text-neutral-500">Current monthly take-home across active payroll profiles.</p>
      </article>

      <article class="min-w-0 rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Active Headcount</p>
        <p class="mt-3 text-2xl font-bold tracking-tight tabular-nums text-neutral-900">{activeHeadcount}</p>
        <p class="mt-2 text-sm text-neutral-500">{activeProjectProfiles} profiles are capitalized directly into projects this cycle.</p>
      </article>

      <article class="min-w-0 rounded-2xl border border-orange-200 bg-orange-50 p-5 sm:p-6">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-orange-600">Statutory Exposure</p>
        <p class="mt-3 text-2xl font-bold tracking-tight tabular-nums text-orange-900">{formatCurrency(statutoryExposureTotal)}</p>
        <p class="mt-2 text-sm text-orange-700">PAYE, pension, NHF, and open filing balances still live in the cycle.</p>
      </article>

      <article class="min-w-0 rounded-2xl border border-sky-200 bg-sky-50 p-5 sm:p-6">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-sky-600">Manual Review</p>
        <p class="mt-3 text-2xl font-bold tracking-tight tabular-nums text-sky-900">{profilesNeedingReview}</p>
        <p class="mt-2 text-sm text-sky-700">Profiles with pending bonus, tax exposure, or missing payslip detail.</p>
      </article>
    </div>

    <section class="min-w-0 rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-neutral-400">Profile Registry</p>
          <h2 class="mt-2 text-lg font-semibold text-neutral-950">
            {filteredProfiles.length} payroll profile{filteredProfiles.length === 1 ? "" : "s"}
          </h2>
          <p class="mt-1 text-sm text-neutral-500">Last sync: {relativeSyncLabel(lastSyncedAt)}.</p>
        </div>

        <div class="flex flex-col gap-3 lg:flex-row">
          <div class="relative w-full lg:w-80">
            <svg class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.6">
              <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
            </svg>
            <input
              type="text"
              bind:value={searchQuery}
              oninput={() => (currentPage = 1)}
              placeholder="Search by employee, ID, project, or role"
              class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 py-2.5 pl-10 pr-4 text-sm text-neutral-800 placeholder:text-neutral-400 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
            />
          </div>

          <select
            bind:value={statusFilter}
            onchange={() => (currentPage = 1)}
            class="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-2.5 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
          >
            <option value="all">All statuses</option>
            <option value="active">Active</option>
            <option value="probation">Probation</option>
            <option value="on_leave">On leave</option>
            <option value="needs_review">Needs review</option>
            <option value="terminated">Inactive</option>
          </select>

          <select
            bind:value={projectFilter}
            onchange={() => (currentPage = 1)}
            class="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-2.5 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
          >
            <option value="all">All projects</option>
            {#each projectOptions as option}
              <option value={option}>{option}</option>
            {/each}
          </select>
        </div>
      </div>
    </section>

    <section class="min-w-0 overflow-hidden rounded-2xl border border-neutral-200 bg-white">
      {#if filteredProfiles.length === 0}
        <div class="px-8 py-20 text-center">
          <p class="text-lg font-semibold text-neutral-900">No payroll profiles match these filters.</p>
          <p class="mt-2 text-sm text-neutral-500">Try widening the status or project filter, or clear the search query.</p>
        </div>
      {:else}
        <div class="overflow-x-auto">
          <table class="min-w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-200 bg-neutral-50 text-[10px] uppercase tracking-wider text-neutral-500">
                <th class="px-6 py-3 text-left font-semibold">Employee</th>
                <th class="px-6 py-3 text-left font-semibold">Primary Project</th>
                <th class="px-6 py-3 text-left font-semibold">Earnings Stack</th>
                <th class="px-6 py-3 text-left font-semibold">Compliance</th>
                <th class="px-6 py-3 text-left font-semibold">Allocation</th>
                <th class="px-6 py-3 text-right font-semibold">Net Pay</th>
                <th class="px-6 py-3 text-left font-semibold">Status</th>
                <th class="px-6 py-3 text-right font-semibold">Open</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each pagedProfiles as profile}
                <tr class="border-t border-neutral-200 align-top transition hover:bg-neutral-50">
                  <td class="px-6 py-5">
                    <div class="flex items-start gap-3">
                      {#if profile.employee.profile_photo}
                        <img src={profile.employee.profile_photo} alt={profile.employee.full_name} class="h-12 w-12 rounded-2xl object-cover" />
                      {:else}
                        <div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-neutral-900 text-sm font-semibold text-white">
                          {profile.employee.full_name.split(" ").map((part) => part[0]).slice(0, 2).join("")}
                        </div>
                      {/if}
                      <div class="min-w-0">
                        <p class="truncate text-base font-bold text-neutral-950">{profile.employee.full_name}</p>
                        <p class="mt-0.5 text-[10px] uppercase tracking-wider text-neutral-400">{profile.employee.employee_id}</p>
                        <p class="mt-2 text-sm text-neutral-500">{profile.employee.job_title}</p>
                        <p class="mt-1 text-xs text-neutral-400">{profile.employee.department_name ?? "No department"} &middot; {profile.employee.office_location}</p>
                      </div>
                    </div>
                  </td>

                  <td class="px-6 py-5">
                    <div class="rounded-2xl border border-neutral-200 bg-white px-4 py-3">
                      <p class="text-sm font-semibold text-neutral-900">{profile.primaryProjectName}</p>
                      <p class="mt-1 text-xs text-neutral-400">{profile.primaryProjectLocation}</p>
                      <span class="mt-3 inline-flex rounded-full border border-neutral-200 bg-neutral-50 px-2.5 py-1 text-[11px] font-medium text-neutral-600">
                        {profile.primaryProjectRatio}% primary allocation
                      </span>
                    </div>
                  </td>

                  <td class="px-6 py-5">
                    <div class="space-y-2">
                      <div>
                        <p class="text-[10px] uppercase tracking-wider text-neutral-400">Base</p>
                        <p class="mt-1 font-semibold tabular-nums text-neutral-900">{formatCurrency(profile.modeled.baseSalary)}</p>
                      </div>
                      <div>
                        <p class="text-[10px] uppercase tracking-wider text-neutral-400">Allowances</p>
                        <p class="mt-1 text-sm tabular-nums text-neutral-600">{formatCurrency(profile.modeled.recurringAllowances)}</p>
                      </div>
                      <div>
                        <p class="text-[10px] uppercase tracking-wider text-neutral-400">Bonuses</p>
                        <p class={`mt-1 text-sm tabular-nums ${profile.pendingBonusTotal > 0 ? "font-semibold text-orange-600" : "text-neutral-600"}`}>
                          {formatCurrency(profile.modeled.approvedBonuses + profile.pendingBonusTotal)}
                        </p>
                      </div>
                    </div>
                  </td>

                  <td class="px-6 py-5">
                    <div class="space-y-2">
                      <div>
                        <p class="text-[10px] uppercase tracking-wider text-neutral-400">Monthly statutory</p>
                        <p class="mt-1 font-semibold tabular-nums text-neutral-900">{formatCurrency(profile.statutoryMonthly)}</p>
                      </div>
                      <div>
                        <p class="text-[10px] uppercase tracking-wider text-neutral-400">Exposure</p>
                        <p class={`mt-1 tabular-nums ${profile.statutoryExposure > profile.statutoryMonthly ? "font-semibold text-orange-600" : "text-neutral-600"}`}>
                          {formatCurrency(profile.statutoryExposure)}
                        </p>
                      </div>
                    </div>
                  </td>

                  <td class="px-6 py-5">
                    <div class="flex flex-wrap gap-2">
                      {#each profile.allocationBase.slice(0, 2) as item}
                        <span class="inline-flex rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[11px] font-medium text-emerald-700">
                          {item.name} {item.ratio}%
                        </span>
                      {/each}
                      {#if profile.allocationBase.length > 2}
                        <span class="inline-flex rounded-full border border-neutral-200 bg-neutral-50 px-2.5 py-1 text-[11px] font-medium text-neutral-600">
                          +{profile.allocationBase.length - 2} more
                        </span>
                      {/if}
                    </div>
                    <p class="mt-3 text-xs text-neutral-400">{profile.overtimeHours.toFixed(1)} overtime hrs in recent logs</p>
                  </td>

                  <td class="px-6 py-5 text-right">
                    <p class="text-xl font-bold tracking-tight tabular-nums text-neutral-950">{formatCurrency(profile.currentNet)}</p>
                    <p class="mt-2 text-xs text-neutral-400">Gross {formatCurrency(profile.currentGross)}</p>
                  </td>

                  <td class="px-6 py-5">
                    <span class={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold ${profile.statusTone === "good" ? "bg-emerald-100 text-emerald-700" : profile.statusTone === "warn" ? "bg-orange-100 text-orange-700" : profile.statusTone === "review" ? "bg-sky-100 text-sky-700" : "bg-neutral-200 text-neutral-600"}`}>
                      {#if profile.statusTone === "good"}
                        <span class="pulse-dot h-2 w-2 rounded-full bg-emerald-500"></span>
                      {/if}
                      {profile.statusLabel}
                    </span>
                    <p class="mt-3 max-w-xs text-xs leading-5 text-neutral-500">{profile.attentionNote}</p>
                  </td>

                  <td class="px-6 py-5 text-right">
                    <button
                      onclick={() => openProfile(profile)}
                      class="inline-flex items-center gap-2 rounded-2xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-neutral-800"
                    >
                      Open Profile
                      <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.7">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                      </svg>
                    </button>
                    <p class="mt-3 text-xs text-neutral-400">{profile.documentCount} vault item{profile.documentCount === 1 ? "" : "s"}</p>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>

        {#if totalPages > 1}
          <div class="flex flex-col gap-3 border-t border-neutral-100 px-6 py-4 text-sm text-neutral-500 sm:flex-row sm:items-center sm:justify-between">
            <span>
              Showing {(currentPage - 1) * PROFILES_PER_PAGE + 1}-{Math.min(currentPage * PROFILES_PER_PAGE, filteredProfiles.length)} of {filteredProfiles.length}
            </span>
            <div class="flex items-center gap-2">
              <button
                onclick={() => (currentPage = Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
                class="rounded-xl border border-neutral-200 px-3 py-2 hover:bg-neutral-50 disabled:opacity-40"
              >
                Previous
              </button>
              {#each Array.from({ length: totalPages }, (_, index) => index + 1).slice(Math.max(0, currentPage - 3), Math.min(totalPages, currentPage + 2)) as pageNumber}
                <button
                  onclick={() => (currentPage = pageNumber)}
                  class={`h-10 w-10 rounded-xl ${pageNumber === currentPage ? "bg-neutral-950 text-white" : "border border-neutral-200 text-neutral-600 hover:bg-neutral-50"}`}
                >
                  {pageNumber}
                </button>
              {/each}
              <button
                onclick={() => (currentPage = Math.min(totalPages, currentPage + 1))}
                disabled={currentPage === totalPages}
                class="rounded-xl border border-neutral-200 px-3 py-2 hover:bg-neutral-50 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        {/if}
      {/if}
    </section>
  </div>
{/if}

{#if drawerOpen}
  <div
    class="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm"
    onclick={closeProfile}
    onkeydown={(event) => event.key === "Escape" && closeProfile()}
    role="button"
    tabindex="-1"
  ></div>

  <div class="fixed inset-y-0 right-0 z-50 w-full max-w-[1480px] border-l border-neutral-200 bg-white shadow-2xl drawer-slide-in">
    {#if drawerLoading || !selectedProfile}
      <div class="flex h-full items-center justify-center">
        <div class="flex items-center gap-3 rounded-full border border-neutral-200 bg-white px-5 py-3 text-sm text-neutral-600 shadow-sm">
          <div class="h-4 w-4 rounded-full border-2 border-neutral-300 border-t-neutral-900 animate-spin"></div>
          Building payroll profile...
        </div>
      </div>
    {:else}
      <div class="flex h-full flex-col">
        <div class="flex items-center justify-between px-6 py-4 bg-neutral-900 border-b border-neutral-200">
          <div class="flex min-w-0 items-center gap-4">
            {#if selectedProfile.employee.profile_photo}
              <img src={selectedProfile.employee.profile_photo} alt={selectedProfile.employee.full_name} class="h-11 w-11 rounded-2xl object-cover" />
            {:else}
              <div class="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/10 text-sm font-semibold text-white">
                {selectedProfile.employee.full_name.split(" ").map((part) => part[0]).slice(0, 2).join("")}
              </div>
            {/if}
            <div class="min-w-0">
              <p class="truncate text-lg font-semibold text-white">
                {selectedProfile.employee.full_name}
              </p>
              <div class="mt-1 flex flex-wrap items-center gap-2 text-xs text-neutral-400">
                <span>{selectedProfile.employee.employee_id}</span>
                <span>&middot;</span>
                <span>{selectedProfile.employee.job_title}</span>
                <span>&middot;</span>
                <span>{selectedProfile.primaryProjectName}</span>
              </div>
            </div>
          </div>

          <div class="flex items-center gap-2">
            <button
              onclick={() => goto("/hr/compensation")}
              class="rounded-2xl border border-neutral-700 px-3 py-2 text-xs font-medium text-neutral-300 transition hover:border-neutral-500 hover:text-white"
            >
              Compensation
            </button>
            <button
              onclick={() => goto("/hr/payslips")}
              class="rounded-2xl border border-neutral-700 px-3 py-2 text-xs font-medium text-neutral-300 transition hover:border-neutral-500 hover:text-white"
            >
              Payslips
            </button>
            <button
              onclick={() => goto("/hr/deductions")}
              class="rounded-2xl border border-neutral-700 px-3 py-2 text-xs font-medium text-neutral-300 transition hover:border-neutral-500 hover:text-white"
            >
              Deductions
            </button>
            <button
              onclick={closeProfile}
              class="flex h-8 w-8 items-center justify-center rounded-2xl text-neutral-400 transition hover:bg-white/10 hover:text-white"
              aria-label="Close profile"
            >
              <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <div class="border-b border-neutral-200 px-6 py-3">
          <div class="flex flex-wrap items-center gap-6 text-sm">
            <div>
              <span class="text-neutral-400">Current net:</span>
              <span class="ml-2 font-semibold text-neutral-950 tabular-nums">
                {formatCurrency(selectedProfile.currentNet)}
              </span>
            </div>
            <div>
              <span class="text-neutral-400">Gross:</span>
              <span class="ml-2 font-semibold text-neutral-900 tabular-nums">{formatCurrency(selectedProfile.currentGross)}</span>
            </div>
            <div>
              <span class="text-neutral-400">Primary allocation:</span>
              <span class="ml-2 font-semibold text-neutral-900">{selectedProfile.primaryProjectRatio}% {selectedProfile.primaryProjectName}</span>
            </div>
            <div>
              <span class="text-neutral-400">Overtime:</span>
              <span class="ml-2 font-semibold text-neutral-900">{selectedProfile.overtimeHours.toFixed(1)} hrs</span>
            </div>
          </div>
        </div>

        <div bind:this={drawerBodyEl} class="flex-1 overflow-y-auto bg-neutral-50">
          <div class="grid gap-6 px-6 py-6 xl:grid-cols-[250px_minmax(0,1fr)]">
            <aside class="xl:sticky xl:top-6 xl:self-start">
              <div class="rounded-2xl border border-neutral-200 bg-white p-4">
                <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-neutral-400">Section Navigation</p>
                <div class="mt-4 space-y-2">
                  {#each SECTION_ITEMS as section}
                    <button
                      onclick={() => jumpToSection(section.key)}
                      class={`w-full rounded-2xl border px-4 py-3 text-left transition ${sectionButtonClasses(section.key, selectedProfile.statusTone === "good")}`}
                    >
                      <p class="text-sm font-semibold">{section.label}</p>
                      <p class="mt-1 text-xs text-neutral-500">{section.caption}</p>
                    </button>
                  {/each}
                </div>
              </div>
            </aside>

            <div class="space-y-6">
              <section data-section="overview" class="space-y-4">
                <div class="rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
                  <div class="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
                    <div class="flex min-w-0 items-start gap-4">
                      {#if selectedProfile.employee.profile_photo}
                        <img src={selectedProfile.employee.profile_photo} alt={selectedProfile.employee.full_name} class="h-20 w-20 rounded-2xl object-cover" />
                      {:else}
                        <div class="flex h-20 w-20 items-center justify-center rounded-2xl bg-neutral-900 text-xl font-semibold text-white">
                          {selectedProfile.employee.full_name.split(" ").map((part) => part[0]).slice(0, 2).join("")}
                        </div>
                      {/if}
                      <div class="min-w-0">
                        <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-neutral-400">Employee Identity</p>
                        <h2 class="mt-3 truncate text-lg font-semibold text-neutral-950">
                          {selectedProfile.employee.full_name}
                        </h2>
                        <div class="mt-3 flex flex-wrap items-center gap-2">
                          <span class={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold ${employmentStatusClasses(selectedProfile.employee.employment_status)}`}>
                            <span class={`h-2 w-2 rounded-full ${selectedProfile.employee.employment_status === "active" ? "pulse-dot bg-emerald-500" : "bg-neutral-400"}`}></span>
                            {selectedProfile.employmentStatusLabel}
                          </span>
                          <span class="inline-flex rounded-full border border-neutral-200 bg-white px-3 py-1 text-xs font-medium text-neutral-600">
                            {selectedProfile.employee.employee_id}
                          </span>
                          <span class="inline-flex rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
                            {selectedProfile.primaryProjectName}
                          </span>
                        </div>
                        <p class="mt-4 max-w-3xl text-sm leading-6 text-neutral-600">
                          {selectedProfile.attentionNote}
                        </p>
                      </div>
                    </div>

                    <div class="rounded-2xl bg-neutral-900 p-5 text-white">
                      <p class="text-[10px] font-semibold uppercase tracking-wider text-white/60">Net Pay Snapshot</p>
                      <p class="mt-4 text-3xl font-semibold tabular-nums">
                        {formatCurrency(selectedProfile.currentNet)}
                      </p>
                      <p class="mt-3 text-sm text-white/70">Current monthly take-home from the latest payroll cycle.</p>
                    </div>
                  </div>

                  <div class="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                    <div class="rounded-2xl border border-neutral-200 bg-white p-4">
                      <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Role</p>
                      <p class="mt-3 text-base font-semibold text-neutral-900">{selectedProfile.employee.position_title ?? selectedProfile.employee.job_title}</p>
                      <p class="mt-1 text-xs text-neutral-500">{selectedProfile.employee.department_name ?? "No department mapped"}</p>
                    </div>
                    <div class="rounded-2xl border border-neutral-200 bg-white p-4">
                      <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Manager</p>
                      <p class="mt-3 text-base font-semibold text-neutral-900">{selectedProfile.employee.manager_name ?? "Not assigned"}</p>
                      <p class="mt-1 text-xs text-neutral-500">Hire date {formatDate(selectedProfile.employee.hire_date)}</p>
                    </div>
                    <div class="rounded-2xl border border-neutral-200 bg-white p-4">
                      <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Payroll Status</p>
                      <p class="mt-3 text-base font-semibold text-neutral-900">{selectedProfile.statusLabel}</p>
                      <p class="mt-1 text-xs text-neutral-500">
                        {selectedProfile.latestPayslip ? `Latest payslip ${shortDate(selectedProfile.latestPayslip.period_end)}` : "Awaiting first payslip"}
                      </p>
                    </div>
                    <div class="rounded-2xl border border-neutral-200 bg-white p-4">
                      <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Contract</p>
                      <p class="mt-3 text-base font-semibold text-neutral-900">{selectedEmployeeDetail?.contract_type || selectedProfile.employee.contract_type || "Not set"}</p>
                      <p class="mt-1 text-xs text-neutral-500">{selectedEmployeeDetail?.notes || "Payroll-linked employee record"}</p>
                    </div>
                  </div>
                </div>
              </section>

              <section data-section="earnings" class="rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
                <div class="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
                  <div>
                    <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-neutral-400">Compensation Structure</p>
                    <h3 class="mt-2 text-lg font-semibold text-neutral-950">Earnings Stack</h3>
                    <p class="mt-2 text-sm text-neutral-500">Fixed and variable pay components feeding the payroll run.</p>
                  </div>
                  <button
                    onclick={() => goto("/hr/compensation")}
                    class="inline-flex items-center gap-2 rounded-2xl border border-neutral-200 bg-white px-4 py-2 text-sm font-semibold text-neutral-700 transition hover:border-neutral-400 hover:text-neutral-950"
                  >
                    Manage in Compensation
                  </button>
                </div>

                <div class="mt-6 overflow-hidden rounded-2xl border border-neutral-200 bg-white">
                  <table class="min-w-full text-sm">
                    <thead>
                      <tr class="border-b border-neutral-200 bg-neutral-50">
                        <th class="px-5 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Component</th>
                        <th class="px-5 py-3 text-right text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Amount</th>
                        <th class="px-5 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Frequency</th>
                        <th class="px-5 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">UX Detail</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-neutral-100">
                      {#each selectedEarningsRows as row}
                        <tr>
                          <td class="px-5 py-4 font-medium text-neutral-900">{row.label}</td>
                          <td class={`px-5 py-4 text-right font-semibold tabular-nums ${row.tone === "warn" ? "text-orange-600" : row.tone === "good" ? "text-emerald-700" : "text-neutral-900"}`}>
                            {row.amount !== null ? formatCurrency(row.amount) : "Variable"}
                          </td>
                          <td class="px-5 py-4 text-neutral-600">{row.frequency}</td>
                          <td class={`px-5 py-4 ${row.tone === "warn" ? "text-orange-600" : "text-neutral-500"}`}>{row.detail}</td>
                        </tr>
                      {/each}
                    </tbody>
                  </table>
                </div>
              </section>

              <section data-section="compliance" class="space-y-4 rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
                <div class="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
                  <div>
                    <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-neutral-400">Compliance Layer</p>
                    <h3 class="mt-2 text-lg font-semibold text-neutral-950">Statutory and Voluntary Deductions</h3>
                    <p class="mt-2 text-sm text-neutral-500">Live deduction logic reacts as NHF and pending bonus assumptions change.</p>
                  </div>
                  <div class="flex flex-wrap items-center gap-3 text-sm">
                    <label class="inline-flex items-center gap-2 rounded-2xl border border-neutral-200 bg-white px-3 py-2 text-neutral-700">
                      <input type="checkbox" bind:checked={includeNhf} class="rounded border-neutral-300 text-emerald-600 focus:ring-emerald-200" />
                      Include NHF 2.5%
                    </label>
                    <label class="inline-flex items-center gap-2 rounded-2xl border border-neutral-200 bg-white px-3 py-2 text-neutral-700">
                      <input type="checkbox" bind:checked={includePendingBonus} class="rounded border-neutral-300 text-emerald-600 focus:ring-emerald-200" />
                      Include pending bonuses
                    </label>
                  </div>
                </div>

                {#if selectedCalculation}
                  <div class="grid gap-4 xl:grid-cols-4">
                    <article class="rounded-2xl border border-neutral-200 bg-white p-5">
                      <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">PAYE Tax</p>
                      <p class="mt-3 text-2xl font-semibold text-neutral-950 tabular-nums">{formatCurrency(selectedCalculation.paye)}</p>
                      <p class="mt-2 text-sm text-neutral-500">Calculated from active tax deductions and latest tax filing.</p>
                    </article>
                    <article class="rounded-2xl border border-emerald-200 bg-emerald-50 p-5">
                      <p class="text-[10px] font-semibold uppercase tracking-wider text-emerald-600">Pension Split</p>
                      <p class="mt-3 text-2xl font-semibold text-emerald-800 tabular-nums">
                        {formatCurrency(selectedCalculation.pensionEmployee)}
                      </p>
                      <p class="mt-2 text-sm text-emerald-700/80">Employee 8% / Employer {formatCurrency(selectedCalculation.pensionEmployer)} tracked.</p>
                    </article>
                    <article class="rounded-2xl border border-sky-200 bg-sky-50 p-5">
                      <p class="text-[10px] font-semibold uppercase tracking-wider text-sky-600">NHF Toggle</p>
                      <p class="mt-3 text-2xl font-semibold text-sky-700 tabular-nums">
                        {formatCurrency(selectedCalculation.nhf)}
                      </p>
                      <p class="mt-2 text-sm text-sky-700/80">{includeNhf ? "Housing fund is included in the modeled net pay." : "Housing fund is currently excluded from the model."}</p>
                    </article>
                    <article class="rounded-2xl border border-orange-200 bg-orange-50 p-5">
                      <p class="text-[10px] font-semibold uppercase tracking-wider text-orange-600">Loan Tracker</p>
                      <p class="mt-3 text-2xl font-semibold text-orange-700 tabular-nums">
                        {formatCurrency(selectedCalculation.loanRepayment)}
                      </p>
                      <p class="mt-2 text-sm text-orange-700/80">
                        {selectedCalculation.loanRepayment > 0 ? `Estimated remaining balance ${formatCurrency(selectedLoanEstimate)}.` : "No active payroll loan deductions are linked."}
                      </p>
                    </article>
                  </div>

                  <div class="grid gap-4 xl:grid-cols-[1fr_320px]">
                    <div class="rounded-2xl border border-neutral-200 bg-white p-5">
                      <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Deduction Summary</p>
                      <div class="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                        <div class="rounded-2xl bg-neutral-50 px-4 py-3">
                          <p class="text-xs text-neutral-400">Insurance</p>
                          <p class="mt-2 font-semibold text-neutral-900 tabular-nums">{formatCurrency(selectedCalculation.insurance)}</p>
                        </div>
                        <div class="rounded-2xl bg-neutral-50 px-4 py-3">
                          <p class="text-xs text-neutral-400">Union</p>
                          <p class="mt-2 font-semibold text-neutral-900 tabular-nums">{formatCurrency(selectedCalculation.unionDues)}</p>
                        </div>
                        <div class="rounded-2xl bg-neutral-50 px-4 py-3">
                          <p class="text-xs text-neutral-400">Other</p>
                          <p class="mt-2 font-semibold text-neutral-900 tabular-nums">{formatCurrency(selectedCalculation.otherDeductions)}</p>
                        </div>
                        <div class="rounded-2xl bg-neutral-900 px-4 py-3 text-white">
                          <p class="text-xs text-white/60">Modeled Net Pay</p>
                          <p class="mt-2 font-semibold tabular-nums">{formatCurrency(selectedCalculation.netPay)}</p>
                        </div>
                      </div>
                    </div>

                    <div class="rounded-2xl border border-neutral-200 bg-white p-5">
                      <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Current Controls</p>
                      <div class="mt-4 space-y-3 text-sm text-neutral-600">
                        <div class="flex items-center justify-between rounded-2xl bg-neutral-50 px-4 py-3">
                          <span>Gross modeled pay</span>
                          <span class="font-semibold text-neutral-900 tabular-nums">{formatCurrency(selectedCalculation.grossPay)}</span>
                        </div>
                        <div class="flex items-center justify-between rounded-2xl bg-neutral-50 px-4 py-3">
                          <span>Total deductions</span>
                          <span class="font-semibold text-neutral-900 tabular-nums">{formatCurrency(selectedCalculation.totalDeductions)}</span>
                        </div>
                        <div class="flex items-center justify-between rounded-2xl bg-neutral-50 px-4 py-3">
                          <span>Pending bonus exposure</span>
                          <span class={`font-semibold tabular-nums ${selectedProfile.pendingBonusTotal > 0 ? "text-orange-600" : "text-neutral-900"}`}>
                            {formatCurrency(selectedProfile.pendingBonusTotal)}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                {/if}
              </section>

              <section data-section="allocation" class="space-y-4 rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
                <div class="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
                  <div>
                    <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-neutral-400">Project Allocation and Timesheets</p>
                    <h3 class="mt-2 text-lg font-semibold text-neutral-950">Cost Center Mapping</h3>
                    <p class="mt-2 text-sm text-neutral-500">Adjust the project split below. The slider total always resolves back to 100%.</p>
                  </div>
                  <div class="flex flex-wrap items-center gap-3">
                    <button
                      onclick={resetAllocationDraft}
                      class="inline-flex items-center gap-2 rounded-2xl border border-neutral-200 bg-white px-4 py-2 text-sm font-semibold text-neutral-700 transition hover:border-neutral-400 hover:text-neutral-950"
                    >
                      Reset Split
                    </button>
                    <button
                      onclick={() => goto("/payroll/time-inputs")}
                      class="inline-flex items-center gap-2 rounded-2xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-neutral-800"
                    >
                      Open Time Inputs
                    </button>
                  </div>
                </div>

                <div class="grid gap-4 xl:grid-cols-3">
                  <article class="rounded-2xl border border-neutral-200 bg-white p-5">
                    <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Overtime Rate</p>
                    <p class="mt-3 text-2xl font-semibold text-neutral-950">{selectedProfile.overtimeRate.toFixed(2)}x</p>
                    <p class="mt-2 text-sm text-neutral-500">Operational multiplier inferred from role and site context.</p>
                  </article>
                  <article class="rounded-2xl border border-neutral-200 bg-white p-5">
                    <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Billable Rate</p>
                    <p class="mt-3 text-2xl font-semibold text-neutral-950 tabular-nums">{formatCurrency(selectedProfile.billableRate)}</p>
                    <p class="mt-2 text-sm text-neutral-500">Modeled internal charge-out rate for project feasibility and IRR work.</p>
                  </article>
                  <article class="rounded-2xl border border-orange-200 bg-orange-50 p-5">
                    <p class="text-[10px] font-semibold uppercase tracking-wider text-orange-600">Recent Labor Burn</p>
                    <p class="mt-3 text-2xl font-semibold text-orange-700 tabular-nums">{selectedProfile.overtimeHours.toFixed(1)} hrs</p>
                    <p class="mt-2 text-sm text-orange-700/80">Overtime logged in the last 60 days from workforce and site attendance records.</p>
                  </article>
                </div>

                <div class="grid gap-4">
                  {#each allocationDraft as item, index}
                    <AllocationSlider
                      label={item.name}
                      note={`${item.location} · ${item.logs} recent log${item.logs === 1 ? "" : "s"}`}
                      value={item.ratio}
                      amountLabel={selectedCalculation ? formatCurrency((selectedCalculation.netPay * item.ratio) / 100) : ""}
                      onChange={(value) => rebalanceAllocation(index, value)}
                    />
                  {/each}
                </div>

                <div class="rounded-2xl border border-dashed border-emerald-300 bg-emerald-50 px-5 py-4 text-sm text-emerald-700">
                  Total allocation: <span class="font-semibold">{selectedAllocationTotal}%</span>. The working split is interactive for planning and always balances back to 100%.
                </div>
              </section>

              <section data-section="banking" class="space-y-4 rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
                <div class="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
                  <div>
                    <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-neutral-400">Banking and Payment Metadata</p>
                    <h3 class="mt-2 text-lg font-semibold text-neutral-950">Secure Disbursement Layer</h3>
                    <p class="mt-2 text-sm text-neutral-500">Sensitive payroll fields stay masked unless the current session has elevated access.</p>
                  </div>
                  <button
                    onclick={() => (sensitiveVisible = !sensitiveVisible)}
                    disabled={!canRevealSensitive}
                    class={`inline-flex items-center gap-2 rounded-2xl px-4 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${canRevealSensitive ? "bg-neutral-900 text-white hover:bg-neutral-800" : "border border-neutral-200 bg-white text-neutral-500"}`}
                  >
                    {canRevealSensitive ? (sensitiveVisible ? "Hide Sensitive Data" : "View Sensitive Data") : "Requires admin access"}
                  </button>
                </div>

                <div class="grid gap-4 xl:grid-cols-[1fr_320px]">
                  <div class="rounded-2xl border border-neutral-200 bg-white p-5">
                    <div class="grid gap-4 md:grid-cols-2">
                      <div class="rounded-2xl bg-neutral-50 px-4 py-4">
                        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Bank Name</p>
                        <p class="mt-3 text-base font-semibold text-neutral-900">
                          {#if sensitiveVisible && canRevealSensitive && selectedBanking}
                            {selectedBanking.bankName}
                          {:else if sensitiveVisible && canRevealSensitive}
                            Awaiting secure registry sync
                          {:else}
                            Hidden
                          {/if}
                        </p>
                      </div>
                      <div class="rounded-2xl bg-neutral-50 px-4 py-4">
                        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Account Number</p>
                        <p class="mt-3 text-base font-semibold text-neutral-900">
                          {#if sensitiveVisible && canRevealSensitive && selectedBanking}
                            {selectedBanking.accountNumber}
                          {:else if selectedBanking}
                            {maskAccount(selectedBanking.accountNumber)}
                          {:else}
                            Not available
                          {/if}
                        </p>
                      </div>
                      <div class="rounded-2xl bg-neutral-50 px-4 py-4">
                        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Payment Method</p>
                        <p class="mt-3 text-base font-semibold text-neutral-900">{selectedBanking?.paymentMethod ?? "Awaiting secure registry sync"}</p>
                      </div>
                      <div class="rounded-2xl bg-neutral-50 px-4 py-4">
                        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">TIN</p>
                        <p class="mt-3 text-base font-semibold text-neutral-900">
                          {#if sensitiveVisible && canRevealSensitive && selectedBanking}
                            {selectedBanking.tin}
                          {:else if selectedBanking}
                            {maskTin(selectedBanking.tin)}
                          {:else}
                            Not available
                          {/if}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div class="rounded-2xl border border-neutral-200 bg-white p-5">
                    <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Security Layer</p>
                    <div class="mt-4 space-y-3 text-sm text-neutral-600">
                      <div class="rounded-2xl bg-neutral-50 px-4 py-3">
                        {#if canRevealSensitive}
                          This session is allowed to unlock payroll-sensitive metadata.
                        {:else}
                          Bank details and TIN stay masked until an admin or elevated payroll reviewer opens the profile.
                        {/if}
                      </div>
                      <div class="rounded-2xl bg-neutral-50 px-4 py-3">
                        {#if selectedBanking}
                          Preview registry status: <span class={`font-semibold ${selectedBanking.verified ? "text-emerald-700" : "text-neutral-700"}`}>{selectedBanking.sourceLabel}</span>
                        {:else}
                          No dedicated disbursement registry is wired into this employee profile yet.
                        {/if}
                      </div>
                    </div>
                  </div>
                </div>
              </section>

              <section data-section="documents" class="space-y-4 rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
                <div class="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
                  <div>
                    <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-neutral-400">Document Vault</p>
                    <h3 class="mt-2 text-lg font-semibold text-neutral-950">Paper Trail</h3>
                    <p class="mt-2 text-sm text-neutral-500">Contracts, payslip archive, tax clearance, and payroll support files in one gallery.</p>
                  </div>
                  <button
                    onclick={() => goto("/hr/contracts")}
                    class="inline-flex items-center gap-2 rounded-2xl border border-neutral-200 bg-white px-4 py-2 text-sm font-semibold text-neutral-700 transition hover:border-neutral-400 hover:text-neutral-950"
                  >
                    Open HR Documents
                  </button>
                </div>

                <div class="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
                  {#each selectedVault as item}
                    <article class="rounded-2xl border border-neutral-200 bg-white p-5">
                      <div class="flex items-start justify-between gap-3">
                        <div>
                          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">{item.kind}</p>
                          <h4 class="mt-2 text-lg font-semibold text-neutral-950">{item.title}</h4>
                        </div>
                        <span class={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold ${item.tone === "good" ? "bg-emerald-100 text-emerald-700" : item.tone === "warn" ? "bg-orange-100 text-orange-700" : "bg-neutral-100 text-neutral-600"}`}>
                          {item.tone === "good" ? "Ready" : item.tone === "warn" ? "Pending" : "Vault"}
                        </span>
                      </div>
                      <p class="mt-3 text-sm leading-6 text-neutral-600">{item.subtitle}</p>
                      <div class="mt-5 flex items-center justify-between text-xs text-neutral-400">
                        <span>{formatDate(item.date)}</span>
                        {#if item.href}
                          <a href={item.href} target="_blank" rel="noreferrer" class="font-medium text-neutral-700 hover:text-neutral-950">{item.actionLabel}</a>
                        {:else}
                          <button
                            onclick={() => {
                              if (item.kind === "payslip") goto("/hr/payslips");
                              else if (item.kind === "tax clearance") goto("/hr/tax-records");
                              else goto("/hr/contracts");
                            }}
                            class="font-medium text-neutral-700 hover:text-neutral-950"
                          >
                            {item.actionLabel}
                          </button>
                        {/if}
                      </div>
                    </article>
                  {/each}
                </div>
              </section>

              <section data-section="history" class="rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
                <div>
                  <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-neutral-400">Payroll History</p>
                  <h3 class="mt-2 text-lg font-semibold text-neutral-950">Compensation and Labor Cost Timeline</h3>
                  <p class="mt-2 text-sm text-neutral-500">A running trail from compensation setup through tax, bonuses, and payslip generation.</p>
                </div>

                <div class="mt-6 space-y-4">
                  {#each selectedHistory as item}
                    <div class="flex gap-4 rounded-2xl border border-neutral-200 bg-white px-5 py-4">
                      <div class={`mt-1 h-3 w-3 rounded-full ${item.tone === "good" ? "bg-emerald-500" : item.tone === "warn" ? "bg-orange-500" : "bg-neutral-300"}`}></div>
                      <div class="flex-1">
                        <div class="flex flex-col gap-1 md:flex-row md:items-center md:justify-between">
                          <p class="font-semibold text-neutral-900">{item.label}</p>
                          <span class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">{formatDate(item.date)}</span>
                        </div>
                        <p class="mt-2 text-sm leading-6 text-neutral-600">{item.description}</p>
                      </div>
                    </div>
                  {/each}
                </div>
              </section>
            </div>
          </div>
        </div>
      </div>
    {/if}
  </div>
{/if}

<svelte:window onkeydown={(event) => event.key === "Escape" && drawerOpen && closeProfile()} />

<style>
  .drawer-slide-in { animation: drawerSlideIn 0.25s ease-out both; }
  @keyframes drawerSlideIn {
    from { transform: translateX(100%); }
    to { transform: translateX(0); }
  }

  .pulse-dot {
    animation: pulseDot 1.8s ease-in-out infinite;
  }

  @keyframes pulseDot {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.55; transform: scale(1.25); }
  }
</style>

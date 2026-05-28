<script lang="ts">
  import { onMount } from "svelte";
  import { api } from "$lib/api";
  import { fetchAllPages, toAmount } from "$lib/contracts";
  import BankExport from "$lib/components/payroll/BankExport.svelte";
  import BankFilePreview from "$lib/components/payroll/BankFilePreview.svelte";
  import { PREVIEW_PAYROLL_DASHBOARD_DATA } from "$lib/payrollDashboardPreview";
  import {
    buildPayrollDisbursementBatches,
    maskAccount,
    type DisbursementBatch,
    type DisbursementBatchKey,
    type DisbursementQueueRow,
    type DisbursementRowStatus,
  } from "$lib/payroll/disbursementBatcher";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    BankAccountListItem,
    BankLiquidityOverview,
    BonusListItem,
    DeductionListItem,
    EmployeeDirectoryItem,
    PaymentReceiptListItem,
    PayslipListItem,
    PayrollRunListItem,
    ProjectListItem,
    ProjectWorkforceLog,
    TaxRecordListItem,
  } from "$lib/types";

  type LoadMode = "live" | "preview";
  type TransmissionStageKey = "file_generated" | "bank_uploaded" | "processing" | "settled";

  type TransmissionRuntime = {
    fileGeneratedAt: string | null;
    uploadedAt: string | null;
    processingAt: string | null;
    settledAt: string | null;
    stoppedAt: string | null;
  };

  type FailedAuditItem = {
    id: string;
    label: string;
    detail: string;
    amount: number;
    tone: "red" | "orange" | "blue";
    statusLabel: string;
    reference: string;
  };

  type FundingAccountSummary = {
    id: number | null;
    label: string;
    bankName: string;
    accountNumber: string;
    balance: number;
    source: string;
  };

  const MAX_PAGES = 10;
  const AUTO_REFRESH_MS = 60_000;
  const PREVIEW_AUTH_CODE = "284713";

  const PREVIEW_BANK_ACCOUNTS: BankAccountListItem[] = [
    {
      id: 8801,
      account_name: "Main Operations Account",
      bank_name: "Zenith Bank",
      account_number: "0012345678",
      account_type: "current",
      currency: "NGN",
      status: "active",
      current_balance: "24650000.00",
      gl_account: null,
      gl_account_name: "Cash at Bank",
      branch: "Victoria Island",
      created_at: "2026-03-25T09:00:00Z",
    },
    {
      id: 8802,
      account_name: "Project Treasury Reserve",
      bank_name: "GTBank",
      account_number: "0098765432",
      account_type: "current",
      currency: "NGN",
      status: "active",
      current_balance: "12400000.00",
      gl_account: null,
      gl_account_name: "Project Cash Pool",
      branch: "Lekki",
      created_at: "2026-03-25T09:00:00Z",
    },
  ];

  let loading = $state(true);
  let refreshing = $state(false);
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
  let bankAccounts = $state<BankAccountListItem[]>([]);
  let paymentReceipts = $state<PaymentReceiptListItem[]>([]);
  let liquidity = $state<BankLiquidityOverview | null>(null);

  let selectedBatchKey = $state<DisbursementBatchKey>("staff_salaries");
  let queueSearch = $state("");
  let queueStatusFilter = $state<"all" | DisbursementRowStatus>("all");
  let validationFilter = $state<"all" | "valid" | "warning" | "review">("all");
  let postToCostControl = $state(true);
  let apiTransferEnabled = $state(false);

  let bankFilePreviewOpen = $state(false);
  let queueDrawerOpen = $state(false);
  let authDrawerOpen = $state(false);
  let selectedRowId = $state<string | null>(null);
  let otpCode = $state("");
  let otpError = $state("");

  let rowStatusOverrides = $state<Record<string, DisbursementRowStatus>>({});
  let transmissionRuntime = $state<Record<DisbursementBatchKey, TransmissionRuntime>>({
    staff_salaries: createRuntime(),
    site_wages: createRuntime(),
    statutory_remittances: createRuntime(),
  });

  let refreshTimer: ReturnType<typeof setInterval> | null = null;
  const settlementTimers: Partial<Record<DisbursementBatchKey, ReturnType<typeof setTimeout>>> = {};

  function createRuntime(): TransmissionRuntime {
    return {
      fileGeneratedAt: null,
      uploadedAt: null,
      processingAt: null,
      settledAt: null,
      stoppedAt: null,
    };
  }

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

  function formatDateTime(value: string | null | undefined): string {
    const parsed = parseDate(value);
    if (!parsed) return "Not logged";
    return new Intl.DateTimeFormat("en-NG", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(parsed);
  }

  function relativeSyncLabel(date: Date | null): string {
    if (!date) return "Never";
    const delta = Date.now() - date.getTime();
    if (delta < 60_000) return "Just now";
    if (delta < 3_600_000) return `${Math.round(delta / 60_000)} min ago`;
    return `${Math.round(delta / 3_600_000)} hr ago`;
  }

  function fallbackLiquidity(accounts: BankAccountListItem[], pendingOutflow = 0): BankLiquidityOverview {
    const ordered = [...accounts].sort((left, right) => toAmount(right.current_balance) - toAmount(left.current_balance));
    const primary = ordered[0] ?? null;
    return {
      total_cash_on_hand: String(ordered.reduce((sum, item) => sum + toAmount(item.current_balance), 0)),
      account_count: ordered.length,
      primary_account: primary
        ? {
            id: primary.id,
            account_name: primary.account_name,
            bank_name: primary.bank_name,
            current_balance: primary.current_balance,
          }
        : null,
      pending_outflow: String(pendingOutflow),
      pending_run_count: 0,
    };
  }

  function updateRuntime(batchKey: DisbursementBatchKey, patch: Partial<TransmissionRuntime>) {
    transmissionRuntime = {
      ...transmissionRuntime,
      [batchKey]: {
        ...transmissionRuntime[batchKey],
        ...patch,
      },
    };
  }

  function clearSettlementTimer(batchKey: DisbursementBatchKey) {
    const timer = settlementTimers[batchKey];
    if (timer) {
      clearTimeout(timer);
      delete settlementTimers[batchKey];
    }
  }

  function applyStatusToBatch(batch: DisbursementBatch | null, nextStatus: DisbursementRowStatus, allowed: DisbursementRowStatus[]) {
    if (!batch) return;
    const next = { ...rowStatusOverrides };
    for (const row of batch.rows) {
      const current = next[row.id] ?? row.status;
      if (!allowed.includes(current)) continue;
      next[row.id] = nextStatus;
    }
    rowStatusOverrides = next;
  }

  async function loadDisbursements(background = false) {
    if (background) refreshing = true;
    else loading = true;

    const results = await Promise.allSettled([
      fetchAllPages<EmployeeDirectoryItem>("/hr/employee-records/", { page_size: "200" }, MAX_PAGES),
      fetchAllPages<PayrollRunListItem>("/hr/payroll-runs/", { page_size: "200" }, MAX_PAGES),
      fetchAllPages<PayslipListItem>("/hr/payslips/", { page_size: "200" }, MAX_PAGES),
      fetchAllPages<TaxRecordListItem>("/hr/tax-records/", { page_size: "200" }, MAX_PAGES),
      fetchAllPages<DeductionListItem>("/hr/deductions/", { page_size: "200" }, MAX_PAGES),
      fetchAllPages<BonusListItem>("/hr/bonuses/", { page_size: "200" }, MAX_PAGES),
      fetchAllPages<ProjectWorkforceLog>("/projects/field-operations/workforce/", { page_size: "200" }, MAX_PAGES),
      fetchAllPages<ProjectListItem>("/projects/", { page_size: "200", ordering: "name" }, MAX_PAGES),
      fetchAllPages<BankAccountListItem>("/finance/bank-accounts/", { page_size: "200" }, MAX_PAGES),
      fetchAllPages<PaymentReceiptListItem>("/finance/payment-receipts/", { page_size: "200" }, MAX_PAGES),
      api.get<BankLiquidityOverview>("/finance/bank-accounts/liquidity/"),
    ]);

    const liveEmployees = getSettledValue(results[0], []);
    const liveRuns = getSettledValue(results[1], []);
    const livePayslips = getSettledValue(results[2], []);
    const liveTaxRecords = getSettledValue(results[3], []);
    const liveDeductions = getSettledValue(results[4], []);
    const liveBonuses = getSettledValue(results[5], []);
    const liveWorkforce = getSettledValue(results[6], []);
    const liveProjects = getSettledValue(results[7], []);
    const liveBankAccounts = getSettledValue(results[8], []);
    const liveReceipts = getSettledValue(results[9], []);
    const liveLiquidity = getSettledValue(results[10], null);

    const noLivePayrollData =
      liveRuns.length === 0 &&
      livePayslips.length === 0 &&
      liveTaxRecords.length === 0 &&
      liveWorkforce.length === 0;
    const usePreview = noLivePayrollData && isLocalPreviewAllowed();

    dataMode = usePreview ? "preview" : "live";

    if (usePreview) {
      employees = PREVIEW_PAYROLL_DASHBOARD_DATA.employees;
      payrollRuns = PREVIEW_PAYROLL_DASHBOARD_DATA.payrollRuns;
      payslips = PREVIEW_PAYROLL_DASHBOARD_DATA.payslips;
      taxRecords = PREVIEW_PAYROLL_DASHBOARD_DATA.taxRecords;
      deductions = PREVIEW_PAYROLL_DASHBOARD_DATA.deductions;
      bonuses = PREVIEW_PAYROLL_DASHBOARD_DATA.bonuses;
      workforceLogs = PREVIEW_PAYROLL_DASHBOARD_DATA.workforceLogs;
      projects = PREVIEW_PAYROLL_DASHBOARD_DATA.projects;
      bankAccounts = PREVIEW_BANK_ACCOUNTS;
      paymentReceipts = [];
      liquidity = fallbackLiquidity(PREVIEW_BANK_ACCOUNTS, PREVIEW_PAYROLL_DASHBOARD_DATA.payrollRuns.reduce((sum, item) => sum + toAmount(item.total_net), 0));
    } else {
      employees = liveEmployees;
      payrollRuns = liveRuns;
      payslips = livePayslips;
      taxRecords = liveTaxRecords;
      deductions = liveDeductions;
      bonuses = liveBonuses;
      workforceLogs = liveWorkforce;
      projects = liveProjects;
      bankAccounts = liveBankAccounts;
      paymentReceipts = liveReceipts;
      liquidity = liveLiquidity ?? fallbackLiquidity(liveBankAccounts);
    }

    lastSyncedAt = new Date();
    loading = false;
    refreshing = false;
  }

  function chooseFundingAccount(batchKey: DisbursementBatchKey, accounts: BankAccountListItem[], overview: BankLiquidityOverview | null): FundingAccountSummary | null {
    const sorted = [...accounts].sort((left, right) => toAmount(right.current_balance) - toAmount(left.current_balance));
    const defaultAccount = sorted[0] ?? null;

    const picked = batchKey === "statutory_remittances"
      ? sorted.find((item) => item.account_name.toLowerCase().includes("operations")) ?? defaultAccount
      : sorted.find((item) => item.account_name.toLowerCase().includes("operations")) ?? defaultAccount;

    if (picked) {
      return {
        id: picked.id,
        label: `${picked.account_name} • ${picked.bank_name}`,
        bankName: picked.bank_name,
        accountNumber: picked.account_number,
        balance: toAmount(picked.current_balance),
        source: "Finance bank accounts",
      };
    }

    if (overview?.primary_account) {
      return {
        id: overview.primary_account.id,
        label: `${overview.primary_account.account_name} • ${overview.primary_account.bank_name}`,
        bankName: overview.primary_account.bank_name,
        accountNumber: "",
        balance: toAmount(overview.primary_account.current_balance),
        source: "Liquidity overview",
      };
    }

    return null;
  }

  function resolveStatusClass(status: DisbursementRowStatus): string {
    if (status === "settled") return "bg-emerald-100/90 text-emerald-700";
    if (status === "ready") return "bg-emerald-50/90 text-emerald-700";
    if (status === "processing") return "bg-sky-100/90 text-sky-700";
    if (status === "pending") return "bg-orange-100/90 text-orange-700";
    if (status === "hold") return "bg-neutral-200/90 text-neutral-600";
    return "bg-red-100/90 text-red-700";
  }

  function displayStatusLabel(status: DisbursementRowStatus): string {
    if (status === "ready") return "Ready";
    if (status === "pending") return "Pending";
    if (status === "hold") return "Hold";
    if (status === "processing") return "Processing";
    if (status === "settled") return "Settled";
    return "Bounced";
  }

  function validationClass(state: "valid" | "warning" | "review"): string {
    if (state === "valid") return "border-emerald-200/70 bg-emerald-50/80 text-emerald-700";
    if (state === "warning") return "border-orange-200/70 bg-orange-50/80 text-orange-700";
    return "border-sky-200/70 bg-sky-50/85 text-sky-700";
  }

  function batchButtonClass(active: boolean): string {
    return active
      ? "border-neutral-950 bg-neutral-950 text-white shadow-[0_24px_60px_rgba(17,24,39,0.22)]"
      : "border-white/55 bg-white/60 text-neutral-700 shadow-[0_16px_40px_rgba(148,163,184,0.12)] hover:border-neutral-200 hover:bg-white/75";
  }

  function transmissionStage(runtime: TransmissionRuntime, rows: DisbursementQueueRow[]): TransmissionStageKey | null {
    if (!rows.length) return null;
    if (runtime.settledAt || rows.every((row) => row.status === "settled")) return "settled";
    if (runtime.processingAt || rows.some((row) => row.status === "processing")) return "processing";
    if (runtime.uploadedAt) return "bank_uploaded";
    if (runtime.fileGeneratedAt) return "file_generated";
    return null;
  }

  function stepState(step: TransmissionStageKey, active: TransmissionStageKey | null): { active: boolean; complete: boolean } {
    const order: TransmissionStageKey[] = ["file_generated", "bank_uploaded", "processing", "settled"];
    const activeIndex = active ? order.indexOf(active) : -1;
    const currentIndex = order.indexOf(step);
    return {
      active: activeIndex === currentIndex,
      complete: activeIndex > currentIndex,
    };
  }

  function transmissionSegmentClass(step: { active: boolean; complete: boolean }): string {
    if (step.complete) return "bg-emerald-500/95 text-white";
    if (step.active) return "bg-neutral-950 text-white";
    return "bg-white/65 text-neutral-400";
  }

  function openQueueDrawer(rowId: string) {
    selectedRowId = rowId;
    queueDrawerOpen = true;
  }

  function closeQueueDrawer() {
    queueDrawerOpen = false;
    selectedRowId = null;
  }

  function openBankFilePreview() {
    if (!selectedBatch) return;
    updateRuntime(selectedBatch.key, {
      fileGeneratedAt: new Date().toISOString(),
      stoppedAt: null,
    });
    bankFilePreviewOpen = true;
  }

  function closeBankFilePreview() {
    bankFilePreviewOpen = false;
  }

  function confirmBankUpload() {
    if (!selectedBatch) return;
    if (selectedSummary.holdCount > 0 || selectedSummary.reviewCount > 0) {
      toast.error("Batch blocked", "Resolve secure bank sync or manual review rows before marking this upload as ready.");
      return;
    }
    updateRuntime(selectedBatch.key, {
      fileGeneratedAt: transmissionRuntime[selectedBatch.key].fileGeneratedAt ?? new Date().toISOString(),
      uploadedAt: new Date().toISOString(),
      stoppedAt: null,
    });
    toast.success("Upload staged", "Treasury can now treat this batch as uploaded to the bank channel.");
  }

  function openTransferAuth() {
    if (!selectedBatch) return;
    if (!apiTransferEnabled) {
      toast.error("NIBSS/API disabled", "Turn on instant transfer before attempting a live bank push.");
      return;
    }
    if (!canTriggerTransfer) {
      toast.error("Batch not ready", "All pending or hold rows must be cleared before instant transfer can begin.");
      return;
    }
    otpCode = "";
    otpError = "";
    authDrawerOpen = true;
  }

  function closeTransferAuth() {
    authDrawerOpen = false;
    otpCode = "";
    otpError = "";
  }

  function startSettlementTimer(batch: DisbursementBatch) {
    clearSettlementTimer(batch.key);
    settlementTimers[batch.key] = setTimeout(() => {
      applyStatusToBatch(batch, "settled", ["processing", "ready"]);
      updateRuntime(batch.key, {
        settledAt: new Date().toISOString(),
        processingAt: null,
      });
      toast.success(
        "Batch settled",
        postToCostControl
          ? "Payments were marked as settled and cost-control posting is ready."
          : "Payments were marked as settled. Ledger sync is still turned off."
      );
    }, 2200);
  }

  function confirmTransfer() {
    if (!selectedBatch) return;
    if (dataMode !== "preview" && selectedSummary.reviewCount > 0) {
      otpError = "Secure bank fields are not yet exposed by the live HR registry.";
      return;
    }
    if (otpCode !== PREVIEW_AUTH_CODE) {
      otpError = `Use ${PREVIEW_AUTH_CODE} to simulate the finance OTP handoff.`;
      return;
    }

    updateRuntime(selectedBatch.key, {
      fileGeneratedAt: transmissionRuntime[selectedBatch.key].fileGeneratedAt ?? new Date().toISOString(),
      uploadedAt: transmissionRuntime[selectedBatch.key].uploadedAt ?? new Date().toISOString(),
      processingAt: new Date().toISOString(),
      settledAt: null,
      stoppedAt: null,
    });
    applyStatusToBatch(selectedBatch, "processing", ["ready"]);
    closeTransferAuth();
    startSettlementTimer(selectedBatch);
    toast.success("Transfer triggered", "Payroll disbursement moved into processing and settlement tracking has started.");
  }

  function emergencyStop() {
    if (!selectedBatch) return;
    clearSettlementTimer(selectedBatch.key);
    applyStatusToBatch(selectedBatch, "hold", ["processing", "ready"]);
    updateRuntime(selectedBatch.key, {
      processingAt: null,
      stoppedAt: new Date().toISOString(),
      settledAt: null,
    });
    toast.error("Batch halted", "The batch is now on hold until the disbursement queue is reviewed.");
  }

  onMount(() => {
    void loadDisbursements();
    refreshTimer = setInterval(() => {
      void loadDisbursements(true);
    }, AUTO_REFRESH_MS);

    return () => {
      if (refreshTimer) clearInterval(refreshTimer);
      for (const timer of Object.values(settlementTimers)) {
        if (timer) clearTimeout(timer);
      }
    };
  });

  const disbursementBuild = $derived.by(() =>
    buildPayrollDisbursementBatches({
      previewMode: dataMode === "preview",
      employees,
      payrollRuns,
      payslips,
      taxRecords,
      deductions,
      bonuses,
      workforceLogs,
      projects,
    })
  );

  const resolvedBatches = $derived.by(() =>
    disbursementBuild.batches.map((batch) => ({
      ...batch,
      rows: batch.rows.map((row) => {
        const nextStatus = rowStatusOverrides[row.id] ?? row.status;
        return {
          ...row,
          status: nextStatus,
          statusLabel: displayStatusLabel(nextStatus),
        };
      }),
    }))
  );

  function summarizeRows(rows: DisbursementQueueRow[]) {
    const summary = {
      total: rows.reduce((sum, row) => sum + row.netAmount, 0),
      readyCount: 0,
      pendingCount: 0,
      holdCount: 0,
      processingCount: 0,
      settledCount: 0,
      bouncedCount: 0,
      reviewCount: 0,
      warningCount: 0,
      capitalizedTotal: rows.reduce((sum, row) => sum + row.capitalizedAmount, 0),
      expensedTotal: rows.reduce((sum, row) => sum + row.expensedAmount, 0),
    };

    for (const row of rows) {
      if (row.status === "ready") summary.readyCount += 1;
      if (row.status === "pending") summary.pendingCount += 1;
      if (row.status === "hold") summary.holdCount += 1;
      if (row.status === "processing") summary.processingCount += 1;
      if (row.status === "settled") summary.settledCount += 1;
      if (row.status === "bounced") summary.bouncedCount += 1;
      if (row.validationState === "review") summary.reviewCount += 1;
      if (row.validationState === "warning") summary.warningCount += 1;
    }

    return summary;
  }

  const selectedBatch = $derived.by(() => resolvedBatches.find((batch) => batch.key === selectedBatchKey) ?? resolvedBatches[0] ?? null);
  const selectedSummary = $derived.by(() => summarizeRows(selectedBatch?.rows ?? []));
  const selectedRuntime = $derived.by(() => transmissionRuntime[selectedBatchKey]);
  const currentStage = $derived.by(() => transmissionStage(selectedRuntime, selectedBatch?.rows ?? []));
  const selectedFundingAccount = $derived.by(() => chooseFundingAccount(selectedBatchKey, bankAccounts, liquidity));
  const fundingGap = $derived.by(() => Math.max(0, selectedSummary.total - (selectedFundingAccount?.balance ?? 0)));
  const fundingCoverage = $derived.by(() =>
    selectedSummary.total > 0 ? Math.min(100, ((selectedFundingAccount?.balance ?? 0) / selectedSummary.total) * 100) : 0
  );
  const canTriggerTransfer = $derived.by(() =>
    Boolean(
      selectedBatch &&
      selectedBatch.rows.length > 0 &&
      selectedSummary.pendingCount === 0 &&
      selectedSummary.holdCount === 0 &&
      selectedSummary.reviewCount === 0 &&
      transmissionRuntime[selectedBatchKey].uploadedAt
    )
  );
  const bankFileRows = $derived.by(() =>
    (selectedBatch?.rows ?? []).map((row) => ({
      employeeName: row.beneficiaryName,
      employeeId: row.employeeCode ?? row.beneficiarySecondary,
      amount: row.netAmount,
      narration: `${disbursementBuild.reportingPeriodLabel} ${selectedBatch?.label ?? "Payroll"} disbursement`,
      projectName: row.projectName,
      runName: row.runName,
      bankName: row.banking.bankName,
      accountNumber: row.banking.accountNumber,
      accountType: row.banking.paymentMethod,
      bankCode: row.banking.bankCode,
    }))
  );

  const filteredRows = $derived.by(() => {
    const rows = selectedBatch?.rows ?? [];
    const query = queueSearch.trim().toLowerCase();
    return rows.filter((row) => {
      if (queueStatusFilter !== "all" && row.status !== queueStatusFilter) return false;
      if (validationFilter !== "all" && row.validationState !== validationFilter) return false;
      if (!query) return true;
      return (
        row.beneficiaryName.toLowerCase().includes(query) ||
        row.projectCode.toLowerCase().includes(query) ||
        row.projectName.toLowerCase().includes(query) ||
        row.roleLabel.toLowerCase().includes(query) ||
        row.validationLabel.toLowerCase().includes(query)
      );
    });
  });

  const selectedRow = $derived.by(() => {
    const rows = resolvedBatches.flatMap((batch) => batch.rows);
    return rows.find((row) => row.id === selectedRowId) ?? null;
  });

  const paymentHealth = $derived.by(() => {
    if (selectedSummary.holdCount > 0 || selectedSummary.reviewCount > 0) {
      return {
        title: "Invalid account numbers found",
        subtitle: `${selectedSummary.holdCount + selectedSummary.reviewCount} line${selectedSummary.holdCount + selectedSummary.reviewCount === 1 ? "" : "s"} need secure registry release or manual review.`,
        tone: "orange",
      };
    }
    if (selectedSummary.warningCount > 0 || selectedSummary.pendingCount > 0) {
      return {
        title: "Manual review required",
        subtitle: `${selectedSummary.warningCount + selectedSummary.pendingCount} line${selectedSummary.warningCount + selectedSummary.pendingCount === 1 ? "" : "s"} still carry warnings or pending approvals.`,
        tone: "blue",
      };
    }
    return {
      title: "All accounts validated",
      subtitle: "Queue is clean and ready for upload or settlement.",
      tone: "mint",
    };
  });

  const workflowSteps = $derived.by(() => {
    const steps: Array<{ key: TransmissionStageKey; label: string; caption: string; time: string }> = [
      {
        key: "file_generated",
        label: "File Generated",
        caption: "Bank-ready schedule staged",
        time: formatDateTime(selectedRuntime.fileGeneratedAt),
      },
      {
        key: "bank_uploaded",
        label: "Bank Uploaded",
        caption: "Portal upload acknowledged",
        time: formatDateTime(selectedRuntime.uploadedAt),
      },
      {
        key: "processing",
        label: "Processing",
        caption: "Transfer engine or manual bank flow",
        time: formatDateTime(selectedRuntime.processingAt),
      },
      {
        key: "settled",
        label: "Settled",
        caption: postToCostControl ? "Ready to post to cost control" : "Awaiting ledger sync",
        time: formatDateTime(selectedRuntime.settledAt),
      },
    ];
    return steps.map((step) => ({
      ...step,
      state: stepState(step.key, currentStage),
    }));
  });

  const projectCapRows = $derived.by(() => {
    const grouped = new Map<string, { projectCode: string; amount: number; capitalized: number; expensed: number; budget: number }>();
    for (const row of selectedBatch?.rows ?? []) {
      const key = `${row.projectCode}:${row.projectName}`;
      const current = grouped.get(key) ?? {
        projectCode: row.projectCode,
        amount: 0,
        capitalized: 0,
        expensed: 0,
        budget: row.projectBudget,
      };
      current.amount += row.netAmount;
      current.capitalized += row.capitalizedAmount;
      current.expensed += row.expensedAmount;
      current.budget = Math.max(current.budget, row.projectBudget);
      grouped.set(key, current);
    }

    return [...grouped.entries()]
      .map(([name, payload]) => ({
        name: name.split(":")[1],
        projectCode: payload.projectCode,
        amount: payload.amount,
        capitalized: payload.capitalized,
        expensed: payload.expensed,
        budget: payload.budget,
        ratio: payload.budget > 0 ? (payload.amount / payload.budget) * 100 : 0,
      }))
      .sort((left, right) => right.amount - left.amount);
  });

  const capitalizedShare = $derived.by(() =>
    selectedSummary.total > 0 ? (selectedSummary.capitalizedTotal / selectedSummary.total) * 100 : 0
  );
  const expensedShare = $derived.by(() =>
    selectedSummary.total > 0 ? (selectedSummary.expensedTotal / selectedSummary.total) * 100 : 0
  );

  const failedAuditItems = $derived.by(() => {
    const items: FailedAuditItem[] = [];

    for (const row of selectedBatch?.rows ?? []) {
      if (row.status !== "hold" && row.status !== "bounced" && row.validationState !== "review") continue;
      items.push({
        id: `queue-${row.id}`,
        label: row.beneficiaryName,
        detail: row.validationLabel,
        amount: row.netAmount,
        tone: row.status === "bounced" ? "red" : "blue",
        statusLabel: row.status === "bounced" ? "Bounced" : "Needs review",
        reference: row.projectCode,
      });
    }

    for (const receipt of paymentReceipts.filter((item) => item.status === "failed" || item.status === "reversed")) {
      items.push({
        id: `receipt-${receipt.id}`,
        label: receipt.receipt_number,
        detail: receipt.vendor_name ?? "Finance payment receipt",
        amount: toAmount(receipt.amount),
        tone: receipt.status === "failed" ? "red" : "orange",
        statusLabel: receipt.status === "failed" ? "Failed" : "Reversed",
        reference: receipt.transaction_reference,
      });
    }

    return items.slice(0, 8);
  });

  const totalMonthlyOutflow = $derived.by(() =>
    resolvedBatches.reduce((sum, batch) => sum + batch.total, 0)
  );
  const totalHeadcount = $derived.by(() =>
    selectedBatch?.rows.reduce((sum, row) => sum + row.headcount, 0) ?? 0
  );
</script>

<svelte:head>
  <title>Payroll Disbursements</title>
</svelte:head>

<div class="space-y-6">
  <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-[#e2557b]">Payroll</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800" style="font-family: 'Raleway', sans-serif;">Disbursements</h1>
      <p class="mt-2 max-w-3xl text-sm leading-6 text-neutral-600">
        Move payroll from calculated liability into bank-ready instructions, settlement tracking, and post-payment cost control.
      </p>
    </div>

    <div class="flex flex-wrap items-center gap-3">
      <button
        type="button"
        class="inline-flex items-center justify-center rounded-2xl border border-neutral-200 bg-white px-4 py-3 text-sm font-semibold text-neutral-700 transition hover:border-neutral-300 hover:bg-neutral-50"
        onclick={() => loadDisbursements(true)}
        disabled={refreshing}
      >
        {refreshing ? "Syncing..." : "Sync Queue"}
      </button>
      <button
        type="button"
        class="inline-flex items-center justify-center rounded-2xl bg-neutral-950 px-4 py-3 text-sm font-semibold text-white transition hover:bg-neutral-800"
        onclick={openBankFilePreview}
        disabled={!selectedBatch || selectedBatch.rows.length === 0}
      >
        Preview Bank File
      </button>
    </div>
  </div>

  {#if loading}
    <div class="rounded-[32px] border border-white/45 bg-white/70 p-10 shadow-[0_32px_90px_rgba(148,163,184,0.18)] backdrop-blur-xl">
      <div class="flex flex-col items-center justify-center gap-4 py-16">
        <div class="h-10 w-10 rounded-full border-2 border-neutral-200 border-t-neutral-900 animate-spin"></div>
        <p class="text-sm text-neutral-500">Loading disbursement command center...</p>
      </div>
    </div>
  {:else}
    <div class="grid gap-4 xl:grid-cols-4">
      <div class="rounded-[28px] border border-white/50 bg-[linear-gradient(180deg,rgba(255,255,255,0.86),rgba(249,247,251,0.76))] p-5 shadow-[0_24px_70px_rgba(148,163,184,0.16)] backdrop-blur-xl">
        <p class="text-xs font-semibold uppercase tracking-[0.24em] text-neutral-400">Batch Total</p>
        <p class="mt-4 text-3xl font-bold tracking-tight text-neutral-950">{formatCurrency(selectedSummary.total)}</p>
        <p class="mt-2 text-sm text-neutral-500">
          {selectedBatch?.label ?? "No batch selected"} in {disbursementBuild.reportingPeriodLabel}
        </p>
      </div>

      <div class="rounded-[28px] border border-white/50 bg-[linear-gradient(180deg,rgba(255,255,255,0.86),rgba(247,249,250,0.76))] p-5 shadow-[0_24px_70px_rgba(148,163,184,0.16)] backdrop-blur-xl">
        <p class="text-xs font-semibold uppercase tracking-[0.24em] text-neutral-400">Funding Account</p>
        <p class="mt-4 text-xl font-semibold tracking-tight text-neutral-950">{selectedFundingAccount?.label ?? "No linked treasury account"}</p>
        <p class="mt-2 text-sm text-neutral-500">
          Balance {formatCurrency(selectedFundingAccount?.balance ?? 0)}
          {#if fundingGap > 0}
            <span class="text-orange-600"> • Gap {formatCurrency(fundingGap)}</span>
          {/if}
        </p>
        <div class="mt-4 h-2 overflow-hidden rounded-full bg-neutral-200">
          <div class="h-full rounded-full bg-emerald-500 transition-all duration-300" style={`width:${fundingCoverage}%`}></div>
        </div>
      </div>

      <div class="rounded-[28px] border border-white/50 bg-[linear-gradient(180deg,rgba(255,255,255,0.86),rgba(244,247,252,0.74))] p-5 shadow-[0_24px_70px_rgba(148,163,184,0.16)] backdrop-blur-xl">
        <p class="text-xs font-semibold uppercase tracking-[0.24em] text-neutral-400">Transmission Status</p>
        <div class="mt-4 flex items-center gap-2">
          {#each workflowSteps as step}
            <div class={`flex-1 rounded-full px-3 py-2 text-center text-[11px] font-semibold uppercase tracking-[0.18em] ${transmissionSegmentClass(step.state)}`}>
              {step.label}
            </div>
          {/each}
        </div>
        <p class="mt-4 text-sm text-neutral-500">
          {selectedRuntime.stoppedAt ? `Emergency stop at ${formatDateTime(selectedRuntime.stoppedAt)}` : currentStage ? `${currentStage.replaceAll("_", " ")} is the current batch stage.` : "Generate the bank file to begin transmission tracking."}
        </p>
      </div>

      <div class={`rounded-[28px] border p-5 shadow-[0_24px_70px_rgba(148,163,184,0.16)] backdrop-blur-xl ${
        paymentHealth.tone === "mint"
          ? "border-emerald-200/70 bg-emerald-50/80"
          : paymentHealth.tone === "orange"
            ? "border-orange-200/70 bg-orange-50/80"
            : "border-sky-200/70 bg-sky-50/85"
      }`}>
        <div class="flex items-center gap-3">
          <span class={`h-2.5 w-2.5 rounded-full ${paymentHealth.tone === "mint" ? "bg-emerald-500 pulse-dot" : paymentHealth.tone === "orange" ? "bg-orange-500" : "bg-sky-500 blur-[1px]"}`}></span>
          <p class="text-xs font-semibold uppercase tracking-[0.24em] text-neutral-500">Payment Health</p>
        </div>
        <p class="mt-4 text-2xl font-bold tracking-tight text-neutral-950">{paymentHealth.title}</p>
        <p class="mt-2 text-sm leading-6 text-neutral-600">{paymentHealth.subtitle}</p>
      </div>
    </div>

    <div class="grid gap-6 lg:grid-cols-[280px,minmax(0,1fr)]">
      <aside class="space-y-4">
        <div class="rounded-[30px] border border-white/50 bg-[linear-gradient(180deg,rgba(255,255,255,0.82),rgba(245,247,250,0.72))] p-5 shadow-[0_24px_70px_rgba(148,163,184,0.16)] backdrop-blur-xl">
          <p class="text-xs font-semibold uppercase tracking-[0.24em] text-neutral-400">Batch Selection</p>
          <div class="mt-4 space-y-3">
            {#each resolvedBatches as batch}
              {@const batchSummary = summarizeRows(batch.rows)}
              <button
                type="button"
                class={`w-full rounded-[24px] border p-4 text-left transition ${batchButtonClass(batch.key === selectedBatchKey)}`}
                onclick={() => (selectedBatchKey = batch.key)}
              >
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <p class="text-sm font-semibold tracking-tight">{batch.label}</p>
                    <p class={`mt-1 text-xs leading-5 ${batch.key === selectedBatchKey ? "text-white/70" : "text-neutral-500"}`}>
                      {batch.description}
                    </p>
                  </div>
                  <span class={`inline-flex rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] ${batch.key === selectedBatchKey ? "bg-white/15 text-white" : "bg-neutral-100 text-neutral-600"}`}>
                    {batch.cadence}
                  </span>
                </div>
                <div class={`mt-4 flex items-center justify-between text-xs ${batch.key === selectedBatchKey ? "text-white/80" : "text-neutral-500"}`}>
                  <span>{batch.rows.length} lines</span>
                  <span>{formatCurrency(batchSummary.total)}</span>
                </div>
              </button>
            {/each}
          </div>
        </div>

        <div class="rounded-[30px] border border-white/45 bg-white/68 p-5 shadow-[0_24px_70px_rgba(148,163,184,0.16)] backdrop-blur-xl">
          <p class="text-xs font-semibold uppercase tracking-[0.24em] text-neutral-400">Liquidity Snapshot</p>
          <p class="mt-4 text-2xl font-bold tracking-tight text-neutral-950">{formatCurrency(toAmount(liquidity?.total_cash_on_hand))}</p>
          <p class="mt-2 text-sm text-neutral-500">{liquidity?.account_count ?? 0} treasury account{liquidity?.account_count === 1 ? "" : "s"} online.</p>
          <div class="mt-4 rounded-2xl border border-dashed border-neutral-300 bg-neutral-50/80 p-4">
            <p class="text-sm font-medium text-neutral-800">Monthly labor outflow</p>
            <p class="mt-2 text-lg font-semibold text-neutral-950">{formatCurrency(totalMonthlyOutflow)}</p>
            <p class="mt-1 text-xs text-neutral-500">{totalHeadcount} heads flowing through the active batch.</p>
          </div>
        </div>
      </aside>

      <div class="space-y-6">
        <div class="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
          <section class="rounded-[32px] border border-white/50 bg-[linear-gradient(180deg,rgba(255,255,255,0.84),rgba(246,248,251,0.76))] p-6 shadow-[0_28px_80px_rgba(148,163,184,0.16)] backdrop-blur-xl">
            <div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <p class="text-xs font-semibold uppercase tracking-[0.28em] text-neutral-400">Payroll And Bank Workflow</p>
                <h2 class="mt-3 text-xl font-semibold tracking-tight text-neutral-950">Transmission Timeline</h2>
                <p class="mt-2 text-sm leading-6 text-neutral-600">
                  Follow the approved payroll batch from file generation through upload, processing, and final reconciliation.
                </p>
              </div>
              <div class="rounded-2xl border border-dashed border-neutral-300 bg-white/70 px-4 py-3 text-sm text-neutral-600">
                Last synced {relativeSyncLabel(lastSyncedAt)}
              </div>
            </div>

            <div class="mt-6 grid gap-3 xl:grid-cols-4">
              {#each workflowSteps as step}
                <div class={`rounded-[24px] border p-4 ${step.state.complete ? "border-emerald-200 bg-emerald-50/75" : step.state.active ? "border-neutral-900 bg-neutral-950 text-white" : "border-neutral-200 bg-white/80 text-neutral-800"}`}>
                  <p class={`text-[11px] font-semibold uppercase tracking-[0.22em] ${step.state.active ? "text-white/60" : "text-neutral-400"}`}>{step.label}</p>
                  <p class={`mt-3 text-sm leading-6 ${step.state.active ? "text-white/85" : "text-neutral-600"}`}>{step.caption}</p>
                  <p class={`mt-4 text-xs ${step.state.active ? "text-white/60" : "text-neutral-400"}`}>{step.time}</p>
                </div>
              {/each}
            </div>

            <div class="mt-6 rounded-[24px] border border-white/50 bg-white/60 p-5">
              <div class="flex items-center justify-between gap-4">
                <div>
                  <p class="text-xs font-semibold uppercase tracking-[0.22em] text-neutral-400">Post-Payment Audit</p>
                  <p class="mt-2 text-sm leading-6 text-neutral-600">
                    Settlement proof can roll into employee payroll profiles and labor cost control once the batch completes.
                  </p>
                </div>
                <label class="inline-flex items-center gap-3 rounded-full border border-neutral-200 bg-white px-3 py-2 text-sm font-medium text-neutral-700">
                  <span>Post to Cost Control</span>
                  <button
                    type="button"
                    class={`relative h-7 w-12 rounded-full transition ${postToCostControl ? "bg-emerald-500" : "bg-neutral-300"}`}
                    onclick={() => (postToCostControl = !postToCostControl)}
                    aria-label="Toggle ledger sync"
                  >
                    <span class={`absolute top-1 h-5 w-5 rounded-full bg-white shadow-sm transition ${postToCostControl ? "left-6" : "left-1"}`}></span>
                  </button>
                </label>
              </div>
            </div>
          </section>

          <section class="rounded-[32px] border border-white/50 bg-[linear-gradient(180deg,rgba(255,255,255,0.84),rgba(250,248,251,0.76))] p-6 shadow-[0_28px_80px_rgba(148,163,184,0.16)] backdrop-blur-xl">
            <p class="text-xs font-semibold uppercase tracking-[0.28em] text-neutral-400">Bank Link And File Generation</p>
            <h2 class="mt-3 text-xl font-semibold tracking-tight text-neutral-950">Automation Control</h2>
            <p class="mt-2 text-sm leading-6 text-neutral-600">
              Generate the bank-ready schedule, confirm upload, or simulate instant transfer once every row is clean.
            </p>

            <div class="mt-5 space-y-3">
              <button
                type="button"
                class="flex w-full items-center justify-between rounded-[24px] border border-neutral-200 bg-white/80 px-4 py-4 text-left transition hover:border-neutral-300"
                onclick={openBankFilePreview}
              >
                <span>
                  <span class="block text-sm font-semibold text-neutral-950">Open Print-Friendly Schedule</span>
                  <span class="mt-1 block text-xs text-neutral-500">Use this for manual sign-off and treasury authorization.</span>
                </span>
                <span class="text-sm font-semibold text-emerald-700">Preview</span>
              </button>

              <button
                type="button"
                class="flex w-full items-center justify-between rounded-[24px] border border-neutral-200 bg-white/80 px-4 py-4 text-left transition hover:border-neutral-300"
                onclick={confirmBankUpload}
              >
                <span>
                  <span class="block text-sm font-semibold text-neutral-950">Confirm Bank Upload</span>
                  <span class="mt-1 block text-xs text-neutral-500">Moves the transmission bar into the bank uploaded stage.</span>
                </span>
                <span class="text-sm font-semibold text-neutral-700">Advance</span>
              </button>
            </div>

            <div class="mt-5 rounded-[24px] border border-white/60 bg-white/65 p-5">
              <div class="flex items-center justify-between gap-4">
                <div>
                  <p class="text-xs font-semibold uppercase tracking-[0.22em] text-neutral-400">NIBSS / API Toggle</p>
                  <p class="mt-2 text-sm leading-6 text-neutral-600">Enable automated transfer mode for gateway-driven disbursement runs.</p>
                </div>
                <button
                  type="button"
                  class={`relative h-7 w-12 rounded-full transition ${apiTransferEnabled ? "bg-emerald-500" : "bg-neutral-300"}`}
                  onclick={() => (apiTransferEnabled = !apiTransferEnabled)}
                  aria-label="Toggle instant transfer"
                >
                  <span class={`absolute top-1 h-5 w-5 rounded-full bg-white shadow-sm transition ${apiTransferEnabled ? "left-6" : "left-1"}`}></span>
                </button>
              </div>

              <div class="mt-5 grid gap-3">
                <button
                  type="button"
                  class="inline-flex items-center justify-center rounded-2xl bg-emerald-500 px-4 py-3 text-sm font-semibold text-white transition hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-45"
                  onclick={openTransferAuth}
                  disabled={!canTriggerTransfer}
                >
                  Trigger Instant Transfer
                </button>

                <button
                  type="button"
                  class="inline-flex items-center justify-center rounded-2xl border border-red-200 bg-red-50/80 px-4 py-3 text-sm font-semibold text-red-700 transition hover:bg-red-100"
                  onclick={emergencyStop}
                >
                  Emergency Stop
                </button>
              </div>
            </div>
          </section>
        </div>

        <BankExport
          rows={bankFileRows}
          currencyCode={currency.config.code || "NGN"}
          periodLabel={`${disbursementBuild.reportingPeriodLabel} ${selectedBatch?.label ?? "payroll"}`}
          previewMode={dataMode === "preview"}
        />

        <section class="rounded-[32px] border border-white/50 bg-[linear-gradient(180deg,rgba(255,255,255,0.86),rgba(247,248,251,0.76))] p-6 shadow-[0_28px_80px_rgba(148,163,184,0.16)] backdrop-blur-xl">
          <div class="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.28em] text-neutral-400">Disbursement Queue</p>
              <h2 class="mt-3 text-xl font-semibold tracking-tight text-neutral-950">Master Verification List</h2>
              <p class="mt-2 text-sm leading-6 text-neutral-600">
                Final review layer before funds are sent. Click a row for drawer detail and payout notes.
              </p>
            </div>

            <div class="flex flex-col gap-3 sm:flex-row">
              <input
                type="search"
                bind:value={queueSearch}
                placeholder="Search beneficiary, project, or issue..."
                class="w-full min-w-[240px] rounded-2xl border border-neutral-200 bg-white/85 px-4 py-3 text-sm text-neutral-700 focus:border-neutral-400 focus:outline-none"
              />
              <select
                bind:value={queueStatusFilter}
                class="rounded-2xl border border-neutral-200 bg-white/85 px-4 py-3 text-sm text-neutral-700 focus:border-neutral-400 focus:outline-none"
              >
                <option value="all">All statuses</option>
                <option value="ready">Ready</option>
                <option value="pending">Pending</option>
                <option value="hold">Hold</option>
                <option value="processing">Processing</option>
                <option value="settled">Settled</option>
                <option value="bounced">Bounced</option>
              </select>
              <select
                bind:value={validationFilter}
                class="rounded-2xl border border-neutral-200 bg-white/85 px-4 py-3 text-sm text-neutral-700 focus:border-neutral-400 focus:outline-none"
              >
                <option value="all">All validations</option>
                <option value="valid">Validated</option>
                <option value="warning">Warning</option>
                <option value="review">Review</option>
              </select>
            </div>
          </div>

          <div class="mt-6 overflow-hidden rounded-[28px] border border-neutral-200/80 bg-white/78">
            <table class="min-w-full text-sm">
              <thead class="bg-neutral-50/90 text-[11px] uppercase tracking-[0.22em] text-neutral-400">
                <tr>
                  <th class="px-4 py-3 text-left font-semibold">Employee / Vendor</th>
                  <th class="px-4 py-3 text-left font-semibold">Project Code</th>
                  <th class="px-4 py-3 text-right font-semibold">Net Amount</th>
                  <th class="px-4 py-3 text-left font-semibold">Bank Details</th>
                  <th class="px-4 py-3 text-left font-semibold">Validation</th>
                  <th class="px-4 py-3 text-left font-semibold">Status</th>
                </tr>
              </thead>
              <tbody>
                {#each filteredRows as row}
                  <tr
                    class={`cursor-pointer border-t border-neutral-200/70 transition hover:bg-neutral-50/85 ${row.validationState === "review" ? "bg-[radial-gradient(circle_at_left,rgba(239,68,68,0.12),transparent_48%)]" : ""}`}
                    onclick={() => openQueueDrawer(row.id)}
                  >
                    <td class="px-4 py-4">
                      <p class="font-medium text-neutral-950">{row.beneficiaryName}</p>
                      <p class="mt-1 text-xs text-neutral-500">{row.roleLabel} • {row.beneficiarySecondary}</p>
                    </td>
                    <td class="px-4 py-4">
                      <p class="font-semibold text-neutral-900">{row.projectCode}</p>
                      <p class="mt-1 text-xs text-neutral-500">{row.projectName}</p>
                    </td>
                    <td class="px-4 py-4 text-right font-bold text-neutral-950">{formatCurrency(row.netAmount)}</td>
                    <td class="px-4 py-4">
                      <p class="font-medium text-neutral-800">{row.banking.bankName || "Secure registry pending"}</p>
                      <p class="mt-1 text-xs text-neutral-500">
                        {row.banking.accountNumber ? maskAccount(row.banking.accountNumber) : row.banking.paymentMethod}
                      </p>
                    </td>
                    <td class="px-4 py-4">
                      <span class={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold ${validationClass(row.validationState)}`}>
                        {row.validationLabel}
                      </span>
                    </td>
                    <td class="px-4 py-4">
                      <span class={`inline-flex rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] ${resolveStatusClass(row.status)}`}>
                        {row.status}
                      </span>
                    </td>
                  </tr>
                {/each}
                {#if filteredRows.length === 0}
                  <tr>
                    <td colspan="6" class="px-4 py-12 text-center text-sm text-neutral-500">
                      No queue lines match the current search or filter state.
                    </td>
                  </tr>
                {/if}
              </tbody>
            </table>
          </div>
        </section>

        <div class="grid gap-6 xl:grid-cols-[0.95fr,1.05fr]">
          <section class="rounded-[32px] border border-white/50 bg-[linear-gradient(180deg,rgba(255,255,255,0.86),rgba(250,247,246,0.76))] p-6 shadow-[0_28px_80px_rgba(148,163,184,0.16)] backdrop-blur-xl">
            <p class="text-xs font-semibold uppercase tracking-[0.28em] text-neutral-400">Failed Transaction Log</p>
            <h2 class="mt-3 text-xl font-semibold tracking-tight text-neutral-950">Quick Correction Queue</h2>
            <div class="mt-5 space-y-3">
              {#each failedAuditItems as item}
                <div class={`rounded-[24px] border p-4 ${item.tone === "red" ? "border-red-200 bg-red-50/80" : item.tone === "orange" ? "border-orange-200 bg-orange-50/80" : "border-sky-200 bg-sky-50/85"}`}>
                  <div class="flex items-start justify-between gap-4">
                    <div>
                      <p class="text-sm font-semibold text-neutral-950">{item.label}</p>
                      <p class="mt-1 text-xs text-neutral-500">{item.reference}</p>
                    </div>
                    <span class={`inline-flex rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] ${item.tone === "red" ? "bg-red-100 text-red-700" : item.tone === "orange" ? "bg-orange-100 text-orange-700" : "bg-sky-100 text-sky-700"}`}>
                      {item.statusLabel}
                    </span>
                  </div>
                  <p class="mt-3 text-sm leading-6 text-neutral-600">{item.detail}</p>
                  <p class="mt-3 text-sm font-semibold text-neutral-900">{formatCurrency(item.amount)}</p>
                </div>
              {/each}
              {#if failedAuditItems.length === 0}
                <div class="rounded-[24px] border border-dashed border-neutral-300 bg-neutral-50/80 p-6 text-sm text-neutral-500">
                  No failed or bounced entries are active in this batch right now.
                </div>
              {/if}
            </div>
          </section>

          <section class="rounded-[32px] border border-white/50 bg-[linear-gradient(180deg,rgba(255,255,255,0.86),rgba(245,248,250,0.74))] p-6 shadow-[0_28px_80px_rgba(148,163,184,0.16)] backdrop-blur-xl">
            <p class="text-xs font-semibold uppercase tracking-[0.28em] text-neutral-400">Project Labor Cap</p>
            <h2 class="mt-3 text-xl font-semibold tracking-tight text-neutral-950">Capitalized Vs Expensed</h2>
            <p class="mt-2 text-sm leading-6 text-neutral-600">
              Track how much of this disbursement adds project value versus what lands as HQ or statutory overhead.
            </p>

            <div class="mt-6 grid gap-4 lg:grid-cols-[220px,minmax(0,1fr)]">
              <div class="rounded-[28px] border border-white/60 bg-white/55 p-5 shadow-[0_18px_50px_rgba(148,163,184,0.14)] backdrop-blur-xl">
                <div class="relative mx-auto h-44 w-44">
                  <div
                    class="absolute inset-0 rounded-full"
                    style={`background: conic-gradient(#10b981 0 ${capitalizedShare}%, #111827 ${capitalizedShare}% ${Math.min(100, capitalizedShare + expensedShare)}%, #e5e7eb 0 100%);`}
                  ></div>
                  <div class="absolute inset-5 rounded-full border border-white/60 bg-white/85 backdrop-blur-xl"></div>
                  <div class="absolute inset-0 flex flex-col items-center justify-center text-center">
                    <p class="text-[11px] font-semibold uppercase tracking-[0.22em] text-neutral-400">Capitalized</p>
                    <p class="mt-2 text-2xl font-bold tracking-tight text-neutral-950">{capitalizedShare.toFixed(0)}%</p>
                    <p class="mt-1 text-xs text-neutral-500">{formatCurrency(selectedSummary.capitalizedTotal)}</p>
                  </div>
                </div>
                <div class="mt-5 grid gap-3">
                  <div class="rounded-2xl border border-emerald-200/70 bg-emerald-50/80 px-4 py-3">
                    <p class="text-xs uppercase tracking-[0.2em] text-emerald-600">Capitalized</p>
                    <p class="mt-2 text-lg font-semibold text-emerald-950">{formatCurrency(selectedSummary.capitalizedTotal)}</p>
                  </div>
                  <div class="rounded-2xl border border-neutral-200 bg-neutral-50/85 px-4 py-3">
                    <p class="text-xs uppercase tracking-[0.2em] text-neutral-500">Expensed</p>
                    <p class="mt-2 text-lg font-semibold text-neutral-950">{formatCurrency(selectedSummary.expensedTotal)}</p>
                  </div>
                </div>
              </div>

              <div class="space-y-3">
                {#each projectCapRows as item}
                  <div class="rounded-[24px] border border-white/60 bg-white/62 p-4 shadow-[0_16px_40px_rgba(148,163,184,0.12)] backdrop-blur-xl">
                    <div class="flex items-start justify-between gap-4">
                      <div>
                        <p class="text-sm font-semibold text-neutral-950">{item.name}</p>
                        <p class="mt-1 text-xs text-neutral-500">{item.projectCode}</p>
                      </div>
                      <div class="text-right">
                        <p class="text-sm font-semibold text-neutral-950">{formatCurrency(item.amount)}</p>
                        <p class="mt-1 text-xs text-neutral-500">{item.ratio.toFixed(2)}% of budget</p>
                      </div>
                    </div>
                    <div class="mt-4 h-2 overflow-hidden rounded-full bg-neutral-200">
                      <div class="h-full rounded-full bg-emerald-500" style={`width:${Math.min(100, item.ratio)}%`}></div>
                    </div>
                    <div class="mt-4 flex flex-wrap gap-2 text-xs text-neutral-500">
                      <span class="rounded-full bg-emerald-50 px-3 py-1 text-emerald-700">Capitalized {formatCurrency(item.capitalized)}</span>
                      <span class="rounded-full bg-neutral-100 px-3 py-1 text-neutral-600">Expensed {formatCurrency(item.expensed)}</span>
                    </div>
                  </div>
                {/each}
                {#if projectCapRows.length === 0}
                  <div class="rounded-[24px] border border-dashed border-neutral-300 bg-neutral-50/80 p-6 text-sm text-neutral-500">
                    No project burn insight is available until the selected batch contains disbursement lines.
                  </div>
                {/if}
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  {/if}
</div>

<BankFilePreview
  open={bankFilePreviewOpen}
  batchLabel={selectedBatch?.label ?? "Payroll disbursement"}
  periodLabel={disbursementBuild.reportingPeriodLabel}
  rows={selectedBatch?.rows ?? []}
  fundingAccountLabel={selectedFundingAccount?.label ?? "No funding account linked"}
  currencyCode={currency.config.code || "NGN"}
  previewMode={dataMode === "preview"}
  onClose={closeBankFilePreview}
/>

{#if queueDrawerOpen}
  <div
    class="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm"
    onclick={closeQueueDrawer}
    onkeydown={(event) => event.key === "Escape" && closeQueueDrawer()}
    role="button"
    tabindex="-1"
  ></div>

  <div class="fixed inset-y-0 right-0 z-50 flex w-full max-w-5xl flex-col border-l border-neutral-200 bg-white shadow-2xl drawer-slide-in">
    <div class="flex items-center justify-between border-b border-neutral-200 bg-black px-6 py-4">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.3em] text-neutral-500">Disbursement Detail</p>
        <h2 class="mt-1 text-lg font-bold text-white">{selectedRow?.beneficiaryName ?? "Payroll line"}</h2>
        <p class="text-xs text-neutral-400">{selectedRow?.projectCode ?? "Pending"} • {selectedRow?.projectName ?? "Awaiting project mapping"}</p>
      </div>

      <button
        type="button"
        class="flex h-8 w-8 items-center justify-center rounded-lg text-neutral-400 transition hover:bg-neutral-100 hover:text-neutral-600"
        onclick={closeQueueDrawer}
        aria-label="Close detail drawer"
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div class="border-b border-neutral-100 px-6 py-3 text-sm">
      <div class="flex flex-wrap items-center gap-6">
        <div><span class="text-neutral-400">Amount:</span> <span class="ml-1 font-bold text-neutral-950">{formatCurrency(selectedRow?.netAmount ?? 0)}</span></div>
        <div><span class="text-neutral-400">Status:</span> <span class="ml-1 font-semibold text-neutral-900">{selectedRow?.statusLabel ?? "Pending"}</span></div>
        <div><span class="text-neutral-400">Cadence:</span> <span class="ml-1 font-semibold text-neutral-900">{selectedBatch?.cadence ?? "Monthly"}</span></div>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto px-6 py-6">
      {#if selectedRow}
        <div class="grid gap-6 lg:grid-cols-[1.12fr_0.88fr]">
          <div class="space-y-5">
            <div class="rounded-[28px] border border-white/55 bg-[linear-gradient(180deg,rgba(255,255,255,0.86),rgba(247,248,251,0.8))] p-5 shadow-[0_20px_60px_rgba(148,163,184,0.16)] backdrop-blur-xl">
              <div class="grid gap-4 sm:grid-cols-3">
                <div class="rounded-2xl border border-neutral-200 bg-white/75 p-4">
                  <p class="text-xs font-semibold uppercase tracking-[0.22em] text-neutral-400">Net Amount</p>
                  <p class="mt-3 text-2xl font-bold tracking-tight text-neutral-950">{formatCurrency(selectedRow.netAmount)}</p>
                </div>
                <div class="rounded-2xl border border-emerald-200/70 bg-emerald-50/80 p-4">
                  <p class="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-600">Capitalized</p>
                  <p class="mt-3 text-2xl font-bold tracking-tight text-emerald-950">{formatCurrency(selectedRow.capitalizedAmount)}</p>
                </div>
                <div class="rounded-2xl border border-neutral-200 bg-neutral-50/85 p-4">
                  <p class="text-xs font-semibold uppercase tracking-[0.22em] text-neutral-500">Expensed</p>
                  <p class="mt-3 text-2xl font-bold tracking-tight text-neutral-950">{formatCurrency(selectedRow.expensedAmount)}</p>
                </div>
              </div>

              <div class="mt-5 rounded-[24px] border border-neutral-200 bg-neutral-950 p-5 text-white">
                <div class="flex items-end justify-between gap-4">
                  <div>
                    <p class="text-xs font-semibold uppercase tracking-[0.22em] text-white/60">Validation</p>
                    <p class="mt-3 text-2xl font-semibold tracking-tight">{selectedRow.validationLabel}</p>
                  </div>
                  <span class={`inline-flex rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${resolveStatusClass(selectedRow.status)}`}>
                    {selectedRow.status}
                  </span>
                </div>
              </div>
            </div>

            <div class="rounded-[28px] border border-white/55 bg-white/72 p-5 shadow-[0_20px_60px_rgba(148,163,184,0.15)] backdrop-blur-xl">
              <p class="text-xs font-semibold uppercase tracking-[0.24em] text-neutral-400">Bank Instruction</p>
              <div class="mt-4 grid gap-3 sm:grid-cols-2">
                <div class="rounded-2xl border border-neutral-200 bg-neutral-50/80 px-4 py-3">
                  <p class="text-xs uppercase tracking-[0.18em] text-neutral-400">Bank Name</p>
                  <p class="mt-2 text-base font-semibold text-neutral-950">{selectedRow.banking.bankName || "Secure registry pending"}</p>
                </div>
                <div class="rounded-2xl border border-neutral-200 bg-neutral-50/80 px-4 py-3">
                  <p class="text-xs uppercase tracking-[0.18em] text-neutral-400">Account Number</p>
                  <p class="mt-2 text-base font-semibold text-neutral-950">
                    {selectedRow.banking.accountNumber ? selectedRow.banking.accountNumber : "Awaiting secure registry release"}
                  </p>
                </div>
                <div class="rounded-2xl border border-neutral-200 bg-neutral-50/80 px-4 py-3">
                  <p class="text-xs uppercase tracking-[0.18em] text-neutral-400">Payment Method</p>
                  <p class="mt-2 text-base font-semibold text-neutral-950">{selectedRow.banking.paymentMethod}</p>
                </div>
                <div class="rounded-2xl border border-neutral-200 bg-neutral-50/80 px-4 py-3">
                  <p class="text-xs uppercase tracking-[0.18em] text-neutral-400">Archive Action</p>
                  <p class="mt-2 text-base font-semibold text-neutral-950">{selectedRow.receiptArchiveLabel}</p>
                </div>
              </div>
            </div>
          </div>

          <div class="space-y-4">
            <div class="rounded-[28px] border border-white/55 bg-white/72 p-5 shadow-[0_20px_60px_rgba(148,163,184,0.15)] backdrop-blur-xl">
              <p class="text-xs font-semibold uppercase tracking-[0.24em] text-neutral-400">Payout Notes</p>
              <p class="mt-4 text-sm leading-7 text-neutral-600">{selectedRow.notes}</p>
              <div class="mt-4 rounded-2xl border border-dashed border-neutral-300 bg-neutral-50/80 p-4">
                <p class="text-xs uppercase tracking-[0.18em] text-neutral-400">Source</p>
                <p class="mt-2 text-sm font-medium text-neutral-900">{selectedRow.sourceLabel}</p>
              </div>
            </div>

            <div class="rounded-[28px] border border-white/55 bg-white/72 p-5 shadow-[0_20px_60px_rgba(148,163,184,0.15)] backdrop-blur-xl">
              <p class="text-xs font-semibold uppercase tracking-[0.24em] text-neutral-400">Project And Cost Control</p>
              <div class="mt-4 space-y-3">
                <div class="flex items-center justify-between rounded-2xl bg-neutral-50/80 px-4 py-3">
                  <span class="text-sm text-neutral-500">Project</span>
                  <span class="text-sm font-medium text-neutral-900">{selectedRow.projectName}</span>
                </div>
                <div class="flex items-center justify-between rounded-2xl bg-neutral-50/80 px-4 py-3">
                  <span class="text-sm text-neutral-500">Allocation</span>
                  <span class="text-sm font-medium text-neutral-900">{selectedRow.allocationPercent ?? "N/A"}%</span>
                </div>
                <div class="flex items-center justify-between rounded-2xl bg-neutral-50/80 px-4 py-3">
                  <span class="text-sm text-neutral-500">Overtime Alert</span>
                  <span class="text-sm font-medium text-neutral-900">{selectedRow.overtimeHours.toFixed(1)} hrs</span>
                </div>
                <div class="flex items-center justify-between rounded-2xl bg-neutral-50/80 px-4 py-3">
                  <span class="text-sm text-neutral-500">Project Budget</span>
                  <span class="text-sm font-medium text-neutral-900">{formatCurrency(selectedRow.projectBudget)}</span>
                </div>
              </div>
            </div>

            <div class={`rounded-[28px] border p-5 ${selectedRow.validationState === "valid" ? "border-emerald-200 bg-emerald-50/80" : selectedRow.validationState === "warning" ? "border-orange-200 bg-orange-50/80" : "border-sky-200 bg-sky-50/85"}`}>
              <p class="text-xs font-semibold uppercase tracking-[0.24em] text-neutral-500">Validation State</p>
              <p class="mt-3 text-lg font-semibold text-neutral-950">{selectedRow.validationLabel}</p>
              <p class="mt-2 text-sm leading-6 text-neutral-600">
                {selectedRow.validationState === "valid"
                  ? "This line is ready for transmission, archive, and downstream reconciliation."
                  : selectedRow.validationState === "warning"
                    ? "Proceed with caution and review the flagged cost or bonus note before releasing funds."
                    : "This line should remain blocked until secure payroll registry or split-sheet approval is complete."}
              </p>
            </div>
          </div>
        </div>
      {/if}
    </div>
  </div>
{/if}

{#if authDrawerOpen}
  <div
    class="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm"
    onclick={closeTransferAuth}
    onkeydown={(event) => event.key === "Escape" && closeTransferAuth()}
    role="button"
    tabindex="-1"
  ></div>

  <div class="fixed inset-y-0 right-0 z-50 flex w-full max-w-2xl flex-col border-l border-neutral-200 bg-white shadow-2xl drawer-slide-in">
    <div class="flex items-center justify-between border-b border-neutral-200 bg-black px-6 py-4">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.3em] text-neutral-500">Transfer Authorization</p>
        <h2 class="mt-1 text-lg font-bold text-white">{selectedBatch?.label ?? "Batch"} MFA</h2>
        <p class="text-xs text-neutral-400">Confirm the bank push before the queue enters processing.</p>
      </div>

      <button
        type="button"
        class="flex h-8 w-8 items-center justify-center rounded-lg text-neutral-400 transition hover:bg-neutral-100 hover:text-neutral-600"
        onclick={closeTransferAuth}
        aria-label="Close transfer drawer"
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div class="flex-1 overflow-y-auto px-6 py-6">
      <div class="space-y-5">
        <div class="rounded-[28px] border border-white/55 bg-[linear-gradient(180deg,rgba(255,255,255,0.86),rgba(247,248,251,0.8))] p-5 shadow-[0_20px_60px_rgba(148,163,184,0.16)] backdrop-blur-xl">
          <p class="text-xs font-semibold uppercase tracking-[0.24em] text-neutral-400">Batch Summary</p>
          <div class="mt-4 grid gap-3 sm:grid-cols-2">
            <div class="rounded-2xl border border-neutral-200 bg-white/80 px-4 py-3">
              <p class="text-xs uppercase tracking-[0.18em] text-neutral-400">Total</p>
              <p class="mt-2 text-2xl font-bold tracking-tight text-neutral-950">{formatCurrency(selectedSummary.total)}</p>
            </div>
            <div class="rounded-2xl border border-neutral-200 bg-white/80 px-4 py-3">
              <p class="text-xs uppercase tracking-[0.18em] text-neutral-400">Funding</p>
              <p class="mt-2 text-base font-semibold text-neutral-950">{selectedFundingAccount?.label ?? "No linked account"}</p>
            </div>
          </div>
        </div>

        <div class="rounded-[28px] border border-white/55 bg-white/72 p-5 shadow-[0_20px_60px_rgba(148,163,184,0.15)] backdrop-blur-xl">
          <p class="text-xs font-semibold uppercase tracking-[0.24em] text-neutral-400">One-Time Code</p>
          <p class="mt-3 text-sm leading-6 text-neutral-600">
            Enter the finance OTP to simulate the final approval handoff. Preview mode uses a fixed code so the interface can be exercised safely.
          </p>

          <label class="mt-5 block">
            <span class="mb-2 block text-sm font-medium text-neutral-700">OTP</span>
            <input
              type="text"
              bind:value={otpCode}
              maxlength="6"
              inputmode="numeric"
              class="w-full rounded-2xl border border-neutral-200 bg-white/90 px-4 py-3 text-sm text-neutral-700 focus:border-neutral-400 focus:outline-none"
              placeholder="Enter 6-digit code"
            />
          </label>
          {#if otpError}
            <p class="mt-2 text-sm text-red-600">{otpError}</p>
          {/if}

          <div class="mt-5 rounded-2xl border border-dashed border-neutral-300 bg-neutral-50/85 p-4 text-sm text-neutral-600">
            Preview code: <span class="font-semibold text-neutral-900">{PREVIEW_AUTH_CODE}</span>
          </div>

          <div class="mt-5 flex flex-wrap gap-3">
            <button
              type="button"
              class="inline-flex items-center justify-center rounded-2xl bg-neutral-950 px-4 py-3 text-sm font-semibold text-white transition hover:bg-neutral-800"
              onclick={confirmTransfer}
            >
              Authorize Transfer
            </button>
            <button
              type="button"
              class="inline-flex items-center justify-center rounded-2xl border border-neutral-200 bg-white px-4 py-3 text-sm font-semibold text-neutral-700 transition hover:bg-neutral-50"
              onclick={closeTransferAuth}
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  .drawer-slide-in { animation: drawerSlideIn 0.25s ease-out both; }
  .pulse-dot { animation: pulseDot 1.8s ease-in-out infinite; }

  @keyframes drawerSlideIn {
    from { transform: translateX(100%); }
    to { transform: translateX(0); }
  }

  @keyframes pulseDot {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.55; transform: scale(1.18); }
  }
</style>

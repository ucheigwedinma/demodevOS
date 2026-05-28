<script lang="ts">
  import { api } from "$lib/api";
  import GroupedBarChart from "$lib/components/charts/GroupedBarChart.svelte";
  import BarChart from "$lib/components/charts/BarChart.svelte";
  import DonutChart from "$lib/components/charts/DonutChart.svelte";
  import AreaChart from "$lib/components/charts/AreaChart.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import { onboarding } from "$lib/stores/onboarding.svelte";
  import { useLiveKpis } from "$lib/realtime.svelte";
  import LiveBadge from "$lib/components/LiveBadge.svelte";
  import type {
    BillListItem,
    FinanceOverview,
    InvoiceListItem,
    MyApprovalItem,
    PaginatedResponse,
    PortfolioAnalytics,
    ProjectListItem,
    UserListResponse,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  interface LifecycleStages {
    pending_invitations: number;
    pending_onboarding: number;
    active: number;
    suspended: number;
    locked: number;
    never_logged_in: number;
  }

  interface LifecycleResponse {
    stages: LifecycleStages;
  }

  type KpiCard = {
    title: string;
    value: number;
    note: string;
    valueKind?: "money" | "count";
    accent: string;
    valueClass: string;
    badgeClass: string;
    module?: string;
  };

  type ApprovalRow = {
    property: string;
    manager: string;
    status: string;
  };

  type PayoutRow = {
    period: string;
    amount: number;
    status: string;
  };

  type RegionRow = {
    region: string;
    value: number;
  };

  type LocationRow = {
    name: string;
    location: string;
    occupancy: string;
  };

  let loading = $state(true);
  let portfolio = $state<PortfolioAnalytics | null>(null);
  let finance = $state<FinanceOverview | null>(null);
  let projects = $state<ProjectListItem[]>([]);
  let approvals = $state<MyApprovalItem[]>([]);
  let invoices = $state<InvoiceListItem[]>([]);
  let bills = $state<BillListItem[]>([]);
  let selectedRegion = $state("all");
  let dateFrom = $state("");
  let dateTo = $state("");
  let userOverview = $state({ total: 0, active: 0, suspended: 0, locked: 0 });
  let lifecycle = $state<LifecycleStages>({
    pending_invitations: 0,
    pending_onboarding: 0,
    active: 0,
    suspended: 0,
    locked: 0,
    never_logged_in: 0,
  });

  async function fetchAllPages<T>(
    endpoint: string,
    params: Record<string, string> = {},
    maxPages = 6,
  ): Promise<T[]> {
    const rows: T[] = [];
    let page = 1;

    while (page <= maxPages) {
      const res = await api.get<PaginatedResponse<T>>(endpoint, {
        ...params,
        page: String(page),
      });
      rows.push(...res.results);
      if (!res.next || res.results.length === 0) break;
      page += 1;
    }

    return rows;
  }

  const hasAnalytics = $derived(onboarding.hasModule("analytics"));
  const hasFinance = $derived(onboarding.hasModule("finance"));
  const hasIam = $derived(onboarding.hasModule("iam"));
  const hasProjects = $derived(onboarding.hasModule("projects"));
  const hasProcurement = $derived(onboarding.hasModule("procurement"));
  const hasProperties = $derived(onboarding.hasModule("properties"));

  async function loadData() {
    loading = true;
    const [
      portfolioRes,
      financeRes,
      projectsRes,
      approvalsRes,
      invoicesRes,
      billsRes,
      usersRes,
      lifecycleRes,
    ] = await Promise.allSettled([
      hasAnalytics
        ? api.get<PortfolioAnalytics>("/analytics/portfolio/")
        : Promise.reject("disabled"),
      hasFinance
        ? api.get<FinanceOverview>("/finance/overview/")
        : Promise.reject("disabled"),
      hasProjects
        ? api.get<PaginatedResponse<ProjectListItem>>("/projects/", {
            page_size: "200",
            ordering: "-created_at",
          })
        : Promise.reject("disabled"),
      api.get<MyApprovalItem[]>("/workflows/my-approvals/"),
      hasFinance
        ? fetchAllPages<InvoiceListItem>("/finance/invoices/", {
            page_size: "200",
            ordering: "-issue_date",
          })
        : Promise.reject("disabled"),
      hasFinance
        ? fetchAllPages<BillListItem>("/finance/bills/", {
            page_size: "200",
            ordering: "-issue_date",
          })
        : Promise.reject("disabled"),
      hasIam
        ? api.get<UserListResponse>("/iam/users/", { page_size: "1" })
        : Promise.reject("disabled"),
      hasIam
        ? api.get<LifecycleResponse>("/iam/users/lifecycle/")
        : Promise.reject("disabled"),
    ]);

    portfolio = portfolioRes.status === "fulfilled" ? portfolioRes.value : null;
    finance = financeRes.status === "fulfilled" ? financeRes.value : null;
    projects = projectsRes.status === "fulfilled" ? projectsRes.value.results : [];
    approvals = approvalsRes.status === "fulfilled" ? approvalsRes.value : [];
    invoices = invoicesRes.status === "fulfilled" ? invoicesRes.value : [];
    bills = billsRes.status === "fulfilled" ? billsRes.value : [];
    userOverview = usersRes.status === "fulfilled"
      ? usersRes.value.overview
      : { total: 0, active: 0, suspended: 0, locked: 0 };
    lifecycle = lifecycleRes.status === "fulfilled"
      ? lifecycleRes.value.stages
      : {
          pending_invitations: 0,
          pending_onboarding: 0,
          active: 0,
          suspended: 0,
          locked: 0,
          never_logged_in: 0,
        };

    loading = false;
  }

  $effect(() => {
    loadData();
  });

  const live = useLiveKpis(
    ["Project", "Bill", "Invoice", "Budget", "PurchaseOrder", "PurchaseRequisition", "Lead", "Reservation", "Lease", "Employee", "Ticket"],
    loadData,
    { debounceMs: 3000 },
  );

  function toAmount(value: string | number | null | undefined): number {
    if (typeof value === "number") return Number.isFinite(value) ? value : 0;
    const parsed = Number(value ?? 0);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function roundCurrency(value: number): number {
    return Math.round((value + Number.EPSILON) * 100) / 100;
  }

  function formatMonthKey(dateStr: string): string {
    const date = new Date(dateStr);
    if (Number.isNaN(date.getTime())) return "";
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
  }

  function monthWindow(count = 12): { key: string; label: string }[] {
    const formatter = new Intl.DateTimeFormat("en-US", { month: "short" });
    const now = new Date();
    const months: { key: string; label: string }[] = [];
    for (let i = count - 1; i >= 0; i -= 1) {
      const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
      months.push({
        key: `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`,
        label: formatter.format(d),
      });
    }
    return months;
  }

  function toDateInputValue(timestamp: number): string {
    const date = new Date(timestamp);
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
  }

  function parseDate(dateStr: string | null | undefined): number | null {
    if (!dateStr) return null;
    const ts = new Date(dateStr).getTime();
    return Number.isFinite(ts) ? ts : null;
  }

  function isInSelectedDateRange(dateStr: string | null | undefined): boolean {
    const ts = parseDate(dateStr);
    const hasRange = Boolean(dateFrom || dateTo);
    if (ts === null) return !hasRange;

    const fromTs = dateFrom ? new Date(`${dateFrom}T00:00:00`).getTime() : null;
    const toTs = dateTo ? new Date(`${dateTo}T23:59:59.999`).getTime() : null;

    if (fromTs !== null && ts < fromTs) return false;
    if (toTs !== null && ts > toTs) return false;
    return true;
  }

  function normalizeRegion(location: string): string {
    const parts = location
      .split(",")
      .map((part) => part.trim())
      .filter(Boolean);
    return parts[parts.length - 1] ?? parts[0] ?? "Unspecified";
  }

  function titleize(value: string): string {
    return value
      .replace(/_/g, " ")
      .split(" ")
      .filter(Boolean)
      .map((word) => word[0]?.toUpperCase() + word.slice(1))
      .join(" ");
  }

  function formatPeriod(dateStr: string): string {
    const d = new Date(dateStr);
    if (Number.isNaN(d.getTime())) return "--";
    return d.toLocaleDateString("en-US", { month: "long", year: "numeric" });
  }

  function formatPct(value: number): string {
    return `${Math.round(value)}%`;
  }

  function fmtMoney(value: number): string {
    return currency.format(value);
  }

  function fmtCompactMoney(value: number): string {
    return currency.formatAbbreviated(value);
  }

  function fmtKpiMoney(value: number): string {
    const formatted = fmtCompactMoney(value);
    const symbol = currency.config.symbol;

    if (!symbol) return formatted.trim();

    if (currency.config.position === "prefix" && formatted.startsWith(symbol)) {
      return formatted.slice(symbol.length).trim();
    }

    if (currency.config.position === "suffix" && formatted.endsWith(symbol)) {
      return formatted.slice(0, -symbol.length).trim();
    }

    return formatted.replace(symbol, "").trim();
  }

  function fmtKpi(card: KpiCard): string {
    if (card.valueKind === "count") return card.value.toLocaleString("en-US");
    return fmtKpiMoney(card.value);
  }

  const months = $derived(monthWindow(12));

  const filteredInvoices = $derived.by(() => {
    const source = invoices.length > 0 ? invoices : (finance?.recent_invoices ?? []);
    return source.filter((row) => isInSelectedDateRange(row.issue_date));
  });

  const filteredBills = $derived.by(() => {
    const source = bills.length > 0 ? bills : (finance?.recent_bills ?? []);
    return source.filter((row) => isInSelectedDateRange(row.issue_date));
  });

  const filteredApprovalsSource = $derived(
    approvals.filter((row) => isInSelectedDateRange(row.submitted_at))
  );

  const dateFilteredProjects = $derived.by(() => {
    return projects.filter((project) => isInSelectedDateRange(project.start_date ?? project.created_at));
  });

  $effect(() => {
    if (dateFrom && dateTo && dateFrom > dateTo) {
      dateTo = dateFrom;
    }
  });

  $effect(() => {
    if (dateFrom || dateTo) return;
    const dateCandidates = [
      ...invoices.map((row) => parseDate(row.issue_date)),
      ...bills.map((row) => parseDate(row.issue_date)),
      ...projects.map((row) => parseDate(row.start_date ?? row.created_at)),
      ...approvals.map((row) => parseDate(row.submitted_at)),
    ].filter((value): value is number => value !== null);

    if (dateCandidates.length === 0) return;
    dateFrom = toDateInputValue(Math.min(...dateCandidates));
    dateTo = toDateInputValue(Math.max(...dateCandidates));
  });

  const availableRegions = $derived.by(() => {
    return Array.from(
      new Set(
        dateFilteredProjects
          .filter((project) => project.location)
          .map((project) => normalizeRegion(project.location))
      )
    ).sort((a, b) => a.localeCompare(b));
  });

  $effect(() => {
    if (selectedRegion !== "all" && !availableRegions.includes(selectedRegion)) {
      selectedRegion = "all";
    }
  });

  const filteredProjects = $derived.by(() => {
    if (selectedRegion === "all") return dateFilteredProjects;
    return dateFilteredProjects.filter((project) => {
      if (!project.location) return false;
      return normalizeRegion(project.location) === selectedRegion;
    });
  });

  const activeProjects = $derived(filteredProjects.filter((project) => project.status !== "completed").length);
  const completedProjects = $derived(filteredProjects.filter((project) => project.status === "completed").length);

  const operationalKpis = $derived.by(() => {
    const totalUsers = userOverview.total;
    const activeRatio = totalUsers > 0 ? (userOverview.active / totalUsers) * 100 : 0;
    const pendingKyc = lifecycle.pending_invitations + lifecycle.pending_onboarding;
    return [
      {
        title: "Total Users",
        value: totalUsers,
        note: `${formatPct(activeRatio)} active`,
        valueKind: "count" as const,
        accent: "border-t-pink-500",
        valueClass: "text-pink-700",
        badgeClass: "bg-pink-50 text-pink-700",
        module: "iam",
      },
      {
        title: "Total Investments",
        value: toAmount(portfolio?.kpis.total_value),
        note: `${activeProjects} active projects`,
        accent: "border-t-emerald-600",
        valueClass: "text-emerald-700",
        badgeClass: "bg-emerald-50 text-emerald-700",
        module: "analytics",
      },
      {
        title: "Properties Listed",
        value: portfolio?.kpis.property_count ?? 0,
        note: `${portfolio?.classification_breakdown.length ?? 0} classifications`,
        valueKind: "count" as const,
        accent: "border-t-lime-500",
        valueClass: "text-lime-700",
        badgeClass: "bg-lime-50 text-lime-700",
        module: "analytics",
      },
      {
        title: "KYC Pending",
        value: pendingKyc,
        note: lifecycle.never_logged_in > 0 ? `${lifecycle.never_logged_in} never logged in` : "No backlog",
        valueKind: "count" as const,
        accent: "border-t-amber-500",
        valueClass: "text-amber-700",
        badgeClass: "bg-amber-50 text-amber-700",
        module: "iam",
      },
    ] satisfies KpiCard[];
  });

  const visibleOperationalKpis = $derived(
    operationalKpis.filter((card) => !card.module || onboarding.hasModule(card.module))
  );

  const crossModuleKpis = $derived.by(() => [
    {
      title: "Construction Pulse",
      value: portfolio?.construction_summary.open_field_issues ?? 0,
      note: `${Math.round(portfolio?.construction_summary.avg_progress_percent ?? 0)}% avg site progress`,
      valueKind: "count" as const,
      accent: "border-t-cyan-500",
      valueClass: "text-cyan-700",
      badgeClass: "bg-cyan-50 text-cyan-700",
      module: "projects",
    },
    {
      title: "Sales Pipeline (CRM)",
      value: portfolio?.crm_summary.active_leads ?? 0,
      note: `${portfolio?.crm_summary.active_reservations ?? 0} active reservations`,
      valueKind: "count" as const,
      accent: "border-t-fuchsia-500",
      valueClass: "text-fuchsia-700",
      badgeClass: "bg-fuchsia-50 text-fuchsia-700",
      module: "crm",
    },
    {
      title: "HR Workforce",
      value: portfolio?.hr_summary.active_employees ?? 0,
      note: `${portfolio?.hr_summary.open_vacancies ?? 0} open vacancies`,
      valueKind: "count" as const,
      accent: "border-t-emerald-500",
      valueClass: "text-emerald-700",
      badgeClass: "bg-emerald-50 text-emerald-700",
      module: "hr",
    },
    {
      title: "Procurement Commitments",
      value: toAmount(portfolio?.procurement_summary.committed_amount),
      note: `${portfolio?.procurement_summary.open_commitments ?? 0} open PO commitments`,
      accent: "border-t-amber-500",
      valueClass: "text-amber-700",
      badgeClass: "bg-amber-50 text-amber-700",
      module: "procurement",
    },
    {
      title: "Facility Maintenance",
      value: portfolio?.facility_summary.open_work_orders ?? 0,
      note: `${portfolio?.facility_summary.pending_inspections ?? 0} pending inspections`,
      valueKind: "count" as const,
      accent: "border-t-orange-500",
      valueClass: "text-orange-700",
      badgeClass: "bg-orange-50 text-orange-700",
      module: "properties",
    },
    {
      title: "Tenants Live",
      value: portfolio?.tenant_summary.active_tenants ?? 0,
      note: `${portfolio?.tenant_summary.open_tenant_requests ?? 0} open tenant requests`,
      valueKind: "count" as const,
      accent: "border-t-indigo-500",
      valueClass: "text-indigo-700",
      badgeClass: "bg-indigo-50 text-indigo-700",
      module: "tenants",
    },
  ] satisfies KpiCard[]);

  const visibleCrossModuleKpis = $derived(
    crossModuleKpis.filter((card) => !card.module || onboarding.hasModule(card.module))
  );

  const portfolioKpis = $derived.by(() => [
    {
      title: "Property Portfolio Control",
      value: portfolio?.kpis.property_count ?? 0,
      note: `${activeProjects} active project${activeProjects === 1 ? "" : "s"}`,
      valueKind: "count" as const,
      accent: "border-t-blue-500",
      valueClass: "text-blue-700",
      badgeClass: "bg-blue-50 text-blue-700",
    },
    {
      title: "Portfolio Value Management",
      value: toAmount(portfolio?.kpis.total_value),
      note: `${fmtKpiMoney(toAmount(portfolio?.kpis.unrealized_gain))} unrealized gain`,
      accent: "border-t-violet-500",
      valueClass: "text-violet-700",
      badgeClass: "bg-violet-50 text-violet-700",
    },
    {
      title: "Portfolio Divestitures",
      value: completedProjects,
      note: `${filteredProjects.length} total projects`,
      valueKind: "count" as const,
      accent: "border-t-red-500",
      valueClass: "text-red-700",
      badgeClass: "bg-red-50 text-red-700",
    },
  ] satisfies KpiCard[]);

  const operationalKpiMax = $derived(Math.max(...visibleOperationalKpis.map((card) => Math.abs(card.value)), 1));
  const crossModuleKpiMax = $derived(Math.max(...visibleCrossModuleKpis.map((card) => Math.abs(card.value)), 1));
  const portfolioKpiMax = $derived(Math.max(...portfolioKpis.map((card) => Math.abs(card.value)), 1));

  const monthlyCashFlow = $derived.by(() => {
    const invoiceTotals = new Map<string, number>();
    const billTotals = new Map<string, number>();

    for (const row of filteredInvoices) {
      const key = formatMonthKey(row.issue_date);
      if (!key) continue;
      invoiceTotals.set(key, (invoiceTotals.get(key) ?? 0) + toAmount(row.total_amount));
    }

    for (const row of filteredBills) {
      const key = formatMonthKey(row.issue_date);
      if (!key) continue;
      billTotals.set(key, (billTotals.get(key) ?? 0) + toAmount(row.total_amount));
    }

    return months.map((month) => ({
      label: month.label,
      value1: invoiceTotals.get(month.key) ?? 0,
      value2: billTotals.get(month.key) ?? 0,
    }));
  });

  const monthlyNetSpark = $derived.by(() => {
    const source = monthlyCashFlow.slice(-8).map((row) => ({
      label: row.label,
      value: roundCurrency(row.value1 - row.value2),
    }));
    const maxAbs = Math.max(...source.map((row) => Math.abs(row.value)), 1);
    return source.map((row) => ({
      ...row,
      height: Math.max(12, Math.round((Math.abs(row.value) / maxAbs) * 100)),
      positive: row.value >= 0,
    }));
  });

  const rentIncome = $derived(
    monthlyCashFlow.map((row) => ({ label: row.label, value: row.value1 }))
  );

  const listedVsOffer = $derived.by(() => {
    const budgetRows = (portfolio?.project_budget_summary ?? []).map((item) => ({
      label: item.name,
      value1: toAmount(item.total_planned),
      value2: toAmount(item.total_actual),
    }));
    if (budgetRows.length > 0) return budgetRows.slice(0, 12);
    return monthlyCashFlow.map((row) => ({
      label: row.label,
      value1: row.value1,
      value2: row.value2,
    }));
  });

  const inflowValue = $derived.by(() => {
    if (invoices.length > 0 || (finance?.recent_invoices.length ?? 0) > 0) {
      return roundCurrency(filteredInvoices.reduce((sum, row) => sum + toAmount(row.total_amount), 0));
    }
    return roundCurrency(toAmount(finance?.total_receivable));
  });

  const outflowValue = $derived.by(() => {
    if (bills.length > 0 || (finance?.recent_bills.length ?? 0) > 0) {
      return roundCurrency(filteredBills.reduce((sum, row) => sum + toAmount(row.total_amount), 0));
    }
    return roundCurrency(toAmount(finance?.total_payable));
  });
  const fundBalance = $derived(roundCurrency(Math.max(inflowValue - outflowValue, 0)));

  const fundsEscrow = $derived([
    { label: "Funds", value: fundBalance },
    { label: "Inflow", value: inflowValue },
    { label: "Outflow", value: outflowValue },
  ]);

  const fundsEscrowChart = $derived(fundsEscrow.filter((row) => row.value > 0));

  const constructionBudgetBurn = $derived.by(() => {
    const rows = portfolio?.project_budget_summary ?? [];
    const planned = rows.reduce((sum, row) => sum + toAmount(row.total_planned), 0);
    const actual = rows.reduce((sum, row) => sum + toAmount(row.total_actual), 0);
    const burnRate = planned > 0 ? (actual / planned) * 100 : 0;
    return {
      planned: roundCurrency(planned),
      actual: roundCurrency(actual),
      burnRate,
      projectCount: rows.length,
    };
  });

  const propertyInventory = $derived.by(() => {
    const summary = { total: 0, available: 0, reserved: 0, sold: 0, leased: 0 };
    for (const row of portfolio?.unit_occupancy ?? []) {
      const status = (row.status ?? "").toLowerCase();
      const count = row.count ?? 0;
      summary.total += count;
      if (status === "available") summary.available += count;
      if (status === "reserved") summary.reserved += count;
      if (status === "sold") summary.sold += count;
      if (status === "leased") summary.leased += count;
    }
    return summary;
  });

  const rentalOccupancy = $derived.by(() => {
    const total = propertyInventory.total;
    const leased = propertyInventory.leased;
    const pct = total > 0 ? (leased / total) * 100 : 0;
    return { total, leased, pct };
  });

  const maintenanceBacklog = $derived.by(() => {
    const openWorkOrders = portfolio?.facility_summary.open_work_orders ?? 0;
    const openServiceRequests = portfolio?.facility_summary.open_service_requests ?? 0;
    const urgentWorkOrders = portfolio?.facility_summary.urgent_work_orders ?? 0;
    const pendingInspections = portfolio?.facility_summary.pending_inspections ?? 0;
    return {
      total: openWorkOrders + openServiceRequests,
      openWorkOrders,
      openServiceRequests,
      urgentWorkOrders,
      pendingInspections,
    };
  });

  const procurementCommitments = $derived.by(() => {
    const summary = portfolio?.procurement_summary;
    return {
      amount: toAmount(summary?.committed_amount),
      openCommitments: summary?.open_commitments ?? 0,
      overdueDeliveries: summary?.overdue_deliveries ?? 0,
      pendingRequisitions: summary?.pending_requisitions ?? 0,
    };
  });

  const cashFlowForecast = $derived.by(() => {
    const recentNet = monthlyCashFlow
      .slice(-3)
      .map((row) => roundCurrency(row.value1 - row.value2));
    const avgMonthlyNet = recentNet.length > 0
      ? roundCurrency(recentNet.reduce((sum, value) => sum + value, 0) / recentNet.length)
      : 0;
    const now = new Date();
    let running = roundCurrency(fundBalance);
    const series: { x: Date; y: number; label: string }[] = [
      {
        x: new Date(now.getFullYear(), now.getMonth(), 1),
        y: running,
        label: now.toLocaleDateString("en-US", { month: "short", year: "numeric" }),
      },
    ];
    for (let step = 1; step <= 3; step += 1) {
      const pointDate = new Date(now.getFullYear(), now.getMonth() + step, 1);
      running = roundCurrency(running + avgMonthlyNet);
      series.push({
        x: pointDate,
        y: running,
        label: pointDate.toLocaleDateString("en-US", { month: "short", year: "numeric" }),
      });
    }
    return {
      avgMonthlyNet,
      projectedBalance: running,
      series,
    };
  });

  const pendingApprovals = $derived.by(() => {
    return filteredApprovalsSource.slice(0, 4).map((item) => {
      const status = item.sla_breached ? "Breached" : item.state === "pending" ? "Pending" : titleize(item.state);
      return {
        property: item.template_name,
        manager: item.step_name,
        status,
      };
    }) satisfies ApprovalRow[];
  });

  const scheduledPayouts = $derived.by(() => {
    return filteredBills.slice(0, 4).map((row) => ({
      period: formatPeriod(row.due_date),
      amount: toAmount(row.total_amount),
      status: row.status === "paid" ? "Paid" : row.status === "approved" ? "Scheduled" : titleize(row.status),
    })) satisfies PayoutRow[];
  });

  const regionalPortfolio = $derived.by(() => {
    const byRegion = new Map<string, number>();

    for (const project of filteredProjects) {
      if (!project.location) continue;
      const region = normalizeRegion(project.location);
      const value = toAmount(project.budget);
      byRegion.set(region, (byRegion.get(region) ?? 0) + value);
    }

    if (byRegion.size === 0 && !dateFrom && !dateTo) {
      for (const item of portfolio?.type_distribution ?? []) {
        byRegion.set(titleize(item.type), toAmount(item.total_value));
      }
    }

    return Array.from(byRegion.entries())
      .map(([region, value]) => ({ region, value }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 5) satisfies RegionRow[];
  });

  const locationCards = $derived.by(() => {
    const rows = filteredProjects
      .filter((project) => project.location)
      .slice(0, 3)
      .map((project) => ({
        name: project.name,
        location: project.location,
        occupancy: `${Math.max(0, Math.min(100, Math.round(project.progress)))}%`,
      })) as LocationRow[];

    if (rows.length > 0) return rows;

    if (dateFrom || dateTo) return [];

    return (portfolio?.top_appreciating ?? []).slice(0, 3).map((property) => ({
      name: property.name,
      location: titleize(property.property_type),
      occupancy: `${Math.max(0, Math.round(Number(property.gain_pct)))}%`,
    }));
  });

  const topRegionalValue = $derived(regionalPortfolio[0]?.value ?? 1);

  const selectedRegionLabel = $derived(selectedRegion === "all" ? "All Regions" : selectedRegion);

  const timePill = $derived.by(() => {
    if (dateFrom || dateTo) {
      const fromLabel = dateFrom
        ? new Date(dateFrom).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
        : "Start";
      const toLabel = dateTo
        ? new Date(dateTo).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
        : "Now";
      return `${fromLabel} - ${toLabel}`;
    }

    const dates = [
      ...filteredInvoices.map((row) => row.issue_date),
      ...filteredBills.map((row) => row.issue_date),
    ]
      .map((date) => new Date(date).getTime())
      .filter((value) => Number.isFinite(value));

    if (dates.length === 0) return "Live";

    const minDate = new Date(Math.min(...dates));
    const maxDate = new Date(Math.max(...dates));
    const minLabel = minDate.toLocaleDateString("en-US", { month: "short", year: "numeric" });
    const maxLabel = maxDate.toLocaleDateString("en-US", { month: "short", year: "numeric" });

    return `${minLabel} - ${maxLabel}`;
  });

  function approvalStatusClass(status: string): string {
    if (status.toLowerCase() === "breached") return "bg-red-50 text-red-700";
    if (status.toLowerCase() === "pending") return "bg-amber-50 text-amber-700";
    return "bg-neutral-100 text-neutral-700";
  }

  function payoutStatusClass(status: string): string {
    const normalized = status.toLowerCase();
    if (normalized === "paid") return "bg-emerald-50 text-emerald-700";
    if (normalized === "scheduled" || normalized === "approved") return "bg-amber-50 text-amber-700";
    return "bg-red-50 text-red-700";
  }

  function kpiBarClass(valueClass: string): string {
    if (valueClass.includes("pink")) return "bg-pink-500";
    if (valueClass.includes("emerald")) return "bg-emerald-500";
    if (valueClass.includes("lime")) return "bg-lime-500";
    if (valueClass.includes("amber")) return "bg-amber-500";
    if (valueClass.includes("cyan")) return "bg-cyan-500";
    if (valueClass.includes("fuchsia")) return "bg-fuchsia-500";
    if (valueClass.includes("orange")) return "bg-orange-500";
    if (valueClass.includes("indigo")) return "bg-indigo-500";
    if (valueClass.includes("violet")) return "bg-violet-500";
    if (valueClass.includes("red")) return "bg-rose-500";
    if (valueClass.includes("blue")) return "bg-blue-500";
    return "bg-neutral-500";
  }
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
  </div>
{:else}
  <div class="space-y-6">
    <div class="space-y-3">
      <div class="min-w-0">
        <div class="flex items-center gap-2">
          <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-pink-600">Dashboard</p>
          <LiveBadge refreshing={live.refreshing} />
        </div>
        <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Operations Hub</h1>
        <p class="mt-1 overflow-hidden text-ellipsis whitespace-nowrap text-sm text-neutral-500">
          Daily cockpit — leaderboards, pending approvals, scheduled payouts, and live cash flow.
        </p>
      </div>
      <div class="flex flex-col gap-2">
        <div class="flex flex-wrap items-center gap-2">
          <label class="inline-flex items-center gap-2 rounded-full bg-neutral-100 px-3 py-1 text-xs font-medium text-neutral-600">
            <span>From:</span>
            <DateInput bind:value={dateFrom} />
          </label>
          <label class="inline-flex items-center gap-2 rounded-full bg-neutral-100 px-3 py-1 text-xs font-medium text-neutral-600">
            <span>To:</span>
            <DateInput bind:value={dateTo} />
          </label>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <span class="rounded-full bg-neutral-100 px-3 py-1 text-xs font-medium text-neutral-600">Range: {timePill}</span>
          <label class="inline-flex items-center gap-2 rounded-full bg-neutral-100 px-3 py-1 text-xs font-medium text-neutral-600">
            <span>Region:</span>
            <select
              bind:value={selectedRegion}
              class="w-auto rounded-md border border-neutral-200 bg-white px-2 py-0.5 text-xs text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
            >
              <option value="all">All Regions</option>
              {#each availableRegions as region}
                <option value={region}>{region}</option>
              {/each}
            </select>
          </label>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 gap-4 xl:grid-cols-12">
      <div class="rounded-xl border border-neutral-200 bg-white p-5 xl:col-span-5">
        <div class="flex items-start justify-between gap-3">
          <div>
            <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Capital Pulse</p>
            <p class="mt-1 text-3xl font-bold tabular-nums text-violet-700">{fmtKpiMoney(toAmount(portfolio?.kpis.total_value))}</p>
            <p class="mt-1 text-xs text-neutral-500">
              {portfolio?.kpis.property_count ?? 0} properties · {activeProjects} active projects · {selectedRegionLabel}
            </p>
          </div>
          <span class="rounded-full bg-violet-50 px-2.5 py-1 text-[10px] font-semibold text-violet-700">{timePill}</span>
        </div>

        <div class="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-2">
          {#if visibleOperationalKpis.length > 0}
            {#each visibleOperationalKpis as card}
              <div class="rounded-lg border border-neutral-100 bg-neutral-50 p-3">
                <p class="text-[11px] font-semibold text-neutral-600">{card.title}</p>
                <p class="mt-1 text-lg font-bold tabular-nums {card.valueClass}">{fmtKpi(card)}</p>
                <p class="mt-1 text-[10px] text-neutral-500">{card.note}</p>
              </div>
            {/each}
          {:else}
            <p class="col-span-2 rounded-lg border border-dashed border-neutral-200 px-3 py-5 text-sm text-neutral-400">No operational KPI blocks.</p>
          {/if}
        </div>

        <div class="mt-4 border-t border-neutral-100 pt-3">
          <div class="mb-2 flex items-center justify-between">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Net Cash Spark</p>
            <p class="text-[10px] text-neutral-500">Last {monthlyNetSpark.length} periods</p>
          </div>
          <div class="grid grid-cols-8 gap-1.5">
            {#if monthlyNetSpark.length > 0}
              {#each monthlyNetSpark as bar}
                <div class="text-center">
                  <div class="flex h-16 items-end justify-center">
                    <div
                      class="w-full rounded-sm {bar.positive ? 'bg-emerald-400' : 'bg-rose-300'}"
                      style="height: {bar.height}%;"
                    ></div>
                  </div>
                  <p class="mt-1 text-[10px] text-neutral-500">{bar.label}</p>
                </div>
              {/each}
            {:else}
              <p class="col-span-8 py-3 text-center text-xs text-neutral-400">No spark data.</p>
            {/if}
          </div>
        </div>
      </div>

      <div class="rounded-xl border border-neutral-200 bg-white p-5 xl:col-span-4">
        <div class="mb-3 flex items-center justify-between">
          <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Operational Leaderboard</h2>
          <span class="text-xs text-neutral-400">Weight by value</span>
        </div>

        <div class="space-y-3">
          {#if visibleOperationalKpis.length > 0}
            {#each visibleOperationalKpis as card}
              <div>
                <div class="mb-1 flex items-center justify-between text-xs">
                  <span class="text-neutral-600">{card.title}</span>
                  <span class="font-semibold tabular-nums {card.valueClass}">{fmtKpi(card)}</span>
                </div>
                <div class="h-2 rounded-full bg-neutral-100">
                  <div
                    class="h-2 rounded-full {kpiBarClass(card.valueClass)}"
                    style="width: {Math.max(8, Math.round((Math.abs(card.value) / Math.max(operationalKpiMax, 1)) * 100))}%"
                  ></div>
                </div>
                <p class="mt-1 text-[10px] text-neutral-500">{card.note}</p>
              </div>
            {/each}
          {:else}
            <p class="rounded-lg border border-dashed border-neutral-200 px-3 py-6 text-center text-sm text-neutral-400">
              No operational metrics available.
            </p>
          {/if}
        </div>
      </div>

      <div class="rounded-xl border border-neutral-200 bg-white p-5 xl:col-span-3">
        <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Portfolio Control Matrix</h2>
        <p class="mt-1 text-xs text-neutral-400">Portfolio control, value control, and divestiture signal.</p>
        <div class="mt-4 space-y-3">
          {#each portfolioKpis as card}
            <div class="rounded-lg border border-neutral-100 bg-neutral-50 p-3">
              <div class="mb-1 flex items-center justify-between text-xs">
                <span class="font-medium text-neutral-600">{card.title}</span>
                <span class="font-semibold tabular-nums {card.valueClass}">{fmtKpi(card)}</span>
              </div>
              <div class="h-1.5 rounded-full bg-neutral-200">
                <div
                  class="h-1.5 rounded-full {kpiBarClass(card.valueClass)}"
                  style="width: {Math.max(8, Math.round((Math.abs(card.value) / Math.max(portfolioKpiMax, 1)) * 100))}%"
                ></div>
              </div>
              <p class="mt-1.5 text-[10px] text-neutral-500">{card.note}</p>
            </div>
          {/each}
        </div>

        {#if visibleCrossModuleKpis.length > 0}
          <div class="mt-4 border-t border-neutral-100 pt-3">
            <p class="mb-2 text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Cross-Module Watchlist</p>
            <div class="max-h-72 space-y-2 overflow-y-auto pr-1">
              {#each visibleCrossModuleKpis as card}
                <div class="rounded-lg bg-neutral-50 px-2.5 py-2">
                  <div class="mb-1 flex items-center justify-between text-[11px]">
                    <span class="text-neutral-600">{card.title}</span>
                    <span class="font-semibold tabular-nums {card.valueClass}">{fmtKpi(card)}</span>
                  </div>
                  <div class="h-1.5 rounded-full bg-neutral-200">
                    <div
                      class="h-1.5 rounded-full {kpiBarClass(card.valueClass)}"
                      style="width: {Math.max(8, Math.round((Math.abs(card.value) / Math.max(crossModuleKpiMax, 1)) * 100))}%"
                    ></div>
                  </div>
                </div>
              {/each}
            </div>
          </div>
        {/if}
      </div>
    </div>

    {#if hasAnalytics}
      <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {#if hasProjects}
          <div class="rounded-xl border border-neutral-200 border-t-4 border-t-rose-500 bg-white p-4">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Construction Budget Burn</p>
            <p class="mt-1 text-2xl font-bold tabular-nums text-rose-700">{constructionBudgetBurn.burnRate.toFixed(1)}%</p>
            <div class="mt-3 h-2 overflow-hidden rounded-full bg-rose-50">
              <div
                class="h-full rounded-full bg-rose-500"
                style="width: {Math.min(100, Math.max(0, constructionBudgetBurn.burnRate))}%"
              ></div>
            </div>
            <p class="mt-2 text-xs text-neutral-500">
              Planned {fmtCompactMoney(constructionBudgetBurn.planned)} · Actual {fmtCompactMoney(constructionBudgetBurn.actual)}
            </p>
            <p class="mt-1 text-[11px] text-neutral-400">{constructionBudgetBurn.projectCount} active project budgets</p>
          </div>
        {/if}

        {#if hasProperties}
          <div class="rounded-xl border border-neutral-200 border-t-4 border-t-lime-500 bg-white p-4">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Property Inventory</p>
            <p class="mt-1 text-2xl font-bold tabular-nums text-lime-700">{propertyInventory.total.toLocaleString("en-US")}</p>
            <p class="mt-2 text-xs text-neutral-500">
              {propertyInventory.available} available · {propertyInventory.reserved} reserved · {propertyInventory.sold} sold
            </p>
            <p class="mt-1 text-[11px] text-neutral-400">{propertyInventory.leased} currently leased</p>
          </div>
        {/if}

        {#if hasProcurement}
          <div class="rounded-xl border border-neutral-200 border-t-4 border-t-amber-500 bg-white p-4">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Procurement Commitments</p>
            <p class="mt-1 text-2xl font-bold tabular-nums text-amber-700">{fmtCompactMoney(procurementCommitments.amount)}</p>
            <p class="mt-2 text-xs text-neutral-500">{procurementCommitments.openCommitments} open commitments</p>
            <p class="mt-1 text-[11px] text-neutral-400">
              {procurementCommitments.overdueDeliveries} overdue deliveries · {procurementCommitments.pendingRequisitions} pending requisitions
            </p>
          </div>
        {/if}

        {#if hasProperties}
          <div class="rounded-xl border border-neutral-200 border-t-4 border-t-cyan-500 bg-white p-4">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Rental Occupancy</p>
            <p class="mt-1 text-2xl font-bold tabular-nums text-cyan-700">{rentalOccupancy.pct.toFixed(1)}%</p>
            <div class="mt-3 h-2 overflow-hidden rounded-full bg-cyan-50">
              <div
                class="h-full rounded-full bg-cyan-500"
                style="width: {Math.min(100, Math.max(0, rentalOccupancy.pct))}%"
              ></div>
            </div>
            <p class="mt-2 text-xs text-neutral-500">
              {rentalOccupancy.leased} leased out of {rentalOccupancy.total} units
            </p>
          </div>
        {/if}

        {#if hasProperties}
          <div class="rounded-xl border border-neutral-200 border-t-4 border-t-orange-500 bg-white p-4">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Maintenance Backlog</p>
            <p class="mt-1 text-2xl font-bold tabular-nums text-orange-700">{maintenanceBacklog.total.toLocaleString("en-US")}</p>
            <p class="mt-2 text-xs text-neutral-500">
              {maintenanceBacklog.openWorkOrders} work orders · {maintenanceBacklog.openServiceRequests} service requests
            </p>
            <p class="mt-1 text-[11px] text-neutral-400">
              {maintenanceBacklog.urgentWorkOrders} urgent · {maintenanceBacklog.pendingInspections} pending inspections
            </p>
          </div>
        {/if}

        {#if hasFinance}
          <div class="rounded-xl border border-neutral-200 border-t-4 border-t-blue-500 bg-white p-4">
            <div class="mb-2 flex items-center justify-between">
              <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Cash Flow Forecast</p>
              <span class="text-[10px] text-neutral-400">90 days</span>
            </div>
            <p class="text-xl font-bold tabular-nums text-blue-700">{fmtCompactMoney(cashFlowForecast.projectedBalance)}</p>
            <p class="mt-1 text-[11px] text-neutral-500">
              Avg monthly net: {cashFlowForecast.avgMonthlyNet >= 0 ? "+" : ""}{fmtCompactMoney(cashFlowForecast.avgMonthlyNet)}
            </p>
            <div class="mt-3">
              <AreaChart
                data={cashFlowForecast.series}
                formatX={(d: unknown) => (d as Date).toLocaleDateString("en-US", { month: "short" })}
                formatY={(d: unknown) => fmtCompactMoney(Number(d || 0))}
                color="#2563eb"
                height={150}
              />
            </div>
          </div>
        {/if}
      </div>
    {/if}

    {#if hasFinance}
      <div class="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div class="rounded-xl border border-neutral-200 bg-white p-5 xl:col-span-2">
          <div class="mb-4 flex items-center justify-between">
            <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Monthly Inflows vs Outflows</h2>
            <span class="text-xs text-neutral-400">Monthly</span>
          </div>
          <GroupedBarChart
            data={monthlyCashFlow}
            label1="Monthly Inflows"
            label2="Monthly Outflows"
            color1="#f9a8d4"
            color2="#db2777"
            formatValue={(value: number) => fmtCompactMoney(value)}
            height={290}
          />
        </div>

        <div class="rounded-xl border border-neutral-200 bg-white p-5">
          <div class="mb-4 flex items-center justify-between">
            <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Rent Income</h2>
            <span class="text-xs text-neutral-400">Monthly</span>
          </div>
          <BarChart
            data={rentIncome}
            formatValue={(value: number) => fmtCompactMoney(value)}
            colors={["#dbeafe", "#bfdbfe", "#93c5fd", "#60a5fa", "#3b82f6", "#2563eb", "#1d4ed8"]}
            height={290}
          />
        </div>
      </div>
    {/if}

    {#if hasFinance || hasAnalytics}
      <div class="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div class="rounded-xl border border-neutral-200 bg-white p-5 {hasFinance ? 'xl:col-span-2' : 'xl:col-span-3'}">
          <div class="mb-4 flex items-center justify-between">
            <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Listed vs Offer Price for Rejections</h2>
            <span class="text-xs text-neutral-400">Live</span>
          </div>
          <GroupedBarChart
            data={listedVsOffer}
            label1="Offer Price"
            label2="Listed Price"
            color1="#3f3f46"
            color2="#d4d4d8"
            formatValue={(value: number) => fmtCompactMoney(value)}
            height={290}
          />
        </div>

        {#if hasFinance}
          <div class="rounded-xl border border-neutral-200 bg-white p-5">
            <h2 class="mb-4 text-sm font-semibold uppercase tracking-wider text-neutral-900">Funds & Escrow</h2>
            <div class="flex justify-center">
              <DonutChart
                data={fundsEscrowChart}
                centerValue={fmtCompactMoney(roundCurrency(fundsEscrow.reduce((sum, item) => sum + item.value, 0)))}
                centerLabel="Total"
                size={210}
                colors={["#84cc16", "#16a34a", "#dc2626"]}
                formatValue={(value: number) => fmtCompactMoney(value)}
              />
            </div>
            <div class="mt-4 space-y-2 border-t border-neutral-100 pt-4">
              <div class="flex items-center justify-between text-xs text-neutral-500">
                <span>Total Funds</span>
                <span class="font-semibold tabular-nums text-neutral-900">{fmtMoney(fundBalance)}</span>
              </div>
              <div class="flex items-center justify-between text-xs text-neutral-500">
                <span>Inflow</span>
                <span class="font-semibold tabular-nums text-emerald-700">{fmtMoney(inflowValue)}</span>
              </div>
              <div class="flex items-center justify-between text-xs text-neutral-500">
                <span>Outflow</span>
                <span class="font-semibold tabular-nums text-red-700">{fmtMoney(outflowValue)}</span>
              </div>
            </div>
          </div>
        {/if}
      </div>
    {/if}

    <div class="grid grid-cols-1 gap-6 {hasFinance ? 'xl:grid-cols-3' : 'xl:grid-cols-2'}">
      <div class="overflow-hidden rounded-xl border border-neutral-200 bg-white">
        <div class="border-b border-neutral-100 px-5 py-4">
          <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Pending Property Approvals</h2>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full min-w-[420px] text-left">
            <thead>
              <tr class="text-[10px] uppercase tracking-wider text-neutral-400">
                <th class="px-5 py-3 font-semibold">Property</th>
                <th class="px-5 py-3 font-semibold">Manager</th>
                <th class="px-5 py-3 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100 text-sm text-neutral-700">
              {#if pendingApprovals.length > 0}
                {#each pendingApprovals as row}
                  <tr>
                    <td class="px-5 py-3.5 font-medium text-neutral-900">{row.property}</td>
                    <td class="px-5 py-3.5">{row.manager}</td>
                    <td class="px-5 py-3.5">
                      <span class="rounded-full px-2 py-0.5 text-xs font-medium {approvalStatusClass(row.status)}">{row.status}</span>
                    </td>
                  </tr>
                {/each}
              {:else}
                <tr>
                  <td class="px-5 py-4 text-sm text-neutral-400" colspan="3">No pending approval data.</td>
                </tr>
              {/if}
            </tbody>
          </table>
        </div>
      </div>

      {#if hasFinance}
        <div class="overflow-hidden rounded-xl border border-neutral-200 bg-white">
          <div class="border-b border-neutral-100 px-5 py-4">
            <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Scheduled Payouts</h2>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full min-w-[360px] text-left">
              <thead>
                <tr class="text-[10px] uppercase tracking-wider text-neutral-400">
                  <th class="px-5 py-3 font-semibold">Period</th>
                  <th class="px-5 py-3 font-semibold">Amount</th>
                  <th class="px-5 py-3 font-semibold">Status</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100 text-sm text-neutral-700">
                {#if scheduledPayouts.length > 0}
                  {#each scheduledPayouts as row}
                    <tr>
                      <td class="px-5 py-3.5">{row.period}</td>
                      <td class="px-5 py-3.5 font-medium tabular-nums text-neutral-900">{fmtMoney(row.amount)}</td>
                      <td class="px-5 py-3.5">
                        <span class="rounded-full px-2 py-0.5 text-xs font-medium {payoutStatusClass(row.status)}">{row.status}</span>
                      </td>
                    </tr>
                  {/each}
                {:else}
                  <tr>
                    <td class="px-5 py-4 text-sm text-neutral-400" colspan="3">No payout data available.</td>
                  </tr>
                {/if}
              </tbody>
            </table>
          </div>
        </div>
      {/if}

      <div class="rounded-xl border border-neutral-200 bg-white p-5">
        <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Properties & Location</h2>
        <p class="mt-1 text-xs text-neutral-400">Regional portfolio exposure and occupancy ({selectedRegionLabel})</p>

        <div class="mt-4 space-y-2">
          {#if regionalPortfolio.length > 0}
            {#each regionalPortfolio as region}
              <div>
                <div class="mb-1 flex items-center justify-between text-xs">
                  <span class="text-neutral-600">{region.region}</span>
                  <span class="font-medium tabular-nums text-neutral-900">{fmtCompactMoney(region.value)}</span>
                </div>
                <div class="h-2 rounded-full bg-neutral-100">
                  <div
                    class="h-2 rounded-full bg-linear-to-r from-orange-500 via-violet-500 to-indigo-500"
                    style="width: {Math.max(8, Math.round((region.value / Math.max(topRegionalValue, 1)) * 100))}%"
                  ></div>
                </div>
              </div>
            {/each}
          {:else}
            <p class="text-sm text-neutral-400">No regional data available.</p>
          {/if}
        </div>

        <div class="mt-5 space-y-3 border-t border-neutral-100 pt-4">
          {#if locationCards.length > 0}
            {#each locationCards as item}
              <div class="rounded-lg border border-neutral-100 px-3 py-2.5">
                <p class="text-sm font-medium text-neutral-900">{item.name}</p>
                <div class="mt-1 flex items-center justify-between text-xs text-neutral-500">
                  <span>{item.location}</span>
                  <span class="font-medium text-neutral-700">{item.occupancy} occupied</span>
                </div>
              </div>
            {/each}
          {:else}
            <p class="text-sm text-neutral-400">No location cards available.</p>
          {/if}
        </div>
      </div>
    </div>
  </div>
{/if}

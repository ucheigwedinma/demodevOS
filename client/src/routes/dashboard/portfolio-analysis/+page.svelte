<script lang="ts">
  import { goto } from "$app/navigation";
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import DonutChart from "$lib/components/charts/DonutChart.svelte";
  import AreaChart from "$lib/components/charts/AreaChart.svelte";
  import HorizontalBarChart from "$lib/components/charts/HorizontalBarChart.svelte";
  import GroupedBarChart from "$lib/components/charts/GroupedBarChart.svelte";
  import BarChart from "$lib/components/charts/BarChart.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import type {
    DocumentRecord,
    PortfolioAnalytics,
    FinanceOverview,
    InvoiceListItem,
    MyApprovalItem,
    ProjectListItem,
    PaginatedResponse,
    WorkflowInstanceListItem,
  } from "$lib/types";

  let portfolio = $state<PortfolioAnalytics | null>(null);
  let finance = $state<FinanceOverview | null>(null);
  let projects = $state<ProjectListItem[]>([]);
  let workflowApprovals = $state<MyApprovalItem[]>([]);
  let openApprovalPoolCount = $state(0);
  let invoices = $state<InvoiceListItem[]>([]);
  let contractDocuments = $state<DocumentRecord[]>([]);
  let loading = $state(true);

  async function fetchAllPages<T>(
    endpoint: string,
    params: Record<string, string> = {},
    maxPages = 5,
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

  async function fetchAll() {
    loading = true;
    try {
      const [p, f, proj] = await Promise.all([
        api.get<PortfolioAnalytics>("/analytics/portfolio/"),
        api.get<FinanceOverview>("/finance/overview/"),
        api.get<PaginatedResponse<ProjectListItem>>("/projects/", {
          page_size: "200",
          ordering: "-created_at",
        }),
      ]);
      portfolio = p;
      finance = f;
      projects = proj.results;

      const [approvalsRes, pendingRes, inProgressRes, invoicesRes, contractsRes] = await Promise.allSettled([
        api.get<MyApprovalItem[]>("/workflows/my-approvals/"),
        api.get<PaginatedResponse<WorkflowInstanceListItem>>("/workflows/instances/", {
          state: "pending",
          page_size: "1",
        }),
        api.get<PaginatedResponse<WorkflowInstanceListItem>>("/workflows/instances/", {
          state: "in_progress",
          page_size: "1",
        }),
        fetchAllPages<InvoiceListItem>("/finance/invoices/", {
          ordering: "-issue_date",
          page_size: "200",
        }),
        fetchAllPages<DocumentRecord>("/documents/records/", {
          category: "CON",
          ordering: "-created_at",
          page_size: "200",
        }),
      ]);

      workflowApprovals = approvalsRes.status === "fulfilled" ? approvalsRes.value : [];
      const pendingCount = pendingRes.status === "fulfilled" ? pendingRes.value.count : 0;
      const inProgressCount = inProgressRes.status === "fulfilled" ? inProgressRes.value.count : 0;
      openApprovalPoolCount = pendingCount + inProgressCount;
      invoices = invoicesRes.status === "fulfilled" ? invoicesRes.value : [];
      contractDocuments = contractsRes.status === "fulfilled" ? contractsRes.value : [];
    } catch {
      toast.error("Failed to load", "Could not fetch dashboard data");
    }
    loading = false;
  }

  $effect(() => {
    fetchAll();
  });

  // ── Formatters ──────────────────────────────────────────────────────

  function fmtCurrency(n: number | string): string {
    const val = typeof n === "string" ? Number(n) : n;
    if (Number.isNaN(val)) return currency.formatCompact(0);
    return currency.formatAbbreviated(val);
  }

  function fmtPct(n: string): string {
    const val = Number(n);
    return (val >= 0 ? "+" : "") + val.toFixed(1) + "%";
  }

  function fmtMonth(d: unknown): string {
    if (d instanceof Date) {
      return d.toLocaleDateString("en-US", { month: "short", year: "2-digit" });
    }
    return String(d);
  }

  function fmtDate(d: string | null): string {
    if (!d) return "--";
    return new Date(d).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    });
  }

  function daysUntil(d: string | null): number | null {
    if (!d) return null;
    const diff = new Date(d).getTime() - Date.now();
    return Math.ceil(diff / (1000 * 60 * 60 * 24));
  }

  function toAmount(value: string | number | null | undefined): number {
    if (typeof value === "number") return Number.isFinite(value) ? value : 0;
    const parsed = Number(value ?? 0);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function clamp(value: number, min = 0, max = 100): number {
    return Math.min(Math.max(value, min), max);
  }

  // ── Label maps ──────────────────────────────────────────────────────

  const statusLabels: Record<string, string> = {
    planning: "Planning",
    in_progress: "In Progress",
    on_hold: "On Hold",
    completed: "Completed",
  };

  const statusColors: Record<string, string> = {
    planning: "bg-blue-100 text-blue-700",
    in_progress: "bg-neutral-900 text-white",
    on_hold: "bg-amber-100 text-amber-700",
    completed: "bg-emerald-100 text-emerald-700",
  };

  const typeLabels: Record<string, string> = {
    land: "Land",
    building: "Building",
    mixed: "Mixed-Use",
    estate: "Estate",
    warehouse: "Warehouse",
    industrial: "Industrial",
  };

  const unitStatusLabels: Record<string, string> = {
    available: "Available",
    reserved: "Reserved",
    sold: "Sold",
    leased: "Leased",
  };

  const classLabels: Record<string, string> = {
    owned: "Owned",
    lease: "Lease",
    concession: "Concession",
    under_development: "Under Dev.",
  };

  const encumbranceLabels: Record<string, string> = {
    mortgage: "Mortgage",
    lien: "Lien",
    legal_dispute: "Legal Dispute",
    court_case: "Court Case",
    tax_arrears: "Tax Arrears",
  };

  // ── Derived data ────────────────────────────────────────────────────

  const gain = $derived(Number(portfolio?.kpis.unrealized_gain ?? 0));
  const gainPositive = $derived(gain >= 0);

  const totalPayable = $derived(Number(finance?.total_payable ?? 0));
  const totalReceivable = $derived(Number(finance?.total_receivable ?? 0));
  const netCashPosition = $derived(totalReceivable - totalPayable);

  const salesVelocity = $derived.by(() => {
    const now = new Date();
    const currentStart = new Date(now);
    currentStart.setDate(now.getDate() - 30);
    const previousStart = new Date(currentStart);
    previousStart.setDate(currentStart.getDate() - 30);

    let currentCount = 0;
    let currentValue = 0;
    let previousCount = 0;
    let previousValue = 0;

    for (const invoice of invoices) {
      if (invoice.status === "draft" || invoice.status === "cancelled") continue;
      const issueDate = new Date(invoice.issue_date);
      if (Number.isNaN(issueDate.getTime())) continue;
      const amount = toAmount(invoice.total_amount);

      if (issueDate >= currentStart && issueDate <= now) {
        currentCount += 1;
        currentValue += amount;
      } else if (issueDate >= previousStart && issueDate < currentStart) {
        previousCount += 1;
        previousValue += amount;
      }
    }

    const valueDeltaPct = previousValue > 0
      ? ((currentValue - previousValue) / previousValue) * 100
      : currentValue > 0 ? 100 : 0;

    return {
      currentCount,
      currentValue,
      previousCount,
      previousValue,
      valueDeltaPct,
    };
  });

  const openApprovalsCount = $derived(
    openApprovalPoolCount > 0 ? openApprovalPoolCount : workflowApprovals.length
  );

  const slaSignals = $derived.by(() => {
    const now = Date.now();
    const soonWindowMs = 48 * 60 * 60 * 1000;
    let breached = 0;
    let dueSoon = 0;

    for (const item of workflowApprovals) {
      if (item.sla_breached) {
        breached += 1;
        continue;
      }
      if (!item.sla_deadline) continue;
      const deadline = new Date(item.sla_deadline).getTime();
      if (Number.isNaN(deadline)) continue;
      if (deadline >= now && deadline <= now + soonWindowMs) {
        dueSoon += 1;
      }
    }

    return { breached, dueSoon, total: breached + dueSoon };
  });

  const contractExposure = $derived.by(() => {
    let activeCount = 0;
    let activeValue = 0;
    let pendingHighValueCount = 0;
    let pendingValue = 0;

    for (const doc of contractDocuments) {
      const value = toAmount(doc.contract_value);
      const isActive = doc.status !== "archived" && doc.status !== "superseded";
      const isPending = doc.status === "submitted" || doc.status === "under_review";

      if (isActive) {
        activeCount += 1;
        activeValue += value;
      }
      if (isPending) {
        pendingValue += value;
        if (value >= 100_000) {
          pendingHighValueCount += 1;
        }
      }
    }

    return { activeCount, activeValue, pendingHighValueCount, pendingValue };
  });

  type OperationalSignal = {
    key: string;
    label: string;
    value: string;
    detail: string;
    meta: string;
    href: string;
    health: number;
    state: "healthy" | "watch" | "critical";
  };

  const operationalSignals = $derived.by(() => {
    const salesHealth = clamp(50 + salesVelocity.valueDeltaPct, 0, 100);
    const approvalsHealth = openApprovalsCount > 0
      ? clamp(100 - (slaSignals.dueSoon / openApprovalsCount) * 100, 0, 100)
      : 100;
    const slaWeight = slaSignals.breached * 2 + slaSignals.dueSoon;
    const slaHealth = openApprovalsCount > 0
      ? clamp(100 - (slaWeight / openApprovalsCount) * 100, 0, 100)
      : slaSignals.total > 0 ? clamp(100 - slaSignals.total * 20, 0, 100) : 100;
    const contractHealth = contractExposure.activeCount > 0
      ? clamp(100 - (contractExposure.pendingHighValueCount / contractExposure.activeCount) * 100, 0, 100)
      : 100;

    return [
      {
        key: "sales",
        label: "Sales Velocity (30d)",
        value: String(salesVelocity.currentCount),
        detail: `${fmtCurrency(salesVelocity.currentValue)} billed`,
        meta: `${salesVelocity.valueDeltaPct >= 0 ? "+" : ""}${salesVelocity.valueDeltaPct.toFixed(1)}% vs prior 30d`,
        href: "/finance/invoices",
        health: salesHealth,
        state: salesVelocity.valueDeltaPct >= 0 ? "healthy" : "watch",
      },
      {
        key: "approvals",
        label: "Open Approvals",
        value: String(openApprovalsCount),
        detail: `${slaSignals.dueSoon} due in 48h`,
        meta: `${workflowApprovals.length} assigned approvals`,
        href: "/settings/workflows",
        health: approvalsHealth,
        state: slaSignals.dueSoon > 0 ? "watch" : "healthy",
      },
      {
        key: "sla",
        label: "SLA Alerts",
        value: String(slaSignals.total),
        detail: `${slaSignals.breached} breached · ${slaSignals.dueSoon} due soon`,
        meta: slaSignals.breached > 0 ? "Immediate intervention required" : "Monitor before breach window",
        href: "/settings/workflows",
        health: slaHealth,
        state: slaSignals.breached > 0 ? "critical" : slaSignals.dueSoon > 0 ? "watch" : "healthy",
      },
      {
        key: "contracts",
        label: "Contract Exposure",
        value: fmtCurrency(contractExposure.activeValue),
        detail: `${contractExposure.activeCount} active contracts`,
        meta: `${contractExposure.pendingHighValueCount} high-value pending approvals`,
        href: "/documents/dashboard",
        health: contractHealth,
        state: contractExposure.pendingHighValueCount > 0 ? "watch" : "healthy",
      },
    ] as OperationalSignal[];
  });

  type WorkloadRow = {
    manager: string;
    activeProjects: number;
    atRisk: number;
    avgProgress: number;
  };

  const workloadRows = $derived.by(() => {
    const byManager = new Map<string, { activeProjects: number; atRisk: number; progressTotal: number }>();

    for (const project of projects) {
      if (project.status === "completed") continue;
      const manager = project.project_manager?.trim() || "Unassigned";
      const existing = byManager.get(manager) ?? { activeProjects: 0, atRisk: 0, progressTotal: 0 };
      existing.activeProjects += 1;
      existing.progressTotal += Number(project.progress || 0);
      const overdue = (daysUntil(project.target_end_date) ?? 0) < 0;
      const highRisk = project.risk_rating === "high" || project.risk_rating === "critical";
      if (overdue || highRisk) existing.atRisk += 1;
      byManager.set(manager, existing);
    }

    return Array.from(byManager.entries())
      .map(([manager, value]) => ({
        manager,
        activeProjects: value.activeProjects,
        atRisk: value.atRisk,
        avgProgress: value.activeProjects > 0 ? value.progressTotal / value.activeProjects : 0,
      }))
      .sort((a, b) => {
        if (b.activeProjects !== a.activeProjects) return b.activeProjects - a.activeProjects;
        if (b.atRisk !== a.atRisk) return b.atRisk - a.atRisk;
        return a.manager.localeCompare(b.manager);
      })
      .slice(0, 5) as WorkloadRow[];
  });

  // Alerts requiring attention
  const alerts = $derived.by(() => {
    const items: { severity: "critical" | "warning" | "info"; message: string; href: string }[] = [];
    if (finance) {
      if (finance.overdue_payable_count > 0) {
        items.push({
          severity: "critical",
          message: `${finance.overdue_payable_count} overdue bill${finance.overdue_payable_count > 1 ? "s" : ""} totaling ${fmtCurrency(finance.overdue_payable_amount)}`,
          href: "/finance/bills",
        });
      }
      if (finance.overdue_receivable_count > 0) {
        items.push({
          severity: "warning",
          message: `${finance.overdue_receivable_count} overdue invoice${finance.overdue_receivable_count > 1 ? "s" : ""} — ${fmtCurrency(finance.overdue_receivable_amount)} uncollected`,
          href: "/finance/invoices",
        });
      }
    }
    if (portfolio) {
      if (portfolio.encumbrance_summary.total_count > 0) {
        items.push({
          severity: "warning",
          message: `${portfolio.encumbrance_summary.total_count} active encumbrance${portfolio.encumbrance_summary.total_count > 1 ? "s" : ""} worth ${fmtCurrency(portfolio.encumbrance_summary.total_amount)}`,
          href: "/properties",
        });
      }
    }
    const onHold = projects.filter((p) => p.status === "on_hold");
    if (onHold.length > 0) {
      items.push({
        severity: "info",
        message: `${onHold.length} project${onHold.length > 1 ? "s" : ""} on hold`,
        href: "/projects",
      });
    }
    return items;
  });

  // Active projects (not completed)
  const activeProjects = $derived(
    projects.filter((p) => p.status !== "completed").slice(0, 8)
  );

  // Project status distribution
  const projectStatusCounts = $derived.by(() => {
    const counts: Record<string, number> = { planning: 0, in_progress: 0, on_hold: 0, completed: 0 };
    projects.forEach((p) => {
      if (counts[p.status] !== undefined) counts[p.status]++;
    });
    return counts;
  });

  // Valuation trend
  const valuationData = $derived(
    (portfolio?.valuation_history ?? []).map((v) => ({
      x: new Date(v.month),
      y: Number(v.total_value),
    }))
  );

  // Unit occupancy
  const unitData = $derived(
    (portfolio?.unit_occupancy ?? []).map((u) => ({
      label: unitStatusLabels[u.status] ?? u.status,
      value: u.count,
    }))
  );

  const typeData = $derived(
    (portfolio?.type_distribution ?? []).map((item) => ({
      label: typeLabels[item.type] ?? item.type,
      value: Number(item.total_value),
    }))
  );

  const classData = $derived(
    (portfolio?.classification_breakdown ?? []).map((item) => ({
      label: classLabels[item.classification] ?? item.classification,
      value: item.count,
    }))
  );

  const budgetData = $derived(
    (portfolio?.project_budget_summary ?? []).map((item) => ({
      label: item.name,
      value1: Number(item.total_planned || 0),
      value2: Number(item.total_actual || 0),
    }))
  );

  const encumbranceData = $derived(
    (portfolio?.encumbrance_summary.by_type ?? []).map((item) => ({
      label: encumbranceLabels[item.type] ?? item.type,
      value: Number(item.total_amount || 0),
    }))
  );

  const totalUnits = $derived(
    unitData.reduce((sum, u) => sum + u.value, 0)
  );

</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
  </div>
{:else}
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-start justify-between">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-violet-600">Dashboard</p>
        <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Portfolio Analysis</h1>
        <p class="text-sm text-neutral-500 mt-1">
          Valuation trend, project delivery, classification mix, and cash-flow activity across the portfolio.
        </p>
      </div>
      <button
        onclick={() => fetchAll()}
        class="flex items-center gap-2 px-3 py-2 text-sm text-neutral-500 hover:text-neutral-900 hover:bg-neutral-100 rounded-lg transition-colors"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182" />
        </svg>
        Refresh
      </button>
    </div>

    <!-- Alerts -->
    {#if alerts.length > 0}
      <div class="space-y-2">
        {#each alerts as alert}
          <a
            href={alert.href}
            class="flex items-center gap-3 px-4 py-3 rounded-xl border transition-colors
                   {alert.severity === 'critical'
                     ? 'bg-red-50 border-red-200 hover:bg-red-100'
                     : alert.severity === 'warning'
                       ? 'bg-amber-50 border-amber-200 hover:bg-amber-100'
                       : 'bg-blue-50 border-blue-200 hover:bg-blue-100'}"
          >
            {#if alert.severity === "critical"}
              <svg class="w-4 h-4 text-red-600 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
              </svg>
              <span class="text-sm font-medium text-red-800">{alert.message}</span>
            {:else if alert.severity === "warning"}
              <svg class="w-4 h-4 text-amber-600 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
              </svg>
              <span class="text-sm font-medium text-amber-800">{alert.message}</span>
            {:else}
              <svg class="w-4 h-4 text-blue-600 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z" />
              </svg>
              <span class="text-sm font-medium text-blue-800">{alert.message}</span>
            {/if}
            <svg class="w-4 h-4 ml-auto text-neutral-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
            </svg>
          </a>
        {/each}
      </div>
    {/if}

    <!-- Portfolio KPI Strip -->
    {#if portfolio}
      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        <a href="/dashboard/portfolio-analysis" class="bg-white rounded-xl border border-neutral-200 border-t-4 border-t-amber-500 p-4 hover:border-neutral-300 transition-colors">
          <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Portfolio Value</p>
          <p class="mt-1 text-lg font-bold text-neutral-900 tabular-nums">{fmtCurrency(portfolio.kpis.total_value)}</p>
        </a>

        <a href="/properties" class="bg-white rounded-xl border border-neutral-200 border-t-4 border-t-violet-500 p-4 hover:border-neutral-300 transition-colors">
          <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Properties</p>
          <p class="mt-1 text-lg font-bold text-neutral-900 tabular-nums">{portfolio.kpis.property_count}</p>
        </a>

        <a href="/dashboard/portfolio-analysis" class="bg-white rounded-xl border border-neutral-200 border-t-4 {gainPositive ? 'border-t-emerald-500' : 'border-t-rose-500'} p-4 hover:border-neutral-300 transition-colors">
          <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Unrealized Gain</p>
          <p class="mt-1 text-lg font-bold tabular-nums {gainPositive ? 'text-emerald-600' : 'text-red-600'}">
            {gainPositive ? "+" : ""}{fmtCurrency(portfolio.kpis.unrealized_gain)}
          </p>
        </a>

        <a href="/finance" class="bg-white rounded-xl border border-neutral-200 border-t-4 border-t-orange-700 p-4 hover:border-neutral-300 transition-colors">
          <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Receivable</p>
          <p class="mt-1 text-lg font-bold text-emerald-600 tabular-nums">{fmtCurrency(totalReceivable)}</p>
        </a>

        <a href="/finance" class="bg-white rounded-xl border border-neutral-200 border-t-4 border-t-rose-500 p-4 hover:border-neutral-300 transition-colors">
          <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Payable</p>
          <p class="mt-1 text-lg font-bold text-red-600 tabular-nums">{fmtCurrency(totalPayable)}</p>
        </a>

        <div class="bg-white rounded-xl border border-neutral-200 border-t-4 border-t-sky-500 p-4">
          <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Net Position</p>
          <p class="mt-1 text-lg font-bold tabular-nums {netCashPosition >= 0 ? 'text-emerald-600' : 'text-red-600'}">
            {netCashPosition >= 0 ? "+" : ""}{fmtCurrency(netCashPosition)}
          </p>
        </div>
      </div>
    {/if}

    <!-- Operational Signals -->
    <section class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      <div class="px-5 py-4 border-b border-neutral-100 flex items-center justify-between">
        <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Operational Signal Board</h3>
        <span class="text-xs text-neutral-400">Live feed across sales, workflows, and contracts</span>
      </div>
      <div class="divide-y divide-neutral-100">
        {#each operationalSignals as signal}
          <a
            href={signal.href}
            class="group grid gap-4 px-5 py-3.5 transition-colors hover:bg-neutral-50 md:grid-cols-[170px_minmax(0,1fr)_auto]"
          >
            <div class="min-w-0">
              <p class="truncate text-[10px] font-semibold uppercase tracking-wider text-neutral-400">{signal.label}</p>
              <p class="mt-1 text-xl font-bold tabular-nums text-neutral-900">{signal.value}</p>
            </div>

            <div class="min-w-0">
              <p class="truncate text-sm text-neutral-700">{signal.detail}</p>
              <div class="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-neutral-100">
                <div
                  class="h-full rounded-full
                    {signal.state === 'critical'
                      ? 'bg-rose-500'
                      : signal.state === 'watch'
                        ? 'bg-amber-500'
                        : 'bg-emerald-500'}"
                  style="width: {signal.health}%;"
                ></div>
              </div>
              <p
                class="mt-1 text-[11px] font-medium
                  {signal.state === 'critical'
                    ? 'text-rose-600'
                    : signal.state === 'watch'
                      ? 'text-amber-700'
                      : 'text-emerald-600'}"
              >
                {signal.meta}
              </p>
            </div>

            <div class="flex items-center gap-2 justify-self-end">
              <span
                class="rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider
                  {signal.state === 'critical'
                    ? 'bg-rose-100 text-rose-700'
                    : signal.state === 'watch'
                      ? 'bg-amber-100 text-amber-700'
                      : 'bg-emerald-100 text-emerald-700'}"
              >
                {signal.state}
              </span>
              <svg class="h-4 w-4 text-neutral-300 transition-colors group-hover:text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="m9 6 6 6-6 6" />
              </svg>
            </div>
          </a>
        {/each}
      </div>
    </section>

    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      <div class="px-5 py-4 border-b border-neutral-100 flex items-center justify-between">
        <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Team Workload Snapshot</h3>
        <a href="/projects/execution-stats" class="text-xs text-neutral-400 hover:text-neutral-700 transition-colors">Execution stats &rarr;</a>
      </div>
      {#if workloadRows.length === 0}
        <div class="px-5 py-10 text-center">
          <p class="text-sm text-neutral-400">No active assignments yet.</p>
        </div>
      {:else}
        <div class="divide-y divide-neutral-100">
          {#each workloadRows as row}
            <div class="px-5 py-3.5">
              <div class="flex items-center justify-between gap-3">
                <p class="text-sm font-medium text-neutral-900 truncate">{row.manager}</p>
                <div class="flex items-center gap-3 text-[11px] text-neutral-500 tabular-nums">
                  <span>{row.activeProjects} active</span>
                  <span class="{row.atRisk > 0 ? 'text-rose-600 font-medium' : 'text-neutral-500'}">
                    {row.atRisk} at risk
                  </span>
                  <span>{row.avgProgress.toFixed(0)}% avg progress</span>
                </div>
              </div>
              <div class="mt-2 h-1.5 w-full rounded-full bg-neutral-100 overflow-hidden">
                <div
                  class="h-1.5 rounded-full {row.avgProgress >= 75 ? 'bg-emerald-500' : row.avgProgress >= 45 ? 'bg-blue-600' : 'bg-amber-500'}"
                  style="width: {Math.min(Math.max(row.avgProgress, 0), 100)}%"
                ></div>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>

    <!-- Main Grid: Revenue Trend + Project Heatmap -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Portfolio Valuation Trend (2 col span) -->
      <div class="lg:col-span-2 bg-white rounded-xl border border-neutral-200 p-6">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Portfolio Valuation Trend</h3>
          <a href="/dashboard/portfolio-analysis" class="text-xs text-neutral-400 hover:text-neutral-700 transition-colors">Portfolio &rarr;</a>
        </div>
        {#if valuationData.length > 1}
          <AreaChart
            data={valuationData}
            formatX={fmtMonth}
            formatY={(d: unknown) => fmtCurrency(d as number)}
            height={240}
          />
        {:else}
          <div class="h-[240px] flex items-center justify-center">
            <div class="text-center">
              <svg class="w-10 h-10 mx-auto text-neutral-200" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
              </svg>
              <p class="mt-2 text-sm text-neutral-400">Add property valuations to see the trend</p>
            </div>
          </div>
        {/if}
      </div>

      <!-- Project Status Heatmap -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6">
        <div class="flex items-center justify-between mb-5">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Project Status</h3>
          <a href="/projects" class="text-xs text-neutral-400 hover:text-neutral-700 transition-colors">All &rarr;</a>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <a
            href="/projects"
            class="rounded-xl p-4 text-center transition-colors bg-blue-50 hover:bg-blue-100 border border-blue-100"
          >
            <p class="text-2xl font-bold text-blue-700 tabular-nums">{projectStatusCounts.planning}</p>
            <p class="text-[10px] font-semibold text-blue-600 uppercase tracking-wider mt-1">Planning</p>
          </a>

          <a
            href="/projects"
            class="rounded-xl p-4 text-center transition-colors bg-neutral-900 hover:bg-neutral-800"
          >
            <p class="text-2xl font-bold text-white tabular-nums">{projectStatusCounts.in_progress}</p>
            <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider mt-1">In Progress</p>
          </a>

          <a
            href="/projects"
            class="rounded-xl p-4 text-center transition-colors bg-amber-50 hover:bg-amber-100 border border-amber-100"
          >
            <p class="text-2xl font-bold text-amber-700 tabular-nums">{projectStatusCounts.on_hold}</p>
            <p class="text-[10px] font-semibold text-amber-600 uppercase tracking-wider mt-1">On Hold</p>
          </a>

          <a
            href="/projects"
            class="rounded-xl p-4 text-center transition-colors bg-emerald-50 hover:bg-emerald-100 border border-emerald-100"
          >
            <p class="text-2xl font-bold text-emerald-700 tabular-nums">{projectStatusCounts.completed}</p>
            <p class="text-[10px] font-semibold text-emerald-600 uppercase tracking-wider mt-1">Completed</p>
          </a>
        </div>

        <!-- Unit Occupancy mini -->
        {#if totalUnits > 0}
          <div class="mt-5 pt-5 border-t border-neutral-100">
            <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider mb-3">Unit Occupancy</p>
            <div class="flex justify-center">
              <DonutChart
                data={unitData}
                colors={["#10b981", "#f59e0b", "#6366f1", "#06b6d4"]}
                centerValue={String(totalUnits)}
                centerLabel="Units"
                size={160}
              />
            </div>
          </div>
        {/if}
      </div>
    </div>

    <!-- Portfolio Mix & Execution Curves -->
    {#if portfolio}
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div class="bg-white rounded-xl border border-neutral-200 p-6">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Value by Property Type</h3>
          <HorizontalBarChart
            data={typeData}
            formatValue={fmtCurrency}
          />
        </div>

        <div class="bg-white rounded-xl border border-neutral-200 p-6">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Classification Breakdown</h3>
          <div class="flex justify-center">
            <DonutChart
              data={classData}
              centerValue={String(portfolio.kpis.property_count)}
              centerLabel="Properties"
              size={220}
            />
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div class="bg-white rounded-xl border border-neutral-200 p-6">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Project Budgets</h3>
          <GroupedBarChart
            data={budgetData}
            value1Key="value1"
            value2Key="value2"
            label1="Planned"
            label2="Actual"
            formatValue={fmtCurrency}
          />
        </div>

        <div class="bg-white rounded-xl border border-neutral-200 p-6">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Encumbrance Risk</h3>
          <BarChart
            data={encumbranceData}
            formatValue={fmtCurrency}
            colors={["#ef4444", "#f97316", "#f59e0b", "#8b5cf6", "#6366f1"]}
          />
        </div>
      </div>
    {/if}

    <!-- Bottom Grid: Active Projects + Financial Activity -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Active Projects -->
      <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
        <div class="px-5 py-4 border-b border-neutral-100 flex items-center justify-between">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Active Projects</h3>
          <a href="/projects" class="text-xs text-neutral-400 hover:text-neutral-700 transition-colors">View all &rarr;</a>
        </div>
        {#if activeProjects.length > 0}
          <div class="divide-y divide-neutral-50">
            {#each activeProjects as project}
              <button
                onclick={() => goto(`/projects/${project.id}`)}
                class="w-full px-5 py-3.5 flex items-center gap-4 hover:bg-neutral-50 transition-colors text-left"
              >
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2">
                    <p class="text-sm font-medium text-neutral-900 truncate">{project.name}</p>
                    <span class="inline-block px-2 py-0.5 rounded-full text-[10px] font-medium shrink-0 {statusColors[project.status] ?? 'bg-neutral-100 text-neutral-600'}">
                      {statusLabels[project.status] ?? project.status}
                    </span>
                  </div>
                  <p class="text-xs text-neutral-400 mt-0.5">{project.property_name}</p>
                </div>
                <div class="text-right shrink-0">
                  {#if project.budget}
                    <p class="text-xs font-medium text-neutral-900 tabular-nums">{fmtCurrency(project.budget)}</p>
                  {/if}
                  {#if project.target_end_date}
                    {@const days = daysUntil(project.target_end_date)}
                    <p class="text-[10px] tabular-nums {days !== null && days < 0 ? 'text-red-500 font-medium' : days !== null && days < 14 ? 'text-amber-500' : 'text-neutral-400'}">
                      {#if days !== null && days < 0}
                        {Math.abs(days)}d overdue
                      {:else if days !== null}
                        {days}d remaining
                      {/if}
                    </p>
                  {/if}
                </div>
                <!-- Progress bar -->
                <div class="w-16 shrink-0">
                  <div class="h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                    <div
                      class="h-full rounded-full transition-all {project.progress >= 100 ? 'bg-emerald-500' : project.progress >= 50 ? 'bg-neutral-900' : 'bg-neutral-400'}"
                      style="width: {Math.min(project.progress, 100)}%"
                    ></div>
                  </div>
                  <p class="text-[10px] text-neutral-400 text-center mt-0.5 tabular-nums">{project.progress}%</p>
                </div>
              </button>
            {/each}
          </div>
        {:else}
          <div class="px-5 py-12 text-center">
            <p class="text-sm text-neutral-400">No active projects</p>
          </div>
        {/if}
      </div>

      <!-- Cash Flow: Recent Bills + Invoices -->
      <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
        <div class="px-5 py-4 border-b border-neutral-100 flex items-center justify-between">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Cash Flow Activity</h3>
          <a href="/finance" class="text-xs text-neutral-400 hover:text-neutral-700 transition-colors">Finance hub &rarr;</a>
        </div>

        {#if finance}
          <!-- Cash summary row -->
          <div class="grid grid-cols-3 divide-x divide-neutral-100 border-b border-neutral-100">
            <div class="px-4 py-3 text-center">
              <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Incoming</p>
              <p class="mt-0.5 text-sm font-bold text-emerald-600 tabular-nums">{fmtCurrency(finance.total_receivable)}</p>
            </div>
            <div class="px-4 py-3 text-center">
              <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Outgoing</p>
              <p class="mt-0.5 text-sm font-bold text-red-600 tabular-nums">{fmtCurrency(finance.total_payable)}</p>
            </div>
            <div class="px-4 py-3 text-center">
              <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Overdue</p>
              <p class="mt-0.5 text-sm font-bold text-amber-600 tabular-nums">
                {finance.overdue_payable_count + finance.overdue_receivable_count}
              </p>
            </div>
          </div>

          <!-- Recent bills -->
          {#if finance.recent_bills.length > 0}
            <div class="px-4 pt-3 pb-1">
              <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Recent Bills</p>
            </div>
            <div class="divide-y divide-neutral-50">
              {#each finance.recent_bills.slice(0, 3) as bill}
                <button
                  onclick={() => goto(`/finance/bills/${bill.id}`)}
                  class="w-full px-4 py-2.5 flex items-center gap-3 hover:bg-neutral-50 transition-colors text-left"
                >
                  <div class="w-7 h-7 rounded-lg bg-red-50 flex items-center justify-center shrink-0">
                    <svg class="w-3.5 h-3.5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 19.5l15-15m0 0H8.25m11.25 0v11.25" />
                    </svg>
                  </div>
                  <div class="flex-1 min-w-0">
                    <p class="text-xs font-medium text-neutral-900 truncate">{bill.vendor_name}</p>
                    <p class="text-[10px] text-neutral-400">{bill.bill_number} &middot; Due {fmtDate(bill.due_date)}</p>
                  </div>
                  <div class="text-right shrink-0">
                    <p class="text-xs font-medium text-neutral-900 tabular-nums">{fmtCurrency(bill.total_amount)}</p>
                    {#if bill.is_overdue}
                      <p class="text-[10px] text-red-500 font-medium">{bill.days_overdue}d late</p>
                    {/if}
                  </div>
                </button>
              {/each}
            </div>
          {/if}

          <!-- Recent invoices -->
          {#if finance.recent_invoices.length > 0}
            <div class="px-4 pt-3 pb-1 border-t border-neutral-100">
              <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Recent Invoices</p>
            </div>
            <div class="divide-y divide-neutral-50">
              {#each finance.recent_invoices.slice(0, 3) as inv}
                <button
                  onclick={() => goto(`/finance/invoices/${inv.id}`)}
                  class="w-full px-4 py-2.5 flex items-center gap-3 hover:bg-neutral-50 transition-colors text-left"
                >
                  <div class="w-7 h-7 rounded-lg bg-emerald-50 flex items-center justify-center shrink-0">
                    <svg class="w-3.5 h-3.5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 4.5l-15 15m0 0h11.25m-11.25 0V8.25" />
                    </svg>
                  </div>
                  <div class="flex-1 min-w-0">
                    <p class="text-xs font-medium text-neutral-900 truncate">{inv.customer_name}</p>
                    <p class="text-[10px] text-neutral-400">{inv.invoice_number} &middot; Due {fmtDate(inv.due_date)}</p>
                  </div>
                  <div class="text-right shrink-0">
                    <p class="text-xs font-medium text-neutral-900 tabular-nums">{fmtCurrency(inv.total_amount)}</p>
                    {#if inv.is_overdue}
                      <p class="text-[10px] text-red-500 font-medium">{inv.days_overdue}d late</p>
                    {/if}
                  </div>
                </button>
              {/each}
            </div>
          {/if}

          {#if finance.recent_bills.length === 0 && finance.recent_invoices.length === 0}
            <div class="px-5 py-12 text-center">
              <p class="text-sm text-neutral-400">No recent financial activity</p>
            </div>
          {/if}
        {/if}
      </div>
    </div>

    <!-- Risk Indicators Row -->
    {#if portfolio}
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Top Performers -->
        <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
          <div class="px-5 py-4 border-b border-neutral-100 flex items-center justify-between">
            <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Top Performers</h3>
            <a href="/dashboard/portfolio-analysis" class="text-xs text-neutral-400 hover:text-neutral-700 transition-colors">Portfolio &rarr;</a>
          </div>
          {#if portfolio.top_appreciating.length > 0}
            <div class="divide-y divide-neutral-50">
              {#each portfolio.top_appreciating.slice(0, 4) as item}
                <button
                  onclick={() => goto(`/properties/${item.id}`)}
                  class="w-full px-5 py-3 flex items-center gap-3 hover:bg-neutral-50 transition-colors text-left"
                >
                  <div class="flex-1 min-w-0">
                    <p class="text-xs font-medium text-neutral-900 truncate">{item.name}</p>
                    <p class="text-[10px] text-neutral-400">{typeLabels[item.property_type] ?? item.property_type}</p>
                  </div>
                  <div class="text-right">
                    <p class="text-xs font-medium text-neutral-900 tabular-nums">{fmtCurrency(item.current_value)}</p>
                    <p class="text-[10px] font-medium text-emerald-600 tabular-nums">{fmtPct(item.gain_pct)}</p>
                  </div>
                </button>
              {/each}
            </div>
          {:else}
            <div class="px-5 py-8 text-center">
              <p class="text-sm text-neutral-400">No appreciation data yet</p>
            </div>
          {/if}
        </div>

        <!-- Risk: Underperforming + Encumbrances -->
        <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
          <div class="px-5 py-4 border-b border-neutral-100">
            <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Risk Indicators</h3>
          </div>

          {#if portfolio.top_depreciating.length > 0}
            <div class="px-4 pt-3 pb-1">
              <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Underperforming Assets</p>
            </div>
            <div class="divide-y divide-neutral-50">
              {#each portfolio.top_depreciating.slice(0, 3) as item}
                <button
                  onclick={() => goto(`/properties/${item.id}`)}
                  class="w-full px-5 py-2.5 flex items-center gap-3 hover:bg-neutral-50 transition-colors text-left"
                >
                  <div class="flex-1 min-w-0">
                    <p class="text-xs font-medium text-neutral-900 truncate">{item.name}</p>
                  </div>
                  <span class="text-[10px] font-medium text-red-600 tabular-nums">{fmtPct(item.gain_pct)}</span>
                </button>
              {/each}
            </div>
          {/if}

          {#if portfolio.encumbrance_summary.by_type.length > 0}
            <div class="px-4 pt-3 pb-1 {portfolio.top_depreciating.length > 0 ? 'border-t border-neutral-100' : ''}">
              <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Encumbrances</p>
            </div>
            <div class="px-5 py-3 space-y-2">
              {#each portfolio.encumbrance_summary.by_type as enc}
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-2">
                    <span class="inline-block w-2 h-2 rounded-full {enc.type === 'mortgage' ? 'bg-red-500' : enc.type === 'lien' ? 'bg-orange-500' : enc.type === 'tax_arrears' ? 'bg-amber-500' : 'bg-violet-500'}"></span>
                    <span class="text-xs text-neutral-700 capitalize">{enc.type.replace("_", " ")}</span>
                  </div>
                  <div class="flex items-center gap-3">
                    <span class="text-[10px] text-neutral-400">{enc.count} active</span>
                    <span class="text-xs font-medium text-neutral-900 tabular-nums">{fmtCurrency(enc.total_amount)}</span>
                  </div>
                </div>
              {/each}
            </div>
          {/if}

          {#if portfolio.top_depreciating.length === 0 && portfolio.encumbrance_summary.by_type.length === 0}
            <div class="px-5 py-8 text-center">
              <div class="w-8 h-8 rounded-full bg-emerald-50 flex items-center justify-center mx-auto">
                <svg class="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                </svg>
              </div>
              <p class="mt-2 text-sm text-neutral-400">No risk indicators at this time</p>
            </div>
          {/if}
        </div>
      </div>
    {/if}
  </div>
{/if}

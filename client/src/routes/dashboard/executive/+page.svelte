<script lang="ts">
  import { onMount } from "svelte";
  import { api } from "$lib/api";
  import DonutChart from "$lib/components/charts/DonutChart.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import { onboarding } from "$lib/stores/onboarding.svelte";
  import type {
    FinanceCashFlow,
    FinanceOverview,
    LeadListItem,
    MyApprovalItem,
    PaginatedResponse,
    PipelineStage,
    PortfolioAnalytics,
    ProjectListItem,
  } from "$lib/types";

  type TimeWindow = "30" | "90" | "180";

  interface MetricCard {
    key: string;
    label: string;
    value: string;
    delta: string;
    detail: string;
    tone: "positive" | "warning" | "critical" | "neutral";
  }

  interface TrendPoint {
    label: string;
    inflow: number;
    outflow: number;
    net: number;
  }

  interface TrendPointPosition {
    x: number;
    label: string;
    inflowY: number;
    outflowY: number;
    netY: number;
  }

  interface ExecutionRow {
    id: string;
    stream: "Workflow" | "Project" | "CRM";
    subject: string;
    owner: string;
    context: string;
    due: string;
    status: "critical" | "watch" | "healthy";
    score: number;
    note: string;
  }

  const pipelineStageOrder: PipelineStage[] = [
    "inquiry",
    "qualified",
    "site_visit",
    "offer_made",
    "reservation",
    "spa_issued",
    "closed",
  ];

  const pipelineStageLabel: Record<PipelineStage, string> = {
    inquiry: "Inquiry",
    qualified: "Qualified",
    site_visit: "Site Visit",
    offer_made: "Offer",
    reservation: "Reservation",
    spa_issued: "SPA",
    closed: "Closed",
  };

  const pipelineStageColor: Record<PipelineStage, string> = {
    inquiry: "#bfd6ff",
    qualified: "#8bb7ff",
    site_visit: "#5f8df7",
    offer_made: "#4f46e5",
    reservation: "#9333ea",
    spa_issued: "#c026d3",
    closed: "#16a34a",
  };

  const windowOptions: { key: TimeWindow; label: string }[] = [
    { key: "30", label: "30 Days" },
    { key: "90", label: "90 Days" },
    { key: "180", label: "180 Days" },
  ];

  const sidebarItems = [
    { key: "realtime", label: "Realtime Overview", caption: "Cross-module command view" },
    { key: "capital", label: "Capital & Treasury", caption: "Cash and receivables pulse" },
    { key: "delivery", label: "Delivery", caption: "Project execution health" },
    { key: "commercial", label: "Commercial", caption: "CRM conversion pressure" },
    { key: "governance", label: "Governance", caption: "Approvals and SLA posture" },
  ] as const;

  type MenuKey = (typeof sidebarItems)[number]["key"];

  const metricKeysByMenu: Record<MenuKey, string[]> = {
    realtime: ["capital", "cash", "collection", "projects", "workflow", "crm"],
    capital: ["capital", "cash", "collection"],
    delivery: ["projects"],
    commercial: ["crm"],
    governance: ["workflow"],
  };

  const streamsByMenu: Record<MenuKey, ExecutionRow["stream"][]> = {
    realtime: ["Workflow", "Project", "CRM"],
    capital: [],
    delivery: ["Project"],
    commercial: ["CRM"],
    governance: ["Workflow"],
  };

  let loading = $state(true);
  let refreshing = $state(false);
  let loadError = $state<string | null>(null);
  let slowLoad = $state(false);
  let selectedWindow = $state<TimeWindow>("90");
  let activeMenu = $state<MenuKey>("realtime");
  let searchQuery = $state("");

  const ONBOARDING_FALLBACK_MS = 6000;
  const SLOW_LOAD_HINT_MS = 4000;

  let portfolio = $state<PortfolioAnalytics | null>(null);
  let financeOverview = $state<FinanceOverview | null>(null);
  let financeCashFlow = $state<FinanceCashFlow | null>(null);
  let projects = $state<ProjectListItem[]>([]);
  let approvals = $state<MyApprovalItem[]>([]);
  let leads = $state<LeadListItem[]>([]);

  let requestSeq = 0;
  let initialized = $state(false);

  const hasAnalytics = $derived(onboarding.hasModule("analytics"));
  const hasFinance = $derived(onboarding.hasModule("finance"));
  const hasProjects = $derived(onboarding.hasModule("projects"));
  const hasCrm = $derived(onboarding.hasModule("crm"));

  function toNumber(value: unknown): number {
    const parsed = Number(value ?? 0);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function clamp(value: number, min: number, max: number): number {
    return Math.min(Math.max(value, min), max);
  }

  function pct(value: number, total: number): number {
    if (total <= 0) return 0;
    return (value / total) * 100;
  }

  function compactMoney(value: number): string {
    return currency.formatAbbreviated(value);
  }

  function signedCompactMoney(value: number): string {
    const abs = compactMoney(Math.abs(value));
    if (value > 0) return `+${abs}`;
    if (value < 0) return `-${abs}`;
    return abs;
  }

  function formatDateShort(value: string | null | undefined): string {
    if (!value) return "--";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "--";
    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }

  function toRegionLabel(location: string | null | undefined): string {
    if (!location) return "Unspecified";
    const parts = location
      .split(",")
      .map((part) => part.trim())
      .filter(Boolean);
    return parts[parts.length - 1] ?? parts[0] ?? "Unspecified";
  }

  function parseMonthDate(raw: unknown): Date {
    const normalized = typeof raw === "string" ? raw.trim() : String(raw ?? "").trim();
    const compactMatch = normalized.match(/^(\d{4})-(\d{1,2})$/);
    if (compactMatch) {
      const year = Number(compactMatch[1]);
      const monthIndex = Number(compactMatch[2]) - 1;
      return new Date(year, clamp(monthIndex, 0, 11), 1);
    }

    const fromIso = new Date(normalized);
    if (Number.isFinite(fromIso.getTime())) {
      return new Date(fromIso.getFullYear(), fromIso.getMonth(), 1);
    }

    const withYear = new Date(`${normalized} 1, ${new Date().getFullYear()}`);
    if (Number.isFinite(withYear.getTime())) {
      return new Date(withYear.getFullYear(), withYear.getMonth(), 1);
    }

    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1);
  }

  async function loadExecutive(manualRefresh = false) {
    const seq = ++requestSeq;
    refreshing = manualRefresh;
    loading = true;
    loadError = null;

    const year = new Date().getFullYear();

    try {
      const [
        portfolioRes,
        financeRes,
        financeCashFlowRes,
        projectsRes,
        approvalsRes,
        leadsRes,
      ] = await Promise.allSettled([
        hasAnalytics
          ? api.get<PortfolioAnalytics>("/analytics/portfolio/")
          : Promise.reject("disabled"),
        hasFinance
          ? api.get<FinanceOverview>("/finance/overview/")
          : Promise.reject("disabled"),
        hasFinance
          ? api.get<FinanceCashFlow>(`/finance/cash-flow/?year=${year}`)
          : Promise.reject("disabled"),
        hasProjects
          ? api.get<PaginatedResponse<ProjectListItem>>("/projects/", {
              page_size: "200",
              ordering: "-updated_at",
            })
          : Promise.reject("disabled"),
        api.get<MyApprovalItem[]>("/workflows/my-approvals/"),
        hasCrm
          ? api.get<PaginatedResponse<LeadListItem>>("/crm/leads/", {
              status: "active",
              page_size: "200",
              ordering: "-updated_at",
            })
          : Promise.reject("disabled"),
      ]);

      if (seq !== requestSeq) return;

      portfolio = portfolioRes.status === "fulfilled" ? portfolioRes.value : null;
      financeOverview = financeRes.status === "fulfilled" ? financeRes.value : null;
      financeCashFlow = financeCashFlowRes.status === "fulfilled" ? financeCashFlowRes.value : null;
      projects = projectsRes.status === "fulfilled" ? projectsRes.value.results : [];
      approvals = approvalsRes.status === "fulfilled" ? approvalsRes.value : [];
      leads = leadsRes.status === "fulfilled" ? leadsRes.value.results : [];
    } catch (err) {
      if (seq !== requestSeq) return;
      loadError = err instanceof Error ? err.message : "Could not load the executive dashboard.";
    } finally {
      if (seq === requestSeq) {
        loading = false;
        refreshing = false;
        slowLoad = false;
      }
    }
  }

  function retryLoad() {
    initialized = true;
    void loadExecutive(false);
  }

  $effect(() => {
    if (initialized || !onboarding.loaded) return;
    initialized = true;
    void loadExecutive(false);
  });

  onMount(() => {
    const slowTimer = window.setTimeout(() => {
      if (loading) slowLoad = true;
    }, SLOW_LOAD_HINT_MS);

    const fallbackTimer = window.setTimeout(() => {
      if (!initialized) {
        initialized = true;
        void loadExecutive(false);
      }
    }, ONBOARDING_FALLBACK_MS);

    return () => {
      window.clearTimeout(slowTimer);
      window.clearTimeout(fallbackTimer);
    };
  });

  const trendSeries = $derived.by(() => {
    const monthsToShow = selectedWindow === "30" ? 3 : selectedWindow === "90" ? 6 : 12;
    const monthlyRows = Array.isArray(financeCashFlow?.monthly_flow) ? financeCashFlow.monthly_flow : [];

    if (monthlyRows.length === 0) return [];

    return monthlyRows.slice(-monthsToShow).map((row) => {
      const monthDate = parseMonthDate(row.month);
      const inflow = toNumber(row.income);
      const outflow = toNumber(row.expenses);
      return {
        label: monthDate.toLocaleDateString("en-US", { month: "short" }),
        inflow,
        outflow,
        net: inflow - outflow,
      } satisfies TrendPoint;
    });
  });

  const trendChart = $derived.by(() => {
    const width = 860;
    const height = 250;
    const padding = { top: 14, right: 16, bottom: 34, left: 66 };
    const innerWidth = width - padding.left - padding.right;
    const innerHeight = height - padding.top - padding.bottom;

    if (trendSeries.length === 0) {
      return {
        width,
        height,
        points: [] as TrendPointPosition[],
        yTicks: [] as { y: number; label: string }[],
        inflowPath: "",
        outflowPath: "",
        netPath: "",
      };
    }

    const values = trendSeries.flatMap((row) => [row.inflow, row.outflow, row.net]);
    const minValue = Math.min(...values, 0);
    const maxValue = Math.max(...values, 1);
    const span = maxValue - minValue || 1;

    const step = trendSeries.length > 1 ? innerWidth / (trendSeries.length - 1) : 0;

    const toY = (value: number) => {
      const normalized = (value - minValue) / span;
      return padding.top + (1 - normalized) * innerHeight;
    };

    const points = trendSeries.map((row, index) => ({
      x: padding.left + step * index,
      label: row.label,
      inflowY: toY(row.inflow),
      outflowY: toY(row.outflow),
      netY: toY(row.net),
    }));

    const toPath = (key: keyof Pick<TrendPointPosition, "inflowY" | "outflowY" | "netY">) =>
      points
        .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x.toFixed(1)} ${point[key].toFixed(1)}`)
        .join(" ");

    const yTicks = Array.from({ length: 5 }, (_, index) => {
      const ratio = index / 4;
      const value = maxValue - span * ratio;
      return {
        y: padding.top + innerHeight * ratio,
        label: compactMoney(value),
      };
    });

    return {
      width,
      height,
      points,
      yTicks,
      inflowPath: toPath("inflowY"),
      outflowPath: toPath("outflowY"),
      netPath: toPath("netY"),
    };
  });

  const latestTrend = $derived(trendSeries.length > 0 ? trendSeries[trendSeries.length - 1] : null);
  const previousTrend = $derived(trendSeries.length > 1 ? trendSeries[trendSeries.length - 2] : null);
  const trendDelta = $derived.by(() => {
    if (!latestTrend || !previousTrend) return 0;
    return latestTrend.net - previousTrend.net;
  });

  const totalActiveProjects = $derived(projects.filter((project) => project.status !== "completed").length);
  const completedProjects = $derived(projects.filter((project) => project.status === "completed").length);
  const atRiskProjects = $derived(
    projects.filter((project) => project.risk_rating === "high" || project.risk_rating === "critical").length,
  );

  const breachedApprovals = $derived(approvals.filter((approval) => approval.sla_breached).length);

  const stageCounts = $derived.by(() => {
    const counts: Record<PipelineStage, number> = {
      inquiry: 0,
      qualified: 0,
      site_visit: 0,
      offer_made: 0,
      reservation: 0,
      spa_issued: 0,
      closed: 0,
    };

    for (const lead of leads) {
      const stage = lead.pipeline_stage;
      if (!(stage in counts)) continue;
      counts[stage] += 1;
    }

    return counts;
  });

  const conversionRate = $derived.by(() => pct(stageCounts.closed, leads.length));
  const urgentLeads = $derived(leads.filter((lead) => lead.priority === "urgent").length);

  const netCashPosition = $derived.by(() => {
    if (financeCashFlow) return toNumber(financeCashFlow.net_balance);
    return toNumber(financeOverview?.total_receivable) - toNumber(financeOverview?.total_payable);
  });

  const collectionRate = $derived.by(() => {
    const totalReceivable = toNumber(financeOverview?.total_receivable);
    const overdueReceivable = toNumber(financeOverview?.overdue_receivable_amount);
    if (totalReceivable <= 0) return 100;
    return clamp(((totalReceivable - overdueReceivable) / totalReceivable) * 100, 0, 100);
  });

  const overviewMetrics = $derived.by(() => {
    const cards = [
      {
        key: "capital",
        label: "Capital Exposure",
        value: compactMoney(toNumber(portfolio?.kpis.total_value)),
        delta: `${signedCompactMoney(toNumber(portfolio?.kpis.unrealized_gain))} unrealized`,
        detail: `${portfolio?.kpis.property_count ?? 0} properties tracked`,
        tone: toNumber(portfolio?.kpis.unrealized_gain) >= 0 ? "positive" : "warning",
        enabled: hasAnalytics,
      },
      {
        key: "cash",
        label: "Net Cash Position",
        value: compactMoney(netCashPosition),
        delta: `${signedCompactMoney(trendDelta)} vs prior`,
        detail: `${compactMoney(toNumber(financeOverview?.total_receivable))} receivable · ${compactMoney(toNumber(financeOverview?.total_payable))} payable`,
        tone: netCashPosition >= 0 ? "positive" : "critical",
        enabled: hasFinance,
      },
      {
        key: "collection",
        label: "Collection Efficiency",
        value: `${collectionRate.toFixed(1)}%`,
        delta: `${financeOverview?.overdue_receivable_count ?? 0} overdue receivables`,
        detail: `${compactMoney(toNumber(financeOverview?.overdue_receivable_amount))} at risk`,
        tone: collectionRate >= 88 ? "positive" : collectionRate >= 70 ? "warning" : "critical",
        enabled: hasFinance,
      },
      {
        key: "projects",
        label: "Delivery Load",
        value: totalActiveProjects.toLocaleString("en-US"),
        delta: `${atRiskProjects} projects at high/critical risk`,
        detail: `${completedProjects} completed`,
        tone: atRiskProjects === 0 ? "positive" : atRiskProjects <= 2 ? "warning" : "critical",
        enabled: hasProjects,
      },
      {
        key: "workflow",
        label: "Pending Approvals",
        value: approvals.length.toLocaleString("en-US"),
        delta: `${breachedApprovals} SLA breached`,
        detail: `${approvals.length - breachedApprovals} in window`,
        tone: breachedApprovals === 0 ? "positive" : breachedApprovals <= 2 ? "warning" : "critical",
        enabled: true,
      },
      {
        key: "crm",
        label: "CRM Conversion",
        value: `${conversionRate.toFixed(1)}%`,
        delta: `${stageCounts.closed.toLocaleString("en-US")} closed leads`,
        detail: `${urgentLeads} urgent lead${urgentLeads === 1 ? "" : "s"}`,
        tone: conversionRate >= 24 ? "positive" : conversionRate >= 15 ? "warning" : "critical",
        enabled: hasCrm,
      },
    ] satisfies (MetricCard & { enabled: boolean })[];

    return cards.filter((card) => card.enabled);
  });

  const sourceFeeds = $derived.by(() => [
    {
      label: "Portfolio analytics",
      status: hasAnalytics && portfolio ? "Live" : hasAnalytics ? "No feed" : "Module off",
      healthy: hasAnalytics && portfolio !== null,
    },
    {
      label: "Finance cash flow",
      status: hasFinance && financeCashFlow ? "Live" : hasFinance ? "No feed" : "Module off",
      healthy: hasFinance && financeCashFlow !== null,
    },
    {
      label: "Project delivery",
      status: hasProjects && projects.length > 0 ? "Live" : hasProjects ? "No records" : "Module off",
      healthy: hasProjects && projects.length > 0,
    },
    {
      label: "Workflow approvals",
      status: approvals.length > 0 ? "Live" : "No queue",
      healthy: approvals.length > 0,
    },
    {
      label: "CRM funnel",
      status: hasCrm && leads.length > 0 ? "Live" : hasCrm ? "No funnel" : "Module off",
      healthy: hasCrm && leads.length > 0,
    },
  ]);

  const pipelineRows = $derived.by(() => {
    const total = Math.max(leads.length, 1);
    return pipelineStageOrder
      .map((stage) => {
        const count = stageCounts[stage];
        return {
          stage,
          label: pipelineStageLabel[stage],
          count,
          share: (count / total) * 100,
          tone: pipelineStageColor[stage],
        };
      })
      .filter((row) => row.count > 0);
  });

  const pipelineDonutData = $derived.by(() => pipelineRows.map((row) => ({ label: row.label, value: row.count })));
  const pipelineDonutColors = $derived.by(() => pipelineRows.map((row) => row.tone));

  const netPulseBars = $derived.by(() => {
    const rows = trendSeries.slice(-7);
    if (rows.length === 0) return [];

    const maxAbs = Math.max(...rows.map((row) => Math.abs(row.net)), 1);
    return rows.map((row) => ({
      label: row.label,
      net: row.net,
      height: Math.max(10, (Math.abs(row.net) / maxAbs) * 100),
    }));
  });

  const focusProjects = $derived.by(() => {
    return projects
      .filter((project) => project.status !== "completed")
      .slice(0, 4)
      .map((project) => ({
        id: project.id,
        name: project.name,
        owner: project.project_manager || "Unassigned",
        progress: clamp(Math.round(toNumber(project.progress)), 0, 100),
        risk: project.risk_rating || "low",
        location: toRegionLabel(project.location),
      }));
  });

  const allExecutionRows = $derived.by(() => {
    const rows: ExecutionRow[] = [];

    for (const approval of approvals.slice(0, 8)) {
      rows.push({
        id: `wf-${approval.workflow_instance_id}-${approval.step_id}`,
        stream: "Workflow",
        subject: approval.template_name,
        owner: approval.step_name,
        context: "Governance",
        due: formatDateShort(approval.sla_deadline),
        status: approval.sla_breached ? "critical" : "watch",
        score: approval.sla_breached ? 28 : 72,
        note: approval.sla_breached ? "SLA breached" : "Pending approval",
      });
    }

    for (const project of projects.filter((item) => item.status !== "completed").slice(0, 10)) {
      const projectStatus = typeof project.status === "string" ? project.status : "planning";
      const risk = typeof project.risk_rating === "string" ? project.risk_rating : "low";
      const criticalRisk = risk === "critical" || risk === "high";
      const watchRisk = project.compliance_status === "warning" || projectStatus === "on_hold";

      rows.push({
        id: `prj-${project.id}`,
        stream: "Project",
        subject: project.name,
        owner: project.project_manager || "Unassigned",
        context: toRegionLabel(project.location),
        due: formatDateShort(project.target_end_date),
        status: criticalRisk ? "critical" : watchRisk ? "watch" : "healthy",
        score: clamp(Math.round(toNumber(project.progress)), 0, 100),
        note: `${projectStatus.replace("_", " ")} · ${risk} risk`,
      });
    }

    for (const lead of [...leads].sort((a, b) => b.days_in_pipeline - a.days_in_pipeline).slice(0, 8)) {
      const daysInPipeline = toNumber(lead.days_in_pipeline);
      const highPressure = lead.priority === "urgent" || daysInPipeline >= 45;
      const watchPressure = lead.priority === "high" || daysInPipeline >= 25;

      rows.push({
        id: `crm-${lead.id}`,
        stream: "CRM",
        subject: lead.full_name,
        owner: lead.assigned_to_name || "Unassigned",
        context: lead.source_name || "Inbound",
        due: formatDateShort(lead.inquiry_date),
        status: highPressure ? "critical" : watchPressure ? "watch" : "healthy",
        score: clamp(100 - daysInPipeline, 12, 96),
        note: `${lead.pipeline_stage_display} · ${daysInPipeline.toLocaleString("en-US")} days in stage`,
      });
    }

    const statusRank: Record<ExecutionRow["status"], number> = {
      critical: 0,
      watch: 1,
      healthy: 2,
    };

    return rows.sort((a, b) => {
      if (statusRank[a.status] !== statusRank[b.status]) {
        return statusRank[a.status] - statusRank[b.status];
      }
      return a.score - b.score;
    });
  });

  const executionRows = $derived.by(() => {
    const allowedStreams = streamsByMenu[activeMenu];
    const query = searchQuery.trim().toLowerCase();
    const cap = activeMenu === "realtime" ? 10 : 14;

    return allExecutionRows
      .filter((row) => allowedStreams.includes(row.stream))
      .filter((row) => {
        if (!query) return true;
        return (
          row.subject.toLowerCase().includes(query)
          || row.owner.toLowerCase().includes(query)
          || row.note.toLowerCase().includes(query)
          || row.context.toLowerCase().includes(query)
          || row.stream.toLowerCase().includes(query)
        );
      })
      .slice(0, cap);
  });

  const priorityRow = $derived(executionRows.length > 0 ? executionRows[0] : null);

  const visibleMetrics = $derived.by(() => {
    const allowedKeys = metricKeysByMenu[activeMenu];
    return overviewMetrics.filter((card) => allowedKeys.includes(card.key));
  });

  const showCrmFunnel = $derived(activeMenu === "realtime" || activeMenu === "commercial");
  const showCashPulse = $derived(activeMenu === "realtime" || activeMenu === "capital");
  const showInitiatives = $derived(activeMenu === "realtime" || activeMenu === "delivery");
  const showRightAside = $derived(showCrmFunnel || showCashPulse || showInitiatives);
  const activeMenuLabel = $derived(sidebarItems.find((item) => item.key === activeMenu)?.label ?? "");

  function metricCardToneClass(tone: MetricCard["tone"]): string {
    if (tone === "positive") return "border-emerald-200 bg-emerald-50/50";
    if (tone === "warning") return "border-amber-200 bg-amber-50/60";
    if (tone === "critical") return "border-rose-200 bg-rose-50/60";
    return "border-neutral-200 bg-white";
  }

  function metricPillToneClass(tone: MetricCard["tone"]): string {
    if (tone === "positive") return "bg-emerald-100 text-emerald-700";
    if (tone === "warning") return "bg-amber-100 text-amber-700";
    if (tone === "critical") return "bg-rose-100 text-rose-700";
    return "bg-neutral-100 text-neutral-700";
  }

  function queueStatusClass(status: ExecutionRow["status"]): string {
    if (status === "critical") return "bg-rose-100 text-rose-700";
    if (status === "watch") return "bg-amber-100 text-amber-700";
    return "bg-emerald-100 text-emerald-700";
  }

  function queueDotClass(status: ExecutionRow["status"]): string {
    if (status === "critical") return "bg-rose-500";
    if (status === "watch") return "bg-amber-500";
    return "bg-emerald-500";
  }

  function riskTagClass(risk: ProjectListItem["risk_rating"]): string {
    if (risk === "critical") return "bg-rose-100 text-rose-700";
    if (risk === "high") return "bg-amber-100 text-amber-700";
    if (risk === "medium") return "bg-sky-100 text-sky-700";
    return "bg-emerald-100 text-emerald-700";
  }

  function scoreRingColor(status: ExecutionRow["status"]): string {
    if (status === "critical") return "#e11d48";
    if (status === "watch") return "#d97706";
    return "#16a34a";
  }
</script>

<svelte:head>
  <style>
    @keyframes executiveRise {
      from {
        opacity: 0;
        transform: translateY(12px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }

    .exec-enter {
      animation: executiveRise 0.45s cubic-bezier(0.21, 1, 0.31, 1) both;
    }

    .exec-enter-d1 {
      animation-delay: 0.05s;
    }

    .exec-enter-d2 {
      animation-delay: 0.12s;
    }

    .exec-enter-d3 {
      animation-delay: 0.18s;
    }

    .exec-enter-d4 {
      animation-delay: 0.24s;
    }

    .executive-shell::before {
      content: "";
      position: absolute;
      inset: 0;
      pointer-events: none;
      background:
        radial-gradient(circle at 8% 12%, rgba(59, 130, 246, 0.16), transparent 48%),
        radial-gradient(circle at 92% 86%, rgba(16, 185, 129, 0.16), transparent 50%),
        linear-gradient(130deg, rgba(255, 255, 255, 0.96), rgba(243, 244, 246, 0.86));
    }

    .executive-shell > * {
      position: relative;
      z-index: 1;
    }
  </style>
</svelte:head>

{#if loading}
  <div class="flex flex-col items-center justify-center gap-3 py-28">
    <div class="h-7 w-7 animate-spin rounded-full border-[2.5px] border-neutral-200 border-t-neutral-900"></div>
    {#if slowLoad}
      <p class="text-xs text-neutral-500">Still loading… verifying your modules and fetching feeds.</p>
      <button
        type="button"
        onclick={retryLoad}
        class="rounded-full border border-neutral-300 bg-white px-3 py-1 text-xs font-semibold text-neutral-700 hover:border-neutral-400"
      >
        Retry now
      </button>
    {/if}
  </div>
{:else if loadError}
  <div class="mx-auto max-w-md rounded-2xl border border-rose-200 bg-rose-50/60 px-6 py-10 text-center">
    <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-rose-700">Dashboard error</p>
    <h1 class="mt-2 text-lg font-bold text-neutral-900">We couldn't load the executive dashboard.</h1>
    <p class="mt-2 text-sm text-neutral-600">{loadError}</p>
    <button
      type="button"
      onclick={retryLoad}
      class="mt-4 inline-flex items-center gap-2 rounded-full bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800"
    >
      Retry
    </button>
  </div>
{:else}
  <div class="space-y-4">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">Dashboard</p>
        <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Executive Command Center</h1>
        <p class="mt-1 text-sm text-neutral-500">
          Unified pulse across capital, delivery, governance, and commercial performance.
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        {#each windowOptions as option}
          <button
            type="button"
            onclick={() => selectedWindow = option.key}
            class="rounded-full border px-3 py-1.5 text-xs font-medium transition-colors
              {selectedWindow === option.key
                ? 'border-neutral-900 bg-neutral-900 text-white'
                : 'border-neutral-200 bg-white text-neutral-600 hover:border-neutral-300'}"
          >
            {option.label}
          </button>
        {/each}
        <button
          type="button"
          onclick={() => loadExecutive(true)}
          class="rounded-full border border-neutral-200 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:border-neutral-300"
        >
          {refreshing ? "Refreshing..." : "Refresh"}
        </button>
      </div>
    </div>

    <section class="executive-shell relative overflow-hidden rounded-xl border border-neutral-200 p-2 sm:p-3">
      <div
        class="grid gap-3 {showRightAside
          ? 'xl:grid-cols-[230px_minmax(0,1fr)_310px]'
          : 'xl:grid-cols-[230px_minmax(0,1fr)]'}"
      >
        <aside class="exec-enter rounded-2xl border border-neutral-200/80 bg-white/90 p-3 sm:p-4">
          <label class="block">
            <span class="sr-only">Search execution queue</span>
            <input
              type="search"
              bind:value={searchQuery}
              placeholder="Search stream, owner, or item..."
              class="w-full rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs text-neutral-700 placeholder:text-neutral-400 focus:border-neutral-400 focus:bg-white focus:outline-none"
            />
          </label>

          <div class="mt-4 space-y-1">
            {#each sidebarItems as item}
              <button
                type="button"
                onclick={() => activeMenu = item.key}
                class="w-full rounded-xl border px-3 py-2 text-left transition-colors
                  {activeMenu === item.key
                    ? 'border-neutral-900 bg-neutral-900 text-white'
                    : 'border-neutral-200 bg-white text-neutral-700 hover:border-neutral-300'}"
              >
                <p class="text-xs font-semibold">{item.label}</p>
                <p class="mt-0.5 text-[11px] {activeMenu === item.key ? 'text-neutral-200' : 'text-neutral-500'}">{item.caption}</p>
              </button>
            {/each}
          </div>

          <div class="mt-5 rounded-xl border border-neutral-200 bg-white p-3">
            <div class="mb-2 flex items-center justify-between">
              <p class="text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Data Sources</p>
              <span class="text-[10px] text-neutral-400">Live Sync</span>
            </div>
            <div class="space-y-2">
              {#each sourceFeeds as feed}
                <div class="flex items-center justify-between rounded-lg bg-neutral-50 px-2.5 py-2 text-[11px]">
                  <span class="text-neutral-600">{feed.label}</span>
                  <span class="inline-flex items-center gap-1">
                    <span class="h-1.5 w-1.5 rounded-full {feed.healthy ? 'bg-emerald-500' : 'bg-amber-400'}"></span>
                    <span class={feed.healthy ? "text-emerald-700" : "text-amber-700"}>{feed.status}</span>
                  </span>
                </div>
              {/each}
            </div>
          </div>
        </aside>

        <div class="space-y-3 min-w-0">
          <section class="exec-enter exec-enter-d1 rounded-2xl border border-neutral-200/80 bg-white/95 p-3 sm:p-4">
            <div class="mb-2 flex items-center justify-between">
              <p class="text-[11px] font-semibold uppercase tracking-wider text-neutral-500">{activeMenuLabel}</p>
              {#if activeMenu !== "realtime"}
                <button
                  type="button"
                  onclick={() => (activeMenu = "realtime")}
                  class="text-[10px] font-medium text-neutral-500 hover:text-neutral-900"
                >
                  Show all
                </button>
              {/if}
            </div>
            {#if visibleMetrics.length === 0}
              <div class="rounded-xl border border-dashed border-neutral-200 bg-neutral-50/50 px-4 py-6 text-center text-xs text-neutral-500">
                No metrics available for this view. The relevant module may be disabled.
              </div>
            {:else}
              <div class="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                {#each visibleMetrics as card}
                  <article class="rounded-xl border p-3 {metricCardToneClass(card.tone)}">
                    <div class="flex items-start justify-between gap-2">
                      <p class="text-[11px] font-semibold uppercase tracking-wider text-neutral-500">{card.label}</p>
                      <span class="rounded-full px-2 py-0.5 text-[10px] font-semibold {metricPillToneClass(card.tone)}">Live</span>
                    </div>
                    <p class="mt-2 text-2xl font-bold tabular-nums text-neutral-900">{card.value}</p>
                    <p class="mt-1 text-[11px] text-neutral-600">{card.delta}</p>
                    <p class="mt-1 text-[10px] text-neutral-500">{card.detail}</p>
                  </article>
                {/each}
              </div>
            {/if}
          </section>

          <section class="exec-enter exec-enter-d2 rounded-2xl border border-neutral-200/80 bg-white/95 p-3 sm:p-4">
            <div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Operational Trendlines</h2>
                <p class="mt-1 text-xs text-neutral-500">Inflow, outflow, and net balance movement over the selected window.</p>
              </div>
              <div class="space-y-1 text-right">
                <p class="text-xs text-neutral-500">
                  Latest Net:
                  <span class="font-semibold {latestTrend && latestTrend.net >= 0 ? 'text-emerald-700' : 'text-rose-700'}">
                    {latestTrend ? signedCompactMoney(latestTrend.net) : "--"}
                  </span>
                </p>
                <p class="text-xs text-neutral-500">
                  Delta:
                  <span class="font-semibold {previousTrend && trendDelta >= 0 ? 'text-emerald-700' : previousTrend ? 'text-rose-700' : 'text-neutral-400'}">
                    {previousTrend ? signedCompactMoney(trendDelta) : "--"}
                  </span>
                </p>
              </div>
            </div>

            <div class="mt-3 rounded-xl border border-neutral-200 bg-neutral-50/60 p-2 sm:p-3">
              {#if trendChart.points.length > 0}
                <svg viewBox="0 0 {trendChart.width} {trendChart.height}" class="w-full">
                  {#each trendChart.yTicks as tick}
                    <line
                      x1="66"
                      y1={tick.y}
                      x2={trendChart.width - 16}
                      y2={tick.y}
                      stroke="#e5e7eb"
                      stroke-dasharray="2 4"
                      stroke-width="1"
                    />
                    <text x="58" y={tick.y + 3} text-anchor="end" class="fill-neutral-400 text-[10px] font-medium">{tick.label}</text>
                  {/each}

                  <path d={trendChart.inflowPath} fill="none" stroke="#0ea5e9" stroke-width="2" stroke-linecap="round" />
                  <path d={trendChart.outflowPath} fill="none" stroke="#f97316" stroke-width="2" stroke-linecap="round" />
                  <path d={trendChart.netPath} fill="none" stroke="#2563eb" stroke-width="2.6" stroke-linecap="round" />

                  {#each trendChart.points as point, index}
                    {#if index % 2 === 0 || index === trendChart.points.length - 1}
                      <text x={point.x} y={trendChart.height - 10} text-anchor="middle" class="fill-neutral-500 text-[10px]">{point.label}</text>
                    {/if}
                  {/each}

                  {#if trendChart.points.length > 0}
                    {@const tailPoint = trendChart.points[trendChart.points.length - 1]}
                    <circle cx={tailPoint.x} cy={tailPoint.inflowY} r="3.8" fill="#0ea5e9" />
                    <circle cx={tailPoint.x} cy={tailPoint.outflowY} r="3.8" fill="#f97316" />
                    <circle cx={tailPoint.x} cy={tailPoint.netY} r="4.2" fill="#2563eb" />
                  {/if}
                </svg>
              {:else}
                <div class="flex h-44 flex-col items-center justify-center gap-1 text-center">
                  <p class="text-sm font-medium text-neutral-700">Cash-flow series unavailable for this window</p>
                  <p class="text-xs text-neutral-500">Trend will appear once finance posts monthly inflow and outflow data.</p>
                </div>
              {/if}

              {#if trendChart.points.length > 0}
                <div class="mt-2 flex flex-wrap items-center gap-3 text-[11px] text-neutral-600">
                  <span class="inline-flex items-center gap-1.5"><span class="h-2 w-2 rounded-full bg-sky-500"></span>Inflow</span>
                  <span class="inline-flex items-center gap-1.5"><span class="h-2 w-2 rounded-full bg-orange-500"></span>Outflow</span>
                  <span class="inline-flex items-center gap-1.5"><span class="h-2 w-2 rounded-full bg-blue-600"></span>Net</span>
                </div>
              {/if}
            </div>
          </section>

          <section class="exec-enter exec-enter-d3 rounded-2xl border border-neutral-200/80 bg-white/95 p-3 sm:p-4">
            <div class="mb-2 flex items-center justify-between">
              <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Execution Queue</h2>
              <span class="rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] font-medium text-neutral-600">
                {executionRows.length} active lines
              </span>
            </div>

            <div class="overflow-x-auto rounded-xl border border-neutral-200 bg-white">
              <table class="min-w-full text-xs">
                <thead class="bg-neutral-50 text-neutral-500">
                  <tr>
                    <th class="px-3 py-2 text-left font-semibold uppercase tracking-wider">Stream</th>
                    <th class="px-3 py-2 text-left font-semibold uppercase tracking-wider">Item</th>
                    <th class="px-3 py-2 text-left font-semibold uppercase tracking-wider">Owner</th>
                    <th class="px-3 py-2 text-left font-semibold uppercase tracking-wider">Context</th>
                    <th class="px-3 py-2 text-left font-semibold uppercase tracking-wider">Due</th>
                    <th class="px-3 py-2 text-left font-semibold uppercase tracking-wider">Health</th>
                  </tr>
                </thead>
                <tbody>
                  {#if executionRows.length === 0}
                    <tr>
                      <td colspan="6" class="px-3 py-5 text-center text-neutral-500">No execution rows available for the current modules.</td>
                    </tr>
                  {:else}
                    {#each executionRows as row}
                      <tr class="border-t border-neutral-100 text-neutral-700 hover:bg-neutral-50/70">
                        <td class="px-3 py-2.5">
                          <span class="rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] font-semibold text-neutral-600">{row.stream}</span>
                        </td>
                        <td class="px-3 py-2.5">
                          <p class="max-w-[210px] truncate font-medium text-neutral-900">{row.subject}</p>
                          <p class="text-[10px] text-neutral-500">{row.note}</p>
                        </td>
                        <td class="px-3 py-2.5">{row.owner}</td>
                        <td class="px-3 py-2.5">{row.context}</td>
                        <td class="px-3 py-2.5">{row.due}</td>
                        <td class="px-3 py-2.5">
                          <span class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold {queueStatusClass(row.status)}">
                            <span class="h-1.5 w-1.5 rounded-full {queueDotClass(row.status)}"></span>
                            {row.score}
                          </span>
                        </td>
                      </tr>
                    {/each}
                  {/if}
                </tbody>
              </table>
            </div>

            {#if priorityRow}
              <div class="mt-3 rounded-xl border border-amber-200 bg-amber-50/70 p-3">
                <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p class="text-[11px] font-semibold uppercase tracking-wider text-amber-700">Priority Focus</p>
                    <p class="mt-1 text-sm font-semibold text-neutral-900">{priorityRow.subject}</p>
                    <p class="mt-1 text-xs text-neutral-600">{priorityRow.note} · Owner: {priorityRow.owner} · Due: {priorityRow.due}</p>
                  </div>
                  <div class="flex items-center gap-3">
                    <div
                      class="relative h-14 w-14 rounded-full"
                      style="background: conic-gradient({scoreRingColor(priorityRow.status)} {priorityRow.score}%, #e5e7eb 0);"
                    >
                      <div class="absolute inset-[6px] flex items-center justify-center rounded-full bg-white text-xs font-semibold text-neutral-700">
                        {priorityRow.score}
                      </div>
                    </div>
                    <div class="flex items-center gap-2">
                      <a href="/reports/dashboard" class="rounded-lg bg-neutral-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-neutral-800">View feed</a>
                      <a href="/projects/tasks" class="rounded-lg border border-neutral-300 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:border-neutral-400">Assign team</a>
                    </div>
                  </div>
                </div>
              </div>
            {/if}
          </section>
        </div>

        {#if showRightAside}
        <aside class="space-y-3 min-w-0">
          {#if showCrmFunnel}
          <section class="exec-enter exec-enter-d2 rounded-2xl border border-neutral-200/80 bg-white/95 p-3 sm:p-4">
            <div class="flex items-center justify-between">
              <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">CRM Funnel</h2>
              <span class="text-[10px] text-neutral-400">{selectedWindow}d view</span>
            </div>
            <div class="mt-2 flex items-end justify-between">
              <div>
                <p class="text-2xl font-bold tabular-nums text-neutral-900">{leads.length.toLocaleString("en-US")}</p>
                <p class="text-[11px] text-neutral-500">Active leads</p>
              </div>
              <div class="text-right">
                <p class="text-lg font-semibold tabular-nums text-emerald-700">{conversionRate.toFixed(1)}%</p>
                <p class="text-[11px] text-neutral-500">Close conversion</p>
              </div>
            </div>

            <div class="mt-3 rounded-xl border border-neutral-200 bg-neutral-50/60 p-2">
              {#if pipelineDonutData.length > 0}
                <DonutChart
                  data={pipelineDonutData}
                  colors={pipelineDonutColors}
                  size={170}
                  showLegend={false}
                  centerLabel="Closed"
                  centerValue={stageCounts.closed.toLocaleString("en-US")}
                  formatValue={(value: number) => value.toLocaleString("en-US")}
                />
              {:else}
                <div class="flex h-32 items-center justify-center text-sm text-neutral-500">No CRM pipeline data.</div>
              {/if}
            </div>

            {#if pipelineRows.length > 0}
              <div class="mt-3 space-y-1.5">
                {#each pipelineRows.slice(0, 4) as row}
                  <div class="flex items-center justify-between text-[11px]">
                    <span class="inline-flex items-center gap-1.5 text-neutral-600">
                      <span class="h-2 w-2 rounded-full" style="background: {row.tone};"></span>
                      {row.label}
                    </span>
                    <span class="font-semibold text-neutral-700">{row.count} ({row.share.toFixed(0)}%)</span>
                  </div>
                {/each}
              </div>
            {/if}
          </section>
          {/if}

          {#if showCashPulse}
          <section class="exec-enter exec-enter-d3 rounded-2xl border border-neutral-200/80 bg-white/95 p-3 sm:p-4">
            <div class="flex items-center justify-between">
              <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Cash Pulse</h2>
              <span class="text-[10px] text-neutral-400">Net bars</span>
            </div>

            {#if netPulseBars.length > 0}
              <div class="mt-3 grid grid-cols-7 gap-1.5">
                {#each netPulseBars as bar}
                  <div class="space-y-1 text-center">
                    <div class="flex h-20 items-end justify-center">
                      <div
                        class="w-full rounded-sm {bar.net >= 0 ? 'bg-emerald-400' : 'bg-rose-300'}"
                        style="height: {bar.height}%;"
                      ></div>
                    </div>
                    <p class="text-[10px] text-neutral-500">{bar.label}</p>
                  </div>
                {/each}
              </div>
            {:else}
              <div class="mt-3 flex h-24 items-center justify-center rounded-xl border border-dashed border-neutral-200 text-sm text-neutral-500">
                Cash pulse unavailable.
              </div>
            {/if}

            <div class="mt-3 space-y-2 text-[11px]">
              <div class="flex items-center justify-between rounded-lg bg-neutral-50 px-2.5 py-2">
                <span class="text-neutral-500">Receivable</span>
                <span class="font-semibold text-neutral-800">{compactMoney(toNumber(financeOverview?.total_receivable))}</span>
              </div>
              <div class="flex items-center justify-between rounded-lg bg-neutral-50 px-2.5 py-2">
                <span class="text-neutral-500">Payable</span>
                <span class="font-semibold text-neutral-800">{compactMoney(toNumber(financeOverview?.total_payable))}</span>
              </div>
              <div class="flex items-center justify-between rounded-lg bg-neutral-50 px-2.5 py-2">
                <span class="text-neutral-500">Overdue exposure</span>
                <span class="font-semibold text-amber-700">
                  {compactMoney(toNumber(financeOverview?.overdue_receivable_amount) + toNumber(financeOverview?.overdue_payable_amount))}
                </span>
              </div>
            </div>
          </section>
          {/if}

          {#if showInitiatives}
          <section class="exec-enter exec-enter-d4 rounded-2xl border border-neutral-200/80 bg-white/95 p-3 sm:p-4">
            <div class="flex items-center justify-between">
              <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Strategic Initiatives</h2>
              <span class="text-[10px] text-neutral-400">Top 4</span>
            </div>

            {#if focusProjects.length === 0}
              <div class="mt-3 flex h-24 items-center justify-center rounded-xl border border-dashed border-neutral-200 text-sm text-neutral-500">
                No active projects.
              </div>
            {:else}
              <div class="mt-3 grid grid-cols-2 gap-2">
                {#each focusProjects as project}
                  <article class="rounded-xl border border-neutral-200 bg-neutral-50/60 p-2.5">
                    <p class="truncate text-xs font-semibold text-neutral-900">{project.name}</p>
                    <p class="mt-0.5 truncate text-[10px] text-neutral-500">{project.location} · {project.owner}</p>
                    <div class="mt-2 h-1.5 overflow-hidden rounded-full bg-neutral-200">
                      <div class="h-full rounded-full bg-blue-500" style="width: {project.progress}%;"></div>
                    </div>
                    <div class="mt-1.5 flex items-center justify-between">
                      <span class="rounded-full px-1.5 py-0.5 text-[10px] font-medium {riskTagClass(project.risk)}">{project.risk}</span>
                      <span class="text-[10px] font-semibold text-neutral-600">{project.progress}%</span>
                    </div>
                  </article>
                {/each}
              </div>
            {/if}
          </section>
          {/if}
        </aside>
        {/if}
      </div>
    </section>
  </div>
{/if}

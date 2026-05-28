<script lang="ts">
  import { goto } from "$app/navigation";
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import DonutChart from "$lib/components/charts/DonutChart.svelte";
  import GroupedBarChart from "$lib/components/charts/GroupedBarChart.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import type {
    PaginatedResponse,
    PortfolioAnalytics,
    ProjectBudgetItem,
    ProjectListItem,
  } from "$lib/types";

  let loading = $state(true);
  let projects = $state<ProjectListItem[]>([]);
  let projectBudgets = $state<ProjectBudgetItem[]>([]);

  async function fetchExecutionStats() {
    loading = true;
    try {
      const [projectRes, analytics] = await Promise.all([
        api.get<PaginatedResponse<ProjectListItem>>("/projects/", {
          page_size: "200",
          ordering: "target_end_date",
        }),
        api.get<PortfolioAnalytics>("/analytics/portfolio/"),
      ]);
      projects = projectRes.results;
      projectBudgets = analytics.project_budget_summary ?? [];
    } catch {
      toast.error("Load failed", "Could not load execution statistics.");
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    fetchExecutionStats();
  });

  function fmtCurrency(n: number | string): string {
    const value = typeof n === "string" ? Number(n) : n;
    if (Number.isNaN(value)) return "0";
    return fmtCurrencyCompactNoSymbol(value);
  }

  function stripCurrencySymbol(formatted: string): string {
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

  function fmtCurrencyCompactNoSymbol(value: number): string {
    return stripCurrencySymbol(currency.formatCompact(value));
  }

  function fmtCurrencyAbbreviatedNoSymbol(value: number): string {
    return stripCurrencySymbol(currency.formatAbbreviated(value));
  }

  function fmtDate(d: string | null): string {
    if (!d) return "--";
    return new Date(d).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function daysUntil(d: string | null): number | null {
    if (!d) return null;
    const diff = new Date(d).getTime() - Date.now();
    return Math.ceil(diff / (1000 * 60 * 60 * 24));
  }

  const statusLabels: Record<ProjectListItem["status"], string> = {
    planning: "Planning",
    in_progress: "In Progress",
    on_hold: "On Hold",
    completed: "Completed",
  };

  const statusColors: Record<ProjectListItem["status"], string> = {
    planning: "bg-blue-50 text-blue-700 border-blue-100",
    in_progress: "bg-emerald-50 text-emerald-700 border-emerald-100",
    on_hold: "bg-amber-50 text-amber-700 border-amber-100",
    completed: "bg-violet-50 text-violet-700 border-violet-100",
  };

  const statusCounts = $derived.by(() => {
    const counts: Record<ProjectListItem["status"], number> = {
      planning: 0,
      in_progress: 0,
      on_hold: 0,
      completed: 0,
    };
    for (const project of projects) {
      counts[project.status] += 1;
    }
    return counts;
  });

  const activeProjects = $derived(
    projects.filter((project) => project.status !== "completed")
  );

  const avgCompletion = $derived.by(() => {
    if (activeProjects.length === 0) return 0;
    const total = activeProjects.reduce((sum, project) => sum + Number(project.progress || 0), 0);
    return total / activeProjects.length;
  });

  const overdueProjects = $derived(
    activeProjects.filter((project) => {
      const days = daysUntil(project.target_end_date);
      return days !== null && days < 0;
    }).length
  );

  const dueSoonProjects = $derived(
    activeProjects.filter((project) => {
      const days = daysUntil(project.target_end_date);
      return days !== null && days >= 0 && days <= 14;
    }).length
  );

  const totalPlanned = $derived(
    projectBudgets.reduce((sum, project) => sum + Number(project.total_planned || 0), 0)
  );

  const totalActual = $derived(
    projectBudgets.reduce((sum, project) => sum + Number(project.total_actual || 0), 0)
  );

  const totalVariance = $derived(totalPlanned - totalActual);

  const completionBands = $derived.by(() => {
    const buckets = {
      not_started: 0,
      mobilizing: 0,
      progressing: 0,
      closing: 0,
    };
    for (const project of activeProjects) {
      const progress = Number(project.progress || 0);
      if (progress < 25) buckets.not_started += 1;
      else if (progress < 50) buckets.mobilizing += 1;
      else if (progress < 80) buckets.progressing += 1;
      else buckets.closing += 1;
    }
    return [
      { label: "0-24%", value: buckets.not_started },
      { label: "25-49%", value: buckets.mobilizing },
      { label: "50-79%", value: buckets.progressing },
      { label: "80-99%", value: buckets.closing },
    ].filter((item) => item.value > 0);
  });

  const budgetExecutionData = $derived(
    [...projectBudgets]
      .sort((a, b) => Number(b.total_actual || 0) - Number(a.total_actual || 0))
      .slice(0, 8)
      .map((project) => ({
        label: project.name,
        value1: Number(project.total_planned || 0),
        value2: Number(project.total_actual || 0),
      }))
  );

  const upcomingDeadlines = $derived.by(() => {
    return [...activeProjects]
      .filter((project) => project.target_end_date)
      .sort((a, b) => {
        const left = new Date(a.target_end_date as string).getTime();
        const right = new Date(b.target_end_date as string).getTime();
        return left - right;
      })
      .slice(0, 8);
  });
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
  </div>
{:else}
  <div class="space-y-6">
    <div class="flex items-start justify-between gap-4">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-orange-700">Projects</p>
        <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-900">Execution Stats</h1>
        <p class="text-sm text-neutral-500 mt-1">
          Field execution, schedule, and delivery performance across active projects.
        </p>
      </div>
      <button
        onclick={() => fetchExecutionStats()}
        class="rounded-lg border border-neutral-200 bg-white p-2 text-neutral-500 hover:bg-neutral-50 hover:text-neutral-900 transition-colors"
        aria-label="Refresh"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182" />
        </svg>
      </button>
    </div>

    <div class="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-4">
      <div class="rounded-xl border border-neutral-200 border-t-4 border-t-emerald-500 bg-white p-4">
        <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Active Projects</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{activeProjects.length}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 border-t-4 border-t-indigo-500 bg-white p-4">
        <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Avg Completion</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{avgCompletion.toFixed(1)}%</p>
      </div>
      <div class="rounded-xl border border-neutral-200 border-t-4 border-t-rose-500 bg-white p-4">
        <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Schedule At Risk</p>
        <p class="mt-1 text-xl font-bold text-rose-600 tabular-nums">{overdueProjects}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 border-t-4 border-t-amber-500 bg-white p-4">
        <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Due In 14 Days</p>
        <p class="mt-1 text-xl font-bold text-amber-600 tabular-nums">{dueSoonProjects}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 border-t-4 border-t-sky-500 bg-white p-4">
        <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Planned Spend</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{fmtCurrency(totalPlanned)}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 border-t-4 border-t-violet-500 bg-white p-4">
        <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Actual Spend</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{fmtCurrency(totalActual)}</p>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div class="rounded-xl border border-neutral-200 bg-white p-6">
        <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Project Completion Distribution</h3>
        <div class="flex flex-wrap gap-x-4 gap-y-1 mb-4">
          <span class="flex items-center gap-1.5 text-xs text-neutral-600"><span class="inline-block w-2.5 h-2.5 rounded-full" style="background:#b91c1c"></span> Not Started (0–24%)</span>
          <span class="flex items-center gap-1.5 text-xs text-neutral-600"><span class="inline-block w-2.5 h-2.5 rounded-full" style="background:#f59e0b"></span> Mobilizing (25–49%)</span>
          <span class="flex items-center gap-1.5 text-xs text-neutral-600"><span class="inline-block w-2.5 h-2.5 rounded-full" style="background:#10b981"></span> Progressing (50–74%)</span>
          <span class="flex items-center gap-1.5 text-xs text-neutral-600"><span class="inline-block w-2.5 h-2.5 rounded-full" style="background:#6366f1"></span> Closing (75–100%)</span>
        </div>
        <div class="flex justify-center">
          <DonutChart
            data={completionBands}
            colors={["#b91c1c", "#f59e0b", "#10b981", "#6366f1"]}
            centerValue={String(activeProjects.length)}
            centerLabel="Active"
            size={220}
          />
        </div>
      </div>

      <div class="rounded-xl border border-neutral-200 bg-white p-6">
        <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Delivery Pipeline</h3>
        <div class="grid grid-cols-2 gap-3">
          {#each (Object.keys(statusCounts) as Array<ProjectListItem["status"]>) as status}
            <div class="rounded-lg border p-4 {statusColors[status]}">
              <p class="text-[10px] font-semibold uppercase tracking-wider">{statusLabels[status]}</p>
              <p class="mt-1 text-2xl font-bold tabular-nums">{statusCounts[status]}</p>
            </div>
          {/each}
        </div>
        <div class="mt-4 rounded-lg border border-neutral-100 bg-neutral-50 px-4 py-3">
          <p class="text-xs text-neutral-500">Budget Variance</p>
          <p class="text-lg font-semibold tabular-nums {totalVariance >= 0 ? 'text-emerald-600' : 'text-red-600'}">
            {totalVariance >= 0 ? "+" : "-"}{fmtCurrency(Math.abs(totalVariance))}
          </p>
        </div>
      </div>
    </div>

    <div class="rounded-xl border border-neutral-200 bg-white p-6 overflow-hidden">
      <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Budget Execution By Project</h3>
      <div class="overflow-hidden">
        <GroupedBarChart
          data={budgetExecutionData}
          value1Key="value1"
          value2Key="value2"
          label1="Planned"
          label2="Actual"
          color1="#bfdbfe"
          color2="#2563eb"
          formatValue={fmtCurrency}
          formatAxisValue={fmtCurrencyAbbreviatedNoSymbol}
          height={340}
        />
      </div>
    </div>

    <div class="grid grid-cols-1 xl:grid-cols-2 gap-6">
      <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
        <div class="px-5 py-4 border-b border-neutral-100">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Upcoming Deadlines</h3>
        </div>
        {#if upcomingDeadlines.length === 0}
          <div class="px-5 py-10 text-center">
            <p class="text-sm text-neutral-400">No target end dates available.</p>
          </div>
        {:else}
          <div class="divide-y divide-neutral-100">
            {#each upcomingDeadlines as project}
              {@const days = daysUntil(project.target_end_date)}
              <button
                onclick={() => goto(`/projects/${project.id}`)}
                class="w-full px-5 py-3 text-left hover:bg-neutral-50 transition-colors"
              >
                <div class="flex items-center justify-between gap-4">
                  <div class="min-w-0">
                    <p class="text-sm font-medium text-neutral-900 truncate">{project.name}</p>
                    <p class="text-xs text-neutral-500 mt-0.5">{project.property_name ?? "Unlinked property"}</p>
                  </div>
                  <div class="text-right shrink-0">
                    <p class="text-xs text-neutral-700">{fmtDate(project.target_end_date)}</p>
                    <p class="text-[11px] font-medium tabular-nums {days !== null && days < 0 ? 'text-red-600' : days !== null && days <= 14 ? 'text-amber-600' : 'text-emerald-600'}">
                      {#if days !== null && days < 0}
                        {Math.abs(days)}d overdue
                      {:else if days !== null}
                        {days}d left
                      {/if}
                    </p>
                  </div>
                </div>
              </button>
            {/each}
          </div>
        {/if}
      </div>

      <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
        <div class="px-5 py-4 border-b border-neutral-100">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Active Project Worklist</h3>
        </div>
        {#if activeProjects.length === 0}
          <div class="px-5 py-10 text-center">
            <p class="text-sm text-neutral-400">No active projects found.</p>
          </div>
        {:else}
          <div class="divide-y divide-neutral-100 max-h-[460px] overflow-y-auto">
            {#each activeProjects as project}
              <button
                onclick={() => goto(`/projects/${project.id}`)}
                class="w-full px-5 py-3 text-left hover:bg-neutral-50 transition-colors"
              >
                <div class="flex items-center gap-4">
                  <div class="min-w-0 flex-1">
                    <div class="flex items-center gap-2">
                      <p class="text-sm font-medium text-neutral-900 truncate">{project.name}</p>
                      <span class="inline-flex items-center rounded px-2 py-0.5 text-[10px] font-semibold border {statusColors[project.status]}">
                        {statusLabels[project.status]}
                      </span>
                    </div>
                    <p class="text-xs text-neutral-500 mt-0.5">{project.project_manager || "Unassigned manager"}</p>
                    <div class="mt-2 h-1.5 w-full rounded-full bg-neutral-100 overflow-hidden">
                      <div
                        class="h-1.5 rounded-full {project.progress >= 80 ? 'bg-emerald-500' : project.progress >= 50 ? 'bg-blue-600' : 'bg-amber-500'}"
                        style="width: {Math.min(project.progress, 100)}%"
                      ></div>
                    </div>
                  </div>
                  <div class="text-right shrink-0">
                    <p class="text-sm font-semibold tabular-nums text-neutral-900">{project.progress}%</p>
                    <p class="text-[11px] text-neutral-500">{fmtCurrency(project.budget || 0)}</p>
                  </div>
                </div>
              </button>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}

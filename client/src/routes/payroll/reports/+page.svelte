<script lang="ts">
  import { onMount } from "svelte";
  import DataStateBanner from "$lib/components/DataStateBanner.svelte";
  import { fetchAllPages, toAmount } from "$lib/contracts";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    BonusListItem,
    DeductionListItem,
    EmployeeDirectoryItem,
    PayrollRunListItem,
    PayslipListItem,
    TaxRecordListItem,
  } from "$lib/types";

  type PeriodKey = "this_month" | "last_month" | "this_quarter" | "this_year" | "all_time";

  const MAX_PAGES = 10;

  const PERIODS: { value: PeriodKey; label: string }[] = [
    { value: "this_month", label: "This Month" },
    { value: "last_month", label: "Last Month" },
    { value: "this_quarter", label: "This Quarter" },
    { value: "this_year", label: "This Year" },
    { value: "all_time", label: "All Time" },
  ];

  const RUN_STATUS_CLASSES: Record<string, string> = {
    draft: "bg-neutral-100 border-neutral-200 text-neutral-600",
    processing: "bg-sky-50 border-sky-200 text-sky-700",
    completed: "bg-emerald-50 border-emerald-200 text-emerald-700",
    cancelled: "bg-rose-50 border-rose-200 text-rose-700",
  };

  const ACTIVE_EMPLOYMENT_STATUSES = new Set(["active", "probation", "notice_period", "on_leave"]);
  const CHIP_BASE = "inline-flex rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wider";

  let loading = $state(true);
  let refreshing = $state(false);
  let error = $state<string | null>(null);

  let payrollRuns = $state<PayrollRunListItem[]>([]);
  let payslips = $state<PayslipListItem[]>([]);
  let taxRecords = $state<TaxRecordListItem[]>([]);
  let employees = $state<EmployeeDirectoryItem[]>([]);
  // referenced for parity / future expansion
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  let deductions = $state<DeductionListItem[]>([]);
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  let bonuses = $state<BonusListItem[]>([]);

  let periodFilter = $state<PeriodKey>("this_year");

  function getSettledValue<T>(result: PromiseSettledResult<T[]>, fallback: T[]): T[] {
    return result.status === "fulfilled" ? result.value : fallback;
  }

  function parseDate(value: string | null | undefined): Date | null {
    if (!value) return null;
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  function formatCurrency(value: number, digits = 0): string {
    return new Intl.NumberFormat("en-NG", {
      style: "currency",
      currency: currency.config.code || "NGN",
      minimumFractionDigits: 0,
      maximumFractionDigits: digits,
    }).format(Number.isFinite(value) ? value : 0);
  }

  function shortDate(value: string | null | undefined): string {
    const date = parseDate(value);
    if (!date) return "—";
    return new Intl.DateTimeFormat("en-NG", { day: "numeric", month: "short", year: "numeric" }).format(date);
  }

  function formatStatusLabel(value: string): string {
    return value
      .split("_")
      .map((part) => (part.length === 0 ? part : part[0].toUpperCase() + part.slice(1)))
      .join(" ");
  }

  function chipClassFor(map: Record<string, string>, key: string): string {
    return map[key] ?? "bg-neutral-100 border-neutral-200 text-neutral-600";
  }

  function periodBounds(key: PeriodKey): { start: Date | null; end: Date | null; year: number } {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const year = today.getFullYear();
    if (key === "this_month") {
      const start = new Date(year, today.getMonth(), 1);
      const end = new Date(year, today.getMonth() + 1, 1);
      return { start, end, year };
    }
    if (key === "last_month") {
      const start = new Date(year, today.getMonth() - 1, 1);
      const end = new Date(year, today.getMonth(), 1);
      return { start, end, year };
    }
    if (key === "this_quarter") {
      const quarter = Math.floor(today.getMonth() / 3);
      const start = new Date(year, quarter * 3, 1);
      const end = new Date(year, quarter * 3 + 3, 1);
      return { start, end, year };
    }
    if (key === "this_year") {
      const start = new Date(year, 0, 1);
      const end = new Date(year + 1, 0, 1);
      return { start, end, year };
    }
    return { start: null, end: null, year };
  }

  function withinPeriod(date: Date | null, bounds: { start: Date | null; end: Date | null }): boolean {
    if (!date) return false;
    if (bounds.start === null || bounds.end === null) return true;
    return date >= bounds.start && date < bounds.end;
  }

  function csvEscape(value: string): string {
    if (/[",\n]/.test(value)) {
      return `"${value.replaceAll('"', '""')}"`;
    }
    return value;
  }

  async function loadData(background = false) {
    if (background) refreshing = true;
    else loading = true;
    error = null;

    try {
      const results = await Promise.allSettled([
        fetchAllPages<PayrollRunListItem>("/hr/payroll-runs/", { page_size: "200" }, MAX_PAGES),
        fetchAllPages<PayslipListItem>("/hr/payslips/", { page_size: "200" }, MAX_PAGES),
        fetchAllPages<TaxRecordListItem>("/hr/tax-records/", { page_size: "200" }, MAX_PAGES),
        fetchAllPages<EmployeeDirectoryItem>("/hr/employee-records/", { page_size: "200" }, MAX_PAGES),
        fetchAllPages<DeductionListItem>("/hr/deductions/", { page_size: "200" }, MAX_PAGES),
        fetchAllPages<BonusListItem>("/hr/bonuses/", { page_size: "200" }, MAX_PAGES),
      ]);

      payrollRuns = getSettledValue(results[0], []);
      payslips = getSettledValue(results[1], []);
      taxRecords = getSettledValue(results[2], []);
      employees = getSettledValue(results[3], []);
      deductions = getSettledValue(results[4], []);
      bonuses = getSettledValue(results[5], []);

      const allFailed = results.every((r) => r.status === "rejected");
      if (allFailed) error = "We couldn't reach the payroll reporting service right now.";
    } catch {
      error = "We couldn't reach the payroll reporting service right now.";
    } finally {
      loading = false;
      refreshing = false;
    }
  }

  onMount(() => {
    void loadData();
  });

  let bounds = $derived(periodBounds(periodFilter));

  let runsInPeriod = $derived.by(() =>
    payrollRuns.filter((row) => withinPeriod(parseDate(row.period_end ?? row.run_date ?? row.period_start), bounds))
  );

  let payslipsInPeriod = $derived.by(() =>
    payslips.filter((row) => withinPeriod(parseDate(row.period_end ?? row.period_start), bounds))
  );

  let totalNetPayroll = $derived.by(() =>
    runsInPeriod.length > 0
      ? runsInPeriod.reduce((sum, row) => sum + toAmount(row.total_net), 0)
      : payslipsInPeriod.reduce((sum, row) => sum + toAmount(row.net_salary), 0)
  );

  let totalGrossPayroll = $derived.by(() =>
    runsInPeriod.length > 0
      ? runsInPeriod.reduce((sum, row) => sum + toAmount(row.total_gross), 0)
      : payslipsInPeriod.reduce((sum, row) => sum + toAmount(row.gross_salary), 0)
  );

  let taxLiability = $derived.by(() => {
    const fiscalYear = String(bounds.year);
    return taxRecords
      .filter((row) => (periodFilter === "all_time" ? true : row.fiscal_year === fiscalYear))
      .reduce((sum, row) => sum + toAmount(row.balance), 0);
  });

  let activeHeadcount = $derived.by(() =>
    employees.filter((emp) => ACTIVE_EMPLOYMENT_STATUSES.has(emp.employment_status)).length
  );

  let averagePerEmployee = $derived.by(() => {
    const headcount = Math.max(activeHeadcount, 1);
    return totalNetPayroll / headcount;
  });

  let sortedRunsInPeriod = $derived.by(() =>
    [...runsInPeriod].sort((a, b) => {
      const left = parseDate(a.period_end)?.getTime() ?? 0;
      const right = parseDate(b.period_end)?.getTime() ?? 0;
      return right - left;
    })
  );

  let runHeadcountMap = $derived.by(() => {
    const map = new Map<number, number>();
    for (const slip of payslips) {
      if (slip.payroll_run === null) continue;
      map.set(slip.payroll_run, (map.get(slip.payroll_run) ?? 0) + 1);
    }
    return map;
  });

  // Trend: last 6 calendar months — rolling context regardless of selected period.
  let trendPoints = $derived.by(() => {
    const totalsByMonth = new Map<string, number>();
    for (const run of payrollRuns) {
      const date = parseDate(run.period_end ?? run.run_date ?? run.period_start);
      if (!date) continue;
      const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
      totalsByMonth.set(key, (totalsByMonth.get(key) ?? 0) + toAmount(run.total_net));
    }

    const months: { key: string; label: string }[] = [];
    const today = new Date();
    today.setDate(1);
    for (let index = 5; index >= 0; index -= 1) {
      const date = new Date(today);
      date.setMonth(today.getMonth() - index);
      months.push({
        key: `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`,
        label: new Intl.DateTimeFormat("en-NG", { month: "short" }).format(date),
      });
    }

    const values = months.map((month) => totalsByMonth.get(month.key) ?? 0);
    const max = Math.max(...values, 1);
    return months.map((month, idx) => ({
      key: month.key,
      label: month.label,
      value: values[idx],
      ratio: values[idx] / max,
    }));
  });

  let departmentBreakdown = $derived.by(() => {
    const empMap = new Map<number, EmployeeDirectoryItem>(employees.map((emp) => [emp.id, emp]));
    const aggregated = new Map<string, { name: string; total: number; count: number }>();

    for (const slip of payslipsInPeriod) {
      const employee = empMap.get(slip.employee);
      const deptName = employee?.department_name ?? "Unassigned";
      const current = aggregated.get(deptName) ?? { name: deptName, total: 0, count: 0 };
      current.total += toAmount(slip.net_salary);
      current.count += 1;
      aggregated.set(deptName, current);
    }

    return [...aggregated.values()].sort((a, b) => b.total - a.total);
  });

  let totalDepartmentNet = $derived(departmentBreakdown.reduce((sum, row) => sum + row.total, 0));

  let activePeriodLabel = $derived(
    PERIODS.find((option) => option.value === periodFilter)?.label ?? "Selected Period"
  );

  function exportRunsCsv() {
    if (sortedRunsInPeriod.length === 0) {
      toast.info("Nothing to export", "There are no payroll runs in the selected period yet.");
      return;
    }
    const headers = ["name", "period_start", "period_end", "headcount", "total_gross", "total_deductions", "total_net", "status"];
    const lines = [headers.join(",")];
    for (const run of sortedRunsInPeriod) {
      const headcount = runHeadcountMap.get(run.id) ?? 0;
      const row = [
        run.name,
        run.period_start,
        run.period_end,
        String(headcount),
        toAmount(run.total_gross).toFixed(2),
        toAmount(run.total_deductions).toFixed(2),
        toAmount(run.total_net).toFixed(2),
        run.status,
      ];
      lines.push(row.map(csvEscape).join(","));
    }

    const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `payroll-report-${periodFilter}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
    toast.success("Export queued", `Downloaded payroll runs for ${activePeriodLabel.toLowerCase()}.`);
  }
</script>

<svelte:head>
  <title>Payroll Reports | developerOS</title>
</svelte:head>

{#if loading}
  <div class="flex min-h-[60vh] items-center justify-center">
    <div class="flex items-center gap-3 text-sm text-neutral-500">
      <div class="h-4 w-4 rounded-full border-2 border-neutral-300 border-t-neutral-900 animate-spin"></div>
      Loading payroll reports…
    </div>
  </div>
{:else}
  <div class="space-y-4 overflow-x-clip">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">
          <a href="/payroll" class="hover:text-indigo-700">Payroll</a>
          <span class="text-neutral-300"> › </span>
          <span class="text-indigo-600">Reports</span>
        </p>
        <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Payroll Reports</h1>
        <p class="mt-1 max-w-2xl text-sm text-neutral-500">
          Review payroll summaries across periods, with trends, run breakdowns, and departmental cost composition.
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <select
          bind:value={periodFilter}
          class="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-2.5 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
        >
          {#each PERIODS as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
        <button
          type="button"
          class="inline-flex items-center gap-2 rounded-2xl border border-neutral-200 bg-white px-4 py-2.5 text-sm font-semibold text-neutral-700 transition hover:border-neutral-400 hover:text-neutral-950 disabled:opacity-50"
          onclick={() => void loadData(true)}
          disabled={refreshing}
        >
          <svg class={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.75">
            <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992V4.356m-1.636 14.288A9 9 0 1 1 21 12.003" />
          </svg>
          {refreshing ? "Refreshing…" : "Refresh"}
        </button>
        <button
          type="button"
          class="inline-flex items-center gap-2 rounded-2xl bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-neutral-800"
          onclick={exportRunsCsv}
        >
          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.75">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
          </svg>
          Export CSV
        </button>
      </div>
    </div>

    {#if error}
      <DataStateBanner message={error} onretry={() => loadData(true)} retrying={refreshing} />
    {/if}

    <div class="grid gap-4 xl:grid-cols-4">
      <div class="min-w-0 rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Total Net Payroll</p>
        <p class="mt-3 text-2xl font-bold tracking-tight tabular-nums text-neutral-900">{formatCurrency(totalNetPayroll)}</p>
        <p class="mt-2 text-xs text-neutral-500">Net amount paid in {activePeriodLabel.toLowerCase()}.</p>
      </div>

      <div class="min-w-0 rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Total Gross Payroll</p>
        <p class="mt-3 text-2xl font-bold tracking-tight tabular-nums text-neutral-900">{formatCurrency(totalGrossPayroll)}</p>
        <p class="mt-2 text-xs text-neutral-500">Gross compensation before statutory and personal deductions.</p>
      </div>

      <div class={`min-w-0 rounded-2xl border p-5 sm:p-6 ${taxLiability > 0 ? "border-orange-200 bg-orange-50" : "border-neutral-200 bg-white"}`}>
        <p class={`text-[10px] font-semibold uppercase tracking-wider ${taxLiability > 0 ? "text-orange-600" : "text-neutral-500"}`}>
          Tax Liability
        </p>
        <p class={`mt-3 text-2xl font-bold tracking-tight tabular-nums ${taxLiability > 0 ? "text-orange-900" : "text-neutral-900"}`}>
          {formatCurrency(taxLiability)}
        </p>
        <p class={`mt-2 text-xs ${taxLiability > 0 ? "text-orange-800/90" : "text-neutral-500"}`}>
          Sum of outstanding balances from tax records in {periodFilter === "all_time" ? "all fiscal years" : `FY ${bounds.year}`}.
        </p>
      </div>

      <div class="min-w-0 rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Average per Employee</p>
        <p class="mt-3 text-2xl font-bold tracking-tight tabular-nums text-neutral-900">{formatCurrency(averagePerEmployee)}</p>
        <p class="mt-2 text-xs text-neutral-500">{activeHeadcount} active staff over selected period.</p>
      </div>
    </div>

    <div class="grid gap-4 xl:grid-cols-2">
      <section class="min-w-0 rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-neutral-400">Run Summary</p>
            <h2 class="mt-2 text-lg font-semibold text-neutral-950">Payroll runs in {activePeriodLabel.toLowerCase()}</h2>
          </div>
          <span class="rounded-full border border-neutral-200 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-600">
            {sortedRunsInPeriod.length} runs
          </span>
        </div>
        <div class="mt-5 overflow-x-auto">
          {#if sortedRunsInPeriod.length === 0}
            <div class="rounded-2xl border border-dashed border-neutral-200 bg-neutral-50 px-6 py-10 text-center text-sm text-neutral-500">
              No payroll runs were processed in the selected period.
            </div>
          {:else}
            <table class="min-w-full text-sm">
              <thead>
                <tr class="bg-neutral-50 text-left text-[10px] uppercase tracking-wider text-neutral-500">
                  <th class="px-4 py-3">Run</th>
                  <th class="px-4 py-3">Period</th>
                  <th class="px-4 py-3 text-right">Headcount</th>
                  <th class="px-4 py-3 text-right">Gross</th>
                  <th class="px-4 py-3 text-right">Net</th>
                  <th class="px-4 py-3">Status</th>
                </tr>
              </thead>
              <tbody>
                {#each sortedRunsInPeriod as run}
                  <tr class="border-t border-neutral-200 hover:bg-neutral-50">
                    <td class="px-4 py-3 font-medium text-neutral-900">{run.name}</td>
                    <td class="px-4 py-3 text-neutral-700">
                      {shortDate(run.period_start)} → {shortDate(run.period_end)}
                    </td>
                    <td class="px-4 py-3 text-right tabular-nums text-neutral-900">
                      {runHeadcountMap.get(run.id) ?? 0}
                    </td>
                    <td class="px-4 py-3 text-right tabular-nums text-neutral-900">
                      {formatCurrency(toAmount(run.total_gross))}
                    </td>
                    <td class="px-4 py-3 text-right tabular-nums text-neutral-900">
                      {formatCurrency(toAmount(run.total_net))}
                    </td>
                    <td class="px-4 py-3">
                      <span class={`${CHIP_BASE} ${chipClassFor(RUN_STATUS_CLASSES, run.status)}`}>
                        {formatStatusLabel(run.status)}
                      </span>
                    </td>
                  </tr>
                {/each}
              </tbody>
            </table>
          {/if}
        </div>
      </section>

      <section class="min-w-0 rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-neutral-400">Trend</p>
            <h2 class="mt-2 text-lg font-semibold text-neutral-950">Net pay by month (last 6)</h2>
            <p class="mt-1 text-sm text-neutral-500">Independent of the selected period — rolling six-month context.</p>
          </div>
        </div>

        <div class="mt-6 flex h-48 items-end gap-3">
          {#each trendPoints as point}
            <div class="flex flex-1 flex-col items-center gap-2">
              <div class="relative flex h-40 w-full items-end">
                <div
                  class="w-full rounded-t-lg bg-neutral-900 transition-all duration-500"
                  style={`height: ${Math.max(point.ratio * 100, point.value > 0 ? 4 : 0)}%`}
                ></div>
              </div>
              <span class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">{point.label}</span>
              <span class="text-[10px] tabular-nums text-neutral-400">{formatCurrency(point.value)}</span>
            </div>
          {/each}
        </div>
      </section>
    </div>

    <section class="min-w-0 rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
      <div class="flex items-start justify-between gap-4">
        <div>
          <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-neutral-400">Cost Breakdown</p>
          <h2 class="mt-2 text-lg font-semibold text-neutral-950">Departmental composition</h2>
          <p class="mt-1 text-sm text-neutral-500">Aggregated net pay across departments for the selected period.</p>
        </div>
        <span class="rounded-full border border-neutral-200 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-600">
          {departmentBreakdown.length} departments
        </span>
      </div>

      <div class="mt-5">
        {#if departmentBreakdown.length === 0}
          <div class="rounded-2xl border border-dashed border-neutral-200 bg-neutral-50 px-6 py-10 text-center text-sm text-neutral-500">
            No departmental cost data for the selected period.
          </div>
        {:else}
          <div class="space-y-3">
            {#each departmentBreakdown as dept}
              {@const ratio = totalDepartmentNet > 0 ? dept.total / totalDepartmentNet : 0}
              <div class="rounded-2xl border border-neutral-200 bg-white px-4 py-3">
                <div class="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p class="text-sm font-semibold text-neutral-900">{dept.name}</p>
                    <p class="text-xs text-neutral-500">{dept.count} payslip{dept.count === 1 ? "" : "s"}</p>
                  </div>
                  <div class="text-right">
                    <p class="text-sm font-semibold tabular-nums text-neutral-900">{formatCurrency(dept.total)}</p>
                    <p class="text-xs tabular-nums text-neutral-500">{(ratio * 100).toFixed(1)}%</p>
                  </div>
                </div>
                <div class="mt-2 h-1.5 overflow-hidden rounded-full bg-neutral-100">
                  <div class="h-full rounded-full bg-neutral-900" style={`width: ${(ratio * 100).toFixed(2)}%`}></div>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </section>
  </div>
{/if}

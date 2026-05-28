<script lang="ts">
  import { api } from "$lib/api";
  import { currency } from "$lib/stores/currency.svelte";
  import type { FinanceCashFlow } from "$lib/types";

  let data = $state<FinanceCashFlow | null>(null);
  let loading = $state(true);
  let selectedYear = $state(new Date().getFullYear());
  let mounted = $state(false);

  async function fetchDashboard() {
    loading = true;
    try {
      data = await api.get<FinanceCashFlow>(`/finance/cash-flow/?year=${selectedYear}`);
    } catch {
      data = null;
    }
    loading = false;
    mounted = false;
    requestAnimationFrame(() => {
      mounted = true;
    });
  }

  $effect(() => {
    fetchDashboard();
  });

  const yearOptions = $derived.by(() => {
    const now = new Date().getFullYear();
    return [now, now - 1, now - 2];
  });

  // Split currency value into dollars and cents for display
  function splitAmount(val: string): { dollars: string; cents: string } {
    const num = Number(val);
    const formatted = currency.format(num);
    const dotIdx = formatted.lastIndexOf(".");
    if (dotIdx === -1) return { dollars: formatted, cents: "" };
    return {
      dollars: formatted.slice(0, dotIdx),
      cents: formatted.slice(dotIdx),
    };
  }

  // Income sparkline bars (last 6 months with data)
  const sparkBars = $derived.by(() => {
    if (!data) return [];
    return data.monthly_flow
      .map((m) => Number(m.income))
      .slice(-6);
  });
  const sparkMax = $derived(Math.max(...sparkBars, 1));

  // Expense progress data: total goal line
  const expenseMonthly = $derived.by(() => {
    if (!data) return [];
    return data.monthly_flow.map((m) => Number(m.expenses));
  });
  const expenseMax = $derived(Math.max(...expenseMonthly, 1));

  // Income breakdown by customer for sub-metrics
  const incomeBreakdown = $derived.by(() => {
    if (!data) return [];
    return data.income_by_customer.slice(0, 3).map((c) => ({
      label: c.label,
      value: currency.formatAbbreviated(c.value),
    }));
  });

  // Money flow bar chart
  const flowMax = $derived.by(() => {
    if (!data) return 1;
    return Math.max(
      ...data.monthly_flow.flatMap((m) => [Number(m.income), Number(m.expenses)]),
      1
    );
  });

  // Budget ring
  const ringR = 58;
  const ringStroke = 12;
  const ringC = 2 * Math.PI * ringR;
  const budgetOffset = $derived(
    data ? ringC - (data.budget_pct_remaining / 100) * ringC : ringC
  );

  // Vendor expense bars for the breakdown section
  const vendorMax = $derived.by(() => {
    if (!data || data.expense_by_vendor.length === 0) return 1;
    return Math.max(...data.expense_by_vendor.map((v) => Number(v.value)), 1);
  });

  // Cash Flow section derived metrics
  const avgMonthlyIncome = $derived.by(() => {
    if (!data) return 0;
    const months = data.monthly_flow.filter((m) => Number(m.income) > 0);
    if (months.length === 0) return 0;
    return months.reduce((s, m) => s + Number(m.income), 0) / months.length;
  });

  const operationalCosts = $derived(data ? Number(data.total_expenses) : 0);

  const revenueGrowth = $derived.by(() => {
    if (!data) return 0;
    const incomes = data.monthly_flow.map((m) => Number(m.income)).filter((v) => v > 0);
    if (incomes.length < 2) return 0;
    const prev = incomes[incomes.length - 2];
    const curr = incomes[incomes.length - 1];
    return prev > 0 ? ((curr - prev) / prev) * 100 : 0;
  });

  const expenseRatio = $derived.by(() => {
    if (!data) return 0;
    const inc = Number(data.total_income);
    if (inc === 0) return 0;
    return (Number(data.total_expenses) / inc) * 100;
  });

  const netProfitMargin = $derived.by(() => {
    if (!data) return 0;
    const inc = Number(data.total_income);
    if (inc === 0) return 0;
    return ((inc - Number(data.total_expenses)) / inc) * 100;
  });

  // Cash flow timeline: which month are we in
  const currentMonthIdx = $derived.by(() => {
    if (!data || data.year !== new Date().getFullYear()) return -1;
    return new Date().getMonth();
  });
</script>

<svelte:head>
  <style>
    @keyframes fadeSlideUp {
      from { opacity: 0; transform: translateY(16px); }
      to { opacity: 1; transform: translateY(0); }
    }
    @keyframes scaleIn {
      from { opacity: 0; transform: scale(0.92); }
      to { opacity: 1; transform: scale(1); }
    }
    @keyframes drawIn {
      from { stroke-dashoffset: var(--ring-c); }
    }
    @keyframes barGrow {
      from { transform: scaleY(0); }
      to { transform: scaleY(1); }
    }
    @keyframes progressGrow {
      from { width: 0; }
    }
    .dash-anim {
      animation: fadeSlideUp 0.5s ease-out both;
    }
    .dash-anim-d1 { animation-delay: 0.05s; }
    .dash-anim-d2 { animation-delay: 0.1s; }
    .dash-anim-d3 { animation-delay: 0.15s; }
    .dash-anim-d4 { animation-delay: 0.25s; }
    .dash-anim-d5 { animation-delay: 0.35s; }
    .dash-anim-d6 { animation-delay: 0.45s; }
    .dash-anim-d7 { animation-delay: 0.55s; }
    @keyframes pulseGlow {
      0%, 100% { box-shadow: 0 0 8px rgba(16, 185, 129, 0.3); }
      50% { box-shadow: 0 0 16px rgba(16, 185, 129, 0.5); }
    }
    .pulse-glow { animation: pulseGlow 2s ease-in-out infinite; }
    @keyframes slideBarIn {
      from { transform: scaleX(0); }
      to { transform: scaleX(1); }
    }
    .slide-bar {
      animation: slideBarIn 0.8s ease-out both;
      transform-origin: left;
    }
    .dash-scale {
      animation: scaleIn 0.4s ease-out both;
    }
    .bar-grow {
      animation: barGrow 0.6s ease-out both;
      transform-origin: bottom;
    }
    .progress-grow {
      animation: progressGrow 0.8s ease-out both;
    }
  </style>
</svelte:head>

{#if loading}
  <div class="flex items-center justify-center py-32">
    <div class="inline-block w-7 h-7 border-[2.5px] border-emerald-100 border-t-emerald-600 rounded-full animate-spin"></div>
  </div>
{:else if data}
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between dash-anim">
      <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-pink-600">Finance</p>
        <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Intelligence</h1>
        <p class="text-sm text-neutral-400 mt-0.5">Turn project data into clear, actionable financial insights</p>
      </div>
      <div class="flex items-center gap-2">
        <select
          bind:value={selectedYear}
          onchange={() => fetchDashboard()}
          class="px-3 py-1.5 text-xs font-medium text-neutral-700 bg-white border border-neutral-200 rounded-lg cursor-pointer hover:border-neutral-300 focus:outline-none focus:ring-2 focus:ring-emerald-500/20 focus:border-emerald-400 transition-all"
        >
          {#each yearOptions as yr}
            <option value={yr}>{yr}</option>
          {/each}
        </select>
      </div>
    </div>

    <!-- Row 1: Three KPI cards matching the Dribbble layout -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">

      <!-- My Balance Card -->
      <div class="dash-anim dash-anim-d1 bg-white rounded-2xl border border-neutral-100 shadow-sm px-6 py-6 hover:shadow-md transition-shadow">
        <div class="flex items-center justify-between mb-4">
          <p class="text-md font-bold text-pink-600">Balance</p>
          <span class="text-[10px] text-neutral-400 font-medium">All time</span>
        </div>
        <p class="text-[10px] text-neutral-600 uppercase tracking-wider mb-1">Total balance</p>
        <p class="text-[22px] font-bold text-neutral-800 tabular-nums leading-none tracking-tight">
          {splitAmount(data.net_balance).dollars}<span class="text-lg text-neutral-400 font-semibold">{splitAmount(data.net_balance).cents}</span>
        </p>
        <div class="mt-5 space-y-2">
          <div class="flex items-center gap-2 text-xs">
            <span class="inline-flex items-center justify-center w-5 h-5 rounded-full bg-emerald-50">
              <svg class="w-3 h-3 text-emerald-500" viewBox="0 0 12 12" fill="none"><path d="M6 9V3m0 0L3 6m3-3l3 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </span>
            <span class="text-neutral-500 mt-1">Total earned last time</span>
            <span class="text-emerald-600 font-semibold ml-auto">+{currency.format(data.total_income)}</span>
          </div>
          <div class="flex items-center gap-2 text-xs">
            <span class="inline-flex items-center justify-center w-5 h-5 rounded-full bg-emerald-50">
              <svg class="w-3 h-3 text-emerald-500" viewBox="0 0 12 12" fill="none"><path d="M4 6.5L6 3l2 3.5M3 9h6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </span>
            <span class="text-neutral-500">Total receivable</span>
            <span class="text-emerald-600 font-semibold ml-auto">+{currency.format(data.total_income)}</span>
          </div>
        </div>
      </div>

      <!-- My Income Card -->
      <div class="dash-anim dash-anim-d2 bg-white rounded-2xl border border-neutral-100 shadow-sm px-6 py-6 hover:shadow-md transition-shadow">
        <div class="flex items-center justify-between mb-4">
          <p class="text-md font-bold text-pink-600">Income</p>
          <span class="text-[10px] text-neutral-400 font-medium">{data.year}</span>
        </div>
        <div class="flex items-end justify-between">
          <div>
            <p class="text-[10px] text-neutral-600 uppercase tracking-wider mb-1">Total income</p>
            <p class="text-[22px] font-bold text-neutral-800 tabular-nums leading-none tracking-tight">
              {splitAmount(data.total_income).dollars}<span class="text-base text-neutral-400 font-semibold">{splitAmount(data.total_income).cents}</span>
            </p>
          </div>
          <!-- Mini sparkline bars -->
          <div class="flex items-end gap-[3px] h-10 mb-1">
            {#each sparkBars as val, i}
              {@const h = Math.max((val / sparkMax) * 36, 3)}
              <div
                class="w-[7px] rounded-sm bar-grow"
                style="height: {h}px; background: {i === sparkBars.length - 1 ? '#059669' : i >= sparkBars.length - 2 ? '#34d399' : '#a7f3d0'}; animation-delay: {0.15 + i * 0.06}s;"
              ></div>
            {/each}
          </div>
        </div>

        <!-- Breakdown chips -->
        {#if incomeBreakdown.length > 0}
          <div class="mt-5 flex items-center gap-4">
            {#each incomeBreakdown as item}
              <div class="text-center">
                <p class="text-xs font-semibold text-emerald-600 tabular-nums">{item.value}</p>
                <p class="text-[9px] text-neutral-400 mt-0.5 truncate max-w-[72px]">{item.label}</p>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Total Expense Card -->
      <div class="dash-anim dash-anim-d3 bg-white rounded-2xl border border-neutral-100 shadow-sm px-6 py-6 hover:shadow-md transition-shadow">
        <div class="flex items-start justify-between mb-2">
          <div>
            <p class="text-md font-bold text-pink-600">Expenses</p>
            <p class="text-[10px] text-neutral-600 tracking wider uppercase mt-1">Total expense</p>
            <p class="text-[22px] font-bold text-neutral-800 tabular-nums leading-none tracking-tight">
              {splitAmount(data.total_expenses).dollars}<span class="text-lg text-neutral-400 font-semibold">{splitAmount(data.total_expenses).cents}</span>
            </p>
          </div>
        </div>

        <!-- Monthly expense mini-bars (horizontal stacked look) -->
        <div class="mt-4 space-y-[5px]">
          {#each data.monthly_flow.slice(-6) as m, i}
            {@const val = Number(m.expenses)}
            {@const pct = Math.max((val / expenseMax) * 100, 2)}
            <div class="flex items-center gap-2">
              <span class="text-[9px] text-neutral-400 w-6 text-right">{m.month}</span>
              <div class="flex-1 h-[14px] bg-neutral-50 rounded-full overflow-hidden">
                <div
                  class="h-full rounded-full progress-grow"
                  style="width: {pct}%; background: {['#064e3b','#065f46','#047857','#059669','#10b981','#34d399'][i]}; animation-delay: {0.2 + i * 0.08}s;"
                ></div>
              </div>
              <span class="text-[9px] text-neutral-500 tabular-nums w-12 text-right">{currency.formatAbbreviated(val)}</span>
            </div>
          {/each}
        </div>
      </div>
    </div>

    <!-- Cash Flow Panel -->
    <div class="dash-anim dash-anim-d3 bg-white rounded-2xl border border-neutral-100 shadow-sm px-7 py-6 hover:shadow-md transition-shadow">
      <div class="flex items-center justify-between mb-6">
        <p class="text-md font-bold text-pink-600">Cash Flow</p>
        <span class="text-[10px] text-neutral-400 font-medium">Monthly</span>
      </div>

      <!-- 5 KPI metrics row -->
      <div class="grid grid-cols-2 md:grid-cols-5 gap-6 mb-6">
        <div>
          <p class="text-[22px] font-bold text-neutral-800 tabular-nums leading-none tracking-tight">
            {currency.formatAbbreviated(data.total_income)}
          </p>
          <p class="text-[11px] text-neutral-400 mt-1.5">Incoming Funds</p>
        </div>
        <div>
          <p class="text-[22px] font-bold text-neutral-800 tabular-nums leading-none tracking-tight">
            {currency.formatAbbreviated(avgMonthlyIncome)}
          </p>
          <p class="text-[11px] text-neutral-400 mt-1.5">Recurring Income</p>
        </div>
        <div>
          <p class="text-[22px] font-bold text-neutral-800 tabular-nums leading-none tracking-tight">
            {currency.formatAbbreviated(operationalCosts)}
          </p>
          <p class="text-[11px] text-neutral-400 mt-1.5">Operational Costs</p>
        </div>
        <div>
          <p class="text-[22px] font-bold text-neutral-800 tabular-nums leading-none tracking-tight">
            {currency.formatAbbreviated(Number(data.total_income) - operationalCosts)}
          </p>
          <p class="text-[11px] text-neutral-400 mt-1.5">Net Surplus</p>
        </div>
        <div>
          <p class="text-[22px] font-bold text-neutral-800 tabular-nums leading-none tracking-tight">
            {currency.formatAbbreviated(data.net_balance)}
          </p>
          <p class="text-[11px] text-neutral-400 mt-1.5">Net Balance</p>
        </div>
      </div>

      <!-- Metrics chip -->
      <div class="flex items-center justify-end mb-3">
        <div class="inline-flex items-center gap-3 bg-neutral-50 rounded-lg px-4 py-1.5 text-[10px]">
          <span class="text-neutral-400">Revenue Growth: <span class="{revenueGrowth >= 0 ? 'text-emerald-600' : 'text-red-500'} font-semibold">{revenueGrowth >= 0 ? '+' : ''}{revenueGrowth.toFixed(1)}%</span></span>
          <span class="text-neutral-200">|</span>
          <span class="text-neutral-400">Expense Ratio: <span class="text-emerald-600 font-semibold">{expenseRatio.toFixed(0)}%</span></span>
          <span class="text-neutral-200">|</span>
          <span class="text-neutral-400">Net Profit Margin: <span class="text-neutral-800 font-semibold">{netProfitMargin.toFixed(0)}%</span></span>
        </div>
      </div>

      <!-- Timeline bar -->
      <div class="flex items-center gap-[2px] h-9">
        {#each data.monthly_flow as m, i}
          {@const val = Number(m.income)}
          {@const h = Math.max((val / (flowMax || 1)) * 28, 2)}
          {@const isCurrent = i === currentMonthIdx}
          {#if isCurrent}
            <div class="relative flex-1 h-full flex items-center justify-center rounded-md bg-linear-to-r from-emerald-500/30 to-emerald-400/20 pulse-glow">
              <div class="w-3 h-3 rounded-full bg-emerald-500 border-2 border-emerald-300 shadow-lg"></div>
            </div>
          {:else if i < currentMonthIdx || currentMonthIdx === -1}
            <div class="flex-1 h-full flex items-end justify-center">
              <div
                class="w-[3px] rounded-sm slide-bar"
                style="height: {h}px; background: #047857; animation-delay: {0.5 + i * 0.03}s;"
              ></div>
            </div>
          {:else}
            <div class="flex-1 h-full flex items-center justify-center">
              <div
                class="w-[18px] h-[18px] rounded-[3px] slide-bar"
                style="background: #a7f3d0; opacity: {0.5 + ((i - currentMonthIdx) / 12) * 0.5}; animation-delay: {0.5 + i * 0.03}s;"
              ></div>
            </div>
          {/if}
        {/each}
      </div>
    </div>

    <!-- Row 2: Money Flow + Remaining Monthly -->
    <div class="grid grid-cols-1 lg:grid-cols-[1fr_340px] gap-4">

      <!-- Money Flow Chart -->
      <div class="dash-anim dash-anim-d4 bg-white rounded-2xl border border-neutral-100 shadow-sm px-6 py-6 hover:shadow-md transition-shadow">
        <div class="flex items-center justify-between mb-6">
          <p class="text-md font-bold text-pink-600">Money Flow</p>
          <div class="flex items-center gap-4">
            <span class="inline-flex items-center gap-1.5 text-[11px] text-neutral-500">
              <span class="inline-block w-2.5 h-2.5 rounded-sm bg-[#065f46]"></span>
              Income
            </span>
            <span class="inline-flex items-center gap-1.5 text-[11px] text-neutral-500">
              <span class="inline-block w-2.5 h-2.5 rounded-sm bg-[#86efac]"></span>
              Expense
            </span>
          </div>
        </div>

        <!-- Custom grouped bar chart with green palette -->
        <div class="w-full overflow-hidden" style="height: 260px;">
          <svg width="100%" height="100%" viewBox="0 0 720 260" preserveAspectRatio="xMidYMid meet" class="font-sans">
            <g transform="translate(56, 12)">
              <!-- Y-axis gridlines -->
              {#each [0, 0.25, 0.5, 0.75, 1] as tick}
                {@const y = 210 - tick * 210}
                <line x1={0} y1={y} x2={640} y2={y} stroke="#f5f5f5" stroke-width="1" />
                <text x={-8} y={y} dy="0.32em" text-anchor="end" class="text-[9px] fill-neutral-400" font-family="inherit">
                  {currency.formatAbbreviated(flowMax * tick)}
                </text>
              {/each}

              <!-- Bars -->
              {#each data.monthly_flow as m, i}
                {@const x = i * (640 / 12) + 8}
                {@const barW = 18}
                {@const incH = (Number(m.income) / flowMax) * 210}
                {@const expH = (Number(m.expenses) / flowMax) * 210}
                <!-- Income bar -->
                <rect
                  x={x}
                  y={210 - incH}
                  width={barW}
                  height={Math.max(incH, 0)}
                  rx={3}
                  fill="#065f46"
                  class="bar-grow"
                  style="animation-delay: {0.3 + i * 0.04}s;"
                >
                  <title>Income: {currency.format(m.income)}</title>
                </rect>
                <!-- Expense bar -->
                <rect
                  x={x + barW + 2}
                  y={210 - expH}
                  width={barW}
                  height={Math.max(expH, 0)}
                  rx={3}
                  fill="#86efac"
                  class="bar-grow"
                  style="animation-delay: {0.35 + i * 0.04}s;"
                >
                  <title>Expense: {currency.format(m.expenses)}</title>
                </rect>
                <!-- Month label -->
                <text
                  x={x + barW + 1}
                  y={228}
                  text-anchor="middle"
                  class="text-[10px] fill-neutral-400"
                  font-family="inherit"
                >{m.month}</text>
              {/each}

              <!-- Baseline -->
              <line x1={0} y1={210} x2={640} y2={210} stroke="#e5e5e5" stroke-width="1" />
            </g>
          </svg>
        </div>
      </div>

      <!-- Remaining Monthly / Budget -->
      <div class="dash-anim dash-anim-d5 bg-white rounded-2xl border border-neutral-100 shadow-sm px-6 py-6 hover:shadow-md transition-shadow">
        <div class="flex items-center justify-between mb-6">
          <p class="text-md font-bold text-pink-600">Remaining Monthly</p>
          <a href="/finance/budgets" class="text-[10px] text-emerald-600 font-medium hover:text-emerald-800 transition-colors">
            Budget setting &rarr;
          </a>
        </div>

        <!-- Big percentage -->
        <p class="text-[56px] font-bold text-neutral-800 tabular-nums leading-none">
          {Math.round(data.budget_pct_remaining)}<span class="text-2xl text-neutral-400 font-semibold">%</span>
        </p>

        {#if data.budget_pct_remaining > 50}
          <p class="text-xs text-neutral-500 mt-2 leading-relaxed">
            You're in great shape &mdash;<br>your monthly usage is still very safe.
          </p>
        {:else if data.budget_pct_remaining > 20}
          <p class="text-xs text-amber-600 mt-2 leading-relaxed">
            Budget is halfway used &mdash;<br>monitor spending carefully.
          </p>
        {:else}
          <p class="text-xs text-red-500 mt-2 leading-relaxed">
            Budget is nearly exhausted &mdash;<br>review spending immediately.
          </p>
        {/if}

        <!-- Vendor expense breakdown bars -->
        <div class="mt-6 space-y-3">
          {#each data.expense_by_vendor.slice(0, 4) as vendor, i}
            {@const pct = (Number(vendor.value) / vendorMax) * 100}
            <div>
              <div class="flex items-center justify-between mb-1">
                <span class="text-[10px] text-neutral-500 truncate max-w-[140px]">{vendor.label}</span>
                <span class="text-[10px] font-semibold text-neutral-700 tabular-nums">{currency.formatAbbreviated(vendor.value)}</span>
              </div>
              <div class="h-5 bg-neutral-50 rounded-md overflow-hidden">
                <div
                  class="h-full rounded-md progress-grow"
                  style="width: {pct}%; background: {['#064e3b','#059669','#34d399','#a7f3d0'][i]}; animation-delay: {0.4 + i * 0.1}s;"
                ></div>
              </div>
            </div>
          {/each}
        </div>
      </div>
    </div>

    <!-- Row 3: Income by customer donut + Budget ring -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <!-- Income by Customer -->
      <div class="dash-anim dash-anim-d5 bg-white rounded-2xl border border-neutral-100 shadow-sm px-6 py-6 hover:shadow-md transition-shadow">
        <p class="text-md font-bold text-pink-600 mb-5">Income by Customer</p>
        {#if data.income_by_customer.length > 0}
          <div class="flex items-center gap-8">
            <!-- Donut -->
            <div class="relative shrink-0" style="width: 160px; height: 160px;">
              <svg width="160" height="160" class="transform -rotate-90">
                {#each data.income_by_customer as cust, i}
                  {@const total = data.income_by_customer.reduce((s, c) => s + Number(c.value), 0)}
                  {@const pct = Number(cust.value) / total}
                  {@const prevPct = data.income_by_customer.slice(0, i).reduce((s, c) => s + Number(c.value) / total, 0)}
                  {@const r = 62}
                  {@const circ = 2 * Math.PI * r}
                  <circle
                    cx="80" cy="80" r={r}
                    fill="none"
                    stroke={["#064e3b","#047857","#10b981","#6ee7b7","#d1fae5"][i]}
                    stroke-width="28"
                    stroke-dasharray="{pct * circ - 3} {circ}"
                    stroke-dashoffset={-prevPct * circ}
                    class="transition-all duration-700"
                  />
                {/each}
              </svg>
              <div class="absolute inset-0 flex flex-col items-center justify-center">
                <span class="text-lg font-bold text-neutral-800 tabular-nums">{currency.formatAbbreviated(data.total_income)}</span>
                <span class="text-[9px] text-neutral-400 uppercase tracking-wider">Income</span>
              </div>
            </div>

            <!-- Legend -->
            <div class="flex flex-col gap-2.5">
              {#each data.income_by_customer as cust, i}
                <div class="flex items-center gap-2.5">
                  <div class="w-3 h-3 rounded-sm shrink-0" style="background: {['#064e3b','#047857','#10b981','#6ee7b7','#d1fae5'][i]};"></div>
                  <div>
                    <p class="text-xs text-neutral-700 leading-none">{cust.label}</p>
                    <p class="text-[10px] text-neutral-400 tabular-nums mt-0.5">{currency.format(cust.value)}</p>
                  </div>
                </div>
              {/each}
            </div>
          </div>
        {:else}
          <div class="py-8 text-center">
            <p class="text-sm text-neutral-400">No income data yet</p>
          </div>
        {/if}
      </div>

      <!-- Budget Utilization Ring -->
      <div class="dash-anim dash-anim-d5 bg-white rounded-2xl border border-neutral-100 shadow-sm px-6 py-6 hover:shadow-md transition-shadow">
        <p class="text-md font-bold text-pink-600 mb-5">Budget Utilization</p>
        <div class="flex items-center gap-8">
          <div class="relative shrink-0" style="width: 148px; height: 148px;">
            <svg width="148" height="148" class="transform -rotate-90">
              <circle
                cx="74" cy="74" r={ringR}
                fill="none" stroke="#f0fdf4" stroke-width={ringStroke}
              />
              <circle
                cx="74" cy="74" r={ringR}
                fill="none"
                stroke={data.budget_pct_remaining > 50 ? "#059669" : data.budget_pct_remaining > 20 ? "#f59e0b" : "#ef4444"}
                stroke-width={ringStroke}
                stroke-dasharray={ringC}
                stroke-dashoffset={budgetOffset}
                stroke-linecap="round"
                style="--ring-c: {ringC}; transition: stroke-dashoffset 1s ease-out;"
              />
            </svg>
            <div class="absolute inset-0 flex flex-col items-center justify-center">
              <span class="text-2xl font-bold text-neutral-800 tabular-nums">{data.budget_pct_remaining}%</span>
              <span class="text-[9px] text-neutral-400">remaining</span>
            </div>
          </div>
          <div class="space-y-3">
            <div>
              <p class="text-xs text-neutral-400">Spent</p>
              <p class="text-sm font-semibold text-neutral-800 tabular-nums">{(100 - data.budget_pct_remaining).toFixed(1)}%</p>
            </div>
            <div>
              <p class="text-xs text-neutral-400">Remaining</p>
              <p class="text-sm font-semibold text-emerald-700 tabular-nums">{data.budget_pct_remaining}%</p>
            </div>
            <div class="h-2 w-32 bg-neutral-100 rounded-full overflow-hidden">
              <div
                class="h-full rounded-full progress-grow"
                style="width: {100 - data.budget_pct_remaining}%; background: {data.budget_pct_remaining > 50 ? '#059669' : data.budget_pct_remaining > 20 ? '#f59e0b' : '#ef4444'}; animation-delay: 0.5s;"
              ></div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Row 5: AI Analysis Prompt -->
    <div class="dash-anim dash-anim-d7 bg-white rounded-2xl border border-neutral-100 shadow-sm px-7 py-5 hover:shadow-md transition-shadow">
      <div class="flex items-center gap-3 mb-4">
        <svg class="w-5 h-5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 0 0-2.455 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z" />
        </svg>
        <p class="text-sm font-medium text-neutral-800">What area would you like to analyze next?</p>
      </div>
      <div class="relative">
        <input
          type="text"
          placeholder="I want to identify the reason behind the decline from authorized to successful payments"
          disabled
          class="w-full bg-neutral-50 text-sm text-neutral-500 placeholder-neutral-400 rounded-xl border border-neutral-200 px-4 py-3 focus:outline-none cursor-not-allowed"
        />
        <span class="absolute right-3 top-1/2 -translate-y-1/2 text-[9px] text-neutral-400 uppercase tracking-wider">Coming soon</span>
      </div>
    </div>
  </div>
{:else}
  <div class="flex flex-col items-center justify-center py-32">
    <div class="w-12 h-12 rounded-full bg-red-50 flex items-center justify-center mb-4">
      <svg class="w-6 h-6 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
      </svg>
    </div>
    <p class="text-sm text-neutral-500">Failed to load dashboard data</p>
    <button
      onclick={() => fetchDashboard()}
      class="mt-4 px-5 py-2 text-xs font-medium text-white bg-emerald-600 rounded-lg hover:bg-emerald-700 transition-colors shadow-sm"
    >
      Try Again
    </button>
  </div>
{/if}

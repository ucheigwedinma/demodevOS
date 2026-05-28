<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { onMount } from "svelte";

  interface BomSummary {
    id: number; bom_number: string; name: string;
    project: number | null; project_name: string | null;
    status: string; version: number; confidence_pct: number;
    margin_pct: string; vat_pct: string; site_location: string;
    total_estimated_cost: string; subtotal: string;
    vat_amount: string; margin_amount: string; grand_total: string;
    fx_rate_usd_ngn: string; item_count: number;
    created_by_name: string; created_at: string; updated_at: string;
  }
  interface BomItem {
    id: number; material_name: string; category: string; section: string;
    quantity: string; unit_of_measure: string; unit_cost: string; line_total: string;
    supplier: string; is_approved: boolean; price_volatile: boolean;
    waste_factor_pct: string; item_markup_pct: string; lead_time_days: number;
    effective_line_total: string;
  }
  interface BomDetail extends BomSummary { description: string; items: BomItem[]; }

  // --- State ---
  let loading = $state(true);
  let allBoms = $state<BomSummary[]>([]);
  let selectedBomId = $state<number | null>(null);
  let activeBom = $state<BomDetail | null>(null);

  let displayCurrency = $state<"NGN" | "USD">("NGN");
  let contingencyPct = $state(5);
  let inflationPct = $state(0);

  // Scenario drawer
  let showScenario = $state(false);
  let scenarioVisible = $state(false);
  let scenarioCategory = $state("");
  let scenarioPricing = $state<"current" | "optimistic" | "pessimistic">("current");

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  // --- Computed ---
  const fxRate = $derived(activeBom ? Number(activeBom.fx_rate_usd_ngn) || 1550 : 1550);
  const subtotal = $derived(activeBom ? Number(activeBom.total_estimated_cost || 0) : 0);
  const marginPct = $derived(activeBom ? Number(activeBom.margin_pct || 0) : 0);
  const vatPct = $derived(activeBom ? Number(activeBom.vat_pct || 0) : 0);

  const scenarioMultiplier = $derived(
    scenarioPricing === "optimistic" ? 0.9 : scenarioPricing === "pessimistic" ? 1.15 : 1,
  );
  const inflationMultiplier = $derived(1 + inflationPct / 100);
  const adjustedSubtotal = $derived(subtotal * scenarioMultiplier * inflationMultiplier);
  const contingencyAmount = $derived(adjustedSubtotal * contingencyPct / 100);
  const vatAmount = $derived(adjustedSubtotal * vatPct / 100);
  const marginAmount = $derived(adjustedSubtotal * marginPct / 100);
  const grandTotal = $derived(adjustedSubtotal + contingencyAmount + vatAmount + marginAmount);

  const confidenceColor = $derived(
    activeBom ? (activeBom.confidence_pct >= 90 ? "text-emerald-600" : activeBom.confidence_pct >= 60 ? "text-blue-600" : "text-amber-600") : "text-neutral-400",
  );

  // Work packages (grouped by section)
  const workPackages = $derived.by(() => {
    if (!activeBom || activeBom.items.length === 0) return [];
    const map = new Map<string, { category: string; items: BomItem[]; total: number; verifiedCount: number; volatileCount: number }>();
    for (const item of activeBom.items) {
      const sec = item.section || "Uncategorized";
      if (!map.has(sec)) map.set(sec, { category: item.category || "general", items: [], total: 0, verifiedCount: 0, volatileCount: 0 });
      const entry = map.get(sec)!;
      const lt = Number(item.effective_line_total || item.line_total || 0);
      entry.items.push(item);
      entry.total += lt;
      if (item.is_approved) entry.verifiedCount++;
      if (item.price_volatile) entry.volatileCount++;
    }
    const arr = Array.from(map.entries()).map(([name, data], idx) => ({
      code: String(idx + 1).padStart(2, "0"),
      name,
      category: data.category,
      estimated: data.total * scenarioMultiplier * inflationMultiplier,
      rawTotal: data.total,
      pctOfTotal: adjustedSubtotal > 0 ? (data.total * scenarioMultiplier * inflationMultiplier) / adjustedSubtotal * 100 : 0,
      status: data.volatileCount > 0 ? "Estimated" : data.verifiedCount === data.items.length ? "Verified" : "Market Rate",
      itemCount: data.items.length,
      verifiedCount: data.verifiedCount,
    }));
    return arr.sort((a, b) => b.estimated - a.estimated);
  });

  // Category breakdown for donut
  const CHART_COLORS = ["#10b981", "#3b82f6", "#f59e0b", "#8b5cf6", "#f43f5e", "#0ea5e9", "#f97316", "#14b8a6", "#818cf8", "#737373"];
  const categoryBreakdown = $derived.by(() => {
    if (!activeBom || activeBom.items.length === 0) return [];
    const map = new Map<string, number>();
    for (const item of activeBom.items) {
      const cat = item.category || "other";
      map.set(cat, (map.get(cat) || 0) + Number(item.effective_line_total || item.line_total || 0));
    }
    const total = [...map.values()].reduce((s, v) => s + v, 0) || 1;
    return Array.from(map.entries())
      .map(([cat, val]) => ({ category: cat, value: val, pct: val / total * 100 }))
      .sort((a, b) => b.value - a.value);
  });

  // Cash flow (monthly spread)
  const cashFlow = $derived.by(() => {
    if (workPackages.length === 0) return [];
    const months = 6;
    const perMonth = grandTotal / months;
    let cumulative = 0;
    return Array.from({ length: months }, (_, i) => {
      cumulative += perMonth;
      return { month: `M${i + 1}`, spend: perMonth, cumulative };
    });
  });
  const maxCumulative = $derived(cashFlow.length > 0 ? cashFlow[cashFlow.length - 1].cumulative : 1);

  // Benchmark: compare current estimate against other BoQs
  const benchmarks = $derived.by(() => {
    if (!activeBom || allBoms.length < 2) return [];
    const currentTotal = grandTotal;
    const currentPerItem = activeBom.item_count > 0 ? currentTotal / activeBom.item_count : 0;
    return allBoms
      .filter(b => b.id !== activeBom!.id && Number(b.grand_total || b.total_estimated_cost || 0) > 0)
      .map(b => {
        const bTotal = Number(b.grand_total || b.total_estimated_cost || 0);
        const bPerItem = b.item_count > 0 ? bTotal / b.item_count : 0;
        const diffPct = bTotal > 0 ? ((currentTotal - bTotal) / bTotal) * 100 : 0;
        const perItemDiffPct = bPerItem > 0 ? ((currentPerItem - bPerItem) / bPerItem) * 100 : 0;
        return {
          name: b.name,
          bom_number: b.bom_number,
          project_name: b.project_name,
          total: bTotal,
          itemCount: b.item_count,
          diffPct,
          perItemDiffPct,
          isHigher: diffPct > 0,
        };
      })
      .sort((a, b) => Math.abs(a.diffPct) - Math.abs(b.diffPct))
      .slice(0, 5);
  });

  const STATUS_COLORS: Record<string, string> = {
    Verified: "bg-emerald-50 text-emerald-700 border-emerald-200",
    "Market Rate": "bg-blue-50 text-blue-700 border-blue-200",
    Quoted: "bg-sky-50 text-sky-700 border-sky-200",
    Standard: "bg-neutral-100 text-neutral-600 border-neutral-200",
    Estimated: "bg-amber-50 text-amber-700 border-amber-200",
  };

  function fmt(n: number): string {
    if (displayCurrency === "USD") {
      const usd = fxRate > 0 ? n / fxRate : 0;
      return `$${usd.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
    }
    return `\u20A6${Math.round(n).toLocaleString()}`;
  }
  function fmtM(n: number): string {
    if (displayCurrency === "USD") { const usd = fxRate > 0 ? n / fxRate : 0; return usd >= 1_000_000 ? `$${(usd / 1_000_000).toFixed(1)}M` : `$${Math.round(usd).toLocaleString()}`; }
    return n >= 1_000_000 ? `\u20A6${(n / 1_000_000).toFixed(1)}M` : fmt(n);
  }

  function openScenario(category: string) {
    scenarioCategory = category;
    showScenario = true;
    requestAnimationFrame(() => { scenarioVisible = true; });
  }
  function closeScenario() {
    scenarioVisible = false;
    setTimeout(() => { showScenario = false; }, 300);
  }

  async function loadBoms() {
    loading = true;
    try {
      const res = await api.get<{ results: BomSummary[] }>("/bom/", { page_size: "200" });
      allBoms = res.results;
    } catch { toast.error("Load failed", "Could not load BoQs."); }
    finally { loading = false; }
  }

  async function selectBom(id: number) {
    selectedBomId = id;
    loading = true;
    try {
      activeBom = await api.get<BomDetail>(`/bom/${id}/`);
    } catch { toast.error("Load failed", "Could not load BoQ."); }
    finally { loading = false; }
  }

  onMount(() => { loadBoms(); });
</script>

<svelte:head><title>Cost Estimates | developerOS</title></svelte:head>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-700">Bill of Quantities</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Cost Estimates</h1>
      <p class="mt-1 text-sm text-neutral-500">Strategic projection of total investment. High-level financial planning before the BoQ is finalized.</p>
    </div>
    <div class="flex gap-2">
      <div class="flex rounded-md border border-neutral-200 overflow-hidden">
        <button onclick={() => (displayCurrency = "NGN")} class="px-3 py-2 text-xs font-medium transition-colors {displayCurrency === 'NGN' ? 'bg-neutral-900 text-white' : 'text-neutral-600 hover:bg-neutral-50'}">{String.fromCharCode(8358)} NGN</button>
        <button onclick={() => (displayCurrency = "USD")} class="px-3 py-2 text-xs font-medium transition-colors {displayCurrency === 'USD' ? 'bg-neutral-900 text-white' : 'text-neutral-600 hover:bg-neutral-50'}">$ USD</button>
      </div>
    </div>
  </div>

  <!-- BoQ selector -->
  <div class="flex items-center gap-4">
    <select onchange={(e) => { const id = Number((e.target as HTMLSelectElement).value); if (id) selectBom(id); }} class="rounded-lg border border-neutral-200 bg-white px-3.5 py-2.5 text-sm font-medium min-w-[300px] focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">Select a BoQ for estimation...</option>
      {#each allBoms as bom}
        <option value={bom.id} selected={selectedBomId === bom.id}>{bom.bom_number} — {bom.name}</option>
      {/each}
    </select>
    {#if activeBom}
      {#if activeBom.project_name}
        <span class="rounded-full bg-indigo-50 border border-indigo-200 px-2.5 py-0.5 text-[10px] font-semibold text-indigo-700">{activeBom.project_name}</span>
      {/if}
      <span class="text-xs text-neutral-400">v{activeBom.version} &middot; {activeBom.item_count} items</span>
    {/if}
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-16 text-sm text-neutral-400">Loading...</div>
  {:else if !activeBom}
    <div class="rounded-xl border border-neutral-200 bg-white p-12 text-center text-sm text-neutral-500">Select a BoQ to view the cost estimate.</div>
  {:else}

    <!-- 1. Estimate Summary HUD -->
    <div class="rounded-2xl border border-neutral-200 bg-white/80 overflow-hidden" style="backdrop-filter: blur(12px)">
      <div class="grid grid-cols-2 md:grid-cols-4 divide-x divide-neutral-100">
        <div class="px-6 py-5 text-center">
          <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Total Projected Cost</p>
          <p class="mt-1 text-2xl font-bold text-emerald-700 tabular-nums">{fmtM(grandTotal)}</p>
          <p class="mt-0.5 text-[10px] text-neutral-400">incl. VAT, margin & contingency</p>
        </div>
        <div class="px-6 py-5 text-center">
          <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Cost per Item</p>
          <p class="mt-1 text-2xl font-bold text-blue-700 tabular-nums">{fmt(activeBom.item_count > 0 ? grandTotal / activeBom.item_count : 0)}</p>
          <p class="mt-0.5 text-[10px] text-neutral-400">{activeBom.item_count} line items</p>
        </div>
        <div class="px-6 py-5 text-center">
          <p class="text-[10px] font-semibold text-amber-600 uppercase tracking-wider">Contingency Reserve</p>
          <p class="mt-1 text-2xl font-bold text-amber-700 tabular-nums">{fmtM(contingencyAmount)}</p>
          <div class="flex items-center justify-center gap-2 mt-1">
            <input type="range" min="0" max="20" step="1" bind:value={contingencyPct} class="w-20 accent-amber-500" />
            <span class="text-xs font-bold text-amber-700 tabular-nums">{contingencyPct}%</span>
          </div>
        </div>
        <div class="px-6 py-5 text-center">
          <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Confidence Score</p>
          <p class="mt-1 text-2xl font-bold tabular-nums {confidenceColor}">{activeBom.confidence_pct}%</p>
          <p class="mt-0.5 text-[10px] text-neutral-400">{activeBom.confidence_pct >= 90 ? "Definitive" : activeBom.confidence_pct >= 60 ? "Substantive" : activeBom.confidence_pct >= 30 ? "Budgetary" : "Rough Order"}</p>
        </div>
      </div>
    </div>

    <!-- Scenario controls bar -->
    <div class="flex flex-wrap items-center gap-4 rounded-xl border border-neutral-200 bg-white/80 px-5 py-3" style="backdrop-filter: blur(12px)">
      <div class="flex items-center gap-2">
        <span class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Pricing</span>
        <div class="flex rounded-md border border-neutral-200 overflow-hidden">
          <button onclick={() => (scenarioPricing = "optimistic")} class="px-2.5 py-1 text-[10px] font-medium transition-colors {scenarioPricing === 'optimistic' ? 'bg-emerald-600 text-white' : 'text-neutral-500 hover:bg-neutral-50'}">Optimistic (-10%)</button>
          <button onclick={() => (scenarioPricing = "current")} class="px-2.5 py-1 text-[10px] font-medium transition-colors {scenarioPricing === 'current' ? 'bg-neutral-900 text-white' : 'text-neutral-500 hover:bg-neutral-50'}">Current</button>
          <button onclick={() => (scenarioPricing = "pessimistic")} class="px-2.5 py-1 text-[10px] font-medium transition-colors {scenarioPricing === 'pessimistic' ? 'bg-red-600 text-white' : 'text-neutral-500 hover:bg-neutral-50'}">Pessimistic (+15%)</button>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <span class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Inflation</span>
        <input type="range" min="0" max="10" step="0.5" bind:value={inflationPct} class="w-24 accent-neutral-900" />
        <span class="text-xs font-bold text-neutral-700 tabular-nums w-10">{inflationPct}%</span>
      </div>
      <div class="ml-auto text-right">
        <p class="text-[9px] text-neutral-400 uppercase">Adjusted Subtotal</p>
        <p class="text-sm font-bold text-neutral-900 tabular-nums">{fmt(adjustedSubtotal)}</p>
      </div>
    </div>

    <!-- 2. Work Packages + Donut side by side -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Work Packages Table -->
      <div class="lg:col-span-2 rounded-xl border border-neutral-200 bg-white overflow-hidden">
        <div class="border-b border-neutral-200 bg-neutral-800 px-5 py-3">
          <h3 class="text-[10px] font-semibold text-white uppercase tracking-widest">High-Level Cost Assemblies</h3>
        </div>
        <table class="w-full text-xs">
          <thead>
            <tr class="border-b border-neutral-200 bg-neutral-700">
              <th class="px-4 py-2 text-left font-medium text-neutral-200 w-12">#</th>
              <th class="px-4 py-2 text-left font-medium text-neutral-200">Work Package</th>
              <th class="px-4 py-2 text-left font-medium text-neutral-200">Category</th>
              <th class="px-4 py-2 text-right font-medium text-neutral-200">Estimated</th>
              <th class="px-4 py-2 text-right font-medium text-neutral-200">% of Total</th>
              <th class="px-4 py-2 text-center font-medium text-neutral-200">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-50">
            {#each workPackages as wp (wp.code)}
              <tr class="hover:bg-neutral-50/50 cursor-pointer transition-colors" onclick={() => openScenario(wp.name)}>
                <td class="px-4 py-2.5 text-neutral-400 tabular-nums">{wp.code}</td>
                <td class="px-4 py-2.5 font-semibold text-neutral-900">{wp.name}</td>
                <td class="px-4 py-2.5 text-neutral-500 capitalize">{wp.category}</td>
                <td class="px-4 py-2.5 text-right tabular-nums font-bold text-emerald-700">{fmt(wp.estimated)}</td>
                <td class="px-4 py-2.5 text-right">
                  <div class="flex items-center gap-2 justify-end">
                    <div class="w-16 h-1.5 rounded-full bg-neutral-100 overflow-hidden">
                      <div class="h-full rounded-full bg-neutral-800 transition-all" style="width: {Math.min(wp.pctOfTotal, 100)}%"></div>
                    </div>
                    <span class="tabular-nums text-neutral-600 w-10 text-right">{wp.pctOfTotal.toFixed(0)}%</span>
                  </div>
                </td>
                <td class="px-4 py-2.5 text-center">
                  <span class="rounded-full border px-2 py-0.5 text-[10px] font-semibold {STATUS_COLORS[wp.status] || STATUS_COLORS.Estimated}">{wp.status}</span>
                </td>
              </tr>
            {/each}
          </tbody>
          <tfoot>
            <tr class="border-t-2 border-neutral-200 bg-neutral-50">
              <td colspan="3" class="px-4 py-3 font-bold text-neutral-800">Total ({workPackages.length} packages)</td>
              <td class="px-4 py-3 text-right tabular-nums font-bold text-emerald-700">{fmt(adjustedSubtotal)}</td>
              <td class="px-4 py-3 text-right tabular-nums font-bold text-neutral-800">100%</td>
              <td></td>
            </tr>
          </tfoot>
        </table>
      </div>

      <!-- Donut Chart -->
      <div class="rounded-xl border border-neutral-200 bg-white/80 p-5" style="backdrop-filter: blur(12px)">
        <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-4">Cost Breakdown</h3>
        {#if categoryBreakdown.length > 0}
          {@const donutSize = 180}
          {@const donutStroke = 32}
          {@const donutRadius = (donutSize - donutStroke) / 2}
          {@const donutCircum = 2 * Math.PI * donutRadius}
          <div class="flex flex-col items-center">
            <div class="relative" style="width: {donutSize}px; height: {donutSize}px">
              <svg width={donutSize} height={donutSize} viewBox="0 0 {donutSize} {donutSize}" class="transform -rotate-90">
                <circle cx={donutSize/2} cy={donutSize/2} r={donutRadius} fill="none" stroke="#f5f5f5" stroke-width={donutStroke} />
                {#each categoryBreakdown as cat, i}
                  {@const offset = categoryBreakdown.slice(0, i).reduce((s, c) => s + c.pct, 0)}
                  <circle
                    cx={donutSize/2} cy={donutSize/2} r={donutRadius}
                    fill="none" stroke={CHART_COLORS[i % CHART_COLORS.length]}
                    stroke-width={donutStroke}
                    stroke-dasharray="{cat.pct / 100 * donutCircum} {donutCircum}"
                    stroke-dashoffset="{-offset / 100 * donutCircum}"
                    class="transition-all duration-500"
                  />
                {/each}
              </svg>
              <div class="absolute inset-0 flex flex-col items-center justify-center">
                <p class="text-xl font-bold text-emerald-700 tabular-nums">{fmtM(grandTotal)}</p>
                <p class="text-[8px] text-neutral-400 uppercase tracking-wider">Grand Total</p>
              </div>
            </div>
            <div class="mt-4 w-full space-y-1.5">
              {#each categoryBreakdown as cat, i}
                <div class="flex items-center gap-2">
                  <span class="inline-block w-2.5 h-2.5 rounded-full shrink-0" style="background: {CHART_COLORS[i % CHART_COLORS.length]}"></span>
                  <span class="text-[10px] text-neutral-600 capitalize flex-1 truncate">{cat.category}</span>
                  <span class="text-[10px] font-bold text-neutral-800 tabular-nums">{cat.pct.toFixed(0)}%</span>
                </div>
              {/each}
            </div>
          </div>
        {/if}
      </div>
    </div>

    <!-- Financial Summary Card -->
    <div class="rounded-2xl border border-neutral-200 bg-white/80 p-6" style="backdrop-filter: blur(12px)">
      <h3 class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-4">Financial Summary</h3>
      <div class="grid grid-cols-2 md:grid-cols-6 gap-4">
        <div class="text-center">
          <p class="text-[10px] text-neutral-400">Subtotal</p>
          <p class="text-sm font-bold text-neutral-900 tabular-nums mt-0.5">{fmt(subtotal)}</p>
        </div>
        <div class="text-center">
          <p class="text-[10px] text-neutral-400">Scenario Adj.</p>
          <p class="text-sm font-bold tabular-nums mt-0.5 {scenarioPricing === 'optimistic' ? 'text-emerald-600' : scenarioPricing === 'pessimistic' ? 'text-red-600' : 'text-neutral-900'}">{scenarioPricing === 'current' ? '—' : `${scenarioPricing === 'optimistic' ? '-10' : '+15'}%`}</p>
        </div>
        <div class="text-center">
          <p class="text-[10px] text-amber-600">Contingency ({contingencyPct}%)</p>
          <p class="text-sm font-bold text-amber-700 tabular-nums mt-0.5">{fmt(contingencyAmount)}</p>
        </div>
        <div class="text-center">
          <p class="text-[10px] text-neutral-400">VAT ({vatPct}%)</p>
          <p class="text-sm font-bold text-neutral-900 tabular-nums mt-0.5">{fmt(vatAmount)}</p>
        </div>
        <div class="text-center">
          <p class="text-[10px] text-neutral-400">Margin ({marginPct}%)</p>
          <p class="text-sm font-bold text-neutral-900 tabular-nums mt-0.5">{fmt(marginAmount)}</p>
        </div>
        <div class="text-center rounded-xl bg-emerald-50 border border-emerald-200 py-2">
          <p class="text-[10px] text-emerald-600 font-semibold">Grand Total</p>
          <p class="text-lg font-bold text-emerald-700 tabular-nums">{fmtM(grandTotal)}</p>
        </div>
      </div>
    </div>

    <!-- Cash Flow Projection -->
    <div class="rounded-xl border border-neutral-200 bg-white/80 p-5" style="backdrop-filter: blur(12px)">
      <h3 class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-4">Cash Flow Projection (6-Month Spread)</h3>
      <div class="flex items-end gap-3 h-32">
        {#each cashFlow as cf, i}
          <div class="flex-1 flex flex-col items-center gap-1">
            <div class="w-full rounded-t-md bg-neutral-800 transition-all relative" style="height: {(cf.cumulative / maxCumulative) * 100}%">
              <div class="absolute inset-x-0 bottom-0 rounded-t-md bg-emerald-500 transition-all" style="height: {(cf.spend / maxCumulative) * 100 * (cashFlow.length)}%"></div>
            </div>
            <span class="text-[9px] text-neutral-400 font-semibold">{cf.month}</span>
          </div>
        {/each}
      </div>
      <div class="flex items-center gap-4 mt-3 text-[10px] text-neutral-400">
        <span class="flex items-center gap-1"><span class="inline-block w-3 h-2 rounded bg-emerald-500"></span> Period Spend</span>
        <span class="flex items-center gap-1"><span class="inline-block w-3 h-2 rounded bg-neutral-800"></span> Cumulative</span>
        <span class="ml-auto tabular-nums">Total: {fmt(grandTotal)}</span>
      </div>
    </div>

    <!-- Benchmark Tracker -->
    {#if benchmarks.length > 0}
      <div class="rounded-xl border border-neutral-200 bg-white/80 overflow-hidden" style="backdrop-filter: blur(12px)">
        <div class="border-b border-neutral-100 bg-neutral-50 px-5 py-3">
          <h3 class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest">Benchmark Tracker — vs. Other Estimates</h3>
        </div>
        <div class="divide-y divide-neutral-50">
          {#each benchmarks as bm}
            <div class="flex items-center gap-4 px-5 py-3 hover:bg-neutral-50/50 transition-colors">
              <div class="flex-1 min-w-0">
                <p class="text-xs font-medium text-neutral-900 truncate">{bm.name}</p>
                <p class="text-[10px] text-neutral-400">{bm.bom_number}{bm.project_name ? ` \u00B7 ${bm.project_name}` : ""} \u00B7 {bm.itemCount} items</p>
              </div>
              <div class="text-right shrink-0">
                <p class="text-xs tabular-nums text-neutral-600">{fmt(bm.total)}</p>
              </div>
              <div class="w-28 shrink-0">
                <div class="flex items-center gap-1.5">
                  <div class="flex-1 h-2 rounded-full bg-neutral-100 overflow-hidden">
                    <div
                      class="h-full rounded-full transition-all {bm.isHigher ? 'bg-amber-400' : 'bg-emerald-400'}"
                      style="width: {Math.min(Math.abs(bm.diffPct), 100)}%"
                    ></div>
                  </div>
                  <span class="text-[10px] font-bold tabular-nums w-14 text-right {bm.isHigher ? 'text-amber-700' : 'text-emerald-700'}">
                    {bm.isHigher ? "+" : ""}{bm.diffPct.toFixed(0)}%
                  </span>
                </div>
                <p class="text-[9px] text-neutral-400 text-right mt-0.5">{bm.isHigher ? "higher" : "lower"} than this</p>
              </div>
            </div>
          {/each}
        </div>
      </div>
    {/if}

  {/if}
</div>

<!-- Scenario Modeler Drawer -->
{#if showScenario}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="fixed inset-0 z-40 bg-black/20 transition-opacity duration-300" style="opacity: {scenarioVisible ? 1 : 0}; backdrop-filter: blur(25px)" onclick={closeScenario}></div>
  <aside class="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col bg-white/90 shadow-2xl border-l border-neutral-200/60 transition-transform duration-300" style="transform: translateX({scenarioVisible ? '0%' : '100%'}); backdrop-filter: blur(25px)">
    <div class="bg-linear-to-br from-neutral-900 to-neutral-800 px-6 py-5">
      <div class="flex items-start justify-between">
        <div>
          <h2 class="text-base font-semibold text-white">Scenario Modeler</h2>
          <p class="mt-0.5 text-sm text-neutral-400">{scenarioCategory}</p>
        </div>
        <button onclick={closeScenario} class="rounded-md p-1.5 text-neutral-400 hover:text-white" aria-label="Close">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
        </button>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto px-6 py-5 space-y-5">
      <!-- Pricing toggle -->
      <section>
        <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3">Pricing Scenario</h3>
        <div class="space-y-2">
          {#each [{ key: "optimistic", label: "Optimistic (Best Case)", desc: "-10% on all rates. Bulk discounts, local sourcing.", color: "border-emerald-200 bg-emerald-50/50" }, { key: "current", label: "Current Market", desc: "Current supplier quotes and warehouse prices.", color: "border-neutral-200 bg-white" }, { key: "pessimistic", label: "Pessimistic (Worst Case)", desc: "+15% buffer for FX movement, shipping delays.", color: "border-red-200 bg-red-50/50" }] as opt}
            <button
              onclick={() => { scenarioPricing = opt.key as any; }}
              class="w-full text-left rounded-xl border p-4 transition-all {scenarioPricing === opt.key ? opt.color + ' ring-2 ring-neutral-900' : 'border-neutral-100 bg-white hover:border-neutral-300'}"
            >
              <p class="text-sm font-semibold text-neutral-900">{opt.label}</p>
              <p class="text-[10px] text-neutral-500 mt-0.5">{opt.desc}</p>
            </button>
          {/each}
        </div>
      </section>

      <!-- Inflation buffer -->
      <section>
        <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3">Inflation Buffer</h3>
        <div class="flex items-center gap-3">
          <input type="range" min="0" max="10" step="0.5" bind:value={inflationPct} class="flex-1 accent-neutral-900" />
          <span class="text-sm font-bold text-neutral-900 tabular-nums w-12 text-right">{inflationPct}%</span>
        </div>
        <p class="mt-1 text-[10px] text-neutral-400">For projects spanning 6+ months. Accounts for material price increases.</p>
      </section>

      <!-- Contingency -->
      <section>
        <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3">Contingency Reserve</h3>
        <div class="flex items-center gap-3">
          <input type="range" min="0" max="20" step="1" bind:value={contingencyPct} class="flex-1 accent-amber-500" />
          <span class="text-sm font-bold text-amber-700 tabular-nums w-12 text-right">{contingencyPct}%</span>
        </div>
        <p class="mt-1 text-[10px] text-neutral-400">Buffer for unforeseen site conditions, scope changes, and rework.</p>
      </section>

      <!-- Impact summary -->
      <section class="rounded-xl bg-neutral-50 border border-neutral-200 p-4">
        <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3">Impact Summary</h3>
        <div class="space-y-2 text-xs">
          <div class="flex justify-between"><span class="text-neutral-500">Base Subtotal</span><span class="tabular-nums font-medium">{fmt(subtotal)}</span></div>
          <div class="flex justify-between"><span class="text-neutral-500">Scenario Adjustment</span><span class="tabular-nums font-medium {scenarioPricing === 'optimistic' ? 'text-emerald-600' : scenarioPricing === 'pessimistic' ? 'text-red-600' : ''}">{fmt(adjustedSubtotal - subtotal)}</span></div>
          <div class="flex justify-between"><span class="text-amber-600">Contingency</span><span class="tabular-nums font-medium text-amber-700">{fmt(contingencyAmount)}</span></div>
          <div class="flex justify-between"><span class="text-neutral-500">VAT</span><span class="tabular-nums font-medium">{fmt(vatAmount)}</span></div>
          <div class="flex justify-between"><span class="text-neutral-500">Margin</span><span class="tabular-nums font-medium">{fmt(marginAmount)}</span></div>
          <div class="flex justify-between pt-2 border-t border-neutral-200"><span class="font-bold text-neutral-900">Grand Total</span><span class="tabular-nums font-bold text-emerald-700">{fmt(grandTotal)}</span></div>
        </div>
      </section>
    </div>
  </aside>
{/if}

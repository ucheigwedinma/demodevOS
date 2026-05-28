<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DrawerShell from "$lib/components/DrawerShell.svelte";
  import type {
    SalesRevenueForecastListItem,
    SalesRevenueForecastDetail,
    PaginatedResponse,
    ProjectListItem,
  } from "$lib/types";

  let forecasts = $state<SalesRevenueForecastListItem[]>([]);
  let loading = $state(true);
  let projects = $state<ProjectListItem[]>([]);
  let projectFilter = $state("");

  let detailOpen = $state(false);
  let detail = $state<SalesRevenueForecastDetail | null>(null);
  let detailLoading = $state(false);
  let detailTab = $state<"overview" | "units" | "phases" | "strategy">("overview");
  let unitStatusFilter = $state("");

  let createOpen = $state(false);
  let saving = $state(false);
  let form = $state(defaultForm());

  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  function defaultForm() {
    return {
      project: "", gross_development_value: "",
      marketing_budget: "", marketing_budget_pct: "2",
      sales_launch_date: "", target_sellout_date: "", notes: "",
    };
  }

  function devFill() {
    form = {
      project: form.project || (projects.length > 0 ? String(projects[0].id) : ""),
      gross_development_value: "3500000000",
      marketing_budget: "70000000",
      marketing_budget_pct: "2",
      sales_launch_date: "2026-06-01",
      target_sellout_date: "2028-12-31",
      notes: "Phase 1 off-plan sales targeting 40% pre-construction. Showroom launch planned for Q2 2026. Primary agent: Knight Frank Nigeria.",
    };
  }

  async function fetchData() {
    loading = true;
    try {
      const params: Record<string, string> = { page_size: "100" };
      if (projectFilter) params.project = projectFilter;
      const [res, projRes] = await Promise.all([
        api.get<PaginatedResponse<SalesRevenueForecastListItem>>("/projects/sales-forecasts/", params),
        projects.length === 0 ? api.get<PaginatedResponse<ProjectListItem>>("/projects/", { page_size: "200", ordering: "name" }) : Promise.resolve(null),
      ]);
      forecasts = res.results;
      if (projRes) projects = projRes.results;
    } catch { forecasts = []; }
    loading = false;
  }

  $effect(() => { void projectFilter; fetchData(); });

  async function openDetail(id: number) {
    detailOpen = true;
    detailLoading = true;
    detailTab = "overview";
    unitStatusFilter = "";
    try { detail = await api.get<SalesRevenueForecastDetail>(`/projects/sales-forecasts/${id}/`); } catch { detail = null; }
    detailLoading = false;
  }

  async function saveForecast(e: Event) {
    e.preventDefault();
    if (!form.project) { toast.error("Required", "Select a project."); return; }
    saving = true;
    try {
      await api.post("/projects/sales-forecasts/", {
        ...form,
        project: Number(form.project),
        gross_development_value: form.gross_development_value || "0",
        marketing_budget: form.marketing_budget || "0",
        sales_launch_date: form.sales_launch_date || null,
        target_sellout_date: form.target_sellout_date || null,
        payment_structure: [{ stage: "Deposit", pct: 30 }, { stage: "Construction", pct: 40 }, { stage: "Handover", pct: 30 }],
        agents: [],
      });
      toast.success("Forecast created", "Sales & Revenue forecast registered.");
      createOpen = false;
      form = defaultForm();
      await fetchData();
    } catch (error) {
      const msg = error instanceof ApiError ? (Object.values(error.fieldErrors)[0]?.[0] ?? "Save failed.") : "Save failed.";
      toast.error("Save failed", msg);
    } finally { saving = false; }
  }

  function fmtC(v: string | number | null | undefined): string { if (!v || v === "0.00" || v === "0") return "--"; return currency.formatCompact(v); }
  function fmtCFull(v: string | number | null | undefined): string { if (!v || v === "0.00" || v === "0") return "--"; return currency.format(v); }
  function fmtDate(v: string | null | undefined): string { if (!v) return "--"; const d = new Date(v); return Number.isNaN(d.getTime()) ? "--" : d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }); }

  function unitStatusColor(s: string): string {
    if (s === "sold") return "bg-emerald-100 text-emerald-800";
    if (s === "under_contract") return "bg-blue-100 text-blue-800";
    if (s === "reserved") return "bg-amber-100 text-amber-800";
    if (s === "held") return "bg-neutral-200 text-neutral-500";
    return "bg-neutral-100 text-neutral-600";
  }

  const filteredUnits = $derived(
    detail ? (unitStatusFilter ? detail.units.filter(u => u.status === unitStatusFilter) : detail.units) : []
  );

  const unitStats = $derived(() => {
    if (!detail) return { available: 0, reserved: 0, underContract: 0, sold: 0, total: 0, soldPct: 0 };
    const units = detail.units;
    const available = units.filter(u => u.status === "available").length;
    const reserved = units.filter(u => u.status === "reserved").length;
    const underContract = units.filter(u => u.status === "under_contract").length;
    const sold = units.filter(u => u.status === "sold").length;
    const total = units.length;
    const soldPct = total > 0 ? Math.round((sold + underContract) / total * 100) : 0;
    return { available, reserved, underContract, sold, total, soldPct };
  });
</script>

<div class="space-y-6">
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">Projects</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-900">Sales & Revenue Forecast</h1>
      <p class="mt-1 text-sm text-neutral-500">Revenue targets, unit inventory, pricing matrix, and sales velocity tracking.</p>
    </div>
    <div class="flex items-center gap-2">
      <select bind:value={projectFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
        <option value="">All Projects</option>
        {#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}
      </select>
      <button onclick={() => { form = defaultForm(); createOpen = true; }} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800">+ New Forecast</button>
    </div>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if forecasts.length === 0}
    <div class="rounded-2xl border border-neutral-200 bg-white px-6 py-14 text-center"><p class="text-sm text-neutral-500">No sales forecasts found.</p></div>
  {:else}
    <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
      {#each forecasts as f}
        {@const soldPct = f.total_units > 0 ? Math.round((f.sold_units) / f.total_units * 100) : 0}
        <button class="w-full text-left rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow cursor-pointer" onclick={() => openDetail(f.id)}>
          <div class="flex items-start justify-between mb-3">
            <div>
              <p class="text-sm font-semibold text-neutral-900">{f.project_name}</p>
              <p class="text-xs text-neutral-500 mt-0.5">Launch: {fmtDate(f.sales_launch_date)}</p>
            </div>
            <div class="text-right">
              <p class="text-[9px] text-neutral-400">GDV</p>
              <p class="text-sm font-bold text-neutral-900 tabular-nums">{fmtC(f.gross_development_value)}</p>
            </div>
          </div>
          <div class="grid grid-cols-4 gap-3 mb-3">
            <div><p class="text-[9px] text-neutral-400">Units</p><p class="text-sm font-semibold text-neutral-900">{f.total_units}</p></div>
            <div><p class="text-[9px] text-neutral-400">Sold</p><p class="text-sm font-semibold text-emerald-600">{f.sold_units}</p></div>
            <div><p class="text-[9px] text-neutral-400">Reserved</p><p class="text-sm font-semibold text-amber-600">{f.reserved_units}</p></div>
            <div><p class="text-[9px] text-neutral-400">Revenue</p><p class="text-sm font-semibold text-neutral-900 tabular-nums">{fmtC(f.actual_revenue)}</p></div>
          </div>
          <div class="h-1.5 w-full rounded-full bg-neutral-100 overflow-hidden">
            <div class="h-full rounded-full bg-emerald-500 transition-all" style="width: {soldPct}%"></div>
          </div>
          <p class="text-[10px] text-neutral-400 mt-1">{soldPct}% sold</p>
        </button>
      {/each}
    </div>
  {/if}
</div>

<!-- ═══════════ DETAIL DRAWER ═══════════ -->
<DrawerShell open={detailOpen} title="Sales Forecast" subtitle={detail ? detail.project_name : ""} width="max-w-3xl" onclose={() => (detailOpen = false)}>
  {#if detailLoading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if detail}
    {@const stats = unitStats()}
    <div class="border-b border-neutral-200">
      <div class="flex gap-1 px-6 pt-4">
        {#each [["overview", "Overview"], ["units", "Unit Inventory"], ["phases", "Sales Phases"], ["strategy", "Strategy"]] as [key, label]}
          <button onclick={() => (detailTab = key as typeof detailTab)} class="rounded-t-lg px-4 py-2 text-xs font-semibold transition-colors {detailTab === key ? 'bg-white text-neutral-900 border border-b-white border-neutral-200 -mb-px' : 'text-neutral-500 hover:text-neutral-700'}">{label}</button>
        {/each}
      </div>
    </div>

    <div class="p-6 space-y-5">
      {#if detailTab === "overview"}
        <!-- KPI Cards -->
        <div class="grid grid-cols-2 gap-3 md:grid-cols-4">
          <div class="rounded-lg border border-neutral-200 p-3 text-center">
            <p class="text-[9px] font-semibold uppercase text-neutral-400">GDV</p>
            <p class="mt-1 text-lg font-bold text-neutral-900 tabular-nums">{fmtC(detail.gross_development_value)}</p>
          </div>
          <div class="rounded-lg border border-emerald-100 bg-emerald-50 p-3 text-center">
            <p class="text-[9px] font-semibold uppercase text-emerald-700">Actual Revenue</p>
            <p class="mt-1 text-lg font-bold text-emerald-900 tabular-nums">{fmtC(detail.units.filter(u => u.sold_price).reduce((s, u) => s + Number(u.sold_price || 0), 0))}</p>
          </div>
          <div class="rounded-lg border border-neutral-200 p-3 text-center">
            <p class="text-[9px] font-semibold uppercase text-neutral-400">Total Units</p>
            <p class="mt-1 text-lg font-bold text-neutral-900 tabular-nums">{stats.total}</p>
          </div>
          <div class="rounded-lg border border-neutral-200 p-3 text-center">
            <p class="text-[9px] font-semibold uppercase text-neutral-400">Sold %</p>
            <p class="mt-1 text-lg font-bold text-neutral-900 tabular-nums">{stats.soldPct}%</p>
          </div>
        </div>

        <!-- Unit Status Breakdown -->
        <div class="grid grid-cols-4 gap-3">
          <div class="rounded-lg bg-neutral-50 p-3 text-center"><p class="text-[9px] font-semibold uppercase text-neutral-500">Available</p><p class="mt-1 text-xl font-bold text-neutral-700">{stats.available}</p></div>
          <div class="rounded-lg bg-amber-50 p-3 text-center"><p class="text-[9px] font-semibold uppercase text-amber-700">Reserved</p><p class="mt-1 text-xl font-bold text-amber-900">{stats.reserved}</p></div>
          <div class="rounded-lg bg-blue-50 p-3 text-center"><p class="text-[9px] font-semibold uppercase text-blue-700">Under Contract</p><p class="mt-1 text-xl font-bold text-blue-900">{stats.underContract}</p></div>
          <div class="rounded-lg bg-emerald-50 p-3 text-center"><p class="text-[9px] font-semibold uppercase text-emerald-700">Sold</p><p class="mt-1 text-xl font-bold text-emerald-900">{stats.sold}</p></div>
        </div>

        <div class="grid grid-cols-2 gap-3 text-sm">
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Sales Launch</p><p class="text-neutral-900">{fmtDate(detail.sales_launch_date)}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Target Sellout</p><p class="text-neutral-900">{fmtDate(detail.target_sellout_date)}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Marketing Budget</p><p class="text-neutral-900">{fmtC(detail.marketing_budget)} ({detail.marketing_budget_pct}% of GDV)</p></div>
        </div>

      {:else if detailTab === "units"}
        <!-- Unit Inventory -->
        <div class="flex items-center gap-2 mb-3">
          {#each [["", "All"], ["available", "Available"], ["reserved", "Reserved"], ["under_contract", "Under Contract"], ["sold", "Sold"]] as [key, label]}
            <button onclick={() => (unitStatusFilter = key)} class="rounded-lg px-3 py-1.5 text-xs font-medium transition-colors {unitStatusFilter === key ? 'bg-neutral-900 text-white' : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200'}">{label}</button>
          {/each}
        </div>
        {#if filteredUnits.length === 0}
          <p class="text-sm text-neutral-400 text-center py-6">No units match filter.</p>
        {:else}
          <div class="overflow-x-auto">
            <table class="w-full">
              <thead class="bg-neutral-50"><tr>
                <th class="px-3 py-2 text-left text-[10px] font-semibold uppercase text-neutral-500">Unit</th>
                <th class="px-3 py-2 text-left text-[10px] font-semibold uppercase text-neutral-500">Type</th>
                <th class="px-3 py-2 text-left text-[10px] font-semibold uppercase text-neutral-500">Floor</th>
                <th class="px-3 py-2 text-right text-[10px] font-semibold uppercase text-neutral-500">Size</th>
                <th class="px-3 py-2 text-right text-[10px] font-semibold uppercase text-neutral-500">Asking</th>
                <th class="px-3 py-2 text-center text-[10px] font-semibold uppercase text-neutral-500">Status</th>
                <th class="px-3 py-2 text-left text-[10px] font-semibold uppercase text-neutral-500">Buyer</th>
              </tr></thead>
              <tbody class="divide-y divide-neutral-100">
                {#each filteredUnits as u}
                  <tr>
                    <td class="px-3 py-2 text-sm font-semibold text-neutral-900">{u.unit_id}</td>
                    <td class="px-3 py-2 text-xs text-neutral-600">{u.unit_type_display}</td>
                    <td class="px-3 py-2 text-xs text-neutral-600">{u.floor_location || "--"}</td>
                    <td class="px-3 py-2 text-right text-sm tabular-nums text-neutral-700">{u.size_sqm ? `${u.size_sqm} sqm` : "--"}</td>
                    <td class="px-3 py-2 text-right text-sm font-semibold tabular-nums text-neutral-900">{fmtCFull(u.asking_price)}</td>
                    <td class="px-3 py-2 text-center"><span class="inline-block rounded-full px-2 py-0.5 text-[9px] font-semibold {unitStatusColor(u.status)}">{u.status_display}</span></td>
                    <td class="px-3 py-2 text-sm text-neutral-600 max-w-[120px] truncate">{u.buyer_name || "--"}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}

      {:else if detailTab === "phases"}
        <!-- Sales Phases -->
        {#if detail.phase_targets.length === 0}
          <p class="text-sm text-neutral-400 text-center py-6">No sales phases defined.</p>
        {:else}
          <div class="space-y-3">
            {#each detail.phase_targets as pt}
              <div class="rounded-lg border border-neutral-200 p-4">
                <div class="flex items-center justify-between mb-2">
                  <div>
                    <p class="text-sm font-semibold text-neutral-900">{pt.phase_name}</p>
                    <p class="text-xs text-neutral-500">{fmtDate(pt.start_date)} — {fmtDate(pt.end_date)}</p>
                  </div>
                  {#if pt.milestone_trigger}<span class="text-[9px] font-semibold text-indigo-600 bg-indigo-50 rounded-full px-2 py-0.5">{pt.milestone_trigger}</span>{/if}
                </div>
                <div class="grid grid-cols-4 gap-3">
                  <div><p class="text-[9px] text-neutral-400">Target Units</p><p class="text-sm font-bold text-neutral-900">{pt.target_units}</p></div>
                  <div><p class="text-[9px] text-neutral-400">Actual Units</p><p class="text-sm font-bold {pt.unit_variance >= 0 ? 'text-emerald-600' : 'text-red-600'}">{pt.actual_units}</p></div>
                  <div><p class="text-[9px] text-neutral-400">Target Revenue</p><p class="text-sm font-bold text-neutral-900 tabular-nums">{fmtC(pt.target_revenue)}</p></div>
                  <div><p class="text-[9px] text-neutral-400">Actual Revenue</p><p class="text-sm font-bold tabular-nums {Number(pt.variance) >= 0 ? 'text-emerald-600' : 'text-red-600'}">{fmtC(pt.actual_revenue)}</p></div>
                </div>
              </div>
            {/each}
          </div>
        {/if}

      {:else if detailTab === "strategy"}
        <!-- Payment Structure & Agents -->
        {#if detail.payment_structure && detail.payment_structure.length > 0}
          <div>
            <p class="text-[10px] font-semibold uppercase text-neutral-400 mb-2">Payment Structure</p>
            <div class="flex gap-2">
              {#each detail.payment_structure as ps}
                <div class="flex-1 rounded-lg border border-neutral-200 p-3 text-center">
                  <p class="text-xs font-medium text-neutral-600">{ps.stage}</p>
                  <p class="text-lg font-bold text-neutral-900">{ps.pct}%</p>
                </div>
              {/each}
            </div>
          </div>
        {/if}

        {#if detail.agents && detail.agents.length > 0}
          <div>
            <p class="text-[10px] font-semibold uppercase text-neutral-400 mb-2">Agents & Brokers</p>
            <div class="space-y-2">
              {#each detail.agents as agent}
                <div class="rounded-lg border border-neutral-200 p-3 flex items-center justify-between">
                  <p class="text-sm font-medium text-neutral-900">{agent.firm}</p>
                  <p class="text-sm font-bold text-neutral-700">{agent.commission_pct}% commission</p>
                </div>
              {/each}
            </div>
          </div>
        {/if}

        {#if detail.notes}<div><p class="text-[10px] font-semibold uppercase text-neutral-400 mb-1">Notes</p><p class="text-sm text-neutral-700 whitespace-pre-line">{detail.notes}</p></div>{/if}
      {/if}
    </div>
  {/if}
</DrawerShell>

<!-- ═══════════ CREATE DRAWER ═══════════ -->
<DrawerShell open={createOpen} title="New Sales Forecast" subtitle="Revenue targets and unit pricing strategy" width="max-w-md" onclose={() => (createOpen = false)}>
  <form onsubmit={saveForecast} class="p-6 space-y-4">
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Project *</span><select bind:value={form.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"><option value="">Select</option>{#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}</select></label>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Gross Development Value (GDV)</span><input type="number" step="0.01" bind:value={form.gross_development_value} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Marketing Budget</span><input type="number" step="0.01" bind:value={form.marketing_budget} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Marketing % of GDV</span><input type="number" step="0.1" bind:value={form.marketing_budget_pct} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Sales Launch</span><input type="date" bind:value={form.sales_launch_date} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Target Sellout</span><input type="date" bind:value={form.target_sellout_date} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Notes</span><textarea bind:value={form.notes} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <div class="flex justify-end gap-2 pt-2">
      <button type="button" onclick={() => (createOpen = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      {#if isDev}<button type="button" onclick={devFill} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
      <button type="submit" disabled={saving} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{saving ? "Saving..." : "Create Forecast"}</button>
    </div>
  </form>
</DrawerShell>

<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { onMount } from "svelte";

  // --- Types ---
  interface TaskSummary {
    id: number; name: string; assigned_role: string; estimated_effort_hours: number | null;
    standard_duration_hours: number | null; crew_size: number | null; equipment_type: string;
    estimated_labor_cost: number | null; category: string;
    required_materials: { item: string; quantity: string; unit: string; essential: boolean }[];
  }
  interface Activity { id: number; name: string; wbs_code: string; estimated_duration_days: number | null; sort_order: number; task_templates: TaskSummary[]; }
  interface Phase { id: number; name: string; sort_order: number; duration_days: number | null; activities: Activity[]; }
  interface Template { id: number; name: string; phases: Phase[]; }
  interface TemplateListItem { id: number; name: string; template_type_display: string; }
  interface ScheduleSettings { hours_per_day: number; resource_roles: { role: string; capacity: number; daily_rate: number }[]; duration_scalar_pct: number; }

  interface MaterialCostLine { item: string; unit: string; quantity: number; unitPrice: number; lineTotal: number; essential: boolean; }
  interface LaborCostLine { role: string; hours: number; rate: number; lineTotal: number; }
  interface PhaseCostBreakdown { phase: string; materialCost: number; laborCost: number; equipmentCost: number; total: number; dayStart: number; dayEnd: number; }

  const LOCATION_FACTORS: Record<string, number> = {
    lagos: 1.0,
    abuja: 1.15,
    port_harcourt: 1.1,
    kano: 1.2,
    remote_site: 1.35,
  };

  // --- State ---
  let loading = $state(true);
  let templates = $state<TemplateListItem[]>([]);
  let selectedTemplateId = $state<number | null>(null);
  let activeTemplate = $state<Template | null>(null);
  let schedSettings = $state<ScheduleSettings | null>(null);

  // Cost controls
  let materialMarkupPct = $state(10);
  let locationFactor = $state("lagos");
  let contingencyPct = $state(10);
  let equipmentDailyRate = $state(50000);

  // Computed cost data
  let materialLines = $state<MaterialCostLine[]>([]);
  let laborLines = $state<LaborCostLine[]>([]);
  let phaseCosts = $state<PhaseCostBreakdown[]>([]);

  // --- Derived totals ---
  const rawMaterialCost = $derived(materialLines.reduce((s, m) => s + m.lineTotal, 0));
  const markedUpMaterialCost = $derived(rawMaterialCost * (1 + materialMarkupPct / 100));
  const totalLaborCost = $derived(laborLines.reduce((s, l) => s + l.lineTotal, 0));
  const totalEquipmentCost = $derived.by(() => {
    if (!activeTemplate) return 0;
    let eqDays = 0;
    for (const phase of activeTemplate.phases) {
      for (const act of phase.activities) {
        if (act.task_templates.some(t => t.equipment_type)) eqDays += act.estimated_duration_days || 1;
      }
    }
    return eqDays * equipmentDailyRate;
  });

  const locMultiplier = $derived(LOCATION_FACTORS[locationFactor] || 1);
  const subtotalBeforeLocation = $derived(markedUpMaterialCost + totalLaborCost + totalEquipmentCost);
  const subtotalAfterLocation = $derived(subtotalBeforeLocation * locMultiplier);
  const contingencyAmount = $derived(subtotalAfterLocation * contingencyPct / 100);
  const grandTotal = $derived(subtotalAfterLocation + contingencyAmount);

  // Cash flow (cumulative per phase)
  const cashFlowData = $derived.by(() => {
    let cumulative = 0;
    return phaseCosts.map(p => {
      cumulative += p.total * locMultiplier * (1 + contingencyPct / 100);
      return { phase: p.phase, periodCost: p.total * locMultiplier * (1 + contingencyPct / 100), cumulative, dayStart: p.dayStart, dayEnd: p.dayEnd };
    });
  });

  const maxCumulative = $derived(cashFlowData.length > 0 ? cashFlowData[cashFlowData.length - 1].cumulative : 1);

  // --- Load ---
  async function loadTemplates() {
    try {
      const res = await api.get<{ results: TemplateListItem[] }>("/settings/project-templates/", { page_size: "100", is_active: "true" });
      templates = res.results;
      if (templates.length > 0 && !selectedTemplateId) await selectTemplate(templates[0].id);
    } catch { toast.error("Load failed", "Could not load templates."); }
    finally { loading = false; }
  }

  async function selectTemplate(id: number) {
    selectedTemplateId = id;
    loading = true;
    try {
      const [tmpl, sched] = await Promise.all([
        api.get<Template>(`/settings/project-templates/${id}/`),
        api.get<ScheduleSettings>(`/settings/project-templates/${id}/schedule-settings/`),
      ]);
      activeTemplate = tmpl;
      schedSettings = sched;
      computeCosts();
    } catch { toast.error("Load failed", "Could not load template."); }
    finally { loading = false; }
  }

  // Recompute when controls change
  $effect(() => {
    if (activeTemplate && schedSettings) {
      void materialMarkupPct;
      void locationFactor;
      void contingencyPct;
      void equipmentDailyRate;
      computeCosts();
    }
  });

  // --- Cost Computation ---
  function computeCosts() {
    if (!activeTemplate || !schedSettings) return;

    const roleRates = new Map((schedSettings.resource_roles || []).map(r => [r.role.toLowerCase(), r.daily_rate * (schedSettings!.hours_per_day || 9)]));
    const hoursPerDay = schedSettings.hours_per_day || 9;

    // Material aggregation with unit prices (placeholder — in production, pull from inventory)
    const matMap = new Map<string, { qty: number; unit: string; essential: boolean }>();
    for (const phase of activeTemplate.phases) {
      for (const act of phase.activities) {
        for (const task of act.task_templates) {
          for (const mat of (task.required_materials || [])) {
            const key = `${mat.item}||${mat.unit}`;
            const entry = matMap.get(key) || { qty: 0, unit: mat.unit, essential: false };
            entry.qty += Number(mat.quantity) || 0;
            if (mat.essential) entry.essential = true;
            matMap.set(key, entry);
          }
        }
      }
    }

    // Estimate unit prices (in production these come from procurement/inventory)
    const priceGuess = (item: string): number => {
      const lower = item.toLowerCase();
      if (lower.includes("cable")) return 2500;
      if (lower.includes("panel")) return 180000;
      if (lower.includes("inverter")) return 450000;
      if (lower.includes("cement") || lower.includes("concrete")) return 7500;
      if (lower.includes("rebar") || lower.includes("steel")) return 3500;
      if (lower.includes("sand")) return 800;
      if (lower.includes("gravel")) return 1200;
      if (lower.includes("block")) return 450;
      if (lower.includes("pipe")) return 1800;
      if (lower.includes("paint")) return 12000;
      return 5000;
    };

    materialLines = Array.from(matMap.entries()).map(([key, data]) => {
      const item = key.split("||")[0];
      const unitPrice = priceGuess(item);
      return { item, unit: data.unit, quantity: data.qty, unitPrice, lineTotal: data.qty * unitPrice, essential: data.essential };
    }).sort((a, b) => b.lineTotal - a.lineTotal);

    // Labor aggregation
    const labMap = new Map<string, { hours: number; rate: number }>();
    for (const phase of activeTemplate.phases) {
      for (const act of phase.activities) {
        for (const task of act.task_templates) {
          const role = task.assigned_role || "Unassigned";
          const entry = labMap.get(role) || { hours: 0, rate: 0 };
          entry.hours += task.estimated_effort_hours || 0;
          const hourlyRate = (roleRates.get(role.toLowerCase()) || 0) / hoursPerDay;
          if (hourlyRate > entry.rate) entry.rate = hourlyRate;
          if (entry.rate === 0 && task.estimated_labor_cost) {
            entry.rate = task.estimated_labor_cost / Math.max(task.estimated_effort_hours || 1, 1);
          }
          labMap.set(role, entry);
        }
      }
    }
    laborLines = Array.from(labMap.entries()).map(([role, data]) => ({
      role, hours: data.hours, rate: data.rate, lineTotal: data.hours * data.rate,
    })).sort((a, b) => b.lineTotal - a.lineTotal);

    // Phase cost breakdown
    let dayAccum = 0;
    phaseCosts = activeTemplate.phases.map(phase => {
      let matCost = 0;
      let labCost = 0;
      let eqCost = 0;
      for (const act of phase.activities) {
        const actDays = act.estimated_duration_days || 1;
        for (const task of act.task_templates) {
          // Materials
          for (const mat of (task.required_materials || [])) {
            matCost += (Number(mat.quantity) || 0) * priceGuess(mat.item);
          }
          // Labor
          const role = task.assigned_role || "Unassigned";
          const hourlyRate = (roleRates.get(role.toLowerCase()) || 0) / hoursPerDay;
          labCost += (task.estimated_effort_hours || 0) * (hourlyRate || (task.estimated_labor_cost ? task.estimated_labor_cost / Math.max(task.estimated_effort_hours || 1, 1) : 0));
          // Equipment
          if (task.equipment_type) eqCost += actDays * equipmentDailyRate / Math.max(act.task_templates.length, 1);
        }
      }
      matCost *= (1 + materialMarkupPct / 100);
      const dayStart = dayAccum;
      dayAccum += phase.duration_days || phase.activities.reduce((s, a) => s + (a.estimated_duration_days || 1), 0);
      return { phase: phase.name, materialCost: matCost, laborCost: labCost, equipmentCost: eqCost, total: matCost + labCost + eqCost, dayStart, dayEnd: dayAccum };
    });
  }

  function fmt(n: number): string { return `₦${Math.round(n).toLocaleString()}`; }
  function fmtM(n: number): string { return n >= 1_000_000 ? `₦${(n / 1_000_000).toFixed(1)}M` : fmt(n); }

  onMount(() => { loadTemplates(); });
</script>

<svelte:head><title>Cost Projection — Project Planner | developerOS</title></svelte:head>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-700">Project Planning</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Cost Projection Layer</h1>
      <p class="mt-1 text-sm text-neutral-500">Derived from BoQ and resource assumptions. Produces cost curves and cash flow forecasts.</p>
    </div>
  </div>

  <!-- Template selector -->
  <div class="flex flex-col gap-4 sm:flex-row sm:items-center">
    <div class="w-64">
      <select onchange={(e) => { const id = Number((e.target as HTMLSelectElement).value); if (id) selectTemplate(id); }} class="w-full rounded-lg border border-neutral-200 bg-white px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
        {#each templates as tmpl}
          <option value={tmpl.id} selected={tmpl.id === selectedTemplateId}>{tmpl.name}</option>
        {/each}
      </select>
    </div>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-16 text-sm text-neutral-400">Loading...</div>
  {:else if !activeTemplate}
    <div class="rounded-xl border border-neutral-200 bg-white p-12 text-center text-sm text-neutral-500">No template selected.</div>
  {:else}

    <!-- Cost Controls -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="rounded-xl border border-neutral-200 bg-white p-4">
        <label for="materialMarkup" class="block text-xs font-medium text-neutral-600 mb-2">Material Markup</label>
        <div class="flex items-center gap-3">
          <input id="materialMarkup" type="range" min="0" max="50" step="1" bind:value={materialMarkupPct} class="flex-1 accent-neutral-900" />
          <span class="text-sm font-bold text-neutral-900 tabular-nums w-10 text-right">{materialMarkupPct}%</span>
        </div>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white p-4">
        <label for="locationFactor" class="block text-xs font-medium text-neutral-600 mb-2">Location Factor</label>
        <select id="locationFactor" bind:value={locationFactor} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
          <option value="lagos">Lagos (1.0x)</option>
          <option value="abuja">Abuja (1.15x)</option>
          <option value="port_harcourt">Port Harcourt (1.1x)</option>
          <option value="kano">Kano (1.2x)</option>
          <option value="remote_site">Remote Site (1.35x)</option>
        </select>
      </div>
      <div class="rounded-xl border border-white/60 bg-white/70 p-4 shadow-sm" style="backdrop-filter: blur(10px)">
        <label for="contingencyBuffer" class="block text-xs font-medium text-neutral-600 mb-2">Contingency Buffer</label>
        <div class="flex items-center gap-3">
          <input id="contingencyBuffer" type="range" min="0" max="25" step="1" bind:value={contingencyPct} class="flex-1 accent-neutral-900" />
          <span class="text-sm font-bold text-neutral-900 tabular-nums w-10 text-right">{contingencyPct}%</span>
        </div>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white p-4">
        <label for="equipmentDailyRate" class="block text-xs font-medium text-neutral-600 mb-2">Equipment Daily Rate (₦)</label>
        <input id="equipmentDailyRate" type="number" bind:value={equipmentDailyRate} step="5000" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" />
      </div>
    </div>

    <!-- Cost Summary Cards -->
    <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
      <div class="rounded-xl border border-neutral-200 bg-white p-4 text-center">
        <p class="text-lg font-bold text-neutral-900 tabular-nums">{fmtM(rawMaterialCost)}</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider mt-1">Materials (Raw)</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white p-4 text-center">
        <p class="text-lg font-bold text-neutral-900 tabular-nums">{fmtM(markedUpMaterialCost)}</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider mt-1">Materials (+{materialMarkupPct}%)</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white p-4 text-center">
        <p class="text-lg font-bold text-neutral-900 tabular-nums">{fmtM(totalLaborCost)}</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider mt-1">Labor</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white p-4 text-center">
        <p class="text-lg font-bold text-neutral-900 tabular-nums">{fmtM(totalEquipmentCost)}</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider mt-1">Equipment</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white p-4 text-center">
        <p class="text-lg font-bold text-amber-600 tabular-nums">{fmtM(contingencyAmount)}</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider mt-1">Contingency</p>
      </div>
      <div class="rounded-xl border-2 border-emerald-300 bg-emerald-50 p-4 text-center">
        <p class="text-xl font-black text-emerald-700 tabular-nums">{fmtM(grandTotal)}</p>
        <p class="text-[9px] font-bold text-emerald-600 uppercase tracking-wider mt-1">Total Estimate</p>
      </div>
    </div>

    <!-- Phase Cost Breakdown -->
    <section class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
      <div class="border-b border-neutral-100 bg-neutral-50 px-5 py-3">
        <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest">Phase Cost Breakdown</h3>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-xs">
          <thead>
            <tr class="border-b border-neutral-100">
              <th class="px-5 py-2.5 text-left font-medium text-neutral-500">Phase</th>
              <th class="px-4 py-2.5 text-right font-medium text-neutral-500">Material</th>
              <th class="px-4 py-2.5 text-right font-medium text-neutral-500">Labor</th>
              <th class="px-4 py-2.5 text-right font-medium text-neutral-500">Equipment</th>
              <th class="px-4 py-2.5 text-right font-medium text-neutral-500">Phase Total</th>
              <th class="px-4 py-2.5 text-left font-medium text-neutral-500 w-40">Distribution</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-50">
            {#each phaseCosts as pc}
              {@const pct = subtotalBeforeLocation > 0 ? (pc.total / subtotalBeforeLocation * 100) : 0}
              <tr class="hover:bg-neutral-50/50">
                <td class="px-5 py-2.5 font-semibold text-neutral-900">{pc.phase}</td>
                <td class="px-4 py-2.5 text-right tabular-nums text-neutral-600">{fmt(pc.materialCost)}</td>
                <td class="px-4 py-2.5 text-right tabular-nums text-neutral-600">{fmt(pc.laborCost)}</td>
                <td class="px-4 py-2.5 text-right tabular-nums text-neutral-600">{fmt(pc.equipmentCost)}</td>
                <td class="px-4 py-2.5 text-right tabular-nums font-bold text-neutral-900">{fmt(pc.total)}</td>
                <td class="px-4 py-2.5">
                  <div class="flex items-center gap-2">
                    <div class="flex-1 h-4 rounded-full bg-neutral-100 overflow-hidden">
                      <div class="h-full rounded-full bg-neutral-800" style="width: {pct}%"></div>
                    </div>
                    <span class="text-[10px] text-neutral-400 tabular-nums w-8 text-right">{pct.toFixed(0)}%</span>
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
          <tfoot>
            <tr class="border-t-2 border-neutral-200 bg-neutral-50">
              <td class="px-5 py-2.5 font-bold text-neutral-900">Total</td>
              <td class="px-4 py-2.5 text-right tabular-nums font-bold">{fmt(markedUpMaterialCost)}</td>
              <td class="px-4 py-2.5 text-right tabular-nums font-bold">{fmt(totalLaborCost)}</td>
              <td class="px-4 py-2.5 text-right tabular-nums font-bold">{fmt(totalEquipmentCost)}</td>
              <td class="px-4 py-2.5 text-right tabular-nums font-bold text-emerald-700">{fmt(subtotalBeforeLocation)}</td>
              <td></td>
            </tr>
          </tfoot>
        </table>
      </div>
    </section>

    <!-- Material Cost Detail + Labor Cost Detail -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Material Cost -->
      <section class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
        <div class="border-b border-neutral-100 bg-neutral-50 px-5 py-3 flex items-center justify-between">
          <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest">Material Cost Summary</h3>
          <span class="text-[10px] text-neutral-400">{materialLines.length} line(s)</span>
        </div>
        {#if materialLines.length > 0}
          <div class="overflow-x-auto">
            <table class="w-full text-xs">
              <thead><tr class="border-b border-neutral-100"><th class="px-4 py-2 text-left font-medium text-neutral-500">Item</th><th class="px-3 py-2 text-right font-medium text-neutral-500">Qty</th><th class="px-3 py-2 text-left font-medium text-neutral-500">Unit</th><th class="px-3 py-2 text-right font-medium text-neutral-500">Unit Price</th><th class="px-4 py-2 text-right font-medium text-neutral-500">Line Total</th></tr></thead>
              <tbody class="divide-y divide-neutral-50">
                {#each materialLines as mat}
                  <tr class="hover:bg-neutral-50/50">
                    <td class="px-4 py-2 font-medium text-neutral-800">
                      {mat.item}
                      {#if mat.essential}<span class="ml-1 rounded-full bg-emerald-50 text-emerald-700 px-1.5 py-0.5 text-[8px] font-bold">REQ</span>{/if}
                    </td>
                    <td class="px-3 py-2 text-right tabular-nums text-neutral-600">{mat.quantity.toLocaleString()}</td>
                    <td class="px-3 py-2 text-neutral-500">{mat.unit}</td>
                    <td class="px-3 py-2 text-right tabular-nums text-neutral-500">{fmt(mat.unitPrice)}</td>
                    <td class="px-4 py-2 text-right tabular-nums font-semibold text-neutral-900">{fmt(mat.lineTotal)}</td>
                  </tr>
                {/each}
              </tbody>
              <tfoot><tr class="border-t border-neutral-200 bg-neutral-50"><td colspan="4" class="px-4 py-2 font-bold text-neutral-900">Raw Total</td><td class="px-4 py-2 text-right tabular-nums font-bold text-neutral-900">{fmt(rawMaterialCost)}</td></tr></tfoot>
            </table>
          </div>
          <div class="px-5 py-2 bg-neutral-50 border-t border-neutral-100 text-xs text-neutral-500">
            Unit prices are estimates. Link to procurement module for live pricing.
          </div>
        {:else}
          <div class="p-8 text-center text-xs text-neutral-400">No materials in task templates.</div>
        {/if}
      </section>

      <!-- Labor Cost -->
      <section class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
        <div class="border-b border-neutral-100 bg-neutral-50 px-5 py-3">
          <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest">Labor Cost Projection</h3>
        </div>
        {#if laborLines.length > 0}
          <div class="overflow-x-auto">
            <table class="w-full text-xs">
              <thead><tr class="border-b border-neutral-100"><th class="px-4 py-2 text-left font-medium text-neutral-500">Role</th><th class="px-3 py-2 text-right font-medium text-neutral-500">Man-Hours</th><th class="px-3 py-2 text-right font-medium text-neutral-500">Hourly Rate</th><th class="px-4 py-2 text-right font-medium text-neutral-500">Line Total</th></tr></thead>
              <tbody class="divide-y divide-neutral-50">
                {#each laborLines as lab}
                  <tr class="hover:bg-neutral-50/50">
                    <td class="px-4 py-2 font-medium text-neutral-800">{lab.role}</td>
                    <td class="px-3 py-2 text-right tabular-nums text-neutral-600">{lab.hours}h</td>
                    <td class="px-3 py-2 text-right tabular-nums text-neutral-500">{lab.rate > 0 ? fmt(Math.round(lab.rate)) + "/h" : "—"}</td>
                    <td class="px-4 py-2 text-right tabular-nums font-semibold text-neutral-900">{fmt(lab.lineTotal)}</td>
                  </tr>
                {/each}
              </tbody>
              <tfoot><tr class="border-t border-neutral-200 bg-neutral-50"><td colspan="3" class="px-4 py-2 font-bold text-neutral-900">Total Labor</td><td class="px-4 py-2 text-right tabular-nums font-bold text-neutral-900">{fmt(totalLaborCost)}</td></tr></tfoot>
            </table>
          </div>
        {:else}
          <div class="p-8 text-center text-xs text-neutral-400">No roles with effort estimates.</div>
        {/if}
      </section>
    </div>

    <!-- Cash Flow Forecast (S-Curve) -->
    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-4">Cash Flow Forecast — Cumulative S-Curve</h3>
      {#if cashFlowData.length > 0}
        <div class="relative h-56 flex items-end gap-1" style="padding-left: 60px">
          <!-- Y-axis -->
          <div class="absolute left-0 top-0 bottom-0 w-14 flex flex-col justify-between text-right pr-2">
            <span class="text-[9px] text-neutral-400 tabular-nums">{fmtM(maxCumulative)}</span>
            <span class="text-[9px] text-neutral-400 tabular-nums">{fmtM(maxCumulative / 2)}</span>
            <span class="text-[9px] text-neutral-400 tabular-nums">₦0</span>
          </div>
          <!-- Grid lines -->
          <div class="absolute inset-0" style="left: 60px">
            <div class="absolute top-0 left-0 right-0 border-t border-dashed border-neutral-100"></div>
            <div class="absolute top-1/2 left-0 right-0 border-t border-dashed border-neutral-100"></div>
            <div class="absolute bottom-0 left-0 right-0 border-t border-neutral-200"></div>
          </div>

          {#each cashFlowData as cf, i}
            {@const barHeight = maxCumulative > 0 ? (cf.cumulative / maxCumulative) * 100 : 0}
            {@const periodHeight = maxCumulative > 0 ? (cf.periodCost / maxCumulative) * 100 : 0}
            <div class="flex-1 flex flex-col items-center justify-end relative z-10" style="height: 100%">
              <!-- Cumulative bar -->
              <div
                class="w-full rounded-t-md bg-emerald-500/80 transition-all relative"
                style="height: {barHeight}%"
                title="{cf.phase}: Period {fmtM(cf.periodCost)}, Cumulative {fmtM(cf.cumulative)}"
              >
                <!-- Period overlay -->
                <div class="absolute bottom-0 left-0 right-0 rounded-t-md bg-emerald-700/60" style="height: {barHeight > 0 ? (periodHeight / barHeight) * 100 : 0}%"></div>
              </div>
              <div class="mt-1.5 text-center">
                <p class="text-[8px] text-neutral-500 leading-tight truncate w-full max-w-[80px]" title={cf.phase}>{cf.phase}</p>
                <p class="text-[9px] text-emerald-700 font-bold tabular-nums mt-0.5">{fmtM(cf.cumulative)}</p>
              </div>
            </div>
          {/each}
        </div>
        <div class="flex items-center gap-4 mt-4 pt-3 border-t border-neutral-100 justify-center">
          <span class="flex items-center gap-1.5 text-[10px] text-neutral-500"><span class="inline-block w-3 h-3 rounded bg-emerald-500/80"></span> Cumulative</span>
          <span class="flex items-center gap-1.5 text-[10px] text-neutral-500"><span class="inline-block w-3 h-3 rounded bg-emerald-700/60"></span> Period Cost</span>
        </div>
      {:else}
        <div class="text-center text-xs text-neutral-400 py-8">No cost data to chart.</div>
      {/if}
    </section>

    <!-- Grand Total -->
    <div class="rounded-2xl border-2 border-emerald-300 bg-linear-to-r from-emerald-50 via-white to-emerald-50 p-8 text-center">
      <p class="text-[10px] font-bold text-emerald-600 uppercase tracking-widest mb-2">Total Project Estimate</p>
      <p class="text-4xl font-black text-emerald-700 tabular-nums">{fmt(grandTotal)}</p>
      <p class="text-xs text-emerald-600 mt-2">
        Materials {fmtM(markedUpMaterialCost)} + Labor {fmtM(totalLaborCost)} + Equipment {fmtM(totalEquipmentCost)}
        × {locMultiplier}x location + {contingencyPct}% contingency
      </p>
    </div>

  {/if}
</div>

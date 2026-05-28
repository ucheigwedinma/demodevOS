<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { onMount } from "svelte";

  interface TemplateListItem { id: number; name: string; template_type_display: string; }
  interface Scenario {
    id: number; template: number; name: string; description: string; is_baseline: boolean;
    duration_scalar_pct: number; material_markup_pct: number; location_factor: string;
    contingency_pct: number; equipment_daily_rate: number; fx_rate_usd_ngn: number;
    risk_level: string; risk_level_display: string;
    projected_duration_days: number; projected_material_cost: number; projected_labor_cost: number;
    projected_equipment_cost: number; projected_contingency: number; projected_total_cost: number;
    sensitivity_fx_10pct_impact: number; sensitivity_material_10pct_impact: number;
    notes: string; created_by_name: string; created_at: string; updated_at: string;
  }

  const LOCATION_LABELS: Record<string, string> = {
    lagos: "Lagos", abuja: "Abuja", port_harcourt: "Port Harcourt", kano: "Kano", remote_site: "Remote Site",
  };
  const LOCATION_FACTORS: Record<string, number> = { lagos: 1.0, abuja: 1.15, port_harcourt: 1.1, kano: 1.2, remote_site: 1.35 };
  const RISK_COLORS: Record<string, string> = {
    low: "bg-emerald-50 text-emerald-700 border-emerald-200",
    medium: "bg-amber-50 text-amber-700 border-amber-200",
    high: "bg-red-50 text-red-700 border-red-200",
  };

  let loading = $state(true);
  let templates = $state<TemplateListItem[]>([]);
  let selectedTemplateId = $state<number | null>(null);
  let scenarios = $state<Scenario[]>([]);

  // Create/Edit
  let showModal = $state(false);
  let editingId = $state<number | null>(null);
  let saving = $state(false);
  let form = $state(emptyForm());

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");
  const baseline = $derived(scenarios.find(s => s.is_baseline) || null);
  const nonBaseline = $derived(scenarios.filter(s => !s.is_baseline));

  function emptyForm() {
    return {
      name: "", description: "", risk_level: "medium",
      duration_scalar_pct: "100", material_markup_pct: "10", location_factor: "lagos",
      contingency_pct: "10", equipment_daily_rate: "50000", fx_rate_usd_ngn: "1550",
      projected_duration_days: "0", projected_material_cost: "0", projected_labor_cost: "0",
      projected_equipment_cost: "0", projected_contingency: "0", projected_total_cost: "0",
      sensitivity_fx_10pct_impact: "0", sensitivity_material_10pct_impact: "0",
      notes: "",
    };
  }

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
      const res = await api.get<{ results: Scenario[] }>(`/settings/project-templates/${id}/scenarios/`, { page_size: "50" });
      scenarios = res.results;
    } catch { toast.error("Load failed", "Could not load scenarios."); }
    finally { loading = false; }
  }

  function openCreate() {
    editingId = null;
    form = emptyForm();
    showModal = true;
  }

  function openEdit(s: Scenario) {
    editingId = s.id;
    form = {
      name: s.name, description: s.description, risk_level: s.risk_level,
      duration_scalar_pct: String(s.duration_scalar_pct), material_markup_pct: String(s.material_markup_pct),
      location_factor: s.location_factor, contingency_pct: String(s.contingency_pct),
      equipment_daily_rate: String(s.equipment_daily_rate), fx_rate_usd_ngn: String(s.fx_rate_usd_ngn),
      projected_duration_days: String(s.projected_duration_days), projected_material_cost: String(s.projected_material_cost),
      projected_labor_cost: String(s.projected_labor_cost), projected_equipment_cost: String(s.projected_equipment_cost),
      projected_contingency: String(s.projected_contingency), projected_total_cost: String(s.projected_total_cost),
      sensitivity_fx_10pct_impact: String(s.sensitivity_fx_10pct_impact),
      sensitivity_material_10pct_impact: String(s.sensitivity_material_10pct_impact),
      notes: s.notes,
    };
    showModal = true;
  }

  // Auto-compute projections from assumptions
  const computedTotal = $derived.by(() => {
    const mat = Number(form.projected_material_cost) || 0;
    const lab = Number(form.projected_labor_cost) || 0;
    const eq = Number(form.projected_equipment_cost) || 0;
    const loc = LOCATION_FACTORS[form.location_factor] || 1;
    const sub = (mat * (1 + (Number(form.material_markup_pct) || 0) / 100) + lab + eq) * loc;
    const cont = sub * (Number(form.contingency_pct) || 0) / 100;
    return { subtotal: sub, contingency: cont, total: sub + cont };
  });

  async function saveScenario() {
    if (!form.name.trim() || !selectedTemplateId) { toast.error("Missing data", "Scenario name is required."); return; }
    saving = true;
    try {
      const payload = {
        ...form,
        template: selectedTemplateId,
        duration_scalar_pct: Number(form.duration_scalar_pct) || 100,
        material_markup_pct: Number(form.material_markup_pct) || 0,
        contingency_pct: Number(form.contingency_pct) || 0,
        equipment_daily_rate: Number(form.equipment_daily_rate) || 0,
        fx_rate_usd_ngn: Number(form.fx_rate_usd_ngn) || 1550,
        projected_duration_days: Number(form.projected_duration_days) || 0,
        projected_material_cost: Number(form.projected_material_cost) || 0,
        projected_labor_cost: Number(form.projected_labor_cost) || 0,
        projected_equipment_cost: Number(form.projected_equipment_cost) || 0,
        projected_contingency: computedTotal.contingency,
        projected_total_cost: computedTotal.total,
        sensitivity_fx_10pct_impact: Number(form.projected_material_cost) * 0.1 * (LOCATION_FACTORS[form.location_factor] || 1),
        sensitivity_material_10pct_impact: Number(form.projected_material_cost) * 0.1,
      };
      if (editingId) {
        await api.patch(`/settings/project-templates/${selectedTemplateId}/scenarios/${editingId}/`, payload);
        toast.success("Scenario updated", `"${form.name}" has been saved.`);
      } else {
        await api.post(`/settings/project-templates/${selectedTemplateId}/scenarios/`, payload);
        toast.success("Scenario created", `"${form.name}" has been added.`);
      }
      showModal = false;
      await selectTemplate(selectedTemplateId);
    } catch (err) {
      if (err instanceof ApiError) toast.error("Save failed", Object.values(err.fieldErrors).flat().join(" ") || "Check the form.");
      else toast.error("Save failed", "Could not save scenario.");
    } finally { saving = false; }
  }

  async function commitBaseline(scenarioId: number) {
    if (!selectedTemplateId) return;
    try {
      await api.post(`/settings/project-templates/${selectedTemplateId}/scenarios/${scenarioId}/commit-baseline/`, {});
      toast.success("Baseline committed", "This scenario is now the official project baseline.");
      await selectTemplate(selectedTemplateId);
    } catch { toast.error("Failed", "Could not commit baseline."); }
  }

  async function deleteScenario(id: number) {
    if (!selectedTemplateId) return;
    try {
      await api.delete(`/settings/project-templates/${selectedTemplateId}/scenarios/${id}/`);
      toast.success("Deleted", "Scenario has been removed.");
      await selectTemplate(selectedTemplateId);
    } catch { toast.error("Failed", "Could not delete scenario."); }
  }

  function devFill(preset: "standard" | "fast_track" | "economy") {
    const presets: Record<string, Partial<typeof form>> = {
      standard: { name: "Standard Execution", description: "Balanced cost, timeline, and risk profile.", risk_level: "low", duration_scalar_pct: "100", material_markup_pct: "10", contingency_pct: "10", projected_duration_days: "120", projected_material_cost: "8500000", projected_labor_cost: "3200000", projected_equipment_cost: "1800000" },
      fast_track: { name: "Fast-Track Delivery", description: "Compressed timeline with overtime and parallel execution. Higher cost, higher risk.", risk_level: "high", duration_scalar_pct: "75", material_markup_pct: "15", contingency_pct: "15", projected_duration_days: "90", projected_material_cost: "9200000", projected_labor_cost: "4800000", projected_equipment_cost: "2400000" },
      economy: { name: "Economy Build", description: "Minimised spend with longer timeline. Phased procurement, smaller crew sizes.", risk_level: "medium", duration_scalar_pct: "130", material_markup_pct: "5", contingency_pct: "8", projected_duration_days: "156", projected_material_cost: "7200000", projected_labor_cost: "2600000", projected_equipment_cost: "1200000" },
    };
    const p = presets[preset];
    if (p) Object.assign(form, p);
  }

  function fmt(n: number | string): string { const v = Number(n); return `₦${Math.round(v).toLocaleString()}`; }
  function fmtM(n: number | string): string { const v = Number(n); return v >= 1_000_000 ? `₦${(v / 1_000_000).toFixed(1)}M` : fmt(v); }

  onMount(() => { loadTemplates(); });
</script>

<svelte:head><title>Scenario Analysis — Project Planner | developerOS</title></svelte:head>

<div class="space-y-6">
  <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-amber-600">Project Planning</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Scenario Analysis</h1>
      <p class="mt-1 text-sm text-neutral-500">Compare execution strategies before committing to a baseline plan.</p>
    </div>
    <button onclick={openCreate} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800">+ New Scenario</button>
  </div>

  <!-- Template selector -->
  <div class="w-64">
    <select onchange={(e) => { const id = Number((e.target as HTMLSelectElement).value); if (id) selectTemplate(id); }} class="w-full rounded-lg border border-neutral-200 bg-white px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
      {#each templates as tmpl}
        <option value={tmpl.id} selected={tmpl.id === selectedTemplateId}>{tmpl.name}</option>
      {/each}
    </select>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-16 text-sm text-neutral-400">Loading...</div>
  {:else if scenarios.length === 0}
    <div class="rounded-xl border border-neutral-200 bg-white p-12 text-center">
      <p class="text-sm text-neutral-500">No scenarios yet. Create your first scenario to begin what-if analysis.</p>
      <div class="flex justify-center gap-2 mt-4">
        {#if isDev}
          <button onclick={() => { openCreate(); devFill("standard"); }} class="rounded-lg border border-neutral-200 px-3 py-2 text-xs font-medium text-neutral-700 hover:bg-neutral-50">Quick: Standard</button>
          <button onclick={() => { openCreate(); devFill("fast_track"); }} class="rounded-lg border border-neutral-200 px-3 py-2 text-xs font-medium text-neutral-700 hover:bg-neutral-50">Quick: Fast-Track</button>
          <button onclick={() => { openCreate(); devFill("economy"); }} class="rounded-lg border border-neutral-200 px-3 py-2 text-xs font-medium text-neutral-700 hover:bg-neutral-50">Quick: Economy</button>
        {/if}
      </div>
    </div>
  {:else}

    <!-- Scenario Comparison Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
      {#each scenarios as sc (sc.id)}
        {@const isBase = sc.is_baseline}
        <div class="rounded-2xl border-2 p-5 transition-all {isBase ? 'border-emerald-300 bg-emerald-50/30 shadow-[0_0_20px_-4px_rgba(16,185,129,0.2)]' : 'border-neutral-200 bg-white hover:border-neutral-300 hover:shadow-md'}">
          <!-- Header -->
          <div class="flex items-start justify-between gap-2 mb-3">
            <div>
              <div class="flex items-center gap-2">
                <h3 class="text-sm font-bold text-neutral-900">{sc.name}</h3>
                {#if isBase}
                  <span class="rounded-full bg-emerald-100 px-2 py-0.5 text-[9px] font-bold text-emerald-700 uppercase tracking-wider">Baseline</span>
                {/if}
              </div>
              {#if sc.description}
                <p class="text-xs text-neutral-500 mt-1 line-clamp-2">{sc.description}</p>
              {/if}
            </div>
            <span class="shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold {RISK_COLORS[sc.risk_level] || RISK_COLORS.medium}">
              {sc.risk_level_display} Risk
            </span>
          </div>

          <!-- Impact Cards -->
          <div class="grid grid-cols-3 gap-2 mb-4">
            <div class="rounded-lg bg-neutral-100/80 p-2.5 text-center">
              <p class="text-lg font-black text-neutral-900 tabular-nums">{sc.projected_duration_days}<span class="text-[10px] font-normal text-neutral-400">d</span></p>
              <p class="text-[9px] font-semibold text-neutral-400 uppercase">Duration</p>
            </div>
            <div class="rounded-lg bg-neutral-100/80 p-2.5 text-center">
              <p class="text-lg font-black text-neutral-900 tabular-nums">{fmtM(sc.projected_total_cost)}</p>
              <p class="text-[9px] font-semibold text-neutral-400 uppercase">Total Cost</p>
            </div>
            <div class="rounded-lg p-2.5 text-center {sc.risk_level === 'high' ? 'bg-red-50' : sc.risk_level === 'low' ? 'bg-emerald-50' : 'bg-amber-50'}">
              <p class="text-lg font-black tabular-nums {sc.risk_level === 'high' ? 'text-red-700' : sc.risk_level === 'low' ? 'text-emerald-700' : 'text-amber-700'}">{sc.risk_level_display}</p>
              <p class="text-[9px] font-semibold text-neutral-400 uppercase">Risk</p>
            </div>
          </div>

          <!-- Assumptions -->
          <div class="space-y-1 mb-4">
            <div class="flex justify-between text-[10px]"><span class="text-neutral-400">Speed</span><span class="font-semibold text-neutral-700 tabular-nums">{sc.duration_scalar_pct}%</span></div>
            <div class="flex justify-between text-[10px]"><span class="text-neutral-400">Material Markup</span><span class="font-semibold text-neutral-700 tabular-nums">{sc.material_markup_pct}%</span></div>
            <div class="flex justify-between text-[10px]"><span class="text-neutral-400">Location</span><span class="font-semibold text-neutral-700">{LOCATION_LABELS[sc.location_factor] || sc.location_factor} ({LOCATION_FACTORS[sc.location_factor] || 1}x)</span></div>
            <div class="flex justify-between text-[10px]"><span class="text-neutral-400">Contingency</span><span class="font-semibold text-neutral-700 tabular-nums">{sc.contingency_pct}%</span></div>
            <div class="flex justify-between text-[10px]"><span class="text-neutral-400">FX Rate</span><span class="font-semibold text-neutral-700 tabular-nums">₦{Number(sc.fx_rate_usd_ngn).toLocaleString()}/USD</span></div>
          </div>

          <!-- Sensitivity -->
          {#if sc.sensitivity_fx_10pct_impact > 0 || sc.sensitivity_material_10pct_impact > 0}
            <div class="rounded-lg border border-neutral-200/60 bg-white/70 p-3 mb-4" style="backdrop-filter: blur(8px)">
              <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider mb-1.5">Sensitivity (10% increase)</p>
              <div class="space-y-1">
                {#if sc.sensitivity_fx_10pct_impact > 0}
                  <div class="flex justify-between text-[10px]">
                    <span class="text-neutral-500">FX rate impact</span>
                    <span class="font-semibold text-red-600 tabular-nums">+{fmtM(sc.sensitivity_fx_10pct_impact)}</span>
                  </div>
                {/if}
                {#if sc.sensitivity_material_10pct_impact > 0}
                  <div class="flex justify-between text-[10px]">
                    <span class="text-neutral-500">Material price impact</span>
                    <span class="font-semibold text-red-600 tabular-nums">+{fmtM(sc.sensitivity_material_10pct_impact)}</span>
                  </div>
                {/if}
              </div>
            </div>
          {/if}

          <!-- Actions -->
          <div class="flex items-center gap-2 pt-3 border-t border-neutral-100">
            {#if !isBase}
              <button onclick={() => commitBaseline(sc.id)} class="flex-1 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-700 transition-colors">Commit as Baseline</button>
            {:else}
              <span class="flex-1 rounded-lg bg-emerald-100 px-3 py-2 text-xs font-semibold text-emerald-700 text-center">Official Baseline</span>
            {/if}
            <button onclick={() => openEdit(sc)} class="rounded-lg border border-neutral-200 px-3 py-2 text-xs font-medium text-neutral-700 hover:bg-neutral-50">Edit</button>
            {#if !isBase}
              <button onclick={() => deleteScenario(sc.id)} class="rounded-lg border border-neutral-200 px-2 py-2 text-neutral-400 hover:text-red-500 hover:border-red-200 transition-colors" title="Delete">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" /></svg>
              </button>
            {/if}
          </div>

          <p class="text-[9px] text-neutral-300 mt-2">{sc.created_by_name ? `By ${sc.created_by_name} · ` : ""}{new Date(sc.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}</p>
        </div>
      {/each}
    </div>

    <!-- Comparison Table -->
    {#if scenarios.length >= 2}
      <section class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
        <div class="border-b border-neutral-100 bg-neutral-50 px-5 py-3">
          <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest">Side-by-Side Comparison</h3>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-xs">
            <thead>
              <tr class="border-b border-neutral-100">
                <th class="px-5 py-2.5 text-left font-medium text-neutral-500 sticky left-0 bg-white z-10">Metric</th>
                {#each scenarios as sc}
                  <th class="px-4 py-2.5 text-right font-semibold text-neutral-700 min-w-[140px] {sc.is_baseline ? 'bg-emerald-50/50' : ''}">{sc.name}</th>
                {/each}
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-50">
              {#each [
                { label: "Duration", key: "projected_duration_days", suffix: " days" },
                { label: "Material Cost", key: "projected_material_cost", isCurrency: true },
                { label: "Labor Cost", key: "projected_labor_cost", isCurrency: true },
                { label: "Equipment Cost", key: "projected_equipment_cost", isCurrency: true },
                { label: "Contingency", key: "projected_contingency", isCurrency: true },
                { label: "Total Cost", key: "projected_total_cost", isCurrency: true, bold: true },
                { label: "Speed Scalar", key: "duration_scalar_pct", suffix: "%" },
                { label: "Risk Level", key: "risk_level_display" },
              ] as row}
                <tr>
                  <td class="px-5 py-2 font-medium text-neutral-700 sticky left-0 bg-white z-10 {row.bold ? 'font-bold' : ''}">{row.label}</td>
                  {#each scenarios as sc}
                    {@const val = (sc as unknown as Record<string, unknown>)[row.key ?? ""]}
                    <td class="px-4 py-2 text-right tabular-nums {sc.is_baseline ? 'bg-emerald-50/50 font-semibold' : ''} {row.bold ? 'font-bold text-neutral-900' : 'text-neutral-600'}">
                      {row.isCurrency ? fmtM(Number(val) || 0) : `${val}${row.suffix || ""}`}
                    </td>
                  {/each}
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </section>
    {/if}

  {/if}
</div>

<!-- Scenario Modal -->
{#if showModal}
  <div class="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 backdrop-blur-sm p-4 pt-12 pb-12">
    <div class="relative w-full max-w-2xl rounded-xl bg-white shadow-2xl p-6">
      <button onclick={() => (showModal = false)} class="absolute top-4 right-4 rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-900" aria-label="Close">
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
      </button>

      <h3 class="text-base font-semibold text-neutral-900 mb-5">{editingId ? "Edit Scenario" : "New Scenario"}</h3>

      <div class="space-y-5">
        <!-- Identity -->
        <div class="grid grid-cols-2 gap-3">
          <label class="col-span-2 text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Scenario Name</span><input bind:value={form.name} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="e.g. Fast-Track Delivery" /></label>
          <label class="col-span-2 text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Description</span><textarea bind:value={form.description} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none" placeholder="Strategy and rationale"></textarea></label>
          <label class="text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Risk Level</span>
            <select bind:value={form.risk_level} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
              <option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option>
            </select>
          </label>
          <label class="text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">FX Rate (₦/USD)</span><input type="number" bind:value={form.fx_rate_usd_ngn} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" /></label>
        </div>

        <!-- Assumptions -->
        <section>
          <h4 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3">Assumptions</h4>
          <div class="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <label class="text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Speed (%)</span><input type="number" bind:value={form.duration_scalar_pct} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" /></label>
            <label class="text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Material Markup (%)</span><input type="number" bind:value={form.material_markup_pct} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" /></label>
            <label class="text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Contingency (%)</span><input type="number" bind:value={form.contingency_pct} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" /></label>
            <label class="text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Location</span>
              <select bind:value={form.location_factor} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
                {#each Object.entries(LOCATION_LABELS) as [val, label]}<option value={val}>{label} ({LOCATION_FACTORS[val]}x)</option>{/each}
              </select>
            </label>
            <label class="text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Equipment Rate (₦/day)</span><input type="number" bind:value={form.equipment_daily_rate} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" /></label>
            <label class="text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Duration (days)</span><input type="number" bind:value={form.projected_duration_days} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" /></label>
          </div>
        </section>

        <!-- Projected Costs -->
        <section>
          <h4 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3">Projected Costs</h4>
          <div class="grid grid-cols-3 gap-3">
            <label class="text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Material (₦)</span><input type="number" bind:value={form.projected_material_cost} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" /></label>
            <label class="text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Labor (₦)</span><input type="number" bind:value={form.projected_labor_cost} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" /></label>
            <label class="text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Equipment (₦)</span><input type="number" bind:value={form.projected_equipment_cost} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" /></label>
          </div>
          <!-- Live computed total -->
          <div class="mt-3 rounded-lg border-2 border-emerald-200 bg-emerald-50 p-3 text-center">
            <p class="text-[9px] font-bold text-emerald-600 uppercase tracking-wider">Computed Total</p>
            <p class="text-xl font-black text-emerald-700 tabular-nums mt-1">{fmt(computedTotal.total)}</p>
            <p class="text-[10px] text-emerald-600 mt-0.5">Subtotal {fmt(computedTotal.subtotal)} + Contingency {fmt(computedTotal.contingency)}</p>
          </div>
        </section>

        <!-- Notes -->
        <label class="block text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Notes</span><textarea bind:value={form.notes} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none" placeholder="Risks, trade-offs, or management notes"></textarea></label>
      </div>

      <div class="flex items-center justify-end gap-3 mt-5 pt-4 border-t border-neutral-100">
        {#if isDev && !editingId}
          <div class="mr-auto flex gap-1">
            <button onclick={() => devFill("standard")} class="rounded-lg bg-amber-500 px-2.5 py-1.5 text-[10px] font-medium text-white hover:bg-amber-600">Standard</button>
            <button onclick={() => devFill("fast_track")} class="rounded-lg bg-amber-500 px-2.5 py-1.5 text-[10px] font-medium text-white hover:bg-amber-600">Fast-Track</button>
            <button onclick={() => devFill("economy")} class="rounded-lg bg-amber-500 px-2.5 py-1.5 text-[10px] font-medium text-white hover:bg-amber-600">Economy</button>
          </div>
        {/if}
        <button onclick={() => (showModal = false)} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
        <button onclick={saveScenario} disabled={saving} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50">{saving ? "Saving..." : editingId ? "Save Changes" : "Create Scenario"}</button>
      </div>
    </div>
  </div>
{/if}

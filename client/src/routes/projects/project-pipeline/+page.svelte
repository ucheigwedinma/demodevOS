<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DrawerShell from "$lib/components/DrawerShell.svelte";
  import DateInput from "$lib/components/DateInput.svelte";
  import type {
    PipelineOpportunityListItem,
    PipelineOpportunityDetail,
    PipelineSummary,
    DevPipelineStage,
    DevPipelineDevType,
    PaginatedResponse,
  } from "$lib/types";

  // ── State ─────────────────────────────────────────────────────────────
  let rows = $state<PipelineOpportunityListItem[]>([]);
  let loading = $state(true);
  let summary = $state<PipelineSummary | null>(null);

  let detailOpen = $state(false);
  let detail = $state<PipelineOpportunityDetail | null>(null);
  let detailLoading = $state(false);

  let createOpen = $state(false);
  let saving = $state(false);
  let form = $state(defaultForm());

  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  const STAGES: { key: DevPipelineStage; label: string; color: string }[] = [
    { key: "opportunity", label: "Opportunity", color: "border-blue-200 bg-blue-50/60" },
    { key: "feasibility", label: "Feasibility", color: "border-indigo-200 bg-indigo-50/60" },
    { key: "financial_model", label: "Financial Modeling", color: "border-amber-200 bg-amber-50/60" },
    { key: "due_diligence", label: "Due Diligence", color: "border-orange-200 bg-orange-50/60" },
    { key: "ic_review", label: "IC Review", color: "border-purple-200 bg-purple-50/60" },
    { key: "approved", label: "Approved", color: "border-emerald-200 bg-emerald-50/60" },
  ];

  function defaultForm() {
    return {
      name: "",
      location: "",
      gps_coordinates: "",
      description: "",
      stage: "opportunity" as DevPipelineStage,
      development_type: "residential" as DevPipelineDevType,
      land_size_sqm: "",
      land_cost: "",
      land_status: "",
      estimated_gdv: "",
      estimated_cost: "",
      expected_irr: "",
      hurdle_rate: "25",
      number_of_units: "0",
      market_analysis: "",
      feasibility_notes: "",
      identified_date: new Date().toISOString().slice(0, 10),
      target_start_date: "",
      target_completion_date: "",
      notes: "",
    };
  }

  // ── Dev Fill ──────────────────────────────────────────────────────────
  let devIdx = 0;
  const SAMPLES = [
    {
      name: "Victoria Island Mixed-Use Tower",
      location: "Plot 12, Adeola Odeku Street, Victoria Island, Lagos",
      description: "35-storey mixed-use development comprising 18 floors of Grade A office space, 12 floors of luxury residential apartments, and 5 floors of retail/parking podium. Prime VI location with waterfront views.",
      development_type: "mixed_use" as DevPipelineDevType,
      stage: "financial_model" as DevPipelineStage,
      land_size_sqm: "4500",
      land_cost: "2800000000",
      land_status: "MOU Signed — Title verification in progress",
      estimated_gdv: "18500000000",
      estimated_cost: "12200000000",
      expected_irr: "28.5",
      number_of_units: "180",
      market_analysis: "Victoria Island office vacancy at 15% (down from 22% in 2024). Grade A rents averaging ₦120,000/sqm/annum. Residential demand strong for 2-3 bed luxury units priced ₦150M-₦350M. Comparable: Eko Atlantic towers achieving ₦180,000/sqm office rents.",
      target_start_date: "2026-09-01",
    },
    {
      name: "Abuja Residential Estate — Katampe Extension",
      location: "Plot 1847, Katampe Extension, Abuja FCT",
      description: "Gated residential estate of 120 units comprising 40 semi-detached duplexes, 60 terraced houses, and 20 detached villas. Full infrastructure including internal roads, sewage treatment, and 2MW power plant.",
      development_type: "residential" as DevPipelineDevType,
      stage: "feasibility" as DevPipelineStage,
      land_size_sqm: "28000",
      land_cost: "950000000",
      land_status: "Under Survey — C of O application submitted",
      estimated_gdv: "8200000000",
      estimated_cost: "5800000000",
      expected_irr: "22.1",
      number_of_units: "120",
      market_analysis: "Katampe Extension experiencing rapid development. Comparable estates selling 4-bed duplexes at ₦85M-₦120M. Absorption rate: 8-12 units/month for well-priced estates. Key risk: infrastructure delivery timeline.",
      target_start_date: "2026-11-01",
    },
    {
      name: "Lekki Commercial Complex",
      location: "Admiralty Way, Lekki Phase 1, Lagos",
      description: "12-storey commercial office building with 2 basement parking levels. Target: tech companies and financial services firms relocating from Victoria Island.",
      development_type: "commercial" as DevPipelineDevType,
      stage: "opportunity" as DevPipelineStage,
      land_size_sqm: "3200",
      land_cost: "1500000000",
      land_status: "Preliminary discussions with landowner",
      estimated_gdv: "9800000000",
      estimated_cost: "6500000000",
      expected_irr: "31.2",
      number_of_units: "0",
      market_analysis: "Lekki Phase 1 emerging as alternative commercial hub. Rents 30-40% below VI with modern infrastructure. Several tech firms (Flutterwave, Paystack) already relocated. Limited Grade A supply.",
      target_start_date: "2027-03-01",
    },
  ];

  function devFill() {
    const s = SAMPLES[devIdx % SAMPLES.length];
    devIdx++;
    form = { ...defaultForm(), ...s };
  }

  // ── Data Fetching ─────────────────────────────────────────────────────

  async function fetchPipeline() {
    loading = true;
    try {
      const [res, sum] = await Promise.all([
        api.get<PaginatedResponse<PipelineOpportunityListItem>>("/projects/pipeline/", { page_size: "200", ordering: "stage,stage_order,-created_at" }),
        api.get<PipelineSummary>("/projects/pipeline/summary/"),
      ]);
      rows = res.results;
      summary = sum;
    } catch { rows = []; }
    loading = false;
  }

  $effect(() => { fetchPipeline(); });

  function cardsByStage(stage: DevPipelineStage): PipelineOpportunityListItem[] {
    return rows.filter(r => r.stage === stage);
  }

  async function openDetail(id: number) {
    detailOpen = true;
    detailLoading = true;
    try { detail = await api.get<PipelineOpportunityDetail>(`/projects/pipeline/${id}/`); } catch { detail = null; }
    detailLoading = false;
  }

  async function moveStage(id: number, newStage: DevPipelineStage) {
    try {
      await api.post(`/projects/pipeline/${id}/move-stage/`, { stage: newStage });
      await fetchPipeline();
    } catch { toast.error("Move failed", "Could not update stage."); }
  }

  async function saveOpportunity(e: Event) {
    e.preventDefault();
    if (!form.name.trim()) { toast.error("Validation", "Name is required."); return; }
    saving = true;
    try {
      await api.post("/projects/pipeline/", {
        ...form,
        land_size_sqm: form.land_size_sqm || null,
        land_cost: form.land_cost || "0",
        estimated_gdv: form.estimated_gdv || "0",
        estimated_cost: form.estimated_cost || "0",
        expected_irr: form.expected_irr || "0",
        number_of_units: Number(form.number_of_units) || 0,
        target_start_date: form.target_start_date || null,
        target_completion_date: form.target_completion_date || null,
        identified_date: form.identified_date || null,
      });
      toast.success("Opportunity added", `"${form.name}" added to pipeline.`);
      createOpen = false;
      form = defaultForm();
      await fetchPipeline();
    } catch (error) {
      const msg = error instanceof ApiError ? (Object.values(error.fieldErrors)[0]?.[0] ?? "Save failed.") : "Save failed.";
      toast.error("Save failed", msg);
    } finally { saving = false; }
  }

  // ── Helpers ───────────────────────────────────────────────────────────
  function fmtC(v: string | number | null | undefined): string { if (!v || v === "0.00" || v === "0") return "--"; return currency.formatCompact(v); }
  function fmtCFull(v: string | number | null | undefined): string { if (!v || v === "0.00" || v === "0") return "--"; return currency.format(v); }
  function fmtDate(v: string | null | undefined): string { if (!v) return "--"; const d = new Date(v); return Number.isNaN(d.getTime()) ? "--" : d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }); }
  function fmtPct(v: string | number | null): string { if (v === null || v === "") return "--"; return `${Number(v).toFixed(1)}%`; }

  function devTypeColor(t: string): string {
    const map: Record<string, string> = { residential: "bg-blue-100 text-blue-800", commercial: "bg-emerald-100 text-emerald-800", mixed_use: "bg-indigo-100 text-indigo-800", industrial: "bg-neutral-100 text-neutral-700", hospitality: "bg-purple-100 text-purple-800", retail: "bg-amber-100 text-amber-800" };
    return map[t] ?? "bg-neutral-100 text-neutral-600";
  }
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">Development</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-900">Project Pipeline</h1>
      <p class="mt-1 text-sm text-neutral-500">Track development opportunities from identification through IC approval.</p>
    </div>
    <button onclick={() => { form = defaultForm(); createOpen = true; }} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800">+ New Opportunity</button>
  </div>

  <!-- Summary -->
  {#if summary}
    <div class="grid grid-cols-2 gap-4 md:grid-cols-4">
      <div class="rounded-xl border border-neutral-200 bg-white p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Pipeline</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{summary.total} opportunities</p>
      </div>
      <div class="rounded-xl border border-emerald-100 bg-emerald-50 p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-emerald-700">Total GDV</p>
        <p class="mt-1 text-xl font-bold text-emerald-900 tabular-nums">{fmtC(summary.total_gdv)}</p>
      </div>
      <div class="rounded-xl border border-indigo-100 bg-indigo-50 p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-indigo-700">Approved</p>
        <p class="mt-1 text-xl font-bold text-indigo-900 tabular-nums">{summary.approved}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Stage Breakdown</p>
        <div class="mt-1 flex items-center gap-1">
          {#each summary.stages.slice(0, 5) as s}
            <div class="flex-1 text-center">
              <p class="text-sm font-bold tabular-nums text-neutral-900">{s.count}</p>
              <p class="text-[8px] text-neutral-400 truncate">{s.label.split(" ")[0]}</p>
            </div>
          {/each}
        </div>
      </div>
    </div>
  {/if}

  <!-- Kanban Board -->
  {#if loading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else}
    <div class="overflow-x-auto pb-4">
      <div class="flex gap-4" style="min-width: {STAGES.length * 280}px">
        {#each STAGES as stage}
          {@const cards = cardsByStage(stage.key)}
          <div class="w-[270px] shrink-0">
            <div class="rounded-t-xl border {stage.color} px-3 py-2.5 backdrop-blur-sm">
              <div class="flex items-center justify-between">
                <h3 class="text-xs font-semibold text-neutral-700">{stage.label}</h3>
                <span class="rounded-full bg-white/80 px-2 py-0.5 text-[10px] font-bold text-neutral-600 tabular-nums">{cards.length}</span>
              </div>
            </div>
            <div class="space-y-2 rounded-b-xl border border-t-0 border-neutral-200 bg-neutral-50/50 p-2 min-h-[200px]">
              {#each cards as card}
                <button class="w-full text-left rounded-xl border border-white/60 bg-white/80 p-3 shadow-sm hover:shadow-md transition-shadow backdrop-blur-sm cursor-pointer" onclick={() => openDetail(card.id)}>
                  <div class="flex items-start justify-between gap-2 mb-2">
                    <p class="text-sm font-semibold text-neutral-900 leading-tight">{card.name}</p>
                    <span class="shrink-0 rounded-full px-1.5 py-0.5 text-[9px] font-semibold {devTypeColor(card.development_type)}">{card.development_type_display}</span>
                  </div>
                  {#if card.location}<p class="text-[11px] text-neutral-500 mb-2 truncate">{card.location}</p>{/if}
                  <div class="grid grid-cols-2 gap-x-3 gap-y-1">
                    <div><p class="text-[9px] text-neutral-400">GDV</p><p class="text-xs font-bold text-emerald-700 tabular-nums">{fmtC(card.estimated_gdv)}</p></div>
                    <div><p class="text-[9px] text-neutral-400">Cost</p><p class="text-xs font-bold text-neutral-700 tabular-nums">{fmtC(card.estimated_cost)}</p></div>
                  </div>
                  <div class="mt-2 flex items-center justify-between">
                    <span class="text-[10px] font-bold tabular-nums {card.meets_hurdle ? 'text-emerald-600' : 'text-amber-600'}">IRR {fmtPct(card.expected_irr)}</span>
                    {#if card.number_of_units > 0}<span class="text-[10px] text-neutral-400">{card.number_of_units} units</span>{/if}
                  </div>
                </button>
              {/each}
              {#if cards.length === 0}<div class="flex items-center justify-center py-8"><p class="text-[11px] text-neutral-400">No opportunities</p></div>{/if}
            </div>
          </div>
        {/each}
      </div>
    </div>
  {/if}
</div>

<!-- ═══════════ DETAIL DRAWER ═══════════ -->
<DrawerShell open={detailOpen} title={detail?.pipeline_ref ?? "Opportunity"} subtitle={detail?.name ?? ""} width="max-w-2xl" onclose={() => (detailOpen = false)}>
  {#if detailLoading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if detail}
    <div class="p-6 space-y-5">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <StatusBadge status={detail.stage} />
          <span class="rounded-full px-2 py-0.5 text-[10px] font-semibold {devTypeColor(detail.development_type)}">{detail.development_type_display}</span>
        </div>
        {#if detail.ic_decision !== "pending"}
          <span class="text-xs font-semibold {detail.ic_decision === 'approved' ? 'text-emerald-600' : detail.ic_decision === 'rejected' ? 'text-red-600' : 'text-amber-600'}">IC: {detail.ic_decision_display}</span>
        {/if}
      </div>

      <!-- Financial hero -->
      <div class="grid grid-cols-3 gap-3">
        <div class="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-center">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-emerald-700">Est. GDV</p>
          <p class="mt-1 text-lg font-bold text-emerald-900 tabular-nums">{fmtC(detail.estimated_gdv)}</p>
        </div>
        <div class="rounded-lg border border-amber-200 bg-amber-50 p-3 text-center">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-amber-700">Est. Cost</p>
          <p class="mt-1 text-lg font-bold text-amber-900 tabular-nums">{fmtC(detail.estimated_cost)}</p>
        </div>
        <div class="rounded-lg border-2 {detail.meets_hurdle ? 'border-emerald-300 bg-emerald-50' : 'border-amber-300 bg-amber-50'} p-3 text-center">
          <p class="text-[10px] font-semibold uppercase tracking-wider {detail.meets_hurdle ? 'text-emerald-700' : 'text-amber-700'}">Expected IRR</p>
          <p class="mt-1 text-2xl font-bold tabular-nums {detail.meets_hurdle ? 'text-emerald-600' : 'text-amber-600'}">{fmtPct(detail.expected_irr)}</p>
          <p class="text-[9px] text-neutral-400">Hurdle: {fmtPct(detail.hurdle_rate)}</p>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <div class="rounded-lg border border-neutral-200 p-3 text-center">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Margin</p>
          <p class="text-sm font-bold text-neutral-900 tabular-nums">{fmtPct(detail.expected_margin_pct)}</p>
        </div>
        <div class="rounded-lg border border-neutral-200 p-3 text-center">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Profit</p>
          <p class="text-sm font-bold text-neutral-900 tabular-nums">{fmtC(detail.profit)}</p>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Location</p><p class="text-sm text-neutral-900">{detail.location || "--"}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Land Size</p><p class="text-sm text-neutral-900">{detail.land_size_sqm ? `${Number(detail.land_size_sqm).toLocaleString()} sqm` : "--"}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Land Cost</p><p class="text-sm text-neutral-900">{fmtCFull(detail.land_cost)}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Land Status</p><p class="text-sm text-neutral-900">{detail.land_status || "--"}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Units</p><p class="text-sm text-neutral-900">{detail.number_of_units || "--"}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Target Start</p><p class="text-sm text-neutral-900">{fmtDate(detail.target_start_date)}</p></div>
      </div>

      {#if detail.description}<div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Description</p><p class="text-sm text-neutral-700 whitespace-pre-line">{detail.description}</p></div>{/if}

      {#if detail.market_analysis}
        <div class="rounded-lg border border-blue-200 bg-blue-50/50 p-4">
          <p class="text-[10px] font-bold uppercase tracking-wider text-blue-700 mb-2">Market Analysis</p>
          <p class="text-sm text-neutral-800 whitespace-pre-line">{detail.market_analysis}</p>
        </div>
      {/if}

      {#if detail.feasibility_notes}<div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Feasibility Notes</p><p class="text-sm text-neutral-700 whitespace-pre-line">{detail.feasibility_notes}</p></div>{/if}

      {#if detail.ic_decision !== "pending" || detail.ic_conditions || detail.ic_reviewers}
        <div class="rounded-lg border border-purple-200 bg-purple-50/50 p-4">
          <p class="text-[10px] font-bold uppercase tracking-wider text-purple-700 mb-2">Investment Committee</p>
          <div class="grid grid-cols-2 gap-3">
            <div><p class="text-[10px] text-neutral-400">Decision</p><p class="text-sm font-semibold {detail.ic_decision === 'approved' ? 'text-emerald-600' : detail.ic_decision === 'rejected' ? 'text-red-600' : 'text-neutral-900'}">{detail.ic_decision_display}</p></div>
            <div><p class="text-[10px] text-neutral-400">Review Date</p><p class="text-sm text-neutral-900">{fmtDate(detail.ic_review_date)}</p></div>
          </div>
          {#if detail.ic_conditions}<p class="mt-2 text-sm text-neutral-700">{detail.ic_conditions}</p>{/if}
          {#if detail.ic_reviewers}<p class="mt-1 text-xs text-neutral-500">Reviewers: {detail.ic_reviewers}</p>{/if}
        </div>
      {/if}

      <!-- Stage Move -->
      <div class="border-t border-neutral-200 pt-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-2">Move Stage</p>
        <div class="flex flex-wrap gap-2">
          {#each STAGES as s}
            <button disabled={s.key === detail.stage} onclick={() => { moveStage(detail!.id, s.key); detailOpen = false; }}
              class="rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors {s.key === detail.stage ? 'border-neutral-300 bg-neutral-100 text-neutral-400 cursor-not-allowed' : 'border-neutral-200 bg-white text-neutral-700 hover:bg-neutral-50'}">
              {s.label}
            </button>
          {/each}
        </div>
      </div>

      {#if detail.notes}<div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Notes</p><p class="text-sm text-neutral-700 whitespace-pre-line">{detail.notes}</p></div>{/if}
    </div>
  {/if}
</DrawerShell>

<!-- ═══════════ CREATE DRAWER ═══════════ -->
<DrawerShell open={createOpen} title="New Opportunity" subtitle="Add a development opportunity to the pipeline" width="max-w-xl" onclose={() => (createOpen = false)}>
  <form onsubmit={saveOpportunity} class="p-6 space-y-4">
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Project Name *</span><input bind:value={form.name} placeholder="e.g. Victoria Island Mixed-Use Tower" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Stage</span><select bind:value={form.stage} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="opportunity">Opportunity Identified</option><option value="feasibility">Feasibility Study</option><option value="financial_model">Financial Modeling</option><option value="due_diligence">Due Diligence</option><option value="ic_review">IC Review</option><option value="approved">Approved</option>
      </select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Development Type</span><select bind:value={form.development_type} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="residential">Residential</option><option value="commercial">Commercial</option><option value="mixed_use">Mixed-Use</option><option value="industrial">Industrial</option><option value="hospitality">Hospitality</option><option value="retail">Retail</option><option value="infrastructure">Infrastructure</option><option value="other">Other</option>
      </select></label>
    </div>
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Location</span><input bind:value={form.location} placeholder="Address or area" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Description</span><textarea bind:value={form.description} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>

    <div class="grid grid-cols-3 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Land Size (sqm)</span><input type="number" step="0.01" bind:value={form.land_size_sqm} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Land Cost</span><input type="number" step="0.01" bind:value={form.land_cost} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Land Status</span><input bind:value={form.land_status} placeholder="e.g. MOU Signed" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>

    <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-3 space-y-3">
      <p class="text-xs font-semibold text-neutral-600">Financial Projections</p>
      <div class="grid grid-cols-2 gap-4">
        <label><span class="mb-1 block text-xs text-neutral-500">Estimated GDV</span><input type="number" step="0.01" bind:value={form.estimated_gdv} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
        <label><span class="mb-1 block text-xs text-neutral-500">Estimated Cost</span><input type="number" step="0.01" bind:value={form.estimated_cost} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      </div>
      <div class="grid grid-cols-3 gap-4">
        <label><span class="mb-1 block text-xs text-neutral-500">Expected IRR (%)</span><input type="number" step="0.1" bind:value={form.expected_irr} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
        <label><span class="mb-1 block text-xs text-neutral-500">Hurdle Rate (%)</span><input type="number" step="0.1" bind:value={form.hurdle_rate} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
        <label><span class="mb-1 block text-xs text-neutral-500">Number of Units</span><input type="number" bind:value={form.number_of_units} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      </div>
    </div>

    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Market Analysis</span><textarea bind:value={form.market_analysis} rows="3" placeholder="Absorption rates, comparable sales, demographics..." class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>

    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Target Start Date</span><DateInput bind:value={form.target_start_date} /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Identified Date</span><DateInput bind:value={form.identified_date} /></label>
    </div>

    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Notes</span><textarea bind:value={form.notes} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>

    <div class="flex justify-end gap-2 pt-2">
      <button type="button" onclick={() => (createOpen = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      {#if isDev}<button type="button" onclick={devFill} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
      <button type="submit" disabled={saving} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{saving ? "Saving..." : "Add to Pipeline"}</button>
    </div>
  </form>
</DrawerShell>

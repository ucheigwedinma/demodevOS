<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DrawerShell from "$lib/components/DrawerShell.svelte";
  import type {
    FinancingSourceListItem,
    FinancingSourceDetail,
    FinancingDashboard,
    FinancingSourceType,
    FinancingSourceStatus,
    PaginatedResponse,
    ProjectListItem,
  } from "$lib/types";

  let sources = $state<FinancingSourceListItem[]>([]);
  let dashboard = $state<FinancingDashboard | null>(null);
  let loading = $state(true);
  let projectFilter = $state("");
  let typeFilter = $state("");
  let statusFilter = $state("");
  let searchInput = $state("");
  let searchQuery = $state("");
  let searchTimeout: ReturnType<typeof setTimeout> | undefined;

  let detailOpen = $state(false);
  let detail = $state<FinancingSourceDetail | null>(null);
  let detailLoading = $state(false);
  let detailTab = $state<"overview" | "drawdowns" | "repayments" | "covenants">("overview");

  let createOpen = $state(false);
  let saving = $state(false);
  let projects = $state<ProjectListItem[]>([]);
  let form = $state(defaultForm());

  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  function defaultForm() {
    return {
      project: "", name: "", source_type: "bank_loan" as FinancingSourceType,
      committed_amount: "", interest_rate: "", rate_type: "fixed",
      rate_benchmark: "", arrangement_fee_pct: "", grace_period_months: "0",
      tenor_months: "", repayment_frequency: "quarterly",
      agreement_date: "", maturity_date: "",
      institution: "", contact_person: "", contact_email: "", notes: "",
    };
  }

  function devFill() {
    form = {
      ...form,
      project: form.project || (projects.length > 0 ? String(projects[0].id) : ""),
      name: "GTBank Construction Facility",
      source_type: "bank_loan",
      committed_amount: "1500000000",
      interest_rate: "18.5",
      rate_type: "variable",
      rate_benchmark: "MPR + 3%",
      arrangement_fee_pct: "1.5",
      grace_period_months: "6",
      tenor_months: "36",
      repayment_frequency: "quarterly",
      agreement_date: "2025-10-01",
      maturity_date: "2028-09-30",
      institution: "Guaranty Trust Bank Plc",
      contact_person: "Adebayo Ojo",
      contact_email: "adebayo.ojo@gtbank.com",
      notes: "Construction finance facility secured against project receivables. First drawdown upon site mobilization certificate.",
    };
  }

  async function fetchData() {
    loading = true;
    try {
      const params: Record<string, string> = { page_size: "100" };
      if (projectFilter) params.project = projectFilter;
      if (typeFilter) params.source_type = typeFilter;
      if (statusFilter) params.status = statusFilter;
      if (searchQuery) params.search = searchQuery;

      const [res, dashRes, projRes] = await Promise.all([
        api.get<PaginatedResponse<FinancingSourceListItem>>("/projects/financing/", params),
        api.get<FinancingDashboard>("/projects/financing/dashboard/"),
        projects.length === 0 ? api.get<PaginatedResponse<ProjectListItem>>("/projects/", { page_size: "200", ordering: "name" }) : Promise.resolve(null),
      ]);
      sources = res.results;
      dashboard = dashRes;
      if (projRes) projects = projRes.results;
    } catch { sources = []; }
    loading = false;
  }

  $effect(() => { void projectFilter; void typeFilter; void statusFilter; void searchQuery; fetchData(); });

  function onSearchInput(e: Event) {
    searchInput = (e.target as HTMLInputElement).value;
    if (searchTimeout) clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => { searchQuery = searchInput.trim(); }, 250);
  }

  async function openDetail(id: number) {
    detailOpen = true;
    detailLoading = true;
    detailTab = "overview";
    try { detail = await api.get<FinancingSourceDetail>(`/projects/financing/${id}/`); } catch { detail = null; }
    detailLoading = false;
  }

  async function saveSource(e: Event) {
    e.preventDefault();
    if (!form.project || !form.name.trim()) { toast.error("Required", "Project and name are required."); return; }
    saving = true;
    try {
      await api.post("/projects/financing/", {
        ...form,
        project: Number(form.project),
        committed_amount: form.committed_amount || "0",
        interest_rate: form.interest_rate || null,
        arrangement_fee_pct: form.arrangement_fee_pct || "0",
        grace_period_months: Number(form.grace_period_months) || 0,
        tenor_months: Number(form.tenor_months) || 0,
        agreement_date: form.agreement_date || null,
        maturity_date: form.maturity_date || null,
      });
      toast.success("Source added", `"${form.name}" registered.`);
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

  function covenantColor(s: string): string {
    if (s === "compliant") return "bg-emerald-100 text-emerald-800";
    if (s === "at_risk") return "bg-amber-100 text-amber-800";
    if (s === "breached") return "bg-red-100 text-red-800";
    return "bg-neutral-100 text-neutral-600";
  }
</script>

<div class="space-y-6">
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">Projects</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-900">Project Financing</h1>
      <p class="mt-1 text-sm text-neutral-500">Capital stack transparency — funding sources, drawdowns, repayments, and covenant compliance.</p>
    </div>
    <button onclick={() => { form = defaultForm(); createOpen = true; }} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800">+ Add Source</button>
  </div>

  <!-- Dashboard KPIs -->
  {#if dashboard}
    <div class="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-6">
      <div class="rounded-xl border border-blue-100 bg-blue-50 p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-blue-600">Committed</p>
        <p class="mt-1 text-xl font-bold text-blue-900 tabular-nums">{fmtC(dashboard.total_committed)}</p>
      </div>
      <div class="rounded-xl border border-emerald-100 bg-emerald-50 p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-emerald-700">Drawn</p>
        <p class="mt-1 text-xl font-bold text-emerald-900 tabular-nums">{fmtC(dashboard.total_drawn)}</p>
      </div>
      <div class="rounded-xl border border-indigo-100 bg-indigo-50 p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-indigo-700">Available</p>
        <p class="mt-1 text-xl font-bold text-indigo-900 tabular-nums">{fmtC(dashboard.available_liquidity)}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">WACC</p>
        <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{dashboard.wacc}%</p>
      </div>
      {#if dashboard}
        {@const eq = Number(dashboard.equity_total) || 0}
        {@const dt = Number(dashboard.debt_total) || 0}
        {@const tot = eq + dt}
        <div class="rounded-xl border border-neutral-200 bg-white p-4">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Equity / Debt</p>
          <p class="mt-1 text-lg font-bold text-neutral-900 tabular-nums">{tot > 0 ? Math.round(eq / tot * 100) : 0}% / {tot > 0 ? Math.round(dt / tot * 100) : 0}%</p>
        </div>
      {/if}
      <div class="rounded-xl border border-amber-100 bg-amber-50 p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-amber-700">Alerts</p>
        <p class="mt-1 text-sm font-semibold text-amber-900">{dashboard.upcoming_drawdowns} drawdown{dashboard.upcoming_drawdowns !== 1 ? "s" : ""} due</p>
        {#if dashboard.at_risk_covenants > 0}<p class="text-xs text-red-600 font-semibold">{dashboard.at_risk_covenants} covenant{dashboard.at_risk_covenants !== 1 ? "s" : ""} at risk</p>{/if}
      </div>
    </div>
  {/if}

  <!-- Filters -->
  <div class="grid grid-cols-1 gap-3 xl:grid-cols-4">
    <input type="text" value={searchInput} oninput={onSearchInput} placeholder="Search name, reference, institution..." class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
    <select bind:value={projectFilter} onchange={() => {}} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Projects</option>
      {#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}
    </select>
    <select bind:value={typeFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Types</option>
      <option value="bank_loan">Bank Loan</option><option value="mezzanine">Mezzanine</option><option value="equity">Equity</option>
      <option value="joint_venture">Joint Venture</option><option value="private_placement">Private Placement</option><option value="grant">Grant</option><option value="other">Other</option>
    </select>
    <select bind:value={statusFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Statuses</option>
      <option value="pending">Pending</option><option value="active">Active</option><option value="fully_drawn">Fully Drawn</option><option value="repaid">Repaid</option><option value="expired">Expired</option>
    </select>
  </div>

  <!-- Sources Table -->
  {#if loading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if sources.length === 0}
    <div class="rounded-2xl border border-neutral-200 bg-white px-6 py-14 text-center"><p class="text-sm text-neutral-500">No financing sources found.</p></div>
  {:else}
    <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
      <div class="overflow-x-auto">
        <table class="min-w-[900px] w-full">
          <thead class="border-b border-neutral-200 bg-neutral-50">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Reference</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Source</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Type</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Status</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Committed</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Drawn</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Available</th>
              <th class="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-neutral-500">Rate</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each sources as s}
              <tr class="hover:bg-neutral-50 cursor-pointer" onclick={() => openDetail(s.id)}>
                <td class="px-4 py-3 text-sm font-semibold text-neutral-900">{s.reference}</td>
                <td class="px-4 py-3">
                  <p class="text-sm font-medium text-neutral-900">{s.name}</p>
                  <p class="text-xs text-neutral-400">{s.institution || s.project_name}</p>
                </td>
                <td class="px-4 py-3 text-xs text-neutral-600">{s.source_type_display}</td>
                <td class="px-4 py-3"><StatusBadge status={s.status} /></td>
                <td class="px-4 py-3 text-right text-sm font-bold tabular-nums text-neutral-900">{fmtC(s.committed_amount)}</td>
                <td class="px-4 py-3 text-right text-sm tabular-nums text-neutral-700">{fmtC(s.drawn_amount)}</td>
                <td class="px-4 py-3 text-right text-sm font-semibold tabular-nums text-emerald-600">{fmtC(s.available_amount)}</td>
                <td class="px-4 py-3 text-center text-sm tabular-nums text-neutral-600">{s.interest_rate ? `${s.interest_rate}%` : "--"}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>
  {/if}
</div>

<!-- ═══════════ DETAIL DRAWER ═══════════ -->
<DrawerShell open={detailOpen} title="Financing Source" subtitle={detail ? `${detail.reference} — ${detail.name}` : ""} width="max-w-2xl" onclose={() => (detailOpen = false)}>
  {#if detailLoading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if detail}
    <div class="border-b border-neutral-200">
      <div class="flex gap-1 px-6 pt-4">
        {#each [["overview", "Overview"], ["drawdowns", "Drawdowns"], ["repayments", "Repayments"], ["covenants", "Covenants"]] as [key, label]}
          <button onclick={() => (detailTab = key as typeof detailTab)} class="rounded-t-lg px-4 py-2 text-xs font-semibold transition-colors {detailTab === key ? 'bg-white text-neutral-900 border border-b-white border-neutral-200 -mb-px' : 'text-neutral-500 hover:text-neutral-700'}">{label}</button>
        {/each}
      </div>
    </div>

    <div class="p-6 space-y-5">
      {#if detailTab === "overview"}
        <div class="flex items-center gap-3">
          <StatusBadge status={detail.status} />
          <span class="text-xs text-neutral-500">{detail.source_type_display} — {detail.rate_type_display}</span>
        </div>
        <div class="grid grid-cols-3 gap-4">
          <div class="rounded-lg border border-blue-100 bg-blue-50 p-3 text-center">
            <p class="text-[9px] font-semibold uppercase tracking-wider text-blue-600">Committed</p>
            <p class="mt-1 text-lg font-bold text-blue-900 tabular-nums">{fmtC(detail.committed_amount)}</p>
          </div>
          <div class="rounded-lg border border-neutral-200 bg-white p-3 text-center">
            <p class="text-[9px] font-semibold uppercase tracking-wider text-neutral-500">Drawn</p>
            <p class="mt-1 text-lg font-bold text-neutral-900 tabular-nums">{fmtC(detail.drawn_amount)}</p>
          </div>
          <div class="rounded-lg border border-emerald-100 bg-emerald-50 p-3 text-center">
            <p class="text-[9px] font-semibold uppercase tracking-wider text-emerald-700">Available</p>
            <p class="mt-1 text-lg font-bold text-emerald-900 tabular-nums">{fmtC(detail.available_amount)}</p>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3 text-sm">
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Interest Rate</p><p class="text-neutral-900 font-semibold">{detail.interest_rate ? `${detail.interest_rate}% (${detail.rate_type_display})` : "--"}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Benchmark</p><p class="text-neutral-900">{detail.rate_benchmark || "--"}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Tenor</p><p class="text-neutral-900">{detail.tenor_months ? `${detail.tenor_months} months` : "--"}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Grace Period</p><p class="text-neutral-900">{detail.grace_period_months ? `${detail.grace_period_months} months` : "--"}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Repayment</p><p class="text-neutral-900 capitalize">{detail.repayment_frequency.replace("_", "-")}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Arrangement Fee</p><p class="text-neutral-900">{detail.arrangement_fee_pct}%</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Agreement Date</p><p class="text-neutral-900">{fmtDate(detail.agreement_date)}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Maturity</p><p class="text-neutral-900">{fmtDate(detail.maturity_date)}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Institution</p><p class="text-neutral-900">{detail.institution || "--"}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Contact</p><p class="text-neutral-900">{detail.contact_person || "--"}</p></div>
        </div>
        {#if detail.notes}<div><p class="text-[10px] font-semibold uppercase text-neutral-400 mb-1">Notes</p><p class="text-sm text-neutral-700 whitespace-pre-line">{detail.notes}</p></div>{/if}

      {:else if detailTab === "drawdowns"}
        {#if detail.drawdowns.length === 0}
          <p class="text-sm text-neutral-400 text-center py-6">No drawdowns recorded.</p>
        {:else}
          <table class="w-full">
            <thead class="bg-neutral-50"><tr>
              <th class="px-3 py-2 text-left text-[10px] font-semibold uppercase text-neutral-500">Date</th>
              <th class="px-3 py-2 text-left text-[10px] font-semibold uppercase text-neutral-500">Reference</th>
              <th class="px-3 py-2 text-right text-[10px] font-semibold uppercase text-neutral-500">Requested</th>
              <th class="px-3 py-2 text-right text-[10px] font-semibold uppercase text-neutral-500">Received</th>
              <th class="px-3 py-2 text-center text-[10px] font-semibold uppercase text-neutral-500">Status</th>
            </tr></thead>
            <tbody class="divide-y divide-neutral-100">
              {#each detail.drawdowns as d}
                <tr>
                  <td class="px-3 py-2 text-sm text-neutral-700">{fmtDate(d.request_date)}</td>
                  <td class="px-3 py-2 text-sm text-neutral-900 font-medium">{d.reference || "--"}</td>
                  <td class="px-3 py-2 text-right text-sm font-semibold tabular-nums text-neutral-900">{fmtCFull(d.amount_requested)}</td>
                  <td class="px-3 py-2 text-right text-sm tabular-nums text-emerald-600">{d.amount_received ? fmtCFull(d.amount_received) : "--"}</td>
                  <td class="px-3 py-2 text-center"><StatusBadge status={d.status} /></td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}

      {:else if detailTab === "repayments"}
        {#if detail.repayments.length === 0}
          <p class="text-sm text-neutral-400 text-center py-6">No repayment schedule defined.</p>
        {:else}
          <table class="w-full">
            <thead class="bg-neutral-50"><tr>
              <th class="px-3 py-2 text-left text-[10px] font-semibold uppercase text-neutral-500">Date</th>
              <th class="px-3 py-2 text-right text-[10px] font-semibold uppercase text-neutral-500">Principal</th>
              <th class="px-3 py-2 text-right text-[10px] font-semibold uppercase text-neutral-500">Interest</th>
              <th class="px-3 py-2 text-right text-[10px] font-semibold uppercase text-neutral-500">Total</th>
              <th class="px-3 py-2 text-right text-[10px] font-semibold uppercase text-neutral-500">Balance</th>
              <th class="px-3 py-2 text-center text-[10px] font-semibold uppercase text-neutral-500">Status</th>
            </tr></thead>
            <tbody class="divide-y divide-neutral-100">
              {#each detail.repayments as r}
                <tr class="{r.status === 'overdue' ? 'bg-red-50/40' : ''}">
                  <td class="px-3 py-2 text-sm text-neutral-700">{fmtDate(r.payment_date)}</td>
                  <td class="px-3 py-2 text-right text-sm tabular-nums text-neutral-900">{fmtCFull(r.principal_amount)}</td>
                  <td class="px-3 py-2 text-right text-sm tabular-nums text-neutral-500">{fmtCFull(r.interest_amount)}</td>
                  <td class="px-3 py-2 text-right text-sm font-semibold tabular-nums text-neutral-900">{fmtCFull(r.total_payment)}</td>
                  <td class="px-3 py-2 text-right text-sm tabular-nums text-neutral-600">{fmtCFull(r.ending_balance)}</td>
                  <td class="px-3 py-2 text-center"><StatusBadge status={r.status} /></td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}

      {:else if detailTab === "covenants"}
        {#if detail.covenants.length === 0}
          <p class="text-sm text-neutral-400 text-center py-6">No covenants tracked.</p>
        {:else}
          <div class="space-y-3">
            {#each detail.covenants as c}
              <div class="rounded-xl border border-neutral-200 p-4">
                <div class="flex items-center justify-between mb-2">
                  <p class="text-sm font-semibold text-neutral-900">{c.name}</p>
                  <span class="inline-block rounded-full px-2.5 py-0.5 text-[10px] font-semibold {covenantColor(c.status)}">{c.status_display}</span>
                </div>
                <div class="grid grid-cols-3 gap-3 text-xs">
                  <div><p class="text-neutral-400">Threshold</p><p class="text-neutral-900 font-medium">{c.threshold || "--"}</p></div>
                  <div><p class="text-neutral-400">Current</p><p class="text-neutral-900 font-medium">{c.current_value || "--"}</p></div>
                  <div><p class="text-neutral-400">Last Tested</p><p class="text-neutral-900">{fmtDate(c.last_tested)}</p></div>
                </div>
                {#if c.description}<p class="mt-2 text-xs text-neutral-500">{c.description}</p>{/if}
              </div>
            {/each}
          </div>
        {/if}
      {/if}
    </div>
  {/if}
</DrawerShell>

<!-- ═══════════ CREATE DRAWER ═══════════ -->
<DrawerShell open={createOpen} title="Add Financing Source" subtitle="Register a new capital provider" width="max-w-xl" onclose={() => (createOpen = false)}>
  <form onsubmit={saveSource} class="p-6 space-y-4">
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Project *</span><select bind:value={form.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"><option value="">Select</option>{#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}</select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Source Type</span><select bind:value={form.source_type} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="bank_loan">Bank Loan</option><option value="mezzanine">Mezzanine</option><option value="equity">Equity</option>
        <option value="joint_venture">Joint Venture</option><option value="private_placement">Private Placement</option><option value="grant">Grant</option><option value="other">Other</option>
      </select></label>
    </div>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Name *</span><input bind:value={form.name} placeholder="e.g. GTBank Construction Facility" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Committed Amount</span><input type="number" step="0.01" bind:value={form.committed_amount} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Interest Rate (%)</span><input type="number" step="0.001" bind:value={form.interest_rate} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <div class="grid grid-cols-3 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Rate Type</span><select bind:value={form.rate_type} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"><option value="fixed">Fixed</option><option value="variable">Variable</option></select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Benchmark</span><input bind:value={form.rate_benchmark} placeholder="e.g. MPR + 3%" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Arrangement Fee %</span><input type="number" step="0.01" bind:value={form.arrangement_fee_pct} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <div class="grid grid-cols-3 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Tenor (months)</span><input type="number" bind:value={form.tenor_months} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Grace Period (months)</span><input type="number" bind:value={form.grace_period_months} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Repayment</span><select bind:value={form.repayment_frequency} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="monthly">Monthly</option><option value="quarterly">Quarterly</option><option value="semi_annual">Semi-Annual</option><option value="annual">Annual</option><option value="bullet">Bullet</option>
      </select></label>
    </div>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Agreement Date</span><input type="date" bind:value={form.agreement_date} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Maturity Date</span><input type="date" bind:value={form.maturity_date} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <div class="grid grid-cols-3 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Institution</span><input bind:value={form.institution} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Contact Person</span><input bind:value={form.contact_person} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Contact Email</span><input type="email" bind:value={form.contact_email} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Notes</span><textarea bind:value={form.notes} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <div class="flex justify-end gap-2 pt-2">
      <button type="button" onclick={() => (createOpen = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      {#if isDev}<button type="button" onclick={devFill} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
      <button type="submit" disabled={saving} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{saving ? "Saving..." : "Add Source"}</button>
    </div>
  </form>
</DrawerShell>

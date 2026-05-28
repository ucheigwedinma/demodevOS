<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { useAutoRefresh } from "$lib/realtime.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DrawerShell from "$lib/components/DrawerShell.svelte";
  import type {
    ContractListItem,
    ContractDetail,
    ContractSummary,
    ContractType,
    ContractStatus,
    PaginatedResponse,
    ProjectListItem,
  } from "$lib/types";

  let contracts = $state<ContractListItem[]>([]);
  let summary = $state<ContractSummary | null>(null);
  let loading = $state(true);
  let projects = $state<ProjectListItem[]>([]);
  let projectFilter = $state("");
  let typeFilter = $state("");
  let statusFilter = $state("");
  let searchInput = $state("");
  let searchQuery = $state("");
  let searchTimeout: ReturnType<typeof setTimeout> | undefined;

  let detailOpen = $state(false);
  let detail = $state<ContractDetail | null>(null);
  let detailLoading = $state(false);
  let detailTab = $state<"overview" | "terms" | "sla" | "amendments" | "clauses">("overview");

  let createOpen = $state(false);
  let saving = $state(false);
  let form = $state(defaultForm());

  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  function defaultForm() {
    return {
      vendor: "", project: "", title: "",
      contract_type: "construction" as ContractType,
      original_value: "", currency: "NGN",
      effective_date: "", expiry_date: "",
      is_price_locked: false,
      payment_terms_summary: "", advance_payment_pct: "0", retention_pct: "5",
      defects_liability_months: "12",
      scope_of_work: "", governing_law: "Laws of the Federal Republic of Nigeria",
      notes: "",
    };
  }

  function devFill() {
    form = {
      ...form,
      title: "Main Shell & Core Works — Phase 1",
      contract_type: "construction",
      original_value: "1200000000",
      currency: "NGN",
      effective_date: "2026-04-01",
      expiry_date: "2028-03-31",
      is_price_locked: true,
      payment_terms_summary: "Net 30, 5% retention, 10% advance on mobilization",
      advance_payment_pct: "10",
      retention_pct: "5",
      defects_liability_months: "12",
      scope_of_work: "Complete substructure and superstructure works for Tower A Phase 1 including piling, concrete frame, blockwork, and waterproofing. Excludes MEP, finishing trades, and external works.",
      governing_law: "Laws of the Federal Republic of Nigeria",
      notes: "Framework agreement with JBN. Pricing locked for 24 months with CPI-linked escalation clause capped at 5% per annum.",
    };
  }

  async function fetchData() {
    loading = true;
    try {
      const params: Record<string, string> = { page_size: "100" };
      if (searchQuery) params.search = searchQuery;
      if (projectFilter) params.project = projectFilter;
      if (typeFilter) params.contract_type = typeFilter;
      if (statusFilter) params.status = statusFilter;
      const [res, sumRes, projRes] = await Promise.all([
        api.get<PaginatedResponse<ContractListItem>>("/procurement/contracts/", params),
        api.get<ContractSummary>("/procurement/contracts/summary/"),
        projects.length === 0 ? api.get<PaginatedResponse<ProjectListItem>>("/projects/", { page_size: "200", ordering: "name" }) : Promise.resolve(null),
      ]);
      contracts = res.results;
      summary = sumRes;
      if (projRes) projects = projRes.results;
    } catch { contracts = []; }
    loading = false;
  }

  $effect(() => { void searchQuery; void projectFilter; void typeFilter; void statusFilter; fetchData(); });

  function onSearchInput(e: Event) {
    searchInput = (e.target as HTMLInputElement).value;
    if (searchTimeout) clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => { searchQuery = searchInput.trim(); }, 250);
  }

  async function openDetail(id: number) {
    detailOpen = true;
    detailLoading = true;
    detailTab = "overview";
    try { detail = await api.get<ContractDetail>(`/procurement/contracts/${id}/`); } catch { detail = null; }
    detailLoading = false;
  }

  async function saveContract(e: Event) {
    e.preventDefault();
    if (!form.vendor || !form.title.trim()) { toast.error("Required", "Vendor and title are required."); return; }
    saving = true;
    try {
      await api.post("/procurement/contracts/", {
        ...form,
        vendor: Number(form.vendor),
        project: form.project ? Number(form.project) : null,
        original_value: form.original_value || "0",
        effective_date: form.effective_date || null,
        expiry_date: form.expiry_date || null,
        defects_liability_months: Number(form.defects_liability_months) || 12,
      });
      toast.success("Contract created", `"${form.title}" registered.`);
      createOpen = false;
      form = defaultForm();
      await fetchData();
    } catch (error) {
      const msg = error instanceof ApiError ? (Object.values(error.fieldErrors)[0]?.[0] ?? "Failed.") : "Failed.";
      toast.error("Save failed", msg);
    } finally { saving = false; }
  }

  function fmtC(v: string | number | null | undefined): string { if (!v || v === "0.00" || v === "0") return "--"; return currency.formatCompact(v); }
  function fmtCFull(v: string | number | null | undefined): string { if (!v || v === "0.00" || v === "0") return "--"; return currency.format(v); }
  function fmtDate(v: string | null | undefined): string { if (!v) return "--"; const d = new Date(v); return Number.isNaN(d.getTime()) ? "--" : d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }); }

  useAutoRefresh("Contract", fetchData);
</script>

<div class="space-y-6">
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">Procurement</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-900">Contracts & Agreements</h1>
      <p class="mt-1 text-sm text-neutral-500">Long-term contracts, framework agreements, pricing locks, and SLA terms.</p>
    </div>
    <button onclick={() => { form = defaultForm(); createOpen = true; }} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800">+ New Contract</button>
  </div>

  <!-- Summary KPIs -->
  {#if summary}
    <div class="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
      <div class="rounded-xl border border-emerald-100 bg-emerald-50 p-3.5 text-center">
        <p class="text-[9px] font-semibold uppercase tracking-wider text-emerald-700">Active</p>
        <p class="mt-1 text-xl font-bold text-emerald-900 tabular-nums">{summary.active}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white p-3.5 text-center">
        <p class="text-[9px] font-semibold uppercase tracking-wider text-neutral-500">Total Value</p>
        <p class="mt-1 text-lg font-bold text-neutral-900 tabular-nums">{fmtC(summary.total_value)}</p>
      </div>
      <div class="rounded-xl border border-blue-100 bg-blue-50 p-3.5 text-center">
        <p class="text-[9px] font-semibold uppercase tracking-wider text-blue-700">Draft/Negotiation</p>
        <p class="mt-1 text-xl font-bold text-blue-900 tabular-nums">{summary.draft_negotiation}</p>
      </div>
      <div class="rounded-xl border border-amber-100 bg-amber-50 p-3.5 text-center">
        <p class="text-[9px] font-semibold uppercase tracking-wider text-amber-700">Expiring (30d)</p>
        <p class="mt-1 text-xl font-bold text-amber-900 tabular-nums">{summary.expiring_30d}</p>
      </div>
      <div class="rounded-xl border border-indigo-100 bg-indigo-50 p-3.5 text-center">
        <p class="text-[9px] font-semibold uppercase tracking-wider text-indigo-700">Framework</p>
        <p class="mt-1 text-xl font-bold text-indigo-900 tabular-nums">{summary.framework_agreements}</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-3.5 text-center">
        <p class="text-[9px] font-semibold uppercase tracking-wider text-neutral-500">Price Locked</p>
        <p class="mt-1 text-xl font-bold text-neutral-700 tabular-nums">{summary.price_locked}</p>
      </div>
    </div>
  {/if}

  <!-- Filters -->
  <div class="grid grid-cols-1 gap-3 xl:grid-cols-4">
    <input type="text" value={searchInput} oninput={onSearchInput} placeholder="Search contract #, title, vendor..." class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
    <select bind:value={projectFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Projects</option>
      {#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}
    </select>
    <select bind:value={typeFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Types</option>
      <option value="construction">Construction</option><option value="supply">Supply</option><option value="service">Service</option>
      <option value="framework">Framework</option><option value="consultancy">Consultancy</option><option value="subcontract">Subcontract</option><option value="other">Other</option>
    </select>
    <select bind:value={statusFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Statuses</option>
      <option value="draft">Draft</option><option value="negotiation">Negotiation</option><option value="pending_approval">Pending Approval</option>
      <option value="executed">Executed</option><option value="suspended">Suspended</option><option value="completed">Completed</option><option value="terminated">Terminated</option><option value="expired">Expired</option>
    </select>
  </div>

  <!-- Contracts Table -->
  {#if loading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if contracts.length === 0}
    <div class="rounded-2xl border border-neutral-200 bg-white px-6 py-14 text-center"><p class="text-sm text-neutral-500">No contracts found.</p></div>
  {:else}
    <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
      <div class="overflow-x-auto">
        <table class="min-w-[1000px] w-full">
          <thead class="bg-neutral-50 border-b border-neutral-200">
            <tr>
              <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Contract</th>
              <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Vendor</th>
              <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Type</th>
              <th class="px-4 py-3 text-center text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Status</th>
              <th class="px-4 py-3 text-right text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Value</th>
              <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Effective</th>
              <th class="px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Expiry</th>
              <th class="px-4 py-3 text-center text-[10px] font-semibold uppercase tracking-wider text-neutral-500">AMD</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each contracts as c}
              <tr class="hover:bg-neutral-50 cursor-pointer {c.days_until_expiry !== null && c.days_until_expiry <= 30 && c.days_until_expiry > 0 ? 'bg-amber-50/30' : ''}" onclick={() => openDetail(c.id)}>
                <td class="px-4 py-3">
                  <p class="text-sm font-semibold text-neutral-900">{c.contract_number}</p>
                  <p class="text-xs text-neutral-500 mt-0.5 max-w-[200px] truncate">{c.title}</p>
                  {#if c.is_price_locked}<span class="text-[8px] font-bold text-indigo-600 bg-indigo-50 px-1 py-0.5 rounded">PRICE LOCKED</span>{/if}
                </td>
                <td class="px-4 py-3 text-sm text-neutral-700">{c.vendor_name}</td>
                <td class="px-4 py-3 text-xs text-neutral-600">{c.contract_type_display}</td>
                <td class="px-4 py-3 text-center"><StatusBadge status={c.status} /></td>
                <td class="px-4 py-3 text-right">
                  <p class="text-sm font-bold tabular-nums text-neutral-900">{fmtC(c.revised_value && c.revised_value !== c.original_value ? c.revised_value : c.original_value)}</p>
                  {#if c.revised_value && c.revised_value !== c.original_value}<p class="text-[9px] text-neutral-400 line-through">{fmtC(c.original_value)}</p>{/if}
                </td>
                <td class="px-4 py-3 text-sm text-neutral-600">{fmtDate(c.effective_date)}</td>
                <td class="px-4 py-3 text-sm {c.days_until_expiry !== null && c.days_until_expiry <= 30 ? 'text-amber-600 font-semibold' : 'text-neutral-600'}">
                  {fmtDate(c.expiry_date)}
                  {#if c.days_until_expiry !== null && c.days_until_expiry > 0 && c.days_until_expiry <= 30}<span class="text-[9px]"> ({c.days_until_expiry}d)</span>{/if}
                </td>
                <td class="px-4 py-3 text-center text-sm text-neutral-600">{c.amendment_count}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>
  {/if}
</div>

<!-- ═══════════ DETAIL DRAWER ═══════════ -->
<DrawerShell open={detailOpen} title="Contract Detail" subtitle={detail ? `${detail.contract_number} — ${detail.title}` : ""} width="max-w-2xl" onclose={() => (detailOpen = false)}>
  {#if detailLoading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if detail}
    <div class="border-b border-neutral-200">
      <div class="flex gap-1 px-6 pt-4 overflow-x-auto">
        {#each [["overview", "Overview"], ["terms", "Terms"], ["sla", "SLA"], ["amendments", "Amendments"], ["clauses", "Clauses"]] as [key, label]}
          <button onclick={() => (detailTab = key as typeof detailTab)} class="shrink-0 rounded-t-lg px-3 py-2 text-xs font-semibold transition-colors {detailTab === key ? 'bg-white text-neutral-900 border border-b-white border-neutral-200 -mb-px' : 'text-neutral-500 hover:text-neutral-700'}">{label}</button>
        {/each}
      </div>
    </div>

    <div class="p-6 space-y-5">
      {#if detailTab === "overview"}
        <div class="flex items-center gap-3">
          <StatusBadge status={detail.status} />
          <span class="text-xs text-neutral-500">{detail.contract_type_display}</span>
          {#if detail.is_price_locked}<span class="text-[9px] font-bold text-indigo-600 bg-indigo-50 rounded px-1.5 py-0.5">PRICE LOCKED</span>{/if}
          {#if detail.is_active}<span class="text-[9px] font-bold text-emerald-600 bg-emerald-50 rounded px-1.5 py-0.5">ACTIVE</span>{/if}
        </div>

        <div class="grid grid-cols-3 gap-3">
          <div class="rounded-lg border border-neutral-200 p-3 text-center"><p class="text-[9px] font-semibold uppercase text-neutral-400">Original Value</p><p class="mt-1 text-lg font-bold text-neutral-900 tabular-nums">{fmtC(detail.original_value)}</p></div>
          <div class="rounded-lg border border-blue-100 bg-blue-50 p-3 text-center"><p class="text-[9px] font-semibold uppercase text-blue-600">Revised Value</p><p class="mt-1 text-lg font-bold text-blue-900 tabular-nums">{fmtC(detail.revised_value)}</p></div>
          <div class="rounded-lg border border-neutral-200 p-3 text-center"><p class="text-[9px] font-semibold uppercase text-neutral-400">Amendments</p><p class="mt-1 text-lg font-bold text-neutral-900 tabular-nums">{fmtC(detail.total_amendments_value)}</p></div>
        </div>

        <div class="grid grid-cols-2 gap-3 text-sm">
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Vendor</p><p class="text-neutral-900 font-medium">{detail.vendor_name}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Project</p><p class="text-neutral-900">{detail.project_name || "--"}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Effective</p><p class="text-neutral-900">{fmtDate(detail.effective_date)}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Expiry</p><p class="{detail.days_until_expiry !== null && detail.days_until_expiry <= 30 ? 'text-amber-600 font-semibold' : 'text-neutral-900'}">{fmtDate(detail.expiry_date)} {detail.days_until_expiry !== null ? `(${detail.days_until_expiry}d)` : ""}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Signed By (Org)</p><p class="text-neutral-900">{detail.signed_by_org || "--"}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Signed By (Vendor)</p><p class="text-neutral-900">{detail.signed_by_vendor || "--"}</p></div>
        </div>

        {#if detail.scope_of_work}<div><p class="text-[10px] font-semibold uppercase text-neutral-400 mb-1">Scope of Work</p><p class="text-sm text-neutral-700 whitespace-pre-line">{detail.scope_of_work}</p></div>{/if}
        {#if detail.exclusions}<div><p class="text-[10px] font-semibold uppercase text-neutral-400 mb-1">Exclusions</p><p class="text-sm text-neutral-700 whitespace-pre-line">{detail.exclusions}</p></div>{/if}

        <!-- Locked Rates -->
        {#if detail.locked_rates && detail.locked_rates.length > 0}
          <div>
            <p class="text-[10px] font-semibold uppercase text-indigo-600 mb-2">Locked Rates</p>
            <table class="w-full"><thead class="bg-neutral-50"><tr>
              <th class="px-3 py-1.5 text-left text-[10px] font-semibold uppercase text-neutral-500">Item</th>
              <th class="px-3 py-1.5 text-left text-[10px] font-semibold uppercase text-neutral-500">Unit</th>
              <th class="px-3 py-1.5 text-right text-[10px] font-semibold uppercase text-neutral-500">Rate</th>
              <th class="px-3 py-1.5 text-left text-[10px] font-semibold uppercase text-neutral-500">Valid Until</th>
            </tr></thead><tbody class="divide-y divide-neutral-100">
              {#each detail.locked_rates as lr}
                <tr><td class="px-3 py-1.5 text-sm text-neutral-900">{lr.item}</td><td class="px-3 py-1.5 text-xs text-neutral-600">{lr.unit}</td><td class="px-3 py-1.5 text-right text-sm font-semibold tabular-nums text-neutral-900">{fmtCFull(lr.rate)}</td><td class="px-3 py-1.5 text-sm text-neutral-600">{fmtDate(lr.valid_until)}</td></tr>
              {/each}
            </tbody></table>
          </div>
        {/if}

      {:else if detailTab === "terms"}
        <div class="grid grid-cols-2 gap-3 text-sm">
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Payment Terms</p><p class="text-neutral-900">{detail.payment_terms_summary || "--"}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Advance Payment</p><p class="text-neutral-900">{detail.advance_payment_pct}%</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Retention</p><p class="text-neutral-900">{detail.retention_pct}%</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Defects Liability</p><p class="text-neutral-900">{detail.defects_liability_months} months</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Performance Bond</p><p class="text-neutral-900">{detail.performance_bond_pct}%</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Insurance Required</p><p class="text-neutral-900">{detail.insurance_required ? `Yes (min ${fmtC(detail.insurance_minimum_cover)})` : "No"}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Liquidated Damages</p><p class="text-neutral-900">{detail.liquidated_damages_rate}% per day (capped at {detail.liquidated_damages_cap_pct}%)</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Notice Period</p><p class="text-neutral-900">{detail.notice_period_days} days</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Governing Law</p><p class="text-neutral-900">{detail.governing_law || "--"}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Dispute Resolution</p><p class="text-neutral-900">{detail.dispute_resolution || "--"}</p></div>
        </div>
        {#if detail.price_escalation_clause}<div class="rounded-lg border border-indigo-200 bg-indigo-50 p-3"><p class="text-[10px] font-semibold uppercase text-indigo-700 mb-1">Price Escalation Clause</p><p class="text-sm text-indigo-900">{detail.price_escalation_clause}</p></div>{/if}

      {:else if detailTab === "sla"}
        <div class="grid grid-cols-2 gap-3 text-sm">
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Response Time</p><p class="text-neutral-900">{detail.sla_response_hours ? `${detail.sla_response_hours} hours` : "--"}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Resolution Time</p><p class="text-neutral-900">{detail.sla_resolution_hours ? `${detail.sla_resolution_hours} hours` : "--"}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Uptime Guarantee</p><p class="text-neutral-900">{detail.sla_uptime_pct ? `${detail.sla_uptime_pct}%` : "--"}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Penalty per Breach</p><p class="text-neutral-900">{fmtCFull(detail.sla_penalty_per_breach)}</p></div>
        </div>
        {#if detail.sla_notes}<div><p class="text-[10px] font-semibold uppercase text-neutral-400 mb-1">SLA Notes</p><p class="text-sm text-neutral-700 whitespace-pre-line">{detail.sla_notes}</p></div>{/if}

      {:else if detailTab === "amendments"}
        {#if detail.amendments.length === 0}
          <p class="text-sm text-neutral-400 text-center py-6">No amendments recorded.</p>
        {:else}
          <div class="space-y-2">
            {#each detail.amendments as a}
              <div class="rounded-lg border border-neutral-200 p-3">
                <div class="flex items-center justify-between mb-1">
                  <div class="flex items-center gap-2">
                    <span class="text-sm font-bold text-neutral-900">{a.amendment_number}</span>
                    <span class="text-[9px] font-semibold rounded-full px-2 py-0.5 bg-neutral-100 text-neutral-600">{a.amendment_type_display}</span>
                    <StatusBadge status={a.status} />
                  </div>
                  <span class="text-sm font-semibold tabular-nums {Number(a.value_change) >= 0 ? 'text-emerald-600' : 'text-red-600'}">{Number(a.value_change) >= 0 ? "+" : ""}{fmtCFull(a.value_change)}</span>
                </div>
                <p class="text-sm text-neutral-700">{a.title}</p>
                {#if a.time_extension_days}<p class="text-xs text-blue-600 mt-1">+{a.time_extension_days} days extension</p>{/if}
                {#if a.reason}<p class="text-xs text-neutral-500 mt-1">{a.reason}</p>{/if}
              </div>
            {/each}
          </div>
        {/if}

      {:else if detailTab === "clauses"}
        {#if detail.clauses.length === 0}
          <p class="text-sm text-neutral-400 text-center py-6">No clauses defined.</p>
        {:else}
          <div class="space-y-2">
            {#each detail.clauses as cl}
              <div class="rounded-lg border border-neutral-200 p-3 {cl.is_critical ? 'border-l-4 border-l-red-500' : ''}">
                <div class="flex items-center justify-between mb-1">
                  <div class="flex items-center gap-2">
                    <span class="text-xs font-bold text-neutral-700">{cl.clause_number}</span>
                    <p class="text-sm font-medium text-neutral-900">{cl.title}</p>
                  </div>
                  <span class="text-[9px] font-semibold rounded-full px-2 py-0.5 bg-neutral-100 text-neutral-600">{cl.category_display}</span>
                </div>
                <p class="text-xs text-neutral-600 whitespace-pre-line">{cl.body}</p>
                {#if cl.is_critical}<span class="text-[8px] font-bold text-red-600 mt-1 inline-block">CRITICAL CLAUSE</span>{/if}
              </div>
            {/each}
          </div>
        {/if}
      {/if}
    </div>
  {/if}
</DrawerShell>

<!-- ═══════════ CREATE DRAWER ═══════════ -->
<DrawerShell open={createOpen} title="New Contract" subtitle="Register a formal agreement" width="max-w-xl" onclose={() => (createOpen = false)}>
  <form onsubmit={saveContract} class="p-6 space-y-4">
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Vendor *</span><input type="number" bind:value={form.vendor} placeholder="Vendor ID" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Project</span><select bind:value={form.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"><option value="">None</option>{#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}</select></label>
    </div>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Title *</span><input bind:value={form.title} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Type</span><select bind:value={form.contract_type} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="construction">Construction</option><option value="supply">Supply</option><option value="service">Service</option>
        <option value="framework">Framework</option><option value="consultancy">Consultancy</option><option value="subcontract">Subcontract</option><option value="other">Other</option>
      </select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Value</span><input type="number" step="0.01" bind:value={form.original_value} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Effective Date</span><input type="date" bind:value={form.effective_date} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Expiry Date</span><input type="date" bind:value={form.expiry_date} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <div class="grid grid-cols-3 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Advance %</span><input type="number" step="0.01" bind:value={form.advance_payment_pct} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Retention %</span><input type="number" step="0.01" bind:value={form.retention_pct} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label class="flex items-center gap-2 pt-6"><input type="checkbox" bind:checked={form.is_price_locked} class="h-4 w-4 rounded border-neutral-300" /><span class="text-xs font-semibold text-neutral-600">Price Locked</span></label>
    </div>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Scope of Work</span><textarea bind:value={form.scope_of_work} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Notes</span><textarea bind:value={form.notes} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <div class="flex justify-end gap-2 pt-2">
      <button type="button" onclick={() => (createOpen = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      {#if isDev}<button type="button" onclick={devFill} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
      <button type="submit" disabled={saving} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{saving ? "Saving..." : "Create Contract"}</button>
    </div>
  </form>
</DrawerShell>

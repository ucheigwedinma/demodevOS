<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DrawerShell from "$lib/components/DrawerShell.svelte";
  import type {
    ProcurementPlanListItem,
    ProcurementPlanDetail,
    ProcurementPackageListItem,
    ProcurementPackageDetail,
    PaginatedResponse,
    ProjectListItem,
  } from "$lib/types";

  let plans = $state<ProcurementPlanListItem[]>([]);
  let loading = $state(true);
  let projects = $state<ProjectListItem[]>([]);
  let projectFilter = $state("");

  // Plan detail
  let planDetailOpen = $state(false);
  let planDetail = $state<ProcurementPlanDetail | null>(null);
  let planDetailLoading = $state(false);
  let planDetailAllocated = $derived(
    planDetail ? planDetail.packages.reduce((sum, pkg) => sum + Number(pkg.estimated_budget || 0), 0) : 0,
  );
  let planDetailContracted = $derived(
    planDetail ? planDetail.packages.reduce((sum, pkg) => sum + Number(pkg.contract_value || 0), 0) : 0,
  );

  // Package detail
  let pkgDetailOpen = $state(false);
  let pkgDetail = $state<ProcurementPackageDetail | null>(null);
  let pkgDetailLoading = $state(false);

  // Create plan
  let createOpen = $state(false);
  let saving = $state(false);
  let form = $state({ project: "", strategy: "traditional", total_budget: "", contingency_pct: "5", notes: "" });

  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  function devFill() {
    form = {
      project: form.project || (projects.length > 0 ? String(projects[0].id) : ""),
      strategy: "traditional",
      total_budget: "2500000000",
      contingency_pct: "5",
      notes: "Traditional contracting strategy with separate packages for piling, main shell/core, MEP, and finishing trades. Prequalification required for all packages above ₦100M.",
    };
  }

  async function fetchData() {
    loading = true;
    try {
      const params: Record<string, string> = { page_size: "100" };
      if (projectFilter) params.project = projectFilter;
      const [res, projRes] = await Promise.all([
        api.get<PaginatedResponse<ProcurementPlanListItem>>("/projects/procurement-plans/", params),
        projects.length === 0 ? api.get<PaginatedResponse<ProjectListItem>>("/projects/", { page_size: "200", ordering: "name" }) : Promise.resolve(null),
      ]);
      plans = res.results;
      if (projRes) projects = projRes.results;
    } catch { plans = []; }
    loading = false;
  }

  $effect(() => { void projectFilter; fetchData(); });

  async function openPlanDetail(id: number) {
    planDetailOpen = true;
    planDetailLoading = true;
    try { planDetail = await api.get<ProcurementPlanDetail>(`/projects/procurement-plans/${id}/`); } catch { planDetail = null; }
    planDetailLoading = false;
  }

  async function openPackageDetail(planId: number, pkgId: number) {
    pkgDetailOpen = true;
    pkgDetailLoading = true;
    try { pkgDetail = await api.get<ProcurementPackageDetail>(`/projects/procurement-plans/${planId}/packages/${pkgId}/`); } catch { pkgDetail = null; }
    pkgDetailLoading = false;
  }

  async function savePlan(e: Event) {
    e.preventDefault();
    if (!form.project) { toast.error("Required", "Select a project."); return; }
    saving = true;
    try {
      await api.post("/projects/procurement-plans/", {
        ...form,
        project: Number(form.project),
        total_budget: form.total_budget || "0",
      });
      toast.success("Plan created", "Procurement plan registered.");
      createOpen = false;
      form = { project: "", strategy: "traditional", total_budget: "", contingency_pct: "5", notes: "" };
      await fetchData();
    } catch (error) {
      const msg = error instanceof ApiError ? (Object.values(error.fieldErrors)[0]?.[0] ?? "Save failed.") : "Save failed.";
      toast.error("Save failed", msg);
    } finally { saving = false; }
  }

  function fmtC(v: string | number | null | undefined): string { if (!v || v === "0.00" || v === "0") return "--"; return currency.formatCompact(v); }
  function fmtCFull(v: string | number | null | undefined): string { if (!v || v === "0.00" || v === "0") return "--"; return currency.format(v); }
  function fmtDate(v: string | null | undefined): string { if (!v) return "--"; const d = new Date(v); return Number.isNaN(d.getTime()) ? "--" : d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }); }

  function pkgStatusColor(status: string, isBehind: boolean): string {
    if (isBehind) return "bg-amber-100 text-amber-800";
    if (status === "signed") return "bg-emerald-100 text-emerald-800";
    if (status === "awarded") return "bg-emerald-50 text-emerald-700";
    if (status === "tendering" || status === "evaluation") return "bg-blue-100 text-blue-800";
    if (status === "cancelled") return "bg-neutral-200 text-neutral-500";
    return "bg-neutral-100 text-neutral-600";
  }
</script>

<div class="space-y-6">
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">Projects</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-900">Procurement Planning</h1>
      <p class="mt-1 text-sm text-neutral-500">Contracting strategy, tender pipeline, package breakdown, and evaluation matrix.</p>
    </div>
    <div class="flex items-center gap-2">
      <select bind:value={projectFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
        <option value="">All Projects</option>
        {#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}
      </select>
      <button onclick={() => { form = { project: "", strategy: "traditional", total_budget: "", contingency_pct: "5", notes: "" }; createOpen = true; }} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800">+ New Plan</button>
    </div>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if plans.length === 0}
    <div class="rounded-2xl border border-neutral-200 bg-white px-6 py-14 text-center"><p class="text-sm text-neutral-500">No procurement plans found.</p></div>
  {:else}
    <div class="space-y-4">
      {#each plans as plan}
        <button class="w-full text-left rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow cursor-pointer" onclick={() => openPlanDetail(plan.id)}>
          <div class="flex items-start justify-between mb-3">
            <div>
              <p class="text-sm font-semibold text-neutral-900">{plan.project_name}</p>
              <p class="text-xs text-neutral-500 mt-0.5">{plan.strategy_display} — {plan.package_count} package{plan.package_count !== 1 ? "s" : ""}</p>
            </div>
            <div class="text-right">
              <p class="text-[9px] text-neutral-400">Total Budget</p>
              <p class="text-sm font-bold text-neutral-900 tabular-nums">{fmtC(plan.total_budget)}</p>
            </div>
          </div>
          <div class="grid grid-cols-3 gap-4">
            <div><p class="text-[9px] text-neutral-400">Allocated</p><p class="text-sm font-semibold text-neutral-900 tabular-nums">{fmtC(plan.total_allocated)}</p></div>
            <div><p class="text-[9px] text-neutral-400">Contracted</p><p class="text-sm font-semibold text-emerald-600 tabular-nums">{fmtC(plan.total_contracted)}</p></div>
            <div><p class="text-[9px] text-neutral-400">Contingency</p><p class="text-sm font-semibold text-amber-600 tabular-nums">{plan.contingency_pct}%</p></div>
          </div>
        </button>
      {/each}
    </div>
  {/if}
</div>

<!-- ═══════════ PLAN DETAIL DRAWER ═══════════ -->
<DrawerShell open={planDetailOpen} title="Procurement Plan" subtitle={planDetail?.project_name ?? ""} width="max-w-2xl" onclose={() => (planDetailOpen = false)}>
  {#if planDetailLoading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if planDetail}
    <div class="p-6 space-y-5">
      <div class="flex items-center gap-3">
        <span class="text-xs font-semibold text-neutral-600 bg-neutral-100 rounded-full px-3 py-1">{planDetail.strategy_display}</span>
        <span class="text-xs text-neutral-500">Contingency: {planDetail.contingency_pct}%</span>
      </div>

      <div class="grid grid-cols-3 gap-3">
        <div class="rounded-lg border border-neutral-200 p-3 text-center">
          <p class="text-[9px] font-semibold uppercase text-neutral-400">Total Budget</p>
          <p class="mt-1 text-lg font-bold text-neutral-900 tabular-nums">{fmtC(planDetail.total_budget)}</p>
        </div>
        <div class="rounded-lg border border-blue-100 bg-blue-50 p-3 text-center">
          <p class="text-[9px] font-semibold uppercase text-blue-600">Allocated</p>
          <p class="mt-1 text-lg font-bold text-blue-900 tabular-nums">{fmtC(planDetailAllocated)}</p>
        </div>
        <div class="rounded-lg border border-emerald-100 bg-emerald-50 p-3 text-center">
          <p class="text-[9px] font-semibold uppercase text-emerald-700">Contracted</p>
          <p class="mt-1 text-lg font-bold text-emerald-900 tabular-nums">{fmtC(planDetailContracted)}</p>
        </div>
      </div>

      {#if planDetail.notes}<div><p class="text-[10px] font-semibold uppercase text-neutral-400 mb-1">Strategy Notes</p><p class="text-sm text-neutral-700 whitespace-pre-line">{planDetail.notes}</p></div>{/if}

      <!-- Packages -->
      <div>
        <p class="text-[10px] font-semibold uppercase text-neutral-400 mb-2">Contract Packages ({planDetail.packages.length})</p>
        {#if planDetail.packages.length === 0}
          <p class="text-sm text-neutral-400 py-3">No packages defined yet.</p>
        {:else}
          <div class="space-y-2">
            {#each planDetail.packages as pkg}
              <button class="w-full text-left rounded-lg border border-neutral-200 p-3 hover:bg-neutral-50 transition-colors {pkg.is_behind_schedule ? 'border-amber-200 bg-amber-50/30' : ''}" onclick={() => openPackageDetail(planDetail!.id, pkg.id)}>
                <div class="flex items-center justify-between mb-1.5">
                  <p class="text-sm font-medium text-neutral-900">{pkg.name}</p>
                  <span class="inline-block rounded-full px-2.5 py-0.5 text-[10px] font-semibold {pkgStatusColor(pkg.status, pkg.is_behind_schedule)}">
                    {pkg.is_behind_schedule ? "BEHIND" : pkg.status_display}
                  </span>
                </div>
                <div class="flex items-center gap-4 text-xs text-neutral-500">
                  <span>Est: <span class="font-semibold text-neutral-700">{fmtC(pkg.estimated_budget)}</span></span>
                  {#if pkg.contract_value && pkg.contract_value !== "0.00"}<span>Contract: <span class="font-semibold text-emerald-600">{fmtC(pkg.contract_value)}</span></span>{/if}
                  {#if pkg.awarded_to}<span>→ {pkg.awarded_to}</span>{/if}
                  <span>{pkg.bidder_count} bidder{pkg.bidder_count !== 1 ? "s" : ""}</span>
                </div>
                <!-- Timeline -->
                <div class="flex items-center gap-3 mt-2 text-[10px] text-neutral-400">
                  {#if pkg.rfp_issue_date}<span>RFP: {fmtDate(pkg.rfp_issue_date)}</span>{/if}
                  {#if pkg.tender_return_date}<span>Return: {fmtDate(pkg.tender_return_date)}</span>{/if}
                  {#if pkg.award_date}<span>Award: {fmtDate(pkg.award_date)}</span>{/if}
                </div>
              </button>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  {/if}
</DrawerShell>

<!-- ═══════════ PACKAGE DETAIL DRAWER ═══════════ -->
<DrawerShell open={pkgDetailOpen} title="Package Detail" subtitle={pkgDetail?.name ?? ""} width="max-w-2xl" onclose={() => (pkgDetailOpen = false)}>
  {#if pkgDetailLoading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if pkgDetail}
    <div class="p-6 space-y-5">
      <div class="flex items-center gap-3">
        <span class="inline-block rounded-full px-2.5 py-0.5 text-[10px] font-semibold {pkgStatusColor(pkgDetail.status, pkgDetail.is_behind_schedule)}">
          {pkgDetail.is_behind_schedule ? "BEHIND SCHEDULE" : pkgDetail.status_display}
        </span>
        {#if pkgDetail.awarded_to}<span class="text-xs text-neutral-500">Awarded to: <span class="font-semibold text-neutral-900">{pkgDetail.awarded_to}</span></span>{/if}
      </div>

      <div class="grid grid-cols-3 gap-3">
        <div class="rounded-lg border border-neutral-200 p-3 text-center">
          <p class="text-[9px] font-semibold uppercase text-neutral-400">Estimated</p>
          <p class="mt-1 text-lg font-bold text-neutral-900 tabular-nums">{fmtC(pkgDetail.estimated_budget)}</p>
        </div>
        <div class="rounded-lg border border-emerald-100 bg-emerald-50 p-3 text-center">
          <p class="text-[9px] font-semibold uppercase text-emerald-700">Contract Value</p>
          <p class="mt-1 text-lg font-bold text-emerald-900 tabular-nums">{fmtC(pkgDetail.contract_value)}</p>
        </div>
        <div class="rounded-lg border border-neutral-200 p-3 text-center">
          <p class="text-[9px] font-semibold uppercase text-neutral-400">Variance</p>
          <p class="mt-1 text-lg font-bold tabular-nums {Number(pkgDetail.budget_variance || 0) >= 0 ? 'text-emerald-600' : 'text-red-600'}">{fmtC(pkgDetail.budget_variance)}</p>
        </div>
      </div>

      <!-- Timeline -->
      <div class="grid grid-cols-3 gap-3 text-sm">
        <div><p class="text-[10px] font-semibold uppercase text-neutral-400">PQQ Issued</p><p class="text-neutral-900">{fmtDate(pkgDetail.pqq_issue_date)}</p></div>
        <div><p class="text-[10px] font-semibold uppercase text-neutral-400">RFP Issued</p><p class="text-neutral-900">{fmtDate(pkgDetail.rfp_issue_date)}</p></div>
        <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Tender Return</p><p class="text-neutral-900">{fmtDate(pkgDetail.tender_return_date)}</p></div>
        <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Evaluation End</p><p class="text-neutral-900">{fmtDate(pkgDetail.evaluation_end_date)}</p></div>
        <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Award Date</p><p class="text-neutral-900">{fmtDate(pkgDetail.award_date)}</p></div>
        <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Contract Start</p><p class="text-neutral-900">{fmtDate(pkgDetail.contract_start_date)}</p></div>
      </div>

      {#if pkgDetail.award_justification}<div class="rounded-lg border border-emerald-200 bg-emerald-50 p-3"><p class="text-[10px] font-semibold uppercase text-emerald-700 mb-1">Award Justification</p><p class="text-sm text-emerald-900 whitespace-pre-line">{pkgDetail.award_justification}</p></div>{/if}

      <!-- Bidders / Evaluation Matrix -->
      <div>
        <p class="text-[10px] font-semibold uppercase text-neutral-400 mb-2">Tender Evaluation ({pkgDetail.bidders.length} bidders)</p>
        {#if pkgDetail.bidders.length === 0}
          <p class="text-sm text-neutral-400 py-3">No bidders recorded.</p>
        {:else}
          <div class="overflow-x-auto">
            <table class="w-full">
              <thead class="bg-neutral-50"><tr>
                <th class="px-3 py-2 text-left text-[10px] font-semibold uppercase text-neutral-500">Firm</th>
                <th class="px-3 py-2 text-right text-[10px] font-semibold uppercase text-neutral-500">Bid</th>
                <th class="px-3 py-2 text-center text-[10px] font-semibold uppercase text-neutral-500">Price</th>
                <th class="px-3 py-2 text-center text-[10px] font-semibold uppercase text-neutral-500">Tech</th>
                <th class="px-3 py-2 text-center text-[10px] font-semibold uppercase text-neutral-500">Time</th>
                <th class="px-3 py-2 text-center text-[10px] font-semibold uppercase text-neutral-500">Safety</th>
                <th class="px-3 py-2 text-center text-[10px] font-semibold uppercase text-neutral-500">Total</th>
              </tr></thead>
              <tbody class="divide-y divide-neutral-100">
                {#each pkgDetail.bidders as b}
                  <tr class="{b.is_recommended ? 'bg-emerald-50/40' : ''}">
                    <td class="px-3 py-2">
                      <p class="text-sm font-medium text-neutral-900">{b.firm_name}</p>
                      {#if b.is_recommended}<span class="text-[9px] font-bold text-emerald-600">RECOMMENDED</span>{/if}
                      {#if b.specialization}<p class="text-[10px] text-neutral-400">{b.specialization}</p>{/if}
                    </td>
                    <td class="px-3 py-2 text-right text-sm font-semibold tabular-nums text-neutral-900">{fmtC(b.bid_amount)}</td>
                    <td class="px-3 py-2 text-center text-sm tabular-nums text-neutral-600">{b.score_price ?? "--"}</td>
                    <td class="px-3 py-2 text-center text-sm tabular-nums text-neutral-600">{b.score_technical ?? "--"}</td>
                    <td class="px-3 py-2 text-center text-sm tabular-nums text-neutral-600">{b.score_timeline ?? "--"}</td>
                    <td class="px-3 py-2 text-center text-sm tabular-nums text-neutral-600">{b.score_safety ?? "--"}</td>
                    <td class="px-3 py-2 text-center text-sm font-bold tabular-nums text-neutral-900">{b.total_score ?? "--"}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </div>

      {#if pkgDetail.notes}<div><p class="text-[10px] font-semibold uppercase text-neutral-400 mb-1">Notes</p><p class="text-sm text-neutral-700 whitespace-pre-line">{pkgDetail.notes}</p></div>{/if}
    </div>
  {/if}
</DrawerShell>

<!-- ═══════════ CREATE PLAN DRAWER ═══════════ -->
<DrawerShell open={createOpen} title="New Procurement Plan" subtitle="Define the contracting strategy" width="max-w-md" onclose={() => (createOpen = false)}>
  <form onsubmit={savePlan} class="p-6 space-y-4">
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Project *</span><select bind:value={form.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"><option value="">Select</option>{#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}</select></label>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Contracting Strategy</span><select bind:value={form.strategy} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
      <option value="design_build">Design & Build</option><option value="traditional">Traditional</option><option value="management">Management Contracting</option>
      <option value="construction_mgmt">Construction Management</option><option value="turnkey">Turnkey / EPC</option><option value="other">Other</option>
    </select></label>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Total Budget</span><input type="number" step="0.01" bind:value={form.total_budget} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Contingency %</span><input type="number" step="0.1" bind:value={form.contingency_pct} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Notes</span><textarea bind:value={form.notes} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <div class="flex justify-end gap-2 pt-2">
      <button type="button" onclick={() => (createOpen = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      {#if isDev}<button type="button" onclick={devFill} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
      <button type="submit" disabled={saving} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{saving ? "Saving..." : "Create Plan"}</button>
    </div>
  </form>
</DrawerShell>

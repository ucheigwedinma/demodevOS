<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DrawerShell from "$lib/components/DrawerShell.svelte";
  import type {
    ProjectCloseoutListItem,
    ProjectCloseoutDetail,
    PaginatedResponse,
    ProjectListItem,
  } from "$lib/types";

  let closeouts = $state<ProjectCloseoutListItem[]>([]);
  let loading = $state(true);
  let projects = $state<ProjectListItem[]>([]);
  let projectFilter = $state("");

  let detailOpen = $state(false);
  let detail = $state<ProjectCloseoutDetail | null>(null);
  let detailLoading = $state(false);
  let detailTab = $state<"checklist" | "accounts" | "snags" | "warranties">("checklist");

  let createOpen = $state(false);
  let saving = $state(false);
  let form = $state({ project: "", practical_completion_date: "", original_budget: "", notes: "" });

  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  function devFill() {
    form = {
      project: form.project || (projects.length > 0 ? String(projects[0].id) : ""),
      practical_completion_date: "2027-09-15",
      original_budget: "2500000000",
      notes: "Phase 1 practical completion achieved. Defects liability period commences. Final account negotiations in progress with Julius Berger.",
    };
  }

  async function fetchData() {
    loading = true;
    try {
      const params: Record<string, string> = { page_size: "100" };
      if (projectFilter) params.project = projectFilter;
      const [res, projRes] = await Promise.all([
        api.get<PaginatedResponse<ProjectCloseoutListItem>>("/projects/closeouts/", params),
        projects.length === 0 ? api.get<PaginatedResponse<ProjectListItem>>("/projects/", { page_size: "200", ordering: "name" }) : Promise.resolve(null),
      ]);
      closeouts = res.results;
      if (projRes) projects = projRes.results;
    } catch { closeouts = []; }
    loading = false;
  }

  $effect(() => { void projectFilter; fetchData(); });

  async function openDetail(id: number) {
    detailOpen = true;
    detailLoading = true;
    detailTab = "checklist";
    try { detail = await api.get<ProjectCloseoutDetail>(`/projects/closeouts/${id}/`); } catch { detail = null; }
    detailLoading = false;
  }

  async function saveCloseout(e: Event) {
    e.preventDefault();
    if (!form.project) { toast.error("Required", "Select a project."); return; }
    saving = true;
    try {
      await api.post("/projects/closeouts/", {
        project: Number(form.project),
        practical_completion_date: form.practical_completion_date || null,
        original_budget: form.original_budget || null,
        notes: form.notes,
      });
      toast.success("Closeout created", "Project closeout initiated.");
      createOpen = false;
      form = { project: "", practical_completion_date: "", original_budget: "", notes: "" };
      await fetchData();
    } catch (error) {
      const msg = error instanceof ApiError ? (Object.values(error.fieldErrors)[0]?.[0] ?? "Failed.") : "Failed.";
      toast.error("Save failed", msg);
    } finally { saving = false; }
  }

  function fmtDate(v: string | null | undefined): string { if (!v) return "--"; const d = new Date(v); return Number.isNaN(d.getTime()) ? "--" : d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }); }
  function fmtC(v: string | number | null | undefined): string { if (!v || v === "0.00" || v === "0") return "--"; return currency.formatCompact(v); }
  function fmtCFull(v: string | number | null | undefined): string { if (!v || v === "0.00" || v === "0") return "--"; return currency.format(v); }

  function snagColor(s: string): string {
    if (s === "open") return "bg-amber-100 text-amber-800";
    if (s === "in_progress") return "bg-blue-100 text-blue-800";
    if (s === "resolved") return "bg-emerald-100 text-emerald-800";
    return "bg-neutral-100 text-neutral-600";
  }
</script>

<div class="space-y-6">
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">Projects</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-900">Closeout</h1>
      <p class="mt-1 text-sm text-neutral-500">Final reconciliation, contract closure, snag lists, handover, and warranty tracking.</p>
    </div>
    <div class="flex items-center gap-2">
      <select bind:value={projectFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
        <option value="">All Projects</option>
        {#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}
      </select>
      <button onclick={() => { form = { project: "", practical_completion_date: "", original_budget: "", notes: "" }; createOpen = true; }} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800">+ Initiate Closeout</button>
    </div>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if closeouts.length === 0}
    <div class="rounded-2xl border border-neutral-200 bg-white px-6 py-14 text-center"><p class="text-sm text-neutral-500">No project closeouts initiated.</p></div>
  {:else}
    <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
      {#each closeouts as c}
        <button class="w-full text-left rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow cursor-pointer" onclick={() => openDetail(c.id)}>
          <div class="flex items-start justify-between mb-3">
            <div>
              <p class="text-sm font-semibold text-neutral-900">{c.project_name}</p>
              <p class="text-xs text-neutral-500 mt-0.5">PC: {fmtDate(c.practical_completion_date)}</p>
            </div>
            <StatusBadge status={c.status} />
          </div>
          <!-- Progress bar -->
          <div class="mb-3">
            <div class="flex items-center justify-between text-[10px] text-neutral-500 mb-1">
              <span>Closeout Progress</span>
              <span class="font-semibold {c.completion_pct === 100 ? 'text-emerald-600' : 'text-neutral-700'}">{c.completion_pct}%</span>
            </div>
            <div class="h-2 w-full rounded-full bg-neutral-100 overflow-hidden">
              <div class="h-full rounded-full transition-all {c.completion_pct === 100 ? 'bg-emerald-500' : 'bg-blue-500'}" style="width: {c.completion_pct}%"></div>
            </div>
          </div>
          <div class="grid grid-cols-3 gap-3 text-xs text-neutral-500">
            <div><span class="block text-[9px] text-neutral-400">Final Cost</span><span class="font-semibold text-neutral-700">{fmtC(c.final_project_cost)}</span></div>
            <div><span class="block text-[9px] text-neutral-400">Retention</span><span class="font-semibold text-neutral-700">{fmtC(c.retention_held)}</span></div>
            <div><span class="block text-[9px] text-neutral-400">Snags</span><span class="font-semibold {c.open_snag_count > 0 ? 'text-amber-600' : 'text-emerald-600'}">{c.open_snag_count} open / {c.snag_count}</span></div>
          </div>
        </button>
      {/each}
    </div>
  {/if}
</div>

<!-- ═══════════ DETAIL DRAWER ═══════════ -->
<DrawerShell open={detailOpen} title="Project Closeout" subtitle={detail ? detail.project_name : ""} width="max-w-2xl" onclose={() => (detailOpen = false)}>
  {#if detailLoading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if detail}
    <div class="border-b border-neutral-200">
      <div class="flex gap-1 px-6 pt-4">
        {#each [["checklist", "Checklist"], ["accounts", "Final Accounts"], ["snags", "Snag List"], ["warranties", "Warranties"]] as [key, label]}
          <button onclick={() => (detailTab = key as typeof detailTab)} class="rounded-t-lg px-4 py-2 text-xs font-semibold transition-colors {detailTab === key ? 'bg-white text-neutral-900 border border-b-white border-neutral-200 -mb-px' : 'text-neutral-500 hover:text-neutral-700'}">{label}</button>
        {/each}
      </div>
    </div>

    <div class="p-6 space-y-5">
      {#if detailTab === "checklist"}
        <div class="flex items-center gap-3 mb-3">
          <StatusBadge status={detail.status} />
          <span class="text-sm font-bold {detail.completion_pct === 100 ? 'text-emerald-600' : 'text-neutral-700'}">{detail.completion_pct}% Complete</span>
        </div>

        <!-- Checklist -->
        <div class="space-y-2">
          {#each [
            ["financial_reconciliation_done", "Financial Reconciliation"],
            ["contracts_closed", "Contracts & Consultants Closed"],
            ["handover_completed", "Handover Completed"],
            ["snags_resolved", "Snags Resolved"],
            ["documentation_archived", "Documentation Archived"],
            ["warranties_registered", "Warranties Registered"],
          ] as [key, label]}
            <div class="flex items-center gap-3 rounded-lg border border-neutral-200 p-3">
              {#if detail[key as keyof typeof detail]}
                <svg class="h-5 w-5 text-emerald-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>
              {:else}
                <span class="h-5 w-5 rounded-full border-2 border-neutral-300 shrink-0"></span>
              {/if}
              <p class="text-sm text-neutral-900">{label}</p>
            </div>
          {/each}
        </div>

        <!-- Financial summary -->
        <div class="grid grid-cols-2 gap-3 md:grid-cols-4">
          <div class="rounded-lg border border-neutral-200 p-3 text-center"><p class="text-[9px] font-semibold uppercase text-neutral-400">Original Budget</p><p class="mt-1 text-sm font-bold text-neutral-900 tabular-nums">{fmtC(detail.original_budget)}</p></div>
          <div class="rounded-lg border border-neutral-200 p-3 text-center"><p class="text-[9px] font-semibold uppercase text-neutral-400">Final Cost</p><p class="mt-1 text-sm font-bold text-neutral-900 tabular-nums">{fmtC(detail.final_project_cost)}</p></div>
          <div class="rounded-lg border border-neutral-200 p-3 text-center"><p class="text-[9px] font-semibold uppercase text-neutral-400">Variations</p><p class="mt-1 text-sm font-bold text-neutral-900 tabular-nums">{fmtC(detail.total_variations)}</p></div>
          <div class="rounded-lg border p-3 text-center {Number(detail.budget_variance || 0) >= 0 ? 'border-emerald-200 bg-emerald-50' : 'border-red-200 bg-red-50'}"><p class="text-[9px] font-semibold uppercase {Number(detail.budget_variance || 0) >= 0 ? 'text-emerald-700' : 'text-red-700'}">Variance</p><p class="mt-1 text-sm font-bold tabular-nums {Number(detail.budget_variance || 0) >= 0 ? 'text-emerald-900' : 'text-red-900'}">{fmtC(detail.budget_variance)}</p></div>
        </div>

        <div class="grid grid-cols-2 gap-3 text-sm">
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Practical Completion</p><p class="text-neutral-900">{fmtDate(detail.practical_completion_date)}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Final Completion</p><p class="text-neutral-900">{fmtDate(detail.final_completion_date)}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Retention Held</p><p class="text-neutral-900">{fmtC(detail.retention_held)}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Retention Released</p><p class="text-neutral-900">{fmtC(detail.retention_released)} {detail.retention_release_date ? `(${fmtDate(detail.retention_release_date)})` : ""}</p></div>
        </div>

        {#if detail.notes}<div><p class="text-[10px] font-semibold uppercase text-neutral-400 mb-1">Notes</p><p class="text-sm text-neutral-700 whitespace-pre-line">{detail.notes}</p></div>{/if}

      {:else if detailTab === "accounts"}
        {#if detail.final_accounts.length === 0}
          <p class="text-sm text-neutral-400 text-center py-6">No final accounts recorded.</p>
        {:else}
          <div class="overflow-x-auto">
            <table class="w-full">
              <thead class="bg-neutral-50"><tr>
                <th class="px-3 py-2 text-left text-[10px] font-semibold uppercase text-neutral-500">Contractor</th>
                <th class="px-3 py-2 text-right text-[10px] font-semibold uppercase text-neutral-500">Original</th>
                <th class="px-3 py-2 text-right text-[10px] font-semibold uppercase text-neutral-500">Variations</th>
                <th class="px-3 py-2 text-right text-[10px] font-semibold uppercase text-neutral-500">Settled</th>
                <th class="px-3 py-2 text-center text-[10px] font-semibold uppercase text-neutral-500">Cert</th>
                <th class="px-3 py-2 text-center text-[10px] font-semibold uppercase text-neutral-500">Rating</th>
              </tr></thead>
              <tbody class="divide-y divide-neutral-100">
                {#each detail.final_accounts as fa}
                  <tr>
                    <td class="px-3 py-2 text-sm font-medium text-neutral-900">{fa.contractor_name}</td>
                    <td class="px-3 py-2 text-right text-sm tabular-nums text-neutral-700">{fmtCFull(fa.original_contract_value)}</td>
                    <td class="px-3 py-2 text-right text-sm tabular-nums text-neutral-600">{fmtCFull(fa.approved_variations)}</td>
                    <td class="px-3 py-2 text-right text-sm font-semibold tabular-nums text-neutral-900">{fmtCFull(fa.final_settled_amount)}</td>
                    <td class="px-3 py-2 text-center">{#if fa.closeout_certificate_issued}<span class="text-emerald-600 text-xs font-semibold">Issued</span>{:else}<span class="text-amber-600 text-xs font-semibold">Pending</span>{/if}</td>
                    <td class="px-3 py-2 text-center text-sm text-neutral-600">{fa.performance_rating ? `${fa.performance_rating}/5` : "--"}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}

      {:else if detailTab === "snags"}
        {#if detail.snag_items.length === 0}
          <p class="text-sm text-neutral-400 text-center py-6">No snags recorded.</p>
        {:else}
          <div class="space-y-2">
            {#each detail.snag_items as snag}
              <div class="rounded-lg border border-neutral-200 p-3 {snag.status === 'open' ? 'border-l-4 border-l-amber-500' : ''}">
                <div class="flex items-center justify-between mb-1">
                  <p class="text-sm font-medium text-neutral-900">{snag.location}</p>
                  <span class="inline-block rounded-full px-2 py-0.5 text-[9px] font-semibold {snagColor(snag.status)}">{snag.status_display}</span>
                </div>
                <p class="text-xs text-neutral-600">{snag.description}</p>
                <div class="flex items-center gap-3 mt-1 text-[10px] text-neutral-400">
                  {#if snag.responsible_contractor}<span>Contractor: {snag.responsible_contractor}</span>{/if}
                  <span>Reported: {fmtDate(snag.reported_date)}</span>
                  {#if snag.resolved_date}<span class="text-emerald-600">Resolved: {fmtDate(snag.resolved_date)}</span>{/if}
                </div>
              </div>
            {/each}
          </div>
        {/if}

      {:else if detailTab === "warranties"}
        {#if detail.warranties.length === 0}
          <p class="text-sm text-neutral-400 text-center py-6">No warranties tracked.</p>
        {:else}
          <div class="space-y-2">
            {#each detail.warranties as w}
              <div class="rounded-lg border border-neutral-200 p-3">
                <div class="flex items-center justify-between mb-1">
                  <p class="text-sm font-semibold text-neutral-900">{w.asset_system}</p>
                  {#if w.is_active}
                    <span class="text-[9px] font-semibold rounded-full px-2 py-0.5 bg-emerald-100 text-emerald-800">{w.days_remaining}d remaining</span>
                  {:else}
                    <span class="text-[9px] font-semibold rounded-full px-2 py-0.5 bg-red-100 text-red-800">Expired</span>
                  {/if}
                </div>
                <div class="flex items-center gap-4 text-xs text-neutral-500">
                  <span>Provider: {w.provider || "--"}</span>
                  <span>{fmtDate(w.warranty_start)} — {fmtDate(w.warranty_end)}</span>
                </div>
                {#if w.claim_log && w.claim_log.length > 0}
                  <div class="mt-2">
                    <p class="text-[10px] font-semibold text-neutral-400 mb-1">Claims ({w.claim_log.length})</p>
                    {#each w.claim_log as claim}
                      <p class="text-xs text-neutral-600">{claim.date}: {claim.issue} — <span class="font-medium">{claim.status}</span></p>
                    {/each}
                  </div>
                {/if}
              </div>
            {/each}
          </div>
        {/if}
      {/if}
    </div>
  {/if}
</DrawerShell>

<!-- ═══════════ CREATE DRAWER ═══════════ -->
<DrawerShell open={createOpen} title="Initiate Closeout" subtitle="Begin the project closeout process" width="max-w-md" onclose={() => (createOpen = false)}>
  <form onsubmit={saveCloseout} class="p-6 space-y-4">
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Project *</span><select bind:value={form.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"><option value="">Select</option>{#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}</select></label>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Practical Completion Date</span><input type="date" bind:value={form.practical_completion_date} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Original Budget</span><input type="number" step="0.01" bind:value={form.original_budget} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Notes</span><textarea bind:value={form.notes} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <div class="flex justify-end gap-2 pt-2">
      <button type="button" onclick={() => (createOpen = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      {#if isDev}<button type="button" onclick={devFill} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
      <button type="submit" disabled={saving} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{saving ? "Creating..." : "Initiate Closeout"}</button>
    </div>
  </form>
</DrawerShell>

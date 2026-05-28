<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DrawerShell from "$lib/components/DrawerShell.svelte";
  import DateInput from "$lib/components/DateInput.svelte";
  import type {
    LandAcquisitionListItem,
    LandAcquisitionDetail,
    LandTitleType,
    LandVerificationStatus,
    LandAcquisitionStatus,
    PaginatedResponse,
    ProjectListItem,
  } from "$lib/types";

  let rows = $state<LandAcquisitionListItem[]>([]);
  let loading = $state(true);
  let totalCount = $state(0);
  let currentPage = $state(1);
  let statusFilter = $state("");
  const pageSize = 15;

  let detailOpen = $state(false);
  let detail = $state<LandAcquisitionDetail | null>(null);
  let detailLoading = $state(false);

  let createOpen = $state(false);
  let saving = $state(false);
  let form = $state(defaultForm());

  let projects = $state<ProjectListItem[]>([]);
  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  function defaultForm() {
    return {
      project: "",
      location: "",
      land_size_sqm: "",
      description: "",
      title_type: "pending" as LandTitleType,
      verification_status: "not_started" as LandVerificationStatus,
      acquisition_status: "prospecting" as LandAcquisitionStatus,
      survey_plan_ref: "",
      title_document_ref: "",
      purchase_price: "",
      agency_fees: "",
      legal_fees: "",
      stamp_duty: "",
      registration_fees: "",
      seller_name: "",
      seller_contact: "",
      land_search_registry: "",
      escrow_holder: "",
      notes: "",
    };
  }

  function devFill() {
    form = {
      ...form,
      project: form.project || (projects.length > 0 ? String(projects[0].id) : ""),
      location: "Plot 1847, Katampe Extension, Abuja FCT",
      land_size_sqm: "28000",
      description: "28,000 sqm prime residential land in Katampe Extension. Gently sloping terrain with good access roads. Currently vacant with perimeter fencing. Adjacent to completed Asokoro Estate.",
      title_type: "c_of_o",
      verification_status: "in_progress",
      acquisition_status: "due_diligence",
      survey_plan_ref: "ABJ/KAT/2026/SRV/0487",
      title_document_ref: "FCT/ABJ/C-OF-O/2024/0891",
      purchase_price: "950000000",
      agency_fees: "47500000",
      legal_fees: "28500000",
      stamp_duty: "14250000",
      registration_fees: "9500000",
      seller_name: "Alhaji Musa Ibrahim",
      seller_contact: "+234 803 555 7890",
      land_search_registry: "AGIS (Abuja Geographic Information Systems)",
      escrow_holder: "Aluko & Oyebode (Solicitors)",
      notes: "MOU signed on 15 Feb 2026. C of O application submitted. Survey plan verified by licensed surveyor. Encumbrance search pending at AGIS — estimated 3 weeks turnaround.",
    };
  }

  async function fetchLands() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (statusFilter) params.acquisition_status = statusFilter;
      const [res, projRes] = await Promise.all([
        api.get<PaginatedResponse<LandAcquisitionListItem>>("/projects/land-acquisitions/", params),
        projects.length === 0 ? api.get<PaginatedResponse<ProjectListItem>>("/projects/", { page_size: "200", ordering: "name" }) : Promise.resolve(null),
      ]);
      rows = res.results;
      totalCount = res.count;
      if (projRes) projects = projRes.results;
    } catch { rows = []; totalCount = 0; }
    loading = false;
  }

  $effect(() => { void statusFilter; void currentPage; fetchLands(); });

  async function openDetail(id: number) {
    detailOpen = true;
    detailLoading = true;
    try { detail = await api.get<LandAcquisitionDetail>(`/projects/land-acquisitions/${id}/`); } catch { detail = null; }
    detailLoading = false;
  }

  async function saveLand(e: Event) {
    e.preventDefault();
    if (!form.project || !form.location.trim()) { toast.error("Required", "Project and location are required."); return; }
    saving = true;
    try {
      await api.post("/projects/land-acquisitions/", {
        ...form,
        project: Number(form.project),
        land_size_sqm: form.land_size_sqm || null,
        purchase_price: form.purchase_price || "0",
        agency_fees: form.agency_fees || "0",
        legal_fees: form.legal_fees || "0",
        stamp_duty: form.stamp_duty || "0",
        registration_fees: form.registration_fees || "0",
      });
      toast.success("Land parcel added", `${form.location}`);
      createOpen = false;
      form = defaultForm();
      await fetchLands();
    } catch (error) {
      const msg = error instanceof ApiError ? (Object.values(error.fieldErrors)[0]?.[0] ?? "Save failed.") : "Save failed.";
      toast.error("Save failed", msg);
    } finally { saving = false; }
  }

  function fmtC(v: string | number | null | undefined): string { if (!v || v === "0.00" || v === "0") return "--"; return currency.formatCompact(v); }
  function fmtCFull(v: string | number | null | undefined): string { if (!v || v === "0.00" || v === "0") return "--"; return currency.format(v); }
  function fmtDate(v: string | null | undefined): string { if (!v) return "--"; const d = new Date(v); return Number.isNaN(d.getTime()) ? "--" : d.toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }); }
  const totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));

  function verificationColor(s: string): string {
    if (s === "verified" || s === "registered") return "bg-emerald-100 text-emerald-800";
    if (s === "encumbrance_found") return "bg-red-100 text-red-800";
    if (s === "in_progress") return "bg-amber-100 text-amber-800";
    return "bg-neutral-100 text-neutral-600";
  }

  function paymentStatusColor(s: string): string {
    if (s === "paid") return "bg-emerald-100 text-emerald-800";
    if (s === "overdue") return "bg-red-100 text-red-800";
    if (s === "invoiced") return "bg-amber-100 text-amber-800";
    return "bg-neutral-100 text-neutral-600";
  }
</script>

<div class="space-y-6">
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">Development</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-900">Land Acquisition</h1>
      <p class="mt-1 text-sm text-neutral-500">Track parcels, title verification, due diligence, and payment milestones.</p>
    </div>
    <button onclick={() => { form = defaultForm(); createOpen = true; }} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800">+ New Parcel</button>
  </div>

  <div class="flex items-center gap-3">
    <select bind:value={statusFilter} onchange={() => (currentPage = 1)} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Statuses</option>
      <option value="prospecting">Prospecting</option>
      <option value="negotiation">Negotiation</option>
      <option value="mou_signed">MOU Signed</option>
      <option value="due_diligence">Due Diligence</option>
      <option value="contract_signed">Contract Signed</option>
      <option value="payment_in_progress">Payment In Progress</option>
      <option value="completed">Completed</option>
    </select>
  </div>

  <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
    {#if loading}
      <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
    {:else if rows.length === 0}
      <div class="px-6 py-14 text-center"><p class="text-sm text-neutral-500">No land acquisitions found.</p></div>
    {:else}
      <div class="overflow-x-auto">
        <table class="min-w-[1000px] w-full">
          <thead class="border-b border-neutral-200 bg-neutral-50">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Parcel</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Location</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Title</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Verification</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Status</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Total Cost</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Paid</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Balance</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each rows as row}
              <tr class="hover:bg-neutral-50 cursor-pointer" onclick={() => openDetail(row.id)}>
                <td class="px-4 py-3 text-sm font-semibold text-neutral-900">{row.parcel_id}</td>
                <td class="px-4 py-3 text-sm text-neutral-700 max-w-[200px] truncate">{row.location || "--"}</td>
                <td class="px-4 py-3 text-xs font-medium text-neutral-600">{row.title_type_display}</td>
                <td class="px-4 py-3"><span class="inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold {verificationColor(row.verification_status)}">{row.verification_status_display}</span></td>
                <td class="px-4 py-3"><StatusBadge status={row.acquisition_status} /></td>
                <td class="px-4 py-3 text-right text-sm font-bold tabular-nums text-neutral-900">{fmtC(row.total_acquisition_cost)}</td>
                <td class="px-4 py-3 text-right text-sm tabular-nums text-emerald-600">{fmtC(row.total_paid)}</td>
                <td class="px-4 py-3 text-right text-sm font-bold tabular-nums {Number(row.balance_remaining) > 0 ? 'text-amber-600' : 'text-neutral-400'}">{fmtC(row.balance_remaining)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      {#if totalCount > pageSize}
        <div class="flex items-center justify-between border-t border-neutral-200 px-4 py-3">
          <p class="text-xs text-neutral-500">Showing {(currentPage - 1) * pageSize + 1}–{Math.min(currentPage * pageSize, totalCount)} of {totalCount}</p>
          <div class="flex items-center gap-2">
            <button onclick={() => (currentPage = Math.max(1, currentPage - 1))} disabled={currentPage <= 1} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 disabled:opacity-40">Previous</button>
            <span class="text-xs font-medium text-neutral-600">Page {currentPage} of {totalPages}</span>
            <button onclick={() => (currentPage = Math.min(totalPages, currentPage + 1))} disabled={currentPage >= totalPages} class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 disabled:opacity-40">Next</button>
          </div>
        </div>
      {/if}
    {/if}
  </section>
</div>

<!-- ═══════════ DETAIL DRAWER ═══════════ -->
<DrawerShell open={detailOpen} title={detail?.parcel_id ?? "Parcel"} subtitle={detail?.location ?? ""} width="max-w-2xl" onclose={() => (detailOpen = false)}>
  {#if detailLoading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if detail}
    <div class="p-6 space-y-5">
      <!-- Title + Verification header -->
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="text-xs font-medium text-neutral-600">{detail.title_type_display}</span>
          <span class="inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold {verificationColor(detail.verification_status)}">{detail.verification_status_display}</span>
        </div>
        <StatusBadge status={detail.acquisition_status} />
      </div>

      <!-- Financial summary -->
      <div class="grid grid-cols-3 gap-3">
        <div class="rounded-lg border border-neutral-200 bg-white p-3 text-center">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Total Cost</p>
          <p class="mt-1 text-lg font-bold text-neutral-900 tabular-nums">{fmtC(detail.total_acquisition_cost)}</p>
        </div>
        <div class="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-center">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-emerald-700">Paid</p>
          <p class="mt-1 text-lg font-bold text-emerald-900 tabular-nums">{fmtC(detail.total_paid)}</p>
        </div>
        <div class="rounded-lg border-2 {Number(detail.balance_remaining) > 0 ? 'border-amber-300 bg-amber-50' : 'border-emerald-300 bg-emerald-50'} p-3 text-center">
          <p class="text-[10px] font-semibold uppercase tracking-wider {Number(detail.balance_remaining) > 0 ? 'text-amber-700' : 'text-emerald-700'}">Balance</p>
          <p class="mt-1 text-lg font-bold tabular-nums {Number(detail.balance_remaining) > 0 ? 'text-amber-900' : 'text-emerald-900'}">{fmtC(detail.balance_remaining)}</p>
        </div>
      </div>

      <!-- Cost breakdown -->
      <div class="rounded-lg border border-neutral-200 p-4">
        <p class="text-[10px] font-bold uppercase tracking-wider text-neutral-500 mb-2">Cost Breakdown</p>
        <div class="grid grid-cols-2 gap-3 text-sm">
          <div class="flex justify-between"><span class="text-neutral-500">Purchase Price</span><span class="font-bold tabular-nums text-neutral-900">{fmtCFull(detail.purchase_price)}</span></div>
          <div class="flex justify-between"><span class="text-neutral-500">Agency Fees</span><span class="tabular-nums text-neutral-700">{fmtCFull(detail.agency_fees)}</span></div>
          <div class="flex justify-between"><span class="text-neutral-500">Legal Fees</span><span class="tabular-nums text-neutral-700">{fmtCFull(detail.legal_fees)}</span></div>
          <div class="flex justify-between"><span class="text-neutral-500">Stamp Duty</span><span class="tabular-nums text-neutral-700">{fmtCFull(detail.stamp_duty)}</span></div>
          <div class="flex justify-between"><span class="text-neutral-500">Registration</span><span class="tabular-nums text-neutral-700">{fmtCFull(detail.registration_fees)}</span></div>
        </div>
      </div>

      <!-- Meta -->
      <div class="grid grid-cols-2 gap-4">
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Project</p><p class="text-sm text-neutral-900">{detail.project_name}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Land Size</p><p class="text-sm text-neutral-900">{detail.land_size_sqm ? `${Number(detail.land_size_sqm).toLocaleString()} sqm` : "--"}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Survey Plan</p><p class="text-sm text-neutral-900">{detail.survey_plan_ref || "--"}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Title Doc Ref</p><p class="text-sm text-neutral-900">{detail.title_document_ref || "--"}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Seller</p><p class="text-sm text-neutral-900">{detail.seller_name || "--"}</p></div>
        <div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Seller Contact</p><p class="text-sm text-neutral-900">{detail.seller_contact || "--"}</p></div>
      </div>

      <!-- Escrow -->
      {#if detail.escrow_holder}
        <div class="rounded-lg border {detail.escrow_secured ? 'border-emerald-200 bg-emerald-50' : 'border-amber-200 bg-amber-50'} p-3">
          <p class="text-[10px] font-semibold uppercase tracking-wider {detail.escrow_secured ? 'text-emerald-700' : 'text-amber-700'}">Escrow {detail.escrow_secured ? "Secured" : "Pending"}</p>
          <p class="text-sm text-neutral-900 mt-0.5">{detail.escrow_holder}</p>
        </div>
      {/if}

      <!-- Legal verification -->
      <div class="rounded-lg border border-neutral-200 p-4">
        <p class="text-[10px] font-bold uppercase tracking-wider text-neutral-500 mb-2">Legal Verification</p>
        <div class="grid grid-cols-2 gap-3">
          <div><p class="text-[10px] text-neutral-400">Land Search Registry</p><p class="text-sm text-neutral-900">{detail.land_search_registry || "--"}</p></div>
          <div><p class="text-[10px] text-neutral-400">Search Date</p><p class="text-sm text-neutral-900">{fmtDate(detail.land_search_date)}</p></div>
          <div><p class="text-[10px] text-neutral-400">Encumbrance Check</p><p class="text-sm {detail.encumbrance_check ? 'text-emerald-600 font-semibold' : 'text-neutral-500'}">{detail.encumbrance_check ? "Clear" : "Pending"}</p></div>
          <div><p class="text-[10px] text-neutral-400">Govt Approval</p><p class="text-sm text-neutral-900">{detail.govt_approval_status || "--"}{detail.govt_approval_days_elapsed > 0 ? ` (${detail.govt_approval_days_elapsed} days)` : ""}</p></div>
        </div>
        {#if detail.encumbrance_notes}<p class="mt-2 text-xs text-neutral-600">{detail.encumbrance_notes}</p>{/if}
      </div>

      <!-- Payment Milestones -->
      {#if detail.payment_milestones.length > 0}
        <div class="border-t border-neutral-200 pt-4">
          <p class="text-[10px] font-bold uppercase tracking-wider text-neutral-500 mb-3">Payment Schedule ({detail.payment_milestones.length})</p>
          <div class="space-y-2">
            {#each detail.payment_milestones as pm}
              <div class="rounded-lg border border-neutral-100 bg-neutral-50 p-3 flex items-center justify-between">
                <div>
                  <p class="text-sm font-medium text-neutral-900">{pm.title}</p>
                  <p class="text-xs text-neutral-500">{fmtDate(pm.due_date)}{pm.recipient ? ` — ${pm.recipient}` : ""}</p>
                </div>
                <div class="text-right">
                  <p class="text-sm font-bold tabular-nums text-neutral-900">{fmtCFull(pm.amount)}</p>
                  <span class="inline-block rounded-full px-2 py-0.5 text-[9px] font-semibold {paymentStatusColor(pm.status)}">{pm.status_display}</span>
                </div>
              </div>
            {/each}
          </div>
        </div>
      {/if}

      {#if detail.description}<div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Description</p><p class="text-sm text-neutral-700 whitespace-pre-line">{detail.description}</p></div>{/if}
      {#if detail.notes}<div><p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-1">Notes</p><p class="text-sm text-neutral-700 whitespace-pre-line">{detail.notes}</p></div>{/if}
    </div>
  {/if}
</DrawerShell>

<!-- ═══════════ CREATE DRAWER ═══════════ -->
<DrawerShell open={createOpen} title="New Land Parcel" subtitle="Register a land acquisition" width="max-w-xl" onclose={() => (createOpen = false)}>
  <form onsubmit={saveLand} class="p-6 space-y-4">
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Project *</span><select bind:value={form.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"><option value="">Select</option>{#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}</select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Land Size (sqm)</span><input type="number" step="0.01" bind:value={form.land_size_sqm} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Location *</span><input bind:value={form.location} placeholder="Address or plot reference" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Description</span><textarea bind:value={form.description} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>

    <div class="grid grid-cols-3 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Title Type</span><select bind:value={form.title_type} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="pending">Pending</option><option value="c_of_o">C of O</option><option value="governors_consent">Governor's Consent</option><option value="excision">Excision</option><option value="deed_of_assignment">Deed of Assignment</option><option value="freehold">Freehold</option><option value="leasehold">Leasehold</option>
      </select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Verification</span><select bind:value={form.verification_status} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="not_started">Not Started</option><option value="in_progress">In Progress</option><option value="encumbrance_found">Encumbrance Found</option><option value="verified">Verified</option><option value="registered">Registered</option>
      </select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Status</span><select bind:value={form.acquisition_status} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="prospecting">Prospecting</option><option value="negotiation">Negotiation</option><option value="mou_signed">MOU Signed</option><option value="due_diligence">Due Diligence</option><option value="contract_signed">Contract Signed</option><option value="payment_in_progress">Payment In Progress</option><option value="completed">Completed</option>
      </select></label>
    </div>

    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Survey Plan Ref</span><input bind:value={form.survey_plan_ref} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Title Doc Ref</span><input bind:value={form.title_document_ref} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>

    <!-- Financial -->
    <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-3 space-y-3">
      <p class="text-xs font-semibold text-neutral-600">Acquisition Costs</p>
      <label><span class="mb-1 block text-[10px] text-neutral-500">Purchase Price</span><input type="number" step="0.01" bind:value={form.purchase_price} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <div class="grid grid-cols-2 gap-3">
        <label><span class="mb-1 block text-[10px] text-neutral-500">Agency Fees</span><input type="number" step="0.01" bind:value={form.agency_fees} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
        <label><span class="mb-1 block text-[10px] text-neutral-500">Legal Fees</span><input type="number" step="0.01" bind:value={form.legal_fees} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      </div>
      <div class="grid grid-cols-2 gap-3">
        <label><span class="mb-1 block text-[10px] text-neutral-500">Stamp Duty</span><input type="number" step="0.01" bind:value={form.stamp_duty} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
        <label><span class="mb-1 block text-[10px] text-neutral-500">Registration Fees</span><input type="number" step="0.01" bind:value={form.registration_fees} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      </div>
    </div>

    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Seller Name</span><input bind:value={form.seller_name} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Seller Contact</span><input bind:value={form.seller_contact} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Land Search Registry</span><input bind:value={form.land_search_registry} placeholder="e.g. AGIS" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Escrow Holder</span><input bind:value={form.escrow_holder} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <label class="block"><span class="mb-1 block text-xs font-semibold text-neutral-600">Notes</span><textarea bind:value={form.notes} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>

    <div class="flex justify-end gap-2 pt-2">
      <button type="button" onclick={() => (createOpen = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      {#if isDev}<button type="button" onclick={devFill} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
      <button type="submit" disabled={saving} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{saving ? "Saving..." : "Register Parcel"}</button>
    </div>
  </form>
</DrawerShell>

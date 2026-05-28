<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DrawerShell from "$lib/components/DrawerShell.svelte";
  import type {
    ProjectConsultantListItem,
    ProjectConsultantDetail,
    ConsultantDiscipline,
    ConsultantEngagementStatus,
    PaginatedResponse,
    ProjectListItem,
  } from "$lib/types";

  let rows = $state<ProjectConsultantListItem[]>([]);
  let loading = $state(true);
  let projects = $state<ProjectListItem[]>([]);
  let searchInput = $state("");
  let searchQuery = $state("");
  let projectFilter = $state("");
  let disciplineFilter = $state("");
  let statusFilter = $state("");
  let searchTimeout: ReturnType<typeof setTimeout> | undefined;

  let detailOpen = $state(false);
  let detail = $state<ProjectConsultantDetail | null>(null);
  let detailLoading = $state(false);
  let detailTab = $state<"scope" | "financials" | "deliverables" | "comms" | "compliance">("scope");

  let createOpen = $state(false);
  let saving = $state(false);
  let form = $state(defaultForm());

  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  function defaultForm() {
    return {
      project: "", firm_name: "", contact_person: "", contact_role: "",
      email: "", phone: "", whatsapp: "", address: "",
      discipline: "architectural" as ConsultantDiscipline,
      status: "onboarding" as ConsultantEngagementStatus,
      scope_of_work: "", contract_value: "", amount_paid: "",
      contract_start_date: "", contract_end_date: "",
      compliance_status: "green",
      insurance_policy: "", insurance_expiry: "",
      license_number: "", license_expiry: "",
      reports_to: "", notes: "",
    };
  }

  function devFill() {
    form = {
      ...form,
      project: form.project || (projects.length > 0 ? String(projects[0].id) : ""),
      firm_name: "Adesanya & Partners — Structural Engineers",
      contact_person: "Engr. Bola Adesanya",
      contact_role: "Managing Partner",
      email: "bola@adesanya-eng.ng",
      phone: "+234 803 456 7890",
      whatsapp: "+234 803 456 7890",
      address: "15 Awolowo Way, Ikeja, Lagos",
      discipline: "structural",
      status: "active",
      scope_of_work: "Full structural design and supervision for Phases 1-3 including substructure, superstructure, and retaining walls. Responsible for structural calculations, shop drawings review, and site inspection reports.",
      contract_value: "45000000",
      amount_paid: "18000000",
      contract_start_date: "2025-11-01",
      contract_end_date: "2027-06-30",
      compliance_status: "green",
      insurance_policy: "PI-STR-2026-0089",
      insurance_expiry: "2027-03-31",
      license_number: "COREN/2024/STR-4412",
      license_expiry: "2026-12-31",
      reports_to: "Project Manager",
      notes: "Firm has 15+ years experience in high-rise residential structures in Lagos. Currently engaged on 2 other projects.",
    };
  }

  async function fetchData() {
    loading = true;
    try {
      const params: Record<string, string> = { page_size: "100" };
      if (searchQuery) params.search = searchQuery;
      if (projectFilter) params.project = projectFilter;
      if (disciplineFilter) params.discipline = disciplineFilter;
      if (statusFilter) params.status = statusFilter;

      const [res, projRes] = await Promise.all([
        api.get<PaginatedResponse<ProjectConsultantListItem>>("/projects/consultants/", params),
        projects.length === 0 ? api.get<PaginatedResponse<ProjectListItem>>("/projects/", { page_size: "200", ordering: "name" }) : Promise.resolve(null),
      ]);
      rows = res.results;
      if (projRes) projects = projRes.results;
    } catch { rows = []; }
    loading = false;
  }

  $effect(() => { void searchQuery; void projectFilter; void disciplineFilter; void statusFilter; fetchData(); });

  function onSearchInput(e: Event) {
    searchInput = (e.target as HTMLInputElement).value;
    if (searchTimeout) clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => { searchQuery = searchInput.trim(); }, 250);
  }

  async function openDetail(id: number) {
    detailOpen = true;
    detailLoading = true;
    detailTab = "scope";
    try { detail = await api.get<ProjectConsultantDetail>(`/projects/consultants/${id}/`); } catch { detail = null; }
    detailLoading = false;
  }

  async function saveConsultant(e: Event) {
    e.preventDefault();
    if (!form.project || !form.firm_name.trim()) { toast.error("Required", "Project and firm name are required."); return; }
    saving = true;
    try {
      await api.post("/projects/consultants/", {
        ...form,
        project: Number(form.project),
        contract_value: form.contract_value || "0",
        amount_paid: form.amount_paid || "0",
        contract_start_date: form.contract_start_date || null,
        contract_end_date: form.contract_end_date || null,
        insurance_expiry: form.insurance_expiry || null,
        license_expiry: form.license_expiry || null,
        collaborates_with: [],
      });
      toast.success("Consultant added", `"${form.firm_name}" registered.`);
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

  function complianceColor(s: string): string {
    if (s === "green") return "bg-emerald-500";
    if (s === "yellow") return "bg-amber-500";
    return "bg-red-500";
  }
</script>

<div class="space-y-6">
  <div class="flex items-start justify-between gap-4">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">Projects</p>
      <h1 class="mt-2 text-2xl font-bold text-neutral-900">Consultants & Stakeholders</h1>
      <p class="mt-1 text-sm text-neutral-500">Professional directory — scope, financials, deliverables, and compliance tracking.</p>
    </div>
    <button onclick={() => { form = defaultForm(); createOpen = true; }} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800">+ Add Consultant</button>
  </div>

  <!-- Filters -->
  <div class="grid grid-cols-1 gap-3 xl:grid-cols-4">
    <input type="text" value={searchInput} oninput={onSearchInput} placeholder="Search firm, contact, email..." class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
    <select bind:value={projectFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Projects</option>
      {#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}
    </select>
    <select bind:value={disciplineFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Disciplines</option>
      <option value="architectural">Architectural</option><option value="structural">Structural</option><option value="mep">MEP</option>
      <option value="quantity_surveying">Quantity Surveying</option><option value="legal">Legal</option><option value="geotechnical">Geotechnical</option>
      <option value="environmental">Environmental</option><option value="town_planning">Town Planning</option><option value="land_surveying">Land Surveying</option>
      <option value="project_management">Project Management</option><option value="interior_design">Interior Design</option><option value="landscape">Landscape</option><option value="other">Other</option>
    </select>
    <select bind:value={statusFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
      <option value="">All Statuses</option>
      <option value="onboarding">On-Boarding</option><option value="active">Active</option><option value="on_hold">On Hold</option><option value="completed">Completed</option><option value="terminated">Terminated</option>
    </select>
  </div>

  <!-- Directory -->
  {#if loading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if rows.length === 0}
    <div class="rounded-2xl border border-neutral-200 bg-white px-6 py-14 text-center"><p class="text-sm text-neutral-500">No consultants found.</p></div>
  {:else}
    <div class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
      {#each rows as c}
        <button class="w-full text-left rounded-2xl border border-neutral-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow cursor-pointer" onclick={() => openDetail(c.id)}>
          <div class="flex items-start justify-between mb-3">
            <div>
              <p class="text-sm font-semibold text-neutral-900">{c.firm_name}</p>
              <p class="text-xs text-neutral-500 mt-0.5">{c.discipline_display}</p>
            </div>
            <div class="flex items-center gap-2">
              <span class="h-2.5 w-2.5 rounded-full {complianceColor(c.compliance_status)}" title={c.compliance_status_display}></span>
              <StatusBadge status={c.status} />
            </div>
          </div>
          {#if c.contact_person}
            <p class="text-xs text-neutral-600 mb-2">{c.contact_person}{c.contact_role ? ` — ${c.contact_role}` : ""}</p>
          {/if}
          <!-- Payment progress -->
          <div class="mb-2">
            <div class="flex items-center justify-between text-[10px] text-neutral-500 mb-1">
              <span>Payment Progress</span>
              <span class="font-semibold text-neutral-700">{c.payment_progress}%</span>
            </div>
            <div class="h-1.5 w-full rounded-full bg-neutral-100 overflow-hidden">
              <div class="h-full rounded-full bg-emerald-500 transition-all" style="width: {Math.min(c.payment_progress, 100)}%"></div>
            </div>
          </div>
          <div class="flex items-center justify-between text-xs text-neutral-500">
            <span>{fmtC(c.contract_value)}</span>
            <div class="flex items-center gap-2">
              {#if c.email}<a href="mailto:{c.email}" onclick={(e) => e.stopPropagation()} class="text-blue-500 hover:text-blue-700" title="Email">@</a>{/if}
              {#if c.phone}<a href="tel:{c.phone}" onclick={(e) => e.stopPropagation()} class="text-neutral-400 hover:text-neutral-700" title="Phone">Ph</a>{/if}
            </div>
          </div>
        </button>
      {/each}
    </div>
  {/if}
</div>

<!-- ═══════════ DETAIL DRAWER ═══════════ -->
<DrawerShell open={detailOpen} title="Consultant Profile" subtitle={detail?.firm_name ?? ""} width="max-w-2xl" onclose={() => (detailOpen = false)}>
  {#if detailLoading}
    <div class="flex items-center justify-center py-16"><div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div></div>
  {:else if detail}
    <div class="border-b border-neutral-200">
      <div class="flex gap-1 px-6 pt-4">
        {#each [["scope", "Scope"], ["financials", "Financials"], ["deliverables", "Deliverables"], ["comms", "Communications"], ["compliance", "Compliance"]] as [key, label]}
          <button onclick={() => (detailTab = key as typeof detailTab)} class="rounded-t-lg px-3 py-2 text-xs font-semibold transition-colors {detailTab === key ? 'bg-white text-neutral-900 border border-b-white border-neutral-200 -mb-px' : 'text-neutral-500 hover:text-neutral-700'}">{label}</button>
        {/each}
      </div>
    </div>

    <div class="p-6 space-y-5">
      {#if detailTab === "scope"}
        <div class="flex items-center gap-3">
          <StatusBadge status={detail.status} />
          <span class="text-xs text-neutral-500">{detail.discipline_display}</span>
          <span class="h-2.5 w-2.5 rounded-full {complianceColor(detail.compliance_status)}" title={detail.compliance_status_display}></span>
        </div>
        <div class="grid grid-cols-2 gap-3 text-sm">
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Contact Person</p><p class="text-neutral-900 font-medium">{detail.contact_person || "--"}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Role</p><p class="text-neutral-900">{detail.contact_role || "--"}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Email</p>{#if detail.email}<a href="mailto:{detail.email}" class="text-blue-600 hover:underline">{detail.email}</a>{:else}<p class="text-neutral-400">--</p>{/if}</div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Phone</p><p class="text-neutral-900">{detail.phone || "--"}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Reports To</p><p class="text-neutral-900">{detail.reports_to || "--"}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Contract Period</p><p class="text-neutral-900">{fmtDate(detail.contract_start_date)} — {fmtDate(detail.contract_end_date)}</p></div>
        </div>
        {#if detail.scope_of_work}<div><p class="text-[10px] font-semibold uppercase text-neutral-400 mb-1">Scope of Work</p><p class="text-sm text-neutral-700 whitespace-pre-line">{detail.scope_of_work}</p></div>{/if}
        {#if detail.notes}<div><p class="text-[10px] font-semibold uppercase text-neutral-400 mb-1">Notes</p><p class="text-sm text-neutral-700 whitespace-pre-line">{detail.notes}</p></div>{/if}

      {:else if detailTab === "financials"}
        <div class="grid grid-cols-3 gap-3">
          <div class="rounded-lg border border-neutral-200 p-3 text-center">
            <p class="text-[9px] font-semibold uppercase text-neutral-400">Contract Value</p>
            <p class="mt-1 text-lg font-bold text-neutral-900 tabular-nums">{fmtC(detail.contract_value)}</p>
          </div>
          <div class="rounded-lg border border-emerald-100 bg-emerald-50 p-3 text-center">
            <p class="text-[9px] font-semibold uppercase text-emerald-700">Paid</p>
            <p class="mt-1 text-lg font-bold text-emerald-900 tabular-nums">{fmtC(detail.amount_paid)}</p>
          </div>
          <div class="rounded-lg border border-amber-100 bg-amber-50 p-3 text-center">
            <p class="text-[9px] font-semibold uppercase text-amber-700">Remaining</p>
            <p class="mt-1 text-lg font-bold text-amber-900 tabular-nums">{fmtC(detail.amount_remaining)}</p>
          </div>
        </div>
        <div class="mb-3">
          <div class="flex items-center justify-between text-xs text-neutral-500 mb-1"><span>Payment Progress</span><span class="font-semibold text-neutral-700">{detail.payment_progress}%</span></div>
          <div class="h-2 w-full rounded-full bg-neutral-100"><div class="h-full rounded-full bg-emerald-500" style="width: {Math.min(detail.payment_progress, 100)}%"></div></div>
        </div>

        {#if detail.payment_milestones.length === 0}
          <p class="text-sm text-neutral-400 text-center py-4">No payment milestones defined.</p>
        {:else}
          <table class="w-full">
            <thead class="bg-neutral-50"><tr>
              <th class="px-3 py-2 text-left text-[10px] font-semibold uppercase text-neutral-500">Milestone</th>
              <th class="px-3 py-2 text-right text-[10px] font-semibold uppercase text-neutral-500">Amount</th>
              <th class="px-3 py-2 text-left text-[10px] font-semibold uppercase text-neutral-500">Trigger</th>
              <th class="px-3 py-2 text-center text-[10px] font-semibold uppercase text-neutral-500">Status</th>
            </tr></thead>
            <tbody class="divide-y divide-neutral-100">
              {#each detail.payment_milestones as pm}
                <tr>
                  <td class="px-3 py-2 text-sm text-neutral-900">{pm.description}</td>
                  <td class="px-3 py-2 text-right text-sm font-semibold tabular-nums text-neutral-900">{fmtCFull(pm.amount)}</td>
                  <td class="px-3 py-2 text-sm text-neutral-600">{fmtDate(pm.trigger_date)}</td>
                  <td class="px-3 py-2 text-center"><StatusBadge status={pm.status} /></td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}

      {:else if detailTab === "deliverables"}
        {#if detail.deliverables.length === 0}
          <p class="text-sm text-neutral-400 text-center py-6">No deliverables tracked.</p>
        {:else}
          <table class="w-full">
            <thead class="bg-neutral-50"><tr>
              <th class="px-3 py-2 text-left text-[10px] font-semibold uppercase text-neutral-500">Deliverable</th>
              <th class="px-3 py-2 text-left text-[10px] font-semibold uppercase text-neutral-500">Due</th>
              <th class="px-3 py-2 text-center text-[10px] font-semibold uppercase text-neutral-500">Format</th>
              <th class="px-3 py-2 text-center text-[10px] font-semibold uppercase text-neutral-500">Status</th>
            </tr></thead>
            <tbody class="divide-y divide-neutral-100">
              {#each detail.deliverables as d}
                <tr>
                  <td class="px-3 py-2 text-sm text-neutral-900">{d.name}</td>
                  <td class="px-3 py-2 text-sm text-neutral-600">{fmtDate(d.due_date)}</td>
                  <td class="px-3 py-2 text-center text-xs text-neutral-500">{d.format_display}</td>
                  <td class="px-3 py-2 text-center"><StatusBadge status={d.status} /></td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}

      {:else if detailTab === "comms"}
        {#if detail.communication_logs.length === 0}
          <p class="text-sm text-neutral-400 text-center py-6">No communication logs recorded.</p>
        {:else}
          <div class="space-y-3">
            {#each detail.communication_logs as log}
              <div class="rounded-lg border border-neutral-200 p-3">
                <div class="flex items-center justify-between mb-1">
                  <div class="flex items-center gap-2">
                    <span class="text-[9px] font-semibold rounded-full px-2 py-0.5 bg-neutral-100 text-neutral-600">{log.entry_type_display}</span>
                    <p class="text-sm font-medium text-neutral-900">{log.subject}</p>
                  </div>
                  <span class="text-xs text-neutral-400">{fmtDate(log.date)}</span>
                </div>
                {#if log.summary}<p class="text-xs text-neutral-600 mt-1">{log.summary}</p>{/if}
                {#if log.action_items}<p class="text-xs text-blue-600 mt-1 font-medium">Actions: {log.action_items}</p>{/if}
              </div>
            {/each}
          </div>
        {/if}

      {:else if detailTab === "compliance"}
        <div class="grid grid-cols-2 gap-3 text-sm">
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Compliance Status</p><div class="flex items-center gap-2 mt-1"><span class="h-3 w-3 rounded-full {complianceColor(detail.compliance_status)}"></span><span class="text-neutral-900 font-medium">{detail.compliance_status_display}</span></div></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Insurance Policy</p><p class="text-neutral-900">{detail.insurance_policy || "--"}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">Insurance Expiry</p><p class="text-neutral-900">{fmtDate(detail.insurance_expiry)}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">License Number</p><p class="text-neutral-900">{detail.license_number || "--"}</p></div>
          <div><p class="text-[10px] font-semibold uppercase text-neutral-400">License Expiry</p><p class="text-neutral-900">{fmtDate(detail.license_expiry)}</p></div>
        </div>
      {/if}
    </div>
  {/if}
</DrawerShell>

<!-- ═══════════ CREATE DRAWER ═══════════ -->
<DrawerShell open={createOpen} title="Add Consultant" subtitle="Register a professional or firm" width="max-w-xl" onclose={() => (createOpen = false)}>
  <form onsubmit={saveConsultant} class="p-6 space-y-4">
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Project *</span><select bind:value={form.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"><option value="">Select</option>{#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}</select></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Discipline</span><select bind:value={form.discipline} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="architectural">Architectural</option><option value="structural">Structural</option><option value="mep">MEP</option>
        <option value="quantity_surveying">Quantity Surveying</option><option value="legal">Legal</option><option value="geotechnical">Geotechnical</option>
        <option value="environmental">Environmental</option><option value="town_planning">Town Planning</option><option value="land_surveying">Land Surveying</option>
        <option value="project_management">Project Management</option><option value="interior_design">Interior Design</option><option value="landscape">Landscape</option><option value="other">Other</option>
      </select></label>
    </div>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Firm Name *</span><input bind:value={form.firm_name} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Contact Person</span><input bind:value={form.contact_person} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Contact Role</span><input bind:value={form.contact_role} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <div class="grid grid-cols-3 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Email</span><input type="email" bind:value={form.email} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Phone</span><input bind:value={form.phone} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">WhatsApp</span><input bind:value={form.whatsapp} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Scope of Work</span><textarea bind:value={form.scope_of_work} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Contract Value</span><input type="number" step="0.01" bind:value={form.contract_value} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Reports To</span><input bind:value={form.reports_to} placeholder="e.g. Project Manager" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <div class="grid grid-cols-2 gap-4">
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Contract Start</span><input type="date" bind:value={form.contract_start_date} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
      <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Contract End</span><input type="date" bind:value={form.contract_end_date} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" /></label>
    </div>
    <label><span class="mb-1 block text-xs font-semibold text-neutral-600">Notes</span><textarea bind:value={form.notes} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm"></textarea></label>
    <div class="flex justify-end gap-2 pt-2">
      <button type="button" onclick={() => (createOpen = false)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      {#if isDev}<button type="button" onclick={devFill} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
      <button type="submit" disabled={saving} class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{saving ? "Saving..." : "Add Consultant"}</button>
    </div>
  </form>
</DrawerShell>

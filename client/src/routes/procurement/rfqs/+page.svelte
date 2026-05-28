<script lang="ts">
  import { useAutoRefresh } from "$lib/realtime.svelte";
  import { api, ApiError } from "$lib/api";
  import { fetchBudgetLineOptions, fetchCostCodeOptions, type BudgetLineOption } from "$lib/procurement";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import DrawerShell from "$lib/components/DrawerShell.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DateInput from "$lib/components/DateInput.svelte";
  import type {
    RFQListItem,
    RFQ,
    RFQQuote,
    VendorListItem,
    PurchaseRequisitionListItem,
    ProjectListItem,
    PropertyListItem,
    MasterDataEntry,
    PaginatedResponse,
    WorkflowInstanceDetail,
  } from "$lib/types";

  // ── List state ──
  let loading = $state(true);
  let creating = $state(false);
  let showCreate = $state(false);
  let pg = $state(1);
  let pageSize = $state(20);
  let totalCount = $state(0);
  let search = $state("");
  let statusFilter = $state("");

  let rfqs = $state<RFQListItem[]>([]);
  let requisitions = $state<PurchaseRequisitionListItem[]>([]);
  let projects = $state<ProjectListItem[]>([]);
  let properties = $state<PropertyListItem[]>([]);
  let budgetLines = $state<BudgetLineOption[]>([]);
  let costCodes = $state<MasterDataEntry[]>([]);
  let vendors = $state<VendorListItem[]>([]);

  let createForm = $state({
    title: "", requisition: "", project: "", property: "",
    issue_date: "", submission_deadline: "",
    budget_line_item: "", budget_code: "", cost_code: "", notes: "",
  });
  let createErrors = $state<Record<string, string[]>>({});

  function createFieldError(name: string): string { return createErrors[name]?.[0] ?? ""; }

  function formatCurrencyVal(value: string | number | null): string {
    if (value === null || value === undefined) return "—";
    const n = typeof value === "string" ? Number(value) : value;
    if (Number.isNaN(n)) return "—";
    return currency.format(n);
  }

  function formatDate(value: string | null): string {
    if (!value) return "—";
    return new Date(`${value}T00:00:00`).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  async function loadRFQs() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(pg), page_size: String(pageSize), ordering: "-created_at" };
      if (search.trim()) params.search = search.trim();
      if (statusFilter) params.status = statusFilter;
      const res = await api.get<PaginatedResponse<RFQListItem>>("/procurement/rfqs/", params);
      rfqs = res.results;
      totalCount = res.count;
    } catch {
      toast.error("Load failed", "Could not load RFQs.");
      rfqs = []; totalCount = 0;
    } finally { loading = false; }
  }

  async function loadLookups() {
    const [reqRes, projRes, propRes, bl, cc, vendorRes] = await Promise.all([
      api.get<PaginatedResponse<PurchaseRequisitionListItem>>("/procurement/requisitions/", { page_size: "200", ordering: "-created_at" })
        .catch(() => ({ results: [] as PurchaseRequisitionListItem[] } as PaginatedResponse<PurchaseRequisitionListItem>)),
      api.get<PaginatedResponse<ProjectListItem>>("/projects/", { page_size: "200", ordering: "name" })
        .catch(() => ({ results: [] as ProjectListItem[] } as PaginatedResponse<ProjectListItem>)),
      api.get<PaginatedResponse<PropertyListItem>>("/properties/", { page_size: "200", ordering: "name" })
        .catch(() => ({ results: [] as PropertyListItem[] } as PaginatedResponse<PropertyListItem>)),
      fetchBudgetLineOptions(),
      fetchCostCodeOptions(),
      api.get<PaginatedResponse<VendorListItem>>("/procurement/vendors/", { page_size: "200", ordering: "name" })
        .catch(() => ({ results: [] as VendorListItem[] } as PaginatedResponse<VendorListItem>)),
    ]);
    requisitions = reqRes.results; projects = projRes.results; properties = propRes.results;
    budgetLines = bl; costCodes = cc; vendors = vendorRes.results;
  }

  function resetCreateForm() {
    createForm = { title: "", requisition: "", project: "", property: "", issue_date: "", submission_deadline: "", budget_line_item: "", budget_code: "", cost_code: "", notes: "" };
    createErrors = {};
  }

  async function handleCreate(e: Event) {
    e.preventDefault();
    creating = true; createErrors = {};
    try {
      const payload: Record<string, unknown> = {
        title: createForm.title,
        requisition: createForm.requisition ? Number(createForm.requisition) : null,
        project: createForm.project ? Number(createForm.project) : null,
        property: createForm.property ? Number(createForm.property) : null,
        issue_date: createForm.issue_date || null,
        submission_deadline: createForm.submission_deadline || null,
        budget_line_item: createForm.budget_line_item ? Number(createForm.budget_line_item) : null,
        budget_code: createForm.budget_code, cost_code: createForm.cost_code, notes: createForm.notes,
      };
      const result = await api.post<RFQ>("/procurement/rfqs/", payload);
      toast.success("RFQ created", `${result.rfq_number} has been created.`);
      showCreate = false; resetCreateForm();
      loadRFQs();
      openDetail(result.id);
    } catch (err) {
      if (err instanceof ApiError) { createErrors = err.fieldErrors; toast.error("Validation error", "Please correct highlighted fields."); }
      else toast.error("Error", "Could not create RFQ.");
    } finally { creating = false; }
  }

  $effect(() => { loadLookups(); });
  $effect(() => { void search; void statusFilter; void pg; loadRFQs(); });

  useAutoRefresh("RFQ", loadRFQs);

  // ── Detail Drawer ──
  let showDetail = $state(false);
  let detailLoading = $state(false);
  let rfq = $state<RFQ | null>(null);
  let detailEditing = $state(false);
  let detailSaving = $state(false);
  let detailDeleting = $state(false);
  let detailErrors = $state<Record<string, string[]>>({});
  let workflow = $state<WorkflowInstanceDetail | null>(null);
  let submittingApproval = $state(false);
  let selectingVendor = $state(false);
  let addingQuote = $state(false);
  let detailTab = $state<"details" | "quotes" | "comparison">("details");
  let quotesComparison = $state<(RFQQuote & { rank: number })[]>([]);

  const isEditable = $derived(rfq != null && (rfq.status === "draft" || rfq.status === "issued" || rfq.status === "evaluation"));

  let detailForm = $state({
    title: "", status: "draft", requisition: "", project: "", property: "",
    issue_date: "", submission_deadline: "", budget_line_item: "", budget_code: "",
    cost_code: "", selected_vendor: "", selection_notes: "", notes: "",
  });

  let quoteForm = $state({
    vendor: "", quote_number: "", quote_date: "", validity_date: "",
    quoted_amount: "", delivery_days: "", warranty_terms: "", payment_terms: "",
    compliance_score: "", technical_score: "", commercial_score: "", notes: "",
  });

  function detailFieldError(name: string): string { return detailErrors[name]?.[0] ?? ""; }

  function rankClass(rank: number): string {
    if (rank === 1) return "bg-emerald-50 text-emerald-700";
    if (rank === 2) return "bg-blue-50 text-blue-700";
    if (rank === 3) return "bg-amber-50 text-amber-700";
    return "bg-neutral-100 text-neutral-600";
  }

  async function openDetail(id: number) {
    showDetail = true; detailLoading = true; detailErrors = {};
    detailTab = "details"; detailEditing = false;
    try {
      rfq = await api.get<RFQ>(`/procurement/rfqs/${id}/`);
      populateDetailForm();
      loadWorkflow(id);
      loadComparison(id);
    } catch { toast.error("Load failed", "Could not load RFQ details"); showDetail = false; }
    detailLoading = false;
  }

  function populateDetailForm() {
    if (!rfq) return;
    detailForm = {
      title: rfq.title, status: rfq.status,
      requisition: rfq.requisition ? String(rfq.requisition) : "",
      project: rfq.project ? String(rfq.project) : "",
      property: rfq.property ? String(rfq.property) : "",
      issue_date: rfq.issue_date, submission_deadline: rfq.submission_deadline || "",
      budget_line_item: rfq.budget_line_item ? String(rfq.budget_line_item) : "",
      budget_code: rfq.budget_code, cost_code: rfq.cost_code,
      selected_vendor: rfq.selected_vendor ? String(rfq.selected_vendor) : "",
      selection_notes: rfq.selection_notes, notes: rfq.notes,
    };
  }

  async function loadWorkflow(id: number) {
    try {
      const res = await api.get<{ results: WorkflowInstanceDetail[] }>("/workflows/instances/", { model: "procurement.requestforquotation", object_id: String(id) });
      workflow = res.results.length > 0 ? res.results[0] : null;
    } catch { workflow = null; }
  }

  async function loadComparison(id: number) {
    try {
      const res = await api.get<{ quotes: (RFQQuote & { rank: number })[] }>(`/procurement/rfqs/${id}/comparison/`);
      quotesComparison = res.quotes;
    } catch { quotesComparison = []; }
  }

  async function saveDetail() {
    if (!rfq) return;
    detailErrors = {}; detailSaving = true;
    try {
      const payload: Record<string, unknown> = {
        title: detailForm.title, status: detailForm.status,
        requisition: detailForm.requisition ? Number(detailForm.requisition) : null,
        project: detailForm.project ? Number(detailForm.project) : null,
        property: detailForm.property ? Number(detailForm.property) : null,
        issue_date: detailForm.issue_date || null,
        submission_deadline: detailForm.submission_deadline || null,
        budget_line_item: detailForm.budget_line_item ? Number(detailForm.budget_line_item) : null,
        budget_code: detailForm.budget_code, cost_code: detailForm.cost_code,
        selected_vendor: detailForm.selected_vendor ? Number(detailForm.selected_vendor) : null,
        selection_notes: detailForm.selection_notes, notes: detailForm.notes,
      };
      await api.patch<RFQ>(`/procurement/rfqs/${rfq.id}/`, payload);
      toast.success("Saved", "RFQ updated.");
      detailEditing = false;
      await openDetail(rfq.id); loadRFQs();
    } catch (err) {
      if (err instanceof ApiError) { detailErrors = err.fieldErrors; toast.error("Validation error", "Please review the form."); }
      else toast.error("Error", "Could not save RFQ.");
    }
    detailSaving = false;
  }

  async function deleteRFQ() {
    if (!rfq || !confirm("Delete this RFQ? This cannot be undone.")) return;
    detailDeleting = true;
    try {
      await api.delete(`/procurement/rfqs/${rfq.id}/`);
      toast.success("Deleted", "RFQ deleted.");
      showDetail = false; loadRFQs();
    } catch { toast.error("Error", "Could not delete RFQ."); }
    detailDeleting = false;
  }

  async function submitForApproval() {
    if (!rfq) return;
    submittingApproval = true;
    try {
      await api.post(`/procurement/rfqs/${rfq.id}/submit-approval/`, {});
      toast.success("Submitted", "RFQ submitted for approval.");
      await openDetail(rfq.id); loadRFQs();
    } catch { toast.error("Error", "Could not submit RFQ for approval."); }
    submittingApproval = false;
  }

  async function selectVendor(quoteId: number) {
    if (!rfq) return;
    selectingVendor = true;
    try {
      await api.post(`/procurement/rfqs/${rfq.id}/select-vendor/`, { quote_id: quoteId, selection_notes: detailForm.selection_notes });
      toast.success("Vendor selected", "Winning quote selected.");
      await openDetail(rfq.id); loadRFQs();
    } catch { toast.error("Error", "Could not select vendor."); }
    selectingVendor = false;
  }

  async function addQuote(e: Event) {
    e.preventDefault();
    if (!rfq) return;
    addingQuote = true;
    try {
      await api.post(`/procurement/rfqs/${rfq.id}/quotes/`, {
        vendor: quoteForm.vendor ? Number(quoteForm.vendor) : null,
        quote_number: quoteForm.quote_number,
        quote_date: quoteForm.quote_date || null,
        validity_date: quoteForm.validity_date || null,
        quoted_amount: quoteForm.quoted_amount || "0",
        delivery_days: quoteForm.delivery_days ? Number(quoteForm.delivery_days) : null,
        warranty_terms: quoteForm.warranty_terms, payment_terms: quoteForm.payment_terms,
        compliance_score: quoteForm.compliance_score || "0",
        technical_score: quoteForm.technical_score || "0",
        commercial_score: quoteForm.commercial_score || "0",
        notes: quoteForm.notes,
      });
      quoteForm = { vendor: "", quote_number: "", quote_date: "", validity_date: "", quoted_amount: "", delivery_days: "", warranty_terms: "", payment_terms: "", compliance_score: "", technical_score: "", commercial_score: "", notes: "" };
      toast.success("Quote added", "Vendor quote recorded.");
      await openDetail(rfq.id); loadRFQs();
    } catch { toast.error("Error", "Could not add quote."); }
    addingQuote = false;
  }

  async function removeQuote(quoteId: number) {
    if (!rfq || !confirm("Delete this quote?")) return;
    try {
      await api.delete(`/procurement/rfqs/${rfq.id}/quotes/${quoteId}/`);
      toast.success("Deleted", "Quote removed.");
      await openDetail(rfq.id);
    } catch { toast.error("Error", "Could not delete quote."); }
  }

  function closeDetail() { showDetail = false; rfq = null; workflow = null; detailErrors = {}; quotesComparison = []; }
</script>

<div class="space-y-6">
  <div class="flex items-center justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-700">Procurement</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">RFQs</h1>
      <p class="text-sm text-neutral-400 mt-1">Manage request-for-quotation cycles and vendor evaluations.</p>
    </div>
    <button onclick={() => { resetCreateForm(); showCreate = true; }}
      class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors">
      + New RFQ
    </button>
  </div>

  <div class="bg-white rounded-xl border border-neutral-200 p-4">
    <div class="grid grid-cols-1 md:grid-cols-4 gap-3">
      <input bind:value={search} placeholder="Search RFQ #, title, budget code..."
        class="md:col-span-2 px-3 py-2.5 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
      <select bind:value={statusFilter}
        class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent">
        <option value="">All statuses</option>
        <option value="draft">Draft</option>
        <option value="issued">Issued</option>
        <option value="evaluation">Evaluation</option>
        <option value="submitted">Submitted</option>
        <option value="approved">Approved</option>
        <option value="cancelled">Cancelled</option>
        <option value="closed">Closed</option>
      </select>
      <button onclick={() => { pg = 1; loadRFQs(); }}
        class="px-3 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800">Apply</button>
    </div>
  </div>

  <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
    {#if loading}
      <div class="py-20 text-center">
        <div class="inline-block w-5 h-5 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div>
      </div>
    {:else if rfqs.length === 0}
      <div class="py-16 text-center">
        <p class="text-sm text-neutral-500">No RFQs found.</p>
      </div>
    {:else}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50">
            <th class="px-5 py-3 text-left text-xs uppercase tracking-wider text-neutral-500 font-semibold">RFQ</th>
            <th class="px-5 py-3 text-left text-xs uppercase tracking-wider text-neutral-500 font-semibold">Status</th>
            <th class="px-5 py-3 text-left text-xs uppercase tracking-wider text-neutral-500 font-semibold">Deadline</th>
            <th class="px-5 py-3 text-left text-xs uppercase tracking-wider text-neutral-500 font-semibold">Selected Vendor</th>
            <th class="px-5 py-3 text-right text-xs uppercase tracking-wider text-neutral-500 font-semibold">Lowest Quote</th>
            <th class="px-5 py-3 text-right text-xs uppercase tracking-wider text-neutral-500 font-semibold">Quotes</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each rfqs as r}
            <tr class="hover:bg-neutral-50 cursor-pointer transition-colors" onclick={() => openDetail(r.id)}>
              <td class="px-5 py-4">
                <p class="font-medium text-neutral-900">{r.rfq_number}</p>
                <p class="text-xs text-neutral-500 truncate max-w-[280px]">{r.title}</p>
              </td>
              <td class="px-5 py-4"><StatusBadge status={r.status} /></td>
              <td class="px-5 py-4 text-neutral-600">{formatDate(r.submission_deadline)}</td>
              <td class="px-5 py-4 text-neutral-700">{r.selected_vendor_name || "—"}</td>
              <td class="px-5 py-4 text-right text-neutral-900 tabular-nums">{formatCurrencyVal(r.lowest_quote)}</td>
              <td class="px-5 py-4 text-right text-neutral-700 tabular-nums">{r.quote_count}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>

  <div class="flex items-center justify-between text-sm text-neutral-500">
    <p>Showing {totalCount === 0 ? 0 : (pg - 1) * pageSize + 1} to {Math.min(pg * pageSize, totalCount)} of {totalCount}</p>
    <div class="flex items-center gap-2">
      <button onclick={() => pg--} disabled={pg <= 1} class="px-3 py-1.5 border border-neutral-200 rounded-lg disabled:opacity-40">Prev</button>
      <span>Page {pg}</span>
      <button onclick={() => pg++} disabled={pg * pageSize >= totalCount} class="px-3 py-1.5 border border-neutral-200 rounded-lg disabled:opacity-40">Next</button>
    </div>
  </div>
</div>

<!-- Create RFQ Modal -->
{#if showCreate}
  <div class="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4">
    <div class="w-full max-w-3xl bg-white rounded-2xl border border-neutral-200 shadow-xl max-h-[92vh] overflow-y-auto">
      <div class="sticky top-0 bg-white border-b border-neutral-100 px-6 py-4 flex items-center justify-between">
        <h2 class="text-lg font-semibold text-neutral-900">Create RFQ</h2>
        <button onclick={() => (showCreate = false)} class="text-sm text-neutral-500 hover:text-neutral-900">Close</button>
      </div>
      <form class="p-6 space-y-4" onsubmit={handleCreate}>
        <label class="block">
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Title</span>
          <input bind:value={createForm.title} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm" />
          {#if createFieldError("title")}<p class="mt-1 text-xs text-red-500">{createFieldError("title")}</p>{/if}
        </label>
        <div class="grid grid-cols-2 gap-4">
          <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Requisition (optional)</span>
            <select bind:value={createForm.requisition} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm">
              <option value="">None</option>
              {#each requisitions as req}<option value={String(req.id)}>{req.pr_number} - {req.title}</option>{/each}
            </select>
          </label>
          <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Project (optional)</span>
            <select bind:value={createForm.project} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm">
              <option value="">None</option>
              {#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}
            </select>
          </label>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Issue Date</span>
            <DateInput bind:value={createForm.issue_date} />
          </label>
          <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Submission Deadline</span>
            <DateInput bind:value={createForm.submission_deadline} />
          </label>
        </div>
        <label><span class="block text-sm font-medium text-neutral-700 mb-1.5">Notes</span>
          <textarea rows={3} bind:value={createForm.notes} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm resize-none"></textarea>
        </label>
        <div class="flex items-center justify-end gap-3 pt-2">
          <button type="button" onclick={() => (showCreate = false)} class="px-4 py-2 text-sm font-medium text-neutral-600 hover:text-neutral-900">Cancel</button>
          <button type="submit" disabled={creating} class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50">
            {creating ? "Creating..." : "Create RFQ"}
          </button>
        </div>
      </form>
    </div>
  </div>
{/if}

<!-- Detail Drawer -->
<DrawerShell open={showDetail} onclose={closeDetail} title={rfq?.rfq_number ?? "RFQ"} subtitle={rfq?.title ?? ""} width="max-w-2xl" model="RFQ" recordId={rfq?.id ?? null}>
  {#snippet badges()}
    {#if rfq}
      <StatusBadge status={rfq.status} />
      {#if rfq.selected_vendor_name}
        <span class="inline-flex items-center rounded-full bg-emerald-900/30 px-2 py-0.5 text-[10px] font-semibold text-emerald-300">Awarded</span>
      {/if}
      {#if workflow}<StatusBadge status={workflow.state} />{/if}
    {/if}
  {/snippet}

  {#if detailLoading}
    <div class="flex items-center justify-center py-24">
      <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
    </div>
  {:else if rfq}
    <!-- Summary strip -->
    <div class="px-6 py-4 border-b border-neutral-100 bg-neutral-50/50">
      <div class="grid grid-cols-4 gap-4 text-sm">
        <div>
          <p class="text-neutral-400 text-xs">Issue Date</p>
          <p class="font-semibold text-neutral-900">{formatDate(rfq.issue_date)}</p>
        </div>
        <div>
          <p class="text-neutral-400 text-xs">Deadline</p>
          <p class="font-semibold text-neutral-900">{formatDate(rfq.submission_deadline)}</p>
        </div>
        <div>
          <p class="text-neutral-400 text-xs">Quotes</p>
          <p class="font-semibold text-neutral-900">{rfq.quotes?.length ?? 0}</p>
        </div>
        <div>
          <p class="text-neutral-400 text-xs">Lowest Quote</p>
          <p class="font-semibold text-neutral-900 tabular-nums">{formatCurrencyVal(rfq.lowest_quote)}</p>
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div class="px-6 py-3 border-b border-neutral-100 flex gap-2 flex-wrap">
      {#if rfq.status === "draft" || rfq.status === "issued" || rfq.status === "evaluation"}
        <button onclick={submitForApproval} disabled={submittingApproval}
          class="px-3 py-1.5 bg-neutral-900 text-white rounded-lg text-xs font-medium hover:bg-neutral-800 disabled:opacity-50">
          {submittingApproval ? "Submitting..." : "Submit for Approval"}
        </button>
      {/if}
      {#if isEditable}
        <button onclick={deleteRFQ} disabled={detailDeleting}
          class="px-3 py-1.5 border border-red-200 text-red-600 rounded-lg text-xs font-medium hover:bg-red-50 disabled:opacity-50 ml-auto">
          {detailDeleting ? "Deleting..." : "Delete"}
        </button>
      {/if}
    </div>

    <!-- Tabs -->
    <div class="px-6 pt-4 border-b border-neutral-100 flex gap-6">
      <button onclick={() => detailTab = "details"}
        class="pb-3 text-sm font-medium border-b-2 transition-colors {detailTab === 'details' ? 'border-neutral-900 text-neutral-900' : 'border-transparent text-neutral-400 hover:text-neutral-600'}">
        Details
      </button>
      <button onclick={() => detailTab = "quotes"}
        class="pb-3 text-sm font-medium border-b-2 transition-colors {detailTab === 'quotes' ? 'border-neutral-900 text-neutral-900' : 'border-transparent text-neutral-400 hover:text-neutral-600'}">
        Quotes ({rfq.quotes?.length ?? 0})
      </button>
      <button onclick={() => detailTab = "comparison"}
        class="pb-3 text-sm font-medium border-b-2 transition-colors {detailTab === 'comparison' ? 'border-neutral-900 text-neutral-900' : 'border-transparent text-neutral-400 hover:text-neutral-600'}">
        Comparison
      </button>
    </div>

    {#if detailTab === "details"}
      {#if detailEditing}
        <!-- ── Edit Mode ── -->
        <div class="p-6 space-y-4">
          <label class="block"><span class="block text-xs font-medium text-neutral-500 mb-1">Title</span>
            <input bind:value={detailForm.title} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
            {#if detailFieldError("title")}<p class="mt-1 text-xs text-red-500">{detailFieldError("title")}</p>{/if}
          </label>
          <div class="grid grid-cols-2 gap-3">
            <label class="block"><span class="block text-xs font-medium text-neutral-500 mb-1">Requisition</span>
              <select bind:value={detailForm.requisition} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent">
                <option value="">None</option>
                {#each requisitions as req}<option value={String(req.id)}>{req.pr_number} - {req.title}</option>{/each}
              </select>
            </label>
            <label class="block"><span class="block text-xs font-medium text-neutral-500 mb-1">Project</span>
              <select bind:value={detailForm.project} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent">
                <option value="">None</option>
                {#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}
              </select>
            </label>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <label class="block"><span class="block text-xs font-medium text-neutral-500 mb-1">Issue Date</span>
              <DateInput bind:value={detailForm.issue_date} />
            </label>
            <label class="block"><span class="block text-xs font-medium text-neutral-500 mb-1">Submission Deadline</span>
              <DateInput bind:value={detailForm.submission_deadline} />
            </label>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <label class="block"><span class="block text-xs font-medium text-neutral-500 mb-1">Budget Line</span>
              <select bind:value={detailForm.budget_line_item} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent">
                <option value="">None</option>
                {#each budgetLines as line}<option value={String(line.id)}>{line.label}</option>{/each}
              </select>
            </label>
            <label class="block"><span class="block text-xs font-medium text-neutral-500 mb-1">Budget Code</span>
              <input bind:value={detailForm.budget_code} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
            </label>
          </div>
          <label class="block"><span class="block text-xs font-medium text-neutral-500 mb-1">Cost Code</span>
            <select bind:value={detailForm.cost_code} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent">
              <option value="">None</option>
              {#each costCodes as code}<option value={code.code}>{code.code} - {code.label}</option>{/each}
            </select>
          </label>
          <label class="block"><span class="block text-xs font-medium text-neutral-500 mb-1">Selection Notes</span>
            <textarea bind:value={detailForm.selection_notes} rows="2" class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"></textarea>
          </label>
          <label class="block"><span class="block text-xs font-medium text-neutral-500 mb-1">Notes</span>
            <textarea bind:value={detailForm.notes} rows="2" class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"></textarea>
          </label>
        </div>
        <div class="sticky bottom-0 bg-white border-t border-neutral-100 px-6 py-4 flex gap-3">
          <div class="flex-1"></div>
          <button onclick={() => { detailEditing = false; populateDetailForm(); detailErrors = {}; }}
            class="px-4 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
          <button onclick={saveDetail} disabled={detailSaving}
            class="px-5 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50">
            {detailSaving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      {:else}
        <!-- ── View Mode ── -->
        <div class="p-6 space-y-4">
          {#if isEditable}
            <div class="flex justify-end">
              <button onclick={() => detailEditing = true}
                class="px-3 py-1.5 border border-neutral-200 rounded-lg text-xs font-medium text-neutral-700 hover:bg-neutral-50 flex items-center gap-1.5">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" /></svg>
                Edit
              </button>
            </div>
          {/if}
          <div class="grid grid-cols-2 gap-x-6 gap-y-4">
            <div class="col-span-2">
              <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-1">Title</p>
              <p class="text-sm text-neutral-900">{rfq.title || "—"}</p>
            </div>
            <div>
              <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-1">Requisition</p>
              <p class="text-sm text-neutral-900">{rfq.requisition_number || "—"}</p>
            </div>
            <div>
              <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-1">Project</p>
              <p class="text-sm text-neutral-900">{rfq.project_name || "—"}</p>
            </div>
            <div>
              <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-1">Property</p>
              <p class="text-sm text-neutral-900">{rfq.property_name || "—"}</p>
            </div>
            <div>
              <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-1">Budget Code</p>
              <p class="text-sm text-neutral-900">{rfq.budget_code || "—"}</p>
            </div>
            <div>
              <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-1">Cost Code</p>
              <p class="text-sm text-neutral-900">{rfq.cost_code || "—"}</p>
            </div>
            {#if rfq.selected_vendor_name}
              <div>
                <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-1">Selected Vendor</p>
                <p class="text-sm text-emerald-700 font-semibold">{rfq.selected_vendor_name}</p>
              </div>
            {/if}
          </div>
          {#if rfq.selection_notes}
            <div class="border-t border-neutral-100 pt-4">
              <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-1">Selection Notes</p>
              <p class="text-sm text-neutral-700 whitespace-pre-line">{rfq.selection_notes}</p>
            </div>
          {/if}
          {#if rfq.notes}
            <div class="border-t border-neutral-100 pt-4">
              <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-1">Notes</p>
              <p class="text-sm text-neutral-700 whitespace-pre-line">{rfq.notes}</p>
            </div>
          {/if}
        </div>
      {/if}

    {:else if detailTab === "quotes"}
      <div class="p-6">
        {#if rfq.quotes && rfq.quotes.length > 0}
          <div class="rounded-xl border border-neutral-200 overflow-hidden mb-4">
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b border-neutral-200 bg-neutral-50">
                  <th class="px-4 py-2.5 text-left text-xs font-medium text-neutral-400 uppercase">Vendor</th>
                  <th class="px-4 py-2.5 text-right text-xs font-medium text-neutral-400 uppercase">Amount</th>
                  <th class="px-4 py-2.5 text-right text-xs font-medium text-neutral-400 uppercase">Score</th>
                  <th class="px-4 py-2.5 text-center text-xs font-medium text-neutral-400 uppercase">Status</th>
                  {#if isEditable}<th class="px-4 py-2.5 w-20"></th>{/if}
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100">
                {#each rfq.quotes as quote}
                  <tr class="hover:bg-neutral-50 {quote.status === 'winner' ? 'bg-emerald-50/50' : ''}">
                    <td class="px-4 py-3">
                      <p class="text-neutral-900 font-medium">{quote.vendor_name}</p>
                      <p class="text-[10px] text-neutral-400">{quote.quote_number || "No ref"}</p>
                    </td>
                    <td class="px-4 py-3 text-right text-neutral-900 tabular-nums font-medium">{formatCurrencyVal(quote.quoted_amount)}</td>
                    <td class="px-4 py-3 text-right tabular-nums">{Number(quote.total_score).toFixed(1)}</td>
                    <td class="px-4 py-3 text-center"><StatusBadge status={quote.status} /></td>
                    {#if isEditable}
                      <td class="px-4 py-3 text-right space-x-2">
                        {#if quote.status !== "winner"}
                          <button onclick={() => selectVendor(quote.id)} disabled={selectingVendor}
                            class="text-[10px] font-semibold text-emerald-600 hover:text-emerald-800">Award</button>
                        {/if}
                        <button onclick={() => removeQuote(quote.id)} class="text-[10px] text-neutral-400 hover:text-red-600">Delete</button>
                      </td>
                    {/if}
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {:else}
          <div class="text-center py-8">
            <p class="text-sm text-neutral-400">{isEditable ? "No quotes yet. Add your first quote below." : "No quotes on this RFQ."}</p>
          </div>
        {/if}

        {#if isEditable}
          <form class="rounded-xl border border-neutral-200 p-4 space-y-3" onsubmit={addQuote}>
            <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest">Add Quote</p>
            <label class="block"><span class="block text-xs font-medium text-neutral-500 mb-1">Vendor</span>
              <select bind:value={quoteForm.vendor} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent">
                <option value="">Select vendor</option>
                {#each vendors as v}<option value={String(v.id)}>{v.name}</option>{/each}
              </select>
            </label>
            <div class="grid grid-cols-2 gap-3">
              <label class="block"><span class="block text-xs font-medium text-neutral-500 mb-1">Quote #</span>
                <input bind:value={quoteForm.quote_number} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
              </label>
              <label class="block"><span class="block text-xs font-medium text-neutral-500 mb-1">Quote Date</span>
                <DateInput bind:value={quoteForm.quote_date} />
              </label>
            </div>
            <div class="grid grid-cols-2 gap-3">
              <label class="block"><span class="block text-xs font-medium text-neutral-500 mb-1">Amount</span>
                <input type="number" step="0.01" bind:value={quoteForm.quoted_amount} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
              </label>
              <label class="block"><span class="block text-xs font-medium text-neutral-500 mb-1">Delivery Days</span>
                <input type="number" bind:value={quoteForm.delivery_days} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
              </label>
            </div>
            <div class="grid grid-cols-3 gap-3">
              <label class="block"><span class="block text-xs font-medium text-neutral-500 mb-1">Technical</span>
                <input type="number" step="0.01" bind:value={quoteForm.technical_score} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
              </label>
              <label class="block"><span class="block text-xs font-medium text-neutral-500 mb-1">Commercial</span>
                <input type="number" step="0.01" bind:value={quoteForm.commercial_score} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
              </label>
              <label class="block"><span class="block text-xs font-medium text-neutral-500 mb-1">Compliance</span>
                <input type="number" step="0.01" bind:value={quoteForm.compliance_score} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
              </label>
            </div>
            <button type="submit" disabled={addingQuote}
              class="w-full px-4 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50">
              {addingQuote ? "Adding..." : "Add Quote"}
            </button>
          </form>
        {/if}
      </div>

    {:else}
      <!-- Comparison tab -->
      <div class="p-6">
        {#if quotesComparison.length === 0}
          <div class="text-center py-8">
            <p class="text-sm text-neutral-400">No comparison data. Add vendor quotes to generate the matrix.</p>
          </div>
        {:else}
          <div class="rounded-xl border border-neutral-200 overflow-hidden">
            <div class="overflow-x-auto">
              <table class="w-full text-sm">
                <thead>
                  <tr class="border-b border-neutral-100 bg-neutral-50">
                    <th class="px-3 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase">#</th>
                    <th class="px-3 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase">Vendor</th>
                    <th class="px-3 py-2.5 text-right text-[10px] font-semibold text-neutral-500 uppercase">Amount</th>
                    <th class="px-3 py-2.5 text-center text-[10px] font-semibold text-neutral-500 uppercase">Days</th>
                    <th class="px-3 py-2.5 text-center text-[10px] font-semibold text-neutral-900 uppercase">Score</th>
                    <th class="px-3 py-2.5 text-center text-[10px] font-semibold text-neutral-500 uppercase">Status</th>
                    {#if isEditable}<th class="px-3 py-2.5 w-16"></th>{/if}
                  </tr>
                </thead>
                <tbody class="divide-y divide-neutral-50">
                  {#each quotesComparison as quote}
                    <tr class="{quote.status === 'winner' ? 'bg-emerald-50/50' : ''} hover:bg-neutral-50">
                      <td class="px-3 py-3">
                        <span class={`inline-flex items-center justify-center h-6 w-6 rounded-full text-[10px] font-bold ${rankClass(quote.rank)}`}>#{quote.rank}</span>
                      </td>
                      <td class="px-3 py-3">
                        <p class="font-medium text-neutral-900">{quote.vendor_name}</p>
                        <p class="text-[10px] text-neutral-400">{quote.quote_number || "No ref"}</p>
                      </td>
                      <td class="px-3 py-3 text-right font-bold text-neutral-900 tabular-nums">{formatCurrencyVal(quote.quoted_amount)}</td>
                      <td class="px-3 py-3 text-center">
                        {#if quote.delivery_days}
                          <span class="rounded-full px-2 py-0.5 text-[10px] font-semibold tabular-nums {quote.delivery_days <= 7 ? 'bg-emerald-100 text-emerald-700' : quote.delivery_days <= 21 ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-700'}">{quote.delivery_days}d</span>
                        {:else}—{/if}
                      </td>
                      <td class="px-3 py-3 text-center">
                        <span class="text-lg font-bold {Number(quote.total_score) >= 80 ? 'text-emerald-700' : Number(quote.total_score) >= 60 ? 'text-amber-700' : 'text-red-700'} tabular-nums">{Number(quote.total_score).toFixed(1)}</span>
                      </td>
                      <td class="px-3 py-3 text-center"><StatusBadge status={quote.status} /></td>
                      {#if isEditable}
                        <td class="px-3 py-3 text-center">
                          {#if quote.status !== "winner"}
                            <button onclick={() => selectVendor(quote.id)} disabled={selectingVendor}
                              class="rounded-md bg-emerald-600 px-2 py-1 text-[10px] font-semibold text-white hover:bg-emerald-700 disabled:opacity-50">Award</button>
                          {:else}
                            <span class="text-[10px] font-semibold text-emerald-600">Awarded</span>
                          {/if}
                        </td>
                      {/if}
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
            {#if quotesComparison.length >= 2}
              {#if true}
                {@const amounts = quotesComparison.map(q => Number(q.quoted_amount))}
                {@const minAmt = Math.min(...amounts)}
                {@const maxAmt = Math.max(...amounts)}
                {@const spread = maxAmt - minAmt}
                <div class="border-t border-neutral-100 bg-neutral-50 px-4 py-3 flex flex-wrap gap-4 text-[10px]">
                  <span class="text-neutral-500">Range: <strong class="text-neutral-900">{formatCurrencyVal(String(minAmt))}</strong> — <strong class="text-neutral-900">{formatCurrencyVal(String(maxAmt))}</strong></span>
                  <span class="text-neutral-500">Spread: <strong class="{spread > minAmt * 0.3 ? 'text-red-600' : 'text-emerald-600'}">{formatCurrencyVal(String(spread))}</strong> ({minAmt > 0 ? (spread / minAmt * 100).toFixed(0) : 0}%)</span>
                </div>
              {/if}
            {/if}
          </div>
        {/if}
      </div>
    {/if}
  {/if}
</DrawerShell>

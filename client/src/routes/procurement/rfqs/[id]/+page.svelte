<script lang="ts">
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { fetchBudgetLineOptions, fetchCostCodeOptions, type BudgetLineOption } from "$lib/procurement";
  import { toast } from "$lib/stores/toast.svelte";
  import Breadcrumb from "$lib/components/Breadcrumb.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import ApprovalTimeline from "$lib/components/workflows/ApprovalTimeline.svelte";
  import DecisionPanel from "$lib/components/workflows/DecisionPanel.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import type {
    RFQ,
    RFQQuote,
    VendorListItem,
    PurchaseRequisitionListItem,
    ProjectListItem,
    PropertyListItem,
    MasterDataEntry,
    WorkflowInstanceDetail,
    PaginatedResponse,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  const id = $derived($page.params.id ?? "");

  let rfq = $state<RFQ | null>(null);
  let loading = $state(true);
  let saving = $state(false);
  let deleting = $state(false);
  let submittingApproval = $state(false);
  let selectingVendor = $state(false);
  let addingQuote = $state(false);
  let errors = $state<Record<string, string[]>>({});

  let workflow = $state<WorkflowInstanceDetail | null>(null);
  let quotesComparison = $state<(RFQQuote & { rank: number })[]>([]);

  let vendors = $state<VendorListItem[]>([]);
  let requisitions = $state<PurchaseRequisitionListItem[]>([]);
  let projects = $state<ProjectListItem[]>([]);
  let properties = $state<PropertyListItem[]>([]);
  let budgetLines = $state<BudgetLineOption[]>([]);
  let costCodes = $state<MasterDataEntry[]>([]);

  let form = $state({
    title: "",
    status: "draft",
    requisition: "",
    project: "",
    property: "",
    issue_date: "",
    submission_deadline: "",
    budget_line_item: "",
    budget_code: "",
    cost_code: "",
    selected_vendor: "",
    selection_notes: "",
    notes: "",
  });

  let quoteForm = $state({
    vendor: "",
    quote_number: "",
    quote_date: "",
    validity_date: "",
    quoted_amount: "",
    delivery_days: "",
    warranty_terms: "",
    payment_terms: "",
    compliance_score: "",
    technical_score: "",
    commercial_score: "",
    notes: "",
  });

  const rfqQuotes = $derived.by(() => rfq?.quotes ?? []);

  function fieldError(name: string): string {
    return errors[name]?.[0] ?? "";
  }

  function formatCurrency(value: string | number | null): string {
    if (value === null || value === undefined || value === "") return "—";
    const n = typeof value === "string" ? Number(value) : value;
    if (Number.isNaN(n)) return "—";
    return currency.format(n);
  }

  function formatDate(value: string | null): string {
    if (!value) return "—";
    const d = new Date(`${value}T00:00:00`);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  function rankClass(rank: number): string {
    if (rank === 1) return "bg-emerald-50 text-emerald-700";
    if (rank === 2) return "bg-blue-50 text-blue-700";
    if (rank === 3) return "bg-amber-50 text-amber-700";
    return "bg-neutral-100 text-neutral-600";
  }

  async function loadRFQ() {
    if (!id) {
      rfq = null;
      loading = false;
      return;
    }
    loading = true;
    try {
      rfq = await api.get<RFQ>(`/procurement/rfqs/${id}/`);
      form = {
        title: rfq.title,
        status: rfq.status,
        requisition: rfq.requisition ? String(rfq.requisition) : "",
        project: rfq.project ? String(rfq.project) : "",
        property: rfq.property ? String(rfq.property) : "",
        issue_date: rfq.issue_date,
        submission_deadline: rfq.submission_deadline || "",
        budget_line_item: rfq.budget_line_item ? String(rfq.budget_line_item) : "",
        budget_code: rfq.budget_code,
        cost_code: rfq.cost_code,
        selected_vendor: rfq.selected_vendor ? String(rfq.selected_vendor) : "",
        selection_notes: rfq.selection_notes,
        notes: rfq.notes,
      };
    } catch {
      rfq = null;
      toast.error("Load failed", "Could not load RFQ details.");
    } finally {
      loading = false;
    }
  }

  async function loadWorkflow() {
    if (!id) {
      workflow = null;
      return;
    }
    try {
      const res = await api.get<{ results: WorkflowInstanceDetail[] }>("/workflows/instances/", {
        model: "procurement.requestforquotation",
        object_id: id,
      });
      workflow = res.results.length > 0 ? res.results[0] : null;
    } catch {
      workflow = null;
    }
  }

  async function loadComparison() {
    if (!id) {
      quotesComparison = [];
      return;
    }
    try {
      const res = await api.get<{ quotes: (RFQQuote & { rank: number })[] }>(`/procurement/rfqs/${id}/comparison/`);
      quotesComparison = res.quotes;
    } catch {
      quotesComparison = [];
    }
  }

  async function loadLookups() {
    const [vendorRes, requisitionRes, projectRes, propertyRes, fetchedBudgetLines, fetchedCostCodes] = await Promise.all([
      api.get<PaginatedResponse<VendorListItem>>("/procurement/vendors/", { page_size: "200", ordering: "name" }).catch(
        () => ({ results: [] as VendorListItem[] } as PaginatedResponse<VendorListItem>)
      ),
      api
        .get<PaginatedResponse<PurchaseRequisitionListItem>>("/procurement/requisitions/", {
          page_size: "200",
          ordering: "-created_at",
        })
        .catch(() => ({ results: [] as PurchaseRequisitionListItem[] } as PaginatedResponse<PurchaseRequisitionListItem>)),
      api.get<PaginatedResponse<ProjectListItem>>("/projects/", { page_size: "200", ordering: "name" }).catch(
        () => ({ results: [] as ProjectListItem[] } as PaginatedResponse<ProjectListItem>)
      ),
      api.get<PaginatedResponse<PropertyListItem>>("/properties/", { page_size: "200", ordering: "name" }).catch(
        () => ({ results: [] as PropertyListItem[] } as PaginatedResponse<PropertyListItem>)
      ),
      fetchBudgetLineOptions(),
      fetchCostCodeOptions(),
    ]);

    vendors = vendorRes.results;
    requisitions = requisitionRes.results;
    projects = projectRes.results;
    properties = propertyRes.results;
    budgetLines = fetchedBudgetLines;
    costCodes = fetchedCostCodes;
  }

  async function saveRFQ(e: Event) {
    e.preventDefault();
    if (!rfq || !id) return;
    saving = true;
    errors = {};

    try {
      const payload: Record<string, unknown> = {
        title: form.title,
        status: form.status,
        requisition: form.requisition ? Number(form.requisition) : null,
        project: form.project ? Number(form.project) : null,
        property: form.property ? Number(form.property) : null,
        issue_date: form.issue_date || null,
        submission_deadline: form.submission_deadline || null,
        budget_line_item: form.budget_line_item ? Number(form.budget_line_item) : null,
        budget_code: form.budget_code,
        cost_code: form.cost_code,
        selected_vendor: form.selected_vendor ? Number(form.selected_vendor) : null,
        selection_notes: form.selection_notes,
        notes: form.notes,
      };
      rfq = await api.patch<RFQ>(`/procurement/rfqs/${id}/`, payload);
      toast.success("Saved", "RFQ details updated.");
      await Promise.all([loadComparison(), loadWorkflow()]);
    } catch (err) {
      if (err instanceof ApiError) {
        errors = err.fieldErrors;
        toast.error("Validation error", "Please review the form.");
      } else {
        toast.error("Error", "Could not save RFQ.");
      }
    } finally {
      saving = false;
    }
  }

  async function deleteRFQ() {
    if (!rfq || !id) return;
    if (!confirm("Delete this RFQ? This action cannot be undone.")) return;
    deleting = true;
    try {
      await api.delete(`/procurement/rfqs/${id}/`);
      toast.success("Deleted", "RFQ deleted.");
      goto("/procurement/rfqs");
    } catch {
      toast.error("Error", "Could not delete RFQ.");
    } finally {
      deleting = false;
    }
  }

  async function submitForApproval() {
    if (!id) return;
    submittingApproval = true;
    try {
      await api.post(`/procurement/rfqs/${id}/submit-approval/`, {});
      toast.success("Submitted", "RFQ submitted for approval.");
      await Promise.all([loadRFQ(), loadWorkflow()]);
    } catch {
      toast.error("Error", "Could not submit RFQ for approval.");
    } finally {
      submittingApproval = false;
    }
  }

  async function selectVendor(quoteId: number) {
    if (!id) return;
    selectingVendor = true;
    try {
      await api.post(`/procurement/rfqs/${id}/select-vendor/`, {
        quote_id: quoteId,
        selection_notes: form.selection_notes,
      });
      toast.success("Vendor selected", "Winning quote selected.");
      await Promise.all([loadRFQ(), loadComparison()]);
    } catch {
      toast.error("Error", "Could not select vendor.");
    } finally {
      selectingVendor = false;
    }
  }

  async function addQuote(e: Event) {
    e.preventDefault();
    if (!id) return;
    addingQuote = true;
    try {
      await api.post(`/procurement/rfqs/${id}/quotes/`, {
        vendor: quoteForm.vendor ? Number(quoteForm.vendor) : null,
        quote_number: quoteForm.quote_number,
        quote_date: quoteForm.quote_date || null,
        validity_date: quoteForm.validity_date || null,
        quoted_amount: quoteForm.quoted_amount || "0",
        delivery_days: quoteForm.delivery_days ? Number(quoteForm.delivery_days) : null,
        warranty_terms: quoteForm.warranty_terms,
        payment_terms: quoteForm.payment_terms,
        compliance_score: quoteForm.compliance_score || "0",
        technical_score: quoteForm.technical_score || "0",
        commercial_score: quoteForm.commercial_score || "0",
        notes: quoteForm.notes,
      });
      quoteForm = {
        vendor: "",
        quote_number: "",
        quote_date: "",
        validity_date: "",
        quoted_amount: "",
        delivery_days: "",
        warranty_terms: "",
        payment_terms: "",
        compliance_score: "",
        technical_score: "",
        commercial_score: "",
        notes: "",
      };
      toast.success("Quote added", "Vendor quote has been recorded.");
      await Promise.all([loadRFQ(), loadComparison()]);
    } catch {
      toast.error("Error", "Could not add quote.");
    } finally {
      addingQuote = false;
    }
  }

  async function removeQuote(quoteId: number) {
    if (!id) return;
    if (!confirm("Delete this quote?")) return;
    try {
      await api.delete(`/procurement/rfqs/${id}/quotes/${quoteId}/`);
      toast.success("Deleted", "Quote removed.");
      await Promise.all([loadRFQ(), loadComparison()]);
    } catch {
      toast.error("Error", "Could not delete quote.");
    }
  }

  $effect(() => {
    loadLookups();
  });

  $effect(() => {
    Promise.all([loadRFQ(), loadWorkflow(), loadComparison()]);
  });
</script>

{#if loading}
  <div class="py-24 text-center">
    <div class="inline-block w-6 h-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div>
  </div>
{:else if !rfq}
  <div class="py-24 text-center">
    <p class="text-sm text-neutral-500">RFQ not found.</p>
    <a href="/procurement/rfqs" class="inline-block mt-4 text-sm font-medium text-neutral-900 hover:underline">Back to RFQs</a>
  </div>
{:else}
  <div class="space-y-6">
    <Breadcrumb items={[{ label: "Procurement", href: "/procurement" }, { label: "RFQs", href: "/procurement/rfqs" }, { label: rfq.rfq_number }]} />

    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-neutral-900">{rfq.rfq_number}</h1>
        <p class="text-sm text-neutral-500 mt-1">{rfq.title}</p>
      </div>
      <div class="flex items-center gap-2">
        <StatusBadge status={rfq.status} />
        {#if workflow}
          <StatusBadge status={workflow.state} size="md" />
        {/if}
      </div>
    </div>

    <div class="grid grid-cols-1 xl:grid-cols-3 gap-6">
      <form class="xl:col-span-2 bg-white rounded-xl border border-neutral-200 p-6 space-y-4" onsubmit={saveRFQ}>
        <h2 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">RFQ Details</h2>

        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Title</span>
          <input bind:value={form.title} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm" />
          {#if fieldError("title")}<p class="mt-1 text-xs text-red-500">{fieldError("title")}</p>{/if}
        </label>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Status</span>
            <select bind:value={form.status} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm">
              <option value="draft">Draft</option>
              <option value="issued">Issued</option>
              <option value="evaluation">Evaluation</option>
              <option value="submitted">Submitted</option>
              <option value="approved">Approved</option>
              <option value="cancelled">Cancelled</option>
              <option value="closed">Closed</option>
            </select>
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Requisition</span>
            <select bind:value={form.requisition} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm">
              <option value="">None</option>
              {#each requisitions as req}
                <option value={String(req.id)}>{req.pr_number} - {req.title}</option>
              {/each}
            </select>
          </label>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Project</span>
            <select bind:value={form.project} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm">
              <option value="">None</option>
              {#each projects as project}
                <option value={String(project.id)}>{project.name}</option>
              {/each}
            </select>
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Property</span>
            <select bind:value={form.property} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm">
              <option value="">None</option>
              {#each properties as property}
                <option value={String(property.id)}>{property.name}</option>
              {/each}
            </select>
          </label>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Issue Date</span>
            <DateInput bind:value={form.issue_date} />
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Submission Deadline</span>
            <DateInput bind:value={form.submission_deadline} />
          </label>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Budget Line</span>
            <select bind:value={form.budget_line_item} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm">
              <option value="">None</option>
              {#each budgetLines as line}
                <option value={String(line.id)}>{line.label}</option>
              {/each}
            </select>
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Cost Code</span>
            <select bind:value={form.cost_code} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm">
              <option value="">None</option>
              {#each costCodes as code}
                <option value={code.code}>{code.code} - {code.label}</option>
              {/each}
            </select>
          </label>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Budget Code</span>
            <input bind:value={form.budget_code} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm" />
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Selected Vendor</span>
            <select bind:value={form.selected_vendor} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm">
              <option value="">None</option>
              {#each vendors as vendor}
                <option value={String(vendor.id)}>{vendor.name}</option>
              {/each}
            </select>
          </label>
        </div>

        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Selection Notes</span>
          <textarea rows={2} bind:value={form.selection_notes} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm resize-none"></textarea>
        </label>

        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Notes</span>
          <textarea rows={3} bind:value={form.notes} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm resize-none"></textarea>
        </label>

        <div class="flex items-center justify-end gap-3">
          <button type="button" onclick={deleteRFQ} disabled={deleting} class="px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg">
            {deleting ? "Deleting..." : "Delete"}
          </button>
          <button type="submit" disabled={saving} class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50">
            {saving ? "Saving..." : "Save RFQ"}
          </button>
        </div>
      </form>

      <div class="space-y-4">
        <div class="bg-white rounded-xl border border-neutral-200 p-5 space-y-3">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Summary</h3>
          <div class="flex justify-between text-sm"><span class="text-neutral-500">Issue Date</span><span class="text-neutral-900">{formatDate(rfq.issue_date)}</span></div>
          <div class="flex justify-between text-sm"><span class="text-neutral-500">Deadline</span><span class="text-neutral-900">{formatDate(rfq.submission_deadline)}</span></div>
          <div class="flex justify-between text-sm"><span class="text-neutral-500">Estimated</span><span class="text-neutral-900">{formatCurrency(rfq.estimated_value)}</span></div>
          <div class="flex justify-between text-sm"><span class="text-neutral-500">Quotes</span><span class="text-neutral-900">{rfqQuotes.length}</span></div>
        </div>

        <div class="bg-white rounded-xl border border-neutral-200 p-5">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-3">Approval</h3>
          <button
            type="button"
            onclick={submitForApproval}
            disabled={submittingApproval}
            class="w-full px-4 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50"
          >
            {submittingApproval ? "Submitting..." : "Submit for Approval"}
          </button>
        </div>

        {#if workflow}
          <DecisionPanel instance={workflow} onDecision={loadWorkflow} />
          {#if workflow.steps.length > 0}
            <div class="bg-white rounded-xl border border-neutral-200 p-5">
              <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Approval Progress</h3>
              <ApprovalTimeline steps={workflow.steps} />
            </div>
          {/if}
        {/if}
      </div>
    </div>

    <div class="grid grid-cols-1 xl:grid-cols-2 gap-6">
      <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
        <div class="px-5 py-4 border-b border-neutral-100">
          <h2 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Vendor Quotes</h2>
        </div>
        {#if rfqQuotes.length === 0}
          <div class="p-6 text-sm text-neutral-500">No quotes yet.</div>
        {:else}
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-100">
                <th class="px-4 py-2.5 text-left text-xs uppercase tracking-wider text-neutral-500">Vendor</th>
                <th class="px-4 py-2.5 text-right text-xs uppercase tracking-wider text-neutral-500">Amount</th>
                <th class="px-4 py-2.5 text-right text-xs uppercase tracking-wider text-neutral-500">Score</th>
                <th class="px-4 py-2.5 text-right text-xs uppercase tracking-wider text-neutral-500">Status</th>
                <th class="px-4 py-2.5 text-right text-xs uppercase tracking-wider text-neutral-500">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each rfqQuotes as quote}
                <tr>
                  <td class="px-4 py-3 text-neutral-900">{quote.vendor_name}</td>
                  <td class="px-4 py-3 text-right tabular-nums">{formatCurrency(quote.quoted_amount)}</td>
                  <td class="px-4 py-3 text-right tabular-nums">{Number(quote.total_score).toFixed(2)}</td>
                  <td class="px-4 py-3 text-right">
                    <StatusBadge status={quote.status} />
                  </td>
                  <td class="px-4 py-3 text-right space-x-2">
                    <button class="text-xs text-neutral-500 hover:text-emerald-700" onclick={() => selectVendor(quote.id)} disabled={selectingVendor}>Select</button>
                    <button class="text-xs text-red-500 hover:text-red-700" onclick={() => removeQuote(quote.id)}>Delete</button>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}
      </div>

      <form class="bg-white rounded-xl border border-neutral-200 p-6 space-y-3" onsubmit={addQuote}>
        <h2 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Add Quote</h2>

        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Vendor</span>
          <select bind:value={quoteForm.vendor} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm">
            <option value="">Select vendor</option>
            {#each vendors as vendor}
              <option value={String(vendor.id)}>{vendor.name}</option>
            {/each}
          </select>
        </label>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Quote #</span>
            <input bind:value={quoteForm.quote_number} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm" />
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Quote Date</span>
            <DateInput bind:value={quoteForm.quote_date} />
          </label>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Amount</span>
            <input type="number" step="0.01" bind:value={quoteForm.quoted_amount} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm" />
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Delivery Days</span>
            <input type="number" bind:value={quoteForm.delivery_days} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm" />
          </label>
        </div>

        <div class="grid grid-cols-3 gap-3">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Tech</span>
            <input type="number" step="0.01" bind:value={quoteForm.technical_score} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm" />
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Comm</span>
            <input type="number" step="0.01" bind:value={quoteForm.commercial_score} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm" />
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Compliance</span>
            <input type="number" step="0.01" bind:value={quoteForm.compliance_score} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm" />
          </label>
        </div>

        <button type="submit" disabled={addingQuote} class="w-full px-4 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50">
          {addingQuote ? "Adding..." : "Add Quote"}
        </button>
      </form>
    </div>

    <!-- Comparison Matrix -->
    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      <div class="px-5 py-4 border-b border-neutral-100 flex items-center justify-between">
        <h2 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Tender Comparison Matrix</h2>
        {#if quotesComparison.length > 0}
          <span class="text-[10px] text-neutral-400">{quotesComparison.length} vendor(s) compared</span>
        {/if}
      </div>
      {#if quotesComparison.length === 0}
        <div class="p-6 text-sm text-neutral-500">No comparison data yet. Add vendor quotes to generate the comparison matrix.</div>
      {:else}
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-100 bg-neutral-50">
                <th class="px-4 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Rank</th>
                <th class="px-4 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Vendor</th>
                <th class="px-4 py-2.5 text-right text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Unit Price</th>
                <th class="px-4 py-2.5 text-center text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Lead Time</th>
                <th class="px-4 py-2.5 text-center text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Compliance</th>
                <th class="px-4 py-2.5 text-center text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Technical</th>
                <th class="px-4 py-2.5 text-center text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Commercial</th>
                <th class="px-4 py-2.5 text-center text-[10px] font-semibold text-neutral-900 uppercase tracking-wider">Score</th>
                <th class="px-4 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Terms</th>
                <th class="px-4 py-2.5 text-center text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Status</th>
                <th class="px-4 py-2.5 text-center text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">Action</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-50">
              {#each quotesComparison as quote, i}
                {@const isWinner = quote.status === "winner"}
                {@const isBest = i === 0}
                <tr class="{isWinner ? 'bg-emerald-50/50' : isBest ? 'bg-indigo-50/30' : ''} hover:bg-neutral-50">
                  <td class="px-4 py-3">
                    <span class={`inline-flex items-center justify-center h-6 w-6 rounded-full text-[10px] font-bold ${rankClass(quote.rank)}`}>#{quote.rank}</span>
                  </td>
                  <td class="px-4 py-3">
                    <p class="font-medium text-neutral-900">{quote.vendor_name}</p>
                    <p class="text-[10px] text-neutral-400 mt-0.5">{quote.quote_number || 'No ref'}</p>
                  </td>
                  <td class="px-4 py-3 text-right">
                    <span class="font-bold text-neutral-900 tabular-nums">{formatCurrency(quote.quoted_amount)}</span>
                    {#if isBest}
                      <p class="text-[9px] text-emerald-600 font-semibold mt-0.5">Best value</p>
                    {:else if quotesComparison[0]}
                      {@const diff = Number(quote.quoted_amount) - Number(quotesComparison[0].quoted_amount)}
                      {#if diff > 0}
                        <p class="text-[9px] text-red-500 tabular-nums mt-0.5">+{formatCurrency(String(diff))}</p>
                      {/if}
                    {/if}
                  </td>
                  <td class="px-4 py-3 text-center">
                    {#if quote.delivery_days}
                      <span class="rounded-full px-2 py-0.5 text-[10px] font-semibold tabular-nums {quote.delivery_days <= 7 ? 'bg-emerald-100 text-emerald-700' : quote.delivery_days <= 21 ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-700'}">
                        {quote.delivery_days}d
                      </span>
                    {:else}
                      <span class="text-neutral-400">—</span>
                    {/if}
                  </td>
                  <td class="px-4 py-3 text-center">
                    <div class="inline-flex items-center gap-1">
                      <div class="h-1.5 w-12 rounded-full bg-neutral-100 overflow-hidden">
                        <div class="h-full rounded-full {Number(quote.compliance_score) >= 80 ? 'bg-emerald-500' : Number(quote.compliance_score) >= 60 ? 'bg-amber-500' : 'bg-red-500'}" style="width: {Math.min(100, Number(quote.compliance_score))}%"></div>
                      </div>
                      <span class="text-[10px] tabular-nums font-medium text-neutral-700">{Number(quote.compliance_score).toFixed(0)}</span>
                    </div>
                  </td>
                  <td class="px-4 py-3 text-center">
                    <div class="inline-flex items-center gap-1">
                      <div class="h-1.5 w-12 rounded-full bg-neutral-100 overflow-hidden">
                        <div class="h-full rounded-full {Number(quote.technical_score) >= 80 ? 'bg-emerald-500' : Number(quote.technical_score) >= 60 ? 'bg-amber-500' : 'bg-red-500'}" style="width: {Math.min(100, Number(quote.technical_score))}%"></div>
                      </div>
                      <span class="text-[10px] tabular-nums font-medium text-neutral-700">{Number(quote.technical_score).toFixed(0)}</span>
                    </div>
                  </td>
                  <td class="px-4 py-3 text-center">
                    <div class="inline-flex items-center gap-1">
                      <div class="h-1.5 w-12 rounded-full bg-neutral-100 overflow-hidden">
                        <div class="h-full rounded-full {Number(quote.commercial_score) >= 80 ? 'bg-emerald-500' : Number(quote.commercial_score) >= 60 ? 'bg-amber-500' : 'bg-red-500'}" style="width: {Math.min(100, Number(quote.commercial_score))}%"></div>
                      </div>
                      <span class="text-[10px] tabular-nums font-medium text-neutral-700">{Number(quote.commercial_score).toFixed(0)}</span>
                    </div>
                  </td>
                  <td class="px-4 py-3 text-center">
                    <span class="text-lg font-bold {Number(quote.total_score) >= 80 ? 'text-emerald-700' : Number(quote.total_score) >= 60 ? 'text-amber-700' : 'text-red-700'} tabular-nums">{Number(quote.total_score).toFixed(1)}</span>
                  </td>
                  <td class="px-4 py-3">
                    <div class="max-w-[120px]">
                      {#if quote.payment_terms}<p class="text-[10px] text-neutral-600 truncate" title={quote.payment_terms}>{quote.payment_terms}</p>{/if}
                      {#if quote.warranty_terms}<p class="text-[10px] text-neutral-400 truncate" title={quote.warranty_terms}>{quote.warranty_terms}</p>{/if}
                    </div>
                  </td>
                  <td class="px-4 py-3 text-center">
                    <span class="rounded-full border px-2 py-0.5 text-[9px] font-semibold {quote.status === 'winner' ? 'bg-emerald-100 text-emerald-700 border-emerald-200' : quote.status === 'shortlisted' ? 'bg-blue-100 text-blue-700 border-blue-200' : quote.status === 'rejected' ? 'bg-red-100 text-red-700 border-red-200' : 'bg-neutral-100 text-neutral-600 border-neutral-200'}">
                      {quote.status}
                    </span>
                  </td>
                  <td class="px-4 py-3 text-center">
                    {#if rfq && rfq.status !== "closed" && quote.status !== "winner"}
                      <button
                        onclick={() => selectVendor(quote.id)}
                        disabled={selectingVendor}
                        class="rounded-md bg-emerald-600 px-2.5 py-1 text-[10px] font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
                      >Award</button>
                    {:else if quote.status === "winner"}
                      <span class="text-[10px] font-semibold text-emerald-600">Awarded</span>
                    {/if}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>

        <!-- Comparison Summary -->
        {#if quotesComparison.length >= 2}
          <div class="border-t border-neutral-100 bg-neutral-50 px-5 py-3">
            {#if true}
              {@const amounts = quotesComparison.map(q => Number(q.quoted_amount))}
              {@const minAmt = Math.min(...amounts)}
              {@const maxAmt = Math.max(...amounts)}
              {@const spread = maxAmt - minAmt}
              {@const avgDays = quotesComparison.filter(q => q.delivery_days).reduce((s, q) => s + (q.delivery_days || 0), 0) / (quotesComparison.filter(q => q.delivery_days).length || 1)}
              <div class="flex flex-wrap gap-4 text-[10px]">
                <span class="text-neutral-500">Price range: <strong class="text-neutral-900">{formatCurrency(String(minAmt))}</strong> — <strong class="text-neutral-900">{formatCurrency(String(maxAmt))}</strong></span>
                <span class="text-neutral-500">Spread: <strong class="{spread > minAmt * 0.3 ? 'text-red-600' : 'text-emerald-600'}">{formatCurrency(String(spread))}</strong> ({minAmt > 0 ? (spread / minAmt * 100).toFixed(0) : 0}%)</span>
                <span class="text-neutral-500">Avg lead time: <strong class="text-neutral-900">{avgDays.toFixed(0)} days</strong></span>
              </div>
            {/if}
          </div>
        {/if}
      {/if}
    </div>
  </div>
{/if}

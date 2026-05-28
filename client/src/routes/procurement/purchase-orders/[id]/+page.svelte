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
    PurchaseOrder, PurchaseOrderItem, GoodsReceiptListItem,
    BillListItem, ThreeWayMatch, VendorListItem, ProjectListItem,
    PropertyListItem, MasterDataEntry, PaginatedResponse, WorkflowInstanceDetail,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  const id = $derived($page.params.id);

  let po = $state<PurchaseOrder | null>(null);
  let loading = $state(true);
  let saving = $state(false);
  let deleting = $state(false);
  let errors = $state<Record<string, string[]>>({});

  let vendors = $state<VendorListItem[]>([]);
  let projects = $state<ProjectListItem[]>([]);
  let properties = $state<PropertyListItem[]>([]);
  let budgetLines = $state<BudgetLineOption[]>([]);
  let costCodes = $state<MasterDataEntry[]>([]);

  // Workflow state
  let workflow = $state<WorkflowInstanceDetail | null>(null);
  let submittingApproval = $state(false);
  const poItems = $derived.by(() => po?.items ?? []);
  const poGoodsReceipts = $derived.by(() => po?.goods_receipts ?? []);
  const poBills = $derived.by(() => po?.bills ?? []);
  const poThreeWayMatch = $derived.by<ThreeWayMatch>(() => (
    po?.three_way_match ?? {
      po_total: "0.00",
      grn_accepted_total: "0.00",
      invoice_total: "0.00",
      qty_match: false,
      amount_match: false,
      status: "pending",
    }
  ));

  async function loadWorkflow() {
    if (!id) {
      workflow = null;
      return;
    }
    try {
      const res = await api.get<{ results: WorkflowInstanceDetail[] }>("/workflows/instances/", {
        model: "procurement.purchaseorder",
        object_id: id,
      });
      workflow = res.results.length > 0 ? res.results[0] : null;
    } catch {
      workflow = null;
    }
  }

  async function submitForApproval() {
    if (!id) return;
    submittingApproval = true;
    try {
      await api.post(`/procurement/purchase-orders/${id}/submit-approval/`, {});
      toast.success("Submitted", "Purchase order has been submitted for approval.");
      await Promise.all([loadPO(), loadWorkflow()]);
    } catch {
      toast.error("Error", "Could not submit for approval.");
    } finally {
      submittingApproval = false;
    }
  }

  // Editable form state
  let form = $state({
    po_number: "",
    status: "draft",
    vendor: "",
    project: "",
    property: "",
    issue_date: "",
    expected_delivery_date: "",
    budget_line_item: "",
    cost_code: "",
    tax_amount: "",
    budget_code: "",
    payment_terms: "",
    delivery_address: "",
    notes: "",
    approved_by: "",
    approved_date: "",
  });

  // Item add form
  let itemForm = $state({
    description: "",
    quantity: "",
    unit_of_measure: "",
    unit_price: "",
  });
  let addingItem = $state(false);

  // GRN form
  let showGrnForm = $state(false);
  let grnForm = $state({
    received_date: "",
    received_by: "",
    delivery_note_number: "",
    notes: "",
  });
  let savingGrn = $state(false);

  function formatCurrency(v: string | null): string {
    if (!v) return "\u2014";
    return currency.format(v);
  }

  function formatDate(v: string | null): string {
    if (!v) return "\u2014";
    return new Date(v).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  }

  async function fetchVendors() {
    try {
      const res = await api.get<PaginatedResponse<VendorListItem>>("/procurement/vendors/", { page_size: "200" });
      vendors = res.results;
    } catch {
      vendors = [];
    }
  }

  async function fetchProjects() {
    try {
      const res = await api.get<PaginatedResponse<ProjectListItem>>("/projects/", { page_size: "200" });
      projects = res.results;
    } catch {
      projects = [];
    }
  }

  async function fetchProperties() {
    try {
      const res = await api.get<PaginatedResponse<PropertyListItem>>("/properties/", { page_size: "200" });
      properties = res.results;
    } catch {
      properties = [];
    }
  }

  async function loadPO() {
    if (!id) {
      po = null;
      loading = false;
      return;
    }
    loading = true;
    try {
      po = await api.get<PurchaseOrder>(`/procurement/purchase-orders/${id}/`);
      form = {
        po_number: po.po_number,
        status: po.status,
        vendor: String(po.vendor),
        project: po.project ? String(po.project) : "",
        property: po.property ? String(po.property) : "",
        issue_date: po.issue_date,
        expected_delivery_date: po.expected_delivery_date ?? "",
        budget_line_item: po.budget_line_item ? String(po.budget_line_item) : "",
        cost_code: po.cost_code || "",
        tax_amount: po.tax_amount,
        budget_code: po.budget_code || "",
        payment_terms: po.payment_terms,
        delivery_address: po.delivery_address,
        notes: po.notes,
        approved_by: po.approved_by,
        approved_date: po.approved_date ?? "",
      };
    } catch {
      po = null;
    }
    loading = false;
  }

  $effect(() => {
    fetchVendors();
    fetchProjects();
    fetchProperties();
    Promise.all([
      fetchBudgetLineOptions().then((rows) => (budgetLines = rows)),
      fetchCostCodeOptions().then((rows) => (costCodes = rows)),
    ]);
  });

  $effect(() => {
    void id;
    loadPO();
    loadWorkflow();
  });

  function fieldError(field: string): string {
    return errors[field]?.[0] ?? "";
  }

  // --- Save PO ---
  async function handleSave(e: Event) {
    e.preventDefault();
    errors = {};
    saving = true;
    try {
      const payload = {
        po_number: form.po_number,
        status: form.status,
        vendor: form.vendor ? Number(form.vendor) : null,
        project: form.project ? Number(form.project) : null,
        property: form.property ? Number(form.property) : null,
        issue_date: form.issue_date || null,
        expected_delivery_date: form.expected_delivery_date || null,
        budget_line_item: form.budget_line_item ? Number(form.budget_line_item) : null,
        budget_code: form.budget_code,
        cost_code: form.cost_code,
        tax_amount: form.tax_amount || "0.00",
        payment_terms: form.payment_terms,
        delivery_address: form.delivery_address,
        notes: form.notes,
        approved_by: form.approved_by,
        approved_date: form.approved_date || null,
      };
      await api.patch<PurchaseOrder>(`/procurement/purchase-orders/${id}/`, payload);
      await loadPO();
      toast.success("Purchase order updated", "Changes have been saved");
    } catch (err) {
      if (err instanceof ApiError) {
        errors = err.fieldErrors;
        toast.error("Validation error", "Please fix the highlighted fields below");
      } else {
        toast.error("Something went wrong", "Could not update the purchase order");
      }
    }
    saving = false;
  }

  // --- Delete PO ---
  async function handleDelete() {
    if (!confirm("Are you sure you want to delete this purchase order? This action cannot be undone.")) return;
    deleting = true;
    try {
      await api.delete(`/procurement/purchase-orders/${id}/`);
      toast.success("Purchase order deleted", "The purchase order has been removed");
      goto("/procurement/purchase-orders");
    } catch {
      toast.error("Something went wrong", "Could not delete the purchase order");
    }
    deleting = false;
  }

  // --- Items ---
  async function addItem() {
    if (!itemForm.description || !itemForm.quantity || !itemForm.unit_price) return;
    addingItem = true;
    try {
      await api.post(`/procurement/purchase-orders/${id}/items/`, {
        description: itemForm.description,
        quantity: itemForm.quantity,
        unit_of_measure: itemForm.unit_of_measure,
        unit_price: itemForm.unit_price,
      });
      itemForm = { description: "", quantity: "", unit_of_measure: "", unit_price: "" };
      toast.success("Item added", "The item has been added to this purchase order");
      await loadPO();
    } catch (err) {
      if (err instanceof ApiError) {
        const msg = Object.values(err.fieldErrors).flat()[0];
        toast.error("Validation error", msg || "Could not add item");
      } else {
        toast.error("Something went wrong", "Could not add item");
      }
    }
    addingItem = false;
  }

  async function removeItem(itemId: number) {
    if (!confirm("Remove this item?")) return;
    try {
      await api.delete(`/procurement/purchase-orders/${id}/items/${itemId}/`);
      toast.success("Item removed", "The item has been deleted");
      await loadPO();
    } catch {
      toast.error("Something went wrong", "Could not remove item");
    }
  }

  // --- Goods Receipts ---
  async function recordGoodsReceipt() {
    if (!grnForm.received_date || !grnForm.received_by) return;
    savingGrn = true;
    try {
      await api.post(`/procurement/purchase-orders/${id}/goods-receipts/`, {
        received_date: grnForm.received_date,
        received_by: grnForm.received_by,
        delivery_note_number: grnForm.delivery_note_number,
        notes: grnForm.notes,
      });
      grnForm = { received_date: "", received_by: "", delivery_note_number: "", notes: "" };
      showGrnForm = false;
      toast.success("Goods receipt created", "The delivery has been recorded");
      await loadPO();
    } catch (err) {
      if (err instanceof ApiError) {
        const msg = Object.values(err.fieldErrors).flat()[0];
        toast.error("Validation error", msg || "Could not record goods receipt");
      } else {
        toast.error("Something went wrong", "Could not record goods receipt");
      }
    }
    savingGrn = false;
  }
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
  </div>
{:else if !po}
  <div class="text-center py-24">
    <p class="text-neutral-400">Purchase order not found.</p>
    <a href="/procurement/purchase-orders" class="mt-4 inline-block text-sm font-medium text-neutral-900 hover:underline">Back to purchase orders</a>
  </div>
{:else}
  <!-- Header -->
  <div class="mb-8">
    <Breadcrumb items={[{ label: "Procurement", href: "/procurement" }, { label: "Purchase Orders", href: "/procurement/purchase-orders" }, { label: po.po_number }]} />
    <div class="flex items-center gap-4 mt-3">
      <h1 class="text-2xl font-bold text-neutral-900">{po.po_number}</h1>
      <StatusBadge status={po.status} size="md" />
      {#if workflow}
        <StatusBadge status={workflow.state} size="md" />
      {/if}
    </div>
    <p class="text-sm text-neutral-500 mt-1">{po.vendor_name}</p>
  </div>

  <!-- Two-column layout -->
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
    <!-- Left: Editable form (2 cols) -->
    <div class="lg:col-span-2">
      <form onsubmit={handleSave} class="bg-white rounded-xl border border-neutral-200 p-6 space-y-5">
        <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Purchase Order Details</h3>

        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">PO Number</span>
            <input
              bind:value={form.po_number}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if fieldError("po_number")}<p class="mt-1 text-xs text-red-500">{fieldError("po_number")}</p>{/if}
          </label>

          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Status</span>
            <select
              bind:value={form.status}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            >
              <option value="draft">Draft</option>
              <option value="approved">Approved</option>
              <option value="issued">Issued</option>
              <option value="partially_received">Partially Received</option>
              <option value="received">Received</option>
              <option value="cancelled">Cancelled</option>
            </select>
            {#if fieldError("status")}<p class="mt-1 text-xs text-red-500">{fieldError("status")}</p>{/if}
          </label>
        </div>

        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Budget Code</span>
          <input
            bind:value={form.budget_code}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            placeholder="e.g. CAPEX-2026-002"
          />
          {#if fieldError("budget_code")}<p class="mt-1 text-xs text-red-500">{fieldError("budget_code")}</p>{/if}
        </label>

        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Budget Line</span>
            <select
              bind:value={form.budget_line_item}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            >
              <option value="">None</option>
              {#each budgetLines as line}
                <option value={String(line.id)}>{line.label}</option>
              {/each}
            </select>
            {#if fieldError("budget_line_item")}<p class="mt-1 text-xs text-red-500">{fieldError("budget_line_item")}</p>{/if}
          </label>

          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Cost Code</span>
            <select
              bind:value={form.cost_code}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            >
              <option value="">None</option>
              {#each costCodes as code}
                <option value={code.code}>{code.code} - {code.label}</option>
              {/each}
            </select>
            {#if fieldError("cost_code")}<p class="mt-1 text-xs text-red-500">{fieldError("cost_code")}</p>{/if}
          </label>
        </div>

        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Vendor</span>
          <select
            bind:value={form.vendor}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            <option value="">Select a vendor</option>
            {#each vendors as vendor}
              <option value={String(vendor.id)}>{vendor.name}</option>
            {/each}
          </select>
          {#if fieldError("vendor")}<p class="mt-1 text-xs text-red-500">{fieldError("vendor")}</p>{/if}
        </label>

        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Project <span class="text-neutral-400 font-normal">(optional)</span></span>
            <select
              bind:value={form.project}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            >
              <option value="">None</option>
              {#each projects as project}
                <option value={String(project.id)}>{project.name}</option>
              {/each}
            </select>
            {#if fieldError("project")}<p class="mt-1 text-xs text-red-500">{fieldError("project")}</p>{/if}
          </label>

          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Property <span class="text-neutral-400 font-normal">(optional)</span></span>
            <select
              bind:value={form.property}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            >
              <option value="">None</option>
              {#each properties as property}
                <option value={String(property.id)}>{property.name}</option>
              {/each}
            </select>
            {#if fieldError("property")}<p class="mt-1 text-xs text-red-500">{fieldError("property")}</p>{/if}
          </label>
        </div>

        <!-- Requisition (read-only link if linked) -->
        {#if po.requisition}
          <div>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Requisition</span>
            <a
              href="/procurement/requisitions/{po.requisition}"
              class="inline-flex items-center gap-1.5 text-sm text-neutral-900 font-medium hover:underline"
            >
              {po.requisition_number ?? `PR-${po.requisition}`}
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
              </svg>
            </a>
          </div>
        {/if}

        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Issue Date</span>
            <DateInput bind:value={form.issue_date} />
            {#if fieldError("issue_date")}<p class="mt-1 text-xs text-red-500">{fieldError("issue_date")}</p>{/if}
          </label>

          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Expected Delivery Date</span>
            <DateInput bind:value={form.expected_delivery_date} />
            {#if fieldError("expected_delivery_date")}<p class="mt-1 text-xs text-red-500">{fieldError("expected_delivery_date")}</p>{/if}
          </label>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Tax Amount</span>
            <input
              bind:value={form.tax_amount}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white tabular-nums
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
              placeholder="0.00"
            />
            {#if fieldError("tax_amount")}<p class="mt-1 text-xs text-red-500">{fieldError("tax_amount")}</p>{/if}
          </label>

          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Payment Terms</span>
            <input
              bind:value={form.payment_terms}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
              placeholder="e.g. Net 30"
            />
            {#if fieldError("payment_terms")}<p class="mt-1 text-xs text-red-500">{fieldError("payment_terms")}</p>{/if}
          </label>
        </div>

        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Delivery Address</span>
          <textarea
            bind:value={form.delivery_address}
            rows={2}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white resize-none
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            placeholder="Delivery address..."
          ></textarea>
          {#if fieldError("delivery_address")}<p class="mt-1 text-xs text-red-500">{fieldError("delivery_address")}</p>{/if}
        </label>

        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Notes</span>
          <textarea
            bind:value={form.notes}
            rows={3}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white resize-none
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            placeholder="Optional notes..."
          ></textarea>
        </label>

        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Approved By</span>
            <input
              bind:value={form.approved_by}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
              placeholder="Name of approver"
            />
            {#if fieldError("approved_by")}<p class="mt-1 text-xs text-red-500">{fieldError("approved_by")}</p>{/if}
          </label>

          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Approved Date</span>
            <DateInput bind:value={form.approved_date} />
            {#if fieldError("approved_date")}<p class="mt-1 text-xs text-red-500">{fieldError("approved_date")}</p>{/if}
          </label>
        </div>

        <div class="flex items-center justify-between pt-2">
          <div class="flex gap-3">
            <button
              type="submit"
              disabled={saving}
              class="px-6 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium
                     hover:bg-neutral-800 disabled:opacity-50 transition-colors"
            >
              {saving ? "Saving..." : "Save Changes"}
            </button>
          </div>
          <button
            type="button"
            onclick={handleDelete}
            disabled={deleting}
            class="px-4 py-2.5 border border-red-200 text-red-600 rounded-lg text-sm font-medium
                   hover:bg-red-50 disabled:opacity-50 transition-colors"
          >
            {deleting ? "Deleting..." : "Delete PO"}
          </button>
        </div>
      </form>
    </div>

    <!-- Right: Summary card + Workflow (1 col) -->
    <div class="space-y-6">
      <div class="bg-white rounded-xl border border-neutral-200 p-6">
        <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Summary</h3>
        <div class="space-y-3 text-sm">
          <div class="flex justify-between">
            <span class="text-neutral-400">Subtotal</span>
            <span class="text-neutral-900 tabular-nums">{formatCurrency(po.subtotal)}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-neutral-400">Tax</span>
            <span class="text-neutral-900 tabular-nums">{formatCurrency(po.tax_amount)}</span>
          </div>
          <div class="border-t border-neutral-100 pt-3 flex justify-between font-semibold">
            <span class="text-neutral-900">Total</span>
            <span class="text-neutral-900 tabular-nums">{formatCurrency(po.total_amount)}</span>
          </div>
          <div class="border-t border-neutral-100 pt-3 flex justify-between">
            <span class="text-neutral-400">Received</span>
            <span class="inline-flex items-center gap-1.5">
              {#if po.is_fully_received}
                <span class="inline-block w-2 h-2 rounded-full bg-emerald-500"></span>
                <span class="text-emerald-700 text-sm font-medium">Fully Received</span>
              {:else}
                <span class="inline-block w-2 h-2 rounded-full bg-amber-500"></span>
                <span class="text-amber-700 text-sm font-medium">Pending</span>
              {/if}
            </span>
          </div>
        </div>
      </div>

      <!-- Workflow Section -->
      {#if workflow}
        <DecisionPanel instance={workflow} onDecision={loadWorkflow} />
        {#if workflow.steps.length > 0}
          <div class="bg-white rounded-xl border border-neutral-200 p-6">
            <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Approval Progress</h3>
            <ApprovalTimeline steps={workflow.steps} />
          </div>
        {/if}
      {:else if po.status === "draft"}
        <div class="bg-white rounded-xl border border-neutral-200 p-6">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Approval</h3>
          <p class="text-xs text-neutral-400 mb-4">Submit this purchase order for workflow-based approval routing.</p>
          <button
            type="button"
            onclick={submitForApproval}
            disabled={submittingApproval}
            class="w-full px-4 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium
                   hover:bg-neutral-800 disabled:opacity-50 transition-colors"
          >
            {submittingApproval ? "Submitting..." : "Submit for Approval"}
          </button>
        </div>
      {/if}
    </div>
  </div>

  <!-- Items Section -->
  <div class="mb-8">
    <h3 class="text-lg font-semibold text-neutral-900 mb-4">Items</h3>
    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      {#if poItems.length > 0}
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-neutral-200">
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Description</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Qty</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">UOM</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Unit Price</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Amount</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Received Qty</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Remaining Qty</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each poItems as item}
              <tr class="hover:bg-neutral-50 transition-colors">
                <td class="px-5 py-4 text-neutral-900">{item.description}</td>
                <td class="px-5 py-4 text-right text-neutral-500 tabular-nums">{item.quantity}</td>
                <td class="px-5 py-4 text-neutral-500">{item.unit_of_measure || "\u2014"}</td>
                <td class="px-5 py-4 text-right text-neutral-500 tabular-nums">{formatCurrency(item.unit_price)}</td>
                <td class="px-5 py-4 text-right text-neutral-900 tabular-nums font-medium">{formatCurrency(item.amount)}</td>
                <td class="px-5 py-4 text-right tabular-nums {Number(item.quantity_received) > 0 ? 'text-emerald-700' : 'text-neutral-400'}">{item.quantity_received}</td>
                <td class="px-5 py-4 text-right tabular-nums {Number(item.quantity_remaining) > 0 ? 'text-amber-700' : 'text-neutral-400'}">{item.quantity_remaining}</td>
                <td class="px-5 py-4 text-right">
                  <button onclick={() => removeItem(item.id)} class="text-xs text-neutral-400 hover:text-red-600 transition-colors">
                    Delete
                  </button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      {:else}
        <div class="p-8 text-center">
          <p class="text-sm text-neutral-400">No items yet.</p>
        </div>
      {/if}

      <!-- Add item form -->
      <div class="border-t border-neutral-200 px-5 py-4">
        <div class="flex items-end gap-3">
          <label class="flex-1">
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Description</span>
            <input
              bind:value={itemForm.description}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
              placeholder="Item description"
            />
          </label>
          <label class="w-24">
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Qty</span>
            <input
              bind:value={itemForm.quantity}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white tabular-nums
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
              placeholder="1"
            />
          </label>
          <label class="w-28">
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">UOM</span>
            <input
              bind:value={itemForm.unit_of_measure}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
              placeholder="e.g. pcs"
            />
          </label>
          <label class="w-32">
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Unit Price</span>
            <input
              bind:value={itemForm.unit_price}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white tabular-nums
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
              placeholder="0.00"
            />
          </label>
          <button
            type="button"
            onclick={addItem}
            disabled={addingItem}
            class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium
                   hover:bg-neutral-800 disabled:opacity-50 transition-colors"
          >
            {addingItem ? "Adding..." : "Add"}
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- Goods Receipts Section -->
  <div class="mb-8">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-semibold text-neutral-900">Goods Receipts</h3>
      <button
        type="button"
        onclick={() => showGrnForm = !showGrnForm}
        class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium
               hover:bg-neutral-800 transition-colors"
      >
        {showGrnForm ? "Cancel" : "Record Delivery"}
      </button>
    </div>
    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      {#if poGoodsReceipts.length > 0}
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-neutral-200">
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">GRN #</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Received Date</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Received By</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Delivery Note #</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each poGoodsReceipts as grn}
              <tr
                class="hover:bg-neutral-50 transition-colors cursor-pointer"
                onclick={() => goto(`/procurement/goods-receipts/${grn.id}`)}
              >
                <td class="px-5 py-4 text-neutral-900 font-medium">{grn.grn_number}</td>
                <td class="px-5 py-4">
                  <StatusBadge status={grn.status} size="md" />
                </td>
                <td class="px-5 py-4 text-neutral-500">{formatDate(grn.received_date)}</td>
                <td class="px-5 py-4 text-neutral-500">{grn.received_by || "\u2014"}</td>
                <td class="px-5 py-4 text-neutral-500">{grn.delivery_note_number || "\u2014"}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      {:else}
        <div class="p-8 text-center">
          <p class="text-sm text-neutral-400">No goods receipts recorded yet.</p>
        </div>
      {/if}

      <!-- GRN inline form -->
      {#if showGrnForm}
        <div class="border-t border-neutral-200 px-5 py-4">
          <h4 class="text-sm font-medium text-neutral-900 mb-3">Record Delivery</h4>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-3 items-end">
            <label>
              <span class="block text-sm font-medium text-neutral-700 mb-1.5">Received Date</span>
              <DateInput bind:value={grnForm.received_date} />
            </label>
            <label>
              <span class="block text-sm font-medium text-neutral-700 mb-1.5">Received By</span>
              <input
                bind:value={grnForm.received_by}
                class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                       focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
                placeholder="Name"
              />
            </label>
            <label>
              <span class="block text-sm font-medium text-neutral-700 mb-1.5">Delivery Note #</span>
              <input
                bind:value={grnForm.delivery_note_number}
                class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                       focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
                placeholder="Optional"
              />
            </label>
            <label>
              <span class="block text-sm font-medium text-neutral-700 mb-1.5">Notes</span>
              <input
                bind:value={grnForm.notes}
                class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                       focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
                placeholder="Optional"
              />
            </label>
          </div>
          <div class="mt-3">
            <button
              type="button"
              onclick={recordGoodsReceipt}
              disabled={savingGrn}
              class="px-6 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium
                     hover:bg-neutral-800 disabled:opacity-50 transition-colors"
            >
              {savingGrn ? "Saving..." : "Save Goods Receipt"}
            </button>
          </div>
        </div>
      {/if}
    </div>
  </div>

  <!-- 3-Way Match Section -->
  <div class="mb-8">
    <h3 class="text-lg font-semibold text-neutral-900 mb-4">3-Way Match</h3>
    <div class="bg-white rounded-xl border border-neutral-200 p-6">
      <div class="flex items-center gap-3 mb-6">
        <StatusBadge status={poThreeWayMatch.status} size="md" />
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div class="text-center p-4 rounded-lg bg-neutral-50">
          <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider mb-1">PO Total</p>
          <p class="text-xl font-semibold text-neutral-900 tabular-nums">{formatCurrency(poThreeWayMatch.po_total)}</p>
        </div>
        <div class="text-center p-4 rounded-lg bg-neutral-50">
          <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider mb-1">GRN Accepted Total</p>
          <p class="text-xl font-semibold text-neutral-900 tabular-nums">{formatCurrency(poThreeWayMatch.grn_accepted_total)}</p>
        </div>
        <div class="text-center p-4 rounded-lg bg-neutral-50">
          <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider mb-1">Invoice Total</p>
          <p class="text-xl font-semibold text-neutral-900 tabular-nums">{formatCurrency(poThreeWayMatch.invoice_total)}</p>
        </div>
      </div>

      <div class="flex items-center gap-6 text-sm">
        <div class="flex items-center gap-2">
          {#if poThreeWayMatch.qty_match}
            <svg class="w-5 h-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
            </svg>
            <span class="text-emerald-700 font-medium">Quantity Match</span>
          {:else}
            <svg class="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="m9.75 9.75 4.5 4.5m0-4.5-4.5 4.5M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
            </svg>
            <span class="text-red-600 font-medium">Quantity Mismatch</span>
          {/if}
        </div>
        <div class="flex items-center gap-2">
          {#if poThreeWayMatch.amount_match}
            <svg class="w-5 h-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
            </svg>
            <span class="text-emerald-700 font-medium">Amount Match</span>
          {:else}
            <svg class="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="m9.75 9.75 4.5 4.5m0-4.5-4.5 4.5M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
            </svg>
            <span class="text-red-600 font-medium">Amount Mismatch</span>
          {/if}
        </div>
      </div>
    </div>
  </div>

  <!-- Linked Bills Section -->
  <div class="mb-8">
    <h3 class="text-lg font-semibold text-neutral-900 mb-4">Linked Bills</h3>
    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      {#if poBills.length > 0}
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-neutral-200">
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Bill #</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Vendor</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Due Date</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Total</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Paid</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Balance</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each poBills as bill}
              <tr
                class="hover:bg-neutral-50 transition-colors cursor-pointer"
                onclick={() => goto(`/finance/bills/${bill.id}`)}
              >
                <td class="px-5 py-4 text-neutral-900 font-medium">{bill.bill_number}</td>
                <td class="px-5 py-4 text-neutral-500">{bill.vendor_name}</td>
                <td class="px-5 py-4">
                  <StatusBadge status={bill.status} size="md" />
                </td>
                <td class="px-5 py-4 text-neutral-500">{formatDate(bill.due_date)}</td>
                <td class="px-5 py-4 text-right text-neutral-900 tabular-nums font-medium">{formatCurrency(bill.total_amount)}</td>
                <td class="px-5 py-4 text-right text-emerald-600 tabular-nums">{formatCurrency(bill.paid_amount)}</td>
                <td class="px-5 py-4 text-right tabular-nums {Number(bill.balance_due) > 0 ? 'text-red-600' : 'text-neutral-900'}">{formatCurrency(bill.balance_due)}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      {:else}
        <div class="p-8 text-center">
          <p class="text-sm text-neutral-400">No bills linked to this purchase order.</p>
        </div>
      {/if}
    </div>
  </div>
{/if}

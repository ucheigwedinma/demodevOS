<script lang="ts">
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { fetchBudgetLineOptions, fetchCostCodeOptions, type BudgetLineOption } from "$lib/procurement";
  import { toast } from "$lib/stores/toast.svelte";
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

  let {
    open = false,
    poId = null,
    onclose,
    onupdated,
  }: {
    open: boolean;
    poId: number | null;
    onclose: () => void;
    onupdated?: () => void;
  } = $props();

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

  // Tabs
  let activeTab = $state<"details" | "items" | "receipts" | "match" | "bills">("details");

  // Workflow
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

  // Editable form
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

  // Item form
  let itemForm = $state({ description: "", quantity: "", unit_of_measure: "", unit_price: "" });
  let addingItem = $state(false);

  // GRN form
  let showGrnForm = $state(false);
  let grnForm = $state({ received_date: "", received_by: "", delivery_note_number: "", notes: "" });
  let savingGrn = $state(false);

  function fmtCurrency(v: string | null): string {
    if (!v) return "\u2014";
    return currency.format(v);
  }

  function fmtDate(v: string | null): string {
    if (!v) return "\u2014";
    return new Date(v).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  }

  function fieldError(field: string): string {
    return errors[field]?.[0] ?? "";
  }

  // ── Data loading ──────────────────────────────────────────────────────
  let optionsLoaded = false;
  async function loadOptions() {
    if (optionsLoaded) return;
    optionsLoaded = true;
    const [vRes, pRes, prRes] = await Promise.all([
      api.get<PaginatedResponse<VendorListItem>>("/procurement/vendors/", { page_size: "200" }),
      api.get<PaginatedResponse<ProjectListItem>>("/projects/", { page_size: "200" }),
      api.get<PaginatedResponse<PropertyListItem>>("/properties/", { page_size: "200" }),
    ]);
    vendors = vRes.results;
    projects = pRes.results;
    properties = prRes.results;
    const [bl, cc] = await Promise.all([fetchBudgetLineOptions(), fetchCostCodeOptions()]);
    budgetLines = bl;
    costCodes = cc;
  }

  async function loadWorkflow(id: number) {
    try {
      const res = await api.get<{ results: WorkflowInstanceDetail[] }>("/workflows/instances/", {
        model: "procurement.purchaseorder",
        object_id: String(id),
      });
      workflow = res.results.length > 0 ? res.results[0] : null;
    } catch {
      workflow = null;
    }
  }

  async function loadPO(id: number) {
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
    if (open && poId) {
      activeTab = "details";
      loadOptions();
      loadPO(poId);
      loadWorkflow(poId);
    }
  });

  // ── Actions ───────────────────────────────────────────────────────────

  async function handleSave(e: Event) {
    e.preventDefault();
    if (!poId) return;
    errors = {};
    saving = true;
    try {
      await api.patch<PurchaseOrder>(`/procurement/purchase-orders/${poId}/`, {
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
      });
      await loadPO(poId);
      toast.success("Purchase order updated", "Changes have been saved");
      onupdated?.();
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

  async function handleDelete() {
    if (!poId || !confirm("Are you sure you want to delete this purchase order? This action cannot be undone.")) return;
    deleting = true;
    try {
      await api.delete(`/procurement/purchase-orders/${poId}/`);
      toast.success("Purchase order deleted", "The purchase order has been removed");
      onclose();
      onupdated?.();
    } catch {
      toast.error("Something went wrong", "Could not delete the purchase order");
    }
    deleting = false;
  }

  async function submitForApproval() {
    if (!poId) return;
    submittingApproval = true;
    try {
      await api.post(`/procurement/purchase-orders/${poId}/submit-approval/`, {});
      toast.success("Submitted", "Purchase order has been submitted for approval.");
      await Promise.all([loadPO(poId), loadWorkflow(poId)]);
      onupdated?.();
    } catch {
      toast.error("Error", "Could not submit for approval.");
    } finally {
      submittingApproval = false;
    }
  }

  async function addItem() {
    if (!poId || !itemForm.description || !itemForm.quantity || !itemForm.unit_price) return;
    addingItem = true;
    try {
      await api.post(`/procurement/purchase-orders/${poId}/items/`, {
        description: itemForm.description,
        quantity: itemForm.quantity,
        unit_of_measure: itemForm.unit_of_measure,
        unit_price: itemForm.unit_price,
      });
      itemForm = { description: "", quantity: "", unit_of_measure: "", unit_price: "" };
      toast.success("Item added", "Line item has been added");
      await loadPO(poId);
      onupdated?.();
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
    if (!poId || !confirm("Remove this item?")) return;
    try {
      await api.delete(`/procurement/purchase-orders/${poId}/items/${itemId}/`);
      toast.success("Item removed", "The item has been deleted");
      await loadPO(poId);
      onupdated?.();
    } catch {
      toast.error("Something went wrong", "Could not remove item");
    }
  }

  async function recordGoodsReceipt() {
    if (!poId || !grnForm.received_date || !grnForm.received_by) return;
    savingGrn = true;
    try {
      await api.post(`/procurement/purchase-orders/${poId}/goods-receipts/`, {
        received_date: grnForm.received_date,
        received_by: grnForm.received_by,
        delivery_note_number: grnForm.delivery_note_number,
        notes: grnForm.notes,
      });
      grnForm = { received_date: "", received_by: "", delivery_note_number: "", notes: "" };
      showGrnForm = false;
      toast.success("Goods receipt created", "The delivery has been recorded");
      await loadPO(poId);
      onupdated?.();
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

{#if open}
  <div
    class="fixed inset-0 bg-black/30 z-998 transition-opacity"
    onclick={onclose}
    role="presentation"
  ></div>

  <div
    class="fixed inset-y-0 right-0 z-999 w-full max-w-[680px] bg-white shadow-2xl flex flex-col overflow-hidden animate-slide-in"
    role="dialog"
    aria-modal="true"
    aria-label="Purchase Order Details"
  >
    {#if loading}
      <div class="flex-1 flex items-center justify-center">
        <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
      </div>
    {:else if !po}
      <div class="flex-1 flex items-center justify-center text-sm text-neutral-400">
        Purchase order not found.
      </div>
    {:else}
      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-5 bg-linear-to-br from-neutral-900 to-neutral-800">
        <div class="flex items-center gap-3">
          <div>
            <div class="flex items-center gap-2">
              <h2 class="text-base font-semibold text-white">{po.po_number}</h2>
              <StatusBadge status={po.status} />
              {#if workflow}
                <StatusBadge status={workflow.state} />
              {/if}
            </div>
            <p class="text-xs text-neutral-400 mt-0.5">{po.vendor_name}</p>
          </div>
        </div>
        <button
          onclick={onclose}
          class="w-8 h-8 flex items-center justify-center rounded-lg text-neutral-400 hover:text-white transition-colors"
          aria-label="Close"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Summary strip -->
      <div class="grid grid-cols-4 gap-px bg-neutral-200 border-b border-neutral-200">
        <div class="bg-white px-4 py-3 text-center">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Subtotal</p>
          <p class="text-sm font-semibold text-neutral-900 tabular-nums mt-0.5">{fmtCurrency(po.subtotal)}</p>
        </div>
        <div class="bg-white px-4 py-3 text-center">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Tax</p>
          <p class="text-sm font-semibold text-neutral-900 tabular-nums mt-0.5">{fmtCurrency(po.tax_amount)}</p>
        </div>
        <div class="bg-white px-4 py-3 text-center">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Total</p>
          <p class="text-sm font-bold text-neutral-900 tabular-nums mt-0.5">{fmtCurrency(po.total_amount)}</p>
        </div>
        <div class="bg-white px-4 py-3 text-center">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Received</p>
          <div class="flex items-center justify-center gap-1.5 mt-0.5">
            {#if po.is_fully_received}
              <span class="inline-block w-2 h-2 rounded-full bg-emerald-500"></span>
              <span class="text-xs font-medium text-emerald-700">Yes</span>
            {:else}
              <span class="inline-block w-2 h-2 rounded-full bg-amber-500"></span>
              <span class="text-xs font-medium text-amber-700">Pending</span>
            {/if}
          </div>
        </div>
      </div>

      <!-- Tabs -->
      <div class="flex border-b border-neutral-200 px-6 bg-white">
        {#each [
          { key: "details", label: "Details" },
          { key: "items", label: `Items (${poItems.length})` },
          { key: "receipts", label: `Receipts (${poGoodsReceipts.length})` },
          { key: "match", label: "3-Way Match" },
          { key: "bills", label: `Bills (${poBills.length})` },
        ] as tab}
          <button
            onclick={() => (activeTab = tab.key as typeof activeTab)}
            class="px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors {activeTab === tab.key
              ? 'border-neutral-900 text-neutral-900'
              : 'border-transparent text-neutral-400 hover:text-neutral-600'}"
          >
            {tab.label}
          </button>
        {/each}
      </div>

      <!-- Tab content -->
      <div class="flex-1 overflow-y-auto">
        <!-- ─── Details tab ──────────────────────────────────────── -->
        {#if activeTab === "details"}
          <form onsubmit={handleSave} class="p-6 space-y-4">
            <div class="grid grid-cols-2 gap-4">
              <label>
                <span class="mb-1 block text-xs font-semibold text-neutral-600">PO Number</span>
                <input bind:value={form.po_number} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
                {#if fieldError("po_number")}<p class="mt-1 text-xs text-red-500">{fieldError("po_number")}</p>{/if}
              </label>
              <label>
                <span class="mb-1 block text-xs font-semibold text-neutral-600">Status</span>
                <select bind:value={form.status} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
                  <option value="draft">Draft</option>
                  <option value="approved">Approved</option>
                  <option value="issued">Issued</option>
                  <option value="partially_received">Partially Received</option>
                  <option value="received">Received</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </label>
            </div>

            <label>
              <span class="mb-1 block text-xs font-semibold text-neutral-600">Vendor</span>
              <select bind:value={form.vendor} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
                <option value="">Select a vendor</option>
                {#each vendors as vendor}
                  <option value={String(vendor.id)}>{vendor.name}</option>
                {/each}
              </select>
            </label>

            <div class="grid grid-cols-2 gap-4">
              <label>
                <span class="mb-1 block text-xs font-semibold text-neutral-600">Project</span>
                <select bind:value={form.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
                  <option value="">None</option>
                  {#each projects as project}
                    <option value={String(project.id)}>{project.name}</option>
                  {/each}
                </select>
              </label>
              <label>
                <span class="mb-1 block text-xs font-semibold text-neutral-600">Property</span>
                <select bind:value={form.property} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
                  <option value="">None</option>
                  {#each properties as property}
                    <option value={String(property.id)}>{property.name}</option>
                  {/each}
                </select>
              </label>
            </div>

            {#if po.requisition}
              <div>
                <span class="mb-1 block text-xs font-semibold text-neutral-600">Requisition</span>
                <a href="/procurement/requisitions/{po.requisition}" class="text-sm text-blue-600 hover:underline font-medium">
                  {po.requisition_number ?? `PR-${po.requisition}`}
                </a>
              </div>
            {/if}

            <div class="grid grid-cols-2 gap-4">
              <label>
                <span class="mb-1 block text-xs font-semibold text-neutral-600">Issue Date</span>
                <DateInput bind:value={form.issue_date} />
              </label>
              <label>
                <span class="mb-1 block text-xs font-semibold text-neutral-600">Expected Delivery</span>
                <DateInput bind:value={form.expected_delivery_date} />
              </label>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <label>
                <span class="mb-1 block text-xs font-semibold text-neutral-600">Budget Line</span>
                <select bind:value={form.budget_line_item} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
                  <option value="">None</option>
                  {#each budgetLines as line}
                    <option value={String(line.id)}>{line.label}</option>
                  {/each}
                </select>
              </label>
              <label>
                <span class="mb-1 block text-xs font-semibold text-neutral-600">Cost Code</span>
                <select bind:value={form.cost_code} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
                  <option value="">None</option>
                  {#each costCodes as code}
                    <option value={code.code}>{code.code} - {code.label}</option>
                  {/each}
                </select>
              </label>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <label>
                <span class="mb-1 block text-xs font-semibold text-neutral-600">Budget Code</span>
                <input bind:value={form.budget_code} placeholder="e.g. CAPEX-2026-002" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
              </label>
              <label>
                <span class="mb-1 block text-xs font-semibold text-neutral-600">Tax Amount</span>
                <input bind:value={form.tax_amount} placeholder="0.00" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm tabular-nums" />
              </label>
            </div>

            <label>
              <span class="mb-1 block text-xs font-semibold text-neutral-600">Payment Terms</span>
              <input bind:value={form.payment_terms} placeholder="e.g. Net 30" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
            </label>

            <label>
              <span class="mb-1 block text-xs font-semibold text-neutral-600">Delivery Address</span>
              <textarea bind:value={form.delivery_address} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm resize-none"></textarea>
            </label>

            <label>
              <span class="mb-1 block text-xs font-semibold text-neutral-600">Notes</span>
              <textarea bind:value={form.notes} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm resize-none"></textarea>
            </label>

            <div class="grid grid-cols-2 gap-4">
              <label>
                <span class="mb-1 block text-xs font-semibold text-neutral-600">Approved By</span>
                <input bind:value={form.approved_by} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
              </label>
              <label>
                <span class="mb-1 block text-xs font-semibold text-neutral-600">Approved Date</span>
                <DateInput bind:value={form.approved_date} />
              </label>
            </div>

            <!-- Approval section -->
            {#if workflow}
              <div class="rounded-xl border border-neutral-200 p-4 mt-2">
                <DecisionPanel instance={workflow} onDecision={() => poId && loadWorkflow(poId)} />
                {#if workflow.steps.length > 0}
                  <div class="mt-4">
                    <h4 class="text-xs font-semibold text-neutral-600 mb-2">Approval Progress</h4>
                    <ApprovalTimeline steps={workflow.steps} />
                  </div>
                {/if}
              </div>
            {:else if po.status === "draft"}
              <div class="rounded-xl border border-neutral-200 p-4 mt-2">
                <h4 class="text-xs font-semibold text-neutral-600 mb-1">Approval</h4>
                <p class="text-[11px] text-neutral-400 mb-3">Submit this PO for workflow-based approval routing.</p>
                <button
                  type="button"
                  onclick={submitForApproval}
                  disabled={submittingApproval}
                  class="w-full px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50"
                >
                  {submittingApproval ? "Submitting..." : "Submit for Approval"}
                </button>
              </div>
            {/if}

            <div class="flex items-center justify-between pt-2">
              <button
                type="submit"
                disabled={saving}
                class="rounded-lg bg-neutral-900 px-5 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
              >
                {saving ? "Saving..." : "Save Changes"}
              </button>
              <button
                type="button"
                onclick={handleDelete}
                disabled={deleting}
                class="rounded-lg border border-red-200 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50"
              >
                {deleting ? "Deleting..." : "Delete PO"}
              </button>
            </div>
          </form>

        <!-- ─── Items tab ────────────────────────────────────────── -->
        {:else if activeTab === "items"}
          <div class="p-6 space-y-4">
            {#if poItems.length > 0}
              <div class="overflow-hidden rounded-xl border border-neutral-200">
                <table class="w-full text-sm">
                  <thead>
                    <tr class="border-b border-neutral-200 bg-neutral-50">
                      <th class="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Description</th>
                      <th class="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Qty</th>
                      <th class="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">UOM</th>
                      <th class="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Unit Price</th>
                      <th class="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Amount</th>
                      <th class="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Recv</th>
                      <th class="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Rem</th>
                      <th class="px-4 py-2.5 w-12"></th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-neutral-100">
                    {#each poItems as item}
                      <tr class="hover:bg-neutral-50">
                        <td class="px-4 py-3 text-neutral-900">{item.description}</td>
                        <td class="px-4 py-3 text-right text-neutral-500 tabular-nums">{item.quantity}</td>
                        <td class="px-4 py-3 text-neutral-500">{item.unit_of_measure || "\u2014"}</td>
                        <td class="px-4 py-3 text-right text-neutral-500 tabular-nums">{fmtCurrency(item.unit_price)}</td>
                        <td class="px-4 py-3 text-right text-neutral-900 tabular-nums font-medium">{fmtCurrency(item.amount)}</td>
                        <td class="px-4 py-3 text-right tabular-nums {Number(item.quantity_received) > 0 ? 'text-emerald-700' : 'text-neutral-400'}">{item.quantity_received}</td>
                        <td class="px-4 py-3 text-right tabular-nums {Number(item.quantity_remaining) > 0 ? 'text-amber-700' : 'text-neutral-400'}">{item.quantity_remaining}</td>
                        <td class="px-4 py-3 text-right">
                          <button onclick={() => removeItem(item.id)} class="text-xs text-neutral-400 hover:text-red-600">Del</button>
                        </td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </div>
            {:else}
              <p class="text-center text-sm text-neutral-400 py-6">No items yet.</p>
            {/if}

            <!-- Add item -->
            <div class="rounded-xl border border-neutral-200 p-4 space-y-3">
              <h4 class="text-xs font-semibold text-neutral-600">Add Line Item</h4>
              <div class="grid grid-cols-4 gap-3">
                <label class="col-span-4">
                  <input bind:value={itemForm.description} placeholder="Description" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
                </label>
                <label>
                  <input bind:value={itemForm.quantity} placeholder="Qty" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm tabular-nums" />
                </label>
                <label>
                  <input bind:value={itemForm.unit_of_measure} placeholder="UOM" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
                </label>
                <label>
                  <input bind:value={itemForm.unit_price} placeholder="Unit price" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm tabular-nums" />
                </label>
                <button
                  type="button"
                  onclick={addItem}
                  disabled={addingItem}
                  class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
                >
                  {addingItem ? "..." : "Add"}
                </button>
              </div>
            </div>
          </div>

        <!-- ─── Goods Receipts tab ───────────────────────────────── -->
        {:else if activeTab === "receipts"}
          <div class="p-6 space-y-4">
            <div class="flex items-center justify-between">
              <h4 class="text-sm font-semibold text-neutral-900">Goods Receipts</h4>
              <button
                type="button"
                onclick={() => (showGrnForm = !showGrnForm)}
                class="rounded-lg bg-neutral-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-neutral-800"
              >
                {showGrnForm ? "Cancel" : "Record Delivery"}
              </button>
            </div>

            {#if showGrnForm}
              <div class="rounded-xl border border-neutral-200 p-4 space-y-3">
                <div class="grid grid-cols-2 gap-3">
                  <label>
                    <span class="mb-1 block text-xs font-semibold text-neutral-600">Received Date</span>
                    <DateInput bind:value={grnForm.received_date} />
                  </label>
                  <label>
                    <span class="mb-1 block text-xs font-semibold text-neutral-600">Received By</span>
                    <input bind:value={grnForm.received_by} placeholder="Name" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
                  </label>
                  <label>
                    <span class="mb-1 block text-xs font-semibold text-neutral-600">Delivery Note #</span>
                    <input bind:value={grnForm.delivery_note_number} placeholder="Optional" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
                  </label>
                  <label>
                    <span class="mb-1 block text-xs font-semibold text-neutral-600">Notes</span>
                    <input bind:value={grnForm.notes} placeholder="Optional" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
                  </label>
                </div>
                <button
                  type="button"
                  onclick={recordGoodsReceipt}
                  disabled={savingGrn}
                  class="rounded-lg bg-neutral-900 px-5 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
                >
                  {savingGrn ? "Saving..." : "Save Goods Receipt"}
                </button>
              </div>
            {/if}

            {#if poGoodsReceipts.length > 0}
              <div class="overflow-hidden rounded-xl border border-neutral-200">
                <table class="w-full text-sm">
                  <thead>
                    <tr class="border-b border-neutral-200 bg-neutral-50">
                      <th class="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">GRN #</th>
                      <th class="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Status</th>
                      <th class="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Date</th>
                      <th class="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Received By</th>
                      <th class="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">DN #</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-neutral-100">
                    {#each poGoodsReceipts as grn}
                      <tr
                        class="hover:bg-neutral-50 cursor-pointer"
                        onclick={() => goto(`/procurement/goods-receipts/${grn.id}`)}
                      >
                        <td class="px-4 py-3 font-medium text-neutral-900">{grn.grn_number}</td>
                        <td class="px-4 py-3"><StatusBadge status={grn.status} /></td>
                        <td class="px-4 py-3 text-neutral-500">{fmtDate(grn.received_date)}</td>
                        <td class="px-4 py-3 text-neutral-500">{grn.received_by || "\u2014"}</td>
                        <td class="px-4 py-3 text-neutral-500">{grn.delivery_note_number || "\u2014"}</td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </div>
            {:else}
              <p class="text-center text-sm text-neutral-400 py-6">No goods receipts recorded yet.</p>
            {/if}
          </div>

        <!-- ─── 3-Way Match tab ──────────────────────────────────── -->
        {:else if activeTab === "match"}
          <div class="p-6 space-y-5">
            <div class="flex items-center gap-3">
              <h4 class="text-sm font-semibold text-neutral-900">3-Way Match</h4>
              <StatusBadge status={poThreeWayMatch.status} />
            </div>

            <div class="grid grid-cols-3 gap-3">
              <div class="text-center p-4 rounded-xl bg-neutral-50 border border-neutral-100">
                <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">PO Total</p>
                <p class="text-lg font-semibold text-neutral-900 tabular-nums mt-1">{fmtCurrency(poThreeWayMatch.po_total)}</p>
              </div>
              <div class="text-center p-4 rounded-xl bg-neutral-50 border border-neutral-100">
                <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">GRN Accepted</p>
                <p class="text-lg font-semibold text-neutral-900 tabular-nums mt-1">{fmtCurrency(poThreeWayMatch.grn_accepted_total)}</p>
              </div>
              <div class="text-center p-4 rounded-xl bg-neutral-50 border border-neutral-100">
                <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Invoice Total</p>
                <p class="text-lg font-semibold text-neutral-900 tabular-nums mt-1">{fmtCurrency(poThreeWayMatch.invoice_total)}</p>
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

        <!-- ─── Bills tab ────────────────────────────────────────── -->
        {:else if activeTab === "bills"}
          <div class="p-6">
            {#if poBills.length > 0}
              <div class="overflow-hidden rounded-xl border border-neutral-200">
                <table class="w-full text-sm">
                  <thead>
                    <tr class="border-b border-neutral-200 bg-neutral-50">
                      <th class="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Bill #</th>
                      <th class="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Status</th>
                      <th class="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Due</th>
                      <th class="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Total</th>
                      <th class="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Paid</th>
                      <th class="px-4 py-2.5 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Balance</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-neutral-100">
                    {#each poBills as bill}
                      <tr
                        class="hover:bg-neutral-50 cursor-pointer"
                        onclick={() => goto(`/finance/bills/${bill.id}`)}
                      >
                        <td class="px-4 py-3 font-medium text-neutral-900">{bill.bill_number}</td>
                        <td class="px-4 py-3"><StatusBadge status={bill.status} /></td>
                        <td class="px-4 py-3 text-neutral-500">{fmtDate(bill.due_date)}</td>
                        <td class="px-4 py-3 text-right text-neutral-900 tabular-nums font-medium">{fmtCurrency(bill.total_amount)}</td>
                        <td class="px-4 py-3 text-right text-emerald-600 tabular-nums">{fmtCurrency(bill.paid_amount)}</td>
                        <td class="px-4 py-3 text-right tabular-nums {Number(bill.balance_due) > 0 ? 'text-red-600' : 'text-neutral-900'}">{fmtCurrency(bill.balance_due)}</td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </div>
            {:else}
              <p class="text-center text-sm text-neutral-400 py-6">No bills linked to this purchase order.</p>
            {/if}
          </div>
        {/if}
      </div>
    {/if}
  </div>
{/if}

<style>
  @keyframes slideIn {
    from { transform: translateX(100%); }
    to   { transform: translateX(0); }
  }
  .animate-slide-in {
    animation: slideIn 0.2s ease-out;
  }
</style>

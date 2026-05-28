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
    PurchaseRequisition,
    PurchaseRequisitionItem,
    ProjectListItem,
    PropertyListItem,
    MasterDataEntry,
    PaginatedResponse,
    WorkflowInstanceDetail,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  const id = $derived($page.params.id);

  let pr = $state<PurchaseRequisition | null>(null);
  let loading = $state(true);
  let saving = $state(false);
  let deleting = $state(false);
  let errors = $state<Record<string, string[]>>({});

  let projects = $state<ProjectListItem[]>([]);
  let properties = $state<PropertyListItem[]>([]);
  let budgetLines = $state<BudgetLineOption[]>([]);
  let costCodes = $state<MasterDataEntry[]>([]);

  // Workflow state
  let workflow = $state<WorkflowInstanceDetail | null>(null);
  let submittingWorkflow = $state(false);
  const prItems = $derived.by(() => pr?.items ?? []);

  async function loadWorkflow() {
    if (!id) {
      workflow = null;
      return;
    }
    try {
      const res = await api.get<{ results: WorkflowInstanceDetail[] }>("/workflows/instances/", {
        model: "procurement.purchaserequisition",
        object_id: id,
      });
      workflow = res.results.length > 0 ? res.results[0] : null;
    } catch {
      workflow = null;
    }
  }

  async function submitWorkflowApproval() {
    if (!id) return;
    submittingWorkflow = true;
    try {
      await api.post(`/procurement/requisitions/${id}/submit-approval/`, {});
      toast.success("Submitted", "Requisition has been submitted for workflow approval.");
      await Promise.all([loadPR(), loadWorkflow()]);
    } catch {
      toast.error("Error", "Could not submit for workflow approval.");
    } finally {
      submittingWorkflow = false;
    }
  }

  // Editable form state
  let form = $state({
    title: "",
    requester: "",
    project: "",
    property: "",
    priority: "medium",
    required_date: "",
    status: "draft",
    budget_line_item: "",
    budget_code: "",
    cost_code: "",
    justification: "",
    notes: "",
    approved_by: "",
    approved_date: "",
    rejected_reason: "",
  });

  // Line item add form
  let itemForm = $state({
    description: "",
    quantity: "",
    unit_of_measure: "",
    estimated_unit_price: "",
  });
  let addingItem = $state(false);

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

  async function loadPR() {
    if (!id) {
      pr = null;
      loading = false;
      return;
    }
    loading = true;
    try {
      pr = await api.get<PurchaseRequisition>(`/procurement/requisitions/${id}/`);
      form = {
        title: pr.title,
        requester: pr.requester,
        project: pr.project ? String(pr.project) : "",
        property: pr.property ? String(pr.property) : "",
        priority: pr.priority,
        required_date: pr.required_date,
        status: pr.status,
        budget_line_item: pr.budget_line_item ? String(pr.budget_line_item) : "",
        budget_code: pr.budget_code,
        cost_code: pr.cost_code,
        justification: pr.justification,
        notes: pr.notes,
        approved_by: pr.approved_by,
        approved_date: pr.approved_date ?? "",
        rejected_reason: pr.rejected_reason,
      };
    } catch {
      pr = null;
    }
    loading = false;
  }

  $effect(() => {
    fetchProjects();
    fetchProperties();
    Promise.all([
      fetchBudgetLineOptions().then((rows) => (budgetLines = rows)),
      fetchCostCodeOptions().then((rows) => (costCodes = rows)),
    ]);
  });

  $effect(() => {
    void id;
    loadPR();
    loadWorkflow();
  });

  function fieldError(field: string): string {
    return errors[field]?.[0] ?? "";
  }

  function formatCurrency(value: string | null): string {
    if (!value) return "\u2014";
    return currency.format(value);
  }

  // --- Save PR ---
  async function handleSave(e: Event) {
    e.preventDefault();
    errors = {};
    saving = true;
    try {
      const payload: Record<string, unknown> = {
        title: form.title,
        requester: form.requester,
        project: form.project ? Number(form.project) : null,
        property: form.property ? Number(form.property) : null,
        priority: form.priority,
        required_date: form.required_date || null,
        status: form.status,
        budget_line_item: form.budget_line_item ? Number(form.budget_line_item) : null,
        budget_code: form.budget_code,
        cost_code: form.cost_code,
        justification: form.justification,
        notes: form.notes,
      };
      if (form.status === "approved" || form.status === "rejected") {
        payload.approved_by = form.approved_by;
        payload.approved_date = form.approved_date || null;
        payload.rejected_reason = form.rejected_reason;
      }
      await api.patch<PurchaseRequisition>(`/procurement/requisitions/${id}/`, payload);
      await loadPR();
      toast.success("Requisition updated", "Changes have been saved");
    } catch (err) {
      if (err instanceof ApiError) {
        errors = err.fieldErrors;
        toast.error("Validation error", "Please fix the highlighted fields below");
      } else {
        toast.error("Something went wrong", "Could not update the requisition");
      }
    }
    saving = false;
  }

  // --- Delete PR ---
  async function handleDelete() {
    if (!confirm("Are you sure you want to delete this requisition? This action cannot be undone.")) return;
    deleting = true;
    try {
      await api.delete(`/procurement/requisitions/${id}/`);
      toast.success("Requisition deleted", "The requisition has been removed");
      goto("/procurement/requisitions");
    } catch {
      toast.error("Something went wrong", "Could not delete the requisition");
    }
    deleting = false;
  }

  // --- Status Transitions ---
  async function submitForApproval() {
    if (!confirm("Submit this requisition for approval?")) return;
    saving = true;
    try {
      await api.patch<PurchaseRequisition>(`/procurement/requisitions/${id}/`, { status: "submitted" });
      await Promise.all([loadPR(), loadWorkflow()]);
      toast.success("Requisition submitted", "The requisition has been submitted for approval");
    } catch (err) {
      if (err instanceof ApiError) {
        const msg = Object.values(err.fieldErrors).flat()[0];
        toast.error("Could not submit", msg || "Please check the requisition details");
      } else {
        toast.error("Something went wrong", "Could not submit the requisition");
      }
    }
    saving = false;
  }

  async function approveRequisition() {
    const approver = prompt("Approved by (name):");
    if (!approver) return;
    saving = true;
    try {
      const today = new Date().toISOString().slice(0, 10);
      await api.patch<PurchaseRequisition>(`/procurement/requisitions/${id}/`, {
        status: "approved",
        approved_by: approver,
        approved_date: today,
      });
      await Promise.all([loadPR(), loadWorkflow()]);
      toast.success("Requisition approved", "The requisition has been approved");
    } catch (err) {
      if (err instanceof ApiError) {
        const msg = Object.values(err.fieldErrors).flat()[0];
        toast.error("Could not approve", msg || "Please check the requisition details");
      } else {
        toast.error("Something went wrong", "Could not approve the requisition");
      }
    }
    saving = false;
  }

  async function rejectRequisition() {
    const reason = prompt("Reason for rejection:");
    if (reason === null) return;
    saving = true;
    try {
      await api.patch<PurchaseRequisition>(`/procurement/requisitions/${id}/`, {
        status: "rejected",
        rejected_reason: reason,
      });
      await Promise.all([loadPR(), loadWorkflow()]);
      toast.success("Requisition rejected", "The requisition has been rejected");
    } catch (err) {
      if (err instanceof ApiError) {
        const msg = Object.values(err.fieldErrors).flat()[0];
        toast.error("Could not reject", msg || "Please check the requisition details");
      } else {
        toast.error("Something went wrong", "Could not reject the requisition");
      }
    }
    saving = false;
  }

  // --- Line Items ---
  async function addItem() {
    if (!itemForm.description || !itemForm.quantity || !itemForm.estimated_unit_price) return;
    addingItem = true;
    try {
      await api.post(`/procurement/requisitions/${id}/items/`, {
        description: itemForm.description,
        quantity: itemForm.quantity,
        unit_of_measure: itemForm.unit_of_measure,
        estimated_unit_price: itemForm.estimated_unit_price,
      });
      itemForm = { description: "", quantity: "", unit_of_measure: "", estimated_unit_price: "" };
      toast.success("Item added", "The item has been added to this requisition");
      await loadPR();
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
      await api.delete(`/procurement/requisitions/${id}/items/${itemId}/`);
      toast.success("Item removed", "The item has been deleted");
      await loadPR();
    } catch {
      toast.error("Something went wrong", "Could not remove item");
    }
  }
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
  </div>
{:else if !pr}
  <div class="text-center py-24">
    <p class="text-neutral-400">Requisition not found.</p>
    <a href="/procurement/requisitions" class="mt-4 inline-block text-sm font-medium text-neutral-900 hover:underline">Back to requisitions</a>
  </div>
{:else}
  <!-- Header -->
  <div class="mb-8">
    <Breadcrumb items={[{ label: "Procurement", href: "/procurement" }, { label: "Requisitions", href: "/procurement/requisitions" }, { label: pr.pr_number }]} />
    <div class="flex items-center gap-4 mt-3">
      <h1 class="text-2xl font-bold text-neutral-900">{pr.pr_number}</h1>
      <StatusBadge status={pr.status} size="md" />
      <StatusBadge status={pr.priority} size="md" />
      {#if workflow}
        <StatusBadge status={workflow.state} size="md" />
      {/if}
    </div>
    <p class="text-sm text-neutral-500 mt-1">{pr.title}</p>
  </div>

  <!-- Two-column layout -->
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
    <!-- Left: Editable form (2 cols) -->
    <div class="lg:col-span-2">
      <form onsubmit={handleSave} class="bg-white rounded-xl border border-neutral-200 p-6 space-y-5">
        <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Requisition Details</h3>

        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Title</span>
          <input
            bind:value={form.title}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          />
          {#if fieldError("title")}<p class="mt-1 text-xs text-red-500">{fieldError("title")}</p>{/if}
        </label>

        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Requester</span>
          <input
            bind:value={form.requester}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          />
          {#if fieldError("requester")}<p class="mt-1 text-xs text-red-500">{fieldError("requester")}</p>{/if}
        </label>

        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Status</span>
            <select
              bind:value={form.status}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            >
              <option value="draft">Draft</option>
              <option value="submitted">Submitted</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="cancelled">Cancelled</option>
              <option value="ordered">Ordered</option>
            </select>
            {#if fieldError("status")}<p class="mt-1 text-xs text-red-500">{fieldError("status")}</p>{/if}
          </label>

          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Priority</span>
            <select
              bind:value={form.priority}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="urgent">Urgent</option>
            </select>
            {#if fieldError("priority")}<p class="mt-1 text-xs text-red-500">{fieldError("priority")}</p>{/if}
          </label>
        </div>

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

        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Required Date</span>
            <DateInput bind:value={form.required_date} />
            {#if fieldError("required_date")}<p class="mt-1 text-xs text-red-500">{fieldError("required_date")}</p>{/if}
          </label>

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
        </div>

        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Budget Code</span>
            <input
              bind:value={form.budget_code}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
              placeholder="e.g. CAPEX-2024-001"
            />
            {#if fieldError("budget_code")}<p class="mt-1 text-xs text-red-500">{fieldError("budget_code")}</p>{/if}
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
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Justification</span>
          <textarea
            bind:value={form.justification}
            rows={3}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white resize-none
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            placeholder="Business justification for this requisition..."
          ></textarea>
          {#if fieldError("justification")}<p class="mt-1 text-xs text-red-500">{fieldError("justification")}</p>{/if}
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

        <!-- Approval section (shown when approved or rejected) -->
        {#if form.status === "approved" || form.status === "rejected"}
          <div class="border-t border-neutral-100 pt-5 space-y-4">
            <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Approval Details</h3>

            <div class="grid grid-cols-2 gap-4">
              <label>
                <span class="block text-sm font-medium text-neutral-700 mb-1.5">Approved By</span>
                <input
                  bind:value={form.approved_by}
                  class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                         focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
                />
                {#if fieldError("approved_by")}<p class="mt-1 text-xs text-red-500">{fieldError("approved_by")}</p>{/if}
              </label>

              <label>
                <span class="block text-sm font-medium text-neutral-700 mb-1.5">Approved Date</span>
                <DateInput bind:value={form.approved_date} />
                {#if fieldError("approved_date")}<p class="mt-1 text-xs text-red-500">{fieldError("approved_date")}</p>{/if}
              </label>
            </div>

            {#if form.status === "rejected"}
              <label>
                <span class="block text-sm font-medium text-neutral-700 mb-1.5">Rejection Reason</span>
                <textarea
                  bind:value={form.rejected_reason}
                  rows={2}
                  class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white resize-none
                         focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
                  placeholder="Reason for rejection..."
                ></textarea>
                {#if fieldError("rejected_reason")}<p class="mt-1 text-xs text-red-500">{fieldError("rejected_reason")}</p>{/if}
              </label>
            {/if}
          </div>
        {/if}

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
            {deleting ? "Deleting..." : "Delete Requisition"}
          </button>
        </div>
      </form>
    </div>

    <!-- Right: Summary & Actions (1 col) -->
    <div class="space-y-6">
      <!-- Summary card -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6">
        <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Summary</h3>
        <div class="space-y-3 text-sm">
          <div class="flex justify-between">
            <span class="text-neutral-400">Estimated Total</span>
            <span class="text-neutral-900 tabular-nums font-semibold">{formatCurrency(pr.estimated_total)}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-neutral-400">Items</span>
            <span class="text-neutral-900 tabular-nums">{pr.item_count}</span>
          </div>
          <div class="flex justify-between">
            <span class="text-neutral-400">Priority</span>
            <StatusBadge status={pr.priority} />
          </div>
          {#if pr.required_date}
            <div class="flex justify-between">
              <span class="text-neutral-400">Required By</span>
              <span class="text-neutral-900">{new Date(pr.required_date).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" })}</span>
            </div>
          {/if}
          {#if pr.project_name}
            <div class="flex justify-between">
              <span class="text-neutral-400">Project</span>
              <span class="text-neutral-900">{pr.project_name}</span>
            </div>
          {/if}
          {#if pr.property_name}
            <div class="flex justify-between">
              <span class="text-neutral-400">Property</span>
              <span class="text-neutral-900">{pr.property_name}</span>
            </div>
          {/if}
        </div>
      </div>

      <!-- Status Actions card -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6">
        <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Actions</h3>
        <div class="space-y-3">
          {#if pr.status === "draft"}
            <button
              type="button"
              onclick={submitForApproval}
              disabled={saving}
              class="w-full px-4 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium
                     hover:bg-neutral-800 disabled:opacity-50 transition-colors"
            >
              {saving ? "Submitting..." : "Submit for Approval"}
            </button>
            {#if !workflow}
              <button
                type="button"
                onclick={submitWorkflowApproval}
                disabled={submittingWorkflow}
                class="w-full px-4 py-2.5 border border-neutral-200 text-neutral-700 rounded-lg text-sm font-medium
                       hover:bg-neutral-50 disabled:opacity-50 transition-colors"
              >
                {submittingWorkflow ? "Submitting..." : "Submit via Workflow"}
              </button>
            {/if}
          {/if}

          {#if pr.status === "submitted"}
            <button
              type="button"
              onclick={approveRequisition}
              disabled={saving}
              class="w-full px-4 py-2.5 bg-emerald-600 text-white rounded-lg text-sm font-medium
                     hover:bg-emerald-700 disabled:opacity-50 transition-colors"
            >
              {saving ? "Approving..." : "Approve"}
            </button>
            <button
              type="button"
              onclick={rejectRequisition}
              disabled={saving}
              class="w-full px-4 py-2.5 border border-red-200 text-red-600 rounded-lg text-sm font-medium
                     hover:bg-red-50 disabled:opacity-50 transition-colors"
            >
              {saving ? "Rejecting..." : "Reject"}
            </button>
          {/if}

          {#if pr.status === "approved"}
            <button
              type="button"
              onclick={() => goto(`/procurement/purchase-orders/new?from_pr=${id}`)}
              class="w-full px-4 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium
                     hover:bg-neutral-800 transition-colors"
            >
              Create Purchase Order
            </button>
          {/if}

          {#if pr.status === "cancelled" || pr.status === "rejected" || pr.status === "ordered"}
            <p class="text-sm text-neutral-400 text-center">No actions available</p>
          {/if}
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
      {/if}
    </div>
  </div>

  <!-- Items -->
  <div class="mb-8">
    <h3 class="text-lg font-semibold text-neutral-900 mb-4">Items</h3>
    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      {#if prItems.length > 0}
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-neutral-200">
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Description</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Qty</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">UOM</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Unit Price</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Amount</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each prItems as item}
              <tr class="hover:bg-neutral-50 transition-colors">
                <td class="px-5 py-4 text-neutral-900">{item.description}</td>
                <td class="px-5 py-4 text-right text-neutral-500 tabular-nums">{item.quantity}</td>
                <td class="px-5 py-4 text-neutral-500">{item.unit_of_measure || "\u2014"}</td>
                <td class="px-5 py-4 text-right text-neutral-500 tabular-nums">{formatCurrency(item.estimated_unit_price)}</td>
                <td class="px-5 py-4 text-right text-neutral-900 tabular-nums font-medium">{formatCurrency(item.estimated_amount)}</td>
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
              placeholder="e.g. each"
            />
          </label>
          <label class="w-32">
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Unit Price</span>
            <input
              bind:value={itemForm.estimated_unit_price}
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
{/if}

<script lang="ts">
  import { useAutoRefresh } from "$lib/realtime.svelte";
  import { api, ApiError } from "$lib/api";
  import { fetchBudgetLineOptions, fetchCostCodeOptions, type BudgetLineOption } from "$lib/procurement";
  import { toast } from "$lib/stores/toast.svelte";
  import Modal from "$lib/components/Modal.svelte";
  import DrawerShell from "$lib/components/DrawerShell.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import type {
    PurchaseRequisitionListItem,
    PurchaseRequisition,
    ProjectListItem,
    PropertyListItem,
    MasterDataEntry,
    PaginatedResponse,
    WorkflowInstanceDetail,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let data = $state<PurchaseRequisitionListItem[]>([]);
  let totalCount = $state(0);
  let currentPage = $state(1);
  let searchQuery = $state("");
  let statusFilter = $state("");
  let priorityFilter = $state("");
  let loading = $state(true);
  let projects = $state<ProjectListItem[]>([]);
  let properties = $state<PropertyListItem[]>([]);
  let budgetLines = $state<BudgetLineOption[]>([]);
  let costCodes = $state<MasterDataEntry[]>([]);

  let showCreateModal = $state(false);
  let createForm = $state({
    title: "",
    requester: "",
    project: "",
    property: "",
    priority: "medium",
    required_date: "",
    budget_line_item: "",
    budget_code: "",
    cost_code: "",
    justification: "",
    notes: "",
  });
  let createErrors = $state<Record<string, string[]>>({});
  let savingRequisition = $state(false);

  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  type ReqForm = typeof createForm;
  const REQ_SAMPLES: ReqForm[] = [
    {
      title: "Ready-mix concrete — Block C foundations",
      requester: "David Mensah",
      project: "",
      property: "",
      priority: "high",
      required_date: new Date(Date.now() + 10 * 86400000).toISOString().slice(0, 10),
      budget_line_item: "",
      budget_code: "STRUCT-2026-004",
      cost_code: "",
      justification: "Foundation pour for Block C scheduled in two weeks. 380 m³ C40 concrete required per structural engineer's specification. Lead time from Lafarge is 7 working days — order must be placed this week to avoid programme delay.",
      notes: "Pump truck access via Gate 3 only. Coordinate with site logistics for 06:00 delivery slots.",
    },
    {
      title: "Structural steel — Level 12-15 framing",
      requester: "Priya Naidoo",
      project: "",
      property: "",
      priority: "urgent",
      required_date: new Date(Date.now() + 5 * 86400000).toISOString().slice(0, 10),
      budget_line_item: "",
      budget_code: "STRUCT-2026-007",
      cost_code: "",
      justification: "Tower crane standing time begins next Monday if steel is not on site. 42 tonnes of S355 universal beams and columns required for floors 12–15. Procurement delay will trigger VO for crane idle costs estimated at £8,500/day.",
      notes: "Mill certs and inspection release notes required before delivery acceptance. Contact QA team for sampling schedule.",
    },
    {
      title: "MEP ductwork — HVAC risers Block A",
      requester: "James Okafor",
      project: "",
      property: "",
      priority: "medium",
      required_date: new Date(Date.now() + 21 * 86400000).toISOString().slice(0, 10),
      budget_line_item: "",
      budget_code: "MEP-2026-012",
      cost_code: "",
      justification: "First-fix HVAC installation on floors 5–10 commences in three weeks. Galvanised rectangular ductwork (1200×600 and 800×400 sections) plus fire dampers needed. Early order avoids clash with electrical rough-in programme.",
      notes: "Ductwork to be delivered in labelled bundles per floor level. Storage area allocated in basement car park zone D.",
    },
    {
      title: "Façade aluminium curtain wall panels",
      requester: "Amara Diallo",
      project: "",
      property: "",
      priority: "high",
      required_date: new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10),
      budget_line_item: "",
      budget_code: "EXT-2026-003",
      cost_code: "",
      justification: "Building envelope programme requires curtain wall installation to begin on the north elevation by end of month. 240 unitised panels (1500×3600 mm) with double-glazed IGUs. Factory lead time is 4 weeks — order cutoff is this Friday.",
      notes: "Panels arrive on flatbed trucks — crane offload required. Verify tower crane radius covers north elevation laydown area.",
    },
  ];

  let reqDevIdx = 0;

  function devFillRequisition() {
    const sample = REQ_SAMPLES[reqDevIdx % REQ_SAMPLES.length];
    reqDevIdx++;
    createForm = {
      ...sample,
      project: createForm.project || (projects.length > 0 ? String(projects[0].id) : ""),
      property: createForm.property,
      budget_line_item: createForm.budget_line_item,
      cost_code: createForm.cost_code,
    };
  }

  function createFieldError(field: string): string {
    return createErrors[field]?.[0] ?? "";
  }

  function resetCreateForm() {
    createForm = {
      title: "",
      requester: "",
      project: "",
      property: "",
      priority: "medium",
      required_date: "",
      budget_line_item: "",
      budget_code: "",
      cost_code: "",
      justification: "",
      notes: "",
    };
    createErrors = {};
  }

  async function handleCreateRequisition(e: Event) {
    e.preventDefault();
    createErrors = {};
    savingRequisition = true;

    try {
      const payload: Record<string, unknown> = {
        title: createForm.title,
        requester: createForm.requester,
        project: createForm.project ? Number(createForm.project) : null,
        property: createForm.property ? Number(createForm.property) : null,
        priority: createForm.priority,
        required_date: createForm.required_date || null,
        budget_line_item: createForm.budget_line_item ? Number(createForm.budget_line_item) : null,
        budget_code: createForm.budget_code,
        cost_code: createForm.cost_code,
        justification: createForm.justification,
        notes: createForm.notes,
      };
      const result = await api.post<PurchaseRequisition>("/procurement/requisitions/", payload);
      toast.success("Requisition created", `"${result.title}" has been added`);
      showCreateModal = false;
      resetCreateForm();
      fetchRequisitions();
    } catch (err) {
      if (err instanceof ApiError) {
        createErrors = err.fieldErrors;
        toast.error("Validation error", "Please fix the highlighted fields below");
      } else {
        toast.error("Something went wrong", "Could not create the requisition");
      }
    }
    savingRequisition = false;
  }

  const PAGE_SIZE = 25;
  const totalPages = $derived(Math.ceil(totalCount / PAGE_SIZE));
  const startItem = $derived((currentPage - 1) * PAGE_SIZE + 1);
  const endItem = $derived(Math.min(currentPage * PAGE_SIZE, totalCount));

  function pageNumbers(current: number, total: number): (number | "...")[] {
    if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
    const pages: (number | "...")[] = [1];
    if (current > 3) pages.push("...");
    const start = Math.max(2, current - 1);
    const end = Math.min(total - 1, current + 1);
    for (let i = start; i <= end; i++) pages.push(i);
    if (current < total - 2) pages.push("...");
    pages.push(total);
    return pages;
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

  async function fetchRequisitions() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage) };
      if (searchQuery) params.search = searchQuery;
      if (statusFilter) params.status = statusFilter;
      if (priorityFilter) params.priority = priorityFilter;

      const res = await api.get<PaginatedResponse<PurchaseRequisitionListItem>>("/procurement/requisitions/", params);
      data = res.results;
      totalCount = res.count;
    } catch {
      data = [];
      totalCount = 0;
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
    void searchQuery;
    void statusFilter;
    void priorityFilter;
    void currentPage;
    fetchRequisitions();
  });

  let searchTimeout: ReturnType<typeof setTimeout>;
  function onSearchInput(e: Event) {
    clearTimeout(searchTimeout);
    const value = (e.target as HTMLInputElement).value;
    searchTimeout = setTimeout(() => {
      searchQuery = value;
      currentPage = 1;
    }, 300);
  }

  function formatCurrency(value: string | null): string {
    if (!value) return "\u2014";
    return currency.formatCompact(value);
  }

  function formatDate(value: string | null): string {
    if (!value) return "\u2014";
    return new Date(value).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  }

  useAutoRefresh("PurchaseRequisition", fetchRequisitions);

  // ── Detail Drawer ──
  let showDetail = $state(false);
  let detailLoading = $state(false);
  let detailSaving = $state(false);
  let detailDeleting = $state(false);
  let pr = $state<PurchaseRequisition | null>(null);
  let detailErrors = $state<Record<string, string[]>>({});
  let workflow = $state<WorkflowInstanceDetail | null>(null);
  let submittingWorkflow = $state(false);

  let detailForm = $state({
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

  let itemForm = $state({ description: "", quantity: "", unit_of_measure: "", estimated_unit_price: "" });
  let addingItem = $state(false);
  let detailTab = $state<"details" | "items">("details");
  let detailEditing = $state(false);
  const isEditable = $derived(pr != null && (pr.status === "draft" || pr.status === "submitted"));

  function detailFieldError(field: string): string {
    return detailErrors[field]?.[0] ?? "";
  }

  function formatCurrencyFull(value: string | null): string {
    if (!value) return "\u2014";
    return currency.format(value);
  }

  async function openDetail(id: number) {
    showDetail = true;
    detailLoading = true;
    detailErrors = {};
    detailTab = "details";
    detailEditing = false;
    try {
      pr = await api.get<PurchaseRequisition>(`/procurement/requisitions/${id}/`);
      detailForm = {
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
      loadWorkflow(id);
    } catch {
      toast.error("Load failed", "Could not load requisition details");
      showDetail = false;
    }
    detailLoading = false;
  }

  async function loadWorkflow(id: number) {
    try {
      const res = await api.get<{ results: WorkflowInstanceDetail[] }>("/workflows/instances/", {
        model: "procurement.purchaserequisition",
        object_id: String(id),
      });
      workflow = res.results.length > 0 ? res.results[0] : null;
    } catch {
      workflow = null;
    }
  }

  async function saveDetail() {
    if (!pr) return;
    detailErrors = {};
    detailSaving = true;
    try {
      const payload: Record<string, unknown> = {
        title: detailForm.title,
        requester: detailForm.requester,
        project: detailForm.project ? Number(detailForm.project) : null,
        property: detailForm.property ? Number(detailForm.property) : null,
        priority: detailForm.priority,
        required_date: detailForm.required_date || null,
        status: detailForm.status,
        budget_line_item: detailForm.budget_line_item ? Number(detailForm.budget_line_item) : null,
        budget_code: detailForm.budget_code,
        cost_code: detailForm.cost_code,
        justification: detailForm.justification,
        notes: detailForm.notes,
      };
      if (detailForm.status === "approved" || detailForm.status === "rejected") {
        payload.approved_by = detailForm.approved_by;
        payload.approved_date = detailForm.approved_date || null;
        payload.rejected_reason = detailForm.rejected_reason;
      }
      await api.patch<PurchaseRequisition>(`/procurement/requisitions/${pr.id}/`, payload);
      toast.success("Requisition updated", "Changes have been saved");
      await openDetail(pr.id);
      fetchRequisitions();
    } catch (err) {
      if (err instanceof ApiError) {
        detailErrors = err.fieldErrors;
        toast.error("Validation error", "Please fix the highlighted fields");
      } else {
        toast.error("Save failed", "Could not update the requisition");
      }
    }
    detailSaving = false;
  }

  async function deleteRequisition() {
    if (!pr || !confirm("Delete this requisition? This cannot be undone.")) return;
    detailDeleting = true;
    try {
      await api.delete(`/procurement/requisitions/${pr.id}/`);
      toast.success("Requisition deleted", "The requisition has been removed");
      showDetail = false;
      fetchRequisitions();
    } catch {
      toast.error("Delete failed", "Could not delete the requisition");
    }
    detailDeleting = false;
  }

  async function submitForApproval() {
    if (!pr) return;
    detailSaving = true;
    try {
      await api.patch<PurchaseRequisition>(`/procurement/requisitions/${pr.id}/`, { status: "submitted" });
      toast.success("Submitted", "Requisition submitted for approval");
      await openDetail(pr.id);
      fetchRequisitions();
    } catch (err) {
      if (err instanceof ApiError) {
        const msg = Object.values(err.fieldErrors).flat()[0];
        toast.error("Could not submit", msg || "Check requisition details");
      } else {
        toast.error("Submit failed", "Could not submit the requisition");
      }
    }
    detailSaving = false;
  }

  async function submitWorkflowApproval() {
    if (!pr) return;
    submittingWorkflow = true;
    try {
      await api.post(`/procurement/requisitions/${pr.id}/submit-approval/`, {});
      toast.success("Submitted", "Requisition submitted for workflow approval");
      await openDetail(pr.id);
      fetchRequisitions();
    } catch {
      toast.error("Error", "Could not submit for workflow approval");
    }
    submittingWorkflow = false;
  }

  async function approveRequisition() {
    if (!pr) return;
    const approver = prompt("Approved by (name):");
    if (!approver) return;
    detailSaving = true;
    try {
      const today = new Date().toISOString().slice(0, 10);
      await api.patch<PurchaseRequisition>(`/procurement/requisitions/${pr.id}/`, {
        status: "approved",
        approved_by: approver,
        approved_date: today,
      });
      toast.success("Approved", "Requisition has been approved");
      await openDetail(pr.id);
      fetchRequisitions();
    } catch (err) {
      if (err instanceof ApiError) {
        const msg = Object.values(err.fieldErrors).flat()[0];
        toast.error("Could not approve", msg || "Check requisition details");
      } else {
        toast.error("Approve failed", "Could not approve the requisition");
      }
    }
    detailSaving = false;
  }

  async function rejectRequisition() {
    if (!pr) return;
    const reason = prompt("Reason for rejection:");
    if (reason === null) return;
    detailSaving = true;
    try {
      await api.patch<PurchaseRequisition>(`/procurement/requisitions/${pr.id}/`, {
        status: "rejected",
        rejected_reason: reason,
      });
      toast.success("Rejected", "Requisition has been rejected");
      await openDetail(pr.id);
      fetchRequisitions();
    } catch (err) {
      if (err instanceof ApiError) {
        const msg = Object.values(err.fieldErrors).flat()[0];
        toast.error("Could not reject", msg || "Check requisition details");
      } else {
        toast.error("Reject failed", "Could not reject the requisition");
      }
    }
    detailSaving = false;
  }

  async function addItem() {
    if (!pr || !itemForm.description || !itemForm.quantity || !itemForm.estimated_unit_price) return;
    addingItem = true;
    try {
      await api.post(`/procurement/requisitions/${pr.id}/items/`, {
        description: itemForm.description,
        quantity: itemForm.quantity,
        unit_of_measure: itemForm.unit_of_measure,
        estimated_unit_price: itemForm.estimated_unit_price,
      });
      itemForm = { description: "", quantity: "", unit_of_measure: "", estimated_unit_price: "" };
      toast.success("Item added", "Line item added to requisition");
      await openDetail(pr.id);
      fetchRequisitions();
    } catch (err) {
      if (err instanceof ApiError) {
        const msg = Object.values(err.fieldErrors).flat()[0];
        toast.error("Validation error", msg || "Could not add item");
      } else {
        toast.error("Error", "Could not add item");
      }
    }
    addingItem = false;
  }

  async function removeItem(itemId: number) {
    if (!pr || !confirm("Remove this item?")) return;
    try {
      await api.delete(`/procurement/requisitions/${pr.id}/items/${itemId}/`);
      toast.success("Item removed", "Line item deleted");
      await openDetail(pr.id);
      fetchRequisitions();
    } catch {
      toast.error("Error", "Could not remove item");
    }
  }

  function closeDetail() {
    showDetail = false;
    pr = null;
    workflow = null;
    detailErrors = {};
  }
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-700">Procurement</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Purchase Requisitions</h1>
      <p class="text-sm text-neutral-400 mt-1">Manage purchase requests and approvals</p>
    </div>
    <button
      onclick={() => showCreateModal = true}
      class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg hover:bg-neutral-800 text-sm font-medium transition-colors"
    >
      + New Requisition
    </button>
  </div>

  <!-- Filters -->
  <div class="flex gap-3 items-center">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
      </svg>
      <input
        type="text"
        placeholder="Search requisitions..."
        oninput={onSearchInput}
        class="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
               focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent
               placeholder:text-neutral-400"
      />
    </div>
    <select
      bind:value={statusFilter}
      onchange={() => (currentPage = 1)}
      class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600
             focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
    >
      <option value="">All Statuses</option>
      <option value="draft">Draft</option>
      <option value="submitted">Submitted</option>
      <option value="approved">Approved</option>
      <option value="rejected">Rejected</option>
      <option value="cancelled">Cancelled</option>
      <option value="ordered">Ordered</option>
    </select>
    <select
      bind:value={priorityFilter}
      onchange={() => (currentPage = 1)}
      class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600
             focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
    >
      <option value="">All Priorities</option>
      <option value="low">Low</option>
      <option value="medium">Medium</option>
      <option value="high">High</option>
      <option value="urgent">Urgent</option>
    </select>
  </div>

  <!-- Table -->
  <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
    {#if loading}
      <div class="p-16 text-center">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
        <p class="mt-3 text-sm text-neutral-400">Loading requisitions...</p>
      </div>
    {:else if data.length === 0}
      <div class="p-16 text-center">
        <svg class="w-12 h-12 mx-auto text-neutral-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
        </svg>
        <p class="mt-4 text-sm font-medium text-neutral-900">No requisitions found</p>
        <p class="mt-1 text-sm text-neutral-400">Get started by creating your first purchase requisition.</p>
        <button
          onclick={() => showCreateModal = true}
          class="inline-block mt-4 px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors"
        >
          + New Requisition
        </button>
      </div>
    {:else}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200">
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">PR #</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Title</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Requester</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Priority</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Required Date</th>
            <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Est. Total</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each data as requisition}
            <tr
              class="hover:bg-neutral-50 cursor-pointer transition-colors"
              onclick={() => openDetail(requisition.id)}
            >
              <td class="px-5 py-4">
                <span class="font-medium text-neutral-900">{requisition.pr_number}</span>
              </td>
              <td class="px-5 py-4 text-neutral-500">{requisition.title}</td>
              <td class="px-5 py-4 text-neutral-500">{requisition.requester}</td>
              <td class="px-5 py-4">
                <StatusBadge status={requisition.status} />
              </td>
              <td class="px-5 py-4">
                <StatusBadge status={requisition.priority} />
              </td>
              <td class="px-5 py-4 text-neutral-500">{formatDate(requisition.required_date)}</td>
              <td class="px-5 py-4 text-right text-neutral-900 tabular-nums">{formatCurrency(requisition.estimated_total)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>

  <!-- Pagination -->
  {#if totalCount > 0}
    <div class="flex items-center justify-between">
      <p class="text-sm text-neutral-400">
        Showing <span class="font-medium text-neutral-600">{startItem}–{endItem}</span> of
        <span class="font-medium text-neutral-600">{totalCount}</span>
        {totalCount === 1 ? "requisition" : "requisitions"}
      </p>

      {#if totalPages > 1}
        <div class="flex items-center gap-1">
          <button
            onclick={() => currentPage--}
            disabled={currentPage <= 1}
            class="w-9 h-9 flex items-center justify-center border border-neutral-200 rounded-lg text-neutral-500
                   hover:bg-neutral-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            aria-label="Previous page"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
            </svg>
          </button>

          {#each pageNumbers(currentPage, totalPages) as pg}
            {#if pg === "..."}
              <span class="w-9 h-9 flex items-center justify-center text-xs text-neutral-300">...</span>
            {:else}
              <button
                onclick={() => (currentPage = pg)}
                class="w-9 h-9 flex items-center justify-center rounded-lg text-sm font-medium transition-colors
                       {currentPage === pg
                         ? 'bg-neutral-900 text-white'
                         : 'text-neutral-500 hover:bg-neutral-100'}"
              >
                {pg}
              </button>
            {/if}
          {/each}

          <button
            onclick={() => currentPage++}
            disabled={currentPage >= totalPages}
            class="w-9 h-9 flex items-center justify-center border border-neutral-200 rounded-lg text-neutral-500
                   hover:bg-neutral-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            aria-label="Next page"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
            </svg>
          </button>
        </div>
      {/if}
    </div>
  {/if}
</div>

<Modal open={showCreateModal} onclose={() => { showCreateModal = false; resetCreateForm(); }} title="New Requisition" maxWidth="max-w-2xl">
  <form onsubmit={handleCreateRequisition} class="space-y-5">
    <!-- Title — full width -->
    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Title</span>
      <input
        type="text"
        bind:value={createForm.title}
        placeholder="Enter requisition title"
        class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
      />
      {#if createFieldError("title")}<p class="mt-1 text-xs text-red-500">{createFieldError("title")}</p>{/if}
    </label>

    <!-- Row: Requester + Priority -->
    <div class="grid grid-cols-2 gap-4">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Requester</span>
        <input
          type="text"
          bind:value={createForm.requester}
          placeholder="Name of requester"
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        />
        {#if createFieldError("requester")}<p class="mt-1 text-xs text-red-500">{createFieldError("requester")}</p>{/if}
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Priority</span>
        <select
          bind:value={createForm.priority}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        >
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="urgent">Urgent</option>
        </select>
        {#if createFieldError("priority")}<p class="mt-1 text-xs text-red-500">{createFieldError("priority")}</p>{/if}
      </label>
    </div>

    <!-- Row: Required Date + Budget Line -->
    <div class="grid grid-cols-2 gap-4">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Required Date</span>
        <DateInput bind:value={createForm.required_date} />
        {#if createFieldError("required_date")}<p class="mt-1 text-xs text-red-500">{createFieldError("required_date")}</p>{/if}
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Budget Line <span class="text-neutral-400 font-normal">(optional)</span></span>
        <select
          bind:value={createForm.budget_line_item}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        >
          <option value="">None</option>
          {#each budgetLines as line}
            <option value={String(line.id)}>{line.label}</option>
          {/each}
        </select>
        {#if createFieldError("budget_line_item")}<p class="mt-1 text-xs text-red-500">{createFieldError("budget_line_item")}</p>{/if}
      </label>
    </div>

    <div class="grid grid-cols-2 gap-4">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Budget Code <span class="text-neutral-400 font-normal">(optional)</span></span>
        <input
          type="text"
          bind:value={createForm.budget_code}
          placeholder="e.g. DEPT-2024-001"
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        />
        {#if createFieldError("budget_code")}<p class="mt-1 text-xs text-red-500">{createFieldError("budget_code")}</p>{/if}
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Cost Code <span class="text-neutral-400 font-normal">(optional)</span></span>
        <select
          bind:value={createForm.cost_code}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        >
          <option value="">None</option>
          {#each costCodes as code}
            <option value={code.code}>{code.code} - {code.label}</option>
          {/each}
        </select>
        {#if createFieldError("cost_code")}<p class="mt-1 text-xs text-red-500">{createFieldError("cost_code")}</p>{/if}
      </label>
    </div>

    <!-- Row: Project + Property -->
    <div class="grid grid-cols-2 gap-4">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Project <span class="text-neutral-400 font-normal">(optional)</span></span>
        <select
          bind:value={createForm.project}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        >
          <option value="">None</option>
          {#each projects as project}
            <option value={String(project.id)}>{project.name}</option>
          {/each}
        </select>
        {#if createFieldError("project")}<p class="mt-1 text-xs text-red-500">{createFieldError("project")}</p>{/if}
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Property <span class="text-neutral-400 font-normal">(optional)</span></span>
        <select
          bind:value={createForm.property}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        >
          <option value="">None</option>
          {#each properties as property}
            <option value={String(property.id)}>{property.name}</option>
          {/each}
        </select>
        {#if createFieldError("property")}<p class="mt-1 text-xs text-red-500">{createFieldError("property")}</p>{/if}
      </label>
    </div>

    <!-- Justification — full width -->
    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Justification <span class="text-neutral-400 font-normal">(optional)</span></span>
      <textarea
        bind:value={createForm.justification}
        rows="2"
        placeholder="Business justification for this purchase..."
        class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent resize-none"
      ></textarea>
      {#if createFieldError("justification")}<p class="mt-1 text-xs text-red-500">{createFieldError("justification")}</p>{/if}
    </label>

    <!-- Notes — full width -->
    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Notes <span class="text-neutral-400 font-normal">(optional)</span></span>
      <textarea
        bind:value={createForm.notes}
        rows="2"
        placeholder="Additional notes..."
        class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent resize-none"
      ></textarea>
      {#if createFieldError("notes")}<p class="mt-1 text-xs text-red-500">{createFieldError("notes")}</p>{/if}
    </label>

    <!-- Actions -->
    <div class="flex justify-end gap-3 pt-2">
      <button
        type="button"
        onclick={() => { showCreateModal = false; resetCreateForm(); }}
        class="px-4 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors"
      >
        Cancel
      </button>
      {#if isDev}
        <button
          type="button"
          onclick={devFillRequisition}
          class="px-4 py-2.5 bg-orange-500 rounded-lg text-sm font-medium text-white hover:bg-orange-600 transition-colors"
        >
          Dev Fill
        </button>
      {/if}
      <button
        type="submit"
        disabled={savingRequisition}
        class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
      >
        {savingRequisition ? "Creating..." : "Create Requisition"}
      </button>
    </div>
  </form>
</Modal>

<!-- Detail Drawer -->
<DrawerShell open={showDetail} onclose={closeDetail} title={pr?.pr_number ?? "Requisition"} subtitle={pr?.title ?? ""} width="max-w-2xl" model="PurchaseRequisition" recordId={pr?.id ?? null}>
  {#snippet badges()}
    {#if pr}
      <StatusBadge status={pr.status} />
      <StatusBadge status={pr.priority} />
      {#if workflow}<StatusBadge status={workflow.state} />{/if}
    {/if}
  {/snippet}
  {#if detailLoading}
    <div class="flex items-center justify-center py-24">
      <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
    </div>
  {:else if pr}
    <!-- Summary strip -->
    <div class="px-6 py-4 border-b border-neutral-100 bg-neutral-50/50">
      <div class="grid grid-cols-3 gap-4 text-sm">
        <div>
          <p class="text-neutral-400 text-xs">Estimated Total</p>
          <p class="font-semibold text-neutral-900 tabular-nums">{formatCurrencyFull(pr.estimated_total)}</p>
        </div>
        <div>
          <p class="text-neutral-400 text-xs">Items</p>
          <p class="font-semibold text-neutral-900">{pr.item_count}</p>
        </div>
        <div>
          <p class="text-neutral-400 text-xs">Required By</p>
          <p class="font-semibold text-neutral-900">{pr.required_date ? formatDate(pr.required_date) : "\u2014"}</p>
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div class="px-6 py-3 border-b border-neutral-100 flex gap-2 flex-wrap">
      {#if pr.status === "draft"}
        <button onclick={submitForApproval} disabled={detailSaving}
          class="px-3 py-1.5 bg-neutral-900 text-white rounded-lg text-xs font-medium hover:bg-neutral-800 disabled:opacity-50">
          {detailSaving ? "Submitting..." : "Submit for Approval"}
        </button>
        {#if !workflow}
          <button onclick={submitWorkflowApproval} disabled={submittingWorkflow}
            class="px-3 py-1.5 border border-neutral-200 text-neutral-700 rounded-lg text-xs font-medium hover:bg-neutral-50 disabled:opacity-50">
            {submittingWorkflow ? "Submitting..." : "Submit via Workflow"}
          </button>
        {/if}
      {/if}
      {#if pr.status === "submitted"}
        <button onclick={approveRequisition} disabled={detailSaving}
          class="px-3 py-1.5 bg-emerald-600 text-white rounded-lg text-xs font-medium hover:bg-emerald-700 disabled:opacity-50">
          {detailSaving ? "Approving..." : "Approve"}
        </button>
        <button onclick={rejectRequisition} disabled={detailSaving}
          class="px-3 py-1.5 border border-red-200 text-red-600 rounded-lg text-xs font-medium hover:bg-red-50 disabled:opacity-50">
          {detailSaving ? "Rejecting..." : "Reject"}
        </button>
      {/if}
      {#if isEditable}
        <button onclick={deleteRequisition} disabled={detailDeleting}
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
      <button onclick={() => detailTab = "items"}
        class="pb-3 text-sm font-medium border-b-2 transition-colors {detailTab === 'items' ? 'border-neutral-900 text-neutral-900' : 'border-transparent text-neutral-400 hover:text-neutral-600'}">
        Items ({pr.items?.length ?? 0})
      </button>
    </div>

    {#if detailTab === "details"}
      {#if detailEditing}
        <!-- ── Edit Mode ── -->
        <div class="p-6 space-y-4">
          <label class="block">
            <span class="block text-xs font-medium text-neutral-500 mb-1">Title</span>
            <input bind:value={detailForm.title}
              class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
            {#if detailFieldError("title")}<p class="mt-1 text-xs text-red-500">{detailFieldError("title")}</p>{/if}
          </label>

          <div class="grid grid-cols-2 gap-3">
            <label class="block">
              <span class="block text-xs font-medium text-neutral-500 mb-1">Requester</span>
              <input bind:value={detailForm.requester}
                class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
              {#if detailFieldError("requester")}<p class="mt-1 text-xs text-red-500">{detailFieldError("requester")}</p>{/if}
            </label>
            <label class="block">
              <span class="block text-xs font-medium text-neutral-500 mb-1">Priority</span>
              <select bind:value={detailForm.priority}
                class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent">
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </label>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <label class="block">
              <span class="block text-xs font-medium text-neutral-500 mb-1">Required Date</span>
              <DateInput bind:value={detailForm.required_date} />
            </label>
            <label class="block">
              <span class="block text-xs font-medium text-neutral-500 mb-1">Budget Line</span>
              <select bind:value={detailForm.budget_line_item}
                class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent">
                <option value="">None</option>
                {#each budgetLines as line}<option value={String(line.id)}>{line.label}</option>{/each}
              </select>
            </label>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <label class="block">
              <span class="block text-xs font-medium text-neutral-500 mb-1">Project</span>
              <select bind:value={detailForm.project}
                class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent">
                <option value="">None</option>
                {#each projects as project}<option value={String(project.id)}>{project.name}</option>{/each}
              </select>
            </label>
            <label class="block">
              <span class="block text-xs font-medium text-neutral-500 mb-1">Property</span>
              <select bind:value={detailForm.property}
                class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent">
                <option value="">None</option>
                {#each properties as property}<option value={String(property.id)}>{property.name}</option>{/each}
              </select>
            </label>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <label class="block">
              <span class="block text-xs font-medium text-neutral-500 mb-1">Budget Code</span>
              <input bind:value={detailForm.budget_code} placeholder="e.g. DEPT-2024-001"
                class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
            </label>
            <label class="block">
              <span class="block text-xs font-medium text-neutral-500 mb-1">Cost Code</span>
              <select bind:value={detailForm.cost_code}
                class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent">
                <option value="">None</option>
                {#each costCodes as code}<option value={code.code}>{code.code} - {code.label}</option>{/each}
              </select>
            </label>
          </div>

          <label class="block">
            <span class="block text-xs font-medium text-neutral-500 mb-1">Justification</span>
            <textarea bind:value={detailForm.justification} rows="2" placeholder="Business justification..."
              class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"></textarea>
          </label>

          <label class="block">
            <span class="block text-xs font-medium text-neutral-500 mb-1">Notes</span>
            <textarea bind:value={detailForm.notes} rows="2" placeholder="Additional notes..."
              class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"></textarea>
          </label>
        </div>

        <!-- Save footer -->
        <div class="sticky bottom-0 bg-white border-t border-neutral-100 px-6 py-4 flex gap-3">
          <div class="flex-1"></div>
          <button onclick={() => { detailEditing = false; detailErrors = {}; }}
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
              <p class="text-sm text-neutral-900">{pr.title || "\u2014"}</p>
            </div>
            <div>
              <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-1">Requester</p>
              <p class="text-sm text-neutral-900">{pr.requester || "\u2014"}</p>
            </div>
            <div>
              <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-1">Priority</p>
              <StatusBadge status={pr.priority} />
            </div>
            <div>
              <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-1">Status</p>
              <StatusBadge status={pr.status} />
            </div>
            <div>
              <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-1">Required Date</p>
              <p class="text-sm text-neutral-900">{pr.required_date ? formatDate(pr.required_date) : "\u2014"}</p>
            </div>
            <div>
              <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-1">Project</p>
              <p class="text-sm text-neutral-900">{pr.project_name || "\u2014"}</p>
            </div>
            <div>
              <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-1">Property</p>
              <p class="text-sm text-neutral-900">{pr.property_name || "\u2014"}</p>
            </div>
            <div>
              <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-1">Budget Code</p>
              <p class="text-sm text-neutral-900">{pr.budget_code || "\u2014"}</p>
            </div>
            <div>
              <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-1">Cost Code</p>
              <p class="text-sm text-neutral-900">{pr.cost_code || "\u2014"}</p>
            </div>
          </div>

          {#if pr.justification}
            <div class="border-t border-neutral-100 pt-4">
              <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-1">Justification</p>
              <p class="text-sm text-neutral-700 whitespace-pre-line">{pr.justification}</p>
            </div>
          {/if}

          {#if pr.notes}
            <div class="border-t border-neutral-100 pt-4">
              <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-1">Notes</p>
              <p class="text-sm text-neutral-700 whitespace-pre-line">{pr.notes}</p>
            </div>
          {/if}

          {#if pr.approved_by || pr.rejected_reason}
            <div class="border-t border-neutral-100 pt-4 space-y-3">
              <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest">Approval Details</p>
              <div class="grid grid-cols-2 gap-x-6 gap-y-3">
                {#if pr.approved_by}
                  <div>
                    <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-1">Approved By</p>
                    <p class="text-sm text-neutral-900">{pr.approved_by}</p>
                  </div>
                {/if}
                {#if pr.approved_date}
                  <div>
                    <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-1">Approved Date</p>
                    <p class="text-sm text-neutral-900">{formatDate(pr.approved_date)}</p>
                  </div>
                {/if}
              </div>
              {#if pr.rejected_reason}
                <div>
                  <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest mb-1">Rejection Reason</p>
                  <p class="text-sm text-neutral-700 whitespace-pre-line">{pr.rejected_reason}</p>
                </div>
              {/if}
            </div>
          {/if}
        </div>
      {/if}
    {:else}
      <!-- Items tab -->
      <div class="p-6">
        {#if pr.items && pr.items.length > 0}
          <div class="rounded-xl border border-neutral-200 overflow-hidden mb-4">
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b border-neutral-200 bg-neutral-50">
                  <th class="px-4 py-2.5 text-left text-xs font-medium text-neutral-400 uppercase">Description</th>
                  <th class="px-4 py-2.5 text-right text-xs font-medium text-neutral-400 uppercase">Qty</th>
                  <th class="px-4 py-2.5 text-left text-xs font-medium text-neutral-400 uppercase">UOM</th>
                  <th class="px-4 py-2.5 text-right text-xs font-medium text-neutral-400 uppercase">Unit Price</th>
                  <th class="px-4 py-2.5 text-right text-xs font-medium text-neutral-400 uppercase">Amount</th>
                  {#if isEditable}<th class="px-4 py-2.5 w-10"></th>{/if}
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100">
                {#each pr.items as item}
                  <tr class="hover:bg-neutral-50">
                    <td class="px-4 py-3 text-neutral-900">{item.description}</td>
                    <td class="px-4 py-3 text-right text-neutral-500 tabular-nums">{item.quantity}</td>
                    <td class="px-4 py-3 text-neutral-500">{item.unit_of_measure || "\u2014"}</td>
                    <td class="px-4 py-3 text-right text-neutral-500 tabular-nums">{formatCurrencyFull(item.estimated_unit_price)}</td>
                    <td class="px-4 py-3 text-right text-neutral-900 tabular-nums font-medium">{formatCurrencyFull(item.estimated_amount)}</td>
                    {#if isEditable}
                      <td class="px-4 py-3 text-right">
                        <button onclick={() => removeItem(item.id)} class="text-xs text-neutral-400 hover:text-red-600" aria-label="Delete item">
                          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" /></svg>
                        </button>
                      </td>
                    {/if}
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {:else}
          <div class="text-center py-8">
            <p class="text-sm text-neutral-400">{isEditable ? "No items yet. Add your first item below." : "No items on this requisition."}</p>
          </div>
        {/if}

        {#if isEditable}
          <!-- Add item form -->
          <div class="rounded-xl border border-neutral-200 p-4 space-y-3">
            <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest">Add Item</p>
            <label class="block">
              <span class="block text-xs font-medium text-neutral-500 mb-1">Description</span>
              <input bind:value={itemForm.description} placeholder="Item description"
                class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
            </label>
            <div class="grid grid-cols-3 gap-3">
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Quantity</span>
                <input bind:value={itemForm.quantity} placeholder="1"
                  class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
              </label>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">UOM</span>
                <input bind:value={itemForm.unit_of_measure} placeholder="e.g. each"
                  class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
              </label>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Unit Price</span>
                <input bind:value={itemForm.estimated_unit_price} placeholder="0.00"
                  class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent" />
              </label>
            </div>
            <button onclick={addItem} disabled={addingItem}
              class="w-full px-4 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50">
              {addingItem ? "Adding..." : "Add Item"}
            </button>
          </div>
        {/if}
      </div>
    {/if}
  {/if}
</DrawerShell>

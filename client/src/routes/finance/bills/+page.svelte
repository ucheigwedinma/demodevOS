<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { useAutoRefresh } from "$lib/realtime.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import Modal from "$lib/components/Modal.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import ApprovalTimeline from "$lib/components/workflows/ApprovalTimeline.svelte";
  import DecisionPanel from "$lib/components/workflows/DecisionPanel.svelte";
  import type { Bill, BillListItem, VendorListItem, PropertyListItem, PaginatedResponse, WorkflowInstanceDetail } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let data = $state<BillListItem[]>([]);
  let totalCount = $state(0);
  let currentPage = $state(1);
  let searchQuery = $state("");
  let statusFilter = $state("");
  let vendorFilter = $state("");
  let loading = $state(true);
  let vendors = $state<VendorListItem[]>([]);
  let properties = $state<PropertyListItem[]>([]);

  let showCreateModal = $state(false);
  let createForm = $state({
    bill_number: "",
    vendor: "",
    property: "",
    issue_date: "",
    due_date: "",
    notes: "",
  });
  let createErrors = $state<Record<string, string[]>>({});
  let savingBill = $state(false);

  function createFieldError(field: string): string {
    return createErrors[field]?.[0] ?? "";
  }

  function resetCreateForm() {
    createForm = {
      bill_number: "",
      vendor: "",
      property: "",
      issue_date: "",
      due_date: "",
      notes: "",
    };
    createErrors = {};
  }

  async function handleCreateBill(e: Event) {
    e.preventDefault();
    createErrors = {};
    savingBill = true;

    try {
      const payload: Record<string, unknown> = {
        vendor: createForm.vendor ? Number(createForm.vendor) : null,
        property: createForm.property ? Number(createForm.property) : null,
        issue_date: createForm.issue_date || null,
        due_date: createForm.due_date || null,
        notes: createForm.notes,
      };
      if (createForm.bill_number.trim()) {
        payload.bill_number = createForm.bill_number.trim();
      }
      const result = await api.post<Bill>("/finance/bills/", payload);
      toast.success("Bill created", `"${result.bill_number}" has been added`);
      showCreateModal = false;
      resetCreateForm();
      fetchBills();
    } catch (err) {
      if (err instanceof ApiError) {
        createErrors = err.fieldErrors;
        toast.error("Validation error", "Please fix the highlighted fields below");
      } else {
        toast.error("Something went wrong", "Could not create the bill");
      }
    }
    savingBill = false;
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

  async function fetchVendors() {
    try {
      const res = await api.get<PaginatedResponse<VendorListItem>>("/procurement/vendors/", { page_size: "200" });
      vendors = res.results;
    } catch {
      vendors = [];
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

  async function fetchBills() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage) };
      if (searchQuery) params.search = searchQuery;
      if (statusFilter) params.status = statusFilter;
      if (vendorFilter) params.vendor = vendorFilter;

      const res = await api.get<PaginatedResponse<BillListItem>>("/finance/bills/", params);
      data = res.results;
      totalCount = res.count;
    } catch {
      data = [];
      totalCount = 0;
    }
    loading = false;
  }

  // ── Dev fill ──
  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  const BILL_SAMPLES = [
    {
      bill_number: "BILL-2025-0042",
      notes: "Cement and rebar delivery for Phase 3 foundation works",
      issue_offset: -3,
      due_offset: 27,
    },
    {
      bill_number: "BILL-2025-0043",
      notes: "Electrical wiring and panel installation — Block A",
      issue_offset: -7,
      due_offset: 23,
    },
    {
      bill_number: "BILL-2025-0044",
      notes: "Plumbing fixtures and fittings — Units 12–24",
      issue_offset: -1,
      due_offset: 29,
    },
    {
      bill_number: "BILL-2025-0045",
      notes: "Site security services — March 2025",
      issue_offset: -14,
      due_offset: 16,
    },
  ];

  let billDevIdx = $state(0);

  function devFillBill() {
    const sample = BILL_SAMPLES[billDevIdx % BILL_SAMPLES.length];
    billDevIdx++;

    const today = new Date();
    const issueDate = new Date(today);
    issueDate.setDate(issueDate.getDate() + sample.issue_offset);
    const dueDate = new Date(today);
    dueDate.setDate(dueDate.getDate() + sample.due_offset);

    createForm.bill_number = sample.bill_number;
    createForm.vendor = vendors.length > 0 ? String(vendors[billDevIdx % vendors.length].id) : "";
    createForm.property = properties.length > 0 ? String(properties[billDevIdx % properties.length].id) : "";
    createForm.issue_date = issueDate.toISOString().slice(0, 10);
    createForm.due_date = dueDate.toISOString().slice(0, 10);
    createForm.notes = sample.notes;
  }

  $effect(() => {
    fetchVendors();
    fetchProperties();
  });

  $effect(() => {
    void searchQuery;
    void statusFilter;
    void vendorFilter;
    void currentPage;
    fetchBills();
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
    return currency.format(value);
  }

  function formatDate(value: string | null): string {
    if (!value) return "\u2014";
    return new Date(value).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  }

  // ── Detail drawer ──
  let drawerOpen = $state(false);
  let drawerBill = $state<Bill | null>(null);
  let drawerLoading = $state(false);
  let saving = $state(false);
  let deleting = $state(false);
  let errors = $state<Record<string, string[]>>({});

  // Editable form
  let form = $state({
    bill_number: "", vendor: "", property: "",
    issue_date: "", due_date: "", status: "draft",
    tax_amount: "", notes: "",
  });

  // Workflow
  let workflow = $state<WorkflowInstanceDetail | null>(null);
  let submittingApproval = $state(false);

  // Line items
  let lineForm = $state({ description: "", quantity: "", unit_price: "" });
  let addingLine = $state(false);

  // Payments
  let paymentForm = $state({ amount: "", payment_date: "", payment_method: "bank_transfer", reference_number: "", notes: "" });
  let recordingPayment = $state(false);

  const paymentMethodLabels: Record<string, string> = {
    bank_transfer: "Bank Transfer", check: "Check", cash: "Cash",
    credit_card: "Credit Card", other: "Other",
  };

  function fieldError(field: string): string {
    return errors[field]?.[0] ?? "";
  }

  async function openDrawer(id: number) {
    drawerOpen = true;
    drawerLoading = true;
    drawerBill = null;
    workflow = null;
    try {
      drawerBill = await api.get<Bill>(`/finance/bills/${id}/`);
      form = {
        bill_number: drawerBill.bill_number,
        vendor: String(drawerBill.vendor),
        property: drawerBill.property ? String(drawerBill.property) : "",
        issue_date: drawerBill.issue_date,
        due_date: drawerBill.due_date,
        status: drawerBill.status,
        tax_amount: drawerBill.tax_amount,
        notes: drawerBill.notes,
      };
      errors = {};
      // Load workflow
      try {
        const res = await api.get<{ results: WorkflowInstanceDetail[] }>("/workflows/instances/", { model: "finance.bill", object_id: String(id) });
        workflow = res.results.length > 0 ? res.results[0] : null;
      } catch { workflow = null; }
    } catch {
      toast.error("Not found", "Bill could not be loaded");
      drawerOpen = false;
    }
    drawerLoading = false;
  }

  function closeDrawer() {
    drawerOpen = false;
    drawerBill = null;
    workflow = null;
  }

  async function reloadDrawerBill() {
    if (!drawerBill) return;
    drawerBill = await api.get<Bill>(`/finance/bills/${drawerBill.id}/`);
    form.status = drawerBill.status;
    fetchBills();
  }

  async function loadDrawerWorkflow() {
    if (!drawerBill) return;
    try {
      const res = await api.get<{ results: WorkflowInstanceDetail[] }>("/workflows/instances/", { model: "finance.bill", object_id: String(drawerBill.id) });
      workflow = res.results.length > 0 ? res.results[0] : null;
    } catch { workflow = null; }
  }

  async function handleSave(e: Event) {
    e.preventDefault();
    if (!drawerBill) return;
    errors = {};
    saving = true;
    try {
      drawerBill = await api.patch<Bill>(`/finance/bills/${drawerBill.id}/`, {
        bill_number: form.bill_number,
        vendor: form.vendor ? Number(form.vendor) : null,
        property: form.property ? Number(form.property) : null,
        issue_date: form.issue_date || null,
        due_date: form.due_date || null,
        status: form.status,
        tax_amount: form.tax_amount || "0.00",
        notes: form.notes,
      });
      toast.success("Bill updated", "Changes have been saved");
      fetchBills();
    } catch (err) {
      if (err instanceof ApiError) {
        errors = err.fieldErrors;
        toast.error("Validation error", "Please fix the highlighted fields");
      } else {
        toast.error("Something went wrong", "Could not update the bill");
      }
    }
    saving = false;
  }

  async function handleDelete() {
    if (!drawerBill || !confirm("Are you sure you want to delete this bill?")) return;
    deleting = true;
    try {
      await api.delete(`/finance/bills/${drawerBill.id}/`);
      toast.success("Bill deleted", "The bill has been removed");
      closeDrawer();
      fetchBills();
    } catch {
      toast.error("Something went wrong", "Could not delete the bill");
    }
    deleting = false;
  }

  async function submitForApproval() {
    if (!drawerBill) return;
    submittingApproval = true;
    try {
      await api.post(`/finance/bills/${drawerBill.id}/submit-approval/`, {});
      toast.success("Submitted", "Bill has been submitted for approval.");
      await Promise.all([reloadDrawerBill(), loadDrawerWorkflow()]);
    } catch {
      toast.error("Error", "Could not submit for approval.");
    }
    submittingApproval = false;
  }

  async function addLineItem() {
    if (!drawerBill || !lineForm.description || !lineForm.quantity || !lineForm.unit_price) return;
    addingLine = true;
    try {
      await api.post(`/finance/bills/${drawerBill.id}/line-items/`, {
        description: lineForm.description, quantity: lineForm.quantity, unit_price: lineForm.unit_price,
      });
      lineForm = { description: "", quantity: "", unit_price: "" };
      toast.success("Line item added", "");
      await reloadDrawerBill();
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error("Validation error", Object.values(err.fieldErrors).flat()[0] || "Could not add line item");
      } else {
        toast.error("Something went wrong", "Could not add line item");
      }
    }
    addingLine = false;
  }

  async function removeLineItem(itemId: number) {
    if (!drawerBill || !confirm("Remove this line item?")) return;
    try {
      await api.delete(`/finance/bills/${drawerBill.id}/line-items/${itemId}/`);
      toast.success("Line item removed", "");
      await reloadDrawerBill();
    } catch {
      toast.error("Something went wrong", "Could not remove line item");
    }
  }

  async function recordPayment() {
    if (!drawerBill || !paymentForm.amount || !paymentForm.payment_date) return;
    recordingPayment = true;
    try {
      await api.post(`/finance/bills/${drawerBill.id}/payments/`, {
        amount: paymentForm.amount, payment_date: paymentForm.payment_date,
        payment_method: paymentForm.payment_method,
        reference_number: paymentForm.reference_number, notes: paymentForm.notes,
      });
      paymentForm = { amount: "", payment_date: "", payment_method: "bank_transfer", reference_number: "", notes: "" };
      toast.success("Payment recorded", "");
      await reloadDrawerBill();
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error("Validation error", Object.values(err.fieldErrors).flat()[0] || "Could not record payment");
      } else {
        toast.error("Something went wrong", "Could not record payment");
      }
    }
    recordingPayment = false;
  }

  async function removePayment(paymentId: number) {
    if (!drawerBill || !confirm("Remove this payment?")) return;
    try {
      await api.delete(`/finance/bills/${drawerBill.id}/payments/${paymentId}/`);
      toast.success("Payment removed", "");
      await reloadDrawerBill();
    } catch {
      toast.error("Something went wrong", "Could not remove payment");
    }
  }

  useAutoRefresh("Bill", fetchBills);
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-green-600">Accounts Payable</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Bills</h1>
      <p class="text-sm text-neutral-400 mt-1">Track and organize all project bills in one accurate, auditable space</p>
    </div>
    <button
      onclick={() => showCreateModal = true}
      class="px-4 py-2.5 bg-neutral-800 text-white rounded-lg hover:bg-neutral-800 text-sm font-medium transition-colors"
    >
      + New Bill
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
        placeholder="Search bills..."
        oninput={onSearchInput}
        class="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
               focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent
               placeholder:text-neutral-400"
      />
    </div>
    <select
      bind:value={statusFilter}
      onchange={() => (currentPage = 1)}
      class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600
             focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
    >
      <option value="">All Statuses</option>
      <option value="draft">Draft</option>
      <option value="approved">Approved</option>
      <option value="paid">Paid</option>
      <option value="cancelled">Cancelled</option>
    </select>
    <select
      bind:value={vendorFilter}
      onchange={() => (currentPage = 1)}
      class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600
             focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
    >
      <option value="">All Vendors</option>
      {#each vendors as vendor}
        <option value={String(vendor.id)}>{vendor.name}</option>
      {/each}
    </select>
  </div>

  <!-- Table -->
  <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
    {#if loading}
      <div class="p-16 text-center">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
        <p class="mt-3 text-sm text-neutral-400">Loading bills...</p>
      </div>
    {:else if data.length === 0}
      <div class="p-16 text-center">
        <svg class="w-12 h-12 mx-auto text-neutral-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
        </svg>
        <p class="mt-4 text-sm font-medium text-neutral-800">No bills found</p>
        <p class="mt-1 text-sm text-neutral-400">Get started by creating your first bill.</p>
        <button
          onclick={() => showCreateModal = true}
          class="inline-block mt-4 px-4 py-2 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors"
        >
          + New Bill
        </button>
      </div>
    {:else}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200">
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Bill #</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Vendor</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Issue Date</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Due Date</th>
            <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Total</th>
            <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Paid</th>
            <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Balance</th>
            <th class="px-5 py-3.5 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Overdue</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each data as bill}
            <tr
              class="hover:bg-neutral-50 cursor-pointer transition-colors"
              onclick={() => openDrawer(bill.id)}
            >
              <td class="px-5 py-4">
                <span class="font-medium text-neutral-800">{bill.bill_number}</span>
              </td>
              <td class="px-5 py-4 text-neutral-500">{bill.vendor_name}</td>
              <td class="px-5 py-4">
                <StatusBadge status={bill.status} />
              </td>
              <td class="px-5 py-4 text-neutral-500">{formatDate(bill.issue_date)}</td>
              <td class="px-5 py-4 text-neutral-500">{formatDate(bill.due_date)}</td>
              <td class="px-5 py-4 text-right text-neutral-800 tabular-nums">{formatCurrency(bill.total_amount)}</td>
              <td class="px-5 py-4 text-right text-neutral-500 tabular-nums">{formatCurrency(bill.paid_amount)}</td>
              <td class="px-5 py-4 text-right text-neutral-800 tabular-nums font-medium">{formatCurrency(bill.balance_due)}</td>
              <td class="px-5 py-4 text-center">
                {#if bill.is_overdue}
                  <span class="inline-block w-2.5 h-2.5 rounded-full bg-red-500" title="{bill.days_overdue} days overdue"></span>
                {/if}
              </td>
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
        {totalCount === 1 ? "bill" : "bills"}
        {#if totalPages > 1}
          <span class="mx-1.5 text-neutral-300">·</span> Page <span class="font-medium text-neutral-600">{currentPage}</span> of <span class="font-medium text-neutral-600">{totalPages}</span>
        {/if}
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
                         ? 'bg-neutral-800 text-white'
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

<Modal open={showCreateModal} onclose={() => { showCreateModal = false; resetCreateForm(); }} title="New Bill" maxWidth="max-w-xl">
  <form onsubmit={handleCreateBill} class="space-y-5">
    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Bill Number <span class="text-neutral-400 font-normal">(auto-generated if blank)</span></span>
      <input
        type="text"
        bind:value={createForm.bill_number}
        placeholder="Auto-generated"
        class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
      />
      {#if createFieldError("bill_number")}<p class="mt-1 text-xs text-red-500">{createFieldError("bill_number")}</p>{/if}
    </label>

    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Vendor</span>
      <select
        bind:value={createForm.vendor}
        class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
      >
        <option value="">Select a vendor</option>
        {#each vendors as vendor}
          <option value={String(vendor.id)}>{vendor.name}</option>
        {/each}
      </select>
      {#if createFieldError("vendor")}<p class="mt-1 text-xs text-red-500">{createFieldError("vendor")}</p>{/if}
    </label>

    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Property <span class="text-neutral-400 font-normal">(optional)</span></span>
      <select
        bind:value={createForm.property}
        class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
      >
        <option value="">None</option>
        {#each properties as property}
          <option value={String(property.id)}>{property.name}</option>
        {/each}
      </select>
      {#if createFieldError("property")}<p class="mt-1 text-xs text-red-500">{createFieldError("property")}</p>{/if}
    </label>

    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Issue Date</span>
      <DateInput bind:value={createForm.issue_date} />
      {#if createFieldError("issue_date")}<p class="mt-1 text-xs text-red-500">{createFieldError("issue_date")}</p>{/if}
    </label>

    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Due Date</span>
      <DateInput bind:value={createForm.due_date} />
      {#if createFieldError("due_date")}<p class="mt-1 text-xs text-red-500">{createFieldError("due_date")}</p>{/if}
    </label>

    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Notes</span>
      <textarea
        bind:value={createForm.notes}
        rows="3"
        class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
      ></textarea>
      {#if createFieldError("notes")}<p class="mt-1 text-xs text-red-500">{createFieldError("notes")}</p>{/if}
    </label>

    <div class="flex justify-end gap-3 pt-2">
      {#if isDev}
        <button
          type="button"
          onclick={devFillBill}
          class="mr-auto rounded-lg bg-orange-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-orange-600 transition-colors"
        >
          Dev Fill
        </button>
      {/if}
      <button
        type="button"
        onclick={() => { showCreateModal = false; resetCreateForm(); }}
        class="px-4 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors"
      >
        Cancel
      </button>
      <button
        type="submit"
        disabled={savingBill}
        class="px-4 py-2.5 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
      >
        {savingBill ? "Creating..." : "Create Bill"}
      </button>
    </div>
  </form>
</Modal>

<!-- Bill Detail Drawer -->
{#if drawerOpen}
  <div
    class="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm transition-opacity"
    onclick={closeDrawer}
    onkeydown={(e) => e.key === "Escape" && closeDrawer()}
    role="button"
    tabindex="-1"
  ></div>

  <div class="fixed inset-y-0 right-0 z-50 w-full max-w-2xl bg-white shadow-2xl border-l border-neutral-200 flex flex-col drawer-slide-in">
    {#if drawerLoading}
      <div class="flex-1 flex items-center justify-center">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
        <span class="ml-3 text-sm text-neutral-400">Loading bill...</span>
      </div>
    {:else if drawerBill}
      {@const b = drawerBill}

      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200">
        <div class="flex items-center gap-3">
          <h2 class="text-lg font-bold text-neutral-800">{b.bill_number}</h2>
          <StatusBadge status={b.status} size="md" />
          {#if workflow}
            <StatusBadge status={workflow.state} size="md" />
          {/if}
        </div>
        <button
          onclick={closeDrawer}
          class="w-8 h-8 flex items-center justify-center rounded-lg text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 transition-colors"
          aria-label="Close"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Body -->
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-6">
        <!-- Summary card -->
        <div class="rounded-xl bg-pink-50 border border-pink-100 p-5">
          <div class="grid grid-cols-4 gap-4 text-center">
            <div>
              <p class="text-xs font-medium text-pink-400 uppercase tracking-wider mb-1">Subtotal</p>
              <p class="text-sm font-semibold text-pink-900 tabular-nums">{formatCurrency(b.subtotal)}</p>
            </div>
            <div>
              <p class="text-xs font-medium text-pink-400 uppercase tracking-wider mb-1">Tax</p>
              <p class="text-sm font-semibold text-pink-900 tabular-nums">{formatCurrency(b.tax_amount)}</p>
            </div>
            <div>
              <p class="text-xs font-medium text-pink-400 uppercase tracking-wider mb-1">Paid</p>
              <p class="text-sm font-semibold text-emerald-700 tabular-nums">{formatCurrency(b.paid_amount)}</p>
            </div>
            <div>
              <p class="text-xs font-medium text-pink-400 uppercase tracking-wider mb-1">Balance</p>
              <p class="text-lg font-bold tabular-nums {Number(b.balance_due) > 0 ? 'text-red-600' : 'text-pink-900'}">{formatCurrency(b.balance_due)}</p>
            </div>
          </div>
        </div>

        <!-- Bill Details (editable form) -->
        <form onsubmit={handleSave} class="space-y-4">
          <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider">Bill Details</h3>

          <div class="grid grid-cols-2 gap-3">
            <label>
              <span class="block text-sm font-medium text-neutral-700 mb-1">Bill Number</span>
              <input bind:value={form.bill_number} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />
              {#if fieldError("bill_number")}<p class="mt-1 text-xs text-red-500">{fieldError("bill_number")}</p>{/if}
            </label>
            <label>
              <span class="block text-sm font-medium text-neutral-700 mb-1">Status</span>
              <select bind:value={form.status} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent">
                <option value="draft">Draft</option>
                <option value="approved">Approved</option>
                <option value="paid">Paid</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </label>
          </div>

          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1">Vendor</span>
            <select bind:value={form.vendor} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent">
              <option value="">Select a vendor</option>
              {#each vendors as vendor}
                <option value={String(vendor.id)}>{vendor.name}</option>
              {/each}
            </select>
          </label>

          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1">Property <span class="text-neutral-400 font-normal">(optional)</span></span>
            <select bind:value={form.property} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent">
              <option value="">None</option>
              {#each properties as property}
                <option value={String(property.id)}>{property.name}</option>
              {/each}
            </select>
          </label>

          <div class="grid grid-cols-2 gap-3">
            <label>
              <span class="block text-sm font-medium text-neutral-700 mb-1">Issue Date</span>
              <DateInput bind:value={form.issue_date} />
            </label>
            <label>
              <span class="block text-sm font-medium text-neutral-700 mb-1">Due Date</span>
              <DateInput bind:value={form.due_date} />
            </label>
          </div>

          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1">Tax Amount</span>
            <input bind:value={form.tax_amount} placeholder="0.00" class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />
          </label>

          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1">Notes</span>
            <textarea bind:value={form.notes} rows={2} placeholder="Optional notes..." class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"></textarea>
          </label>

          <div class="flex items-center justify-between">
            <button type="submit" disabled={saving} class="px-5 py-2 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">
              {saving ? "Saving..." : "Save Changes"}
            </button>
            <button type="button" onclick={handleDelete} disabled={deleting} class="px-4 py-2 border border-red-200 text-red-600 rounded-lg text-sm font-medium hover:bg-red-50 disabled:opacity-50 transition-colors">
              {deleting ? "Deleting..." : "Delete Bill"}
            </button>
          </div>
        </form>

        <!-- Approval -->
        {#if workflow}
          <div class="space-y-3">
            <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider">Approval</h3>
            <DecisionPanel instance={workflow} onDecision={loadDrawerWorkflow} />
            {#if workflow.steps.length > 0}
              <div class="bg-white rounded-xl border border-neutral-200 p-4">
                <ApprovalTimeline steps={workflow.steps} />
              </div>
            {/if}
          </div>
        {:else if b.status === "draft"}
          <div>
            <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-3">Approval</h3>
            <p class="text-xs text-neutral-400 mb-3">Submit this bill for workflow-based approval routing.</p>
            <button type="button" onclick={submitForApproval} disabled={submittingApproval} class="w-full px-4 py-2.5 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">
              {submittingApproval ? "Submitting..." : "Submit for Approval"}
            </button>
          </div>
        {/if}

        <!-- Line Items -->
        <div>
          <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-3">Line Items</h3>
          <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
            {#if b.line_items.length > 0}
              <table class="w-full text-sm">
                <thead>
                  <tr class="border-b border-neutral-200">
                    <th class="px-4 py-2.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Description</th>
                    <th class="px-4 py-2.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Qty</th>
                    <th class="px-4 py-2.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Price</th>
                    <th class="px-4 py-2.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Amount</th>
                    <th class="px-4 py-2.5 w-12"></th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-neutral-100">
                  {#each b.line_items as item}
                    <tr class="hover:bg-neutral-50 transition-colors">
                      <td class="px-4 py-3 text-neutral-800">{item.description}</td>
                      <td class="px-4 py-3 text-right text-neutral-500 tabular-nums">{item.quantity}</td>
                      <td class="px-4 py-3 text-right text-neutral-500 tabular-nums">{formatCurrency(item.unit_price)}</td>
                      <td class="px-4 py-3 text-right text-neutral-800 tabular-nums font-medium">{formatCurrency(item.amount)}</td>
                      <td class="px-4 py-3 text-right">
                        <button onclick={() => removeLineItem(item.id)} class="text-xs text-neutral-400 hover:text-red-600 transition-colors">Del</button>
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            {:else}
              <div class="p-6 text-center">
                <p class="text-sm text-neutral-400">No line items yet.</p>
              </div>
            {/if}

            <!-- Add line item -->
            <div class="border-t border-neutral-200 px-4 py-3">
              <div class="flex items-end gap-2">
                <label class="flex-1">
                  <span class="block text-xs font-medium text-neutral-500 mb-1">Description</span>
                  <input bind:value={lineForm.description} placeholder="Item description" class="w-full px-2.5 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />
                </label>
                <label class="w-16">
                  <span class="block text-xs font-medium text-neutral-500 mb-1">Qty</span>
                  <input bind:value={lineForm.quantity} placeholder="1" class="w-full px-2.5 py-2 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />
                </label>
                <label class="w-24">
                  <span class="block text-xs font-medium text-neutral-500 mb-1">Price</span>
                  <input bind:value={lineForm.unit_price} placeholder="0.00" class="w-full px-2.5 py-2 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />
                </label>
                <button type="button" onclick={addLineItem} disabled={addingLine} class="px-3 py-2 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">
                  {addingLine ? "..." : "Add"}
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Payments -->
        <div>
          <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-3">Payments</h3>
          <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
            {#if b.payments.length > 0}
              <table class="w-full text-sm">
                <thead>
                  <tr class="border-b border-neutral-200">
                    <th class="px-4 py-2.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Date</th>
                    <th class="px-4 py-2.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Amount</th>
                    <th class="px-4 py-2.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Method</th>
                    <th class="px-4 py-2.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Ref</th>
                    <th class="px-4 py-2.5 w-12"></th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-neutral-100">
                  {#each b.payments as payment}
                    <tr class="hover:bg-neutral-50 transition-colors">
                      <td class="px-4 py-3 text-neutral-800">{formatDate(payment.payment_date)}</td>
                      <td class="px-4 py-3 text-right text-neutral-800 tabular-nums font-medium">{formatCurrency(payment.amount)}</td>
                      <td class="px-4 py-3 text-neutral-500">{paymentMethodLabels[payment.payment_method] ?? payment.payment_method}</td>
                      <td class="px-4 py-3 text-neutral-500 truncate max-w-[120px]">{payment.reference_number || "\u2014"}</td>
                      <td class="px-4 py-3 text-right">
                        <button onclick={() => removePayment(payment.id)} class="text-xs text-neutral-400 hover:text-red-600 transition-colors">Del</button>
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            {:else}
              <div class="p-6 text-center">
                <p class="text-sm text-neutral-400">No payments recorded yet.</p>
              </div>
            {/if}

            <!-- Record payment -->
            <div class="border-t border-neutral-200 px-4 py-3">
              <p class="text-xs font-medium text-neutral-500 mb-2">Record Payment</p>
              <div class="grid grid-cols-2 gap-2">
                <label>
                  <span class="block text-xs text-neutral-400 mb-1">Amount</span>
                  <input bind:value={paymentForm.amount} placeholder="0.00" class="w-full px-2.5 py-2 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />
                </label>
                <label>
                  <span class="block text-xs text-neutral-400 mb-1">Date</span>
                  <DateInput bind:value={paymentForm.payment_date} />
                </label>
                <label>
                  <span class="block text-xs text-neutral-400 mb-1">Method</span>
                  <select bind:value={paymentForm.payment_method} class="w-full px-2.5 py-2 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent">
                    <option value="bank_transfer">Bank Transfer</option>
                    <option value="check">Check</option>
                    <option value="cash">Cash</option>
                    <option value="credit_card">Credit Card</option>
                    <option value="other">Other</option>
                  </select>
                </label>
                <label>
                  <span class="block text-xs text-neutral-400 mb-1">Reference #</span>
                  <input bind:value={paymentForm.reference_number} placeholder="Optional" class="w-full px-2.5 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />
                </label>
              </div>
              <button type="button" onclick={recordPayment} disabled={recordingPayment} class="mt-2 px-4 py-2 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">
                {recordingPayment ? "Recording..." : "Record Payment"}
              </button>
            </div>
          </div>
        </div>
      </div>
    {/if}
  </div>
{/if}

<style>
  .drawer-slide-in {
    animation: drawerSlideIn 0.25s ease-out both;
  }

  @keyframes drawerSlideIn {
    from { transform: translateX(100%); }
    to { transform: translateX(0); }
  }
</style>

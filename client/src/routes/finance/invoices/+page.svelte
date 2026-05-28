<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { useAutoRefresh } from "$lib/realtime.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import Modal from "$lib/components/Modal.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import ApprovalTimeline from "$lib/components/workflows/ApprovalTimeline.svelte";
  import DecisionPanel from "$lib/components/workflows/DecisionPanel.svelte";
  import type {
    Invoice,
    InvoiceListItem,
    CustomerListItem,
    PropertyListItem,
    PaginatedResponse,
    WorkflowInstanceDetail,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let search = $state("");
  let status = $state("");
  let customerId = $state("");
  let currentPage = $state(1);
  const pageSize = 25;

  let invoices = $state<InvoiceListItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let customers = $state<CustomerListItem[]>([]);
  let properties = $state<PropertyListItem[]>([]);

  let showCreateModal = $state(false);
  let createForm = $state({
    invoice_number: "",
    customer: "",
    property: "",
    issue_date: "",
    due_date: "",
    notes: "",
  });
  let createErrors = $state<Record<string, string[]>>({});
  let savingInvoice = $state(false);

  function createFieldError(field: string): string {
    return createErrors[field]?.[0] ?? "";
  }

  function resetCreateForm() {
    createForm = {
      invoice_number: "",
      customer: "",
      property: "",
      issue_date: "",
      due_date: "",
      notes: "",
    };
    createErrors = {};
  }

  async function handleCreateInvoice(e: Event) {
    e.preventDefault();
    createErrors = {};
    savingInvoice = true;

    try {
      const payload: Record<string, unknown> = {
        customer: createForm.customer ? Number(createForm.customer) : null,
        issue_date: createForm.issue_date || null,
        due_date: createForm.due_date || null,
        notes: createForm.notes,
      };
      if (createForm.invoice_number.trim()) {
        payload.invoice_number = createForm.invoice_number.trim();
      }
      if (createForm.property) {
        payload.property = Number(createForm.property);
      }
      const result = await api.post<Invoice>("/finance/invoices/", payload);
      toast.success("Invoice created", `"${result.invoice_number}" has been added`);
      showCreateModal = false;
      resetCreateForm();
      fetchInvoices();
    } catch (err) {
      if (err instanceof ApiError) {
        createErrors = err.fieldErrors;
        const allErrors = Object.entries(err.fieldErrors);
        if (allErrors.length > 0) {
          const [field, messages] = allErrors[0];
          const msg = Array.isArray(messages) ? messages[0] : messages;
          const label = field === "non_field_errors" || field === "detail" ? "" : `${field}: `;
          toast.error("Validation error", `${label}${typeof msg === "string" ? msg : "Please check the form"}`);
        } else {
          toast.error("Validation error", "Please fix the highlighted fields");
        }
      } else {
        toast.error("Something went wrong", "Could not create the invoice");
      }
    }
    savingInvoice = false;
  }

  let debounceTimer: ReturnType<typeof setTimeout>;

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));

  let pageNumbers = $derived.by(() => {
    const pages: number[] = [];
    const maxVisible = 5;
    let start = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let end = Math.min(totalPages, start + maxVisible - 1);
    if (end - start + 1 < maxVisible) {
      start = Math.max(1, end - maxVisible + 1);
    }
    for (let i = start; i <= end; i++) {
      pages.push(i);
    }
    return pages;
  });


  function formatCurrency(value: string): string {
    const num = parseFloat(value);
    if (isNaN(num)) return value;
    return currency.format(num);
  }

  function formatDate(dateStr: string): string {
    if (!dateStr) return "";
    const d = new Date(dateStr + "T00:00:00");
    return d.toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  async function fetchInvoices() {
    loading = true;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        page_size: String(pageSize),
      };
      if (search) params.search = search;
      if (status) params.status = status;
      if (customerId) params.customer = customerId;

      const res = await api.get<PaginatedResponse<InvoiceListItem>>(
        "/finance/invoices/",
        params,
      );
      invoices = res.results;
      totalCount = res.count;
    } catch {
      invoices = [];
      totalCount = 0;
    } finally {
      loading = false;
    }
  }

  async function fetchCustomers() {
    try {
      const res = await api.get<PaginatedResponse<CustomerListItem>>(
        "/finance/customers/",
        { page_size: "200" },
      );
      customers = res.results;
    } catch {
      customers = [];
    }
  }

  async function fetchProperties() {
    try {
      const res = await api.get<PaginatedResponse<PropertyListItem>>(
        "/finance/properties/",
        { page_size: "200" },
      );
      properties = res.results;
    } catch {
      properties = [];
    }
  }

  function handleSearchInput(value: string) {
    search = value;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      currentPage = 1;
      fetchInvoices();
    }, 300);
  }

  function handleStatusChange(value: string) {
    status = value;
    currentPage = 1;
    fetchInvoices();
  }

  function handleCustomerChange(value: string) {
    customerId = value;
    currentPage = 1;
    fetchInvoices();
  }

  function goToPage(page: number) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    fetchInvoices();
  }

  // ── Dev fill ──
  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  const INVOICE_SAMPLES = [
    {
      invoice_number: "INV-2025-0091",
      notes: "Unit 14B — first quarterly service charge",
      issue_offset: 0,
      due_offset: 30,
    },
    {
      invoice_number: "INV-2025-0092",
      notes: "Parking bay lease renewal — Basement Level 2, Bay 37",
      issue_offset: -5,
      due_offset: 25,
    },
    {
      invoice_number: "INV-2025-0093",
      notes: "Roof terrace event space hire — corporate function 22 Mar",
      issue_offset: -2,
      due_offset: 14,
    },
    {
      invoice_number: "INV-2025-0094",
      notes: "Fit-out deposit — Unit 8A commercial shell",
      issue_offset: -1,
      due_offset: 7,
    },
  ];

  let invoiceDevIdx = $state(0);

  function devFillInvoice() {
    const sample = INVOICE_SAMPLES[invoiceDevIdx % INVOICE_SAMPLES.length];
    invoiceDevIdx++;

    const today = new Date();
    const issueDate = new Date(today);
    issueDate.setDate(issueDate.getDate() + sample.issue_offset);
    const dueDate = new Date(today);
    dueDate.setDate(dueDate.getDate() + sample.due_offset);

    createForm.invoice_number = sample.invoice_number;
    createForm.customer = customers.length > 0 ? String(customers[invoiceDevIdx % customers.length].id) : "";
    createForm.property = properties.length > 0 ? String(properties[invoiceDevIdx % properties.length].id) : "";
    createForm.issue_date = issueDate.toISOString().slice(0, 10);
    createForm.due_date = dueDate.toISOString().slice(0, 10);
    createForm.notes = sample.notes;
  }

  $effect(() => {
    fetchCustomers();
    fetchProperties();
    fetchInvoices();
  });

  // ── Detail drawer ──
  let drawerOpen = $state(false);
  let drawerInvoice = $state<Invoice | null>(null);
  let drawerLoading = $state(false);
  let dSaving = $state(false);
  let dDeleting = $state(false);
  let dErrors = $state<Record<string, string[]>>({});

  let dForm = $state({
    invoice_number: "", customer: "", property: "",
    issue_date: "", due_date: "", status: "draft",
    tax_amount: "", notes: "",
  });

  let workflow = $state<WorkflowInstanceDetail | null>(null);
  let submittingApproval = $state(false);

  let lineForm = $state({ description: "", quantity: "", unit_price: "" });
  let addingLine = $state(false);

  let paymentForm = $state({ amount: "", payment_date: "", payment_method: "bank_transfer", reference_number: "", notes: "" });
  let recordingPayment = $state(false);

  const paymentMethodLabels: Record<string, string> = {
    bank_transfer: "Bank Transfer", check: "Check", cash: "Cash",
    credit_card: "Credit Card", other: "Other",
  };

  function dFieldError(f: string): string { return dErrors[f]?.[0] ?? ""; }

  async function openDrawer(id: number) {
    drawerOpen = true;
    drawerLoading = true;
    drawerInvoice = null;
    workflow = null;
    dErrors = {};
    try {
      drawerInvoice = await api.get<Invoice>(`/finance/invoices/${id}/`);
      dForm = {
        invoice_number: drawerInvoice.invoice_number,
        customer: String(drawerInvoice.customer),
        property: drawerInvoice.property ? String(drawerInvoice.property) : "",
        issue_date: drawerInvoice.issue_date,
        due_date: drawerInvoice.due_date,
        status: drawerInvoice.status,
        tax_amount: drawerInvoice.tax_amount,
        notes: drawerInvoice.notes,
      };
      try {
        const res = await api.get<{ results: WorkflowInstanceDetail[] }>("/workflows/instances/", { model: "finance.invoice", object_id: String(id) });
        workflow = res.results.length > 0 ? res.results[0] : null;
      } catch { workflow = null; }
    } catch {
      toast.error("Not found", "Invoice could not be loaded");
      drawerOpen = false;
    }
    drawerLoading = false;
  }

  function closeDrawer() { drawerOpen = false; drawerInvoice = null; workflow = null; }

  async function reloadDrawerInvoice() {
    if (!drawerInvoice) return;
    drawerInvoice = await api.get<Invoice>(`/finance/invoices/${drawerInvoice.id}/`);
    dForm.status = drawerInvoice.status;
    fetchInvoices();
  }

  async function loadDrawerWorkflow() {
    if (!drawerInvoice) return;
    try {
      const res = await api.get<{ results: WorkflowInstanceDetail[] }>("/workflows/instances/", { model: "finance.invoice", object_id: String(drawerInvoice.id) });
      workflow = res.results.length > 0 ? res.results[0] : null;
    } catch { workflow = null; }
  }

  async function dHandleSave(e: Event) {
    e.preventDefault();
    if (!drawerInvoice) return;
    dErrors = {};
    dSaving = true;
    try {
      drawerInvoice = await api.patch<Invoice>(`/finance/invoices/${drawerInvoice.id}/`, {
        invoice_number: dForm.invoice_number, customer: dForm.customer ? Number(dForm.customer) : null,
        property: dForm.property ? Number(dForm.property) : null,
        issue_date: dForm.issue_date || null, due_date: dForm.due_date || null,
        status: dForm.status, tax_amount: dForm.tax_amount || "0.00", notes: dForm.notes,
      });
      toast.success("Invoice updated", "Changes saved");
      fetchInvoices();
    } catch (err) {
      if (err instanceof ApiError) { dErrors = err.fieldErrors; toast.error("Validation error", "Please fix the fields"); }
      else toast.error("Error", "Could not update invoice");
    }
    dSaving = false;
  }

  async function dHandleDelete() {
    if (!drawerInvoice || !confirm("Delete this invoice?")) return;
    dDeleting = true;
    try {
      await api.delete(`/finance/invoices/${drawerInvoice.id}/`);
      toast.success("Deleted", "Invoice removed");
      closeDrawer();
      fetchInvoices();
    } catch { toast.error("Error", "Could not delete"); }
    dDeleting = false;
  }

  async function dSubmitApproval() {
    if (!drawerInvoice) return;
    submittingApproval = true;
    try {
      await api.post(`/finance/invoices/${drawerInvoice.id}/submit-approval/`, {});
      toast.success("Submitted", "Invoice submitted for approval");
      await Promise.all([reloadDrawerInvoice(), loadDrawerWorkflow()]);
    } catch { toast.error("Error", "Could not submit"); }
    submittingApproval = false;
  }

  async function dAddLine() {
    if (!drawerInvoice || !lineForm.description || !lineForm.quantity || !lineForm.unit_price) return;
    addingLine = true;
    try {
      await api.post(`/finance/invoices/${drawerInvoice.id}/line-items/`, lineForm);
      lineForm = { description: "", quantity: "", unit_price: "" };
      toast.success("Added", "");
      await reloadDrawerInvoice();
    } catch (err) {
      if (err instanceof ApiError) toast.error("Error", Object.values(err.fieldErrors).flat()[0] || "Could not add");
      else toast.error("Error", "Could not add line item");
    }
    addingLine = false;
  }

  async function dRemoveLine(itemId: number) {
    if (!drawerInvoice || !confirm("Remove this line item?")) return;
    try {
      await api.delete(`/finance/invoices/${drawerInvoice.id}/line-items/${itemId}/`);
      await reloadDrawerInvoice();
    } catch { toast.error("Error", "Could not remove"); }
  }

  async function dRecordPayment() {
    if (!drawerInvoice || !paymentForm.amount || !paymentForm.payment_date) return;
    recordingPayment = true;
    try {
      await api.post(`/finance/invoices/${drawerInvoice.id}/payments/`, paymentForm);
      paymentForm = { amount: "", payment_date: "", payment_method: "bank_transfer", reference_number: "", notes: "" };
      toast.success("Payment recorded", "");
      await reloadDrawerInvoice();
    } catch (err) {
      if (err instanceof ApiError) toast.error("Error", Object.values(err.fieldErrors).flat()[0] || "Could not record");
      else toast.error("Error", "Could not record payment");
    }
    recordingPayment = false;
  }

  async function dRemovePayment(paymentId: number) {
    if (!drawerInvoice || !confirm("Remove this payment?")) return;
    try {
      await api.delete(`/finance/invoices/${drawerInvoice.id}/payments/${paymentId}/`);
      await reloadDrawerInvoice();
    } catch { toast.error("Error", "Could not remove payment"); }
  }

  useAutoRefresh("Invoice", fetchInvoices);
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-pink-600">Accounts Receivable</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Invoices</h1>
      <p class="mt-1 text-sm text-neutral-500">Automate construction invoicing to improve cash flow and cut errors</p>
    </div>
    <button
      onclick={() => showCreateModal = true}
      class="inline-flex items-center px-4 py-2.5 bg-neutral-800 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
    >
      + New Invoice
    </button>
  </div>

  <!-- Filters -->
  <div class="bg-white rounded-xl border border-neutral-200 p-5">
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5"
          >Search</span
        >
        <input
          type="text"
          placeholder="Search invoices..."
          value={search}
          oninput={(e) =>
            handleSearchInput((e.target as HTMLInputElement).value)}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
        />
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5"
          >Status</span
        >
        <select
          value={status}
          onchange={(e) =>
            handleStatusChange((e.target as HTMLSelectElement).value)}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
        >
          <option value="">All</option>
          <option value="draft">Draft</option>
          <option value="sent">Sent</option>
          <option value="paid">Paid</option>
          <option value="overdue">Overdue</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5"
          >Customer</span
        >
        <select
          value={customerId}
          onchange={(e) =>
            handleCustomerChange((e.target as HTMLSelectElement).value)}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
        >
          <option value="">All Customers</option>
          {#each customers as customer}
            <option value={String(customer.id)}>{customer.name}</option>
          {/each}
        </select>
      </label>
    </div>
  </div>

  <!-- Table -->
  <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
    {#if loading}
      <div class="flex items-center justify-center py-20">
        <div
          class="h-8 w-8 animate-spin rounded-full border-4 border-neutral-200 border-t-neutral-800"
        ></div>
      </div>
    {:else if invoices.length === 0}
      <div class="flex flex-col items-center justify-center py-20 text-center">
        <div class="text-neutral-400 mb-2">
          <svg
            class="mx-auto h-12 w-12"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="1.5"
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
        </div>
        <p class="text-neutral-500 text-sm">No invoices found</p>
        <button
          onclick={() => showCreateModal = true}
          class="mt-3 text-sm font-medium text-neutral-800 hover:underline"
        >
          Create your first invoice
        </button>
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="border-b border-neutral-200 bg-pink-100">
            <tr>
              <th
                class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider"
                >Invoice #</th
              >
              <th
                class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider"
                >Customer</th
              >
              <th
                class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider"
                >Status</th
              >
              <th
                class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider"
                >Issue Date</th
              >
              <th
                class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider"
                >Due Date</th
              >
              <th
                class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider"
                >Total</th
              >
              <th
                class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider"
                >Paid</th
              >
              <th
                class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider"
                >Balance</th
              >
              <th
                class="px-5 py-3.5 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider"
                >Overdue</th
              >
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each invoices as invoice}
              <tr
                class="hover:bg-neutral-50 cursor-pointer transition-colors"
                onclick={() => openDrawer(invoice.id)}
              >
                <td class="px-5 py-4 text-sm font-medium text-neutral-800">
                  {invoice.invoice_number}
                </td>
                <td class="px-5 py-4 text-sm text-neutral-700">
                  {invoice.customer_name}
                </td>
                <td class="px-5 py-4">
                  <StatusBadge status={invoice.status} />
                </td>
                <td class="px-5 py-4 text-sm text-neutral-500">
                  {formatDate(invoice.issue_date)}
                </td>
                <td class="px-5 py-4 text-sm text-neutral-500">
                  {formatDate(invoice.due_date)}
                </td>
                <td class="px-5 py-4 text-sm text-neutral-800 text-right">
                  {formatCurrency(invoice.total_amount)}
                </td>
                <td class="px-5 py-4 text-sm text-neutral-500 text-right">
                  {formatCurrency(invoice.paid_amount)}
                </td>
                <td class="px-5 py-4 text-sm text-neutral-800 font-medium text-right">
                  {formatCurrency(invoice.balance_due)}
                </td>
                <td class="px-5 py-4 text-center">
                  {#if invoice.is_overdue}
                    <span
                      class="inline-block h-2.5 w-2.5 rounded-full bg-red-500"
                      title="{invoice.days_overdue} days overdue"
                    ></span>
                  {/if}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div
        class="flex items-center justify-between border-t border-neutral-200 px-5 py-4"
      >
        <p class="text-sm text-neutral-400">
          Showing {(currentPage - 1) * pageSize + 1}–{Math.min(currentPage * pageSize, totalCount)} of {totalCount}
        </p>
        {#if totalPages > 1}
          <div class="flex items-center gap-1">
            <button
              onclick={() => goToPage(currentPage - 1)}
              disabled={currentPage <= 1}
              aria-label="Previous page"
              class="px-3 py-1.5 text-sm rounded-lg border border-neutral-200 hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
              </svg>
            </button>
            {#each pageNumbers as pg}
              <button
                onclick={() => goToPage(pg)}
                class="px-3 py-1.5 text-sm rounded-lg border transition-colors {pg === currentPage
                  ? 'bg-neutral-800 text-white border-neutral-800'
                  : 'border-neutral-200 hover:bg-neutral-50'}"
              >
                {pg}
              </button>
            {/each}
            <button
              onclick={() => goToPage(currentPage + 1)}
              disabled={currentPage >= totalPages}
              aria-label="Next page"
              class="px-3 py-1.5 text-sm rounded-lg border border-neutral-200 hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
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
</div>

<Modal open={showCreateModal} onclose={() => { showCreateModal = false; resetCreateForm(); }} title="New Invoice" maxWidth="max-w-xl">
  <form onsubmit={handleCreateInvoice} class="space-y-5">
    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Invoice Number <span class="text-neutral-400 font-normal">(auto-generated if blank)</span></span>
      <input
        type="text"
        bind:value={createForm.invoice_number}
        placeholder="Auto-generated"
        class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
      />
      {#if createFieldError("invoice_number")}<p class="mt-1 text-xs text-red-500">{createFieldError("invoice_number")}</p>{/if}
    </label>

    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Customer</span>
      <select
        bind:value={createForm.customer}
        class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
      >
        <option value="">Select a customer</option>
        {#each customers as customer}
          <option value={String(customer.id)}>{customer.name}</option>
        {/each}
      </select>
      {#if createFieldError("customer")}<p class="mt-1 text-xs text-red-500">{createFieldError("customer")}</p>{/if}
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
          onclick={devFillInvoice}
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
        disabled={savingInvoice}
        class="px-4 py-2.5 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
      >
        {savingInvoice ? "Creating..." : "Create Invoice"}
      </button>
    </div>
  </form>
</Modal>

<!-- Invoice Detail Drawer -->
{#if drawerOpen}
  <div class="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm" onclick={closeDrawer} onkeydown={(e) => e.key === "Escape" && closeDrawer()} role="button" tabindex="-1"></div>
  <div class="fixed inset-y-0 right-0 z-50 w-full max-w-2xl bg-white shadow-2xl border-l border-neutral-200 flex flex-col drawer-slide-in">
    {#if drawerLoading}
      <div class="flex-1 flex items-center justify-center"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div></div>
    {:else if drawerInvoice}
      {@const inv = drawerInvoice}

      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200">
        <div class="flex items-center gap-3">
          <h2 class="text-lg font-bold text-neutral-800">{inv.invoice_number}</h2>
          <StatusBadge status={inv.status} size="md" />
          {#if workflow}<StatusBadge status={workflow.state} size="md" />{/if}
        </div>
        <button onclick={closeDrawer} class="w-8 h-8 flex items-center justify-center rounded-lg text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 transition-colors" aria-label="Close">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
        </button>
      </div>

      <!-- Body -->
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-6">
        <!-- Summary card (pink) -->
        <div class="rounded-xl bg-pink-50 border border-pink-100 p-5">
          <div class="grid grid-cols-4 gap-4 text-center">
            <div>
              <p class="text-xs font-medium text-pink-400 uppercase tracking-wider mb-1">Subtotal</p>
              <p class="text-sm font-semibold text-pink-900 tabular-nums">{currency.format(inv.subtotal)}</p>
            </div>
            <div>
              <p class="text-xs font-medium text-pink-400 uppercase tracking-wider mb-1">Tax</p>
              <p class="text-sm font-semibold text-pink-900 tabular-nums">{currency.format(inv.tax_amount)}</p>
            </div>
            <div>
              <p class="text-xs font-medium text-pink-400 uppercase tracking-wider mb-1">Paid</p>
              <p class="text-sm font-semibold text-emerald-700 tabular-nums">{currency.format(inv.paid_amount)}</p>
            </div>
            <div>
              <p class="text-xs font-medium text-pink-400 uppercase tracking-wider mb-1">Balance</p>
              <p class="text-sm font-bold tabular-nums" style="color: {Number(inv.balance_due) > 0 ? '#dc2626' : '#171717'};">{currency.format(inv.balance_due)}</p>
            </div>
          </div>
        </div>

        <!-- Editable form -->
        <form onsubmit={dHandleSave} class="space-y-4">
          <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider">Invoice Details</h3>
          <div class="grid grid-cols-2 gap-3">
            <label><span class="block text-sm font-medium text-neutral-700 mb-1">Invoice Number</span><input bind:value={dForm.invoice_number} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />{#if dFieldError("invoice_number")}<p class="mt-1 text-xs text-red-500">{dFieldError("invoice_number")}</p>{/if}</label>
            <label><span class="block text-sm font-medium text-neutral-700 mb-1">Status</span><select bind:value={dForm.status} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"><option value="draft">Draft</option><option value="sent">Sent</option><option value="paid">Paid</option><option value="overdue">Overdue</option><option value="cancelled">Cancelled</option></select></label>
          </div>
          <label><span class="block text-sm font-medium text-neutral-700 mb-1">Customer</span><select bind:value={dForm.customer} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"><option value="">Select</option>{#each customers as c}<option value={String(c.id)}>{c.name}</option>{/each}</select></label>
          <label><span class="block text-sm font-medium text-neutral-700 mb-1">Property <span class="text-neutral-400 font-normal">(optional)</span></span><select bind:value={dForm.property} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"><option value="">None</option>{#each properties as p}<option value={String(p.id)}>{p.name}</option>{/each}</select></label>
          <div class="grid grid-cols-2 gap-3">
            <label><span class="block text-sm font-medium text-neutral-700 mb-1">Issue Date</span><DateInput bind:value={dForm.issue_date} /></label>
            <label><span class="block text-sm font-medium text-neutral-700 mb-1">Due Date</span><DateInput bind:value={dForm.due_date} /></label>
          </div>
          <label><span class="block text-sm font-medium text-neutral-700 mb-1">Tax Amount</span><input bind:value={dForm.tax_amount} placeholder="0.00" class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" /></label>
          <label><span class="block text-sm font-medium text-neutral-700 mb-1">Notes</span><textarea bind:value={dForm.notes} rows={2} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"></textarea></label>
          <div class="flex items-center justify-between">
            <button type="submit" disabled={dSaving} class="px-5 py-2 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">{dSaving ? "Saving..." : "Save Changes"}</button>
            <button type="button" onclick={dHandleDelete} disabled={dDeleting} class="px-4 py-2 border border-red-200 text-red-600 rounded-lg text-sm font-medium hover:bg-red-50 disabled:opacity-50 transition-colors">{dDeleting ? "Deleting..." : "Delete Invoice"}</button>
          </div>
        </form>

        <!-- Approval -->
        {#if workflow}
          <div class="space-y-3">
            <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider">Approval</h3>
            <DecisionPanel instance={workflow} onDecision={loadDrawerWorkflow} />
            {#if workflow.steps.length > 0}
              <div class="bg-white rounded-xl border border-neutral-200 p-4"><ApprovalTimeline steps={workflow.steps} /></div>
            {/if}
          </div>
        {:else if inv.status === "draft"}
          <div>
            <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-3">Approval</h3>
            <p class="text-xs text-neutral-400 mb-3">Submit this invoice for workflow-based approval.</p>
            <button type="button" onclick={dSubmitApproval} disabled={submittingApproval} class="w-full px-4 py-2.5 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">{submittingApproval ? "Submitting..." : "Submit for Approval"}</button>
          </div>
        {/if}

        <!-- Line Items -->
        <div>
          <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-3">Line Items</h3>
          <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
            {#if inv.line_items.length > 0}
              <table class="w-full text-sm">
                <thead><tr class="border-b border-neutral-200">
                  <th class="px-4 py-2.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Description</th>
                  <th class="px-4 py-2.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Qty</th>
                  <th class="px-4 py-2.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Price</th>
                  <th class="px-4 py-2.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Amount</th>
                  <th class="px-4 py-2.5 w-12"></th>
                </tr></thead>
                <tbody class="divide-y divide-neutral-100">
                  {#each inv.line_items as item}
                    <tr class="hover:bg-neutral-50 transition-colors">
                      <td class="px-4 py-3 text-neutral-800">{item.description}</td>
                      <td class="px-4 py-3 text-right text-neutral-500 tabular-nums">{item.quantity}</td>
                      <td class="px-4 py-3 text-right text-neutral-500 tabular-nums">{currency.format(item.unit_price)}</td>
                      <td class="px-4 py-3 text-right text-neutral-800 tabular-nums font-medium">{currency.format(item.amount)}</td>
                      <td class="px-4 py-3 text-right"><button onclick={() => dRemoveLine(item.id)} class="text-xs text-neutral-400 hover:text-red-600 transition-colors">Del</button></td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            {:else}
              <div class="p-6 text-center"><p class="text-sm text-neutral-400">No line items yet.</p></div>
            {/if}
            <div class="border-t border-neutral-200 px-4 py-3">
              <div class="flex items-end gap-2">
                <label class="flex-1"><span class="block text-xs font-medium text-neutral-500 mb-1">Description</span><input bind:value={lineForm.description} placeholder="Item" class="w-full px-2.5 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" /></label>
                <label class="w-16"><span class="block text-xs font-medium text-neutral-500 mb-1">Qty</span><input bind:value={lineForm.quantity} placeholder="1" class="w-full px-2.5 py-2 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" /></label>
                <label class="w-24"><span class="block text-xs font-medium text-neutral-500 mb-1">Price</span><input bind:value={lineForm.unit_price} placeholder="0.00" class="w-full px-2.5 py-2 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" /></label>
                <button type="button" onclick={dAddLine} disabled={addingLine} class="px-3 py-2 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">{addingLine ? "..." : "Add"}</button>
              </div>
            </div>
          </div>
        </div>

        <!-- Payments -->
        <div>
          <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-3">Payments</h3>
          <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
            {#if inv.payments.length > 0}
              <table class="w-full text-sm">
                <thead><tr class="border-b border-neutral-200">
                  <th class="px-4 py-2.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Date</th>
                  <th class="px-4 py-2.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Amount</th>
                  <th class="px-4 py-2.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Method</th>
                  <th class="px-4 py-2.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Ref</th>
                  <th class="px-4 py-2.5 w-12"></th>
                </tr></thead>
                <tbody class="divide-y divide-neutral-100">
                  {#each inv.payments as payment}
                    <tr class="hover:bg-neutral-50 transition-colors">
                      <td class="px-4 py-3 text-neutral-800">{new Date(payment.payment_date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}</td>
                      <td class="px-4 py-3 text-right text-neutral-800 tabular-nums font-medium">{currency.format(payment.amount)}</td>
                      <td class="px-4 py-3 text-neutral-500">{paymentMethodLabels[payment.payment_method] ?? payment.payment_method}</td>
                      <td class="px-4 py-3 text-neutral-500 truncate max-w-[120px]">{payment.reference_number || "\u2014"}</td>
                      <td class="px-4 py-3 text-right"><button onclick={() => dRemovePayment(payment.id)} class="text-xs text-neutral-400 hover:text-red-600 transition-colors">Del</button></td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            {:else}
              <div class="p-6 text-center"><p class="text-sm text-neutral-400">No payments recorded.</p></div>
            {/if}
            <div class="border-t border-neutral-200 px-4 py-3">
              <p class="text-xs font-medium text-neutral-500 mb-2">Record Payment</p>
              <div class="grid grid-cols-2 gap-2">
                <label><span class="block text-xs text-neutral-400 mb-1">Amount</span><input bind:value={paymentForm.amount} placeholder="0.00" class="w-full px-2.5 py-2 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" /></label>
                <label><span class="block text-xs text-neutral-400 mb-1">Date</span><DateInput bind:value={paymentForm.payment_date} /></label>
                <label><span class="block text-xs text-neutral-400 mb-1">Method</span><select bind:value={paymentForm.payment_method} class="w-full px-2.5 py-2 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"><option value="bank_transfer">Bank Transfer</option><option value="check">Check</option><option value="cash">Cash</option><option value="credit_card">Credit Card</option><option value="other">Other</option></select></label>
                <label><span class="block text-xs text-neutral-400 mb-1">Reference #</span><input bind:value={paymentForm.reference_number} placeholder="Optional" class="w-full px-2.5 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" /></label>
              </div>
              <button type="button" onclick={dRecordPayment} disabled={recordingPayment} class="mt-2 px-4 py-2 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">{recordingPayment ? "Recording..." : "Record Payment"}</button>
            </div>
          </div>
        </div>
      </div>
    {/if}
  </div>
{/if}

<style>
  .drawer-slide-in { animation: drawerSlideIn 0.25s ease-out both; }
  @keyframes drawerSlideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }
</style>

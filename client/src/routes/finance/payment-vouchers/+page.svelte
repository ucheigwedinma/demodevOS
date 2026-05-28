<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import Modal from "$lib/components/Modal.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DateInput from "$lib/components/DateInput.svelte";
  import type {
    PaymentVoucher,
    PaymentVoucherListItem,
    VendorListItem,
    BillListItem,
    PaginatedResponse,
  } from "$lib/types";

  let data = $state<PaymentVoucherListItem[]>([]);
  let totalCount = $state(0);
  let currentPage = $state(1);
  let searchQuery = $state("");
  let statusFilter = $state("");
  let vendorFilter = $state("");
  let loading = $state(true);
  let vendors = $state<VendorListItem[]>([]);

  // ── Create modal ──
  let showCreateModal = $state(false);
  let bills = $state<BillListItem[]>([]);
  let createForm = $state({
    voucher_number: "",
    vendor: "",
    bill: "",
    issue_date: "",
    amount: "",
    payment_method: "",
    description: "",
    notes: "",
  });
  let createErrors = $state<Record<string, string[]>>({});
  let savingVoucher = $state(false);

  function createFieldError(field: string): string {
    return createErrors[field]?.[0] ?? "";
  }

  function resetCreateForm() {
    createForm = {
      voucher_number: "",
      vendor: "",
      bill: "",
      issue_date: "",
      amount: "",
      payment_method: "",
      description: "",
      notes: "",
    };
    createErrors = {};
  }

  async function handleCreateVoucher(e: Event) {
    e.preventDefault();
    createErrors = {};
    savingVoucher = true;

    try {
      const body: Record<string, unknown> = {
        vendor: createForm.vendor ? Number(createForm.vendor) : null,
        bill: createForm.bill ? Number(createForm.bill) : null,
        issue_date: createForm.issue_date || null,
        amount: createForm.amount || null,
        payment_method: createForm.payment_method || null,
        description: createForm.description,
        notes: createForm.notes,
      };
      if (createForm.voucher_number.trim()) {
        body.voucher_number = createForm.voucher_number.trim();
      }

      const result = await api.post<PaymentVoucher>("/finance/payment-vouchers/", body);
      toast.success("Voucher created", `"${result.voucher_number}" has been created`);
      showCreateModal = false;
      resetCreateForm();
      fetchVouchers();
    } catch (err) {
      if (err instanceof ApiError) {
        createErrors = err.fieldErrors;
        toast.error("Validation error", "Please fix the highlighted fields below");
      } else {
        toast.error("Something went wrong", "Could not create the payment voucher");
      }
    }
    savingVoucher = false;
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

  async function fetchBills() {
    try {
      const params: Record<string, string> = { page_size: "200", status: "approved" };
      if (createForm.vendor) params.vendor = createForm.vendor;
      const res = await api.get<PaginatedResponse<BillListItem>>("/finance/bills/", params);
      bills = res.results;
    } catch {
      bills = [];
    }
  }

  async function fetchVouchers() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage) };
      if (searchQuery) params.search = searchQuery;
      if (statusFilter) params.status = statusFilter;
      if (vendorFilter) params.vendor = vendorFilter;

      const res = await api.get<PaginatedResponse<PaymentVoucherListItem>>("/finance/payment-vouchers/", params);
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

  const VOUCHER_SAMPLES = [
    {
      voucher_number: "PV-2026-001",
      description: "Payment for cement and rebar — Phase 3 foundation works",
      amount: "245000.00",
      payment_method: "bank_transfer",
      notes: "Ref: BILL-2025-0042. Wire to vendor's Zenith account.",
      issue_offset: 0,
    },
    {
      voucher_number: "PV-2026-002",
      description: "Electrical sub-contractor — Block A wiring milestone",
      amount: "187500.00",
      payment_method: "cheque",
      notes: "Cheque to be collected from accounts office.",
      issue_offset: -1,
    },
    {
      voucher_number: "PV-2026-003",
      description: "Plumbing fixtures — Units 12-24 fit-out",
      amount: "92300.00",
      payment_method: "bank_transfer",
      notes: "Second tranche per PO-2025-118.",
      issue_offset: -3,
    },
    {
      voucher_number: "PV-2026-004",
      description: "Monthly site security services — March 2026",
      amount: "45000.00",
      payment_method: "bank_transfer",
      notes: "Recurring monthly payment.",
      issue_offset: 0,
    },
  ];

  let devIdx = $state(0);

  function devFillVoucher() {
    const sample = VOUCHER_SAMPLES[devIdx % VOUCHER_SAMPLES.length];
    devIdx++;

    const today = new Date();
    const issueDate = new Date(today);
    issueDate.setDate(issueDate.getDate() + sample.issue_offset);

    createForm.voucher_number = sample.voucher_number;
    createForm.vendor = vendors.length > 0 ? String(vendors[devIdx % vendors.length].id) : "";
    createForm.bill = bills.length > 0 ? String(bills[devIdx % bills.length].id) : "";
    createForm.issue_date = issueDate.toISOString().slice(0, 10);
    createForm.amount = sample.amount;
    createForm.payment_method = sample.payment_method;
    createForm.description = sample.description;
    createForm.notes = sample.notes;
  }

  $effect(() => {
    fetchVendors();
  });

  $effect(() => {
    void createForm.vendor;
    fetchBills();
  });

  $effect(() => {
    void searchQuery;
    void statusFilter;
    void vendorFilter;
    void currentPage;
    fetchVouchers();
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
  let drawerVoucher = $state<PaymentVoucher | null>(null);
  let drawerLoading = $state(false);
  let approving = $state(false);
  let voiding = $state(false);

  const PAYMENT_METHOD_LABELS: Record<string, string> = {
    bank_transfer: "Bank Transfer",
    cheque: "Cheque",
    check: "Check",
    cash: "Cash",
    credit_card: "Credit Card",
    mobile_money: "Mobile Money",
    other: "Other",
  };

  async function openDrawer(id: number) {
    drawerOpen = true;
    drawerLoading = true;
    drawerVoucher = null;
    try {
      drawerVoucher = await api.get<PaymentVoucher>(`/finance/payment-vouchers/${id}/`);
    } catch {
      toast.error("Not found", "Payment voucher could not be loaded");
      drawerOpen = false;
    }
    drawerLoading = false;
  }

  function closeDrawer() {
    drawerOpen = false;
    drawerVoucher = null;
  }

  async function handleApprove() {
    if (!drawerVoucher) return;
    approving = true;
    try {
      await api.post(`/finance/payment-vouchers/${drawerVoucher.id}/approve/`, {});
      toast.success("Approved", "Payment voucher has been approved");
      drawerVoucher = await api.get<PaymentVoucher>(`/finance/payment-vouchers/${drawerVoucher.id}/`);
      fetchVouchers();
    } catch {
      toast.error("Error", "Could not approve this voucher");
    }
    approving = false;
  }

  async function handleVoid() {
    if (!drawerVoucher) return;
    voiding = true;
    try {
      await api.post(`/finance/payment-vouchers/${drawerVoucher.id}/void/`, {});
      toast.success("Voided", "Payment voucher has been voided");
      drawerVoucher = await api.get<PaymentVoucher>(`/finance/payment-vouchers/${drawerVoucher.id}/`);
      fetchVouchers();
    } catch {
      toast.error("Error", "Could not void this voucher");
    }
    voiding = false;
  }

  function handlePrint() {
    window.print();
  }
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-green-600">Accounts Payable</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Payment Vouchers</h1>
      <p class="text-sm text-neutral-400 mt-1">Authorize and track vendor payment disbursements</p>
    </div>
    <button
      onclick={() => showCreateModal = true}
      class="px-4 py-2.5 bg-neutral-800 text-white rounded-lg hover:bg-neutral-800 text-sm font-medium transition-colors"
    >
      + New Voucher
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
        placeholder="Search vouchers..."
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
      <option value="pending">Pending</option>
      <option value="approved">Approved</option>
      <option value="paid">Paid</option>
      <option value="voided">Voided</option>
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
        <p class="mt-3 text-sm text-neutral-400">Loading payment vouchers...</p>
      </div>
    {:else if data.length === 0}
      <div class="p-16 text-center">
        <svg class="w-12 h-12 mx-auto text-neutral-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25ZM6.75 12h.008v.008H6.75V12Zm0 3h.008v.008H6.75V15Zm0 3h.008v.008H6.75V18Z" />
        </svg>
        <p class="mt-4 text-sm font-medium text-neutral-800">No payment vouchers found</p>
        <p class="mt-1 text-sm text-neutral-400">Get started by creating your first payment voucher.</p>
        <button
          onclick={() => showCreateModal = true}
          class="inline-block mt-4 px-4 py-2 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors"
        >
          + New Voucher
        </button>
      </div>
    {:else}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200">
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Voucher #</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Vendor</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Bill #</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Issue Date</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Method</th>
            <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Amount</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each data as voucher}
            <tr
              class="hover:bg-neutral-50 cursor-pointer transition-colors"
              onclick={() => openDrawer(voucher.id)}
            >
              <td class="px-5 py-4">
                <span class="font-medium text-neutral-800">{voucher.voucher_number}</span>
              </td>
              <td class="px-5 py-4 text-neutral-500">{voucher.vendor_name}</td>
              <td class="px-5 py-4 text-neutral-500">{voucher.bill_number ?? "\u2014"}</td>
              <td class="px-5 py-4">
                <StatusBadge status={voucher.status} />
              </td>
              <td class="px-5 py-4 text-neutral-500">{formatDate(voucher.issue_date)}</td>
              <td class="px-5 py-4 text-neutral-500 capitalize">{voucher.payment_method.replace(/_/g, " ")}</td>
              <td class="px-5 py-4 text-right text-neutral-800 tabular-nums font-medium">{formatCurrency(voucher.amount)}</td>
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
        {totalCount === 1 ? "voucher" : "vouchers"}
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

<Modal open={showCreateModal} onclose={() => { showCreateModal = false; resetCreateForm(); }} title="New Payment Voucher" maxWidth="max-w-xl">
  <form onsubmit={handleCreateVoucher} class="space-y-5">
    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Voucher Number <span class="text-neutral-400 font-normal">(auto-generated if blank)</span></span>
      <input
        type="text"
        bind:value={createForm.voucher_number}
        placeholder="Auto-generated"
        class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
      />
      {#if createFieldError("voucher_number")}<p class="mt-1 text-xs text-red-500">{createFieldError("voucher_number")}</p>{/if}
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
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Linked Bill <span class="text-neutral-400 font-normal">(optional)</span></span>
      <select
        bind:value={createForm.bill}
        class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
      >
        <option value="">None</option>
        {#each bills as bill}
          <option value={String(bill.id)}>{bill.bill_number} — {bill.vendor_name}</option>
        {/each}
      </select>
      {#if createFieldError("bill")}<p class="mt-1 text-xs text-red-500">{createFieldError("bill")}</p>{/if}
    </label>

    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Issue Date</span>
      <DateInput bind:value={createForm.issue_date} />
      {#if createFieldError("issue_date")}<p class="mt-1 text-xs text-red-500">{createFieldError("issue_date")}</p>{/if}
    </label>

    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Amount</span>
      <input
        type="text"
        inputmode="decimal"
        bind:value={createForm.amount}
        placeholder="0.00"
        class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent tabular-nums"
      />
      {#if createFieldError("amount")}<p class="mt-1 text-xs text-red-500">{createFieldError("amount")}</p>{/if}
    </label>

    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Payment Method</span>
      <select
        bind:value={createForm.payment_method}
        class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
      >
        <option value="">Select method</option>
        <option value="bank_transfer">Bank Transfer</option>
        <option value="cheque">Cheque</option>
        <option value="cash">Cash</option>
        <option value="mobile_money">Mobile Money</option>
      </select>
      {#if createFieldError("payment_method")}<p class="mt-1 text-xs text-red-500">{createFieldError("payment_method")}</p>{/if}
    </label>

    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Description</span>
      <input
        type="text"
        bind:value={createForm.description}
        placeholder="Brief description of the payment..."
        class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
      />
      {#if createFieldError("description")}<p class="mt-1 text-xs text-red-500">{createFieldError("description")}</p>{/if}
    </label>

    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Notes <span class="text-neutral-400 font-normal">(optional)</span></span>
      <textarea
        bind:value={createForm.notes}
        rows="3"
        placeholder="Additional notes..."
        class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent resize-none"
      ></textarea>
      {#if createFieldError("notes")}<p class="mt-1 text-xs text-red-500">{createFieldError("notes")}</p>{/if}
    </label>

    <div class="flex justify-end gap-3 pt-2">
      {#if isDev}
        <button
          type="button"
          onclick={devFillVoucher}
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
        disabled={savingVoucher}
        class="px-4 py-2.5 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
      >
        {savingVoucher ? "Creating..." : "Create Voucher"}
      </button>
    </div>
  </form>
</Modal>

<!-- Detail Drawer -->
{#if drawerOpen}
  <!-- Backdrop -->
  <div
    class="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm transition-opacity"
    onclick={closeDrawer}
    onkeydown={(e) => e.key === "Escape" && closeDrawer()}
    role="button"
    tabindex="-1"
  ></div>

  <!-- Drawer panel -->
  <div class="fixed inset-y-0 right-0 z-50 w-full max-w-lg bg-white shadow-2xl border-l border-neutral-200 flex flex-col drawer-slide-in">
    {#if drawerLoading}
      <div class="flex-1 flex items-center justify-center">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
        <span class="ml-3 text-sm text-neutral-400">Loading voucher...</span>
      </div>
    {:else if drawerVoucher}
      {@const v = drawerVoucher}

      <!-- Drawer header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200">
        <div class="flex items-center gap-3">
          <h2 class="text-lg font-bold text-neutral-800">{v.voucher_number}</h2>
          <StatusBadge status={v.status} size="md" />
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

      <!-- Drawer body -->
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-6">
        <!-- Summary -->
        <div class="flex items-center gap-4 text-sm text-neutral-500">
          <span>Issued {formatDate(v.issue_date)}</span>
          {#if v.vendor_name}
            <span class="text-neutral-300">&middot;</span>
            <span>{v.vendor_name}</span>
          {/if}
        </div>

        <!-- Amount highlight -->
        <div class="rounded-xl bg-pink-50 border border-pink-100 p-5 text-center">
          <p class="text-xs font-medium text-pink-400 uppercase tracking-wider mb-1">Amount</p>
          <p class="text-2xl font-bold text-pink-900 tabular-nums">{currency.format(v.amount)}</p>
          <p class="text-xs text-pink-300 mt-1">{currency.config.code}</p>
        </div>

        <!-- Payee Information -->
        {#if v.vendor_detail}
          {@const vd = v.vendor_detail}
          <div>
            <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-3">Payee Information</h3>
            <dl class="space-y-2.5 text-sm">
              <div>
                <dt class="text-neutral-400">Vendor / Entity</dt>
                <dd class="mt-0.5 font-medium text-neutral-800">{vd.name}</dd>
              </div>
              {#if vd.contact_person}
                <div>
                  <dt class="text-neutral-400">Contact Person</dt>
                  <dd class="mt-0.5 text-neutral-700">{vd.contact_person}</dd>
                </div>
              {/if}
              <div class="flex gap-8">
                {#if vd.email}
                  <div>
                    <dt class="text-neutral-400">Email</dt>
                    <dd class="mt-0.5 text-neutral-700">{vd.email}</dd>
                  </div>
                {/if}
                {#if vd.phone}
                  <div>
                    <dt class="text-neutral-400">Phone</dt>
                    <dd class="mt-0.5 text-neutral-700">{vd.phone}</dd>
                  </div>
                {/if}
              </div>
              {#if vd.bank_name || vd.bank_account_number}
                <div class="pt-2.5 border-t border-neutral-100">
                  <dt class="text-neutral-400 mb-1">Bank Details</dt>
                  <dd class="space-y-1 text-neutral-700">
                    {#if vd.bank_name}
                      <p>{vd.bank_name}{vd.bank_branch ? ` — ${vd.bank_branch}` : ""}</p>
                    {/if}
                    {#if vd.bank_account_number}
                      <p class="font-mono text-xs tracking-wide text-neutral-500">{vd.bank_account_number}</p>
                    {/if}
                  </dd>
                </div>
              {/if}
            </dl>
          </div>
        {/if}

        <!-- Payment Details -->
        <div>
          <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-3">Payment Details</h3>
          <dl class="space-y-2.5 text-sm">
            <div>
              <dt class="text-neutral-400">Payment Method</dt>
              <dd class="mt-0.5 font-medium text-neutral-800">{PAYMENT_METHOD_LABELS[v.payment_method] ?? v.payment_method}</dd>
            </div>
            <div>
              <dt class="text-neutral-400">Issue Date</dt>
              <dd class="mt-0.5 text-neutral-700">{formatDate(v.issue_date)}</dd>
            </div>
            {#if v.bill_number}
              <div>
                <dt class="text-neutral-400">Linked Bill</dt>
                <dd class="mt-0.5">
                  <a href="/finance/bills/{v.bill}" class="text-neutral-800 font-medium hover:underline">{v.bill_number}</a>
                </dd>
              </div>
            {/if}
            {#if v.description}
              <div>
                <dt class="text-neutral-400">Description</dt>
                <dd class="mt-0.5 text-neutral-700">{v.description}</dd>
              </div>
            {/if}
            {#if v.notes}
              <div>
                <dt class="text-neutral-400">Notes</dt>
                <dd class="mt-0.5 text-neutral-500 text-xs leading-relaxed">{v.notes}</dd>
              </div>
            {/if}
          </dl>
        </div>

        <!-- Approval info -->
        {#if v.approved_by_name || v.approved_at}
          <div>
            <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-3">Approval</h3>
            <dl class="space-y-2.5 text-sm">
              {#if v.approved_by_name}
                <div>
                  <dt class="text-neutral-400">Approved By</dt>
                  <dd class="mt-0.5 text-neutral-700">{v.approved_by_name}</dd>
                </div>
              {/if}
              {#if v.approved_at}
                <div>
                  <dt class="text-neutral-400">Approved At</dt>
                  <dd class="mt-0.5 text-neutral-700">{formatDate(v.approved_at)}</dd>
                </div>
              {/if}
            </dl>
          </div>
        {/if}
      </div>

      <!-- Drawer footer actions -->
      <div class="px-6 py-4 border-t border-neutral-200 flex items-center gap-2">
        {#if v.status === "draft" || v.status === "pending"}
          <button
            onclick={handleApprove}
            disabled={approving}
            class="inline-flex items-center gap-1.5 px-4 py-2.5 bg-neutral-800 text-white rounded-lg text-sm font-medium
                   hover:bg-neutral-800 disabled:opacity-50 transition-colors"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
            </svg>
            {approving ? "Approving..." : "Approve"}
          </button>
        {/if}

        <button
          onclick={handlePrint}
          class="inline-flex items-center gap-1.5 px-4 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700
                 hover:bg-neutral-50 transition-colors"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6.72 13.829c-.24.03-.48.062-.72.096m.72-.096a42.415 42.415 0 0 1 10.56 0m-10.56 0L6.34 18m10.94-4.171c.24.03.48.062.72.096m-.72-.096L17.66 18m0 0 .229 2.523a1.125 1.125 0 0 1-1.12 1.227H7.231c-.662 0-1.18-.568-1.12-1.227L6.34 18m11.318 0h1.091A2.25 2.25 0 0 0 21 15.75V9.456c0-1.081-.768-2.015-1.837-2.175a48.055 48.055 0 0 0-1.913-.247M6.34 18H5.25A2.25 2.25 0 0 1 3 15.75V9.456c0-1.081.768-2.015 1.837-2.175a48.041 48.041 0 0 1 1.913-.247m10.5 0a48.536 48.536 0 0 0-10.5 0m10.5 0V3.375c0-.621-.504-1.125-1.125-1.125h-8.25c-.621 0-1.125.504-1.125 1.125v3.659M18 10.5h.008v.008H18V10.5Zm-3 0h.008v.008H15V10.5Z" />
          </svg>
          Print
        </button>

        {#if v.status !== "voided" && v.status !== "paid"}
          <button
            onclick={handleVoid}
            disabled={voiding}
            class="ml-auto inline-flex items-center gap-1.5 px-4 py-2.5 border border-red-200 rounded-lg text-sm font-medium text-red-600
                   hover:bg-red-50 disabled:opacity-50 transition-colors"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M18.364 18.364A9 9 0 0 0 5.636 5.636m12.728 12.728A9 9 0 0 1 5.636 5.636m12.728 12.728L5.636 5.636" />
            </svg>
            {voiding ? "Voiding..." : "Void"}
          </button>
        {/if}
      </div>
    {/if}
  </div>
{/if}

<style>
  .drawer-slide-in {
    animation: drawerSlideIn 0.25s ease-out both;
  }

  @keyframes drawerSlideIn {
    from {
      transform: translateX(100%);
    }
    to {
      transform: translateX(0);
    }
  }
</style>

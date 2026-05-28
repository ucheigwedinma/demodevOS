<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import Modal from "$lib/components/Modal.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DateInput from "$lib/components/DateInput.svelte";
  import type {
    PaymentReceipt,
    PaymentReceiptListItem,
    PaymentVoucherListItem,
    VendorListItem,
    PaginatedResponse,
  } from "$lib/types";

  let data = $state<PaymentReceiptListItem[]>([]);
  let totalCount = $state(0);
  let currentPage = $state(1);
  let searchQuery = $state("");
  let statusFilter = $state("");
  let loading = $state(true);

  // Create modal
  let showCreateModal = $state(false);
  let vendors = $state<VendorListItem[]>([]);
  let vouchers = $state<PaymentVoucherListItem[]>([]);
  let createForm = $state({
    receipt_number: "",
    transaction_reference: "",
    status: "successful",
    payment_date: "",
    amount: "",
    payment_method: "bank_transfer",
    vendor: "",
    voucher: "",
    payer_account: "",
    payee_account: "",
    description: "",
    notes: "",
  });
  let createErrors = $state<Record<string, string[]>>({});
  let savingReceipt = $state(false);

  function createFieldError(field: string): string {
    return createErrors[field]?.[0] ?? "";
  }

  function resetCreateForm() {
    createForm = {
      receipt_number: "", transaction_reference: "", status: "successful",
      payment_date: "", amount: "", payment_method: "bank_transfer",
      vendor: "", voucher: "", payer_account: "", payee_account: "",
      description: "", notes: "",
    };
    createErrors = {};
  }

  const PAYMENT_METHOD_LABELS: Record<string, string> = {
    bank_transfer: "Bank Transfer", check: "Check", cash: "Cash",
    credit_card: "Credit Card", other: "Other",
  };

  async function handleCreateReceipt(e: Event) {
    e.preventDefault();
    createErrors = {};
    savingReceipt = true;
    try {
      const body: Record<string, unknown> = {
        transaction_reference: createForm.transaction_reference,
        status: createForm.status,
        payment_date: createForm.payment_date || null,
        amount: createForm.amount || null,
        payment_method: createForm.payment_method,
        vendor: createForm.vendor ? Number(createForm.vendor) : null,
        voucher: createForm.voucher ? Number(createForm.voucher) : null,
        payer_account: createForm.payer_account,
        payee_account: createForm.payee_account,
        description: createForm.description,
        notes: createForm.notes,
      };
      if (createForm.receipt_number.trim()) body.receipt_number = createForm.receipt_number.trim();

      const result = await api.post<PaymentReceipt>("/finance/payment-receipts/", body);
      toast.success("Receipt created", `${result.receipt_number} has been recorded`);
      showCreateModal = false;
      resetCreateForm();
      fetchReceipts();
    } catch (err) {
      if (err instanceof ApiError) {
        createErrors = err.fieldErrors;
        toast.error("Validation error", "Please fix the highlighted fields");
      } else {
        toast.error("Something went wrong", "Could not create the receipt");
      }
    }
    savingReceipt = false;
  }

  // Dev fill
  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  const RECEIPT_SAMPLES = [
    {
      transaction_reference: "NIP/00293847556",
      description: "Payment for cement and rebar — Phase 3 foundation works",
      amount: "4200000.00",
      payer_account: "0012345678 (Zenith Bank)",
      payee_account: "0098765432 (GTBank)",
      notes: "Settled via NIBSS Instant Payment. Ref: PV-00102.",
    },
    {
      transaction_reference: "TRF/2026031700412",
      description: "Electrical sub-contractor milestone — Block A wiring",
      amount: "1875000.00",
      payer_account: "0012345678 (Zenith Bank)",
      payee_account: "2210445567 (UBA)",
      notes: "Monthly contractor payment.",
    },
    {
      transaction_reference: "NIP/00481923004",
      description: "Site security services — March 2026",
      amount: "450000.00",
      payer_account: "0012345678 (Zenith Bank)",
      payee_account: "0045112233 (Access Bank)",
      notes: "Recurring monthly service fee.",
    },
  ];

  let devIdx = $state(0);

  function devFillReceipt() {
    const sample = RECEIPT_SAMPLES[devIdx % RECEIPT_SAMPLES.length];
    devIdx++;
    const now = new Date();
    createForm.transaction_reference = sample.transaction_reference;
    createForm.payment_date = now.toISOString().slice(0, 16);
    createForm.amount = sample.amount;
    createForm.payer_account = sample.payer_account;
    createForm.payee_account = sample.payee_account;
    createForm.description = sample.description;
    createForm.notes = sample.notes;
    createForm.status = "successful";
    createForm.payment_method = "bank_transfer";
    if (vendors.length > 0) createForm.vendor = String(vendors[devIdx % vendors.length].id);
    if (vouchers.length > 0) createForm.voucher = String(vouchers[devIdx % vouchers.length].id);
  }

  // Pagination
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

  // Fetchers
  async function fetchVendors() {
    try {
      const res = await api.get<PaginatedResponse<VendorListItem>>("/procurement/vendors/", { page_size: "200" });
      vendors = res.results;
    } catch { vendors = []; }
  }

  async function fetchVouchers() {
    try {
      const res = await api.get<PaginatedResponse<PaymentVoucherListItem>>("/finance/payment-vouchers/", { page_size: "200", status: "paid" });
      vouchers = res.results;
    } catch { vouchers = []; }
  }

  async function fetchReceipts() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage) };
      if (searchQuery) params.search = searchQuery;
      if (statusFilter) params.status = statusFilter;
      const res = await api.get<PaginatedResponse<PaymentReceiptListItem>>("/finance/payment-receipts/", params);
      data = res.results;
      totalCount = res.count;
    } catch {
      data = [];
      totalCount = 0;
    }
    loading = false;
  }

  $effect(() => { fetchVendors(); });
  $effect(() => {
    void searchQuery; void statusFilter; void currentPage;
    fetchReceipts();
  });

  let searchTimeout: ReturnType<typeof setTimeout>;
  function onSearchInput(e: Event) {
    clearTimeout(searchTimeout);
    const value = (e.target as HTMLInputElement).value;
    searchTimeout = setTimeout(() => { searchQuery = value; currentPage = 1; }, 300);
  }

  function formatCurrency(value: string | null): string {
    if (!value) return "\u2014";
    return currency.format(value);
  }

  function formatDate(value: string | null): string {
    if (!value) return "\u2014";
    return new Date(value).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  }

  function formatDateTime(value: string | null): string {
    if (!value) return "\u2014";
    return new Date(value).toLocaleString("en-US", {
      year: "numeric", month: "short", day: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  }

  // Amount in words
  function amountToWords(value: string | null): string {
    if (!value) return "";
    const num = Math.abs(parseFloat(value));
    if (isNaN(num)) return "";

    const ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
      "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"];
    const tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"];

    function chunk(n: number): string {
      if (n === 0) return "";
      if (n < 20) return ones[n];
      if (n < 100) return tens[Math.floor(n / 10)] + (n % 10 ? "-" + ones[n % 10] : "");
      return ones[Math.floor(n / 100)] + " Hundred" + (n % 100 ? " and " + chunk(n % 100) : "");
    }

    const integer = Math.floor(num);
    const kobo = Math.round((num - integer) * 100);

    if (integer === 0 && kobo === 0) return "Zero Naira Only";

    const scales = ["", " Thousand", " Million", " Billion", " Trillion"];
    let remaining = integer;
    const parts: string[] = [];
    let scaleIdx = 0;

    while (remaining > 0) {
      const seg = remaining % 1000;
      if (seg > 0) parts.unshift(chunk(seg) + scales[scaleIdx]);
      remaining = Math.floor(remaining / 1000);
      scaleIdx++;
    }

    let result = parts.join(", ") + " Naira";
    if (kobo > 0) result += ", " + chunk(kobo) + " Kobo";
    result += " Only";
    return result;
  }

  // Detail drawer
  let drawerOpen = $state(false);
  let drawerReceipt = $state<PaymentReceipt | null>(null);
  let drawerLoading = $state(false);

  async function openDrawer(id: number) {
    drawerOpen = true;
    drawerLoading = true;
    drawerReceipt = null;
    try {
      drawerReceipt = await api.get<PaymentReceipt>(`/finance/payment-receipts/${id}/`);
    } catch {
      toast.error("Not found", "Receipt could not be loaded");
      drawerOpen = false;
    }
    drawerLoading = false;
  }

  function closeDrawer() {
    drawerOpen = false;
    drawerReceipt = null;
  }

  function handlePrint() {
    window.print();
  }
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-green-600">Accounts Receivable</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Payment Receipts</h1>
      <p class="text-sm text-neutral-400 mt-1">Proof of payment records for completed transactions</p>
    </div>
    <button
      onclick={() => { showCreateModal = true; fetchVouchers(); }}
      class="px-4 py-2.5 bg-neutral-800 text-white rounded-lg hover:bg-neutral-800 text-sm font-medium transition-colors"
    >
      + New Receipt
    </button>
  </div>

  <!-- Filters -->
  <div class="flex gap-3 items-center">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
      </svg>
      <input type="text" placeholder="Search receipts..." oninput={onSearchInput}
        class="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent placeholder:text-neutral-400" />
    </div>
    <select bind:value={statusFilter} onchange={() => (currentPage = 1)}
      class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent">
      <option value="">All Statuses</option>
      <option value="successful">Successful</option>
      <option value="settled">Settled</option>
      <option value="reversed">Reversed</option>
      <option value="failed">Failed</option>
    </select>
  </div>

  <!-- Table -->
  <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
    {#if loading}
      <div class="p-16 text-center">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
        <p class="mt-3 text-sm text-neutral-400">Loading receipts...</p>
      </div>
    {:else if data.length === 0}
      <div class="p-16 text-center">
        <svg class="w-12 h-12 mx-auto text-neutral-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
        </svg>
        <p class="mt-4 text-sm font-medium text-neutral-800">No payment receipts found</p>
        <p class="mt-1 text-sm text-neutral-400">Record your first proof of payment.</p>
        <button onclick={() => { showCreateModal = true; fetchVouchers(); }}
          class="inline-block mt-4 px-4 py-2 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors">
          + New Receipt
        </button>
      </div>
    {:else}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200">
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Receipt #</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Reference</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Vendor</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Date</th>
            <th class="px-5 py-3.5 text-right font-medium text-emerald-500 text-xs uppercase tracking-wider">Amount</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each data as receipt}
            <tr class="hover:bg-neutral-50 cursor-pointer transition-colors" onclick={() => openDrawer(receipt.id)}>
              <td class="px-5 py-4"><span class="font-medium text-neutral-800">{receipt.receipt_number}</span></td>
              <td class="px-5 py-4 text-neutral-500 font-mono text-xs">{receipt.transaction_reference || "\u2014"}</td>
              <td class="px-5 py-4 text-neutral-500">{receipt.vendor_name || "\u2014"}</td>
              <td class="px-5 py-4"><StatusBadge status={receipt.status} /></td>
              <td class="px-5 py-4 text-neutral-500">{formatDate(receipt.payment_date)}</td>
              <td class="px-5 py-4 text-right tabular-nums font-semibold text-emerald-700">{formatCurrency(receipt.amount)}</td>
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
        {totalCount === 1 ? "receipt" : "receipts"}
        {#if totalPages > 1}
          <span class="mx-1.5 text-neutral-300">&middot;</span> Page <span class="font-medium text-neutral-600">{currentPage}</span> of <span class="font-medium text-neutral-600">{totalPages}</span>
        {/if}
      </p>
      {#if totalPages > 1}
        <div class="flex items-center gap-1">
          <button onclick={() => currentPage--} disabled={currentPage <= 1} class="w-9 h-9 flex items-center justify-center border border-neutral-200 rounded-lg text-neutral-500 hover:bg-neutral-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors" aria-label="Previous page">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" /></svg>
          </button>
          {#each pageNumbers(currentPage, totalPages) as pg}
            {#if pg === "..."}
              <span class="w-9 h-9 flex items-center justify-center text-xs text-neutral-300">...</span>
            {:else}
              <button onclick={() => (currentPage = pg)} class="w-9 h-9 flex items-center justify-center rounded-lg text-sm font-medium transition-colors {currentPage === pg ? 'bg-neutral-800 text-white' : 'text-neutral-500 hover:bg-neutral-100'}">
                {pg}
              </button>
            {/if}
          {/each}
          <button onclick={() => currentPage++} disabled={currentPage >= totalPages} class="w-9 h-9 flex items-center justify-center border border-neutral-200 rounded-lg text-neutral-500 hover:bg-neutral-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors" aria-label="Next page">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" /></svg>
          </button>
        </div>
      {/if}
    </div>
  {/if}
</div>

<!-- Create Modal -->
<Modal open={showCreateModal} onclose={() => { showCreateModal = false; resetCreateForm(); }} title="New Payment Receipt" maxWidth="max-w-2xl">
  <form onsubmit={handleCreateReceipt} class="space-y-5">
    <div class="grid grid-cols-2 gap-4">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Receipt Number <span class="text-neutral-400 font-normal">(auto)</span></span>
        <input type="text" bind:value={createForm.receipt_number} placeholder="Auto-generated"
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />
        {#if createFieldError("receipt_number")}<p class="mt-1 text-xs text-red-500">{createFieldError("receipt_number")}</p>{/if}
      </label>
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Transaction Reference</span>
        <input type="text" bind:value={createForm.transaction_reference} placeholder="NIP/00293847556"
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />
        {#if createFieldError("transaction_reference")}<p class="mt-1 text-xs text-red-500">{createFieldError("transaction_reference")}</p>{/if}
      </label>
    </div>

    <div class="grid grid-cols-3 gap-4">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Payment Date & Time</span>
        <input type="datetime-local" bind:value={createForm.payment_date}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />
        {#if createFieldError("payment_date")}<p class="mt-1 text-xs text-red-500">{createFieldError("payment_date")}</p>{/if}
      </label>
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Amount</span>
        <input type="text" inputmode="decimal" bind:value={createForm.amount} placeholder="0.00"
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />
        {#if createFieldError("amount")}<p class="mt-1 text-xs text-red-500">{createFieldError("amount")}</p>{/if}
      </label>
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Status</span>
        <select bind:value={createForm.status}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent">
          <option value="successful">Successful</option>
          <option value="settled">Settled</option>
          <option value="reversed">Reversed</option>
          <option value="failed">Failed</option>
        </select>
      </label>
    </div>

    <div class="grid grid-cols-2 gap-4">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Vendor</span>
        <select bind:value={createForm.vendor}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent">
          <option value="">Select vendor</option>
          {#each vendors as vendor}
            <option value={String(vendor.id)}>{vendor.name}</option>
          {/each}
        </select>
      </label>
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Payment Method</span>
        <select bind:value={createForm.payment_method}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent">
          <option value="bank_transfer">Bank Transfer</option>
          <option value="check">Check</option>
          <option value="cash">Cash</option>
          <option value="credit_card">Credit Card</option>
          <option value="other">Other</option>
        </select>
      </label>
    </div>

    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Linked Voucher <span class="text-neutral-400 font-normal">(optional)</span></span>
      <select bind:value={createForm.voucher}
        class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent">
        <option value="">None</option>
        {#each vouchers as v}
          <option value={String(v.id)}>{v.voucher_number} — {v.vendor_name}</option>
        {/each}
      </select>
    </label>

    <div class="grid grid-cols-2 gap-4">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Payer Account</span>
        <input type="text" bind:value={createForm.payer_account} placeholder="0012345678 (Zenith Bank)"
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />
      </label>
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Payee Account</span>
        <input type="text" bind:value={createForm.payee_account} placeholder="0098765432 (GTBank)"
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />
      </label>
    </div>

    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Description</span>
      <input type="text" bind:value={createForm.description} placeholder="Payment description..."
        class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />
    </label>

    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Notes <span class="text-neutral-400 font-normal">(optional)</span></span>
      <textarea bind:value={createForm.notes} rows="2" placeholder="Additional notes..."
        class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent resize-none"></textarea>
    </label>

    <div class="flex justify-end gap-3 pt-2">
      {#if isDev}
        <button type="button" onclick={devFillReceipt} class="mr-auto rounded-lg bg-orange-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-orange-600 transition-colors">Dev Fill</button>
      {/if}
      <button type="button" onclick={() => { showCreateModal = false; resetCreateForm(); }}
        class="px-4 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">Cancel</button>
      <button type="submit" disabled={savingReceipt}
        class="px-4 py-2.5 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">
        {savingReceipt ? "Creating..." : "Record Receipt"}
      </button>
    </div>
  </form>
</Modal>

<!-- Detail Drawer -->
{#if drawerOpen}
  <div class="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm transition-opacity"
    onclick={closeDrawer} onkeydown={(e) => e.key === "Escape" && closeDrawer()} role="button" tabindex="-1"></div>

  <div class="fixed inset-y-0 right-0 z-50 w-full max-w-lg bg-white shadow-2xl border-l border-neutral-200 flex flex-col drawer-slide-in">
    {#if drawerLoading}
      <div class="flex-1 flex items-center justify-center">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
        <span class="ml-3 text-sm text-neutral-400">Loading receipt...</span>
      </div>
    {:else if drawerReceipt}
      {@const r = drawerReceipt}

      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200">
        <div class="flex items-center gap-3">
          <h2 class="text-lg font-bold text-neutral-800">{r.receipt_number}</h2>
          <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold bg-emerald-100 text-emerald-800">
            {r.status.charAt(0).toUpperCase() + r.status.slice(1)}
          </span>
        </div>
        <button onclick={closeDrawer} class="w-8 h-8 flex items-center justify-center rounded-lg text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 transition-colors" aria-label="Close">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
        </button>
      </div>

      <!-- Body -->
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-6">
        <!-- Receipt header card — glassmorphic -->
        <div class="rounded-xl bg-white/60 backdrop-blur-md border border-neutral-200 shadow-lg p-5">
          <div class="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p class="text-xs text-neutral-400">Transaction Reference</p>
              <p class="mt-0.5 font-mono text-xs font-medium text-neutral-800">{r.transaction_reference || "\u2014"}</p>
            </div>
            <div>
              <p class="text-xs text-neutral-400">Timestamp</p>
              <p class="mt-0.5 font-medium text-neutral-700">{formatDateTime(r.payment_date)}</p>
            </div>
          </div>
        </div>

        <!-- Core Payment Details -->
        <div>
          <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-3">Payment Details</h3>
          <div class="rounded-xl border border-neutral-200 bg-white p-5 space-y-4">
            <!-- Amount -->
            <div class="text-center pb-4 border-b border-neutral-100">
              <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider mb-1">Amount Paid</p>
              <p class="text-3xl font-bold text-emerald-700 tabular-nums" style="font-family: 'Raleway', sans-serif; font-weight: 700;">
                {currency.format(r.amount)}
              </p>
              <p class="mt-1.5 text-xs text-neutral-500 italic leading-relaxed">{amountToWords(r.amount)}</p>
            </div>

            <dl class="space-y-3 text-sm">
              <!-- Payee -->
              <div>
                <dt class="text-neutral-400">Payee Name</dt>
                <dd class="mt-0.5 text-base font-semibold text-neutral-800">{r.vendor_name || "\u2014"}</dd>
              </div>

              <!-- Payment Method -->
              <div>
                <dt class="text-neutral-400">Payment Method</dt>
                <dd class="mt-0.5 font-medium text-neutral-800">{PAYMENT_METHOD_LABELS[r.payment_method] ?? r.payment_method}</dd>
              </div>

              <!-- Source Account -->
              <div>
                <dt class="text-neutral-400">Source Account</dt>
                <dd class="mt-0.5 text-neutral-700 font-mono text-xs">{r.payer_account || "\u2014"}</dd>
              </div>

              <!-- Destination Account -->
              {#if r.payee_account}
                <div>
                  <dt class="text-neutral-400">Destination Account</dt>
                  <dd class="mt-0.5 text-neutral-700 font-mono text-xs">{r.payee_account}</dd>
                </div>
              {/if}
            </dl>
          </div>
        </div>

        <!-- Allocation Table -->
        {#if r.allocation_items.length > 0}
          <div>
            <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-3">Allocation</h3>
            <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
              <table class="w-full text-sm">
                <thead>
                  <tr class="border-b border-neutral-200 bg-neutral-50">
                    <th class="px-4 py-2.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Voucher Ref</th>
                    <th class="px-4 py-2.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Project Location</th>
                    <th class="px-4 py-2.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Description</th>
                    <th class="px-4 py-2.5 text-right font-medium text-emerald-500 text-xs uppercase tracking-wider">Amount</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-neutral-100">
                  {#each r.allocation_items as item}
                    <tr class="hover:bg-neutral-50 transition-colors">
                      <td class="px-4 py-3 font-medium text-neutral-800 font-mono text-xs">{item.voucher_number}</td>
                      <td class="px-4 py-3 text-neutral-500 text-xs">{item.property_name || "\u2014"}</td>
                      <td class="px-4 py-3 text-neutral-500 text-xs truncate max-w-[140px]">{item.description || "\u2014"}</td>
                      <td class="px-4 py-3 text-right tabular-nums font-semibold text-emerald-700 text-xs">{formatCurrency(item.amount)}</td>
                    </tr>
                  {/each}
                </tbody>
                <tfoot>
                  <tr class="border-t border-neutral-200 bg-neutral-50">
                    <td class="px-4 py-2.5 font-semibold text-neutral-800 text-xs" colspan="3">Total</td>
                    <td class="px-4 py-2.5 text-right tabular-nums font-bold text-emerald-700 text-xs">
                      {formatCurrency(String(r.allocation_items.reduce((sum, v) => sum + Number(v.amount || 0), 0).toFixed(2)))}
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        {/if}

        <!-- Linked References -->
        <div>
          <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-3">References</h3>
          <dl class="space-y-2.5 text-sm">
            {#if r.voucher_number}
              <div>
                <dt class="text-neutral-400">Linked Voucher</dt>
                <dd class="mt-0.5 font-medium text-neutral-800">{r.voucher_number}</dd>
              </div>
            {/if}
            {#if r.payment_run_batch_id}
              <div>
                <dt class="text-neutral-400">Payment Run</dt>
                <dd class="mt-0.5 font-medium text-neutral-800">{r.payment_run_batch_id}</dd>
              </div>
            {/if}
            <div>
              <dt class="text-neutral-400">Recorded By</dt>
              <dd class="mt-0.5 text-neutral-700">{r.created_by_name || "\u2014"}</dd>
            </div>
            {#if r.description}
              <div>
                <dt class="text-neutral-400">Description</dt>
                <dd class="mt-0.5 text-neutral-700">{r.description}</dd>
              </div>
            {/if}
            {#if r.notes}
              <div>
                <dt class="text-neutral-400">Notes</dt>
                <dd class="mt-0.5 text-neutral-500 text-xs leading-relaxed">{r.notes}</dd>
              </div>
            {/if}
          </dl>
        </div>

        <!-- Security & Audit -->
        <div>
          <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-3">Security & Audit</h3>
          <div class="rounded-xl border border-neutral-200 bg-white p-5 space-y-5 relative overflow-hidden">
            <!-- "PAID" watermark -->
            <div class="absolute inset-0 flex items-center justify-center pointer-events-none select-none" aria-hidden="true">
              <span class="text-[72px] font-black text-emerald-500/6 uppercase tracking-[12px] -rotate-20">Paid</span>
            </div>

            <div class="relative z-10 space-y-5">
              <!-- QR Code -->
              <div>
                <p class="text-xs text-neutral-400 mb-2">Verification QR Code</p>
                <div class="inline-flex items-center gap-3">
                  <div class="w-20 h-20 bg-neutral-50 border border-neutral-200 rounded-lg flex items-center justify-center">
                    {#if r.receipt_number}
                      <svg viewBox="0 0 100 100" class="w-16 h-16">
                        <!-- Simplified QR pattern generated from receipt number -->
                        <rect width="100" height="100" fill="white"/>
                        <!-- Position markers -->
                        <rect x="4" y="4" width="24" height="24" fill="#111"/>
                        <rect x="8" y="8" width="16" height="16" fill="white"/>
                        <rect x="12" y="12" width="8" height="8" fill="#111"/>
                        <rect x="72" y="4" width="24" height="24" fill="#111"/>
                        <rect x="76" y="8" width="16" height="16" fill="white"/>
                        <rect x="80" y="12" width="8" height="8" fill="#111"/>
                        <rect x="4" y="72" width="24" height="24" fill="#111"/>
                        <rect x="8" y="76" width="16" height="16" fill="white"/>
                        <rect x="12" y="80" width="8" height="8" fill="#111"/>
                        <!-- Data pattern -->
                        <rect x="36" y="4" width="4" height="4" fill="#111"/>
                        <rect x="44" y="4" width="4" height="4" fill="#111"/>
                        <rect x="56" y="4" width="4" height="4" fill="#111"/>
                        <rect x="36" y="12" width="4" height="4" fill="#111"/>
                        <rect x="48" y="12" width="4" height="4" fill="#111"/>
                        <rect x="60" y="12" width="4" height="4" fill="#111"/>
                        <rect x="36" y="20" width="4" height="4" fill="#111"/>
                        <rect x="52" y="20" width="4" height="4" fill="#111"/>
                        <rect x="36" y="36" width="4" height="4" fill="#111"/>
                        <rect x="44" y="40" width="4" height="4" fill="#111"/>
                        <rect x="52" y="36" width="4" height="4" fill="#111"/>
                        <rect x="60" y="44" width="4" height="4" fill="#111"/>
                        <rect x="68" y="36" width="4" height="4" fill="#111"/>
                        <rect x="40" y="52" width="4" height="4" fill="#111"/>
                        <rect x="52" y="56" width="4" height="4" fill="#111"/>
                        <rect x="64" y="52" width="4" height="4" fill="#111"/>
                        <rect x="76" y="56" width="4" height="4" fill="#111"/>
                        <rect x="84" y="48" width="4" height="4" fill="#111"/>
                        <rect x="36" y="64" width="4" height="4" fill="#111"/>
                        <rect x="48" y="68" width="4" height="4" fill="#111"/>
                        <rect x="60" y="64" width="4" height="4" fill="#111"/>
                        <rect x="36" y="76" width="4" height="4" fill="#111"/>
                        <rect x="44" y="80" width="4" height="4" fill="#111"/>
                        <rect x="56" y="76" width="4" height="4" fill="#111"/>
                        <rect x="68" y="80" width="4" height="4" fill="#111"/>
                        <rect x="76" y="76" width="4" height="4" fill="#111"/>
                        <rect x="84" y="72" width="4" height="4" fill="#111"/>
                        <rect x="88" y="84" width="4" height="4" fill="#111"/>
                        <rect x="80" y="88" width="4" height="4" fill="#111"/>
                        <rect x="72" y="92" width="4" height="4" fill="#111"/>
                      </svg>
                    {/if}
                  </div>
                  <div>
                    <p class="text-xs text-neutral-500">Scan to verify this receipt</p>
                    <p class="text-xs text-neutral-400 font-mono mt-0.5">{r.receipt_number}</p>
                  </div>
                </div>
              </div>

              <!-- Digital Signature -->
              <div class="pt-4 border-t border-neutral-100">
                <p class="text-xs text-neutral-400 mb-3">Authorized By</p>
                <div class="flex items-end gap-4">
                  <div class="flex-1">
                    <div class="h-12 border-b-2 border-neutral-300 flex items-end pb-1">
                      {#if r.created_by_name}
                        <span class="text-lg text-neutral-700 italic" style="font-family: 'Georgia', serif;">{r.created_by_name}</span>
                      {:else}
                        <span class="text-xs text-neutral-300 italic">Signature</span>
                      {/if}
                    </div>
                    <p class="text-xs text-neutral-400 mt-1">Digital Signature</p>
                  </div>
                  <div class="text-right">
                    <p class="text-xs text-neutral-700 font-medium">{formatDate(r.created_at)}</p>
                    <p class="text-xs text-neutral-400">Date</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Footer actions -->
      <div class="px-6 py-4 border-t border-neutral-200 flex items-center gap-2">
        <button onclick={handlePrint}
          class="inline-flex items-center gap-1.5 px-4 py-2.5 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6.72 13.829c-.24.03-.48.062-.72.096m.72-.096a42.415 42.415 0 0 1 10.56 0m-10.56 0L6.34 18m10.94-4.171c.24.03.48.062.72.096m-.72-.096L17.66 18m0 0 .229 2.523a1.125 1.125 0 0 1-1.12 1.227H7.231c-.662 0-1.18-.568-1.12-1.227L6.34 18m11.318 0h1.091A2.25 2.25 0 0 0 21 15.75V9.456c0-1.081-.768-2.015-1.837-2.175a48.055 48.055 0 0 0-1.913-.247M6.34 18H5.25A2.25 2.25 0 0 1 3 15.75V9.456c0-1.081.768-2.015 1.837-2.175a48.041 48.041 0 0 1 1.913-.247m10.5 0a48.536 48.536 0 0 0-10.5 0m10.5 0V3.375c0-.621-.504-1.125-1.125-1.125h-8.25c-.621 0-1.125.504-1.125 1.125v3.659M18 10.5h.008v.008H18V10.5Zm-3 0h.008v.008H15V10.5Z" />
          </svg>
          Print
        </button>

        <button onclick={() => toast.info("Coming soon", "PDF download will be available shortly")}
          class="inline-flex items-center gap-1.5 px-4 py-2.5 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
          </svg>
          Download PDF
        </button>

        <button onclick={() => toast.info("Coming soon", "Email integration will be available shortly")}
          class="ml-auto inline-flex items-center gap-1.5 px-4 py-2.5 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25h-15a2.25 2.25 0 0 1-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0L3.32 8.91a2.25 2.25 0 0 1-1.07-1.916V6.75" />
          </svg>
          Email to Vendor
        </button>
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

  @media print {
    /* Hide everything except the drawer */
    :global(body > *:not(.drawer-slide-in)),
    :global(nav),
    :global(aside),
    :global(header) {
      display: none !important;
    }

    /* Make drawer fill the page */
    .drawer-slide-in {
      position: static !important;
      width: 100% !important;
      max-width: 100% !important;
      height: auto !important;
      border: none !important;
      box-shadow: none !important;
      animation: none !important;
    }

    /* Strip glassmorphism, blurs, shadows, backgrounds */
    :global(.backdrop-blur-sm),
    :global(.backdrop-blur-md) {
      backdrop-filter: none !important;
      -webkit-backdrop-filter: none !important;
      background: transparent !important;
    }

    .drawer-slide-in :global([class*="shadow"]) {
      box-shadow: none !important;
    }

    .drawer-slide-in :global([class*="backdrop-blur"]) {
      backdrop-filter: none !important;
      -webkit-backdrop-filter: none !important;
      background: white !important;
    }

    .drawer-slide-in :global([class*="bg-white/60"]) {
      background: white !important;
    }

    .drawer-slide-in :global([class*="bg-emerald"]) {
      background: transparent !important;
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }

    /* Hide footer action buttons */
    .drawer-slide-in > div:last-child {
      display: none !important;
    }

    /* Hide backdrop overlay */
    :global(.fixed.inset-0.z-40) {
      display: none !important;
    }

    /* Keep the PAID watermark and QR visible */
    .drawer-slide-in :global([class*="text-emerald-500"]) {
      -webkit-print-color-adjust: exact;
      print-color-adjust: exact;
    }
  }
</style>

<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import Modal from "$lib/components/Modal.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DateInput from "$lib/components/DateInput.svelte";
  import type {
    PaymentRun,
    PaymentRunListItem,
    PaymentVoucherListItem,
    AccountListItem,
    PropertyListItem,
    PaginatedResponse,
  } from "$lib/types";

  let data = $state<PaymentRunListItem[]>([]);
  let totalCount = $state(0);
  let currentPage = $state(1);
  let searchQuery = $state("");
  let statusFilter = $state("");
  let loading = $state(true);

  // Create modal
  let showCreateModal = $state(false);
  let accounts = $state<AccountListItem[]>([]);
  let properties = $state<PropertyListItem[]>([]);
  let approvedVouchers = $state<PaymentVoucherListItem[]>([]);
  let selectedVoucherIds = $state<Set<number>>(new Set());
  let heldVoucherIds = $state<Set<number>>(new Set());
  let createForm = $state({
    batch_id: "",
    funding_account: "",
    funding_account_label: "",
    scheduled_date: "",
    notes: "",
  });
  let createErrors = $state<Record<string, string[]>>({});
  let savingRun = $state(false);

  // Voucher filter state
  let voucherDateFrom = $state("");
  let voucherDateTo = $state("");
  let voucherPropertyFilter = $state("");
  let voucherPriorityFilter = $state<"" | "high" | "standard">("");

  // Filtered vouchers (excludes held)
  const filteredVouchers = $derived(() => {
    let list = approvedVouchers.filter((v) => !heldVoucherIds.has(v.id));
    if (voucherDateFrom) list = list.filter((v) => v.issue_date >= voucherDateFrom);
    if (voucherDateTo) list = list.filter((v) => v.issue_date <= voucherDateTo);
    if (voucherPropertyFilter) list = list.filter((v) => String(v.property_id) === voucherPropertyFilter);
    if (voucherPriorityFilter) list = list.filter((v) => v.priority === voucherPriorityFilter);
    return list;
  });

  // Unique properties from loaded vouchers for filter dropdown
  const voucherProperties = $derived(() => {
    const seen = new Map<number, string>();
    for (const v of approvedVouchers) {
      if (v.property_id && v.property_name && !seen.has(v.property_id)) {
        seen.set(v.property_id, v.property_name);
      }
    }
    return [...seen.entries()].map(([id, name]) => ({ id, name }));
  });

  function createFieldError(field: string): string {
    return createErrors[field]?.[0] ?? "";
  }

  function resetCreateForm() {
    createForm = { batch_id: "", funding_account: "", funding_account_label: "", scheduled_date: "", notes: "" };
    createErrors = {};
    selectedVoucherIds = new Set();
    heldVoucherIds = new Set();
    voucherDateFrom = "";
    voucherDateTo = "";
    voucherPropertyFilter = "";
    voucherPriorityFilter = "";
  }

  function toggleVoucher(id: number) {
    const next = new Set(selectedVoucherIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    selectedVoucherIds = next;
  }

  function selectAllFiltered() {
    const ids = filteredVouchers().map((v) => v.id);
    selectedVoucherIds = new Set([...selectedVoucherIds, ...ids]);
  }

  function deselectAllFiltered() {
    const ids = new Set(filteredVouchers().map((v) => v.id));
    selectedVoucherIds = new Set([...selectedVoucherIds].filter((id) => !ids.has(id)));
  }

  function excludeSelected() {
    // Move selected items to the held set
    for (const id of selectedVoucherIds) {
      heldVoucherIds = new Set([...heldVoucherIds, id]);
    }
    selectedVoucherIds = new Set();
  }

  function holdVoucher(id: number) {
    heldVoucherIds = new Set([...heldVoucherIds, id]);
    const next = new Set(selectedVoucherIds);
    next.delete(id);
    selectedVoucherIds = next;
  }

  function unholdVoucher(id: number) {
    const next = new Set(heldVoucherIds);
    next.delete(id);
    heldVoucherIds = next;
  }

  function clearAllHolds() {
    heldVoucherIds = new Set();
  }

  const selectedTotal = $derived(
    approvedVouchers
      .filter((v) => selectedVoucherIds.has(v.id))
      .reduce((sum, v) => sum + Number(v.amount || 0), 0)
  );

  const heldVouchers = $derived(approvedVouchers.filter((v) => heldVoucherIds.has(v.id)));

  async function handleCreateRun(e: Event) {
    e.preventDefault();
    createErrors = {};
    savingRun = true;
    try {
      const body: Record<string, unknown> = {
        funding_account: createForm.funding_account ? Number(createForm.funding_account) : null,
        funding_account_label: createForm.funding_account_label,
        scheduled_date: createForm.scheduled_date || null,
        notes: createForm.notes,
        voucher_ids: [...selectedVoucherIds],
      };
      if (createForm.batch_id.trim()) body.batch_id = createForm.batch_id.trim();

      const result = await api.post<PaymentRun>("/finance/payment-runs/", body);
      toast.success("Run created", `"${result.batch_id}" has been created with ${result.payment_count} vouchers`);
      showCreateModal = false;
      resetCreateForm();
      fetchRuns();
    } catch (err) {
      if (err instanceof ApiError) {
        createErrors = err.fieldErrors;
        toast.error("Validation error", "Please fix the highlighted fields");
      } else {
        toast.error("Something went wrong", "Could not create the payment run");
      }
    }
    savingRun = false;
  }

  // Dev fill
  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  function devFillRun() {
    const today = new Date().toISOString().slice(0, 10);
    createForm.funding_account_label = "Main Operations - Zenith Bank";
    createForm.scheduled_date = today;
    createForm.notes = "Monthly vendor disbursement batch — March 2026";
    if (accounts.length > 0) {
      createForm.funding_account = String(accounts[0].id);
    }
    // Select all filtered vouchers
    selectedVoucherIds = new Set(filteredVouchers().map((v) => v.id));
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
  async function fetchAccounts() {
    try {
      const res = await api.get<PaginatedResponse<AccountListItem>>("/finance/accounts/", { page_size: "200", account_type: "asset" });
      accounts = res.results;
    } catch { accounts = []; }
  }

  async function fetchProperties() {
    try {
      const res = await api.get<PaginatedResponse<PropertyListItem>>("/properties/", { page_size: "200" });
      properties = res.results;
    } catch { properties = []; }
  }

  async function fetchApprovedVouchers() {
    try {
      const res = await api.get<PaginatedResponse<PaymentVoucherListItem>>("/finance/payment-vouchers/", { page_size: "200", status: "approved" });
      approvedVouchers = res.results;
    } catch { approvedVouchers = []; }
  }

  async function fetchRuns() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage) };
      if (searchQuery) params.search = searchQuery;
      if (statusFilter) params.status = statusFilter;
      const res = await api.get<PaginatedResponse<PaymentRunListItem>>("/finance/payment-runs/", params);
      data = res.results;
      totalCount = res.count;
    } catch {
      data = [];
      totalCount = 0;
    }
    loading = false;
  }

  $effect(() => { fetchAccounts(); });
  $effect(() => {
    void searchQuery; void statusFilter; void currentPage;
    fetchRuns();
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

  // Detail drawer
  let drawerOpen = $state(false);
  let drawerRun = $state<PaymentRun | null>(null);
  let drawerLoading = $state(false);
  let executing = $state(false);
  let cancelling = $state(false);
  let showExecuteConfirm = $state(false);
  let executeConfirmText = $state("");

  async function openDrawer(id: number) {
    drawerOpen = true;
    drawerLoading = true;
    drawerRun = null;
    try {
      drawerRun = await api.get<PaymentRun>(`/finance/payment-runs/${id}/`);
    } catch {
      toast.error("Not found", "Payment run could not be loaded");
      drawerOpen = false;
    }
    drawerLoading = false;
  }

  function closeDrawer() {
    drawerOpen = false;
    drawerRun = null;
  }

  async function handleExecute() {
    if (!drawerRun) return;
    executing = true;
    try {
      await api.post(`/finance/payment-runs/${drawerRun.id}/execute/`, {});
      toast.success("Executed", "Payment run has been executed and vouchers marked as paid");
      drawerRun = await api.get<PaymentRun>(`/finance/payment-runs/${drawerRun.id}/`);
      fetchRuns();
    } catch {
      toast.error("Error", "Could not execute this payment run");
    }
    executing = false;
  }

  let approving = $state(false);
  let balanceInput = $state("");

  const fundingSufficient = $derived(() => {
    if (!drawerRun || !balanceInput) return null;
    const balance = Number(balanceInput);
    const total = Number(drawerRun.total_value);
    if (isNaN(balance) || isNaN(total)) return null;
    return balance >= total;
  });

  async function handleApprove() {
    if (!drawerRun) return;
    approving = true;
    try {
      const body: Record<string, unknown> = {};
      if (balanceInput) body.funding_balance = balanceInput;
      await api.post(`/finance/payment-runs/${drawerRun.id}/approve/`, body);
      toast.success("Approved", "Payment run has been signed off");
      drawerRun = await api.get<PaymentRun>(`/finance/payment-runs/${drawerRun.id}/`);
      fetchRuns();
    } catch {
      toast.error("Error", "Could not approve this payment run");
    }
    approving = false;
  }

  function handleExportCSV() {
    if (!drawerRun) return;
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    const url = `/api/finance/payment-runs/${drawerRun.id}/export-csv/`;
    // Open in new tab with auth header via fetch + blob download
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => {
        if (!res.ok) throw new Error("Export failed");
        return res.blob();
      })
      .then((blob) => {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `${drawerRun!.batch_id}.csv`;
        a.click();
        URL.revokeObjectURL(a.href);
        toast.success("Exported", "Bank file downloaded");
      })
      .catch(() => toast.error("Error", "Could not export bank file"));
  }

  async function handleRemoveVoucher(voucherId: number) {
    if (!drawerRun) return;
    try {
      await api.post(`/finance/payment-runs/${drawerRun.id}/remove-voucher/`, { voucher_id: voucherId });
      toast.success("Removed", "Voucher removed from this run");
      drawerRun = await api.get<PaymentRun>(`/finance/payment-runs/${drawerRun.id}/`);
      fetchRuns();
    } catch {
      toast.error("Error", "Could not remove voucher from this run");
    }
  }

  async function handleCancel() {
    if (!drawerRun) return;
    cancelling = true;
    try {
      await api.post(`/finance/payment-runs/${drawerRun.id}/cancel/`, {});
      toast.success("Cancelled", "Payment run has been cancelled");
      drawerRun = await api.get<PaymentRun>(`/finance/payment-runs/${drawerRun.id}/`);
      fetchRuns();
    } catch {
      toast.error("Error", "Could not cancel this payment run");
    }
    cancelling = false;
  }
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-green-600">Accounts Payable</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Payment Runs</h1>
      <p class="text-sm text-neutral-400 mt-1">Batch approved vouchers for simultaneous disbursement</p>
    </div>
    <button
      onclick={() => { showCreateModal = true; fetchApprovedVouchers(); fetchProperties(); }}
      class="px-4 py-2.5 bg-neutral-800 text-white rounded-lg hover:bg-neutral-800 text-sm font-medium transition-colors"
    >
      + New Payment Run
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
        placeholder="Search payment runs..."
        oninput={onSearchInput}
        class="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
               focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent placeholder:text-neutral-400"
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
      <option value="scheduled">Scheduled</option>
      <option value="processing">Processing</option>
      <option value="completed">Completed</option>
      <option value="failed">Failed</option>
      <option value="cancelled">Cancelled</option>
    </select>
  </div>

  <!-- Table -->
  <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
    {#if loading}
      <div class="p-16 text-center">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
        <p class="mt-3 text-sm text-neutral-400">Loading payment runs...</p>
      </div>
    {:else if data.length === 0}
      <div class="p-16 text-center">
        <svg class="w-12 h-12 mx-auto text-neutral-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1">
          <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z" />
        </svg>
        <p class="mt-4 text-sm font-medium text-neutral-800">No payment runs found</p>
        <p class="mt-1 text-sm text-neutral-400">Create a payment run to batch approved vouchers for disbursement.</p>
        <button
          onclick={() => { showCreateModal = true; fetchApprovedVouchers(); fetchProperties(); }}
          class="inline-block mt-4 px-4 py-2 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors"
        >
          + New Payment Run
        </button>
      </div>
    {:else}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200">
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Batch ID</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
            <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Vouchers</th>
            <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Total Value</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Funding Account</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Scheduled</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Created</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each data as run}
            <tr
              class="hover:bg-neutral-50 cursor-pointer transition-colors"
              onclick={() => openDrawer(run.id)}
            >
              <td class="px-5 py-4">
                <span class="font-medium text-neutral-800">{run.batch_id}</span>
              </td>
              <td class="px-5 py-4"><StatusBadge status={run.status} /></td>
              <td class="px-5 py-4 text-right text-neutral-500 tabular-nums">{run.payment_count}</td>
              <td class="px-5 py-4 text-right text-neutral-800 tabular-nums font-medium">{formatCurrency(run.total_value)}</td>
              <td class="px-5 py-4 text-neutral-500">{run.funding_account_label || run.funding_account_name || "\u2014"}</td>
              <td class="px-5 py-4 text-neutral-500">{formatDate(run.scheduled_date)}</td>
              <td class="px-5 py-4 text-neutral-500">{formatDate(run.created_at)}</td>
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
        {totalCount === 1 ? "run" : "runs"}
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
<Modal open={showCreateModal} onclose={() => { showCreateModal = false; resetCreateForm(); }} title="New Payment Run" maxWidth="max-w-2xl">
  <form onsubmit={handleCreateRun} class="space-y-5">
    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Batch ID <span class="text-neutral-400 font-normal">(auto-generated if blank)</span></span>
      <input type="text" bind:value={createForm.batch_id} placeholder="Auto-generated" class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />
      {#if createFieldError("batch_id")}<p class="mt-1 text-xs text-red-500">{createFieldError("batch_id")}</p>{/if}
    </label>

    <div class="grid grid-cols-2 gap-4">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Funding Account</span>
        <select bind:value={createForm.funding_account} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent">
          <option value="">Select account</option>
          {#each accounts as account}
            <option value={String(account.id)}>{account.code} — {account.name}</option>
          {/each}
        </select>
      </label>
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Account Label</span>
        <input type="text" bind:value={createForm.funding_account_label} placeholder="e.g. Main Operations - Zenith Bank" class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />
      </label>
    </div>

    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Scheduled Date <span class="text-neutral-400 font-normal">(optional)</span></span>
      <DateInput bind:value={createForm.scheduled_date} />
    </label>

    <!-- Selection & Filter Console -->
    <div class="space-y-3">
      <div class="flex items-center justify-between">
        <span class="text-sm font-medium text-neutral-700">Selection & Filter Console</span>
        {#if selectedVoucherIds.size > 0}
          <span class="text-xs font-medium text-neutral-500">{selectedVoucherIds.size} selected &middot; {currency.format(String(selectedTotal.toFixed(2)))}</span>
        {/if}
      </div>

      <!-- Filters row -->
      <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
        <div class="grid grid-cols-4 gap-2">
          <label>
            <span class="block text-xs font-medium text-neutral-500 mb-1">Date From</span>
            <DateInput bind:value={voucherDateFrom} />
          </label>
          <label>
            <span class="block text-xs font-medium text-neutral-500 mb-1">Date To</span>
            <DateInput bind:value={voucherDateTo} />
          </label>
          <label>
            <span class="block text-xs font-medium text-neutral-500 mb-1">Project / Property</span>
            <select bind:value={voucherPropertyFilter} class="w-full px-2.5 py-2 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent">
              <option value="">All Projects</option>
              {#each voucherProperties() as prop}
                <option value={String(prop.id)}>{prop.name}</option>
              {/each}
            </select>
          </label>
          <label>
            <span class="block text-xs font-medium text-neutral-500 mb-1">Priority</span>
            <select bind:value={voucherPriorityFilter} class="w-full px-2.5 py-2 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent">
              <option value="">All Priorities</option>
              <option value="high">High Priority</option>
              <option value="standard">Standard</option>
            </select>
          </label>
        </div>

        <!-- Bulk actions -->
        <div class="flex items-center gap-2 mt-2 pt-2 border-t border-neutral-200">
          <button type="button" onclick={selectAllFiltered} class="px-2.5 py-1.5 text-xs font-medium text-neutral-700 bg-white border border-neutral-200 rounded-md hover:bg-neutral-100 transition-colors">
            Select All
          </button>
          <button type="button" onclick={deselectAllFiltered} class="px-2.5 py-1.5 text-xs font-medium text-neutral-700 bg-white border border-neutral-200 rounded-md hover:bg-neutral-100 transition-colors">
            Deselect All
          </button>
          {#if selectedVoucherIds.size > 0}
            <button type="button" onclick={excludeSelected} class="px-2.5 py-1.5 text-xs font-medium text-amber-700 bg-amber-50 border border-amber-200 rounded-md hover:bg-amber-100 transition-colors">
              Exclude Selected ({selectedVoucherIds.size})
            </button>
          {/if}
          <span class="ml-auto text-xs text-neutral-400">{filteredVouchers().length} voucher{filteredVouchers().length !== 1 ? "s" : ""} shown</span>
        </div>
      </div>

      <!-- Voucher table -->
      {#if approvedVouchers.length === 0}
        <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-6 text-center">
          <p class="text-sm text-neutral-400">No approved vouchers available for batching.</p>
        </div>
      {:else if filteredVouchers().length === 0}
        <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-6 text-center">
          <p class="text-sm text-neutral-400">No vouchers match the current filters.</p>
        </div>
      {:else}
        <div class="rounded-lg border border-neutral-200 overflow-hidden max-h-56 overflow-y-auto">
          <table class="w-full text-sm">
            <thead class="sticky top-0 bg-neutral-50">
              <tr class="border-b border-neutral-200">
                <th class="px-3 py-2.5 text-left w-10">
                  <input type="checkbox" checked={filteredVouchers().every((v) => selectedVoucherIds.has(v.id)) && filteredVouchers().length > 0} onchange={() => filteredVouchers().every((v) => selectedVoucherIds.has(v.id)) ? deselectAllFiltered() : selectAllFiltered()} class="rounded border-neutral-300" />
                </th>
                <th class="px-3 py-2.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Voucher</th>
                <th class="px-3 py-2.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Vendor</th>
                <th class="px-3 py-2.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Project</th>
                <th class="px-3 py-2.5 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Priority</th>
                <th class="px-3 py-2.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Amount</th>
                <th class="px-3 py-2.5 w-10"></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each filteredVouchers() as voucher}
                <tr class="hover:bg-neutral-50 transition-colors cursor-pointer" onclick={() => toggleVoucher(voucher.id)}>
                  <td class="px-3 py-2.5">
                    <input type="checkbox" checked={selectedVoucherIds.has(voucher.id)} onchange={() => toggleVoucher(voucher.id)} onclick={(e) => e.stopPropagation()} class="rounded border-neutral-300" />
                  </td>
                  <td class="px-3 py-2.5 font-medium text-neutral-800 text-xs">{voucher.voucher_number}</td>
                  <td class="px-3 py-2.5 text-neutral-500 text-xs">{voucher.vendor_name}</td>
                  <td class="px-3 py-2.5 text-neutral-500 text-xs">{voucher.property_name || "\u2014"}</td>
                  <td class="px-3 py-2.5 text-center">
                    {#if voucher.priority === "high"}
                      <span class="inline-block w-2 h-2 rounded-full bg-red-500" title="High priority"></span>
                    {:else}
                      <span class="inline-block w-2 h-2 rounded-full bg-neutral-300" title="Standard"></span>
                    {/if}
                  </td>
                  <td class="px-3 py-2.5 text-right text-neutral-800 tabular-nums text-xs font-medium">{formatCurrency(voucher.amount)}</td>
                  <td class="px-3 py-2.5 text-right">
                    <button type="button" onclick={(e) => { e.stopPropagation(); holdVoucher(voucher.id); }} class="text-xs text-neutral-400 hover:text-amber-600 transition-colors" title="Hold payment">
                      Hold
                    </button>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}

      <!-- Held vouchers -->
      {#if heldVouchers.length > 0}
        <div class="rounded-lg border border-amber-200 bg-amber-50 p-3">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-semibold text-amber-800">Held Payments ({heldVouchers.length})</span>
            <button type="button" onclick={clearAllHolds} class="text-xs text-amber-600 hover:text-amber-800 font-medium transition-colors">Release All</button>
          </div>
          <div class="flex flex-wrap gap-1.5">
            {#each heldVouchers as voucher}
              <span class="inline-flex items-center gap-1 rounded-md bg-white border border-amber-200 px-2 py-1 text-xs text-neutral-700">
                {voucher.voucher_number}
                <button type="button" onclick={() => unholdVoucher(voucher.id)} class="text-amber-400 hover:text-amber-700 transition-colors" aria-label="Release">
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
                </button>
              </span>
            {/each}
          </div>
        </div>
      {/if}
    </div>

    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Notes <span class="text-neutral-400 font-normal">(optional)</span></span>
      <textarea bind:value={createForm.notes} rows="2" placeholder="Additional notes..." class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent resize-none"></textarea>
    </label>

    <div class="flex justify-end gap-3 pt-2">
      {#if isDev}
        <button type="button" onclick={devFillRun} class="mr-auto rounded-lg bg-orange-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-orange-600 transition-colors">Dev Fill</button>
      {/if}
      <button type="button" onclick={() => { showCreateModal = false; resetCreateForm(); }} class="px-4 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">Cancel</button>
      <button type="submit" disabled={savingRun || selectedVoucherIds.size === 0} class="px-4 py-2.5 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">
        {savingRun ? "Creating..." : `Create Run (${selectedVoucherIds.size} vouchers)`}
      </button>
    </div>
  </form>
</Modal>

<!-- Detail Drawer -->
{#if drawerOpen}
  <div
    class="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm transition-opacity"
    onclick={closeDrawer}
    onkeydown={(e) => e.key === "Escape" && closeDrawer()}
    role="button"
    tabindex="-1"
  ></div>

  <div class="fixed inset-y-0 right-0 z-50 w-full max-w-lg bg-white shadow-2xl border-l border-neutral-200 flex flex-col drawer-slide-in">
    {#if drawerLoading}
      <div class="flex-1 flex items-center justify-center">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
        <span class="ml-3 text-sm text-neutral-400">Loading run...</span>
      </div>
    {:else if drawerRun}
      {@const r = drawerRun}

      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200">
        <div class="flex items-center gap-3">
          <h2 class="text-lg font-bold text-neutral-800">{r.batch_id}</h2>
          <StatusBadge status={r.status} size="md" />
        </div>
        <button onclick={closeDrawer} class="w-8 h-8 flex items-center justify-center rounded-lg text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 transition-colors" aria-label="Close">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
        </button>
      </div>

      <!-- Body -->
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-6">
        <!-- Batch summary — glassmorphic -->
        <div class="rounded-xl bg-white/60 backdrop-blur-md border border-neutral-200 shadow-lg p-5">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider mb-1">Total Value</p>
              <p class="text-xl font-bold text-neutral-800 tabular-nums">{currency.format(String(r.total_value))}</p>
            </div>
            <div>
              <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider mb-1">Payment Count</p>
              <p class="text-xl font-bold text-neutral-800 tabular-nums">{r.payment_count}</p>
            </div>
            <div>
              <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider mb-1">Funding Account</p>
              <p class="text-sm font-medium text-neutral-700">{r.funding_account_label || r.funding_account_name || "\u2014"}</p>
            </div>
            <div>
              <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider mb-1">Scheduled</p>
              <p class="text-sm font-medium text-neutral-700">{formatDate(r.scheduled_date)}</p>
            </div>
          </div>
        </div>

        <!-- Run details -->
        <div>
          <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-3">Details</h3>
          <dl class="space-y-2.5 text-sm">
            {#if r.created_by_name}
              <div>
                <dt class="text-neutral-400">Created By</dt>
                <dd class="mt-0.5 text-neutral-700">{r.created_by_name}</dd>
              </div>
            {/if}
            <div>
              <dt class="text-neutral-400">Created</dt>
              <dd class="mt-0.5 text-neutral-700">{formatDate(r.created_at)}</dd>
            </div>
            {#if r.executed_at}
              <div>
                <dt class="text-neutral-400">Executed</dt>
                <dd class="mt-0.5 text-neutral-700">{formatDate(r.executed_at)}{r.executed_by_name ? ` by ${r.executed_by_name}` : ""}</dd>
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

        <!-- Batch Table (Workspace) -->
        <div>
          <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-3">Batch Table ({r.voucher_items.length})</h3>
          {#if r.voucher_items.length > 0}
            <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
              <table class="w-full text-sm">
                <thead>
                  <tr class="border-b border-neutral-200">
                    <th class="px-3 py-2.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Payee</th>
                    <th class="px-3 py-2.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Voucher Ref</th>
                    <th class="px-3 py-2.5 text-right font-medium text-emerald-500 text-xs uppercase tracking-wider">Amount</th>
                    <th class="px-3 py-2.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Bank Details</th>
                    <th class="px-3 py-2.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Action</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-neutral-100">
                  {#each r.voucher_items as v}
                    <tr class="hover:bg-neutral-50 transition-colors">
                      <td class="px-3 py-3">
                        <span class="font-medium text-neutral-800 text-xs">{v.vendor_name}</span>
                        {#if v.priority === "high"}
                          <span class="ml-1 inline-block w-1.5 h-1.5 rounded-full bg-red-500" title="High priority"></span>
                        {/if}
                      </td>
                      <td class="px-3 py-3 text-neutral-500 text-xs font-mono">{v.voucher_number}</td>
                      <td class="px-3 py-3 text-right tabular-nums text-xs font-semibold text-emerald-700 bg-emerald-50/50">{formatCurrency(v.amount)}</td>
                      <td class="px-3 py-3">
                        {#if v.bank_account_number}
                          <span class="text-xs text-neutral-500 font-mono">{v.bank_account_number.slice(0, 4)}...{v.bank_account_number.slice(-3)}</span>
                          {#if v.bank_name}
                            <span class="text-xs text-neutral-400 ml-1">({v.bank_name})</span>
                          {/if}
                        {:else}
                          <span class="text-xs text-neutral-300">&mdash;</span>
                        {/if}
                      </td>
                      <td class="px-3 py-3 text-right">
                        <div class="flex items-center justify-end gap-1.5">
                          {#if r.status === "draft" || r.status === "scheduled"}
                            <button
                              type="button"
                              onclick={() => handleRemoveVoucher(v.id)}
                              class="text-xs text-red-400 hover:text-red-600 font-medium transition-colors"
                            >
                              Remove
                            </button>
                          {/if}
                        </div>
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {:else}
            <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-6 text-center">
              <p class="text-sm text-neutral-400">No vouchers in this run.</p>
            </div>
          {/if}
        </div>

        <!-- Bank Integration & Export -->
        <div>
          <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-3">Bank Integration</h3>
          <div class="rounded-xl border border-neutral-200 bg-white p-4 space-y-3">
            <button
              type="button"
              onclick={handleExportCSV}
              disabled={r.voucher_items.length === 0}
              class="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
              </svg>
              Export Bank File (CSV)
            </button>
            <p class="text-xs text-neutral-400 text-center">Download for bulk upload to corporate banking portal or NIP gateway</p>
          </div>
        </div>

        <!-- Balance Check -->
        <div>
          <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-3">Balance Check</h3>
          <div class="rounded-xl border border-neutral-200 bg-white p-4 space-y-3">
            {#if r.funding_balance}
              {@const balance = Number(r.funding_balance)}
              {@const total = Number(r.total_value)}
              {@const sufficient = balance >= total}
              <div class="flex items-center justify-between">
                <div>
                  <p class="text-xs text-neutral-400">Bank Balance (at sign-off)</p>
                  <p class="text-sm font-semibold text-neutral-800 tabular-nums">{currency.format(r.funding_balance)}</p>
                </div>
                <div class="text-right">
                  <p class="text-xs text-neutral-400">Batch Total</p>
                  <p class="text-sm font-semibold text-neutral-800 tabular-nums">{currency.format(String(r.total_value))}</p>
                </div>
              </div>
              <div class="rounded-lg px-3 py-2 text-xs font-medium text-center {sufficient ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-red-50 text-red-700 border border-red-200'}">
                {#if sufficient}
                  Sufficient funds — {currency.format(String((balance - total).toFixed(2)))} remaining after execution
                {:else}
                  Insufficient funds — shortfall of {currency.format(String((total - balance).toFixed(2)))}
                {/if}
              </div>
            {:else if r.status === "draft"}
              <label>
                <span class="block text-xs text-neutral-500 mb-1">Enter current bank balance for verification</span>
                <input
                  type="text"
                  inputmode="decimal"
                  bind:value={balanceInput}
                  placeholder="0.00"
                  class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
                />
              </label>
              {#if fundingSufficient() !== null}
                <div class="rounded-lg px-3 py-2 text-xs font-medium text-center {fundingSufficient() ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-red-50 text-red-700 border border-red-200'}">
                  {#if fundingSufficient()}
                    Sufficient — {currency.format(String((Number(balanceInput) - Number(r.total_value)).toFixed(2)))} will remain
                  {:else}
                    Shortfall of {currency.format(String((Number(r.total_value) - Number(balanceInput)).toFixed(2)))}
                  {/if}
                </div>
              {/if}
            {:else}
              <p class="text-xs text-neutral-400 text-center">No balance recorded for this run.</p>
            {/if}
          </div>
        </div>

        <!-- Approval Chain -->
        <div>
          <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-3">Authorization</h3>
          <div class="rounded-xl border border-neutral-200 bg-white p-4">
            {#if r.approved_by_name}
              <div class="flex items-start gap-3">
                <div class="mt-0.5 w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center shrink-0">
                  <svg class="w-4 h-4 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                  </svg>
                </div>
                <div>
                  <p class="text-sm font-medium text-neutral-800">{r.approved_by_name}</p>
                  <p class="text-xs text-neutral-400">Signed off {formatDate(r.approved_at)}</p>
                </div>
              </div>
              {#if r.executed_by_name}
                <div class="flex items-start gap-3 mt-3 pt-3 border-t border-neutral-100">
                  <div class="mt-0.5 w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center shrink-0">
                    <svg class="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z" />
                    </svg>
                  </div>
                  <div>
                    <p class="text-sm font-medium text-neutral-800">{r.executed_by_name}</p>
                    <p class="text-xs text-neutral-400">Executed {formatDate(r.executed_at)}</p>
                  </div>
                </div>
              {/if}
            {:else if r.status === "draft"}
              <div class="text-center space-y-3">
                <p class="text-xs text-neutral-400">This run requires sign-off before execution.</p>
                <button
                  type="button"
                  onclick={handleApprove}
                  disabled={approving || r.voucher_items.length === 0}
                  class="inline-flex items-center gap-1.5 px-4 py-2.5 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                  </svg>
                  {approving ? "Signing..." : "Sign Off & Schedule"}
                </button>
              </div>
            {:else}
              <p class="text-xs text-neutral-400 text-center">No authorization recorded.</p>
            {/if}
          </div>
        </div>
      </div>

      <!-- Sticky Footer -->
      <div class="px-6 py-4 border-t border-neutral-200 bg-white shrink-0">
        <!-- Batch total -->
        <div class="flex items-center justify-between mb-3">
          <span class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Batch Total</span>
          <span class="text-xl font-bold text-neutral-800 tabular-nums" style="font-family: 'Raleway', sans-serif; font-weight: 700;">
            {currency.format(String(r.total_value))}
          </span>
        </div>

        <div class="flex items-center gap-2">
          {#if r.status === "draft" || r.status === "scheduled"}
            <button
              onclick={() => { showExecuteConfirm = true; executeConfirmText = ""; }}
              disabled={executing || r.voucher_items.length === 0}
              class="inline-flex items-center gap-1.5 px-4 py-2.5 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z" />
              </svg>
              Execute Run
            </button>
          {/if}

          {#if r.status !== "completed" && r.status !== "cancelled"}
            <button
              onclick={handleCancel}
              disabled={cancelling}
              class="ml-auto inline-flex items-center gap-1.5 px-4 py-2.5 border border-red-200 rounded-lg text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50 transition-colors"
            >
              {cancelling ? "Cancelling..." : "Cancel Run"}
            </button>
          {/if}
        </div>
      </div>
    {/if}
  </div>

  <!-- Double-Confirmation Modal -->
  {#if showExecuteConfirm && drawerRun}
    <div class="fixed inset-0 z-60 flex items-center justify-center p-4">
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" onclick={() => (showExecuteConfirm = false)}></div>
      <div class="relative w-full max-w-sm rounded-2xl bg-white shadow-2xl overflow-hidden confirm-modal">
        <div class="h-1 bg-red-500"></div>
        <div class="p-6">
          <div class="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
            <svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
            </svg>
          </div>
          <h3 class="text-center text-lg font-bold text-neutral-800">Confirm Batch Execution</h3>
          <p class="mt-2 text-center text-sm text-neutral-500">
            You are about to execute <span class="font-semibold text-neutral-800">{drawerRun.batch_id}</span> disbursing
            <span class="font-bold text-neutral-800" style="font-family: 'Raleway', sans-serif;">{currency.format(String(drawerRun.total_value))}</span>
            across <span class="font-semibold text-neutral-800">{drawerRun.payment_count}</span> voucher{drawerRun.payment_count !== 1 ? "s" : ""}.
          </p>
          <p class="mt-3 text-center text-xs text-neutral-400">This action cannot be undone. All vouchers will be marked as paid.</p>

          <div class="mt-4">
            <!-- svelte-ignore a11y_label_has_associated_control -->
            <label class="block text-xs font-medium text-neutral-500 mb-1.5">
              Type <span class="font-bold text-neutral-800">EXECUTE</span> to confirm
            </label>
            <input
              type="text"
              bind:value={executeConfirmText}
              placeholder="EXECUTE"
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm text-center tracking-widest font-mono uppercase focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
            />
          </div>

          <div class="flex gap-3 mt-5">
            <button
              type="button"
              onclick={() => (showExecuteConfirm = false)}
              class="flex-1 px-4 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onclick={() => { showExecuteConfirm = false; handleExecute(); }}
              disabled={executeConfirmText.toUpperCase() !== "EXECUTE" || executing}
              class="flex-1 px-4 py-2.5 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {executing ? "Executing..." : "Execute Batch"}
            </button>
          </div>
        </div>
      </div>
    </div>
  {/if}
{/if}

<style>
  .drawer-slide-in {
    animation: drawerSlideIn 0.25s ease-out both;
  }

  @keyframes drawerSlideIn {
    from { transform: translateX(100%); }
    to { transform: translateX(0); }
  }

  .confirm-modal {
    animation: confirmPop 0.25s cubic-bezier(0.34, 1.56, 0.64, 1) both;
  }

  @keyframes confirmPop {
    from { opacity: 0; transform: scale(0.95) translateY(8px); }
    to { opacity: 1; transform: scale(1) translateY(0); }
  }
</style>

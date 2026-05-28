<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import Modal from "$lib/components/Modal.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DateInput from "$lib/components/DateInput.svelte";
  import type { BankReconciliation, BankReconciliationListItem, BankAccountListItem, BankTransactionListItem, PaymentVoucherListItem, PaginatedResponse } from "$lib/types";

  // Reconciliation overview
  interface ReconOverview {
    book_balance: string;
    bank_balance: string;
    difference: string;
    is_balanced: boolean;
    unreconciled_count: number;
    in_progress_count: number;
  }
  let overview = $state<ReconOverview | null>(null);

  async function fetchOverview() {
    try {
      overview = await api.get<ReconOverview>("/finance/bank-reconciliations/overview/");
    } catch { overview = null; }
  }

  let data = $state<BankReconciliationListItem[]>([]);
  let totalCount = $state(0);
  let currentPage = $state(1);
  let searchQuery = $state("");
  let statusFilter = $state("");
  let loading = $state(true);

  let showCreateModal = $state(false);
  let bankAccounts = $state<BankAccountListItem[]>([]);
  let createForm = $state({
    bank_account: "", period_start: "", period_end: "",
    statement_balance: "", book_balance: "", notes: "",
  });
  let createErrors = $state<Record<string, string[]>>({});
  let saving = $state(false);

  function createFieldError(f: string) { return createErrors[f]?.[0] ?? ""; }
  function resetForm() {
    createForm = { bank_account: "", period_start: "", period_end: "", statement_balance: "", book_balance: "", notes: "" };
    createErrors = {};
  }

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");
  const SAMPLES = [
    { statement_balance: "18750000", book_balance: "18650000", notes: "March 2026 reconciliation — Main Operations Account" },
    { statement_balance: "42300000", book_balance: "42300000", notes: "March 2026 reconciliation — Revenue Collection Account" },
    { statement_balance: "85000", book_balance: "84500", notes: "March 2026 reconciliation — USD Domiciliary Account" },
  ];
  let devIdx = $state(0);
  function devFill() {
    const s = SAMPLES[devIdx % SAMPLES.length]; devIdx++;
    createForm.statement_balance = s.statement_balance;
    createForm.book_balance = s.book_balance;
    createForm.notes = s.notes;
    createForm.period_start = "2026-03-01";
    createForm.period_end = "2026-03-31";
    if (bankAccounts.length > 0) createForm.bank_account = String(bankAccounts[devIdx % bankAccounts.length].id);
  }

  const difference = $derived(() => {
    const stmt = Number(createForm.statement_balance);
    const book = Number(createForm.book_balance);
    if (isNaN(stmt) || isNaN(book)) return null;
    return (stmt - book).toFixed(2);
  });

  async function handleCreate(e: Event) {
    e.preventDefault(); createErrors = {}; saving = true;
    try {
      const diff = difference();
      const body: Record<string, unknown> = {
        bank_account: Number(createForm.bank_account),
        period_start: createForm.period_start, period_end: createForm.period_end,
        statement_balance: createForm.statement_balance, book_balance: createForm.book_balance,
        difference: diff || "0", notes: createForm.notes,
      };
      await api.post<BankReconciliation>("/finance/bank-reconciliations/", body);
      toast.success("Reconciliation started", ""); showCreateModal = false; resetForm(); fetchData();
    } catch (err) {
      if (err instanceof ApiError) { createErrors = err.fieldErrors; toast.error("Validation error", ""); }
      else toast.error("Error", "Could not create reconciliation");
    }
    saving = false;
  }

  const PAGE_SIZE = 25;
  const totalPages = $derived(Math.ceil(totalCount / PAGE_SIZE));
  const startItem = $derived((currentPage - 1) * PAGE_SIZE + 1);
  const endItem = $derived(Math.min(currentPage * PAGE_SIZE, totalCount));

  async function fetchBankAccounts() {
    try { const res = await api.get<PaginatedResponse<BankAccountListItem>>("/finance/bank-accounts/", { page_size: "200", status: "active" }); bankAccounts = res.results; } catch { bankAccounts = []; }
  }

  async function fetchData() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage) };
      if (searchQuery) params.search = searchQuery;
      if (statusFilter) params.status = statusFilter;
      const res = await api.get<PaginatedResponse<BankReconciliationListItem>>("/finance/bank-reconciliations/", params);
      data = res.results; totalCount = res.count;
    } catch { data = []; totalCount = 0; }
    loading = false;
  }

  $effect(() => { fetchBankAccounts(); fetchOverview(); });
  $effect(() => { void searchQuery; void statusFilter; void currentPage; fetchData(); });

  let searchTimeout: ReturnType<typeof setTimeout>;
  function onSearch(e: Event) { clearTimeout(searchTimeout); const v = (e.target as HTMLInputElement).value; searchTimeout = setTimeout(() => { searchQuery = v; currentPage = 1; }, 300); }

  function formatDate(v: string | null) { if (!v) return "\u2014"; return new Date(v).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }); }

  // Drawer
  let drawerOpen = $state(false);
  let drawerItem = $state<BankReconciliation | null>(null);
  let drawerLoading = $state(false);
  let completing = $state(false);

  // Dual-pane matching
  let bankTxns = $state<BankTransactionListItem[]>([]);
  let vouchers = $state<PaymentVoucherListItem[]>([]);
  let bankTxnsLoading = $state(false);
  let vouchersLoading = $state(false);
  let selectedTxnId = $state<number | null>(null);
  let selectedVoucherId = $state<number | null>(null);
  let selectedVoucherIds = $state<Set<number>>(new Set());
  let splitMode = $state(false);
  let linking = $state(false);
  let autoMatching = $state(false);
  let addingAdjustment = $state(false);
  let adjustmentForm = $state({ amount: "", description: "", transaction_type: "debit" });

  async function fetchReconTxns(accountId: number) {
    bankTxnsLoading = true;
    try {
      const res = await api.get<PaginatedResponse<BankTransactionListItem>>("/finance/bank-transactions/", {
        bank_account: String(accountId), page_size: "100",
      });
      bankTxns = res.results;
    } catch { bankTxns = []; }
    bankTxnsLoading = false;
  }

  async function fetchReconVouchers() {
    vouchersLoading = true;
    try {
      const res = await api.get<PaginatedResponse<PaymentVoucherListItem>>("/finance/payment-vouchers/", {
        page_size: "100", status: "approved",
      });
      vouchers = res.results;
    } catch { vouchers = []; }
    vouchersLoading = false;
  }

  async function linkMatch() {
    if (!selectedTxnId) return;

    if (splitMode && selectedVoucherIds.size > 0) {
      // Split link — one transaction to multiple vouchers
      linking = true;
      try {
        await api.post(`/finance/bank-transactions/${selectedTxnId}/split-link/`, { voucher_ids: [...selectedVoucherIds] });
        toast.success("Split matched", `Transaction linked to ${selectedVoucherIds.size} vouchers`);
        selectedTxnId = null; selectedVoucherIds = new Set(); splitMode = false;
        await refreshPanes();
      } catch (err: any) {
        const detail = err?.data?.detail || "Voucher total does not match transaction amount";
        toast.error("Split failed", detail);
      }
      linking = false;
      return;
    }

    if (!selectedVoucherId) return;
    linking = true;
    try {
      await api.post(`/finance/bank-transactions/${selectedTxnId}/link/`, { voucher_id: selectedVoucherId });
      toast.success("Matched", "Transaction linked to voucher");
      selectedTxnId = null; selectedVoucherId = null;
      await refreshPanes();
    } catch { toast.error("Error", "Could not link transaction"); }
    linking = false;
  }

  async function autoMatch() {
    if (!drawerItem) return;
    autoMatching = true;
    try {
      const res = await api.post<{ matched_count: number; message: string }>("/finance/bank-transactions/auto-match/", {
        bank_account_id: drawerItem.bank_account,
      });
      toast.success("Auto-match complete", res.message);
      await refreshPanes();
    } catch { toast.error("Error", "Auto-match failed"); }
    autoMatching = false;
  }

  async function addAdjustment() {
    if (!drawerItem || !adjustmentForm.amount || !adjustmentForm.description) return;
    addingAdjustment = true;
    try {
      const today = new Date().toISOString().slice(0, 10);
      const txn = await api.post("/finance/bank-transactions/", {
        bank_account: drawerItem.bank_account,
        transaction_date: today,
        transaction_type: adjustmentForm.transaction_type,
        amount: adjustmentForm.amount,
        reference: "ADJ/" + Date.now().toString().slice(-8),
        description: adjustmentForm.description,
        counterparty: "Bank Charge / Adjustment",
        status: "reconciled",
      });
      toast.success("Adjustment added", "Bank charge recorded and auto-reconciled");
      adjustmentForm = { amount: "", description: "", transaction_type: "debit" };
      await refreshPanes();
    } catch { toast.error("Error", "Could not add adjustment"); }
    addingAdjustment = false;
  }

  function toggleSplitVoucher(id: number) {
    const next = new Set(selectedVoucherIds);
    if (next.has(id)) next.delete(id); else next.add(id);
    selectedVoucherIds = next;
  }

  const splitTotal = $derived(
    vouchers.filter(v => selectedVoucherIds.has(v.id)).reduce((s, v) => s + Number(v.amount || 0), 0)
  );

  // Drag-and-drop matching
  let draggedTxnId = $state<number | null>(null);

  function handleTxnDragStart(e: DragEvent, txnId: number) {
    draggedTxnId = txnId;
    selectedTxnId = txnId;
    e.dataTransfer?.setData("text/plain", String(txnId));
    if (e.dataTransfer) e.dataTransfer.effectAllowed = "link";
  }

  function handleVoucherDrop(e: DragEvent, voucherId: number) {
    e.preventDefault();
    if (!draggedTxnId) return;
    selectedTxnId = draggedTxnId;
    selectedVoucherId = voucherId;
    draggedTxnId = null;
    linkMatch();
  }

  function handleVoucherDragOver(e: DragEvent) {
    if (draggedTxnId) {
      e.preventDefault();
      if (e.dataTransfer) e.dataTransfer.dropEffect = "link";
    }
  }

  // Approver note
  let approverNote = $state("");
  let savingNote = $state(false);

  async function saveApproverNote() {
    if (!drawerItem) return;
    savingNote = true;
    try {
      await api.patch(`/finance/bank-reconciliations/${drawerItem.id}/`, { notes: approverNote });
      drawerItem = await api.get<BankReconciliation>(`/finance/bank-reconciliations/${drawerItem.id}/`);
      toast.success("Note saved", "Approver note has been recorded");
    } catch { toast.error("Error", "Could not save note"); }
    savingNote = false;
  }

  function exportReconReport() {
    if (!drawerItem) return;
    const r = drawerItem;
    const matched = bankTxns.filter(t => t.status === "reconciled");
    const unmatched = bankTxns.filter(t => t.status !== "reconciled");

    const lines = [
      `RECONCILIATION REPORT`,
      `=====================`,
      `Account: ${r.bank_account_name} — ${r.bank_name}`,
      `Period: ${r.period_start} to ${r.period_end}`,
      `Status: ${r.status}`,
      ``,
      `SUMMARY`,
      `Statement Balance: ${r.statement_balance}`,
      `Book Balance: ${r.book_balance}`,
      `Difference: ${r.difference}`,
      `Reconciled: ${r.reconciled_count} | Unreconciled: ${r.unreconciled_count}`,
      ``,
      `MATCHED TRANSACTIONS (${matched.length})`,
      `Date | Counterparty | Reference | Amount | Type`,
      ...matched.map(t => `${t.transaction_date} | ${t.counterparty} | ${t.reference} | ${t.amount} | ${t.transaction_type}`),
      ``,
      `OUTSTANDING ITEMS (${unmatched.length})`,
      `Date | Counterparty | Reference | Amount | Type`,
      ...unmatched.map(t => `${t.transaction_date} | ${t.counterparty} | ${t.reference} | ${t.amount} | ${t.transaction_type}`),
    ];

    if (r.notes) {
      lines.push(``, `APPROVER NOTES`, r.notes);
    }

    lines.push(``, `Generated: ${new Date().toISOString()}`, `By: developerOS Reconciliation Module`);

    const blob = new Blob([lines.join("\n")], { type: "text/plain" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `reconciliation-report-${r.bank_account_name.replace(/\s+/g, "-")}-${r.period_end}.txt`;
    a.click();
    URL.revokeObjectURL(a.href);
    toast.success("Report exported", "Reconciliation report downloaded");
  }

  async function refreshPanes() {
    if (!drawerItem) return;
    fetchReconTxns(drawerItem.bank_account);
    fetchReconVouchers();
    drawerItem = await api.get<BankReconciliation>(`/finance/bank-reconciliations/${drawerItem.id}/`);
    fetchData();
    fetchOverview();
  }

  async function openDrawer(id: number) {
    drawerOpen = true;
    drawerLoading = true;
    drawerItem = null;
    bankTxns = []; vouchers = [];
    selectedTxnId = null; selectedVoucherId = null;
    approverNote = "";
    try {
      drawerItem = await api.get<BankReconciliation>(`/finance/bank-reconciliations/${id}/`);
      approverNote = drawerItem.notes || "";
      fetchReconTxns(drawerItem.bank_account);
      fetchReconVouchers();
    } catch { toast.error("Not found", ""); drawerOpen = false; }
    drawerLoading = false;
  }

  function closeDrawer() { drawerOpen = false; drawerItem = null; bankTxns = []; vouchers = []; }

  async function handleComplete() {
    if (!drawerItem) return;
    completing = true;
    try {
      await api.post(`/finance/bank-reconciliations/${drawerItem.id}/complete/`, {});
      toast.success("Completed", "Reconciliation has been finalized");
      drawerItem = await api.get<BankReconciliation>(`/finance/bank-reconciliations/${drawerItem.id}/`);
      fetchData();
    } catch { toast.error("Error", "Could not complete reconciliation"); }
    completing = false;
  }
</script>

<div class="space-y-6">
  <div class="flex items-center justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-pink-600">Banking</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Bank Reconciliation</h1>
      <p class="text-sm text-neutral-400 mt-1">Match bank statements to internal records</p> 
    </div>
    <button onclick={() => { showCreateModal = true; fetchBankAccounts(); }} class="px-4 py-2.5 bg-neutral-800 text-white rounded-lg hover:bg-neutral-800 text-sm font-medium transition-colors">+ New Reconciliation</button>
  </div>

  <!-- Reconciliation Overview Header -->
  {#if overview}
    <div class="grid grid-cols-4 gap-4">
      <!-- Book Balance -->
      <div class="rounded-xl bg-white/60 backdrop-blur-md border border-neutral-200 shadow-sm p-4">
        <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider mb-1">Book Balance</p>
        <p class="text-xl font-bold text-neutral-800 tabular-nums" style="font-family: 'Raleway', sans-serif;">{currency.format(overview.book_balance)}</p>
        <p class="text-xs text-neutral-400 mt-1">Internal ERP records</p>
      </div>

      <!-- Bank Balance -->
      <div class="rounded-xl bg-white/60 backdrop-blur-md border border-neutral-200 shadow-sm p-4">
        <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider mb-1">Bank Balance</p>
        <p class="text-xl font-bold text-neutral-800 tabular-nums" style="font-family: 'Raleway', sans-serif;">{currency.format(overview.bank_balance)}</p>
        <p class="text-xs text-neutral-400 mt-1">Last statement / API</p>
      </div>

      <!-- Difference -->
      <div class="rounded-xl bg-white/60 backdrop-blur-md border shadow-sm p-4" style="border-color: {overview.is_balanced ? '#a7f3d0' : '#fecaca'};">
        <div class="flex items-center gap-2 mb-1">
          <p class="text-xs font-medium uppercase tracking-wider" style="color: {overview.is_balanced ? '#059669' : '#dc2626'};">Difference</p>
          {#if overview.is_balanced}
            <svg class="w-4 h-4" style="color: #10b981;" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" /></svg>
          {:else}
            <svg class="w-4 h-4" style="color: #ef4444;" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" /></svg>
          {/if}
        </div>
        <p class="text-xl font-bold tabular-nums" style="font-family: 'Raleway', sans-serif; color: {overview.is_balanced ? '#059669' : '#dc2626'};">{currency.format(overview.difference)}</p>
        <p class="text-xs mt-1" style="color: {overview.is_balanced ? '#059669' : '#dc2626'};">{overview.is_balanced ? "Balanced" : "Discrepancy"}</p>
      </div>

      <!-- Unreconciled Items -->
      <div class="rounded-xl bg-white/60 backdrop-blur-md border border-neutral-200 shadow-sm p-4">
        <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider mb-1">Unreconciled</p>
        <p class="text-xl font-bold tabular-nums" style="font-family: 'Raleway', sans-serif; color: {overview.unreconciled_count > 0 ? '#f59e0b' : '#059669'};">{overview.unreconciled_count}</p>
        <p class="text-xs text-neutral-400 mt-1">transaction{overview.unreconciled_count !== 1 ? "s" : ""} pending{#if overview.in_progress_count > 0} &middot; {overview.in_progress_count} in progress{/if}</p>
      </div>
    </div>
  {/if}

  <div class="flex gap-3 items-center">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
      <input type="text" placeholder="Search..." oninput={onSearch} class="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent placeholder:text-neutral-400" />
    </div>
    <select bind:value={statusFilter} onchange={() => (currentPage = 1)} class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent">
      <option value="">All Statuses</option><option value="in_progress">In Progress</option><option value="completed">Completed</option><option value="cancelled">Cancelled</option>
    </select>
  </div>

  <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
    {#if loading}
      <div class="p-16 text-center"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div></div>
    {:else if data.length === 0}
      <div class="p-16 text-center">
        <p class="text-sm font-medium text-neutral-800">No reconciliations found</p>
        <button onclick={() => { showCreateModal = true; fetchBankAccounts(); }} class="inline-block mt-4 px-4 py-2 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors">+ New Reconciliation</button>
      </div>
    {:else}
      <table class="w-full text-sm">
        <thead><tr class="border-b border-neutral-200">
          <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Account</th>
          <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Period</th>
          <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
          <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Statement</th>
          <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Book</th>
          <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Difference</th>
          <th class="px-5 py-3.5 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Matched</th>
        </tr></thead>
        <tbody class="divide-y divide-neutral-100">
          {#each data as r}
            <tr class="hover:bg-neutral-50 cursor-pointer transition-colors" onclick={() => openDrawer(r.id)}>
              <td class="px-5 py-4"><span class="font-medium text-neutral-800">{r.bank_account_name}</span><br><span class="text-xs text-neutral-400">{r.bank_name}</span></td>
              <td class="px-5 py-4 text-neutral-500 text-xs">{formatDate(r.period_start)} — {formatDate(r.period_end)}</td>
              <td class="px-5 py-4"><StatusBadge status={r.status} /></td>
              <td class="px-5 py-4 text-right tabular-nums text-neutral-700">{currency.format(r.statement_balance)}</td>
              <td class="px-5 py-4 text-right tabular-nums text-neutral-700">{currency.format(r.book_balance)}</td>
              <td class="px-5 py-4 text-right tabular-nums font-medium {Number(r.difference) === 0 ? 'text-emerald-600' : 'text-red-600'}">{currency.format(r.difference)}</td>
              <td class="px-5 py-4 text-center text-neutral-500">{r.reconciled_count}/{r.reconciled_count + r.unreconciled_count}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>

  {#if totalCount > 0}
    <div class="flex items-center justify-between">
      <p class="text-sm text-neutral-400">Showing <span class="font-medium text-neutral-600">{startItem}–{endItem}</span> of <span class="font-medium text-neutral-600">{totalCount}</span></p>
    </div>
  {/if}
</div>

<Modal open={showCreateModal} onclose={() => { showCreateModal = false; resetForm(); }} title="New Reconciliation" maxWidth="max-w-xl">
  <form onsubmit={handleCreate} class="space-y-4">
    <label><span class="block text-sm font-medium text-neutral-700 mb-1">Bank Account</span><select bind:value={createForm.bank_account} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"><option value="">Select account</option>{#each bankAccounts as a}<option value={String(a.id)}>{a.account_name} — {a.bank_name}</option>{/each}</select>{#if createFieldError("bank_account")}<p class="mt-1 text-xs text-red-500">{createFieldError("bank_account")}</p>{/if}</label>
    <div class="grid grid-cols-2 gap-3">
      <label><span class="block text-sm font-medium text-neutral-700 mb-1">Period Start</span><DateInput bind:value={createForm.period_start} />{#if createFieldError("period_start")}<p class="mt-1 text-xs text-red-500">{createFieldError("period_start")}</p>{/if}</label>
      <label><span class="block text-sm font-medium text-neutral-700 mb-1">Period End</span><DateInput bind:value={createForm.period_end} />{#if createFieldError("period_end")}<p class="mt-1 text-xs text-red-500">{createFieldError("period_end")}</p>{/if}</label>
    </div>
    <div class="grid grid-cols-2 gap-3">
      <label><span class="block text-sm font-medium text-neutral-700 mb-1">Statement Balance</span><input bind:value={createForm.statement_balance} placeholder="0.00" class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />{#if createFieldError("statement_balance")}<p class="mt-1 text-xs text-red-500">{createFieldError("statement_balance")}</p>{/if}</label>
      <label><span class="block text-sm font-medium text-neutral-700 mb-1">Book Balance</span><input bind:value={createForm.book_balance} placeholder="0.00" class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />{#if createFieldError("book_balance")}<p class="mt-1 text-xs text-red-500">{createFieldError("book_balance")}</p>{/if}</label>
    </div>
    {#if difference() !== null}
      <div class="rounded-lg px-3 py-2 text-xs font-medium text-center {Number(difference()) === 0 ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-red-50 text-red-700 border border-red-200'}">
        Difference: {currency.format(difference()!)}
        {#if Number(difference()) === 0} — Balanced{/if}
      </div>
    {/if}
    <label><span class="block text-sm font-medium text-neutral-700 mb-1">Notes</span><textarea bind:value={createForm.notes} rows="2" class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"></textarea></label>
    <div class="flex justify-end gap-3 pt-2">
      {#if isDev}<button type="button" onclick={devFill} class="mr-auto rounded-lg bg-orange-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-orange-600 transition-colors">Dev Fill</button>{/if}
      <button type="button" onclick={() => { showCreateModal = false; resetForm(); }} class="px-4 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">Cancel</button>
      <button type="submit" disabled={saving} class="px-4 py-2.5 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">{saving ? "Creating..." : "Start Reconciliation"}</button>
    </div>
  </form>
</Modal>

{#if drawerOpen}
  <div class="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm" onclick={closeDrawer} onkeydown={(e) => e.key === "Escape" && closeDrawer()} role="button" tabindex="-1"></div>
  <div class="fixed inset-y-0 right-0 z-50 w-full max-w-5xl bg-white shadow-2xl border-l border-neutral-200 flex flex-col drawer-slide-in">
    {#if drawerLoading}
      <div class="flex-1 flex items-center justify-center"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div></div>
    {:else if drawerItem}
      {@const r = drawerItem}

      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 bg-black border-b border-neutral-200">
        <div class="flex items-center gap-3">
          <h2 class="text-lg font-bold text-white">{r.bank_account_name}</h2>
          <StatusBadge status={r.status} size="md" />
          <span class="text-xs text-neutral-400">{r.bank_name} &middot; {formatDate(r.period_start)} — {formatDate(r.period_end)}</span>
        </div>
        <div class="flex items-center gap-2">
          {#if r.status === "in_progress"}
            <!-- Auto-match -->
            <button onclick={autoMatch} disabled={autoMatching} class="inline-flex items-center gap-1.5 px-3 py-2 border border-neutral-200 rounded-lg text-xs font-medium text-neutral-400 hover:bg-neutral-50 disabled:opacity-50 transition-colors">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 0 0-2.455 2.456Z" /></svg>
              {autoMatching ? "Matching..." : "Auto-Match"}
            </button>
            <!-- Split toggle -->
            <button onclick={() => { splitMode = !splitMode; selectedVoucherIds = new Set(); selectedVoucherId = null; }} class="inline-flex items-center gap-1.5 px-3 py-2 border rounded-lg text-xs font-medium transition-colors" style="border-color: {splitMode ? '#8b5cf6' : '#e5e7eb'}; color: {splitMode ? '#7c3aed' : '#525252'}; background: {splitMode ? '#f5f3ff' : 'white'};">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" /></svg>
              Split
            </button>
            <!-- Link button -->
            {#if selectedTxnId && (selectedVoucherId || (splitMode && selectedVoucherIds.size > 0))}
              <button onclick={linkMatch} disabled={linking} class="inline-flex items-center gap-1.5 px-4 py-2 bg-emerald-600 text-white rounded-lg text-xs font-medium hover:bg-emerald-700 disabled:opacity-50 transition-colors">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m9.86-2.56a4.5 4.5 0 0 0-1.242-7.244l4.5-4.5a4.5 4.5 0 0 1 6.364 6.364l-1.757 1.757" /></svg>
                {linking ? "Linking..." : splitMode ? `Link ${selectedVoucherIds.size} vouchers` : "Link Selected"}
              </button>
            {/if}
          {/if}
          <button onclick={closeDrawer} class="w-8 h-8 flex items-center justify-center rounded-lg text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 transition-colors" aria-label="Close">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
          </button>
        </div>
      </div>

      <!-- Summary bar -->
      <div class="px-6 py-3 border-b border-neutral-100 flex items-center gap-6 text-sm">
        <div><span class="text-neutral-400">Statement:</span> <span class="font-semibold text-neutral-800 tabular-nums">{currency.format(r.statement_balance)}</span></div>
        <div><span class="text-neutral-400">Book:</span> <span class="font-semibold text-neutral-800 tabular-nums">{currency.format(r.book_balance)}</span></div>
        <div><span class="text-neutral-400">Diff:</span> <span class="font-bold tabular-nums" style="color: {Number(r.difference) === 0 ? '#059669' : '#dc2626'};">{currency.format(r.difference)}</span></div>
        <div class="flex items-center gap-1.5">
          <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
          <span class="text-neutral-500">{r.reconciled_count} matched</span>
        </div>
        <div class="flex items-center gap-1.5">
          <span class="w-2 h-2 rounded-full bg-amber-400"></span>
          <span class="text-neutral-500">{r.unreconciled_count} unmatched</span>
        </div>
      </div>

      <!-- Dual-pane body -->
      <div class="flex-1 flex min-h-0">
        <!-- LEFT PANE: Bank Statement Lines -->
        <div class="w-1/2 border-r border-neutral-200 flex flex-col">
          <div class="px-4 py-3 border-b border-neutral-100 bg-neutral-50">
            <p class="text-sm font-semibold text-neutral-700 uppercase tracking-wider">Bank Statement</p>
            <p class="text-xs text-neutral-400 mt-0.5">Real-world transactions from your bank</p>
          </div>
          <div class="flex-1 overflow-y-auto">
            {#if bankTxnsLoading}
              <div class="p-8 text-center"><div class="inline-block w-5 h-5 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div></div>
            {:else if bankTxns.length === 0}
              <div class="p-8 text-center"><p class="text-sm text-neutral-400">No transactions found for this account.</p></div>
            {:else}
              {#each bankTxns as txn}
                <button
                  type="button"
                  class="w-full text-left px-4 py-3 border-b border-neutral-100 transition-colors"
                  style="background: {selectedTxnId === txn.id ? '#ecfdf5' : txn.status === 'reconciled' ? '#fafafa' : 'white'}; cursor: {txn.status === 'reconciled' ? 'default' : 'grab'};"
                  onclick={() => (selectedTxnId = selectedTxnId === txn.id ? null : txn.id)}
                  disabled={txn.status === "reconciled"}
                  draggable={txn.status !== "reconciled"}
                  ondragstart={(e) => handleTxnDragStart(e, txn.id)}
                  ondragend={() => (draggedTxnId = null)}
                >
                  <div class="flex items-center justify-between">
                    <div class="min-w-0">
                      <p class="text-sm font-medium text-neutral-800 truncate">{txn.counterparty || "Bank Transaction"}</p>
                      <p class="text-xs text-neutral-400 mt-0.5">{formatDate(txn.transaction_date)} &middot; {txn.reference || "No ref"}</p>
                    </div>
                    <div class="text-right shrink-0 ml-3">
                      <p class="text-sm font-semibold tabular-nums" style="color: {txn.transaction_type === 'credit' ? '#047857' : '#dc2626'};">
                        {txn.transaction_type === "credit" ? "+" : "-"}{currency.format(txn.amount)}
                      </p>
                      {#if txn.status === "reconciled"}
                        <span class="text-[10px] text-emerald-600 font-medium">Matched</span>
                      {:else if selectedTxnId === txn.id}
                        <span class="text-[10px] text-emerald-600 font-medium">Selected</span>
                      {:else}
                        <span class="text-[10px] text-amber-500 font-medium">Unmatched</span>
                      {/if}
                    </div>
                  </div>
                </button>
              {/each}
            {/if}
          </div>
        </div>

        <!-- RIGHT PANE: Internal Ledger (Vouchers) -->
        <div class="w-1/2 flex flex-col">
          <div class="px-4 py-3 border-b border-neutral-100 bg-neutral-50">
            <div class="flex items-center justify-between">
              <div>
                <p class="text-sm font-semibold text-neutral-700 uppercase tracking-wider">Internal Ledger</p>
                <p class="text-xs text-neutral-400 mt-0.5">{splitMode ? "Multi-select mode — pick vouchers to split-match" : "Payment vouchers"}</p>
              </div>
              {#if splitMode && selectedVoucherIds.size > 0}
                <span class="text-xs font-semibold tabular-nums" style="color: {selectedTxnId ? '#7c3aed' : '#525252'};">
                  {selectedVoucherIds.size} selected &middot; {currency.format(String(splitTotal.toFixed(2)))}
                </span>
              {/if}
            </div>
          </div>
          <div class="flex-1 overflow-y-auto">
            {#if vouchersLoading}
              <div class="p-8 text-center"><div class="inline-block w-5 h-5 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div></div>
            {:else if vouchers.length === 0}
              <div class="p-8 text-center"><p class="text-sm text-neutral-400">No approved vouchers to match.</p></div>
            {:else}
              {#each vouchers as v}
                <button
                  type="button"
                  class="w-full text-left px-4 py-3 border-b border-neutral-100 transition-colors"
                  style="background: {splitMode ? (selectedVoucherIds.has(v.id) ? '#f5f3ff' : 'white') : (selectedVoucherId === v.id ? '#eff6ff' : 'white')};"
                  onclick={() => splitMode ? toggleSplitVoucher(v.id) : (selectedVoucherId = selectedVoucherId === v.id ? null : v.id)}
                  ondragover={handleVoucherDragOver}
                  ondrop={(e) => handleVoucherDrop(e, v.id)}
                >
                  <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2 min-w-0">
                      {#if splitMode}
                        <input type="checkbox" checked={selectedVoucherIds.has(v.id)} class="rounded border-neutral-300 w-3.5 h-3.5" onclick={(e) => e.stopPropagation()} onchange={() => toggleSplitVoucher(v.id)} />
                      {/if}
                      <div class="min-w-0">
                        <div class="flex items-center gap-2">
                          <p class="text-sm font-medium text-neutral-800 font-mono">{v.voucher_number}</p>
                          {#if v.property_name}
                            <span class="text-[10px] rounded-full px-1.5 py-0.5 bg-neutral-100 text-neutral-500">{v.property_name}</span>
                          {/if}
                        </div>
                        <p class="text-xs text-neutral-400 mt-0.5">{v.vendor_name} &middot; {formatDate(v.issue_date)}</p>
                      </div>
                    </div>
                    <div class="text-right shrink-0 ml-3">
                      <p class="text-sm font-semibold text-neutral-800 tabular-nums">{currency.format(v.amount)}</p>
                      {#if splitMode && selectedVoucherIds.has(v.id)}
                        <span class="text-[10px] font-medium" style="color: #7c3aed;">Selected</span>
                      {:else if selectedVoucherId === v.id}
                        <span class="text-[10px] text-blue-600 font-medium">Selected</span>
                      {:else}
                        <span class="text-[10px] text-neutral-400">Approved</span>
                      {/if}
                    </div>
                  </div>
                </button>
              {/each}
            {/if}
          </div>

          <!-- Quick-add Adjustment -->
          {#if r.status === "in_progress"}
            <div class="px-4 py-3 border-t border-neutral-200 bg-neutral-50">
              <p class="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-2">Quick Add: Bank Charge / Fee</p>
              <div class="flex items-end gap-2">
                <label class="w-20">
                  <span class="block text-xs text-neutral-400 mb-0.5">Amount</span>
                  <input type="text" inputmode="decimal" bind:value={adjustmentForm.amount} placeholder="0.00" class="w-full px-2 py-1.5 border border-neutral-200 rounded text-sm tabular-nums focus:outline-none focus:ring-1 focus:ring-neutral-800" />
                </label>
                <label class="flex-1">
                  <span class="block text-xs text-neutral-400 mb-0.5">Description</span>
                  <input type="text" bind:value={adjustmentForm.description} placeholder="e.g. SMS charge, stamp duty" class="w-full px-2 py-1.5 border border-neutral-200 rounded text-sm focus:outline-none focus:ring-1 focus:ring-neutral-800" />
                </label>
                <select bind:value={adjustmentForm.transaction_type} class="px-2 py-1.5 border border-neutral-200 rounded text-sm bg-white focus:outline-none focus:ring-1 focus:ring-neutral-800">
                  <option value="debit">DR</option>
                  <option value="credit">CR</option>
                </select>
                <button type="button" onclick={addAdjustment} disabled={addingAdjustment || !adjustmentForm.amount} class="px-3 py-1.5 bg-neutral-800 text-white rounded text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">
                  {addingAdjustment ? "..." : "Add"}
                </button>
              </div>
            </div>
          {/if}
        </div>
      </div>

      <!-- Clean Books state -->
      {#if !bankTxnsLoading && bankTxns.length > 0 && bankTxns.every(t => t.status === "reconciled")}
        <div class="absolute inset-0 z-10 flex items-center justify-center bg-white/90 backdrop-blur-sm">
          <div class="text-center px-8">
            <div class="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100">
              <svg class="w-8 h-8 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
              </svg>
            </div>
            <h3 class="text-lg font-bold text-neutral-800">Clean Books</h3>
            <p class="mt-1 text-sm text-neutral-500">All transactions have been reconciled.</p>
            <p class="mt-0.5 text-sm text-emerald-600 font-medium">{r.bank_account_name} — {formatDate(r.period_start)} to {formatDate(r.period_end)}</p>
            {#if r.status === "in_progress"}
              <button onclick={handleComplete} disabled={completing} class="mt-4 inline-flex items-center gap-1.5 px-5 py-2.5 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" /></svg>
                {completing ? "Completing..." : "Finalize Reconciliation"}
              </button>
            {/if}
          </div>
        </div>
      {/if}

      <!-- Approver Note + Footer -->
      <div class="border-t border-neutral-200">
        {#if r.status === "in_progress"}
          <div class="px-6 py-3 border-b border-neutral-100 bg-neutral-50">
            <p class="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-1.5">Approver Note</p>
            <div class="flex gap-2">
              <textarea bind:value={approverNote} rows="2" placeholder="Explain any permanent discrepancies (e.g. bank error under investigation)..." class="flex-1 px-3 py-2 border border-neutral-200 rounded-lg text-sm resize-none focus:outline-none focus:ring-1 focus:ring-neutral-800"></textarea>
              <button type="button" onclick={saveApproverNote} disabled={savingNote} class="shrink-0 self-end px-3 py-2 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">
                {savingNote ? "..." : "Save"}
              </button>
            </div>
          </div>
        {/if}

        <div class="px-6 py-4 flex items-center gap-2">
          {#if r.status === "in_progress"}
            <button onclick={handleComplete} disabled={completing} class="inline-flex items-center gap-1.5 px-4 py-2.5 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" /></svg>
              {completing ? "Completing..." : "Mark Complete"}
            </button>
          {/if}
          <button type="button" onclick={exportReconReport} class="inline-flex items-center gap-1.5 px-4 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" /></svg>
            Export Report
          </button>
        </div>
      </div>
    {/if}
  </div>
{/if}

<style>
  .drawer-slide-in { animation: drawerSlideIn 0.25s ease-out both; }
  @keyframes drawerSlideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }
</style>

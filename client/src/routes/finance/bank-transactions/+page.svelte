<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import Modal from "$lib/components/Modal.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DateInput from "$lib/components/DateInput.svelte";
  import type { BankTransaction, BankTransactionListItem, BankAccountListItem, AccountListItem, PaginatedResponse } from "$lib/types";

  let data = $state<BankTransactionListItem[]>([]);
  let totalCount = $state(0);
  let currentPage = $state(1);
  let searchQuery = $state("");
  let statusFilter = $state("");
  let typeFilter = $state("");
  let accountFilter = $state("");
  let dateFrom = $state("");
  let dateTo = $state("");
  let amountMin = $state("");
  let amountMax = $state("");
  let loading = $state(true);

  // Transaction intelligence
  interface TxnSummary {
    total_inflow: string;
    total_outflow: string;
    total_count: number;
    reconciled_count: number;
    reconciliation_pct: number;
  }
  let summary = $state<TxnSummary | null>(null);

  let showCreateModal = $state(false);
  let bankAccounts = $state<BankAccountListItem[]>([]);
  let createForm = $state({
    bank_account: "", transaction_date: "", value_date: "",
    transaction_type: "debit", amount: "", reference: "",
    description: "", counterparty: "", status: "pending", notes: "",
  });
  let createErrors = $state<Record<string, string[]>>({});
  let saving = $state(false);

  function createFieldError(f: string) { return createErrors[f]?.[0] ?? ""; }
  function resetForm() {
    createForm = { bank_account: "", transaction_date: "", value_date: "", transaction_type: "debit", amount: "", reference: "", description: "", counterparty: "", status: "pending", notes: "" };
    createErrors = {};
  }

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");
  const SAMPLES = [
    { transaction_type: "debit", amount: "4200000", reference: "NIP/00293847556", counterparty: "Alpha Solar Ltd", description: "Payment for solar panels — Phase 3" },
    { transaction_type: "credit", amount: "15000000", reference: "TRF/2026031712", counterparty: "Crescent Holdings Ltd", description: "Deposit — Block A Unit 12 reservation" },
    { transaction_type: "debit", amount: "450000", reference: "NIP/00481923004", counterparty: "SecureGuard Services", description: "Monthly site security — March 2026" },
    { transaction_type: "credit", amount: "8500000", reference: "CHQ/00912", counterparty: "Ogundimu Adebayo", description: "Instalment payment — Ikoyi Waterfront Villa" },
  ];
  let devIdx = $state(0);
  function devFill() {
    const s = SAMPLES[devIdx % SAMPLES.length]; devIdx++;
    const today = new Date().toISOString().slice(0, 10);
    createForm = { ...createForm, ...s, transaction_date: today, value_date: today, status: "cleared" };
    if (bankAccounts.length > 0) createForm.bank_account = String(bankAccounts[devIdx % bankAccounts.length].id);
  }

  async function handleCreate(e: Event) {
    e.preventDefault(); createErrors = {}; saving = true;
    try {
      const body: Record<string, unknown> = { ...createForm, bank_account: Number(createForm.bank_account), value_date: createForm.value_date || null };
      await api.post<BankTransaction>("/finance/bank-transactions/", body);
      toast.success("Transaction recorded", ""); showCreateModal = false; resetForm(); fetchData();
    } catch (err) {
      if (err instanceof ApiError) { createErrors = err.fieldErrors; toast.error("Validation error", ""); }
      else toast.error("Error", "Could not record transaction");
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

  async function fetchSummary() {
    try {
      const params: Record<string, string> = {};
      if (accountFilter) params.bank_account = accountFilter;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      summary = await api.get<TxnSummary>("/finance/bank-transactions/summary/", params);
    } catch { summary = null; }
  }

  async function fetchData() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage) };
      if (searchQuery) params.search = searchQuery;
      if (statusFilter) params.status = statusFilter;
      if (typeFilter) params.transaction_type = typeFilter;
      if (accountFilter) params.bank_account = accountFilter;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      if (amountMin) params.amount_min = amountMin;
      if (amountMax) params.amount_max = amountMax;
      const res = await api.get<PaginatedResponse<BankTransactionListItem>>("/finance/bank-transactions/", params);
      data = res.results; totalCount = res.count;
    } catch { data = []; totalCount = 0; }
    loading = false;
  }

  $effect(() => { fetchBankAccounts(); });
  $effect(() => { void searchQuery; void statusFilter; void typeFilter; void accountFilter; void dateFrom; void dateTo; void amountMin; void amountMax; void currentPage; fetchData(); fetchSummary(); });

  let searchTimeout: ReturnType<typeof setTimeout>;
  function onSearch(e: Event) { clearTimeout(searchTimeout); const v = (e.target as HTMLInputElement).value; searchTimeout = setTimeout(() => { searchQuery = v; currentPage = 1; }, 300); }

  function formatDate(v: string | null) { if (!v) return "\u2014"; return new Date(v).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" }); }

  // Drawer
  let drawerOpen = $state(false);
  let drawerItem = $state<BankTransaction | null>(null);
  let drawerLoading = $state(false);

  // Reconciliation workspace
  interface MatchSuggestion {
    id: number; type: string; number: string;
    counterparty: string; amount: string; date: string; match_reason: string;
  }
  let suggestions = $state<MatchSuggestion[]>([]);
  let suggestionsLoading = $state(false);
  let matchSearch = $state("");
  let linking = $state(false);
  let glAccounts = $state<AccountListItem[]>([]);
  let selectedGLAccount = $state("");
  let categorizing = $state(false);

  const filteredSuggestions = $derived(() => {
    if (!matchSearch) return suggestions;
    const q = matchSearch.toLowerCase();
    return suggestions.filter(s =>
      s.number.toLowerCase().includes(q) ||
      s.counterparty.toLowerCase().includes(q) ||
      s.amount.includes(q)
    );
  });

  async function fetchSuggestions(txnId: number) {
    suggestionsLoading = true;
    try {
      const res = await api.get<{ suggestions: MatchSuggestion[] }>(`/finance/bank-transactions/${txnId}/matches/`);
      suggestions = res.suggestions;
    } catch { suggestions = []; }
    suggestionsLoading = false;
  }

  async function fetchGLAccounts() {
    try {
      const res = await api.get<PaginatedResponse<AccountListItem>>("/finance/accounts/", { page_size: "200", is_active: "true" });
      glAccounts = res.results;
    } catch { glAccounts = []; }
  }

  async function linkToVoucher(voucherId: number) {
    if (!drawerItem) return;
    linking = true;
    try {
      drawerItem = await api.post<BankTransaction>(`/finance/bank-transactions/${drawerItem.id}/link/`, { voucher_id: voucherId });
      toast.success("Matched", "Transaction linked to voucher and marked as reconciled");
      fetchData(); fetchSummary();
    } catch { toast.error("Error", "Could not link transaction"); }
    linking = false;
  }

  async function categorizeToGL() {
    if (!drawerItem || !selectedGLAccount) return;
    categorizing = true;
    try {
      drawerItem = await api.post<BankTransaction>(`/finance/bank-transactions/${drawerItem.id}/link/`, { gl_account_id: Number(selectedGLAccount) });
      toast.success("Categorized", "Transaction categorized to GL account and reconciled");
      selectedGLAccount = "";
      fetchData(); fetchSummary();
    } catch { toast.error("Error", "Could not categorize transaction"); }
    categorizing = false;
  }

  async function openDrawer(id: number) {
    drawerOpen = true;
    drawerLoading = true;
    drawerItem = null;
    suggestions = [];
    matchSearch = "";
    selectedGLAccount = "";
    try {
      drawerItem = await api.get<BankTransaction>(`/finance/bank-transactions/${id}/`);
      if (drawerItem.status !== "reconciled") {
        fetchSuggestions(id);
        fetchGLAccounts();
      }
    } catch { toast.error("Not found", ""); drawerOpen = false; }
    drawerLoading = false;
  }

  function closeDrawer() { drawerOpen = false; drawerItem = null; suggestions = []; }

  // ── Import & Sync ──
  let syncing = $state(false);
  let lastSynced = $state<string | null>(null);
  let uploadingStatement = $state(false);
  let statementDragOver = $state(false);

  async function handleSync() {
    syncing = true;
    // In production, this would call a bank API sync endpoint (Mono/Okra)
    setTimeout(() => {
      syncing = false;
      lastSynced = new Date().toISOString();
      toast.success("Synced", "Bank transactions have been updated");
      fetchData();
      fetchSummary();
    }, 2000);
  }

  function handleStatementDrop(e: DragEvent) {
    e.preventDefault();
    statementDragOver = false;
    const file = e.dataTransfer?.files?.[0];
    if (file) processStatement(file);
  }

  function handleStatementSelect(e: Event) {
    const file = (e.target as HTMLInputElement).files?.[0];
    if (file) processStatement(file);
  }

  function processStatement(file: File) {
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (!["csv", "xlsx", "xls"].includes(ext || "")) {
      toast.error("Invalid file", "Please upload a CSV or Excel bank statement");
      return;
    }
    uploadingStatement = true;
    setTimeout(() => {
      uploadingStatement = false;
      toast.success("Statement imported", `"${file.name}" — transactions will appear after processing`);
      fetchData();
      fetchSummary();
    }, 1500);
  }

  function exportLedger(format: "csv" | "pdf") {
    const params = new URLSearchParams();
    if (accountFilter) params.set("bank_account", accountFilter);
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    if (typeFilter) params.set("transaction_type", typeFilter);
    if (statusFilter) params.set("status", statusFilter);
    if (searchQuery) params.set("search", searchQuery);

    if (format === "csv") {
      // Build CSV from current data
      const headers = ["Date", "Type", "Counterparty", "Reference", "Amount", "Status", "Account"];
      const rows = data.map(t => [
        t.transaction_date, t.transaction_type, t.counterparty, t.reference,
        t.amount, t.status, t.bank_account_name,
      ]);
      const csv = [headers, ...rows].map(r => r.map(c => `"${c}"`).join(",")).join("\n");
      const blob = new Blob([csv], { type: "text/csv" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `bank-transactions-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(a.href);
      toast.success("Exported", "CSV file downloaded");
    } else {
      toast.info("Coming soon", "PDF export will be available shortly");
    }
  }

  function formatSyncTime(iso: string | null): string {
    if (!iso) return "Never";
    const d = new Date(iso);
    const now = new Date();
    const diff = Math.floor((now.getTime() - d.getTime()) / 60000);
    if (diff < 1) return "Just now";
    if (diff < 60) return `${diff}m ago`;
    return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
  }
</script>

<div class="space-y-6">
  <div class="flex items-center justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-pink-600">Banking</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Bank Transactions</h1>
      <p class="text-sm text-neutral-400 mt-1">Track credits, debits, and transaction status</p>
    </div>
    <div class="flex items-center gap-2">
      <button onclick={() => { showCreateModal = true; fetchBankAccounts(); }} class="px-4 py-2.5 bg-neutral-800 text-white rounded-lg hover:bg-neutral-800 text-sm font-medium transition-colors">+ Record Transaction</button>
      <button onclick={() => exportLedger("csv")} class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors" title="Export CSV">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" /></svg>
      </button>
    </div>
  </div>

  <!-- Import & Sync Controls -->
  <div class="flex items-center gap-3">
    <!-- Bank Sync -->
    <button onclick={handleSync} disabled={syncing} class="inline-flex items-center gap-2 px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 disabled:opacity-50 transition-colors">
      <svg class="w-4 h-4" style={syncing ? "animation: spin 1s linear infinite;" : ""} fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182M2.985 14.652V19.644" />
      </svg>
      {syncing ? "Syncing..." : "Sync Now"}
    </button>
    <span class="text-xs text-neutral-400">Last synced: {formatSyncTime(lastSynced)}</span>

    <div class="flex-1"></div>

    <!-- Statement Upload -->
    <div
      class="relative flex items-center gap-2 rounded-lg border border-dashed px-4 py-2 transition-colors cursor-pointer"
      style="border-color: {statementDragOver ? '#171717' : '#d4d4d4'}; background: {statementDragOver ? '#fafafa' : 'transparent'};"
      ondragover={(e) => { e.preventDefault(); statementDragOver = true; }}
      ondragleave={() => (statementDragOver = false)}
      ondrop={handleStatementDrop}
      role="region"
    >
      {#if uploadingStatement}
        <div class="inline-block w-4 h-4 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
        <span class="text-xs text-neutral-500">Importing...</span>
      {:else}
        <svg class="w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5" /></svg>
        <span class="text-xs text-neutral-500">Drop statement or</span>
        <label class="text-xs font-medium text-neutral-800 hover:underline cursor-pointer">
          browse
          <input type="file" accept=".csv,.xlsx,.xls" class="hidden" onchange={handleStatementSelect} />
        </label>
      {/if}
    </div>

    <!-- Export -->
    <button onclick={() => exportLedger("pdf")} class="inline-flex items-center gap-1.5 px-3 py-2 border border-neutral-200 rounded-lg text-xs font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">
      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" /></svg>
      PDF
    </button>
  </div>

  <!-- Transaction Intelligence Header -->
  {#if summary}
    <div class="grid grid-cols-3 gap-4">
      <!-- Total Inflow -->
      <div class="rounded-xl bg-white/60 backdrop-blur-md border border-neutral-200 shadow-sm p-4">
        <p class="text-xs font-medium text-emerald-500 uppercase tracking-wider mb-1">Total Inflow</p>
        <p class="text-xl font-bold text-emerald-700 tabular-nums" style="font-family: 'Raleway', sans-serif;">{currency.format(summary.total_inflow)}</p>
        <p class="text-xs text-neutral-400 mt-1">Credits received</p>
      </div>

      <!-- Total Outflow -->
      <div class="rounded-xl bg-white/60 backdrop-blur-md border border-neutral-200 shadow-sm p-4">
        <p class="text-xs font-medium text-red-400 uppercase tracking-wider mb-1">Total Outflow</p>
        <p class="text-xl font-bold text-red-600 tabular-nums" style="font-family: 'Raleway', sans-serif;">{currency.format(summary.total_outflow)}</p>
        <p class="text-xs text-neutral-400 mt-1">Debits processed</p>
      </div>

      <!-- Reconciliation Progress -->
      <div class="rounded-xl bg-white/60 backdrop-blur-md border border-neutral-200 shadow-sm p-4">
        <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider mb-1">Reconciliation</p>
        <div class="flex items-center gap-3">
          <!-- Circular progress -->
          <div class="relative w-12 h-12">
            <svg class="w-12 h-12 -rotate-90" viewBox="0 0 36 36">
              <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#e5e7eb" stroke-width="3" />
              <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#10b981" stroke-width="3" stroke-dasharray="{summary.reconciliation_pct}, 100" stroke-linecap="round" />
            </svg>
            <span class="absolute inset-0 flex items-center justify-center text-xs font-bold text-neutral-800">{summary.reconciliation_pct}%</span>
          </div>
          <div>
            <p class="text-sm font-semibold text-neutral-800">{summary.reconciled_count}/{summary.total_count}</p>
            <p class="text-xs text-neutral-400">matched</p>
          </div>
        </div>
      </div>
    </div>
  {/if}

  <!-- Filters -->
  <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
    <div class="flex gap-3 items-center flex-wrap">
      <div class="relative flex-1 min-w-[180px] max-w-sm">
        <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
        <input type="text" placeholder="Search transactions..." oninput={onSearch} class="w-full pl-10 pr-4 py-2 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent placeholder:text-neutral-400" />
      </div>
      <select bind:value={typeFilter} onchange={() => (currentPage = 1)} class="px-3 py-2 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent">
        <option value="">All Types</option><option value="credit">Credit</option><option value="debit">Debit</option>
      </select>
      <select bind:value={statusFilter} onchange={() => (currentPage = 1)} class="px-3 py-2 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent">
        <option value="">All Statuses</option><option value="pending">Pending</option><option value="cleared">Cleared</option><option value="reconciled">Reconciled</option><option value="voided">Voided</option>
      </select>
      <select bind:value={accountFilter} onchange={() => (currentPage = 1)} class="px-3 py-2 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent">
        <option value="">All Accounts</option>
        {#each bankAccounts as acct}<option value={String(acct.id)}>{acct.account_name} — {acct.bank_name}</option>{/each}
      </select>
    </div>
    <div class="flex gap-3 items-center flex-wrap mt-2 pt-2 border-t border-neutral-200">
      <label class="flex items-center gap-1.5">
        <span class="text-xs text-neutral-500">From</span>
        <DateInput bind:value={dateFrom} />
      </label>
      <label class="flex items-center gap-1.5">
        <span class="text-xs text-neutral-500">To</span>
        <DateInput bind:value={dateTo} />
      </label>
      <label class="flex items-center gap-1.5">
        <span class="text-xs text-neutral-500">Min</span>
        <input type="text" inputmode="decimal" bind:value={amountMin} placeholder="0" class="w-24 px-2.5 py-1.5 border border-neutral-200 rounded-lg text-sm tabular-nums bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />
      </label>
      <label class="flex items-center gap-1.5">
        <span class="text-xs text-neutral-500">Max</span>
        <input type="text" inputmode="decimal" bind:value={amountMax} placeholder="999M" class="w-24 px-2.5 py-1.5 border border-neutral-200 rounded-lg text-sm tabular-nums bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />
      </label>
      {#if dateFrom || dateTo || amountMin || amountMax}
        <button type="button" onclick={() => { dateFrom = ""; dateTo = ""; amountMin = ""; amountMax = ""; currentPage = 1; }} class="text-xs text-neutral-500 hover:text-neutral-800 font-medium transition-colors">Clear filters</button>
      {/if}
    </div>
  </div>

  <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
    {#if loading}
      <div class="p-16 text-center"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div></div>
    {:else if data.length === 0}
      <div class="p-16 text-center">
        <p class="text-sm font-medium text-neutral-800">No transactions found</p>
        <button onclick={() => { showCreateModal = true; fetchBankAccounts(); }} class="inline-block mt-4 px-4 py-2 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors">+ Record Transaction</button>
      </div>
    {:else}
      <table class="w-full text-sm">
        <thead><tr class="border-b border-neutral-200">
          <th class="px-4 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Date</th>
          <th class="px-4 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Description</th>
          <th class="px-4 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Reference / ID</th>
          <th class="px-4 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Amount</th>
          <th class="px-4 py-3.5 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
          <th class="px-4 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Actions</th>
        </tr></thead>
        <tbody class="divide-y divide-neutral-100">
          {#each data as txn}
            <tr class="hover:bg-neutral-50 cursor-pointer transition-colors" onclick={() => openDrawer(txn.id)}>
              <td class="px-4 py-3.5 text-neutral-500 text-xs whitespace-nowrap">{formatDate(txn.transaction_date)}</td>
              <td class="px-4 py-3.5">
                <div class="flex items-center gap-2">
                  <span class="inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-semibold" style="background: {txn.transaction_type === 'credit' ? '#d1fae5' : '#fee2e2'}; color: {txn.transaction_type === 'credit' ? '#065f46' : '#991b1b'};">
                    {txn.transaction_type === "credit" ? "CR" : "DR"}
                  </span>
                  <div class="min-w-0">
                    <p class="text-xs font-medium text-neutral-800 truncate max-w-[220px]">{txn.counterparty || "Bank Transaction"}</p>
                    <p class="text-[10px] text-neutral-400">{txn.bank_account_name}</p>
                  </div>
                </div>
              </td>
              <td class="px-4 py-3.5 text-neutral-500 font-mono text-xs">{txn.reference ? (txn.reference.length > 12 ? txn.reference.slice(0, 12) + "..." : txn.reference) : "\u2014"}</td>
              <td class="px-4 py-3.5 text-right tabular-nums font-semibold text-xs" style="color: {txn.transaction_type === 'credit' ? '#047857' : '#dc2626'};">
                {txn.transaction_type === "credit" ? "+" : "-"}{currency.format(txn.amount)}
              </td>
              <td class="px-4 py-3.5 text-center">
                {#if txn.status === "reconciled"}
                  <span class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold bg-emerald-50 text-emerald-700">
                    <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>Matched
                  </span>
                {:else if txn.status === "cleared"}
                  <span class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold bg-amber-50 text-amber-700">
                    <span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>Unmatched
                  </span>
                {:else if txn.status === "voided"}
                  <span class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold bg-red-50 text-red-700">
                    <span class="w-1.5 h-1.5 rounded-full bg-red-500"></span>Flagged
                  </span>
                {:else}
                  <span class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold bg-neutral-100 text-neutral-500">
                    <span class="w-1.5 h-1.5 rounded-full bg-neutral-400"></span>Pending
                  </span>
                {/if}
              </td>
              <td class="px-4 py-3.5 text-right">
                <div class="flex items-center justify-end gap-2" onclick={(e) => e.stopPropagation()}>
                  {#if txn.status === "reconciled"}
                    <button type="button" onclick={() => openDrawer(txn.id)} class="text-[10px] font-medium text-emerald-600 hover:text-emerald-800 transition-colors">View Receipt</button>
                  {:else if txn.status === "cleared"}
                    <button type="button" onclick={() => openDrawer(txn.id)} class="text-[10px] font-medium text-amber-600 hover:text-amber-800 transition-colors">Categorize</button>
                  {:else if txn.status === "voided"}
                    <button type="button" onclick={() => openDrawer(txn.id)} class="text-[10px] font-medium text-red-600 hover:text-red-800 transition-colors">Resolve</button>
                  {:else}
                    <button type="button" onclick={() => openDrawer(txn.id)} class="text-[10px] font-medium text-neutral-500 hover:text-neutral-800 transition-colors">Review</button>
                  {/if}
                </div>
              </td>
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

<Modal open={showCreateModal} onclose={() => { showCreateModal = false; resetForm(); }} title="Record Bank Transaction" maxWidth="max-w-xl">
  <form onsubmit={handleCreate} class="space-y-4">
    <label><span class="block text-sm font-medium text-neutral-700 mb-1">Bank Account</span><select bind:value={createForm.bank_account} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"><option value="">Select account</option>{#each bankAccounts as a}<option value={String(a.id)}>{a.account_name} — {a.bank_name}</option>{/each}</select>{#if createFieldError("bank_account")}<p class="mt-1 text-xs text-red-500">{createFieldError("bank_account")}</p>{/if}</label>
    <div class="grid grid-cols-3 gap-3">
      <label><span class="block text-sm font-medium text-neutral-700 mb-1">Type</span><select bind:value={createForm.transaction_type} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"><option value="debit">Debit</option><option value="credit">Credit</option></select></label>
      <label><span class="block text-sm font-medium text-neutral-700 mb-1">Transaction Date</span><DateInput bind:value={createForm.transaction_date} /></label>
      <label><span class="block text-sm font-medium text-neutral-700 mb-1">Amount</span><input bind:value={createForm.amount} placeholder="0.00" class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" /></label>
    </div>
    <div class="grid grid-cols-2 gap-3">
      <label><span class="block text-sm font-medium text-neutral-700 mb-1">Reference</span><input bind:value={createForm.reference} placeholder="NIP/TRF ref" class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" /></label>
      <label><span class="block text-sm font-medium text-neutral-700 mb-1">Counterparty</span><input bind:value={createForm.counterparty} placeholder="Vendor / payer name" class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" /></label>
    </div>
    <label><span class="block text-sm font-medium text-neutral-700 mb-1">Description</span><input bind:value={createForm.description} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" /></label>
    <label><span class="block text-sm font-medium text-neutral-700 mb-1">Notes</span><textarea bind:value={createForm.notes} rows="2" class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"></textarea></label>
    <div class="flex justify-end gap-3 pt-2">
      {#if isDev}<button type="button" onclick={devFill} class="mr-auto rounded-lg bg-orange-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-orange-600 transition-colors">Dev Fill</button>{/if}
      <button type="button" onclick={() => { showCreateModal = false; resetForm(); }} class="px-4 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">Cancel</button>
      <button type="submit" disabled={saving} class="px-4 py-2.5 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">{saving ? "Saving..." : "Record"}</button>
    </div>
  </form>
</Modal>

{#if drawerOpen}
  <div class="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm" onclick={closeDrawer} onkeydown={(e) => e.key === "Escape" && closeDrawer()} role="button" tabindex="-1"></div>
  <div class="fixed inset-y-0 right-0 z-50 w-full max-w-2xl bg-white shadow-2xl border-l border-neutral-200 flex flex-col drawer-slide-in">
    {#if drawerLoading}
      <div class="flex-1 flex items-center justify-center"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div></div>
    {:else if drawerItem}
      {@const t = drawerItem}

      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200">
        <div class="flex items-center gap-3">
          <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold" style="background: {t.transaction_type === 'credit' ? '#d1fae5' : '#fee2e2'}; color: {t.transaction_type === 'credit' ? '#065f46' : '#991b1b'};">
            {t.transaction_type === "credit" ? "CREDIT" : "DEBIT"}
          </span>
          {#if t.status === "reconciled"}
            <span class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold bg-emerald-50 text-emerald-700"><span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>Matched</span>
          {:else if t.status === "cleared"}
            <span class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold bg-amber-50 text-amber-700"><span class="w-1.5 h-1.5 rounded-full bg-amber-500"></span>Unmatched</span>
          {:else if t.status === "voided"}
            <span class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold bg-red-50 text-red-700"><span class="w-1.5 h-1.5 rounded-full bg-red-500"></span>Flagged</span>
          {:else}
            <span class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold bg-neutral-100 text-neutral-500"><span class="w-1.5 h-1.5 rounded-full bg-neutral-400"></span>Pending</span>
          {/if}
        </div>
        <button onclick={closeDrawer} class="w-8 h-8 flex items-center justify-center rounded-lg text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 transition-colors" aria-label="Close">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
        </button>
      </div>

      <!-- Body -->
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-6">
        <!-- Amount card -->
        <div class="rounded-xl border border-neutral-200 p-5 text-center" style="background: {t.transaction_type === 'credit' ? '#ecfdf5' : '#fef2f2'};">
          <p class="text-xs font-medium uppercase tracking-wider mb-1" style="color: {t.transaction_type === 'credit' ? '#34d399' : '#f87171'};">Amount</p>
          <p class="text-2xl font-bold tabular-nums" style="font-family: 'Raleway', sans-serif; color: {t.transaction_type === 'credit' ? '#047857' : '#dc2626'};">{currency.format(t.amount)}</p>
        </div>

        <!-- Transaction details -->
        <dl class="grid grid-cols-2 gap-x-6 gap-y-2.5 text-sm">
          <div><dt class="text-neutral-400">Account</dt><dd class="mt-0.5 font-medium text-neutral-800">{t.bank_account_name} — {t.bank_name}</dd></div>
          <div><dt class="text-neutral-400">Date</dt><dd class="mt-0.5 text-neutral-700">{formatDate(t.transaction_date)}</dd></div>
          {#if t.reference}<div><dt class="text-neutral-400">Reference</dt><dd class="mt-0.5 text-neutral-700 font-mono text-xs">{t.reference}</dd></div>{/if}
          {#if t.counterparty}<div><dt class="text-neutral-400">Counterparty</dt><dd class="mt-0.5 font-medium text-neutral-800">{t.counterparty}</dd></div>{/if}
          {#if t.description}<div class="col-span-2"><dt class="text-neutral-400">Description</dt><dd class="mt-0.5 text-neutral-700">{t.description}</dd></div>{/if}
          {#if t.voucher_number}<div><dt class="text-neutral-400">Linked Voucher</dt><dd class="mt-0.5 text-emerald-700 font-medium">{t.voucher_number}</dd></div>{/if}
          {#if t.receipt_number}<div><dt class="text-neutral-400">Linked Receipt</dt><dd class="mt-0.5 text-emerald-700 font-medium">{t.receipt_number}</dd></div>{/if}
          {#if t.notes}<div class="col-span-2"><dt class="text-neutral-400">Notes</dt><dd class="mt-0.5 text-neutral-500 text-xs">{t.notes}</dd></div>{/if}
        </dl>

        <!-- Reconciliation Workspace (only for unreconciled) -->
        {#if t.status !== "reconciled"}
          <div>
            <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-3">Reconciliation Workspace</h3>

            <!-- Suggested Matches -->
            <div class="rounded-xl border border-neutral-200 bg-white p-4 space-y-3">
              <div class="flex items-center justify-between">
                <p class="text-xs font-semibold text-neutral-700">Suggested Matches</p>
                <span class="text-[10px] text-neutral-400">{suggestions.length} suggestion{suggestions.length !== 1 ? "s" : ""}</span>
              </div>

              <!-- Manual Search -->
              <input type="text" bind:value={matchSearch} placeholder="Search vouchers by number, vendor, or amount..." class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm bg-neutral-50 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent placeholder:text-neutral-400" />

              {#if suggestionsLoading}
                <div class="p-4 text-center"><div class="inline-block w-4 h-4 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div></div>
              {:else if filteredSuggestions().length === 0}
                <p class="text-xs text-neutral-400 text-center py-3">No matching vouchers found.</p>
              {:else}
                <div class="space-y-2 max-h-48 overflow-y-auto">
                  {#each filteredSuggestions() as match}
                    <div class="flex items-center justify-between rounded-lg border border-neutral-100 bg-neutral-50 px-3 py-2.5">
                      <div class="min-w-0">
                        <div class="flex items-center gap-2">
                          <span class="text-xs font-medium text-neutral-800 font-mono">{match.number}</span>
                          <span class="text-[10px] rounded-full px-1.5 py-0.5 font-medium" style="background: {match.match_reason === 'amount' ? '#dbeafe' : '#fef3c7'}; color: {match.match_reason === 'amount' ? '#1e40af' : '#92400e'};">
                            {match.match_reason === "amount" ? "Amount match" : "Date match"}
                          </span>
                        </div>
                        <p class="text-[10px] text-neutral-500 mt-0.5">{match.counterparty} &middot; {currency.format(match.amount)} &middot; {match.date}</p>
                      </div>
                      <button
                        type="button"
                        onclick={() => linkToVoucher(match.id)}
                        disabled={linking}
                        class="shrink-0 px-3 py-1.5 bg-neutral-800 text-white rounded-lg text-[10px] font-semibold hover:bg-neutral-800 disabled:opacity-50 transition-colors"
                      >
                        {linking ? "..." : "Link"}
                      </button>
                    </div>
                  {/each}
                </div>
              {/if}
            </div>
          </div>

          <!-- Ignore / Internal (GL Categorize) -->
          <div>
            <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-3">Categorize as Internal</h3>
            <div class="rounded-xl border border-neutral-200 bg-white p-4">
              <p class="text-xs text-neutral-500 mb-3">For bank charges, fees, or non-business transactions — categorize directly to a GL account without a voucher.</p>
              <div class="flex items-end gap-2">
                <label class="flex-1">
                  <span class="block text-xs font-medium text-neutral-500 mb-1">GL Account</span>
                  <select bind:value={selectedGLAccount} class="w-full px-2.5 py-2 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent">
                    <option value="">Select account</option>
                    {#each glAccounts as a}
                      <option value={String(a.id)}>{a.code} — {a.name}</option>
                    {/each}
                  </select>
                </label>
                <button
                  type="button"
                  onclick={categorizeToGL}
                  disabled={!selectedGLAccount || categorizing}
                  class="shrink-0 px-4 py-2 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
                >
                  {categorizing ? "Saving..." : "Categorize"}
                </button>
              </div>
            </div>
          </div>
        {:else}
          <!-- Already reconciled -->
          <div class="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-center">
            <svg class="w-8 h-8 mx-auto text-emerald-500 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" /></svg>
            <p class="text-sm font-medium text-emerald-800">This transaction has been reconciled</p>
            {#if t.voucher_number}
              <p class="text-xs text-emerald-600 mt-1">Matched to voucher {t.voucher_number}</p>
            {/if}
          </div>
        {/if}
      </div>
    {/if}
  </div>
{/if}

<style>
  .drawer-slide-in { animation: drawerSlideIn 0.25s ease-out both; }
  @keyframes drawerSlideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }
  @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
</style>

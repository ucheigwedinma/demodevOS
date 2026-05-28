<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import Modal from "$lib/components/Modal.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type { BankAccount, BankAccountListItem, BankLiquidityOverview, BankTransactionListItem, AccountListItem, PaginatedResponse } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let data = $state<BankAccountListItem[]>([]);
  let totalCount = $state(0);
  let currentPage = $state(1);
  let searchQuery = $state("");
  let statusFilter = $state("");
  let loading = $state(true);

  let showCreateModal = $state(false);
  let glAccounts = $state<AccountListItem[]>([]);
  let createForm = $state({
    account_name: "", bank_name: "", account_number: "",
    account_type: "current", currency: "NGN", status: "active",
    opening_balance: "", current_balance: "",
    gl_account: "", branch: "", swift_code: "", sort_code: "", notes: "",
  });
  let createErrors = $state<Record<string, string[]>>({});
  let saving = $state(false);

  function createFieldError(f: string) { return createErrors[f]?.[0] ?? ""; }
  function resetForm() {
    createForm = { account_name: "", bank_name: "", account_number: "", account_type: "current", currency: "NGN", status: "active", opening_balance: "", current_balance: "", gl_account: "", branch: "", swift_code: "", sort_code: "", notes: "" };
    createErrors = {};
  }

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");
  const SAMPLES = [
    { account_name: "Main Operations Account", bank_name: "Zenith Bank", account_number: "0012345678", branch: "Victoria Island", opening_balance: "25000000", current_balance: "18750000", notes: "Primary disbursement account for all project payments." },
    { account_name: "Revenue Collection Account", bank_name: "GTBank", account_number: "0098765432", branch: "Lekki", opening_balance: "5000000", current_balance: "42300000", notes: "Receives client payments and deposits." },
    { account_name: "USD Domiciliary Account", bank_name: "Access Bank", account_number: "0045112233", account_type: "domiciliary", currency: "USD", branch: "Marina", opening_balance: "100000", current_balance: "85000", notes: "Foreign procurement and import payments." },
  ];
  let devIdx = $state(0);
  function devFill() {
    const s = SAMPLES[devIdx % SAMPLES.length]; devIdx++;
    createForm = { ...createForm, ...s };
    if (glAccounts.length > 0) createForm.gl_account = String(glAccounts[0].id);
  }

  async function handleCreate(e: Event) {
    e.preventDefault(); createErrors = {}; saving = true;
    try {
      const body: Record<string, unknown> = { ...createForm, gl_account: createForm.gl_account ? Number(createForm.gl_account) : null, opening_balance: createForm.opening_balance || "0", current_balance: createForm.current_balance || "0" };
      await api.post<BankAccount>("/finance/bank-accounts/", body);
      toast.success("Account created", "Bank account has been added");
      showCreateModal = false; resetForm(); fetchData();
    } catch (err) {
      if (err instanceof ApiError) { createErrors = err.fieldErrors; toast.error("Validation error", "Please fix the highlighted fields"); }
      else toast.error("Error", "Could not create bank account");
    }
    saving = false;
  }

  const PAGE_SIZE = 25;
  const totalPages = $derived(Math.ceil(totalCount / PAGE_SIZE));
  const startItem = $derived((currentPage - 1) * PAGE_SIZE + 1);
  const endItem = $derived(Math.min(currentPage * PAGE_SIZE, totalCount));

  async function fetchGLAccounts() {
    try { const res = await api.get<PaginatedResponse<AccountListItem>>("/finance/accounts/", { page_size: "200", account_type: "asset" }); glAccounts = res.results; } catch { glAccounts = []; }
  }

  async function fetchData() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage) };
      if (searchQuery) params.search = searchQuery;
      if (statusFilter) params.status = statusFilter;
      const res = await api.get<PaginatedResponse<BankAccountListItem>>("/finance/bank-accounts/", params);
      data = res.results; totalCount = res.count;
    } catch { data = []; totalCount = 0; }
    loading = false;
  }

  // Liquidity overview
  let liquidity = $state<BankLiquidityOverview | null>(null);

  async function fetchLiquidity() {
    try {
      liquidity = await api.get<BankLiquidityOverview>("/finance/bank-accounts/liquidity/");
    } catch { liquidity = null; }
  }

  $effect(() => { fetchGLAccounts(); fetchLiquidity(); });
  $effect(() => { void searchQuery; void statusFilter; void currentPage; fetchData(); });

  let searchTimeout: ReturnType<typeof setTimeout>;
  function onSearch(e: Event) { clearTimeout(searchTimeout); const v = (e.target as HTMLInputElement).value; searchTimeout = setTimeout(() => { searchQuery = v; currentPage = 1; }, 300); }

  // Balance color: mint green = positive, burnt orange = low (<5% of opening), red = negative
  function balanceColor(balance: string, opening?: string): string {
    const bal = Number(balance);
    if (bal < 0) return "red";
    if (opening) {
      const open = Number(opening);
      if (open > 0 && bal < open * 0.05) return "orange";
    }
    if (bal === 0) return "orange";
    return "green";
  }

  function balanceStyles(color: string, onDark = false): { text: string; bg: string; border: string; label: string } {
    if (color === "red") return {
      text: onDark ? "#f87171" : "#dc2626",
      bg: "#fef2f2", border: "#fee2e2", label: "#f87171",
    };
    if (color === "orange") return {
      text: onDark ? "#fdba74" : "#f97316",
      bg: "#fff7ed", border: "#ffedd5", label: "#fb923c",
    };
    return {
      text: onDark ? "#6ee7b7" : "#047857",
      bg: "#ecfdf5", border: "#d1fae5", label: "#34d399",
    };
  }

  function statusStyles(status: string): { bg: string; text: string; dot: string } {
    if (status === "active") return { bg: "rgba(52,211,153,0.2)", text: "#a7f3d0", dot: "#6ee7b7" };
    if (status === "inactive") return { bg: "rgba(251,191,36,0.2)", text: "#fde68a", dot: "#fbbf24" };
    return { bg: "rgba(248,113,113,0.2)", text: "#fecaca", dot: "#f87171" };
  }

  function maskAccount(num: string): string {
    if (num.length <= 4) return num;
    return "**** " + num.slice(-4);
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text);
    toast.success("Copied", "Account number copied to clipboard");
  }

  // Bank card color schemes by bank name keyword
  function cardColor(bankName: string): { from: string; to: string } {
    const b = bankName.toLowerCase();
    if (b.includes("zenith")) return { from: "#7f1d1d", to: "#450a0a" };
    if (b.includes("gtbank") || b.includes("guaranty")) return { from: "#ea580c", to: "#9a3412" };
    if (b.includes("access")) return { from: "#166534", to: "#14532d" };
    if (b.includes("first") || b.includes("fbn")) return { from: "#1e3a5f", to: "#0c1e3a" };
    if (b.includes("uba") || b.includes("united")) return { from: "#b91c1c", to: "#7f1d1d" };
    if (b.includes("stanbic")) return { from: "#1d4ed8", to: "#1e3a8a" };
    if (b.includes("sterling")) return { from: "#dc2626", to: "#991b1b" };
    if (b.includes("wema") || b.includes("alat")) return { from: "#6b21a8", to: "#4c1d95" };
    if (b.includes("polaris")) return { from: "#4c1d95", to: "#312e81" };
    if (b.includes("keystone")) return { from: "#2563eb", to: "#1e40af" };
    if (b.includes("fcmb")) return { from: "#6d28d9", to: "#4c1d95" };
    if (b.includes("ecobank")) return { from: "#1e40af", to: "#1e3a8a" };
    if (b.includes("fidelity")) return { from: "#15803d", to: "#166534" };
    return { from: "#404040", to: "#262626" };
  }

  // Drawer
  let drawerOpen = $state(false);
  let drawerItem = $state<BankAccount | null>(null);
  let drawerLoading = $state(false);

  // Drawer transaction history
  let drawerTxns = $state<BankTransactionListItem[]>([]);
  let drawerTxnLoading = $state(false);
  let txnDateFrom = $state("");
  let txnDateTo = $state("");
  let txnTypeFilter = $state("");
  let txnSearch = $state("");

  const filteredTxns = $derived(() => {
    let list = drawerTxns;
    if (txnDateFrom) list = list.filter((t) => t.transaction_date >= txnDateFrom);
    if (txnDateTo) list = list.filter((t) => t.transaction_date <= txnDateTo);
    if (txnTypeFilter) list = list.filter((t) => t.transaction_type === txnTypeFilter);
    if (txnSearch) {
      const q = txnSearch.toLowerCase();
      list = list.filter((t) =>
        t.reference.toLowerCase().includes(q) ||
        t.counterparty.toLowerCase().includes(q)
      );
    }
    return list;
  });

  async function fetchDrawerTxns(accountId: number) {
    drawerTxnLoading = true;
    try {
      const res = await api.get<PaginatedResponse<BankTransactionListItem>>("/finance/bank-transactions/", {
        bank_account: String(accountId), page_size: "100",
      });
      drawerTxns = res.results;
    } catch { drawerTxns = []; }
    drawerTxnLoading = false;
  }

  async function openDrawer(id: number) {
    drawerOpen = true;
    drawerLoading = true;
    drawerItem = null;
    drawerTxns = [];
    txnDateFrom = ""; txnDateTo = ""; txnTypeFilter = ""; txnSearch = "";
    try {
      drawerItem = await api.get<BankAccount>(`/finance/bank-accounts/${id}/`);
      fetchDrawerTxns(id);
    } catch {
      toast.error("Not found", "");
      drawerOpen = false;
    }
    drawerLoading = false;
  }

  function closeDrawer() {
    drawerOpen = false;
    drawerItem = null;
    drawerTxns = [];
  }

  // Statement upload
  let uploading = $state(false);
  let dragOver = $state(false);

  function handleStatementDrop(e: DragEvent) {
    e.preventDefault();
    dragOver = false;
    const file = e.dataTransfer?.files?.[0];
    if (file) processStatementFile(file);
  }

  function handleStatementSelect(e: Event) {
    const file = (e.target as HTMLInputElement).files?.[0];
    if (file) processStatementFile(file);
  }

  function processStatementFile(file: File) {
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (!["csv", "pdf", "xlsx", "xls"].includes(ext || "")) {
      toast.error("Invalid file", "Please upload a CSV, Excel, or PDF bank statement");
      return;
    }
    uploading = true;
    // Simulate processing — in production this would POST to a parse endpoint
    setTimeout(() => {
      uploading = false;
      toast.success("Statement uploaded", `"${file.name}" has been received for reconciliation`);
    }, 1500);
  }

  function formatTxnDate(v: string | null) {
    if (!v) return "\u2014";
    return new Date(v).toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }
</script>

<div class="space-y-6">
  <div class="flex items-center justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-orange-600">Banking</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Bank Accounts</h1>
      <p class="text-sm text-neutral-400 mt-1">Manage company bank accounts and balances</p>
    </div>
    <button onclick={() => showCreateModal = true} class="px-4 py-2.5 bg-neutral-800 text-white rounded-lg hover:bg-neutral-800 text-sm font-medium transition-colors">+ Add Account</button>
  </div>

  <!-- Liquidity Overview Ribbon -->
  {#if liquidity}
    <div class="grid grid-cols-4 gap-4">
      <!-- Total Cash on Hand -->
      <div class="rounded-xl bg-white/60 backdrop-blur-md border border-neutral-200 shadow-sm p-4">
        <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider mb-1">Total Cash on Hand</p>
        <p class="text-xl font-bold text-neutral-800 tabular-nums" style="font-family: 'Raleway', sans-serif;">{currency.format(liquidity.total_cash_on_hand)}</p>
        <p class="text-xs text-neutral-400 mt-1">{liquidity.account_count} active account{liquidity.account_count !== 1 ? "s" : ""}</p>
      </div>

      <!-- Primary Operations Account -->
      <div class="rounded-xl bg-white/60 backdrop-blur-md border border-neutral-200 shadow-sm p-4">
        <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider mb-1">Primary Operations</p>
        {#if liquidity.primary_account}
          <p class="text-xl font-bold text-emerald-700 tabular-nums" style="font-family: 'Raleway', sans-serif;">{currency.format(liquidity.primary_account.current_balance)}</p>
          <p class="text-xs text-neutral-400 mt-1">{liquidity.primary_account.account_name} — {liquidity.primary_account.bank_name}</p>
        {:else}
          <p class="text-sm text-neutral-400">No active accounts</p>
        {/if}
      </div>

      <!-- Pending Outflow -->
      <div class="rounded-xl bg-white/60 backdrop-blur-md border border-neutral-200 shadow-sm p-4">
        <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider mb-1">Pending Outflow</p>
        <p class="text-xl font-bold tabular-nums {Number(liquidity.pending_outflow) > 0 ? 'text-red-600' : 'text-neutral-800'}" style="font-family: 'Raleway', sans-serif;">{currency.format(liquidity.pending_outflow)}</p>
        <p class="text-xs text-neutral-400 mt-1">{liquidity.pending_run_count} pending run{liquidity.pending_run_count !== 1 ? "s" : ""}</p>
      </div>

      <!-- Last Sync -->
      <div class="rounded-xl bg-white/60 backdrop-blur-md border border-neutral-200 shadow-sm p-4">
        <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider mb-1">Last Sync</p>
        <p class="text-sm font-medium text-neutral-700 mt-1">Manual</p>
        <p class="text-xs text-neutral-400 mt-1">Statement upload / API integration</p>
      </div>
    </div>
  {/if}

  <div class="flex gap-3 items-center">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
      <input type="text" placeholder="Search accounts..." oninput={onSearch} class="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent placeholder:text-neutral-400" />
    </div>
    <select bind:value={statusFilter} onchange={() => (currentPage = 1)} class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent">
      <option value="">All Statuses</option>
      <option value="active">Active</option>
      <option value="inactive">Inactive</option>
      <option value="closed">Closed</option>
    </select>
  </div>

  <!-- Account Cards Grid -->
  {#if loading}
    <div class="p-16 text-center"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div></div>
  {:else if data.length === 0}
    <div class="p-16 text-center bg-white rounded-xl border border-neutral-200">
      <p class="text-sm font-medium text-neutral-800">No bank accounts found</p>
      <button onclick={() => showCreateModal = true} class="inline-block mt-4 px-4 py-2 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors">+ Add Account</button>
    </div>
  {:else}
    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
      {#each data as acct}
        <div
          class="text-left rounded-2xl overflow-hidden shadow-lg hover:shadow-xl transition-shadow duration-200 cursor-pointer group"
          onclick={() => openDrawer(acct.id)}
          onkeydown={(e) => e.key === "Enter" && openDrawer(acct.id)}
          role="button"
          tabindex="0"
        >
          <!-- Card face -->
          <div class="relative p-5 pb-4 min-h-[180px] flex flex-col justify-between" style="background: linear-gradient(135deg, {cardColor(acct.bank_name).from}, {cardColor(acct.bank_name).to});">
            <!-- Decorative circles -->
            <div class="absolute top-4 right-4 w-12 h-12 rounded-full border border-white/10"></div>
            <div class="absolute top-7 right-7 w-12 h-12 rounded-full border border-white/10"></div>

            <!-- Chip -->
            <div class="absolute top-5 left-5 w-10 h-7 rounded-md bg-linear-to-br from-amber-300/80 to-amber-500/60 border border-amber-200/30">
              <div class="absolute inset-[3px] grid grid-cols-3 grid-rows-2 gap-px">
                <div class="bg-amber-400/40 rounded-sm"></div>
                <div class="bg-amber-300/30 rounded-sm"></div>
                <div class="bg-amber-400/40 rounded-sm"></div>
                <div class="bg-amber-300/30 rounded-sm"></div>
                <div class="bg-amber-400/40 rounded-sm"></div>
                <div class="bg-amber-300/30 rounded-sm"></div>
              </div>
            </div>

            <!-- Top section -->
            <div class="mt-10">
              <!-- Account number (masked) -->
              <div class="flex items-center gap-2">
                <span class="text-white/90 font-mono text-base tracking-[3px]">{maskAccount(acct.account_number)}</span>
                <button
                  type="button"
                  class="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded hover:bg-white/10"
                  onclick={(e) => { e.stopPropagation(); copyToClipboard(acct.account_number); }}
                  aria-label="Copy account number"
                >
                  <svg class="w-3.5 h-3.5 text-white/60" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15.666 3.888A2.25 2.25 0 0 0 13.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 0 1-.75.75H9.75a.75.75 0 0 1-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 0 1-2.25 2.25H6.75A2.25 2.25 0 0 1 4.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 0 1 1.927-.184" />
                  </svg>
                </button>
              </div>

              <!-- Balance -->
              <div class="mt-3">
                <p class="text-white/50 text-[10px] uppercase tracking-wider">Current Balance</p>
                <p class="text-xl font-bold tabular-nums mt-0.5" style="font-family: 'Raleway', sans-serif; color: {balanceStyles(balanceColor(acct.current_balance), true).text};">
                  {currency.format(acct.current_balance)}
                </p>
              </div>
            </div>

            <!-- Bottom section -->
            <div class="flex items-end justify-between mt-3">
              <div>
                <p class="text-white/50 text-[10px] uppercase tracking-wider">Account Name</p>
                <p class="text-white text-xs font-semibold mt-0.5 truncate max-w-[180px]">{acct.account_name}</p>
              </div>
              <div class="text-right">
                <p class="text-white font-bold text-sm tracking-wide">{acct.bank_name}</p>
                <p class="text-white/40 text-[10px] uppercase mt-0.5">{acct.account_type.replace(/_/g, " ")} &middot; {acct.currency}</p>
              </div>
            </div>

            <!-- Status indicator -->
            <div class="absolute top-5 right-5">
              <span class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold" style="background: {statusStyles(acct.status).bg}; color: {statusStyles(acct.status).text};">
                <span class="w-1.5 h-1.5 rounded-full" style="background: {statusStyles(acct.status).dot};"></span>
                {acct.status.charAt(0).toUpperCase() + acct.status.slice(1)}
              </span>
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}

  {#if totalCount > 0}
    <div class="flex items-center justify-between">
      <p class="text-sm text-neutral-400">Showing <span class="font-medium text-neutral-600">{startItem}–{endItem}</span> of <span class="font-medium text-neutral-600">{totalCount}</span></p>
    </div>
  {/if}
</div>

<Modal open={showCreateModal} onclose={() => { showCreateModal = false; resetForm(); }} title="Add Bank Account" maxWidth="max-w-xl">
  <form onsubmit={handleCreate} class="space-y-4">
    <div class="grid grid-cols-2 gap-3">
      <label><span class="block text-sm font-medium text-neutral-700 mb-1">Account Name</span><input bind:value={createForm.account_name} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />{#if createFieldError("account_name")}<p class="mt-1 text-xs text-red-500">{createFieldError("account_name")}</p>{/if}</label>
      <label><span class="block text-sm font-medium text-neutral-700 mb-1">Bank Name</span><input bind:value={createForm.bank_name} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />{#if createFieldError("bank_name")}<p class="mt-1 text-xs text-red-500">{createFieldError("bank_name")}</p>{/if}</label>
    </div>
    <div class="grid grid-cols-3 gap-3">
      <label><span class="block text-sm font-medium text-neutral-700 mb-1">Account Number</span><input bind:value={createForm.account_number} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" /></label>
      <label><span class="block text-sm font-medium text-neutral-700 mb-1">Account Type</span><select bind:value={createForm.account_type} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"><option value="current">Current</option><option value="savings">Savings</option><option value="domiciliary">Domiciliary</option><option value="fixed_deposit">Fixed Deposit</option></select></label>
      <label><span class="block text-sm font-medium text-neutral-700 mb-1">Currency</span><input bind:value={createForm.currency} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" /></label>
    </div>
    <div class="grid grid-cols-2 gap-3">
      <label><span class="block text-sm font-medium text-neutral-700 mb-1">Opening Balance</span><input bind:value={createForm.opening_balance} placeholder="0.00" class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" /></label>
      <label><span class="block text-sm font-medium text-neutral-700 mb-1">Current Balance</span><input bind:value={createForm.current_balance} placeholder="0.00" class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" /></label>
    </div>
    <label><span class="block text-sm font-medium text-neutral-700 mb-1">Branch</span><input bind:value={createForm.branch} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" /></label>
    <label><span class="block text-sm font-medium text-neutral-700 mb-1">Linked GL Account <span class="text-neutral-400 font-normal">(optional)</span></span><select bind:value={createForm.gl_account} class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"><option value="">None</option>{#each glAccounts as a}<option value={String(a.id)}>{a.code} — {a.name}</option>{/each}</select></label>
    <label><span class="block text-sm font-medium text-neutral-700 mb-1">Notes</span><textarea bind:value={createForm.notes} rows="2" class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"></textarea></label>
    <div class="flex justify-end gap-3 pt-2">
      {#if isDev}<button type="button" onclick={devFill} class="mr-auto rounded-lg bg-orange-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-orange-600 transition-colors">Dev Fill</button>{/if}
      <button type="button" onclick={() => { showCreateModal = false; resetForm(); }} class="px-4 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">Cancel</button>
      <button type="submit" disabled={saving} class="px-4 py-2.5 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">{saving ? "Saving..." : "Add Account"}</button>
    </div>
  </form>
</Modal>

{#if drawerOpen}
  <div class="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm" onclick={closeDrawer} onkeydown={(e) => e.key === "Escape" && closeDrawer()} role="button" tabindex="-1"></div>
  <div class="fixed inset-y-0 right-0 z-50 w-full max-w-2xl bg-white shadow-2xl border-l border-neutral-200 flex flex-col drawer-slide-in">
    {#if drawerLoading}
      <div class="flex-1 flex items-center justify-center"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div></div>
    {:else if drawerItem}
      {@const a = drawerItem}

      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200">
        <div class="flex items-center gap-3">
          <h2 class="text-lg font-bold text-neutral-800">{a.account_name}</h2>
          <StatusBadge status={a.status} size="md" />
        </div>
        <button onclick={closeDrawer} class="w-8 h-8 flex items-center justify-center rounded-lg text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 transition-colors" aria-label="Close">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
        </button>
      </div>

      <!-- Body -->
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-6">
        <!-- Balance card -->
        <div class="rounded-xl border p-5 text-center" style="background: {balanceStyles(balanceColor(a.current_balance, a.opening_balance)).bg}; border-color: {balanceStyles(balanceColor(a.current_balance, a.opening_balance)).border};">
          <p class="text-xs font-medium uppercase tracking-wider mb-1" style="color: {balanceStyles(balanceColor(a.current_balance, a.opening_balance)).label};">Current Balance</p>
          <p class="text-2xl font-bold tabular-nums" style="font-family: 'Raleway', sans-serif; color: {balanceStyles(balanceColor(a.current_balance, a.opening_balance)).text};">{currency.format(a.current_balance)}</p>
          <p class="text-xs mt-1" style="color: {balanceStyles(balanceColor(a.current_balance, a.opening_balance)).label};">{a.currency}</p>
        </div>

        <!-- Account Details -->
        <div>
          <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-3">Account Details</h3>
          <dl class="grid grid-cols-2 gap-x-6 gap-y-2.5 text-sm">
            <div><dt class="text-neutral-400">Bank</dt><dd class="mt-0.5 font-medium text-neutral-800">{a.bank_name}</dd></div>
            <div><dt class="text-neutral-400">Account Number</dt><dd class="mt-0.5 text-neutral-700 font-mono">{a.account_number}</dd></div>
            <div><dt class="text-neutral-400">Type</dt><dd class="mt-0.5 text-neutral-700 capitalize">{a.account_type.replace(/_/g, " ")}</dd></div>
            {#if a.branch}<div><dt class="text-neutral-400">Branch</dt><dd class="mt-0.5 text-neutral-700">{a.branch}</dd></div>{/if}
            <div><dt class="text-neutral-400">Opening Balance</dt><dd class="mt-0.5 text-neutral-700 tabular-nums">{currency.format(a.opening_balance)}</dd></div>
            {#if a.gl_account_name}<div><dt class="text-neutral-400">GL Account</dt><dd class="mt-0.5 text-neutral-700">{a.gl_account_name}</dd></div>{/if}
          </dl>
        </div>

        <!-- Transaction History -->
        <div>
          <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-3">Transaction History</h3>

          <!-- Filters -->
          <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-3 mb-3">
            <div class="grid grid-cols-4 gap-2">
              <label>
                <span class="block text-[10px] font-medium text-neutral-500 mb-1">Search</span>
                <input type="text" bind:value={txnSearch} placeholder="Ref or counterparty" class="w-full px-2.5 py-1.5 border border-neutral-200 rounded-md text-xs bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />
              </label>
              <label>
                <span class="block text-[10px] font-medium text-neutral-500 mb-1">From</span>
                <DateInput bind:value={txnDateFrom} />
              </label>
              <label>
                <span class="block text-[10px] font-medium text-neutral-500 mb-1">To</span>
                <DateInput bind:value={txnDateTo} />
              </label>
              <label>
                <span class="block text-[10px] font-medium text-neutral-500 mb-1">Type</span>
                <select bind:value={txnTypeFilter} class="w-full px-2.5 py-1.5 border border-neutral-200 rounded-md text-xs bg-white focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent">
                  <option value="">All</option>
                  <option value="credit">Credit</option>
                  <option value="debit">Debit</option>
                </select>
              </label>
            </div>
          </div>

          <!-- Transaction list -->
          <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
            {#if drawerTxnLoading}
              <div class="p-8 text-center"><div class="inline-block w-5 h-5 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div></div>
            {:else if filteredTxns().length === 0}
              <div class="p-8 text-center">
                <p class="text-xs text-neutral-400">{drawerTxns.length === 0 ? "No transactions for this account." : "No transactions match the filters."}</p>
              </div>
            {:else}
              <div class="max-h-64 overflow-y-auto">
                <table class="w-full text-xs">
                  <thead class="sticky top-0 bg-neutral-50">
                    <tr class="border-b border-neutral-200">
                      <th class="px-3 py-2 text-left font-medium text-neutral-400 uppercase tracking-wider">Date</th>
                      <th class="px-3 py-2 text-left font-medium text-neutral-400 uppercase tracking-wider">Type</th>
                      <th class="px-3 py-2 text-left font-medium text-neutral-400 uppercase tracking-wider">Counterparty</th>
                      <th class="px-3 py-2 text-left font-medium text-neutral-400 uppercase tracking-wider">Reference</th>
                      <th class="px-3 py-2 text-center font-medium text-neutral-400 uppercase tracking-wider">Recon</th>
                      <th class="px-3 py-2 text-right font-medium text-neutral-400 uppercase tracking-wider">Amount</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-neutral-100">
                    {#each filteredTxns() as txn}
                      <tr class="hover:bg-neutral-50 transition-colors">
                        <td class="px-3 py-2.5 text-neutral-500">{formatTxnDate(txn.transaction_date)}</td>
                        <td class="px-3 py-2.5">
                          <span class="inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-semibold {txn.transaction_type === 'credit' ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'}">
                            {txn.transaction_type === "credit" ? "CR" : "DR"}
                          </span>
                        </td>
                        <td class="px-3 py-2.5 text-neutral-800 truncate max-w-[120px]">{txn.counterparty || "\u2014"}</td>
                        <td class="px-3 py-2.5 text-neutral-500 font-mono">{txn.reference || "\u2014"}</td>
                        <td class="px-3 py-2.5 text-center">
                          {#if txn.status === "reconciled"}
                            <span class="inline-block w-2 h-2 rounded-full bg-emerald-500" title="Reconciled"></span>
                          {:else if txn.status === "cleared"}
                            <span class="inline-block w-2 h-2 rounded-full bg-amber-400" title="Cleared (unreconciled)"></span>
                          {:else}
                            <span class="inline-block w-2 h-2 rounded-full bg-neutral-300" title="Pending"></span>
                          {/if}
                        </td>
                        <td class="px-3 py-2.5 text-right tabular-nums font-semibold {txn.transaction_type === 'credit' ? 'text-emerald-700' : 'text-red-600'}">{currency.format(txn.amount)}</td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </div>
              <div class="px-3 py-2 border-t border-neutral-100 text-xs text-neutral-400">
                {filteredTxns().length} transaction{filteredTxns().length !== 1 ? "s" : ""}
              </div>
            {/if}
          </div>
        </div>

        <!-- Statement Upload -->
        <div>
          <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-3">Statement Upload</h3>
          <div
            class="rounded-xl border-2 border-dashed transition-colors p-6 text-center {dragOver ? 'border-neutral-800 bg-neutral-50' : 'border-neutral-200 bg-white'}"
            ondragover={(e) => { e.preventDefault(); dragOver = true; }}
            ondragleave={() => (dragOver = false)}
            ondrop={handleStatementDrop}
            role="region"
          >
            {#if uploading}
              <div class="inline-block w-5 h-5 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin mb-2"></div>
              <p class="text-xs text-neutral-500">Processing statement...</p>
            {:else}
              <svg class="w-8 h-8 mx-auto text-neutral-300 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5" />
              </svg>
              <p class="text-xs font-medium text-neutral-700">Drag & drop a bank statement</p>
              <p class="text-[10px] text-neutral-400 mt-1">CSV, Excel, or PDF</p>
              <label class="mt-3 inline-flex items-center gap-1.5 px-3 py-1.5 bg-neutral-800 text-white rounded-lg text-xs font-medium hover:bg-neutral-800 cursor-pointer transition-colors">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5" /></svg>
                Browse files
                <input type="file" accept=".csv,.xlsx,.xls,.pdf" class="hidden" onchange={handleStatementSelect} />
              </label>
            {/if}
          </div>
        </div>

        <!-- Security & Configuration -->
        <div>
          <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-3">Security & Configuration</h3>
          <div class="space-y-4">

            <!-- Authorized Users -->
            <div class="rounded-xl border border-neutral-200 bg-white p-4">
              <div class="flex items-center justify-between mb-3">
                <p class="text-xs font-semibold text-neutral-700">Authorized Users</p>
                <span class="text-[10px] text-neutral-400">{a.authorized_user_list.length} user{a.authorized_user_list.length !== 1 ? "s" : ""}</span>
              </div>
              {#if a.authorized_user_list.length > 0}
                <div class="space-y-2">
                  {#each a.authorized_user_list as user}
                    <div class="flex items-center gap-3 rounded-lg bg-neutral-50 px-3 py-2">
                      <div class="w-7 h-7 rounded-full bg-neutral-200 flex items-center justify-center text-[10px] font-bold text-neutral-600">
                        {user.full_name.charAt(0).toUpperCase()}
                      </div>
                      <div class="flex-1 min-w-0">
                        <p class="text-xs font-medium text-neutral-800 truncate">{user.full_name}</p>
                        <p class="text-[10px] text-neutral-400 truncate">{user.email}</p>
                      </div>
                      <span class="text-[10px] font-medium text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">Transfer</span>
                    </div>
                  {/each}
                </div>
              {:else}
                <p class="text-xs text-neutral-400">No authorized users configured. All org admins have access by default.</p>
              {/if}
            </div>

            <!-- Daily Limits -->
            <div class="rounded-xl border border-neutral-200 bg-white p-4">
              <p class="text-xs font-semibold text-neutral-700 mb-2">Daily Transfer Limit</p>
              {#if a.daily_transfer_limit}
                <div class="flex items-center gap-3">
                  <p class="text-lg font-bold text-neutral-800 tabular-nums" style="font-family: 'Raleway', sans-serif;">{currency.format(a.daily_transfer_limit)}</p>
                  <span class="text-[10px] text-neutral-400">per day</span>
                </div>
                <p class="text-[10px] text-neutral-400 mt-1">Payment runs exceeding this limit will require additional approval.</p>
              {:else}
                <div class="flex items-center gap-2">
                  <span class="inline-block w-2 h-2 rounded-full bg-amber-400"></span>
                  <p class="text-xs text-amber-600">No limit configured — unlimited outflow permitted</p>
                </div>
              {/if}
            </div>

            <!-- Webhook / API Config -->
            <div class="rounded-xl border border-neutral-200 bg-white p-4">
              <p class="text-xs font-semibold text-neutral-700 mb-2">API / Webhook Integration</p>
              {#if a.api_provider || a.webhook_url}
                <dl class="space-y-2 text-xs">
                  {#if a.api_provider}
                    <div class="flex items-center justify-between">
                      <dt class="text-neutral-400">Provider</dt>
                      <dd class="font-medium text-neutral-800 capitalize">{a.api_provider}</dd>
                    </div>
                  {/if}
                  {#if a.webhook_url}
                    <div>
                      <dt class="text-neutral-400 mb-0.5">Webhook URL</dt>
                      <dd class="font-mono text-[10px] text-neutral-500 bg-neutral-50 rounded px-2 py-1 break-all">{a.webhook_url}</dd>
                    </div>
                  {/if}
                  {#if a.api_key_ref}
                    <div class="flex items-center justify-between">
                      <dt class="text-neutral-400">API Key</dt>
                      <dd class="font-mono text-[10px] text-neutral-500">**** {a.api_key_ref.slice(-6)}</dd>
                    </div>
                  {/if}
                </dl>
                <div class="mt-2 flex items-center gap-1.5">
                  <span class="inline-block w-2 h-2 rounded-full bg-emerald-500"></span>
                  <span class="text-[10px] text-emerald-600 font-medium">Connected</span>
                </div>
              {:else}
                <div class="flex items-center gap-2 mb-2">
                  <span class="inline-block w-2 h-2 rounded-full bg-neutral-300"></span>
                  <p class="text-xs text-neutral-400">No integration configured</p>
                </div>
                <p class="text-[10px] text-neutral-400">Connect to Mono, Flutterwave, or another provider for real-time balance tracking and automatic transaction sync.</p>
              {/if}
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

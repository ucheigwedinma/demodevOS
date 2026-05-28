<script lang="ts">
  import { api } from "$lib/api";
  import { can } from "$lib/permissions";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import Modal from "$lib/components/Modal.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import { useAutoRefresh } from "$lib/realtime.svelte";
  import type {
    FinanceTransaction,
    FinanceTransactionType,
    FinanceTransactionsResponse,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  type SortField = "date" | "reference" | "counterparty" | "amount" | "type";

  let transactions = $state<FinanceTransaction[]>([]);
  let totalCount = $state(0);
  let typeCounts = $state<Record<string, number>>({});
  let currentPage = $state(1);
  let pageSize = $state(25);
  let loading = $state(true);

  let searchInput = $state("");
  let searchQuery = $state("");
  let typeFilter = $state("");
  let statusFilter = $state("");

  let sortField = $state<SortField>("date");
  let sortDirection = $state<"asc" | "desc">("desc");

  let selectedTx = $state<FinanceTransaction | null>(null);
  let showViewModal = $state(false);
  let editing = $state(false);
  let saving = $state(false);
  let deleting = $state(false);

  let editForm = $state({ reference: "", counterparty: "", date: "", amount: "", status: "" });

  const canEdit = $derived(can("finance.all", "edit"));
  const canDelete = $derived(can("finance.all", "delete"));

  let searchTimeout: ReturnType<typeof setTimeout> | undefined;
  let fetchToken = 0;

  const totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));

  const hasActiveFilters = $derived(
    Boolean(searchQuery || typeFilter || statusFilter)
  );

  const ordering = $derived(
    sortDirection === "desc" ? `-${sortField}` : sortField
  );

  const visiblePages = $derived.by(() => {
    const pages: number[] = [];
    const maxVisible = 7;
    let start = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let end = Math.min(totalPages, start + maxVisible - 1);

    if (end - start + 1 < maxVisible) {
      start = Math.max(1, end - maxVisible + 1);
    }

    for (let i = start; i <= end; i += 1) {
      pages.push(i);
    }
    return pages;
  });

  const typeLabels: Record<FinanceTransactionType, string> = {
    bill: "Bill",
    invoice: "Invoice",
    bill_payment: "Payment Out",
    invoice_payment: "Payment In",
  };

  const typeBadgeColors: Record<FinanceTransactionType, string> = {
    bill: "bg-amber-50 text-amber-700 border-amber-100",
    invoice: "bg-blue-50 text-blue-700 border-blue-100",
    bill_payment: "bg-rose-50 text-rose-700 border-rose-100",
    invoice_payment: "bg-emerald-50 text-emerald-700 border-emerald-100",
  };

  function buildQueryParams(): Record<string, string> {
    const params: Record<string, string> = {
      page: String(currentPage),
      page_size: String(pageSize),
      ordering,
    };

    if (searchQuery) params.search = searchQuery;
    if (typeFilter) params.type = typeFilter;
    if (statusFilter) params.status = statusFilter;

    return params;
  }

  async function fetchTransactions() {
    loading = true;
    const token = ++fetchToken;

    try {
      const res = await api.get<FinanceTransactionsResponse>(
        "/finance/transactions/",
        buildQueryParams(),
      );
      if (token !== fetchToken) return;

      transactions = res.results;
      totalCount = res.count;
      typeCounts = res.type_counts;

      if (currentPage > Math.max(1, Math.ceil(res.count / pageSize))) {
        currentPage = 1;
      }
    } catch {
      if (token !== fetchToken) return;
      transactions = [];
      totalCount = 0;
      typeCounts = {};
    } finally {
      if (token === fetchToken) loading = false;
    }
  }

  function onSearchInput(e: Event) {
    searchInput = (e.target as HTMLInputElement).value;
    if (searchTimeout) clearTimeout(searchTimeout);

    searchTimeout = setTimeout(() => {
      searchQuery = searchInput.trim();
      currentPage = 1;
    }, 300);
  }

  function resetFilters() {
    searchInput = "";
    searchQuery = "";
    typeFilter = "";
    statusFilter = "";
    sortField = "date";
    sortDirection = "desc";
    currentPage = 1;
  }

  function fmtDate(value: string): string {
    const d = new Date(value + "T00:00:00");
    return d.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  function toggleSort(field: SortField) {
    if (sortField === field) {
      sortDirection = sortDirection === "asc" ? "desc" : "asc";
    } else {
      sortField = field;
      sortDirection = field === "date" ? "desc" : "asc";
    }
    currentPage = 1;
  }

  function isSorted(field: SortField): boolean {
    return sortField === field;
  }

  function sortIconClass(field: SortField): string {
    if (!isSorted(field)) return "text-neutral-300";
    return "text-neutral-700";
  }

  function apiEndpoint(tx: FinanceTransaction): string {
    const rawId = tx.id.replace(/^(bill|bp|inv|ip)-/, "");
    return (tx.type === "bill" || tx.type === "bill_payment")
      ? `/finance/bills/${rawId}/`
      : `/finance/invoices/${rawId}/`;
  }

  function openViewModal(tx: FinanceTransaction) {
    selectedTx = tx;
    editing = false;
    showViewModal = true;
  }

  function closeViewModal() {
    showViewModal = false;
    editing = false;
    selectedTx = null;
  }

  function startEditing() {
    if (!selectedTx || !canEdit) return;
    editForm = {
      reference: selectedTx.reference,
      counterparty: selectedTx.counterparty,
      date: selectedTx.date,
      amount: selectedTx.amount,
      status: selectedTx.status,
    };
    editing = true;
  }

  function cancelEditing() {
    editing = false;
  }

  async function handleSave() {
    if (!selectedTx || saving) return;
    saving = true;
    try {
      await api.patch(apiEndpoint(selectedTx), {
        date: editForm.date,
        status: editForm.status,
        ...(selectedTx.type === "bill" || selectedTx.type === "invoice"
          ? { total_amount: editForm.amount }
          : { amount: editForm.amount }),
      });
      editing = false;
      closeViewModal();
      await fetchTransactions();
      toast.success("Transaction updated");
    } catch {
      toast.error("Failed to update transaction");
    } finally {
      saving = false;
    }
  }

  async function handleDelete() {
    if (!selectedTx || deleting) return;
    if (!confirm("Are you sure you want to delete this transaction? This cannot be undone.")) return;
    deleting = true;
    try {
      await api.delete(apiEndpoint(selectedTx));
      closeViewModal();
      await fetchTransactions();
      toast.success("Transaction deleted");
    } catch {
      toast.error("Failed to delete transaction");
    } finally {
      deleting = false;
    }
  }

  $effect(() => {
    void searchQuery;
    void typeFilter;
    void statusFilter;
    void sortField;
    void sortDirection;
    void currentPage;
    void pageSize;
    fetchTransactions();
  });

  useAutoRefresh(["Bill", "Invoice", "Budget"], fetchTransactions, { debounceMs: 3000 });
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-800">Transactions</h1>
    <p class="mt-1 text-sm text-neutral-500">
      Unified view of all bills, invoices, and payments across your organization.
    </p>
  </div>

  <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
    <!-- Filter bar -->
    <div class="border-b border-neutral-200 bg-linear-to-r from-neutral-50 via-white to-neutral-50 p-4 sm:p-5">
      <div class="grid grid-cols-1 gap-3 xl:grid-cols-5">
        <input
          type="text"
          placeholder="Search reference, vendor, customer..."
          value={searchInput}
          oninput={onSearchInput}
          class="xl:col-span-2 rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-800"
        />

        <select
          bind:value={typeFilter}
          onchange={() => (currentPage = 1)}
          class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-800"
        >
          <option value="">All Types</option>
          <option value="bill">Bills</option>
          <option value="invoice">Invoices</option>
          <option value="bill_payment">Payments Out</option>
          <option value="invoice_payment">Payments In</option>
        </select>

        <select
          bind:value={statusFilter}
          onchange={() => (currentPage = 1)}
          class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-800"
        >
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="approved">Approved</option>
          <option value="sent">Sent</option>
          <option value="paid">Paid</option>
          <option value="overdue">Overdue</option>
          <option value="completed">Completed</option>
          <option value="cancelled">Cancelled</option>
        </select>

        <select
          value={String(pageSize)}
          onchange={(e) => {
            pageSize = Number((e.target as HTMLSelectElement).value);
            currentPage = 1;
          }}
          class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-800"
        >
          <option value="10">10 / page</option>
          <option value="25">25 / page</option>
          <option value="50">50 / page</option>
          <option value="100">100 / page</option>
        </select>
      </div>

      <div class="mt-3 flex flex-wrap items-center gap-2">
        {#if hasActiveFilters}
          <button
            onclick={resetFilters}
            class="rounded-lg border border-neutral-200 px-3 py-2 text-sm font-medium text-neutral-600 hover:bg-neutral-50"
          >
            Reset Filters
          </button>
        {/if}
      </div>

      {#if !loading && transactions.length > 0}
        <div class="mt-4 grid grid-cols-2 gap-3 md:grid-cols-5">
          <div class="rounded-lg border border-neutral-200 bg-white px-3 py-2">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Bills</p>
            <p class="mt-0.5 text-sm font-semibold text-neutral-800 tabular-nums">{typeCounts.bill ?? 0}</p>
          </div>
          <div class="rounded-lg border border-neutral-200 bg-white px-3 py-2">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Invoices</p>
            <p class="mt-0.5 text-sm font-semibold text-neutral-800 tabular-nums">{typeCounts.invoice ?? 0}</p>
          </div>
          <div class="rounded-lg border border-neutral-200 bg-white px-3 py-2">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Payments Out</p>
            <p class="mt-0.5 text-sm font-semibold text-neutral-800 tabular-nums">{typeCounts.bill_payment ?? 0}</p>
          </div>
          <div class="rounded-lg border border-neutral-200 bg-white px-3 py-2">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Payments In</p>
            <p class="mt-0.5 text-sm font-semibold text-neutral-800 tabular-nums">{typeCounts.invoice_payment ?? 0}</p>
          </div>
          <div class="rounded-lg border border-neutral-200 bg-white px-3 py-2">
            <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Total Shown</p>
            <p class="mt-0.5 text-sm font-semibold text-neutral-800 tabular-nums">{totalCount}</p>
          </div>
        </div>
      {/if}
    </div>

    <!-- Table -->
    {#if loading}
      <div class="flex items-center justify-center py-24">
        <div class="h-7 w-7 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-800"></div>
      </div>
    {:else if transactions.length === 0}
      <div class="py-24 text-center">
        <p class="text-sm text-neutral-400">No transactions found for this filter set.</p>
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full min-w-[960px] text-sm">
          <thead>
            <tr class="border-b border-neutral-200 bg-neutral-50/80">
              <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">
                <button class="inline-flex items-center gap-1" onclick={() => toggleSort("date")}>
                  Date
                  <svg class="h-3.5 w-3.5 {sortIconClass('date')}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                    {#if isSorted("date") && sortDirection === "asc"}
                      <path stroke-linecap="round" stroke-linejoin="round" d="m5.25 15.75 6.75-6.75 6.75 6.75" />
                    {:else}
                      <path stroke-linecap="round" stroke-linejoin="round" d="m18.75 8.25-6.75 6.75-6.75-6.75" />
                    {/if}
                  </svg>
                </button>
              </th>

              <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">
                <button class="inline-flex items-center gap-1" onclick={() => toggleSort("type")}>
                  Type
                  <svg class="h-3.5 w-3.5 {sortIconClass('type')}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                    {#if isSorted("type") && sortDirection === "asc"}
                      <path stroke-linecap="round" stroke-linejoin="round" d="m5.25 15.75 6.75-6.75 6.75 6.75" />
                    {:else}
                      <path stroke-linecap="round" stroke-linejoin="round" d="m18.75 8.25-6.75 6.75-6.75-6.75" />
                    {/if}
                  </svg>
                </button>
              </th>

              <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">
                <button class="inline-flex items-center gap-1" onclick={() => toggleSort("reference")}>
                  Reference
                  <svg class="h-3.5 w-3.5 {sortIconClass('reference')}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                    {#if isSorted("reference") && sortDirection === "asc"}
                      <path stroke-linecap="round" stroke-linejoin="round" d="m5.25 15.75 6.75-6.75 6.75 6.75" />
                    {:else}
                      <path stroke-linecap="round" stroke-linejoin="round" d="m18.75 8.25-6.75 6.75-6.75-6.75" />
                    {/if}
                  </svg>
                </button>
              </th>

              <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">
                <button class="inline-flex items-center gap-1" onclick={() => toggleSort("counterparty")}>
                  Counterparty
                  <svg class="h-3.5 w-3.5 {sortIconClass('counterparty')}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                    {#if isSorted("counterparty") && sortDirection === "asc"}
                      <path stroke-linecap="round" stroke-linejoin="round" d="m5.25 15.75 6.75-6.75 6.75 6.75" />
                    {:else}
                      <path stroke-linecap="round" stroke-linejoin="round" d="m18.75 8.25-6.75 6.75-6.75-6.75" />
                    {/if}
                  </svg>
                </button>
              </th>

              <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Status</th>

              <th class="px-5 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Direction</th>

              <th class="px-5 py-3 text-right text-[11px] font-semibold uppercase tracking-wider text-neutral-500">
                <button class="inline-flex items-center gap-1" onclick={() => toggleSort("amount")}>
                  Amount
                  <svg class="h-3.5 w-3.5 {sortIconClass('amount')}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                    {#if isSorted("amount") && sortDirection === "asc"}
                      <path stroke-linecap="round" stroke-linejoin="round" d="m5.25 15.75 6.75-6.75 6.75 6.75" />
                    {:else}
                      <path stroke-linecap="round" stroke-linejoin="round" d="m18.75 8.25-6.75 6.75-6.75-6.75" />
                    {/if}
                  </svg>
                </button>
              </th>
            </tr>
          </thead>

          <tbody class="divide-y divide-neutral-100">
            {#each transactions as tx (tx.id)}
              <tr
                class="cursor-pointer bg-white transition-colors hover:bg-neutral-50"
                onclick={() => openViewModal(tx)}
              >
                <td class="px-5 py-4 text-neutral-600">{fmtDate(tx.date)}</td>

                <td class="px-5 py-4">
                  <span class="inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold {typeBadgeColors[tx.type] ?? 'bg-neutral-100 text-neutral-700 border-neutral-200'}">
                    {typeLabels[tx.type] ?? tx.type}
                  </span>
                </td>

                <td class="px-5 py-4">
                  <p class="font-semibold text-neutral-800">{tx.reference}</p>
                </td>

                <td class="px-5 py-4 text-neutral-600">{tx.counterparty}</td>

                <td class="px-5 py-4">
                  <StatusBadge status={tx.status} />
                </td>

                <td class="px-5 py-4">
                  {#if tx.direction === "incoming"}
                    <span class="inline-flex items-center gap-1 text-xs font-medium text-emerald-600">
                      <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="m19.5 4.5-15 15m0 0h11.25m-11.25 0V8.25" />
                      </svg>
                      In
                    </span>
                  {:else}
                    <span class="inline-flex items-center gap-1 text-xs font-medium text-rose-600">
                      <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 19.5 15-15m0 0H8.25m11.25 0v11.25" />
                      </svg>
                      Out
                    </span>
                  {/if}
                </td>

                <td class="px-5 py-4 text-right font-medium tabular-nums {tx.direction === 'incoming' ? 'text-emerald-700' : 'text-neutral-800'}">
                  {tx.direction === "incoming" ? "+" : "-"}{currency.format(tx.amount)}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div class="flex items-center justify-between border-t border-neutral-200 px-5 py-3.5">
        <p class="text-sm text-neutral-500">
          Page {currentPage} of {totalPages}
        </p>

        <div class="flex items-center gap-1">
          <button
            onclick={() => (currentPage = Math.max(1, currentPage - 1))}
            disabled={currentPage === 1}
            class="rounded-lg border border-neutral-200 px-2.5 py-1.5 text-sm text-neutral-600 hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Prev
          </button>

          {#each visiblePages as page}
            <button
              onclick={() => (currentPage = page)}
              class="min-w-8 rounded-lg px-2.5 py-1.5 text-sm font-medium transition-colors {page === currentPage ? 'bg-neutral-800 text-white' : 'text-neutral-600 hover:bg-neutral-50'}"
            >
              {page}
            </button>
          {/each}

          <button
            onclick={() => (currentPage = Math.min(totalPages, currentPage + 1))}
            disabled={currentPage === totalPages}
            class="rounded-lg border border-neutral-200 px-2.5 py-1.5 text-sm text-neutral-600 hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
      </div>
    {/if}
  </section>
</div>

<!-- Transaction Modal -->
{#if selectedTx}
  <Modal
    open={showViewModal}
    onclose={closeViewModal}
    title={editing ? "Edit Transaction" : "Transaction Details"}
    maxWidth="max-w-xl"
  >
    <!-- Type + Status header -->
    <div class="flex items-center justify-between">
      <span class="inline-flex items-center rounded-full border px-3 py-1.5 text-xs font-semibold {typeBadgeColors[selectedTx.type] ?? 'bg-neutral-100 text-neutral-700 border-neutral-200'}">
        {typeLabels[selectedTx.type] ?? selectedTx.type}
      </span>
      {#if editing}
        <select
          bind:value={editForm.status}
          class="rounded-lg border border-neutral-200 bg-white px-3 py-1.5 text-xs font-medium text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-800"
        >
          <option value="draft">Draft</option>
          <option value="approved">Approved</option>
          <option value="sent">Sent</option>
          <option value="paid">Paid</option>
          <option value="overdue">Overdue</option>
          <option value="completed">Completed</option>
          <option value="cancelled">Cancelled</option>
        </select>
      {:else}
        <StatusBadge status={selectedTx.status} />
      {/if}
    </div>

    <!-- Detail grid -->
    <div class="mt-5 space-y-4">
      <div class="grid grid-cols-2 gap-4">
        <div>
          <p class="text-[11px] font-semibold uppercase tracking-wider text-neutral-400">Reference</p>
          <p class="mt-1 text-sm font-semibold text-neutral-800">{editing ? editForm.reference : selectedTx.reference}</p>
        </div>
        <div>
          <p class="text-[11px] font-semibold uppercase tracking-wider text-neutral-400">Counterparty</p>
          <p class="mt-1 text-sm text-neutral-700">{editing ? editForm.counterparty : selectedTx.counterparty}</p>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div>
          <p class="text-[11px] font-semibold uppercase tracking-wider text-neutral-400">Date</p>
          {#if editing}
            <DateInput bind:value={editForm.date} />
          {:else}
            <p class="mt-1 text-sm text-neutral-700">{fmtDate(selectedTx.date)}</p>
          {/if}
        </div>
        <div>
          <p class="text-[11px] font-semibold uppercase tracking-wider text-neutral-400">Direction</p>
          <div class="mt-1">
            {#if selectedTx.direction === "incoming"}
              <span class="inline-flex items-center gap-1.5 text-sm font-medium text-emerald-600">
                <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="m19.5 4.5-15 15m0 0h11.25m-11.25 0V8.25" />
                </svg>
                Incoming
              </span>
            {:else}
              <span class="inline-flex items-center gap-1.5 text-sm font-medium text-rose-600">
                <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 19.5 15-15m0 0H8.25m11.25 0v11.25" />
                </svg>
                Outgoing
              </span>
            {/if}
          </div>
        </div>
      </div>

      <div class="rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-3">
        <p class="text-[11px] font-semibold uppercase tracking-wider text-neutral-400">Amount</p>
        {#if editing}
          <input
            type="number"
            step="0.01"
            bind:value={editForm.amount}
            class="mt-1 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-lg font-bold tabular-nums text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800"
          />
        {:else}
          <p class="mt-1 text-xl font-bold tabular-nums {selectedTx.direction === 'incoming' ? 'text-emerald-700' : 'text-neutral-800'}">
            {selectedTx.direction === "incoming" ? "+" : "-"}{currency.format(selectedTx.amount)}
          </p>
        {/if}
      </div>
    </div>

    <!-- Action bar -->
    <div class="mt-6 flex items-center justify-end gap-2 border-t border-neutral-100 pt-4">
      {#if editing}
        <button
          onclick={cancelEditing}
          class="rounded-lg border border-neutral-200 px-3.5 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors"
        >
          Cancel
        </button>
        <button
          onclick={handleSave}
          disabled={saving}
          class="inline-flex items-center gap-1.5 rounded-lg bg-neutral-800 px-3.5 py-2 text-sm font-medium text-white hover:bg-neutral-800 transition-colors disabled:opacity-50"
        >
          {#if saving}
            <div class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white"></div>
          {/if}
          {saving ? "Saving..." : "Save"}
        </button>
      {:else}
        {#if canDelete}
          <button
            onclick={handleDelete}
            disabled={deleting}
            class="inline-flex items-center gap-1.5 rounded-lg border border-red-200 px-3.5 py-2 text-sm font-medium text-red-700 hover:bg-red-50 transition-colors disabled:opacity-50"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
            </svg>
            {deleting ? "Deleting..." : "Delete"}
          </button>
        {/if}
        {#if canEdit}
          <button
            onclick={startEditing}
            class="inline-flex items-center gap-1.5 rounded-lg bg-neutral-800 px-3.5 py-2 text-sm font-medium text-white hover:bg-neutral-800 transition-colors"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
            </svg>
            Edit
          </button>
        {/if}
      {/if}
    </div>
  </Modal>
{/if}

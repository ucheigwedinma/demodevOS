<script lang="ts">
  import { onMount } from "svelte";
  import { api } from "$lib/api";
  import { currency } from "$lib/stores/currency.svelte";
  import type {
    AccountListItem,
    GeneralLedgerResponse,
    JournalSourceType,
    PaginatedResponse,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let loading = $state(true);
  let data = $state<GeneralLedgerResponse | null>(null);
  let accounts = $state<AccountListItem[]>([]);
  let currentPage = $state(1);

  let filters = $state({
    account: "",
    date_from: "",
    date_to: "",
    source_type: "" as "" | JournalSourceType,
    page_size: "200",
  });

  const sourceOptions: { value: JournalSourceType; label: string }[] = [
    { value: "manual", label: "Manual" },
    { value: "bill", label: "Bill" },
    { value: "invoice", label: "Invoice" },
    { value: "payment", label: "Payment" },
    { value: "adjustment", label: "Adjustment" },
    { value: "closing", label: "Closing Entry" },
    { value: "opening", label: "Opening Balance" },
  ];

  async function fetchAccounts() {
    try {
      const res = await api.get<PaginatedResponse<AccountListItem>>("/finance/accounts/", {
        page_size: "500",
        is_active: "true",
      });
      accounts = res.results;
    } catch {
      accounts = [];
    }
  }

  async function fetchLedger(page = currentPage) {
    loading = true;
    try {
      const params: Record<string, string> = {};
      if (filters.account) params.account = filters.account;
      if (filters.date_from) params.date_from = filters.date_from;
      if (filters.date_to) params.date_to = filters.date_to;
      if (filters.source_type) params.source_type = filters.source_type;
      if (filters.page_size) params.page_size = filters.page_size;
      params.page = String(page);

      const response = await api.get<GeneralLedgerResponse>("/finance/reports/general-ledger/", params);
      data = response;
      currentPage = response.page;
      filters.page_size = String(response.page_size);
    } catch {
      data = null;
      currentPage = 1;
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    fetchAccounts();
    fetchLedger();
  });

  function formatDate(value: string): string {
    const d = new Date(`${value}T00:00:00`);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  const totalPages = $derived(data?.total_pages ?? 1);

  const pageStart = $derived.by(() => {
    if (!data || data.count === 0) return 0;
    return (currentPage - 1) * data.page_size + 1;
  });

  const pageEnd = $derived.by(() => {
    if (!data || data.count === 0) return 0;
    return pageStart + data.results.length - 1;
  });

  const visiblePages = $derived.by(() => {
    const maxButtons = 7;
    const pages: number[] = [];
    const total = totalPages;

    if (total <= maxButtons) {
      for (let page = 1; page <= total; page += 1) pages.push(page);
      return pages;
    }

    let start = Math.max(1, currentPage - Math.floor(maxButtons / 2));
    let end = Math.min(total, start + maxButtons - 1);
    start = Math.max(1, end - maxButtons + 1);

    for (let page = start; page <= end; page += 1) pages.push(page);
    return pages;
  });

  function applyFilters() {
    currentPage = 1;
    fetchLedger(1);
  }

  function resetFilters() {
    filters = { account: "", date_from: "", date_to: "", source_type: "", page_size: "200" };
    currentPage = 1;
    fetchLedger(1);
  }

  function goToPage(page: number) {
    if (!data) return;
    const nextPage = Math.max(1, Math.min(page, totalPages));
    if (nextPage === currentPage) return;
    fetchLedger(nextPage);
  }
</script>

<div class="space-y-6">
  <div>
    <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-pink-600">Accounting</p>
    <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">General Ledger</h1>
    <p class="text-sm text-neutral-500 mt-1">Authoritative record of posted journal activity across accounts, periods, and balances.</p>
  </div>

  <section class="bg-white rounded-xl border border-neutral-200 p-4 md:p-5 space-y-4">
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3">
      <label>
        <span class="block text-xs uppercase tracking-wide font-semibold text-neutral-500 mb-1.5">Account</span>
        <select
          bind:value={filters.account}
          class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800"
        >
          <option value="">All accounts</option>
          {#each accounts as account}
            <option value={String(account.id)}>{account.code} - {account.name}</option>
          {/each}
        </select>
      </label>

      <label>
        <span class="block text-xs uppercase tracking-wide font-semibold text-neutral-500 mb-1.5">Date From</span>
        <DateInput bind:value={filters.date_from} />
      </label>

      <label>
        <span class="block text-xs uppercase tracking-wide font-semibold text-neutral-500 mb-1.5">Date To</span>
        <DateInput bind:value={filters.date_to} />
      </label>

      <label>
        <span class="block text-xs uppercase tracking-wide font-semibold text-neutral-500 mb-1.5">Source Type</span>
        <select
          bind:value={filters.source_type}
          class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800"
        >
          <option value="">All sources</option>
          {#each sourceOptions as source}
            <option value={source.value}>{source.label}</option>
          {/each}
        </select>
      </label>

      <label>
        <span class="block text-xs uppercase tracking-wide font-semibold text-neutral-500 mb-1.5">Rows / Page</span>
        <input
          type="number"
          min="1"
          max="1000"
          step="1"
          bind:value={filters.page_size}
          class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800"
        />
      </label>
    </div>

    <div class="flex items-center gap-2">
      <button
        onclick={applyFilters}
        class="rounded-lg bg-neutral-800 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800"
      >
        Apply Filters
      </button>
      <button
        onclick={resetFilters}
        class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
      >
        Reset
      </button>
    </div>
  </section>

  {#if loading}
    <div class="py-16 text-center text-sm text-neutral-500">Loading ledger entries...</div>
  {:else if !data}
    <div class="py-16 text-center text-sm text-neutral-500">Could not load general ledger data.</div>
  {:else}
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div class="rounded-xl border border-pink-100 bg-pink-50 px-4 py-3.5">
        <p class="text-xs uppercase tracking-wide font-semibold text-pink-400">Rows</p>
        <p class="mt-1 text-base font-semibold text-pink-900">{data.count}</p>
      </div>
      <div class="rounded-xl border border-pink-100 bg-pink-50 px-4 py-3.5">
        <p class="text-xs uppercase tracking-wide font-semibold text-pink-400">Total Debit</p>
        <p class="mt-1 text-base font-semibold text-pink-900">{currency.format(data.totals.debit)}</p>
      </div>
      <div class="rounded-xl border border-pink-100 bg-pink-50 px-4 py-3.5">
        <p class="text-xs uppercase tracking-wide font-semibold text-pink-400">Total Credit</p>
        <p class="mt-1 text-base font-semibold text-pink-900">{currency.format(data.totals.credit)}</p>
      </div>
    </div>

    <section class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      <div class="px-5 py-4 border-b border-neutral-100 flex items-center justify-between">
        <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-800">Ledger Activity</h2>
        <span class="text-xs text-neutral-500">
          {#if data.count === 0}
            No rows
          {:else}
            Showing {pageStart}-{pageEnd} of {data.count}
          {/if}
        </span>
      </div>

      {#if data.results.length === 0}
        <div class="py-14 text-center text-sm text-neutral-500">No posted entries found for this filter.</div>
      {:else}
        <div class="overflow-x-auto">
          <table class="w-full min-w-[1140px] text-sm">
            <thead>
              <tr class="border-b border-neutral-100 text-left">
                <th class="px-5 py-3 text-xs uppercase tracking-wide font-semibold text-neutral-500">Date</th>
                <th class="px-5 py-3 text-xs uppercase tracking-wide font-semibold text-neutral-500">Journal</th>
                <th class="px-5 py-3 text-xs uppercase tracking-wide font-semibold text-neutral-500">Account</th>
                <th class="px-5 py-3 text-xs uppercase tracking-wide font-semibold text-neutral-500">Source</th>
                <th class="px-5 py-3 text-xs uppercase tracking-wide font-semibold text-neutral-500">Description</th>
                <th class="px-5 py-3 text-xs uppercase tracking-wide font-semibold text-neutral-500 text-right">Debit</th>
                <th class="px-5 py-3 text-xs uppercase tracking-wide font-semibold text-neutral-500 text-right">Credit</th>
              </tr>
            </thead>
            <tbody>
              {#each data.results as row (row.id)}
                <tr class="border-b border-neutral-50 hover:bg-neutral-50/60 transition-colors">
                  <td class="px-5 py-3.5 text-neutral-600">{formatDate(row.entry_date)}</td>
                  <td class="px-5 py-3.5 font-medium text-neutral-800">{row.journal_number}</td>
                  <td class="px-5 py-3.5">
                    <p class="font-medium text-neutral-800">{row.account_code}</p>
                    <p class="text-xs text-neutral-500">{row.account_name}</p>
                  </td>
                  <td class="px-5 py-3.5 text-neutral-600 capitalize">{row.source_type}{row.source_id ? ` #${row.source_id}` : ""}</td>
                  <td class="px-5 py-3.5 text-neutral-700">{row.description || "-"}</td>
                  <td class="px-5 py-3.5 text-right tabular-nums">{currency.format(row.debit_amount)}</td>
                  <td class="px-5 py-3.5 text-right tabular-nums">{currency.format(row.credit_amount)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>

        <div class="flex flex-col gap-3 border-t border-neutral-100 px-5 py-4 md:flex-row md:items-center md:justify-between">
          <p class="text-xs text-neutral-500">
            Page {currentPage} of {totalPages} · {data.page_size} rows per page
          </p>

          {#if totalPages > 1}
            <div class="flex flex-wrap items-center gap-1">
              <button
                onclick={() => goToPage(currentPage - 1)}
                disabled={currentPage <= 1 || loading}
                class="rounded-md border border-neutral-200 px-3 py-1.5 text-sm font-medium text-neutral-600 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Previous
              </button>

              {#each visiblePages as page}
                <button
                  onclick={() => goToPage(page)}
                  disabled={loading}
                  class="rounded-md px-3 py-1.5 text-sm font-medium transition-colors {page === currentPage ? 'bg-neutral-800 text-white' : 'border border-neutral-200 text-neutral-600 hover:bg-neutral-50'} disabled:cursor-not-allowed"
                >
                  {page}
                </button>
              {/each}

              <button
                onclick={() => goToPage(currentPage + 1)}
                disabled={currentPage >= totalPages || loading}
                class="rounded-md border border-neutral-200 px-3 py-1.5 text-sm font-medium text-neutral-600 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Next
              </button>
            </div>
          {/if}
        </div>
      {/if}
    </section>
  {/if}
</div>

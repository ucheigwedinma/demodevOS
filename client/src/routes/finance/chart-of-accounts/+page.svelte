<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    AccountListItem,
    AccountType,
    AccountSubType,
    PaginatedResponse,
  } from "$lib/types";

  let loading = $state(true);
  let data = $state<AccountListItem[]>([]);
  let totalCount = $state(0);
  let currentPage = $state(1);
  let searchQuery = $state("");
  let typeFilter = $state("");
  let statusFilter = $state("");
  let sortValue = $state("code");

  let showModal = $state(false);
  let editingId = $state<number | null>(null);
  let saving = $state(false);
  let deleting = $state<number | null>(null);
  let showDeleteConfirm = $state<number | null>(null);

  let form = $state({
    code: "",
    name: "",
    account_type: "" as AccountType | "",
    sub_type: "" as AccountSubType | "",
    description: "",
    is_active: true,
  });

  const PAGE_SIZE = 25;
  const totalPages = $derived(Math.ceil(totalCount / PAGE_SIZE));
  const startItem = $derived((currentPage - 1) * PAGE_SIZE + 1);
  const endItem = $derived(Math.min(currentPage * PAGE_SIZE, totalCount));

  // Sub-types grouped by parent type for dependent filtering
  const SUB_TYPE_MAP: Record<AccountType, { value: AccountSubType; label: string }[]> = {
    asset: [
      { value: "current_asset", label: "Current Asset" },
      { value: "fixed_asset", label: "Fixed Asset" },
      { value: "other_asset", label: "Other Asset" },
    ],
    liability: [
      { value: "current_liability", label: "Current Liability" },
      { value: "long_term_liability", label: "Long-Term Liability" },
    ],
    equity: [
      { value: "owners_equity", label: "Owner's Equity" },
      { value: "retained_earnings", label: "Retained Earnings" },
    ],
    revenue: [
      { value: "operating_revenue", label: "Operating Revenue" },
      { value: "other_revenue", label: "Other Revenue" },
    ],
    expense: [
      { value: "operating_expense", label: "Operating Expense" },
      { value: "cost_of_goods_sold", label: "Cost of Goods Sold" },
      { value: "other_expense", label: "Other Expense" },
    ],
  };

  const availableSubTypes = $derived(
    form.account_type ? SUB_TYPE_MAP[form.account_type] : []
  );

  const TYPE_LABELS: Record<AccountType, string> = {
    asset: "Asset",
    liability: "Liability",
    equity: "Equity",
    revenue: "Revenue",
    expense: "Expense",
  };

  const SUB_TYPE_LABELS: Record<AccountSubType, string> = {
    current_asset: "Current Asset",
    fixed_asset: "Fixed Asset",
    other_asset: "Other Asset",
    current_liability: "Current Liability",
    long_term_liability: "Long-Term Liability",
    owners_equity: "Owner's Equity",
    retained_earnings: "Retained Earnings",
    operating_revenue: "Operating Revenue",
    other_revenue: "Other Revenue",
    operating_expense: "Operating Expense",
    cost_of_goods_sold: "Cost of Goods Sold",
    other_expense: "Other Expense",
  };

  const TYPE_STYLES: Record<AccountType, string> = {
    asset: "bg-blue-50 text-blue-700",
    liability: "bg-red-50 text-red-700",
    equity: "bg-purple-50 text-purple-700",
    revenue: "bg-emerald-50 text-emerald-700",
    expense: "bg-amber-50 text-amber-700",
  };

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

  async function loadAccounts() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage) };
      if (searchQuery) params.search = searchQuery;
      if (typeFilter) params.account_type = typeFilter;
      if (statusFilter) params.is_active = statusFilter;
      params.ordering = sortValue;

      const res = await api.get<PaginatedResponse<AccountListItem>>(
        "/finance/accounts/",
        params
      );
      data = res.results;
      totalCount = res.count;
    } catch {
      data = [];
      totalCount = 0;
      toast.error("Load failed", "Could not load accounts.");
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    void searchQuery;
    void typeFilter;
    void statusFilter;
    void sortValue;
    void currentPage;
    loadAccounts();
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

  function openAdd() {
    editingId = null;
    form = {
      code: "",
      name: "",
      account_type: "",
      sub_type: "",
      description: "",
      is_active: true,
    };
    showModal = true;
  }

  function openEdit(account: AccountListItem) {
    editingId = account.id;
    form = {
      code: account.code,
      name: account.name,
      account_type: account.account_type,
      sub_type: account.sub_type,
      description: "",
      is_active: account.is_active,
    };
    // Load full detail to get description
    api
      .get<{ description: string }>(`/finance/accounts/${account.id}/`)
      .then((detail) => {
        form.description = detail.description;
      });
    showModal = true;
  }

  function onTypeChange() {
    form.sub_type = "";
  }

  function toMessage(value: unknown): string | null {
    if (typeof value === "string" && value.trim().length) return value;
    if (Array.isArray(value) && value.length && typeof value[0] === "string") {
      return value[0];
    }
    return null;
  }

  function apiMessage(err: ApiError, fallback: string): string {
    return toMessage(err.data["code"]) ?? toMessage(err.data["detail"]) ?? fallback;
  }

  async function handleSave() {
    if (!form.code.trim() || !form.name.trim()) {
      toast.error("Validation", "Code and name are required.");
      return;
    }
    if (!form.account_type) {
      toast.error("Validation", "Account type is required.");
      return;
    }
    if (!form.sub_type) {
      toast.error("Validation", "Sub-type is required.");
      return;
    }
    saving = true;
    try {
      const payload = {
        code: form.code,
        name: form.name,
        account_type: form.account_type,
        sub_type: form.sub_type,
        description: form.description,
        is_active: form.is_active,
      };
      if (editingId) {
        await api.patch(`/finance/accounts/${editingId}/`, payload);
        toast.success("Updated", "Account updated successfully.");
      } else {
        await api.post("/finance/accounts/", payload);
        toast.success("Created", "Account created successfully.");
      }
      showModal = false;
      await loadAccounts();
    } catch (err) {
      if (err instanceof ApiError) {
        const msg = apiMessage(err, "Please check the form for errors.");
        toast.error("Save failed", msg);
      }
    } finally {
      saving = false;
    }
  }

  async function handleDelete(id: number) {
    deleting = id;
    try {
      await api.delete(`/finance/accounts/${id}/`);
      toast.success("Deleted", "Account removed.");
      showDeleteConfirm = null;
      await loadAccounts();
    } catch (err) {
      if (err instanceof ApiError) {
        const msg = apiMessage(err, "Could not delete account.");
        toast.error("Delete failed", msg);
      } else {
        toast.error("Delete failed", "Could not delete account.");
      }
    } finally {
      deleting = null;
    }
  }
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-pink-600">Accounting</p>
      <h2 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Chart of Accounts</h2>
      <p class="mt-1 text-sm text-neutral-500">
        Manage your general ledger account structure, including assets, liabilities, equity, revenue, and expenses.
        {#if totalCount > 0}
          <span
            class="ml-1 inline-flex items-center rounded-full bg-neutral-100 px-2.5 py-0.5 text-xs font-medium text-neutral-700"
          >
            {totalCount} {totalCount === 1 ? "account" : "accounts"}
          </span>
        {/if}
      </p>
    </div>
    <button
      onclick={openAdd}
      class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800"
    >
      Add Account
    </button>
  </div>

  <!-- Filters -->
  <div class="flex gap-3 items-center">
    <div class="relative flex-1 max-w-sm">
      <svg
        class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        stroke-width="1.5"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
        />
      </svg>
      <input
        type="text"
        placeholder="Search by code, name..."
        oninput={onSearchInput}
        class="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
               focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent
               placeholder:text-neutral-400"
      />
    </div>
    <select
      bind:value={typeFilter}
      onchange={() => (currentPage = 1)}
      class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600
             focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
    >
      <option value="">All Types</option>
      <option value="asset">Asset</option>
      <option value="liability">Liability</option>
      <option value="equity">Equity</option>
      <option value="revenue">Revenue</option>
      <option value="expense">Expense</option>
    </select>
    <select
      bind:value={statusFilter}
      onchange={() => (currentPage = 1)}
      class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600
             focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
    >
      <option value="">All Status</option>
      <option value="true">Active</option>
      <option value="false">Inactive</option>
    </select>
    <select
      bind:value={sortValue}
      onchange={() => (currentPage = 1)}
      class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600
             focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
    >
      <option value="code">Code A–Z</option>
      <option value="-code">Code Z–A</option>
      <option value="name">Name A–Z</option>
      <option value="-name">Name Z–A</option>
      <option value="-created_at">Newest First</option>
      <option value="created_at">Oldest First</option>
    </select>
  </div>

  <!-- Table -->
  <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
    {#if loading}
      <div class="p-16 text-center">
        <div
          class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"
        ></div>
        <p class="mt-3 text-sm text-neutral-400">Loading accounts...</p>
      </div>
    {:else if data.length === 0}
      <div class="p-16 text-center">
        <div
          class="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-neutral-100"
        >
          <svg
            class="w-6 h-6 text-neutral-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            stroke-width="1.5"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              d="M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.332A48.36 48.36 0 0 0 12 9.75c-2.551 0-5.056.2-7.5.582V21"
            />
          </svg>
        </div>
        <h3 class="text-sm font-semibold text-neutral-800">No accounts found</h3>
        <p class="mt-1.5 text-sm text-neutral-500">
          {#if searchQuery || typeFilter || statusFilter}
            Try adjusting your search or filters.
          {:else}
            Create your first account to build your chart of accounts.
          {/if}
        </p>
        {#if !searchQuery && !typeFilter && !statusFilter}
          <button
            onclick={openAdd}
            class="mt-5 rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 transition-colors"
          >
            Add Account
          </button>
        {/if}
      </div>
    {:else}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200">
            <th
              class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider"
              >Code</th
            >
            <th
              class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider"
              >Name</th
            >
            <th
              class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider"
              >Type</th
            >
            <th
              class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider"
              >Sub-Type</th
            >
            <th
              class="px-5 py-3.5 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider"
              >Status</th
            >
            <th
              class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider"
              >Actions</th
            >
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each data as account}
            <tr class="hover:bg-neutral-50 transition-colors">
              <td class="px-5 py-4">
                <span class="font-mono text-sm font-medium text-neutral-800"
                  >{account.code}</span
                >
              </td>
              <td class="px-5 py-4">
                <span class="font-medium text-neutral-800">{account.name}</span>
              </td>
              <td class="px-5 py-4">
                <span
                  class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium {TYPE_STYLES[
                    account.account_type
                  ]}"
                >
                  {TYPE_LABELS[account.account_type]}
                </span>
              </td>
              <td class="px-5 py-4 text-neutral-600">
                {SUB_TYPE_LABELS[account.sub_type]}
              </td>
              <td class="px-5 py-4 text-center">
                {#if account.is_active}
                  <span
                    class="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700"
                  >
                    Active
                  </span>
                {:else}
                  <span
                    class="inline-flex items-center rounded-full bg-neutral-100 px-2.5 py-0.5 text-xs font-medium text-neutral-500"
                  >
                    Inactive
                  </span>
                {/if}
              </td>
              <td class="px-5 py-4 text-right">
                <div class="flex items-center justify-end gap-2">
                  <button
                    onclick={() => openEdit(account)}
                    class="rounded-lg px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 transition-colors"
                  >
                    Edit
                  </button>
                  {#if !account.is_system}
                    <button
                      onclick={() => (showDeleteConfirm = account.id)}
                      class="rounded-lg px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 transition-colors"
                    >
                      Delete
                    </button>
                  {:else}
                    <span class="px-3 py-1.5 text-xs text-neutral-300">System</span>
                  {/if}
                </div>
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
        Showing <span class="font-medium text-neutral-600"
          >{startItem}–{endItem}</span
        >
        of
        <span class="font-medium text-neutral-600">{totalCount}</span>
        {totalCount === 1 ? "account" : "accounts"}
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
            <svg
              class="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              stroke-width="2"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M15.75 19.5 8.25 12l7.5-7.5"
              />
            </svg>
          </button>

          {#each pageNumbers(currentPage, totalPages) as pg}
            {#if pg === "..."}
              <span class="w-9 h-9 flex items-center justify-center text-xs text-neutral-300"
                >...</span
              >
            {:else}
              <button
                onclick={() => (currentPage = pg as number)}
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
            <svg
              class="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              stroke-width="2"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="m8.25 4.5 7.5 7.5-7.5 7.5"
              />
            </svg>
          </button>
        </div>
      {/if}
    </div>
  {/if}
</div>

<!-- Add/Edit Modal -->
{#if showModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button
      class="absolute inset-0 bg-black/40 backdrop-blur-sm"
      onclick={() => (showModal = false)}
      aria-label="Close"
    ></button>
    <div
      class="relative w-full max-w-lg rounded-2xl bg-white shadow-2xl border border-neutral-200"
    >
      <div class="p-6">
        <h2 class="text-lg font-bold text-neutral-800 mb-6">
          {editingId ? "Edit Account" : "Add Account"}
        </h2>

        <div class="space-y-4">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label for="acct-code" class="block text-sm font-medium text-neutral-700 mb-1.5"
                >Code *</label
              >
              <input
                id="acct-code"
                type="text"
                bind:value={form.code}
                placeholder="e.g. 1000"
                class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800 font-mono
                       focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
              />
            </div>
            <div>
              <label for="acct-name" class="block text-sm font-medium text-neutral-700 mb-1.5"
                >Name *</label
              >
              <input
                id="acct-name"
                type="text"
                bind:value={form.name}
                placeholder="e.g. Cash and Cash Equivalents"
                class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800
                       focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
              />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label for="acct-type" class="block text-sm font-medium text-neutral-700 mb-1.5"
                >Type *</label
              >
              <select
                id="acct-type"
                bind:value={form.account_type}
                onchange={onTypeChange}
                class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800
                       focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow"
              >
                <option value="">Select type...</option>
                <option value="asset">Asset</option>
                <option value="liability">Liability</option>
                <option value="equity">Equity</option>
                <option value="revenue">Revenue</option>
                <option value="expense">Expense</option>
              </select>
            </div>
            <div>
              <label
                for="acct-subtype"
                class="block text-sm font-medium text-neutral-700 mb-1.5">Sub-Type *</label
              >
              <select
                id="acct-subtype"
                bind:value={form.sub_type}
                disabled={!form.account_type}
                class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800
                       focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow
                       disabled:bg-neutral-50 disabled:text-neutral-400"
              >
                <option value=""
                  >{form.account_type ? "Select sub-type..." : "Select type first"}</option
                >
                {#each availableSubTypes as st}
                  <option value={st.value}>{st.label}</option>
                {/each}
              </select>
            </div>
          </div>

          <div>
            <label for="acct-desc" class="block text-sm font-medium text-neutral-700 mb-1.5"
              >Description</label
            >
            <textarea
              id="acct-desc"
              rows="3"
              bind:value={form.description}
              placeholder="Optional description of this account..."
              class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-800
                     focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent transition-shadow resize-none"
            ></textarea>
          </div>

          <label class="flex items-center gap-2.5 cursor-pointer">
            <input
              type="checkbox"
              bind:checked={form.is_active}
              class="w-4 h-4 rounded border-neutral-300 text-neutral-800 focus:ring-neutral-800"
            />
            <span class="text-sm text-neutral-700">Active</span>
          </label>
        </div>

        <div class="mt-7 flex items-center justify-end gap-3">
          <button
            onclick={() => (showModal = false)}
            class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onclick={handleSave}
            disabled={saving}
            class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 transition-colors disabled:opacity-60"
          >
            {saving ? "Saving..." : editingId ? "Update" : "Create"}
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}

<!-- Delete Confirmation -->
{#if showDeleteConfirm !== null}
  {@const accountToDelete = data.find((a) => a.id === showDeleteConfirm)}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button
      class="absolute inset-0 bg-black/40 backdrop-blur-sm"
      onclick={() => (showDeleteConfirm = null)}
      aria-label="Close"
    ></button>
    <div
      class="relative w-full max-w-sm rounded-2xl bg-white shadow-2xl border border-neutral-200 p-6"
    >
      <h3 class="text-lg font-bold text-neutral-800">Delete Account</h3>
      <p class="mt-2 text-sm text-neutral-600">
        Are you sure you want to delete <strong
          >{accountToDelete?.code} — {accountToDelete?.name}</strong
        >? This action cannot be undone.
      </p>
      <div class="mt-6 flex items-center justify-end gap-3">
        <button
          onclick={() => (showDeleteConfirm = null)}
          class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors"
        >
          Cancel
        </button>
        <button
          onclick={() => showDeleteConfirm !== null && handleDelete(showDeleteConfirm)}
          disabled={deleting !== null}
          class="rounded-lg bg-red-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-red-700 transition-colors disabled:opacity-60"
        >
          {deleting !== null ? "Deleting..." : "Delete"}
        </button>
      </div>
    </div>
  </div>
{/if}

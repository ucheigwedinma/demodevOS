<script lang="ts">
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import type { AccountListItem, PaginatedResponse } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let saving = $state(false);
  let accounts = $state<AccountListItem[]>([]);
  let accountsLoaded = $state(false);

  let form = $state({
    name: "",
    period_type: "annual" as "annual" | "quarterly" | "monthly",
    start_date: "",
    end_date: "",
    total_amount: "",
    warning_threshold_pct: "80",
    overspend_tolerance_pct: "0",
    notes: "",
  });

  interface LineItemDraft {
    key: number;
    account: string;
    department: string;
    cost_center: string;
    budgeted_amount: string;
    notes: string;
  }

  let nextKey = $state(1);
  let lineItems = $state<LineItemDraft[]>([
    { key: 0, account: "", department: "", cost_center: "", budgeted_amount: "", notes: "" },
  ]);

  const lineTotal = $derived(
    lineItems.reduce((sum, li) => sum + (Number(li.budgeted_amount) || 0), 0)
  );

  async function loadAccounts() {
    try {
      // Load expense accounts for budget line items
      const res = await api.get<PaginatedResponse<AccountListItem>>(
        "/finance/accounts/",
        { page_size: "500", account_type: "expense", is_active: "true" }
      );
      accounts = res.results;
    } catch {
      accounts = [];
    } finally {
      accountsLoaded = true;
    }
  }

  function addLine() {
    lineItems = [
      ...lineItems,
      { key: nextKey++, account: "", department: "", cost_center: "", budgeted_amount: "", notes: "" },
    ];
  }

  function removeLine(key: number) {
    if (lineItems.length <= 1) return;
    lineItems = lineItems.filter((li) => li.key !== key);
  }

  async function handleSubmit() {
    if (!form.name || !form.start_date || !form.end_date) {
      toast.error("Please fill in all required fields.");
      return;
    }

    const validLines = lineItems.filter((li) => li.account && li.budgeted_amount);
    if (validLines.length === 0) {
      toast.error("Add at least one line item with an account and amount.");
      return;
    }

    saving = true;
    try {
      const budget = await api.post<{ id: number }>("/finance/budgets/", {
        name: form.name,
        period_type: form.period_type,
        start_date: form.start_date,
        end_date: form.end_date,
        total_amount: form.total_amount || String(lineTotal),
        warning_threshold_pct: form.warning_threshold_pct,
        overspend_tolerance_pct: form.overspend_tolerance_pct,
        notes: form.notes,
      });

      // Create line items
      for (let i = 0; i < validLines.length; i++) {
        const li = validLines[i];
        await api.post(`/finance/budgets/${budget.id}/line-items/`, {
          account: Number(li.account),
          department: li.department ? Number(li.department) : null,
          cost_center: li.cost_center ? Number(li.cost_center) : null,
          budgeted_amount: li.budgeted_amount,
          notes: li.notes,
          sort_order: i,
        });
      }

      toast.success("Budget created successfully.");
      goto(`/finance/budgets/${budget.id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        const msgs = Object.values(err.fieldErrors).flat();
        toast.error(msgs.join(", ") || "Failed to create budget.");
      } else {
        toast.error("Failed to create budget.");
      }
    } finally {
      saving = false;
    }
  }

  function formatCurrency(val: number): string {
    return currency.formatCompact(val);
  }

  $effect(() => {
    loadAccounts();
  });
</script>

<div class="max-w-4xl">
  <!-- Header -->
  <div class="mb-6">
    <a href="/finance/budgets" class="inline-flex items-center gap-1 text-sm text-neutral-500 hover:text-neutral-900 transition-colors mb-3">
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
      </svg>
      Back to Budgets
    </a>
    <h1 class="text-2xl font-bold text-neutral-900">New Budget</h1>
  </div>

  <form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
    <!-- Budget Details Card -->
    <div class="bg-white rounded-xl border border-neutral-200 p-6 mb-6">
      <h2 class="text-sm font-semibold text-neutral-900 uppercase tracking-wide mb-4">Budget Details</h2>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="md:col-span-2">
          <label for="name" class="block text-sm font-medium text-neutral-700 mb-1">Name *</label>
          <input
            id="name"
            type="text"
            bind:value={form.name}
            placeholder="e.g. FY2026 Operating Budget"
            class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          />
        </div>

        <div>
          <label for="period_type" class="block text-sm font-medium text-neutral-700 mb-1">Period Type</label>
          <select
            id="period_type"
            bind:value={form.period_type}
            class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
          >
            <option value="annual">Annual</option>
            <option value="quarterly">Quarterly</option>
            <option value="monthly">Monthly</option>
          </select>
        </div>

        <div></div>

        <div>
          <label for="start_date" class="block text-sm font-medium text-neutral-700 mb-1">Start Date *</label>
          <DateInput id="start_date" bind:value={form.start_date} />
        </div>

        <div>
          <label for="end_date" class="block text-sm font-medium text-neutral-700 mb-1">End Date *</label>
          <DateInput id="end_date" bind:value={form.end_date} />
        </div>

        <div>
          <label for="warning_threshold_pct" class="block text-sm font-medium text-neutral-700 mb-1">Warning Threshold %</label>
          <input
            id="warning_threshold_pct"
            type="number"
            step="0.01"
            min="0"
            max="100"
            bind:value={form.warning_threshold_pct}
            class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
          />
          <p class="text-xs text-neutral-400 mt-1">Alert when spending reaches this % of budget</p>
        </div>

        <div>
          <label for="overspend_tolerance_pct" class="block text-sm font-medium text-neutral-700 mb-1">Overspend Tolerance %</label>
          <input
            id="overspend_tolerance_pct"
            type="number"
            step="0.01"
            min="0"
            bind:value={form.overspend_tolerance_pct}
            class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
          />
          <p class="text-xs text-neutral-400 mt-1">% above 100% before critical alert</p>
        </div>

        <div class="md:col-span-2">
          <label for="notes" class="block text-sm font-medium text-neutral-700 mb-1">Notes</label>
          <textarea
            id="notes"
            rows="2"
            bind:value={form.notes}
            class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"
          ></textarea>
        </div>
      </div>
    </div>

    <!-- Line Items Card -->
    <div class="bg-white rounded-xl border border-neutral-200 p-6 mb-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-sm font-semibold text-neutral-900 uppercase tracking-wide">Line Items</h2>
        <div class="text-sm font-medium text-neutral-600">
          Total: <span class="text-neutral-900 font-bold">{formatCurrency(lineTotal)}</span>
        </div>
      </div>

      <div class="space-y-3">
        {#each lineItems as li, i (li.key)}
          <div class="flex gap-3 items-start">
            <div class="flex-1 min-w-0">
              <select
                bind:value={li.account}
                class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
              >
                <option value="">Select GL Account</option>
                {#each accounts as acct}
                  <option value={String(acct.id)}>{acct.code} — {acct.name}</option>
                {/each}
              </select>
            </div>
            <div class="w-40">
              <input
                type="number"
                step="0.01"
                min="0"
                placeholder="Amount"
                bind:value={li.budgeted_amount}
                class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 tabular-nums"
              />
            </div>
            <div class="flex-1 min-w-0">
              <input
                type="text"
                placeholder="Notes (optional)"
                bind:value={li.notes}
                class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
              />
            </div>
            <button
              type="button"
              onclick={() => removeLine(li.key)}
              disabled={lineItems.length <= 1}
              class="p-2 rounded-lg text-neutral-400 hover:text-red-500 hover:bg-red-50 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              aria-label="Remove line"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        {/each}
      </div>

      <button
        type="button"
        onclick={addLine}
        class="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-neutral-600 hover:text-neutral-900 transition-colors"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
        Add Line Item
      </button>
    </div>

    <!-- Actions -->
    <div class="flex items-center justify-end gap-3">
      <a
        href="/finance/budgets"
        class="px-4 py-2.5 rounded-lg border border-neutral-200 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50"
      >
        Cancel
      </a>
      <button
        type="submit"
        disabled={saving}
        class="px-6 py-2.5 rounded-lg bg-neutral-900 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {saving ? "Creating..." : "Create Budget"}
      </button>
    </div>
  </form>
</div>

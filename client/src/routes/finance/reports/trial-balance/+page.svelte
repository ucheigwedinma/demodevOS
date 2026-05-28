<script lang="ts">
  import { api } from "$lib/api";
  import { currency } from "$lib/stores/currency.svelte";
  import type { TrialBalanceResponse } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let loading = $state(true);
  let asOf = $state(new Date().toISOString().slice(0, 10));
  let data = $state<TrialBalanceResponse | null>(null);

  async function loadTrialBalance() {
    loading = true;
    try {
      data = await api.get<TrialBalanceResponse>("/finance/reports/trial-balance/", {
        as_of: asOf,
      });
    } catch {
      data = null;
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    loadTrialBalance();
  });

  function formatDate(dateStr: string): string {
    const d = new Date(`${dateStr}T00:00:00`);
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }
</script>

<div class="space-y-6">
  <div class="flex items-start justify-between gap-4">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900">Trial Balance</h1>
      <p class="text-sm text-neutral-500 mt-1">Phase 2: account balance validation as of a reporting date.</p>
    </div>

    <div class="flex items-center gap-2">
      <DateInput bind:value={asOf} />
      <button
        onclick={loadTrialBalance}
        class="rounded-lg bg-neutral-900 px-3.5 py-2 text-sm font-semibold text-white hover:bg-neutral-800"
      >
        Refresh
      </button>
    </div>
  </div>

  {#if loading}
    <div class="py-16 text-center text-sm text-neutral-500">Loading trial balance...</div>
  {:else if !data}
    <div class="py-16 text-center text-sm text-neutral-500">Could not load trial balance.</div>
  {:else}
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div class="bg-white rounded-xl border border-neutral-200 px-4 py-3.5">
        <p class="text-xs uppercase tracking-wide font-semibold text-neutral-500">As Of</p>
        <p class="text-base font-semibold text-neutral-900 mt-1">{formatDate(data.as_of)}</p>
      </div>
      <div class="bg-white rounded-xl border border-neutral-200 px-4 py-3.5">
        <p class="text-xs uppercase tracking-wide font-semibold text-neutral-500">Total Debit</p>
        <p class="text-base font-semibold text-neutral-900 mt-1">{currency.format(data.totals.debit)}</p>
      </div>
      <div class="bg-white rounded-xl border border-neutral-200 px-4 py-3.5">
        <p class="text-xs uppercase tracking-wide font-semibold text-neutral-500">Total Credit</p>
        <p class="text-base font-semibold text-neutral-900 mt-1">{currency.format(data.totals.credit)}</p>
      </div>
      <div class="bg-white rounded-xl border border-neutral-200 px-4 py-3.5">
        <p class="text-xs uppercase tracking-wide font-semibold text-neutral-500">Draft Journals</p>
        <p class="text-base font-semibold text-neutral-900 mt-1">{data.draft_journal_count}</p>
      </div>
    </div>

    <section class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      <div class="px-5 py-4 border-b border-neutral-100 flex items-center justify-between">
        <h2 class="text-sm font-semibold text-neutral-900 uppercase tracking-wide">Account Balances</h2>
        <span class="text-xs text-neutral-500">{data.row_count} accounts</span>
      </div>

      {#if data.rows.length === 0}
        <div class="py-14 text-center text-sm text-neutral-500">No posted ledger activity found for selected date.</div>
      {:else}
        <div class="overflow-x-auto">
          <table class="w-full min-w-[940px] text-sm">
            <thead>
              <tr class="border-b border-neutral-100 text-left">
                <th class="px-5 py-3 text-xs uppercase tracking-wide font-semibold text-neutral-500">Account</th>
                <th class="px-5 py-3 text-xs uppercase tracking-wide font-semibold text-neutral-500">Type</th>
                <th class="px-5 py-3 text-xs uppercase tracking-wide font-semibold text-neutral-500 text-right">Movement Debit</th>
                <th class="px-5 py-3 text-xs uppercase tracking-wide font-semibold text-neutral-500 text-right">Movement Credit</th>
                <th class="px-5 py-3 text-xs uppercase tracking-wide font-semibold text-neutral-500 text-right">Closing Debit</th>
                <th class="px-5 py-3 text-xs uppercase tracking-wide font-semibold text-neutral-500 text-right">Closing Credit</th>
              </tr>
            </thead>
            <tbody>
              {#each data.rows as row (row.account_id)}
                <tr class="border-b border-neutral-50 hover:bg-neutral-50/60 transition-colors">
                  <td class="px-5 py-3.5">
                    <p class="font-medium text-neutral-900">{row.account_code}</p>
                    <p class="text-xs text-neutral-500">{row.account_name}</p>
                  </td>
                  <td class="px-5 py-3.5 text-neutral-600 capitalize">{row.account_type}</td>
                  <td class="px-5 py-3.5 text-right tabular-nums">{currency.format(row.movement_debit)}</td>
                  <td class="px-5 py-3.5 text-right tabular-nums">{currency.format(row.movement_credit)}</td>
                  <td class="px-5 py-3.5 text-right tabular-nums font-medium text-neutral-900">{currency.format(row.debit_balance)}</td>
                  <td class="px-5 py-3.5 text-right tabular-nums font-medium text-neutral-900">{currency.format(row.credit_balance)}</td>
                </tr>
              {/each}
            </tbody>
            <tfoot>
              <tr class="bg-neutral-50 border-t border-neutral-200">
                <td class="px-5 py-3 text-xs uppercase tracking-wide font-semibold text-neutral-600" colspan="4">Totals</td>
                <td class="px-5 py-3 text-right text-sm font-semibold text-neutral-900">{currency.format(data.totals.debit)}</td>
                <td class="px-5 py-3 text-right text-sm font-semibold text-neutral-900">{currency.format(data.totals.credit)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      {/if}
    </section>
  {/if}
</div>

<script lang="ts">
  import { api } from "$lib/api";
  import { parsePortalError } from "$lib/partnerPortal";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    PartnerPortalContextResponse,
    PartnerPortalFinancialResponse,
  } from "$lib/types";

  let loading = $state(true);
  let context = $state<PartnerPortalContextResponse | null>(null);
  let data = $state<PartnerPortalFinancialResponse | null>(null);

  function titleCase(value: string): string {
    return value
      .replaceAll("_", " ")
      .split(" ")
      .filter(Boolean)
      .map((part) => part[0]?.toUpperCase() + part.slice(1))
      .join(" ");
  }

  function summaryRows(summary: Record<string, string | number>): Array<{ key: string; value: string }> {
    return Object.entries(summary).map(([key, value]) => ({
      key: titleCase(key),
      value: String(value),
    }));
  }

  function formatMoney(value: string | number | null): string {
    if (value === null || value === "") return "\u2014";
    return currency.format(value);
  }

  async function loadFinancialOverview() {
    loading = true;
    try {
      const ctx = await api.get<PartnerPortalContextResponse>("/partners/portal/context/");
      context = ctx;
      if (!ctx.is_partner_user && !ctx.is_preview_mode) {
        data = null;
        return;
      }
      const result = await api.get<PartnerPortalFinancialResponse>("/partners/portal/financial/");
      data = result;
    } catch (error) {
      toast.error("Load failed", parsePortalError(error, "Could not load portal financial overview."));
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    loadFinancialOverview();
  });
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
  </div>
{:else if context && !context.is_partner_user && !context.is_preview_mode}
  <div class="rounded-xl border border-amber-200 bg-amber-50 px-6 py-5">
    <h1 class="text-lg font-semibold text-amber-900">No financial access yet</h1>
    <p class="mt-1 text-sm text-amber-800">Financial visibility is controlled by budget scope and entitlement matrix settings.</p>
  </div>
{:else if data}
  <div class="space-y-6">
    <div class="flex items-start justify-between gap-4">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-slate-700">Partners</p>
        <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Financial Distribution and Statements</h1>
        <p class="mt-1 text-sm text-neutral-500">Computed receivables, payables, capital flows, and position summaries.</p>
      </div>
      <button
        onclick={() => loadFinancialOverview()}
        class="rounded-lg border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
      >
        Refresh
      </button>
    </div>

    {#if data.client}
      <section class="space-y-4 rounded-xl border border-neutral-200 bg-white p-5">
        <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Client Ledger</h2>
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {#each summaryRows(data.client.summary) as row (row.key)}
            <div class="rounded-lg border border-neutral-100 bg-neutral-50 px-3 py-2">
              <p class="text-[10px] uppercase tracking-wide text-neutral-500">{row.key}</p>
              <p class="mt-1 text-base font-semibold text-neutral-900">{row.value}</p>
            </div>
          {/each}
        </div>
        <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div class="rounded-lg border border-neutral-100">
            <div class="border-b border-neutral-100 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-neutral-500">Payment Plans</div>
            <div class="max-h-72 overflow-y-auto px-4 py-3 text-sm">
              {#if data.client.payment_plans.length === 0}
                <p class="text-neutral-500">No payment plans.</p>
              {:else}
                <div class="space-y-2">
                  {#each data.client.payment_plans as row (row.id)}
                    <div class="rounded border border-neutral-100 bg-neutral-50 px-3 py-2">
                      <p class="font-medium text-neutral-900">{row.plan_number} • {row.title}</p>
                      <p class="text-xs text-neutral-600">{titleCase(row.status)} • {formatMoney(row.total_amount)}</p>
                    </div>
                  {/each}
                </div>
              {/if}
            </div>
          </div>

          <div class="rounded-lg border border-neutral-100">
            <div class="border-b border-neutral-100 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-neutral-500">Invoices</div>
            <div class="max-h-72 overflow-y-auto px-4 py-3 text-sm">
              {#if data.client.invoices.length === 0}
                <p class="text-neutral-500">No invoices.</p>
              {:else}
                <div class="space-y-2">
                  {#each data.client.invoices as row (row.id)}
                    <div class="rounded border border-neutral-100 bg-neutral-50 px-3 py-2">
                      <p class="font-medium text-neutral-900">{row.invoice_number} • {formatMoney(row.total_amount)}</p>
                      <p class="text-xs text-neutral-600">{titleCase(row.status)} • Due {row.due_date}</p>
                    </div>
                  {/each}
                </div>
              {/if}
            </div>
          </div>
        </div>
      </section>
    {/if}

    {#if data.contractor}
      <section class="space-y-4 rounded-xl border border-neutral-200 bg-white p-5">
        <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Contractor Commercial</h2>
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {#each summaryRows(data.contractor.summary) as row (row.key)}
            <div class="rounded-lg border border-neutral-100 bg-neutral-50 px-3 py-2">
              <p class="text-[10px] uppercase tracking-wide text-neutral-500">{row.key}</p>
              <p class="mt-1 text-base font-semibold text-neutral-900">{row.value}</p>
            </div>
          {/each}
        </div>
        <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div class="rounded-lg border border-neutral-100">
            <div class="border-b border-neutral-100 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-neutral-500">Purchase Orders</div>
            <div class="max-h-72 overflow-y-auto px-4 py-3 text-sm">
              {#if data.contractor.purchase_orders.length === 0}
                <p class="text-neutral-500">No purchase orders.</p>
              {:else}
                <div class="space-y-2">
                  {#each data.contractor.purchase_orders as row (row.id)}
                    <div class="rounded border border-neutral-100 bg-neutral-50 px-3 py-2">
                      <p class="font-medium text-neutral-900">{row.po_number} • {formatMoney(row.total_amount)}</p>
                      <p class="text-xs text-neutral-600">{titleCase(row.status)} • {row.issue_date}</p>
                    </div>
                  {/each}
                </div>
              {/if}
            </div>
          </div>

          <div class="rounded-lg border border-neutral-100">
            <div class="border-b border-neutral-100 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-neutral-500">Bills</div>
            <div class="max-h-72 overflow-y-auto px-4 py-3 text-sm">
              {#if data.contractor.bills.length === 0}
                <p class="text-neutral-500">No bills.</p>
              {:else}
                <div class="space-y-2">
                  {#each data.contractor.bills as row (row.id)}
                    <div class="rounded border border-neutral-100 bg-neutral-50 px-3 py-2">
                      <p class="font-medium text-neutral-900">{row.bill_number} • {formatMoney(row.total_amount)}</p>
                      <p class="text-xs text-neutral-600">{titleCase(row.status)} • Due {row.due_date}</p>
                    </div>
                  {/each}
                </div>
              {/if}
            </div>
          </div>
        </div>
      </section>
    {/if}

    {#if data.investor}
      <section class="space-y-4 rounded-xl border border-neutral-200 bg-white p-5">
        <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Investor Capital Flow</h2>
        <div class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {#each summaryRows(data.investor.summary) as row (row.key)}
            <div class="rounded-lg border border-neutral-100 bg-neutral-50 px-3 py-2">
              <p class="text-[10px] uppercase tracking-wide text-neutral-500">{row.key}</p>
              <p class="mt-1 text-base font-semibold text-neutral-900">{row.value}</p>
            </div>
          {/each}
        </div>
        <div class="rounded-lg border border-neutral-100">
          <div class="border-b border-neutral-100 px-4 py-3 text-xs font-semibold uppercase tracking-wider text-neutral-500">Recent Contributions</div>
          <div class="max-h-72 overflow-y-auto px-4 py-3 text-sm">
            {#if data.investor.contributions.length === 0}
              <p class="text-neutral-500">No contributions recorded.</p>
            {:else}
              <div class="space-y-2">
                {#each data.investor.contributions as row (row.id)}
                  <div class="rounded border border-neutral-100 bg-neutral-50 px-3 py-2">
                    <p class="font-medium text-neutral-900">{row.investor_name} • {formatMoney(row.amount)}</p>
                    <p class="text-xs text-neutral-600">{row.project_name} • {row.contribution_date}</p>
                  </div>
                {/each}
              </div>
            {/if}
          </div>
        </div>
      </section>
    {/if}
  </div>
{/if}

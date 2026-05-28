<script lang="ts">
  import { onMount } from "svelte";

  import { ApiError, api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";

  interface Overview {
    generated_at: string;
    kpis: {
      payments_this_month: string;
      outstanding_total: string;
      overdue_total: string;
      paid_invoices: number;
      receipt_documents: number;
    };
    recent_payments: PaymentRecord[];
    collections_watchlist: InvoiceRecord[];
  }

  interface PaymentRecord {
    id: number;
    invoice_id: number;
    invoice_number: string;
    customer_name: string;
    amount: string;
    payment_date: string;
    payment_method_display: string;
    reference_number: string;
  }

  interface InvoiceRecord {
    id: number;
    invoice_number: string;
    customer_name: string;
    due_date: string;
    balance_due: string;
    status_display: string;
  }

  interface LookupInvoice {
    id: number;
    label: string;
    balance_due: string;
  }

  let loading = $state(true);
  let refreshing = $state(false);
  let syncing = $state(false);
  let saving = $state(false);
  let showDrawer = $state(false);

  let overview = $state<Overview | null>(null);
  let payments = $state<PaymentRecord[]>([]);
  let invoiceLookup = $state<LookupInvoice[]>([]);
  let paymentMethods = $state<Array<{ value: string; label: string }>>([]);

  let form = $state({
    invoice: "",
    amount: "",
    payment_date: "",
    payment_method: "bank_transfer",
    reference_number: "",
    notes: "",
  });

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");
  function devFillPayment() {
    const today = new Date().toISOString().slice(0, 10);
    const methods = ["bank_transfer", "cash", "cheque", "online", "pos"];
    form.amount = String(Math.floor(Math.random() * 3000000) + 100000);
    form.payment_date = today;
    form.payment_method = methods[Math.floor(Math.random() * methods.length)];
    form.reference_number = `PAY-${Date.now().toString(36).toUpperCase()}`;
    form.notes = "Payment received and confirmed. Receipt issued to tenant.";
  }

  function fmtDate(value?: string | null) {
    if (!value) return "--";
    return new Date(value).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
  }

  function fmtDateTime(value?: string | null) {
    if (!value) return "--";
    return new Date(value).toLocaleString();
  }

  function fmtMoney(value?: string | number | null) {
    return new Intl.NumberFormat(undefined, { style: "currency", currency: "NGN", maximumFractionDigits: 2 }).format(Number(value ?? 0));
  }

  function parseApiMessage(error: unknown, fallback: string) {
    if (error instanceof ApiError) {
      if (typeof error.body?.detail === "string" && error.body.detail.trim()) return error.body.detail;
      const fieldMessage = Object.values(error.fieldErrors).flat().join(" ").trim();
      if (fieldMessage) return fieldMessage;
    }
    if (error instanceof Error && error.message.trim()) return error.message;
    return fallback;
  }

  async function loadData(showSpinner = true) {
    if (showSpinner) loading = true;
    try {
      const [overviewRes, paymentRes, lookupsRes] = await Promise.all([
        api.get<Overview>("/tenants/payments/overview/"),
        api.get<{ results: PaymentRecord[] }>("/tenants/payments/records/"),
        api.get<any>("/tenants/operations/lookups/"),
      ]);
      overview = overviewRes;
      payments = paymentRes.results ?? [];
      invoiceLookup = lookupsRes.invoices ?? [];
      paymentMethods = lookupsRes.payment_methods ?? [];
    } catch (error) {
      toast.error("Load failed", parseApiMessage(error, "Could not load payments and collections."));
    } finally {
      loading = false;
      refreshing = false;
    }
  }

  async function refreshAll() {
    refreshing = true;
    await loadData(false);
  }

  async function runWorkflows() {
    syncing = true;
    try {
      const result = await api.post<Record<string, number>>("/tenants/payments/sync/", {});
      toast.success(
        "Collections sync completed",
        `Payments reconciled ${result.payments_reconciled ?? 0}, receipts ${result.receipts_created ?? 0}.`,
      );
      await loadData(false);
    } catch (error) {
      toast.error("Workflow failed", parseApiMessage(error, "Could not run payment workflows."));
    } finally {
      syncing = false;
    }
  }

  function openDrawer() {
    form = {
      invoice: "",
      amount: "",
      payment_date: new Date().toISOString().slice(0, 10),
      payment_method: "bank_transfer",
      reference_number: "",
      notes: "",
    };
    showDrawer = true;
  }

  async function savePayment() {
    saving = true;
    try {
      await api.post("/tenants/payments/records/", {
        ...form,
        invoice: Number(form.invoice),
        amount: Number(form.amount || 0),
      });
      toast.success("Payment recorded", "Reconciliation, receipt generation, and reminders were refreshed.");
      showDrawer = false;
      await loadData(false);
    } catch (error) {
      toast.error("Save failed", parseApiMessage(error, "Could not record the payment."));
    } finally {
      saving = false;
    }
  }

  onMount(() => {
    void loadData();
  });
</script>

<div class="space-y-6">
  <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-600">Tenants</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Payments & Collections</h1>
      <p class="mt-2 max-w-3xl text-sm text-neutral-500">
        Payment records, reconciliation, outstanding balances, receipts, and collection visibility across the tenant portfolio.
      </p>
      {#if overview?.generated_at}<p class="mt-1 text-xs text-neutral-400">Last refreshed: {fmtDateTime(overview.generated_at)}</p>{/if}
    </div>
    <div class="flex items-center gap-2 self-start">
      <button onclick={refreshAll} disabled={refreshing || loading} class="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-neutral-200 bg-white text-neutral-700 shadow-sm hover:border-neutral-900 hover:text-neutral-900 disabled:opacity-50" aria-label="Refresh payments">
        <svg class={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8">
          <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992V4.356m-1.636 14.288A9 9 0 1 1 21 12.003" />
        </svg>
      </button>
      <button onclick={runWorkflows} disabled={syncing || loading} class="rounded-xl border border-neutral-900 bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50">
        {syncing ? "Running..." : "Run Workflows"}
      </button>
    </div>
  </div>

  <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
    <section class="rounded-2xl border border-emerald-200/70 bg-linear-to-br from-emerald-50 via-white to-teal-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-emerald-700">This Month</p><p class="mt-3 text-xl font-semibold text-emerald-700">{fmtMoney(overview?.kpis.payments_this_month)}</p></section>
    <section class="rounded-2xl border border-amber-200/70 bg-linear-to-br from-amber-50 via-white to-yellow-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-amber-700">Outstanding</p><p class="mt-3 text-xl font-semibold text-neutral-900">{fmtMoney(overview?.kpis.outstanding_total)}</p></section>
    <section class="rounded-2xl border border-rose-200/70 bg-linear-to-br from-rose-50 via-white to-red-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-rose-700">Overdue</p><p class="mt-3 text-xl font-semibold text-neutral-900">{fmtMoney(overview?.kpis.overdue_total)}</p></section>
    <section class="rounded-2xl border border-sky-200/70 bg-linear-to-br from-sky-50 via-white to-cyan-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-sky-700">Paid Invoices</p><p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.paid_invoices ?? 0}</p></section>
    <section class="rounded-2xl border border-neutral-200 bg-linear-to-br from-neutral-50 via-white to-slate-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-600">Receipts</p><p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.receipt_documents ?? 0}</p></section>
  </div>

  {#if loading}
    <div class="rounded-2xl border border-neutral-200 bg-white p-12 text-center text-sm text-neutral-500">Loading collections...</div>
  {:else}
    <section class="rounded-[28px] border border-neutral-200 bg-white p-5 shadow-[0_20px_60px_-48px_rgba(15,23,42,0.4)]">
      <div class="grid gap-6 xl:grid-cols-[1.35fr_1fr]">
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Payment Records</p>
              <h2 class="mt-1 text-sm font-bold uppercase tracking-widest text-neutral-900">Bank, card, wallet, and receipt trail</h2>
            </div>
            <button onclick={openDrawer} class="rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-600">Record Payment</button>
          </div>
          <div class="overflow-x-auto rounded-2xl border border-neutral-200">
            <table class="min-w-full divide-y divide-neutral-200 text-sm">
              <thead class="bg-neutral-50 text-[11px] uppercase tracking-[0.22em] text-neutral-500">
                <tr>
                  <th class="px-4 py-3 text-left">Invoice</th>
                  <th class="px-4 py-3 text-left">Tenant</th>
                  <th class="px-4 py-3 text-left">Amount</th>
                  <th class="px-4 py-3 text-left">Date</th>
                  <th class="px-4 py-3 text-left">Method</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100 bg-white">
                {#each payments.slice(0, 14) as payment}
                  <tr class="transition hover:bg-neutral-50/80">
                    <td class="px-4 py-3 font-semibold text-neutral-900">{payment.invoice_number}</td>
                    <td class="px-4 py-3 text-neutral-600">{payment.customer_name}</td>
                    <td class="px-4 py-3 text-neutral-900">{fmtMoney(payment.amount)}</td>
                    <td class="px-4 py-3 text-neutral-600">{fmtDate(payment.payment_date)}</td>
                    <td class="px-4 py-3 text-neutral-600">{payment.payment_method_display}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>
        <div class="rounded-2xl border border-neutral-200 bg-neutral-50/70 p-4">
          <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Outstanding Watchlist</p>
          <div class="mt-4 space-y-3">
            {#each overview?.collections_watchlist ?? [] as invoice}
              <article class="rounded-2xl border border-white/80 bg-white p-3 shadow-sm">
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <p class="text-sm font-semibold text-neutral-900">{invoice.invoice_number}</p>
                    <p class="text-xs text-neutral-500">{invoice.customer_name} • due {fmtDate(invoice.due_date)}</p>
                  </div>
                  <span class="rounded-full bg-neutral-100 px-3 py-1 text-[11px] font-semibold text-neutral-700">{invoice.status_display}</span>
                </div>
                <p class="mt-2 text-sm text-neutral-600">Balance {fmtMoney(invoice.balance_due)}</p>
              </article>
            {/each}
          </div>
        </div>
      </div>
    </section>
  {/if}
</div>

{#if showDrawer}
  <button class="fixed inset-0 z-40 bg-neutral-950/30" onclick={() => (showDrawer = false)} aria-label="Close drawer"></button>
  <aside class="fixed right-0 top-0 z-50 h-full w-full max-w-xl overflow-y-auto border-l border-neutral-200 bg-white shadow-2xl">
    <div class="flex items-center justify-between border-b border-neutral-200 px-6 py-4">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Collections</p>
        <h2 class="mt-1 text-sm font-bold uppercase tracking-widest text-neutral-900">Record Payment</h2>
      </div>
      <button onclick={() => (showDrawer = false)} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-600 hover:border-neutral-900 hover:text-neutral-900">Close</button>
    </div>
    <div class="space-y-4 px-6 py-5">
      <label class="space-y-2 text-sm text-neutral-600"><span>Invoice</span><select bind:value={form.invoice} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5"><option value="">Select invoice</option>{#each invoiceLookup as item}<option value={item.id}>{item.label}</option>{/each}</select></label>
      <div class="grid gap-4 sm:grid-cols-2">
        <label class="space-y-2 text-sm text-neutral-600"><span>Amount</span><input type="number" bind:value={form.amount} class="w-full rounded-xl border border-neutral-200 px-3 py-2.5" /></label>
        <label class="space-y-2 text-sm text-neutral-600"><span>Payment date</span><input type="date" bind:value={form.payment_date} class="w-full rounded-xl border border-neutral-200 px-3 py-2.5" /></label>
      </div>
      <div class="grid gap-4 sm:grid-cols-2">
        <label class="space-y-2 text-sm text-neutral-600"><span>Method</span><select bind:value={form.payment_method} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5">{#each paymentMethods as method}<option value={method.value}>{method.label}</option>{/each}</select></label>
        <label class="space-y-2 text-sm text-neutral-600"><span>Reference</span><input bind:value={form.reference_number} class="w-full rounded-xl border border-neutral-200 px-3 py-2.5" /></label>
      </div>
    </div>
    <div class="sticky bottom-0 flex items-center justify-end gap-3 border-t border-neutral-200 bg-white px-6 py-4">
      {#if isDev}<button type="button" onclick={devFillPayment} class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>{/if}
      <button onclick={() => (showDrawer = false)} class="rounded-xl border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900">Cancel</button>
      <button onclick={savePayment} disabled={saving} class="rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{saving ? "Saving..." : "Record Payment"}</button>
    </div>
  </aside>
{/if}

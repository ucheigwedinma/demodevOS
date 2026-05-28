<script lang="ts">
  import { onMount } from "svelte";

  import { ApiError, api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";

  interface Overview {
    generated_at: string;
    kpis: {
      active_charge_rules: number;
      draft_or_sent_invoices: number;
      overdue_invoices: number;
      outstanding_total: string;
      utility_bills: number;
    };
    invoice_watchlist: InvoiceRecord[];
    utility_watchlist: UtilityBillRecord[];
  }

  interface InvoiceRecord {
    id: number;
    invoice_number: string;
    customer_name: string;
    property_name: string;
    status: string;
    status_display: string;
    issue_date: string;
    due_date: string;
    total_amount: string;
    balance_due: string;
  }

  interface UtilityBillRecord {
    id: number;
    bill_number: string;
    property_name: string;
    utility_type_display: string;
    status_display: string;
    due_date: string;
    total_amount: string;
  }

  interface ChargeRule {
    id: number;
    tenant_name: string;
    lease_code: string;
    title: string;
    charge_type_display: string;
    status_display: string;
    amount: string;
    currency?: string;
    frequency_display: string;
    next_invoice_date: string | null;
  }

  interface LookupItem {
    id: number;
    label: string;
  }

  let loading = $state(true);
  let refreshing = $state(false);
  let syncing = $state(false);
  let saving = $state(false);
  let showDrawer = $state(false);

  let overview = $state<Overview | null>(null);
  let chargeRules = $state<ChargeRule[]>([]);
  let invoices = $state<InvoiceRecord[]>([]);

  let tenantLookup = $state<LookupItem[]>([]);
  let leaseLookup = $state<LookupItem[]>([]);
  let unitLookup = $state<LookupItem[]>([]);
  let spaceLookup = $state<LookupItem[]>([]);

  let form = $state({
    tenant_profile: "",
    lease_agreement: "",
    unit: "",
    facility_space: "",
    title: "",
    charge_type: "rent",
    amount: "",
    frequency: "monthly",
    start_date: "",
    end_date: "",
    applies_mid_period_proration: true,
    auto_invoice: true,
    notes: "",
  });

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");
  function devFillBillingRule() {
    const today = new Date().toISOString().slice(0, 10);
    const nextYear = new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
    const titles = ["Monthly Rent Charge", "Quarterly Service Charge", "Annual Insurance Levy", "Monthly Utility Contribution", "Parking Space Fee", "Generator Diesel Contribution"];
    const chargeTypes = ["rent", "service_charge", "insurance", "utility", "parking", "diesel"];
    const frequencies = ["monthly", "quarterly", "annually", "monthly", "monthly", "monthly"];
    const idx = Math.floor(Math.random() * titles.length);
    form.title = titles[idx];
    form.charge_type = chargeTypes[idx];
    form.amount = String(Math.floor(Math.random() * 2000000) + 50000);
    form.frequency = frequencies[idx];
    form.start_date = today;
    form.end_date = nextYear;
    form.applies_mid_period_proration = true;
    form.auto_invoice = true;
    form.notes = `Recurring ${frequencies[idx]} charge as per lease agreement terms.`;
  }

  function fmtDate(value?: string | null) {
    if (!value) return "--";
    return new Date(value).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
  }

  function fmtDateTime(value?: string | null) {
    if (!value) return "--";
    return new Date(value).toLocaleString();
  }

  function fmtMoney(value?: string | number | null, currency = "NGN") {
    return new Intl.NumberFormat(undefined, { style: "currency", currency, maximumFractionDigits: 2 }).format(Number(value ?? 0));
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
      const [overviewRes, rulesRes, invoiceRes, lookupsRes] = await Promise.all([
        api.get<Overview>("/tenants/billing/overview/"),
        api.get<ChargeRule[]>("/tenants/billing/charge-rules/"),
        api.get<{ results: InvoiceRecord[] }>("/tenants/billing/invoices/"),
        api.get<any>("/tenants/operations/lookups/"),
      ]);
      overview = overviewRes;
      chargeRules = rulesRes;
      invoices = invoiceRes.results ?? [];
      tenantLookup = lookupsRes.tenants ?? [];
      leaseLookup = (lookupsRes.leases ?? []).map((item: any) => ({ id: item.id, label: item.label }));
      unitLookup = lookupsRes.units ?? [];
      spaceLookup = lookupsRes.spaces ?? [];
    } catch (error) {
      toast.error("Load failed", parseApiMessage(error, "Could not load billing and charges."));
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
      const result = await api.post<Record<string, number>>("/tenants/billing/sync/", {});
      toast.success(
        "Billing sync completed",
        `Invoices created ${result.invoices_created ?? 0}, reconciled ${result.payments_reconciled ?? 0}, reminders ${result.rent_reminders_sent ?? 0}.`,
      );
      await loadData(false);
    } catch (error) {
      toast.error("Workflow failed", parseApiMessage(error, "Could not run billing workflows."));
    } finally {
      syncing = false;
    }
  }

  function openDrawer() {
    form = {
      tenant_profile: "",
      lease_agreement: "",
      unit: "",
      facility_space: "",
      title: "",
      charge_type: "rent",
      amount: "",
      frequency: "monthly",
      start_date: "",
      end_date: "",
      applies_mid_period_proration: true,
      auto_invoice: true,
      notes: "",
    };
    showDrawer = true;
  }

  async function saveRule() {
    saving = true;
    try {
      await api.post("/tenants/billing/charge-rules/", {
        ...form,
        tenant_profile: Number(form.tenant_profile),
        lease_agreement: form.lease_agreement ? Number(form.lease_agreement) : null,
        unit: form.unit ? Number(form.unit) : null,
        facility_space: form.facility_space ? Number(form.facility_space) : null,
        amount: Number(form.amount || 0),
        end_date: form.end_date || null,
      });
      toast.success("Charge rule created", "Recurring billing and proration logic are now active.");
      showDrawer = false;
      await loadData(false);
    } catch (error) {
      toast.error("Save failed", parseApiMessage(error, "Could not create the charge rule."));
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
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-amber-600">Tenants</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Billing & Charges</h1>
      <p class="mt-2 max-w-3xl text-sm text-neutral-500">
        Recurring rent and service-charge engine with proration support, utility bill visibility, penalties, discounts, and concessions.
      </p>
      {#if overview?.generated_at}<p class="mt-1 text-xs text-neutral-400">Last refreshed: {fmtDateTime(overview.generated_at)}</p>{/if}
    </div>
    <div class="flex items-center gap-2 self-start">
      <button onclick={refreshAll} disabled={refreshing || loading} class="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-neutral-200 bg-white text-neutral-700 shadow-sm hover:border-neutral-900 hover:text-neutral-900 disabled:opacity-50" aria-label="Refresh billing">
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
    <section class="rounded-2xl border border-amber-200/70 bg-linear-to-br from-amber-50 via-white to-yellow-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-amber-700">Active Rules</p><p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.active_charge_rules ?? 0}</p></section>
    <section class="rounded-2xl border border-sky-200/70 bg-linear-to-br from-sky-50 via-white to-cyan-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-sky-700">Open Invoices</p><p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.draft_or_sent_invoices ?? 0}</p></section>
    <section class="rounded-2xl border border-rose-200/70 bg-linear-to-br from-rose-50 via-white to-red-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-rose-700">Overdue</p><p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.overdue_invoices ?? 0}</p></section>
    <section class="rounded-2xl border border-emerald-200/70 bg-linear-to-br from-emerald-50 via-white to-teal-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-emerald-700">Outstanding</p><p class="mt-3 text-xl font-semibold text-emerald-700">{fmtMoney(overview?.kpis.outstanding_total)}</p></section>
    <section class="rounded-2xl border border-neutral-200 bg-linear-to-br from-neutral-50 via-white to-slate-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-600">Utility Bills</p><p class="mt-3 text-2xl font-semibold text-neutral-900">{overview?.kpis.utility_bills ?? 0}</p></section>
  </div>

  {#if loading}
    <div class="rounded-2xl border border-neutral-200 bg-white p-12 text-center text-sm text-neutral-500">Loading billing engine...</div>
  {:else}
    <section class="rounded-[28px] border border-neutral-200 bg-white p-5 shadow-[0_20px_60px_-48px_rgba(15,23,42,0.4)]">
      <div class="grid gap-6 xl:grid-cols-[1.35fr_1fr]">
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Recurring Charge Rules</p>
              <h2 class="mt-1 text-sm font-bold uppercase tracking-wider text-neutral-900">Automated rent, service charge, and concession setup</h2>
            </div>
            <button onclick={openDrawer} class="rounded-xl bg-amber-500 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-600">Add Rule</button>
          </div>
          <div class="overflow-x-auto rounded-2xl border border-neutral-200">
            <table class="min-w-full divide-y divide-neutral-200 text-sm">
              <thead class="bg-neutral-50 text-[11px] uppercase tracking-[0.22em] text-neutral-500">
                <tr>
                  <th class="px-4 py-3 text-left">Rule</th>
                  <th class="px-4 py-3 text-left">Type</th>
                  <th class="px-4 py-3 text-left">Amount</th>
                  <th class="px-4 py-3 text-left">Frequency</th>
                  <th class="px-4 py-3 text-left">Next Invoice</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100 bg-white">
                {#each chargeRules.slice(0, 12) as rule}
                  <tr class="transition hover:bg-neutral-50/80">
                    <td class="px-4 py-3"><p class="font-semibold text-neutral-900">{rule.title}</p><p class="text-xs text-neutral-500">{rule.tenant_name}</p></td>
                    <td class="px-4 py-3 text-neutral-600">{rule.charge_type_display}</td>
                    <td class="px-4 py-3 text-neutral-900">{fmtMoney(rule.amount, rule.currency || "NGN")}</td>
                    <td class="px-4 py-3 text-neutral-600">{rule.frequency_display}</td>
                    <td class="px-4 py-3 text-neutral-600">{fmtDate(rule.next_invoice_date)}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>

        <div class="space-y-4">
          <div class="rounded-2xl border border-neutral-200 bg-neutral-50/70 p-4">
            <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Invoice Watchlist</p>
            <div class="mt-4 space-y-3">
              {#each overview?.invoice_watchlist ?? [] as invoice}
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

          <div class="rounded-2xl border border-neutral-200 bg-neutral-50/70 p-4">
            <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Utility Bill Feed</p>
            <div class="mt-4 space-y-3">
              {#each overview?.utility_watchlist ?? [] as bill}
                <article class="rounded-2xl border border-white/80 bg-white p-3 shadow-sm">
                  <p class="text-sm font-semibold text-neutral-900">{bill.bill_number}</p>
                  <p class="mt-1 text-xs text-neutral-500">{bill.property_name} • {bill.utility_type_display}</p>
                  <p class="mt-2 text-sm text-neutral-600">{fmtMoney(bill.total_amount)} • due {fmtDate(bill.due_date)}</p>
                </article>
              {/each}
            </div>
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
        <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Tenant Billing</p>
        <h2 class="mt-1 text-sm font-bold uppercase tracking-wider text-neutral-900">Create Charge Rule</h2>
      </div>
      <button onclick={() => (showDrawer = false)} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-600 hover:border-neutral-900 hover:text-neutral-900">Close</button>
    </div>
    <div class="space-y-4 px-6 py-5">
      <label class="space-y-2 text-sm text-neutral-600"><span>Tenant</span><select bind:value={form.tenant_profile} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5"><option value="">Select tenant</option>{#each tenantLookup as item}<option value={item.id}>{item.label}</option>{/each}</select></label>
      <label class="space-y-2 text-sm text-neutral-600"><span>Lease</span><select bind:value={form.lease_agreement} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5"><option value="">Select lease</option>{#each leaseLookup as item}<option value={item.id}>{item.label}</option>{/each}</select></label>
      <label class="space-y-2 text-sm text-neutral-600"><span>Rule title</span><input bind:value={form.title} class="w-full rounded-xl border border-neutral-200 px-3 py-2.5" /></label>
      <div class="grid gap-4 sm:grid-cols-2">
        <label class="space-y-2 text-sm text-neutral-600"><span>Charge type</span><select bind:value={form.charge_type} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5"><option value="rent">Rent</option><option value="service_charge">Service charge</option><option value="utility">Utility</option><option value="penalty">Penalty</option><option value="damage">Damage</option><option value="discount">Discount</option><option value="concession">Concession</option></select></label>
        <label class="space-y-2 text-sm text-neutral-600"><span>Frequency</span><select bind:value={form.frequency} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5"><option value="once">One-time</option><option value="monthly">Monthly</option><option value="quarterly">Quarterly</option><option value="biannual">Biannual</option><option value="annual">Annual</option></select></label>
      </div>
      <div class="grid gap-4 sm:grid-cols-2">
        <label class="space-y-2 text-sm text-neutral-600"><span>Amount</span><input type="number" bind:value={form.amount} class="w-full rounded-xl border border-neutral-200 px-3 py-2.5" /></label>
        <label class="space-y-2 text-sm text-neutral-600"><span>Start date</span><input type="date" bind:value={form.start_date} class="w-full rounded-xl border border-neutral-200 px-3 py-2.5" /></label>
      </div>
      <div class="grid gap-4 sm:grid-cols-2">
        <label class="space-y-2 text-sm text-neutral-600"><span>Unit</span><select bind:value={form.unit} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5"><option value="">Select unit</option>{#each unitLookup as item}<option value={item.id}>{item.label}</option>{/each}</select></label>
        <label class="space-y-2 text-sm text-neutral-600"><span>Space</span><select bind:value={form.facility_space} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2.5"><option value="">Select space</option>{#each spaceLookup as item}<option value={item.id}>{item.label}</option>{/each}</select></label>
      </div>
    </div>
    <div class="sticky bottom-0 flex items-center justify-end gap-3 border-t border-neutral-200 bg-white px-6 py-4">
      {#if isDev}<button type="button" onclick={devFillBillingRule} class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>{/if}
      <button onclick={() => (showDrawer = false)} class="rounded-xl border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:border-neutral-900 hover:text-neutral-900">Cancel</button>
      <button onclick={saveRule} disabled={saving} class="rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">{saving ? "Saving..." : "Save Rule"}</button>
    </div>
  </aside>
{/if}

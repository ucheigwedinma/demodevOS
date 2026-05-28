<script lang="ts">
  import { onMount } from "svelte";

  import { ApiError, api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";

  interface ReportsOverview {
    generated_at: string;
    occupancy: {
      occupied_units: number;
      total_units: number;
      rate: number;
    };
    tenant_churn: {
      moved_out_90_days: number;
      active_tenants: number;
      rate: number;
    };
    revenue_per_tenant: Array<{ tenant_name: string; total_collected: string }>;
    revenue_per_property: Array<{ property_name: string; total_collected: string }>;
    payment_default_trend: Array<{ label: string; overdue_total: string }>;
    collection_trend: Array<{ label: string; total: string }>;
    lease_expiry_forecast: Array<{ label: string; count: number }>;
  }

  let loading = $state(true);
  let refreshing = $state(false);
  let report = $state<ReportsOverview | null>(null);

  function fmtDateTime(value?: string | null) {
    if (!value) return "--";
    return new Date(value).toLocaleString();
  }

  function fmtMoney(value?: string | number | null) {
    return new Intl.NumberFormat(undefined, { style: "currency", currency: "NGN", maximumFractionDigits: 2 }).format(Number(value ?? 0));
  }

  function parseApiMessage(error: unknown, fallback: string) {
    if (error instanceof ApiError && typeof error.body?.detail === "string" && error.body.detail.trim()) return error.body.detail;
    if (error instanceof Error && error.message.trim()) return error.message;
    return fallback;
  }

  async function loadData(showSpinner = true) {
    if (showSpinner) loading = true;
    try {
      report = await api.get<ReportsOverview>("/tenants/reports/overview/");
    } catch (error) {
      toast.error("Load failed", parseApiMessage(error, "Could not load tenant analytics."));
    } finally {
      loading = false;
      refreshing = false;
    }
  }

  async function refreshAll() {
    refreshing = true;
    await loadData(false);
  }

  onMount(() => {
    void loadData();
  });
</script>

<div class="space-y-6">
  <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">Tenants</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Reports & Analytics</h1>
      <p class="mt-2 max-w-3xl text-sm text-neutral-500">
        Occupancy, churn, revenue, payment-default trend, and lease-expiry forecasting for portfolio-level tenant management.
      </p>
      {#if report?.generated_at}<p class="mt-1 text-xs text-neutral-400">Last refreshed: {fmtDateTime(report.generated_at)}</p>{/if}
    </div>
    <button onclick={refreshAll} disabled={refreshing || loading} class="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-neutral-200 bg-white text-neutral-700 shadow-sm hover:border-neutral-900 hover:text-neutral-900 disabled:opacity-50">
      <svg class={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992V4.356m-1.636 14.288A9 9 0 1 1 21 12.003" /></svg>
    </button>
  </div>

  <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
    <section class="rounded-2xl border border-indigo-200/70 bg-linear-to-br from-indigo-50 via-white to-sky-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-indigo-700">Occupancy Rate</p><p class="mt-3 text-2xl font-semibold text-neutral-900">{report?.occupancy.rate ?? 0}%</p></section>
    <section class="rounded-2xl border border-amber-200/70 bg-linear-to-br from-amber-50 via-white to-yellow-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-amber-700">Churn Rate</p><p class="mt-3 text-2xl font-semibold text-neutral-900">{report?.tenant_churn.rate ?? 0}%</p></section>
    <section class="rounded-2xl border border-emerald-200/70 bg-linear-to-br from-emerald-50 via-white to-teal-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-emerald-700">Active Tenants</p><p class="mt-3 text-2xl font-semibold text-neutral-900">{report?.tenant_churn.active_tenants ?? 0}</p></section>
    <section class="rounded-2xl border border-rose-200/70 bg-linear-to-br from-rose-50 via-white to-red-50 p-4"><p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-rose-700">Moved Out 90d</p><p class="mt-3 text-2xl font-semibold text-neutral-900">{report?.tenant_churn.moved_out_90_days ?? 0}</p></section>
  </div>

  {#if loading}
    <div class="rounded-2xl border border-neutral-200 bg-white p-12 text-center text-sm text-neutral-500">Loading analytics...</div>
  {:else if report}
    <section class="rounded-[28px] border border-neutral-200 bg-white p-5 shadow-[0_20px_60px_-48px_rgba(15,23,42,0.4)]">
      <div class="grid gap-6 xl:grid-cols-2">
        <div class="space-y-4">
          <div class="rounded-2xl border border-neutral-200 bg-neutral-50/70 p-4">
            <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Revenue Per Tenant</p>
            <div class="mt-4 space-y-3">
              {#each report.revenue_per_tenant as row}
                <div class="flex items-center justify-between rounded-xl border border-white/80 bg-white px-3 py-2.5 shadow-sm">
                  <span class="text-sm font-medium text-neutral-700">{row.tenant_name}</span>
                  <span class="text-sm font-semibold text-emerald-700">{fmtMoney(row.total_collected)}</span>
                </div>
              {/each}
            </div>
          </div>
          <div class="rounded-2xl border border-neutral-200 bg-neutral-50/70 p-4">
            <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Revenue Per Property</p>
            <div class="mt-4 space-y-3">
              {#each report.revenue_per_property as row}
                <div class="flex items-center justify-between rounded-xl border border-white/80 bg-white px-3 py-2.5 shadow-sm">
                  <span class="text-sm font-medium text-neutral-700">{row.property_name}</span>
                  <span class="text-sm font-semibold text-emerald-700">{fmtMoney(row.total_collected)}</span>
                </div>
              {/each}
            </div>
          </div>
        </div>

        <div class="space-y-4">
          <div class="rounded-2xl border border-neutral-200 bg-neutral-50/70 p-4">
            <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Default Trend</p>
            <div class="mt-4 space-y-3">
              {#each report.payment_default_trend as row}
                <div class="flex items-center justify-between rounded-xl border border-white/80 bg-white px-3 py-2.5 shadow-sm">
                  <span class="text-sm font-medium text-neutral-700">{row.label}</span>
                  <span class="text-sm font-semibold text-rose-600">{fmtMoney(row.overdue_total)}</span>
                </div>
              {/each}
            </div>
          </div>
          <div class="rounded-2xl border border-neutral-200 bg-neutral-50/70 p-4">
            <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Lease Expiry Forecast</p>
            <div class="mt-4 space-y-3">
              {#each report.lease_expiry_forecast as row}
                <div class="flex items-center justify-between rounded-xl border border-white/80 bg-white px-3 py-2.5 shadow-sm">
                  <span class="text-sm font-medium text-neutral-700">{row.label}</span>
                  <span class="text-sm font-semibold text-neutral-900">{row.count}</span>
                </div>
              {/each}
            </div>
          </div>
        </div>
      </div>
    </section>
  {/if}
</div>

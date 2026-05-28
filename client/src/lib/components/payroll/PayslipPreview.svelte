<script lang="ts">
  import type { PayslipDetail } from "$lib/types";

  type Props = {
    open: boolean;
    loading?: boolean;
    payslip: PayslipDetail | null;
    employeeLabel: string;
    projectName: string;
    currencyCode: string;
    onClose: () => void;
  };

  let {
    open,
    loading = false,
    payslip,
    employeeLabel,
    projectName,
    currencyCode,
    onClose,
  }: Props = $props();

  const statusTone: Record<string, string> = {
    draft: "bg-orange-100/80 text-orange-700",
    generated: "bg-sky-100/80 text-sky-700",
    sent: "bg-indigo-100/80 text-indigo-700",
    acknowledged: "bg-emerald-100/80 text-emerald-700",
  };

  function formatCurrency(value: string | null | undefined): string {
    const amount = Number(value ?? 0);
    return new Intl.NumberFormat("en-NG", {
      style: "currency",
      currency: currencyCode || "NGN",
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(Number.isFinite(amount) ? amount : 0);
  }

  function formatDate(value: string | null | undefined): string {
    if (!value) return "Not scheduled";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat("en-NG", {
      day: "numeric",
      month: "short",
      year: "numeric",
    }).format(date);
  }
</script>

{#if open}
  <div
    class="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm"
    onclick={onClose}
    onkeydown={(event) => event.key === "Escape" && onClose()}
    role="button"
    tabindex="-1"
  ></div>

  <div class="fixed inset-y-0 right-0 z-50 w-full max-w-5xl bg-white shadow-2xl border-l border-neutral-200 flex flex-col drawer-slide-in">
    <div class="flex items-center justify-between px-6 py-4 bg-black border-b border-neutral-200">
      <div class="flex items-center gap-3">
        <div>
          <p class="text-[11px] font-semibold uppercase tracking-[0.3em] text-neutral-500">Payslip Preview</p>
          <h2 class="mt-1 text-lg font-bold text-white">{employeeLabel}</h2>
          <span class="text-xs text-neutral-400">
            {projectName}
            {#if payslip?.payroll_run_name}
              &middot; {payslip.payroll_run_name}
            {/if}
          </span>
        </div>
        {#if payslip}
          <span class="inline-flex rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] {statusTone[payslip.status] ?? 'bg-neutral-100 text-neutral-600'}">
            {payslip.status}
          </span>
        {/if}
      </div>

      <button
        onclick={onClose}
        class="w-8 h-8 flex items-center justify-center rounded-lg text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 transition-colors"
        aria-label="Close"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div class="px-6 py-3 border-b border-neutral-100 flex flex-wrap items-center gap-6 text-sm">
      <div>
        <span class="text-neutral-400">Period:</span>
        <span class="ml-1 font-semibold text-neutral-900">{formatDate(payslip?.period_start)} - {formatDate(payslip?.period_end)}</span>
      </div>
      <div>
        <span class="text-neutral-400">Net Pay:</span>
        <span class="ml-1 font-bold text-neutral-900 tabular-nums">{formatCurrency(payslip?.net_salary)}</span>
      </div>
      <div>
        <span class="text-neutral-400">Gross:</span>
        <span class="ml-1 font-semibold text-neutral-900 tabular-nums">{formatCurrency(payslip?.gross_salary)}</span>
      </div>
      <div>
        <span class="text-neutral-400">Generated:</span>
        <span class="ml-1 text-neutral-600">{formatDate(payslip?.generated_at)}</span>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto px-6 py-6">
      <div class="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <div class="space-y-5">
          <div class="rounded-[26px] border border-white/50 bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(247,244,248,0.82))] p-5 shadow-[0_20px_60px_rgba(148,163,184,0.18)] backdrop-blur-xl">
            {#if loading}
              <div class="flex min-h-48 items-center justify-center">
                <div class="h-8 w-8 rounded-full border-2 border-neutral-300 border-t-neutral-900 animate-spin"></div>
              </div>
            {:else if payslip}
              <div class="grid gap-4 sm:grid-cols-3">
                <div class="rounded-2xl border border-emerald-200/70 bg-emerald-50/80 p-4">
                  <p class="text-xs font-semibold uppercase tracking-[0.25em] text-emerald-600">Base</p>
                  <p class="mt-3 text-2xl font-semibold tracking-tight text-emerald-950">{formatCurrency(payslip.basic_salary)}</p>
                </div>
                <div class="rounded-2xl border border-sky-200/70 bg-sky-50/80 p-4">
                  <p class="text-xs font-semibold uppercase tracking-[0.25em] text-sky-600">Allowances</p>
                  <p class="mt-3 text-2xl font-semibold tracking-tight text-sky-950">{formatCurrency(payslip.total_allowances)}</p>
                </div>
                <div class="rounded-2xl border border-orange-200/70 bg-orange-50/80 p-4">
                  <p class="text-xs font-semibold uppercase tracking-[0.25em] text-orange-600">Deductions</p>
                  <p class="mt-3 text-2xl font-semibold tracking-tight text-orange-950">{formatCurrency(payslip.total_deductions)}</p>
                </div>
              </div>

              <div class="mt-5 rounded-[24px] border border-neutral-200 bg-neutral-950 p-5 text-white">
                <div class="flex items-end justify-between gap-4">
                  <div>
                    <p class="text-xs font-semibold uppercase tracking-[0.25em] text-white/60">Net Pay</p>
                    <p class="mt-3 text-3xl font-semibold tracking-tight">{formatCurrency(payslip.net_salary)}</p>
                  </div>
                  <div class="text-right">
                    <p class="text-xs uppercase tracking-[0.25em] text-white/50">Gross</p>
                    <p class="mt-2 text-lg font-medium text-white/90">{formatCurrency(payslip.gross_salary)}</p>
                  </div>
                </div>
              </div>
            {:else}
              <div class="flex min-h-48 flex-col items-center justify-center text-center">
                <p class="text-sm font-medium text-neutral-700">No payslip detail is available yet.</p>
                <p class="mt-2 max-w-sm text-sm text-neutral-500">
                  This payroll line is still waiting for a generated payslip or needs manual review before it can be previewed.
                </p>
              </div>
            {/if}
          </div>
        </div>

        <div class="space-y-4">
          <div class="rounded-[26px] border border-white/50 bg-white/55 p-5 shadow-[0_20px_60px_rgba(148,163,184,0.14)] backdrop-blur-xl">
            <p class="text-xs font-semibold uppercase tracking-[0.25em] text-neutral-400">Lifecycle</p>
            <div class="mt-4 space-y-3">
              <div class="flex items-center justify-between rounded-2xl bg-neutral-50/80 px-4 py-3">
                <span class="text-sm text-neutral-500">Generated</span>
                <span class="text-sm font-medium text-neutral-900">{formatDate(payslip?.generated_at)}</span>
              </div>
              <div class="flex items-center justify-between rounded-2xl bg-neutral-50/80 px-4 py-3">
                <span class="text-sm text-neutral-500">Sent</span>
                <span class="text-sm font-medium text-neutral-900">{formatDate(payslip?.sent_at)}</span>
              </div>
              <div class="flex items-center justify-between rounded-2xl bg-neutral-50/80 px-4 py-3">
                <span class="text-sm text-neutral-500">Payroll Run</span>
                <span class="text-right text-sm font-medium text-neutral-900">{payslip?.payroll_run_name ?? "Pending assignment"}</span>
              </div>
            </div>
          </div>

          <div class="rounded-[26px] border border-dashed border-neutral-300 bg-white/45 p-5 backdrop-blur-xl">
            <p class="text-xs font-semibold uppercase tracking-[0.25em] text-neutral-400">Review Notes</p>
            <p class="mt-4 text-sm leading-6 text-neutral-600">
              Use this preview to validate the salary mix before disbursement, especially where site allocations or allowances changed during the month.
            </p>
          </div>
        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  .drawer-slide-in { animation: drawerSlideIn 0.25s ease-out both; }
  @keyframes drawerSlideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }
</style>

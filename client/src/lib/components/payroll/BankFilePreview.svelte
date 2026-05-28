<script lang="ts">
  import type { DisbursementQueueRow } from "$lib/payroll/disbursementBatcher";
  import { maskAccount } from "$lib/payroll/disbursementBatcher";

  type Props = {
    open: boolean;
    batchLabel: string;
    periodLabel: string;
    rows: DisbursementQueueRow[];
    fundingAccountLabel: string;
    currencyCode: string;
    previewMode?: boolean;
    onClose: () => void;
  };

  let {
    open,
    batchLabel,
    periodLabel,
    rows,
    fundingAccountLabel,
    currencyCode,
    previewMode = false,
    onClose,
  }: Props = $props();

  function formatCurrency(value: number): string {
    return new Intl.NumberFormat("en-NG", {
      style: "currency",
      currency: currencyCode || "NGN",
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(Number.isFinite(value) ? value : 0);
  }

  function printSchedule() {
    window.print();
  }

  const totalAmount = $derived(rows.reduce((sum, row) => sum + row.netAmount, 0));
</script>

{#if open}
  <div
    class="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
    onclick={onClose}
    onkeydown={(event) => event.key === "Escape" && onClose()}
    role="button"
    tabindex="-1"
  ></div>

  <div class="fixed inset-x-4 top-8 z-50 mx-auto flex max-h-[88vh] w-full max-w-6xl flex-col overflow-hidden rounded-[32px] border border-white/30 bg-[linear-gradient(180deg,rgba(255,255,255,0.88),rgba(245,247,250,0.7))] shadow-[0_40px_120px_rgba(15,23,42,0.32)] backdrop-blur-2xl">
    <div class="border-b border-white/50 bg-[linear-gradient(135deg,rgba(17,24,39,0.92),rgba(32,32,32,0.84))] px-7 py-5 text-white">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p class="text-[11px] font-semibold uppercase tracking-[0.34em] text-white/60">Bank File Preview</p>
          <h2 class="mt-2 text-2xl font-semibold tracking-tight">{batchLabel}</h2>
          <p class="mt-2 max-w-2xl text-sm leading-6 text-white/70">
            Print-friendly disbursement schedule for manual authorization, bank portal upload, and treasury sign-off.
          </p>
        </div>

        <div class="flex flex-wrap items-center gap-3">
          <button
            type="button"
            class="inline-flex items-center justify-center rounded-2xl border border-white/20 bg-white/10 px-4 py-3 text-sm font-semibold text-white transition hover:bg-white/15"
            onclick={printSchedule}
          >
            Print Schedule
          </button>
          <button
            type="button"
            class="inline-flex items-center justify-center rounded-2xl bg-white px-4 py-3 text-sm font-semibold text-neutral-950 transition hover:bg-neutral-100"
            onclick={onClose}
          >
            Close
          </button>
        </div>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto p-6">
      <div class="grid gap-4 lg:grid-cols-3">
        <div class="rounded-[24px] border border-white/50 bg-white/65 p-5 shadow-[0_18px_50px_rgba(148,163,184,0.14)] backdrop-blur-xl">
          <p class="text-xs font-semibold uppercase tracking-[0.24em] text-neutral-400">Funding Account</p>
          <p class="mt-3 text-lg font-semibold text-neutral-950">{fundingAccountLabel}</p>
        </div>
        <div class="rounded-[24px] border border-white/50 bg-white/65 p-5 shadow-[0_18px_50px_rgba(148,163,184,0.14)] backdrop-blur-xl">
          <p class="text-xs font-semibold uppercase tracking-[0.24em] text-neutral-400">Period</p>
          <p class="mt-3 text-lg font-semibold text-neutral-950">{periodLabel}</p>
        </div>
        <div class="rounded-[24px] border border-emerald-200/70 bg-emerald-50/80 p-5 shadow-[0_18px_50px_rgba(16,185,129,0.12)] backdrop-blur-xl">
          <p class="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-600">Total Payable</p>
          <p class="mt-3 text-2xl font-bold tracking-tight text-emerald-950">{formatCurrency(totalAmount)}</p>
        </div>
      </div>

      <div class="mt-5 rounded-[28px] border border-white/50 bg-white/58 p-5 shadow-[0_18px_60px_rgba(148,163,184,0.15)] backdrop-blur-xl">
        <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p class="text-xs font-semibold uppercase tracking-[0.24em] text-neutral-400">Authorization Sheet</p>
            <p class="mt-2 text-sm leading-6 text-neutral-600">
              {#if previewMode}
                Preview data is active, so secure banking fields are represented with payroll seed values for interface validation.
              {:else}
                This schedule reflects live payroll and finance data. Secure bank fields remain masked until the source registry exposes them.
              {/if}
            </p>
          </div>
          <div class="rounded-2xl border border-dashed border-neutral-300 bg-neutral-50/75 px-4 py-3 text-sm text-neutral-600">
            Signature Block: Treasury, Finance Lead, and Bank Upload Officer
          </div>
        </div>

        <div class="mt-5 overflow-hidden rounded-[24px] border border-neutral-200/80 bg-white/80">
          <table class="min-w-full text-sm">
            <thead class="bg-neutral-50/90 text-[11px] uppercase tracking-[0.22em] text-neutral-400">
              <tr>
                <th class="px-4 py-3 text-left font-semibold">Beneficiary</th>
                <th class="px-4 py-3 text-left font-semibold">Project</th>
                <th class="px-4 py-3 text-left font-semibold">Bank Detail</th>
                <th class="px-4 py-3 text-left font-semibold">Method</th>
                <th class="px-4 py-3 text-right font-semibold">Amount</th>
              </tr>
            </thead>
            <tbody>
              {#each rows as row}
                <tr class="border-t border-neutral-200/70 align-top">
                  <td class="px-4 py-3">
                    <p class="font-medium text-neutral-950">{row.beneficiaryName}</p>
                    <p class="mt-1 text-xs text-neutral-500">{row.roleLabel}</p>
                  </td>
                  <td class="px-4 py-3">
                    <p class="font-medium text-neutral-900">{row.projectCode}</p>
                    <p class="mt-1 text-xs text-neutral-500">{row.projectName}</p>
                  </td>
                  <td class="px-4 py-3">
                    <p class="font-medium text-neutral-800">{row.banking.bankName || "Secure registry pending"}</p>
                    <p class="mt-1 text-xs text-neutral-500">
                      {row.banking.accountNumber ? maskAccount(row.banking.accountNumber) : row.validationLabel}
                    </p>
                  </td>
                  <td class="px-4 py-3 text-neutral-600">{row.banking.paymentMethod}</td>
                  <td class="px-4 py-3 text-right font-semibold text-neutral-950">{formatCurrency(row.netAmount)}</td>
                </tr>
              {/each}
              {#if rows.length === 0}
                <tr>
                  <td colspan="5" class="px-4 py-10 text-center text-sm text-neutral-500">
                    No disbursement lines are available for this batch yet.
                  </td>
                </tr>
              {/if}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
{/if}

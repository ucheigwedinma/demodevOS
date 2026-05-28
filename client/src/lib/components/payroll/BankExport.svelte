<script lang="ts">
  type BankExportRow = {
    employeeName: string;
    employeeId: string;
    amount: number;
    narration: string;
    projectName: string;
    runName: string;
    bankName: string;
    accountNumber: string;
    accountType: string;
    bankCode: string;
  };

  type BankPresetKey = "generic_ng" | "gtbank" | "zenith" | "access";

  type Props = {
    rows: BankExportRow[];
    currencyCode: string;
    periodLabel: string;
    previewMode?: boolean;
  };

  let {
    rows,
    currencyCode,
    periodLabel,
    previewMode = false,
  }: Props = $props();

  const presets: Array<{ key: BankPresetKey; label: string; description: string }> = [
    {
      key: "generic_ng",
      label: "Generic NG CSV",
      description: "Balanced schedule for finance review and broad bank uploads.",
    },
    {
      key: "gtbank",
      label: "GTBank",
      description: "Beneficiary-first order for typical bulk transfer preparation.",
    },
    {
      key: "zenith",
      label: "Zenith",
      description: "Account-led format for treasury review and upload staging.",
    },
    {
      key: "access",
      label: "Access",
      description: "Finance-friendly order for bulk credit batches.",
    },
  ];

  let preset = $state<BankPresetKey>("generic_ng");

  const totalPayable = $derived(rows.reduce((sum, row) => sum + row.amount, 0));
  const missingBankDetails = $derived(
    rows.filter((row) => !row.bankName.trim() || !row.accountNumber.trim()).length
  );

  function formatCurrency(value: number): string {
    return new Intl.NumberFormat("en-NG", {
      style: "currency",
      currency: currencyCode || "NGN",
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(value);
  }

  function csvEscape(value: string): string {
    if (/[",\n]/.test(value)) {
      return `"${value.replaceAll('"', '""')}"`;
    }
    return value;
  }

  function getHeaders(): string[] {
    switch (preset) {
      case "gtbank":
        return ["beneficiary_name", "account_number", "bank_code", "bank_name", "amount", "narration"];
      case "zenith":
        return ["account_number", "beneficiary_name", "bank_name", "bank_code", "amount", "narration"];
      case "access":
        return ["beneficiary_name", "bank_name", "account_number", "bank_code", "amount", "narration"];
      default:
        return [
          "employee_id",
          "beneficiary_name",
          "bank_name",
          "account_number",
          "bank_code",
          "account_type",
          "amount",
          "narration",
          "project",
          "run",
        ];
    }
  }

  function getRowValues(row: BankExportRow): string[] {
    const amount = row.amount.toFixed(2);
    switch (preset) {
      case "gtbank":
        return [
          row.employeeName,
          row.accountNumber,
          row.bankCode,
          row.bankName,
          amount,
          row.narration,
        ];
      case "zenith":
        return [
          row.accountNumber,
          row.employeeName,
          row.bankName,
          row.bankCode,
          amount,
          row.narration,
        ];
      case "access":
        return [
          row.employeeName,
          row.bankName,
          row.accountNumber,
          row.bankCode,
          amount,
          row.narration,
        ];
      default:
        return [
          row.employeeId,
          row.employeeName,
          row.bankName,
          row.accountNumber,
          row.bankCode,
          row.accountType,
          amount,
          row.narration,
          row.projectName,
          row.runName,
        ];
    }
  }

  function exportCsv() {
    if (!rows.length) return;
    const lines = [
      getHeaders().join(","),
      ...rows.map((row) => getRowValues(row).map(csvEscape).join(",")),
    ];

    const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `payroll-bank-schedule-${preset}-${periodLabel.toLowerCase().replaceAll(" ", "-")}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  }
</script>

<section class="min-w-0 rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
  <div class="flex flex-col gap-4">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-neutral-400">Bank Schedule</p>
        <h3 class="mt-2 text-lg font-semibold text-neutral-950">Bank Export Utility</h3>
        <p class="mt-1 text-sm text-neutral-500">
          Generate a treasury-ready payroll schedule for bulk upload across common Nigerian bank formats.
        </p>
      </div>

      <button
        type="button"
        class="inline-flex items-center justify-center rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-40"
        onclick={exportCsv}
        disabled={!rows.length}
      >
        Download CSV
      </button>
    </div>

    <div class="grid gap-3 sm:grid-cols-3 xl:grid-cols-1 2xl:grid-cols-3">
      <div class="min-w-0 rounded-2xl border border-neutral-200 bg-white p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Payable</p>
        <p class="mt-2 truncate text-lg font-bold tracking-tight tabular-nums text-neutral-900">{formatCurrency(totalPayable)}</p>
      </div>
      <div class="min-w-0 rounded-2xl border border-neutral-200 bg-white p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Beneficiaries</p>
        <p class="mt-2 truncate text-lg font-bold tracking-tight tabular-nums text-neutral-900">{rows.length}</p>
      </div>
      <div class="min-w-0 rounded-2xl border border-orange-200 bg-orange-50 p-4">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-orange-600">Missing Bank Data</p>
        <p class="mt-2 truncate text-lg font-bold tracking-tight tabular-nums text-orange-900">{missingBankDetails}</p>
      </div>
    </div>

    <label class="block">
      <span class="mb-2 block text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Bank Format</span>
      <select
        bind:value={preset}
        class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-2.5 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
      >
        {#each presets as item}
          <option value={item.key}>{item.label}</option>
        {/each}
      </select>
    </label>

    <div class="rounded-2xl border border-dashed border-neutral-300 bg-neutral-50 p-4">
      <p class="text-sm font-medium text-neutral-800">
        {presets.find((item) => item.key === preset)?.description}
      </p>
      <p class="mt-2 text-sm text-neutral-500">
        {#if previewMode}
          Preview mode is active, so bank name and account number fields remain placeholders until live HR banking data is connected.
        {:else if missingBankDetails > 0}
          {missingBankDetails} row{missingBankDetails === 1 ? "" : "s"} still need bank name or account number before upload.
        {:else}
          All exported rows include the minimum schedule fields for finance review and bank upload staging.
        {/if}
      </p>
    </div>

    <div class="overflow-x-auto rounded-2xl border border-neutral-200">
      <table class="min-w-full text-sm">
        <thead class="bg-neutral-50 text-[10px] uppercase tracking-wider text-neutral-500">
          <tr>
            <th class="px-4 py-3 text-left font-semibold">Beneficiary</th>
            <th class="px-4 py-3 text-left font-semibold">Project</th>
            <th class="px-4 py-3 text-left font-semibold">Bank</th>
            <th class="px-4 py-3 text-right font-semibold">Amount</th>
          </tr>
        </thead>
        <tbody>
          {#each rows.slice(0, 4) as row}
            <tr class="border-t border-neutral-200">
              <td class="px-4 py-3">
                <p class="font-medium text-neutral-900">{row.employeeName}</p>
                <p class="text-xs text-neutral-500">{row.employeeId || "Employee ID pending"}</p>
              </td>
              <td class="px-4 py-3 text-neutral-600">{row.projectName}</td>
              <td class="px-4 py-3 text-neutral-600">{row.bankName || "Awaiting bank profile"}</td>
              <td class="px-4 py-3 text-right font-semibold tabular-nums text-neutral-900">{formatCurrency(row.amount)}</td>
            </tr>
          {/each}
          {#if rows.length === 0}
            <tr>
              <td colspan="4" class="px-4 py-8 text-center text-sm text-neutral-500">
                No payslips are ready for bank export in this period yet.
              </td>
            </tr>
          {/if}
        </tbody>
      </table>
    </div>
  </div>
</section>

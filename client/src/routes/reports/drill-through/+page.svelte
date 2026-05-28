<script lang="ts">
  import { currency } from "$lib/stores/currency.svelte";

  type InvoiceRevenueRow = {
    id: number;
    region: string;
    project: string;
    invoice_number: string;
    customer: string;
    issued_on: string;
    amount: number;
    status: "paid" | "partially_paid" | "overdue";
  };

  type StepKey = "summary" | "region" | "project" | "invoice";

  const drillSteps: { key: StepKey; label: string }[] = [
    { key: "summary", label: "Revenue Summary" },
    { key: "region", label: "Region Revenue" },
    { key: "project", label: "Project Revenue" },
    { key: "invoice", label: "Invoice Details" },
  ];

  const invoiceRows: InvoiceRevenueRow[] = [
    { id: 1201, region: "West", project: "Lagos Waterfront Estate", invoice_number: "INV-2026-001", customer: "Harbor Ridge Ltd", issued_on: "2026-02-12", amount: 18500000, status: "paid" },
    { id: 1202, region: "West", project: "Lagos Waterfront Estate", invoice_number: "INV-2026-014", customer: "Blue Cove Holdings", issued_on: "2026-02-26", amount: 9400000, status: "partially_paid" },
    { id: 1203, region: "West", project: "Ikeja Heights", invoice_number: "INV-2026-022", customer: "Summit Prime Homes", issued_on: "2026-03-01", amount: 12600000, status: "overdue" },
    { id: 1204, region: "North", project: "Abuja Central Residences", invoice_number: "INV-2026-003", customer: "Cedarline Partners", issued_on: "2026-02-09", amount: 15450000, status: "paid" },
    { id: 1205, region: "North", project: "Abuja Central Residences", invoice_number: "INV-2026-017", customer: "Apex Shelter Group", issued_on: "2026-02-28", amount: 7700000, status: "partially_paid" },
    { id: 1206, region: "North", project: "Kubwa Smart District", invoice_number: "INV-2026-024", customer: "Crown Habitat", issued_on: "2026-03-03", amount: 10800000, status: "paid" },
    { id: 1207, region: "South", project: "Port Harcourt Marina", invoice_number: "INV-2026-007", customer: "Nautic Build Co", issued_on: "2026-02-16", amount: 13200000, status: "overdue" },
    { id: 1208, region: "South", project: "Port Harcourt Marina", invoice_number: "INV-2026-020", customer: "Delta Crest Ventures", issued_on: "2026-03-02", amount: 6900000, status: "partially_paid" },
    { id: 1209, region: "South", project: "Uyo Business Park", invoice_number: "INV-2026-025", customer: "Sterling Projects", issued_on: "2026-03-04", amount: 9100000, status: "paid" },
  ];

  let selectedRegion = $state<string | null>(null);
  let selectedProject = $state<string | null>(null);

  const currentStep = $derived.by<StepKey>(() => {
    if (selectedProject) return "invoice";
    if (selectedRegion) return "project";
    return "summary";
  });

  const totalRevenue = $derived.by(() =>
    invoiceRows.reduce((sum, row) => sum + row.amount, 0),
  );

  const regionRevenueRows = $derived.by(() => {
    const grouped = new Map<string, { amount: number; invoiceCount: number }>();

    for (const row of invoiceRows) {
      const bucket = grouped.get(row.region) ?? { amount: 0, invoiceCount: 0 };
      bucket.amount += row.amount;
      bucket.invoiceCount += 1;
      grouped.set(row.region, bucket);
    }

    return [...grouped.entries()]
      .map(([region, aggregate]) => ({
        region,
        amount: aggregate.amount,
        invoiceCount: aggregate.invoiceCount,
      }))
      .sort((left, right) => right.amount - left.amount);
  });

  const regionProjectRows = $derived.by(() => {
    if (!selectedRegion) return [];

    const grouped = new Map<string, { amount: number; invoiceCount: number }>();

    for (const row of invoiceRows) {
      if (row.region !== selectedRegion) continue;

      const bucket = grouped.get(row.project) ?? { amount: 0, invoiceCount: 0 };
      bucket.amount += row.amount;
      bucket.invoiceCount += 1;
      grouped.set(row.project, bucket);
    }

    return [...grouped.entries()]
      .map(([project, aggregate]) => ({
        project,
        amount: aggregate.amount,
        invoiceCount: aggregate.invoiceCount,
      }))
      .sort((left, right) => right.amount - left.amount);
  });

  const projectInvoiceRows = $derived.by(() => {
    if (!selectedRegion || !selectedProject) return [];

    return invoiceRows
      .filter((row) => row.region === selectedRegion && row.project === selectedProject)
      .sort((left, right) => right.issued_on.localeCompare(left.issued_on));
  });

  const projectTotal = $derived.by(() =>
    projectInvoiceRows.reduce((sum, row) => sum + row.amount, 0),
  );

  function openRegion(region: string) {
    selectedRegion = region;
    selectedProject = null;
  }

  function openProject(project: string) {
    selectedProject = project;
  }

  function resetToSummary() {
    selectedRegion = null;
    selectedProject = null;
  }

  function goBackToProjects() {
    selectedProject = null;
  }

  function formatDate(value: string): string {
    return new Date(value).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  const statusClass: Record<InvoiceRevenueRow["status"], string> = {
    paid: "bg-emerald-100 text-emerald-800 border-emerald-200",
    partially_paid: "bg-amber-100 text-amber-800 border-amber-200",
    overdue: "bg-rose-100 text-rose-800 border-rose-200",
  };

  const statusLabel: Record<InvoiceRevenueRow["status"], string> = {
    paid: "Paid",
    partially_paid: "Partially Paid",
    overdue: "Overdue",
  };
</script>

<div class="space-y-6">
  <section class="rounded-xl border border-neutral-200 bg-white p-5">
    <h1 class="text-2xl font-bold text-neutral-900">Report Drill-through Navigation</h1>
    <p class="mt-2 text-sm text-neutral-600">Navigate from aggregate revenue to granular invoice detail with progressive drill-through.</p>

    <div class="mt-4 flex flex-wrap items-center gap-2 text-xs text-neutral-600">
      {#each drillSteps as step, index (step.key)}
        <span class={`rounded-lg border px-2.5 py-1 font-semibold ${step.key === currentStep ? "border-neutral-900 bg-neutral-900 text-white" : "border-neutral-300 bg-white text-neutral-700"}`}>
          {step.label}
        </span>
        {#if index < drillSteps.length - 1}
          <span class="text-neutral-400">-></span>
        {/if}
      {/each}
    </div>
  </section>

  {#if currentStep === "summary"}
    <section class="rounded-xl border border-neutral-200 bg-white p-5 space-y-4">
      <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-4">
        <p class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Revenue Summary</p>
        <p class="mt-2 text-2xl font-bold text-neutral-900 tabular-nums">{currency.format(totalRevenue)}</p>
      </div>

      <div class="overflow-x-auto">
        <table class="min-w-full text-sm">
          <thead class="bg-neutral-50">
            <tr>
              <th class="px-4 py-2 text-left font-medium text-neutral-600">Region</th>
              <th class="px-4 py-2 text-right font-medium text-neutral-600">Revenue</th>
              <th class="px-4 py-2 text-right font-medium text-neutral-600">Invoices</th>
              <th class="px-4 py-2 text-right font-medium text-neutral-600">Action</th>
            </tr>
          </thead>
          <tbody>
            {#each regionRevenueRows as row}
              <tr class="border-t border-neutral-100">
                <td class="px-4 py-2 text-neutral-900 font-medium">{row.region}</td>
                <td class="px-4 py-2 text-right text-neutral-700 tabular-nums">{currency.format(row.amount)}</td>
                <td class="px-4 py-2 text-right text-neutral-700 tabular-nums">{row.invoiceCount}</td>
                <td class="px-4 py-2 text-right">
                  <button
                    type="button"
                    onclick={() => openRegion(row.region)}
                    class="rounded-lg border border-neutral-300 px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-100"
                  >
                    View Region Revenue
                  </button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>
  {/if}

  {#if currentStep === "project" && selectedRegion}
    <section class="rounded-xl border border-neutral-200 bg-white p-5 space-y-4">
      <div class="flex items-center justify-between gap-3">
        <div>
          <p class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Region Revenue</p>
          <h2 class="mt-1 text-lg font-bold text-neutral-900">{selectedRegion}</h2>
        </div>
        <button
          type="button"
          onclick={resetToSummary}
          class="rounded-lg border border-neutral-300 px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-100"
        >
          Back To Revenue Summary
        </button>
      </div>

      <div class="overflow-x-auto">
        <table class="min-w-full text-sm">
          <thead class="bg-neutral-50">
            <tr>
              <th class="px-4 py-2 text-left font-medium text-neutral-600">Project</th>
              <th class="px-4 py-2 text-right font-medium text-neutral-600">Revenue</th>
              <th class="px-4 py-2 text-right font-medium text-neutral-600">Invoices</th>
              <th class="px-4 py-2 text-right font-medium text-neutral-600">Action</th>
            </tr>
          </thead>
          <tbody>
            {#each regionProjectRows as row}
              <tr class="border-t border-neutral-100">
                <td class="px-4 py-2 text-neutral-900 font-medium">{row.project}</td>
                <td class="px-4 py-2 text-right text-neutral-700 tabular-nums">{currency.format(row.amount)}</td>
                <td class="px-4 py-2 text-right text-neutral-700 tabular-nums">{row.invoiceCount}</td>
                <td class="px-4 py-2 text-right">
                  <button
                    type="button"
                    onclick={() => openProject(row.project)}
                    class="rounded-lg border border-neutral-300 px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-100"
                  >
                    View Invoice Details
                  </button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>
  {/if}

  {#if currentStep === "invoice" && selectedRegion && selectedProject}
    <section class="rounded-xl border border-neutral-200 bg-white p-5 space-y-4">
      <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Project Revenue</p>
          <h2 class="mt-1 text-lg font-bold text-neutral-900">{selectedProject}</h2>
          <p class="mt-1 text-xs text-neutral-500">{selectedRegion} region</p>
        </div>

        <div class="flex items-center gap-2">
          <button
            type="button"
            onclick={goBackToProjects}
            class="rounded-lg border border-neutral-300 px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-100"
          >
            Back To Region Revenue
          </button>
          <button
            type="button"
            onclick={resetToSummary}
            class="rounded-lg border border-neutral-300 px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-100"
          >
            Back To Summary
          </button>
        </div>
      </div>

      <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-4">
        <p class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Project Revenue</p>
        <p class="mt-2 text-2xl font-bold text-neutral-900 tabular-nums">{currency.format(projectTotal)}</p>
      </div>

      <div class="overflow-x-auto">
        <table class="min-w-full text-sm">
          <thead class="bg-neutral-50">
            <tr>
              <th class="px-4 py-2 text-left font-medium text-neutral-600">Invoice</th>
              <th class="px-4 py-2 text-left font-medium text-neutral-600">Customer</th>
              <th class="px-4 py-2 text-left font-medium text-neutral-600">Issued</th>
              <th class="px-4 py-2 text-right font-medium text-neutral-600">Amount</th>
              <th class="px-4 py-2 text-right font-medium text-neutral-600">Status</th>
            </tr>
          </thead>
          <tbody>
            {#each projectInvoiceRows as row}
              <tr class="border-t border-neutral-100">
                <td class="px-4 py-2 font-medium text-neutral-900">{row.invoice_number}</td>
                <td class="px-4 py-2 text-neutral-700">{row.customer}</td>
                <td class="px-4 py-2 text-neutral-700">{formatDate(row.issued_on)}</td>
                <td class="px-4 py-2 text-right text-neutral-700 tabular-nums">{currency.format(row.amount)}</td>
                <td class="px-4 py-2 text-right">
                  <span class={`inline-flex rounded-full border px-2.5 py-1 text-[11px] font-semibold ${statusClass[row.status]}`}>
                    {statusLabel[row.status]}
                  </span>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </section>
  {/if}
</div>

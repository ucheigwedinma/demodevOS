<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DateInput from "$lib/components/DateInput.svelte";
  import type { PropertyListItem, PaginatedResponse } from "$lib/types";

  interface AgingItem {
    id: number;
    voucher_number: string;
    vendor_name: string;
    property_name: string | null;
    amount: string;
    issue_date: string;
    days_outstanding: number;
    status: string;
    priority: string;
  }

  interface AgingBucket {
    label: string;
    total: string;
    count: number;
    items: AgingItem[];
  }

  interface AgingReport {
    total_outstanding: string;
    voucher_count: number;
    avg_days_to_pay: number;
    buckets: {
      current: AgingBucket;
      overdue_30: AgingBucket;
      overdue_60: AgingBucket;
      overdue_90: AgingBucket;
    };
  }

  let report = $state<AgingReport | null>(null);
  let loading = $state(true);
  let expandedBucket = $state<string | null>(null);

  // Filters
  let asOfDate = $state("");
  let propertyFilter = $state("");
  let properties = $state<PropertyListItem[]>([]);

  async function fetchProperties() {
    try {
      const res = await api.get<PaginatedResponse<PropertyListItem>>("/properties/", { page_size: "200" });
      properties = res.results;
    } catch { properties = []; }
  }

  async function fetchReport() {
    loading = true;
    try {
      const params: Record<string, string> = {};
      if (asOfDate) params.as_of_date = asOfDate;
      if (propertyFilter) params.property = propertyFilter;
      report = await api.get<AgingReport>("/finance/aging-report/", params);
    } catch {
      report = null;
      toast.error("Error", "Could not load aging report");
    }
    loading = false;
  }

  $effect(() => { fetchProperties(); });
  $effect(() => { void asOfDate; void propertyFilter; fetchReport(); });

  // Actions
  let disputing = $state<number | null>(null);
  let addingToRun = $state<number | null>(null);

  async function markDisputed(voucherId: number) {
    disputing = voucherId;
    try {
      await api.post(`/finance/payment-vouchers/${voucherId}/dispute/`, { reason: "Flagged from aging report review" });
      toast.success("Disputed", "Voucher marked as disputed");
      fetchReport();
    } catch { toast.error("Error", "Could not mark as disputed"); }
    disputing = null;
  }

  async function addToPaymentRun(voucherId: number) {
    addingToRun = voucherId;
    try {
      // Find or create the latest draft payment run
      const runsRes = await api.get<{ results: { id: number; batch_id: string; status: string }[] }>("/finance/payment-runs/", { status: "draft", page_size: "1" });
      let runId: number;

      if (runsRes.results.length > 0) {
        runId = runsRes.results[0].id;
      } else {
        const newRun = await api.post<{ id: number }>("/finance/payment-runs/", { voucher_ids: [voucherId] });
        runId = newRun.id;
        toast.success("Run created", "New payment run created with this voucher");
        addingToRun = null;
        return;
      }

      // Add to existing run — get current vouchers, append, PATCH
      const run = await api.get<{ voucher_items: { id: number }[] }>(`/finance/payment-runs/${runId}/`);
      const existingIds = run.voucher_items.map((v: { id: number }) => v.id);
      if (existingIds.includes(voucherId)) {
        toast.info("Already added", "This voucher is already in the next payment run");
        addingToRun = null;
        return;
      }
      await api.patch(`/finance/payment-runs/${runId}/`, { voucher_ids: [...existingIds, voucherId] });
      toast.success("Added", "Voucher added to next payment run");
    } catch { toast.error("Error", "Could not add to payment run"); }
    addingToRun = null;
  }

  function formatDate(v: string): string {
    return new Date(v).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  }

  function toggleBucket(key: string) {
    expandedBucket = expandedBucket === key ? null : key;
  }

  // Vendor-centric aging grid
  interface VendorAging {
    vendor_name: string;
    total: number;
    current: number;
    overdue_30: number;
    overdue_60: number;
    overdue_90: number;
    items: AgingItem[];
  }

  let expandedVendor = $state<string | null>(null);

  const vendorGrid = $derived(() => {
    if (!report) return [];
    const map = new Map<string, VendorAging>();

    for (const [bucketKey, bucket] of Object.entries(report.buckets)) {
      for (const item of bucket.items) {
        const name = item.vendor_name || "Unknown";
        if (!map.has(name)) {
          map.set(name, { vendor_name: name, total: 0, current: 0, overdue_30: 0, overdue_60: 0, overdue_90: 0, items: [] });
        }
        const v = map.get(name)!;
        const amt = Number(item.amount);
        v.total += amt;
        if (bucketKey === "current") v.current += amt;
        else if (bucketKey === "overdue_30") v.overdue_30 += amt;
        else if (bucketKey === "overdue_60") v.overdue_60 += amt;
        else if (bucketKey === "overdue_90") v.overdue_90 += amt;
        v.items.push(item);
      }
    }

    return [...map.values()].sort((a, b) => b.total - a.total);
  });

  function exportAging(format: "csv" | "pdf") {
    if (!report) return;

    if (format === "pdf") {
      toast.info("Coming soon", "PDF export with brand styling will be available shortly");
      return;
    }

    const headers = ["Voucher", "Vendor", "Project", "Issue Date", "Days Outstanding", "Aging Bucket", "Status", "Priority", "Amount"];
    const rows: string[][] = [];

    for (const [, bucket] of Object.entries(report.buckets)) {
      for (const item of bucket.items) {
        rows.push([
          item.voucher_number, item.vendor_name, item.property_name || "",
          item.issue_date, String(item.days_outstanding), bucket.label,
          item.status, item.priority, item.amount,
        ]);
      }
    }

    rows.sort((a, b) => Number(b[4]) - Number(a[4]));

    const csv = [headers, ...rows].map(r => r.map(c => `"${c}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `aging-report-${asOfDate || new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
    toast.success("Exported", "Aging report CSV downloaded");
  }

  const bucketStyles: Record<string, { bg: string; border: string; text: string; label: string }> = {
    current: { bg: "#ecfdf5", border: "#a7f3d0", text: "#047857", label: "#34d399" },
    overdue_30: { bg: "#fff7ed", border: "#fed7aa", text: "#c2410c", label: "#fb923c" },
    overdue_60: { bg: "#fef2f2", border: "#fecaca", text: "#b91c1c", label: "#f87171" },
    overdue_90: { bg: "#fdf2f8", border: "#fbcfe8", text: "#9d174d", label: "#ec4899" },
  };
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-green-600">Accounts Payable</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Aging Report</h1>
      <p class="text-sm text-neutral-400 mt-1">Accounts payable aging analysis, unpaid vouchers by days outstanding</p>
    </div>
    <div class="flex items-center gap-2">
      <button type="button" onclick={() => { exportAging("csv"); }} class="inline-flex items-center gap-1.5 px-3 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" /></svg>
        Excel
      </button>
      <button type="button" onclick={() => { exportAging("pdf"); }} class="inline-flex items-center gap-1.5 px-3 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" /></svg>
        PDF
      </button>
    </div>
  </div>

  <!-- Filters -->
  <div class="flex items-center gap-3 flex-wrap">
    <label class="flex items-center gap-1.5">
      <span class="text-xs text-neutral-500">As of</span>
      <DateInput bind:value={asOfDate} />
    </label>
    <select bind:value={propertyFilter} class="px-3 py-2 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent">
      <option value="">All Projects</option>
      {#each properties as prop}
        <option value={String(prop.id)}>{prop.name}</option>
      {/each}
    </select>
    {#if asOfDate || propertyFilter}
      <button type="button" onclick={() => { asOfDate = ""; propertyFilter = ""; }} class="text-xs text-neutral-500 hover:text-neutral-800 font-medium transition-colors">Clear filters</button>
    {/if}
  </div>

  {#if loading}
    <div class="p-16 text-center"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div></div>
  {:else if report}
    <!-- Aging Summary Dashboard -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <!-- Total Outstanding -->
      <div class="rounded-xl border shadow-lg p-5" style="background: rgba(253,242,248,0.7); border-color: #fbcfe8; backdrop-filter: blur(8px);">
        <p class="text-xs font-medium uppercase tracking-wider mb-1" style="color: #ec4899;">Total Outstanding</p>
        <p class="text-xl font-bold text-neutral-800 tabular-nums" style="font-family: 'Raleway', sans-serif;">{currency.format(report.total_outstanding)}</p>
        <p class="text-xs mt-1" style="color: #f472b6;">{report.voucher_count} unpaid voucher{report.voucher_count !== 1 ? "s" : ""}</p>
      </div>

      <!-- Current (0-30 Days) -->
      <div class="rounded-xl border shadow-lg p-5" style="background: rgba(253,242,248,0.5); border-color: #fce7f3; backdrop-filter: blur(8px);">
        <p class="text-xs font-medium uppercase tracking-wider mb-1" style="color: #34d399;">Current (0–30 Days)</p>
        <p class="text-xl font-bold tabular-nums" style="font-family: 'Raleway', sans-serif; color: {bucketStyles.current.text};">{currency.format(report.buckets.current.total)}</p>
        <p class="text-xs font-light mt-1" style="color: #a3a3a3;">{report.buckets.current.count} voucher{report.buckets.current.count !== 1 ? "s" : ""}</p>
      </div>

      <!-- Overdue (31-60) -->
      <div class="rounded-xl border shadow-lg p-5" style="background: rgba(253,242,248,0.5); border-color: #fce7f3; backdrop-filter: blur(8px);">
        <p class="text-xs font-medium uppercase tracking-wider mb-1" style="color: {bucketStyles.overdue_30.label};">Overdue (31–60 Days)</p>
        <p class="text-xl font-bold tabular-nums" style="font-family: 'Raleway', sans-serif; color: {bucketStyles.overdue_30.text};">{currency.format(report.buckets.overdue_30.total)}</p>
        <p class="text-xs font-light mt-1" style="color: #a3a3a3;">{report.buckets.overdue_30.count} voucher{report.buckets.overdue_30.count !== 1 ? "s" : ""}</p>
      </div>

      <!-- Critical (61+ Days) — PINK -->
      <div class="rounded-xl border shadow-lg p-5" style="background: rgba(253,242,248,0.8); border-color: #f9a8d4; backdrop-filter: blur(8px);">
        <p class="text-xs font-medium uppercase tracking-wider mb-1" style="color: #ec4899;">Critical (61+ Days)</p>
        <p class="text-xl font-bold tabular-nums" style="font-family: 'Raleway', sans-serif; color: #9d174d;">
          {currency.format(String((Number(report.buckets.overdue_60.total) + Number(report.buckets.overdue_90.total)).toFixed(2)))}
        </p>
        <p class="text-xs font-light mt-1" style="color: #f472b6;">{report.buckets.overdue_60.count + report.buckets.overdue_90.count} voucher{report.buckets.overdue_60.count + report.buckets.overdue_90.count !== 1 ? "s" : ""}</p>
      </div>
    </div>

    <!-- Avg Days to Pay -->
    <div class="flex items-center gap-6">
      <div class="rounded-lg bg-white border border-neutral-200 px-4 py-3 inline-flex items-center gap-3">
        <svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>
        <div>
          <p class="text-xs text-neutral-400">Average Days to Pay</p>
          <p class="text-lg font-bold text-neutral-800">{report.avg_days_to_pay} <span class="text-sm font-normal text-neutral-400">days</span></p>
        </div>
      </div>
    </div>

    <!-- Vendor Aging Grid -->
    {#if vendorGrid().length > 0}
      <div>
        <h2 class="text-sm font-semibold text-neutral-800 mb-3">Aging by Vendor</h2>
        <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-200 bg-neutral-50">
                <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Vendor Name</th>
                <th class="px-5 py-3 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Total Due</th>
                <th class="px-5 py-3 text-right font-medium text-xs uppercase tracking-wider" style="color: #34d399;">Current</th>
                <th class="px-5 py-3 text-right font-medium text-xs uppercase tracking-wider" style="color: #fb923c;">31–60 Days</th>
                <th class="px-5 py-3 text-right font-medium text-xs uppercase tracking-wider" style="color: #f87171;">61–90 Days</th>
                <th class="px-5 py-3 text-right font-medium text-xs uppercase tracking-wider" style="color: #ec4899;">90+ Days</th>
              </tr>
            </thead>
            <tbody>
              {#each vendorGrid() as vendor}
                <tr
                  class="border-b border-neutral-100 hover:bg-neutral-50 cursor-pointer transition-colors"
                  onclick={() => (expandedVendor = expandedVendor === vendor.vendor_name ? null : vendor.vendor_name)}
                  onkeydown={(e) => e.key === "Enter" && (expandedVendor = expandedVendor === vendor.vendor_name ? null : vendor.vendor_name)}
                  tabindex="0"
                  role="button"
                >
                  <td class="px-5 py-3.5">
                    <div class="flex items-center gap-2">
                      <svg class="w-3.5 h-3.5 text-neutral-400 transition-transform" style="transform: {expandedVendor === vendor.vendor_name ? 'rotate(90deg)' : 'rotate(0)'};" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" /></svg>
                      <span class="font-medium text-neutral-800">{vendor.vendor_name}</span>
                    </div>
                  </td>
                  <td class="px-5 py-3.5 text-right font-bold text-neutral-800 tabular-nums">{currency.format(String(vendor.total.toFixed(2)))}</td>
                  <td class="px-5 py-3.5 text-right tabular-nums" style="color: {vendor.current > 0 ? '#047857' : '#d4d4d4'};">{vendor.current > 0 ? currency.format(String(vendor.current.toFixed(2))) : "\u2014"}</td>
                  <td class="px-5 py-3.5 text-right tabular-nums" style="color: {vendor.overdue_30 > 0 ? '#c2410c' : '#d4d4d4'};">{vendor.overdue_30 > 0 ? currency.format(String(vendor.overdue_30.toFixed(2))) : "\u2014"}</td>
                  <td class="px-5 py-3.5 text-right tabular-nums" style="color: {vendor.overdue_60 > 0 ? '#b91c1c' : '#d4d4d4'};">{vendor.overdue_60 > 0 ? currency.format(String(vendor.overdue_60.toFixed(2))) : "\u2014"}</td>
                  <td class="px-5 py-3.5 text-right tabular-nums font-semibold" style="color: {vendor.overdue_90 > 0 ? '#9d174d' : '#d4d4d4'}; background: {vendor.overdue_90 > 0 ? 'rgba(253,242,248,0.5)' : 'transparent'};">{vendor.overdue_90 > 0 ? currency.format(String(vendor.overdue_90.toFixed(2))) : "\u2014"}</td>
                </tr>

                <!-- Drill-down: individual vouchers for this vendor -->
                {#if expandedVendor === vendor.vendor_name}
                  <tr>
                    <td colspan="7" class="p-0">
                      <div class="bg-neutral-50 border-t border-neutral-200">
                        <table class="w-full text-xs">
                          <thead>
                            <tr class="border-b border-neutral-200">
                              <th class="px-5 py-2 text-left font-medium text-neutral-400 uppercase tracking-wider">Voucher</th>
                              <th class="px-5 py-2 text-left font-medium text-neutral-400 uppercase tracking-wider">Project</th>
                              <th class="px-5 py-2 text-left font-medium text-neutral-400 uppercase tracking-wider">Issue Date</th>
                              <th class="px-5 py-2 text-center font-medium text-neutral-400 uppercase tracking-wider">Days</th>
                              <th class="px-5 py-2 text-left font-medium text-neutral-400 uppercase tracking-wider">Priority</th>
                              <th class="px-5 py-2 text-left font-medium text-neutral-400 uppercase tracking-wider">Status</th>
                              <th class="px-5 py-2 text-right font-medium text-neutral-400 uppercase tracking-wider">Amount</th>
                              <th class="px-5 py-2 text-right font-medium text-neutral-400 uppercase tracking-wider">Actions</th>
                            </tr>
                          </thead>
                          <tbody class="divide-y divide-neutral-100 bg-white">
                            {#each vendor.items.sort((a, b) => b.days_outstanding - a.days_outstanding) as item}
                              <tr class="hover:bg-neutral-50 transition-colors">
                                <td class="px-5 py-2.5 font-medium text-neutral-800 font-mono">{item.voucher_number}</td>
                                <td class="px-5 py-2.5 text-neutral-500 font-light">{item.property_name || "\u2014"}</td>
                                <td class="px-5 py-2.5 text-neutral-500 font-light">{formatDate(item.issue_date)}</td>
                                <td class="px-5 py-2.5 text-center">
                                  <span class="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold tabular-nums" style="background: {item.days_outstanding <= 30 ? '#ecfdf5' : item.days_outstanding <= 60 ? '#fff7ed' : '#fef2f2'}; color: {item.days_outstanding <= 30 ? '#047857' : item.days_outstanding <= 60 ? '#c2410c' : '#991b1b'};">
                                    {item.days_outstanding}d
                                  </span>
                                </td>
                                <td class="px-5 py-2.5">
                                  {#if item.priority === "high"}
                                    <span class="inline-flex items-center gap-1 text-[10px] font-medium text-red-600"><span class="w-1.5 h-1.5 rounded-full bg-red-500"></span>High</span>
                                  {:else}
                                    <span class="text-[10px] text-neutral-400">Standard</span>
                                  {/if}
                                </td>
                                <td class="px-5 py-2.5"><StatusBadge status={item.status} /></td>
                                <td class="px-5 py-2.5 text-right tabular-nums font-semibold text-neutral-800">{currency.format(item.amount)}</td>
                                <td class="px-5 py-2.5 text-right">
                                  {#if item.status !== "disputed" && item.status !== "paid"}
                                    <div class="flex items-center justify-end gap-2">
                                      <button
                                        type="button"
                                        onclick={() => addToPaymentRun(item.id)}
                                        disabled={addingToRun === item.id}
                                        class="text-[10px] font-medium text-neutral-800 hover:text-emerald-700 transition-colors disabled:opacity-50"
                                      >
                                        {addingToRun === item.id ? "..." : "+ Pay Run"}
                                      </button>
                                      <button
                                        type="button"
                                        onclick={() => markDisputed(item.id)}
                                        disabled={disputing === item.id}
                                        class="text-[10px] font-medium text-red-500 hover:text-red-700 transition-colors disabled:opacity-50"
                                      >
                                        {disputing === item.id ? "..." : "Dispute"}
                                      </button>
                                    </div>
                                  {:else if item.status === "disputed"}
                                    <span class="text-[10px] text-red-400 font-medium">Disputed</span>
                                  {/if}
                                </td>
                              </tr>
                            {/each}
                          </tbody>
                        </table>
                      </div>
                    </td>
                  </tr>
                {/if}
              {/each}
            </tbody>
          </table>
        </div>
      </div>
    {/if}

    <!-- Bucket Detail Tables -->
    {#each Object.entries(report.buckets) as [key, bucket]}
      {#if bucket.count > 0}
        <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
          <button type="button" onclick={() => toggleBucket(key)} class="w-full px-5 py-4 flex items-center justify-between hover:bg-neutral-50 transition-colors">
            <div class="flex items-center gap-3">
              <span class="w-3 h-3 rounded-full" style="background: {bucketStyles[key]?.text ?? '#525252'};"></span>
              <span class="text-sm font-semibold text-neutral-800">{bucket.label}</span>
              <span class="text-xs text-neutral-400">{bucket.count} voucher{bucket.count !== 1 ? "s" : ""}</span>
            </div>
            <div class="flex items-center gap-3">
              <span class="text-sm font-bold tabular-nums" style="color: {bucketStyles[key]?.text ?? '#171717'};">{currency.format(bucket.total)}</span>
              <svg class="w-4 h-4 text-neutral-400 transition-transform" style="transform: {expandedBucket === key ? 'rotate(180deg)' : 'rotate(0)'};" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" /></svg>
            </div>
          </button>

          {#if expandedBucket === key}
            <table class="w-full text-sm border-t border-neutral-200">
              <thead>
                <tr class="bg-neutral-50">
                  <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Voucher</th>
                  <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Vendor</th>
                  <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Project</th>
                  <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Issue Date</th>
                  <th class="px-5 py-3 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Days</th>
                  <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
                  <th class="px-5 py-3 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Amount</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100">
                {#each bucket.items as item}
                  <tr class="hover:bg-neutral-50 transition-colors">
                    <td class="px-5 py-3 font-medium text-neutral-800 font-mono text-xs">{item.voucher_number}</td>
                    <td class="px-5 py-3 text-neutral-700">{item.vendor_name}</td>
                    <td class="px-5 py-3 text-neutral-500 text-xs">{item.property_name || "\u2014"}</td>
                    <td class="px-5 py-3 text-neutral-500 text-xs">{formatDate(item.issue_date)}</td>
                    <td class="px-5 py-3 text-center">
                      <span class="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold tabular-nums" style="background: {bucketStyles[key]?.bg ?? '#f5f5f5'}; color: {bucketStyles[key]?.text ?? '#525252'};">
                        {item.days_outstanding}d
                      </span>
                    </td>
                    <td class="px-5 py-3"><StatusBadge status={item.status} /></td>
                    <td class="px-5 py-3 text-right tabular-nums font-semibold text-neutral-800">{currency.format(item.amount)}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          {/if}
        </div>
      {/if}
    {/each}

    <!-- Empty state -->
    {#if report.voucher_count === 0}
      <div class="bg-white rounded-xl border border-neutral-200 p-16 text-center">
        <div class="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-emerald-100">
          <svg class="w-7 h-7 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" /></svg>
        </div>
        <p class="text-sm font-medium text-neutral-800">All caught up</p>
        <p class="text-sm text-neutral-400 mt-1">No outstanding payment vouchers.</p>
      </div>
    {/if}
  {/if}
</div>

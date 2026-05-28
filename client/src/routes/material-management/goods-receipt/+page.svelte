<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import { onMount } from "svelte";

  interface Summary { in_transit_today: number; pending_inspection: number; inspected: number; accepted: number; rejected: number; }
  interface Delivery { id: number; po_number: string; vendor_name: string; project_name: string; expected_delivery_date: string; total_amount: string; days_until: number; is_overdue: boolean; }
  interface GRN { id: number; grn_number: string; status: string; received_date: string; received_by: string; delivery_note_number: string; po_number: string; vendor_name: string; project_name: string; po_amount: string; }
  interface RejectedGRN { id: number; grn_number: string; received_date: string; inspection_notes: string; po_number: string; vendor_name: string; project_name: string; }
  interface DashboardData { summary: Summary; expected_deliveries: Delivery[]; recent_grns: GRN[]; rejected_grns: RejectedGRN[]; }

  const STATUS_COLORS: Record<string, string> = {
    pending: "bg-amber-100 text-amber-700", inspected: "bg-blue-100 text-blue-700",
    accepted: "bg-emerald-100 text-emerald-700", partially_accepted: "bg-yellow-100 text-yellow-700",
    rejected: "bg-red-100 text-red-700",
  };

  let loading = $state(true);
  let data = $state<DashboardData | null>(null);
  let search = $state("");
  let activeTab = $state<"deliveries" | "received" | "rejected">("deliveries");

  const filteredDeliveries = $derived.by(() => {
    if (!data) return [];
    if (!search.trim()) return data.expected_deliveries;
    const q = search.trim().toLowerCase();
    return data.expected_deliveries.filter(d =>
      d.po_number.toLowerCase().includes(q) || d.vendor_name.toLowerCase().includes(q) || d.project_name.toLowerCase().includes(q)
    );
  });

  const filteredGRNs = $derived.by(() => {
    if (!data) return [];
    if (!search.trim()) return data.recent_grns;
    const q = search.trim().toLowerCase();
    return data.recent_grns.filter(g =>
      g.grn_number.toLowerCase().includes(q) || g.po_number.toLowerCase().includes(q) || g.vendor_name.toLowerCase().includes(q)
    );
  });

  // Log Arrival form
  interface POItem { po_item_id: number; description: string; ordered_quantity: string; unit_of_measure: string; unit_price: string; already_received: string; remaining: string; fully_received: boolean; }
  interface POLookup { po_id: number; po_number: string; vendor_id: number; vendor_name: string; project_name: string; status: string; expected_delivery_date: string | null; total_amount: string; items: POItem[]; all_received: boolean; }
  interface ArrivalLine { po_item_id: number; description: string; ordered: string; remaining: string; unit: string; quantity_received: string; batch_number: string; expiry_date: string; storage_location: string; notes: string; }

  let showLogArrival = $state(false);
  let poSearchQuery = $state("");
  let poLookupLoading = $state(false);
  let poData = $state<POLookup | null>(null);
  let arrivalLines = $state<ArrivalLine[]>([]);
  let arrivalNotes = $state("");
  let deliveryNoteNumber = $state("");
  let arrivalSaving = $state(false);

  async function lookupPO() {
    if (!poSearchQuery.trim()) return;
    poLookupLoading = true;
    poData = null;
    arrivalLines = [];
    try {
      const res = await api.get<POLookup>("/procurement-integration/po-lookup/", { po_number: poSearchQuery.trim() });
      poData = res;
      arrivalLines = res.items.filter(i => !i.fully_received).map(i => ({
        po_item_id: i.po_item_id,
        description: i.description,
        ordered: i.ordered_quantity,
        remaining: i.remaining,
        unit: i.unit_of_measure,
        quantity_received: i.remaining, // Default to remaining
        batch_number: "",
        expiry_date: "",
        storage_location: "",
        notes: "",
      }));
      if (res.all_received) {
        toast.error("Fully received", "All items on this PO have already been received.");
      }
    } catch {
      toast.error("Not found", "PO number not found. Check and try again.");
    } finally { poLookupLoading = false; }
  }

  async function submitArrival() {
    if (!poData || arrivalLines.length === 0) return;
    const validLines = arrivalLines.filter(l => Number(l.quantity_received) > 0);
    if (validLines.length === 0) { toast.error("No items", "Enter received quantities."); return; }

    arrivalSaving = true;
    try {
      const res = await api.post<{ grn_number: string; items_received: number; detail: string }>(
        "/procurement-integration/log-arrival/",
        {
          po_id: poData.po_id,
          delivery_note_number: deliveryNoteNumber,
          notes: arrivalNotes,
          items: validLines.map(l => ({
            po_item_id: l.po_item_id,
            quantity_received: Number(l.quantity_received),
            batch_number: l.batch_number,
            expiry_date: l.expiry_date || null,
            storage_location: l.storage_location,
            notes: l.notes,
          })),
        },
      );
      toast.success("Arrival Logged", `${res.grn_number} — ${res.items_received} item(s) received.`);
      showLogArrival = false;
      poData = null;
      arrivalLines = [];
      poSearchQuery = "";
      deliveryNoteNumber = "";
      arrivalNotes = "";
      await loadData();
    } catch {
      toast.error("Failed", "Could not log arrival.");
    } finally { arrivalSaving = false; }
  }

  // Quality Inspection
  interface QIItem { id: number; description: string; ordered_quantity: string; unit_of_measure: string; quantity_received: string; quantity_accepted: string; quantity_rejected: string; quality_status: string; inspected_by: string; inspected_date: string | null; quality_notes: string; rejection_reason: string; batch_number: string; expiry_date: string | null; storage_location: string; }
  interface QIData { grn_id: number; grn_number: string; status: string; received_date: string; received_by: string; po_number: string; vendor_name: string; project_name: string; inspection_notes: string; items: QIItem[]; }

  let showQI = $state(false);
  let qiLoading = $state(false);
  let qiData = $state<QIData | null>(null);
  let qiSaving = $state(false);
  let qiNotes = $state("");
  let qiItems = $state<{ id: number; quality_status: string; quantity_accepted: string; quantity_rejected: string; quality_notes: string; rejection_reason: string }[]>([]);

  async function openQI(grnId: number) {
    showQI = true;
    qiLoading = true;
    try {
      const res = await api.get<QIData>("/procurement-integration/inspect/", { grn_id: String(grnId) });
      qiData = res;
      qiNotes = res.inspection_notes || "";
      qiItems = res.items.map(i => ({
        id: i.id,
        quality_status: i.quality_status,
        quantity_accepted: i.quantity_accepted,
        quantity_rejected: i.quantity_rejected,
        quality_notes: i.quality_notes,
        rejection_reason: i.rejection_reason,
      }));
    } catch { toast.error("Load failed", "Could not load GRN for inspection."); }
    finally { qiLoading = false; }
  }

  async function submitInspection() {
    if (!qiData) return;
    // Validate: if any item has qty_rejected > 0 or status=failed, require notes
    for (const item of qiItems) {
      if ((item.quality_status === "failed" || Number(item.quantity_rejected) > 0) && !item.rejection_reason.trim()) {
        toast.error("Required", "Rejection reason is mandatory for failed/rejected items.");
        return;
      }
    }
    qiSaving = true;
    try {
      await api.post("/procurement-integration/inspect/", {
        grn_id: qiData.grn_id,
        inspection_notes: qiNotes,
        items: qiItems.map(i => ({
          id: i.id,
          quality_status: i.quality_status,
          quantity_accepted: Number(i.quantity_accepted),
          quantity_rejected: Number(i.quantity_rejected),
          quality_notes: i.quality_notes,
          rejection_reason: i.rejection_reason,
        })),
      });
      toast.success("Inspection Saved", "Quality inspection results recorded.");
      const savedGrnId = qiData.grn_id;
      showQI = false;
      await loadData();
      // Auto-open GRN document after inspection
      openGRNDoc(savedGrnId);
    } catch { toast.error("Failed", "Could not save inspection."); }
    finally { qiSaving = false; }
  }

  function setItemStatus(idx: number, status: string) {
    qiItems[idx].quality_status = status;
    if (status === "passed") {
      qiItems[idx].quantity_rejected = "0";
      qiItems[idx].rejection_reason = "";
      if (qiData) qiItems[idx].quantity_accepted = qiData.items[idx].quantity_received;
    } else if (status === "failed") {
      qiItems[idx].quantity_accepted = "0";
      if (qiData) qiItems[idx].quantity_rejected = qiData.items[idx].quantity_received;
    }
  }

  // GRN Document Preview
  interface GRNDocItem { description: string; unit: string; ordered_qty: string; received_qty: string; accepted_qty: string; rejected_qty: string; unit_price: string; line_value: string; quality_status: string; batch_number: string; expiry_date: string; storage_location: string; rejection_reason: string; }
  interface GRNDoc { grn_number: string; status: string; status_display: string; received_date: string; received_by: string; delivery_note_number: string; inspection_notes: string; po_number: string; po_date: string; vendor_name: string; vendor_address: string; project_name: string; delivery_address: string; org_name: string; items: GRNDocItem[]; total_value: string; item_count: number; }

  let showGRNDoc = $state(false);
  let grnDocLoading = $state(false);
  let grnDoc = $state<GRNDoc | null>(null);

  async function openGRNDoc(grnId: number) {
    showGRNDoc = true;
    grnDocLoading = true;
    try {
      grnDoc = await api.get<GRNDoc>("/procurement-integration/grn-document/", { grn_id: String(grnId) });
    } catch { toast.error("Load failed", "Could not load GRN document."); }
    finally { grnDocLoading = false; }
  }

  function printGRN() {
    const printArea = document.getElementById("grn-print-area");
    if (!printArea) return;
    const w = window.open("", "_blank", "width=800,height=600");
    if (!w) return;
    w.document.write(`<html><head><title>GRN — ${grnDoc?.grn_number}</title><style>
      body { font-family: 'Raleway', Arial, sans-serif; padding: 24px; color: #1a1a1a; font-size: 12px; }
      table { width: 100%; border-collapse: collapse; margin: 16px 0; }
      th, td { border: 1px solid #d4d4d4; padding: 6px 10px; text-align: left; }
      th { background: #f5f5f5; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px; }
      .header { display: flex; justify-content: space-between; margin-bottom: 20px; }
      .title { font-size: 18px; font-weight: 700; }
      .label { font-size: 9px; text-transform: uppercase; color: #737373; font-weight: 600; letter-spacing: 0.5px; }
      .value { font-size: 12px; font-weight: 600; margin-top: 2px; }
      .info-grid { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 12px; margin: 16px 0; }
      .total { text-align: right; font-size: 14px; font-weight: 700; margin-top: 12px; }
      .signature { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 40px; margin-top: 40px; }
      .sig-line { border-top: 1px solid #a3a3a3; padding-top: 4px; font-size: 10px; color: #737373; }
      .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 600; }
      .passed { background: #d1fae5; color: #065f46; }
      .failed { background: #fee2e2; color: #991b1b; }
      @media print { body { padding: 0; } }
    </style></head><body>${printArea.innerHTML}</body></html>`);
    w.document.close();
    w.print();
  }

  async function loadData() {
    loading = true;
    try {
      data = await api.get<DashboardData>("/procurement-integration/goods-receipt-dashboard/");
    } catch { toast.error("Load failed", "Could not load goods receipt dashboard."); }
    finally { loading = false; }
  }

  onMount(() => { loadData(); });
</script>

<svelte:head><title>Goods Receipt | developerOS</title></svelte:head>

<div class="space-y-4">
  <!-- Header (compact for mobile) -->
  <div class="flex items-start justify-between gap-3">
    <div>
      <p class="text-[10px] font-semibold uppercase tracking-[0.3em] text-emerald-700">Material Management</p>
      <h1 class="mt-1 text-xl font-bold text-neutral-800">Goods Receipt</h1>
      <p class="text-xs text-neutral-500">Incoming shipments, inspections, and material acceptance.</p>
    </div>
    <button onclick={() => { showLogArrival = true; }} class="rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 shadow-sm whitespace-nowrap">
      Log Arrival
    </button>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-20">
      <div class="h-6 w-6 rounded-full border-2 border-neutral-200 border-t-neutral-900 animate-spin"></div>
    </div>
  {:else if data}

    <!-- Summary Cards (mobile: 2-col grid, stacked) -->
    <div class="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
      <div class="rounded-xl border {data.summary.in_transit_today > 0 ? 'border-indigo-200 bg-indigo-50' : 'border-neutral-200 bg-white'} p-3 text-center">
        <p class="text-[8px] font-bold {data.summary.in_transit_today > 0 ? 'text-indigo-400' : 'text-neutral-400'} uppercase tracking-wider">In Transit</p>
        <p class="mt-0.5 text-2xl font-bold {data.summary.in_transit_today > 0 ? 'text-indigo-700' : 'text-neutral-900'} tabular-nums">{data.summary.in_transit_today}</p>
        <p class="text-[8px] text-neutral-400">due today+</p>
      </div>
      <div class="rounded-xl border {data.summary.pending_inspection > 0 ? 'border-amber-200 bg-amber-50' : 'border-neutral-200 bg-white'} p-3 text-center">
        <p class="text-[8px] font-bold {data.summary.pending_inspection > 0 ? 'text-amber-400' : 'text-neutral-400'} uppercase tracking-wider">Pending QC</p>
        <p class="mt-0.5 text-2xl font-bold {data.summary.pending_inspection > 0 ? 'text-amber-700' : 'text-neutral-900'} tabular-nums">{data.summary.pending_inspection}</p>
      </div>
      <div class="rounded-xl border border-blue-200 bg-blue-50 p-3 text-center">
        <p class="text-[8px] font-bold text-blue-400 uppercase tracking-wider">Inspected</p>
        <p class="mt-0.5 text-2xl font-bold text-blue-700 tabular-nums">{data.summary.inspected}</p>
      </div>
      <div class="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-center">
        <p class="text-[8px] font-bold text-emerald-400 uppercase tracking-wider">Accepted</p>
        <p class="mt-0.5 text-2xl font-bold text-emerald-700 tabular-nums">{data.summary.accepted}</p>
      </div>
      <div class="rounded-xl border {data.summary.rejected > 0 ? 'border-red-200 bg-red-50' : 'border-neutral-200 bg-white'} col-span-2 sm:col-span-1 p-3 text-center">
        <p class="text-[8px] font-bold {data.summary.rejected > 0 ? 'text-red-400' : 'text-neutral-400'} uppercase tracking-wider">Rejected</p>
        <p class="mt-0.5 text-2xl font-bold {data.summary.rejected > 0 ? 'text-red-700' : 'text-neutral-900'} tabular-nums">{data.summary.rejected}</p>
      </div>
    </div>

    <!-- Quick Scan Search (large touch target for mobile) -->
    <div class="relative">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
      <input type="text" bind:value={search} placeholder="Quick scan: PO number, vendor, or project..."
        class="w-full rounded-xl border border-neutral-200 bg-white py-3 pl-10 pr-4 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
    </div>

    <!-- Tab Switcher (mobile: full width pills) -->
    <div class="flex gap-1 rounded-lg bg-neutral-100 p-1">
      <button onclick={() => { activeTab = "deliveries"; }} class="flex-1 rounded-md py-2 text-xs font-medium transition-colors {activeTab === 'deliveries' ? 'bg-white text-neutral-900 shadow-sm' : 'text-neutral-500'}">
        Expected ({data.expected_deliveries.length})
      </button>
      <button onclick={() => { activeTab = "received"; }} class="flex-1 rounded-md py-2 text-xs font-medium transition-colors {activeTab === 'received' ? 'bg-white text-neutral-900 shadow-sm' : 'text-neutral-500'}">
        Received ({data.recent_grns.length})
      </button>
      <button onclick={() => { activeTab = "rejected"; }} class="flex-1 rounded-md py-2 text-xs font-medium transition-colors {activeTab === 'rejected' ? 'bg-white text-neutral-900 shadow-sm' : 'text-neutral-500'}">
        Rejected ({data.rejected_grns.length})
      </button>
    </div>

    <!-- Expected Deliveries (mobile card layout) -->
    {#if activeTab === "deliveries"}
      {#if filteredDeliveries.length === 0}
        <div class="rounded-xl border border-neutral-200 bg-white p-6 text-center">
          <p class="text-sm text-neutral-500">No expected deliveries.</p>
        </div>
      {:else}
        <!-- Mobile: cards, Desktop: table -->
        <div class="space-y-2 lg:hidden">
          {#each filteredDeliveries as d}
            <div class="rounded-xl border {d.is_overdue ? 'border-red-200 bg-red-50/50' : d.days_until <= 2 ? 'border-amber-200 bg-amber-50/50' : 'border-neutral-200 bg-white'} p-4">
              <div class="flex items-start justify-between">
                <div>
                  <p class="text-sm font-bold text-neutral-900">{d.po_number}</p>
                  <p class="text-xs text-neutral-600 mt-0.5">{d.vendor_name}</p>
                </div>
                {#if d.is_overdue}
                  <span class="rounded-full bg-red-100 text-red-700 px-2 py-0.5 text-[10px] font-bold">{Math.abs(d.days_until)}d overdue</span>
                {:else if d.days_until === 0}
                  <span class="rounded-full bg-emerald-100 text-emerald-700 px-2 py-0.5 text-[10px] font-bold">Today</span>
                {:else}
                  <span class="rounded-full bg-neutral-100 text-neutral-600 px-2 py-0.5 text-[10px] font-semibold tabular-nums">{d.days_until}d</span>
                {/if}
              </div>
              <div class="flex items-center justify-between mt-2 pt-2 border-t border-neutral-100">
                <span class="text-xs text-neutral-500">{d.project_name}</span>
                <span class="text-xs font-bold text-neutral-900 tabular-nums">{currency.format(Number(d.total_amount))}</span>
              </div>
              <p class="text-[10px] text-neutral-400 mt-1">Expected: {d.expected_delivery_date}</p>
            </div>
          {/each}
        </div>

        <!-- Desktop table -->
        <div class="hidden lg:block rounded-xl border border-neutral-200 bg-white overflow-hidden">
          <table class="w-full text-sm">
            <thead><tr class="border-b border-neutral-100 bg-neutral-50">
              <th class="px-4 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase">PO #</th>
              <th class="px-4 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase">Vendor</th>
              <th class="px-4 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase">Project</th>
              <th class="px-4 py-2.5 text-center text-[10px] font-semibold text-neutral-500 uppercase">Expected</th>
              <th class="px-4 py-2.5 text-center text-[10px] font-semibold text-neutral-500 uppercase">Status</th>
              <th class="px-4 py-2.5 text-right text-[10px] font-semibold text-neutral-500 uppercase">Amount</th>
            </tr></thead>
            <tbody class="divide-y divide-neutral-50">
              {#each filteredDeliveries as d}
                <tr class="hover:bg-neutral-50 {d.is_overdue ? 'bg-red-50/30' : ''}">
                  <td class="px-4 py-3 font-semibold text-neutral-900">{d.po_number}</td>
                  <td class="px-4 py-3 text-neutral-700">{d.vendor_name}</td>
                  <td class="px-4 py-3 text-neutral-600">{d.project_name}</td>
                  <td class="px-4 py-3 text-center tabular-nums text-neutral-500">{d.expected_delivery_date}</td>
                  <td class="px-4 py-3 text-center">
                    {#if d.is_overdue}
                      <span class="rounded-full bg-red-100 text-red-700 px-2 py-0.5 text-[10px] font-bold">{Math.abs(d.days_until)}d overdue</span>
                    {:else if d.days_until === 0}
                      <span class="rounded-full bg-emerald-100 text-emerald-700 px-2 py-0.5 text-[10px] font-bold">Today</span>
                    {:else if d.days_until <= 3}
                      <span class="rounded-full bg-amber-100 text-amber-700 px-2 py-0.5 text-[10px] font-semibold">{d.days_until}d away</span>
                    {:else}
                      <span class="rounded-full bg-neutral-100 text-neutral-600 px-2 py-0.5 text-[10px] font-semibold">{d.days_until}d away</span>
                    {/if}
                  </td>
                  <td class="px-4 py-3 text-right font-semibold text-neutral-900 tabular-nums">{currency.format(Number(d.total_amount))}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    {/if}

    <!-- Received GRNs -->
    {#if activeTab === "received"}
      {#if filteredGRNs.length === 0}
        <div class="rounded-xl border border-neutral-200 bg-white p-6 text-center">
          <p class="text-sm text-neutral-500">No goods receipts found.</p>
        </div>
      {:else}
        <!-- Mobile cards -->
        <div class="space-y-2 lg:hidden">
          {#each filteredGRNs as g}
            <button type="button" onclick={() => openQI(g.id)} class="w-full text-left rounded-xl border border-neutral-200 bg-white p-4 hover:border-indigo-200 hover:bg-indigo-50/30 transition-colors">
              <div class="flex items-start justify-between">
                <div>
                  <p class="text-sm font-bold text-neutral-900">{g.grn_number}</p>
                  <p class="text-xs text-neutral-500 mt-0.5">PO: {g.po_number}</p>
                </div>
                <span class="rounded-full border px-2 py-0.5 text-[10px] font-semibold {STATUS_COLORS[g.status] || 'bg-neutral-100 text-neutral-600'}">{g.status.replace(/_/g, " ")}</span>
              </div>
              <div class="mt-2 grid grid-cols-2 gap-2 text-[10px]">
                <div><span class="text-neutral-400">Vendor:</span> <span class="text-neutral-700">{g.vendor_name}</span></div>
                <div><span class="text-neutral-400">Project:</span> <span class="text-neutral-700">{g.project_name}</span></div>
                <div><span class="text-neutral-400">Received:</span> <span class="text-neutral-700">{g.received_date}</span></div>
                <div><span class="text-neutral-400">By:</span> <span class="text-neutral-700">{g.received_by}</span></div>
              </div>
              {#if g.delivery_note_number}
                <p class="text-[10px] text-neutral-400 mt-1">DN: {g.delivery_note_number}</p>
              {/if}
            </button>
          {/each}
        </div>

        <!-- Desktop table -->
        <div class="hidden lg:block rounded-xl border border-neutral-200 bg-white overflow-hidden">
          <table class="w-full text-sm">
            <thead><tr class="border-b border-neutral-100 bg-neutral-50">
              <th class="px-4 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase">GRN #</th>
              <th class="px-4 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase">PO #</th>
              <th class="px-4 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase">Vendor</th>
              <th class="px-4 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase">Project</th>
              <th class="px-4 py-2.5 text-center text-[10px] font-semibold text-neutral-500 uppercase">Status</th>
              <th class="px-4 py-2.5 text-center text-[10px] font-semibold text-neutral-500 uppercase">Received</th>
              <th class="px-4 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase">By</th>
            </tr></thead>
            <tbody class="divide-y divide-neutral-50">
              {#each filteredGRNs as g}
                <tr class="hover:bg-indigo-50/50 cursor-pointer" onclick={() => openQI(g.id)}>
                  <td class="px-4 py-3 font-semibold text-neutral-800">{g.grn_number}</td>
                  <td class="px-4 py-3 text-neutral-600">{g.po_number}</td>
                  <td class="px-4 py-3 text-neutral-700">{g.vendor_name}</td>
                  <td class="px-4 py-3 text-neutral-600">{g.project_name}</td>
                  <td class="px-4 py-3 text-center"><span class="rounded-full border px-2 py-0.5 text-[10px] font-semibold {STATUS_COLORS[g.status] || ''}">{g.status.replace(/_/g, " ")}</span></td>
                  <td class="px-4 py-3 text-center tabular-nums text-neutral-500">{g.received_date}</td>
                  <td class="px-4 py-3 text-neutral-600">{g.received_by}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    {/if}

    <!-- Rejected GRNs -->
    {#if activeTab === "rejected"}
      {#if data.rejected_grns.length === 0}
        <div class="rounded-xl border border-emerald-200 bg-emerald-50 p-6 text-center">
          <p class="text-sm font-medium text-emerald-700">No rejected deliveries.</p>
          <p class="text-[10px] text-emerald-500 mt-1">All received goods have passed inspection.</p>
        </div>
      {:else}
        <div class="space-y-2">
          {#each data.rejected_grns as r}
            <div class="rounded-xl border border-red-200 bg-red-50/50 p-4">
              <div class="flex items-start justify-between">
                <div>
                  <p class="text-sm font-bold text-red-900">{r.grn_number}</p>
                  <p class="text-xs text-red-700 mt-0.5">PO: {r.po_number} | {r.vendor_name}</p>
                </div>
                <span class="rounded-full bg-red-100 text-red-700 px-2.5 py-0.5 text-[10px] font-bold">Rejected</span>
              </div>
              <p class="text-xs text-neutral-600 mt-1">{r.project_name}</p>
              {#if r.inspection_notes}
                <div class="mt-2 rounded-lg border border-red-200 bg-white p-3">
                  <p class="text-[9px] font-semibold text-red-500 uppercase mb-1">Inspection Notes</p>
                  <p class="text-xs text-red-800">{r.inspection_notes}</p>
                </div>
              {/if}
              <p class="text-[10px] text-neutral-400 mt-2">Received: {r.received_date}</p>
            </div>
          {/each}
        </div>
      {/if}
    {/if}

  {/if}
</div>

<!-- Log Arrival Drawer -->
{#if showLogArrival}
  <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
  <div class="fixed inset-0 z-50 flex justify-end bg-black/30" style="backdrop-filter: blur(4px)" onclick={() => { showLogArrival = false; }}>
    <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
    <div class="w-full max-w-2xl bg-white shadow-2xl overflow-y-auto" onclick={(e) => e.stopPropagation()}>
      <!-- Dark Header -->
      <div class="bg-neutral-900 px-5 py-4 flex items-center justify-between sticky top-0 z-10">
        <div>
          <h2 class="text-lg font-semibold text-white">Log Material Arrival</h2>
          <p class="text-xs text-neutral-400 mt-0.5">Record incoming delivery against a Purchase Order</p>
        </div>
        <button onclick={() => { showLogArrival = false; }} class="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-800 hover:text-white" aria-label="Close">
          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
        </button>
      </div>

      <div class="p-5 space-y-5">
        <!-- PO Lookup -->
        <div>
          <label class="block text-xs font-semibold text-neutral-700 mb-1.5">PO Number Lookup</label>
          <div class="flex gap-2">
            <input type="text" bind:value={poSearchQuery} placeholder="Enter PO number (e.g. PO-00012)"
              class="flex-1 rounded-xl border border-neutral-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
              onkeydown={(e) => { if (e.key === 'Enter') lookupPO(); }} />
            <button onclick={lookupPO} disabled={poLookupLoading || !poSearchQuery.trim()}
              class="rounded-xl bg-neutral-900 px-5 py-3 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-40 whitespace-nowrap">
              {poLookupLoading ? "Looking up..." : "Find PO"}
            </button>
          </div>
        </div>

        <!-- PO Details (auto-populated) -->
        {#if poData}
          <div class="rounded-xl border border-emerald-200 bg-emerald-50/50 p-4">
            <div class="grid grid-cols-2 gap-3 text-xs">
              <div><span class="text-neutral-400 block text-[9px] font-semibold uppercase">PO Number</span><span class="font-bold text-neutral-900">{poData.po_number}</span></div>
              <div><span class="text-neutral-400 block text-[9px] font-semibold uppercase">Vendor</span><span class="font-semibold text-neutral-900">{poData.vendor_name}</span></div>
              <div><span class="text-neutral-400 block text-[9px] font-semibold uppercase">Project</span><span class="text-neutral-700">{poData.project_name}</span></div>
              <div><span class="text-neutral-400 block text-[9px] font-semibold uppercase">Expected Delivery</span><span class="text-neutral-700">{poData.expected_delivery_date || "Not set"}</span></div>
            </div>
          </div>

          <!-- Delivery Note -->
          <div class="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <label class="block">
              <span class="text-xs font-semibold text-neutral-700 mb-1 block">Delivery Note #</span>
              <input type="text" bind:value={deliveryNoteNumber} placeholder="DN-001234"
                class="w-full rounded-xl border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
            </label>
            <label class="block">
              <span class="text-xs font-semibold text-neutral-700 mb-1 block">Notes</span>
              <input type="text" bind:value={arrivalNotes} placeholder="Condition, remarks..."
                class="w-full rounded-xl border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
            </label>
          </div>

          <!-- Line Items -->
          {#if arrivalLines.length === 0}
            <div class="rounded-xl border border-amber-200 bg-amber-50 p-4 text-center">
              <p class="text-sm text-amber-700 font-medium">All items on this PO have been fully received.</p>
            </div>
          {:else}
            <div>
              <h3 class="text-[10px] font-semibold text-neutral-500 uppercase tracking-widest mb-2">Items to Receive ({arrivalLines.length})</h3>
              <div class="space-y-3">
                {#each arrivalLines as line, i}
                  <div class="rounded-xl border border-neutral-200 bg-white p-4">
                    <!-- Item header -->
                    <div class="flex items-start justify-between mb-3">
                      <div>
                        <p class="text-sm font-semibold text-neutral-900">{line.description}</p>
                        <p class="text-[10px] text-neutral-500 mt-0.5">Ordered: {line.ordered} {line.unit} | Remaining: <span class="font-semibold text-amber-700">{line.remaining}</span></p>
                      </div>
                    </div>

                    <!-- Quantity (large input for mobile/tablet) -->
                    <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
                      <label class="block">
                        <span class="text-[9px] font-semibold text-neutral-500 uppercase mb-1 block">Qty Received *</span>
                        <input type="number" step="0.01" min="0" max={line.remaining} bind:value={line.quantity_received}
                          class="w-full rounded-lg border {Number(line.quantity_received) < Number(line.remaining) ? 'border-amber-300 bg-amber-50' : 'border-neutral-200'} px-3 py-2.5 text-sm font-bold tabular-nums focus:outline-none focus:ring-2 focus:ring-emerald-500" />
                        {#if Number(line.quantity_received) < Number(line.remaining)}
                          <p class="text-[8px] text-amber-600 font-semibold mt-0.5">Partial receipt</p>
                        {/if}
                      </label>
                      <label class="block">
                        <span class="text-[9px] font-semibold text-neutral-500 uppercase mb-1 block">Batch #</span>
                        <input type="text" bind:value={line.batch_number} placeholder="LOT-001"
                          class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                      </label>
                      <label class="block">
                        <span class="text-[9px] font-semibold text-neutral-500 uppercase mb-1 block">Expiry Date</span>
                        <input type="date" bind:value={line.expiry_date}
                          class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                      </label>
                      <label class="block">
                        <span class="text-[9px] font-semibold text-neutral-500 uppercase mb-1 block">Storage Location</span>
                        <input type="text" bind:value={line.storage_location} placeholder="Bay A-3"
                          class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                      </label>
                    </div>
                  </div>
                {/each}
              </div>
            </div>

            <!-- Submit -->
            <div class="sticky bottom-0 bg-white border-t border-neutral-100 -mx-5 px-5 py-4 flex gap-3">
              <button onclick={() => { showLogArrival = false; }}
                class="flex-1 rounded-xl border border-neutral-200 py-3 text-sm font-medium text-neutral-700 hover:bg-neutral-50">
                Cancel
              </button>
              <button onclick={submitArrival} disabled={arrivalSaving}
                class="flex-1 rounded-xl bg-emerald-600 py-3 text-sm font-bold text-white hover:bg-emerald-700 disabled:opacity-50 shadow-sm">
                {arrivalSaving ? "Saving..." : `Confirm Receipt (${arrivalLines.filter(l => Number(l.quantity_received) > 0).length} items)`}
              </button>
            </div>
          {/if}
        {/if}
      </div>
    </div>
  </div>
{/if}

<!-- Quality Inspection Drawer -->
{#if showQI}
  <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
  <div class="fixed inset-0 z-50 flex justify-end bg-black/30" style="backdrop-filter: blur(4px)" onclick={() => { showQI = false; qiData = null; }}>
    <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
    <div class="w-full max-w-2xl bg-white shadow-2xl overflow-y-auto" onclick={(e) => e.stopPropagation()}>
      <!-- Dark Header -->
      <div class="bg-neutral-900 px-5 py-4 flex items-center justify-between sticky top-0 z-10">
        <div>
          <h2 class="text-lg font-semibold text-white">Quality Inspection</h2>
          {#if qiData}
            <p class="text-xs text-neutral-400 mt-0.5">{qiData.grn_number} | PO: {qiData.po_number} | {qiData.vendor_name}</p>
          {/if}
        </div>
        <button onclick={() => { showQI = false; qiData = null; }} class="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-800 hover:text-white" aria-label="Close">
          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
        </button>
      </div>

      {#if qiLoading}
        <div class="p-12 text-center text-sm text-neutral-400">Loading inspection data...</div>
      {:else if qiData}
        <div class="p-5 space-y-5">
          <!-- GRN Info -->
          <div class="grid grid-cols-2 gap-3 sm:grid-cols-4 text-xs">
            <div><span class="text-[9px] font-semibold text-neutral-400 uppercase block">Project</span><span class="text-neutral-900 font-medium">{qiData.project_name}</span></div>
            <div><span class="text-[9px] font-semibold text-neutral-400 uppercase block">Received</span><span class="text-neutral-900">{qiData.received_date}</span></div>
            <div><span class="text-[9px] font-semibold text-neutral-400 uppercase block">By</span><span class="text-neutral-900">{qiData.received_by}</span></div>
            <div><span class="text-[9px] font-semibold text-neutral-400 uppercase block">Status</span><span class="rounded-full border px-2 py-0.5 text-[10px] font-semibold {STATUS_COLORS[qiData.status] || ''}">{qiData.status.replace(/_/g, " ")}</span></div>
          </div>

          <!-- Inspection Notes -->
          <label class="block">
            <span class="text-xs font-semibold text-neutral-700 mb-1 block">Overall Inspection Notes</span>
            <textarea bind:value={qiNotes} rows="2" placeholder="General observations about this delivery..."
              class="w-full rounded-xl border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
          </label>

          <!-- Items -->
          <div>
            <h3 class="text-[10px] font-semibold text-neutral-500 uppercase tracking-widest mb-3">Items ({qiData.items.length})</h3>
            <div class="space-y-4">
              {#each qiData.items as item, i}
                <div class="rounded-xl border {qiItems[i]?.quality_status === 'failed' ? 'border-red-200 bg-red-50/30' : qiItems[i]?.quality_status === 'passed' ? 'border-emerald-200 bg-emerald-50/30' : qiItems[i]?.quality_status === 'conditional' ? 'border-amber-200 bg-amber-50/30' : 'border-neutral-200'} p-4 transition-colors">
                  <!-- Item header -->
                  <div class="flex items-start justify-between mb-3">
                    <div>
                      <p class="text-sm font-semibold text-neutral-900">{item.description}</p>
                      <p class="text-[10px] text-neutral-500 mt-0.5">
                        Received: <span class="font-semibold">{item.quantity_received}</span> {item.unit_of_measure}
                        {#if item.batch_number} | Batch: {item.batch_number}{/if}
                        {#if item.expiry_date} | Exp: {item.expiry_date}{/if}
                      </p>
                    </div>
                  </div>

                  <!-- Pass / Fail / Conditional toggle -->
                  <div class="flex gap-1 mb-3">
                    <button type="button" onclick={() => setItemStatus(i, "passed")}
                      class="flex-1 rounded-lg py-2.5 text-xs font-bold transition-colors {qiItems[i]?.quality_status === 'passed' ? 'bg-emerald-600 text-white shadow-sm' : 'bg-neutral-100 text-neutral-600 hover:bg-emerald-50 hover:text-emerald-700'}">
                      Pass
                    </button>
                    <button type="button" onclick={() => setItemStatus(i, "conditional")}
                      class="flex-1 rounded-lg py-2.5 text-xs font-bold transition-colors {qiItems[i]?.quality_status === 'conditional' ? 'bg-amber-500 text-white shadow-sm' : 'bg-neutral-100 text-neutral-600 hover:bg-amber-50 hover:text-amber-700'}">
                      Partial
                    </button>
                    <button type="button" onclick={() => setItemStatus(i, "failed")}
                      class="flex-1 rounded-lg py-2.5 text-xs font-bold transition-colors {qiItems[i]?.quality_status === 'failed' ? 'bg-red-600 text-white shadow-sm' : 'bg-neutral-100 text-neutral-600 hover:bg-red-50 hover:text-red-700'}">
                      Fail
                    </button>
                  </div>

                  <!-- Conditional: qty accepted/rejected -->
                  {#if qiItems[i]?.quality_status === "conditional"}
                    <div class="grid grid-cols-2 gap-3 mb-3">
                      <label class="block">
                        <span class="text-[9px] font-semibold text-emerald-600 uppercase mb-1 block">Qty Accepted</span>
                        <input type="number" step="0.01" min="0" bind:value={qiItems[i].quantity_accepted}
                          class="w-full rounded-lg border border-emerald-200 px-3 py-2.5 text-sm font-bold tabular-nums focus:outline-none focus:ring-2 focus:ring-emerald-500" />
                      </label>
                      <label class="block">
                        <span class="text-[9px] font-semibold text-red-500 uppercase mb-1 block">Qty Rejected</span>
                        <input type="number" step="0.01" min="0" bind:value={qiItems[i].quantity_rejected}
                          class="w-full rounded-lg border border-red-200 px-3 py-2.5 text-sm font-bold tabular-nums focus:outline-none focus:ring-2 focus:ring-red-500" />
                      </label>
                    </div>
                  {/if}

                  <!-- Quality notes -->
                  <label class="block mb-2">
                    <span class="text-[9px] font-semibold text-neutral-500 uppercase mb-1 block">Quality Notes</span>
                    <input type="text" bind:value={qiItems[i].quality_notes} placeholder="Grade check, visual inspection..."
                      class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
                  </label>

                  <!-- Rejection reason (mandatory for fail/reject) -->
                  {#if qiItems[i]?.quality_status === "failed" || Number(qiItems[i]?.quantity_rejected) > 0}
                    <label class="block">
                      <span class="text-[9px] font-semibold text-red-500 uppercase mb-1 block">Rejection Reason *</span>
                      <textarea bind:value={qiItems[i].rejection_reason} rows="2" placeholder="Describe the defect, damage, or non-compliance... (required)"
                        class="w-full rounded-lg border border-red-300 bg-red-50/50 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-500 resize-none"></textarea>
                    </label>
                  {/if}

                  <!-- Photo upload -->
                  <div class="mt-3">
                    <input type="file" accept="image/*" capture="environment"
                      id={`photo-input-${i}`}
                      class="hidden"
                      onchange={async (e) => {
                        const file = (e.target as HTMLInputElement).files?.[0];
                        if (!file || !qiData) return;
                        const fd = new FormData();
                        fd.append("image", file);
                        fd.append("grn_id", String(qiData.grn_id));
                        fd.append("receipt_item_id", String(item.id));
                        fd.append("photo_type", qiItems[i]?.quality_status === "failed" ? "damage" : "grade");
                        fd.append("caption", `${item.description} — QC photo`);
                        try {
                          const res = await fetch("/api/procurement-integration/grn-photos/", {
                            method: "POST",
                            headers: { Authorization: `Bearer ${localStorage.getItem("access_token")}` },
                            body: fd,
                          });
                          if (res.ok) toast.success("Uploaded", "Photo attached.");
                          else toast.error("Failed", "Could not upload photo.");
                        } catch { toast.error("Failed", "Upload error."); }
                        (e.target as HTMLInputElement).value = "";
                      }}
                    />
                    <button type="button" onclick={() => document.getElementById(`photo-input-${i}`)?.click()}
                      class="w-full rounded-lg border border-dashed border-neutral-300 bg-neutral-50 p-3 text-center hover:border-indigo-300 hover:bg-indigo-50/30 transition-colors">
                      <svg class="mx-auto h-5 w-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6.827 6.175A2.31 2.31 0 0 1 5.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 0 0-1.134-.175 2.31 2.31 0 0 1-1.64-1.055l-.822-1.316a2.192 2.192 0 0 0-1.736-1.039 48.774 48.774 0 0 0-5.232 0 2.192 2.192 0 0 0-1.736 1.039l-.821 1.316Z" /><path stroke-linecap="round" stroke-linejoin="round" d="M16.5 12.75a4.5 4.5 0 1 1-9 0 4.5 4.5 0 0 1 9 0ZM18.75 10.5h.008v.008h-.008V10.5Z" /></svg>
                      <p class="text-[10px] text-neutral-500 mt-1">Tap to capture or upload photo</p>
                    </button>
                  </div>
                </div>
              {/each}
            </div>
          </div>

          <!-- Submit -->
          <div class="sticky bottom-0 bg-white border-t border-neutral-100 -mx-5 px-5 py-4 flex gap-3">
            <button onclick={() => { showQI = false; qiData = null; }}
              class="flex-1 rounded-xl border border-neutral-200 py-3 text-sm font-medium text-neutral-700 hover:bg-neutral-50">
              Cancel
            </button>
            <button onclick={submitInspection} disabled={qiSaving}
              class="flex-1 rounded-xl bg-neutral-900 py-3 text-sm font-bold text-white hover:bg-neutral-800 disabled:opacity-50 shadow-sm">
              {qiSaving ? "Saving..." : "Submit Inspection"}
            </button>
          </div>
        </div>
      {/if}
    </div>
  </div>
{/if}

<!-- GRN Document Preview Modal -->
{#if showGRNDoc}
  <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
  <div class="fixed inset-0 z-60 flex items-center justify-center bg-black/40 p-4" style="backdrop-filter: blur(8px)" onclick={() => { showGRNDoc = false; grnDoc = null; }}>
    <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
    <div class="w-full max-w-3xl max-h-[90vh] rounded-2xl bg-white shadow-2xl overflow-hidden flex flex-col" onclick={(e) => e.stopPropagation()}>
      <!-- Header -->
      <div class="bg-neutral-900 px-6 py-4 flex items-center justify-between shrink-0">
        <div>
          <h2 class="text-lg font-semibold text-white">Goods Receipt Note</h2>
          {#if grnDoc}<p class="text-xs text-neutral-400 mt-0.5">{grnDoc.grn_number}</p>{/if}
        </div>
        <div class="flex items-center gap-2">
          {#if grnDoc}
            <button onclick={printGRN} class="rounded-lg bg-emerald-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700">
              Print / PDF
            </button>
          {/if}
          <button onclick={() => { showGRNDoc = false; grnDoc = null; }} class="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-800 hover:text-white" aria-label="Close">
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
          </button>
        </div>
      </div>

      <!-- Document body -->
      <div class="flex-1 overflow-y-auto p-6">
        {#if grnDocLoading}
          <div class="py-16 text-center text-sm text-neutral-400">Loading document...</div>
        {:else if grnDoc}
          <div id="grn-print-area">
            <!-- Document header -->
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px;">
              <div>
                <p style="font-size: 22px; font-weight: 800; color: #171717; letter-spacing: -0.5px;">GOODS RECEIPT NOTE</p>
                <p style="font-size: 13px; color: #737373; margin-top: 4px;">{grnDoc.org_name}</p>
              </div>
              <div style="text-align: right;">
                <p style="font-size: 16px; font-weight: 700; color: #171717;">{grnDoc.grn_number}</p>
                <p class="badge {grnDoc.status === 'accepted' ? 'passed' : grnDoc.status === 'rejected' ? 'failed' : ''}" style="margin-top: 4px; display: inline-block; padding: 2px 10px; border-radius: 4px; font-size: 11px; font-weight: 600; {grnDoc.status === 'accepted' ? 'background:#d1fae5;color:#065f46' : grnDoc.status === 'rejected' ? 'background:#fee2e2;color:#991b1b' : 'background:#f5f5f5;color:#525252'}">{grnDoc.status_display}</p>
              </div>
            </div>

            <!-- Info grid -->
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 16px; margin-bottom: 20px;">
              <div>
                <p class="label" style="font-size: 9px; text-transform: uppercase; color: #a3a3a3; font-weight: 600;">PO Number</p>
                <p class="value" style="font-size: 13px; font-weight: 600; margin-top: 2px;">{grnDoc.po_number}</p>
              </div>
              <div>
                <p class="label" style="font-size: 9px; text-transform: uppercase; color: #a3a3a3; font-weight: 600;">Vendor</p>
                <p class="value" style="font-size: 13px; font-weight: 600; margin-top: 2px;">{grnDoc.vendor_name}</p>
              </div>
              <div>
                <p class="label" style="font-size: 9px; text-transform: uppercase; color: #a3a3a3; font-weight: 600;">Project</p>
                <p class="value" style="font-size: 13px; font-weight: 600; margin-top: 2px;">{grnDoc.project_name}</p>
              </div>
              <div>
                <p class="label" style="font-size: 9px; text-transform: uppercase; color: #a3a3a3; font-weight: 600;">Received Date</p>
                <p class="value" style="font-size: 13px; font-weight: 600; margin-top: 2px;">{grnDoc.received_date}</p>
              </div>
              <div>
                <p class="label" style="font-size: 9px; text-transform: uppercase; color: #a3a3a3; font-weight: 600;">Received By</p>
                <p class="value" style="font-size: 13px; margin-top: 2px;">{grnDoc.received_by}</p>
              </div>
              <div>
                <p class="label" style="font-size: 9px; text-transform: uppercase; color: #a3a3a3; font-weight: 600;">Delivery Note</p>
                <p class="value" style="font-size: 13px; margin-top: 2px;">{grnDoc.delivery_note_number || "—"}</p>
              </div>
              <div>
                <p class="label" style="font-size: 9px; text-transform: uppercase; color: #a3a3a3; font-weight: 600;">PO Date</p>
                <p class="value" style="font-size: 13px; margin-top: 2px;">{grnDoc.po_date || "—"}</p>
              </div>
              <div>
                <p class="label" style="font-size: 9px; text-transform: uppercase; color: #a3a3a3; font-weight: 600;">Items</p>
                <p class="value" style="font-size: 13px; font-weight: 600; margin-top: 2px;">{grnDoc.item_count}</p>
              </div>
            </div>

            <!-- Items table -->
            <table style="width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 11px;">
              <thead>
                <tr style="background: #f5f5f5;">
                  <th style="border: 1px solid #d4d4d4; padding: 6px 8px; text-align: left; font-size: 9px; text-transform: uppercase; letter-spacing: 0.5px;">Description</th>
                  <th style="border: 1px solid #d4d4d4; padding: 6px 8px; text-align: center; font-size: 9px; text-transform: uppercase;">Unit</th>
                  <th style="border: 1px solid #d4d4d4; padding: 6px 8px; text-align: center; font-size: 9px; text-transform: uppercase;">Ordered</th>
                  <th style="border: 1px solid #d4d4d4; padding: 6px 8px; text-align: center; font-size: 9px; text-transform: uppercase;">Received</th>
                  <th style="border: 1px solid #d4d4d4; padding: 6px 8px; text-align: center; font-size: 9px; text-transform: uppercase;">Accepted</th>
                  <th style="border: 1px solid #d4d4d4; padding: 6px 8px; text-align: center; font-size: 9px; text-transform: uppercase;">Rejected</th>
                  <th style="border: 1px solid #d4d4d4; padding: 6px 8px; text-align: right; font-size: 9px; text-transform: uppercase;">Rate</th>
                  <th style="border: 1px solid #d4d4d4; padding: 6px 8px; text-align: right; font-size: 9px; text-transform: uppercase;">Value</th>
                  <th style="border: 1px solid #d4d4d4; padding: 6px 8px; text-align: center; font-size: 9px; text-transform: uppercase;">QC</th>
                </tr>
              </thead>
              <tbody>
                {#each grnDoc.items as item}
                  <tr>
                    <td style="border: 1px solid #e5e5e5; padding: 6px 8px; font-weight: 500;">
                      {item.description}
                      {#if item.batch_number}<br><span style="font-size: 9px; color: #737373;">Batch: {item.batch_number}</span>{/if}
                    </td>
                    <td style="border: 1px solid #e5e5e5; padding: 6px 8px; text-align: center;">{item.unit}</td>
                    <td style="border: 1px solid #e5e5e5; padding: 6px 8px; text-align: center; font-variant-numeric: tabular-nums;">{item.ordered_qty}</td>
                    <td style="border: 1px solid #e5e5e5; padding: 6px 8px; text-align: center; font-variant-numeric: tabular-nums; font-weight: 600;">{item.received_qty}</td>
                    <td style="border: 1px solid #e5e5e5; padding: 6px 8px; text-align: center; font-variant-numeric: tabular-nums; color: #065f46;">{item.accepted_qty}</td>
                    <td style="border: 1px solid #e5e5e5; padding: 6px 8px; text-align: center; font-variant-numeric: tabular-nums; {Number(item.rejected_qty) > 0 ? 'color: #991b1b; font-weight: 600;' : ''}">{item.rejected_qty}</td>
                    <td style="border: 1px solid #e5e5e5; padding: 6px 8px; text-align: right; font-variant-numeric: tabular-nums;">{currency.format(Number(item.unit_price))}</td>
                    <td style="border: 1px solid #e5e5e5; padding: 6px 8px; text-align: right; font-variant-numeric: tabular-nums; font-weight: 600;">{currency.format(Number(item.line_value))}</td>
                    <td style="border: 1px solid #e5e5e5; padding: 6px 8px; text-align: center;">
                      <span style="padding: 1px 6px; border-radius: 3px; font-size: 9px; font-weight: 600; {item.quality_status === 'passed' ? 'background:#d1fae5;color:#065f46' : item.quality_status === 'failed' ? 'background:#fee2e2;color:#991b1b' : 'background:#fef3c7;color:#92400e'}">{item.quality_status}</span>
                    </td>
                  </tr>
                {/each}
              </tbody>
              <tfoot>
                <tr style="background: #fafafa;">
                  <td colspan="7" style="border: 1px solid #d4d4d4; padding: 8px; text-align: right; font-weight: 700; font-size: 12px;">TOTAL VALUE</td>
                  <td colspan="2" style="border: 1px solid #d4d4d4; padding: 8px; text-align: right; font-weight: 700; font-size: 14px; color: #065f46; font-variant-numeric: tabular-nums;">{currency.format(Number(grnDoc.total_value))}</td>
                </tr>
              </tfoot>
            </table>

            {#if grnDoc.inspection_notes}
              <div style="margin: 16px 0; padding: 12px; border: 1px solid #e5e5e5; border-radius: 8px; background: #fafafa;">
                <p style="font-size: 9px; text-transform: uppercase; color: #a3a3a3; font-weight: 600; margin-bottom: 4px;">Inspection Notes</p>
                <p style="font-size: 12px; color: #404040;">{grnDoc.inspection_notes}</p>
              </div>
            {/if}

            <!-- Signature lines -->
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 40px; margin-top: 48px;">
              <div>
                <div style="border-top: 1px solid #a3a3a3; padding-top: 6px;">
                  <p style="font-size: 10px; color: #737373;">Received By</p>
                  <p style="font-size: 11px; font-weight: 600; margin-top: 2px;">{grnDoc.received_by}</p>
                </div>
              </div>
              <div>
                <div style="border-top: 1px solid #a3a3a3; padding-top: 6px;">
                  <p style="font-size: 10px; color: #737373;">Inspected By</p>
                </div>
              </div>
              <div>
                <div style="border-top: 1px solid #a3a3a3; padding-top: 6px;">
                  <p style="font-size: 10px; color: #737373;">Authorized By</p>
                </div>
              </div>
            </div>

            <p style="text-align: center; font-size: 9px; color: #a3a3a3; margin-top: 32px;">Generated by <span style="font-weight: 400; color: #171717;">developer</span><span style="font-weight: 700; color: #a3a3a3;">OS</span> — {new Date().toLocaleDateString()}</p>
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}

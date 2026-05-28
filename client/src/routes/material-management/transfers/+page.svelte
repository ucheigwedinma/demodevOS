<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import { onMount } from "svelte";

  interface Route { source: string; source_location: string; destination: string; dest_location: string; }
  interface TransferItem { id: number; transfer_number: string; source_name: string; destination_name: string; project_name: string; status: string; priority: string; scheduled_date: string | null; dispatched_date: string | null; delivered_date: string | null; confirmed_date: string | null; dispatched_by: string; received_by: string; vehicle_details: string; waybill_number: string; requested_by_name: string; approved_by: string; line_count: number; total_value: string; created_at: string; }
  interface TransferLine { id: number; item: number; item_name: string; item_sku: string; quantity: string; received_quantity: string; unit_of_measure: string; unit_cost: string; line_value: string; notes: string; }
  interface TransferDetail extends TransferItem { notes: string; reason: string; lines: TransferLine[]; }
  interface DashboardData { in_transit_value: string; in_transit_count: number; pending_receipts: number; todays_transfers: number; status_counts: Record<string, number>; active_routes: Route[]; recent_transfers: TransferItem[]; }

  const STATUS_COLORS: Record<string, string> = {
    draft: "bg-neutral-100 text-neutral-600", requested: "bg-blue-100 text-blue-700",
    approved: "bg-indigo-100 text-indigo-700", in_transit: "bg-amber-100 text-amber-700",
    delivered: "bg-cyan-100 text-cyan-700", received: "bg-emerald-100 text-emerald-700",
    partially_received: "bg-yellow-100 text-yellow-700", cancelled: "bg-neutral-100 text-neutral-400",
  };
  const PRIORITY_COLORS: Record<string, string> = {
    low: "text-neutral-500", normal: "text-blue-600", high: "text-amber-600", urgent: "text-red-600",
  };

  let loading = $state(true);
  let data = $state<DashboardData | null>(null);
  let statusFilter = $state("");
  let viewMode = $state<"orders" | "ledger">("orders");

  // Flattened ledger: one row per material per transfer
  interface LedgerRow { transfer_id: number; to_number: string; item_name: string; item_sku: string; quantity: string; unit: string; source: string; destination: string; dispatch_date: string | null; status: string; priority: string; value: string; }

  const ledgerRows = $derived.by(() => {
    if (!data) return [] as LedgerRow[];
    const rows: LedgerRow[] = [];
    // We need detail data — for now build from available list data
    // The ledger is populated from the recent_transfers which have line_count but not individual lines
    // So we show transfer-level rows with material count
    for (const t of data.recent_transfers) {
      rows.push({
        transfer_id: t.id,
        to_number: t.transfer_number,
        item_name: `${t.line_count} material(s)`,
        item_sku: "",
        quantity: "",
        unit: "",
        source: t.source_name,
        destination: t.destination_name,
        dispatch_date: t.dispatched_date || t.scheduled_date,
        status: t.status,
        priority: t.priority,
        value: t.total_value,
      });
    }
    return statusFilter ? rows.filter(r => r.status === statusFilter) : rows;
  });

  // Load full ledger data (with lines) from a dedicated call
  let ledgerData = $state<LedgerRow[]>([]);
  let ledgerLoading = $state(false);

  async function loadLedger() {
    ledgerLoading = true;
    try {
      const res = await api.get<{ results: any[] }>("/material-transfers/", { page_size: "50", ordering: "-created_at" });
      const rows: LedgerRow[] = [];
      for (const t of res.results) {
        // Fetch lines for each transfer
        try {
          const detail = await api.get<TransferDetail>(`/material-transfers/${t.id}/`);
          for (const line of detail.lines) {
            rows.push({
              transfer_id: t.id,
              to_number: t.transfer_number,
              item_name: line.item_name,
              item_sku: line.item_sku,
              quantity: `${Number(line.quantity).toLocaleString()} ${line.unit_of_measure}`,
              unit: line.unit_of_measure,
              source: t.source_name || "",
              destination: t.destination_name || "",
              dispatch_date: t.dispatched_date || t.scheduled_date,
              status: t.status,
              priority: t.priority,
              value: line.line_value,
            });
          }
        } catch { /* skip failed detail loads */ }
      }
      ledgerData = statusFilter ? rows.filter(r => r.status === statusFilter) : rows;
    } catch { ledgerData = []; }
    finally { ledgerLoading = false; }
  }

  // Detail
  let showDetail = $state(false);
  let detail = $state<TransferDetail | null>(null);
  let detailLoading = $state(false);

  // Create
  let showCreate = $state(false);
  let createSaving = $state(false);
  let warehouses = $state<{ id: number; name: string }[]>([]);
  let projects = $state<{ id: number; name: string }[]>([]);
  let items = $state<{ id: number; name: string; sku: string; default_unit_cost: string }[]>([]);
  let createForm = $state({ source_warehouse: "", destination_warehouse: "", project: "", priority: "normal", reason: "", reason_category: "", scheduled_date: "", vehicle_details: "", driver_name: "", vehicle_plate: "", gate_pass_id: "", notes: "" });
  let createLines = $state<{ item: string; quantity: string; unit_of_measure: string; available_stock: string; stock_status: string }[]>([]);

  const REASON_CATEGORIES = [
    { value: "surplus_redistribution", label: "Surplus Redistribution", icon: "🔄" },
    { value: "central_procurement", label: "Central Procurement", icon: "🏢" },
    { value: "project_closure", label: "Project Closure", icon: "✅" },
    { value: "site_demand", label: "Urgent Site Demand", icon: "🚨" },
    { value: "stock_balancing", label: "Stock Balancing", icon: "⚖️" },
    { value: "quality_issue", label: "Quality Return", icon: "⚠️" },
    { value: "other", label: "Other", icon: "📋" },
  ];

  async function checkTransferStock(idx: number) {
    const line = createLines[idx];
    if (!line.item || !createForm.source_warehouse) { line.available_stock = "—"; line.stock_status = ""; return; }
    try {
      const res = await api.get<{ results: any[] }>("/inventory/stocks/", { item: line.item, warehouse: createForm.source_warehouse, page_size: "1" });
      if (res.results.length > 0) {
        const qty = Number(res.results[0].quantity_on_hand || 0);
        line.available_stock = String(qty);
        line.stock_status = qty >= Number(line.quantity) ? "sufficient" : qty > 0 ? "insufficient" : "none";
      } else { line.available_stock = "0"; line.stock_status = "none"; }
    } catch { line.available_stock = "?"; line.stock_status = ""; }
    createLines = [...createLines];
  }

  // Recheck all lines when source warehouse changes
  async function onSourceChange() {
    for (let i = 0; i < createLines.length; i++) {
      if (createLines[i].item) await checkTransferStock(i);
    }
  }

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  // Waybill
  interface WaybillData {
    received_by: string; transfer_number: string; source_warehouse: string; source_location: string; destination_warehouse: string; destination_location: string; project_name: string; org_name: string; priority: string; reason: string; scheduled_date: string; dispatched_date: string; vehicle_details: string; waybill_number: string; requested_by: string; approved_by: string; dispatched_by: string; items: { description: string; sku: string; quantity: string; unit: string; unit_cost: string; line_value: string }[]; total_value: string; total_qty: string; item_count: number; qr_data: string; qr_hash: string; 
}
  let showWaybill = $state(false);
  let waybillData = $state<WaybillData | null>(null);
  let waybillLoading = $state(false);

  async function openWaybill(transferId: number) {
    showWaybill = true;
    waybillLoading = true;
    try {
      waybillData = await api.get<WaybillData>("/material-transfers/waybill/", { transfer_id: String(transferId) });
    } catch { toast.error("Failed", "Could not generate waybill."); }
    finally { waybillLoading = false; }
  }

  function printWaybill() {
    const el = document.getElementById("waybill-print");
    if (!el) return;
    const w = window.open("", "_blank", "width=800,height=600");
    if (!w) return;
    w.document.write(`<html><head><title>Waybill — ${waybillData?.waybill_number}</title><style>
      body{font-family:Raleway,Arial,sans-serif;padding:24px;color:#1a1a1a;font-size:12px}
      table{width:100%;border-collapse:collapse;margin:12px 0}
      th,td{border:1px solid #d4d4d4;padding:6px 10px;text-align:left}
      th{background:#f5f5f5;font-size:10px;text-transform:uppercase;letter-spacing:.5px}
      .qr{width:80px;height:80px;border:2px solid #171717;border-radius:8px;display:flex;align-items:center;justify-content:center;font-family:monospace;font-size:9px;word-break:break-all;padding:4px}
      @media print{body{padding:0}}
    </style></head><body>${el.innerHTML}</body></html>`);
    w.document.close();
    w.print();
  }

  // Receiving Confirmation
  let showReceiving = $state(false);
  let receivingTransfer = $state<TransferDetail | null>(null);
  let receivingLines = $state<{ line_id: number; item_name: string; item_sku: string; expected: string; unit: string; received: string; condition: "good" | "damaged"; damage_notes: string }[]>([]);
  let receivingSaving = $state(false);
  let receivingSignature = $state(false);

  function openReceiving(transfer: TransferDetail) {
    receivingTransfer = transfer;
    receivingLines = transfer.lines.map(l => ({
      line_id: l.id,
      item_name: l.item_name,
      item_sku: l.item_sku,
      expected: l.quantity,
      unit: l.unit_of_measure,
      received: l.quantity, // default to full qty
      condition: "good" as const,
      damage_notes: "",
    }));
    receivingSignature = false;
    showReceiving = true;
  }

  async function submitReceiving() {
    if (!receivingTransfer) return;
    if (!receivingSignature) { toast.error("Required", "Digital sign-off is required to confirm receipt."); return; }

    // Validate damaged items have notes
    const damagedWithoutNotes = receivingLines.filter(l => l.condition === "damaged" && !l.damage_notes.trim());
    if (damagedWithoutNotes.length > 0) { toast.error("Required", "Damage notes are required for all damaged items."); return; }

    receivingSaving = true;
    try {
      const lines = receivingLines.map(l => ({
        line_id: l.line_id,
        received_quantity: Number(l.received),
      }));
      await api.post(`/material-transfers/${receivingTransfer.id}/confirm-receipt/`, { lines });

      // Calculate summary
      const shortfalls = receivingLines.filter(l => Number(l.received) < Number(l.expected));
      const damaged = receivingLines.filter(l => l.condition === "damaged");

      let msg = `Receipt confirmed. ${receivingLines.length} item(s) checked in.`;
      if (shortfalls.length > 0) msg += ` ${shortfalls.length} shortfall(s) recorded.`;
      if (damaged.length > 0) msg += ` ${damaged.length} damage report(s) filed.`;

      toast.success("Receipt Confirmed", msg);
      showReceiving = false;
      if (detail) await openDetail(detail.id);
      await loadDashboard();
    } catch (err) {
      if (err instanceof ApiError) toast.error("Failed", err.data?.detail || "Could not confirm receipt.");
      else toast.error("Failed", "Receipt confirmation failed.");
    } finally { receivingSaving = false; }
  }

  const filteredTransfers = $derived.by(() => {
    if (!data) return [];
    if (!statusFilter) return data.recent_transfers;
    return data.recent_transfers.filter(t => t.status === statusFilter);
  });

  async function loadDashboard() {
    loading = true;
    try {
      const [dashRes, whRes, projRes, itemRes] = await Promise.all([
        api.get<DashboardData>("/material-transfers/dashboard/"),
        api.get<{ results: any[] }>("/inventory/warehouses/", { page_size: "100" }),
        api.get<{ results: any[] }>("/projects/", { page_size: "100" }),
        api.get<{ results: any[] }>("/inventory/items/", { page_size: "200", is_active: "true" }),
      ]);
      data = dashRes;
      warehouses = whRes.results.map((w: any) => ({ id: w.id, name: w.name }));
      projects = projRes.results.map((p: any) => ({ id: p.id, name: p.name }));
      items = itemRes.results.map((i: any) => ({ id: i.id, name: i.name, sku: i.sku, default_unit_cost: i.default_unit_cost || "0" }));
    } catch { toast.error("Load failed", "Could not load transfer data."); }
    finally { loading = false; }
  }

  async function openDetail(id: number) {
    showDetail = true; detailLoading = true;
    try { detail = await api.get<TransferDetail>(`/material-transfers/${id}/`); }
    catch { toast.error("Load failed", "Could not load transfer details."); }
    finally { detailLoading = false; }
  }

  async function createTransfer() {
    if (!createForm.source_warehouse || !createForm.destination_warehouse) { toast.error("Required", "Source and destination warehouses are required."); return; }
    if (createForm.source_warehouse === createForm.destination_warehouse) { toast.error("Invalid", "Source and destination must be different."); return; }
    if (createLines.length === 0) { toast.error("Required", "Add at least one material line."); return; }
    // Validate stock availability
    const insufficient = createLines.filter(l => l.stock_status === "insufficient" || l.stock_status === "none");
    if (insufficient.length > 0) {
      const canProceed = confirm(`${insufficient.length} item(s) exceed available stock at source. Proceed anyway?`);
      if (!canProceed) return;
    }
    createSaving = true;
    try {
      const fullReason = createForm.reason_category ? `[${REASON_CATEGORIES.find(r => r.value === createForm.reason_category)?.label || createForm.reason_category}] ${createForm.reason}` : createForm.reason;
      const vehicleInfo = [createForm.driver_name, createForm.vehicle_plate, createForm.gate_pass_id ? `Gate: ${createForm.gate_pass_id}` : ""].filter(Boolean).join(" | ");
      const payload: Record<string, unknown> = { ...createForm, reason: fullReason, vehicle_details: vehicleInfo || createForm.vehicle_details, source_warehouse: Number(createForm.source_warehouse), destination_warehouse: Number(createForm.destination_warehouse), status: "requested" };
      delete payload.reason_category; delete payload.driver_name; delete payload.vehicle_plate; delete payload.gate_pass_id;
      if (createForm.project) payload.project = Number(createForm.project); else delete payload.project;
      if (!createForm.scheduled_date) delete payload.scheduled_date;
      const created = await api.post<{ id: number; transfer_number: string }>("/material-transfers/", payload);
      for (const line of createLines) {
        if (!line.item) continue;
        const itemData = items.find(i => String(i.id) === line.item);
        await api.post(`/material-transfers/${created.id}/lines/`, { item: Number(line.item), quantity: Number(line.quantity), unit_of_measure: line.unit_of_measure, unit_cost: Number(itemData?.default_unit_cost || 0) });
      }
      toast.success("Created", `Transfer ${created.transfer_number} created.`);
      showCreate = false;
      createForm = { source_warehouse: "", destination_warehouse: "", project: "", priority: "normal", reason: "", scheduled_date: "", vehicle_details: "", notes: "" };
      createLines = [];
      await loadDashboard();
    } catch (err) {
      if (err instanceof ApiError) toast.error("Failed", Object.values(err.fieldErrors).flat().join(" ") || "Check the form.");
      else toast.error("Failed", "Could not create transfer.");
    } finally { createSaving = false; }
  }

  async function approveTransfer() { if (!detail) return; try { await api.post(`/material-transfers/${detail.id}/approve/`, {}); toast.success("Approved", "Transfer approved."); await openDetail(detail.id); await loadDashboard(); } catch (err) { if (err instanceof ApiError) toast.error("Failed", err.data?.detail || "Cannot approve."); else toast.error("Failed", "Could not approve."); } }
  async function dispatchTransfer() { if (!detail) return; try { await api.post(`/material-transfers/${detail.id}/dispatch/`, { vehicle_details: detail.vehicle_details, waybill_number: detail.waybill_number }); toast.success("Dispatched", "Materials are now in transit. Source stock deducted."); await openDetail(detail.id); await loadDashboard(); } catch (err) { if (err instanceof ApiError) toast.error("Failed", err.data?.detail || "Cannot dispatch."); } }
  async function confirmReceipt() {
    if (!detail) return;
    try {
      const lines = detail.lines.map(l => ({ line_id: l.id, received_quantity: Number(l.quantity) }));
      await api.post(`/material-transfers/${detail.id}/confirm-receipt/`, { lines });
      toast.success("Confirmed", "Receipt confirmed. Destination stock updated.");
      await openDetail(detail.id); await loadDashboard();
    } catch (err) { if (err instanceof ApiError) toast.error("Failed", err.data?.detail || "Cannot confirm."); }
  }

  function devFill() {
    if (warehouses.length >= 2) { createForm.source_warehouse = String(warehouses[0].id); createForm.destination_warehouse = String(warehouses[1].id); }
    if (projects.length) createForm.project = String(projects[Math.floor(Math.random() * projects.length)].id);
    createForm.reason = ["Surplus rebar from completed project", "Urgent material need at new site", "Centralize slow-moving stock", "Inter-site balancing"][Math.floor(Math.random() * 4)];
    createForm.priority = ["normal", "high", "urgent"][Math.floor(Math.random() * 3)];
    createForm.scheduled_date = new Date(Date.now() + (Math.floor(Math.random() * 5) + 1) * 86400000).toISOString().split("T")[0];
    createForm.vehicle_details = `Truck ${String.fromCharCode(65 + Math.floor(Math.random() * 5))} — ${["Lagos", "Abuja", "PH"][Math.floor(Math.random() * 3)]}`;
    createForm.reason_category = ["surplus_redistribution", "central_procurement", "project_closure", "site_demand", "stock_balancing"][Math.floor(Math.random() * 5)];
    createForm.driver_name = ["Ibrahim Musa", "Chinedu Okafor", "Tunde Bakare", "Emeka Uche"][Math.floor(Math.random() * 4)];
    createForm.vehicle_plate = `${["LAG", "ABJ", "PH", "KD"][Math.floor(Math.random() * 4)]}-${Math.floor(Math.random() * 900 + 100)}${String.fromCharCode(65 + Math.floor(Math.random() * 26))}${String.fromCharCode(65 + Math.floor(Math.random() * 26))}`;
    createForm.gate_pass_id = `GP-${Math.floor(Math.random() * 9000 + 1000)}`;
    createLines = [];
    const count = Math.floor(Math.random() * 3) + 2;
    for (let i = 0; i < count && i < items.length; i++) {
      const item = items[Math.floor(Math.random() * items.length)];
      createLines.push({ item: String(item.id), quantity: String(Math.floor(Math.random() * 100 + 10)), unit_of_measure: "ea", available_stock: "—", stock_status: "" });
    }
  }

  onMount(() => { loadDashboard(); });
</script>

<svelte:head><title>Material Transfers | developerOS</title></svelte:head>

<div class="space-y-5">
  <div class="flex items-start justify-between gap-3">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-pink-600">Material Management</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Material Transfers</h1>
      <p class="mt-1 text-sm text-neutral-500">Inter-warehouse logistics — track value in motion between sites.</p>
    </div>
    <button onclick={() => { showCreate = true; if (createLines.length === 0) createLines.push({
       item: "", quantity: "1", unit_of_measure: "ea",
       available_stock: "",
       stock_status: ""
     }); }} class="rounded-lg bg-linear-to-r from-pink-600 to-rose-600 px-4 py-2.5 text-sm font-semibold text-white hover:from-pink-700 hover:to-rose-700 shadow-lg">+ New Transfer</button>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-20"><div class="h-7 w-7 rounded-full border-2 border-neutral-200 border-t-neutral-900 animate-spin"></div></div>
  {:else if data}

    <!-- Logistics Control Tower HUD -->
    <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <div class="rounded-xl border-2 border-violet-300 bg-linear-to-br from-violet-50 to-indigo-50 p-4 text-center" style="backdrop-filter: blur(10px)">
        <p class="text-[9px] font-bold text-violet-500 uppercase tracking-wider">In Transit</p>
        <p class="mt-1 text-xl font-black text-violet-800 tabular-nums">{currency.format(Number(data.in_transit_value))}</p>
        <p class="text-[9px] text-violet-400">{data.in_transit_count} shipment(s) moving</p>
      </div>
      <div class="rounded-xl border-2 {data.pending_receipts > 0 ? 'border-amber-300 bg-linear-to-br from-amber-50 to-orange-50' : 'border-neutral-200 bg-white'} p-4 text-center {data.pending_receipts > 0 ? 'animate-pulse' : ''}" style="backdrop-filter: blur(10px)">
        <p class="text-[9px] font-bold {data.pending_receipts > 0 ? 'text-amber-500' : 'text-neutral-400'} uppercase tracking-wider">Pending Receipts</p>
        <p class="mt-1 text-2xl font-black {data.pending_receipts > 0 ? 'text-amber-700' : 'text-neutral-900'} tabular-nums">{data.pending_receipts}</p>
        <p class="text-[9px] {data.pending_receipts > 0 ? 'text-amber-400' : 'text-neutral-400'}">awaiting confirmation</p>
      </div>
      <div class="rounded-xl border-2 border-cyan-200 bg-linear-to-br from-cyan-50 to-sky-50 p-4 text-center" style="backdrop-filter: blur(10px)">
        <p class="text-[9px] font-bold text-cyan-500 uppercase tracking-wider">Active Routes</p>
        <p class="mt-1 text-2xl font-black text-cyan-800 tabular-nums">{data.active_routes.length}</p>
        <p class="text-[9px] text-cyan-400">source → destination</p>
      </div>
      <div class="rounded-xl border-2 border-emerald-200 bg-linear-to-br from-emerald-50 to-teal-50 p-4 text-center" style="backdrop-filter: blur(10px)">
        <p class="text-[9px] font-bold text-emerald-500 uppercase tracking-wider">Today's Fleet</p>
        <p class="mt-1 text-2xl font-black text-emerald-800 tabular-nums">{data.todays_transfers}</p>
        <p class="text-[9px] text-emerald-400">scheduled today</p>
      </div>
    </div>

    <!-- Active Routes -->
    {#if data.active_routes.length > 0}
      <div class="rounded-xl border-2 border-indigo-200 bg-linear-to-r from-indigo-50/80 to-violet-50/50 p-4" style="backdrop-filter: blur(12px)">
        <h3 class="text-[9px] font-black text-indigo-600 uppercase tracking-widest mb-3">Active Transit Routes</h3>
        <div class="flex flex-wrap gap-2">
          {#each data.active_routes as route}
            <div class="rounded-lg bg-white/80 border border-indigo-200 px-3 py-2 flex items-center gap-2 shadow-sm">
              <span class="text-xs font-bold text-indigo-900">{route.source}</span>
              <svg class="h-3.5 w-3.5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" /></svg>
              <span class="text-xs font-bold text-indigo-900">{route.destination}</span>
            </div>
          {/each}
        </div>
      </div>
    {/if}

    <!-- View Toggle + Filter + Table -->
    <section class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
      <div class="border-b border-neutral-100 bg-neutral-50 px-5 py-3 flex items-center justify-between flex-wrap gap-2">
        <div class="flex items-center gap-3">
          <div class="flex gap-1 rounded-lg bg-neutral-200/60 p-0.5">
            <button onclick={() => { viewMode = "orders"; }} class="rounded-md px-3 py-1.5 text-[10px] font-bold transition-colors {viewMode === 'orders' ? 'bg-white text-neutral-900 shadow-sm' : 'text-neutral-500'}">Orders</button>
            <button onclick={() => { viewMode = "ledger"; if (ledgerData.length === 0) loadLedger(); }} class="rounded-md px-3 py-1.5 text-[10px] font-bold transition-colors {viewMode === 'ledger' ? 'bg-white text-neutral-900 shadow-sm' : 'text-neutral-500'}">Ledger</button>
          </div>
          <h3 class="text-[10px] font-bold text-neutral-500 uppercase tracking-widest">{viewMode === "orders" ? `Transfer Orders (${filteredTransfers.length})` : `Transfer Ledger (${ledgerData.length} lines)`}</h3>
        </div>
        <div class="flex gap-1">
          {#each [["", "All"], ["requested", "Requested"], ["in_transit", "In Transit"], ["delivered", "Delivered"], ["received", "Received"]] as [val, label]}
            <button onclick={() => { statusFilter = val; }} class="rounded-md px-2.5 py-1 text-[9px] font-semibold transition-colors {statusFilter === val ? 'bg-neutral-900 text-white' : 'text-neutral-500 hover:bg-neutral-100'}">{label}</button>
          {/each}
        </div>
      </div>
      {#if viewMode === "ledger"}
        <!-- Transfer Ledger (Material-Level) -->
        {#if ledgerLoading}
          <div class="p-8 text-center text-sm text-neutral-400">Loading ledger...</div>
        {:else if ledgerData.length === 0}
          <div class="p-8 text-center text-sm text-neutral-400">No ledger entries. Create transfers to populate.</div>
        {:else}
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead><tr class="border-b border-neutral-200 bg-neutral-100/80">
                <th class="px-4 py-2.5 text-left text-[10px] font-black text-neutral-700 uppercase tracking-wider">TO Number</th>
                <th class="px-4 py-2.5 text-left text-[10px] font-black text-neutral-700 uppercase tracking-wider">Material</th>
                <th class="px-4 py-2.5 text-right text-[10px] font-black text-neutral-700 uppercase tracking-wider">Qty</th>
                <th class="px-4 py-2.5 text-left text-[10px] font-black text-neutral-700 uppercase tracking-wider">From</th>
                <th class="px-4 py-2.5 text-left text-[10px] font-black text-neutral-700 uppercase tracking-wider">To</th>
                <th class="px-4 py-2.5 text-center text-[10px] font-black text-neutral-700 uppercase tracking-wider">Dispatch Date</th>
                <th class="px-4 py-2.5 text-center text-[10px] font-black text-neutral-700 uppercase tracking-wider">Status</th>
                <th class="px-4 py-2.5 text-right text-[10px] font-black text-neutral-700 uppercase tracking-wider">Value</th>
              </tr></thead>
              <tbody class="divide-y divide-neutral-50">
                {#each ledgerData as row}
                  <tr class="cursor-pointer hover:bg-neutral-50 {row.status === 'in_transit' ? 'bg-amber-50/20' : row.status === 'received' ? 'bg-emerald-50/20' : ''}" onclick={() => openDetail(row.transfer_id)}>
                    <td class="px-4 py-3">
                      <span class="font-mono text-xs font-bold text-violet-700">{row.to_number}</span>
                    </td>
                    <td class="px-4 py-3">
                      <p class="font-bold text-neutral-900" style="font-family: Raleway, sans-serif;">{row.item_name}</p>
                      {#if row.item_sku}<p class="text-[9px] text-neutral-400 font-mono">{row.item_sku}</p>{/if}
                    </td>
                    <td class="px-4 py-3 text-right font-bold text-neutral-900 tabular-nums">{row.quantity}</td>
                    <td class="px-4 py-3">
                      <span class="rounded-md bg-neutral-100 border border-neutral-200 px-2 py-0.5 text-[10px] font-semibold text-neutral-700">{row.source}</span>
                    </td>
                    <td class="px-4 py-3">
                      <span class="rounded-md bg-indigo-50 border border-indigo-200 px-2 py-0.5 text-[10px] font-semibold text-indigo-700">{row.destination}</span>
                    </td>
                    <td class="px-4 py-3 text-center tabular-nums text-neutral-600">{row.dispatch_date || "—"}</td>
                    <td class="px-4 py-3 text-center">
                      <span class="rounded-full border px-2.5 py-0.5 text-[9px] font-bold {STATUS_COLORS[row.status] || ''}">{row.status.replace(/_/g, " ")}</span>
                    </td>
                    <td class="px-4 py-3 text-right font-bold text-emerald-700 tabular-nums">{currency.format(Number(row.value || 0))}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      {:else if filteredTransfers.length === 0}
        <div class="p-8 text-center text-sm text-neutral-400">No transfers found.</div>
      {:else}
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead><tr class="border-b border-neutral-200 bg-neutral-100/80">
              <th class="px-4 py-2.5 text-left text-[10px] font-black text-neutral-700 uppercase tracking-wider">TO #</th>
              <th class="px-4 py-2.5 text-left text-[10px] font-black text-neutral-700 uppercase tracking-wider">Route</th>
              <th class="px-4 py-2.5 text-center text-[10px] font-black text-neutral-700 uppercase tracking-wider">Progress</th>
              <th class="px-4 py-2.5 text-center text-[10px] font-black text-neutral-700 uppercase tracking-wider">Status</th>
              <th class="px-4 py-2.5 text-center text-[10px] font-black text-neutral-700 uppercase tracking-wider">Items</th>
              <th class="px-4 py-2.5 text-right text-[10px] font-black text-neutral-700 uppercase tracking-wider">Value</th>
              <th class="px-4 py-2.5 text-left text-[10px] font-black text-neutral-700 uppercase tracking-wider">Dispatch</th>
            </tr></thead>
            <tbody class="divide-y divide-neutral-50">
              {#each filteredTransfers as t}
                {@const progressPct = t.status === "received" ? 100 : t.status === "delivered" ? 90 : t.status === "in_transit" ? 55 : t.status === "approved" ? 20 : t.status === "requested" ? 10 : 0}
                <tr class="cursor-pointer transition-all {t.status === 'in_transit' ? '' : t.status === 'received' ? 'bg-emerald-50/30' : 'hover:bg-neutral-50'}"
                  style="{t.status === 'in_transit' ? 'background: rgba(191,219,254,0.15); box-shadow: inset 0 0 24px rgba(59,130,246,0.06);' : ''}"
                  onclick={() => openDetail(t.id)}>
                  <!-- TO Number (Bold) -->
                  <td class="px-4 py-3">
                    <span class="font-black text-neutral-900 tabular-nums" style="font-family: Raleway, sans-serif;">{t.transfer_number}</span>
                  </td>
                  <!-- Route -->
                  <td class="px-4 py-3">
                    <div class="flex items-center gap-1.5">
                      <span class="text-xs text-neutral-600">{t.source_name}</span>
                      <svg class="h-3 w-3 text-neutral-300 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" /></svg>
                      <span class="text-xs font-bold text-neutral-900">{t.destination_name}</span>
                    </div>
                  </td>
                  <!-- Progress Track with Truck -->
                  <td class="px-4 py-3">
                    <div class="relative h-5 w-24 mx-auto">
                      <!-- Track -->
                      <div class="absolute top-1/2 -translate-y-1/2 left-0 right-0 h-1 rounded-full {t.status === 'in_transit' ? 'bg-blue-100' : t.status === 'received' ? 'bg-emerald-100' : 'bg-neutral-100'}">
                        <div class="h-full rounded-full transition-all duration-700 {t.status === 'in_transit' ? 'bg-blue-400' : t.status === 'received' ? 'bg-emerald-500' : t.status === 'delivered' ? 'bg-cyan-400' : 'bg-neutral-300'}" style="width: {progressPct}%"></div>
                      </div>
                      <!-- Source dot -->
                      <div class="absolute top-1/2 -translate-y-1/2 left-0 h-2 w-2 rounded-full bg-neutral-400"></div>
                      <!-- Destination dot / checkmark -->
                      <div class="absolute top-1/2 -translate-y-1/2 right-0">
                        {#if t.status === "received"}
                          <div class="h-4 w-4 rounded-full bg-emerald-500 flex items-center justify-center">
                            <svg class="h-2.5 w-2.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" /></svg>
                          </div>
                        {:else}
                          <div class="h-2 w-2 rounded-full {t.status === 'delivered' ? 'bg-cyan-500' : 'bg-neutral-300'}"></div>
                        {/if}
                      </div>
                      <!-- Truck icon (slides based on progress) -->
                      {#if t.status === "in_transit"}
                        <div class="absolute top-1/2 -translate-y-1/2" style="left: calc({progressPct}% - 6px); transition: left 0.7s ease-out;">
                          <span class="text-[10px]" style="filter: drop-shadow(0 1px 2px rgba(59,130,246,0.3));">🚛</span>
                        </div>
                      {/if}
                    </div>
                  </td>
                  <!-- Status -->
                  <td class="px-4 py-3 text-center">
                    {#if t.status === "received"}
                      <span class="inline-flex items-center gap-1 rounded-full bg-emerald-100 border border-emerald-300 px-2.5 py-1 text-[9px] font-black text-emerald-700">
                        <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" /></svg>
                        Delivered
                      </span>
                    {:else if t.status === "in_transit"}
                      <span class="inline-flex items-center gap-1 rounded-full bg-blue-100 border border-blue-300 px-2.5 py-1 text-[9px] font-black text-blue-700 animate-pulse">
                        In Transit
                      </span>
                    {:else}
                      <span class="rounded-full border px-2.5 py-1 text-[9px] font-bold {STATUS_COLORS[t.status] || ''}">{t.status.replace(/_/g, " ")}</span>
                    {/if}
                  </td>
                  <!-- Items (Bold) -->
                  <td class="px-4 py-3 text-center font-black tabular-nums text-neutral-900">{t.line_count}</td>
                  <!-- Value (Bold) -->
                  <td class="px-4 py-3 text-right font-black text-emerald-700 tabular-nums">{currency.format(Number(t.total_value || 0))}</td>
                  <!-- Dispatch (Light) -->
                  <td class="px-4 py-3">
                    <p class="text-xs text-neutral-500 tabular-nums" style="font-family: Raleway, sans-serif; font-weight: 300;">{t.dispatched_date || t.scheduled_date || "—"}</p>
                    {#if t.vehicle_details}<p class="text-[9px] text-neutral-400" style="font-weight: 300;">{t.vehicle_details}</p>{/if}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </section>
  {/if}
</div>

<!-- Detail Drawer -->
{#if showDetail && detail}
  <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <div class="fixed inset-0 z-50 flex justify-end bg-black/40" style="backdrop-filter: blur(8px)" onclick={() => { showDetail = false; detail = null; }}>
    <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
    <div class="w-full max-w-2xl bg-white shadow-2xl overflow-y-auto" onclick={(e) => e.stopPropagation()}>
      <div class="bg-linear-to-r from-violet-700 to-indigo-700 px-5 py-4 flex items-start justify-between sticky top-0 z-10">
        <div>
          <h2 class="text-lg font-bold text-white">{detail.transfer_number}</h2>
          <p class="text-sm text-violet-200 mt-0.5">{detail.source_name} → {detail.destination_name}</p>
          <div class="flex gap-2 mt-2">
            <span class="rounded-full bg-white/20 border border-white/30 px-2.5 py-0.5 text-[10px] font-bold text-white">{detail.status.replace(/_/g, " ")}</span>
            <span class="rounded-full bg-white/20 border border-white/30 px-2.5 py-0.5 text-[10px] font-bold text-white capitalize">{detail.priority}</span>
          </div>
        </div>
        <div class="flex items-center gap-2">
          {#if detail.status === "requested"}<button onclick={approveTransfer} class="rounded-lg bg-emerald-500 px-3 py-1.5 text-xs font-bold text-white hover:bg-emerald-600">Approve</button>{/if}
          {#if detail.status === "approved"}<button onclick={dispatchTransfer} class="rounded-lg bg-amber-500 px-3 py-1.5 text-xs font-bold text-white hover:bg-amber-600">Dispatch</button>{/if}
          {#if detail.status !== "draft"}
            <button onclick={() => { if (detail) openWaybill(detail.id); }} class="rounded-lg border border-white/30 px-3 py-1.5 text-xs font-semibold text-white/80 hover:bg-white/10">Waybill</button>
          {/if}
          {#if detail.status === "in_transit" || detail.status === "delivered"}<button onclick={() => { if (detail) openReceiving(detail); }} class="rounded-lg bg-emerald-500 px-3 py-1.5 text-xs font-bold text-white hover:bg-emerald-600">Check-In</button>{/if}
          <button onclick={() => { showDetail = false; detail = null; }} class="rounded-lg p-1.5 text-white/70 hover:bg-white/20" aria-label="Close">
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
          </button>
        </div>
      </div>

      {#if detailLoading}
        <div class="p-12 text-center text-sm text-neutral-400">Loading...</div>
      {:else}
        <div class="p-5 space-y-4">
          <div class="grid grid-cols-2 gap-3 sm:grid-cols-4 text-xs">
            <div><span class="text-[9px] text-neutral-400 uppercase font-bold block">Requested By</span><span class="text-neutral-900">{detail.requested_by_name}</span></div>
            <div><span class="text-[9px] text-neutral-400 uppercase font-bold block">Approved By</span><span class="text-neutral-900">{detail.approved_by || "—"}</span></div>
            <div><span class="text-[9px] text-neutral-400 uppercase font-bold block">Vehicle</span><span class="text-neutral-900">{detail.vehicle_details || "—"}</span></div>
            <div><span class="text-[9px] text-neutral-400 uppercase font-bold block">Waybill</span><span class="text-neutral-900">{detail.waybill_number || "—"}</span></div>
          </div>
          {#if detail.reason}<div><p class="text-[9px] text-neutral-400 uppercase font-bold mb-1">Reason</p><p class="text-sm text-neutral-700">{detail.reason}</p></div>{/if}

          <!-- Vertical Transfer Tracker -->
          <div class="rounded-xl border-2 border-neutral-200 bg-linear-to-b from-neutral-50 to-white p-4">
            <h4 class="text-[9px] font-black text-neutral-500 uppercase tracking-widest mb-3">Transfer Lifecycle</h4>
            <div class="space-y-0">
              {#each [
                { label: "Requested", icon: "📋", value: detail.created_at, detail: `By ${detail.requested_by_name}`, date: detail.created_at ? new Date(detail.created_at).toLocaleDateString() : "" },
                { label: "Approved", icon: "✅", value: detail.approved_by, detail: detail.approved_by ? `By ${detail.approved_by}` : "", date: "" },
                { label: "Dispatched", icon: "🚛", value: detail.dispatched_date, detail: detail.vehicle_details ? `Vehicle: ${detail.vehicle_details}` : "", date: detail.dispatched_date || "" },
                { label: "In Transit", icon: "📦", value: detail.status === "in_transit" || detail.dispatched_date ? "yes" : "", detail: detail.waybill_number ? `Waybill: ${detail.waybill_number}` : "", date: "" },
                { label: "Received", icon: "🏁", value: detail.confirmed_date, detail: detail.received_by ? `By ${detail.received_by}` : "", date: detail.confirmed_date || "" },
              ] as step, i}
                {@const done = !!step.value}
                {@const isCurrent = done && i < 4 && !([
                  { label: "Requested", value: detail.created_at },
                  { label: "Approved", value: detail.approved_by },
                  { label: "Dispatched", value: detail.dispatched_date },
                  { label: "In Transit", value: detail.status === "in_transit" ? "yes" : "" },
                  { label: "Received", value: detail.confirmed_date },
                ][i + 1]?.value)}
                <div class="flex gap-3">
                  <!-- Vertical line + dot -->
                  <div class="flex flex-col items-center">
                    <div class="flex items-center justify-center h-8 w-8 rounded-full shrink-0 {done ? isCurrent ? 'bg-linear-to-br from-violet-500 to-indigo-600 text-white shadow-lg ring-4 ring-violet-100' : 'bg-emerald-500 text-white' : 'bg-neutral-200 text-neutral-400'}">
                      {#if done && !isCurrent}
                        <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" /></svg>
                      {:else}
                        <span class="text-sm">{step.icon}</span>
                      {/if}
                    </div>
                    {#if i < 4}
                      <div class="w-0.5 h-6 {done ? 'bg-emerald-300' : 'bg-neutral-200'}"></div>
                    {/if}
                  </div>
                  <!-- Content -->
                  <div class="pt-1 pb-2 min-w-0">
                    <p class="text-xs font-black {done ? isCurrent ? 'text-violet-700' : 'text-emerald-700' : 'text-neutral-400'}">{step.label}</p>
                    {#if step.detail && done}
                      <p class="text-[10px] text-neutral-500 mt-0.5" style="font-weight: 300;">{step.detail}</p>
                    {/if}
                    {#if step.date && done}
                      <p class="text-[9px] text-neutral-400 tabular-nums">{step.date}</p>
                    {/if}
                  </div>
                </div>
              {/each}
            </div>
          </div>

          <!-- Lines -->
          <div class="rounded-lg border border-neutral-200 overflow-hidden">
            <table class="w-full text-sm">
              <thead><tr class="border-b border-neutral-100 bg-neutral-50">
                <th class="px-3 py-2 text-left text-[9px] font-bold text-neutral-500 uppercase">Material</th>
                <th class="px-3 py-2 text-center text-[9px] font-bold text-neutral-500 uppercase">Qty</th>
                <th class="px-3 py-2 text-center text-[9px] font-bold text-neutral-500 uppercase">Received</th>
                <th class="px-3 py-2 text-right text-[9px] font-bold text-neutral-500 uppercase">Value</th>
              </tr></thead>
              <tbody class="divide-y divide-neutral-50">
                {#each detail.lines as line}
                  {@const sent = Number(line.quantity)}
                  {@const received = Number(line.received_quantity)}
                  {@const isMatch = received >= sent}
                  {@const isShort = received > 0 && received < sent}
                  <tr class="{isShort ? 'bg-amber-50/30' : isMatch && received > 0 ? 'bg-emerald-50/20' : ''}">
                    <td class="px-3 py-2.5">
                      <p class="font-black text-neutral-900" style="font-family: Raleway, sans-serif;">{line.item_name}</p>
                      <p class="text-[9px] text-neutral-400 font-mono">{line.item_sku}</p>
                    </td>
                    <td class="px-3 py-2.5 text-center font-black tabular-nums text-neutral-900">{line.quantity} <span class="text-neutral-400 text-[9px] font-normal">{line.unit_of_measure}</span></td>
                    <td class="px-3 py-2.5 text-center tabular-nums">
                      {#if received > 0}
                        <span class="font-black {isMatch ? 'text-emerald-700' : 'text-amber-700'}">{line.received_quantity}</span>
                        {#if isMatch}
                          <span class="inline-block ml-1 text-emerald-500"><svg class="h-3 w-3 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" /></svg></span>
                        {:else if isShort}
                          <span class="block text-[8px] font-bold text-amber-600">-{(sent - received).toFixed(1)} short</span>
                        {/if}
                      {:else}
                        <span class="text-neutral-300">—</span>
                      {/if}
                    </td>
                    <td class="px-3 py-2.5 text-right font-black text-emerald-700 tabular-nums">{currency.format(Number(line.line_value))}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>

          <!-- Total -->
          <div class="rounded-xl bg-linear-to-r from-violet-50 to-indigo-50 border-2 border-violet-200 p-4 flex items-center justify-between">
            <span class="text-xs font-black text-violet-600 uppercase">Total Transfer Value</span>
            <span class="text-xl font-black text-violet-800 tabular-nums">{currency.format(Number(detail.total_value || 0))}</span>
          </div>
        </div>
      {/if}
    </div>
  </div>
{/if}

<!-- Create Modal -->
{#if showCreate}
  <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" style="backdrop-filter: blur(15px)" onclick={() => { showCreate = false; }}>
    <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
    <div class="w-full max-w-2xl max-h-[90vh] rounded-2xl bg-white shadow-2xl overflow-y-auto" onclick={(e) => e.stopPropagation()}>
      <div class="px-6 py-4 border-b border-neutral-100 bg-linear-to-r from-violet-50 to-indigo-50">
        <h2 class="text-base font-bold text-neutral-900">New Material Transfer</h2>
        <p class="text-xs text-neutral-500 mt-0.5">Move materials between warehouses or sites.</p>
      </div>
      <div class="p-6 space-y-4">
        <!-- Source & Destination -->
        <div class="grid grid-cols-2 gap-3">
          <label class="block text-sm"><span class="mb-1 block text-xs font-bold text-neutral-700">Source Warehouse *</span>
            <select bind:value={createForm.source_warehouse} onchange={onSourceChange} class="w-full rounded-lg border-2 border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-violet-400">
              <option value="">Select source</option>
              {#each warehouses as w}<option value={String(w.id)}>{w.name}</option>{/each}
            </select>
          </label>
          <label class="block text-sm"><span class="mb-1 block text-xs font-bold text-neutral-700">Destination Warehouse *</span>
            <select bind:value={createForm.destination_warehouse} class="w-full rounded-lg border-2 border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-violet-400">
              <option value="">Select destination</option>
              {#each warehouses.filter(w => String(w.id) !== createForm.source_warehouse) as w}<option value={String(w.id)}>{w.name}</option>{/each}
            </select>
          </label>
        </div>

        <!-- Route Visual -->
        {#if createForm.source_warehouse && createForm.destination_warehouse}
          {@const srcName = warehouses.find(w => String(w.id) === createForm.source_warehouse)?.name || ""}
          {@const dstName = warehouses.find(w => String(w.id) === createForm.destination_warehouse)?.name || ""}
          <div class="rounded-xl bg-linear-to-r from-violet-50 to-indigo-50 border-2 border-violet-200 p-3 flex items-center justify-center gap-3">
            <span class="rounded-lg bg-white border border-violet-200 px-3 py-1.5 text-xs font-bold text-violet-800 shadow-sm">{srcName}</span>
            <svg class="h-5 w-5 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" /></svg>
            <span class="rounded-lg bg-indigo-100 border border-indigo-300 px-3 py-1.5 text-xs font-bold text-indigo-800 shadow-sm">{dstName}</span>
          </div>
        {/if}

        <div class="grid grid-cols-3 gap-3">
          <label class="block text-sm"><span class="mb-1 block text-xs font-bold text-neutral-700">Project</span>
            <select bind:value={createForm.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500">
              <option value="">No project</option>
              {#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}
            </select>
          </label>
          <label class="block text-sm"><span class="mb-1 block text-xs font-bold text-neutral-700">Priority</span>
            <select bind:value={createForm.priority} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500">
              <option value="low">Low</option><option value="normal">Normal</option><option value="high">High</option><option value="urgent">Urgent</option>
            </select>
          </label>
          <label class="block text-sm"><span class="mb-1 block text-xs font-bold text-neutral-700">Scheduled Date</span>
            <input type="date" bind:value={createForm.scheduled_date} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500" />
          </label>
        </div>

        <!-- Transfer Reason (categorized) -->
        <div>
          <span class="mb-2 block text-xs font-bold text-neutral-700">Transfer Reason *</span>
          <div class="grid grid-cols-4 gap-1.5 mb-2">
            {#each REASON_CATEGORIES as cat}
              <button type="button" onclick={() => { createForm.reason_category = cat.value; }}
                class="rounded-lg border-2 py-2 text-center transition-all {createForm.reason_category === cat.value ? 'border-violet-500 bg-violet-50 shadow-md' : 'border-neutral-200 hover:border-neutral-300'}">
                <span class="text-sm">{cat.icon}</span>
                <p class="text-[8px] font-bold mt-0.5 {createForm.reason_category === cat.value ? 'text-violet-700' : 'text-neutral-500'}">{cat.label}</p>
              </button>
            {/each}
          </div>
          <input type="text" bind:value={createForm.reason} placeholder="Additional details..." class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500" />
        </div>

        <!-- Dispatch Details -->
        <div class="rounded-xl border-2 border-cyan-200 bg-linear-to-br from-cyan-50 to-sky-50 p-4 space-y-3">
          <h4 class="text-[10px] font-black text-cyan-700 uppercase tracking-widest">Dispatch Details</h4>
          <div class="grid grid-cols-3 gap-3">
            <label class="block text-sm"><span class="mb-1 block text-[9px] font-bold text-cyan-600">Driver Name</span>
              <input type="text" bind:value={createForm.driver_name} placeholder="Ibrahim Musa" class="w-full rounded-lg border border-cyan-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500" />
            </label>
            <label class="block text-sm"><span class="mb-1 block text-[9px] font-bold text-cyan-600">Vehicle Plate</span>
              <input type="text" bind:value={createForm.vehicle_plate} placeholder="LAG-234AB" class="w-full rounded-lg border border-cyan-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500" />
            </label>
            <label class="block text-sm"><span class="mb-1 block text-[9px] font-bold text-cyan-600">Gate Pass ID</span>
              <input type="text" bind:value={createForm.gate_pass_id} placeholder="GP-1234" class="w-full rounded-lg border border-cyan-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500" />
            </label>
          </div>
        </div>

        <!-- Material Lines with Stock Check -->
        <div>
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-[10px] font-black text-neutral-500 uppercase tracking-widest">Materials ({createLines.length})</h3>
            <button type="button" onclick={() => { createLines = [...createLines, { item: "", quantity: "1", unit_of_measure: "ea", available_stock: "—", stock_status: "" }]; }} class="rounded-md bg-neutral-900 px-2.5 py-1 text-[10px] font-bold text-white hover:bg-neutral-800">+ Add</button>
          </div>
          <div class="space-y-2">
            {#each createLines as line, i}
              <div class="rounded-lg border-2 p-3 {line.stock_status === 'none' ? 'border-red-300 bg-red-50/30' : line.stock_status === 'insufficient' ? 'border-amber-300 bg-amber-50/30' : 'border-neutral-200'}">
                <div class="flex gap-2 items-end">
                  <label class="flex-1 text-sm"><span class="mb-1 block text-[9px] font-bold text-neutral-500">Material *</span>
                    <select bind:value={line.item} onchange={() => checkTransferStock(i)} class="w-full rounded-lg border border-neutral-200 bg-white px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-violet-500">
                      <option value="">Select</option>
                      {#each items as item}<option value={String(item.id)}>{item.sku} — {item.name}</option>{/each}
                    </select>
                  </label>
                  <label class="w-20 text-sm"><span class="mb-1 block text-[9px] font-bold text-neutral-500">Qty *</span>
                    <input type="number" step="0.01" min="1" bind:value={line.quantity} onchange={() => checkTransferStock(i)} class="w-full rounded-lg border border-neutral-200 px-2 py-1.5 text-xs tabular-nums focus:outline-none focus:ring-2 focus:ring-violet-500" />
                  </label>
                  <!-- Stock indicator -->
                  <div class="w-20 text-center mb-0.5">
                    {#if line.stock_status === "sufficient"}
                      <span class="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-1 text-[9px] font-bold text-emerald-700">
                        <span class="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>{line.available_stock}
                      </span>
                    {:else if line.stock_status === "insufficient"}
                      <span class="inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-1 text-[9px] font-bold text-amber-700">
                        <span class="h-1.5 w-1.5 rounded-full bg-amber-500"></span>{line.available_stock}
                      </span>
                    {:else if line.stock_status === "none"}
                      <span class="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-1 text-[9px] font-bold text-red-700">
                        <span class="h-1.5 w-1.5 rounded-full bg-red-500"></span>0
                      </span>
                    {:else}
                      <span class="text-[9px] text-neutral-300">Stock</span>
                    {/if}
                  </div>
                  <!-- svelte-ignore a11y_consider_explicit_label -->
                  <button type="button" onclick={() => { createLines = createLines.filter((_, idx) => idx !== i); }} class="rounded-md p-1.5 text-neutral-400 hover:text-red-500 mb-0.5">
                    <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
                  </button>
                </div>
                {#if line.stock_status === "none"}
                  <p class="text-[9px] text-red-600 font-bold mt-1">No stock at source warehouse. Transfer cannot proceed for this item.</p>
                {:else if line.stock_status === "insufficient"}
                  <p class="text-[9px] text-amber-600 font-bold mt-1">Only {line.available_stock} available — requested {line.quantity}. Transfer may be partially fulfilled.</p>
                {/if}
              </div>
            {/each}
          </div>
        </div>
      </div>
      <div class="px-6 py-4 border-t border-neutral-100 flex justify-end gap-3">
        {#if isDev}<button type="button" onclick={devFill} class="mr-auto rounded-lg bg-orange-500 px-3 py-2 text-xs font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
        <button onclick={() => { showCreate = false; }} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
        <button onclick={createTransfer} disabled={createSaving} class="rounded-lg bg-linear-to-r from-violet-600 to-indigo-600 px-4 py-2.5 text-sm font-bold text-white hover:from-violet-700 hover:to-indigo-700 disabled:opacity-50 shadow-md">{createSaving ? "Creating..." : "Create Transfer"}</button>
      </div>
    </div>
  </div>
{/if}

<!-- Receiving Confirmation ("The Handshake") -->
{#if showReceiving && receivingTransfer}
  <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <div class="fixed inset-0 z-60 flex justify-end bg-black/50" style="backdrop-filter: blur(15px)" onclick={() => { showReceiving = false; }}>
    <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
    <div class="w-full max-w-xl bg-white/95 shadow-2xl overflow-y-auto" style="backdrop-filter: blur(20px); border-left: 1px solid rgba(200,200,200,0.3);" onclick={(e) => e.stopPropagation()}>
      <!-- Header -->
      <div class="bg-linear-to-r from-emerald-600 via-teal-600 to-cyan-600 px-6 py-5">
        <div class="flex items-start justify-between">
          <div>
            <p class="text-[10px] font-bold text-emerald-100 uppercase tracking-widest">Receiving Confirmation</p>
            <h2 class="text-lg font-black text-white mt-1">{receivingTransfer.transfer_number}</h2>
            <p class="text-sm text-emerald-100 mt-1">{receivingTransfer.source_name} → {receivingTransfer.destination_name}</p>
            {#if receivingTransfer.vehicle_details}
              <p class="text-xs text-emerald-200 mt-1">🚛 {receivingTransfer.vehicle_details}</p>
            {/if}
          </div>
          <button onclick={() => { showReceiving = false; }} class="rounded-lg p-1.5 text-white/70 hover:bg-white/20" aria-label="Close">
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
          </button>
        </div>
      </div>

      <div class="p-6 space-y-5">
        <!-- Check-In Summary -->
        <div class="rounded-xl bg-linear-to-r from-emerald-50 to-teal-50 border-2 border-emerald-200 p-4">
          <div class="grid grid-cols-3 gap-3 text-center">
            <div>
              <p class="text-[8px] font-bold text-emerald-500 uppercase">Expected</p>
              <p class="text-xl font-black text-emerald-800 tabular-nums">{receivingLines.length}</p>
              <p class="text-[9px] text-emerald-400">line items</p>
            </div>
            <div>
              <p class="text-[8px] font-bold {receivingLines.some(l => Number(l.received) < Number(l.expected)) ? 'text-amber-500' : 'text-emerald-500'} uppercase">Shortfalls</p>
              <p class="text-xl font-black {receivingLines.some(l => Number(l.received) < Number(l.expected)) ? 'text-amber-700' : 'text-emerald-800'} tabular-nums">{receivingLines.filter(l => Number(l.received) < Number(l.expected)).length}</p>
              <p class="text-[9px] text-neutral-400">items short</p>
            </div>
            <div>
              <p class="text-[8px] font-bold {receivingLines.some(l => l.condition === 'damaged') ? 'text-red-500' : 'text-emerald-500'} uppercase">Damaged</p>
              <p class="text-xl font-black {receivingLines.some(l => l.condition === 'damaged') ? 'text-red-700' : 'text-emerald-800'} tabular-nums">{receivingLines.filter(l => l.condition === "damaged").length}</p>
              <p class="text-[9px] text-neutral-400">items</p>
            </div>
          </div>
        </div>

        <!-- Material Lines -->
        <div class="space-y-3">
          {#each receivingLines as line, i}
            {@const isShort = Number(line.received) < Number(line.expected)}
            {@const isDamaged = line.condition === "damaged"}
            <div class="rounded-xl border-2 transition-colors {isDamaged ? 'border-red-300 bg-red-50/30' : isShort ? 'border-amber-300 bg-amber-50/20' : 'border-neutral-200 bg-white'} p-4">
              <!-- Item header -->
              <div class="flex items-start justify-between mb-3">
                <div>
                  <p class="font-bold text-neutral-900" style="font-family: Raleway, sans-serif;">{line.item_name}</p>
                  <p class="text-[9px] text-neutral-400 font-mono">{line.item_sku}</p>
                </div>
                <span class="text-xs font-semibold text-neutral-500">Expected: <span class="font-black text-neutral-900">{line.expected}</span> {line.unit}</span>
              </div>

              <!-- Quantity Received -->
              <div class="grid grid-cols-2 gap-3 mb-3">
                <label class="block">
                  <span class="text-[9px] font-bold {isShort ? 'text-amber-600' : 'text-emerald-600'} uppercase mb-1 block">Actual Received *</span>
                  <input type="number" step="0.01" min="0" max={line.expected} bind:value={line.received}
                    class="w-full rounded-lg border-2 {isShort ? 'border-amber-400 bg-amber-50 shadow-[0_0_8px_rgba(245,158,11,0.15)]' : 'border-emerald-300 bg-emerald-50'} px-3 py-2.5 text-base font-black tabular-nums focus:outline-none focus:ring-2 {isShort ? 'focus:ring-amber-500' : 'focus:ring-emerald-500'}" />
                  {#if isShort}
                    <p class="text-[9px] text-amber-600 font-bold mt-1">Shortfall: {(Number(line.expected) - Number(line.received)).toFixed(1)} {line.unit} missing</p>
                  {/if}
                </label>

                <!-- Condition Toggle -->
                <div>
                  <span class="text-[9px] font-bold text-neutral-500 uppercase mb-1 block">Condition</span>
                  <div class="flex gap-1">
                    <button type="button" onclick={() => { line.condition = "good"; line.damage_notes = ""; receivingLines = [...receivingLines]; }}
                      class="flex-1 rounded-lg border-2 py-2.5 text-xs font-bold text-center transition-all {line.condition === 'good' ? 'border-emerald-500 bg-emerald-500 text-white shadow-lg' : 'border-neutral-200 text-neutral-500 hover:border-emerald-200'}">
                      ✓ Good
                    </button>
                    <button type="button" onclick={() => { line.condition = "damaged"; receivingLines = [...receivingLines]; }}
                      class="flex-1 rounded-lg border-2 py-2.5 text-xs font-bold text-center transition-all {line.condition === 'damaged' ? 'border-red-500 bg-red-500 text-white shadow-lg' : 'border-neutral-200 text-neutral-500 hover:border-red-200'}">
                      ✕ Damaged
                    </button>
                  </div>
                </div>
              </div>

              <!-- Damage Notes (mandatory if damaged) -->
              {#if isDamaged}
                <div class="mt-2">
                  <span class="text-[9px] font-bold text-red-500 uppercase mb-1 block">Damage Report *</span>
                  <textarea bind:value={line.damage_notes} rows="2" placeholder="Describe damage: torn bags, broken items, water damage..."
                    class="w-full rounded-lg border-2 border-red-300 bg-red-50/50 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-500 resize-none" style="font-family: Raleway, sans-serif; font-weight: 300;"></textarea>
                </div>
              {/if}
            </div>
          {/each}
        </div>

        <!-- Digital Sign-off -->
        <div class="rounded-xl border-2 {receivingSignature ? 'border-emerald-300 bg-linear-to-br from-emerald-50 to-teal-50' : 'border-neutral-200 bg-neutral-50'} p-4 transition-colors">
          <label class="flex items-start gap-3 cursor-pointer">
            <input type="checkbox" bind:checked={receivingSignature}
              class="mt-0.5 h-5 w-5 rounded border-2 {receivingSignature ? 'border-emerald-500 text-emerald-600' : 'border-neutral-300'} focus:ring-emerald-500" />
            <div>
              <p class="text-sm font-bold {receivingSignature ? 'text-emerald-800' : 'text-neutral-700'}">Digital Sign-Off</p>
              <p class="text-[10px] {receivingSignature ? 'text-emerald-600' : 'text-neutral-400'} mt-0.5">
                I confirm that I have physically verified the quantities and conditions listed above. This receipt will update inventory balances at both source and destination.
              </p>
            </div>
          </label>
        </div>

        <!-- Submit -->
        <div class="sticky bottom-0 bg-white/95 border-t border-neutral-100 -mx-6 px-6 py-4 flex gap-3" style="backdrop-filter: blur(10px)">
          <button onclick={() => { showReceiving = false; }} class="flex-1 rounded-xl border-2 border-neutral-200 py-3 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
          <button onclick={submitReceiving} disabled={receivingSaving || !receivingSignature}
            class="flex-1 rounded-xl py-3 text-sm font-black text-white shadow-lg transition-all disabled:opacity-40 {receivingSignature ? 'bg-linear-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600' : 'bg-neutral-300'}">
            {receivingSaving ? "Confirming..." : "✓ Confirm Receipt"}
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}

<!-- Waybill Document -->
{#if showWaybill}
  <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <div class="fixed inset-0 z-70 flex items-center justify-center bg-black/50 p-4" style="backdrop-filter: blur(12px)" onclick={() => { showWaybill = false; waybillData = null; }}>
    <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
    <div class="w-full max-w-3xl max-h-[90vh] rounded-2xl bg-white/95 shadow-2xl overflow-hidden flex flex-col" style="border: 1px solid rgba(200,200,200,0.4); backdrop-filter: blur(15px);" onclick={(e) => e.stopPropagation()}>
      <!-- Header -->
      <div class="bg-neutral-900 px-6 py-4 flex items-center justify-between shrink-0">
        <div>
          <h2 class="text-lg font-bold text-white">Waybill</h2>
          {#if waybillData}<p class="text-xs text-neutral-400 mt-0.5">{waybillData.waybill_number}</p>{/if}
        </div>
        <div class="flex items-center gap-2">
          {#if waybillData}
            <button onclick={printWaybill} class="rounded-lg bg-emerald-600 px-4 py-1.5 text-xs font-bold text-white hover:bg-emerald-700">Print / PDF</button>
          {/if}
          <button onclick={() => { showWaybill = false; waybillData = null; }} class="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-800 hover:text-white" aria-label="Close">
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
          </button>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto p-6">
        {#if waybillLoading}
          <div class="py-16 text-center text-sm text-neutral-400">Generating waybill...</div>
        {:else if waybillData}
          <div id="waybill-print">
            <!-- Document Header -->
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; border-bottom: 2px solid #171717; padding-bottom: 16px;">
              <div>
                <p style="font-size: 22px; font-weight: 900; color: #171717; letter-spacing: -0.5px;">WAYBILL</p>
                <p style="font-size: 11px; color: #737373; margin-top: 2px;">Material Transfer Document</p>
                <p style="font-size: 12px; font-weight: 700; color: #171717; margin-top: 6px;">{waybillData.org_name}</p>
              </div>
              <div style="text-align: right;">
                <p style="font-size: 14px; font-weight: 900; color: #171717; font-family: monospace;">{waybillData.waybill_number}</p>
                <!-- QR Code placeholder -->
                <div class="qr" style="width: 80px; height: 80px; border: 2px solid #171717; border-radius: 8px; display: flex; flex-direction: column; align-items: center; justify-content: center; font-family: monospace; font-size: 8px; word-break: break-all; padding: 4px; margin-top: 8px; margin-left: auto; background: #fafafa;">
                  <svg viewBox="0 0 40 40" width="40" height="40">
                    <rect x="0" y="0" width="12" height="12" fill="#171717" rx="2"/><rect x="14" y="0" width="4" height="4" fill="#171717"/><rect x="22" y="0" width="4" height="4" fill="#171717"/><rect x="28" y="0" width="12" height="12" fill="#171717" rx="2"/>
                    <rect x="2" y="2" width="8" height="8" fill="white" rx="1"/><rect x="30" y="2" width="8" height="8" fill="white" rx="1"/>
                    <rect x="4" y="4" width="4" height="4" fill="#171717"/><rect x="32" y="4" width="4" height="4" fill="#171717"/>
                    <rect x="0" y="16" width="4" height="4" fill="#171717"/><rect x="8" y="16" width="4" height="4" fill="#171717"/><rect x="16" y="14" width="8" height="8" fill="#171717" rx="1"/><rect x="28" y="16" width="4" height="4" fill="#171717"/>
                    <rect x="0" y="28" width="12" height="12" fill="#171717" rx="2"/><rect x="14" y="28" width="4" height="4" fill="#171717"/><rect x="22" y="32" width="4" height="4" fill="#171717"/><rect x="28" y="28" width="4" height="4" fill="#171717"/><rect x="36" y="32" width="4" height="4" fill="#171717"/>
                    <rect x="2" y="30" width="8" height="8" fill="white" rx="1"/><rect x="4" y="32" width="4" height="4" fill="#171717"/>
                  </svg>
                  <p style="font-size: 7px; color: #a3a3a3; margin-top: 2px;">{waybillData.qr_hash}</p>
                </div>
              </div>
            </div>

            <!-- Route -->
            <div style="display: grid; grid-template-columns: 1fr auto 1fr; gap: 12px; margin-bottom: 20px; align-items: start;">
              <div style="border: 1px solid #e5e5e5; border-radius: 8px; padding: 12px;">
                <p style="font-size: 9px; text-transform: uppercase; color: #a3a3a3; font-weight: 700;">Source</p>
                <p style="font-size: 14px; font-weight: 800; color: #171717; margin-top: 4px;">{waybillData.source_warehouse}</p>
                <p style="font-size: 10px; color: #737373; margin-top: 2px;">{waybillData.source_location}</p>
              </div>
              <div style="padding-top: 20px; text-align: center;">
                <p style="font-size: 18px; color: #a3a3a3;">→</p>
              </div>
              <div style="border: 1px solid #e5e5e5; border-radius: 8px; padding: 12px;">
                <p style="font-size: 9px; text-transform: uppercase; color: #a3a3a3; font-weight: 700;">Destination</p>
                <p style="font-size: 14px; font-weight: 800; color: #171717; margin-top: 4px;">{waybillData.destination_warehouse}</p>
                <p style="font-size: 10px; color: #737373; margin-top: 2px;">{waybillData.destination_location}</p>
              </div>
            </div>

            <!-- Details Grid -->
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 8px; margin-bottom: 16px; font-size: 11px;">
              <div><p style="font-size: 9px; color: #a3a3a3; font-weight: 600; text-transform: uppercase;">Project</p><p style="font-weight: 600; margin-top: 2px;">{waybillData.project_name || "—"}</p></div>
              <div><p style="font-size: 9px; color: #a3a3a3; font-weight: 600; text-transform: uppercase;">Priority</p><p style="font-weight: 600; margin-top: 2px; text-transform: capitalize;">{waybillData.priority}</p></div>
              <div><p style="font-size: 9px; color: #a3a3a3; font-weight: 600; text-transform: uppercase;">Dispatch Date</p><p style="font-weight: 600; margin-top: 2px;">{waybillData.dispatched_date || waybillData.scheduled_date || "—"}</p></div>
              <div><p style="font-size: 9px; color: #a3a3a3; font-weight: 600; text-transform: uppercase;">Vehicle</p><p style="font-weight: 300; margin-top: 2px; font-style: italic;">{waybillData.vehicle_details || "—"}</p></div>
            </div>

            {#if waybillData.reason}
              <div style="margin-bottom: 16px; padding: 8px 12px; border: 1px solid #e5e5e5; border-radius: 6px; font-size: 11px;">
                <span style="font-size: 9px; color: #a3a3a3; font-weight: 600; text-transform: uppercase;">Reason: </span>
                <span style="font-weight: 300;">{waybillData.reason}</span>
              </div>
            {/if}

            <!-- Items Table -->
            <table style="width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 11px;">
              <thead>
                <tr style="background: #f5f5f5;">
                  <th style="border: 1px solid #d4d4d4; padding: 6px 8px; text-align: left; font-size: 9px; text-transform: uppercase; letter-spacing: 0.5px;">#</th>
                  <th style="border: 1px solid #d4d4d4; padding: 6px 8px; text-align: left; font-size: 9px; text-transform: uppercase;">Description</th>
                  <th style="border: 1px solid #d4d4d4; padding: 6px 8px; text-align: center; font-size: 9px; text-transform: uppercase;">Qty</th>
                  <th style="border: 1px solid #d4d4d4; padding: 6px 8px; text-align: center; font-size: 9px; text-transform: uppercase;">Unit</th>
                  <th style="border: 1px solid #d4d4d4; padding: 6px 8px; text-align: right; font-size: 9px; text-transform: uppercase;">Value</th>
                  <th style="border: 1px solid #d4d4d4; padding: 6px 8px; text-align: center; font-size: 9px; text-transform: uppercase;">Received</th>
                </tr>
              </thead>
              <tbody>
                {#each waybillData.items as item, idx}
                  <tr>
                    <td style="border: 1px solid #e5e5e5; padding: 5px 8px; color: #a3a3a3;">{idx + 1}</td>
                    <td style="border: 1px solid #e5e5e5; padding: 5px 8px; font-weight: 600;">{item.description}<br><span style="font-size: 9px; color: #a3a3a3; font-family: monospace;">{item.sku}</span></td>
                    <td style="border: 1px solid #e5e5e5; padding: 5px 8px; text-align: center; font-weight: 800; font-variant-numeric: tabular-nums;">{item.quantity}</td>
                    <td style="border: 1px solid #e5e5e5; padding: 5px 8px; text-align: center; color: #737373;">{item.unit}</td>
                    <td style="border: 1px solid #e5e5e5; padding: 5px 8px; text-align: right; font-variant-numeric: tabular-nums;">{currency.format(Number(item.line_value))}</td>
                    <td style="border: 1px solid #e5e5e5; padding: 5px 8px; text-align: center; min-width: 60px;"></td>
                  </tr>
                {/each}
              </tbody>
              <tfoot>
                <tr style="background: #fafafa;">
                  <td colspan="4" style="border: 1px solid #d4d4d4; padding: 8px; text-align: right; font-weight: 800; font-size: 12px;">TOTAL</td>
                  <td style="border: 1px solid #d4d4d4; padding: 8px; text-align: right; font-weight: 900; font-size: 13px; color: #065f46; font-variant-numeric: tabular-nums;">{currency.format(Number(waybillData.total_value))}</td>
                  <td style="border: 1px solid #d4d4d4; padding: 8px;"></td>
                </tr>
              </tfoot>
            </table>

            <!-- Signatures -->
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 24px; margin-top: 32px; font-size: 10px;">
              <div>
                <div style="height: 32px;"></div>
                <div style="border-top: 1px solid #a3a3a3; padding-top: 4px;">
                  <p style="color: #737373;">Dispatched By</p>
                  <p style="font-weight: 600; margin-top: 2px;">{waybillData.dispatched_by}</p>
                </div>
              </div>
              <div>
                <div style="height: 32px;"></div>
                <div style="border-top: 1px solid #a3a3a3; padding-top: 4px;">
                  <p style="color: #737373;">Driver</p>
                </div>
              </div>
              <div>
                <div style="height: 32px;"></div>
                <div style="border-top: 1px solid #a3a3a3; padding-top: 4px;">
                  <p style="color: #737373;">Gate Security</p>
                </div>
              </div>
              <div>
                <div style="height: 32px;"></div>
                <div style="border-top: 1px solid #a3a3a3; padding-top: 4px;">
                  <p style="color: #737373;">Received By</p>
                  <p style="font-weight: 600; margin-top: 2px;">{waybillData.received_by || ""}</p>
                </div>
              </div>
            </div>

            <p style="text-align: center; font-size: 8px; color: #a3a3a3; margin-top: 24px;">
              Generated by <span style="font-weight: 400; color: #171717;">developer</span><span style="font-weight: 700; color: #a3a3a3;">OS</span> — {new Date().toLocaleDateString()} — Scan QR code at site gate for verification
            </p>
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}

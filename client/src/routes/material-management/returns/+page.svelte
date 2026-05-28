<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import { onMount } from "svelte";

  interface ReturnItem { id: number; return_number: string; return_type: string; project_name: string; source_name: string; destination_name: string; vendor_name: string; status: string; reason: string; reason_detail: string; requested_by_name: string; approved_by: string; approved_date: string | null; dispatched_date: string | null; received_date: string | null; credit_memo_number: string; credit_amount: string; credit_received_date: string | null; line_count: number; total_value: string; created_at: string; }
  interface ReturnLine { id: number; item: number; item_name: string; item_sku: string; quantity: string; received_quantity: string; unit_of_measure: string; unit_cost: string; line_value: string; condition: string; notes: string; }
  interface ReturnDetail extends ReturnItem { notes: string; lines: ReturnLine[]; }
  interface DashboardData { pending_value: string; pending_count: number; credit_pending: number; credit_received_count: number; total_credits_received: string; top_reason: string; top_reason_count: number; return_velocity_30d: number; status_counts: Record<string, number>; recent_returns: ReturnItem[]; }

  const STATUS_COLORS: Record<string, string> = {
    draft: "bg-neutral-100 text-neutral-600", requested: "bg-blue-100 text-blue-700",
    approved: "bg-indigo-100 text-indigo-700", in_transit: "bg-amber-100 text-amber-700",
    received: "bg-emerald-100 text-emerald-700", credit_pending: "bg-orange-100 text-orange-700",
    credit_received: "bg-teal-100 text-teal-700", rejected: "bg-red-100 text-red-700", cancelled: "bg-neutral-100 text-neutral-400",
  };
  const REASON_LABELS: Record<string, string> = { excess: "Excess / Surplus", defective: "Defective", wrong_spec: "Wrong Spec", project_closure: "Project Closure", design_change: "Design Change", expired: "Expired", other: "Other" };
  const REASON_ICONS: Record<string, string> = { excess: "📦", defective: "🔨", wrong_spec: "📐", project_closure: "✅", design_change: "🔄", expired: "⏰", other: "📋" };

  let loading = $state(true);
  let data = $state<DashboardData | null>(null);
  let statusFilter = $state("");

  let viewMode = $state<"orders" | "ledger">("orders");

  // Ledger (material-level)
  interface LedgerRow { return_id: number; return_number: string; item_name: string; item_sku: string; quantity: string; unit: string; return_type: string; source: string; destination: string; reason: string; status: string; condition: string; value: string; }
  let ledgerData = $state<LedgerRow[]>([]);
  let ledgerLoading = $state(false);

  async function loadLedger() {
    ledgerLoading = true;
    try {
      const res = await api.get<{ results: any[] }>("/material-returns/", { page_size: "50", ordering: "-created_at" });
      const rows: LedgerRow[] = [];
      for (const r of res.results) {
        try {
          const d = await api.get<ReturnDetail>(`/material-returns/${r.id}/`);
          for (const line of d.lines) {
            rows.push({
              return_id: r.id, return_number: r.return_number,
              item_name: line.item_name, item_sku: line.item_sku,
              quantity: `${Number(line.quantity).toLocaleString()} ${line.unit_of_measure}`,
              unit: line.unit_of_measure,
              return_type: r.return_type === "to_vendor" ? "Vendor Return" : "Site → Warehouse",
              source: r.source_name || "", destination: r.return_type === "to_vendor" ? (r.vendor_name || "") : (r.destination_name || ""),
              reason: REASON_LABELS[r.reason] || r.reason,
              status: r.status, condition: line.condition, value: line.line_value,
            });
          }
        } catch { /* skip */ }
      }
      ledgerData = statusFilter ? rows.filter(r => r.status === statusFilter) : rows;
    } catch { ledgerData = []; }
    finally { ledgerLoading = false; }
  }

  const filteredLedger = $derived(statusFilter ? ledgerData.filter(r => r.status === statusFilter) : ledgerData);

  // Detail
  let showDetail = $state(false);
  let detail = $state<ReturnDetail | null>(null);
  let detailLoading = $state(false);

  // Create
  let showCreate = $state(false);
  let createSaving = $state(false);
  let warehouses = $state<{ id: number; name: string }[]>([]);
  let projects = $state<{ id: number; name: string }[]>([]);
  let vendors = $state<{ id: number; name: string }[]>([]);
  let items = $state<{ id: number; name: string; sku: string; default_unit_cost: string }[]>([]);
  let createForm = $state({ return_type: "to_warehouse", project: "", source_warehouse: "", destination_warehouse: "", vendor: "", reason: "excess", reason_detail: "", notes: "" });
  let createLines = $state<{ item: string; quantity: string; unit_of_measure: string; condition: string }[]>([]);
  let returnPhotos = $state<File[]>([]);

  function addReturnPhoto(e: Event) {
    const files = (e.target as HTMLInputElement).files;
    if (files) returnPhotos = [...returnPhotos, ...Array.from(files)];
    (e.target as HTMLInputElement).value = "";
  }
  function removeReturnPhoto(idx: number) { returnPhotos = returnPhotos.filter((_, i) => i !== idx); }

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");
  const filteredReturns = $derived.by(() => {
    if (!data) return [];
    return statusFilter ? data.recent_returns.filter(r => r.status === statusFilter) : data.recent_returns;
  });

  async function loadDashboard() {
    loading = true;
    try {
      const [dashRes, whRes, projRes, vendRes, itemRes] = await Promise.all([
        api.get<DashboardData>("/material-returns/dashboard/"),
        api.get<{ results: any[] }>("/inventory/warehouses/", { page_size: "100" }),
        api.get<{ results: any[] }>("/projects/", { page_size: "100" }),
        api.get<{ results: any[] }>("/procurement/vendors/", { page_size: "100" }),
        api.get<{ results: any[] }>("/inventory/items/", { page_size: "200", is_active: "true" }),
      ]);
      data = dashRes;
      warehouses = whRes.results.map((w: any) => ({ id: w.id, name: w.name }));
      projects = projRes.results.map((p: any) => ({ id: p.id, name: p.name }));
      vendors = vendRes.results.map((v: any) => ({ id: v.id, name: v.name }));
      items = itemRes.results.map((i: any) => ({ id: i.id, name: i.name, sku: i.sku, default_unit_cost: i.default_unit_cost || "0" }));
    } catch { toast.error("Load failed", "Could not load returns data."); }
    finally { loading = false; }
  }

  async function openDetail(id: number) {
    showDetail = true; detailLoading = true;
    try { detail = await api.get<ReturnDetail>(`/material-returns/${id}/`); }
    catch { toast.error("Load failed", "Could not load return details."); }
    finally { detailLoading = false; }
  }

  async function createReturn() {
    if (!createForm.source_warehouse) { toast.error("Required", "Source warehouse is required."); return; }
    if (createLines.length === 0) { toast.error("Required", "Add at least one material line."); return; }
    createSaving = true;
    try {
      const payload: Record<string, unknown> = { ...createForm, source_warehouse: Number(createForm.source_warehouse) };
      if (createForm.destination_warehouse) payload.destination_warehouse = Number(createForm.destination_warehouse); else delete payload.destination_warehouse;
      if (createForm.project) payload.project = Number(createForm.project); else delete payload.project;
      if (createForm.vendor) payload.vendor = Number(createForm.vendor); else delete payload.vendor;
      const created = await api.post<{ id: number; return_number: string }>("/material-returns/", payload);
      for (const line of createLines) {
        if (!line.item) continue;
        const itemData = items.find(i => String(i.id) === line.item);
        await api.post(`/material-returns/${created.id}/lines/`, { item: Number(line.item), quantity: Number(line.quantity), unit_of_measure: line.unit_of_measure, condition: line.condition, unit_cost: Number(itemData?.default_unit_cost || 0) });
      }
      toast.success("Created", `Return ${created.return_number} created.`);
      showCreate = false;
      createForm = { return_type: "to_warehouse", project: "", source_warehouse: "", destination_warehouse: "", vendor: "", reason: "excess", reason_detail: "", notes: "" };
      createLines = [];
      await loadDashboard();
    } catch (err) {
      if (err instanceof ApiError) toast.error("Failed", Object.values(err.fieldErrors).flat().join(" ") || "Check the form.");
      else toast.error("Failed", "Could not create return.");
    } finally { createSaving = false; }
  }

  async function approveReturn() { if (!detail) return; try { await api.post(`/material-returns/${detail.id}/approve/`, {}); toast.success("Approved", "Return approved."); await openDetail(detail.id); await loadDashboard(); } catch (err) { if (err instanceof ApiError) toast.error("Failed", err.data?.detail || "Cannot approve."); else toast.error("Failed", "Could not approve."); } }
  async function receiveReturn() { if (!detail) return; try { await api.post(`/material-returns/${detail.id}/receive-return/`, {}); toast.success("Received", "Materials restocked / credit memo pending."); await openDetail(detail.id); await loadDashboard(); } catch (err) { if (err instanceof ApiError) toast.error("Failed", err.data?.detail || "Cannot receive."); else toast.error("Failed", "Could not receive."); } }
  async function recordCredit() {
    if (!detail) return;
    const memo = prompt("Credit Memo Number:");
    if (!memo) return;
    try { await api.post(`/material-returns/${detail.id}/record-credit/`, { credit_memo_number: memo, credit_amount: Number(detail.total_value || 0) }); toast.success("Credit Recorded", "Vendor credit memo linked."); await openDetail(detail.id); await loadDashboard(); }
    catch { toast.error("Failed", "Could not record credit."); }
  }

  function devFill() {
    createForm.return_type = Math.random() > 0.5 ? "to_warehouse" : "to_vendor";
    if (projects.length) createForm.project = String(projects[Math.floor(Math.random() * projects.length)].id);
    if (warehouses.length) createForm.source_warehouse = String(warehouses[0].id);
    if (warehouses.length > 1) createForm.destination_warehouse = String(warehouses[1].id);
    if (vendors.length && createForm.return_type === "to_vendor") createForm.vendor = String(vendors[Math.floor(Math.random() * vendors.length)].id);
    createForm.reason = ["excess", "defective", "wrong_spec", "project_closure", "design_change"][Math.floor(Math.random() * 5)];
    createForm.reason_detail = ["Surplus from completed foundation phase", "Cracked tiles — batch quality issue", "Wrong gauge rebar delivered", "Project completed ahead of schedule", "Architect revised specification"][Math.floor(Math.random() * 5)];
    createLines = [];
    const count = Math.floor(Math.random() * 3) + 1;
    for (let i = 0; i < count && i < items.length; i++) {
      const item = items[Math.floor(Math.random() * items.length)];
      createLines.push({ item: String(item.id), quantity: String(Math.floor(Math.random() * 50 + 5)), unit_of_measure: "ea", condition: ["good", "damaged"][Math.floor(Math.random() * 2)] });
    }
  }

  onMount(() => { loadDashboard(); });
</script>

<svelte:head><title>Returns Management | developerOS</title></svelte:head>

<div class="space-y-5">
  <div class="flex items-start justify-between gap-3">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-pink-600">Material Management</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Returns Management</h1>
      <p class="mt-1 text-sm text-neutral-500">Reverse logistics — recover value from excess, defective, or surplus materials.</p>
    </div>
    <button onclick={() => { showCreate = true; if (createLines.length === 0) createLines.push({ item: "", quantity: "1", unit_of_measure: "ea", condition: "good" }); }} class="rounded-lg bg-linear-to-r from-rose-600 to-pink-600 px-4 py-2.5 text-sm font-semibold text-white hover:from-rose-700 hover:to-pink-700 shadow-lg">+ New Return</button>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-20"><div class="h-7 w-7 rounded-full border-2 border-neutral-200 border-t-neutral-900 animate-spin"></div></div>
  {:else if data}

    <!-- Returns Command Center HUD -->
    <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <div class="rounded-xl border-2 border-rose-300 bg-linear-to-br from-rose-50 to-pink-50 p-4 text-center" style="backdrop-filter: blur(10px)">
        <p class="text-[9px] font-bold text-rose-500 uppercase tracking-wider">Pending Returns</p>
        <p class="mt-1 text-xl font-black text-rose-800 tabular-nums">{currency.format(Number(data.pending_value))}</p>
        <p class="text-[9px] text-rose-400">{data.pending_count} in pipeline</p>
      </div>
      <div class="rounded-xl border-2 border-indigo-200 bg-linear-to-br from-indigo-50 to-violet-50 p-4 text-center" style="backdrop-filter: blur(10px)">
        <p class="text-[9px] font-bold text-indigo-500 uppercase tracking-wider">Return Velocity</p>
        <p class="mt-1 text-2xl font-black text-indigo-800 tabular-nums">{data.return_velocity_30d}</p>
        <p class="text-[9px] text-indigo-400">completed (30d)</p>
      </div>
      <div class="rounded-xl border-2 border-amber-200 bg-linear-to-br from-amber-50 to-orange-50 p-4 text-center" style="backdrop-filter: blur(10px)">
        <p class="text-[9px] font-bold text-amber-500 uppercase tracking-wider">Top Return Reason</p>
        {#if data.top_reason}
          <p class="mt-1 text-sm font-black text-amber-800">{REASON_ICONS[data.top_reason] || ""} {REASON_LABELS[data.top_reason] || data.top_reason}</p>
          <p class="text-[9px] text-amber-400">{data.top_reason_count} return(s)</p>
        {:else}
          <p class="mt-1 text-sm text-amber-300">No data</p>
        {/if}
      </div>
      <div class="rounded-xl border-2 {data.credit_pending > 0 ? 'border-orange-300 bg-linear-to-br from-orange-50 to-amber-50' : 'border-emerald-300 bg-linear-to-br from-emerald-50 to-teal-50'} p-4 text-center {data.credit_pending > 0 ? 'animate-pulse' : ''}" style="backdrop-filter: blur(10px)">
        <p class="text-[9px] font-bold {data.credit_pending > 0 ? 'text-orange-500' : 'text-emerald-500'} uppercase tracking-wider">Credit Memos</p>
        {#if data.credit_pending > 0}
          <p class="mt-1 text-2xl font-black text-orange-700 tabular-nums">{data.credit_pending}</p>
          <p class="text-[9px] text-orange-400">pending vendor credits</p>
        {:else}
          <p class="mt-1 text-lg font-black text-emerald-700 tabular-nums">{currency.format(Number(data.total_credits_received))}</p>
          <p class="text-[9px] text-emerald-400">{data.credit_received_count} credits received</p>
        {/if}
      </div>
    </div>

    <!-- Returns Table -->
    <section class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
      <div class="border-b border-neutral-100 bg-neutral-50 px-5 py-3 flex items-center justify-between flex-wrap gap-2">
        <div class="flex items-center gap-3">
          <div class="flex gap-1 rounded-lg bg-neutral-200/60 p-0.5">
            <button onclick={() => { viewMode = "orders"; }} class="rounded-md px-3 py-1.5 text-[10px] font-bold transition-colors {viewMode === 'orders' ? 'bg-white text-neutral-900 shadow-sm' : 'text-neutral-500'}">Orders</button>
            <button onclick={() => { viewMode = "ledger"; if (ledgerData.length === 0) loadLedger(); }} class="rounded-md px-3 py-1.5 text-[10px] font-bold transition-colors {viewMode === 'ledger' ? 'bg-white text-neutral-900 shadow-sm' : 'text-neutral-500'}">Ledger</button>
          </div>
          <h3 class="text-[10px] font-black text-neutral-500 uppercase tracking-widest">{viewMode === "orders" ? `Return Orders (${filteredReturns.length})` : `Returns Ledger (${filteredLedger.length} lines)`}</h3>
        </div>
        <div class="flex gap-1">
          {#each [["", "All"], ["requested", "Requested"], ["approved", "Approved"], ["received", "Received"], ["credit_pending", "Credit Pending"], ["credit_received", "Credited"]] as [val, label]}
            <button onclick={() => { statusFilter = val; }} class="rounded-md px-2.5 py-1 text-[9px] font-semibold transition-colors {statusFilter === val ? 'bg-neutral-900 text-white' : 'text-neutral-500 hover:bg-neutral-100'}">{label}</button>
          {/each}
        </div>
      </div>
      {#if viewMode === "ledger"}
        {#if ledgerLoading}
          <div class="p-8 text-center text-sm text-neutral-400">Loading ledger...</div>
        {:else if filteredLedger.length === 0}
          <div class="p-8 text-center text-sm text-neutral-400">No ledger entries.</div>
        {:else}
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead><tr class="border-b border-neutral-200 bg-neutral-100/80">
                <th class="px-4 py-2.5 text-left text-[10px] font-black text-neutral-700 uppercase tracking-wider">Return ID</th>
                <th class="px-4 py-2.5 text-left text-[10px] font-black text-neutral-700 uppercase tracking-wider">Material</th>
                <th class="px-4 py-2.5 text-right text-[10px] font-black text-neutral-700 uppercase tracking-wider">Qty</th>
                <th class="px-4 py-2.5 text-left text-[10px] font-black text-neutral-700 uppercase tracking-wider">Type</th>
                <th class="px-4 py-2.5 text-left text-[10px] font-black text-neutral-700 uppercase tracking-wider">Reason</th>
                <th class="px-4 py-2.5 text-center text-[10px] font-black text-neutral-700 uppercase tracking-wider">Condition</th>
                <th class="px-4 py-2.5 text-center text-[10px] font-black text-neutral-700 uppercase tracking-wider">Status</th>
                <th class="px-4 py-2.5 text-right text-[10px] font-black text-neutral-700 uppercase tracking-wider">Value</th>
              </tr></thead>
              <tbody class="divide-y divide-neutral-50">
                {#each filteredLedger as row}
                  <tr class="cursor-pointer hover:bg-neutral-50 {row.status === 'credit_pending' ? 'bg-orange-50/20' : row.status === 'received' || row.status === 'credit_received' ? 'bg-emerald-50/20' : ''}" onclick={() => openDetail(row.return_id)}>
                    <td class="px-4 py-3"><span class="font-mono text-xs font-black text-rose-700">{row.return_number}</span></td>
                    <td class="px-4 py-3">
                      <p class="font-bold text-neutral-900" style="font-family: Raleway, sans-serif;">{row.item_name}</p>
                      <p class="text-[9px] text-neutral-400 font-mono">{row.item_sku}</p>
                    </td>
                    <td class="px-4 py-3 text-right font-black text-neutral-900 tabular-nums">{row.quantity}</td>
                    <td class="px-4 py-3"><span class="rounded-md {row.return_type.includes('Vendor') ? 'bg-orange-50 border-orange-200 text-orange-700' : 'bg-indigo-50 border-indigo-200 text-indigo-700'} border px-2 py-0.5 text-[10px] font-semibold">{row.return_type}</span></td>
                    <td class="px-4 py-3 text-xs text-neutral-700">{row.reason}</td>
                    <td class="px-4 py-3 text-center"><span class="rounded-full border px-2 py-0.5 text-[9px] font-bold {row.condition === 'good' ? 'bg-emerald-100 text-emerald-700 border-emerald-200' : row.condition === 'damaged' ? 'bg-red-100 text-red-700 border-red-200' : 'bg-amber-100 text-amber-700 border-amber-200'}">{row.condition}</span></td>
                    <td class="px-4 py-3 text-center"><span class="rounded-full border px-2.5 py-0.5 text-[9px] font-bold {STATUS_COLORS[row.status] || ''}">{row.status.replace(/_/g, " ")}</span></td>
                    <td class="px-4 py-3 text-right font-black text-emerald-700 tabular-nums">{currency.format(Number(row.value || 0))}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      {:else if filteredReturns.length === 0}
        <div class="p-8 text-center text-sm text-neutral-400">No returns found.</div>
      {:else}
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead><tr class="border-b border-neutral-200 bg-neutral-100/80">
              <th class="px-4 py-2.5 text-left text-[10px] font-black text-neutral-700 uppercase">Return #</th>
              <th class="px-4 py-2.5 text-left text-[10px] font-black text-neutral-700 uppercase">Type</th>
              <th class="px-4 py-2.5 text-left text-[10px] font-black text-neutral-700 uppercase">Reason</th>
              <th class="px-4 py-2.5 text-left text-[10px] font-black text-neutral-700 uppercase">From</th>
              <th class="px-4 py-2.5 text-center text-[10px] font-black text-neutral-700 uppercase">Status</th>
              <th class="px-4 py-2.5 text-center text-[10px] font-black text-neutral-700 uppercase">Items</th>
              <th class="px-4 py-2.5 text-right text-[10px] font-black text-neutral-700 uppercase">Value</th>
            </tr></thead>
            <tbody class="divide-y divide-neutral-50">
              {#each filteredReturns as r}
                <tr class="cursor-pointer hover:bg-neutral-50 {r.status === 'credit_pending' ? 'bg-orange-50/20' : r.status === 'credit_received' ? 'bg-emerald-50/20' : ''}" onclick={() => openDetail(r.id)}>
                  <td class="px-4 py-3 font-black text-neutral-900 tabular-nums">{r.return_number}</td>
                  <td class="px-4 py-3"><span class="rounded-md bg-neutral-100 border border-neutral-200 px-2 py-0.5 text-[10px] font-semibold text-neutral-700">{r.return_type === "to_vendor" ? "Vendor" : "Warehouse"}</span></td>
                  <td class="px-4 py-3"><span class="text-xs">{REASON_ICONS[r.reason] || ""}</span> <span class="text-xs text-neutral-700">{REASON_LABELS[r.reason] || r.reason}</span></td>
                  <td class="px-4 py-3 text-xs text-neutral-600">{r.source_name}</td>
                  <td class="px-4 py-3 text-center"><span class="rounded-full border px-2.5 py-0.5 text-[9px] font-bold {STATUS_COLORS[r.status] || ''}">{r.status.replace(/_/g, " ")}</span></td>
                  <td class="px-4 py-3 text-center font-black tabular-nums">{r.line_count}</td>
                  <td class="px-4 py-3 text-right font-black text-emerald-700 tabular-nums">{currency.format(Number(r.total_value || 0))}</td>
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
  <div class="fixed inset-0 z-50 flex justify-end bg-black/40" style="backdrop-filter: blur(10px)" onclick={() => { showDetail = false; detail = null; }}>
    <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
    <div class="w-full max-w-2xl bg-white shadow-2xl overflow-y-auto" onclick={(e) => e.stopPropagation()}>
      <div class="bg-linear-to-r from-rose-600 to-pink-600 px-5 py-4 flex items-start justify-between sticky top-0 z-10">
        <div>
          <h2 class="text-lg font-black text-white">{detail.return_number}</h2>
          <p class="text-sm text-rose-100 mt-0.5">{detail.return_type === "to_vendor" ? `Return to ${detail.vendor_name}` : `Return to ${detail.destination_name}`}</p>
          <div class="flex gap-2 mt-2">
            <span class="rounded-full bg-white/20 border border-white/30 px-2.5 py-0.5 text-[10px] font-bold text-white">{detail.status.replace(/_/g, " ")}</span>
            <span class="rounded-full bg-white/20 border border-white/30 px-2.5 py-0.5 text-[10px] font-bold text-white">{REASON_ICONS[detail.reason]} {REASON_LABELS[detail.reason]}</span>
          </div>
        </div>
        <div class="flex items-center gap-2">
          {#if detail.status === "requested"}<button onclick={approveReturn} class="rounded-lg bg-emerald-500 px-3 py-1.5 text-xs font-bold text-white hover:bg-emerald-600">Approve</button>{/if}
          {#if detail.status === "approved" || detail.status === "in_transit"}<button onclick={receiveReturn} class="rounded-lg bg-teal-500 px-3 py-1.5 text-xs font-bold text-white hover:bg-teal-600">Receive</button>{/if}
          {#if detail.status === "credit_pending"}<button onclick={recordCredit} class="rounded-lg bg-orange-500 px-3 py-1.5 text-xs font-bold text-white hover:bg-orange-600">Record Credit</button>{/if}
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
            <div><span class="text-[9px] text-neutral-400 uppercase font-bold block">From</span><span class="text-neutral-900">{detail.source_name}</span></div>
            <div><span class="text-[9px] text-neutral-400 uppercase font-bold block">To</span><span class="text-neutral-900">{detail.return_type === "to_vendor" ? detail.vendor_name : detail.destination_name}</span></div>
            <div><span class="text-[9px] text-neutral-400 uppercase font-bold block">Requested By</span><span class="text-neutral-900">{detail.requested_by_name}</span></div>
            <div><span class="text-[9px] text-neutral-400 uppercase font-bold block">Project</span><span class="text-neutral-900">{detail.project_name || "—"}</span></div>
          </div>
          {#if detail.reason_detail}<div><p class="text-[9px] text-neutral-400 uppercase font-bold mb-1">Reason Detail</p><p class="text-sm text-neutral-700" style="font-weight: 300;">{detail.reason_detail}</p></div>{/if}

          <!-- Credit Info (vendor returns) -->
          {#if detail.return_type === "to_vendor" && (detail.credit_memo_number || detail.status === "credit_pending")}
            <div class="rounded-xl border-2 {detail.status === 'credit_received' ? 'border-emerald-300 bg-linear-to-br from-emerald-50 to-teal-50' : 'border-orange-300 bg-linear-to-br from-orange-50 to-amber-50'} p-4">
              <h4 class="text-[9px] font-black {detail.status === 'credit_received' ? 'text-emerald-600' : 'text-orange-600'} uppercase tracking-widest mb-2">Credit Memo</h4>
              <div class="grid grid-cols-3 gap-3 text-xs">
                <div><span class="text-neutral-400 block text-[9px]">Memo #</span><span class="font-bold">{detail.credit_memo_number || "Pending"}</span></div>
                <div><span class="text-neutral-400 block text-[9px]">Amount</span><span class="font-black text-lg tabular-nums">{currency.format(Number(detail.credit_amount || detail.total_value || 0))}</span></div>
                <div><span class="text-neutral-400 block text-[9px]">Received</span><span class="font-bold">{detail.credit_received_date || "—"}</span></div>
              </div>
            </div>
          {/if}

          <!-- Lines -->
          <div class="rounded-lg border border-neutral-200 overflow-hidden">
            <table class="w-full text-sm">
              <thead><tr class="border-b border-neutral-100 bg-neutral-50">
                <th class="px-3 py-2 text-left text-[9px] font-bold text-neutral-500 uppercase">Material</th>
                <th class="px-3 py-2 text-center text-[9px] font-bold text-neutral-500 uppercase">Qty</th>
                <th class="px-3 py-2 text-center text-[9px] font-bold text-neutral-500 uppercase">Condition</th>
                <th class="px-3 py-2 text-right text-[9px] font-bold text-neutral-500 uppercase">Value</th>
              </tr></thead>
              <tbody class="divide-y divide-neutral-50">
                {#each detail.lines as line}
                  <tr>
                    <td class="px-3 py-2.5"><p class="font-bold text-neutral-900">{line.item_name}</p><p class="text-[9px] text-neutral-400 font-mono">{line.item_sku}</p></td>
                    <td class="px-3 py-2.5 text-center font-black tabular-nums">{line.quantity} <span class="text-neutral-400 text-[9px] font-normal">{line.unit_of_measure}</span></td>
                    <td class="px-3 py-2.5 text-center"><span class="rounded-full border px-2 py-0.5 text-[9px] font-bold {line.condition === 'good' ? 'bg-emerald-100 text-emerald-700 border-emerald-200' : line.condition === 'damaged' ? 'bg-red-100 text-red-700 border-red-200' : 'bg-amber-100 text-amber-700 border-amber-200'}">{line.condition}</span></td>
                    <td class="px-3 py-2.5 text-right font-black text-emerald-700 tabular-nums">{currency.format(Number(line.line_value))}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>

          <!-- Total -->
          <div class="rounded-xl bg-linear-to-r from-rose-50 to-pink-50 border-2 border-rose-200 p-4 flex items-center justify-between">
            <span class="text-xs font-black text-rose-600 uppercase">Total Recoverable Value</span>
            <span class="text-xl font-black text-rose-800 tabular-nums">{currency.format(Number(detail.total_value || 0))}</span>
          </div>
        </div>
      {/if}
    </div>
  </div>
{/if}

<!-- Return Authorization Slide-over -->
{#if showCreate}
  <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <div class="fixed inset-0 z-50 flex justify-end bg-black/40" style="backdrop-filter: blur(12px)" onclick={() => { showCreate = false; returnPhotos = []; }}>
    <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
    <div class="w-full max-w-xl h-full bg-white shadow-2xl overflow-y-auto" onclick={(e) => e.stopPropagation()}>
      <!-- Dark gradient header -->
      <div class="bg-neutral-900 px-6 py-5">
        <p class="text-[10px] font-bold text-neutral-400 uppercase tracking-widest">Return Authorization</p>
        <h2 class="text-lg font-black text-white mt-1">New Material Return</h2>
        <p class="text-xs text-neutral-500 mt-1">Initiate reverse logistics for excess, defective, or surplus materials.</p>
      </div>

      <div class="p-6 space-y-5">
        <!-- Return Type Toggle -->
        <div>
          <span class="mb-2 block text-xs font-black text-neutral-700">Return Type</span>
          <div class="flex gap-2">
            <button type="button" onclick={() => { createForm.return_type = "to_warehouse"; }}
              class="flex-1 rounded-xl border-2 py-3.5 text-center transition-all {createForm.return_type === 'to_warehouse' ? 'border-indigo-400 bg-indigo-50 text-indigo-700 shadow-lg ring-2 ring-indigo-100' : 'border-neutral-200 text-neutral-500 hover:border-neutral-300'}">
              <p class="text-xs font-black">Internal Return</p>
              <p class="text-[9px] text-neutral-400 mt-0.5">Site → Warehouse</p>
            </button>
            <button type="button" onclick={() => { createForm.return_type = "to_vendor"; }}
              class="flex-1 rounded-xl border-2 py-3.5 text-center transition-all {createForm.return_type === 'to_vendor' ? 'border-amber-400 bg-amber-50 text-amber-700 shadow-lg ring-2 ring-amber-100' : 'border-neutral-200 text-neutral-500 hover:border-neutral-300'}">
              <p class="text-xs font-black">Vendor Return</p>
              <p class="text-[9px] text-neutral-400 mt-0.5">Site → Supplier</p>
            </button>
          </div>
        </div>

        <!-- Source Location -->
        <label class="block">
          <span class="mb-1 block text-xs font-black text-neutral-700">Source Location *</span>
          <select bind:value={createForm.source_warehouse} class="w-full rounded-xl border-2 border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500 focus:border-rose-400">
            <option value="">Which site/store is the material at?</option>
            {#each warehouses as w}<option value={String(w.id)}>{w.name}</option>{/each}
          </select>
        </label>

        <!-- Destination -->
        {#if createForm.return_type === "to_warehouse"}
          <label class="block">
            <span class="mb-1 block text-xs font-black text-neutral-700">Destination Warehouse</span>
            <select bind:value={createForm.destination_warehouse} class="w-full rounded-xl border-2 border-indigo-200 bg-indigo-50/30 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
              <option value="">Back to which warehouse?</option>
              {#each warehouses.filter(w => String(w.id) !== createForm.source_warehouse) as w}<option value={String(w.id)}>{w.name}</option>{/each}
            </select>
          </label>
        {:else}
          <label class="block">
            <span class="mb-1 block text-xs font-black text-neutral-700">Original Vendor</span>
            <select bind:value={createForm.vendor} class="w-full rounded-xl border-2 border-amber-200 bg-amber-50/30 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-amber-500">
              <option value="">Return to which vendor?</option>
              {#each vendors as v}<option value={String(v.id)}>{v.name}</option>{/each}
            </select>
          </label>
        {/if}

        <div class="grid grid-cols-2 gap-3">
          <label class="block"><span class="mb-1 block text-xs font-black text-neutral-700">Project</span>
            <select bind:value={createForm.project} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500">
              <option value="">No project</option>
              {#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}
            </select>
          </label>
          <label class="block"><span class="mb-1 block text-xs font-black text-neutral-700">Reason Code *</span>
            <select bind:value={createForm.reason} class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500">
              {#each Object.entries(REASON_LABELS) as [val, label]}<option value={val}>{REASON_ICONS[val]} {label}</option>{/each}
            </select>
          </label>
        </div>

        <label class="block"><span class="mb-1 block text-xs font-black text-neutral-700">Reason Detail</span>
          <textarea bind:value={createForm.reason_detail} rows="2" placeholder="Describe why these materials are being returned..."
            class="w-full rounded-xl border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-rose-500 resize-none"></textarea>
        </label>

        <!-- Photo Evidence -->
        <div>
          <span class="mb-2 block text-xs font-black text-neutral-700">Photo Evidence</span>
          <input type="file" accept="image/*" capture="environment" multiple class="hidden" id="return-photo-input" onchange={addReturnPhoto} />
          {#if returnPhotos.length > 0}
            <div class="flex flex-wrap gap-2 mb-2">
              {#each returnPhotos as photo, i}
                <div class="rounded-lg border-2 border-emerald-200 bg-emerald-50 px-3 py-1.5 flex items-center gap-2">
                  <span class="text-xs text-emerald-700 font-semibold truncate max-w-[120px]">{photo.name}</span>
                  <button type="button" onclick={() => removeReturnPhoto(i)} class="text-emerald-400 hover:text-red-500" aria-label="Remove photo">
                    <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
                  </button>
                </div>
              {/each}
            </div>
          {/if}
          <button type="button" onclick={() => document.getElementById("return-photo-input")?.click()}
            class="w-full rounded-xl border-2 border-dashed {createForm.reason === 'defective' || createForm.reason === 'wrong_spec' ? 'border-red-300 bg-red-50/30' : 'border-neutral-300 bg-neutral-50/30'} p-4 text-center hover:border-rose-400 transition-colors">
            <svg class="mx-auto h-6 w-6 {createForm.reason === 'defective' ? 'text-red-400' : 'text-neutral-400'}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6.827 6.175A2.31 2.31 0 0 1 5.186 7.23c-.38.054-.757.112-1.134.175C2.999 7.58 2.25 8.507 2.25 9.574V18a2.25 2.25 0 0 0 2.25 2.25h15A2.25 2.25 0 0 0 21.75 18V9.574c0-1.067-.75-1.994-1.802-2.169a47.865 47.865 0 0 0-1.134-.175 2.31 2.31 0 0 1-1.64-1.055l-.822-1.316a2.192 2.192 0 0 0-1.736-1.039 48.774 48.774 0 0 0-5.232 0 2.192 2.192 0 0 0-1.736 1.039l-.821 1.316Z" /><path stroke-linecap="round" stroke-linejoin="round" d="M16.5 12.75a4.5 4.5 0 1 1-9 0 4.5 4.5 0 0 1 9 0ZM18.75 10.5h.008v.008h-.008V10.5Z" /></svg>
            <p class="text-xs {createForm.reason === 'defective' ? 'text-red-600' : 'text-neutral-600'} font-medium mt-1">
              {createForm.reason === 'defective' || createForm.reason === 'wrong_spec' ? 'Upload Proof of Damage (recommended)' : 'Attach photos (optional)'}
            </p>
          </button>
        </div>

        <!-- Material Lines -->
        <div>
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-[10px] font-black text-neutral-500 uppercase tracking-widest">Materials ({createLines.length})</h3>
            <button type="button" onclick={() => { createLines = [...createLines, { item: "", quantity: "1", unit_of_measure: "ea", condition: "good" }]; }} class="rounded-md bg-neutral-900 px-2.5 py-1 text-[10px] font-bold text-white hover:bg-neutral-800">+ Add</button>
          </div>
          <div class="space-y-2">
            {#each createLines as line, i}
              <div class="rounded-xl border-2 p-3 {line.condition === 'damaged' ? 'border-red-200 bg-red-50/20' : line.condition === 'expired' ? 'border-amber-200 bg-amber-50/20' : 'border-neutral-200'}">
                <div class="flex gap-2 items-end">
                  <label class="flex-1 text-sm"><span class="mb-1 block text-[9px] font-bold text-neutral-500">Material *</span>
                    <select bind:value={line.item} class="w-full rounded-lg border border-neutral-200 bg-white px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-rose-500">
                      <option value="">Select</option>
                      {#each items as item}<option value={String(item.id)}>{item.sku} — {item.name}</option>{/each}
                    </select>
                  </label>
                  <label class="w-20 text-sm"><span class="mb-1 block text-[9px] font-bold text-neutral-500">Qty *</span>
                    <input type="number" step="0.01" min="1" bind:value={line.quantity} class="w-full rounded-lg border border-neutral-200 px-2 py-1.5 text-xs tabular-nums focus:outline-none focus:ring-2 focus:ring-rose-500" />
                  </label>
                  <label class="w-28 text-sm"><span class="mb-1 block text-[9px] font-bold text-neutral-500">Condition</span>
                    <select bind:value={line.condition} class="w-full rounded-lg border border-neutral-200 bg-white px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-rose-500">
                      <option value="good">Good</option><option value="damaged">Damaged</option><option value="expired">Expired</option>
                    </select>
                  </label>
                  <button type="button" onclick={() => { createLines = createLines.filter((_, idx) => idx !== i); }} class="rounded-md p-1.5 text-neutral-400 hover:text-red-500 mb-0.5" aria-label="Remove line">
                    <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
                  </button>
                </div>
              </div>
            {/each}
          </div>
        </div>
      </div>

      <!-- Sticky footer -->
      <div class="sticky bottom-0 bg-white border-t border-neutral-100 px-6 py-4 flex gap-3">
        {#if isDev}<button type="button" onclick={devFill} class="rounded-lg bg-orange-500 px-3 py-2 text-xs font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
        <div class="flex-1"></div>
        <button onclick={() => { showCreate = false; returnPhotos = []; }} class="rounded-xl border-2 border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
        <button onclick={createReturn} disabled={createSaving}
          class="rounded-xl bg-neutral-900 px-5 py-2.5 text-sm font-black text-white hover:bg-neutral-800 disabled:opacity-50 shadow-lg">
          {createSaving ? "Creating..." : "Submit Return"}
        </button>
      </div>
    </div>
  </div>
{/if}

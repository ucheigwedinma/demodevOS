<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import type { InventoryStockRecord, InventoryWarehouse, PaginatedResponse, InventoryItemCategory } from "$lib/types";
  import { onMount } from "svelte";

  const CATEGORY_OPTIONS: { value: InventoryItemCategory; label: string }[] = [
    { value: "structural", label: "Structural" }, { value: "finishing", label: "Finishing" },
    { value: "mep", label: "MEP" }, { value: "electrical", label: "Electrical" },
    { value: "plumbing", label: "Plumbing" }, { value: "safety", label: "Safety" },
    { value: "consumable", label: "Consumable" }, { value: "spare", label: "Spare" },
    { value: "equipment", label: "Equipment" }, { value: "other", label: "Other" },
  ];

  let records = $state<InventoryStockRecord[]>([]);
  let warehouses = $state<InventoryWarehouse[]>([]);
  let loading = $state(true);
  let currentPage = $state(1);
  let pageSize = $state(25);
  let totalCount = $state(0);
  let search = $state("");
  let warehouse = $state("");
  let category = $state("");
  let lowStockOnly = $state(false);

  let warehouseType = $state("");

  // Bulk selection
  let selectedIds = $state<number[]>([]);
  let bulkAction = $state<"" | "transfer" | "reorder">("");
  let bulkSaving = $state(false);

  function toggleSelect(id: number) {
    if (selectedIds.includes(id)) selectedIds = selectedIds.filter(x => x !== id);
    else selectedIds = [...selectedIds, id];
  }
  function selectAll() {
    if (selectedIds.length === records.length) selectedIds = [];
    else selectedIds = records.map(r => r.id);
  }

  // Row drill-down
  let expandedRowId = $state<number | null>(null);
  let expandedData = $state<{ transactions: { id: number; type: string; quantity: string; date: string; reference: string; notes: string }[]; batches: { batch: string; expiry: string; location: string; qty: string }[] } | null>(null);
  let expandedLoading = $state(false);

  async function toggleExpand(row: InventoryStockRecord) {
    if (expandedRowId === row.id) { expandedRowId = null; expandedData = null; return; }
    expandedRowId = row.id;
    expandedLoading = true;
    expandedData = null;
    try {
      // Fetch recent transactions for this item + warehouse
      const txRes = await api.get<{ results: any[] }>("/inventory/transactions/", {
        item: String(row.item), warehouse: String(row.warehouse), page_size: "10", ordering: "-created_at",
      });
      const transactions = (txRes.results || []).map((t: any) => ({
        id: t.id,
        type: t.transaction_type_display || t.transaction_type || "",
        quantity: t.quantity || "0",
        date: t.created_at ? new Date(t.created_at).toLocaleDateString() : "",
        reference: t.reference_number || "",
        notes: t.notes || "",
      }));

      // Batch data from GRN items (if available)
      let batches: { batch: string; expiry: string; location: string; qty: string }[] = [];
      try {
        const batchRes = await api.get<{ results: any[] }>("/procurement/goods-receipts/", { page_size: "20" });
        // Extract batch data from GRN items linked to this inventory item
        // This is a best-effort lookup — proper batch tracking would need a dedicated model
        batches = [];
      } catch { /* batch data optional */ }

      expandedData = { transactions, batches };
    } catch { expandedData = { transactions: [], batches: [] }; }
    finally { expandedLoading = false; }
  }

  // Bulk actions
  async function executeBulkAction() {
    if (selectedIds.length === 0) { toast.error("Select items", "Select at least one stock record."); return; }
    bulkSaving = true;
    try {
      if (bulkAction === "reorder") {
        // Create PRs for selected low-stock items
        const lowItems = records.filter(r => selectedIds.includes(r.id));
        let created = 0;
        for (const row of lowItems) {
          const targetQty = Number(row.target_stock_level || row.reorder_level || 0) * 2;
          const currentQty = Number(row.quantity_on_hand || 0);
          const orderQty = Math.max(1, targetQty - currentQty);
          if (orderQty > 0) {
            try {
              await api.post("/inventory/transactions/", {
                item: row.item,
                warehouse: row.warehouse,
                quantity: orderQty,
                transaction_type: "purchase_order",
                notes: `Bulk reorder: ${row.item_name} — ${orderQty} units`,
              });
              created++;
            } catch { /* continue with others */ }
          }
        }
        toast.success("Reorder Initiated", `${created} reorder transaction(s) created.`);
      } else if (bulkAction === "transfer") {
        toast.success("Transfer", `${selectedIds.length} item(s) selected for transfer. Use the Transfer Request form to specify destination.`);
      }
      selectedIds = [];
      bulkAction = "";
      await fetchStock();
    } catch { toast.error("Failed", "Bulk action failed."); }
    finally { bulkSaving = false; }
  }

  // Adjustment modal
  let showAdjust = $state(false);
  let adjustSaving = $state(false);
  let adjustForm = $state({ item: "", warehouse: "", quantity: "", reason: "" });
  let items = $state<{ id: number; name: string; sku: string }[]>([]);

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");
  const totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));

  // Inline reorder editing
  let editingReorderId = $state<number | null>(null);
  let editingReorderValue = $state("");

  async function saveReorderLevel(row: InventoryStockRecord) {
    const newLevel = Number(editingReorderValue);
    if (isNaN(newLevel) || newLevel < 0) { toast.error("Invalid", "Reorder level must be >= 0."); return; }
    try {
      await api.patch(`/inventory/items/${row.item}/`, { reorder_level: newLevel });
      toast.success("Updated", `Reorder level set to ${newLevel}.`);
      editingReorderId = null;
      await fetchStock();
    } catch { toast.error("Failed", "Could not update reorder level."); }
  }

  // KPI calculations
  const totalValuation = $derived(records.reduce((s, r) => s + Number(r.quantity_on_hand || 0) * Number(r.average_unit_cost || 0), 0));
  const stockOutRisk = $derived(records.filter(r => r.is_low_stock).length);
  const totalAllocated = $derived(records.reduce((s, r) => s + Number(r.quantity_reserved || 0), 0));
  const totalOnHand = $derived(records.reduce((s, r) => s + Number(r.quantity_on_hand || 0), 0));

  function fmtNumber(value: string): string { return Number(value || 0).toLocaleString("en-US", { maximumFractionDigits: 2 }); }

  function buildParams(): Record<string, string> {
    const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize), ordering: "warehouse__name" };
    if (search.trim()) params.search = search.trim();
    if (warehouse) params.warehouse = warehouse;
    if (category) params["item__category"] = category;
    if (lowStockOnly) params.low_stock = "true";
    return params;
  }

  async function fetchStock() {
    loading = true;
    try {
      const res = await api.get<PaginatedResponse<InventoryStockRecord>>("/inventory/stocks/", buildParams());
      records = res.results;
      totalCount = res.count;
    } catch { records = []; totalCount = 0; }
    finally { loading = false; }
  }

  async function fetchWarehouses() {
    try {
      const res = await api.get<PaginatedResponse<InventoryWarehouse>>("/inventory/warehouses/", { page_size: "200", ordering: "name" });
      warehouses = res.results;
    } catch { warehouses = []; }
  }

  async function fetchItems() {
    try {
      const res = await api.get<PaginatedResponse<{ id: number; name: string; sku: string }>>("/inventory/items/", { page_size: "200", ordering: "name", is_active: "true" });
      items = res.results;
    } catch { items = []; }
  }

  async function submitAdjustment() {
    if (!adjustForm.item || !adjustForm.warehouse || !adjustForm.quantity) {
      toast.error("Required", "Item, warehouse, and quantity are required."); return;
    }
    adjustSaving = true;
    try {
      await api.post("/inventory/transactions/", {
        item: Number(adjustForm.item),
        warehouse: Number(adjustForm.warehouse),
        quantity: Number(adjustForm.quantity),
        transaction_type: "adjustment",
        notes: adjustForm.reason,
      });
      toast.success("Adjusted", "Stock adjustment recorded.");
      showAdjust = false;
      adjustForm = { item: "", warehouse: "", quantity: "", reason: "" };
      await fetchStock();
    } catch (err) {
      if (err instanceof ApiError) toast.error("Failed", Object.values(err.fieldErrors).flat().join(" ") || "Check the form.");
      else toast.error("Failed", "Could not save adjustment.");
    } finally { adjustSaving = false; }
  }

  function devFillAdjust() {
    if (items.length) adjustForm.item = String(items[Math.floor(Math.random() * items.length)].id);
    if (warehouses.length) adjustForm.warehouse = String(warehouses[Math.floor(Math.random() * warehouses.length)].id);
    adjustForm.quantity = String(Math.floor(Math.random() * 100 + 10));
    adjustForm.reason = ["Physical count correction", "Damage write-off", "Transfer from transit", "Cycle count adjustment"][Math.floor(Math.random() * 4)];
  }

  function reload() { currentPage = 1; fetchStock(); }

  onMount(() => { fetchWarehouses(); fetchStock(); fetchItems(); });
</script>

<svelte:head><title>Stock — Global Stock Master | developerOS</title></svelte:head>

<div class="space-y-5">
  <!-- Header -->
  <div class="flex items-start justify-between gap-3">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-pink-600">Inventory</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Global Stock Master</h1>
      <p class="mt-1 text-sm text-neutral-500">Granular tracking of metrics, availability, and reordering.</p>
    </div>
    <button onclick={() => { showAdjust = true; }} class="rounded-lg bg-pink-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-pink-700 shadow-sm whitespace-nowrap">Manual Stock Adjustment</button>
  </div>

  <!-- Metric Ribbon -->
  <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
    <div class="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-center">
      <p class="text-[9px] font-semibold text-emerald-400 uppercase tracking-wider">Total Valuation</p>
      <p class="mt-1 text-lg font-bold text-emerald-700 tabular-nums">{currency.format(totalValuation)}</p>
      <p class="text-[9px] text-emerald-400">real-time inventory cost</p>
    </div>
    <div class="rounded-xl border {stockOutRisk > 0 ? 'border-red-200 bg-red-50' : 'border-neutral-200 bg-white'} p-4 text-center">
      <p class="text-[9px] font-semibold {stockOutRisk > 0 ? 'text-red-400' : 'text-neutral-400'} uppercase tracking-wider">Stock-Out Risk</p>
      <p class="mt-1 text-2xl font-bold {stockOutRisk > 0 ? 'text-red-700' : 'text-neutral-900'} tabular-nums">{stockOutRisk}</p>
      <p class="text-[9px] {stockOutRisk > 0 ? 'text-red-400' : 'text-neutral-400'}">SKUs below reorder</p>
    </div>
    <div class="rounded-xl border border-amber-200 bg-amber-50 p-4 text-center">
      <p class="text-[9px] font-semibold text-amber-400 uppercase tracking-wider">Allocated (Reserved)</p>
      <p class="mt-1 text-2xl font-bold text-amber-700 tabular-nums">{totalAllocated.toLocaleString()}</p>
      <p class="text-[9px] text-amber-400">units tied to orders</p>
    </div>
    <div class="rounded-xl border border-neutral-200 bg-white p-4 text-center">
      <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Total On-Hand</p>
      <p class="mt-1 text-2xl font-bold text-neutral-900 tabular-nums">{totalOnHand.toLocaleString()}</p>
      <p class="text-[9px] text-neutral-400">{totalCount} records</p>
    </div>
  </div>

  <!-- Filters -->
  <section class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
    <div class="p-4 border-b border-neutral-100 bg-neutral-50 space-y-2">
      <!-- Filter Row 1 -->
      <div class="grid grid-cols-2 gap-2 sm:grid-cols-6">
        <div class="relative sm:col-span-2">
          <svg class="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
          <input class="w-full rounded-lg border border-neutral-200 py-2 pl-9 pr-3 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="Search item or warehouse" bind:value={search} oninput={reload} />
        </div>
        <select class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" bind:value={warehouse} onchange={reload}>
          <option value="">All warehouses</option>
          {#each warehouses as wh}<option value={String(wh.id)}>{wh.name}</option>{/each}
        </select>
        <select class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" bind:value={warehouseType} onchange={reload}>
          <option value="">All types</option>
          <option value="central">Central</option>
          <option value="site">Site Store</option>
          <option value="transit">Transit Hub</option>
          <option value="bonded">Bonded</option>
        </select>
        <select class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" bind:value={category} onchange={reload}>
          <option value="">All categories</option>
          {#each CATEGORY_OPTIONS as opt}<option value={opt.value}>{opt.label}</option>{/each}
        </select>
        <label class="inline-flex items-center gap-2 rounded-lg border {lowStockOnly ? 'border-red-300 bg-red-50' : 'border-neutral-200'} px-3 py-2 text-sm cursor-pointer {lowStockOnly ? 'text-red-700 font-semibold' : 'text-neutral-600'}">
          <input type="checkbox" bind:checked={lowStockOnly} onchange={reload} class="rounded border-neutral-300" />
          Low stock
        </label>
      </div>

      <!-- Bulk Action Bar -->
      {#if selectedIds.length > 0}
        <div class="flex items-center gap-3 rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-2.5">
          <span class="text-xs font-semibold text-indigo-700">{selectedIds.length} selected</span>
          <div class="flex-1"></div>
          <select bind:value={bulkAction} class="rounded-lg border border-indigo-200 bg-white px-3 py-1.5 text-xs font-medium text-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500">
            <option value="">Choose action...</option>
            <option value="transfer">Transfer Request</option>
            <option value="reorder">Bulk Reorder</option>
          </select>
          <button onclick={executeBulkAction} disabled={!bulkAction || bulkSaving} class="rounded-lg bg-indigo-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-40">
            {bulkSaving ? "Processing..." : "Execute"}
          </button>
          <button onclick={() => { selectedIds = []; }} class="rounded-lg border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-50">Clear</button>
        </div>
      {/if}
    </div>

    <!-- Intelligent Data Table -->
    <div class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-100/80">
            <th class="px-2 py-3 text-center w-10"><input type="checkbox" checked={selectedIds.length === records.length && records.length > 0} onchange={selectAll} class="rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900" /></th>
            <th class="px-4 py-3 text-left text-[10px] font-bold text-neutral-600 uppercase tracking-wider">Material / SKU</th>
            <th class="px-4 py-3 text-left text-[10px] font-bold text-neutral-600 uppercase tracking-wider">Warehouse</th>
            <th class="px-4 py-3 text-right text-[10px] font-bold text-neutral-600 uppercase tracking-wider">Current Stock</th>
            <th class="px-4 py-3 text-right text-[10px] font-bold text-neutral-600 uppercase tracking-wider">Reserved</th>
            <th class="px-4 py-3 text-right text-[10px] font-bold text-neutral-900 uppercase tracking-wider">Available</th>
            <th class="px-4 py-3 text-right text-[10px] font-bold text-neutral-600 uppercase tracking-wider">Reorder Level</th>
            <th class="px-4 py-3 text-right text-[10px] font-bold text-neutral-600 uppercase tracking-wider">Value</th>
            <th class="px-4 py-3 text-center text-[10px] font-bold text-neutral-600 uppercase tracking-wider">Status</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-50">
          {#if loading}
            <tr><td colspan="9" class="px-4 py-12 text-center text-neutral-400">Loading stock...</td></tr>
          {:else if records.length === 0}
            <tr><td colspan="9" class="px-4 py-12 text-center text-neutral-400">No stock records found.</td></tr>
          {:else}
            {#each records as row}
              {@const qty = Number(row.quantity_on_hand || 0)}
              {@const available = Number(row.available_quantity || 0)}
              {@const cost = Number(row.average_unit_cost || 0)}
              {@const value = qty * cost}
              {@const reorder = Number(row.reorder_level || 0)}
              {@const isOut = qty <= 0}
              {@const isLow = row.is_low_stock && !isOut}
              <tr class="hover:bg-neutral-50/80 cursor-pointer {isOut ? 'bg-red-50/40' : isLow ? 'bg-amber-50/30' : ''} {selectedIds.includes(row.id) ? 'bg-indigo-50/40' : ''}" onclick={() => toggleExpand(row)}>
                <!-- Checkbox -->
                <td class="px-2 py-3 text-center" onclick={(e) => e.stopPropagation()}>
                  <input type="checkbox" checked={selectedIds.includes(row.id)} onchange={() => toggleSelect(row.id)} class="rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900" />
                </td>
                <!-- Material / SKU -->
                <td class="px-4 py-3">
                  <p class="font-bold text-neutral-900" style="font-family: Raleway, sans-serif;">{row.item_name}</p>
                  <p class="text-[10px] text-neutral-400 mt-0.5 font-mono">{row.item_sku}</p>
                </td>

                <!-- Warehouse -->
                <td class="px-4 py-3">
                  <span class="inline-flex items-center rounded-md bg-neutral-100 border border-neutral-200 px-2 py-0.5 text-[10px] font-semibold text-neutral-700">{row.warehouse_name}</span>
                </td>

                <!-- Current Stock -->
                <td class="px-4 py-3 text-right tabular-nums text-neutral-800">{fmtNumber(row.quantity_on_hand)}</td>

                <!-- Reserved -->
                <td class="px-4 py-3 text-right tabular-nums italic {Number(row.quantity_reserved) > 0 ? 'text-neutral-600' : 'text-neutral-300'}">{fmtNumber(row.quantity_reserved)}</td>

                <!-- Available -->
                <td class="px-4 py-3 text-right font-bold tabular-nums {isOut ? 'text-red-700' : isLow ? 'text-amber-700' : 'text-emerald-700'}">
                  {fmtNumber(row.available_quantity)}
                </td>

                <!-- Reorder Level (inline editable) -->
                <td class="px-4 py-3 text-right">
                  {#if editingReorderId === row.id}
                    <div class="flex items-center justify-end gap-1">
                      <input type="number" step="1" min="0" bind:value={editingReorderValue}
                        class="w-20 rounded border border-indigo-300 bg-indigo-50 px-2 py-1 text-xs tabular-nums text-right focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        onkeydown={(e) => { if (e.key === 'Enter') saveReorderLevel(row); if (e.key === 'Escape') editingReorderId = null; }}
                      />
                      <button onclick={() => saveReorderLevel(row)} class="rounded bg-indigo-600 px-1.5 py-1 text-[9px] font-bold text-white hover:bg-indigo-700" title="Save">
                        <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" /></svg>
                      </button>
                      <button onclick={() => { editingReorderId = null; }} class="rounded bg-neutral-200 px-1.5 py-1 text-[9px] text-neutral-600 hover:bg-neutral-300" title="Cancel">
                        <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
                      </button>
                    </div>
                  {:else}
                    <button onclick={() => { editingReorderId = row.id; editingReorderValue = String(reorder); }}
                      class="tabular-nums text-neutral-500 hover:text-indigo-700 hover:underline cursor-pointer text-right" title="Click to edit">
                      {reorder > 0 ? fmtNumber(row.reorder_level) : "—"}
                    </button>
                  {/if}
                </td>

                <!-- Value -->
                <td class="px-4 py-3 text-right font-semibold tabular-nums text-emerald-700">{currency.format(value)}</td>

                <!-- Status -->
                <td class="px-4 py-3 text-center">
                  <div class="inline-flex items-center gap-1.5">
                    <span class="inline-block h-2 w-2 rounded-full {isOut ? 'bg-red-500' : isLow ? 'bg-amber-500' : 'bg-emerald-500'}"></span>
                    <span class="text-[10px] font-semibold {isOut ? 'text-red-700' : isLow ? 'text-amber-700' : 'text-emerald-700'}">
                      {isOut ? "Out" : isLow ? "Low" : "In Stock"}
                    </span>
                  </div>
                </td>
              </tr>

              <!-- Expanded Drill-down -->
              {#if expandedRowId === row.id}
                <tr class="bg-neutral-50/70">
                  <td colspan="9" class="px-4 pb-4 pt-0">
                    {#if expandedLoading}
                      <div class="py-4 text-center text-xs text-neutral-400">Loading details...</div>
                    {:else if expandedData}
                      <div class="grid gap-4 pt-3 md:grid-cols-2">
                        <!-- Recent Movement History -->
                        <div class="rounded-lg border border-neutral-200 bg-white overflow-hidden">
                          <div class="border-b border-neutral-100 bg-neutral-50 px-3 py-2">
                            <h4 class="text-[9px] font-bold text-neutral-500 uppercase tracking-widest">Recent Movement History</h4>
                          </div>
                          {#if expandedData.transactions.length === 0}
                            <div class="p-3 text-xs text-neutral-400 text-center">No recent transactions.</div>
                          {:else}
                            <div class="divide-y divide-neutral-50 max-h-48 overflow-y-auto">
                              {#each expandedData.transactions as tx}
                                <div class="px-3 py-2 flex items-center justify-between">
                                  <div>
                                    <span class="text-[10px] font-semibold text-neutral-900">{tx.type}</span>
                                    {#if tx.reference}<span class="text-[9px] text-neutral-400 ml-1">#{tx.reference}</span>{/if}
                                    {#if tx.notes}<p class="text-[9px] text-neutral-500 mt-0.5 truncate max-w-[200px]">{tx.notes}</p>{/if}
                                  </div>
                                  <div class="text-right shrink-0">
                                    <span class="text-[10px] font-bold tabular-nums {Number(tx.quantity) > 0 ? 'text-emerald-700' : 'text-red-700'}">{Number(tx.quantity) > 0 ? '+' : ''}{tx.quantity}</span>
                                    <p class="text-[8px] text-neutral-400">{tx.date}</p>
                                  </div>
                                </div>
                              {/each}
                            </div>
                          {/if}
                        </div>

                        <!-- Stock Details -->
                        <div class="rounded-lg border border-neutral-200 bg-white overflow-hidden">
                          <div class="border-b border-neutral-100 bg-neutral-50 px-3 py-2">
                            <h4 class="text-[9px] font-bold text-neutral-500 uppercase tracking-widest">Stock Details</h4>
                          </div>
                          <div class="p-3 space-y-2">
                            <div class="grid grid-cols-2 gap-2 text-xs">
                              <div><span class="text-[9px] text-neutral-400 uppercase font-semibold block">SKU</span><span class="font-mono text-neutral-900">{row.item_sku}</span></div>
                              <div><span class="text-[9px] text-neutral-400 uppercase font-semibold block">Category</span><span class="text-neutral-700 capitalize">{row.item_category.replace(/_/g, " ")}</span></div>
                              <div><span class="text-[9px] text-neutral-400 uppercase font-semibold block">Reorder Level</span><span class="text-neutral-700 tabular-nums">{fmtNumber(row.reorder_level)}</span></div>
                              <div><span class="text-[9px] text-neutral-400 uppercase font-semibold block">Target Stock</span><span class="text-neutral-700 tabular-nums">{fmtNumber(row.target_stock_level)}</span></div>
                              <div><span class="text-[9px] text-neutral-400 uppercase font-semibold block">Avg Unit Cost</span><span class="text-neutral-700 tabular-nums">{currency.format(Number(row.average_unit_cost))}</span></div>
                              <div><span class="text-[9px] text-neutral-400 uppercase font-semibold block">Last Transaction</span><span class="text-neutral-700">{row.last_transaction_at ? new Date(row.last_transaction_at).toLocaleDateString() : "—"}</span></div>
                            </div>
                          </div>
                        </div>
                      </div>
                    {/if}
                  </td>
                </tr>
              {/if}
            {/each}
          {/if}
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div class="flex items-center justify-between border-t border-neutral-100 px-4 py-3">
      <p class="text-xs text-neutral-400">{totalCount} records</p>
      <div class="flex items-center gap-2">
        <select bind:value={pageSize} onchange={reload} class="rounded-md border border-neutral-200 px-2 py-1 text-xs text-neutral-600">
          <option value={10}>10</option><option value={25}>25</option><option value={50}>50</option>
        </select>
        <button class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 disabled:opacity-40" onclick={() => { if (currentPage > 1) { currentPage -= 1; fetchStock(); } }} disabled={currentPage <= 1}>Prev</button>
        <span class="text-xs text-neutral-500">Page {currentPage} / {totalPages}</span>
        <button class="rounded-md border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-600 disabled:opacity-40" onclick={() => { if (currentPage < totalPages) { currentPage += 1; fetchStock(); } }} disabled={currentPage >= totalPages}>Next</button>
      </div>
    </div>
  </section>
</div>

<!-- Manual Stock Adjustment Modal -->
{#if showAdjust}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/30 backdrop-blur-sm" onclick={() => { showAdjust = false; }} aria-label="Close"></button>
    <div class="relative w-full max-w-md rounded-2xl border border-neutral-200 bg-white p-6 shadow-2xl">
      <h2 class="text-base font-semibold text-neutral-900 mb-4">Manual Stock Adjustment</h2>
      <div class="space-y-3">
        <label class="block text-sm"><span class="mb-1 block text-xs font-medium text-neutral-700">Item *</span>
          <select bind:value={adjustForm.item} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
            <option value="">Select item</option>
            {#each items as item}<option value={String(item.id)}>{item.sku} — {item.name}</option>{/each}
          </select>
        </label>
        <label class="block text-sm"><span class="mb-1 block text-xs font-medium text-neutral-700">Warehouse *</span>
          <select bind:value={adjustForm.warehouse} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
            <option value="">Select warehouse</option>
            {#each warehouses as wh}<option value={String(wh.id)}>{wh.name}</option>{/each}
          </select>
        </label>
        <label class="block text-sm"><span class="mb-1 block text-xs font-medium text-neutral-700">Quantity (+ to add, - to reduce) *</span>
          <input type="number" step="0.01" bind:value={adjustForm.quantity} placeholder="e.g. 50 or -10" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        </label>
        <label class="block text-sm"><span class="mb-1 block text-xs font-medium text-neutral-700">Reason / Notes</span>
          <textarea bind:value={adjustForm.reason} rows="2" placeholder="Reason for adjustment..." class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
        </label>
      </div>
      <div class="mt-5 flex justify-end gap-3">
        {#if isDev}<button type="button" onclick={devFillAdjust} class="mr-auto rounded-lg bg-orange-500 px-3 py-2 text-xs font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
        <button onclick={() => { showAdjust = false; }} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
        <button onclick={submitAdjustment} disabled={adjustSaving} class="rounded-lg bg-pink-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-pink-700 disabled:opacity-50">{adjustSaving ? "Saving..." : "Submit Adjustment"}</button>
      </div>
    </div>
  </div>
{/if}

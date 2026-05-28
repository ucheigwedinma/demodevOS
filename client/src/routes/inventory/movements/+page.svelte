<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import type {
    InventoryItemListItem,
    InventoryTransaction,
    InventoryTransactionType,
    InventoryWarehouse,
    PaginatedResponse,
    ProjectListItem,
    PurchaseOrderListItem,
    GoodsReceiptListItem,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  const MOVEMENT_TYPES: { value: InventoryTransactionType; label: string }[] = [
    { value: "receipt", label: "Receipt" },
    { value: "issue", label: "Issue" },
    { value: "adjustment_in", label: "Adjustment In" },
    { value: "adjustment_out", label: "Adjustment Out" },
    { value: "transfer_in", label: "Transfer In" },
    { value: "transfer_out", label: "Transfer Out" },
  ];

  let records = $state<InventoryTransaction[]>([]);
  let items = $state<InventoryItemListItem[]>([]);
  let warehouses = $state<InventoryWarehouse[]>([]);
  let projects = $state<ProjectListItem[]>([]);
  let purchaseOrders = $state<PurchaseOrderListItem[]>([]);
  let goodsReceipts = $state<GoodsReceiptListItem[]>([]);

  let loading = $state(true);
  let creating = $state(false);
  let showCreate = $state(false);

  let currentPage = $state(1);
  let pageSize = $state(25);
  let totalCount = $state(0);

  let search = $state("");
  let typeFilter = $state("");
  let warehouseFilter = $state("");

  let form = $state({
    transaction_type: "issue",
    warehouse: "",
    item: "",
    project: "",
    purchase_order: "",
    goods_receipt: "",
    goods_receipt_item: "",
    quantity: "1",
    unit_cost: "",
    transaction_date: new Date().toISOString().slice(0, 10),
    notes: "",
  });

  const totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));

  const filteredGoodsReceipts = $derived.by(() => {
    if (!form.purchase_order) return goodsReceipts;
    return goodsReceipts.filter((grn) => String(grn.purchase_order) === form.purchase_order);
  });

  function buildParams(): Record<string, string> {
    const params: Record<string, string> = {
      page: String(currentPage),
      page_size: String(pageSize),
      ordering: "-transaction_date",
    };
    if (search.trim()) params.search = search.trim();
    if (typeFilter) params.transaction_type = typeFilter;
    if (warehouseFilter) params.warehouse = warehouseFilter;
    return params;
  }

  async function fetchMovements() {
    loading = true;
    try {
      const res = await api.get<PaginatedResponse<InventoryTransaction>>("/inventory/transactions/", buildParams());
      records = res.results;
      totalCount = res.count;
    } catch {
      records = [];
      totalCount = 0;
      toast.error("Load failed", "Could not load inventory movements.");
    } finally {
      loading = false;
    }
  }

  async function fetchOptions() {
    try {
      const [itemRes, warehouseRes, projectRes, poRes, grnRes] = await Promise.all([
        api.get<PaginatedResponse<InventoryItemListItem>>("/inventory/items/", {
          page_size: "200",
          ordering: "name",
          is_active: "true",
        }),
        api.get<PaginatedResponse<InventoryWarehouse>>("/inventory/warehouses/", {
          page_size: "200",
          ordering: "name",
          is_active: "true",
        }),
        api.get<PaginatedResponse<ProjectListItem>>("/projects/", {
          page_size: "200",
          ordering: "name",
        }),
        api.get<PaginatedResponse<PurchaseOrderListItem>>("/procurement/purchase-orders/", {
          page_size: "200",
          ordering: "-issue_date",
        }),
        api.get<PaginatedResponse<GoodsReceiptListItem>>("/procurement/goods-receipts/", {
          page_size: "200",
          ordering: "-received_date",
        }),
      ]);
      items = itemRes.results;
      warehouses = warehouseRes.results;
      projects = projectRes.results;
      purchaseOrders = poRes.results;
      goodsReceipts = grnRes.results;

      if (!form.warehouse && warehouses.length > 0) {
        const preferred = warehouses.find((wh) => wh.is_default) ?? warehouses[0];
        form.warehouse = String(preferred.id);
      }
    } catch {
      items = [];
      warehouses = [];
      projects = [];
      purchaseOrders = [];
      goodsReceipts = [];
    }
  }

  async function createMovement() {
    if (!form.transaction_type || !form.item || !form.warehouse || !form.quantity) {
      toast.error("Validation", "Type, item, warehouse, and quantity are required.");
      return;
    }

    creating = true;
    try {
      await api.post("/inventory/transactions/", {
        transaction_type: form.transaction_type,
        item: Number(form.item),
        warehouse: Number(form.warehouse),
        project: form.project ? Number(form.project) : null,
        purchase_order: form.purchase_order ? Number(form.purchase_order) : null,
        goods_receipt: form.goods_receipt ? Number(form.goods_receipt) : null,
        goods_receipt_item: form.goods_receipt_item ? Number(form.goods_receipt_item) : null,
        quantity: form.quantity,
        unit_cost: form.unit_cost ? form.unit_cost : null,
        transaction_date: form.transaction_date,
        source_module: "inventory_manual",
        source_reference: "manual-entry",
        notes: form.notes.trim(),
      });

      toast.success("Recorded", "Inventory movement saved.");
      showCreate = false;
      form = {
        transaction_type: "issue",
        warehouse: warehouses.find((wh) => wh.is_default)?.id?.toString() ?? (warehouses[0]?.id?.toString() ?? ""),
        item: "",
        project: "",
        purchase_order: "",
        goods_receipt: "",
        goods_receipt_item: "",
        quantity: "1",
        unit_cost: "",
        transaction_date: new Date().toISOString().slice(0, 10),
        notes: "",
      };
      currentPage = 1;
      await fetchMovements();
    } catch {
      toast.error("Save failed", "Could not record movement.");
    } finally {
      creating = false;
    }
  }

  function fmtCurrency(value: string): string {
    return currency.format(value || 0);
  }

  function fmtDate(value: string): string {
    return new Date(value).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  const typeBadge: Record<string, string> = {
    receipt: "bg-emerald-50 text-emerald-700",
    issue: "bg-amber-50 text-amber-700",
    adjustment_in: "bg-blue-50 text-blue-700",
    adjustment_out: "bg-orange-50 text-orange-700",
    transfer_in: "bg-indigo-50 text-indigo-700",
    transfer_out: "bg-violet-50 text-violet-700",
  };

  $effect(() => {
    fetchOptions();
  });

  $effect(() => {
    fetchMovements();
  });
</script>

<div class="space-y-6">
  <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-pink-600">Inventory</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Stock Movements</h1>
      <p class="text-sm text-neutral-400 mt-1">Receipts, issues, and adjustments driving inventory balances.</p>
    </div>
    <button
      class="px-4 py-2 rounded-lg bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-800"
      onclick={() => (showCreate = !showCreate)}
    >
      {showCreate ? "Close" : "Record Movement"}
    </button>
  </div>

  {#if showCreate}
    <section class="bg-white rounded-xl border border-neutral-200 p-5 space-y-4">
      <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-500">New Movement</h2>
      <div class="grid grid-cols-1 md:grid-cols-4 gap-3">
        <label class="text-xs text-neutral-500">Type
          <select class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" bind:value={form.transaction_type}>
            {#each MOVEMENT_TYPES as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </label>
        <label class="text-xs text-neutral-500">Item
          <select class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" bind:value={form.item}>
            <option value="">Select item</option>
            {#each items as item}
              <option value={item.id}>{item.sku} - {item.name}</option>
            {/each}
          </select>
        </label>
        <label class="text-xs text-neutral-500">Warehouse
          <select class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" bind:value={form.warehouse}>
            <option value="">Select warehouse</option>
            {#each warehouses as wh}
              <option value={wh.id}>{wh.name}</option>
            {/each}
          </select>
        </label>
        <label class="text-xs text-neutral-500">Date
          <DateInput bind:value={form.transaction_date} />
        </label>
        <label class="text-xs text-neutral-500">Quantity
          <input type="number" min="0.001" step="0.001" class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" bind:value={form.quantity} />
        </label>
        <label class="text-xs text-neutral-500">Unit Cost
          <input type="number" min="0" step="0.01" class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" bind:value={form.unit_cost} />
        </label>
        <label class="text-xs text-neutral-500">Project (optional)
          <select class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" bind:value={form.project}>
            <option value="">No project link</option>
            {#each projects as project}
              <option value={project.id}>{project.name}</option>
            {/each}
          </select>
        </label>
        <label class="text-xs text-neutral-500">Purchase Order (optional)
          <select class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" bind:value={form.purchase_order}>
            <option value="">No PO link</option>
            {#each purchaseOrders as po}
              <option value={po.id}>{po.po_number} - {po.vendor_name}</option>
            {/each}
          </select>
        </label>
        <label class="text-xs text-neutral-500">Goods Receipt (optional)
          <select class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" bind:value={form.goods_receipt}>
            <option value="">No GRN link</option>
            {#each filteredGoodsReceipts as grn}
              <option value={grn.id}>{grn.grn_number} - {grn.vendor_name}</option>
            {/each}
          </select>
        </label>
      </div>
      <label class="text-xs text-neutral-500 block">Notes
        <textarea rows="2" class="mt-1 w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" bind:value={form.notes}></textarea>
      </label>
      <button
        class="px-4 py-2 rounded-lg bg-neutral-900 text-white text-sm font-medium hover:bg-neutral-800 disabled:opacity-60"
        onclick={createMovement}
        disabled={creating}
      >
        {creating ? "Saving..." : "Save Movement"}
      </button>
    </section>
  {/if}

  <section class="bg-white rounded-xl border border-neutral-200 p-4">
    <div class="grid grid-cols-1 md:grid-cols-4 gap-3">
      <input
        class="rounded-lg border border-neutral-200 px-3 py-2 text-sm"
        placeholder="Search item, project, PO, notes"
        bind:value={search}
        oninput={() => {
          currentPage = 1;
          fetchMovements();
        }}
      />
      <select class="rounded-lg border border-neutral-200 px-3 py-2 text-sm" bind:value={typeFilter} onchange={() => { currentPage = 1; fetchMovements(); }}>
        <option value="">All movement types</option>
        {#each MOVEMENT_TYPES as option}
          <option value={option.value}>{option.label}</option>
        {/each}
      </select>
      <select class="rounded-lg border border-neutral-200 px-3 py-2 text-sm" bind:value={warehouseFilter} onchange={() => { currentPage = 1; fetchMovements(); }}>
        <option value="">All warehouses</option>
        {#each warehouses as wh}
          <option value={wh.id}>{wh.name}</option>
        {/each}
      </select>
      <select class="rounded-lg border border-neutral-200 px-3 py-2 text-sm" bind:value={pageSize} onchange={() => { currentPage = 1; fetchMovements(); }}>
        <option value={10}>10 rows</option>
        <option value={25}>25 rows</option>
        <option value={50}>50 rows</option>
      </select>
    </div>

    <div class="mt-4 overflow-x-auto">
      <table class="min-w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-100 text-left text-[11px] uppercase tracking-wider text-neutral-400">
            <th class="px-3 py-2">Date</th>
            <th class="px-3 py-2">Type</th>
            <th class="px-3 py-2">Item</th>
            <th class="px-3 py-2">Warehouse</th>
            <th class="px-3 py-2">Project</th>
            <th class="px-3 py-2 text-right">Qty</th>
            <th class="px-3 py-2 text-right">Cost</th>
            <th class="px-3 py-2">Source</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-50">
          {#if loading}
            <tr><td colspan="8" class="px-3 py-10 text-center text-neutral-400">Loading movements...</td></tr>
          {:else if records.length === 0}
            <tr><td colspan="8" class="px-3 py-10 text-center text-neutral-400">No movements found</td></tr>
          {:else}
            {#each records as row}
              <tr class="hover:bg-neutral-50">
                <td class="px-3 py-3 text-sm text-neutral-600">{fmtDate(row.transaction_date)}</td>
                <td class="px-3 py-3">
                  <span class={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${typeBadge[row.transaction_type] ?? "bg-neutral-100 text-neutral-600"}`}>
                    {row.transaction_type_display}
                  </span>
                </td>
                <td class="px-3 py-3">
                  <p class="text-sm text-neutral-900">{row.item_name}</p>
                  <p class="text-xs text-neutral-400">{row.item_sku}</p>
                </td>
                <td class="px-3 py-3 text-sm text-neutral-600">{row.warehouse_name}</td>
                <td class="px-3 py-3 text-sm text-neutral-600">{row.project_name ?? "-"}</td>
                <td class="px-3 py-3 text-sm text-right text-neutral-700 tabular-nums">{Number(row.quantity).toLocaleString()}</td>
                <td class="px-3 py-3 text-sm text-right text-neutral-700 tabular-nums">{fmtCurrency(row.total_cost)}</td>
                <td class="px-3 py-3 text-xs text-neutral-500">{row.source_module || "manual"}</td>
              </tr>
            {/each}
          {/if}
        </tbody>
      </table>
    </div>

    <div class="mt-4 flex items-center justify-between">
      <p class="text-xs text-neutral-400">{totalCount} movements</p>
      <div class="flex items-center gap-2">
        <button class="px-3 py-1.5 text-sm rounded-lg border border-neutral-200 text-neutral-600 disabled:opacity-40" onclick={() => { if (currentPage > 1) { currentPage -= 1; fetchMovements(); } }} disabled={currentPage <= 1}>Prev</button>
        <span class="text-sm text-neutral-500">Page {currentPage} of {totalPages}</span>
        <button class="px-3 py-1.5 text-sm rounded-lg border border-neutral-200 text-neutral-600 disabled:opacity-40" onclick={() => { if (currentPage < totalPages) { currentPage += 1; fetchMovements(); } }} disabled={currentPage >= totalPages}>Next</button>
      </div>
    </div>
  </section>
</div>

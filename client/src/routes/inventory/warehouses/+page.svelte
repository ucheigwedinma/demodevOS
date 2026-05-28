<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import type { PaginatedResponse, ProjectListItem } from "$lib/types";
  import { onMount } from "svelte";

  interface TopMaterial { name: string; category: string; qty: string; }
  interface WarehouseData {
    id: number; code: string; name: string; location: string; warehouse_type: string;
    project_name: string; is_default: boolean; contact_person: string; contact_phone: string;
    gps_coordinates: string; storage_capacity: number; item_count: number;
    total_quantity: string; stock_value: string; capacity_pct: number; capacity_alert: boolean;
    top_materials: TopMaterial[];
  }
  interface DashboardData {
    total_locations: number; capacity_alert_count: number;
    in_transit_value: string; total_stock_value: string;
    warehouses: WarehouseData[];
  }

  const TYPE_LABELS: Record<string, string> = { central: "Central", site: "Site Store", transit: "Transit Hub", bonded: "Bonded" };
  const TYPE_COLORS: Record<string, string> = { central: "bg-indigo-100 text-indigo-700", site: "bg-emerald-100 text-emerald-700", transit: "bg-amber-100 text-amber-700", bonded: "bg-violet-100 text-violet-700" };

  let loading = $state(true);
  let dashboard = $state<DashboardData | null>(null);
  let projects = $state<ProjectListItem[]>([]);
  let search = $state("");

  // Create modal
  let showCreate = $state(false);
  let creating = $state(false);
  let form = $state({ code: "", name: "", location: "", project: "", warehouse_type: "site", storage_capacity_units: "", contact_person: "", contact_phone: "", gps_coordinates: "", is_active: true, is_default: false });

  // Detail drawer
  let showDetail = $state(false);
  let detailWh = $state<WarehouseData | null>(null);
  let detailGRNs = $state<{ id: number; grn_number: string; status: string; received_date: string; received_by: string; po_number: string; vendor_name: string; item_count: number }[]>([]);
  let detailGRNsLoading = $state(false);

  async function openDetail(wh: WarehouseData) {
    detailWh = wh;
    showDetail = true;
    detailGRNs = [];
    detailGRNsLoading = true;
    try {
      // Fetch recent GRNs for this warehouse (items issued to this warehouse)
      const res = await api.get<{ results: any[] }>("/procurement/goods-receipts/", {
        page_size: "10",
        ordering: "-received_date",
      });
      // Filter by warehouse — GRNs don't have warehouse FK directly,
      // so we show all recent GRNs. A proper filter would need backend support.
      detailGRNs = (res.results || []).map((g: any) => ({
        id: g.id,
        grn_number: g.grn_number,
        status: g.status,
        received_date: g.received_date,
        received_by: g.received_by,
        po_number: g.po_number || g.purchase_order_number || "",
        vendor_name: g.vendor_name || "",
        item_count: g.item_count || 0,
      })).slice(0, 8);
    } catch { detailGRNs = []; }
    finally { detailGRNsLoading = false; }
  }

  // Inventory modal (View Inventory)
  let showInventory = $state(false);
  let inventoryWh = $state<WarehouseData | null>(null);
  let inventoryLoading = $state(false);
  let inventoryItems = $state<{ id: number; item_name: string; category: string; quantity_on_hand: string; unit_of_measure: string; default_unit_cost: string }[]>([]);

  async function openInventory(wh: WarehouseData, e?: Event) {
    if (e) e.stopPropagation();
    inventoryWh = wh;
    showInventory = true;
    inventoryLoading = true;
    try {
      const res = await api.get<{ results: any[] }>("/inventory/stocks/", { warehouse: String(wh.id), page_size: "200" });
      inventoryItems = res.results.map((s: any) => ({
        id: s.id,
        item_name: s.item_name || s.item?.name || "Unknown",
        category: s.item_category || s.item?.category || "",
        quantity_on_hand: s.quantity_on_hand || "0",
        unit_of_measure: s.item_unit || s.item?.unit_of_measure || "ea",
        default_unit_cost: s.item_unit_cost || s.item?.default_unit_cost || "0",
      }));
    } catch { toast.error("Load failed", "Could not load warehouse stock."); inventoryItems = []; }
    finally { inventoryLoading = false; }
  }

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  const filtered = $derived.by(() => {
    if (!dashboard) return [];
    if (!search.trim()) return dashboard.warehouses;
    const q = search.trim().toLowerCase();
    return dashboard.warehouses.filter(w => w.name.toLowerCase().includes(q) || w.code.toLowerCase().includes(q) || w.location.toLowerCase().includes(q));
  });

  async function loadDashboard() {
    loading = true;
    try {
      const [dashRes, projRes] = await Promise.all([
        api.get<DashboardData>("/inventory/warehouse-dashboard/"),
        api.get<PaginatedResponse<ProjectListItem>>("/projects/", { page_size: "100", ordering: "name" }),
      ]);
      dashboard = dashRes;
      projects = projRes.results;
    } catch { toast.error("Load failed", "Could not load warehouse data."); }
    finally { loading = false; }
  }

  async function createWarehouse() {
    if (!form.code.trim() || !form.name.trim()) { toast.error("Required", "Code and Name are required."); return; }
    creating = true;
    try {
      const payload: Record<string, unknown> = {
        code: form.code.trim(), name: form.name.trim(), location: form.location.trim(),
        warehouse_type: form.warehouse_type, is_active: form.is_active, is_default: form.is_default,
        contact_person: form.contact_person, contact_phone: form.contact_phone,
        gps_coordinates: form.gps_coordinates,
        storage_capacity_units: form.storage_capacity_units ? Number(form.storage_capacity_units) : 0,
      };
      if (form.project) payload.project = Number(form.project);
      await api.post("/inventory/warehouses/", payload);
      toast.success("Created", `Warehouse "${form.name}" created.`);
      showCreate = false;
      form = { code: "", name: "", location: "", project: "", warehouse_type: "site", storage_capacity_units: "", contact_person: "", contact_phone: "", gps_coordinates: "", is_active: true, is_default: false };
      await loadDashboard();
    } catch (err) {
      if (err instanceof ApiError) toast.error("Failed", Object.values(err.fieldErrors).flat().join(" ") || "Check the form.");
      else toast.error("Failed", "Could not create warehouse.");
    } finally { creating = false; }
  }

  function devFill() {
    const names = ["Central Store — Abuja", "Lekki Phase 2 Site Store", "Ikoyi Transit Hub", "Port Harcourt Bonded", "Victoria Island Store", "Ikeja Logistics Node"];
    const codes = ["WH-ABJ-01", "WH-LKI-02", "WH-IKY-03", "WH-PHC-04", "WH-VI-05", "WH-IKJ-06"];
    const locs = ["Plot 12, Jabi District, Abuja", "Block C, Lekki Free Zone", "17 Alfred Rewane Rd, Ikoyi", "Trans Amadi Industrial, PH", "21 Adeola Odeku, VI", "15 Oregun Road, Ikeja"];
    const types = ["central", "site", "transit", "bonded", "site", "central"] as const;
    const idx = Math.floor(Math.random() * names.length);
    form = { ...form, code: codes[idx], name: names[idx], location: locs[idx], warehouse_type: types[idx], storage_capacity_units: String(Math.floor(Math.random() * 5000 + 500)), contact_person: "Store Manager", contact_phone: "+234 80" + String(Math.floor(Math.random() * 90000000 + 10000000)), gps_coordinates: `${(6.4 + Math.random() * 0.2).toFixed(4)},${(3.3 + Math.random() * 0.3).toFixed(4)}` };
  }

  onMount(() => { loadDashboard(); });
</script>

<svelte:head><title>Warehouses — Logistics Nodes | developerOS</title></svelte:head>

<div class="space-y-5">
  <!-- Header -->
  <div class="flex items-start justify-between gap-3">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-pink-600">Inventory</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Logistics Nodes</h1>
      <p class="mt-1 text-sm text-neutral-500">High-level logistics overview and site-specific command center.</p>
    </div>
    <button onclick={() => { showCreate = true; }} class="rounded-lg bg-pink-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-pink-700 shadow-sm">+ New Warehouse</button>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-20">
      <div class="h-7 w-7 rounded-full border-2 border-neutral-200 border-t-neutral-900 animate-spin"></div>
    </div>
  {:else if dashboard}

    <!-- Metric Ribbon -->
    <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <div class="rounded-xl border border-neutral-200 bg-white p-4 text-center">
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Total Locations</p>
        <p class="mt-1 text-2xl font-bold text-neutral-900 tabular-nums">{dashboard.total_locations}</p>
        <p class="text-[9px] text-neutral-400">active sites</p>
      </div>
      <div class="rounded-xl border {dashboard.capacity_alert_count > 0 ? 'border-red-200 bg-red-50' : 'border-neutral-200 bg-white'} p-4 text-center">
        <p class="text-[9px] font-semibold {dashboard.capacity_alert_count > 0 ? 'text-red-400' : 'text-neutral-400'} uppercase tracking-wider">Capacity Alert</p>
        <p class="mt-1 text-2xl font-bold {dashboard.capacity_alert_count > 0 ? 'text-red-700' : 'text-neutral-900'} tabular-nums">{dashboard.capacity_alert_count}</p>
        <p class="text-[9px] {dashboard.capacity_alert_count > 0 ? 'text-red-400' : 'text-neutral-400'}">sites &gt;90% full</p>
      </div>
      <div class="rounded-xl border border-amber-200 bg-amber-50 p-4 text-center">
        <p class="text-[9px] font-semibold text-amber-400 uppercase tracking-wider">In-Transit Value</p>
        <p class="mt-1 text-lg font-bold text-amber-700 tabular-nums">{currency.format(Number(dashboard.in_transit_value))}</p>
        <p class="text-[9px] text-amber-400">materials moving</p>
      </div>
      <div class="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-center">
        <p class="text-[9px] font-semibold text-emerald-400 uppercase tracking-wider">Total Stock Value</p>
        <p class="mt-1 text-lg font-bold text-emerald-700 tabular-nums">{currency.format(Number(dashboard.total_stock_value))}</p>
        <p class="text-[9px] text-emerald-400">across all sites</p>
      </div>
    </div>

    <!-- Search -->
    <div class="relative">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
      <input type="text" bind:value={search} placeholder="Search warehouses..." class="w-full rounded-xl border border-neutral-200 bg-white py-2.5 pl-10 pr-4 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
    </div>

    <!-- Location Grid (Glassmorphic Cards) -->
    <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {#each filtered as wh}
        {@const pct = wh.capacity_pct}
        {@const circumference = 2 * Math.PI * 38}
        {@const dashOffset = circumference - (Math.min(100, pct) / 100) * circumference}
        {@const gaugeColor = pct > 90 ? '#ef4444' : pct > 70 ? '#f59e0b' : '#10b981'}
        <div class="rounded-xl border {wh.capacity_alert ? 'border-red-200' : 'border-neutral-200'} bg-white/90 overflow-hidden hover:shadow-lg transition-shadow" style="backdrop-filter: blur(10px)">
          <!-- Card Header -->
          <div class="px-4 py-3 border-b border-neutral-100 bg-neutral-50/80 flex items-center justify-between">
            <div class="flex items-center gap-2 min-w-0">
              <span class="rounded-full border px-2 py-0.5 text-[9px] font-bold {TYPE_COLORS[wh.warehouse_type] || 'bg-neutral-100 text-neutral-600'}">{TYPE_LABELS[wh.warehouse_type] || wh.warehouse_type}</span>
              <h3 class="text-sm font-semibold text-neutral-900 truncate">{wh.name}</h3>
            </div>
            {#if wh.is_default}
              <span class="rounded-full bg-blue-100 text-blue-700 px-2 py-0.5 text-[9px] font-bold shrink-0">Default</span>
            {/if}
          </div>

          <!-- Card Body -->
          <div class="p-4">
            <div class="flex gap-4">
              <!-- Circular Gauge -->
              <div class="shrink-0 relative" style="width: 88px; height: 88px;">
                <svg viewBox="0 0 88 88" class="w-full h-full -rotate-90">
                  <circle cx="44" cy="44" r="38" fill="none" stroke="#f5f5f5" stroke-width="6" />
                  <circle cx="44" cy="44" r="38" fill="none" stroke={gaugeColor} stroke-width="6"
                    stroke-dasharray={String(circumference)} stroke-dashoffset={String(dashOffset)}
                    stroke-linecap="round" class="transition-all duration-500" />
                </svg>
                <div class="absolute inset-0 flex flex-col items-center justify-center">
                  <span class="text-lg font-bold tabular-nums" style="color: {gaugeColor}">{wh.storage_capacity > 0 ? pct : 0}%</span>
                  <span class="text-[7px] text-neutral-400 uppercase font-semibold">Capacity</span>
                </div>
              </div>

              <!-- Info Column -->
              <div class="flex-1 min-w-0 space-y-2">
                <!-- Top Materials -->
                <div>
                  <p class="text-[8px] font-semibold text-neutral-400 uppercase tracking-wider mb-1">Primary Materials</p>
                  {#if wh.top_materials && wh.top_materials.length > 0}
                    {#each wh.top_materials as mat}
                      <div class="flex items-center justify-between text-[10px] leading-relaxed">
                        <span class="text-neutral-700 truncate">{mat.name}</span>
                        <span class="text-neutral-500 tabular-nums shrink-0 ml-2">{Number(mat.qty).toLocaleString()}</span>
                      </div>
                    {/each}
                  {:else}
                    <p class="text-[10px] text-neutral-400">No stock</p>
                  {/if}
                </div>

                <!-- Personnel -->
                <div>
                  <p class="text-[8px] font-semibold text-neutral-400 uppercase tracking-wider">Store Keeper</p>
                  <p class="text-[10px] text-neutral-700">{wh.contact_person || "Unassigned"}</p>
                </div>
              </div>
            </div>

            <!-- Metrics Strip -->
            <div class="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-neutral-100">
              <div class="text-center">
                <p class="text-base font-bold text-neutral-900 tabular-nums">{wh.item_count}</p>
                <p class="text-[7px] text-neutral-400 uppercase font-semibold">Items</p>
              </div>
              <div class="text-center">
                <p class="text-base font-bold text-neutral-900 tabular-nums">{Number(wh.total_quantity).toLocaleString()}</p>
                <p class="text-[7px] text-neutral-400 uppercase font-semibold">Units</p>
              </div>
              <div class="text-center">
                <p class="text-sm font-bold text-emerald-700 tabular-nums">{currency.format(Number(wh.stock_value))}</p>
                <p class="text-[7px] text-neutral-400 uppercase font-semibold">Value</p>
              </div>
            </div>
          </div>

          <!-- Card Actions -->
          <div class="flex border-t border-neutral-100">
            <button type="button" onclick={(e) => openInventory(wh, e)} class="flex-1 py-2.5 text-[10px] font-semibold text-indigo-700 hover:bg-indigo-50 transition-colors text-center border-r border-neutral-100">
              View Inventory
            </button>
            <button type="button" onclick={() => openDetail(wh)} class="flex-1 py-2.5 text-[10px] font-semibold text-neutral-600 hover:bg-neutral-50 transition-colors text-center">
              Details
            </button>
          </div>
        </div>
      {:else}
        <div class="col-span-full rounded-xl border border-neutral-200 bg-white p-8 text-center">
          <p class="text-sm text-neutral-400">No warehouses found.</p>
        </div>
      {/each}
    </div>

  {/if}
</div>

<!-- Detail Drawer -->
{#if showDetail && detailWh}
  <div class="fixed inset-0 z-50 flex justify-end">
    <button class="absolute inset-0 bg-black/30 backdrop-blur-sm" onclick={() => { showDetail = false; detailWh = null; }} aria-label="Close"></button>
    <div class="relative w-full max-w-md bg-white shadow-2xl overflow-y-auto">
      <div class="bg-neutral-900 px-5 py-4 flex items-start justify-between">
        <div>
          <h2 class="text-lg font-semibold text-white">{detailWh.name}</h2>
          <p class="text-xs text-neutral-400 mt-0.5">{detailWh.code}</p>
          <div class="flex gap-2 mt-2">
            <span class="rounded-full border px-2 py-0.5 text-[10px] font-semibold {TYPE_COLORS[detailWh.warehouse_type] || ''}">{TYPE_LABELS[detailWh.warehouse_type] || detailWh.warehouse_type}</span>
            {#if detailWh.is_default}<span class="rounded-full bg-blue-100 text-blue-700 px-2 py-0.5 text-[10px] font-bold">Default</span>{/if}
          </div>
        </div>
        <button onclick={() => { showDetail = false; detailWh = null; }} class="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-800 hover:text-white" aria-label="Close">
          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
        </button>
      </div>

      <div class="p-5 space-y-4">
        <div class="grid grid-cols-2 gap-3">
          <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
            <p class="text-[9px] font-semibold text-neutral-400 uppercase">Location</p>
            <p class="mt-1 text-sm text-neutral-900">{detailWh.location || "—"}</p>
          </div>
          <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
            <p class="text-[9px] font-semibold text-neutral-400 uppercase">Project</p>
            <p class="mt-1 text-sm text-neutral-900">{detailWh.project_name || "—"}</p>
          </div>
          <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
            <p class="text-[9px] font-semibold text-neutral-400 uppercase">Contact</p>
            <p class="mt-1 text-sm text-neutral-900">{detailWh.contact_person || "—"}</p>
            {#if detailWh.contact_phone}<p class="text-[10px] text-neutral-500">{detailWh.contact_phone}</p>{/if}
          </div>
          <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
            <p class="text-[9px] font-semibold text-neutral-400 uppercase">GPS</p>
            <p class="mt-1 text-sm text-neutral-900 tabular-nums">{detailWh.gps_coordinates || "—"}</p>
          </div>
        </div>

        <!-- Stock KPIs -->
        <div class="grid grid-cols-3 gap-3">
          <div class="rounded-xl border border-neutral-200 bg-white p-3 text-center">
            <p class="text-[9px] font-semibold text-neutral-400 uppercase">Items</p>
            <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{detailWh.item_count}</p>
          </div>
          <div class="rounded-xl border border-neutral-200 bg-white p-3 text-center">
            <p class="text-[9px] font-semibold text-neutral-400 uppercase">Total Qty</p>
            <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{Number(detailWh.total_quantity).toLocaleString()}</p>
          </div>
          <div class="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-center">
            <p class="text-[9px] font-semibold text-emerald-400 uppercase">Value</p>
            <p class="mt-1 text-lg font-bold text-emerald-700 tabular-nums">{currency.format(Number(detailWh.stock_value))}</p>
          </div>
        </div>

        <!-- Capacity -->
        {#if detailWh.storage_capacity > 0}
          <div class="rounded-xl border {detailWh.capacity_alert ? 'border-red-200 bg-red-50/50' : 'border-neutral-200'} p-4">
            <div class="flex items-center justify-between mb-2">
              <span class="text-[10px] font-semibold text-neutral-500 uppercase">Storage Capacity</span>
              <span class="text-sm font-bold tabular-nums {detailWh.capacity_pct > 90 ? 'text-red-700' : detailWh.capacity_pct > 70 ? 'text-amber-700' : 'text-emerald-700'}">{detailWh.capacity_pct}%</span>
            </div>
            <div class="h-2.5 rounded-full bg-neutral-100 overflow-hidden">
              <div class="h-full rounded-full transition-all {detailWh.capacity_pct > 90 ? 'bg-red-500' : detailWh.capacity_pct > 70 ? 'bg-amber-500' : 'bg-emerald-500'}" style="width: {Math.min(100, detailWh.capacity_pct)}%"></div>
            </div>
            <p class="mt-1 text-[10px] text-neutral-500">{Number(detailWh.total_quantity).toLocaleString()} / {detailWh.storage_capacity.toLocaleString()} units</p>
          </div>
        {/if}

        <!-- Site Map -->
        {#if detailWh.gps_coordinates}
          {@const coords = detailWh.gps_coordinates.split(",")}
          <div class="rounded-xl border border-neutral-200 overflow-hidden">
            <div class="border-b border-neutral-100 bg-neutral-50 px-4 py-2">
              <h4 class="text-[9px] font-semibold text-neutral-400 uppercase tracking-widest">Site Location</h4>
            </div>
            <div class="h-40 bg-neutral-100 relative flex items-center justify-center">
              <div class="text-center">
                <svg class="mx-auto h-8 w-8 text-pink-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" /><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1 1 15 0Z" /></svg>
                <p class="text-xs font-semibold text-neutral-700 mt-1 tabular-nums">{coords[0]?.trim()}, {coords[1]?.trim()}</p>
                <p class="text-[9px] text-neutral-400 mt-0.5">{detailWh.location}</p>
              </div>
            </div>
          </div>
        {/if}

        <!-- Top Materials -->
        {#if detailWh.top_materials && detailWh.top_materials.length > 0}
          <div class="rounded-xl border border-neutral-200 overflow-hidden">
            <div class="border-b border-neutral-100 bg-neutral-50 px-4 py-2">
              <h4 class="text-[9px] font-semibold text-neutral-400 uppercase tracking-widest">Top Materials</h4>
            </div>
            <div class="divide-y divide-neutral-50">
              {#each detailWh.top_materials as mat}
                <div class="px-4 py-2.5 flex items-center justify-between">
                  <div>
                    <p class="text-sm font-medium text-neutral-900">{mat.name}</p>
                    <p class="text-[9px] text-neutral-400 capitalize">{mat.category.replace(/_/g, " ")}</p>
                  </div>
                  <span class="text-sm font-bold text-neutral-900 tabular-nums">{Number(mat.qty).toLocaleString()}</span>
                </div>
              {/each}
            </div>
          </div>
        {/if}

        <!-- Recent GRNs -->
        <div class="rounded-xl border border-neutral-200 overflow-hidden">
          <div class="border-b border-neutral-100 bg-neutral-50 px-4 py-2">
            <h4 class="text-[9px] font-semibold text-neutral-400 uppercase tracking-widest">Recent Goods Receipts</h4>
          </div>
          {#if detailGRNsLoading}
            <div class="p-4 text-center text-xs text-neutral-400">Loading...</div>
          {:else if detailGRNs.length === 0}
            <div class="p-4 text-center text-xs text-neutral-400">No recent receipts.</div>
          {:else}
            <div class="divide-y divide-neutral-50">
              {#each detailGRNs as grn}
                <div class="px-4 py-2.5">
                  <div class="flex items-center justify-between">
                    <span class="text-xs font-semibold text-neutral-900">{grn.grn_number}</span>
                    <span class="rounded-full border px-2 py-0.5 text-[9px] font-semibold {grn.status === 'accepted' ? 'bg-emerald-100 text-emerald-700' : grn.status === 'rejected' ? 'bg-red-100 text-red-700' : grn.status === 'pending' ? 'bg-amber-100 text-amber-700' : 'bg-neutral-100 text-neutral-600'}">{grn.status}</span>
                  </div>
                  <div class="flex items-center justify-between mt-0.5 text-[10px] text-neutral-500">
                    <span>PO: {grn.po_number} | {grn.vendor_name}</span>
                    <span class="tabular-nums">{grn.received_date}</span>
                  </div>
                </div>
              {/each}
            </div>
          {/if}
        </div>

        <!-- Quick Actions -->
        <div class="flex gap-2">
          <button type="button" onclick={(e) => { if (detailWh) openInventory(detailWh, e); }} class="flex-1 rounded-xl bg-indigo-600 py-2.5 text-xs font-semibold text-white hover:bg-indigo-700 text-center">View Full Inventory</button>
        </div>
      </div>
    </div>
  </div>
{/if}

<!-- Inventory Modal (View Inventory filtered to this warehouse) -->
{#if showInventory && inventoryWh}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/30 backdrop-blur-sm" onclick={() => { showInventory = false; }} aria-label="Close"></button>
    <div class="relative w-full max-w-3xl max-h-[85vh] rounded-2xl bg-white shadow-2xl overflow-hidden flex flex-col">
      <!-- Header -->
      <div class="bg-neutral-900 px-6 py-4 flex items-center justify-between shrink-0">
        <div>
          <h2 class="text-lg font-semibold text-white">{inventoryWh.name}</h2>
          <p class="text-xs text-neutral-400 mt-0.5">{inventoryWh.code} — {inventoryWh.item_count} items, {currency.format(Number(inventoryWh.stock_value))} total value</p>
        </div>
        <button onclick={() => { showInventory = false; }} class="rounded-lg p-1.5 text-neutral-400 hover:bg-neutral-800 hover:text-white" aria-label="Close">
          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
        </button>
      </div>

      <!-- Stock Table -->
      <div class="flex-1 overflow-y-auto">
        {#if inventoryLoading}
          <div class="p-12 text-center text-sm text-neutral-400">Loading stock data...</div>
        {:else if inventoryItems.length === 0}
          <div class="p-12 text-center">
            <p class="text-sm text-neutral-500">No stock items in this warehouse.</p>
          </div>
        {:else}
          <table class="w-full text-sm">
            <thead class="sticky top-0 bg-neutral-50 z-10">
              <tr class="border-b border-neutral-100">
                <th class="px-5 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase">Material</th>
                <th class="px-5 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase">Category</th>
                <th class="px-5 py-2.5 text-center text-[10px] font-semibold text-neutral-500 uppercase">On Hand</th>
                <th class="px-5 py-2.5 text-center text-[10px] font-semibold text-neutral-500 uppercase">Unit</th>
                <th class="px-5 py-2.5 text-right text-[10px] font-semibold text-neutral-500 uppercase">Unit Cost</th>
                <th class="px-5 py-2.5 text-right text-[10px] font-semibold text-neutral-500 uppercase">Total Value</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-50">
              {#each inventoryItems as item}
                <tr class="hover:bg-neutral-50">
                  <td class="px-5 py-3 font-medium text-neutral-900">{item.item_name}</td>
                  <td class="px-5 py-3 text-neutral-600 capitalize">{item.category.replace(/_/g, " ")}</td>
                  <td class="px-5 py-3 text-center font-semibold tabular-nums text-neutral-900">{Number(item.quantity_on_hand).toLocaleString()}</td>
                  <td class="px-5 py-3 text-center text-neutral-500">{item.unit_of_measure}</td>
                  <td class="px-5 py-3 text-right tabular-nums text-neutral-600">{currency.format(Number(item.default_unit_cost))}</td>
                  <td class="px-5 py-3 text-right font-semibold tabular-nums text-emerald-700">{currency.format(Number(item.quantity_on_hand) * Number(item.default_unit_cost))}</td>
                </tr>
              {/each}
            </tbody>
            <tfoot>
              <tr class="border-t border-neutral-200 bg-neutral-50">
                <td colspan="5" class="px-5 py-3 text-right text-xs font-bold text-neutral-900 uppercase">Total</td>
                <td class="px-5 py-3 text-right font-bold text-emerald-700 tabular-nums">{currency.format(Number(inventoryWh.stock_value))}</td>
              </tr>
            </tfoot>
          </table>
        {/if}
      </div>
    </div>
  </div>
{/if}

<!-- Create Modal -->
{#if showCreate}
  <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" style="backdrop-filter: blur(4px)" onclick={() => { showCreate = false; }}>
    <!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
    <div class="w-full max-w-lg rounded-2xl border border-neutral-200 bg-white p-6 shadow-2xl" onclick={(e) => e.stopPropagation()}>
      <h2 class="text-base font-semibold text-neutral-900 mb-4">New Warehouse</h2>
      <div class="space-y-3">
        <div class="grid grid-cols-2 gap-3">
          <label class="block text-sm"><span class="mb-1 block text-xs font-medium text-neutral-700">Code *</span>
            <input type="text" bind:value={form.code} placeholder="WH-ABJ-01" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </label>
          <label class="block text-sm"><span class="mb-1 block text-xs font-medium text-neutral-700">Name *</span>
            <input type="text" bind:value={form.name} placeholder="Central Store — Abuja" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </label>
        </div>
        <label class="block text-sm"><span class="mb-1 block text-xs font-medium text-neutral-700">Location</span>
          <input type="text" bind:value={form.location} placeholder="Address or site description" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        </label>
        <div class="grid grid-cols-2 gap-3">
          <label class="block text-sm"><span class="mb-1 block text-xs font-medium text-neutral-700">Type</span>
            <select bind:value={form.warehouse_type} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
              <option value="central">Central Warehouse</option>
              <option value="site">Site Store</option>
              <option value="transit">Transit Hub</option>
              <option value="bonded">Bonded Store</option>
            </select>
          </label>
          <label class="block text-sm"><span class="mb-1 block text-xs font-medium text-neutral-700">Storage Capacity</span>
            <input type="number" bind:value={form.storage_capacity_units} placeholder="e.g. 5000 units" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </label>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <label class="block text-sm"><span class="mb-1 block text-xs font-medium text-neutral-700">Project</span>
            <select bind:value={form.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
              <option value="">No project link</option>
              {#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}
            </select>
          </label>
          <label class="block text-sm"><span class="mb-1 block text-xs font-medium text-neutral-700">GPS Coordinates</span>
            <input type="text" bind:value={form.gps_coordinates} placeholder="6.4531,3.3958" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </label>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <label class="block text-sm"><span class="mb-1 block text-xs font-medium text-neutral-700">Contact Person</span>
            <input type="text" bind:value={form.contact_person} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </label>
          <label class="block text-sm"><span class="mb-1 block text-xs font-medium text-neutral-700">Contact Phone</span>
            <input type="text" bind:value={form.contact_phone} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </label>
        </div>
        <div class="flex gap-4">
          <label class="inline-flex items-center gap-2 text-sm text-neutral-600">
            <input type="checkbox" bind:checked={form.is_active} class="rounded border-neutral-300" /> Active
          </label>
          <label class="inline-flex items-center gap-2 text-sm text-neutral-600">
            <input type="checkbox" bind:checked={form.is_default} class="rounded border-neutral-300" /> Default warehouse
          </label>
        </div>
      </div>
      <div class="mt-5 flex justify-end gap-3">
        {#if isDev}<button type="button" onclick={devFill} class="mr-auto rounded-lg bg-orange-500 px-3 py-2 text-xs font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
        <button onclick={() => { showCreate = false; }} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
        <button onclick={createWarehouse} disabled={creating} class="rounded-lg bg-pink-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-pink-700 disabled:opacity-50">{creating ? "Creating..." : "Create Warehouse"}</button>
      </div>
    </div>
  </div>
{/if}

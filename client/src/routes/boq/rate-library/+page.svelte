<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { onMount } from "svelte";

  // --- Types ---
  interface RateBook { id: number; name: string; description: string; is_active: boolean; fx_rate_usd_ngn: string; last_synced_at: string | null; item_count: number; created_by_name: string; created_at: string; updated_at: string; }
  interface HistoryEntry { id: number; rate: string; recorded_at: string; changed_by_name: string | null; notes: string; }
  interface CompositeComponent { id: number; component_rate: number; component_code: string; component_description: string; component_unit: string; component_base_rate: string; quantity: string; line_cost: string; }
  interface RateItem {
    id: number; item_code: string; description: string; unit: string;
    base_rate: string; base_rate_usd: string; is_fx_linked: boolean;
    location: string; category: string; status: string;
    purchase_price: string; shipping_cost: string; handling_fee: string; duty_pct: string;
    supplier_vendor: number | null; supplier_vendor_name: string | null;
    is_composite: boolean; is_stale: boolean; total_landed_cost: string;
    notes: string; last_verified_at: string | null; created_at: string; updated_at: string;
    components?: CompositeComponent[]; history?: HistoryEntry[];
  }
  interface VendorOption { id: number; name: string; category: string; }

  const CATEGORIES = [
    { value: "", label: "All Categories" },
    { value: "equipment", label: "Equipment" }, { value: "labor", label: "Labor" },
    { value: "machinery", label: "Machinery" }, { value: "consumables", label: "Consumables" },
    { value: "logistics", label: "Logistics" }, { value: "fees", label: "Fees & Permits" },
    { value: "preliminaries", label: "Preliminaries" }, { value: "other", label: "Other" },
  ];
  const STATUS_COLORS: Record<string, string> = {
    verified: "bg-emerald-50 text-emerald-700 border-emerald-200",
    floating: "bg-amber-50 text-amber-700 border-amber-200",
    expired: "bg-red-50 text-red-700 border-red-200",
  };
  const CAT_COLORS: Record<string, string> = {
    equipment: "border-l-indigo-400", labor: "border-l-blue-400", machinery: "border-l-violet-400",
    consumables: "border-l-emerald-400", logistics: "border-l-amber-400", fees: "border-l-rose-400",
    preliminaries: "border-l-sky-400", other: "border-l-neutral-400",
  };

  // --- State ---
  let loading = $state(true);
  let books = $state<RateBook[]>([]);
  let selectedBookId = $state<number | null>(null);
  let activeBook = $state<RateBook | null>(null);
  let items = $state<RateItem[]>([]);
  let vendors = $state<VendorOption[]>([]);

  let search = $state("");
  let categoryFilter = $state("");
  let statusFilter = $state("");

  // Book creation
  let showBookModal = $state(false);
  let bookForm = $state({ name: "", description: "", fx_rate_usd_ngn: "1550.00" });
  let bookSaving = $state(false);

  function devFillBook() {
    const names = ["2026 Q1 Standard", "Premium Solar Rates", "Government Tender Book", "Economy Build Rates", "Abuja Metro Rates", "Lagos Coastal Rates"];
    const descs = ["Standard rates for Q1 2026 projects", "Premium-tier solar component pricing", "Pre-qualified rates for government tenders", "Value-engineered rates for budget builds", "Abuja metropolitan area pricing", "Lagos coastal zone adjusted rates"];
    const idx = Math.floor(Math.random() * names.length);
    bookForm = { name: names[idx], description: descs[idx], fx_rate_usd_ngn: String(1400 + Math.floor(Math.random() * 300)) };
  }

  async function saveBook() {
    if (!bookForm.name.trim()) return;
    bookSaving = true;
    try {
      const created = await api.post<RateBook>("/rate-library/", {
        name: bookForm.name.trim(),
        description: bookForm.description.trim(),
        fx_rate_usd_ngn: Number(bookForm.fx_rate_usd_ngn) || 1550,
      });
      showBookModal = false;
      bookForm = { name: "", description: "", fx_rate_usd_ngn: "1550.00" };
      await loadBooks();
      await selectBook(created.id);
      toast.success("Created", `Rate book "${created.name}" created.`);
    } catch {
      toast.error("Failed", "Could not create rate book.");
    } finally { bookSaving = false; }
  }

  // Detail drawer
  let showDrawer = $state(false);
  let drawerVisible = $state(false);
  let activeItem = $state<RateItem | null>(null);
  let drawerLoading = $state(false);

  // Create/Edit modal
  let showModal = $state(false);
  let editingId = $state<number | null>(null);
  let modalSaving = $state(false);
  let form = $state(emptyForm());

  // Bulk adjust
  let showBulkModal = $state(false);
  let bulkCategory = $state("");
  let bulkPct = $state("5");
  let bulkSaving = $state(false);

  // Inline edit
  let inlineEditId = $state<number | null>(null);
  let inlineEditValue = $state("");

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");
  const fxRate = $derived(activeBook ? Number(activeBook.fx_rate_usd_ngn) || 1550 : 1550);

  const filtered = $derived.by(() => {
    let list = items;
    if (categoryFilter) list = list.filter(i => i.category === categoryFilter);
    if (statusFilter) list = list.filter(i => i.status === statusFilter);
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      list = list.filter(i => i.item_code.toLowerCase().includes(q) || i.description.toLowerCase().includes(q) || i.location.toLowerCase().includes(q));
    }
    return list;
  });

  const totalItems = $derived(filtered.length);
  const verifiedCount = $derived(filtered.filter(i => i.status === "verified").length);
  const staleCount = $derived(filtered.filter(i => i.is_stale).length);

  function emptyForm() {
    return {
      item_code: "", description: "", unit: "pcs", base_rate: "",
      base_rate_usd: "", is_fx_linked: false, location: "", category: "other",
      status: "floating", purchase_price: "", shipping_cost: "", handling_fee: "",
      duty_pct: "0", supplier_vendor: "", is_composite: false, notes: "",
    };
  }

  function fmt(n: number): string { return `\u20A6${Math.round(n).toLocaleString()}`; }
  function timeAgo(dateStr: string | null): string {
    if (!dateStr) return "Never";
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  }

  // --- API ---
  async function loadBooks() {
    try {
      const res = await api.get<{ results: RateBook[] }>("/rate-library/", { page_size: "50" });
      books = res.results;
      if (books.length > 0 && !selectedBookId) await selectBook(books[0].id);
    } catch { toast.error("Load failed", "Could not load rate books."); }
    finally { loading = false; }
  }

  async function selectBook(id: number) {
    selectedBookId = id;
    activeBook = books.find(b => b.id === id) || null;
    loading = true;
    try {
      const res = await api.get<{ results: RateItem[] }>(`/rate-library/${id}/items/`, { page_size: "500" });
      items = res.results;
    } catch { toast.error("Load failed", "Could not load rates."); }
    finally { loading = false; }
  }

  async function loadVendors() {
    try {
      const res = await api.get<{ inventory_items: any[]; bom_templates: any[]; vendors: VendorOption[] }>("/bom/catalog/");
      vendors = res.vendors || [];
    } catch { /* optional */ }
  }

  async function openDetail(item: RateItem) {
    drawerLoading = true;
    showDrawer = true;
    requestAnimationFrame(() => { drawerVisible = true; });
    try {
      activeItem = await api.get<RateItem>(`/rate-library/${selectedBookId}/items/${item.id}/`);
    } catch { activeItem = item; }
    finally { drawerLoading = false; }
  }

  function closeDrawer() {
    drawerVisible = false;
    setTimeout(() => { showDrawer = false; activeItem = null; }, 300);
  }

  function openCreate() {
    editingId = null;
    form = emptyForm();
    showModal = true;
  }

  function openEdit(item: RateItem) {
    editingId = item.id;
    form = {
      item_code: item.item_code, description: item.description, unit: item.unit,
      base_rate: item.base_rate, base_rate_usd: item.base_rate_usd,
      is_fx_linked: item.is_fx_linked, location: item.location, category: item.category,
      status: item.status, purchase_price: item.purchase_price, shipping_cost: item.shipping_cost,
      handling_fee: item.handling_fee, duty_pct: item.duty_pct,
      supplier_vendor: item.supplier_vendor ? String(item.supplier_vendor) : "",
      is_composite: item.is_composite, notes: item.notes,
    };
    showModal = true;
  }

  async function saveRate() {
    if (!form.item_code.trim() || !form.description.trim() || !selectedBookId) return;
    modalSaving = true;
    try {
      const payload = {
        ...form,
        base_rate: Number(form.base_rate) || 0,
        base_rate_usd: Number(form.base_rate_usd) || 0,
        purchase_price: Number(form.purchase_price) || 0,
        shipping_cost: Number(form.shipping_cost) || 0,
        handling_fee: Number(form.handling_fee) || 0,
        duty_pct: Number(form.duty_pct) || 0,
        supplier_vendor: form.supplier_vendor ? Number(form.supplier_vendor) : null,
      };
      if (editingId) {
        await api.patch(`/rate-library/${selectedBookId}/items/${editingId}/`, payload);
        toast.success("Updated", `${form.item_code} saved.`);
      } else {
        await api.post(`/rate-library/${selectedBookId}/items/`, payload);
        toast.success("Created", `${form.item_code} added to the library.`);
      }
      showModal = false;
      await selectBook(selectedBookId);
    } catch (err) {
      if (err instanceof ApiError) toast.error("Failed", Object.values(err.fieldErrors).flat().join(" ") || "Check the form.");
      else toast.error("Failed", "Could not save rate.");
    } finally { modalSaving = false; }
  }

  async function deleteRate(id: number) {
    if (!selectedBookId || !confirm("Delete this rate?")) return;
    try {
      await api.delete(`/rate-library/${selectedBookId}/items/${id}/`);
      toast.success("Deleted", "Rate removed.");
      await selectBook(selectedBookId);
    } catch { toast.error("Failed", "Could not delete rate."); }
  }

  async function bulkAdjust() {
    if (!selectedBookId) return;
    bulkSaving = true;
    try {
      const res = await api.post<{ detail: string }>(`/rate-library/${selectedBookId}/bulk-adjust/`, {
        category: bulkCategory, adjust_pct: Number(bulkPct) || 0,
      });
      toast.success("Adjusted", res.detail);
      showBulkModal = false;
      await selectBook(selectedBookId);
    } catch { toast.error("Failed", "Could not apply bulk adjustment."); }
    finally { bulkSaving = false; }
  }

  async function inlineSaveRate(item: RateItem) {
    if (!selectedBookId) return;
    try {
      await api.patch(`/rate-library/${selectedBookId}/items/${item.id}/`, { base_rate: Number(inlineEditValue) || 0 });
      inlineEditId = null;
      await selectBook(selectedBookId);
    } catch { toast.error("Failed", "Could not update rate."); }
  }

  function devFill() {
    const codes = ["MAT-PV-550", "LAB-INST-01", "EQP-CRN-15", "MAT-CBL-10", "MAT-INV-5K", "LAB-SUP-01", "LOG-HAU-01", "FEE-PRM-LG"];
    const descs = ["Jinko 550W Panel", "Senior Technician", "15T Mobile Crane", "10mm DC Cable", "5kW Inverter", "Site Supervisor", "Haulage (20T Truck)", "Building Permit Lagos"];
    const units = ["pcs", "hour", "day", "meter", "pcs", "day", "trip", "ls"];
    const rates = [145000, 4500, 185000, 2200, 450000, 25000, 50000, 350000];
    const cats = ["equipment", "labor", "machinery", "consumables", "equipment", "labor", "logistics", "fees"] as const;
    const locs = ["Lagos WH", "Abuja", "National", "Lagos WH", "Lagos WH", "National", "National", "Lagos"];
    const idx = Math.floor(Math.random() * codes.length);
    form = { ...form, item_code: codes[idx], description: descs[idx], unit: units[idx], base_rate: String(rates[idx]), category: cats[idx], location: locs[idx], status: "verified", purchase_price: String(Math.round(rates[idx] * 0.85)), shipping_cost: String(Math.round(rates[idx] * 0.1)), handling_fee: String(Math.round(rates[idx] * 0.05)) };
  }

  onMount(() => { loadBooks(); loadVendors(); });
</script>

<svelte:head><title>Rate Library | developerOS</title></svelte:head>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-700">Bill of Quantities</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Rate Library</h1>
      <p class="mt-1 text-sm text-neutral-500">Centralized database of pre-negotiated and market-standard costs for materials, labor, and equipment.</p>
    </div>
    <div class="flex gap-2">
      <button onclick={() => { showBulkModal = true; }} class="rounded-lg border border-neutral-200 bg-white px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Bulk Adjust</button>
      <button onclick={openCreate} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800">+ New Rate</button>
    </div>
  </div>

  <!-- 1. Library Master Control -->
  <div class="flex flex-col gap-4 sm:flex-row sm:items-center">
    <!-- Book selector -->
    <div class="flex gap-2 items-center">
      <select onchange={(e) => { const id = Number((e.target as HTMLSelectElement).value); if (id) selectBook(id); }} class="rounded-lg border border-neutral-200 bg-white px-3.5 py-2.5 text-sm font-medium min-w-[260px] focus:outline-none focus:ring-2 focus:ring-neutral-900">
        {#if books.length === 0}
          <option value="">No rate books</option>
        {/if}
        {#each books as book}
          <option value={book.id} selected={book.id === selectedBookId}>{book.name}</option>
        {/each}
      </select>
      <button onclick={() => { showBookModal = true; }} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50" title="Create rate book">+</button>
    </div>

    {#if activeBook}
      <!-- FX Anchor -->
      <div class="rounded-xl border border-neutral-200 bg-white/80 px-4 py-2.5 text-center" style="backdrop-filter: blur(12px)">
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">FX Anchor</p>
        <p class="text-sm font-bold text-neutral-900 tabular-nums">$1 = {String.fromCharCode(8358)}{fxRate.toLocaleString()}</p>
      </div>
      <!-- Last Sync -->
      <div class="rounded-xl border border-neutral-200 bg-white/80 px-4 py-2.5 text-center" style="backdrop-filter: blur(12px)">
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Last Sync</p>
        <p class="text-sm font-bold {activeBook.last_synced_at ? 'text-emerald-600' : 'text-amber-600'}">{timeAgo(activeBook.last_synced_at)}</p>
      </div>
    {/if}

    <div class="flex gap-3 ml-auto">
      <div class="rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-center">
        <p class="text-lg font-bold text-neutral-900 tabular-nums">{totalItems}</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Rates</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-center">
        <p class="text-lg font-bold text-emerald-600 tabular-nums">{verifiedCount}</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Verified</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-center">
        <p class="text-lg font-bold text-amber-600 tabular-nums">{staleCount}</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Stale (30d+)</p>
      </div>
    </div>
  </div>

  <!-- Filters -->
  <div class="flex flex-wrap gap-3">
    <input bind:value={search} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm w-64 focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="Search code, description, location..." />
    <select bind:value={categoryFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-xs font-medium text-neutral-700">
      {#each CATEGORIES as cat}<option value={cat.value}>{cat.label}</option>{/each}
    </select>
    <select bind:value={statusFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-xs font-medium text-neutral-700">
      <option value="">All Status</option>
      <option value="verified">Verified</option>
      <option value="floating">Floating</option>
      <option value="expired">Expired</option>
    </select>
  </div>

  <!-- 2. Rate Table -->
  {#if loading}
    <div class="flex items-center justify-center py-16 text-sm text-neutral-400">Loading...</div>
  {:else}
    <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
      <div class="border-b border-neutral-200 bg-neutral-800 px-5 py-3 flex items-center justify-between">
        <h3 class="text-[10px] font-semibold text-white uppercase tracking-widest">Price List ({filtered.length})</h3>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-xs">
          <thead>
            <tr class="border-b border-neutral-200 bg-neutral-700">
              <th class="px-4 py-2 text-left font-medium text-neutral-200">Item Code</th>
              <th class="px-4 py-2 text-left font-medium text-neutral-200">Description</th>
              <th class="px-3 py-2 text-left font-medium text-neutral-200">Unit</th>
              <th class="px-3 py-2 text-right font-medium text-neutral-200">Base Rate ({String.fromCharCode(8358)})</th>
              <th class="px-3 py-2 text-left font-medium text-neutral-200">Location</th>
              <th class="px-3 py-2 text-left font-medium text-neutral-200">Category</th>
              <th class="px-3 py-2 text-center font-medium text-neutral-200">Status</th>
              <th class="px-3 py-2 w-16"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-50">
            {#each filtered as item (item.id)}
              <tr
                class="hover:bg-neutral-50/50 cursor-pointer transition-colors border-l-2 {CAT_COLORS[item.category] || 'border-l-neutral-200'} {item.is_stale ? 'bg-amber-50/30' : ''}"
                onclick={() => openDetail(item)}
              >
                <td class="px-4 py-2.5 font-bold text-neutral-700 tabular-nums">{item.item_code}</td>
                <td class="px-4 py-2.5 font-medium text-neutral-900">
                  {item.description}
                  {#if item.is_composite}<span class="ml-1 text-[8px] text-violet-500">COMP</span>{/if}
                  {#if item.is_fx_linked}<span class="ml-1 text-[8px] text-sky-500">FX</span>{/if}
                </td>
                <td class="px-3 py-2.5 text-neutral-500">{item.unit}</td>
                <td class="px-3 py-2.5 text-right">
                  {#if inlineEditId === item.id}
                    <input
                      type="number"
                      bind:value={inlineEditValue}
                      onclick={(e) => e.stopPropagation()}
                      onkeydown={(e) => { if (e.key === "Enter") inlineSaveRate(item); if (e.key === "Escape") inlineEditId = null; }}
                      class="w-28 rounded border border-emerald-300 bg-emerald-50 px-2 py-0.5 text-xs text-right tabular-nums focus:outline-none focus:ring-1 focus:ring-emerald-500"
                    />
                  {:else}
                    <span
                      class="tabular-nums font-bold text-neutral-900 cursor-text"
                      ondblclick={(e) => { e.stopPropagation(); inlineEditId = item.id; inlineEditValue = item.base_rate; }}
                    >{fmt(Number(item.base_rate))}</span>
                  {/if}
                </td>
                <td class="px-3 py-2.5 text-neutral-500">{item.location || "—"}</td>
                <td class="px-3 py-2.5 text-neutral-500 capitalize">{item.category}</td>
                <td class="px-3 py-2.5 text-center">
                  <span class="rounded-full border px-2 py-0.5 text-[10px] font-semibold {STATUS_COLORS[item.status] || ''}">{item.status}</span>
                </td>
                <td class="px-3 py-2.5">
                  <div class="flex gap-0.5 justify-end">
                    <button onclick={(e) => { e.stopPropagation(); openEdit(item); }} class="rounded p-1 text-neutral-300 hover:text-neutral-700 transition-colors" title="Edit" aria-label="Edit">
                      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125" /></svg>
                    </button>
                    <button onclick={(e) => { e.stopPropagation(); deleteRate(item.id); }} class="rounded p-1 text-neutral-300 hover:text-red-500 transition-colors" title="Delete" aria-label="Delete">
                      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
                    </button>
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  {/if}
</div>

<!-- 3. Rate Detail Drawer -->
{#if showDrawer && activeItem}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="fixed inset-0 z-40 bg-black/20 transition-opacity duration-300" style="opacity: {drawerVisible ? 1 : 0}; backdrop-filter: blur(12px)" onclick={closeDrawer}></div>
  <aside class="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col bg-white/95 shadow-2xl border-l border-neutral-200/60 transition-transform duration-300" style="transform: translateX({drawerVisible ? '0%' : '100%'}); backdrop-filter: blur(12px)">
    <!-- Dark header -->
    <div class="bg-linear-to-br from-neutral-900 to-neutral-800 px-6 py-5">
      <div class="flex items-start justify-between">
        <div>
          <h2 class="text-base font-semibold text-white">{activeItem.description}</h2>
          <p class="mt-0.5 text-sm text-neutral-400">{activeItem.item_code} &middot; {activeItem.unit}</p>
          <div class="mt-2 flex items-center gap-2">
            <span class="rounded-full px-2.5 py-0.5 text-[11px] font-medium capitalize {activeItem.status === 'verified' ? 'bg-emerald-500/20 text-emerald-300' : activeItem.status === 'floating' ? 'bg-amber-500/20 text-amber-300' : 'bg-red-500/20 text-red-300'}">{activeItem.status}</span>
            <span class="rounded-full bg-white/10 px-2.5 py-0.5 text-[11px] font-medium text-neutral-300 capitalize">{activeItem.category}</span>
            {#if activeItem.location}<span class="rounded-full bg-white/10 px-2.5 py-0.5 text-[11px] font-medium text-neutral-300">{activeItem.location}</span>{/if}
          </div>
        </div>
        <div class="flex items-center gap-2">
          <button onclick={() => { closeDrawer(); openEdit(activeItem!); }} class="rounded-md border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-medium text-white hover:bg-white/20">Edit</button>
          <button onclick={closeDrawer} class="rounded-md p-1.5 text-neutral-400 hover:text-white" aria-label="Close">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
          </button>
        </div>
      </div>
    </div>

    <!-- Key figure -->
    <div class="grid grid-cols-3 divide-x divide-neutral-100 border-b border-neutral-100">
      <div class="px-4 py-3 text-center">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Base Rate</p>
        <p class="mt-0.5 text-base font-bold tabular-nums text-emerald-700">{fmt(Number(activeItem.base_rate))}</p>
      </div>
      <div class="px-4 py-3 text-center">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Landed Cost</p>
        <p class="mt-0.5 text-base font-bold tabular-nums text-blue-700">{fmt(Number(activeItem.total_landed_cost))}</p>
      </div>
      <div class="px-4 py-3 text-center">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Verified</p>
        <p class="mt-0.5 text-base font-bold {activeItem.last_verified_at ? 'text-emerald-600' : 'text-amber-600'}">{timeAgo(activeItem.last_verified_at)}</p>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto px-6 py-5 space-y-5">
      <!-- Cost Components -->
      <section>
        <h3 class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-3">Cost Components</h3>
        <div class="rounded-xl border border-neutral-100 bg-neutral-50/50 p-4 space-y-2">
          <div class="flex justify-between text-xs"><span class="text-neutral-500">Purchase Price</span><span class="tabular-nums font-medium text-neutral-900">{fmt(Number(activeItem.purchase_price))}</span></div>
          <div class="flex justify-between text-xs"><span class="text-neutral-500">Shipping</span><span class="tabular-nums font-medium text-neutral-900">{fmt(Number(activeItem.shipping_cost))}</span></div>
          <div class="flex justify-between text-xs"><span class="text-neutral-500">Handling Fee</span><span class="tabular-nums font-medium text-neutral-900">{fmt(Number(activeItem.handling_fee))}</span></div>
          <div class="flex justify-between text-xs"><span class="text-neutral-500">Import Duty</span><span class="tabular-nums font-medium text-neutral-900">{Number(activeItem.duty_pct)}%</span></div>
          <div class="flex justify-between text-xs pt-2 border-t border-neutral-200"><span class="font-semibold text-neutral-700">Total Landed</span><span class="tabular-nums font-bold text-emerald-700">{fmt(Number(activeItem.total_landed_cost))}</span></div>
        </div>
      </section>

      <!-- Supplier -->
      {#if activeItem.supplier_vendor_name}
        <section>
          <h3 class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-2">Supplier</h3>
          <div class="rounded-xl border border-indigo-200 bg-indigo-50/40 px-4 py-3">
            <p class="text-sm font-medium text-neutral-900">{activeItem.supplier_vendor_name}</p>
          </div>
        </section>
      {/if}

      <!-- Composite components -->
      {#if activeItem.is_composite && activeItem.components?.length}
        <section>
          <h3 class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-3">Composite Assembly</h3>
          <div class="rounded-lg border border-neutral-200 overflow-hidden">
            <table class="w-full text-xs">
              <thead><tr class="bg-neutral-50 border-b border-neutral-100"><th class="px-3 py-1.5 text-left font-medium text-neutral-500">Component</th><th class="px-3 py-1.5 text-right font-medium text-neutral-500">Qty</th><th class="px-3 py-1.5 text-right font-medium text-neutral-500">Rate</th><th class="px-3 py-1.5 text-right font-medium text-neutral-500">Cost</th></tr></thead>
              <tbody class="divide-y divide-neutral-50">
                {#each activeItem.components as comp}
                  <tr><td class="px-3 py-1.5 text-neutral-800">{comp.component_description}</td><td class="px-3 py-1.5 text-right tabular-nums">{comp.quantity}</td><td class="px-3 py-1.5 text-right tabular-nums">{fmt(Number(comp.component_base_rate))}</td><td class="px-3 py-1.5 text-right tabular-nums font-semibold">{fmt(Number(comp.line_cost))}</td></tr>
                {/each}
              </tbody>
            </table>
          </div>
        </section>
      {/if}

      <!-- History -->
      {#if activeItem.history?.length}
        <section>
          <h3 class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-3">Price History</h3>
          <div class="space-y-1.5">
            {#each activeItem.history.slice(0, 12) as h}
              <div class="flex items-center justify-between rounded-lg bg-neutral-50 px-3 py-2">
                <div>
                  <span class="text-xs font-bold text-neutral-900 tabular-nums">{fmt(Number(h.rate))}</span>
                  {#if h.notes}<span class="ml-2 text-[10px] text-neutral-400">{h.notes}</span>{/if}
                </div>
                <span class="text-[10px] text-neutral-400">{timeAgo(h.recorded_at)}</span>
              </div>
            {/each}
          </div>
        </section>
      {/if}

      <!-- Notes -->
      {#if activeItem.notes}
        <section>
          <h3 class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-2">Notes</h3>
          <p class="text-xs text-neutral-600 whitespace-pre-line">{activeItem.notes}</p>
        </section>
      {/if}
    </div>
  </aside>
{/if}

<!-- Create/Edit Modal -->
{#if showModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" style="backdrop-filter: blur(4px)">
    <div class="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl border border-neutral-200 bg-white p-6 shadow-2xl">
      <div class="flex items-start justify-between mb-5">
        <h2 class="text-lg font-semibold text-neutral-900">{editingId ? "Edit Rate" : "New Rate Item"}</h2>
        <button onclick={() => { showModal = false; }} class="rounded-md border border-neutral-200 bg-white px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50">Close</button>
      </div>
      <div class="space-y-4">
        <div class="grid grid-cols-3 gap-3">
          <label class="text-sm font-medium text-neutral-700"><span class="mb-1 block text-xs">Item Code *</span><input bind:value={form.item_code} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="MAT-PV-550" /></label>
          <label class="col-span-2 text-sm font-medium text-neutral-700"><span class="mb-1 block text-xs">Description *</span><input bind:value={form.description} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="Jinko 550W Panel" /></label>
        </div>
        <div class="grid grid-cols-4 gap-3">
          <label class="text-sm font-medium text-neutral-700"><span class="mb-1 block text-xs">Unit</span><input bind:value={form.unit} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" /></label>
          <label class="text-sm font-medium text-neutral-700"><span class="mb-1 block text-xs">Base Rate ({String.fromCharCode(8358)})</span><input type="number" bind:value={form.base_rate} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" /></label>
          <label class="text-sm font-medium text-neutral-700"><span class="mb-1 block text-xs">Category</span>
            <select bind:value={form.category} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
              {#each CATEGORIES.slice(1) as cat}<option value={cat.value}>{cat.label}</option>{/each}
            </select>
          </label>
          <label class="text-sm font-medium text-neutral-700"><span class="mb-1 block text-xs">Location</span><input bind:value={form.location} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="Lagos WH" /></label>
        </div>
        <div class="grid grid-cols-4 gap-3">
          <label class="text-sm font-medium text-neutral-700"><span class="mb-1 block text-xs">Purchase Price</span><input type="number" bind:value={form.purchase_price} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" /></label>
          <label class="text-sm font-medium text-neutral-700"><span class="mb-1 block text-xs">Shipping</span><input type="number" bind:value={form.shipping_cost} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" /></label>
          <label class="text-sm font-medium text-neutral-700"><span class="mb-1 block text-xs">Handling Fee</span><input type="number" bind:value={form.handling_fee} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" /></label>
          <label class="text-sm font-medium text-neutral-700"><span class="mb-1 block text-xs">Duty %</span><input type="number" bind:value={form.duty_pct} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" /></label>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <label class="text-sm font-medium text-neutral-700"><span class="mb-1 block text-xs">Status</span>
            <select bind:value={form.status} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
              <option value="verified">Verified</option><option value="floating">Floating</option><option value="expired">Expired</option>
            </select>
          </label>
          <label class="text-sm font-medium text-neutral-700"><span class="mb-1 block text-xs">Vendor</span>
            <select bind:value={form.supplier_vendor} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
              <option value="">No vendor</option>
              {#each vendors as v}<option value={String(v.id)}>{v.name}</option>{/each}
            </select>
          </label>
        </div>
        <label class="block text-sm font-medium text-neutral-700"><span class="mb-1 block text-xs">Notes</span><textarea bind:value={form.notes} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea></label>
      </div>
      <div class="mt-6 flex items-center justify-end gap-3">
        {#if isDev}<button type="button" onclick={devFill} class="mr-auto rounded-lg bg-orange-500 px-3 py-2 text-xs font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
        <button onclick={() => { showModal = false; }} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
        <button onclick={saveRate} disabled={modalSaving} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50">{modalSaving ? "Saving..." : editingId ? "Save Changes" : "Create Rate"}</button>
      </div>
    </div>
  </div>
{/if}

<!-- Bulk Adjust Modal -->
{#if showBulkModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" style="backdrop-filter: blur(4px)">
    <div class="w-full max-w-sm rounded-2xl border border-neutral-200 bg-white p-6 shadow-2xl">
      <h2 class="text-base font-semibold text-neutral-900 mb-4">Bulk Rate Adjustment</h2>
      <div class="space-y-4">
        <label class="block text-sm font-medium text-neutral-700"><span class="mb-1 block text-xs">Category (leave empty for all)</span>
          <select bind:value={bulkCategory} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
            <option value="">All Categories</option>
            {#each CATEGORIES.slice(1) as cat}<option value={cat.value}>{cat.label}</option>{/each}
          </select>
        </label>
        <label class="block text-sm font-medium text-neutral-700"><span class="mb-1 block text-xs">Adjustment %</span>
          <input type="number" bind:value={bulkPct} step="0.5" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          <p class="mt-1 text-[10px] text-neutral-400">Positive = increase, negative = decrease. e.g. +5 for a 5% market spike.</p>
        </label>
      </div>
      <div class="mt-6 flex justify-end gap-3">
        <button onclick={() => { showBulkModal = false; }} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
        <button onclick={bulkAdjust} disabled={bulkSaving} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50">{bulkSaving ? "Applying..." : "Apply"}</button>
      </div>
    </div>
  </div>
{/if}

<!-- Create Rate Book Modal -->
{#if showBookModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" style="backdrop-filter: blur(4px)">
    <div class="w-full max-w-sm rounded-2xl border border-neutral-200 bg-white p-6 shadow-2xl">
      <h2 class="text-base font-semibold text-neutral-900 mb-4">New Rate Book</h2>
      <div class="space-y-4">
        <label class="block text-sm font-medium text-neutral-700"><span class="mb-1 block text-xs">Name *</span>
          <input type="text" bind:value={bookForm.name} placeholder="e.g. 2026 Q1 Standard" class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        </label>
        <label class="block text-sm font-medium text-neutral-700"><span class="mb-1 block text-xs">Description</span>
          <input type="text" bind:value={bookForm.description} placeholder="Optional description" class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        </label>
        <label class="block text-sm font-medium text-neutral-700"><span class="mb-1 block text-xs">FX Rate (USD → NGN)</span>
          <input type="number" bind:value={bookForm.fx_rate_usd_ngn} step="0.01" class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        </label>
      </div>
      <div class="mt-6 flex justify-end gap-3">
        {#if isDev}<button type="button" onclick={devFillBook} class="mr-auto rounded-lg bg-orange-500 px-3 py-2 text-xs font-medium text-white hover:bg-orange-600">Dev Fill</button>{/if}
        <button onclick={() => { showBookModal = false; }} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
        <button onclick={saveBook} disabled={bookSaving} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50">{bookSaving ? "Creating..." : "Create Book"}</button>
      </div>
    </div>
  </div>
{/if}

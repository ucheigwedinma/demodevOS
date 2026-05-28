<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import { onMount } from "svelte";
  import { useLiveKpis } from "$lib/realtime.svelte";
  import LiveBadge from "$lib/components/LiveBadge.svelte";

  // --- Types ---
  interface BomListItem {
    id: number; bom_number: string; name: string;
    project: number | null; project_name: string | null;
    unit_type: string; quantity_of_units: number;
    status: string; total_estimated_cost: string;
    item_count: number; version: number;
    confidence_pct: number; margin_pct: string; vat_pct: string;
    site_location: string; parent_version: number | null;
    subtotal: string; vat_amount: string; margin_amount: string; grand_total: string;
    created_by_name: string; created_at: string; updated_at: string;
  }
  interface BomItem {
    id: number; inventory_item: number | null; inventory_item_name: string | null;
    material_name: string; category: string;
    quantity: string; unit_of_measure: string;
    unit_cost: string; line_total: string;
    notes: string; sort_order: number;
    supplier: string; is_approved: boolean;
    price_volatile: boolean; original_unit_cost: string | null;
    price_drift_pct: number | null;
  }
  interface BomDetail extends BomListItem {
    description: string; items: BomItem[];
  }
  interface ProjectOption { id: number; name: string; }

  const STATUS_OPTIONS = [
    { value: "", label: "All Statuses" },
    { value: "draft", label: "Draft" },
    { value: "in_review", label: "In Review" },
    { value: "pending_approval", label: "Pending Approval" },
    { value: "approved", label: "Approved" },
    { value: "archived", label: "Archived" },
  ];
  const STATUS_COLORS: Record<string, string> = {
    draft: "bg-neutral-100 text-neutral-500 border-neutral-200",
    in_review: "bg-sky-50 text-sky-700 border-sky-200",
    pending_approval: "bg-amber-50 text-amber-700 border-amber-200",
    approved: "bg-emerald-50 text-emerald-700 border-emerald-200",
    archived: "bg-neutral-100 text-neutral-400 border-neutral-200",
  };

  // --- State ---
  let loading = $state(true);
  let boms = $state<BomListItem[]>([]);
  let projects = $state<ProjectOption[]>([]);
  let statusFilter = $state("");
  let searchQuery = $state("");
  let groupBy = $state<"" | "project" | "site">("");

  // Detail / Edit
  let activeBom = $state<BomDetail | null>(null);
  let showWorkspace = $state(false);
  let workspaceLoading = $state(false);
  let compactMode = $state(false);

  // Create modal
  let showCreateModal = $state(false);
  let createSaving = $state(false);
  let createForm = $state({ name: "", description: "", project: "", unit_type: "", site_location: "" });

  // CSV Import
  let showImportModal = $state(false);
  let importBomId = $state<number | null>(null);
  let importFile = $state<File | null>(null);
  let importing = $state(false);

  function openImport(bomId: number) {
    importBomId = bomId;
    importFile = null;
    showImportModal = true;
  }

  async function runImport() {
    if (!importFile || !importBomId) return;
    importing = true;
    try {
      const formData = new FormData();
      formData.append("file", importFile);
      const res = await fetch(`/api/bom/${importBomId}/import-csv/`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${localStorage.getItem("access_token")}` },
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        toast.success("Import complete", `${data.created} item(s) imported.`);
        if (data.errors?.length) toast.error("Some rows skipped", data.errors.slice(0, 3).join("; "));
        showImportModal = false;
        await loadBoms();
        if (importBomId === activeBom?.id) await openWorkspace(importBomId);
      } else {
        toast.error("Import failed", data.detail || "Check your CSV format.");
      }
    } catch { toast.error("Import failed", "Network error."); }
    finally { importing = false; }
  }

  // Item editing
  let editingItemId = $state<number | null>(null);
  let itemSaving = $state(false);
  let addingItem = $state(false);
  let newItem = $state(emptyNewItem());

  // Margin slider
  let liveMarginPct = $state(10);
  let liveVatPct = $state(7.5);
  let marginSaving = $state(false);

  // Comparison
  let compareMode = $state(false);
  let compareIds = $state<number[]>([]);

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  // --- Computed ---
  const filtered = $derived.by(() => {
    let list = boms;
    if (statusFilter) list = list.filter(b => b.status === statusFilter);
    if (searchQuery.trim()) {
      const q = searchQuery.trim().toLowerCase();
      list = list.filter(b =>
        b.name.toLowerCase().includes(q)
        || b.bom_number.toLowerCase().includes(q)
        || (b.project_name || "").toLowerCase().includes(q)
        || b.site_location.toLowerCase().includes(q)
      );
    }
    return list;
  });

  const grouped = $derived.by(() => {
    if (!groupBy) return null;
    const map = new Map<string, BomListItem[]>();
    for (const b of filtered) {
      const key = groupBy === "project" ? (b.project_name || "No Project") : (b.site_location || "No Location");
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(b);
    }
    return map;
  });

  const totalPortfolioValue = $derived(filtered.reduce((s, b) => s + Number(b.grand_total || b.total_estimated_cost || 0), 0));
  const draftCount = $derived(filtered.filter(b => b.status === "draft").length);
  const avgConfidence = $derived(filtered.length > 0 ? Math.round(filtered.reduce((s, b) => s + (b.confidence_pct || 0), 0) / filtered.length) : 0);

  // Workspace computed
  const wsSubtotal = $derived(activeBom ? Number(activeBom.total_estimated_cost || 0) : 0);
  const wsVat = $derived(wsSubtotal * liveVatPct / 100);
  const wsMargin = $derived(wsSubtotal * liveMarginPct / 100);
  const wsGrandTotal = $derived(wsSubtotal + wsVat + wsMargin);
  const wsApprovedCount = $derived(activeBom ? activeBom.items.filter(i => i.is_approved).length : 0);
  const wsVolatileCount = $derived(activeBom ? activeBom.items.filter(i => i.price_volatile).length : 0);
  const wsDriftItems = $derived(activeBom ? activeBom.items.filter(i => i.price_drift_pct !== null && Math.abs(i.price_drift_pct) > 2) : []);

  function emptyNewItem() {
    return { material_name: "", category: "", quantity: "", unit_of_measure: "pcs", unit_cost: "", notes: "", supplier: "", is_approved: false, price_volatile: false };
  }

  function fmt(n: number): string { return `\u20A6${Math.round(n).toLocaleString()}`; }
  function fmtM(n: number): string { return n >= 1_000_000 ? `\u20A6${(n / 1_000_000).toFixed(1)}M` : fmt(n); }
  function timeAgo(dateStr: string): string {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    return `${days}d ago`;
  }
  function confidenceColor(pct: number): string {
    if (pct >= 90) return "text-emerald-600";
    if (pct >= 60) return "text-blue-600";
    if (pct >= 30) return "text-amber-600";
    return "text-neutral-400";
  }
  function confidenceLabel(pct: number): string {
    if (pct >= 90) return "Quoted";
    if (pct >= 60) return "Estimated";
    if (pct >= 30) return "Rough";
    if (pct > 0) return "Prelim.";
    return "Empty";
  }

  // --- API ---
  async function loadBoms() {
    loading = true;
    try {
      const [bomRes, projRes] = await Promise.all([
        api.get<{ results: BomListItem[] }>("/bom/", { page_size: "200" }),
        api.get<{ results: ProjectOption[] }>("/projects/", { page_size: "100", fields: "id,name" }),
      ]);
      boms = bomRes.results;
      projects = projRes.results;
    } catch { toast.error("Load failed", "Could not load Bills of Quantities."); }
    finally { loading = false; }
  }

  async function openWorkspace(bom: BomListItem | number) {
    const bomId = typeof bom === "number" ? bom : bom.id;
    workspaceLoading = true;
    showWorkspace = true;
    try {
      activeBom = await api.get<BomDetail>(`/bom/${bomId}/`);
      liveMarginPct = Number(activeBom.margin_pct) || 10;
      liveVatPct = Number(activeBom.vat_pct) || 7.5;
    } catch { toast.error("Load failed", "Could not load BoQ detail."); showWorkspace = false; }
    finally { workspaceLoading = false; }
  }

  function closeWorkspace() {
    showWorkspace = false;
    activeBom = null;
    editingItemId = null;
    addingItem = false;
    loadBoms();
  }

  async function createBom() {
    if (!createForm.name.trim()) { toast.error("Required", "BoQ name is required."); return; }
    createSaving = true;
    try {
      await api.post("/bom/", {
        name: createForm.name,
        description: createForm.description,
        project: createForm.project ? Number(createForm.project) : null,
        unit_type: createForm.unit_type,
        site_location: createForm.site_location,
      });
      toast.success("Created", "New BoQ draft has been created.");
      showCreateModal = false;
      createForm = { name: "", description: "", project: "", unit_type: "", site_location: "" };
      await loadBoms();
    } catch (err) {
      if (err instanceof ApiError) toast.error("Failed", Object.values(err.fieldErrors).flat().join(" ") || "Could not create BoQ.");
      else toast.error("Failed", "Could not create BoQ.");
    } finally { createSaving = false; }
  }

  async function cloneBom(bomId: number) {
    try {
      const cloned = await api.post<BomDetail>(`/bom/${bomId}/clone/`, {});
      toast.success("Cloned", `New version "${cloned.name}" created.`);
      await loadBoms();
    } catch { toast.error("Clone failed", "Could not create new version."); }
  }

  async function deleteBom(bomId: number) {
    if (!confirm("Delete this BoQ draft? This cannot be undone.")) return;
    try {
      await api.delete(`/bom/${bomId}/`);
      toast.success("Deleted", "BoQ draft has been removed.");
      if (activeBom?.id === bomId) closeWorkspace();
      else await loadBoms();
    } catch { toast.error("Failed", "Could not delete BoQ."); }
  }

  async function updateBomStatus(bomId: number, status: string) {
    try {
      await api.patch(`/bom/${bomId}/`, { status });
      toast.success("Updated", `Status changed to ${status.replace("_", " ")}.`);
      if (activeBom?.id === bomId) activeBom = { ...activeBom!, status };
      await loadBoms();
    } catch { toast.error("Failed", "Could not update status."); }
  }

  async function saveMargin() {
    if (!activeBom) return;
    marginSaving = true;
    try {
      await api.patch(`/bom/${activeBom.id}/`, { margin_pct: liveMarginPct, vat_pct: liveVatPct });
      toast.success("Saved", "Margin and VAT updated.");
    } catch { toast.error("Failed", "Could not save margin."); }
    finally { marginSaving = false; }
  }

  // --- Line Item CRUD ---
  async function saveNewItem() {
    if (!activeBom || !newItem.material_name.trim()) return;
    itemSaving = true;
    try {
      await api.post(`/bom/${activeBom.id}/items/`, {
        material_name: newItem.material_name,
        category: newItem.category,
        quantity: Number(newItem.quantity) || 0,
        unit_of_measure: newItem.unit_of_measure,
        unit_cost: Number(newItem.unit_cost) || 0,
        notes: newItem.notes,
        supplier: newItem.supplier,
        is_approved: newItem.is_approved,
        price_volatile: newItem.price_volatile,
      });
      newItem = emptyNewItem();
      addingItem = false;
      activeBom = await api.get<BomDetail>(`/bom/${activeBom.id}/`);
      toast.success("Added", "Line item added.");
    } catch { toast.error("Failed", "Could not add item."); }
    finally { itemSaving = false; }
  }

  async function updateItem(item: BomItem, field: string, value: any) {
    if (!activeBom) return;
    try {
      await api.patch(`/bom/${activeBom.id}/items/${item.id}/`, { [field]: value });
      activeBom = await api.get<BomDetail>(`/bom/${activeBom.id}/`);
    } catch { toast.error("Failed", "Could not update item."); }
  }

  async function deleteItem(itemId: number) {
    if (!activeBom) return;
    try {
      await api.delete(`/bom/${activeBom.id}/items/${itemId}/`);
      activeBom = await api.get<BomDetail>(`/bom/${activeBom.id}/`);
      toast.success("Removed", "Line item deleted.");
    } catch { toast.error("Failed", "Could not delete item."); }
  }

  function toggleCompare(bomId: number) {
    if (compareIds.includes(bomId)) {
      compareIds = compareIds.filter(id => id !== bomId);
    } else if (compareIds.length < 2) {
      compareIds = [...compareIds, bomId];
    }
  }

  function devFillCreate() {
    const names = ["B-Abuja-002 — 50kW Solar Farm", "B-Lekki-V3 — 10kW Residential", "B-PHC-001 — Estate Infrastructure", "B-Kaduna-Draft — Commercial Complex", "B-Ikoyi-V2 — Luxury Villa"];
    const sites = ["Abuja, FCT", "Lekki Phase 1, Lagos", "Port Harcourt, Rivers", "Kaduna South", "Ikoyi, Lagos"];
    const idx = Math.floor(Math.random() * names.length);
    createForm = { name: names[idx], description: `Bill of Quantities for ${names[idx].split(" — ")[1] || "project"} development. Includes all material, labour, and equipment costings.`, project: projects.length > 0 ? String(projects[0].id) : "", unit_type: "Residential Unit", site_location: sites[idx] };
  }

  onMount(() => { loadBoms(); });

  const live = useLiveKpis(
    ["BillOfMaterials"],
    loadBoms,
    { debounceMs: 3000 },
  );
</script>

<svelte:head><title>Bill of Quantities | developerOS</title></svelte:head>

{#if showWorkspace && activeBom}
  <!-- ═══════════════════════════════════════════════════════════════════════ -->
  <!--  WORKSPACE MODE                                                        -->
  <!-- ═══════════════════════════════════════════════════════════════════════ -->
  <div class="space-y-5">
    <!-- Workspace Header -->
    <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <button onclick={closeWorkspace} class="mb-2 flex items-center gap-1 text-xs text-neutral-400 hover:text-neutral-700 transition-colors">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" /></svg>
          Back to Drafts
        </button>
        <div class="flex items-center gap-3">
          <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-700">Review & Refine</p>
        </div>
        <h1 class="mt-1 text-xl font-bold tracking-wide text-neutral-800">{activeBom.name}</h1>
        <div class="mt-1 flex items-center gap-2">
          <span class="rounded-full border px-2 py-0.5 text-[10px] font-semibold {STATUS_COLORS[activeBom.status] || ''}">{activeBom.status.replace("_", " ")}</span>
          <span class="text-xs text-neutral-400">{activeBom.bom_number} &middot; v{activeBom.version}</span>
          {#if activeBom.project_name}<span class="text-xs text-neutral-400">&middot; {activeBom.project_name}</span>{/if}
        </div>
      </div>
      <div class="flex flex-wrap gap-2">
        <label class="flex items-center gap-2 rounded-lg border border-neutral-200 bg-white px-3 py-2 cursor-pointer">
          <input type="checkbox" bind:checked={compactMode} class="rounded border-neutral-300 text-neutral-900" />
          <span class="text-xs font-medium text-neutral-700">Compact</span>
        </label>
        <select onchange={(e) => updateBomStatus(activeBom!.id, (e.target as HTMLSelectElement).value)} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-xs font-medium text-neutral-700">
          {#each STATUS_OPTIONS.slice(1) as opt}
            <option value={opt.value} selected={activeBom.status === opt.value}>{opt.label}</option>
          {/each}
        </select>
        <button onclick={() => cloneBom(activeBom!.id)} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-xs font-medium text-neutral-700 hover:bg-neutral-50">New Version</button>
      </div>
    </div>

    <!-- Margin & VAT Slider -->
    <div class="rounded-xl border border-neutral-200 bg-white/80 p-5" style="backdrop-filter: blur(12px)">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-6 items-end">
        <div>
          <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider mb-1.5">Project Margin</p>
          <div class="flex items-center gap-3">
            <input type="range" min="0" max="35" step="0.5" bind:value={liveMarginPct} class="flex-1 accent-neutral-900" />
            <span class="text-sm font-bold text-neutral-900 tabular-nums w-12 text-right">{liveMarginPct}%</span>
          </div>
        </div>
        <div>
          <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider mb-1.5">VAT</p>
          <div class="flex items-center gap-3">
            <input type="range" min="0" max="20" step="0.5" bind:value={liveVatPct} class="flex-1 accent-neutral-900" />
            <span class="text-sm font-bold text-neutral-900 tabular-nums w-12 text-right">{liveVatPct}%</span>
          </div>
        </div>
        <div class="text-right">
          <p class="text-[10px] text-emerald-600 uppercase tracking-wider">Grand Total</p>
          <p class="text-xl font-bold text-emerald-700 tabular-nums">{fmt(wsGrandTotal)}</p>
          <p class="text-[10px] text-neutral-400 tabular-nums">Sub: {fmt(wsSubtotal)} + VAT: {fmt(wsVat)} + Margin: {fmt(wsMargin)}</p>
        </div>
        <div>
          <button onclick={saveMargin} disabled={marginSaving} class="w-full rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50">{marginSaving ? "Saving..." : "Apply"}</button>
        </div>
      </div>
    </div>

    <!-- Drift & Approval Stats -->
    <div class="flex gap-3 flex-wrap">
      <div class="rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-center">
        <p class="text-lg font-bold text-neutral-900 tabular-nums">{activeBom.items.length}</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Line Items</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-center">
        <p class="text-lg font-bold text-emerald-600 tabular-nums">{wsApprovedCount}</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Approved</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-center">
        <p class="text-lg font-bold text-amber-600 tabular-nums">{wsVolatileCount}</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Volatile</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-center">
        <p class="text-lg font-bold tabular-nums {wsDriftItems.length > 0 ? 'text-red-600' : 'text-neutral-900'}">{wsDriftItems.length}</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Price Drift</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-center">
        <p class="text-lg font-bold tabular-nums {confidenceColor(activeBom.confidence_pct)}">{activeBom.confidence_pct}%</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Confidence</p>
      </div>
    </div>

    <!-- Line Items Table -->
    <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
      <div class="flex items-center justify-between border-b border-neutral-200 bg-neutral-800 px-5 py-3">
        <h3 class="text-[10px] font-semibold text-white uppercase tracking-widest">Line Items ({activeBom.items.length})</h3>
        <button onclick={() => { addingItem = true; }} class="rounded-lg bg-white/20 border border-white/30 px-3 py-1.5 text-xs font-medium text-white hover:bg-white/30">+ Add Item</button>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-xs">
          <thead>
            <tr class="border-b border-neutral-200 bg-neutral-700">
              <th class="px-4 {compactMode ? 'py-1' : 'py-2'} text-left font-medium text-neutral-200 w-8">#</th>
              <th class="px-4 {compactMode ? 'py-1' : 'py-2'} text-left font-medium text-neutral-200">Material</th>
              <th class="px-4 {compactMode ? 'py-1' : 'py-2'} text-left font-medium text-neutral-200">Category</th>
              <th class="px-4 {compactMode ? 'py-1' : 'py-2'} text-right font-medium text-neutral-200">Qty</th>
              <th class="px-4 {compactMode ? 'py-1' : 'py-2'} text-left font-medium text-neutral-200">Unit</th>
              <th class="px-4 {compactMode ? 'py-1' : 'py-2'} text-right font-medium text-neutral-200">Unit Cost</th>
              <th class="px-4 {compactMode ? 'py-1' : 'py-2'} text-right font-medium text-neutral-200">Line Total</th>
              <th class="px-4 {compactMode ? 'py-1' : 'py-2'} text-left font-medium text-neutral-200">Supplier</th>
              <th class="px-3 {compactMode ? 'py-1' : 'py-2'} w-24"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-50">
            {#each activeBom.items as item, idx (item.id)}
              {@const hasDrift = item.price_drift_pct !== null && Math.abs(item.price_drift_pct) > 2}
              <tr class="hover:bg-neutral-50/50 transition-colors {hasDrift ? 'border-l-2 border-l-amber-400' : ''} {item.is_approved ? 'bg-emerald-50/30' : ''}">
                <td class="px-4 {compactMode ? 'py-1' : 'py-2.5'} text-neutral-400 tabular-nums">{idx + 1}</td>
                <td class="px-4 {compactMode ? 'py-1' : 'py-2.5'} font-medium text-neutral-900">
                  {item.material_name}
                  {#if item.price_volatile}<span class="ml-1 text-amber-500" title="Price volatile">&#9888;</span>{/if}
                </td>
                <td class="px-4 {compactMode ? 'py-1' : 'py-2.5'} text-neutral-500 capitalize">{item.category || "—"}</td>
                <td class="px-4 {compactMode ? 'py-1' : 'py-2.5'} text-right tabular-nums text-neutral-700">{Number(item.quantity).toLocaleString()}</td>
                <td class="px-4 {compactMode ? 'py-1' : 'py-2.5'} text-neutral-500">{item.unit_of_measure}</td>
                <td class="px-4 {compactMode ? 'py-1' : 'py-2.5'} text-right tabular-nums text-neutral-700">
                  {fmt(Number(item.unit_cost))}
                  {#if hasDrift}
                    <span class="ml-1 text-[9px] font-bold {item.price_drift_pct! > 0 ? 'text-red-600' : 'text-emerald-600'}">{item.price_drift_pct! > 0 ? "+" : ""}{item.price_drift_pct!.toFixed(1)}%</span>
                  {/if}
                </td>
                <td class="px-4 {compactMode ? 'py-1' : 'py-2.5'} text-right tabular-nums font-semibold text-neutral-900">{fmt(Number(item.line_total))}</td>
                <td class="px-4 {compactMode ? 'py-1' : 'py-2.5'} text-neutral-500">{item.supplier || "—"}</td>
                <td class="px-3 {compactMode ? 'py-1' : 'py-2.5'}">
                  <div class="flex items-center gap-1 justify-end">
                    <button onclick={() => updateItem(item, "is_approved", !item.is_approved)} class="rounded p-1 transition-colors {item.is_approved ? 'text-emerald-500 hover:text-emerald-700' : 'text-neutral-300 hover:text-emerald-500'}" title="{item.is_approved ? 'Unapprove' : 'Approve'}" aria-label="Toggle approval">
                      <svg class="w-3.5 h-3.5" fill={item.is_approved ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg>
                    </button>
                    <button onclick={() => deleteItem(item.id)} class="rounded p-1 text-neutral-300 hover:text-red-500 transition-colors" title="Delete" aria-label="Delete item">
                      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" /></svg>
                    </button>
                  </div>
                </td>
              </tr>
            {/each}

            <!-- Add new item row -->
            {#if addingItem}
              <tr class="bg-indigo-50/30 border-t border-indigo-100">
                <td class="px-4 py-2 text-indigo-400">+</td>
                <td class="px-4 py-2"><input bind:value={newItem.material_name} class="w-full rounded border border-neutral-200 px-2 py-1 text-xs" placeholder="Material name" /></td>
                <td class="px-4 py-2"><input bind:value={newItem.category} class="w-full rounded border border-neutral-200 px-2 py-1 text-xs" placeholder="Category" /></td>
                <td class="px-4 py-2"><input type="number" bind:value={newItem.quantity} class="w-full rounded border border-neutral-200 px-2 py-1 text-xs text-right" placeholder="0" /></td>
                <td class="px-4 py-2"><input bind:value={newItem.unit_of_measure} class="w-20 rounded border border-neutral-200 px-2 py-1 text-xs" placeholder="pcs" /></td>
                <td class="px-4 py-2"><input type="number" bind:value={newItem.unit_cost} class="w-full rounded border border-neutral-200 px-2 py-1 text-xs text-right" placeholder="0" /></td>
                <td class="px-4 py-2 text-right tabular-nums text-neutral-400">{fmt((Number(newItem.quantity) || 0) * (Number(newItem.unit_cost) || 0))}</td>
                <td class="px-4 py-2"><input bind:value={newItem.supplier} class="w-full rounded border border-neutral-200 px-2 py-1 text-xs" placeholder="Supplier" /></td>
                <td class="px-3 py-2">
                  <div class="flex gap-1">
                    <button onclick={saveNewItem} disabled={itemSaving} class="rounded bg-neutral-900 px-2 py-1 text-[10px] font-medium text-white hover:bg-neutral-800 disabled:opacity-50">Save</button>
                    <button onclick={() => { addingItem = false; newItem = emptyNewItem(); }} class="rounded border border-neutral-200 px-2 py-1 text-[10px] text-neutral-500 hover:bg-neutral-50">Cancel</button>
                  </div>
                </td>
              </tr>
            {/if}
          </tbody>
          {#if activeBom.items.length > 0}
            <tfoot>
              <tr class="border-t-2 border-neutral-200 bg-neutral-50">
                <td colspan="6" class="px-4 py-3 text-right font-bold text-emerald-700">Subtotal</td>
                <td class="px-4 py-3 text-right tabular-nums font-bold text-emerald-700">{fmt(wsSubtotal)}</td>
                <td colspan="2"></td>
              </tr>
            </tfoot>
          {/if}
        </table>
      </div>
    </div>
  </div>

{:else}
  <!-- ═══════════════════════════════════════════════════════════════════════ -->
  <!--  DRAFTS REPOSITORY                                                     -->
  <!-- ═══════════════════════════════════════════════════════════════════════ -->
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <div class="flex items-center gap-2">
          <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-700">Bill of Quantities</p>
          <LiveBadge refreshing={live.refreshing} />
        </div>
        <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Drafted BoQs</h1>
        <p class="mt-1 text-sm text-neutral-500">Version-controlled hub for all preliminary costings across projects and sites.</p>
      </div>
      <div class="flex gap-2">
        <button onclick={() => { if (boms.length > 0) openImport(boms[0].id); else toast.error("No BOMs", "Create a BOM first."); }} class="rounded-lg border border-neutral-200 bg-white px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Import CSV</button>
        <a href="/boq/builder" class="rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 shadow-sm no-underline">Open Builder</a>
      </div>
    </div>

    <!-- Filters & Controls -->
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
      <!-- Status tabs -->
      <div class="flex rounded-lg border border-neutral-200 bg-white overflow-hidden">
        {#each STATUS_OPTIONS as opt}
          <button onclick={() => (statusFilter = opt.value)} class="px-3 py-2 text-xs font-medium transition-colors {statusFilter === opt.value ? 'bg-neutral-900 text-white' : 'text-neutral-600 hover:bg-neutral-50'}">{opt.label}</button>
        {/each}
      </div>
      <div class="flex gap-2 ml-auto">
        <input bind:value={searchQuery} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm w-56 focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="Search drafts..." />
        <select bind:value={groupBy} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-xs font-medium text-neutral-700">
          <option value="">No grouping</option>
          <option value="project">Group by Project</option>
          <option value="site">Group by Site</option>
        </select>
      </div>
    </div>

    <!-- Portfolio KPIs -->
    <div class="flex gap-3 flex-wrap">
      <div class="rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-center">
        <p class="text-lg font-bold text-neutral-900 tabular-nums">{filtered.length}</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Drafts</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-center">
        <p class="text-lg font-bold text-emerald-700 tabular-nums">{fmtM(totalPortfolioValue)}</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Portfolio Value</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-center">
        <p class="text-lg font-bold text-amber-600 tabular-nums">{draftCount}</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">In Draft</p>
      </div>
      <div class="rounded-xl border border-neutral-200 bg-white px-4 py-2.5 text-center">
        <p class="text-lg font-bold tabular-nums {confidenceColor(avgConfidence)}">{avgConfidence}%</p>
        <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Avg Confidence</p>
      </div>
    </div>

    <!-- Card Grid -->
    {#if loading}
      <div class="flex items-center justify-center py-16 text-sm text-neutral-400">Loading drafts...</div>
    {:else if filtered.length === 0}
      <div class="rounded-xl border border-neutral-200 bg-white p-12 text-center">
        <p class="text-sm text-neutral-500">{searchQuery || statusFilter ? "No drafts match your filters." : "No BoQ drafts yet. Create your first draft to begin estimating."}</p>
        {#if isDev}
          <button onclick={() => { showCreateModal = true; devFillCreate(); }} class="mt-3 rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill + Create</button>
        {/if}
      </div>
    {:else}
      {#if grouped}
        {#each [...grouped.entries()] as [groupName, groupBoms]}
          <div>
            <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest mb-3">{groupName} ({groupBoms.length})</h3>
            <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {#each groupBoms as bom (bom.id)}
                {@const isDraft = bom.status === "draft"}
                <div
                  role="button" tabindex="0"
                  onclick={() => openWorkspace(bom)}
                  onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openWorkspace(bom); }}}
                  class="group rounded-xl border bg-white/80 p-5 transition-all hover:shadow-lg cursor-pointer {isDraft ? 'border-neutral-300 shadow-[0_0_0_1px_rgba(0,0,0,0.04)]' : 'border-neutral-200'}"
                  style="backdrop-filter: blur(12px)"
                >
                  <div class="flex items-start justify-between gap-2">
                    <div class="flex-1 min-w-0">
                      <p class="text-sm font-bold text-neutral-900 truncate">{bom.name}</p>
                      <p class="text-[10px] text-neutral-400 mt-0.5">{bom.bom_number} &middot; v{bom.version}</p>
                    </div>
                    <span class="shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold {STATUS_COLORS[bom.status] || ''}">{bom.status.replace("_", " ")}</span>
                  </div>

                  {#if bom.project_name}
                    <p class="mt-2 text-xs text-neutral-500">{bom.project_name}</p>
                  {/if}

                  <div class="mt-3 flex items-end justify-between">
                    <div>
                      <p class="text-[10px] text-neutral-400">Total Estimate</p>
                      <p class="text-base font-bold text-emerald-700 tabular-nums">{fmtM(Number(bom.grand_total || bom.total_estimated_cost || 0))}</p>
                    </div>
                    <div class="text-right">
                      <p class="text-[10px] text-neutral-400">Confidence</p>
                      <p class="text-sm font-bold tabular-nums {confidenceColor(bom.confidence_pct)}">{bom.confidence_pct}% <span class="text-[9px] font-normal">({confidenceLabel(bom.confidence_pct)})</span></p>
                    </div>
                  </div>

                  <div class="mt-3 pt-3 border-t border-neutral-100 flex items-center justify-between">
                    <span class="text-[10px] text-neutral-400">{bom.item_count} items &middot; {timeAgo(bom.updated_at)}</span>
                    <div class="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button onclick={(e) => { e.stopPropagation(); cloneBom(bom.id); }} class="rounded px-2 py-0.5 text-[10px] font-medium text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700" title="Clone">Clone</button>
                      <button onclick={(e) => { e.stopPropagation(); deleteBom(bom.id); }} class="rounded px-2 py-0.5 text-[10px] font-medium text-neutral-400 hover:bg-red-50 hover:text-red-600" title="Delete">Delete</button>
                    </div>
                  </div>
                </div>
              {/each}
            </div>
          </div>
        {/each}
      {:else}
        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {#each filtered as bom (bom.id)}
            {@const isDraft = bom.status === "draft"}
            <div
              role="button" tabindex="0"
              onclick={() => openWorkspace(bom)}
              onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openWorkspace(bom); }}}
              class="group rounded-xl border bg-white/80 p-5 transition-all hover:shadow-lg cursor-pointer {isDraft ? 'border-neutral-300 shadow-[0_0_0_1px_rgba(0,0,0,0.04)]' : 'border-neutral-200'}"
              style="backdrop-filter: blur(12px)"
            >
              <div class="flex items-start justify-between gap-2">
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-bold text-neutral-900 truncate">{bom.name}</p>
                  <p class="text-[10px] text-neutral-400 mt-0.5">{bom.bom_number} &middot; v{bom.version}</p>
                </div>
                <span class="shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold {STATUS_COLORS[bom.status] || ''}">{bom.status.replace("_", " ")}</span>
              </div>

              {#if bom.project_name}
                <p class="mt-2 text-xs text-neutral-500">{bom.project_name}</p>
              {/if}

              <div class="mt-3 flex items-end justify-between">
                <div>
                  <p class="text-[10px] text-neutral-400">Total Estimate</p>
                  <p class="text-base font-bold text-emerald-700 tabular-nums">{fmtM(Number(bom.grand_total || bom.total_estimated_cost || 0))}</p>
                </div>
                <div class="text-right">
                  <p class="text-[10px] text-neutral-400">Confidence</p>
                  <p class="text-sm font-bold tabular-nums {confidenceColor(bom.confidence_pct)}">{bom.confidence_pct}% <span class="text-[9px] font-normal">({confidenceLabel(bom.confidence_pct)})</span></p>
                </div>
              </div>

              <div class="mt-3 pt-3 border-t border-neutral-100 flex items-center justify-between">
                <span class="text-[10px] text-neutral-400">{bom.item_count} items &middot; {timeAgo(bom.updated_at)}</span>
                <div class="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button onclick={(e) => { e.stopPropagation(); cloneBom(bom.id); }} class="rounded px-2 py-0.5 text-[10px] font-medium text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700" title="Clone">Clone</button>
                  <button onclick={(e) => { e.stopPropagation(); deleteBom(bom.id); }} class="rounded px-2 py-0.5 text-[10px] font-medium text-neutral-400 hover:bg-red-50 hover:text-red-600" title="Delete">Delete</button>
                </div>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    {/if}
  </div>
{/if}

<!-- Create Modal -->
{#if showCreateModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" style="backdrop-filter: blur(4px)">
    <div class="w-full max-w-lg rounded-2xl border border-neutral-200 bg-white p-6 shadow-2xl">
      <div class="flex items-start justify-between mb-5">
        <div>
          <h2 class="text-lg font-semibold text-neutral-900">New BoQ Draft</h2>
          <p class="mt-1 text-sm text-neutral-500">Create a new bill of quantities for estimation.</p>
        </div>
        <button onclick={() => { showCreateModal = false; }} class="rounded-md border border-neutral-200 bg-white px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50">Close</button>
      </div>
      <div class="space-y-4">
        <label class="block text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Draft Name *</span><input bind:value={createForm.name} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="B-Abuja-002 — 50kW Solar Farm" /></label>
        <label class="block text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Description</span><textarea bind:value={createForm.description} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none" placeholder="Brief description of the scope"></textarea></label>
        <div class="grid grid-cols-2 gap-3">
          <label class="text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Project</span>
            <select bind:value={createForm.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
              <option value="">No project</option>
              {#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}
            </select>
          </label>
          <label class="text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Unit Type</span><input bind:value={createForm.unit_type} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="Villa, Floor, etc." /></label>
        </div>
        <label class="block text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Site Location</span><input bind:value={createForm.site_location} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="Lekki Phase 1, Lagos" /></label>
      </div>
      <div class="mt-6 flex items-center justify-end gap-3">
        {#if isDev}
          <button type="button" onclick={devFillCreate} class="mr-auto rounded-lg bg-orange-500 px-3 py-2 text-xs font-medium text-white hover:bg-orange-600">Dev Fill</button>
        {/if}
        <button onclick={() => { showCreateModal = false; }} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
        <button onclick={createBom} disabled={createSaving} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50">{createSaving ? "Creating..." : "Create Draft"}</button>
      </div>
    </div>
  </div>
{/if}

<!-- CSV Import Modal -->
{#if showImportModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" style="backdrop-filter: blur(4px)">
    <div class="w-full max-w-md rounded-2xl border border-neutral-200 bg-white p-6 shadow-2xl">
      <h2 class="text-base font-semibold text-neutral-900 mb-1">Import Items from CSV</h2>
      <p class="text-xs text-neutral-500 mb-4">Upload a spreadsheet to bulk-add line items to a BOM.</p>

      <div class="space-y-4">
        <label class="block text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block text-xs">Target BOM</span>
          <select bind:value={importBomId} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
            {#each boms as bom}
              <option value={bom.id}>{bom.bom_number} — {bom.name}</option>
            {/each}
          </select>
        </label>

        <label class="block text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block text-xs">CSV File</span>
          <input type="file" accept=".csv,.txt" onchange={(e) => { importFile = (e.target as HTMLInputElement).files?.[0] || null; }}
            class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm file:mr-3 file:rounded-md file:border-0 file:bg-neutral-100 file:px-3 file:py-1 file:text-xs file:font-medium file:text-neutral-700 focus:outline-none" />
        </label>

        <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
          <p class="text-[10px] font-semibold text-neutral-500 uppercase mb-1">Expected Columns</p>
          <p class="text-[10px] text-neutral-500 font-mono">description, quantity, unit, unit_rate, category, section, notes</p>
          <p class="mt-1 text-[10px] text-neutral-400">Column names are flexible — "name", "item", "material_name" also work for description. "qty", "uom", "rate", "unit_cost" are also accepted.</p>
        </div>
      </div>

      <div class="mt-6 flex justify-end gap-3">
        <button onclick={() => { showImportModal = false; }} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
        <button onclick={runImport} disabled={importing || !importFile} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50">
          {importing ? "Importing..." : "Import"}
        </button>
      </div>
    </div>
  </div>
{/if}

<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { onMount } from "svelte";

  // --- Types ---
  interface CatalogItem { id: number; name: string; category: string; unit_of_measure: string; unit_cost: string; }
  interface BomTemplate { id: number; bom_number: string; name: string; item_count: number; total_estimated_cost: string; }
  interface VendorOption { id: number; name: string; category: string; contact_person: string; }
  interface BomItem {
    id: number; inventory_item: number | null; inventory_item_name: string | null;
    material_name: string; category: string; section: string;
    quantity: string; unit_of_measure: string; unit_cost: string; line_total: string;
    notes: string; sort_order: number; supplier: string;
    is_approved: boolean; price_volatile: boolean;
    original_unit_cost: string | null; price_drift_pct: number | null;
    supplier_vendor: number | null; supplier_vendor_name: string | null;
    price_source: string; waste_factor_pct: string; item_markup_pct: string;
    lead_time_days: number; source_bom: number | null;
    quantity_formula: string;
    is_fx_linked: boolean; unit_cost_usd: string;
    effective_quantity: string; effective_line_total: string;
  }
  interface BomDetail {
    id: number; bom_number: string; name: string; description: string;
    project: number | null; project_name: string | null;
    status: string; version: number; confidence_pct: number;
    margin_pct: string; vat_pct: string; site_location: string;
    total_estimated_cost: string; subtotal: string;
    vat_amount: string; margin_amount: string; grand_total: string;
    project_variables: Record<string, number>;
    fx_rate_usd_ngn: string;
    items: BomItem[];
  }

  const NON_INVENTORY_PRESETS = [
    { name: "Skilled Labour (Man-Day)", category: "labor", unit: "man-day", cost: 15000 },
    { name: "Unskilled Labour (Man-Day)", category: "labor", unit: "man-day", cost: 8000 },
    { name: "Site Supervision", category: "labor", unit: "day", cost: 25000 },
    { name: "Logistics / Haulage", category: "logistics", unit: "trip", cost: 50000 },
    { name: "Scaffolding Rental", category: "preliminaries", unit: "week", cost: 120000 },
    { name: "Site Clearing", category: "preliminaries", unit: "sqm", cost: 500 },
    { name: "Building Permit (Lagos)", category: "fees", unit: "ls", cost: 350000 },
    { name: "Engineering Design Fee", category: "fees", unit: "ls", cost: 500000 },
    { name: "Insurance (CAR)", category: "fees", unit: "ls", cost: 200000 },
  ];

  const SECTION_COLORS: Record<string, string> = {
    "": "border-neutral-200", labor: "border-blue-200", logistics: "border-violet-200",
    preliminaries: "border-amber-200", fees: "border-rose-200",
    electrical: "border-indigo-200", civil: "border-emerald-200", mechanical: "border-sky-200",
  };

  // --- Local workspace item (not yet saved to any BoQ) ---
  interface WorkspaceItem {
    _localId: number; // client-only key
    inventory_item: number | null; material_name: string; category: string; section: string;
    quantity: number; unit_of_measure: string; unit_cost: number; notes: string;
    sort_order: number; supplier: string; supplier_vendor: number | null;
    is_approved: boolean; price_volatile: boolean;
    price_source: string; waste_factor_pct: number; item_markup_pct: number;
    lead_time_days: number; source_bom: number | null;
    quantity_formula: string; is_fx_linked: boolean; unit_cost_usd: number;
    original_unit_cost: number | null;
    price_drift_pct: number | null;
  }

  interface ProjectOption { id: number; name: string; }

  // --- State ---
  let loading = $state(true);

  // Source BOM list
  let bomSources = $state<BomTemplate[]>([]);
  let selectedSourceBomId = $state<number | null>(null);
  let sourceBomName = $state("");

  // Sidebar
  let sidebarTab = $state<"catalog" | "bom" | "quick">("catalog");
  let catalogItems = $state<CatalogItem[]>([]);
  let bomTemplates = $state<BomTemplate[]>([]);
  let vendors = $state<VendorOption[]>([]);
  let projects = $state<ProjectOption[]>([]);
  let catalogSearch = $state("");
  let bomSearch = $state("");
  let sidebarCollapsed = $state(false);

  // Workspace (local items — not persisted until "Save as Draft")
  let workspaceItems = $state<WorkspaceItem[]>([]);
  let nextLocalId = $state(1);
  let compactMode = $state(false);
  let collapsedSections = $state<Set<string>>(new Set());

  // Draft metadata
  let draftName = $state("");
  let draftDescription = $state("");
  let draftProject = $state("");
  let draftSiteLocation = $state("");
  let draftMarginPct = $state(10);
  let draftVatPct = $state(7.5);
  let saving = $state(false);

  // Project variables
  let projectVars = $state<Record<string, number>>({});
  let newVarName = $state("");
  let newVarValue = $state("");
  let showVarsPanel = $state(false);

  // FX Engine
  let fxRate = $state(1550);

  // Currency display
  let displayCurrency = $state<"NGN" | "USD">("NGN");

  // Pulse animation
  let pulseKey = $state(0);

  // Item detail drawer
  let showItemDrawer = $state(false);
  let itemDrawerVisible = $state(false);
  let editingItem = $state<WorkspaceItem | null>(null);
  let itemForm = $state(emptyItemForm());

  // Expand BOM modal
  let showExpandModal = $state(false);
  let expandBomId = $state<number | null>(null);
  let expandMultiplier = $state(1);
  let expandSection = $state("");

  // Save as Draft modal
  let showSaveModal = $state(false);

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  // --- Computed (all from local workspaceItems) ---
  const filteredCatalog = $derived.by(() => {
    if (!catalogSearch.trim()) return catalogItems;
    const q = catalogSearch.trim().toLowerCase();
    return catalogItems.filter(i => i.name.toLowerCase().includes(q) || i.category.toLowerCase().includes(q));
  });

  const filteredBoms = $derived.by(() => {
    if (!bomSearch.trim()) return bomTemplates;
    const q = bomSearch.trim().toLowerCase();
    return bomTemplates.filter(b => b.name.toLowerCase().includes(q) || b.bom_number.toLowerCase().includes(q));
  });

  function lineTotal(item: WorkspaceItem): number {
    const effectiveQty = item.quantity * (1 + item.waste_factor_pct / 100);
    const base = effectiveQty * item.unit_cost;
    return base * (1 + item.item_markup_pct / 100);
  }

  const sections = $derived.by(() => {
    if (workspaceItems.length === 0) return [];
    const map = new Map<string, WorkspaceItem[]>();
    for (const item of workspaceItems) {
      const sec = item.section || "Uncategorized";
      if (!map.has(sec)) map.set(sec, []);
      map.get(sec)!.push(item);
    }
    return Array.from(map.entries()).map(([name, items]) => ({
      name,
      items,
      subtotal: items.reduce((s, i) => s + lineTotal(i), 0),
      itemCount: items.length,
      approvedCount: items.filter(i => i.is_approved).length,
    }));
  });

  const wsSubtotal = $derived(workspaceItems.reduce((s, i) => s + lineTotal(i), 0));
  const wsMargin = $derived(wsSubtotal * draftMarginPct / 100);
  const wsVat = $derived(wsSubtotal * draftVatPct / 100);
  const wsGrandTotal = $derived(wsSubtotal + wsVat + wsMargin);

  const marginHealthy = $derived(draftMarginPct >= 15);
  const missingRateCount = $derived(workspaceItems.filter(i => i.quantity === 0 || i.unit_cost === 0).length);
  const fxLinkedCount = $derived(workspaceItems.filter(i => i.is_fx_linked).length);
  const hasItems = $derived(workspaceItems.length > 0);

  const categoryBreakdown = $derived.by(() => {
    if (workspaceItems.length === 0) return [];
    const map = new Map<string, number>();
    for (const item of workspaceItems) {
      const cat = item.category || "other";
      map.set(cat, (map.get(cat) || 0) + lineTotal(item));
    }
    const total = [...map.values()].reduce((s, v) => s + v, 0) || 1;
    return Array.from(map.entries())
      .map(([cat, val]) => ({ category: cat, value: val, pct: val / total * 100 }))
      .sort((a, b) => b.value - a.value);
  });

  const formulaLinkedItems = $derived(workspaceItems.filter(i => i.quantity_formula?.trim()));

  function emptyItemForm() {
    return {
      material_name: "", category: "", section: "", quantity: "1",
      unit_of_measure: "pcs", unit_cost: "0", notes: "", supplier: "",
      price_source: "manual", waste_factor_pct: "0", item_markup_pct: "0",
      lead_time_days: 0, is_approved: false, price_volatile: false,
      quantity_formula: "",
      is_fx_linked: false, unit_cost_usd: "0",
      supplier_vendor: "",
    };
  }

  function fmt(n: number): string {
    if (displayCurrency === "USD") {
      const usd = fxRate > 0 ? n / fxRate : 0;
      return `$${usd.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
    }
    return `\u20A6${Math.round(n).toLocaleString()}`;
  }

  // --- Formula evaluator ---
  function evaluateFormula(formula: string, vars: Record<string, number>): number | null {
    if (!formula.trim()) return null;
    try {
      let expr = formula.trim();
      for (const [name, val] of Object.entries(vars)) {
        expr = expr.replaceAll(name, String(val));
      }
      if (!/^[\d\s+\-*/().]+$/.test(expr)) return null;
      const result = Function(`"use strict"; return (${expr})`)();
      return typeof result === "number" && isFinite(result) ? Math.round(result * 100) / 100 : null;
    } catch { return null; }
  }

  // --- Project variable management ---
  function addVariable() {
    if (!newVarName.trim() || !newVarValue) return;
    const key = newVarName.trim().toLowerCase().replace(/\s+/g, "_").replace(/[^a-z0-9_]/g, "");
    if (!key) return;
    projectVars = { ...projectVars, [key]: Number(newVarValue) || 0 };
    newVarName = ""; newVarValue = "";
  }

  function removeVariable(key: string) {
    const next = { ...projectVars };
    delete next[key];
    projectVars = next;
  }

  function recalcFormulaItems() {
    workspaceItems = workspaceItems.map(item => {
      if (!item.quantity_formula?.trim()) return item;
      const computed = evaluateFormula(item.quantity_formula, projectVars);
      if (computed !== null) return { ...item, quantity: computed };
      return item;
    });
    pulseKey++;
  }

  function applyFxRate() {
    workspaceItems = workspaceItems.map(item => {
      if (!item.is_fx_linked || !item.unit_cost_usd) return item;
      return { ...item, unit_cost: item.unit_cost_usd * fxRate };
    });
    pulseKey++;
    toast.success("FX Applied", `${fxLinkedCount} items recalculated at ${fxRate}.`);
  }

  // --- Workspace helpers ---
  function newLocalId(): number { return nextLocalId++; }

  function addToWorkspace(partial: Partial<WorkspaceItem>) {
    const item: WorkspaceItem = {
      _localId: newLocalId(),
      inventory_item: null, material_name: "", category: "", section: "Uncategorized",
      quantity: 1, unit_of_measure: "pcs", unit_cost: 0, notes: "",
      sort_order: workspaceItems.length, supplier: "", supplier_vendor: null,
      is_approved: false, price_volatile: false,
      price_source: "manual", waste_factor_pct: 0, item_markup_pct: 0,
      lead_time_days: 0, source_bom: null, quantity_formula: "",
      is_fx_linked: false, unit_cost_usd: 0, original_unit_cost: null, price_drift_pct: null,
      ...partial,
    };
    workspaceItems = [...workspaceItems, item];
    pulseKey++;
  }

  // --- API ---
  async function loadCatalog() {
    try {
      const res = await api.get<{ inventory_items: CatalogItem[]; bom_templates: BomTemplate[]; vendors: VendorOption[] }>("/bom/catalog/");
      catalogItems = res.inventory_items;
      bomTemplates = res.bom_templates;
      bomSources = res.bom_templates; // same list for the main dropdown
      vendors = res.vendors || [];
    } catch { /* catalog is optional */ }
  }

  async function loadProjects() {
    try {
      const res = await api.get<{ results: ProjectOption[] }>("/projects/", { page_size: "100", fields: "id,name" });
      projects = res.results;
    } catch { /* optional */ }
  }

  async function selectSourceBom(id: number) {
    selectedSourceBomId = id;
    loading = true;
    try {
      const bom = await api.get<BomDetail>(`/bom/${id}/`);
      sourceBomName = bom.name;
      draftName = `${bom.name} — BoQ`;
      draftDescription = bom.description || "";
      // Expand BOM items into workspace
      workspaceItems = bom.items.map((item, idx) => ({
        _localId: newLocalId(),
        inventory_item: item.inventory_item,
        material_name: item.material_name,
        category: item.category,
        section: item.section || bom.name,
        quantity: Number(item.quantity) || 0,
        unit_of_measure: item.unit_of_measure,
        unit_cost: Number(item.unit_cost) || 0,
        notes: item.notes,
        sort_order: idx,
        supplier: item.supplier,
        supplier_vendor: item.supplier_vendor,
        is_approved: false,
        price_volatile: item.price_volatile,
        price_source: item.price_source || "warehouse",
        waste_factor_pct: Number(item.waste_factor_pct) || 0,
        item_markup_pct: Number(item.item_markup_pct) || 0,
        lead_time_days: item.lead_time_days || 0,
        source_bom: bom.id,
        quantity_formula: item.quantity_formula || "",
        is_fx_linked: item.is_fx_linked || false,
        unit_cost_usd: Number(item.unit_cost_usd) || 0,
        original_unit_cost: Number(item.unit_cost) || 0,
        price_drift_pct: item.price_drift_pct,
      }));
      pulseKey++;
      toast.success("BOM Loaded", `${bom.items.length} items expanded from "${bom.name}".`);
    } catch { toast.error("Load failed", "Could not load BOM."); }
    finally { loading = false; }
  }

  // Add more items from another BOM into the existing workspace
  function expandBomIntoWorkspace() {
    if (!expandBomId) return;
    const bomId = expandBomId;
    api.get<BomDetail>(`/bom/${bomId}/`).then(bom => {
      for (const item of bom.items) {
        addToWorkspace({
          inventory_item: item.inventory_item,
          material_name: item.material_name,
          category: item.category,
          section: expandSection || bom.name,
          quantity: (Number(item.quantity) || 0) * expandMultiplier,
          unit_of_measure: item.unit_of_measure,
          unit_cost: Number(item.unit_cost) || 0,
          supplier: item.supplier,
          source_bom: bom.id,
          price_source: "warehouse",
          original_unit_cost: Number(item.unit_cost) || 0,
        });
      }
      showExpandModal = false;
      toast.success("Expanded", `${bom.items.length} items added from "${bom.name}".`);
    }).catch(() => toast.error("Failed", "Could not expand BOM."));
  }

  // --- Line Item Operations (all local) ---
  function addCatalogItem(item: CatalogItem) {
    addToWorkspace({
      inventory_item: item.id,
      material_name: item.name,
      category: item.category,
      unit_of_measure: item.unit_of_measure,
      unit_cost: Number(item.unit_cost) || 0,
      original_unit_cost: Number(item.unit_cost) || 0,
      price_source: "warehouse",
      section: item.category || "Materials",
    });
    toast.success("Added", `${item.name} added.`);
  }

  function addPresetItem(preset: typeof NON_INVENTORY_PRESETS[0]) {
    addToWorkspace({
      material_name: preset.name,
      category: preset.category,
      unit_of_measure: preset.unit,
      unit_cost: preset.cost,
      price_source: "manual",
      section: preset.category.charAt(0).toUpperCase() + preset.category.slice(1),
    });
    toast.success("Added", `${preset.name} added.`);
  }

  function updateItemInline(item: WorkspaceItem, field: string, value: any) {
    workspaceItems = workspaceItems.map(i => i._localId === item._localId ? { ...i, [field]: value } : i);
    pulseKey++;
  }

  function deleteItem(localId: number) {
    workspaceItems = workspaceItems.filter(i => i._localId !== localId);
    pulseKey++;
  }

  function openItemDrawer(item: WorkspaceItem) {
    editingItem = item;
    itemForm = {
      material_name: item.material_name, category: item.category,
      section: item.section, quantity: String(item.quantity),
      unit_of_measure: item.unit_of_measure, unit_cost: String(item.unit_cost),
      notes: item.notes, supplier: item.supplier,
      price_source: item.price_source, waste_factor_pct: String(item.waste_factor_pct),
      item_markup_pct: String(item.item_markup_pct), lead_time_days: item.lead_time_days,
      is_approved: item.is_approved, price_volatile: item.price_volatile,
      quantity_formula: item.quantity_formula || "",
      is_fx_linked: item.is_fx_linked || false,
      unit_cost_usd: String(item.unit_cost_usd || 0),
      supplier_vendor: item.supplier_vendor ? String(item.supplier_vendor) : "",
    };
    showItemDrawer = true;
    requestAnimationFrame(() => { itemDrawerVisible = true; });
  }

  function closeItemDrawer() {
    itemDrawerVisible = false;
    setTimeout(() => { showItemDrawer = false; editingItem = null; }, 300);
  }

  function saveItemDetail() {
    if (!editingItem) return;
    const updated: WorkspaceItem = {
      ...editingItem,
      material_name: itemForm.material_name,
      category: itemForm.category,
      section: itemForm.section,
      quantity: Number(itemForm.quantity) || 0,
      unit_of_measure: itemForm.unit_of_measure,
      unit_cost: itemForm.is_fx_linked ? (Number(itemForm.unit_cost_usd) || 0) * fxRate : Number(itemForm.unit_cost) || 0,
      notes: itemForm.notes,
      supplier: itemForm.supplier,
      supplier_vendor: itemForm.supplier_vendor ? Number(itemForm.supplier_vendor) : null,
      price_source: itemForm.price_source,
      waste_factor_pct: Number(itemForm.waste_factor_pct) || 0,
      item_markup_pct: Number(itemForm.item_markup_pct) || 0,
      lead_time_days: Number(itemForm.lead_time_days) || 0,
      quantity_formula: itemForm.quantity_formula,
      is_fx_linked: itemForm.is_fx_linked,
      unit_cost_usd: Number(itemForm.unit_cost_usd) || 0,
      is_approved: itemForm.is_approved,
      price_volatile: itemForm.price_volatile,
    };
    workspaceItems = workspaceItems.map(i => i._localId === editingItem!._localId ? updated : i);
    closeItemDrawer();
    pulseKey++;
    toast.success("Updated", "Item details saved.");
  }

  // --- Save as Draft (persist to backend) ---
  async function saveAsDraft() {
    if (!draftName.trim()) { toast.error("Required", "Draft name is required."); return; }
    if (workspaceItems.length === 0) { toast.error("Empty", "Add at least one item before saving."); return; }
    saving = true;
    try {
      const payload = {
        name: draftName,
        description: draftDescription,
        project: draftProject ? Number(draftProject) : null,
        site_location: draftSiteLocation,
        margin_pct: draftMarginPct,
        vat_pct: draftVatPct,
        fx_rate_usd_ngn: fxRate,
        project_variables: projectVars,
        items: workspaceItems.map((item, idx) => ({
          inventory_item: item.inventory_item,
          material_name: item.material_name,
          category: item.category,
          section: item.section,
          quantity: item.quantity,
          unit_of_measure: item.unit_of_measure,
          unit_cost: item.unit_cost,
          notes: item.notes,
          sort_order: idx,
          supplier: item.supplier,
          supplier_vendor: item.supplier_vendor,
          is_approved: item.is_approved,
          price_volatile: item.price_volatile,
          price_source: item.price_source,
          waste_factor_pct: item.waste_factor_pct,
          item_markup_pct: item.item_markup_pct,
          lead_time_days: item.lead_time_days,
          source_bom: item.source_bom,
          quantity_formula: item.quantity_formula,
          is_fx_linked: item.is_fx_linked,
          unit_cost_usd: item.unit_cost_usd,
          original_unit_cost: item.original_unit_cost,
        })),
      };
      await api.post("/bom/", payload);
      showSaveModal = false;
      toast.success("Draft Created", `"${draftName}" saved with ${workspaceItems.length} items. View it in Drafted BoQs.`);
      // Reset workspace
      workspaceItems = [];
      selectedSourceBomId = null;
      sourceBomName = "";
      draftName = "";
      draftDescription = "";
    } catch (err) {
      if (err instanceof ApiError) toast.error("Failed", Object.values(err.fieldErrors).flat().join(" ") || "Could not save draft.");
      else toast.error("Failed", "Could not save draft.");
    } finally { saving = false; }
  }

  function toggleSection(name: string) {
    const next = new Set(collapsedSections);
    if (next.has(name)) next.delete(name); else next.add(name);
    collapsedSections = next;
  }

  function collapseAll() { collapsedSections = new Set(sections.map(s => s.name)); }
  function expandAll() { collapsedSections = new Set(); }

  function moveSectionUp(sectionName: string) {
    const secNames = sections.map(s => s.name);
    const idx = secNames.indexOf(sectionName);
    if (idx <= 0) return;
    const prevSection = secNames[idx - 1];
    const prevItems = workspaceItems.filter(i => (i.section || "Uncategorized") === prevSection);
    const currItems = workspaceItems.filter(i => (i.section || "Uncategorized") === sectionName);
    const rest = workspaceItems.filter(i => (i.section || "Uncategorized") !== prevSection && (i.section || "Uncategorized") !== sectionName);
    // Rebuild: everything before prev, then curr, then prev, then rest after
    const allBefore = workspaceItems.slice(0, workspaceItems.indexOf(prevItems[0]));
    const allAfter = workspaceItems.slice(workspaceItems.indexOf(prevItems[prevItems.length - 1]) + 1).filter(i => !currItems.includes(i));
    workspaceItems = [...allBefore.filter(i => !currItems.includes(i)), ...currItems, ...prevItems, ...allAfter];
    pulseKey++;
  }

  function moveSectionDown(sectionName: string) {
    const secNames = sections.map(s => s.name);
    const idx = secNames.indexOf(sectionName);
    if (idx < 0 || idx >= secNames.length - 1) return;
    const nextSection = secNames[idx + 1];
    const nextItems = workspaceItems.filter(i => (i.section || "Uncategorized") === nextSection);
    const currItems = workspaceItems.filter(i => (i.section || "Uncategorized") === sectionName);
    const allBefore = workspaceItems.slice(0, workspaceItems.indexOf(currItems[0]));
    const allAfter = workspaceItems.slice(workspaceItems.indexOf(nextItems[nextItems.length - 1]) + 1);
    workspaceItems = [...allBefore, ...nextItems, ...currItems, ...allAfter];
    pulseKey++;
  }

  function sectionColor(name: string): string {
    const lower = name.toLowerCase();
    for (const [key, cls] of Object.entries(SECTION_COLORS)) {
      if (key && lower.includes(key)) return cls;
    }
    return "border-neutral-200";
  }

  onMount(async () => {
    await Promise.all([loadCatalog(), loadProjects()]);
    loading = false;
  });
</script>

<svelte:head><title>Estimate Architect — BoQ | developerOS</title></svelte:head>

<div class="flex gap-0 -mx-6 -mt-6" style="height: calc(100vh - 64px)">
  <!-- ═══════ LEFT SIDEBAR — Assembly Toolbox ═══════ -->
  {#if !sidebarCollapsed}
    <div class="w-72 shrink-0 border-r border-neutral-200 bg-white/80 flex flex-col overflow-hidden" style="backdrop-filter: blur(12px)">
      <!-- Sidebar header -->
      <div class="flex items-center justify-between border-b border-neutral-100 px-4 py-3">
        <h3 class="text-[10px] font-semibold text-neutral-700 uppercase tracking-widest">Toolbox</h3>
        <button onclick={() => { sidebarCollapsed = true; }} class="rounded p-1 text-neutral-400 hover:text-neutral-700" aria-label="Collapse sidebar">
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" /></svg>
        </button>
      </div>

      <!-- Tabs -->
      <div class="flex border-b border-neutral-100">
        <button onclick={() => (sidebarTab = "catalog")} class="flex-1 px-3 py-2 text-[10px] font-semibold uppercase tracking-wider transition-colors {sidebarTab === 'catalog' ? 'text-neutral-900 border-b-2 border-neutral-900' : 'text-neutral-400 hover:text-neutral-600'}">Catalog</button>
        <button onclick={() => (sidebarTab = "bom")} class="flex-1 px-3 py-2 text-[10px] font-semibold uppercase tracking-wider transition-colors {sidebarTab === 'bom' ? 'text-neutral-900 border-b-2 border-neutral-900' : 'text-neutral-400 hover:text-neutral-600'}">BOMs</button>
        <button onclick={() => (sidebarTab = "quick")} class="flex-1 px-3 py-2 text-[10px] font-semibold uppercase tracking-wider transition-colors {sidebarTab === 'quick' ? 'text-neutral-900 border-b-2 border-neutral-900' : 'text-neutral-400 hover:text-neutral-600'}">Quick Add</button>
      </div>

      <!-- Sidebar content -->
      <div class="flex-1 overflow-y-auto">
        {#if sidebarTab === "catalog"}
          <div class="p-3">
            <input bind:value={catalogSearch} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="Search inventory..." />
          </div>
          <div class="px-3 pb-3 space-y-1">
            {#each filteredCatalog as item (item.id)}
              <button
                onclick={() => addCatalogItem(item)}
                disabled={false}
                class="w-full text-left rounded-lg border border-neutral-100 bg-white px-3 py-2 hover:border-emerald-300 hover:bg-emerald-50/50 transition-all disabled:opacity-40 group relative"
              >
                <p class="text-xs font-medium text-neutral-800 truncate">{item.name}</p>
                <div class="flex items-center justify-between mt-0.5">
                  <span class="text-[10px] text-neutral-400 capitalize">{item.category}</span>
                  <span class="text-[10px] tabular-nums text-neutral-500">{fmt(Number(item.unit_cost))}/{item.unit_of_measure}</span>
                </div>
                <span class="text-[10px] font-semibold text-emerald-600 tabular-nums opacity-0 group-hover:opacity-100 transition-opacity absolute top-2 right-2">+ Add</span>
              </button>
            {/each}
            {#if filteredCatalog.length === 0}
              <p class="text-xs text-neutral-400 text-center py-4">No items found.</p>
            {/if}
          </div>

        {:else if sidebarTab === "bom"}
          <div class="p-3">
            <input bind:value={bomSearch} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-xs focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="Search BOMs..." />
          </div>
          <div class="px-3 pb-3 space-y-1">
            {#each filteredBoms as bt (bt.id)}
              <button
                onclick={() => { expandBomId = bt.id; expandSection = bt.name; showExpandModal = true; }}
                disabled={false}
                class="w-full text-left rounded-lg border border-neutral-100 bg-white px-3 py-2 hover:border-indigo-300 hover:bg-indigo-50/50 transition-all disabled:opacity-40 group"
              >
                <div class="flex items-center justify-between">
                  <p class="text-xs font-medium text-neutral-800 truncate">{bt.name}</p>
                  <span class="text-[9px] text-neutral-400">{bt.bom_number}</span>
                </div>
                <div class="flex items-center justify-between mt-0.5">
                  <span class="text-[10px] text-neutral-400">{bt.item_count} items</span>
                  <span class="text-[10px] font-semibold text-indigo-600 tabular-nums opacity-0 group-hover:opacity-100 transition-opacity">Expand</span>
                </div>
              </button>
            {/each}
            {#if filteredBoms.length === 0}
              <p class="text-xs text-neutral-400 text-center py-4">{bomSearch ? "No BOMs match your search." : "No BOM templates found."}</p>
            {/if}
          </div>

        {:else}
          <div class="px-3 py-3 space-y-1">
            <p class="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider mb-2 px-1">Non-Inventory Items</p>
            {#each NON_INVENTORY_PRESETS as preset}
              <button
                onclick={() => addPresetItem(preset)}
                disabled={false}
                class="w-full text-left rounded-lg border border-neutral-100 bg-white px-3 py-2 hover:border-blue-300 hover:bg-blue-50/50 transition-all disabled:opacity-40 group"
              >
                <p class="text-xs font-medium text-neutral-800">{preset.name}</p>
                <div class="flex items-center justify-between mt-0.5">
                  <span class="text-[10px] text-neutral-400 capitalize">{preset.category}</span>
                  <span class="text-[10px] tabular-nums text-neutral-500">{fmt(preset.cost)}/{preset.unit}</span>
                </div>
              </button>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  {/if}

  <!-- ═══════ MAIN CONTENT ═══════ -->
  <div class="flex-1 flex flex-col overflow-hidden">
    <!-- Top bar -->
    <div class="shrink-0 border-b border-neutral-200 bg-white px-6 py-3">
      <div class="flex items-center gap-4">
        {#if sidebarCollapsed}
          <button onclick={() => { sidebarCollapsed = false; }} class="rounded p-1.5 text-neutral-400 hover:text-neutral-700 border border-neutral-200" aria-label="Open sidebar">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" /></svg>
          </button>
        {/if}

        <!-- BOM source selector -->
        <select onchange={(e) => { const id = Number((e.target as HTMLSelectElement).value); if (id) selectSourceBom(id); }} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm font-medium min-w-[260px] focus:outline-none focus:ring-2 focus:ring-neutral-900">
          <option value="">Select a BOM to expand...</option>
          {#each bomSources as bom}
            <option value={bom.id} selected={bom.id === selectedSourceBomId}>{bom.bom_number} — {bom.name}</option>
          {/each}
        </select>

        {#if hasItems}
          <span class="text-xs text-neutral-400">{workspaceItems.length} items</span>
          {#if sourceBomName}
            <span class="rounded-full bg-indigo-50 border border-indigo-200 px-2.5 py-0.5 text-[10px] font-semibold text-indigo-700">from: {sourceBomName}</span>
          {/if}
        {/if}

        <div class="ml-auto flex items-center gap-3">
          {#if hasItems}
            <!-- Validation badges -->
            {#if missingRateCount > 0}
              <span class="rounded-full bg-amber-50 border border-amber-200 px-2.5 py-0.5 text-[10px] font-semibold text-amber-700">{missingRateCount} missing rates</span>
            {/if}
            {#if !marginHealthy}
              <span class="rounded-full bg-red-50 border border-red-200 px-2.5 py-0.5 text-[10px] font-semibold text-red-700">Margin &lt; 15%</span>
            {/if}

            <!-- Grand total -->
            <!-- FX Engine -->
            <div class="flex items-center gap-1.5 rounded-lg border border-neutral-200 bg-white px-2 py-1.5">
              <span class="text-[9px] font-semibold text-neutral-400 uppercase">USD/NGN</span>
              <input type="number" bind:value={fxRate} step="10" class="w-20 rounded border border-neutral-200 px-2 py-0.5 text-xs tabular-nums text-right focus:outline-none focus:ring-1 focus:ring-neutral-900" />
              <button onclick={applyFxRate} class="rounded bg-neutral-800 px-2 py-0.5 text-[10px] font-medium text-white hover:bg-neutral-700">Apply</button>
              {#if fxLinkedCount > 0}
                <span class="text-[9px] text-indigo-500 tabular-nums">{fxLinkedCount} linked</span>
              {/if}
            </div>

            <div class="text-right">
              <p class="text-[9px] text-emerald-600 uppercase tracking-wider font-semibold">Grand Total</p>
              {#key pulseKey}
                <p class="text-lg font-bold text-emerald-700 tabular-nums pulse-total">{fmt(wsGrandTotal)}</p>
              {/key}
            </div>
          {/if}

          <div class="flex items-center gap-1.5">
            <!-- Currency toggle -->
            <div class="flex rounded-md border border-neutral-200 overflow-hidden">
              <button onclick={() => (displayCurrency = "NGN")} class="px-2 py-1 text-[10px] font-medium transition-colors {displayCurrency === 'NGN' ? 'bg-neutral-900 text-white' : 'text-neutral-500 hover:bg-neutral-50'}">{String.fromCharCode(8358)}</button>
              <button onclick={() => (displayCurrency = "USD")} class="px-2 py-1 text-[10px] font-medium transition-colors {displayCurrency === 'USD' ? 'bg-neutral-900 text-white' : 'text-neutral-500 hover:bg-neutral-50'}">$</button>
            </div>
            <!-- Export -->
            <button onclick={collapseAll} class="rounded border border-neutral-200 px-2 py-1 text-[10px] font-medium text-neutral-500 hover:bg-neutral-50" title="Collapse All">Collapse</button>
            <button onclick={expandAll} class="rounded border border-neutral-200 px-2 py-1 text-[10px] font-medium text-neutral-500 hover:bg-neutral-50" title="Expand All">Expand</button>
            <label class="flex items-center gap-1.5 rounded border border-neutral-200 px-2 py-1 cursor-pointer">
              <input type="checkbox" bind:checked={compactMode} class="rounded border-neutral-300 text-neutral-900 w-3 h-3" />
              <span class="text-[10px] font-medium text-neutral-500">Compact</span>
            </label>
            {#if hasItems}
              <button onclick={() => { showSaveModal = true; }} class="rounded-lg bg-emerald-600 px-3 py-1.5 text-[10px] font-semibold text-white hover:bg-emerald-700 shadow-sm">Save as Draft</button>
            {/if}
          </div>
        </div>
      </div>
    </div>

    <!-- Builder workspace -->
    <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
      <!-- Page header -->
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-700">Bill of Quantities</p>
        <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Estimate Architect</h1>
        <p class="mt-1 text-sm text-neutral-500">Assemble, price, and structure your project cost estimates from BOMs, inventory, and custom line items.</p>
      </div>

      {#if !hasItems && !loading}
        <div class="flex items-center justify-center py-16">
          <div class="text-center">
            <p class="text-sm text-neutral-500">Select a BOM from the dropdown to expand its items, or add items from the sidebar.</p>
            <p class="text-xs text-neutral-400 mt-1">When you're done, hit "Save as Draft" to create a BoQ.</p>
          </div>
        </div>
      {:else if loading}
        <div class="flex items-center justify-center py-16 text-sm text-neutral-400">Loading...</div>
      {:else}

        <!-- Project Variables Panel -->
        <div class="rounded-xl border border-neutral-200 bg-white/80 overflow-hidden" style="backdrop-filter: blur(12px)">
          <button onclick={() => { showVarsPanel = !showVarsPanel; }} class="w-full flex items-center justify-between px-5 py-3 hover:bg-neutral-50 transition-colors text-left">
            <div class="flex items-center gap-2">
              <svg class="w-4 h-4 text-indigo-500 transition-transform {showVarsPanel ? 'rotate-90' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" /></svg>
              <h3 class="text-[10px] font-semibold text-neutral-700 uppercase tracking-widest">Project Variables</h3>
              <span class="rounded-full bg-indigo-50 border border-indigo-200 px-2 py-0.5 text-[9px] font-semibold text-indigo-600 tabular-nums">{Object.keys(projectVars).length}</span>
              {#if formulaLinkedItems.length > 0}
                <span class="rounded-full bg-emerald-50 border border-emerald-200 px-2 py-0.5 text-[9px] font-semibold text-emerald-600 tabular-nums">{formulaLinkedItems.length} linked</span>
              {/if}
            </div>
            <span class="text-[10px] text-neutral-400">{showVarsPanel ? "Collapse" : "Expand"}</span>
          </button>
          {#if showVarsPanel}
            <div class="border-t border-neutral-100 px-5 py-4 space-y-3">
              <p class="text-xs text-neutral-500">Define project-level variables that formulas can reference (e.g. <code class="bg-neutral-100 px-1 rounded text-[10px]">panel_count</code>, <code class="bg-neutral-100 px-1 rounded text-[10px]">floor_area_sqm</code>).</p>
              {#if Object.keys(projectVars).length > 0}
                <div class="flex flex-wrap gap-2">
                  {#each Object.entries(projectVars) as [key, val]}
                    <div class="flex items-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50/50 px-3 py-1.5">
                      <span class="text-xs font-mono font-semibold text-indigo-700">{key}</span>
                      <span class="text-xs text-neutral-400">=</span>
                      <input
                        type="number"
                        value={val}
                        onchange={(e) => { projectVars = { ...projectVars, [key]: Number((e.target as HTMLInputElement).value) || 0 }; }}
                        class="w-20 rounded border border-indigo-200 bg-white px-2 py-0.5 text-xs tabular-nums text-right focus:outline-none focus:ring-1 focus:ring-indigo-400"
                      />
                      <button onclick={() => removeVariable(key)} class="text-indigo-300 hover:text-red-500 transition-colors" aria-label="Remove variable">&times;</button>
                    </div>
                  {/each}
                </div>
              {/if}
              <div class="flex gap-2">
                <input bind:value={newVarName} class="flex-1 rounded-lg border border-neutral-200 px-3 py-1.5 text-xs font-mono" placeholder="variable_name" />
                <input type="number" bind:value={newVarValue} class="w-24 rounded-lg border border-neutral-200 px-3 py-1.5 text-xs tabular-nums" placeholder="Value" />
                <button onclick={addVariable} class="rounded-lg border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50">Add</button>
                <button onclick={recalcFormulaItems} class="rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-700">Apply & Recalc</button>
              </div>
            </div>
          {/if}
        </div>

        <!-- Category breakdown bar -->
        {#if categoryBreakdown.length > 0}
          {@const CHART_COLORS = ["#10b981", "#3b82f6", "#f59e0b", "#8b5cf6", "#f43f5e", "#0ea5e9", "#f97316", "#14b8a6", "#818cf8", "#737373"]}
          {@const donutSize = 140}
          {@const donutStroke = 28}
          {@const donutRadius = (donutSize - donutStroke) / 2}
          {@const donutCircum = 2 * Math.PI * donutRadius}
          <div class="rounded-xl border border-neutral-200 bg-white/80 p-5" style="backdrop-filter: blur(12px)">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest">Spend Distribution</h3>
              <span class="text-xs text-neutral-400 tabular-nums">{fmt(wsSubtotal)} subtotal</span>
            </div>
            <div class="flex gap-6 items-center">
              <!-- Donut chart -->
              <div class="shrink-0 relative" style="width: {donutSize}px; height: {donutSize}px">
                <svg width={donutSize} height={donutSize} viewBox="0 0 {donutSize} {donutSize}" class="transform -rotate-90">
                  <!-- Background ring -->
                  <circle cx={donutSize/2} cy={donutSize/2} r={donutRadius} fill="none" stroke="#f5f5f5" stroke-width={donutStroke} />
                  <!-- Category arcs -->
                  {#each categoryBreakdown as cat, i}
                    {@const offset = categoryBreakdown.slice(0, i).reduce((s, c) => s + c.pct, 0)}
                    <circle
                      cx={donutSize/2} cy={donutSize/2} r={donutRadius}
                      fill="none"
                      stroke={CHART_COLORS[i % CHART_COLORS.length]}
                      stroke-width={donutStroke}
                      stroke-dasharray="{cat.pct / 100 * donutCircum} {donutCircum}"
                      stroke-dashoffset="{-offset / 100 * donutCircum}"
                      class="transition-all duration-500"
                    />
                  {/each}
                </svg>
                <div class="absolute inset-0 flex flex-col items-center justify-center">
                  <p class="text-lg font-bold text-neutral-900 tabular-nums">{categoryBreakdown.length}</p>
                  <p class="text-[8px] text-neutral-400 uppercase tracking-wider">Categories</p>
                </div>
              </div>

              <!-- Legend -->
              <div class="flex-1 grid grid-cols-2 gap-x-4 gap-y-1.5">
                {#each categoryBreakdown as cat, i}
                  <div class="flex items-center gap-2">
                    <span class="inline-block w-2.5 h-2.5 rounded-full shrink-0" style="background: {CHART_COLORS[i % CHART_COLORS.length]}"></span>
                    <span class="text-[10px] text-neutral-600 capitalize truncate flex-1">{cat.category}</span>
                    <span class="text-[10px] font-bold text-neutral-800 tabular-nums">{cat.pct.toFixed(0)}%</span>
                  </div>
                {/each}
              </div>
            </div>
          </div>
        {/if}

        <!-- Variance Tracker (Budget vs Estimate by section) -->
        {#if hasItems && sections.length > 0}
          <div class="rounded-xl border border-neutral-200 bg-white/80 overflow-hidden" style="backdrop-filter: blur(12px)">
            <div class="border-b border-neutral-100 bg-neutral-50 px-5 py-3">
              <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest">Budget vs Estimate — Variance Tracker</h3>
            </div>
            <table class="w-full text-xs">
              <thead>
                <tr class="border-b border-neutral-100">
                  <th class="px-5 py-2 text-left font-medium text-neutral-500">Section</th>
                  <th class="px-4 py-2 text-right font-medium text-neutral-500">Items</th>
                  <th class="px-4 py-2 text-right font-medium text-neutral-500">Estimate</th>
                  <th class="px-4 py-2 text-right font-medium text-neutral-500">% of Total</th>
                  <th class="px-4 py-2 text-left font-medium text-neutral-500 w-40">Distribution</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-50">
                {#each sections as sec}
                  {@const pct = wsSubtotal > 0 ? sec.subtotal / wsSubtotal * 100 : 0}
                  {@const isOverweight = pct > 40}
                  <tr class="hover:bg-neutral-50/50">
                    <td class="px-5 py-2 font-semibold text-neutral-800">{sec.name}</td>
                    <td class="px-4 py-2 text-right tabular-nums text-neutral-600">{sec.itemCount}</td>
                    <td class="px-4 py-2 text-right tabular-nums font-medium {isOverweight ? 'text-amber-700' : 'text-neutral-900'}">{fmt(sec.subtotal)}</td>
                    <td class="px-4 py-2 text-right tabular-nums {isOverweight ? 'font-bold text-amber-700' : 'text-neutral-600'}">{pct.toFixed(1)}%</td>
                    <td class="px-4 py-2">
                      <div class="h-2.5 rounded-full bg-neutral-100 overflow-hidden">
                        <div class="h-full rounded-full transition-all {isOverweight ? 'bg-amber-400' : 'bg-emerald-400'}" style="width: {Math.min(pct, 100)}%"></div>
                      </div>
                    </td>
                  </tr>
                {/each}
              </tbody>
              <tfoot>
                <tr class="border-t-2 border-neutral-200 bg-neutral-50">
                  <td class="px-5 py-2 font-bold text-neutral-800">Total</td>
                  <td class="px-4 py-2 text-right tabular-nums font-bold text-neutral-800">{workspaceItems.length}</td>
                  <td class="px-4 py-2 text-right tabular-nums font-bold text-emerald-700">{fmt(wsSubtotal)}</td>
                  <td class="px-4 py-2 text-right tabular-nums font-bold text-neutral-800">100%</td>
                  <td class="px-4 py-2"></td>
                </tr>
              </tfoot>
            </table>
          </div>
        {/if}

        <!-- Sectioned line items -->
        {#each sections as sec, secIdx (sec.name)}
          <div class="rounded-xl border bg-white overflow-hidden {sectionColor(sec.name)}">
            <!-- Section header -->
            <div class="flex items-center bg-neutral-50 hover:bg-neutral-100 transition-colors">
              <button
                onclick={() => toggleSection(sec.name)}
                class="flex-1 flex items-center justify-between px-5 py-3 text-left"
              >
                <div class="flex items-center gap-3">
                  <svg class="w-3.5 h-3.5 text-neutral-400 transition-transform {collapsedSections.has(sec.name) ? '' : 'rotate-90'}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" /></svg>
                  <span class="text-xs font-bold text-neutral-800 uppercase tracking-wider">{sec.name}</span>
                  <span class="rounded-full bg-neutral-200 px-2 py-0.5 text-[9px] font-semibold text-neutral-500 tabular-nums">{sec.itemCount}</span>
                </div>
                <div class="flex items-center gap-4">
                  <span class="text-[10px] text-neutral-400">{sec.approvedCount}/{sec.itemCount} approved</span>
                  {#key pulseKey}
                    <span class="text-sm font-bold text-emerald-700 tabular-nums pulse-total">{fmt(sec.subtotal)}</span>
                  {/key}
                </div>
              </button>
              <!-- Reorder controls -->
              <div class="flex flex-col pr-3 gap-0.5">
                <button
                  onclick={() => moveSectionUp(sec.name)}
                  disabled={secIdx === 0}
                  class="rounded p-0.5 text-neutral-300 hover:text-neutral-700 disabled:opacity-20 transition-colors"
                  aria-label="Move section up"
                >
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m4.5 15.75 7.5-7.5 7.5 7.5" /></svg>
                </button>
                <button
                  onclick={() => moveSectionDown(sec.name)}
                  disabled={secIdx === sections.length - 1}
                  class="rounded p-0.5 text-neutral-300 hover:text-neutral-700 disabled:opacity-20 transition-colors"
                  aria-label="Move section down"
                >
                  <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" /></svg>
                </button>
              </div>
            </div>

            <!-- Section items -->
            {#if !collapsedSections.has(sec.name)}
              <table class="w-full text-xs">
                <thead>
                  <tr class="border-b border-neutral-100 bg-neutral-50/50">
                    <th class="px-4 {compactMode ? 'py-1' : 'py-1.5'} text-left font-medium text-neutral-400 w-8">#</th>
                    <th class="px-4 {compactMode ? 'py-1' : 'py-1.5'} text-left font-medium text-neutral-400">Item</th>
                    <th class="px-3 {compactMode ? 'py-1' : 'py-1.5'} text-right font-medium text-neutral-400 w-20">Qty</th>
                    <th class="px-3 {compactMode ? 'py-1' : 'py-1.5'} text-left font-medium text-neutral-400 w-16">Unit</th>
                    <th class="px-3 {compactMode ? 'py-1' : 'py-1.5'} text-right font-medium text-neutral-400 w-28">Rate</th>
                    <th class="px-3 {compactMode ? 'py-1' : 'py-1.5'} text-right font-medium text-neutral-400 w-32">Amount</th>
                    <th class="px-3 {compactMode ? 'py-1' : 'py-1.5'} w-20"></th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-neutral-50">
                  {#each sec.items as item, idx (item._localId)}
                    {@const missingRate = Number(item.quantity) === 0 || Number(item.unit_cost) === 0}
                    {@const hasDrift = item.price_drift_pct !== null && Math.abs(item.price_drift_pct) > 2}
                    <tr
                      class="hover:bg-neutral-50/80 transition-colors cursor-pointer {missingRate ? 'bg-amber-50/40' : ''} {hasDrift ? 'border-l-2 border-l-amber-400' : ''}"
                      onclick={() => openItemDrawer(item)}
                    >
                      <td class="px-4 {compactMode ? 'py-1' : 'py-2'} text-neutral-400 tabular-nums">{idx + 1}</td>
                      <td class="{item.source_bom ? 'pl-8' : 'px-4'} pr-4 {compactMode ? 'py-1' : 'py-2'}">
                        <div class="flex items-center gap-1.5 {item.source_bom ? 'border-l-2 border-indigo-200 pl-2' : ''}">
                          {#if item.is_approved}<span class="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0"></span>{/if}
                          {#if item.price_volatile}<span class="text-amber-500 shrink-0" title="Volatile">&#9888;</span>{/if}
                          <span class="font-medium text-neutral-900 {compactMode ? '' : 'truncate max-w-[200px]'}">{item.material_name}</span>
                          {#if item.source_bom}<span class="text-[8px] text-indigo-400 ml-1" title="From BOM">BOM</span>{/if}
                          {#if item.quantity_formula}<span class="text-[8px] text-indigo-500 ml-1" title="Formula: {item.quantity_formula}">f(x)</span>{/if}
                          {#if item.is_fx_linked}<span class="text-[8px] text-sky-500 ml-1" title="FX-linked: ${item.unit_cost_usd} USD">FX</span>{/if}
                        </div>
                      </td>
                      <td class="px-3 {compactMode ? 'py-1' : 'py-2'} text-right tabular-nums text-neutral-700">
                        <input
                          type="number"
                          value={item.quantity}
                          onclick={(e) => e.stopPropagation()}
                          onchange={(e) => updateItemInline(item, "quantity", Number((e.target as HTMLInputElement).value))}
                          class="w-full text-right bg-transparent border-0 focus:bg-white focus:border focus:border-neutral-300 focus:rounded px-1 py-0.5 text-xs tabular-nums"
                        />
                      </td>
                      <td class="px-3 {compactMode ? 'py-1' : 'py-2'} text-neutral-500">{item.unit_of_measure}</td>
                      <td class="px-3 {compactMode ? 'py-1' : 'py-2'} text-right">
                        <input
                          type="number"
                          value={item.unit_cost}
                          onclick={(e) => e.stopPropagation()}
                          onchange={(e) => updateItemInline(item, "unit_cost", Number((e.target as HTMLInputElement).value))}
                          class="w-full text-right bg-transparent border-0 focus:bg-white focus:border focus:border-neutral-300 focus:rounded px-1 py-0.5 text-xs tabular-nums"
                        />
                      </td>
                      <td class="px-3 {compactMode ? 'py-1' : 'py-2'} text-right tabular-nums font-semibold text-neutral-900">{fmt(lineTotal(item))}</td>
                      <td class="px-3 {compactMode ? 'py-1' : 'py-2'}">
                        <div class="flex items-center gap-0.5 justify-end opacity-0 group-hover:opacity-100" style="opacity: 1">
                          <button onclick={(e) => { e.stopPropagation(); deleteItem(item._localId); }} class="rounded p-1 text-neutral-300 hover:text-red-500 transition-colors" title="Remove" aria-label="Remove item">
                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
                          </button>
                        </div>
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            {/if}
          </div>
        {/each}

        {#if workspaceItems.length === 0}
          <div class="rounded-xl border border-dashed border-neutral-300 bg-white p-12 text-center">
            <p class="text-sm text-neutral-500">Empty BoQ. Use the sidebar to add items from Catalog, BOMs, or Quick Add.</p>
          </div>
        {/if}

      {/if}
    </div>
  </div>
</div>

<!-- ═══════ EXPAND BOM MODAL ═══════ -->
{#if showExpandModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" style="backdrop-filter: blur(4px)">
    <div class="w-full max-w-sm rounded-2xl border border-neutral-200 bg-white p-6 shadow-2xl">
      <h2 class="text-base font-semibold text-neutral-900 mb-4">Expand BOM into BoQ</h2>
      <div class="space-y-4">
        <label class="block text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block text-xs">Multiplier (quantity of units)</span>
          <input type="number" min="1" bind:value={expandMultiplier} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" />
        </label>
        <label class="block text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block text-xs">Section name</span>
          <input bind:value={expandSection} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="e.g. Solar Modules" />
        </label>
      </div>
      <div class="mt-6 flex justify-end gap-3">
        <button onclick={() => { showExpandModal = false; }} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
        <button onclick={expandBomIntoWorkspace} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800">Expand</button>
      </div>
    </div>
  </div>
{/if}

<!-- ═══════ ITEM DETAIL DRAWER ═══════ -->
{#if showItemDrawer && editingItem}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm transition-opacity duration-300" style="opacity: {itemDrawerVisible ? 1 : 0}" onclick={closeItemDrawer}></div>
  <aside class="fixed inset-y-0 right-0 z-50 flex w-full max-w-md flex-col bg-white shadow-2xl border-l border-neutral-200/60 transition-transform duration-300" style="transform: translateX({itemDrawerVisible ? '0%' : '100%'})">
    <!-- Dark header -->
    <div class="bg-linear-to-br from-neutral-900 to-neutral-800 px-6 py-5">
      <div class="flex items-start justify-between">
        <div>
          <h2 class="text-base font-semibold text-white">{editingItem.material_name}</h2>
          <p class="mt-0.5 text-sm text-neutral-400 capitalize">{editingItem.category || "No category"} &middot; {editingItem.section || "No section"}</p>
        </div>
        <button onclick={closeItemDrawer} class="rounded-md p-1.5 text-neutral-400 hover:text-white" aria-label="Close">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
        </button>
      </div>
    </div>

    <!-- Key figures -->
    <div class="grid grid-cols-3 divide-x divide-neutral-100 border-b border-neutral-100">
      <div class="px-4 py-3 text-center">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Line Total</p>
        <p class="mt-0.5 text-base font-bold tabular-nums text-emerald-700">{fmt(Number(editingItem.line_total))}</p>
      </div>
      <div class="px-4 py-3 text-center">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Lead Time</p>
        <p class="mt-0.5 text-base font-bold tabular-nums text-blue-700">{editingItem.lead_time_days}d</p>
      </div>
      <div class="px-4 py-3 text-center">
        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Waste</p>
        <p class="mt-0.5 text-base font-bold tabular-nums text-amber-700">{Number(editingItem.waste_factor_pct).toFixed(1)}%</p>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto px-6 py-5 space-y-5">
      <!-- Quantity & Rate -->
      <div class="grid grid-cols-2 gap-3">
        <label class="text-xs font-medium text-neutral-700"><span class="mb-1 block text-[11px] text-neutral-500">Quantity</span><input type="number" bind:value={itemForm.quantity} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" /></label>
        <label class="text-xs font-medium text-neutral-700"><span class="mb-1 block text-[11px] text-neutral-500">Unit Cost</span><input type="number" bind:value={itemForm.unit_cost} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" /></label>
      </div>

      <!-- Dynamic Quantity Formula -->
      <label class="block text-xs font-medium text-neutral-700">
        <span class="mb-1 block text-[11px] text-neutral-500">Quantity Formula <span class="text-neutral-400">(optional — links to project variables)</span></span>
        <input bind:value={itemForm.quantity_formula} class="w-full rounded-lg border border-indigo-200 bg-indigo-50/30 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500" placeholder="e.g. panel_count * 0.8" />
        {#if itemForm.quantity_formula.trim()}
          {@const preview = evaluateFormula(itemForm.quantity_formula, projectVars)}
          <p class="mt-1 text-[10px] tabular-nums {preview !== null ? 'text-emerald-600' : 'text-red-500'}">
            {preview !== null ? `Computed: ${preview}` : "Invalid formula — check variable names"}
          </p>
        {/if}
      </label>

      <!-- Price source -->
      <label class="block text-xs font-medium text-neutral-700"><span class="mb-1 block text-[11px] text-neutral-500">Price Source</span>
        <select bind:value={itemForm.price_source} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
          <option value="warehouse">Warehouse Price</option>
          <option value="manual">Manual Override</option>
          <option value="quote">Supplier Quote</option>
        </select>
      </label>

      <!-- FX Linking -->
      <div class="rounded-lg border border-indigo-200 bg-indigo-50/30 p-3 space-y-2">
        <label class="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" bind:checked={itemForm.is_fx_linked} class="rounded border-indigo-300 text-indigo-600" />
          <span class="text-xs font-medium text-indigo-700">FX-Linked Item</span>
          <span class="text-[10px] text-indigo-400">(price derived from USD rate)</span>
        </label>
        {#if itemForm.is_fx_linked}
          <div class="flex items-center gap-2">
            <label class="flex-1 text-xs font-medium text-neutral-700">
              <span class="mb-1 block text-[11px] text-neutral-500">USD Price</span>
              <input type="number" bind:value={itemForm.unit_cost_usd} step="0.01" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-indigo-500" />
            </label>
            <div class="pt-5 text-xs text-neutral-400">
              &times; {fxRate} = <span class="font-bold text-neutral-900 tabular-nums">{fmt(Number(itemForm.unit_cost_usd || 0) * fxRate)}</span>
            </div>
          </div>
        {/if}
      </div>

      <!-- Waste & Markup -->
      <div class="grid grid-cols-2 gap-3">
        <label class="text-xs font-medium text-neutral-700">
          <span class="mb-1 block text-[11px] text-neutral-500">Waste Factor %</span>
          <div class="flex items-center gap-2">
            <input type="range" min="0" max="20" step="0.5" bind:value={itemForm.waste_factor_pct} class="flex-1 accent-amber-500" />
            <span class="text-xs font-bold tabular-nums w-10 text-right">{itemForm.waste_factor_pct}%</span>
          </div>
        </label>
        <label class="text-xs font-medium text-neutral-700">
          <span class="mb-1 block text-[11px] text-neutral-500">Item Markup %</span>
          <div class="flex items-center gap-2">
            <input type="range" min="0" max="50" step="0.5" bind:value={itemForm.item_markup_pct} class="flex-1 accent-emerald-500" />
            <span class="text-xs font-bold tabular-nums w-10 text-right">{itemForm.item_markup_pct}%</span>
          </div>
        </label>
      </div>

      <!-- Lead time & Supplier -->
      <div class="grid grid-cols-2 gap-3">
        <label class="text-xs font-medium text-neutral-700"><span class="mb-1 block text-[11px] text-neutral-500">Lead Time (days)</span><input type="number" bind:value={itemForm.lead_time_days} min="0" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" /></label>
        <label class="text-xs font-medium text-neutral-700"><span class="mb-1 block text-[11px] text-neutral-500">Supplier (text)</span><input bind:value={itemForm.supplier} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="Manual entry" /></label>
      </div>

      <!-- Linked Vendor -->
      <label class="block text-xs font-medium text-neutral-700">
        <span class="mb-1 block text-[11px] text-neutral-500">Preferred Vendor <span class="text-neutral-400">(from procurement database)</span></span>
        <select bind:value={itemForm.supplier_vendor} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
          <option value="">No vendor linked</option>
          {#each vendors as v}
            <option value={String(v.id)}>{v.name} — {v.category}</option>
          {/each}
        </select>
      </label>

      <!-- Section & Category -->
      <div class="grid grid-cols-2 gap-3">
        <label class="text-xs font-medium text-neutral-700"><span class="mb-1 block text-[11px] text-neutral-500">Section</span><input bind:value={itemForm.section} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" /></label>
        <label class="text-xs font-medium text-neutral-700"><span class="mb-1 block text-[11px] text-neutral-500">Category</span><input bind:value={itemForm.category} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" /></label>
      </div>

      <!-- Flags -->
      <div class="flex gap-4">
        <label class="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" bind:checked={itemForm.is_approved} class="rounded border-neutral-300 text-emerald-600" />
          <span class="text-xs font-medium text-neutral-700">Approved</span>
        </label>
        <label class="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" bind:checked={itemForm.price_volatile} class="rounded border-neutral-300 text-amber-600" />
          <span class="text-xs font-medium text-neutral-700">Price Volatile</span>
        </label>
      </div>

      <!-- Notes -->
      <label class="block text-xs font-medium text-neutral-700"><span class="mb-1 block text-[11px] text-neutral-500">Notes</span><textarea bind:value={itemForm.notes} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none" placeholder="Procurement notes, special instructions..."></textarea></label>
    </div>

    <!-- Footer -->
    <div class="flex items-center justify-end gap-3 border-t border-neutral-100 px-6 py-4">
      <button onclick={() => { if (editingItem) deleteItem(editingItem._localId); closeItemDrawer(); }} class="mr-auto rounded-lg border border-red-200 px-3 py-2 text-xs font-medium text-red-600 hover:bg-red-50">Delete</button>
      <button onclick={closeItemDrawer} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
      <button onclick={saveItemDetail} class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-neutral-800">Save</button>
    </div>
  </aside>
{/if}

<!-- Save as Draft Modal -->
{#if showSaveModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4" style="backdrop-filter: blur(4px)">
    <div class="w-full max-w-lg rounded-2xl border border-neutral-200 bg-white p-6 shadow-2xl">
      <div class="flex items-start justify-between mb-5">
        <div>
          <h2 class="text-lg font-semibold text-neutral-900">Save as BoQ Draft</h2>
          <p class="mt-1 text-sm text-neutral-500">{workspaceItems.length} items &middot; Subtotal {fmt(wsSubtotal)}</p>
        </div>
        <button onclick={() => { showSaveModal = false; }} class="rounded-md border border-neutral-200 bg-white px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50">Close</button>
      </div>
      <div class="space-y-4">
        <label class="block text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Draft Name *</span><input bind:value={draftName} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" /></label>
        <label class="block text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Description</span><textarea bind:value={draftDescription} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea></label>
        <div class="grid grid-cols-2 gap-3">
          <label class="text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Project</span>
            <select bind:value={draftProject} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
              <option value="">No project</option>
              {#each projects as p}<option value={String(p.id)}>{p.name}</option>{/each}
            </select>
          </label>
          <label class="text-sm font-medium text-neutral-700"><span class="mb-1.5 block text-xs">Site Location</span><input bind:value={draftSiteLocation} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="Lekki Phase 1, Lagos" /></label>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block text-xs">Margin %</span>
            <input type="number" bind:value={draftMarginPct} step="0.5" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </label>
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block text-xs">VAT %</span>
            <input type="number" bind:value={draftVatPct} step="0.5" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" />
          </label>
        </div>
        <!-- Summary -->
        <div class="rounded-lg bg-emerald-50 border border-emerald-200 p-4">
          <div class="flex justify-between text-xs text-neutral-600"><span>Subtotal</span><span class="tabular-nums">{fmt(wsSubtotal)}</span></div>
          <div class="flex justify-between text-xs text-neutral-600 mt-1"><span>VAT ({draftVatPct}%)</span><span class="tabular-nums">{fmt(wsVat)}</span></div>
          <div class="flex justify-between text-xs text-neutral-600 mt-1"><span>Margin ({draftMarginPct}%)</span><span class="tabular-nums">{fmt(wsMargin)}</span></div>
          <div class="flex justify-between text-sm font-bold text-emerald-700 mt-2 pt-2 border-t border-emerald-200"><span>Grand Total</span><span class="tabular-nums">{fmt(wsGrandTotal)}</span></div>
        </div>
      </div>
      <div class="mt-6 flex items-center justify-end gap-3">
        <button onclick={() => { showSaveModal = false; }} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
        <button onclick={saveAsDraft} disabled={saving} class="rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50">{saving ? "Saving..." : "Save as Draft"}</button>
      </div>
    </div>
  </div>
{/if}

<style>
  @keyframes pulse-green {
    0% { color: inherit; }
    20% { color: #059669; text-shadow: 0 0 8px rgba(16, 185, 129, 0.4); }
    100% { color: inherit; text-shadow: none; }
  }
  :global(.pulse-total) {
    animation: pulse-green 1.2s ease-out;
  }
</style>

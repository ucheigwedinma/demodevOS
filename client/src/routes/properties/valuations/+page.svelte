<script lang="ts">
  import { currency } from "$lib/stores/currency.svelte";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    ValuationListItem, ValuationDetail,
    ComparableSaleListItem, ComparableSaleDetail,
    ValuationAppealListItem, ValuationAppealDetail,
    PropertyListItem, PaginatedResponse,
    ValuationType, ComparableSaleSource,
    ValuationAppealType, ValuationAppealStatus, ValuationAppealOutcome,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  type Tab = "records" | "comparables" | "appeals";
  let activeTab = $state<Tab>("records");
  const tabs: { key: Tab; label: string }[] = [
    { key: "records", label: "Valuations" },
    { key: "comparables", label: "Comparable Sales" },
    { key: "appeals", label: "Appeals" },
  ];

  // --- Shared lookups ---
  let properties = $state<PropertyListItem[]>([]);
  $effect(() => {
    api.get<PaginatedResponse<PropertyListItem>>("/properties/", { page_size: "200" })
      .then((r) => { properties = r.results; }).catch(() => {});
  });

  // --- Shared helpers ---
  const PAGE_SIZE = 25;

  function getVisiblePages(current: number, total: number): number[] {
    if (total <= 0) return [];
    const pages: number[] = [];
    const maxVisible = 7;
    let start = Math.max(1, current - Math.floor(maxVisible / 2));
    let end = Math.min(total, start + maxVisible - 1);
    if (end - start + 1 < maxVisible) start = Math.max(1, end - maxVisible + 1);
    for (let i = start; i <= end; i++) pages.push(i);
    return pages;
  }

  function formatCurrency(v: string | null): string { return v ? currency.formatCompact(v) : "\u2014"; }
  function formatDate(v: string | null): string {
    if (!v) return "\u2014";
    return new Date(v + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }
  function formatDateTime(v: string | null): string {
    if (!v) return "\u2014";
    return new Date(v).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" });
  }
  function formatNum(v: string | null): string { return v ? Number(v).toLocaleString() : "\u2014"; }

  const valTypeLabels: Record<string, string> = {
    appraisal: "Professional Appraisal", internal: "Internal Estimate",
    market: "Market Comparable", tax: "Tax Assessment",
  };
  const valTypeColors: Record<string, string> = {
    appraisal: "bg-blue-50 text-blue-700", internal: "bg-neutral-100 text-neutral-600",
    market: "bg-emerald-50 text-emerald-700", tax: "bg-amber-50 text-amber-700",
  };
  const sourceLabels: Record<string, string> = {
    mls: "MLS Listing", public_records: "Public Records",
    broker: "Broker Report", auction: "Auction", other: "Other",
  };
  const propTypeLabels: Record<string, string> = {
    land: "Land", building: "Building", mixed: "Mixed-Use",
    estate: "Estate", warehouse: "Warehouse", industrial: "Industrial",
  };
  const appealTypeLabels: Record<string, string> = {
    tax_assessment: "Tax Assessment", insurance: "Insurance", dispute: "Dispute",
  };
  const appealStatusLabels: Record<string, string> = {
    filed: "Filed", under_review: "Under Review",
    hearing_scheduled: "Hearing Scheduled", decided: "Decided", withdrawn: "Withdrawn",
  };
  const appealStatusColors: Record<string, string> = {
    filed: "bg-blue-50 text-blue-700", under_review: "bg-violet-50 text-violet-700",
    hearing_scheduled: "bg-amber-50 text-amber-700", decided: "bg-emerald-50 text-emerald-700",
    withdrawn: "bg-neutral-100 text-neutral-500",
  };
  const outcomeLabels: Record<string, string> = {
    pending: "Pending", upheld: "Upheld", reduced: "Reduced",
    increased: "Increased", dismissed: "Dismissed",
  };
  const outcomeColors: Record<string, string> = {
    pending: "bg-neutral-100 text-neutral-600", upheld: "bg-red-50 text-red-700",
    reduced: "bg-emerald-50 text-emerald-700", increased: "bg-amber-50 text-amber-700",
    dismissed: "bg-neutral-100 text-neutral-500",
  };

  let searchTimeout: ReturnType<typeof setTimeout>;
  function debounceSearch(setter: (v: string) => void) {
    return (e: Event) => {
      clearTimeout(searchTimeout);
      const val = (e.target as HTMLInputElement).value;
      searchTimeout = setTimeout(() => setter(val), 300);
    };
  }

  function fieldErr(errors: Record<string, string[]>, key: string): string {
    return errors[key]?.join(", ") ?? "";
  }

  const inputCls = "w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent";
  const selectCls = inputCls;

  // =========================================================================
  //  1. VALUATION RECORDS
  // =========================================================================
  let recData = $state<ValuationListItem[]>([]);
  let recCount = $state(0); let recPage = $state(1); let recLoading = $state(false);
  let recSearch = $state(""); let recProperty = $state(""); let recType = $state("");
  const recPages = $derived(Math.ceil(recCount / PAGE_SIZE));

  let showRecModal = $state(false); let recEditingId = $state<number | null>(null);
  let recSaving = $state(false); let recErrors = $state<Record<string, string[]>>({});
  let recForm = $state({ property: 0, valuation_date: "", value: "", valuation_type: "internal" as ValuationType, appraiser: "", notes: "" });

  let recExpandedId = $state<number | null>(null);
  let recDetail = $state<ValuationDetail | null>(null);
  let recViewing = $state<ValuationDetail | null>(null);
  let recDeleteId = $state<number | null>(null); let recDeleting = $state(false);

  async function fetchRecs() {
    recLoading = true;
    try {
      const p: Record<string, string> = { page: String(recPage) };
      if (recSearch) p.search = recSearch;
      if (recProperty) p.property = recProperty;
      if (recType) p.valuation_type = recType;
      const res = await api.get<PaginatedResponse<ValuationListItem>>("/valuations/records/", p);
      recData = res.results; recCount = res.count;
    } catch { recData = []; recCount = 0; }
    recLoading = false;
  }
  $effect(() => {
    if (activeTab !== "records") return;
    void recSearch; void recProperty; void recType; void recPage;
    fetchRecs();
  });

  async function toggleRecExpand(id: number) {
    if (recExpandedId === id) { recExpandedId = null; recDetail = null; return; }
    try {
      recDetail = await api.get<ValuationDetail>(`/valuations/records/${id}/`);
      recExpandedId = id;
    } catch { toast.error("Error", "Could not load details."); }
  }

  async function viewRec(id: number) {
    try { recViewing = await api.get<ValuationDetail>(`/valuations/records/${id}/`); }
    catch { toast.error("Error", "Could not load details."); }
  }

  function openCreateRec() {
    recEditingId = null;
    recForm = { property: 0, valuation_date: "", value: "", valuation_type: "internal", appraiser: "", notes: "" };
    recErrors = {}; showRecModal = true;
  }

  async function openEditRec(id: number) {
    try {
      const d = await api.get<ValuationDetail>(`/valuations/records/${id}/`);
      recEditingId = id;
      recForm = { property: d.property, valuation_date: d.valuation_date, value: d.value, valuation_type: d.valuation_type, appraiser: d.appraiser, notes: d.notes };
      recErrors = {}; showRecModal = true;
    } catch { toast.error("Error", "Could not load valuation."); }
  }

  function editFromViewRec() {
    if (!recViewing) return;
    const d = recViewing; recViewing = null;
    recEditingId = d.id;
    recForm = { property: d.property, valuation_date: d.valuation_date, value: d.value, valuation_type: d.valuation_type, appraiser: d.appraiser, notes: d.notes };
    recErrors = {}; showRecModal = true;
  }

  async function saveRec() {
    recSaving = true; recErrors = {};
    try {
      if (recEditingId) {
        await api.patch(`/valuations/records/${recEditingId}/`, recForm);
        toast.success("Updated", "Valuation updated");
      } else {
        await api.post("/valuations/records/", recForm);
        toast.success("Created", "Valuation recorded");
      }
      showRecModal = false; recExpandedId = null; recDetail = null; fetchRecs();
    } catch (e) {
      if (e instanceof ApiError) { recErrors = e.fieldErrors; toast.error("Validation error", "Fix highlighted fields"); }
      else toast.error("Error", `Could not ${recEditingId ? "update" : "create"} valuation`);
    }
    recSaving = false;
  }

  async function deleteRec() {
    if (!recDeleteId) return;
    recDeleting = true;
    try {
      await api.delete(`/valuations/records/${recDeleteId}/`);
      toast.success("Deleted", "Valuation removed");
      recDeleteId = null; recExpandedId = null; recDetail = null; fetchRecs();
    } catch { toast.error("Error", "Could not delete valuation"); }
    recDeleting = false;
  }

  // =========================================================================
  //  2. COMPARABLE SALES
  // =========================================================================
  let compData = $state<ComparableSaleListItem[]>([]);
  let compCount = $state(0); let compPage = $state(1); let compLoading = $state(false);
  let compSearch = $state(""); let compType = $state(""); let compSource = $state("");
  const compPages = $derived(Math.ceil(compCount / PAGE_SIZE));

  let showCompModal = $state(false); let compEditingId = $state<number | null>(null);
  let compSaving = $state(false); let compErrors = $state<Record<string, string[]>>({});
  let compForm = $state({ property: null as number | null, address: "", sale_date: "", sale_price: "", property_type: "", area_sqft: "", price_per_sqft: "", proximity_km: "", source: "public_records" as ComparableSaleSource, notes: "" });

  let compExpandedId = $state<number | null>(null);
  let compDetail = $state<ComparableSaleDetail | null>(null);
  let compViewing = $state<ComparableSaleDetail | null>(null);
  let compDeleteId = $state<number | null>(null); let compDeleting = $state(false);

  async function fetchComps() {
    compLoading = true;
    try {
      const p: Record<string, string> = { page: String(compPage) };
      if (compSearch) p.search = compSearch;
      if (compType) p.property_type = compType;
      if (compSource) p.source = compSource;
      const res = await api.get<PaginatedResponse<ComparableSaleListItem>>("/valuations/comparables/", p);
      compData = res.results; compCount = res.count;
    } catch { compData = []; compCount = 0; }
    compLoading = false;
  }
  $effect(() => {
    if (activeTab !== "comparables") return;
    void compSearch; void compType; void compSource; void compPage;
    fetchComps();
  });

  async function toggleCompExpand(id: number) {
    if (compExpandedId === id) { compExpandedId = null; compDetail = null; return; }
    try {
      compDetail = await api.get<ComparableSaleDetail>(`/valuations/comparables/${id}/`);
      compExpandedId = id;
    } catch { toast.error("Error", "Could not load details."); }
  }

  async function viewComp(id: number) {
    try { compViewing = await api.get<ComparableSaleDetail>(`/valuations/comparables/${id}/`); }
    catch { toast.error("Error", "Could not load details."); }
  }

  function openCreateComp() {
    compEditingId = null;
    compForm = { property: null, address: "", sale_date: "", sale_price: "", property_type: "", area_sqft: "", price_per_sqft: "", proximity_km: "", source: "public_records", notes: "" };
    compErrors = {}; showCompModal = true;
  }

  async function openEditComp(id: number) {
    try {
      const d = await api.get<ComparableSaleDetail>(`/valuations/comparables/${id}/`);
      compEditingId = id;
      compForm = { property: d.property, address: d.address, sale_date: d.sale_date, sale_price: d.sale_price, property_type: d.property_type, area_sqft: d.area_sqft ?? "", price_per_sqft: d.price_per_sqft ?? "", proximity_km: d.proximity_km ?? "", source: d.source, notes: d.notes };
      compErrors = {}; showCompModal = true;
    } catch { toast.error("Error", "Could not load comparable."); }
  }

  function editFromViewComp() {
    if (!compViewing) return;
    const d = compViewing; compViewing = null;
    compEditingId = d.id;
    compForm = { property: d.property, address: d.address, sale_date: d.sale_date, sale_price: d.sale_price, property_type: d.property_type, area_sqft: d.area_sqft ?? "", price_per_sqft: d.price_per_sqft ?? "", proximity_km: d.proximity_km ?? "", source: d.source, notes: d.notes };
    compErrors = {}; showCompModal = true;
  }

  async function saveComp() {
    compSaving = true; compErrors = {};
    try {
      const payload: Record<string, unknown> = { ...compForm };
      if (!compForm.property) payload.property = null;
      if (!compForm.area_sqft) payload.area_sqft = null;
      if (!compForm.price_per_sqft) payload.price_per_sqft = null;
      if (!compForm.proximity_km) payload.proximity_km = null;
      if (compEditingId) {
        await api.patch(`/valuations/comparables/${compEditingId}/`, payload);
        toast.success("Updated", "Comparable sale updated");
      } else {
        await api.post("/valuations/comparables/", payload);
        toast.success("Created", "Comparable sale added");
      }
      showCompModal = false; compExpandedId = null; compDetail = null; fetchComps();
    } catch (e) {
      if (e instanceof ApiError) { compErrors = e.fieldErrors; toast.error("Validation error", "Fix highlighted fields"); }
      else toast.error("Error", `Could not ${compEditingId ? "update" : "create"} comparable`);
    }
    compSaving = false;
  }

  async function deleteComp() {
    if (!compDeleteId) return;
    compDeleting = true;
    try {
      await api.delete(`/valuations/comparables/${compDeleteId}/`);
      toast.success("Deleted", "Comparable sale removed");
      compDeleteId = null; compExpandedId = null; compDetail = null; fetchComps();
    } catch { toast.error("Error", "Could not delete comparable"); }
    compDeleting = false;
  }

  // =========================================================================
  //  3. APPEALS
  // =========================================================================
  let appData = $state<ValuationAppealListItem[]>([]);
  let appCount = $state(0); let appPage = $state(1); let appLoading = $state(false);
  let appSearch = $state(""); let appProperty = $state(""); let appType = $state(""); let appStatus = $state("");
  const appPages = $derived(Math.ceil(appCount / PAGE_SIZE));

  let showAppModal = $state(false); let appEditingId = $state<number | null>(null);
  let appSaving = $state(false); let appErrors = $state<Record<string, string[]>>({});
  let appForm = $state({ property: 0, valuation: null as number | null, appeal_type: "tax_assessment" as ValuationAppealType, status: "filed" as ValuationAppealStatus, filed_date: new Date().toISOString().slice(0, 10), hearing_date: "", decision_date: "", assessed_value: "", requested_value: "", decided_value: "", filing_reference: "", representative: "", outcome: "pending" as ValuationAppealOutcome, notes: "" });

  let appExpandedId = $state<number | null>(null);
  let appDetail = $state<ValuationAppealDetail | null>(null);
  let appViewing = $state<ValuationAppealDetail | null>(null);
  let appDeleteId = $state<number | null>(null); let appDeleting = $state(false);

  async function fetchAppeals() {
    appLoading = true;
    try {
      const p: Record<string, string> = { page: String(appPage) };
      if (appSearch) p.search = appSearch;
      if (appProperty) p.property = appProperty;
      if (appType) p.appeal_type = appType;
      if (appStatus) p.status = appStatus;
      const res = await api.get<PaginatedResponse<ValuationAppealListItem>>("/valuations/appeals/", p);
      appData = res.results; appCount = res.count;
    } catch { appData = []; appCount = 0; }
    appLoading = false;
  }
  $effect(() => {
    if (activeTab !== "appeals") return;
    void appSearch; void appProperty; void appType; void appStatus; void appPage;
    fetchAppeals();
  });

  async function toggleAppExpand(id: number) {
    if (appExpandedId === id) { appExpandedId = null; appDetail = null; return; }
    try {
      appDetail = await api.get<ValuationAppealDetail>(`/valuations/appeals/${id}/`);
      appExpandedId = id;
    } catch { toast.error("Error", "Could not load details."); }
  }

  async function viewApp(id: number) {
    try { appViewing = await api.get<ValuationAppealDetail>(`/valuations/appeals/${id}/`); }
    catch { toast.error("Error", "Could not load details."); }
  }

  function openCreateApp() {
    appEditingId = null;
    appForm = { property: 0, valuation: null, appeal_type: "tax_assessment", status: "filed", filed_date: new Date().toISOString().slice(0, 10), hearing_date: "", decision_date: "", assessed_value: "", requested_value: "", decided_value: "", filing_reference: "", representative: "", outcome: "pending", notes: "" };
    appErrors = {}; showAppModal = true;
  }

  async function openEditApp(id: number) {
    try {
      const d = await api.get<ValuationAppealDetail>(`/valuations/appeals/${id}/`);
      appEditingId = id;
      appForm = { property: d.property, valuation: d.valuation, appeal_type: d.appeal_type, status: d.status, filed_date: d.filed_date, hearing_date: d.hearing_date ?? "", decision_date: d.decision_date ?? "", assessed_value: d.assessed_value, requested_value: d.requested_value, decided_value: d.decided_value ?? "", filing_reference: d.filing_reference, representative: d.representative, outcome: d.outcome, notes: d.notes };
      appErrors = {}; showAppModal = true;
    } catch { toast.error("Error", "Could not load appeal."); }
  }

  function editFromViewApp() {
    if (!appViewing) return;
    const d = appViewing; appViewing = null;
    appEditingId = d.id;
    appForm = { property: d.property, valuation: d.valuation, appeal_type: d.appeal_type, status: d.status, filed_date: d.filed_date, hearing_date: d.hearing_date ?? "", decision_date: d.decision_date ?? "", assessed_value: d.assessed_value, requested_value: d.requested_value, decided_value: d.decided_value ?? "", filing_reference: d.filing_reference, representative: d.representative, outcome: d.outcome, notes: d.notes };
    appErrors = {}; showAppModal = true;
  }

  async function saveApp() {
    appSaving = true; appErrors = {};
    try {
      const payload: Record<string, unknown> = { ...appForm };
      if (!appForm.hearing_date) payload.hearing_date = null;
      if (!appForm.decision_date) payload.decision_date = null;
      if (!appForm.decided_value) payload.decided_value = null;
      if (!appForm.valuation) payload.valuation = null;
      if (appEditingId) {
        await api.patch(`/valuations/appeals/${appEditingId}/`, payload);
        toast.success("Updated", "Appeal updated");
      } else {
        await api.post("/valuations/appeals/", payload);
        toast.success("Created", "Appeal filed");
      }
      showAppModal = false; appExpandedId = null; appDetail = null; fetchAppeals();
    } catch (e) {
      if (e instanceof ApiError) { appErrors = e.fieldErrors; toast.error("Validation error", "Fix highlighted fields"); }
      else toast.error("Error", `Could not ${appEditingId ? "update" : "create"} appeal`);
    }
    appSaving = false;
  }

  async function deleteApp() {
    if (!appDeleteId) return;
    appDeleting = true;
    try {
      await api.delete(`/valuations/appeals/${appDeleteId}/`);
      toast.success("Deleted", "Appeal removed");
      appDeleteId = null; appExpandedId = null; appDetail = null; fetchAppeals();
    } catch { toast.error("Error", "Could not delete appeal"); }
    appDeleting = false;
  }
</script>

{#snippet searchIcon()}
  <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
{/snippet}

{#snippet chevron(expanded: boolean)}
  <svg class="w-3.5 h-3.5 text-neutral-400 transition-transform shrink-0 {expanded ? 'rotate-90' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" /></svg>
{/snippet}

{#snippet pagination(page: number, pages: number, setPage: (p: number) => void)}
  {#if pages > 1}
    <div class="flex items-center justify-between border-t border-neutral-200 px-5 py-3.5">
      <p class="text-sm text-neutral-500">Page {page} of {pages}</p>
      <div class="flex items-center gap-1">
        <button onclick={() => setPage(Math.max(1, page - 1))} disabled={page === 1} class="rounded-lg border border-neutral-200 px-2.5 py-1.5 text-sm text-neutral-600 hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed">Prev</button>
        {#each getVisiblePages(page, pages) as pg}
          <button onclick={() => setPage(pg)} class="min-w-8 rounded-lg px-2.5 py-1.5 text-sm font-medium transition-colors {pg === page ? 'bg-neutral-900 text-white' : 'text-neutral-600 hover:bg-neutral-50'}">{pg}</button>
        {/each}
        <button onclick={() => setPage(Math.min(pages, page + 1))} disabled={page === pages} class="rounded-lg border border-neutral-200 px-2.5 py-1.5 text-sm text-neutral-600 hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed">Next</button>
      </div>
    </div>
  {/if}
{/snippet}

{#snippet detailField(label: string, value: string, wide?: boolean)}
  <div class={wide ? "col-span-full" : ""}>
    <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider mb-1">{label}</p>
    <p class="text-sm text-neutral-700 whitespace-pre-wrap">{value || "\u2014"}</p>
  </div>
{/snippet}

{#snippet actionBtns(onView: () => void, onEdit: () => void, onDelete: () => void)}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <td class="px-5 py-4 text-right" onclick={(e: MouseEvent) => e.stopPropagation()}>
    <div class="flex items-center justify-end gap-1">
      <button onclick={onView} class="rounded-lg px-2.5 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 transition-colors">View</button>
      <button onclick={onEdit} class="rounded-lg px-2.5 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 transition-colors">Edit</button>
      <button onclick={onDelete} class="rounded-lg px-2.5 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 transition-colors">Delete</button>
    </div>
  </td>
{/snippet}

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Valuations</h1>
    <p class="text-sm text-neutral-400 mt-1">Manage property valuations, comparable sales, and valuation appeals</p>
  </div>

  <div class="border-b border-neutral-200">
    <nav class="flex gap-6" aria-label="Tabs">
      {#each tabs as tab}
        <button onclick={() => { activeTab = tab.key; }} class="pb-3 text-sm font-medium border-b-2 transition-colors -mb-px {activeTab === tab.key ? 'border-neutral-900 text-neutral-900' : 'border-transparent text-neutral-400 hover:text-neutral-600 hover:border-neutral-300'}">
          {tab.label}
        </button>
      {/each}
    </nav>
  </div>

  <!-- ================================================================ -->
  <!--  1. VALUATION RECORDS TAB                                        -->
  <!-- ================================================================ -->
  {#if activeTab === "records"}
    <div class="flex items-center justify-between">
      <p class="text-sm text-neutral-400">{recCount} valuation{recCount !== 1 ? "s" : ""}</p>
      <button onclick={openCreateRec} class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg hover:bg-neutral-800 text-sm font-medium transition-colors">+ New Valuation</button>
    </div>

    <div class="flex gap-3 items-center">
      <div class="relative flex-1 max-w-sm">
        {@render searchIcon()}
        <input type="text" placeholder="Search valuations..." oninput={debounceSearch(v => { recSearch = v; recPage = 1; })} class="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent placeholder:text-neutral-400" />
      </div>
      <select bind:value={recProperty} onchange={() => (recPage = 1)} class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent">
        <option value="">All Properties</option>
        {#each properties as p}<option value={String(p.id)}>{p.name}</option>{/each}
      </select>
      <select bind:value={recType} onchange={() => (recPage = 1)} class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent">
        <option value="">All Types</option>
        {#each Object.entries(valTypeLabels) as [k, v]}<option value={k}>{v}</option>{/each}
      </select>
    </div>

    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      {#if recLoading}
        <div class="p-16 text-center"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div><p class="mt-3 text-sm text-neutral-400">Loading...</p></div>
      {:else if recData.length === 0}
        <div class="p-16 text-center"><p class="text-sm font-medium text-neutral-900">No valuations found</p><p class="mt-1 text-sm text-neutral-400">Record your first property valuation to get started.</p></div>
      {:else}
        <table class="w-full text-sm">
          <thead><tr class="border-b border-neutral-200">
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Property</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Date</th>
            <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Value</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Type</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Appraiser</th>
            <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Actions</th>
          </tr></thead>
          <tbody class="divide-y divide-neutral-100">
            {#each recData as item}
              <tr onclick={() => toggleRecExpand(item.id)} class="hover:bg-neutral-50 cursor-pointer transition-colors">
                <td class="px-5 py-4"><div class="flex items-center gap-2">{@render chevron(recExpandedId === item.id)}<span class="font-medium text-neutral-900">{item.property_name}</span></div></td>
                <td class="px-5 py-4 text-neutral-500">{formatDate(item.valuation_date)}</td>
                <td class="px-5 py-4 text-right font-medium text-neutral-900 tabular-nums">{formatCurrency(item.value)}</td>
                <td class="px-5 py-4"><span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {valTypeColors[item.valuation_type] ?? 'bg-neutral-100 text-neutral-600'}">{valTypeLabels[item.valuation_type] ?? item.valuation_type}</span></td>
                <td class="px-5 py-4 text-neutral-500">{item.appraiser || "\u2014"}</td>
                {@render actionBtns(() => viewRec(item.id), () => openEditRec(item.id), () => (recDeleteId = item.id))}
              </tr>
              {#if recExpandedId === item.id && recDetail}
                <tr class="bg-neutral-50">
                  <td colspan="6" class="px-8 py-5">
                    <div class="grid grid-cols-3 gap-x-8 gap-y-4">
                      {@render detailField("Notes", recDetail.notes, true)}
                      {@render detailField("Created", formatDateTime(recDetail.created_at))}
                    </div>
                  </td>
                </tr>
              {/if}
            {/each}
          </tbody>
        </table>
        {@render pagination(recPage, recPages, (p) => (recPage = p))}
      {/if}
    </div>

  <!-- ================================================================ -->
  <!--  2. COMPARABLE SALES TAB                                         -->
  <!-- ================================================================ -->
  {:else if activeTab === "comparables"}
    <div class="flex items-center justify-between">
      <p class="text-sm text-neutral-400">{compCount} comparable{compCount !== 1 ? "s" : ""}</p>
      <button onclick={openCreateComp} class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg hover:bg-neutral-800 text-sm font-medium transition-colors">+ New Comparable</button>
    </div>

    <div class="flex gap-3 items-center">
      <div class="relative flex-1 max-w-sm">
        {@render searchIcon()}
        <input type="text" placeholder="Search comparables..." oninput={debounceSearch(v => { compSearch = v; compPage = 1; })} class="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent placeholder:text-neutral-400" />
      </div>
      <select bind:value={compType} onchange={() => (compPage = 1)} class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent">
        <option value="">All Types</option>
        {#each Object.entries(propTypeLabels) as [k, v]}<option value={k}>{v}</option>{/each}
      </select>
      <select bind:value={compSource} onchange={() => (compPage = 1)} class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent">
        <option value="">All Sources</option>
        {#each Object.entries(sourceLabels) as [k, v]}<option value={k}>{v}</option>{/each}
      </select>
    </div>

    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      {#if compLoading}
        <div class="p-16 text-center"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div><p class="mt-3 text-sm text-neutral-400">Loading...</p></div>
      {:else if compData.length === 0}
        <div class="p-16 text-center"><p class="text-sm font-medium text-neutral-900">No comparable sales found</p><p class="mt-1 text-sm text-neutral-400">Add market comparable data for reference.</p></div>
      {:else}
        <table class="w-full text-sm">
          <thead><tr class="border-b border-neutral-200">
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Address</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Sale Date</th>
            <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Sale Price</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Type</th>
            <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Area (sqft)</th>
            <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">{currency.config.symbol}/sqft</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Source</th>
            <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Actions</th>
          </tr></thead>
          <tbody class="divide-y divide-neutral-100">
            {#each compData as item}
              <tr onclick={() => toggleCompExpand(item.id)} class="hover:bg-neutral-50 cursor-pointer transition-colors">
                <td class="px-5 py-4"><div class="flex items-center gap-2">{@render chevron(compExpandedId === item.id)}<span class="font-medium text-neutral-900">{item.address}</span></div></td>
                <td class="px-5 py-4 text-neutral-500">{formatDate(item.sale_date)}</td>
                <td class="px-5 py-4 text-right font-medium text-neutral-900 tabular-nums">{formatCurrency(item.sale_price)}</td>
                <td class="px-5 py-4 text-neutral-500">{propTypeLabels[item.property_type] ?? (item.property_type || "\u2014")}</td>
                <td class="px-5 py-4 text-right text-neutral-500 tabular-nums">{formatNum(item.area_sqft)}</td>
                <td class="px-5 py-4 text-right text-neutral-500 tabular-nums">{item.price_per_sqft ? currency.formatCompact(item.price_per_sqft) : "\u2014"}</td>
                <td class="px-5 py-4 text-neutral-500">{sourceLabels[item.source] ?? item.source}</td>
                {@render actionBtns(() => viewComp(item.id), () => openEditComp(item.id), () => (compDeleteId = item.id))}
              </tr>
              {#if compExpandedId === item.id && compDetail}
                <tr class="bg-neutral-50">
                  <td colspan="8" class="px-8 py-5">
                    <div class="grid grid-cols-3 gap-x-8 gap-y-4">
                      {@render detailField("Linked Property", compDetail.property_name ?? "\u2014")}
                      {@render detailField("Proximity", compDetail.proximity_km ? compDetail.proximity_km + " km" : "\u2014")}
                      {@render detailField("Created", formatDateTime(compDetail.created_at))}
                      {@render detailField("Notes", compDetail.notes, true)}
                    </div>
                  </td>
                </tr>
              {/if}
            {/each}
          </tbody>
        </table>
        {@render pagination(compPage, compPages, (p) => (compPage = p))}
      {/if}
    </div>

  <!-- ================================================================ -->
  <!--  3. APPEALS TAB                                                  -->
  <!-- ================================================================ -->
  {:else if activeTab === "appeals"}
    <div class="flex items-center justify-between">
      <p class="text-sm text-neutral-400">{appCount} appeal{appCount !== 1 ? "s" : ""}</p>
      <button onclick={openCreateApp} class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg hover:bg-neutral-800 text-sm font-medium transition-colors">+ New Appeal</button>
    </div>

    <div class="flex gap-3 items-center">
      <div class="relative flex-1 max-w-sm">
        {@render searchIcon()}
        <input type="text" placeholder="Search appeals..." oninput={debounceSearch(v => { appSearch = v; appPage = 1; })} class="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent placeholder:text-neutral-400" />
      </div>
      <select bind:value={appProperty} onchange={() => (appPage = 1)} class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent">
        <option value="">All Properties</option>
        {#each properties as p}<option value={String(p.id)}>{p.name}</option>{/each}
      </select>
      <select bind:value={appType} onchange={() => (appPage = 1)} class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent">
        <option value="">All Types</option>
        {#each Object.entries(appealTypeLabels) as [k, v]}<option value={k}>{v}</option>{/each}
      </select>
      <select bind:value={appStatus} onchange={() => (appPage = 1)} class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent">
        <option value="">All Statuses</option>
        {#each Object.entries(appealStatusLabels) as [k, v]}<option value={k}>{v}</option>{/each}
      </select>
    </div>

    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      {#if appLoading}
        <div class="p-16 text-center"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div><p class="mt-3 text-sm text-neutral-400">Loading...</p></div>
      {:else if appData.length === 0}
        <div class="p-16 text-center"><p class="text-sm font-medium text-neutral-900">No appeals found</p><p class="mt-1 text-sm text-neutral-400">File a valuation appeal when needed.</p></div>
      {:else}
        <table class="w-full text-sm">
          <thead><tr class="border-b border-neutral-200">
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Property</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Type</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Filed</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Hearing</th>
            <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Assessed</th>
            <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Requested</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Outcome</th>
            <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Actions</th>
          </tr></thead>
          <tbody class="divide-y divide-neutral-100">
            {#each appData as item}
              <tr onclick={() => toggleAppExpand(item.id)} class="hover:bg-neutral-50 cursor-pointer transition-colors">
                <td class="px-5 py-4"><div class="flex items-center gap-2">{@render chevron(appExpandedId === item.id)}<span class="font-medium text-neutral-900">{item.property_name}</span></div></td>
                <td class="px-5 py-4 text-neutral-500">{appealTypeLabels[item.appeal_type] ?? item.appeal_type}</td>
                <td class="px-5 py-4"><span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {appealStatusColors[item.status] ?? 'bg-neutral-100 text-neutral-600'}">{appealStatusLabels[item.status] ?? item.status}</span></td>
                <td class="px-5 py-4 text-neutral-500">{formatDate(item.filed_date)}</td>
                <td class="px-5 py-4 text-neutral-500">{formatDate(item.hearing_date)}</td>
                <td class="px-5 py-4 text-right text-neutral-900 tabular-nums">{formatCurrency(item.assessed_value)}</td>
                <td class="px-5 py-4 text-right text-neutral-900 tabular-nums">{formatCurrency(item.requested_value)}</td>
                <td class="px-5 py-4"><span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {outcomeColors[item.outcome] ?? 'bg-neutral-100 text-neutral-600'}">{outcomeLabels[item.outcome] ?? item.outcome}</span></td>
                {@render actionBtns(() => viewApp(item.id), () => openEditApp(item.id), () => (appDeleteId = item.id))}
              </tr>
              {#if appExpandedId === item.id && appDetail}
                <tr class="bg-neutral-50">
                  <td colspan="9" class="px-8 py-5">
                    <div class="grid grid-cols-3 gap-x-8 gap-y-4">
                      {@render detailField("Decision Date", formatDate(appDetail.decision_date))}
                      {@render detailField("Decided Value", formatCurrency(appDetail.decided_value))}
                      {@render detailField("Filing Reference", appDetail.filing_reference)}
                      {@render detailField("Representative", appDetail.representative)}
                      {@render detailField("Created", formatDateTime(appDetail.created_at))}
                      {@render detailField("Last Updated", formatDateTime(appDetail.updated_at))}
                      {@render detailField("Notes", appDetail.notes, true)}
                    </div>
                  </td>
                </tr>
              {/if}
            {/each}
          </tbody>
        </table>
        {@render pagination(appPage, appPages, (p) => (appPage = p))}
      {/if}
    </div>
  {/if}
</div>

<!-- ======================================================================== -->
<!--  CREATE / EDIT MODALS                                                     -->
<!-- ======================================================================== -->

<!-- Valuation Record Modal -->
{#if showRecModal}
  <div class="fixed inset-0 z-50 flex items-start justify-center pt-[10vh]">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (showRecModal = false)} aria-label="Close"></button>
    <div class="relative w-full max-w-lg mx-4 rounded-2xl bg-white shadow-2xl border border-neutral-200 overflow-hidden">
      <div class="h-1 bg-neutral-900"></div>
      <form onsubmit={(e) => { e.preventDefault(); saveRec(); }} class="p-6 space-y-4">
        <h2 class="text-lg font-bold text-neutral-900">{recEditingId ? "Edit Valuation" : "New Valuation"}</h2>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="rec-prop" class="block text-sm font-medium text-neutral-700 mb-1">Property *</label>
            <select id="rec-prop" bind:value={recForm.property} required class={selectCls}>
              <option value={0} disabled>Select property</option>
              {#each properties as p}<option value={p.id}>{p.name}</option>{/each}
            </select>
            {#if fieldErr(recErrors, "property")}<p class="text-xs text-red-600 mt-1">{fieldErr(recErrors, "property")}</p>{/if}
          </div>
          <div>
            <label for="rec-type" class="block text-sm font-medium text-neutral-700 mb-1">Type</label>
            <select id="rec-type" bind:value={recForm.valuation_type} class={selectCls}>{#each Object.entries(valTypeLabels) as [k, v]}<option value={k}>{v}</option>{/each}</select>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="rec-date" class="block text-sm font-medium text-neutral-700 mb-1">Valuation Date *</label>
            <DateInput id="rec-date" bind:value={recForm.valuation_date} required />
            {#if fieldErr(recErrors, "valuation_date")}<p class="text-xs text-red-600 mt-1">{fieldErr(recErrors, "valuation_date")}</p>{/if}
          </div>
          <div>
            <label for="rec-value" class="block text-sm font-medium text-neutral-700 mb-1">Value *</label>
            <input id="rec-value" type="number" step="0.01" bind:value={recForm.value} required class={inputCls} placeholder="0.00" />
            {#if fieldErr(recErrors, "value")}<p class="text-xs text-red-600 mt-1">{fieldErr(recErrors, "value")}</p>{/if}
          </div>
        </div>
        <div>
          <label for="rec-appraiser" class="block text-sm font-medium text-neutral-700 mb-1">Appraiser</label>
          <input id="rec-appraiser" bind:value={recForm.appraiser} class={inputCls} />
        </div>
        <div>
          <label for="rec-notes" class="block text-sm font-medium text-neutral-700 mb-1">Notes</label>
          <textarea id="rec-notes" bind:value={recForm.notes} rows="2" class={inputCls}></textarea>
        </div>
        <div class="flex justify-end gap-3 pt-2">
          <button type="button" onclick={() => (showRecModal = false)} class="px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">Cancel</button>
          <button type="submit" disabled={recSaving} class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">{recSaving ? "Saving..." : recEditingId ? "Update" : "Create"}</button>
        </div>
      </form>
    </div>
  </div>
{/if}

<!-- Comparable Sale Modal -->
{#if showCompModal}
  <div class="fixed inset-0 z-50 flex items-start justify-center pt-[10vh]">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (showCompModal = false)} aria-label="Close"></button>
    <div class="relative w-full max-w-lg mx-4 rounded-2xl bg-white shadow-2xl border border-neutral-200 overflow-hidden max-h-[80vh] overflow-y-auto">
      <div class="h-1 bg-neutral-900"></div>
      <form onsubmit={(e) => { e.preventDefault(); saveComp(); }} class="p-6 space-y-4">
        <h2 class="text-lg font-bold text-neutral-900">{compEditingId ? "Edit Comparable Sale" : "New Comparable Sale"}</h2>
        <div>
          <label for="comp-addr" class="block text-sm font-medium text-neutral-700 mb-1">Address *</label>
          <input id="comp-addr" bind:value={compForm.address} required class={inputCls} />
          {#if fieldErr(compErrors, "address")}<p class="text-xs text-red-600 mt-1">{fieldErr(compErrors, "address")}</p>{/if}
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="comp-date" class="block text-sm font-medium text-neutral-700 mb-1">Sale Date *</label>
            <DateInput id="comp-date" bind:value={compForm.sale_date} required />
          </div>
          <div>
            <label for="comp-price" class="block text-sm font-medium text-neutral-700 mb-1">Sale Price *</label>
            <input id="comp-price" type="number" step="0.01" bind:value={compForm.sale_price} required class={inputCls} placeholder="0.00" />
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="comp-ptype" class="block text-sm font-medium text-neutral-700 mb-1">Property Type</label>
            <select id="comp-ptype" bind:value={compForm.property_type} class={selectCls}>
              <option value="">Not Specified</option>
              {#each Object.entries(propTypeLabels) as [k, v]}<option value={k}>{v}</option>{/each}
            </select>
          </div>
          <div>
            <label for="comp-source" class="block text-sm font-medium text-neutral-700 mb-1">Source</label>
            <select id="comp-source" bind:value={compForm.source} class={selectCls}>{#each Object.entries(sourceLabels) as [k, v]}<option value={k}>{v}</option>{/each}</select>
          </div>
        </div>
        <div class="grid grid-cols-3 gap-4">
          <div>
            <label for="comp-area" class="block text-sm font-medium text-neutral-700 mb-1">Area (sqft)</label>
            <input id="comp-area" type="number" step="0.01" bind:value={compForm.area_sqft} class={inputCls} />
          </div>
          <div>
            <label for="comp-ppsf" class="block text-sm font-medium text-neutral-700 mb-1">{currency.config.symbol}/sqft</label>
            <input id="comp-ppsf" type="number" step="0.01" bind:value={compForm.price_per_sqft} class={inputCls} />
          </div>
          <div>
            <label for="comp-prox" class="block text-sm font-medium text-neutral-700 mb-1">Proximity (km)</label>
            <input id="comp-prox" type="number" step="0.01" bind:value={compForm.proximity_km} class={inputCls} />
          </div>
        </div>
        <div>
          <label for="comp-prop" class="block text-sm font-medium text-neutral-700 mb-1">Linked Property (optional)</label>
          <select id="comp-prop" bind:value={compForm.property} class={selectCls}>
            <option value={null}>None</option>
            {#each properties as p}<option value={p.id}>{p.name}</option>{/each}
          </select>
        </div>
        <div>
          <label for="comp-notes" class="block text-sm font-medium text-neutral-700 mb-1">Notes</label>
          <textarea id="comp-notes" bind:value={compForm.notes} rows="2" class={inputCls}></textarea>
        </div>
        <div class="flex justify-end gap-3 pt-2">
          <button type="button" onclick={() => (showCompModal = false)} class="px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">Cancel</button>
          <button type="submit" disabled={compSaving} class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">{compSaving ? "Saving..." : compEditingId ? "Update" : "Create"}</button>
        </div>
      </form>
    </div>
  </div>
{/if}

<!-- Appeal Modal -->
{#if showAppModal}
  <div class="fixed inset-0 z-50 flex items-start justify-center pt-[10vh]">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (showAppModal = false)} aria-label="Close"></button>
    <div class="relative w-full max-w-lg mx-4 rounded-2xl bg-white shadow-2xl border border-neutral-200 overflow-hidden max-h-[80vh] overflow-y-auto">
      <div class="h-1 bg-neutral-900"></div>
      <form onsubmit={(e) => { e.preventDefault(); saveApp(); }} class="p-6 space-y-4">
        <h2 class="text-lg font-bold text-neutral-900">{appEditingId ? "Edit Appeal" : "New Valuation Appeal"}</h2>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="app-prop" class="block text-sm font-medium text-neutral-700 mb-1">Property *</label>
            <select id="app-prop" bind:value={appForm.property} required class={selectCls}>
              <option value={0} disabled>Select property</option>
              {#each properties as p}<option value={p.id}>{p.name}</option>{/each}
            </select>
            {#if fieldErr(appErrors, "property")}<p class="text-xs text-red-600 mt-1">{fieldErr(appErrors, "property")}</p>{/if}
          </div>
          <div>
            <label for="app-type" class="block text-sm font-medium text-neutral-700 mb-1">Appeal Type</label>
            <select id="app-type" bind:value={appForm.appeal_type} class={selectCls}>{#each Object.entries(appealTypeLabels) as [k, v]}<option value={k}>{v}</option>{/each}</select>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="app-status" class="block text-sm font-medium text-neutral-700 mb-1">Status</label>
            <select id="app-status" bind:value={appForm.status} class={selectCls}>{#each Object.entries(appealStatusLabels) as [k, v]}<option value={k}>{v}</option>{/each}</select>
          </div>
          <div>
            <label for="app-outcome" class="block text-sm font-medium text-neutral-700 mb-1">Outcome</label>
            <select id="app-outcome" bind:value={appForm.outcome} class={selectCls}>{#each Object.entries(outcomeLabels) as [k, v]}<option value={k}>{v}</option>{/each}</select>
          </div>
        </div>
        <div class="grid grid-cols-3 gap-4">
          <div>
            <label for="app-filed" class="block text-sm font-medium text-neutral-700 mb-1">Filed Date *</label>
            <DateInput id="app-filed" bind:value={appForm.filed_date} required />
          </div>
          <div>
            <label for="app-hearing" class="block text-sm font-medium text-neutral-700 mb-1">Hearing Date</label>
            <DateInput id="app-hearing" bind:value={appForm.hearing_date} />
          </div>
          <div>
            <label for="app-decision" class="block text-sm font-medium text-neutral-700 mb-1">Decision Date</label>
            <DateInput id="app-decision" bind:value={appForm.decision_date} />
          </div>
        </div>
        <div class="grid grid-cols-3 gap-4">
          <div>
            <label for="app-assessed" class="block text-sm font-medium text-neutral-700 mb-1">Assessed Value *</label>
            <input id="app-assessed" type="number" step="0.01" bind:value={appForm.assessed_value} required class={inputCls} placeholder="0.00" />
          </div>
          <div>
            <label for="app-requested" class="block text-sm font-medium text-neutral-700 mb-1">Requested Value *</label>
            <input id="app-requested" type="number" step="0.01" bind:value={appForm.requested_value} required class={inputCls} placeholder="0.00" />
          </div>
          <div>
            <label for="app-decided" class="block text-sm font-medium text-neutral-700 mb-1">Decided Value</label>
            <input id="app-decided" type="number" step="0.01" bind:value={appForm.decided_value} class={inputCls} placeholder="0.00" />
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="app-ref" class="block text-sm font-medium text-neutral-700 mb-1">Filing Reference</label>
            <input id="app-ref" bind:value={appForm.filing_reference} class={inputCls} />
          </div>
          <div>
            <label for="app-rep" class="block text-sm font-medium text-neutral-700 mb-1">Representative</label>
            <input id="app-rep" bind:value={appForm.representative} class={inputCls} />
          </div>
        </div>
        <div>
          <label for="app-notes" class="block text-sm font-medium text-neutral-700 mb-1">Notes</label>
          <textarea id="app-notes" bind:value={appForm.notes} rows="2" class={inputCls}></textarea>
        </div>
        <div class="flex justify-end gap-3 pt-2">
          <button type="button" onclick={() => (showAppModal = false)} class="px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">Cancel</button>
          <button type="submit" disabled={appSaving} class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">{appSaving ? "Saving..." : appEditingId ? "Update" : "Create"}</button>
        </div>
      </form>
    </div>
  </div>
{/if}

<!-- ======================================================================== -->
<!--  DELETE CONFIRMATION MODALS                                               -->
<!-- ======================================================================== -->

{#if recDeleteId !== null}
  {@const item = recData.find(r => r.id === recDeleteId)}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (recDeleteId = null)} aria-label="Close"></button>
    <div class="relative w-full max-w-sm rounded-2xl bg-white shadow-2xl border border-neutral-200 p-6">
      <h3 class="text-lg font-bold text-neutral-900">Delete Valuation</h3>
      <p class="mt-2 text-sm text-neutral-600">Are you sure you want to delete the <strong>{item?.property_name}</strong> valuation from <strong>{formatDate(item?.valuation_date ?? null)}</strong>? This action cannot be undone.</p>
      <div class="mt-6 flex items-center justify-end gap-3">
        <button onclick={() => (recDeleteId = null)} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">Cancel</button>
        <button onclick={deleteRec} disabled={recDeleting} class="rounded-lg bg-red-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-red-700 transition-colors disabled:opacity-60">{recDeleting ? "Deleting..." : "Delete"}</button>
      </div>
    </div>
  </div>
{/if}

{#if compDeleteId !== null}
  {@const item = compData.find(r => r.id === compDeleteId)}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (compDeleteId = null)} aria-label="Close"></button>
    <div class="relative w-full max-w-sm rounded-2xl bg-white shadow-2xl border border-neutral-200 p-6">
      <h3 class="text-lg font-bold text-neutral-900">Delete Comparable Sale</h3>
      <p class="mt-2 text-sm text-neutral-600">Are you sure you want to delete <strong>{item?.address}</strong>? This action cannot be undone.</p>
      <div class="mt-6 flex items-center justify-end gap-3">
        <button onclick={() => (compDeleteId = null)} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">Cancel</button>
        <button onclick={deleteComp} disabled={compDeleting} class="rounded-lg bg-red-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-red-700 transition-colors disabled:opacity-60">{compDeleting ? "Deleting..." : "Delete"}</button>
      </div>
    </div>
  </div>
{/if}

{#if appDeleteId !== null}
  {@const item = appData.find(r => r.id === appDeleteId)}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (appDeleteId = null)} aria-label="Close"></button>
    <div class="relative w-full max-w-sm rounded-2xl bg-white shadow-2xl border border-neutral-200 p-6">
      <h3 class="text-lg font-bold text-neutral-900">Delete Appeal</h3>
      <p class="mt-2 text-sm text-neutral-600">Are you sure you want to delete the appeal for <strong>{item?.property_name}</strong>? This action cannot be undone.</p>
      <div class="mt-6 flex items-center justify-end gap-3">
        <button onclick={() => (appDeleteId = null)} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">Cancel</button>
        <button onclick={deleteApp} disabled={appDeleting} class="rounded-lg bg-red-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-red-700 transition-colors disabled:opacity-60">{appDeleting ? "Deleting..." : "Delete"}</button>
      </div>
    </div>
  </div>
{/if}

<!-- ======================================================================== -->
<!--  VIEW DETAIL MODALS                                                       -->
<!-- ======================================================================== -->

{#if recViewing}
  <div class="fixed inset-0 z-50 flex items-start justify-center pt-[8vh]">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (recViewing = null)} aria-label="Close"></button>
    <div class="relative w-full max-w-2xl mx-4 rounded-2xl bg-white shadow-2xl border border-neutral-200 overflow-hidden max-h-[80vh] overflow-y-auto">
      <div class="h-1 bg-neutral-900"></div>
      <div class="p-6 space-y-6">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-bold text-neutral-900">Valuation Details</h2>
          <div class="flex items-center gap-2">
            <button onclick={editFromViewRec} class="px-3 py-1.5 text-sm font-medium text-neutral-600 hover:bg-neutral-100 rounded-lg transition-colors">Edit</button>
            <button onclick={() => (recViewing = null)} class="px-3 py-1.5 text-sm font-medium text-neutral-600 hover:bg-neutral-100 rounded-lg transition-colors">Close</button>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-x-8 gap-y-5">
          {@render detailField("Property", recViewing.property_name)}
          {@render detailField("Valuation Date", formatDate(recViewing.valuation_date))}
          {@render detailField("Value", formatCurrency(recViewing.value))}
          {@render detailField("Type", valTypeLabels[recViewing.valuation_type] ?? recViewing.valuation_type)}
          {@render detailField("Appraiser", recViewing.appraiser)}
        </div>
        {#if recViewing.notes}
          <div>{@render detailField("Notes", recViewing.notes, true)}</div>
        {/if}
        <div class="border-t border-neutral-100 pt-4">
          <p class="text-xs text-neutral-400">Created {formatDateTime(recViewing.created_at)}</p>
        </div>
      </div>
    </div>
  </div>
{/if}

{#if compViewing}
  <div class="fixed inset-0 z-50 flex items-start justify-center pt-[8vh]">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (compViewing = null)} aria-label="Close"></button>
    <div class="relative w-full max-w-2xl mx-4 rounded-2xl bg-white shadow-2xl border border-neutral-200 overflow-hidden max-h-[80vh] overflow-y-auto">
      <div class="h-1 bg-neutral-900"></div>
      <div class="p-6 space-y-6">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-bold text-neutral-900">Comparable Sale Details</h2>
          <div class="flex items-center gap-2">
            <button onclick={editFromViewComp} class="px-3 py-1.5 text-sm font-medium text-neutral-600 hover:bg-neutral-100 rounded-lg transition-colors">Edit</button>
            <button onclick={() => (compViewing = null)} class="px-3 py-1.5 text-sm font-medium text-neutral-600 hover:bg-neutral-100 rounded-lg transition-colors">Close</button>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-x-8 gap-y-5">
          {@render detailField("Address", compViewing.address)}
          {@render detailField("Sale Date", formatDate(compViewing.sale_date))}
          {@render detailField("Sale Price", formatCurrency(compViewing.sale_price))}
          {@render detailField("Property Type", propTypeLabels[compViewing.property_type] ?? (compViewing.property_type || "\u2014"))}
          {@render detailField("Area", compViewing.area_sqft ? formatNum(compViewing.area_sqft) + " sqft" : "\u2014")}
          {@render detailField("Price per sqft", compViewing.price_per_sqft ? currency.formatCompact(compViewing.price_per_sqft) : "\u2014")}
          {@render detailField("Proximity", compViewing.proximity_km ? compViewing.proximity_km + " km" : "\u2014")}
          {@render detailField("Source", sourceLabels[compViewing.source] ?? compViewing.source)}
          {@render detailField("Linked Property", compViewing.property_name ?? "\u2014")}
        </div>
        {#if compViewing.notes}
          <div>{@render detailField("Notes", compViewing.notes, true)}</div>
        {/if}
        <div class="border-t border-neutral-100 pt-4 flex gap-6">
          <p class="text-xs text-neutral-400">Created {formatDateTime(compViewing.created_at)}</p>
          <p class="text-xs text-neutral-400">Updated {formatDateTime(compViewing.updated_at)}</p>
        </div>
      </div>
    </div>
  </div>
{/if}

{#if appViewing}
  <div class="fixed inset-0 z-50 flex items-start justify-center pt-[8vh]">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (appViewing = null)} aria-label="Close"></button>
    <div class="relative w-full max-w-2xl mx-4 rounded-2xl bg-white shadow-2xl border border-neutral-200 overflow-hidden max-h-[80vh] overflow-y-auto">
      <div class="h-1 bg-neutral-900"></div>
      <div class="p-6 space-y-6">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-bold text-neutral-900">Appeal Details</h2>
          <div class="flex items-center gap-2">
            <button onclick={editFromViewApp} class="px-3 py-1.5 text-sm font-medium text-neutral-600 hover:bg-neutral-100 rounded-lg transition-colors">Edit</button>
            <button onclick={() => (appViewing = null)} class="px-3 py-1.5 text-sm font-medium text-neutral-600 hover:bg-neutral-100 rounded-lg transition-colors">Close</button>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-x-8 gap-y-5">
          {@render detailField("Property", appViewing.property_name)}
          {@render detailField("Appeal Type", appealTypeLabels[appViewing.appeal_type] ?? appViewing.appeal_type)}
          {@render detailField("Status", appealStatusLabels[appViewing.status] ?? appViewing.status)}
          {@render detailField("Outcome", outcomeLabels[appViewing.outcome] ?? appViewing.outcome)}
          {@render detailField("Filed Date", formatDate(appViewing.filed_date))}
          {@render detailField("Hearing Date", formatDate(appViewing.hearing_date))}
          {@render detailField("Decision Date", formatDate(appViewing.decision_date))}
          {@render detailField("Assessed Value", formatCurrency(appViewing.assessed_value))}
          {@render detailField("Requested Value", formatCurrency(appViewing.requested_value))}
          {@render detailField("Decided Value", formatCurrency(appViewing.decided_value))}
          {@render detailField("Filing Reference", appViewing.filing_reference)}
          {@render detailField("Representative", appViewing.representative)}
        </div>
        {#if appViewing.notes}
          <div>{@render detailField("Notes", appViewing.notes, true)}</div>
        {/if}
        <div class="border-t border-neutral-100 pt-4 flex gap-6">
          <p class="text-xs text-neutral-400">Created {formatDateTime(appViewing.created_at)}</p>
          <p class="text-xs text-neutral-400">Updated {formatDateTime(appViewing.updated_at)}</p>
        </div>
      </div>
    </div>
  </div>
{/if}

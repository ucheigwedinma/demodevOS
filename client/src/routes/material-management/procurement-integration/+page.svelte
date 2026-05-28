<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import { onMount } from "svelte";

  interface StatusCounts { total: number; by_status: Record<string, number>; }
  interface PipelineItem {
    id: number; requisition_id: string; project_name: string; urgency: string;
    created_at: string; stage: string; stage_status: string;
    mat_req_status: string; pr_number: string | null; pr_status: string | null;
    rfq_number: string | null; rfq_status: string | null;
    po_number: string | null; po_status: string | null;
    estimated_total: string; line_count: number;
  }
  interface IntegrationData {
    summary: {
      material_requisitions: StatusCounts;
      purchase_requisitions: StatusCounts;
      rfqs: StatusCounts;
      purchase_orders: StatusCounts;
    };
    pipeline: PipelineItem[];
  }

  const STAGES = ["material_requisition", "purchase_requisition", "rfq", "purchase_order"] as const;
  const STAGE_LABELS: Record<string, string> = {
    material_requisition: "Site Requisition",
    purchase_requisition: "Purchase Request",
    rfq: "RFQ / Bidding",
    purchase_order: "Purchase Order",
  };
  const STAGE_ICONS: Record<string, string> = {
    material_requisition: "M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h10.5",
    purchase_requisition: "M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25Z",
    rfq: "M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 5.25h.008v.008H12v-.008Z",
    purchase_order: "M15.75 10.5V6a3.75 3.75 0 1 0-7.5 0v4.5m11.356-1.993 1.263 12c.07.665-.45 1.243-1.119 1.243H4.25a1.125 1.125 0 0 1-1.12-1.243l1.264-12A1.125 1.125 0 0 1 5.513 7.5h12.974c.576 0 1.059.435 1.119 1.007ZM8.625 10.5a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm7.5 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z",
  };
  const URGENCY_COLORS: Record<string, string> = {
    low: "bg-neutral-100 text-neutral-500", normal: "bg-blue-50 text-blue-600",
    high: "bg-amber-50 text-amber-700", critical: "bg-red-50 text-red-700",
  };

  interface BridgeItem {
    req_id: number; requisition_id: string; line_id: number;
    project_id: number; project_name: string; phase_name: string; site_location: string;
    urgency: string; material_id: number | null; material_name: string;
    material_code: string; material_category: string;
    quantity: string; unit_of_measure: string; unit_cost: string; estimated_cost: string;
    available_stock: string; stock_sufficient: boolean;
    required_by_date: string | null; days_until_required: number; date_urgency: string;
    created_by: string; created_at: string;
  }
  interface BridgeData {
    items: BridgeItem[];
    total_count: number; critical_count: number;
    stock_sufficient_count: number; total_value: string;
  }

  let loading = $state(true);
  let data = $state<IntegrationData | null>(null);
  let stageFilter = $state("");
  let activeTab = $state<"pipeline" | "bridge">("pipeline");

  // Bridge state
  let bridgeLoading = $state(false);
  let bridgeData = $state<BridgeData | null>(null);
  let selectedLineIds = $state<number[]>([]);
  let bulkCreating = $state(false);

  function toggleLine(id: number) {
    if (selectedLineIds.includes(id)) selectedLineIds = selectedLineIds.filter(x => x !== id);
    else selectedLineIds = [...selectedLineIds, id];
  }
  function selectAll() {
    if (!bridgeData) return;
    if (selectedLineIds.length === bridgeData.items.length) selectedLineIds = [];
    else selectedLineIds = bridgeData.items.map(i => i.line_id);
  }

  async function loadBridge() {
    bridgeLoading = true;
    try {
      bridgeData = await api.get<BridgeData>("/procurement-integration/bridge/");
    } catch { toast.error("Load failed", "Could not load bridge data."); }
    finally { bridgeLoading = false; }
  }

  async function bulkCreatePR(merge: boolean) {
    if (selectedLineIds.length === 0) { toast.error("Select items", "Select at least one line item."); return; }
    bulkCreating = true;
    try {
      const res = await api.post<{ detail: string; created: { pr_number: string; item_count: number; total: string }[] }>(
        "/procurement-integration/bridge/",
        { line_ids: selectedLineIds, merge },
      );
      toast.success("PRs Created", `${res.created.length} Purchase Request(s) created: ${res.created.map(p => p.pr_number).join(", ")}`);
      selectedLineIds = [];
      await loadBridge();
      await loadData();
    } catch (err) {
      if (err instanceof ApiError) toast.error("Failed", err.data?.detail || "Could not create PRs.");
      else toast.error("Failed", "Could not create Purchase Requests.");
    } finally { bulkCreating = false; }
  }

  const filteredPipeline = $derived.by(() => {
    if (!data) return [];
    if (!stageFilter) return data.pipeline;
    return data.pipeline.filter(p => p.stage === stageFilter);
  });

  function stageIdx(stage: string): number {
    return STAGES.indexOf(stage as typeof STAGES[number]);
  }

  function timeAgo(dateStr: string): string {
    const diff = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000);
    if (diff < 60) return "just now";
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  }

  async function loadData() {
    loading = true;
    try {
      data = await api.get<IntegrationData>("/procurement-integration/");
    } catch { toast.error("Load failed", "Could not load procurement integration data."); }
    finally { loading = false; }
  }

  onMount(() => { loadData(); loadBridge(); });
</script>

<svelte:head><title>Procurement Integration | developerOS</title></svelte:head>

<div class="space-y-6">
  <!-- Header -->
  <div>
    <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-700">Material Management</p>
    <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Procurement Integration</h1>
    <p class="mt-1 text-sm text-neutral-500">End-to-end material pipeline: Site Requisition → Purchase Request → RFQ → Purchase Order.</p>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-32">
      <div class="flex flex-col items-center gap-3">
        <div class="h-8 w-8 rounded-full border-2 border-neutral-200 border-t-neutral-900 animate-spin"></div>
        <p class="text-sm text-neutral-400">Loading pipeline...</p>
      </div>
    </div>
  {:else if data}

    <!-- Global Pipeline Stepper -->
    <div class="rounded-xl border border-neutral-200 bg-white p-6" style="backdrop-filter: blur(10px)">
      <div class="flex items-center justify-between">
        {#each STAGES as stage, i}
          {@const count = stage === "material_requisition" ? data.summary.material_requisitions.total : stage === "purchase_requisition" ? data.summary.purchase_requisitions.total : stage === "rfq" ? data.summary.rfqs.total : data.summary.purchase_orders.total}
          {@const active = filteredPipeline.filter(p => p.stage === stage).length}
          <button
            class="flex flex-col items-center gap-2 group cursor-pointer {stageFilter === stage ? 'opacity-100' : 'opacity-70 hover:opacity-100'} transition-opacity"
            onclick={() => { stageFilter = stageFilter === stage ? "" : stage; }}
          >
            <div class="flex items-center justify-center h-12 w-12 rounded-xl {stageFilter === stage ? 'bg-neutral-900 text-white shadow-lg' : 'bg-neutral-100 text-neutral-600 group-hover:bg-neutral-200'} transition-all">
              <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d={STAGE_ICONS[stage]} />
              </svg>
            </div>
            <div class="text-center">
              <p class="text-[10px] font-semibold text-neutral-500 uppercase tracking-wider">{STAGE_LABELS[stage]}</p>
              <p class="text-lg font-bold text-neutral-900 tabular-nums">{count}</p>
              {#if active > 0 && stageFilter !== stage}
                <p class="text-[9px] text-amber-600 font-semibold">{active} active</p>
              {/if}
            </div>
          </button>
          {#if i < STAGES.length - 1}
            <div class="flex-1 flex items-center mx-3">
              <div class="w-full h-px bg-neutral-200 relative">
                <svg class="absolute right-0 top-1/2 -translate-y-1/2 -mr-1 h-3 w-3 text-neutral-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" /></svg>
              </div>
            </div>
          {/if}
        {/each}
      </div>
    </div>

    <!-- Stage Summary Cards -->
    <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
      {#each STAGES as stage}
        {@const summary = stage === "material_requisition" ? data.summary.material_requisitions : stage === "purchase_requisition" ? data.summary.purchase_requisitions : stage === "rfq" ? data.summary.rfqs : data.summary.purchase_orders}
        <div class="rounded-xl border border-neutral-200 bg-white p-4" style="backdrop-filter: blur(10px)">
          <h4 class="text-[9px] font-semibold text-neutral-400 uppercase tracking-widest mb-3">{STAGE_LABELS[stage]}</h4>
          <div class="space-y-1.5">
            {#each Object.entries(summary.by_status) as [status, count]}
              <div class="flex items-center justify-between">
                <span class="text-[10px] text-neutral-600 capitalize">{status.replace(/_/g, ' ')}</span>
                <span class="rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] font-semibold text-neutral-700 tabular-nums">{count}</span>
              </div>
            {/each}
            {#if Object.keys(summary.by_status).length === 0}
              <p class="text-[10px] text-neutral-400">No records</p>
            {/if}
          </div>
        </div>
      {/each}
    </div>

    <!-- Tab Switcher -->
    <div class="flex gap-1 rounded-lg bg-neutral-100 p-1 w-fit">
      <button onclick={() => { activeTab = "pipeline"; }} class="rounded-md px-4 py-2 text-sm font-medium transition-colors {activeTab === 'pipeline' ? 'bg-white text-neutral-900 shadow-sm' : 'text-neutral-500 hover:text-neutral-700'}">Pipeline Tracker</button>
      <button onclick={() => { activeTab = "bridge"; }} class="rounded-md px-4 py-2 text-sm font-medium transition-colors {activeTab === 'bridge' ? 'bg-white text-neutral-900 shadow-sm' : 'text-neutral-500 hover:text-neutral-700'}">
        Procurement Bridge
        {#if bridgeData && bridgeData.total_count > 0}
          <span class="ml-1.5 rounded-full bg-amber-500 text-white px-1.5 py-0.5 text-[9px] font-bold tabular-nums">{bridgeData.total_count}</span>
        {/if}
      </button>
    </div>

    <!-- Bridge View -->
    {#if activeTab === "bridge"}
      <section class="space-y-4">
        {#if bridgeLoading}
          <p class="py-12 text-center text-sm text-neutral-400">Loading bridge data...</p>
        {:else if bridgeData}
          <!-- Bridge KPIs -->
          <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div class="rounded-xl border border-neutral-200 bg-white p-4 text-center">
              <p class="text-[9px] font-semibold text-neutral-400 uppercase tracking-wider">Pending Items</p>
              <p class="mt-1 text-2xl font-bold text-neutral-900 tabular-nums">{bridgeData.total_count}</p>
            </div>
            <div class="rounded-xl border {bridgeData.critical_count > 0 ? 'border-red-200 bg-red-50' : 'border-neutral-200 bg-white'} p-4 text-center">
              <p class="text-[9px] font-semibold {bridgeData.critical_count > 0 ? 'text-red-400' : 'text-neutral-400'} uppercase tracking-wider">Critical (&lt;7d)</p>
              <p class="mt-1 text-2xl font-bold {bridgeData.critical_count > 0 ? 'text-red-700' : 'text-neutral-900'} tabular-nums">{bridgeData.critical_count}</p>
            </div>
            <div class="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-center">
              <p class="text-[9px] font-semibold text-emerald-400 uppercase tracking-wider">In Stock</p>
              <p class="mt-1 text-2xl font-bold text-emerald-700 tabular-nums">{bridgeData.stock_sufficient_count}</p>
            </div>
            <div class="rounded-xl border border-neutral-200 bg-white p-4 text-center">
              <p class="text-[9px] font-semibold text-emerald-500 uppercase tracking-wider">Total Value</p>
              <p class="mt-1 text-lg font-bold text-emerald-700 tabular-nums">{currency.format(Number(bridgeData.total_value))}</p>
            </div>
          </div>

          <!-- Bulk Actions -->
          {#if selectedLineIds.length > 0}
            <div class="flex items-center gap-3 rounded-xl border border-indigo-200 bg-indigo-50 px-5 py-3">
              <span class="text-sm font-semibold text-indigo-700">{selectedLineIds.length} item(s) selected</span>
              <div class="flex-1"></div>
              <button onclick={() => bulkCreatePR(false)} disabled={bulkCreating} class="rounded-lg bg-neutral-900 px-4 py-2 text-xs font-semibold text-white hover:bg-neutral-800 disabled:opacity-50">
                {bulkCreating ? "Creating..." : "Create PR (Per Requisition)"}
              </button>
              <button onclick={() => bulkCreatePR(true)} disabled={bulkCreating} class="rounded-lg bg-indigo-600 px-4 py-2 text-xs font-semibold text-white hover:bg-indigo-700 disabled:opacity-50">
                {bulkCreating ? "Creating..." : "Merge into One PR"}
              </button>
              <button onclick={() => { selectedLineIds = []; }} class="rounded-lg border border-neutral-200 px-3 py-2 text-xs font-medium text-neutral-600 hover:bg-neutral-50">Clear</button>
            </div>
          {/if}

          <!-- Bridge Table -->
          <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
            <div class="border-b border-neutral-100 bg-neutral-50 px-5 py-3 flex items-center justify-between">
              <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest">Approved Requisition Lines — Ready for PR Conversion</h3>
              <button onclick={selectAll} class="text-[10px] font-medium text-indigo-600 hover:text-indigo-800">
                {selectedLineIds.length === bridgeData.items.length ? "Deselect All" : "Select All"}
              </button>
            </div>

            {#if bridgeData.items.length === 0}
              <div class="p-8 text-center">
                <p class="text-sm text-neutral-500">No approved requisitions pending procurement action.</p>
                <p class="text-[10px] text-neutral-400 mt-1">When material requisitions are approved by the Project Manager, they'll appear here.</p>
              </div>
            {:else}
              <div class="overflow-x-auto">
                <table class="w-full text-sm">
                  <thead>
                    <tr class="border-b border-neutral-100">
                      <th class="px-3 py-2.5 text-center w-10"><input type="checkbox" checked={selectedLineIds.length === bridgeData.items.length && bridgeData.items.length > 0} onchange={selectAll} class="rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900" /></th>
                      <th class="px-3 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase">Material</th>
                      <th class="px-3 py-2.5 text-center text-[10px] font-semibold text-neutral-500 uppercase">Qty</th>
                      <th class="px-3 py-2.5 text-center text-[10px] font-semibold text-neutral-500 uppercase">Stock</th>
                      <th class="px-3 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase">Site</th>
                      <th class="px-3 py-2.5 text-center text-[10px] font-semibold text-neutral-500 uppercase">Required</th>
                      <th class="px-3 py-2.5 text-right text-[10px] font-semibold text-neutral-500 uppercase">Est. Cost</th>
                      <th class="px-3 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase">Req ID</th>
                      <th class="px-3 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase">Project</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-neutral-50">
                    {#each bridgeData.items as item}
                      <tr class="hover:bg-neutral-50 {selectedLineIds.includes(item.line_id) ? 'bg-indigo-50/50' : ''}">
                        <td class="px-3 py-2.5 text-center">
                          <input type="checkbox" checked={selectedLineIds.includes(item.line_id)} onchange={() => toggleLine(item.line_id)} class="rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900" />
                        </td>
                        <td class="px-3 py-2.5">
                          <div>
                            <p class="font-medium text-neutral-900">{item.material_name}</p>
                            {#if item.material_code}<p class="text-[10px] text-neutral-400">{item.material_code}</p>{/if}
                          </div>
                        </td>
                        <td class="px-3 py-2.5 text-center tabular-nums font-medium">{item.quantity} <span class="text-neutral-400 text-[10px]">{item.unit_of_measure}</span></td>
                        <td class="px-3 py-2.5 text-center">
                          <span class="rounded-full px-2 py-0.5 text-[10px] font-semibold tabular-nums {item.stock_sufficient ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}">
                            {item.available_stock}
                          </span>
                        </td>
                        <td class="px-3 py-2.5 text-neutral-600 max-w-[120px] truncate" title={item.site_location}>{item.site_location || "—"}</td>
                        <td class="px-3 py-2.5 text-center">
                          {#if item.required_by_date}
                            <span class="rounded-full px-2 py-0.5 text-[10px] font-semibold tabular-nums
                              {item.date_urgency === 'critical' ? 'bg-red-100 text-red-700' :
                               item.date_urgency === 'warning' ? 'bg-amber-100 text-amber-700' :
                               'bg-neutral-100 text-neutral-600'}">
                              {item.required_by_date}
                              {#if item.date_urgency === "critical"}
                                <span class="ml-1 text-red-500">{item.days_until_required}d</span>
                              {/if}
                            </span>
                          {:else}
                            <span class="text-neutral-400">—</span>
                          {/if}
                        </td>
                        <td class="px-3 py-2.5 text-right font-semibold text-neutral-900 tabular-nums">{currency.format(Number(item.estimated_cost))}</td>
                        <td class="px-3 py-2.5 text-[10px] font-medium text-indigo-600">{item.requisition_id}</td>
                        <td class="px-3 py-2.5 text-neutral-600 max-w-[120px] truncate">{item.project_name}</td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </div>
            {/if}
          </div>
        {/if}
      </section>
    {/if}

    <!-- Pipeline Table -->
    {#if activeTab === "pipeline"}
    <section class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
      <div class="border-b border-neutral-100 bg-neutral-50 px-5 py-3 flex items-center justify-between">
        <h3 class="text-[10px] font-semibold text-neutral-400 uppercase tracking-widest">
          Active Pipeline ({filteredPipeline.length})
          {#if stageFilter}
            <button onclick={() => { stageFilter = ""; }} class="ml-2 rounded-full bg-neutral-200 px-2 py-0.5 text-[9px] font-medium text-neutral-600 hover:bg-neutral-300">Clear filter</button>
          {/if}
        </h3>
      </div>

      {#if filteredPipeline.length === 0}
        <div class="p-8 text-center">
          <p class="text-sm text-neutral-400">No active pipeline items.</p>
        </div>
      {:else}
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-100">
                <th class="px-4 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase">Req ID</th>
                <th class="px-4 py-2.5 text-left text-[10px] font-semibold text-neutral-500 uppercase">Project</th>
                <th class="px-4 py-2.5 text-center text-[10px] font-semibold text-neutral-500 uppercase">Urgency</th>
                <th class="px-4 py-2.5 text-center text-[10px] font-semibold text-neutral-500 uppercase">Lines</th>
                <th class="px-4 py-2.5 text-right text-[10px] font-semibold text-neutral-500 uppercase">Value</th>
                <!-- Pipeline Stage Indicators -->
                <th class="px-2 py-2.5 text-center text-[9px] font-semibold text-neutral-400 uppercase">Site Req</th>
                <th class="px-2 py-2.5 text-center text-[9px] font-semibold text-neutral-400 uppercase">PR</th>
                <th class="px-2 py-2.5 text-center text-[9px] font-semibold text-neutral-400 uppercase">RFQ</th>
                <th class="px-2 py-2.5 text-center text-[9px] font-semibold text-neutral-400 uppercase">PO</th>
                <th class="px-4 py-2.5 text-right text-[10px] font-semibold text-neutral-500 uppercase">Created</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-50">
              {#each filteredPipeline as item}
                {@const si = stageIdx(item.stage)}
                <tr class="hover:bg-neutral-50">
                  <td class="px-4 py-3 font-semibold text-neutral-900">{item.requisition_id}</td>
                  <td class="px-4 py-3 text-neutral-700 max-w-[150px] truncate">{item.project_name}</td>
                  <td class="px-4 py-3 text-center"><span class="rounded-full border px-2 py-0.5 text-[10px] font-semibold {URGENCY_COLORS[item.urgency] || ''}">{item.urgency}</span></td>
                  <td class="px-4 py-3 text-center tabular-nums text-neutral-600">{item.line_count}</td>
                  <td class="px-4 py-3 text-right font-semibold text-neutral-900 tabular-nums">{currency.format(Number(item.estimated_total || 0))}</td>

                  <!-- Stage 1: Site Requisition -->
                  <td class="px-2 py-3 text-center">
                    {#if si >= 0}
                      <span class="inline-flex items-center justify-center h-5 w-5 rounded-full {si > 0 ? 'bg-emerald-500' : 'bg-indigo-600 ring-2 ring-indigo-200'}">
                        {#if si > 0}
                          <svg class="h-3 w-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" /></svg>
                        {:else}
                          <span class="h-1.5 w-1.5 rounded-full bg-white"></span>
                        {/if}
                      </span>
                    {:else}
                      <span class="inline-block h-5 w-5 rounded-full bg-neutral-100"></span>
                    {/if}
                  </td>

                  <!-- Stage 2: PR -->
                  <td class="px-2 py-3 text-center">
                    {#if item.pr_number}
                      <span class="inline-flex items-center justify-center h-5 w-5 rounded-full {si > 1 ? 'bg-emerald-500' : si === 1 ? 'bg-indigo-600 ring-2 ring-indigo-200' : 'bg-emerald-500'}">
                        {#if si > 1}
                          <svg class="h-3 w-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" /></svg>
                        {:else}
                          <span class="h-1.5 w-1.5 rounded-full bg-white"></span>
                        {/if}
                      </span>
                    {:else}
                      <span class="inline-block h-5 w-5 rounded-full bg-neutral-100 border border-neutral-200"></span>
                    {/if}
                  </td>

                  <!-- Stage 3: RFQ -->
                  <td class="px-2 py-3 text-center">
                    {#if item.rfq_number}
                      <span class="inline-flex items-center justify-center h-5 w-5 rounded-full {si > 2 ? 'bg-emerald-500' : si === 2 ? 'bg-indigo-600 ring-2 ring-indigo-200' : 'bg-emerald-500'}">
                        {#if si > 2}
                          <svg class="h-3 w-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" /></svg>
                        {:else}
                          <span class="h-1.5 w-1.5 rounded-full bg-white"></span>
                        {/if}
                      </span>
                    {:else}
                      <span class="inline-block h-5 w-5 rounded-full bg-neutral-100 border border-neutral-200"></span>
                    {/if}
                  </td>

                  <!-- Stage 4: PO -->
                  <td class="px-2 py-3 text-center">
                    {#if item.po_number}
                      <span class="inline-flex items-center justify-center h-5 w-5 rounded-full bg-emerald-500">
                        <svg class="h-3 w-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" /></svg>
                      </span>
                    {:else}
                      <span class="inline-block h-5 w-5 rounded-full bg-neutral-100 border border-neutral-200"></span>
                    {/if}
                  </td>

                  <td class="px-4 py-3 text-right text-[10px] text-neutral-400">{timeAgo(item.created_at)}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </section>
    {/if}

  {/if}
</div>

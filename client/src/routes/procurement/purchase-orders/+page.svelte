<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { useAutoRefresh } from "$lib/realtime.svelte";
  import { fetchBudgetLineOptions, fetchCostCodeOptions, type BudgetLineOption } from "$lib/procurement";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import PODetailDrawer from "./PODetailDrawer.svelte";
  import type {
    PurchaseOrderListItem,
    PurchaseOrder,
    VendorListItem,
    ProjectListItem,
    PropertyListItem,
    MasterDataEntry,
    PaginatedResponse,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let data = $state<PurchaseOrderListItem[]>([]);
  let totalCount = $state(0);
  let currentPage = $state(1);
  let searchQuery = $state("");
  let statusFilter = $state("");
  let vendorFilter = $state("");
  let loading = $state(true);
  let vendors = $state<VendorListItem[]>([]);
  let projects = $state<ProjectListItem[]>([]);
  let properties = $state<PropertyListItem[]>([]);
  let budgetLines = $state<BudgetLineOption[]>([]);
  let costCodes = $state<MasterDataEntry[]>([]);

  // Detail drawer
  let detailDrawerOpen = $state(false);
  let selectedPoId = $state<number | null>(null);

  // Create drawer
  let showCreateDrawer = $state(false);
  let createForm = $state(defaultCreateForm());
  let createErrors = $state<Record<string, string[]>>({});
  let savingPO = $state(false);

  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  function defaultCreateForm() {
    return {
      vendor: "",
      project: "",
      property: "",
      issue_date: "",
      expected_delivery_date: "",
      budget_line_item: "",
      cost_code: "",
      budget_code: "",
      delivery_address: "",
      payment_terms: "",
      notes: "",
    };
  }

  function createFieldError(field: string): string {
    return createErrors[field]?.[0] ?? "";
  }

  function resetCreateForm() {
    createForm = defaultCreateForm();
    createErrors = {};
  }

  // ── Dev Fill ────────────────────────────────────────────────────────
  const PO_SAMPLES = [
    {
      budget_code: "CAPEX-2026-001",
      issue_date: "2026-03-15",
      expected_delivery_date: "2026-04-20",
      payment_terms: "Net 30 — 60% on delivery, 40% after inspection & commissioning",
      delivery_address: "Block A Site Office\nPlot 14, Lekki Phase 2\nLagos, Nigeria",
      notes: "Structural steel for podium frame — columns, beams, and bracing per SE dwg rev. D. Delivery in 2 tranches: columns by Apr 5, beams/bracing by Apr 20. Mill certificates required per EN 10204 3.1.",
    },
    {
      budget_code: "CAPEX-2026-004",
      issue_date: "2026-03-20",
      expected_delivery_date: "2026-05-10",
      payment_terms: "Net 45 — 100% upon satisfactory goods receipt",
      delivery_address: "Central Warehouse Gate 3\n12 Industrial Avenue, Ikeja\nLagos, Nigeria",
      notes: "HVAC package for Tower B floors 1-8. Includes split units, ducting, and control panels. Vendor to provide installation supervision for 5 days on-site. Warranty: 24 months from commissioning.",
    },
    {
      budget_code: "OPEX-2026-012",
      issue_date: "2026-03-18",
      expected_delivery_date: "2026-04-05",
      payment_terms: "Net 14 — payment on delivery",
      delivery_address: "Abuja Phase 2 Site\nPlot 7B, Katampe Extension\nAbuja, Nigeria",
      notes: "Monthly consumables restock: PPE (hard hats, gloves, vests), first-aid supplies, and site cleaning materials. Standing order — auto-renew monthly unless cancelled 7 days prior.",
    },
    {
      budget_code: "CAPEX-2026-009",
      issue_date: "2026-03-22",
      expected_delivery_date: "2026-06-15",
      payment_terms: "Milestone — 30% advance, 40% on shipment, 30% on acceptance",
      delivery_address: "Lekki Residential Tower Site\nPlot 22, Admiralty Way\nLekki Phase 1, Lagos",
      notes: "Curtain wall glazing system — 1,200 m² unitised panels with double-glazed low-E units. Factory acceptance test required before shipment. Vendor arranges freight; buyer covers customs clearance.",
    },
  ];

  let devIdx = 0;
  function devFillCreateForm() {
    const sample = PO_SAMPLES[devIdx % PO_SAMPLES.length];
    devIdx++;
    createForm = {
      ...createForm,
      budget_code: sample.budget_code,
      issue_date: sample.issue_date,
      expected_delivery_date: sample.expected_delivery_date,
      payment_terms: sample.payment_terms,
      delivery_address: sample.delivery_address,
      notes: sample.notes,
    };
  }

  // ── CRUD ────────────────────────────────────────────────────────────
  async function handleCreatePO(e: Event) {
    e.preventDefault();
    createErrors = {};
    savingPO = true;

    try {
      const payload: Record<string, unknown> = {
        vendor: createForm.vendor ? Number(createForm.vendor) : null,
        project: createForm.project ? Number(createForm.project) : null,
        property: createForm.property ? Number(createForm.property) : null,
        issue_date: createForm.issue_date || null,
        expected_delivery_date: createForm.expected_delivery_date || null,
        budget_line_item: createForm.budget_line_item ? Number(createForm.budget_line_item) : null,
        cost_code: createForm.cost_code,
        budget_code: createForm.budget_code,
        delivery_address: createForm.delivery_address,
        payment_terms: createForm.payment_terms,
        notes: createForm.notes,
      };
      const result = await api.post<PurchaseOrder>("/procurement/purchase-orders/", payload);
      toast.success("Purchase order created", `"${result.po_number}" has been added`);
      showCreateDrawer = false;
      resetCreateForm();
      fetchPurchaseOrders();
    } catch (err) {
      if (err instanceof ApiError) {
        createErrors = err.fieldErrors;
        toast.error("Validation error", "Please fix the highlighted fields below");
      } else {
        toast.error("Something went wrong", "Could not create the purchase order");
      }
    }
    savingPO = false;
  }

  // ── Pagination ──────────────────────────────────────────────────────
  const PAGE_SIZE = 25;
  const totalPages = $derived(Math.ceil(totalCount / PAGE_SIZE));
  const startItem = $derived(totalCount === 0 ? 0 : (currentPage - 1) * PAGE_SIZE + 1);
  const endItem = $derived(Math.min(currentPage * PAGE_SIZE, totalCount));

  function pageNumbers(current: number, total: number): (number | "...")[] {
    if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
    const pages: (number | "...")[] = [1];
    if (current > 3) pages.push("...");
    const start = Math.max(2, current - 1);
    const end = Math.min(total - 1, current + 1);
    for (let i = start; i <= end; i++) pages.push(i);
    if (current < total - 2) pages.push("...");
    pages.push(total);
    return pages;
  }

  // ── Data fetching ───────────────────────────────────────────────────
  async function fetchVendors() {
    try {
      const res = await api.get<PaginatedResponse<VendorListItem>>("/procurement/vendors/", { page_size: "200" });
      vendors = res.results;
    } catch {
      vendors = [];
    }
  }

  async function fetchProjects() {
    try {
      const res = await api.get<PaginatedResponse<ProjectListItem>>("/projects/", { page_size: "200" });
      projects = res.results;
    } catch {
      projects = [];
    }
  }

  async function fetchProperties() {
    try {
      const res = await api.get<PaginatedResponse<PropertyListItem>>("/properties/", { page_size: "200" });
      properties = res.results;
    } catch {
      properties = [];
    }
  }

  async function fetchPurchaseOrders() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage) };
      if (searchQuery) params.search = searchQuery;
      if (statusFilter) params.status = statusFilter;
      if (vendorFilter) params.vendor = vendorFilter;

      const res = await api.get<PaginatedResponse<PurchaseOrderListItem>>("/procurement/purchase-orders/", params);
      data = res.results;
      totalCount = res.count;
    } catch {
      data = [];
      totalCount = 0;
    }
    loading = false;
  }

  $effect(() => {
    fetchVendors();
    fetchProjects();
    fetchProperties();
    Promise.all([
      fetchBudgetLineOptions().then((rows) => (budgetLines = rows)),
      fetchCostCodeOptions().then((rows) => (costCodes = rows)),
    ]);
  });

  $effect(() => {
    void searchQuery;
    void statusFilter;
    void vendorFilter;
    void currentPage;
    fetchPurchaseOrders();
  });

  let searchTimeout: ReturnType<typeof setTimeout>;
  function onSearchInput(e: Event) {
    clearTimeout(searchTimeout);
    const value = (e.target as HTMLInputElement).value;
    searchTimeout = setTimeout(() => {
      searchQuery = value;
      currentPage = 1;
    }, 300);
  }

  function formatCurrency(value: string | null): string {
    if (!value) return "\u2014";
    return currency.formatCompact(value);
  }

  function formatDate(value: string | null): string {
    if (!value) return "\u2014";
    return new Date(value).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  }

  function openDetail(id: number) {
    selectedPoId = id;
    detailDrawerOpen = true;
  }

  useAutoRefresh(["PurchaseOrder", "GoodsReceipt"], fetchPurchaseOrders);
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-700">Procurement</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Purchase Orders</h1>
      <p class="text-sm text-neutral-400 mt-1">Manage vendor purchase orders</p>
    </div>
    <button
      onclick={() => { resetCreateForm(); showCreateDrawer = true; }}
      class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg hover:bg-neutral-800 text-sm font-medium transition-colors"
    >
      + New PO
    </button>
  </div>

  <!-- Filters -->
  <div class="flex gap-3 items-center">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
      </svg>
      <input
        type="text"
        placeholder="Search purchase orders..."
        oninput={onSearchInput}
        class="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
               focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent
               placeholder:text-neutral-400"
      />
    </div>
    <select
      bind:value={statusFilter}
      onchange={() => (currentPage = 1)}
      class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600
             focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
    >
      <option value="">All Statuses</option>
      <option value="draft">Draft</option>
      <option value="approved">Approved</option>
      <option value="issued">Issued</option>
      <option value="partially_received">Partially Received</option>
      <option value="received">Received</option>
      <option value="cancelled">Cancelled</option>
    </select>
    <select
      bind:value={vendorFilter}
      onchange={() => (currentPage = 1)}
      class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600
             focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
    >
      <option value="">All Vendors</option>
      {#each vendors as vendor}
        <option value={String(vendor.id)}>{vendor.name}</option>
      {/each}
    </select>
  </div>

  <!-- Table -->
  <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
    {#if loading}
      <div class="p-16 text-center">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
        <p class="mt-3 text-sm text-neutral-400">Loading purchase orders...</p>
      </div>
    {:else if data.length === 0}
      <div class="p-16 text-center">
        <svg class="w-12 h-12 mx-auto text-neutral-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
        </svg>
        <p class="mt-4 text-sm font-medium text-neutral-900">No purchase orders found</p>
        <p class="mt-1 text-sm text-neutral-400">Get started by creating your first purchase order.</p>
        <button
          onclick={() => { resetCreateForm(); showCreateDrawer = true; }}
          class="inline-block mt-4 px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors"
        >
          + New PO
        </button>
      </div>
    {:else}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200">
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">PO #</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Vendor</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Issue Date</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Expected Delivery</th>
            <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Total</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">PR #</th>
            <th class="px-5 py-3.5 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Received</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each data as po}
            <tr
              class="hover:bg-neutral-50 cursor-pointer transition-colors"
              onclick={() => openDetail(po.id)}
            >
              <td class="px-5 py-4">
                <span class="font-medium text-neutral-900">{po.po_number}</span>
              </td>
              <td class="px-5 py-4 text-neutral-500">{po.vendor_name}</td>
              <td class="px-5 py-4">
                <StatusBadge status={po.status} label={po.status === "partially_received" ? "Partial" : undefined} />
              </td>
              <td class="px-5 py-4 text-neutral-500">{formatDate(po.issue_date)}</td>
              <td class="px-5 py-4 text-neutral-500">{formatDate(po.expected_delivery_date)}</td>
              <td class="px-5 py-4 text-right text-neutral-900 tabular-nums">{formatCurrency(po.total_amount)}</td>
              <td class="px-5 py-4">
                {#if po.requisition}
                  <a
                    href="/procurement/requisitions/{po.requisition}"
                    onclick={(e) => e.stopPropagation()}
                    class="text-blue-600 hover:text-blue-800 hover:underline text-sm font-medium"
                  >
                    {po.requisition_number}
                  </a>
                {:else}
                  <span class="text-neutral-300">&mdash;</span>
                {/if}
              </td>
              <td class="px-5 py-4 text-center">
                {#if po.is_fully_received}
                  <span class="inline-block w-2.5 h-2.5 rounded-full bg-emerald-500" title="Fully received"></span>
                {:else if po.status === "partially_received"}
                  <span class="inline-block w-2.5 h-2.5 rounded-full bg-amber-400" title="Partially received"></span>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>

  <!-- Pagination -->
  {#if totalCount > 0}
    <div class="flex items-center justify-between">
      <p class="text-sm text-neutral-400">
        Showing <span class="font-medium text-neutral-600">{startItem}&ndash;{endItem}</span> of
        <span class="font-medium text-neutral-600">{totalCount}</span>
        {totalCount === 1 ? "purchase order" : "purchase orders"}
      </p>

      {#if totalPages > 1}
        <div class="flex items-center gap-1">
          <button
            onclick={() => currentPage--}
            disabled={currentPage <= 1}
            class="w-9 h-9 flex items-center justify-center border border-neutral-200 rounded-lg text-neutral-500
                   hover:bg-neutral-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            aria-label="Previous page"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
            </svg>
          </button>

          {#each pageNumbers(currentPage, totalPages) as pg}
            {#if pg === "..."}
              <span class="w-9 h-9 flex items-center justify-center text-xs text-neutral-300">...</span>
            {:else}
              <button
                onclick={() => (currentPage = pg)}
                class="w-9 h-9 flex items-center justify-center rounded-lg text-sm font-medium transition-colors
                       {currentPage === pg
                         ? 'bg-neutral-900 text-white'
                         : 'text-neutral-500 hover:bg-neutral-100'}"
              >
                {pg}
              </button>
            {/if}
          {/each}

          <button
            onclick={() => currentPage++}
            disabled={currentPage >= totalPages}
            class="w-9 h-9 flex items-center justify-center border border-neutral-200 rounded-lg text-neutral-500
                   hover:bg-neutral-50 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            aria-label="Next page"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
            </svg>
          </button>
        </div>
      {/if}
    </div>
  {/if}
</div>

<!-- Detail Drawer -->
<PODetailDrawer
  open={detailDrawerOpen}
  poId={selectedPoId}
  onclose={() => (detailDrawerOpen = false)}
  onupdated={fetchPurchaseOrders}
/>

<!-- Create Drawer -->
{#if showCreateDrawer}
  <div
    class="fixed inset-0 bg-black/30 z-998 transition-opacity"
    onclick={() => { showCreateDrawer = false; resetCreateForm(); }}
    role="presentation"
  ></div>

  <div
    class="fixed inset-y-0 right-0 z-999 w-full max-w-[560px] bg-white shadow-2xl
           flex flex-col overflow-hidden animate-slide-in"
    role="dialog"
    aria-modal="true"
    aria-label="New Purchase Order"
  >
    <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200 bg-neutral-50/60">
      <div>
        <h2 class="text-base font-semibold text-neutral-900">New Purchase Order</h2>
        <p class="text-xs text-neutral-500 mt-0.5">Create a new purchase order for a vendor</p>
      </div>
      <button
        onclick={() => { showCreateDrawer = false; resetCreateForm(); }}
        class="w-8 h-8 flex items-center justify-center rounded-lg text-neutral-400 hover:text-neutral-900 hover:bg-neutral-100 transition-colors"
        aria-label="Close"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div class="flex-1 overflow-y-auto">
      <form onsubmit={handleCreatePO} class="p-6 space-y-4">
        <!-- Vendor -->
        <label>
          <span class="mb-1 block text-xs font-semibold text-neutral-600">Vendor *</span>
          <select
            bind:value={createForm.vendor}
            class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"
          >
            <option value="">Select a vendor</option>
            {#each vendors as vendor}
              <option value={String(vendor.id)}>{vendor.name}</option>
            {/each}
          </select>
          {#if createFieldError("vendor")}<p class="mt-1 text-xs text-red-500">{createFieldError("vendor")}</p>{/if}
        </label>

        <!-- Project + Property -->
        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="mb-1 block text-xs font-semibold text-neutral-600">Project</span>
            <select bind:value={createForm.project} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
              <option value="">None</option>
              {#each projects as project}
                <option value={String(project.id)}>{project.name}</option>
              {/each}
            </select>
          </label>
          <label>
            <span class="mb-1 block text-xs font-semibold text-neutral-600">Property</span>
            <select bind:value={createForm.property} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
              <option value="">None</option>
              {#each properties as property}
                <option value={String(property.id)}>{property.name}</option>
              {/each}
            </select>
          </label>
        </div>

        <!-- Budget Line + Cost Code -->
        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="mb-1 block text-xs font-semibold text-neutral-600">Budget Line</span>
            <select bind:value={createForm.budget_line_item} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
              <option value="">None</option>
              {#each budgetLines as line}
                <option value={String(line.id)}>{line.label}</option>
              {/each}
            </select>
          </label>
          <label>
            <span class="mb-1 block text-xs font-semibold text-neutral-600">Cost Code</span>
            <select bind:value={createForm.cost_code} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
              <option value="">None</option>
              {#each costCodes as code}
                <option value={code.code}>{code.code} - {code.label}</option>
              {/each}
            </select>
          </label>
        </div>

        <label>
          <span class="mb-1 block text-xs font-semibold text-neutral-600">Budget Code</span>
          <input type="text" bind:value={createForm.budget_code} placeholder="e.g. CAPEX-2026-002" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
        </label>

        <!-- Dates -->
        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="mb-1 block text-xs font-semibold text-neutral-600">Issue Date</span>
            <DateInput bind:value={createForm.issue_date} />
            {#if createFieldError("issue_date")}<p class="mt-1 text-xs text-red-500">{createFieldError("issue_date")}</p>{/if}
          </label>
          <label>
            <span class="mb-1 block text-xs font-semibold text-neutral-600">Expected Delivery</span>
            <DateInput bind:value={createForm.expected_delivery_date} />
          </label>
        </div>

        <label>
          <span class="mb-1 block text-xs font-semibold text-neutral-600">Payment Terms</span>
          <input type="text" bind:value={createForm.payment_terms} placeholder="e.g. Net 30" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
        </label>

        <label>
          <span class="mb-1 block text-xs font-semibold text-neutral-600">Delivery Address</span>
          <textarea bind:value={createForm.delivery_address} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm resize-none" placeholder="Enter delivery address..."></textarea>
        </label>

        <label>
          <span class="mb-1 block text-xs font-semibold text-neutral-600">Notes</span>
          <textarea bind:value={createForm.notes} rows="2" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm resize-none" placeholder="Optional notes..."></textarea>
        </label>

        <!-- Actions -->
        <div class="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onclick={() => { showCreateDrawer = false; resetCreateForm(); }}
            class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
          >
            Cancel
          </button>
          {#if isDev}
            <button type="button" onclick={devFillCreateForm} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">
              Dev Fill
            </button>
          {/if}
          <button
            type="submit"
            disabled={savingPO}
            class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-50"
          >
            {savingPO ? "Creating..." : "Create Purchase Order"}
          </button>
        </div>
      </form>
    </div>
  </div>
{/if}

<style>
  @keyframes slideIn {
    from { transform: translateX(100%); }
    to   { transform: translateX(0); }
  }
  .animate-slide-in {
    animation: slideIn 0.2s ease-out;
  }
</style>

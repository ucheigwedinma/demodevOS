<script lang="ts">
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { fetchBudgetLineOptions, fetchCostCodeOptions, type BudgetLineOption } from "$lib/procurement";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import Breadcrumb from "$lib/components/Breadcrumb.svelte";
  import type {
    PurchaseOrder,
    PurchaseRequisition,
    VendorListItem,
    ProjectListItem,
    PropertyListItem,
    MasterDataEntry,
    PaginatedResponse,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  const fromPr = $derived($page.url.searchParams.get("from_pr"));

  let form = $state({
    vendor: "",
    requisition: "",
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
  });

  let errors = $state<Record<string, string[]>>({});
  let saving = $state(false);
  let vendors = $state<VendorListItem[]>([]);
  let projects = $state<ProjectListItem[]>([]);
  let properties = $state<PropertyListItem[]>([]);
  let budgetLines = $state<BudgetLineOption[]>([]);
  let costCodes = $state<MasterDataEntry[]>([]);
  let loadingPR = $state(false);
  let prDetail = $state<PurchaseRequisition | null>(null);

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

  async function fetchPRDetail(prId: string) {
    loadingPR = true;
    try {
      const pr = await api.get<PurchaseRequisition>(`/procurement/requisitions/${prId}/`);
      prDetail = pr;
      form.requisition = String(pr.id);
      if (pr.project) form.project = String(pr.project);
      if (pr.property) form.property = String(pr.property);
      if (pr.budget_line_item) form.budget_line_item = String(pr.budget_line_item);
      if (pr.cost_code) form.cost_code = pr.cost_code;
      if (pr.budget_code) form.budget_code = pr.budget_code;
    } catch {
      toast.error("Could not load requisition", "The purchase requisition could not be fetched");
      prDetail = null;
    }
    loadingPR = false;
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
    if (fromPr) {
      fetchPRDetail(fromPr);
    }
  });

  function fieldError(field: string): string {
    return errors[field]?.[0] ?? "";
  }

  function formatCurrencyCompact(value: string | number | null): string {
    if (value === null || value === "") return "\u2014";
    return currency.formatCompact(value);
  }

  async function handleSubmit(e: Event) {
    e.preventDefault();
    errors = {};
    saving = true;

    try {
      const payload: Record<string, unknown> = {
        vendor: form.vendor ? Number(form.vendor) : null,
        requisition: form.requisition ? Number(form.requisition) : null,
        project: form.project ? Number(form.project) : null,
        property: form.property ? Number(form.property) : null,
        issue_date: form.issue_date || null,
        expected_delivery_date: form.expected_delivery_date || null,
        budget_line_item: form.budget_line_item ? Number(form.budget_line_item) : null,
        cost_code: form.cost_code,
        budget_code: form.budget_code,
        delivery_address: form.delivery_address,
        payment_terms: form.payment_terms,
        notes: form.notes,
      };
      const result = await api.post<PurchaseOrder>("/procurement/purchase-orders/", payload);
      toast.success("Purchase order created", `"${result.po_number}" has been added`);
      goto(`/procurement/purchase-orders/${result.id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        errors = err.fieldErrors;
        toast.error("Validation error", "Please fix the highlighted fields below");
      } else {
        toast.error("Something went wrong", "Could not create the purchase order");
      }
    }
    saving = false;
  }
</script>

<div class="max-w-2xl">
  <Breadcrumb items={[{ label: "Procurement", href: "/procurement" }, { label: "Purchase Orders", href: "/procurement/purchase-orders" }, { label: "New Purchase Order" }]} />
  <h1 class="text-2xl font-bold text-neutral-900 mt-3 mb-8">New Purchase Order</h1>

  {#if loadingPR}
    <div class="p-16 text-center">
      <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
      <p class="mt-3 text-sm text-neutral-400">Loading requisition details...</p>
    </div>
  {:else}
    <form onsubmit={handleSubmit} class="space-y-6">
      <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-5">
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Vendor</span>
          <select
            bind:value={form.vendor}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            <option value="">Select a vendor</option>
            {#each vendors as vendor}
              <option value={String(vendor.id)}>{vendor.name}</option>
            {/each}
          </select>
          {#if fieldError("vendor")}<p class="mt-1 text-xs text-red-500">{fieldError("vendor")}</p>{/if}
        </label>

        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">
            Purchase Requisition
            {#if fromPr}
              <span class="text-neutral-400 font-normal">(linked from PR)</span>
            {:else}
              <span class="text-neutral-400 font-normal">(optional)</span>
            {/if}
          </span>
          {#if fromPr}
            <div class="flex items-center gap-2">
              <input
                type="text"
                value={prDetail ? `${prDetail.pr_number} - ${prDetail.title}` : `PR #${fromPr}`}
                readonly
                class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-neutral-50 text-neutral-600
                       focus:outline-none cursor-not-allowed"
              />
            </div>
          {:else}
            <input
              type="number"
              bind:value={form.requisition}
              placeholder="Requisition ID (optional)"
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
          {/if}
          {#if fieldError("requisition")}<p class="mt-1 text-xs text-red-500">{fieldError("requisition")}</p>{/if}
        </label>

        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Project <span class="text-neutral-400 font-normal">(optional)</span></span>
          <select
            bind:value={form.project}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            <option value="">None</option>
            {#each projects as project}
              <option value={String(project.id)}>{project.name}</option>
            {/each}
          </select>
          {#if fieldError("project")}<p class="mt-1 text-xs text-red-500">{fieldError("project")}</p>{/if}
        </label>

        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Property <span class="text-neutral-400 font-normal">(optional)</span></span>
          <select
            bind:value={form.property}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            <option value="">None</option>
            {#each properties as property}
              <option value={String(property.id)}>{property.name}</option>
            {/each}
          </select>
          {#if fieldError("property")}<p class="mt-1 text-xs text-red-500">{fieldError("property")}</p>{/if}
        </label>

        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Issue Date</span>
            <DateInput bind:value={form.issue_date} />
            {#if fieldError("issue_date")}<p class="mt-1 text-xs text-red-500">{fieldError("issue_date")}</p>{/if}
          </label>

          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Expected Delivery <span class="text-neutral-400 font-normal">(optional)</span></span>
            <DateInput bind:value={form.expected_delivery_date} />
            {#if fieldError("expected_delivery_date")}<p class="mt-1 text-xs text-red-500">{fieldError("expected_delivery_date")}</p>{/if}
          </label>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Budget Line <span class="text-neutral-400 font-normal">(optional)</span></span>
            <select
              bind:value={form.budget_line_item}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            >
              <option value="">None</option>
              {#each budgetLines as line}
                <option value={String(line.id)}>{line.label}</option>
              {/each}
            </select>
            {#if fieldError("budget_line_item")}<p class="mt-1 text-xs text-red-500">{fieldError("budget_line_item")}</p>{/if}
          </label>

          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Cost Code <span class="text-neutral-400 font-normal">(optional)</span></span>
            <select
              bind:value={form.cost_code}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            >
              <option value="">None</option>
              {#each costCodes as code}
                <option value={code.code}>{code.code} - {code.label}</option>
              {/each}
            </select>
            {#if fieldError("cost_code")}<p class="mt-1 text-xs text-red-500">{fieldError("cost_code")}</p>{/if}
          </label>
        </div>

        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Budget Code <span class="text-neutral-400 font-normal">(optional)</span></span>
          <input
            type="text"
            bind:value={form.budget_code}
            placeholder="e.g. CAPEX-2026-002"
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          />
          {#if fieldError("budget_code")}<p class="mt-1 text-xs text-red-500">{fieldError("budget_code")}</p>{/if}
        </label>

        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Delivery Address <span class="text-neutral-400 font-normal">(optional)</span></span>
          <textarea
            bind:value={form.delivery_address}
            rows={3}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white resize-none
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            placeholder="Enter delivery address..."
          ></textarea>
          {#if fieldError("delivery_address")}<p class="mt-1 text-xs text-red-500">{fieldError("delivery_address")}</p>{/if}
        </label>

        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Payment Terms <span class="text-neutral-400 font-normal">(optional)</span></span>
          <input
            type="text"
            bind:value={form.payment_terms}
            placeholder="e.g. Net 30"
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          />
          {#if fieldError("payment_terms")}<p class="mt-1 text-xs text-red-500">{fieldError("payment_terms")}</p>{/if}
        </label>

        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Notes <span class="text-neutral-400 font-normal">(optional)</span></span>
          <textarea
            bind:value={form.notes}
            rows={3}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white resize-none
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            placeholder="Optional notes..."
          ></textarea>
          {#if fieldError("notes")}<p class="mt-1 text-xs text-red-500">{fieldError("notes")}</p>{/if}
        </label>
      </div>

      {#if prDetail && prDetail.items.length > 0}
        <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-4">
          <h2 class="text-sm font-semibold text-neutral-900">Items from Requisition</h2>
          <p class="text-xs text-neutral-400">These items will be used to pre-populate line items after the PO is created.</p>
          <div class="overflow-hidden rounded-lg border border-neutral-200">
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b border-neutral-200 bg-neutral-50">
                  <th class="px-4 py-2.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Description</th>
                  <th class="px-4 py-2.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Qty</th>
                  <th class="px-4 py-2.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Unit</th>
                  <th class="px-4 py-2.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Est. Price</th>
                  <th class="px-4 py-2.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Est. Amount</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100">
                {#each prDetail.items as item}
                  <tr>
                    <td class="px-4 py-3 text-neutral-700">{item.description}</td>
                    <td class="px-4 py-3 text-right text-neutral-600 tabular-nums">{item.quantity}</td>
                    <td class="px-4 py-3 text-neutral-500">{item.unit_of_measure}</td>
                    <td class="px-4 py-3 text-right text-neutral-600 tabular-nums">{formatCurrencyCompact(item.estimated_unit_price)}</td>
                    <td class="px-4 py-3 text-right text-neutral-900 tabular-nums font-medium">{formatCurrencyCompact(item.estimated_amount)}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>
      {/if}

      <div class="flex gap-3">
        <button
          type="submit"
          disabled={saving}
          class="px-6 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium
                 hover:bg-neutral-800 disabled:opacity-50 transition-colors"
        >
          {saving ? "Creating..." : "Create Purchase Order"}
        </button>
        <a href="/procurement/purchase-orders" class="px-6 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors">
          Cancel
        </a>
      </div>
    </form>
  {/if}
</div>

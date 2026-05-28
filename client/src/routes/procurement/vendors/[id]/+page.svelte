<script lang="ts">
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import Breadcrumb from "$lib/components/Breadcrumb.svelte";
  import DocumentRecordsTable from "$lib/components/documents/DocumentRecordsTable.svelte";
  import type { Vendor, PurchaseOrderListItem, PaginatedResponse, VendorCategory, ComplianceStatus, PriceCompetitiveness } from "$lib/types";
  import { currency } from "$lib/stores/currency.svelte";

  const id = $derived($page.params.id);

  let vendor = $state<Vendor | null>(null);
  let loading = $state(true);
  let saving = $state(false);
  let errors = $state<Record<string, string[]>>({});
  let activeTab = $state<"overview" | "purchase_orders" | "documents">("overview");

  const tabs = [
    { key: "overview" as const, label: "Vendor Profile" },
    { key: "purchase_orders" as const, label: "Purchase Orders" },
    { key: "documents" as const, label: "Documents" },
  ];

  let purchaseOrders = $state<PurchaseOrderListItem[]>([]);
  let posLoading = $state(true);

  let form = $state({
    name: "",
    contact_person: "",
    email: "",
    phone: "",
    address: "",
    tax_id: "",
    notes: "",
    is_active: true,
    category: "other" as VendorCategory,
    bank_name: "",
    bank_account_number: "",
    bank_branch: "",
    performance_rating: "0",
    delivery_timeliness_score: "0",
    price_competitiveness: "average" as PriceCompetitiveness,
    compliance_status: "pending_review" as ComplianceStatus,
    is_blacklisted: false,
    blacklist_reason: "",
  });

  const categoryLabels: Record<string, string> = {
    materials: "Materials",
    contractor: "Contractor",
    consultant: "Consultant",
    other: "Other",
  };
  const categoryColors: Record<string, string> = {
    materials: "bg-blue-50 text-blue-700",
    contractor: "bg-purple-50 text-purple-700",
    consultant: "bg-cyan-50 text-cyan-700",
    other: "bg-neutral-100 text-neutral-600",
  };
  const complianceLabels: Record<string, string> = {
    compliant: "Compliant",
    non_compliant: "Non-Compliant",
    pending_review: "Pending Review",
    expired: "Expired",
  };
  const complianceColors: Record<string, string> = {
    compliant: "bg-emerald-50 text-emerald-700",
    non_compliant: "bg-red-50 text-red-700",
    pending_review: "bg-amber-50 text-amber-700",
    expired: "bg-neutral-100 text-neutral-400",
  };
  const poStatusColors: Record<string, string> = {
    draft: "bg-neutral-100 text-neutral-600",
    approved: "bg-blue-50 text-blue-700",
    issued: "bg-cyan-50 text-cyan-700",
    partially_received: "bg-amber-50 text-amber-700",
    received: "bg-emerald-50 text-emerald-700",
    cancelled: "bg-neutral-100 text-neutral-400",
  };

  async function loadVendor() {
    loading = true;
    try {
      vendor = await api.get<Vendor>(`/procurement/vendors/${id}/`);
      form = {
        name: vendor.name,
        contact_person: vendor.contact_person,
        email: vendor.email,
        phone: vendor.phone,
        address: vendor.address,
        tax_id: vendor.tax_id,
        notes: vendor.notes,
        is_active: vendor.is_active,
        category: vendor.category,
        bank_name: vendor.bank_name,
        bank_account_number: vendor.bank_account_number,
        bank_branch: vendor.bank_branch,
        performance_rating: vendor.performance_rating,
        delivery_timeliness_score: vendor.delivery_timeliness_score,
        price_competitiveness: vendor.price_competitiveness,
        compliance_status: vendor.compliance_status,
        is_blacklisted: vendor.is_blacklisted,
        blacklist_reason: vendor.blacklist_reason,
      };
    } catch {
      vendor = null;
    }
    loading = false;
  }

  async function loadPurchaseOrders() {
    posLoading = true;
    try {
      const res = await api.get<PaginatedResponse<PurchaseOrderListItem>>("/procurement/purchase-orders/", { vendor: id as string });
      purchaseOrders = res.results;
    } catch {
      purchaseOrders = [];
    }
    posLoading = false;
  }

  $effect(() => {
    void id;
    loadVendor();
    loadPurchaseOrders();
  });

  async function handleSave(e: Event) {
    e.preventDefault();
    errors = {};
    saving = true;

    try {
      vendor = await api.patch<Vendor>(`/procurement/vendors/${id}/`, form);
      toast.success("Vendor updated", `"${form.name}" has been saved`);
    } catch (err) {
      if (err instanceof ApiError) {
        errors = err.fieldErrors;
        toast.error("Validation error", "Please fix the highlighted fields below");
      } else {
        toast.error("Something went wrong", "Could not update the vendor");
      }
    }
    saving = false;
  }

  async function handleDelete() {
    if (!confirm("Are you sure you want to delete this vendor? This action cannot be undone.")) return;
    try {
      await api.delete(`/procurement/vendors/${id}/`);
      toast.success("Vendor deleted", `"${vendor?.name}" has been removed`);
      goto("/procurement/vendors");
    } catch {
      toast.error("Failed to delete", "This vendor may have associated purchase orders");
    }
  }

  function fieldError(field: string): string {
    return errors[field]?.[0] ?? "";
  }

  function formatCurrency(value: string): string {
    return currency.format(value);
  }

  function formatDate(value: string): string {
    return new Date(value).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  }

  function formatStatus(status: string): string {
    return status
      .split("_")
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");
  }
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
  </div>
{:else if !vendor}
  <div class="text-center py-24">
    <p class="text-neutral-400">Vendor not found.</p>
    <a href="/procurement/vendors" class="mt-4 inline-block text-sm font-medium text-neutral-900 hover:underline">Back to vendors</a>
  </div>
{:else}
  <div class="space-y-8">
    <!-- Header -->
    <div class="flex items-start justify-between">
      <div>
        <Breadcrumb items={[{ label: "Procurement", href: "/procurement" }, { label: "Vendors", href: "/procurement/vendors" }, { label: vendor.name }]} />
        <h1 class="text-2xl font-bold text-neutral-900 mt-3">{vendor.name}</h1>
        <div class="flex items-center gap-3 mt-2 flex-wrap">
          {#if vendor.is_active}
            <span class="inline-flex items-center gap-1.5 text-xs font-medium text-neutral-900">
              <span class="w-1.5 h-1.5 rounded-full bg-neutral-900"></span>Active
            </span>
          {:else}
            <span class="inline-flex items-center gap-1.5 text-xs font-medium text-neutral-400">
              <span class="w-1.5 h-1.5 rounded-full bg-neutral-300"></span>Inactive
            </span>
          {/if}
          <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {categoryColors[vendor.category]}">
            {categoryLabels[vendor.category]}
          </span>
          <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {complianceColors[vendor.compliance_status]}">
            {complianceLabels[vendor.compliance_status]}
          </span>
          {#if vendor.is_blacklisted}
            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-red-100 text-red-700">Blacklisted</span>
          {/if}
        </div>
      </div>
      <button
        onclick={handleDelete}
        class="px-4 py-2 border border-red-200 rounded-lg text-sm font-medium text-red-600 hover:bg-red-50 transition-colors"
      >
        Delete Vendor
      </button>
    </div>

    <div class="border-b border-neutral-200">
      <nav class="flex gap-6">
        {#each tabs as tab}
          <button
            onclick={() => (activeTab = tab.key)}
            class="pb-3 text-sm font-medium border-b-2 transition-colors -mb-px
                   {activeTab === tab.key
                     ? 'border-neutral-900 text-neutral-900'
                     : 'border-transparent text-neutral-400 hover:text-neutral-600'}"
          >
            {tab.label}
          </button>
        {/each}
      </nav>
    </div>

    {#if activeTab === "overview"}
      <!-- Edit Form -->
      <form onsubmit={handleSave} class="space-y-6 max-w-2xl">
      <!-- Contact Information -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-5">
        <h2 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Contact Information</h2>

        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Name</span>
          <input
            bind:value={form.name}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          />
          {#if fieldError("name")}<p class="mt-1 text-xs text-red-500">{fieldError("name")}</p>{/if}
        </label>

        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Contact Person <span class="text-neutral-400 font-normal">(optional)</span></span>
            <input
              bind:value={form.contact_person}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if fieldError("contact_person")}<p class="mt-1 text-xs text-red-500">{fieldError("contact_person")}</p>{/if}
          </label>

          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Email <span class="text-neutral-400 font-normal">(optional)</span></span>
            <input
              type="email"
              bind:value={form.email}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if fieldError("email")}<p class="mt-1 text-xs text-red-500">{fieldError("email")}</p>{/if}
          </label>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Phone <span class="text-neutral-400 font-normal">(optional)</span></span>
            <input
              bind:value={form.phone}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if fieldError("phone")}<p class="mt-1 text-xs text-red-500">{fieldError("phone")}</p>{/if}
          </label>

          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Tax ID <span class="text-neutral-400 font-normal">(optional)</span></span>
            <input
              bind:value={form.tax_id}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if fieldError("tax_id")}<p class="mt-1 text-xs text-red-500">{fieldError("tax_id")}</p>{/if}
          </label>
        </div>

        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Address <span class="text-neutral-400 font-normal">(optional)</span></span>
          <textarea
            bind:value={form.address}
            rows="2"
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white resize-none
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          ></textarea>
          {#if fieldError("address")}<p class="mt-1 text-xs text-red-500">{fieldError("address")}</p>{/if}
        </label>
      </div>

      <!-- Banking Information -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-5">
        <h2 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Banking Information</h2>

        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Bank Name <span class="text-neutral-400 font-normal">(optional)</span></span>
            <input
              bind:value={form.bank_name}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
              placeholder="Bank name"
            />
            {#if fieldError("bank_name")}<p class="mt-1 text-xs text-red-500">{fieldError("bank_name")}</p>{/if}
          </label>

          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Account Number <span class="text-neutral-400 font-normal">(optional)</span></span>
            <input
              bind:value={form.bank_account_number}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
              placeholder="Account number"
            />
            {#if fieldError("bank_account_number")}<p class="mt-1 text-xs text-red-500">{fieldError("bank_account_number")}</p>{/if}
          </label>
        </div>

        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Branch <span class="text-neutral-400 font-normal">(optional)</span></span>
          <input
            bind:value={form.bank_branch}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            placeholder="Branch name or code"
          />
          {#if fieldError("bank_branch")}<p class="mt-1 text-xs text-red-500">{fieldError("bank_branch")}</p>{/if}
        </label>
      </div>

      <!-- Classification -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-5">
        <h2 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Classification</h2>

        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Category</span>
            <select
              bind:value={form.category}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            >
              <option value="materials">Materials</option>
              <option value="contractor">Contractor</option>
              <option value="consultant">Consultant</option>
              <option value="other">Other</option>
            </select>
          </label>

          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Compliance Status</span>
            <select
              bind:value={form.compliance_status}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            >
              <option value="pending_review">Pending Review</option>
              <option value="compliant">Compliant</option>
              <option value="non_compliant">Non-Compliant</option>
              <option value="expired">Expired</option>
            </select>
          </label>
        </div>

        {#if vendor.approved_projects_detail && vendor.approved_projects_detail.length > 0}
          <div>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Approved Projects</span>
            <div class="flex flex-wrap gap-2">
              {#each vendor.approved_projects_detail as project}
                <a
                  href="/projects/{project.id}"
                  class="inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-medium bg-neutral-100 text-neutral-700 hover:bg-neutral-200 transition-colors"
                >
                  {project.name}
                </a>
              {/each}
            </div>
          </div>
        {/if}

        <label class="flex items-center gap-3 cursor-pointer">
          <input type="checkbox" bind:checked={form.is_active} class="w-4 h-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900" />
          <span class="text-sm text-neutral-700">Active vendor</span>
        </label>
      </div>

      <!-- Vendor Intelligence -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-5">
        <h2 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Vendor Intelligence</h2>

        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Performance Rating <span class="text-neutral-400 font-normal">(0–5)</span></span>
            <input
              type="number"
              step="0.01"
              min="0"
              max="5"
              bind:value={form.performance_rating}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if fieldError("performance_rating")}<p class="mt-1 text-xs text-red-500">{fieldError("performance_rating")}</p>{/if}
          </label>

          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Delivery Timeliness <span class="text-neutral-400 font-normal">(%)</span></span>
            <input
              type="number"
              step="0.01"
              min="0"
              max="100"
              bind:value={form.delivery_timeliness_score}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if fieldError("delivery_timeliness_score")}<p class="mt-1 text-xs text-red-500">{fieldError("delivery_timeliness_score")}</p>{/if}
          </label>
        </div>

        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Price Competitiveness</span>
          <select
            bind:value={form.price_competitiveness}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            <option value="low">Low</option>
            <option value="average">Average</option>
            <option value="high">High</option>
            <option value="premium">Premium</option>
          </select>
        </label>

        <div class="space-y-3">
          <label class="flex items-center gap-3 cursor-pointer">
            <input type="checkbox" bind:checked={form.is_blacklisted} class="w-4 h-4 rounded border-neutral-300 text-red-600 focus:ring-red-500" />
            <span class="text-sm text-neutral-700">Blacklisted</span>
          </label>

          {#if form.is_blacklisted}
            <label>
              <span class="block text-sm font-medium text-neutral-700 mb-1.5">Blacklist Reason</span>
              <textarea
                bind:value={form.blacklist_reason}
                rows="2"
                class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white resize-none
                       focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
                placeholder="Reason for blacklisting"
              ></textarea>
            </label>
          {/if}
        </div>
      </div>

      <!-- Notes -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-5">
        <h2 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Notes</h2>

        <label>
          <textarea
            bind:value={form.notes}
            rows="3"
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white resize-none
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            placeholder="Internal notes about this vendor"
          ></textarea>
        </label>
      </div>

      <div class="flex gap-3">
        <button
          type="submit"
          disabled={saving}
          class="px-6 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium
                 hover:bg-neutral-800 disabled:opacity-50 transition-colors"
        >
          {saving ? "Saving..." : "Save Changes"}
        </button>
        <a href="/procurement/vendors" class="px-6 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors">
          Cancel
        </a>
      </div>
      </form>
    {/if}

    {#if activeTab === "purchase_orders"}
      <!-- Recent Purchase Orders -->
      <div class="space-y-4">
        <h2 class="text-lg font-semibold text-neutral-900">Recent Purchase Orders</h2>

        <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
          {#if posLoading}
            <div class="p-12 text-center">
              <div class="inline-block w-5 h-5 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
              <p class="mt-2 text-sm text-neutral-400">Loading purchase orders...</p>
            </div>
          {:else if purchaseOrders.length === 0}
            <div class="p-12 text-center">
              <p class="text-sm text-neutral-400">No purchase orders for this vendor.</p>
            </div>
          {:else}
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b border-neutral-200">
                  <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">PO #</th>
                  <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
                  <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Issue Date</th>
                  <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Total</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100">
                {#each purchaseOrders as po}
                  <tr
                    class="hover:bg-neutral-50 cursor-pointer transition-colors"
                    onclick={() => goto(`/procurement/purchase-orders/${po.id}`)}
                  >
                    <td class="px-5 py-4 font-medium text-neutral-900">{po.po_number}</td>
                    <td class="px-5 py-4">
                      <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {poStatusColors[po.status] ?? 'bg-neutral-100 text-neutral-600'}">
                        {formatStatus(po.status)}
                      </span>
                    </td>
                    <td class="px-5 py-4 text-neutral-500">{formatDate(po.issue_date)}</td>
                    <td class="px-5 py-4 text-right text-neutral-900 tabular-nums">{formatCurrency(po.total_amount)}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          {/if}
        </div>
      </div>
    {/if}

    {#if activeTab === "documents"}
      <DocumentRecordsTable
        title="Vendor Documents"
        subtitle="Auto-filtered controlled documents linked to this vendor."
        query={{ vendor: Number(id) }}
        pageSize={14}
        showViewAll={true}
        viewAllHref={`/documents/repository?vendor=${id}`}
        emptyMessage="No controlled repository documents are linked to this vendor yet."
      />
    {/if}
  </div>
{/if}

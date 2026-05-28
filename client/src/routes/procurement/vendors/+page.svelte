<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { useAutoRefresh } from "$lib/realtime.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import DocumentRecordsTable from "$lib/components/documents/DocumentRecordsTable.svelte";
  import Modal from "$lib/components/Modal.svelte";
  import type {
    Vendor,
    VendorListItem,
    PaginatedResponse,
    VendorCategory,
    ComplianceStatus,
    PriceCompetitiveness,
    PurchaseOrderListItem,
    RFQListItem,
    GoodsReceiptListItem,
  } from "$lib/types";

  let data = $state<VendorListItem[]>([]);
  let totalCount = $state(0);
  let currentPage = $state(1);
  let searchQuery = $state("");
  let activeFilter = $state("");
  let categoryFilter = $state("");
  let complianceFilter = $state("");
  let blacklistFilter = $state("");
  let loading = $state(true);

  type VendorForm = {
    name: string;
    contact_person: string;
    email: string;
    phone: string;
    address: string;
    tax_id: string;
    notes: string;
    is_active: boolean;
    category: VendorCategory;
    bank_name: string;
    bank_account_number: string;
    bank_branch: string;
    performance_rating: string;
    delivery_timeliness_score: string;
    price_competitiveness: PriceCompetitiveness;
    compliance_status: ComplianceStatus;
    is_blacklisted: boolean;
    blacklist_reason: string;
  };

  function createEmptyVendorForm(): VendorForm {
    return {
      name: "",
      contact_person: "",
      email: "",
      phone: "",
      address: "",
      tax_id: "",
      notes: "",
      is_active: true,
      category: "other",
      bank_name: "",
      bank_account_number: "",
      bank_branch: "",
      performance_rating: "0",
      delivery_timeliness_score: "0",
      price_competitiveness: "average",
      compliance_status: "pending_review",
      is_blacklisted: false,
      blacklist_reason: "",
    };
  }

  function buildVendorForm(vendor: Vendor): VendorForm {
    return {
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
  }

  let showCreateModal = $state(false);
  let vendorForm = $state<VendorForm>(createEmptyVendorForm());
  let vendorErrors = $state<Record<string, string[]>>({});
  let savingVendor = $state(false);

  type VendorDrawerMode = "view" | "edit";
  let showVendorDrawer = $state(false);
  let vendorDrawerMode = $state<VendorDrawerMode>("view");
  let drawerVendor = $state<Vendor | null>(null);
  let drawerLoading = $state(false);
  let drawerSaving = $state(false);
  let drawerErrors = $state<Record<string, string[]>>({});
  let drawerForm = $state<VendorForm>(createEmptyVendorForm());
  type VendorDrawerTab =
    | "overview"
    | "purchase_orders"
    | "rfqs"
    | "goods_receipts"
    | "documents";
  let vendorDrawerTab = $state<VendorDrawerTab>("overview");
  let drawerAssociationsLoading = $state(false);
  let drawerPurchaseOrders = $state<PurchaseOrderListItem[]>([]);
  let drawerRfqs = $state<RFQListItem[]>([]);
  let drawerGoodsReceipts = $state<GoodsReceiptListItem[]>([]);

  const isDev =
    typeof window !== "undefined" &&
    ["localhost", "127.0.0.1"].includes(window.location.hostname);
  const VENDOR_SAMPLES: VendorForm[] = [
    {
      name: "Lafarge Africa PLC",
      contact_person: "Adebayo Ogunlade",
      email: "a.ogunlade@lafarge-africa.com",
      phone: "+234 812 345 6789",
      address: "27B Gerrard Road, Ikoyi, Lagos, Nigeria",
      tax_id: "TIN-1234567890",
      notes:
        "Preferred supplier for ready-mix concrete and cement. 30-day payment terms agreed.",
      is_active: true,
      category: "materials",
      bank_name: "First Bank of Nigeria",
      bank_account_number: "2034567890",
      bank_branch: "Marina, Lagos",
      performance_rating: "4",
      delivery_timeliness_score: "88",
      price_competitiveness: "average",
      compliance_status: "compliant",
      is_blacklisted: false,
      blacklist_reason: "",
    },
    {
      name: "Kier Construction Ltd",
      contact_person: "James Whitfield",
      email: "j.whitfield@kier.co.uk",
      phone: "+44 20 7340 5100",
      address: "Tempsford Hall, Sandy, Bedfordshire SG19 2BD, United Kingdom",
      tax_id: "GB-987654321",
      notes:
        "Tier-1 main contractor. Framework agreement in place for projects above £5m.",
      is_active: true,
      category: "contractor",
      bank_name: "Barclays Bank",
      bank_account_number: "30-91-76 / 12345678",
      bank_branch: "Canary Wharf, London",
      performance_rating: "5",
      delivery_timeliness_score: "94",
      price_competitiveness: "high",
      compliance_status: "compliant",
      is_blacklisted: false,
      blacklist_reason: "",
    },
    {
      name: "Arup Group",
      contact_person: "Mei-Lin Chen",
      email: "mei-lin.chen@arup.com",
      phone: "+852 2268 3111",
      address:
        "Level 5, Festival Walk, 80 Tat Chee Avenue, Kowloon Tong, Hong Kong",
      tax_id: "HK-5566778899",
      notes:
        "Structural and MEP engineering consultants. Retained for high-rise projects.",
      is_active: true,
      category: "consultant",
      bank_name: "HSBC",
      bank_account_number: "400-123456-001",
      bank_branch: "Central, Hong Kong",
      performance_rating: "5",
      delivery_timeliness_score: "91",
      price_competitiveness: "premium",
      compliance_status: "compliant",
      is_blacklisted: false,
      blacklist_reason: "",
    },
    {
      name: "Al Futtaim Building Materials",
      contact_person: "Khalid Al Muhairi",
      email: "k.almuhairi@alfuttaim.ae",
      phone: "+971 4 213 6000",
      address: "Dubai Festival City, Al Rebat Street, Dubai, UAE",
      tax_id: "TRN-300012345600003",
      notes:
        "Steel reinforcement and façade cladding supplier. Bonded warehouse in JAFZA.",
      is_active: true,
      category: "materials",
      bank_name: "Emirates NBD",
      bank_account_number: "1012345678901",
      bank_branch: "Deira, Dubai",
      performance_rating: "3",
      delivery_timeliness_score: "76",
      price_competitiveness: "low",
      compliance_status: "pending_review",
      is_blacklisted: false,
      blacklist_reason: "",
    },
  ];

  let vendorDevIdx = 0;

  function devFillVendor() {
    const sample = VENDOR_SAMPLES[vendorDevIdx % VENDOR_SAMPLES.length];
    vendorDevIdx++;
    vendorForm = { ...sample };
  }

  const PAGE_SIZE = 25;
  const totalPages = $derived(Math.ceil(totalCount / PAGE_SIZE));
  const startItem = $derived((currentPage - 1) * PAGE_SIZE + 1);
  const endItem = $derived(Math.min(currentPage * PAGE_SIZE, totalCount));

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
    pending_review: "Pending",
    expired: "Expired",
  };
  const complianceColors: Record<string, string> = {
    compliant: "bg-emerald-50 text-emerald-700",
    non_compliant: "bg-red-50 text-red-700",
    pending_review: "bg-amber-50 text-amber-700",
    expired: "bg-neutral-100 text-neutral-400",
  };

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

  async function fetchVendors() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage) };
      if (searchQuery) params.search = searchQuery;
      if (activeFilter) params.is_active = activeFilter;
      if (categoryFilter) params.category = categoryFilter;
      if (complianceFilter) params.compliance_status = complianceFilter;
      if (blacklistFilter) params.is_blacklisted = blacklistFilter;

      const res = await api.get<PaginatedResponse<VendorListItem>>(
        "/procurement/vendors/",
        params,
      );
      data = res.results;
      totalCount = res.count;
    } catch {
      data = [];
      totalCount = 0;
    }
    loading = false;
  }

  $effect(() => {
    void searchQuery;
    void activeFilter;
    void categoryFilter;
    void complianceFilter;
    void blacklistFilter;
    void currentPage;
    fetchVendors();
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

  function fieldError(field: string): string {
    return vendorErrors[field]?.[0] ?? "";
  }

  function resetForm() {
    vendorForm = createEmptyVendorForm();
    vendorErrors = {};
  }

  function drawerFieldError(field: string): string {
    return drawerErrors[field]?.[0] ?? "";
  }

  function syncVendorRow(updatedVendor: Vendor) {
    data = data.map((row) =>
      row.id === updatedVendor.id ? { ...row, ...updatedVendor } : row,
    );
  }

  function formatDate(value: string | null | undefined): string {
    if (!value) return "—";
    return new Date(value).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  function formatStatus(status: string): string {
    return status
      .split("_")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  }

  async function loadVendorAssociations(vendorId: number) {
    drawerAssociationsLoading = true;
    drawerPurchaseOrders = [];
    drawerRfqs = [];
    drawerGoodsReceipts = [];

    try {
      const [poRes, rfqRes] = await Promise.all([
        api
          .get<PaginatedResponse<PurchaseOrderListItem>>(
            "/procurement/purchase-orders/",
            {
              vendor: String(vendorId),
              page_size: "8",
              ordering: "-created_at",
            },
          )
          .catch(() => ({ results: [] as PurchaseOrderListItem[] })),
        api
          .get<PaginatedResponse<RFQListItem>>("/procurement/rfqs/", {
            selected_vendor: String(vendorId),
            page_size: "8",
            ordering: "-created_at",
          })
          .catch(() => ({ results: [] as RFQListItem[] })),
      ]);

      drawerPurchaseOrders = poRes.results;
      drawerRfqs = rfqRes.results;

      const grnBatches = await Promise.all(
        poRes.results.slice(0, 8).map((purchaseOrder) =>
          api
            .get<PaginatedResponse<GoodsReceiptListItem>>(
              `/procurement/purchase-orders/${purchaseOrder.id}/goods-receipts/`,
              { page_size: "8" },
            )
            .then((response) => response.results)
            .catch(() => [] as GoodsReceiptListItem[]),
        ),
      );

      const grnMap = new Map<number, GoodsReceiptListItem>();
      for (const batch of grnBatches) {
        for (const grn of batch) {
          grnMap.set(grn.id, grn);
        }
      }
      drawerGoodsReceipts = Array.from(grnMap.values()).sort((left, right) => {
        return (
          new Date(right.received_date).getTime() -
          new Date(left.received_date).getTime()
        );
      });
    } finally {
      drawerAssociationsLoading = false;
    }
  }

  async function openVendorDrawer(vendorId: number, mode: VendorDrawerMode) {
    showVendorDrawer = true;
    vendorDrawerMode = mode;
    vendorDrawerTab = "overview";
    drawerLoading = true;
    drawerErrors = {};
    drawerVendor = null;
    drawerForm = createEmptyVendorForm();

    try {
      const vendor = await api.get<Vendor>(`/procurement/vendors/${vendorId}/`);
      drawerVendor = vendor;
      drawerForm = buildVendorForm(vendor);
      void loadVendorAssociations(vendorId);
    } catch {
      closeVendorDrawer();
      toast.error("Could not load vendor", "Please try again.");
    } finally {
      drawerLoading = false;
    }
  }

  function closeVendorDrawer() {
    showVendorDrawer = false;
    vendorDrawerMode = "view";
    drawerVendor = null;
    drawerLoading = false;
    drawerSaving = false;
    drawerErrors = {};
    drawerForm = createEmptyVendorForm();
    vendorDrawerTab = "overview";
    drawerAssociationsLoading = false;
    drawerPurchaseOrders = [];
    drawerRfqs = [];
    drawerGoodsReceipts = [];
  }

  function openDrawerEditMode() {
    if (!drawerVendor) return;
    vendorDrawerMode = "edit";
    drawerErrors = {};
    drawerForm = buildVendorForm(drawerVendor);
  }

  async function handleVendorUpdate(event: Event) {
    event.preventDefault();
    if (!drawerVendor) return;

    drawerErrors = {};
    drawerSaving = true;

    try {
      const updated = await api.patch<Vendor>(
        `/procurement/vendors/${drawerVendor.id}/`,
        drawerForm,
      );
      drawerVendor = updated;
      drawerForm = buildVendorForm(updated);
      vendorDrawerMode = "view";
      syncVendorRow(updated);
      toast.success("Vendor updated", `"${updated.name}" has been saved`);
      void fetchVendors();
    } catch (err) {
      if (err instanceof ApiError) {
        drawerErrors = err.fieldErrors;
        toast.error(
          "Validation error",
          "Please fix the highlighted fields below",
        );
      } else {
        toast.error("Something went wrong", "Could not update the vendor");
      }
    } finally {
      drawerSaving = false;
    }
  }

  async function handleVendorDelete(
    vendor: Pick<VendorListItem, "id" | "name">,
  ) {
    if (
      !confirm(
        `Are you sure you want to delete "${vendor.name}"? This action cannot be undone.`,
      )
    )
      return;

    try {
      await api.delete(`/procurement/vendors/${vendor.id}/`);
      toast.success("Vendor deleted", `"${vendor.name}" has been removed`);

      if (drawerVendor?.id === vendor.id) {
        closeVendorDrawer();
      }

      if (data.length === 1 && currentPage > 1) {
        currentPage -= 1;
      } else {
        void fetchVendors();
      }
    } catch {
      toast.error(
        "Failed to delete",
        "This vendor may have associated purchase orders",
      );
    }
  }

  async function handleCreateVendor(e: Event) {
    e.preventDefault();
    vendorErrors = {};
    savingVendor = true;

    try {
      await api.post("/procurement/vendors/", vendorForm);
      toast.success("Vendor created", `"${vendorForm.name}" has been added`);
      showCreateModal = false;
      resetForm();
      fetchVendors();
    } catch (err) {
      if (err instanceof ApiError) {
        vendorErrors = err.fieldErrors;
        toast.error(
          "Validation error",
          "Please fix the highlighted fields below",
        );
      } else {
        toast.error("Something went wrong", "Could not create the vendor");
      }
    }
    savingVendor = false;
  }

  useAutoRefresh("Vendor", fetchVendors);
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <p
        class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-700"
      >
        Procurement
      </p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">
        Vendors
      </h1>
      <p class="text-sm text-neutral-400 mt-1">
        Manage your approved vendor directory
      </p>
    </div>
    <button
      onclick={() => (showCreateModal = true)}
      class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg hover:bg-neutral-800 text-sm font-medium transition-colors"
    >
      + New Vendor
    </button>
  </div>

  <!-- Filters -->
  <div class="flex gap-3 items-center flex-wrap">
    <div class="relative flex-1 max-w-sm">
      <svg
        class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        stroke-width="1.5"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
        />
      </svg>
      <input
        type="text"
        placeholder="Search vendors..."
        oninput={onSearchInput}
        class="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
               focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent
               placeholder:text-neutral-400"
      />
    </div>
    <select
      bind:value={categoryFilter}
      onchange={() => (currentPage = 1)}
      class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600
             focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
    >
      <option value="">All Categories</option>
      <option value="materials">Materials</option>
      <option value="contractor">Contractor</option>
      <option value="consultant">Consultant</option>
      <option value="other">Other</option>
    </select>
    <select
      bind:value={complianceFilter}
      onchange={() => (currentPage = 1)}
      class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600
             focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
    >
      <option value="">All Compliance</option>
      <option value="compliant">Compliant</option>
      <option value="non_compliant">Non-Compliant</option>
      <option value="pending_review">Pending Review</option>
      <option value="expired">Expired</option>
    </select>
    <select
      bind:value={activeFilter}
      onchange={() => (currentPage = 1)}
      class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600
             focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
    >
      <option value="">All Status</option>
      <option value="true">Active</option>
      <option value="false">Inactive</option>
    </select>
    <select
      bind:value={blacklistFilter}
      onchange={() => (currentPage = 1)}
      class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600
             focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
    >
      <option value="">Blacklist</option>
      <option value="false">Not Blacklisted</option>
      <option value="true">Blacklisted</option>
    </select>
  </div>

  <!-- Table -->
  <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
    {#if loading}
      <div class="p-16 text-center">
        <div
          class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"
        ></div>
        <p class="mt-3 text-sm text-neutral-400">Loading vendors...</p>
      </div>
    {:else if data.length === 0}
      <div class="p-16 text-center">
        <svg
          class="w-12 h-12 mx-auto text-neutral-300"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          stroke-width="1"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm6 3a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Zm-13.5 0a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Z"
          />
        </svg>
        <p class="mt-4 text-sm font-medium text-neutral-900">
          No vendors found
        </p>
        <p class="mt-1 text-sm text-neutral-400">
          Get started by adding your first vendor.
        </p>
        <button
          onclick={() => (showCreateModal = true)}
          class="inline-block mt-4 px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors"
        >
          + New Vendor
        </button>
      </div>
    {:else}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200">
            <th
              class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider"
              >Name</th
            >
            <th
              class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider"
              >Category</th
            >
            <th
              class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider"
              >Contact</th
            >
            <th
              class="px-5 py-3.5 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider"
              >Rating</th
            >
            <th
              class="px-5 py-3.5 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider"
              >Compliance</th
            >
            <th
              class="px-5 py-3.5 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider"
              >POs</th
            >
            <th
              class="px-5 py-3.5 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider"
              >Status</th
            >
            <th
              class="px-5 py-3.5 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider"
              >Actions</th
            >
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each data as vendor}
            <tr class="hover:bg-neutral-50 transition-colors">
              <td class="px-5 py-4">
                <div class="flex items-center gap-2">
                  <span class="font-medium text-neutral-900">{vendor.name}</span
                  >
                  {#if vendor.is_blacklisted}
                    <span
                      class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-red-100 text-red-700 uppercase tracking-wide"
                      >BL</span
                    >
                  {/if}
                </div>
              </td>
              <td class="px-5 py-4">
                <span
                  class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {categoryColors[
                    vendor.category
                  ] ?? 'bg-neutral-100 text-neutral-600'}"
                >
                  {categoryLabels[vendor.category] ?? vendor.category}
                </span>
              </td>
              <td class="px-5 py-4 text-neutral-500">
                {vendor.contact_person || vendor.email || "\u2014"}
              </td>
              <td class="px-5 py-4 text-center">
                <span class="tabular-nums text-neutral-700 font-medium"
                  >{Number(vendor.performance_rating).toFixed(1)}</span
                >
                <span class="text-neutral-300 text-xs">/5</span>
              </td>
              <td class="px-5 py-4 text-center">
                <span
                  class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {complianceColors[
                    vendor.compliance_status
                  ] ?? 'bg-neutral-100 text-neutral-600'}"
                >
                  {complianceLabels[vendor.compliance_status] ??
                    vendor.compliance_status}
                </span>
              </td>
              <td class="px-5 py-4 text-center text-neutral-500 tabular-nums"
                >{vendor.po_count}</td
              >
              <td class="px-5 py-4 text-center">
                {#if vendor.is_active}
                  <span
                    class="inline-flex items-center gap-1.5 text-xs font-medium text-neutral-900"
                  >
                    <span class="w-1.5 h-1.5 rounded-full bg-neutral-900"
                    ></span>
                    Active
                  </span>
                {:else}
                  <span
                    class="inline-flex items-center gap-1.5 text-xs font-medium text-neutral-400"
                  >
                    <span class="w-1.5 h-1.5 rounded-full bg-neutral-300"
                    ></span>
                    Inactive
                  </span>
                {/if}
              </td>
              <td class="px-5 py-4">
                <div class="flex items-center justify-center gap-2">
                  <button
                    type="button"
                    class="rounded-lg border border-neutral-200 p-2 text-neutral-500 transition-colors hover:bg-neutral-50 hover:text-neutral-900"
                    onclick={() => void openVendorDrawer(vendor.id, "view")}
                    aria-label={`View ${vendor.name}`}
                    title="View vendor"
                  >
                    <svg
                      class="h-4 w-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      stroke-width="1.8"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M2.036 12.322a1 1 0 0 1 0-.644C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.008 9.963 7.178a1 1 0 0 1 0 .644C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.008-9.964-7.178Z"
                      />
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
                      />
                    </svg>
                  </button>
                  <button
                    type="button"
                    class="rounded-lg border border-neutral-200 p-2 text-neutral-500 transition-colors hover:bg-neutral-50 hover:text-neutral-900"
                    onclick={() => void openVendorDrawer(vendor.id, "edit")}
                    aria-label={`Edit ${vendor.name}`}
                    title="Edit vendor"
                  >
                    <svg
                      class="h-4 w-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      stroke-width="1.8"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="m16.862 4.487 1.687-1.688a2.25 2.25 0 1 1 3.182 3.182L10.582 17.13a4.5 4.5 0 0 1-1.897 1.13L6 19l.74-2.685a4.5 4.5 0 0 1 1.13-1.897L16.862 4.487Z"
                      />
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="M19.5 7.125 16.875 4.5"
                      />
                    </svg>
                  </button>
                  <button
                    type="button"
                    class="rounded-lg border border-red-200 p-2 text-red-500 transition-colors hover:bg-red-50 hover:text-red-700"
                    onclick={() => void handleVendorDelete(vendor)}
                    aria-label={`Delete ${vendor.name}`}
                    title="Delete vendor"
                  >
                    <svg
                      class="h-4 w-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      stroke-width="1.8"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673A2.25 2.25 0 0 1 15.916 21.75H8.084A2.25 2.25 0 0 1 5.84 19.673L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916A2.25 2.25 0 0 0 13.5 2.25h-3A2.25 2.25 0 0 0 8.25 4.5v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
                      />
                    </svg>
                  </button>
                </div>
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
        Showing <span class="font-medium text-neutral-600"
          >{startItem}–{endItem}</span
        >
        of
        <span class="font-medium text-neutral-600">{totalCount}</span>
        {totalCount === 1 ? "vendor" : "vendors"}
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
            <svg
              class="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              stroke-width="2"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="M15.75 19.5 8.25 12l7.5-7.5"
              />
            </svg>
          </button>

          {#each pageNumbers(currentPage, totalPages) as pg}
            {#if pg === "..."}
              <span
                class="w-9 h-9 flex items-center justify-center text-xs text-neutral-300"
                >...</span
              >
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
            <svg
              class="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              stroke-width="2"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                d="m8.25 4.5 7.5 7.5-7.5 7.5"
              />
            </svg>
          </button>
        </div>
      {/if}
    </div>
  {/if}
</div>

<Modal
  open={showCreateModal}
  onclose={() => {
    showCreateModal = false;
    resetForm();
  }}
  title="New Vendor"
  maxWidth="max-w-2xl"
>
  <form onsubmit={handleCreateVendor} class="space-y-5">
    <!-- Name -->
    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Name</span
      >
      <input
        bind:value={vendorForm.name}
        class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
               focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        placeholder="Vendor name"
      />
      {#if fieldError("name")}<p class="mt-1 text-xs text-red-500">
          {fieldError("name")}
        </p>{/if}
    </label>

    <!-- Contact Person + Email -->
    <div class="grid grid-cols-2 gap-4">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5"
          >Contact Person <span class="text-neutral-400 font-normal"
            >(optional)</span
          ></span
        >
        <input
          bind:value={vendorForm.contact_person}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          placeholder="Full name"
        />
        {#if fieldError("contact_person")}<p class="mt-1 text-xs text-red-500">
            {fieldError("contact_person")}
          </p>{/if}
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5"
          >Email <span class="text-neutral-400 font-normal">(optional)</span
          ></span
        >
        <input
          type="email"
          bind:value={vendorForm.email}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          placeholder="vendor@example.com"
        />
        {#if fieldError("email")}<p class="mt-1 text-xs text-red-500">
            {fieldError("email")}
          </p>{/if}
      </label>
    </div>

    <!-- Phone + Tax ID -->
    <div class="grid grid-cols-2 gap-4">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5"
          >Phone <span class="text-neutral-400 font-normal">(optional)</span
          ></span
        >
        <input
          bind:value={vendorForm.phone}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          placeholder="+1 (555) 000-0000"
        />
        {#if fieldError("phone")}<p class="mt-1 text-xs text-red-500">
            {fieldError("phone")}
          </p>{/if}
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5"
          >Tax ID <span class="text-neutral-400 font-normal">(optional)</span
          ></span
        >
        <input
          bind:value={vendorForm.tax_id}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          placeholder="Tax identification number"
        />
        {#if fieldError("tax_id")}<p class="mt-1 text-xs text-red-500">
            {fieldError("tax_id")}
          </p>{/if}
      </label>
    </div>

    <!-- Category + Compliance -->
    <div class="grid grid-cols-2 gap-4">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5"
          >Category</span
        >
        <select
          bind:value={vendorForm.category}
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
        <span class="block text-sm font-medium text-neutral-700 mb-1.5"
          >Compliance Status</span
        >
        <select
          bind:value={vendorForm.compliance_status}
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

    <!-- Address -->
    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5"
        >Address <span class="text-neutral-400 font-normal">(optional)</span
        ></span
      >
      <textarea
        bind:value={vendorForm.address}
        rows="2"
        class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white resize-none
               focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        placeholder="Full address"
      ></textarea>
      {#if fieldError("address")}<p class="mt-1 text-xs text-red-500">
          {fieldError("address")}
        </p>{/if}
    </label>

    <!-- Notes -->
    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5"
        >Notes <span class="text-neutral-400 font-normal">(optional)</span
        ></span
      >
      <textarea
        bind:value={vendorForm.notes}
        rows="2"
        class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white resize-none
               focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        placeholder="Optional notes"
      ></textarea>
    </label>

    <label class="flex items-center gap-3 cursor-pointer">
      <input
        type="checkbox"
        bind:checked={vendorForm.is_active}
        class="w-4 h-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900"
      />
      <span class="text-sm text-neutral-700">Active vendor</span>
    </label>

    <div class="flex justify-end gap-3 pt-2">
      <button
        type="button"
        onclick={() => {
          showCreateModal = false;
          resetForm();
        }}
        class="px-4 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors"
      >
        Cancel
      </button>
      {#if isDev}
        <button
          type="button"
          onclick={devFillVendor}
          class="px-4 py-2.5 bg-orange-500 rounded-lg text-sm font-medium text-white hover:bg-orange-600 transition-colors"
        >
          Dev Fill
        </button>
      {/if}
      <button
        type="submit"
        disabled={savingVendor}
        class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium
               hover:bg-neutral-800 disabled:opacity-50 transition-colors"
      >
        {savingVendor ? "Saving..." : "Create Vendor"}
      </button>
    </div>
  </form>
</Modal>

{#if showVendorDrawer}
  <button
    type="button"
    class="fixed inset-0 z-40 bg-neutral-900/35"
    onclick={closeVendorDrawer}
    tabindex="-1"
    aria-label="Close vendor drawer"
  ></button>

  <aside
    class="fixed inset-y-0 right-0 z-50 flex w-full max-w-3xl flex-col bg-white shadow-2xl animate-slide-in-right"
  >
    <div
      class="flex items-start justify-between border-b border-neutral-100 px-6 py-4"
    >
      <div>
        <h2 class="text-lg font-semibold text-emerald-700">
          {vendorDrawerMode === "edit" ? "Edit Vendor" : "Vendor Detail"}
        </h2>
        <p class="mt-1 text-xs text-neutral-500">Approved Vendor Records</p>
      </div>
      <button
        type="button"
        onclick={closeVendorDrawer}
        class="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        aria-label="Close vendor drawer"
      >
        <svg
          class="h-5 w-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          stroke-width="1.5"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M6 18 18 6M6 6l12 12"
          />
        </svg>
      </button>
    </div>

    {#if drawerLoading}
      <div class="flex flex-1 items-center justify-center px-6 py-10">
        <div class="text-center">
          <div
            class="mx-auto inline-block h-6 w-6 rounded-full border-2 border-neutral-200 border-t-neutral-900 animate-spin"
          ></div>
          <p class="mt-3 text-sm text-neutral-500">Loading vendor details...</p>
        </div>
      </div>
    {:else if drawerVendor}
      {#if vendorDrawerMode === "view"}
        <div class="flex-1 overflow-y-auto px-6 py-5">
          <div class="space-y-6">
            <section
              class="rounded-2xl border border-neutral-200 bg-neutral-50/70 p-5"
            >
              <div
                class="flex flex-col gap-4 md:flex-row md:items-start md:justify-between"
              >
                <div class="space-y-3">
                  <div>
                    <p
                      class="text-[11px] font-bold uppercase tracking-[0.32em] text-emerald-700"
                    >
                      Vendor Profile
                    </p>
                    <h3 class="mt-2 text-xl font-semibold text-neutral-900">
                      {drawerVendor.name}
                    </h3>
                  </div>
                  <div class="flex flex-wrap items-center gap-2">
                    <span
                      class="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium {categoryColors[
                        drawerVendor.category
                      ] ?? 'bg-neutral-100 text-neutral-600'}"
                    >
                      {categoryLabels[drawerVendor.category] ??
                        drawerVendor.category}
                    </span>
                    <span
                      class="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium {complianceColors[
                        drawerVendor.compliance_status
                      ] ?? 'bg-neutral-100 text-neutral-600'}"
                    >
                      {complianceLabels[drawerVendor.compliance_status] ??
                        drawerVendor.compliance_status}
                    </span>
                    {#if drawerVendor.is_active}
                      <span
                        class="inline-flex items-center gap-1.5 rounded-full bg-white px-2.5 py-1 text-xs font-medium text-neutral-700"
                      >
                        <span class="h-1.5 w-1.5 rounded-full bg-emerald-500"
                        ></span>
                        Active
                      </span>
                    {:else}
                      <span
                        class="inline-flex items-center gap-1.5 rounded-full bg-white px-2.5 py-1 text-xs font-medium text-neutral-500"
                      >
                        <span class="h-1.5 w-1.5 rounded-full bg-neutral-300"
                        ></span>
                        Inactive
                      </span>
                    {/if}
                    {#if drawerVendor.is_blacklisted}
                      <span
                        class="inline-flex items-center rounded-full bg-red-100 px-2.5 py-1 text-xs font-semibold text-red-700"
                      >
                        Blacklisted
                      </span>
                    {/if}
                  </div>
                </div>

                <div class="grid min-w-[220px] grid-cols-2 gap-3 text-sm">
                  <div
                    class="rounded-xl border border-neutral-200 bg-white p-3"
                  >
                    <p
                      class="text-[11px] font-bold uppercase tracking-[0.28em] text-emerald-700"
                    >
                      Rating
                    </p>
                    <p class="mt-2 text-lg font-semibold text-neutral-900">
                      {Number(drawerVendor.performance_rating).toFixed(1)}<span
                        class="ml-1 text-sm text-neutral-400">/5</span
                      >
                    </p>
                  </div>
                  <div
                    class="rounded-xl border border-neutral-200 bg-white p-3"
                  >
                    <p
                      class="text-[11px] font-bold uppercase tracking-[0.28em] text-emerald-700"
                    >
                      PO Count
                    </p>
                    <p class="mt-2 text-lg font-semibold text-neutral-900">
                      {drawerVendor.po_count}
                    </p>
                  </div>
                  <div
                    class="rounded-xl border border-neutral-200 bg-white p-3"
                  >
                    <p
                      class="text-[11px] font-bold uppercase tracking-[0.28em] text-emerald-700"
                    >
                      Delivery
                    </p>
                    <p class="mt-2 text-lg font-semibold text-neutral-900">
                      {drawerVendor.delivery_timeliness_score || "0"}<span
                        class="ml-1 text-sm text-neutral-400">%</span
                      >
                    </p>
                  </div>
                  <div
                    class="rounded-xl border border-neutral-200 bg-white p-3"
                  >
                    <p
                      class="text-[11px] font-bold uppercase tracking-[0.28em] text-emerald-700"
                    >
                      PO Value
                    </p>
                    <p class="mt-2 text-lg font-semibold text-neutral-900">
                      {drawerVendor.total_po_value || "—"}
                    </p>
                  </div>
                </div>
              </div>
            </section>

            <div
              class="rounded-2xl border border-emerald-100 bg-emerald-50/60 p-1"
            >
              <div class="flex flex-wrap gap-1">
                <button
                  type="button"
                  class="rounded-xl px-3 py-2 text-xs font-semibold transition-colors {vendorDrawerTab ===
                  'overview'
                    ? 'bg-white text-emerald-700 shadow-sm'
                    : 'text-emerald-700/80 hover:bg-white/70'}"
                  onclick={() => (vendorDrawerTab = "overview")}
                >
                  Overview
                </button>
                <button
                  type="button"
                  class="rounded-xl px-3 py-2 text-xs font-semibold transition-colors {vendorDrawerTab ===
                  'purchase_orders'
                    ? 'bg-white text-emerald-700 shadow-sm'
                    : 'text-emerald-700/80 hover:bg-white/70'}"
                  onclick={() => (vendorDrawerTab = "purchase_orders")}
                >
                  Purchase Orders
                </button>
                <button
                  type="button"
                  class="rounded-xl px-3 py-2 text-xs font-semibold transition-colors {vendorDrawerTab ===
                  'rfqs'
                    ? 'bg-white text-emerald-700 shadow-sm'
                    : 'text-emerald-700/80 hover:bg-white/70'}"
                  onclick={() => (vendorDrawerTab = "rfqs")}
                >
                  RFQs
                </button>
                <button
                  type="button"
                  class="rounded-xl px-3 py-2 text-xs font-semibold transition-colors {vendorDrawerTab ===
                  'goods_receipts'
                    ? 'bg-white text-emerald-700 shadow-sm'
                    : 'text-emerald-700/80 hover:bg-white/70'}"
                  onclick={() => (vendorDrawerTab = "goods_receipts")}
                >
                  GRNs
                </button>
                <button
                  type="button"
                  class="rounded-xl px-3 py-2 text-xs font-semibold transition-colors {vendorDrawerTab ===
                  'documents'
                    ? 'bg-white text-emerald-700 shadow-sm'
                    : 'text-emerald-700/80 hover:bg-white/70'}"
                  onclick={() => (vendorDrawerTab = "documents")}
                >
                  Documents
                </button>
              </div>
            </div>

            {#if vendorDrawerTab === "overview"}
              <div class="grid gap-4 md:grid-cols-2">
                <section class="rounded-2xl border border-neutral-200 p-5">
                  <p
                    class="text-[11px] font-bold uppercase tracking-[0.32em] text-emerald-700"
                  >
                    Contact
                  </p>
                  <div class="mt-4 space-y-3 text-sm text-neutral-700">
                    <div>
                      <p
                        class="text-sm font-bold tracking-wider text-neutral-400"
                      >
                        Primary Contact
                      </p>
                      <p class="mt-1 text-xs font-medium text-neutral-900">
                        {drawerVendor.contact_person || "—"}
                      </p>
                    </div>
                    <div>
                      <p
                        class="text-sm font-bold tracking-wider text-neutral-400"
                      >
                        Email
                      </p>
                      <p class="mt-1 text-xs font-medium text-neutral-900">
                        {drawerVendor.email || "—"}
                      </p>
                    </div>
                    <div>
                      <p
                        class="text-sm font-bold tracking-wider text-neutral-400"
                      >
                        Phone
                      </p>
                      <p class="mt-1 text-xs font-medium text-neutral-900">
                        {drawerVendor.phone || "—"}
                      </p>
                    </div>
                    <div>
                      <p
                        class="text-sm font-bold tracking-wider text-neutral-400"
                      >
                        Address
                      </p>
                      <p class="mt-1 text-xs font-medium text-neutral-900">
                        {drawerVendor.address || "—"}
                      </p>
                    </div>
                  </div>
                </section>

                <section class="rounded-2xl border border-neutral-200 p-5">
                  <p
                    class="text-[11px] font-bold uppercase tracking-[0.32em] text-emerald-700"
                  >
                    Compliance & Banking
                  </p>
                  <div class="mt-4 space-y-3 text-sm text-neutral-700">
                    <div>
                      <p
                        class="text-sm font-bold tracking-wider text-neutral-400"
                      >
                        Tax ID
                      </p>
                      <p class="mt-1 text-xs font-medium text-neutral-900">
                        {drawerVendor.tax_id || "—"}
                      </p>
                    </div>
                    <div>
                      <p
                        class="text-sm font-bold tracking-wider text-neutral-400"
                      >
                        Bank
                      </p>
                      <p class="mt-1 text-xs font-medium text-neutral-900">
                        {drawerVendor.bank_name || "—"}
                      </p>
                    </div>
                    <div>
                      <p
                        class="text-sm font-bold tracking-wider text-neutral-400"
                      >
                        Account Number
                      </p>
                      <p class="mt-1 text-xs font-medium text-neutral-900">
                        {drawerVendor.bank_account_number || "—"}
                      </p>
                    </div>
                    <div>
                      <p
                        class="text-sm font-bold tracking-wider text-neutral-400"
                      >
                        Branch
                      </p>
                      <p class="mt-1 text-xs font-medium text-neutral-900">
                        {drawerVendor.bank_branch || "—"}
                      </p>
                    </div>
                    <div>
                      <p
                        class="text-sm font-bold tracking-wider text-neutral-400"
                      >
                        Price Competitiveness
                      </p>
                      <p class="mt-1 text-xs font-medium text-neutral-900">
                        {drawerVendor.price_competitiveness.replace("_", " ")}
                      </p>
                    </div>
                    {#if drawerVendor.blacklist_reason}
                      <div>
                        <p
                          class="text-sm font-bold tracking-wider text-neutral-400"
                        >
                          Blacklist Reason
                        </p>
                        <p class="mt-1 text-xs font-medium text-red-600">
                          {drawerVendor.blacklist_reason}
                        </p>
                      </div>
                    {/if}
                  </div>
                </section>
              </div>

              <section class="rounded-2xl border border-neutral-200 p-5">
                <p
                  class="text-[11px] font-bold uppercase tracking-[0.32em] text-emerald-700"
                >
                  Portfolio Coverage
                </p>
                <div class="mt-4 grid gap-4 md:grid-cols-2">
                  <div>
                    <p class="text-xs tracking-[0.24em] text-neutral-400">
                      Approved Projects
                    </p>
                    {#if drawerVendor.approved_projects_detail.length > 0}
                      <div class="mt-3 flex flex-wrap gap-2">
                        {#each drawerVendor.approved_projects_detail as project}
                          <span
                            class="inline-flex items-center rounded-full bg-neutral-100 px-2.5 py-1 text-xs font-medium text-neutral-700"
                          >
                            {project.name}
                          </span>
                        {/each}
                      </div>
                    {:else}
                      <p class="mt-2 text-sm text-neutral-500">
                        No approved projects assigned yet.
                      </p>
                    {/if}
                  </div>
                  <div>
                    <p
                      class="text-xs font-bold uppercase tracking-wider text-neutral-400"
                    >
                      Internal Notes
                    </p>
                    <p class="mt-2 text-sm leading-6 text-neutral-600">
                      {drawerVendor.notes ||
                        "No internal notes available for this vendor."}
                    </p>
                  </div>
                </div>
              </section>
            {:else if vendorDrawerTab === "purchase_orders"}
              <section class="rounded-2xl border border-neutral-200 p-5">
                <div class="flex items-center justify-between gap-3">
                  <div>
                    <p
                      class="text-[11px] font-semibold uppercase tracking-[0.32em] text-emerald-700"
                    >
                      Purchase Orders
                    </p>
                    <p class="mt-1 text-sm text-neutral-500">
                      Recent orders associated with this vendor.
                    </p>
                  </div>
                  <span
                    class="rounded-full bg-neutral-100 px-2.5 py-1 text-xs font-semibold text-neutral-600"
                    >{drawerPurchaseOrders.length}</span
                  >
                </div>
                {#if drawerAssociationsLoading}
                  <div class="py-12 text-center">
                    <div
                      class="inline-block h-5 w-5 rounded-full border-2 border-neutral-200 border-t-neutral-900 animate-spin"
                    ></div>
                    <p class="mt-3 text-sm text-neutral-500">
                      Loading purchase orders...
                    </p>
                  </div>
                {:else if drawerPurchaseOrders.length === 0}
                  <p class="mt-6 text-sm text-neutral-500">
                    No purchase orders are linked to this vendor yet.
                  </p>
                {:else}
                  <div
                    class="mt-5 overflow-hidden rounded-xl border border-neutral-200"
                  >
                    <table class="w-full text-sm">
                      <thead class="bg-neutral-50">
                        <tr>
                          <th
                            class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.24em] text-neutral-400"
                            >PO #</th
                          >
                          <th
                            class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.24em] text-neutral-400"
                            >Status</th
                          >
                          <th
                            class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.24em] text-neutral-400"
                            >Issued</th
                          >
                          <th
                            class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.24em] text-neutral-400"
                            >Value</th
                          >
                        </tr>
                      </thead>
                      <tbody class="divide-y divide-neutral-100">
                        {#each drawerPurchaseOrders as purchaseOrder}
                          <tr class="hover:bg-neutral-50 transition-colors">
                            <td class="px-4 py-3">
                              <a
                                href="/procurement/purchase-orders/{purchaseOrder.id}"
                                class="font-medium text-neutral-900 hover:text-emerald-700 hover:underline"
                              >
                                {purchaseOrder.po_number}
                              </a>
                            </td>
                            <td class="px-4 py-3 text-neutral-600"
                              >{formatStatus(purchaseOrder.status)}</td
                            >
                            <td class="px-4 py-3 text-neutral-500"
                              >{formatDate(purchaseOrder.issue_date)}</td
                            >
                            <td class="px-4 py-3 text-neutral-900"
                              >{purchaseOrder.total_amount}</td
                            >
                          </tr>
                        {/each}
                      </tbody>
                    </table>
                  </div>
                {/if}
              </section>
            {:else if vendorDrawerTab === "rfqs"}
              <section class="rounded-2xl border border-neutral-200 p-5">
                <div class="flex items-center justify-between gap-3">
                  <div>
                    <p
                      class="text-[11px] font-semibold uppercase tracking-[0.32em] text-emerald-700"
                    >
                      RFQs
                    </p>
                    <p class="mt-1 text-sm text-neutral-500">
                      Requests for quotation where this vendor is currently
                      selected.
                    </p>
                  </div>
                  <span
                    class="rounded-full bg-neutral-100 px-2.5 py-1 text-xs font-semibold text-neutral-600"
                    >{drawerRfqs.length}</span
                  >
                </div>
                {#if drawerAssociationsLoading}
                  <div class="py-12 text-center">
                    <div
                      class="inline-block h-5 w-5 rounded-full border-2 border-neutral-200 border-t-neutral-900 animate-spin"
                    ></div>
                    <p class="mt-3 text-sm text-neutral-500">Loading RFQs...</p>
                  </div>
                {:else if drawerRfqs.length === 0}
                  <p class="mt-6 text-sm text-neutral-500">
                    No selected-vendor RFQs are linked to this vendor yet.
                  </p>
                {:else}
                  <div class="mt-5 space-y-3">
                    {#each drawerRfqs as rfq}
                      <a
                        href="/procurement/rfqs/{rfq.id}"
                        class="block rounded-xl border border-neutral-200 p-4 transition-colors hover:border-emerald-200 hover:bg-emerald-50/40"
                      >
                        <div
                          class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between"
                        >
                          <div>
                            <p class="text-sm font-semibold text-neutral-900">
                              {rfq.rfq_number}
                            </p>
                            <p class="mt-1 text-sm text-neutral-600">
                              {rfq.title}
                            </p>
                            <p class="mt-2 text-xs text-neutral-500">
                              {rfq.project_name ||
                                rfq.property_name ||
                                rfq.requisition_number ||
                                "Unlinked"}
                            </p>
                          </div>
                          <div class="text-left md:text-right">
                            <p
                              class="text-xs font-semibold uppercase tracking-[0.24em] text-neutral-400"
                            >
                              {formatStatus(rfq.status)}
                            </p>
                            <p class="mt-2 text-sm text-neutral-500">
                              Issued {formatDate(rfq.issue_date)}
                            </p>
                            <p class="mt-1 text-sm text-neutral-900">
                              {rfq.estimated_value || "—"}
                            </p>
                          </div>
                        </div>
                      </a>
                    {/each}
                  </div>
                {/if}
              </section>
            {:else if vendorDrawerTab === "goods_receipts"}
              <section class="rounded-2xl border border-neutral-200 p-5">
                <div class="flex items-center justify-between gap-3">
                  <div>
                    <p
                      class="text-[11px] font-semibold uppercase tracking-[0.32em] text-emerald-700"
                    >
                      Goods Received Notes
                    </p>
                    <p class="mt-1 text-sm text-neutral-500">
                      GRNs derived from the vendor’s purchase orders.
                    </p>
                  </div>
                  <span
                    class="rounded-full bg-neutral-100 px-2.5 py-1 text-xs font-semibold text-neutral-600"
                    >{drawerGoodsReceipts.length}</span
                  >
                </div>
                {#if drawerAssociationsLoading}
                  <div class="py-12 text-center">
                    <div
                      class="inline-block h-5 w-5 rounded-full border-2 border-neutral-200 border-t-neutral-900 animate-spin"
                    ></div>
                    <p class="mt-3 text-sm text-neutral-500">
                      Loading goods received notes...
                    </p>
                  </div>
                {:else if drawerGoodsReceipts.length === 0}
                  <p class="mt-6 text-sm text-neutral-500">
                    No goods received notes are linked to this vendor yet.
                  </p>
                {:else}
                  <div class="mt-5 space-y-3">
                    {#each drawerGoodsReceipts as grn}
                      <a
                        href="/procurement/goods-receipts/{grn.id}"
                        class="block rounded-xl border border-neutral-200 p-4 transition-colors hover:border-emerald-200 hover:bg-emerald-50/40"
                      >
                        <div
                          class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between"
                        >
                          <div>
                            <p class="text-sm font-semibold text-neutral-900">
                              {grn.grn_number}
                            </p>
                            <p class="mt-1 text-sm text-neutral-600">
                              PO {grn.po_number}
                            </p>
                            <p class="mt-2 text-xs text-neutral-500">
                              Received by {grn.received_by || "—"}
                            </p>
                          </div>
                          <div class="text-left md:text-right">
                            <p
                              class="text-xs font-semibold uppercase tracking-[0.24em] text-neutral-400"
                            >
                              {formatStatus(grn.status)}
                            </p>
                            <p class="mt-2 text-sm text-neutral-500">
                              {formatDate(grn.received_date)}
                            </p>
                            <p class="mt-1 text-sm text-neutral-900">
                              {grn.item_count} items
                            </p>
                          </div>
                        </div>
                      </a>
                    {/each}
                  </div>
                {/if}
              </section>
            {:else}
              <section class="space-y-4">
                <div>
                  <p
                    class="text-[11px] font-semibold uppercase tracking-[0.32em] text-emerald-700"
                  >
                    Documents
                  </p>
                  <p class="mt-1 text-sm text-neutral-500">
                    Controlled repository documents linked to this vendor.
                  </p>
                </div>
                <DocumentRecordsTable
                  title="Vendor Documents"
                  subtitle="Auto-filtered controlled documents linked to this vendor."
                  query={{ vendor: drawerVendor.id }}
                  pageSize={8}
                  showHeader={false}
                  showViewAll={true}
                  viewAllHref={`/documents/repository?vendor=${drawerVendor.id}`}
                  emptyMessage="No controlled repository documents are linked to this vendor yet."
                />
              </section>
            {/if}
          </div>
        </div>

        <div
          class="flex items-center justify-between border-t border-neutral-100 px-6 py-4"
        >
          <button
            type="button"
            onclick={() => {
              if (!drawerVendor) return;
              void handleVendorDelete({
                id: drawerVendor.id,
                name: drawerVendor.name,
              });
            }}
            class="rounded-lg border border-red-200 px-4 py-2.5 text-sm font-medium text-red-600 transition-colors hover:bg-red-50"
          >
            Delete Vendor
          </button>
          <div class="flex items-center gap-3">
            <button
              type="button"
              onclick={closeVendorDrawer}
              class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-600 transition-colors hover:bg-neutral-50"
            >
              Close
            </button>
            <button
              type="button"
              onclick={openDrawerEditMode}
              class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-neutral-800"
            >
              Edit Vendor
            </button>
          </div>
        </div>
      {:else}
        <form
          id="vendor-edit-form"
          class="flex flex-1 flex-col min-h-0"
          onsubmit={handleVendorUpdate}
        >
          <div class="flex-1 overflow-y-auto min-h-0 px-6 py-5">
            <div class="grid gap-5 md:grid-cols-2">
              <label class="text-sm font-medium text-neutral-700">
                <span class="mb-1.5 block">Vendor Name</span>
                <input
                  bind:value={drawerForm.name}
                  class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm"
                  placeholder="Vendor name"
                />
                {#if drawerFieldError("name")}<p
                    class="mt-1 text-xs text-red-500"
                  >
                    {drawerFieldError("name")}
                  </p>{/if}
              </label>

              <label class="text-sm font-medium text-neutral-700">
                <span class="mb-1.5 block">Category</span>
                <select
                  bind:value={drawerForm.category}
                  class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm"
                >
                  <option value="materials">Materials</option>
                  <option value="contractor">Contractor</option>
                  <option value="consultant">Consultant</option>
                  <option value="other">Other</option>
                </select>
              </label>

              <label class="text-sm font-medium text-neutral-700">
                <span class="mb-1.5 block">Contact Person</span>
                <input
                  bind:value={drawerForm.contact_person}
                  class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm"
                  placeholder="Primary contact"
                />
                {#if drawerFieldError("contact_person")}<p
                    class="mt-1 text-xs text-red-500"
                  >
                    {drawerFieldError("contact_person")}
                  </p>{/if}
              </label>

              <label class="text-sm font-medium text-neutral-700">
                <span class="mb-1.5 block">Email</span>
                <input
                  type="email"
                  bind:value={drawerForm.email}
                  class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm"
                  placeholder="vendor@example.com"
                />
                {#if drawerFieldError("email")}<p
                    class="mt-1 text-xs text-red-500"
                  >
                    {drawerFieldError("email")}
                  </p>{/if}
              </label>

              <label class="text-sm font-medium text-neutral-700">
                <span class="mb-1.5 block">Phone</span>
                <input
                  bind:value={drawerForm.phone}
                  class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm"
                  placeholder="+234..."
                />
                {#if drawerFieldError("phone")}<p
                    class="mt-1 text-xs text-red-500"
                  >
                    {drawerFieldError("phone")}
                  </p>{/if}
              </label>

              <label class="text-sm font-medium text-neutral-700">
                <span class="mb-1.5 block">Tax ID</span>
                <input
                  bind:value={drawerForm.tax_id}
                  class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm"
                  placeholder="Tax identification number"
                />
                {#if drawerFieldError("tax_id")}<p
                    class="mt-1 text-xs text-red-500"
                  >
                    {drawerFieldError("tax_id")}
                  </p>{/if}
              </label>

              <label class="text-sm font-medium text-neutral-700 md:col-span-2">
                <span class="mb-1.5 block">Address</span>
                <textarea
                  bind:value={drawerForm.address}
                  rows="3"
                  class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm"
                  placeholder="Full address"
                ></textarea>
                {#if drawerFieldError("address")}<p
                    class="mt-1 text-xs text-red-500"
                  >
                    {drawerFieldError("address")}
                  </p>{/if}
              </label>

              <label class="text-sm font-medium text-neutral-700">
                <span class="mb-1.5 block">Compliance Status</span>
                <select
                  bind:value={drawerForm.compliance_status}
                  class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm"
                >
                  <option value="pending_review">Pending Review</option>
                  <option value="compliant">Compliant</option>
                  <option value="non_compliant">Non-Compliant</option>
                  <option value="expired">Expired</option>
                </select>
              </label>

              <label class="text-sm font-medium text-neutral-700">
                <span class="mb-1.5 block">Price Competitiveness</span>
                <select
                  bind:value={drawerForm.price_competitiveness}
                  class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm"
                >
                  <option value="low">Low</option>
                  <option value="average">Average</option>
                  <option value="high">High</option>
                  <option value="premium">Premium</option>
                </select>
              </label>

              <label class="text-sm font-medium text-neutral-700">
                <span class="mb-1.5 block">Performance Rating</span>
                <input
                  bind:value={drawerForm.performance_rating}
                  class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm"
                  placeholder="0 - 5"
                />
                {#if drawerFieldError("performance_rating")}<p
                    class="mt-1 text-xs text-red-500"
                  >
                    {drawerFieldError("performance_rating")}
                  </p>{/if}
              </label>

              <label class="text-sm font-medium text-neutral-700">
                <span class="mb-1.5 block">Delivery Timeliness Score</span>
                <input
                  bind:value={drawerForm.delivery_timeliness_score}
                  class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm"
                  placeholder="0 - 100"
                />
                {#if drawerFieldError("delivery_timeliness_score")}<p
                    class="mt-1 text-xs text-red-500"
                  >
                    {drawerFieldError("delivery_timeliness_score")}
                  </p>{/if}
              </label>

              <label class="text-sm font-medium text-neutral-700">
                <span class="mb-1.5 block">Bank Name</span>
                <input
                  bind:value={drawerForm.bank_name}
                  class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm"
                  placeholder="Bank name"
                />
                {#if drawerFieldError("bank_name")}<p
                    class="mt-1 text-xs text-red-500"
                  >
                    {drawerFieldError("bank_name")}
                  </p>{/if}
              </label>

              <label class="text-sm font-medium text-neutral-700">
                <span class="mb-1.5 block">Bank Account Number</span>
                <input
                  bind:value={drawerForm.bank_account_number}
                  class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm"
                  placeholder="Account number"
                />
                {#if drawerFieldError("bank_account_number")}<p
                    class="mt-1 text-xs text-red-500"
                  >
                    {drawerFieldError("bank_account_number")}
                  </p>{/if}
              </label>

              <label class="text-sm font-medium text-neutral-700">
                <span class="mb-1.5 block">Bank Branch</span>
                <input
                  bind:value={drawerForm.bank_branch}
                  class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm"
                  placeholder="Branch"
                />
                {#if drawerFieldError("bank_branch")}<p
                    class="mt-1 text-xs text-red-500"
                  >
                    {drawerFieldError("bank_branch")}
                  </p>{/if}
              </label>

              <label class="text-sm font-medium text-neutral-700 md:col-span-2">
                <span class="mb-1.5 block">Internal Notes</span>
                <textarea
                  bind:value={drawerForm.notes}
                  rows="4"
                  class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm"
                  placeholder="Optional notes about vendor performance, terms, or risk"
                ></textarea>
                {#if drawerFieldError("notes")}<p
                    class="mt-1 text-xs text-red-500"
                  >
                    {drawerFieldError("notes")}
                  </p>{/if}
              </label>

              <div class="space-y-3 md:col-span-2">
                <label
                  class="flex items-center gap-3 rounded-xl border border-neutral-200 px-4 py-3"
                >
                  <input
                    type="checkbox"
                    bind:checked={drawerForm.is_active}
                    class="h-4 w-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900"
                  />
                  <span class="text-sm font-medium text-neutral-700"
                    >Active vendor</span
                  >
                </label>

                <label
                  class="flex items-center gap-3 rounded-xl border border-neutral-200 px-4 py-3"
                >
                  <input
                    type="checkbox"
                    bind:checked={drawerForm.is_blacklisted}
                    class="h-4 w-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900"
                  />
                  <span class="text-sm font-medium text-neutral-700"
                    >Blacklisted vendor</span
                  >
                </label>
              </div>

              {#if drawerForm.is_blacklisted}
                <label
                  class="text-sm font-medium text-neutral-700 md:col-span-2"
                >
                  <span class="mb-1.5 block">Blacklist Reason</span>
                  <textarea
                    bind:value={drawerForm.blacklist_reason}
                    rows="3"
                    class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm"
                    placeholder="Why this vendor is blacklisted"
                  ></textarea>
                  {#if drawerFieldError("blacklist_reason")}<p
                      class="mt-1 text-xs text-red-500"
                    >
                      {drawerFieldError("blacklist_reason")}
                    </p>{/if}
                </label>
              {/if}
            </div>
          </div>

          <div
            class="flex items-center justify-between border-t border-neutral-100 px-6 py-4"
          >
            <button
              type="button"
              onclick={() => (vendorDrawerMode = "view")}
              class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-600 transition-colors hover:bg-neutral-50"
            >
              Back
            </button>
            <div class="flex items-center gap-3">
              <button
                type="button"
                onclick={closeVendorDrawer}
                class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-600 transition-colors hover:bg-neutral-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={drawerSaving}
                class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-neutral-800 disabled:opacity-50"
              >
                {drawerSaving ? "Saving..." : "Save Changes"}
              </button>
            </div>
          </div>
        </form>
      {/if}
    {/if}
  </aside>
{/if}

<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import Modal from "$lib/components/Modal.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type { Customer, CustomerListItem, InvoiceListItem, PaginatedResponse } from "$lib/types";

  let data = $state<CustomerListItem[]>([]);
  let totalCount = $state(0);
  let currentPage = $state(1);
  let searchQuery = $state("");
  let activeFilter = $state("");
  let loading = $state(true);

  let showCreateModal = $state(false);
  let customerForm = $state({
    name: "",
    contact_person: "",
    email: "",
    phone: "",
    address: "",
    tax_id: "",
    notes: "",
    is_active: true,
  });
  let customerErrors = $state<Record<string, string[]>>({});
  let savingCustomer = $state(false);

  // Dev fill
  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  const CUSTOMER_SAMPLES = [
    { name: "Alpha Solar Ltd", contact_person: "Chidi Okafor", email: "chidi@alphasolar.ng", phone: "+234 801 234 5678", address: "12 Admiralty Way, Lekki, Lagos", tax_id: "TIN-98234521", notes: "Primary solar panel supplier for Lagos projects." },
    { name: "BetaCon Engineering", contact_person: "Amina Bello", email: "amina@betacon.com", phone: "+234 802 987 6543", address: "Plot 45, Wuse Zone 5, Abuja", tax_id: "TIN-44218906", notes: "Structural steel and fabrication." },
    { name: "GreenField Logistics", contact_person: "Emeka Nwankwo", email: "emeka@greenfield.ng", phone: "+234 803 111 2222", address: "KM 12, Lekki-Epe Expressway, Lagos", tax_id: "TIN-77653102", notes: "Haulage and site logistics partner." },
  ];

  let devIdx = $state(0);

  function devFillCustomer() {
    const sample = CUSTOMER_SAMPLES[devIdx % CUSTOMER_SAMPLES.length];
    devIdx++;
    customerForm = { ...sample, is_active: true };
  }

  const PAGE_SIZE = 25;
  const totalPages = $derived(Math.ceil(totalCount / PAGE_SIZE));
  const startItem = $derived((currentPage - 1) * PAGE_SIZE + 1);
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

  async function fetchCustomers() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage) };
      if (searchQuery) params.search = searchQuery;
      if (activeFilter) params.is_active = activeFilter;

      const res = await api.get<PaginatedResponse<CustomerListItem>>("/finance/customers/", params);
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
    void currentPage;
    fetchCustomers();
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
    return customerErrors[field]?.[0] ?? "";
  }

  async function handleCreateCustomer(e: Event) {
    e.preventDefault();
    customerErrors = {};
    savingCustomer = true;

    try {
      await api.post<Customer>("/finance/customers/", customerForm);
      toast.success("Customer created", `"${customerForm.name}" has been added`);
      showCreateModal = false;
      customerForm = {
        name: "",
        contact_person: "",
        email: "",
        phone: "",
        address: "",
        tax_id: "",
        notes: "",
        is_active: true,
      };
      customerErrors = {};
      fetchCustomers();
    } catch (err) {
      if (err instanceof ApiError) {
        customerErrors = err.fieldErrors;
        // Extract the first readable error message
        const allErrors = Object.entries(err.fieldErrors);
        if (allErrors.length > 0) {
          const [field, messages] = allErrors[0];
          const msg = Array.isArray(messages) ? messages[0] : messages;
          const label = field === "non_field_errors" || field === "detail" ? "" : `${field}: `;
          toast.error("Validation error", `${label}${typeof msg === "string" ? msg : "Please fix the highlighted fields"}`);
        } else {
          toast.error("Validation error", "Please fix the highlighted fields");
        }
      } else {
        toast.error("Something went wrong", "Could not create the customer");
      }
    }
    savingCustomer = false;
  }

  // ── Detail drawer ──
  let drawerOpen = $state(false);
  let drawerCustomer = $state<Customer | null>(null);
  let drawerLoading = $state(false);
  let drawerSaving = $state(false);
  let drawerDeleting = $state(false);
  let drawerErrors = $state<Record<string, string[]>>({});
  let drawerInvoices = $state<InvoiceListItem[]>([]);
  let drawerInvoicesLoading = $state(false);

  let drawerForm = $state({
    name: "", contact_person: "", email: "", phone: "",
    address: "", tax_id: "", notes: "", is_active: true,
  });

  function drawerFieldError(field: string): string {
    return drawerErrors[field]?.[0] ?? "";
  }

  function formatCurrency(value: string): string {
    return currency.format(value);
  }

  function formatDate(value: string): string {
    return new Date(value).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  }

  async function openDrawer(id: number) {
    drawerOpen = true;
    drawerLoading = true;
    drawerCustomer = null;
    drawerInvoices = [];
    drawerErrors = {};
    try {
      drawerCustomer = await api.get<Customer>(`/finance/customers/${id}/`);
      drawerForm = {
        name: drawerCustomer.name, contact_person: drawerCustomer.contact_person,
        email: drawerCustomer.email, phone: drawerCustomer.phone,
        address: drawerCustomer.address, tax_id: drawerCustomer.tax_id,
        notes: drawerCustomer.notes, is_active: drawerCustomer.is_active,
      };
      // Load invoices for this customer
      drawerInvoicesLoading = true;
      try {
        const res = await api.get<PaginatedResponse<InvoiceListItem>>("/finance/invoices/", { customer: String(id) });
        drawerInvoices = res.results;
      } catch { drawerInvoices = []; }
      drawerInvoicesLoading = false;
    } catch {
      toast.error("Not found", "Customer could not be loaded");
      drawerOpen = false;
    }
    drawerLoading = false;
  }

  function closeDrawer() {
    drawerOpen = false;
    drawerCustomer = null;
  }

  async function handleDrawerSave(e: Event) {
    e.preventDefault();
    if (!drawerCustomer) return;
    drawerErrors = {};
    drawerSaving = true;
    try {
      drawerCustomer = await api.patch<Customer>(`/finance/customers/${drawerCustomer.id}/`, drawerForm);
      toast.success("Customer updated", `"${drawerForm.name}" has been saved`);
      fetchCustomers();
    } catch (err) {
      if (err instanceof ApiError) {
        drawerErrors = err.fieldErrors;
        const allErrors = Object.entries(err.fieldErrors);
        if (allErrors.length > 0) {
          const [field, messages] = allErrors[0];
          const msg = Array.isArray(messages) ? messages[0] : messages;
          toast.error("Validation error", `${field === "non_field_errors" ? "" : field + ": "}${typeof msg === "string" ? msg : "Please check the form"}`);
        }
      } else {
        toast.error("Something went wrong", "Could not update the customer");
      }
    }
    drawerSaving = false;
  }

  async function handleDrawerDelete() {
    if (!drawerCustomer || !confirm("Are you sure you want to delete this customer?")) return;
    drawerDeleting = true;
    try {
      await api.delete(`/finance/customers/${drawerCustomer.id}/`);
      toast.success("Customer deleted", `"${drawerCustomer.name}" has been removed`);
      closeDrawer();
      fetchCustomers();
    } catch {
      toast.error("Failed to delete", "This customer may have associated invoices");
    }
    drawerDeleting = false;
  }
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-pink-600">Accounts Receivable</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Customers</h1>
      <p class="text-sm text-neutral-400 mt-1">Manage your customer directory with ease</p>
    </div>
    <button
      onclick={() => showCreateModal = true}
      class="px-4 py-2.5 bg-neutral-800 text-white rounded-lg hover:bg-neutral-800 text-sm font-medium transition-colors"
    >
      + New Customer
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
        placeholder="Search customers..."
        oninput={onSearchInput}
        class="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
               focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent
               placeholder:text-neutral-400"
      />
    </div>
    <select
      bind:value={activeFilter}
      onchange={() => (currentPage = 1)}
      class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600
             focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
    >
      <option value="">All Status</option>
      <option value="true">Active</option>
      <option value="false">Inactive</option>
    </select>
  </div>

  <!-- Table -->
  <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
    {#if loading}
      <div class="p-16 text-center">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
        <p class="mt-3 text-sm text-neutral-400">Loading customers...</p>
      </div>
    {:else if data.length === 0}
      <div class="p-16 text-center">
        <svg class="w-12 h-12 mx-auto text-neutral-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z" />
        </svg>
        <p class="mt-4 text-sm font-medium text-neutral-800">No customers found</p>
        <p class="mt-1 text-sm text-neutral-400">Get started by adding your first customer.</p>
        <button
          onclick={() => showCreateModal = true}
          class="inline-block mt-4 px-4 py-2 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors"
        >
          + New Customer
        </button>
      </div>
    {:else}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200">
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Name</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Contact Person</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Email</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Phone</th>
            <th class="px-5 py-3.5 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Invoices</th>
            <th class="px-5 py-3.5 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each data as customer}
            <tr
              class="hover:bg-neutral-50 cursor-pointer transition-colors"
              onclick={() => openDrawer(customer.id)}
            >
              <td class="px-5 py-4">
                <span class="font-medium text-neutral-800">{customer.name}</span>
              </td>
              <td class="px-5 py-4 text-neutral-500">{customer.contact_person || "\u2014"}</td>
              <td class="px-5 py-4 text-neutral-500">{customer.email || "\u2014"}</td>
              <td class="px-5 py-4 text-neutral-500">{customer.phone || "\u2014"}</td>
              <td class="px-5 py-4 text-center text-neutral-500">{customer.invoice_count}</td>
              <td class="px-5 py-4 text-center">
                {#if customer.is_active}
                  <span class="inline-flex items-center gap-1.5 text-xs font-medium text-neutral-800">
                    <span class="w-1.5 h-1.5 rounded-full bg-neutral-800"></span>
                    Active
                  </span>
                {:else}
                  <span class="inline-flex items-center gap-1.5 text-xs font-medium text-neutral-400">
                    <span class="w-1.5 h-1.5 rounded-full bg-neutral-300"></span>
                    Inactive
                  </span>
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
        Showing <span class="font-medium text-neutral-600">{startItem}–{endItem}</span> of
        <span class="font-medium text-neutral-600">{totalCount}</span>
        {totalCount === 1 ? "customer" : "customers"}
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
                         ? 'bg-neutral-800 text-white'
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

<Modal open={showCreateModal} onclose={() => showCreateModal = false} title="New Customer" maxWidth="max-w-xl">
  <form onsubmit={handleCreateCustomer} class="space-y-5">
    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Name</span>
      <input
        bind:value={customerForm.name}
        class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
               focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
        placeholder="Customer name"
      />
      {#if fieldError("name")}<p class="mt-1 text-xs text-red-500">{fieldError("name")}</p>{/if}
    </label>

    <div class="grid grid-cols-2 gap-4">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Contact Person</span>
        <input
          bind:value={customerForm.contact_person}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
          placeholder="Full name"
        />
        {#if fieldError("contact_person")}<p class="mt-1 text-xs text-red-500">{fieldError("contact_person")}</p>{/if}
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Email</span>
        <input
          type="email"
          bind:value={customerForm.email}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
          placeholder="customer@example.com"
        />
        {#if fieldError("email")}<p class="mt-1 text-xs text-red-500">{fieldError("email")}</p>{/if}
      </label>
    </div>

    <div class="grid grid-cols-2 gap-4">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Phone</span>
        <input
          bind:value={customerForm.phone}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
          placeholder="+1 (555) 000-0000"
        />
        {#if fieldError("phone")}<p class="mt-1 text-xs text-red-500">{fieldError("phone")}</p>{/if}
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Tax ID</span>
        <input
          bind:value={customerForm.tax_id}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white
                 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
          placeholder="Tax identification number"
        />
        {#if fieldError("tax_id")}<p class="mt-1 text-xs text-red-500">{fieldError("tax_id")}</p>{/if}
      </label>
    </div>

    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Address</span>
      <textarea
        bind:value={customerForm.address}
        rows={3}
        class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white resize-none
               focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
        placeholder="Full address"
      ></textarea>
      {#if fieldError("address")}<p class="mt-1 text-xs text-red-500">{fieldError("address")}</p>{/if}
    </label>

    <label>
      <span class="block text-sm font-medium text-neutral-700 mb-1.5">Notes</span>
      <textarea
        bind:value={customerForm.notes}
        rows={3}
        class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white resize-none
               focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
        placeholder="Optional notes"
      ></textarea>
    </label>

    <label class="flex items-center gap-3 cursor-pointer">
      <input type="checkbox" bind:checked={customerForm.is_active} class="w-4 h-4 rounded border-neutral-300 text-neutral-800 focus:ring-neutral-800" />
      <span class="text-sm text-neutral-700">Active customer</span>
    </label>

    <div class="flex justify-end gap-3 pt-2">
      {#if isDev}
        <button type="button" onclick={devFillCustomer} class="mr-auto rounded-lg bg-orange-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-orange-600 transition-colors">Dev Fill</button>
      {/if}
      <button
        type="button"
        onclick={() => showCreateModal = false}
        class="px-4 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors"
      >
        Cancel
      </button>
      <button
        type="submit"
        disabled={savingCustomer}
        class="px-4 py-2.5 bg-neutral-800 text-white rounded-lg text-sm font-medium
               hover:bg-neutral-800 disabled:opacity-50 transition-colors"
      >
        {savingCustomer ? "Saving..." : "Create Customer"}
      </button>
    </div>
  </form>
</Modal>

<!-- Customer Detail Drawer -->
{#if drawerOpen}
  <div class="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm" onclick={closeDrawer} onkeydown={(e) => e.key === "Escape" && closeDrawer()} role="button" tabindex="-1"></div>
  <div class="fixed inset-y-0 right-0 z-50 w-full max-w-lg bg-white shadow-2xl border-l border-neutral-200 flex flex-col drawer-slide-in">
    {#if drawerLoading}
      <div class="flex-1 flex items-center justify-center"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div></div>
    {:else if drawerCustomer}
      {@const c = drawerCustomer}

      <!-- Header -->
      <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200">
        <div class="flex items-center gap-3">
          <h2 class="text-lg font-bold text-neutral-800">{c.name}</h2>
          <span class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold" style="background: {c.is_active ? 'rgba(52,211,153,0.15)' : 'rgba(163,163,163,0.15)'}; color: {c.is_active ? '#065f46' : '#737373'};">
            <span class="w-1.5 h-1.5 rounded-full" style="background: {c.is_active ? '#10b981' : '#a3a3a3'};"></span>
            {c.is_active ? "Active" : "Inactive"}
          </span>
        </div>
        <button onclick={closeDrawer} class="w-8 h-8 flex items-center justify-center rounded-lg text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 transition-colors" aria-label="Close">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
        </button>
      </div>

      <!-- Body -->
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-6">
        <!-- Edit form -->
        <form onsubmit={handleDrawerSave} class="space-y-4">
          <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider">Customer Details</h3>

          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1">Name</span>
            <input bind:value={drawerForm.name} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />
            {#if drawerFieldError("name")}<p class="mt-1 text-xs text-red-500">{drawerFieldError("name")}</p>{/if}
          </label>

          <div class="grid grid-cols-2 gap-3">
            <label>
              <span class="block text-sm font-medium text-neutral-700 mb-1">Contact Person</span>
              <input bind:value={drawerForm.contact_person} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />
            </label>
            <label>
              <span class="block text-sm font-medium text-neutral-700 mb-1">Email</span>
              <input type="email" bind:value={drawerForm.email} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />
            </label>
          </div>

          <div class="grid grid-cols-2 gap-3">
            <label>
              <span class="block text-sm font-medium text-neutral-700 mb-1">Phone</span>
              <input bind:value={drawerForm.phone} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />
            </label>
            <label>
              <span class="block text-sm font-medium text-neutral-700 mb-1">Tax ID</span>
              <input bind:value={drawerForm.tax_id} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent" />
            </label>
          </div>

          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1">Address</span>
            <textarea bind:value={drawerForm.address} rows={2} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"></textarea>
          </label>

          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1">Notes</span>
            <textarea bind:value={drawerForm.notes} rows={2} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"></textarea>
          </label>

          <label class="flex items-center gap-2.5 cursor-pointer">
            <input type="checkbox" bind:checked={drawerForm.is_active} class="w-4 h-4 rounded border-neutral-300 text-neutral-800 focus:ring-neutral-800" />
            <span class="text-sm text-neutral-700">Active customer</span>
          </label>

          <div class="flex items-center justify-between pt-2">
            <button type="submit" disabled={drawerSaving} class="px-5 py-2 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">
              {drawerSaving ? "Saving..." : "Save Changes"}
            </button>
            <button type="button" onclick={handleDrawerDelete} disabled={drawerDeleting} class="px-4 py-2 border border-red-200 text-red-600 rounded-lg text-sm font-medium hover:bg-red-50 disabled:opacity-50 transition-colors">
              {drawerDeleting ? "Deleting..." : "Delete"}
            </button>
          </div>
        </form>

        <!-- Recent Invoices -->
        <div>
          <h3 class="text-xs font-semibold text-neutral-400 uppercase tracking-wider mb-3">Recent Invoices</h3>
          <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
            {#if drawerInvoicesLoading}
              <div class="p-6 text-center"><div class="inline-block w-5 h-5 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div></div>
            {:else if drawerInvoices.length === 0}
              <div class="p-6 text-center"><p class="text-xs text-neutral-400">No invoices for this customer.</p></div>
            {:else}
              <table class="w-full text-xs">
                <thead>
                  <tr class="border-b border-neutral-200">
                    <th class="px-3 py-2.5 text-left font-medium text-neutral-400 uppercase tracking-wider">Invoice #</th>
                    <th class="px-3 py-2.5 text-left font-medium text-neutral-400 uppercase tracking-wider">Status</th>
                    <th class="px-3 py-2.5 text-left font-medium text-neutral-400 uppercase tracking-wider">Due</th>
                    <th class="px-3 py-2.5 text-right font-medium text-neutral-400 uppercase tracking-wider">Total</th>
                    <th class="px-3 py-2.5 text-right font-medium text-neutral-400 uppercase tracking-wider">Balance</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-neutral-100">
                  {#each drawerInvoices as inv}
                    <tr class="hover:bg-neutral-50 transition-colors">
                      <td class="px-3 py-2.5 font-medium text-neutral-800">{inv.invoice_number}</td>
                      <td class="px-3 py-2.5"><StatusBadge status={inv.status} /></td>
                      <td class="px-3 py-2.5 text-neutral-500">{formatDate(inv.due_date)}</td>
                      <td class="px-3 py-2.5 text-right text-neutral-800 tabular-nums">{formatCurrency(inv.total_amount)}</td>
                      <td class="px-3 py-2.5 text-right tabular-nums font-medium" style="color: {Number(inv.balance_due) > 0 ? '#dc2626' : '#171717'};">{formatCurrency(inv.balance_due)}</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            {/if}
          </div>
        </div>
      </div>
    {/if}
  </div>
{/if}

<style>
  .drawer-slide-in { animation: drawerSlideIn 0.25s ease-out both; }
  @keyframes drawerSlideIn { from { transform: translateX(100%); } to { transform: translateX(0); } }
</style>

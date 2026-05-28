<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import ContactDetailPage from "./[id]/+page.svelte";
  import DataStateBanner from "$lib/components/DataStateBanner.svelte";
  import type {
    ContactAccountListItem,
    ContactAccountOverview,
    ContactEntityType,
    ContactKYCStatus,
    ContactRiskProfile,
    PaginatedResponse,
  } from "$lib/types";

  const pageSize = 20;

  let overview = $state<ContactAccountOverview | null>(null);
  let overviewLoading = $state(true);

  let contacts = $state<ContactAccountListItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let listError = $state<string | null>(null);
  let currentPage = $state(1);

  let search = $state("");
  let entityFilter = $state("");
  let kycFilter = $state("");
  let activeFilter = $state("");

  let showCreate = $state(false);
  let showContactDetailDrawer = $state(false);
  let selectedContactId = $state<number | null>(null);
  let suppressOpenParamSync = $state(false);
  let saving = $state(false);
  let createErrors = $state<Record<string, string[]>>({});
  let createForm = $state({
    entity_type: "individual" as ContactEntityType,
    first_name: "",
    last_name: "",
    legal_name: "",
    trade_name: "",
    primary_contact_name: "",
    email: "",
    phone: "",
    secondary_phone: "",
    address: "",
    city: "",
    country: "",
    kyc_status: "not_submitted" as ContactKYCStatus,
    annual_income: "",
    net_worth: "",
    liquidity_estimate: "",
    budget_min: "",
    budget_max: "",
    risk_profile: "undisclosed" as ContactRiskProfile,
    preferred_locations: "",
    preferred_property_types: "",
    preference_notes: "",
    interaction_summary: "",
    notes: "",
    is_active: true,
  });

  // Dev fill
  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  const CONTACT_SAMPLES = [
    { entity_type: "individual" as ContactEntityType, first_name: "Adebayo", last_name: "Ogundimu", email: "adebayo.ogundimu@gmail.com", phone: "+234 801 555 4321", address: "15 Bourdillon Road, Ikoyi", city: "Lagos", country: "Nigeria", annual_income: "45000000", net_worth: "180000000", budget_min: "50000000", budget_max: "120000000", risk_profile: "moderate" as ContactRiskProfile, preferred_locations: "Ikoyi, Lekki Phase 1", preferred_property_types: "Penthouse, Duplex", notes: "Senior exec at oil & gas firm. Referred by existing client." },
    { entity_type: "organization" as ContactEntityType, legal_name: "Crescent Holdings Ltd", trade_name: "Crescent Properties", primary_contact_name: "Fatima Abdullahi", email: "fatima@crescentholdings.ng", phone: "+234 802 333 8899", address: "Plot 12, Cadastral Zone B06, Maitama", city: "Abuja", country: "Nigeria", annual_income: "0", net_worth: "500000000", budget_min: "100000000", budget_max: "350000000", risk_profile: "aggressive" as ContactRiskProfile, preferred_locations: "Maitama, Asokoro, Wuse", preferred_property_types: "Commercial, Mixed-Use", notes: "Real estate investment company. Looking for bulk unit purchases." },
    { entity_type: "individual" as ContactEntityType, first_name: "Ngozi", last_name: "Eze", email: "ngozi.eze@outlook.com", phone: "+234 803 222 7766", address: "7 Awolowo Road, Ikoyi", city: "Lagos", country: "Nigeria", annual_income: "28000000", net_worth: "95000000", budget_min: "30000000", budget_max: "75000000", risk_profile: "conservative" as ContactRiskProfile, preferred_locations: "Victoria Island, Lekki", preferred_property_types: "3-Bed Flat, Terrace", notes: "Diaspora buyer. Currently based in London, relocating Q4 2026." },
  ];

  let devIdx = $state(0);

  function devFillContact() {
    const sample = CONTACT_SAMPLES[devIdx % CONTACT_SAMPLES.length];
    devIdx++;
    createForm.entity_type = sample.entity_type;
    createForm.first_name = sample.first_name || "";
    createForm.last_name = sample.last_name || "";
    createForm.legal_name = sample.legal_name || "";
    createForm.trade_name = sample.trade_name || "";
    createForm.primary_contact_name = sample.primary_contact_name || "";
    createForm.email = sample.email;
    createForm.phone = sample.phone;
    createForm.address = sample.address;
    createForm.city = sample.city;
    createForm.country = sample.country;
    createForm.annual_income = sample.annual_income;
    createForm.net_worth = sample.net_worth;
    createForm.budget_min = sample.budget_min;
    createForm.budget_max = sample.budget_max;
    createForm.risk_profile = sample.risk_profile;
    createForm.preferred_locations = sample.preferred_locations;
    createForm.preferred_property_types = sample.preferred_property_types;
    createForm.notes = sample.notes;
  }

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));

  let pageNumbers = $derived.by(() => {
    const pages: number[] = [];
    const maxVisible = 5;
    let start = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let end = Math.min(totalPages, start + maxVisible - 1);
    if (end - start + 1 < maxVisible) {
      start = Math.max(1, end - maxVisible + 1);
    }
    for (let i = start; i <= end; i += 1) {
      pages.push(i);
    }
    return pages;
  });

  function formatDateTime(value: string | null): string {
    if (!value) return "\u2014";
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return "\u2014";
    return d.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function formatBudget(min: string | null, max: string | null): string {
    if (!min && !max) return "\u2014";
    if (min && max) return `${currency.format(Number(min))} \u2013 ${currency.format(Number(max))}`;
    if (max) return currency.format(Number(max));
    return min ? currency.format(Number(min)) : "\u2014";
  }

  function parseList(raw: string): string[] {
    return raw
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function fieldError(field: string): string {
    return createErrors[field]?.[0] ?? "";
  }

  function statusBadgeClass(status: ContactKYCStatus): string {
    if (status === "verified") return "bg-emerald-100 text-emerald-700";
    if (status === "rejected") return "bg-rose-100 text-rose-700";
    if (status === "pending_review" || status === "under_review") return "bg-amber-100 text-amber-700";
    return "bg-neutral-100 text-neutral-600";
  }

  function entityBadgeClass(entity: ContactEntityType): string {
    if (entity === "organization") return "bg-sky-100 text-sky-700";
    return "bg-violet-100 text-violet-700";
  }

  function resetCreateForm() {
    createForm = {
      entity_type: "individual",
      first_name: "",
      last_name: "",
      legal_name: "",
      trade_name: "",
      primary_contact_name: "",
      email: "",
      phone: "",
      secondary_phone: "",
      address: "",
      city: "",
      country: "",
      kyc_status: "not_submitted",
      annual_income: "",
      net_worth: "",
      liquidity_estimate: "",
      budget_min: "",
      budget_max: "",
      risk_profile: "undisclosed",
      preferred_locations: "",
      preferred_property_types: "",
      preference_notes: "",
      interaction_summary: "",
      notes: "",
      is_active: true,
    };
    createErrors = {};
  }

  async function fetchOverview() {
    overviewLoading = true;
    try {
      overview = await api.get<ContactAccountOverview>("/crm/contacts/overview/");
    } catch (err) {
      console.error("[crm/contacts]", err);
      overview = null;
    }
    overviewLoading = false;
  }

  async function fetchContacts() {
    loading = true;
    listError = null;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        page_size: String(pageSize),
        ordering: "-updated_at",
      };
      if (search) params.search = search;
      if (entityFilter) params.entity_type = entityFilter;
      if (kycFilter) params.kyc_status = kycFilter;
      if (activeFilter) params.is_active = activeFilter;

      const res = await api.get<PaginatedResponse<ContactAccountListItem>>("/crm/contacts/", params);
      contacts = res.results;
      totalCount = res.count;
    } catch (err) {
      console.error("[crm/contacts]", err);
      contacts = [];
      totalCount = 0;
      listError = err instanceof Error ? err.message : "Could not load contacts.";
      toast.error("Could not load contacts", "Please refresh and try again.");
    }
    loading = false;
  }

  async function createContact(e: Event) {
    e.preventDefault();
    createErrors = {};
    saving = true;

    try {
      const payload: Record<string, unknown> = {
        entity_type: createForm.entity_type,
        first_name: createForm.first_name,
        last_name: createForm.last_name,
        legal_name: createForm.legal_name,
        trade_name: createForm.trade_name,
        primary_contact_name: createForm.primary_contact_name,
        email: createForm.email || "",
        phone: createForm.phone || "",
        secondary_phone: createForm.secondary_phone || "",
        address: createForm.address || "",
        city: createForm.city || "",
        country: createForm.country || "",
        kyc_status: createForm.kyc_status,
        annual_income: createForm.annual_income || null,
        net_worth: createForm.net_worth || null,
        liquidity_estimate: createForm.liquidity_estimate || null,
        budget_min: createForm.budget_min || null,
        budget_max: createForm.budget_max || null,
        risk_profile: createForm.risk_profile,
        preferred_locations: parseList(createForm.preferred_locations),
        preferred_property_types: parseList(createForm.preferred_property_types),
        preference_notes: createForm.preference_notes,
        interaction_summary: createForm.interaction_summary,
        notes: createForm.notes,
        is_active: createForm.is_active,
      };

      const created = await api.post<ContactAccountListItem>("/crm/contacts/", payload);
      toast.success("Contact created", `${created.display_name} has been added.`);
      showCreate = false;
      resetCreateForm();
      currentPage = 1;
      await Promise.all([fetchContacts(), fetchOverview()]);
    } catch (err) {
      console.error("[crm/contacts]", err);
      if (err instanceof ApiError) {
        createErrors = err.fieldErrors;
        toast.error("Validation error", "Please check the highlighted fields.");
      } else {
        toast.error("Could not create contact", "Please try again.");
      }
    }

    saving = false;
  }

  async function syncFinance(contact: ContactAccountListItem) {
    try {
      await api.post(`/crm/contacts/${contact.id}/sync_finance/`, {});
      toast.success("Finance sync complete", `${contact.display_name} synced to customer ledger.`);
      await Promise.all([fetchContacts(), fetchOverview()]);
    } catch (err) {
      console.error("[crm/contacts]", err);
      toast.error("Sync failed", "Could not sync contact to Finance.");
    }
  }

  async function requestReview(contact: ContactAccountListItem) {
    try {
      await api.post(`/crm/contacts/${contact.id}/request_kyc_review/`, {});
      toast.success("Review requested", "Compliance has been notified.");
      await Promise.all([fetchContacts(), fetchOverview()]);
    } catch (err) {
      console.error("[crm/contacts]", err);
      if (err instanceof ApiError && err.status === 400) {
        toast.error("No document found", "Upload a KYC document before requesting a review.");
      } else {
        toast.error("Request failed", "Could not trigger compliance review.");
      }
    }
  }

  function openCreate() {
    resetCreateForm();
    showCreate = true;
  }

  function goToPage(page: number) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    fetchContacts();
  }

  function openContact(contactId: number, syncUrl = true) {
    suppressOpenParamSync = false;
    selectedContactId = contactId;
    showContactDetailDrawer = true;
    showCreate = false;
    if (!syncUrl) return;
    const params = new URLSearchParams($page.url.searchParams);
    params.set("open", String(contactId));
    goto(`/crm/contacts?${params.toString()}`, {
      replaceState: true,
      noScroll: true,
      keepFocus: true,
    });
  }

  function closeContactDrawer() {
    showContactDetailDrawer = false;
    if (!$page.url.searchParams.has("open")) {
      selectedContactId = null;
      suppressOpenParamSync = false;
      return;
    }

    suppressOpenParamSync = true;
    const params = new URLSearchParams($page.url.searchParams);
    params.delete("open");
    const query = params.toString();
    void goto(query ? `/crm/contacts?${query}` : "/crm/contacts", {
      replaceState: true,
      noScroll: true,
      keepFocus: true,
    }).finally(() => {
      selectedContactId = null;
      suppressOpenParamSync = false;
    });
  }

  let debounceTimer: ReturnType<typeof setTimeout>;

  function handleSearch(value: string) {
    search = value;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      currentPage = 1;
      fetchContacts();
    }, 300);
  }

  function updateFilters() {
    currentPage = 1;
    fetchContacts();
  }

  $effect(() => {
    if (suppressOpenParamSync) return;
    const openParam = $page.url.searchParams.get("open");
    if (!openParam) return;
    const id = Number(openParam);
    if (!Number.isInteger(id) || id <= 0) return;
    if (selectedContactId === id) return;
    openContact(id, false);
  });

  onMount(() => {
    void fetchOverview();
    void fetchContacts();
  });
</script>

<div class="space-y-6">
  <div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-600">CRM</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Contact & Account Management</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Structured profiles for individuals and organizations, with KYC, financial capacity, preferences, and linked activity.
      </p>
    </div>
    <div class="flex gap-2">
      <button
        type="button"
        class="rounded-xl border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
        onclick={() => {
          fetchOverview();
          fetchContacts();
        }}
      >
        Refresh
      </button>
      <button
        type="button"
        class="rounded-xl bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800"
        onclick={openCreate}
      >
        New contact
      </button>
    </div>
  </div>

  <section class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
    <article class="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
      <p class="text-xs font-semibold uppercase tracking-wide text-emerald-700">Total Contacts</p>
      <p class="mt-2 text-2xl font-semibold text-emerald-950">{overviewLoading ? "\u2014" : (overview?.total_contacts ?? 0)}</p>
      <p class="mt-2 text-xs text-emerald-700">
        {overviewLoading ? "" : `${overview?.individual_contacts ?? 0} individuals \u2022 ${overview?.organization_accounts ?? 0} organizations`}
      </p>
    </article>

    <article class="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
      <p class="text-xs font-semibold uppercase tracking-wide text-emerald-700">KYC Health</p>
      <p class="mt-2 text-2xl font-semibold text-emerald-950">{overviewLoading ? "\u2014" : (overview?.kyc_verified ?? 0)}</p>
      <p class="mt-2 text-xs text-emerald-700">
        {overviewLoading ? "" : `${overview?.kyc_pending ?? 0} pending review`}
      </p>
    </article>

    <article class="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
      <p class="text-xs font-semibold uppercase tracking-wide text-emerald-700">Finance Sync</p>
      <p class="mt-2 text-2xl font-semibold text-emerald-950">{overviewLoading ? "\u2014" : (overview?.finance_synced ?? 0)}</p>
      <p class="mt-2 text-xs text-emerald-700">Contacts mirrored in customer ledger</p>
    </article>

    <article class="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
      <p class="text-xs font-semibold uppercase tracking-wide text-emerald-700">Priority Queue</p>
      <p class="mt-2 text-2xl font-semibold text-emerald-950">{overviewLoading ? "\u2014" : (overview?.follow_up_due ?? 0)}</p>
      <p class="mt-2 text-xs text-emerald-700">
        {overviewLoading ? "" : `${overview?.high_value_contacts ?? 0} high-value contacts`}
      </p>
    </article>
  </section>

  <section class="rounded-2xl border border-neutral-200 bg-white p-4 sm:p-5">
    <div class="grid gap-3 lg:grid-cols-4">
      <div class="lg:col-span-2">
        <label for="contact-search" class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Search</label>
        <input
          id="contact-search"
          type="search"
          class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900 outline-none transition focus:border-neutral-400"
          placeholder="Name, email, phone, registration"
          value={search}
          oninput={(e) => handleSearch((e.currentTarget as HTMLInputElement).value)}
        />
      </div>

      <div>
        <label for="entity-filter" class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Entity</label>
        <select
          id="entity-filter"
          class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900 outline-none transition focus:border-neutral-400"
          bind:value={entityFilter}
          onchange={updateFilters}
        >
          <option value="">All</option>
          <option value="individual">Individual</option>
          <option value="organization">Organization</option>
        </select>
      </div>

      <div>
        <label for="kyc-filter" class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">KYC</label>
        <select
          id="kyc-filter"
          class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900 outline-none transition focus:border-neutral-400"
          bind:value={kycFilter}
          onchange={updateFilters}
        >
          <option value="">All</option>
          <option value="not_submitted">Not submitted</option>
          <option value="pending_review">Pending review</option>
          <option value="under_review">Under review</option>
          <option value="verified">Verified</option>
          <option value="rejected">Rejected</option>
        </select>
      </div>

      <div>
        <label for="active-filter" class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Status</label>
        <select
          id="active-filter"
          class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900 outline-none transition focus:border-neutral-400"
          bind:value={activeFilter}
          onchange={updateFilters}
        >
          <option value="">All</option>
          <option value="true">Active</option>
          <option value="false">Inactive</option>
        </select>
      </div>
    </div>
  </section>

  <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
    <div class="overflow-x-auto">
      <table class="min-w-full divide-y divide-neutral-200 text-sm">
        <thead class="bg-neutral-50 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">
          <tr>
            <th class="px-4 py-3">Contact</th>
            <th class="px-4 py-3">Entity</th>
            <th class="px-4 py-3">KYC</th>
            <th class="px-4 py-3">Financial Capacity</th>
            <th class="px-4 py-3">Preferences</th>
            <th class="px-4 py-3">Linked Data</th>
            <th class="px-4 py-3">Finance</th>
            <th class="px-4 py-3 text-right">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#if loading}
            <tr>
              <td colspan="8" class="px-4 py-10 text-center text-sm text-neutral-500">Loading contacts...</td>
            </tr>
          {:else if listError}
            <tr>
              <td colspan="8" class="px-4 py-6">
                <DataStateBanner
                  title="Couldn't load contacts"
                  message={listError}
                  onretry={fetchContacts}
                />
              </td>
            </tr>
          {:else if contacts.length === 0}
            <tr>
              <td colspan="8" class="px-4 py-10 text-center text-sm text-neutral-500">No contacts found for current filters.</td>
            </tr>
          {:else}
            {#each contacts as contact}
              <tr class="hover:bg-neutral-50">
                <td class="px-4 py-3 align-top">
                  <button
                    type="button"
                    class="text-left"
                    onclick={() => openContact(contact.id)}
                  >
                    <p class="font-semibold text-neutral-900 hover:text-neutral-700">{contact.display_name}</p>
                    <p class="mt-0.5 text-xs text-neutral-500">{contact.email || "No email"} \u2022 {contact.phone || "No phone"}</p>
                  </button>
                </td>
                <td class="px-4 py-3 align-top">
                  <span class={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${entityBadgeClass(contact.entity_type)}`}>
                    {contact.entity_type_display}
                  </span>
                </td>
                <td class="px-4 py-3 align-top">
                  <span class={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${statusBadgeClass(contact.kyc_status)}`}>
                    {contact.kyc_status_display}
                  </span>
                </td>
                <td class="px-4 py-3 align-top text-neutral-700">
                  <p>{formatBudget(contact.budget_min, contact.budget_max)}</p>
                  <p class="mt-0.5 text-xs text-neutral-500">{contact.risk_profile_display}</p>
                </td>
                <td class="px-4 py-3 align-top text-neutral-700">
                  <p class="line-clamp-1 text-xs">{contact.preferred_locations?.join(", ") || "\u2014"}</p>
                  <p class="mt-0.5 line-clamp-1 text-xs text-neutral-500">{contact.preferred_property_types?.join(", ") || "\u2014"}</p>
                </td>
                <td class="px-4 py-3 align-top text-xs text-neutral-600">
                  <p>{contact.interaction_count} interactions</p>
                  <p>{contact.active_deal_count} active deals</p>
                  <p>{contact.document_count} docs</p>
                </td>
                <td class="px-4 py-3 align-top text-xs text-neutral-600">
                  <p>{contact.finance_customer_name ?? "Not synced"}</p>
                  <p class="mt-0.5 text-neutral-500">{formatDateTime(contact.finance_synced_at)}</p>
                </td>
                <td class="px-4 py-3 align-top">
                  <div class="flex items-center justify-end gap-2">
                    <button
                      type="button"
                      class="rounded-lg border border-neutral-200 px-2.5 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-100"
                      onclick={() => syncFinance(contact)}
                    >
                      Sync finance
                    </button>
                    <button
                      type="button"
                      class="rounded-lg border border-neutral-200 px-2.5 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-100"
                      onclick={() => requestReview(contact)}
                    >
                      Request KYC
                    </button>
                    <button
                      type="button"
                      class="rounded-lg bg-neutral-900 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-neutral-800"
                      onclick={() => openContact(contact.id)}
                    >
                      Open
                    </button>
                  </div>
                </td>
              </tr>
            {/each}
          {/if}
        </tbody>
      </table>
    </div>

    <div class="flex flex-col gap-3 border-t border-neutral-200 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <p class="text-xs text-neutral-500">Showing {(currentPage - 1) * pageSize + 1} - {Math.min(currentPage * pageSize, totalCount)} of {totalCount}</p>
      <div class="flex items-center gap-1">
        <button
          type="button"
          class="rounded-lg border border-neutral-200 px-2 py-1 text-xs text-neutral-700 disabled:opacity-40"
          disabled={currentPage === 1}
          onclick={() => goToPage(currentPage - 1)}
        >
          Prev
        </button>
        {#each pageNumbers as page}
          <button
            type="button"
            class={`rounded-lg px-2 py-1 text-xs ${page === currentPage ? "bg-neutral-900 text-white" : "border border-neutral-200 text-neutral-700"}`}
            onclick={() => goToPage(page)}
          >
            {page}
          </button>
        {/each}
        <button
          type="button"
          class="rounded-lg border border-neutral-200 px-2 py-1 text-xs text-neutral-700 disabled:opacity-40"
          disabled={currentPage === totalPages}
          onclick={() => goToPage(currentPage + 1)}
        >
          Next
        </button>
      </div>
    </div>
  </section>
</div>

<svelte:window
  onkeydown={(event) => {
    if (event.key !== "Escape") return;
    if (showContactDetailDrawer) {
      closeContactDrawer();
      return;
    }
    if (showCreate) showCreate = false;
  }}
/>

{#if showContactDetailDrawer && selectedContactId !== null}
  <button
    type="button"
    class="fixed inset-0 z-998 bg-black/40 backdrop-blur-sm"
    onclick={closeContactDrawer}
    aria-label="Close contact detail drawer"
  ></button>

  <aside class="fixed inset-y-0 right-0 z-999 w-full max-w-7xl overflow-y-auto border-l border-neutral-200 bg-white">
    <div class="sticky top-0 z-10 flex items-center justify-between border-b border-neutral-200 bg-white/95 px-5 py-3 backdrop-blur">
      <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-500">Contact Detail</h2>
      <button
        type="button"
        class="rounded-lg border border-neutral-200 px-2.5 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-100"
        onclick={closeContactDrawer}
      >
        Close
      </button>
    </div>
    <div class="p-5 sm:p-6">
      <ContactDetailPage contactId={selectedContactId} embedded={true} />
    </div>
  </aside>
{/if}

{#if showCreate}
  <div class="fixed inset-0 z-40 flex">
    <button
      type="button"
      class="h-full flex-1 bg-black/40"
      onclick={() => (showCreate = false)}
      aria-label="Close new contact panel"
    ></button>

    <aside class="h-full w-full max-w-2xl overflow-y-auto border-l border-neutral-200 bg-white p-5 sm:p-6">
      <div class="flex items-start justify-between gap-3">
        <div>
          <h2 class="text-lg font-semibold text-neutral-900">New Contact Account</h2>
          <p class="mt-1 text-sm text-neutral-500">Capture profile, capacity, preferences, and KYC context.</p>
        </div>
        <button
          type="button"
          class="rounded-lg border border-neutral-200 px-2.5 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-100"
          onclick={() => (showCreate = false)}
        >
          Close
        </button>
      </div>

      <form class="mt-6 space-y-5" onsubmit={createContact}>
        <section class="grid gap-3 sm:grid-cols-2">
          <label class="text-sm text-neutral-700">
            <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Entity Type</span>
            <select
              class="w-full rounded-xl border border-neutral-200 px-3 py-2"
              bind:value={createForm.entity_type}
            >
              <option value="individual">Individual</option>
              <option value="organization">Organization</option>
            </select>
          </label>

          <label class="text-sm text-neutral-700">
            <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">KYC Status</span>
            <select class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={createForm.kyc_status}>
              <option value="not_submitted">Not submitted</option>
              <option value="pending_review">Pending review</option>
              <option value="under_review">Under review</option>
              <option value="verified">Verified</option>
              <option value="rejected">Rejected</option>
            </select>
          </label>
        </section>

        <section class="grid gap-3 sm:grid-cols-2">
          <label class="text-sm text-neutral-700">
            <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">First Name</span>
            <input class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={createForm.first_name} />
            {#if fieldError("first_name")}<p class="mt-1 text-xs text-rose-600">{fieldError("first_name")}</p>{/if}
          </label>

          <label class="text-sm text-neutral-700">
            <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Last Name</span>
            <input class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={createForm.last_name} />
            {#if fieldError("last_name")}<p class="mt-1 text-xs text-rose-600">{fieldError("last_name")}</p>{/if}
          </label>

          <label class="text-sm text-neutral-700 sm:col-span-2">
            <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Legal Name (Organization)</span>
            <input class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={createForm.legal_name} />
          </label>

          <label class="text-sm text-neutral-700">
            <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Trade Name</span>
            <input class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={createForm.trade_name} />
          </label>

          <label class="text-sm text-neutral-700">
            <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Primary Contact Name</span>
            <input class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={createForm.primary_contact_name} />
          </label>

          <label class="text-sm text-neutral-700">
            <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Email</span>
            <input type="email" class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={createForm.email} />
            {#if fieldError("email")}<p class="mt-1 text-xs text-rose-600">{fieldError("email")}</p>{/if}
          </label>

          <label class="text-sm text-neutral-700">
            <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Phone</span>
            <input class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={createForm.phone} />
            {#if fieldError("phone")}<p class="mt-1 text-xs text-rose-600">{fieldError("phone")}</p>{/if}
          </label>

          <label class="text-sm text-neutral-700">
            <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Secondary Phone</span>
            <input class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={createForm.secondary_phone} />
          </label>

          <label class="text-sm text-neutral-700">
            <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">City</span>
            <input class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={createForm.city} />
          </label>

          <label class="text-sm text-neutral-700">
            <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Country</span>
            <input class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={createForm.country} />
          </label>

          <label class="text-sm text-neutral-700 sm:col-span-2">
            <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Address</span>
            <textarea rows="2" class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={createForm.address}></textarea>
          </label>
        </section>

        <section class="grid gap-3 sm:grid-cols-2">
          <label class="text-sm text-neutral-700">
            <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Budget Min</span>
            <input type="number" min="0" class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={createForm.budget_min} />
          </label>

          <label class="text-sm text-neutral-700">
            <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Budget Max</span>
            <input type="number" min="0" class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={createForm.budget_max} />
            {#if fieldError("budget_max")}<p class="mt-1 text-xs text-rose-600">{fieldError("budget_max")}</p>{/if}
          </label>

          <label class="text-sm text-neutral-700">
            <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Annual Income</span>
            <input type="number" min="0" class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={createForm.annual_income} />
          </label>

          <label class="text-sm text-neutral-700">
            <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Net Worth</span>
            <input type="number" min="0" class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={createForm.net_worth} />
          </label>

          <label class="text-sm text-neutral-700">
            <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Liquidity Estimate</span>
            <input type="number" min="0" class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={createForm.liquidity_estimate} />
          </label>

          <label class="text-sm text-neutral-700">
            <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Risk Profile</span>
            <select class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={createForm.risk_profile}>
              <option value="undisclosed">Undisclosed</option>
              <option value="conservative">Conservative</option>
              <option value="balanced">Balanced</option>
              <option value="aggressive">Aggressive</option>
            </select>
          </label>

          <label class="text-sm text-neutral-700 sm:col-span-2">
            <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Preferred Locations (comma separated)</span>
            <input class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={createForm.preferred_locations} />
          </label>

          <label class="text-sm text-neutral-700 sm:col-span-2">
            <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Preferred Property Types (comma separated)</span>
            <input class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={createForm.preferred_property_types} />
          </label>

          <label class="text-sm text-neutral-700 sm:col-span-2">
            <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Preference Notes</span>
            <textarea rows="2" class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={createForm.preference_notes}></textarea>
          </label>

          <label class="text-sm text-neutral-700 sm:col-span-2">
            <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Interaction Summary</span>
            <textarea rows="2" class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={createForm.interaction_summary}></textarea>
          </label>

          <label class="text-sm text-neutral-700 sm:col-span-2">
            <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Notes</span>
            <textarea rows="2" class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={createForm.notes}></textarea>
          </label>
        </section>

        <label class="flex items-center gap-2 text-sm text-neutral-700">
          <input type="checkbox" class="h-4 w-4 rounded border-neutral-300" bind:checked={createForm.is_active} />
          Active profile
        </label>

        <div class="flex items-center justify-end gap-2 border-t border-neutral-200 pt-4">
          {#if isDev}
            <button type="button" onclick={devFillContact} class="mr-auto rounded-xl bg-orange-500 px-4 py-2 text-sm font-semibold text-white hover:bg-orange-600 transition-colors">Dev Fill</button>
          {/if}
          <button
            type="button"
            class="rounded-xl border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100"
            onclick={() => (showCreate = false)}
          >
            Cancel
          </button>
          <button
            type="submit"
            class="rounded-xl bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
            disabled={saving}
          >
            {saving ? "Saving..." : "Create contact"}
          </button>
        </div>
      </form>
    </aside>
  </div>
{/if}

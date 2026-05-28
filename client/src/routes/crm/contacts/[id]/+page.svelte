<script lang="ts">
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import Breadcrumb from "$lib/components/Breadcrumb.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    ContactAccountDetail,
    ContactComplianceReview,
    ContactDealStatus,
    ContactDocumentType,
    ContactEntityType,
    ContactInteractionType,
    ContactKYCStatus,
    ContactRelationshipType,
    ContactRiskProfile,
    PaginatedResponse,
  } from "$lib/types";

  let {
    contactId: contactIdProp = null,
    embedded = false,
  }: {
    contactId?: number | string | null;
    embedded?: boolean;
  } = $props();

  const contactId = $derived(String(contactIdProp ?? $page.params.id ?? ""));

  type Tab = "overview" | "interactions" | "deals" | "properties" | "documents" | "compliance";

  let activeTab = $state<Tab | null>("overview");
  let loading = $state(true);
  let savingProfile = $state(false);
  let syncingFinance = $state(false);
  let requestingKycReview = $state(false);

  let contact = $state<ContactAccountDetail | null>(null);

  let leads = $state<{ id: number; label: string }[]>([]);
  let reservations = $state<{ id: number; label: string }[]>([]);
  let projects = $state<{ id: number; label: string }[]>([]);
  let properties = $state<{ id: number; label: string }[]>([]);
  let units = $state<{ id: number; label: string }[]>([]);

  let profileErrors = $state<Record<string, string[]>>({});
  let profileForm = $state({
    entity_type: "individual" as ContactEntityType,
    first_name: "",
    middle_name: "",
    last_name: "",
    title: "",
    date_of_birth: "",
    nationality: "",
    legal_name: "",
    trade_name: "",
    registration_number: "",
    tax_identification_number: "",
    primary_contact_name: "",
    email: "",
    phone: "",
    secondary_phone: "",
    address: "",
    city: "",
    country: "",
    kyc_status: "not_submitted" as ContactKYCStatus,
    kyc_reference_number: "",
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

  let interactionForm = $state({
    interaction_type: "note" as ContactInteractionType,
    subject: "",
    details: "",
    happened_at: "",
    follow_up_required: false,
    follow_up_due_at: "",
  });
  let savingInteraction = $state(false);

  let dealForm = $state({
    lead: "",
    reservation: "",
    deal_name: "",
    stage: "",
    status: "active" as ContactDealStatus,
    deal_value: "",
    close_probability: "0",
    notes: "",
  });
  let savingDeal = $state(false);

  let propertyForm = $state({
    project: "",
    property: "",
    unit: "",
    relationship_type: "interested" as ContactRelationshipType,
    budget_estimate: "",
    notes: "",
  });
  let savingProperty = $state(false);

  let documentForm = $state({
    document_type: "other" as ContactDocumentType,
    file_name: "",
    file_url: "",
    reference_number: "",
    issued_at: "",
    expires_at: "",
    is_kyc_document: true,
    notes: "",
  });
  let savingDocument = $state(false);

  function toggleTab(tab: Tab) {
    activeTab = activeTab === tab ? null : tab;
  }

  function parseList(raw: string): string[] {
    return raw
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function parseDateTimeLocal(value: string): string | null {
    if (!value) return null;
    const dt = new Date(value);
    return Number.isNaN(dt.getTime()) ? null : dt.toISOString();
  }

  function fmtDate(value: string | null | undefined): string {
    if (!value) return "\u2014";
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return "\u2014";
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  function fmtDateTime(value: string | null | undefined): string {
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

  function fmtMoney(value: string | null | undefined): string {
    if (!value) return "\u2014";
    return currency.format(Number(value));
  }

  function kycBadge(status: ContactKYCStatus): string {
    if (status === "verified") return "bg-emerald-100 text-emerald-700";
    if (status === "rejected") return "bg-rose-100 text-rose-700";
    if (status === "pending_review" || status === "under_review") return "bg-amber-100 text-amber-700";
    return "bg-neutral-100 text-neutral-600";
  }

  function entityBadge(entity: ContactEntityType): string {
    return entity === "organization" ? "bg-sky-100 text-sky-700" : "bg-violet-100 text-violet-700";
  }

  function complianceBadge(status: ContactComplianceReview["status"]): string {
    if (status === "approved") return "bg-emerald-100 text-emerald-700";
    if (status === "rejected") return "bg-rose-100 text-rose-700";
    if (status === "in_review") return "bg-blue-100 text-blue-700";
    return "bg-amber-100 text-amber-700";
  }

  function profileFieldError(field: string): string {
    return profileErrors[field]?.[0] ?? "";
  }

  function populateProfileForm(data: ContactAccountDetail) {
    profileForm = {
      entity_type: data.entity_type,
      first_name: data.first_name,
      middle_name: data.middle_name,
      last_name: data.last_name,
      title: data.title,
      date_of_birth: data.date_of_birth ?? "",
      nationality: data.nationality,
      legal_name: data.legal_name,
      trade_name: data.trade_name,
      registration_number: data.registration_number,
      tax_identification_number: data.tax_identification_number,
      primary_contact_name: data.primary_contact_name,
      email: data.email,
      phone: data.phone,
      secondary_phone: data.secondary_phone,
      address: data.address,
      city: data.city,
      country: data.country,
      kyc_status: data.kyc_status,
      kyc_reference_number: data.kyc_reference_number,
      annual_income: data.annual_income ?? "",
      net_worth: data.net_worth ?? "",
      liquidity_estimate: data.liquidity_estimate ?? "",
      budget_min: data.budget_min ?? "",
      budget_max: data.budget_max ?? "",
      risk_profile: data.risk_profile,
      preferred_locations: data.preferred_locations.join(", "),
      preferred_property_types: data.preferred_property_types.join(", "),
      preference_notes: data.preference_notes,
      interaction_summary: data.interaction_summary,
      notes: data.notes,
      is_active: data.is_active,
    };
  }

  async function loadContact() {
    loading = true;
    try {
      const res = await api.get<ContactAccountDetail>(`/crm/contacts/${contactId}/`);
      contact = res;
      populateProfileForm(res);
      profileErrors = {};
    } catch {
      contact = null;
    }
    loading = false;
  }

  async function loadReferenceData() {
    try {
      const [leadRes, reservationRes, projectRes, propertyRes, unitRes] = await Promise.all([
        api.get<PaginatedResponse<{ id: number; first_name: string; last_name: string }>>("/crm/leads/", {
          page_size: "200",
          status: "active",
        }),
        api.get<PaginatedResponse<{ id: number; reservation_number: string }>>("/crm/reservations/", {
          page_size: "200",
        }),
        api.get<PaginatedResponse<{ id: number; name: string }>>("/projects/projects/", { page_size: "200" }),
        api.get<PaginatedResponse<{ id: number; name: string }>>("/properties/", { page_size: "200" }),
        api.get<PaginatedResponse<{ id: number; unit_number: string; property_name?: string }>>("/properties/units/", {
          page_size: "200",
        }),
      ]);

      leads = leadRes.results.map((item) => ({
        id: item.id,
        label: `${item.first_name} ${item.last_name}`.trim() || `Lead #${item.id}`,
      }));
      reservations = reservationRes.results.map((item) => ({
        id: item.id,
        label: item.reservation_number,
      }));
      projects = projectRes.results.map((item) => ({ id: item.id, label: item.name }));
      properties = propertyRes.results.map((item) => ({ id: item.id, label: item.name }));
      units = unitRes.results.map((item) => ({
        id: item.id,
        label: item.property_name ? `${item.unit_number} - ${item.property_name}` : item.unit_number,
      }));
    } catch {
      leads = [];
      reservations = [];
      projects = [];
      properties = [];
      units = [];
    }
  }

  async function saveProfile(e: Event) {
    e.preventDefault();
    if (!contact) return;

    savingProfile = true;
    profileErrors = {};

    try {
      const payload: Record<string, unknown> = {
        entity_type: profileForm.entity_type,
        first_name: profileForm.first_name,
        middle_name: profileForm.middle_name,
        last_name: profileForm.last_name,
        title: profileForm.title,
        date_of_birth: profileForm.date_of_birth || null,
        nationality: profileForm.nationality,
        legal_name: profileForm.legal_name,
        trade_name: profileForm.trade_name,
        registration_number: profileForm.registration_number,
        tax_identification_number: profileForm.tax_identification_number,
        primary_contact_name: profileForm.primary_contact_name,
        email: profileForm.email,
        phone: profileForm.phone,
        secondary_phone: profileForm.secondary_phone,
        address: profileForm.address,
        city: profileForm.city,
        country: profileForm.country,
        kyc_status: profileForm.kyc_status,
        kyc_reference_number: profileForm.kyc_reference_number,
        annual_income: profileForm.annual_income || null,
        net_worth: profileForm.net_worth || null,
        liquidity_estimate: profileForm.liquidity_estimate || null,
        budget_min: profileForm.budget_min || null,
        budget_max: profileForm.budget_max || null,
        risk_profile: profileForm.risk_profile,
        preferred_locations: parseList(profileForm.preferred_locations),
        preferred_property_types: parseList(profileForm.preferred_property_types),
        preference_notes: profileForm.preference_notes,
        interaction_summary: profileForm.interaction_summary,
        notes: profileForm.notes,
        is_active: profileForm.is_active,
      };

      const res = await api.patch<ContactAccountDetail>(`/crm/contacts/${contact.id}/`, payload);
      contact = res;
      populateProfileForm(res);
      toast.success("Profile updated", "Contact account changes saved.");
    } catch (err) {
      if (err instanceof ApiError) {
        profileErrors = err.fieldErrors;
        toast.error("Validation error", "Please check highlighted profile fields.");
      } else {
        toast.error("Update failed", "Could not save profile updates.");
      }
    }

    savingProfile = false;
  }

  async function syncFinance() {
    if (!contact || syncingFinance) return;
    syncingFinance = true;
    try {
      await api.post(`/crm/contacts/${contact.id}/sync_finance/`, {});
      toast.success("Finance sync complete", "Contact synced to customer ledger.");
      await loadContact();
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        toast.error("Permission denied", "You do not have permission to sync to Finance.");
      } else {
        toast.error("Sync failed", "Could not sync contact to Finance.");
      }
    }
    syncingFinance = false;
  }

  async function requestKycReview(documentId?: number) {
    if (!contact || requestingKycReview) return;
    requestingKycReview = true;
    try {
      const payload = documentId ? { document: documentId } : {};
      await api.post(`/crm/contacts/${contact.id}/request_kyc_review/`, payload);
      toast.success("Review requested", "Compliance team has been notified.");
      await loadContact();
      activeTab = "compliance";
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        toast.error("Review request failed", "Upload a KYC document before requesting a review.");
      } else if (err instanceof ApiError && err.status === 403) {
        toast.error("Permission denied", "You do not have permission to request KYC reviews.");
      } else {
        toast.error("Review request failed", "Could not request compliance review.");
      }
    }
    requestingKycReview = false;
  }

  async function addInteraction(e: Event) {
    e.preventDefault();
    if (!contact) return;

    savingInteraction = true;
    try {
      const payload: Record<string, unknown> = {
        interaction_type: interactionForm.interaction_type,
        subject: interactionForm.subject,
        details: interactionForm.details,
        happened_at: parseDateTimeLocal(interactionForm.happened_at) ?? new Date().toISOString(),
        follow_up_required: interactionForm.follow_up_required,
        follow_up_due_at: parseDateTimeLocal(interactionForm.follow_up_due_at),
      };
      await api.post(`/crm/contacts/${contact.id}/interactions/`, payload);
      interactionForm = {
        interaction_type: "note",
        subject: "",
        details: "",
        happened_at: "",
        follow_up_required: false,
        follow_up_due_at: "",
      };
      toast.success("Interaction logged", "Contact timeline has been updated.");
      await loadContact();
    } catch {
      toast.error("Could not add interaction", "Please try again.");
    }
    savingInteraction = false;
  }

  async function addDealLink(e: Event) {
    e.preventDefault();
    if (!contact) return;

    savingDeal = true;
    try {
      const payload: Record<string, unknown> = {
        lead: dealForm.lead ? Number(dealForm.lead) : null,
        reservation: dealForm.reservation ? Number(dealForm.reservation) : null,
        deal_name: dealForm.deal_name,
        stage: dealForm.stage,
        status: dealForm.status,
        deal_value: dealForm.deal_value || null,
        close_probability: Number(dealForm.close_probability) || 0,
        notes: dealForm.notes,
      };
      await api.post(`/crm/contacts/${contact.id}/deal-links/`, payload);
      dealForm = {
        lead: "",
        reservation: "",
        deal_name: "",
        stage: "",
        status: "active",
        deal_value: "",
        close_probability: "0",
        notes: "",
      };
      toast.success("Deal linked", "Contact now has an updated deal mapping.");
      await loadContact();
    } catch {
      toast.error("Could not link deal", "Check that linked records belong to this organization.");
    }
    savingDeal = false;
  }

  async function addPropertyLink(e: Event) {
    e.preventDefault();
    if (!contact) return;

    savingProperty = true;
    try {
      const payload: Record<string, unknown> = {
        project: propertyForm.project ? Number(propertyForm.project) : null,
        property: propertyForm.property ? Number(propertyForm.property) : null,
        unit: propertyForm.unit ? Number(propertyForm.unit) : null,
        relationship_type: propertyForm.relationship_type,
        budget_estimate: propertyForm.budget_estimate || null,
        notes: propertyForm.notes,
      };
      await api.post(`/crm/contacts/${contact.id}/property-links/`, payload);
      propertyForm = {
        project: "",
        property: "",
        unit: "",
        relationship_type: "interested",
        budget_estimate: "",
        notes: "",
      };
      toast.success("Property link added", "Contact property mapping has been updated.");
      await loadContact();
    } catch {
      toast.error("Could not link property", "Check that selected records belong to this organization.");
    }
    savingProperty = false;
  }

  async function addDocument(e: Event) {
    e.preventDefault();
    if (!contact) return;

    savingDocument = true;
    const shouldOpenCompliance = documentForm.is_kyc_document;
    try {
      const payload: Record<string, unknown> = {
        document_type: documentForm.document_type,
        file_name: documentForm.file_name,
        file_url: documentForm.file_url,
        reference_number: documentForm.reference_number,
        issued_at: documentForm.issued_at || null,
        expires_at: documentForm.expires_at || null,
        is_kyc_document: documentForm.is_kyc_document,
        notes: documentForm.notes,
      };
      await api.post(`/crm/contacts/${contact.id}/documents/`, payload);
      documentForm = {
        document_type: "other",
        file_name: "",
        file_url: "",
        reference_number: "",
        issued_at: "",
        expires_at: "",
        is_kyc_document: true,
        notes: "",
      };
      toast.success("Document uploaded", "Document has been attached to this contact.");
      await loadContact();
      if (shouldOpenCompliance) activeTab = "compliance";
    } catch {
      toast.error("Upload failed", "Could not save document.");
    }
    savingDocument = false;
  }

  async function complianceAction(reviewId: number, action: "mark_in_review" | "approve" | "reject") {
    if (!contact) return;

    try {
      const payload = action === "reject" ? { notes: "Rejected after review." } : {};
      await api.post(`/crm/contacts/${contact.id}/compliance-reviews/${reviewId}/${action}/`, payload);
      toast.success("Review updated", "Compliance review status changed.");
      await loadContact();
    } catch {
      toast.error("Update failed", "Could not update review status.");
    }
  }

  $effect(() => {
    void contactId;
    loadContact();
    loadReferenceData();
  });
</script>

<div class={embedded ? "space-y-6" : "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6"}>
  {#if !embedded}
    <Breadcrumb
      items={[
        { label: "Operations", href: "/crm" },
        { label: "CRM", href: "/crm" },
        { label: "Contact & Account Management", href: "/crm/contacts" },
        { label: contact?.display_name ?? "Contact" },
      ]}
    />
  {/if}

  {#if loading}
    <section class="rounded-2xl border border-neutral-200 bg-white p-8 text-center text-sm text-neutral-500">
      Loading contact profile...
    </section>
  {:else if !contact}
    <section class="rounded-2xl border border-neutral-200 bg-white p-8 text-center text-sm text-neutral-500">
      Contact not found.
      <button
        type="button"
        class="ml-3 rounded-lg border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-100"
        on:click={() => goto("/crm/contacts")}
      >
        Back to contacts
      </button>
    </section>
  {:else}
    <section class="rounded-2xl border border-neutral-200 bg-white p-6">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h1 class="text-2xl font-bold text-neutral-900">{contact.display_name}</h1>
          <div class="mt-2 flex flex-wrap items-center gap-2">
            <span class={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${entityBadge(contact.entity_type)}`}>
              {contact.entity_type_display}
            </span>
            <span class={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${kycBadge(contact.kyc_status)}`}>
              {contact.kyc_status_display}
            </span>
            <span class="inline-flex rounded-full bg-neutral-100 px-2 py-1 text-xs font-medium text-neutral-700">
              {contact.is_active ? "Active" : "Inactive"}
            </span>
          </div>
          <p class="mt-3 text-sm text-neutral-500">{contact.email || "No email"} \u2022 {contact.phone || "No phone"}</p>
          <p class="mt-1 text-sm text-neutral-500">Finance customer: {contact.finance_customer_name ?? "Not synced"}</p>
        </div>

        <div class="flex flex-wrap gap-2">
          <button
            type="button"
            class="rounded-xl border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={syncingFinance}
            on:click={syncFinance}
          >
            {syncingFinance ? "Syncing..." : "Sync to Finance"}
          </button>
          <button
            type="button"
            class="rounded-xl border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={requestingKycReview}
            on:click={() => requestKycReview()}
          >
            {requestingKycReview ? "Requesting..." : "Request KYC Review"}
          </button>
          <button
            type="button"
            class="rounded-xl bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800"
            on:click={loadContact}
          >
            Refresh
          </button>
        </div>
      </div>

      <div class="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <article class="rounded-xl border border-neutral-200 p-3">
          <p class="text-xs uppercase tracking-wide text-neutral-500">Budget Window</p>
          <p class="mt-1 text-sm font-semibold text-neutral-900">{fmtMoney(contact.budget_min)} - {fmtMoney(contact.budget_max)}</p>
        </article>
        <article class="rounded-xl border border-neutral-200 p-3">
          <p class="text-xs uppercase tracking-wide text-neutral-500">Risk Profile</p>
          <p class="mt-1 text-sm font-semibold text-neutral-900">{contact.risk_profile_display}</p>
        </article>
        <article class="rounded-xl border border-neutral-200 p-3">
          <p class="text-xs uppercase tracking-wide text-neutral-500">Interactions</p>
          <p class="mt-1 text-sm font-semibold text-neutral-900">{contact.interaction_count}</p>
        </article>
        <article class="rounded-xl border border-neutral-200 p-3">
          <p class="text-xs uppercase tracking-wide text-neutral-500">Documents</p>
          <p class="mt-1 text-sm font-semibold text-neutral-900">{contact.document_count}</p>
        </article>
      </div>
    </section>

    <section class="space-y-0">
      <section class="rounded-2xl border border-neutral-200 bg-white">
      <button
        type="button"
        class="flex w-full items-center justify-between gap-3 px-4 py-3 text-left sm:px-5"
        aria-expanded={activeTab === "overview"}
        on:click={() => toggleTab("overview")}
      >
        <span class="text-sm font-semibold text-neutral-900 sm:text-base">Overview</span>
        <span class="text-xs font-semibold uppercase tracking-wide text-neutral-500">
          {activeTab === "overview" ? "Collapse" : "Expand"}
        </span>
      </button>
      </section>

    {#if activeTab === "overview"}
      <section class="rounded-2xl border border-neutral-200 bg-white p-5 sm:p-6">
        <h2 class="text-lg font-semibold text-neutral-900">Profile & Account Details</h2>
        <form class="mt-5 space-y-5" on:submit={saveProfile}>
          <div class="grid gap-3 sm:grid-cols-2">
            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Entity Type</span>
              <select class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={profileForm.entity_type}>
                <option value="individual">Individual</option>
                <option value="organization">Organization</option>
              </select>
            </label>

            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">KYC Status</span>
              <select class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={profileForm.kyc_status}>
                <option value="not_submitted">Not submitted</option>
                <option value="pending_review">Pending review</option>
                <option value="under_review">Under review</option>
                <option value="verified">Verified</option>
                <option value="rejected">Rejected</option>
              </select>
            </label>

            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">First Name</span>
              <input class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={profileForm.first_name} />
              {#if profileFieldError("first_name")}<p class="mt-1 text-xs text-rose-600">{profileFieldError("first_name")}</p>{/if}
            </label>

            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Last Name</span>
              <input class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={profileForm.last_name} />
              {#if profileFieldError("last_name")}<p class="mt-1 text-xs text-rose-600">{profileFieldError("last_name")}</p>{/if}
            </label>

            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Middle Name</span>
              <input class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={profileForm.middle_name} />
            </label>

            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Title</span>
              <input class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={profileForm.title} />
            </label>

            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Date of Birth</span>
              <input type="date" class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={profileForm.date_of_birth} />
            </label>

            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Nationality</span>
              <input class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={profileForm.nationality} />
            </label>

            <label class="text-sm text-neutral-700 sm:col-span-2">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Legal Name</span>
              <input class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={profileForm.legal_name} />
            </label>

            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Trade Name</span>
              <input class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={profileForm.trade_name} />
            </label>

            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Primary Contact Name</span>
              <input class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={profileForm.primary_contact_name} />
            </label>

            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Registration Number</span>
              <input class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={profileForm.registration_number} />
            </label>

            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Tax ID</span>
              <input class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={profileForm.tax_identification_number} />
            </label>

            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Email</span>
              <input type="email" class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={profileForm.email} />
              {#if profileFieldError("email")}<p class="mt-1 text-xs text-rose-600">{profileFieldError("email")}</p>{/if}
            </label>

            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Phone</span>
              <input class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={profileForm.phone} />
            </label>

            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Secondary Phone</span>
              <input class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={profileForm.secondary_phone} />
            </label>

            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">KYC Reference</span>
              <input class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={profileForm.kyc_reference_number} />
            </label>

            <label class="text-sm text-neutral-700 sm:col-span-2">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Address</span>
              <textarea rows="2" class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={profileForm.address}></textarea>
            </label>

            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">City</span>
              <input class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={profileForm.city} />
            </label>

            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Country</span>
              <input class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={profileForm.country} />
            </label>
          </div>

          <div class="grid gap-3 sm:grid-cols-2">
            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Budget Min</span>
              <input type="number" min="0" class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={profileForm.budget_min} />
            </label>
            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Budget Max</span>
              <input type="number" min="0" class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={profileForm.budget_max} />
              {#if profileFieldError("budget_max")}<p class="mt-1 text-xs text-rose-600">{profileFieldError("budget_max")}</p>{/if}
            </label>
            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Annual Income</span>
              <input type="number" min="0" class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={profileForm.annual_income} />
            </label>
            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Net Worth</span>
              <input type="number" min="0" class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={profileForm.net_worth} />
            </label>
            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Liquidity Estimate</span>
              <input type="number" min="0" class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={profileForm.liquidity_estimate} />
            </label>
            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Risk Profile</span>
              <select class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={profileForm.risk_profile}>
                <option value="undisclosed">Undisclosed</option>
                <option value="conservative">Conservative</option>
                <option value="balanced">Balanced</option>
                <option value="aggressive">Aggressive</option>
              </select>
            </label>
            <label class="text-sm text-neutral-700 sm:col-span-2">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Preferred Locations (comma separated)</span>
              <input class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={profileForm.preferred_locations} />
            </label>
            <label class="text-sm text-neutral-700 sm:col-span-2">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Preferred Property Types (comma separated)</span>
              <input class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={profileForm.preferred_property_types} />
            </label>
            <label class="text-sm text-neutral-700 sm:col-span-2">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Preference Notes</span>
              <textarea rows="2" class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={profileForm.preference_notes}></textarea>
            </label>
            <label class="text-sm text-neutral-700 sm:col-span-2">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Interaction Summary</span>
              <textarea rows="2" class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={profileForm.interaction_summary}></textarea>
            </label>
            <label class="text-sm text-neutral-700 sm:col-span-2">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Notes</span>
              <textarea rows="2" class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={profileForm.notes}></textarea>
            </label>
          </div>

          <label class="flex items-center gap-2 text-sm text-neutral-700">
            <input type="checkbox" class="h-4 w-4 rounded border-neutral-300" bind:checked={profileForm.is_active} />
            Active profile
          </label>

          <div class="flex justify-end">
            <button
              type="submit"
              class="rounded-xl bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
              disabled={savingProfile}
            >
              {savingProfile ? "Saving..." : "Save profile"}
            </button>
          </div>
        </form>
      </section>
    {/if}

    </section>

    <section class="space-y-0">
      <section class="rounded-2xl border border-neutral-200 bg-white">
      <button
        type="button"
        class="flex w-full items-center justify-between gap-3 px-4 py-3 text-left sm:px-5"
        aria-expanded={activeTab === "interactions"}
        on:click={() => toggleTab("interactions")}
      >
        <span class="text-sm font-semibold text-neutral-900 sm:text-base">Interactions</span>
        <span class="text-xs font-semibold uppercase tracking-wide text-neutral-500">
          {activeTab === "interactions" ? "Collapse" : "Expand"}
        </span>
      </button>
      </section>

    {#if activeTab === "interactions"}
      <section class="space-y-4">
        <article class="rounded-2xl border border-neutral-200 bg-white p-5">
          <h2 class="text-base font-semibold text-neutral-900">Add Interaction</h2>
          <form class="mt-4 grid gap-3 sm:grid-cols-2" on:submit={addInteraction}>
            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Type</span>
              <select class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={interactionForm.interaction_type}>
                <option value="call">Call</option>
                <option value="email">Email</option>
                <option value="meeting">Meeting</option>
                <option value="site_visit">Site Visit</option>
                <option value="whatsapp">WhatsApp</option>
                <option value="note">Note</option>
              </select>
            </label>
            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Happened At</span>
              <input type="datetime-local" class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={interactionForm.happened_at} />
            </label>
            <label class="text-sm text-neutral-700 sm:col-span-2">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Subject</span>
              <input required class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={interactionForm.subject} />
            </label>
            <label class="text-sm text-neutral-700 sm:col-span-2">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Details</span>
              <textarea rows="2" class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={interactionForm.details}></textarea>
            </label>
            <label class="flex items-center gap-2 text-sm text-neutral-700">
              <input type="checkbox" class="h-4 w-4 rounded border-neutral-300" bind:checked={interactionForm.follow_up_required} />
              Follow-up required
            </label>
            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Follow-up Due</span>
              <input type="datetime-local" class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={interactionForm.follow_up_due_at} />
            </label>
            <div class="sm:col-span-2 flex justify-end">
              <button
                type="submit"
                class="rounded-xl bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
                disabled={savingInteraction}
              >
                {savingInteraction ? "Saving..." : "Log interaction"}
              </button>
            </div>
          </form>
        </article>

        <article class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-neutral-200 text-sm">
              <thead class="bg-neutral-50 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">
                <tr>
                  <th class="px-4 py-3">Type</th>
                  <th class="px-4 py-3">Subject</th>
                  <th class="px-4 py-3">Date</th>
                  <th class="px-4 py-3">Follow-up</th>
                  <th class="px-4 py-3">By</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100">
                {#if contact.interactions.length === 0}
                  <tr><td colspan="5" class="px-4 py-8 text-center text-sm text-neutral-500">No interaction history.</td></tr>
                {:else}
                  {#each contact.interactions as item}
                    <tr>
                      <td class="px-4 py-3 text-neutral-700">{item.interaction_type_display}</td>
                      <td class="px-4 py-3">
                        <p class="font-medium text-neutral-900">{item.subject}</p>
                        <p class="mt-0.5 text-xs text-neutral-500">{item.details || "\u2014"}</p>
                      </td>
                      <td class="px-4 py-3 text-neutral-600">{fmtDateTime(item.happened_at)}</td>
                      <td class="px-4 py-3 text-neutral-600">{item.follow_up_required ? fmtDateTime(item.follow_up_due_at) : "No"}</td>
                      <td class="px-4 py-3 text-neutral-600">{item.performed_by_name || "System"}</td>
                    </tr>
                  {/each}
                {/if}
              </tbody>
            </table>
          </div>
        </article>
      </section>
    {/if}

    </section>

    <section class="space-y-0">
      <section class="rounded-2xl border border-neutral-200 bg-white">
      <button
        type="button"
        class="flex w-full items-center justify-between gap-3 px-4 py-3 text-left sm:px-5"
        aria-expanded={activeTab === "deals"}
        on:click={() => toggleTab("deals")}
      >
        <span class="text-sm font-semibold text-neutral-900 sm:text-base">Linked Deals</span>
        <span class="text-xs font-semibold uppercase tracking-wide text-neutral-500">
          {activeTab === "deals" ? "Collapse" : "Expand"}
        </span>
      </button>
      </section>

    {#if activeTab === "deals"}
      <section class="space-y-4">
        <article class="rounded-2xl border border-neutral-200 bg-white p-5">
          <h2 class="text-base font-semibold text-neutral-900">Link Deal</h2>
          <form class="mt-4 grid gap-3 sm:grid-cols-2" on:submit={addDealLink}>
            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Lead</span>
              <select class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={dealForm.lead}>
                <option value="">None</option>
                {#each leads as lead}
                  <option value={String(lead.id)}>{lead.label}</option>
                {/each}
              </select>
            </label>
            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Reservation</span>
              <select class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={dealForm.reservation}>
                <option value="">None</option>
                {#each reservations as reservation}
                  <option value={String(reservation.id)}>{reservation.label}</option>
                {/each}
              </select>
            </label>
            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Deal Name</span>
              <input class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={dealForm.deal_name} />
            </label>
            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Stage</span>
              <input class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={dealForm.stage} />
            </label>
            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Status</span>
              <select class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={dealForm.status}>
                <option value="active">Active</option>
                <option value="won">Won</option>
                <option value="lost">Lost</option>
                <option value="on_hold">On Hold</option>
              </select>
            </label>
            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Deal Value</span>
              <input type="number" min="0" class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={dealForm.deal_value} />
            </label>
            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Close Probability (%)</span>
              <input type="number" min="0" max="100" class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={dealForm.close_probability} />
            </label>
            <label class="text-sm text-neutral-700 sm:col-span-2">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Notes</span>
              <textarea rows="2" class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={dealForm.notes}></textarea>
            </label>
            <div class="sm:col-span-2 flex justify-end">
              <button
                type="submit"
                class="rounded-xl bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
                disabled={savingDeal}
              >
                {savingDeal ? "Saving..." : "Add deal link"}
              </button>
            </div>
          </form>
        </article>

        <article class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-neutral-200 text-sm">
              <thead class="bg-neutral-50 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">
                <tr>
                  <th class="px-4 py-3">Deal</th>
                  <th class="px-4 py-3">Stage</th>
                  <th class="px-4 py-3">Status</th>
                  <th class="px-4 py-3">Value</th>
                  <th class="px-4 py-3">Probability</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100">
                {#if contact.deal_links.length === 0}
                  <tr><td colspan="5" class="px-4 py-8 text-center text-sm text-neutral-500">No linked deals.</td></tr>
                {:else}
                  {#each contact.deal_links as link}
                    <tr>
                      <td class="px-4 py-3">
                        <p class="font-medium text-neutral-900">{link.deal_name || link.lead_name || link.reservation_number || "Linked deal"}</p>
                        <p class="mt-0.5 text-xs text-neutral-500">Lead: {link.lead_name || "\u2014"} \u2022 Reservation: {link.reservation_number || "\u2014"}</p>
                      </td>
                      <td class="px-4 py-3 text-neutral-600">{link.stage || "\u2014"}</td>
                      <td class="px-4 py-3 text-neutral-600">{link.status_display}</td>
                      <td class="px-4 py-3 text-neutral-600">{fmtMoney(link.deal_value)}</td>
                      <td class="px-4 py-3 text-neutral-600">{link.close_probability}%</td>
                    </tr>
                  {/each}
                {/if}
              </tbody>
            </table>
          </div>
        </article>
      </section>
    {/if}

    </section>

    <section class="space-y-0">
      <section class="rounded-2xl border border-neutral-200 bg-white">
      <button
        type="button"
        class="flex w-full items-center justify-between gap-3 px-4 py-3 text-left sm:px-5"
        aria-expanded={activeTab === "properties"}
        on:click={() => toggleTab("properties")}
      >
        <span class="text-sm font-semibold text-neutral-900 sm:text-base">Property Links</span>
        <span class="text-xs font-semibold uppercase tracking-wide text-neutral-500">
          {activeTab === "properties" ? "Collapse" : "Expand"}
        </span>
      </button>
      </section>

    {#if activeTab === "properties"}
      <section class="space-y-4">
        <article class="rounded-2xl border border-neutral-200 bg-white p-5">
          <h2 class="text-base font-semibold text-neutral-900">Link Property</h2>
          <form class="mt-4 grid gap-3 sm:grid-cols-2" on:submit={addPropertyLink}>
            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Project</span>
              <select class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={propertyForm.project}>
                <option value="">None</option>
                {#each projects as project}
                  <option value={String(project.id)}>{project.label}</option>
                {/each}
              </select>
            </label>
            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Property</span>
              <select class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={propertyForm.property}>
                <option value="">None</option>
                {#each properties as property}
                  <option value={String(property.id)}>{property.label}</option>
                {/each}
              </select>
            </label>
            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Unit</span>
              <select class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={propertyForm.unit}>
                <option value="">None</option>
                {#each units as unit}
                  <option value={String(unit.id)}>{unit.label}</option>
                {/each}
              </select>
            </label>
            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Relationship</span>
              <select class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={propertyForm.relationship_type}>
                <option value="interested">Interested</option>
                <option value="shortlisted">Shortlisted</option>
                <option value="reserved">Reserved</option>
                <option value="purchased">Purchased</option>
                <option value="leased">Leased</option>
                <option value="investor_target">Investor Target</option>
              </select>
            </label>
            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Budget Estimate</span>
              <input type="number" min="0" class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={propertyForm.budget_estimate} />
            </label>
            <label class="text-sm text-neutral-700 sm:col-span-2">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Notes</span>
              <textarea rows="2" class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={propertyForm.notes}></textarea>
            </label>
            <div class="sm:col-span-2 flex justify-end">
              <button
                type="submit"
                class="rounded-xl bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
                disabled={savingProperty}
              >
                {savingProperty ? "Saving..." : "Add property link"}
              </button>
            </div>
          </form>
        </article>

        <article class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-neutral-200 text-sm">
              <thead class="bg-neutral-50 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">
                <tr>
                  <th class="px-4 py-3">Relationship</th>
                  <th class="px-4 py-3">Project / Property / Unit</th>
                  <th class="px-4 py-3">Budget</th>
                  <th class="px-4 py-3">Linked</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100">
                {#if contact.property_links.length === 0}
                  <tr><td colspan="4" class="px-4 py-8 text-center text-sm text-neutral-500">No property links.</td></tr>
                {:else}
                  {#each contact.property_links as link}
                    <tr>
                      <td class="px-4 py-3 text-neutral-600">{link.relationship_type_display}</td>
                      <td class="px-4 py-3 text-neutral-700">
                        <p>{link.project_name || "\u2014"}</p>
                        <p class="mt-0.5 text-xs text-neutral-500">{link.property_name || "\u2014"} \u2022 {link.unit_number || "\u2014"}</p>
                      </td>
                      <td class="px-4 py-3 text-neutral-600">{fmtMoney(link.budget_estimate)}</td>
                      <td class="px-4 py-3 text-neutral-600">{fmtDateTime(link.linked_at)}</td>
                    </tr>
                  {/each}
                {/if}
              </tbody>
            </table>
          </div>
        </article>
      </section>
    {/if}

    </section>

    <section class="space-y-0">
      <section class="rounded-2xl border border-neutral-200 bg-white">
      <button
        type="button"
        class="flex w-full items-center justify-between gap-3 px-4 py-3 text-left sm:px-5"
        aria-expanded={activeTab === "documents"}
        on:click={() => toggleTab("documents")}
      >
        <span class="text-sm font-semibold text-neutral-900 sm:text-base">Documents</span>
        <span class="text-xs font-semibold uppercase tracking-wide text-neutral-500">
          {activeTab === "documents" ? "Collapse" : "Expand"}
        </span>
      </button>
      </section>

    {#if activeTab === "documents"}
      <section class="space-y-4">
        <article class="rounded-2xl border border-neutral-200 bg-white p-5">
          <h2 class="text-base font-semibold text-neutral-900">Upload Document</h2>
          <form class="mt-4 grid gap-3 sm:grid-cols-2" on:submit={addDocument}>
            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Document Type</span>
              <select class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={documentForm.document_type}>
                <option value="id_card">National ID</option>
                <option value="passport">Passport</option>
                <option value="company_registration">Company Registration</option>
                <option value="proof_of_funds">Proof of Funds</option>
                <option value="utility_bill">Utility Bill</option>
                <option value="other">Other</option>
              </select>
            </label>
            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">File Name</span>
              <input required class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={documentForm.file_name} />
            </label>
            <label class="text-sm text-neutral-700 sm:col-span-2">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">File URL</span>
              <input class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={documentForm.file_url} placeholder="https://..." />
            </label>
            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Reference Number</span>
              <input class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={documentForm.reference_number} />
            </label>
            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Issued Date</span>
              <input type="date" class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={documentForm.issued_at} />
            </label>
            <label class="text-sm text-neutral-700">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Expiry Date</span>
              <input type="date" class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={documentForm.expires_at} />
            </label>
            <label class="flex items-center gap-2 text-sm text-neutral-700">
              <input type="checkbox" class="h-4 w-4 rounded border-neutral-300" bind:checked={documentForm.is_kyc_document} />
              Treat as KYC document
            </label>
            <label class="text-sm text-neutral-700 sm:col-span-2">
              <span class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Notes</span>
              <textarea rows="2" class="w-full rounded-xl border border-neutral-200 px-3 py-2" bind:value={documentForm.notes}></textarea>
            </label>
            <div class="sm:col-span-2 flex justify-end">
              <button
                type="submit"
                class="rounded-xl bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
                disabled={savingDocument}
              >
                {savingDocument ? "Saving..." : "Add document"}
              </button>
            </div>
          </form>
        </article>

        <article class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-neutral-200 text-sm">
              <thead class="bg-neutral-50 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">
                <tr>
                  <th class="px-4 py-3">Document</th>
                  <th class="px-4 py-3">Type</th>
                  <th class="px-4 py-3">KYC</th>
                  <th class="px-4 py-3">Dates</th>
                  <th class="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-neutral-100">
                {#if contact.documents.length === 0}
                  <tr><td colspan="5" class="px-4 py-8 text-center text-sm text-neutral-500">No documents uploaded.</td></tr>
                {:else}
                  {#each contact.documents as doc}
                    <tr>
                      <td class="px-4 py-3">
                        <p class="font-medium text-neutral-900">{doc.file_name}</p>
                        <p class="mt-0.5 text-xs text-neutral-500">{doc.reference_number || "\u2014"}</p>
                      </td>
                      <td class="px-4 py-3 text-neutral-600">{doc.document_type_display}</td>
                      <td class="px-4 py-3 text-neutral-600">
                        <p>{doc.is_kyc_document ? "Yes" : "No"}</p>
                        <p class="mt-0.5 text-xs text-neutral-500">{doc.latest_review_status || "\u2014"}</p>
                      </td>
                      <td class="px-4 py-3 text-neutral-600">
                        <p>Issued: {fmtDate(doc.issued_at)}</p>
                        <p class="mt-0.5 text-xs text-neutral-500">Expires: {fmtDate(doc.expires_at)}</p>
                      </td>
                      <td class="px-4 py-3">
                        <div class="flex justify-end gap-2">
                          <button
                            type="button"
                            class="rounded-lg border border-neutral-200 px-2.5 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-100 disabled:cursor-not-allowed disabled:opacity-60"
                            disabled={requestingKycReview}
                            on:click={() => requestKycReview(doc.id)}
                          >
                            {requestingKycReview ? "Requesting..." : "Request Review"}
                          </button>
                          {#if doc.file_url}
                            <a
                              class="rounded-lg border border-neutral-200 px-2.5 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-100"
                              href={doc.file_url}
                              target="_blank"
                              rel="noreferrer"
                            >
                              Open
                            </a>
                          {/if}
                        </div>
                      </td>
                    </tr>
                  {/each}
                {/if}
              </tbody>
            </table>
          </div>
        </article>
      </section>
    {/if}

    </section>

    <section class="space-y-0">
      <section class="rounded-2xl border border-neutral-200 bg-white">
      <button
        type="button"
        class="flex w-full items-center justify-between gap-3 px-4 py-3 text-left sm:px-5"
        aria-expanded={activeTab === "compliance"}
        on:click={() => toggleTab("compliance")}
      >
        <span class="text-sm font-semibold text-neutral-900 sm:text-base">Compliance Reviews</span>
        <span class="text-xs font-semibold uppercase tracking-wide text-neutral-500">
          {activeTab === "compliance" ? "Collapse" : "Expand"}
        </span>
      </button>
      </section>

    {#if activeTab === "compliance"}
      <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-neutral-200 text-sm">
            <thead class="bg-neutral-50 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">
              <tr>
                <th class="px-4 py-3">Requested</th>
                <th class="px-4 py-3">Document</th>
                <th class="px-4 py-3">Status</th>
                <th class="px-4 py-3">Owners</th>
                <th class="px-4 py-3">Notes</th>
                <th class="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#if contact.compliance_reviews.length === 0}
                <tr><td colspan="6" class="px-4 py-8 text-center text-sm text-neutral-500">No compliance reviews yet.</td></tr>
              {:else}
                {#each contact.compliance_reviews as review}
                  <tr>
                    <td class="px-4 py-3 text-neutral-600">{fmtDateTime(review.requested_at)}</td>
                    <td class="px-4 py-3 text-neutral-700">{review.document_name || "\u2014"}</td>
                    <td class="px-4 py-3">
                      <span class={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${complianceBadge(review.status)}`}>
                        {review.status_display}
                      </span>
                    </td>
                    <td class="px-4 py-3 text-xs text-neutral-600">
                      <p>By: {review.requested_by_name || "System"}</p>
                      <p class="mt-0.5">Reviewed: {review.reviewed_by_name || "\u2014"}</p>
                    </td>
                    <td class="px-4 py-3 text-neutral-600">{review.notes || "\u2014"}</td>
                    <td class="px-4 py-3">
                      <div class="flex justify-end gap-2">
                        <button
                          type="button"
                          class="rounded-lg border border-neutral-200 px-2.5 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-100"
                          on:click={() => complianceAction(review.id, "mark_in_review")}
                        >
                          In review
                        </button>
                        <button
                          type="button"
                          class="rounded-lg border border-emerald-200 bg-emerald-50 px-2.5 py-1.5 text-xs font-medium text-emerald-700 hover:bg-emerald-100"
                          on:click={() => complianceAction(review.id, "approve")}
                        >
                          Approve
                        </button>
                        <button
                          type="button"
                          class="rounded-lg border border-rose-200 bg-rose-50 px-2.5 py-1.5 text-xs font-medium text-rose-700 hover:bg-rose-100"
                          on:click={() => complianceAction(review.id, "reject")}
                        >
                          Reject
                        </button>
                      </div>
                    </td>
                  </tr>
                {/each}
              {/if}
            </tbody>
          </table>
        </div>
      </section>
    {/if}

    </section>
  {/if}
</div>

<script lang="ts">
  import { currency } from "$lib/stores/currency.svelte";
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import Breadcrumb from "$lib/components/Breadcrumb.svelte";
  import DocumentRecordsTable from "$lib/components/documents/DocumentRecordsTable.svelte";
  import type { Property, Unit, PropertyImage, PropertyDocument, PropertyValuation, PropertyOwnership, PropertyEncumbrance } from "$lib/types";
  import PropertyMap from "$lib/components/PropertyMap.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DateInput from "$lib/components/DateInput.svelte";

  const propertyId = $derived($page.params.id);

  let property = $state<Property | null>(null);
  let loading = $state(true);
  let activeTab = $state<"overview" | "units" | "ownership" | "images" | "documents" | "valuations" | "encumbrances">("overview");

  const tabs = [
    { key: "overview" as const, label: "Overview" },
    { key: "units" as const, label: "Units" },
    { key: "ownership" as const, label: "Ownership" },
    { key: "images" as const, label: "Images" },
    { key: "documents" as const, label: "Documents" },
    { key: "valuations" as const, label: "Valuations" },
    { key: "encumbrances" as const, label: "Encumbrances" },
  ];

  const typeLabels: Record<string, string> = {
    land: "Land Parcel",
    building: "Building",
    mixed: "Mixed-Use",
    estate: "Estate",
    warehouse: "Warehouse",
    industrial: "Industrial",
  };

  const classificationLabels: Record<string, string> = {
    owned: "Owned",
    lease: "Lease",
    concession: "Concession",
    under_development: "Under Development",
  };

  const statusLabels: Record<string, string> = {
    available: "Available",
    reserved: "Reserved",
    sold: "Sold",
    leased: "Leased",
  };

  const unitCategoryLabels: Record<string, string> = {
    apartment: "Apartment",
    villa: "Villa",
    townhouse: "Townhouse",
    penthouse: "Penthouse",
    studio: "Studio",
    duplex: "Duplex",
    office: "Office",
    retail: "Retail",
    warehouse: "Warehouse",
    land: "Land",
    other: "Other",
  };

  const docTypeLabels: Record<string, string> = {
    deed: "Deed",
    contract: "Contract",
    survey: "Survey",
    permit: "Permit",
    inspection: "Inspection",
    appraisal: "Appraisal",
    insurance: "Insurance",
    tax: "Tax",
    certificate_of_occupancy: "Certificate of Occupancy",
    lease_agreement: "Lease Agreement",
    easement: "Easement",
    mortgage: "Mortgage",
    government_approval: "Government Approval",
    other: "Other",
  };

  const valTypeLabels: Record<string, string> = {
    appraisal: "Professional Appraisal",
    internal: "Internal Estimate",
    market: "Market Comparable",
    tax: "Tax Assessment",
  };

  const ownershipStructureLabels: Record<string, string> = {
    individual: "Individual",
    corporate: "Corporate",
    trust: "Trust",
    joint_venture: "Joint Venture",
  };

  const encumbranceTypeLabels: Record<string, string> = {
    mortgage: "Mortgage",
    lien: "Lien",
    legal_dispute: "Legal Dispute",
    court_case: "Court Case",
    tax_arrears: "Tax Arrears",
  };

  async function loadProperty() {
    loading = true;
    try {
      property = await api.get<Property>(`/properties/${propertyId}/`);
    } catch {
      property = null;
    }
    loading = false;
  }

  $effect(() => {
    void propertyId;
    loadProperty();
  });

  function fmt(value: string | null): string {
    return value ? currency.formatCompact(value) : "\u2014";
  }

  function fmtArea(value: string | null): string {
    return value ? Number(value).toLocaleString() + " sqft" : "\u2014";
  }

  function fmtDate(value: string | null): string {
    if (!value) return "\u2014";
    return new Date(value).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  }

  function apiErrorDetail(err: unknown): string {
    if (err instanceof ApiError && err.fieldErrors) {
      const msgs = Object.entries(err.fieldErrors)
        .map(([field, errors]) => `${field}: ${errors[0]}`)
        .slice(0, 2);
      if (msgs.length) return msgs.join(". ");
    }
    return "Please try again later";
  }

  // --- Unit CRUD ---
  let showUnitForm = $state(false);
  let editingUnit = $state<Unit | null>(null);
  let unitForm = $state({
    unit_number: "",
    floor: "",
    area_sqft: "",
    bedrooms: "",
    bathrooms: "",
    unit_category: "apartment",
    asking_price: "",
    status: "available",
    gps_latitude: "",
    gps_longitude: "",
    location_description: "",
  });

  function openAddUnit() {
    editingUnit = null;
    unitForm = {
      unit_number: "",
      floor: "",
      area_sqft: "",
      bedrooms: "",
      bathrooms: "",
      unit_category: "apartment",
      asking_price: "",
      status: "available",
      gps_latitude: "",
      gps_longitude: "",
      location_description: "",
    };
    showUnitForm = true;
  }

  function openEditUnit(unit: Unit) {
    editingUnit = unit;
    unitForm = {
      unit_number: unit.unit_number,
      floor: unit.floor?.toString() ?? "",
      area_sqft: unit.area_sqft,
      bedrooms: unit.bedrooms?.toString() ?? "",
      bathrooms: unit.bathrooms?.toString() ?? "",
      unit_category: unit.unit_category ?? "apartment",
      asking_price: unit.asking_price ?? "",
      status: unit.status,
      gps_latitude: unit.gps_latitude ?? "",
      gps_longitude: unit.gps_longitude ?? "",
      location_description: unit.location_description ?? "",
    };
    showUnitForm = true;
  }

  async function saveUnit() {
    try {
      const payload = {
        unit_number: unitForm.unit_number,
        floor: unitForm.floor ? Number(unitForm.floor) : null,
        area_sqft: unitForm.area_sqft,
        bedrooms: unitForm.bedrooms ? Number(unitForm.bedrooms) : null,
        bathrooms: unitForm.bathrooms ? Number(unitForm.bathrooms) : null,
        unit_category: unitForm.unit_category,
        asking_price: unitForm.asking_price || null,
        status: unitForm.status,
        gps_latitude: unitForm.gps_latitude || null,
        gps_longitude: unitForm.gps_longitude || null,
        location_description: unitForm.location_description,
      };
      if (editingUnit) {
        await api.patch(`/properties/${propertyId}/units/${editingUnit.id}/`, payload);
        toast.success("Unit updated", `${unitForm.unit_number} has been saved`);
      } else {
        await api.post(`/properties/${propertyId}/units/`, payload);
        toast.success("Unit added", `${unitForm.unit_number} has been created`);
      }
      showUnitForm = false;
      loadProperty();
    } catch (err) {
      toast.error("Failed to save unit", apiErrorDetail(err));
    }
  }

  async function deleteUnit(unitId: number) {
    if (!confirm("Delete this unit?")) return;
    try {
      await api.delete(`/properties/${propertyId}/units/${unitId}/`);
      toast.success("Unit deleted", "The unit has been permanently removed");
      loadProperty();
    } catch (err) {
      toast.error("Failed to delete unit", apiErrorDetail(err));
    }
  }

  // --- Image Upload ---
  let uploadingImage = $state(false);

  async function handleImageUpload(e: Event) {
    const input = e.target as HTMLInputElement;
    if (!input.files?.length) return;
    uploadingImage = true;
    try {
      for (const file of input.files) {
        const fd = new FormData();
        fd.append("image", file);
        fd.append("caption", "");
        await api.upload(`/properties/${propertyId}/images/`, fd);
      }
      toast.success("Images uploaded", `${input.files.length} file${input.files.length > 1 ? "s" : ""} added to gallery`);
      loadProperty();
    } catch (err) {
      toast.error("Upload failed", apiErrorDetail(err));
    }
    uploadingImage = false;
    input.value = "";
  }

  async function setPrimaryImage(imageId: number) {
    try {
      await api.post(`/properties/${propertyId}/images/${imageId}/set_primary/`, {});
      toast.success("Primary image updated", "This image will be shown on the property card");
      loadProperty();
    } catch (err) {
      toast.error("Failed to set primary image", apiErrorDetail(err));
    }
  }

  async function deleteImage(imageId: number) {
    if (!confirm("Delete this image?")) return;
    try {
      await api.delete(`/properties/${propertyId}/images/${imageId}/`);
      toast.success("Image deleted", "The image has been permanently removed");
      loadProperty();
    } catch (err) {
      toast.error("Failed to delete image", apiErrorDetail(err));
    }
  }

  // --- Document Upload ---
  let showDocForm = $state(false);
  let docForm = $state({ title: "", document_type: "other", file: null as File | null });

  async function saveDocument() {
    if (!docForm.file || !docForm.title) return;
    try {
      const fd = new FormData();
      fd.append("file", docForm.file);
      fd.append("title", docForm.title);
      fd.append("document_type", docForm.document_type);
      await api.upload(`/properties/${propertyId}/documents/`, fd);
      toast.success("Document uploaded", `"${docForm.title}" has been attached`);
      showDocForm = false;
      docForm = { title: "", document_type: "other", file: null };
      loadProperty();
    } catch (err) {
      toast.error("Upload failed", apiErrorDetail(err));
    }
  }

  async function deleteDocument(docId: number) {
    if (!confirm("Delete this document?")) return;
    try {
      await api.delete(`/properties/${propertyId}/documents/${docId}/`);
      toast.success("Document deleted", "The document has been permanently removed");
      loadProperty();
    } catch (err) {
      toast.error("Failed to delete document", apiErrorDetail(err));
    }
  }

  // --- Valuation ---
  let showValForm = $state(false);
  let valForm = $state({ valuation_date: "", value: "", valuation_type: "internal", appraiser: "", notes: "" });

  async function saveValuation() {
    try {
      await api.post(`/properties/${propertyId}/valuations/`, valForm);
      toast.success("Valuation saved", "The valuation record has been added");
      showValForm = false;
      valForm = { valuation_date: "", value: "", valuation_type: "internal", appraiser: "", notes: "" };
      loadProperty();
    } catch (err) {
      toast.error("Failed to save valuation", apiErrorDetail(err));
    }
  }

  async function deleteValuation(valId: number) {
    if (!confirm("Delete this valuation?")) return;
    try {
      await api.delete(`/properties/${propertyId}/valuations/${valId}/`);
      toast.success("Valuation deleted", "The valuation record has been removed");
      loadProperty();
    } catch (err) {
      toast.error("Failed to delete valuation", apiErrorDetail(err));
    }
  }

  // --- Ownership CRUD ---
  let showOwnershipForm = $state(false);
  let editingOwnership = $state<PropertyOwnership | null>(null);
  let ownershipForm = $state({
    legal_owner_name: "",
    ownership_structure: "individual",
    ownership_percentage: "",
    title_deed_number: "",
    registration_authority: "",
    date_of_registration: "",
    deed_expiry: "",
  });

  function openAddOwnership() {
    editingOwnership = null;
    ownershipForm = {
      legal_owner_name: "",
      ownership_structure: "individual",
      ownership_percentage: "",
      title_deed_number: "",
      registration_authority: "",
      date_of_registration: "",
      deed_expiry: "",
    };
    showOwnershipForm = true;
  }

  function openEditOwnership(o: PropertyOwnership) {
    editingOwnership = o;
    ownershipForm = {
      legal_owner_name: o.legal_owner_name,
      ownership_structure: o.ownership_structure,
      ownership_percentage: o.ownership_percentage,
      title_deed_number: o.title_deed_number,
      registration_authority: o.registration_authority,
      date_of_registration: o.date_of_registration,
      deed_expiry: o.deed_expiry ?? "",
    };
    showOwnershipForm = true;
  }

  async function saveOwnership() {
    try {
      const payload = {
        ...ownershipForm,
        deed_expiry: ownershipForm.deed_expiry || null,
      };
      if (editingOwnership) {
        await api.patch(`/properties/${propertyId}/ownerships/${editingOwnership.id}/`, payload);
        toast.success("Ownership updated", `${ownershipForm.legal_owner_name} has been saved`);
      } else {
        await api.post(`/properties/${propertyId}/ownerships/`, payload);
        toast.success("Ownership added", `${ownershipForm.legal_owner_name} — ${ownershipForm.ownership_percentage}%`);
      }
      showOwnershipForm = false;
      loadProperty();
    } catch (err) {
      toast.error("Failed to save ownership", apiErrorDetail(err));
    }
  }

  async function deleteOwnership(id: number) {
    if (!confirm("Delete this ownership record?")) return;
    try {
      await api.delete(`/properties/${propertyId}/ownerships/${id}/`);
      toast.success("Ownership deleted", "The ownership record has been removed");
      loadProperty();
    } catch (err) {
      toast.error("Failed to delete ownership", apiErrorDetail(err));
    }
  }

  // --- Encumbrance CRUD ---
  let showEncumbranceForm = $state(false);
  let editingEncumbrance = $state<PropertyEncumbrance | null>(null);
  let encumbranceForm = $state({
    encumbrance_type: "mortgage",
    title: "",
    description: "",
    amount: "",
    status: "active",
    date_filed: "",
    date_resolved: "",
    reference_number: "",
    notes: "",
  });

  function openAddEncumbrance() {
    editingEncumbrance = null;
    encumbranceForm = {
      encumbrance_type: "mortgage",
      title: "",
      description: "",
      amount: "",
      status: "active",
      date_filed: "",
      date_resolved: "",
      reference_number: "",
      notes: "",
    };
    showEncumbranceForm = true;
  }

  function openEditEncumbrance(enc: PropertyEncumbrance) {
    editingEncumbrance = enc;
    encumbranceForm = {
      encumbrance_type: enc.encumbrance_type,
      title: enc.title,
      description: enc.description,
      amount: enc.amount ?? "",
      status: enc.status,
      date_filed: enc.date_filed,
      date_resolved: enc.date_resolved ?? "",
      reference_number: enc.reference_number,
      notes: enc.notes,
    };
    showEncumbranceForm = true;
  }

  async function saveEncumbrance() {
    try {
      const payload = {
        ...encumbranceForm,
        amount: encumbranceForm.amount || null,
        date_resolved: encumbranceForm.date_resolved || null,
      };
      if (editingEncumbrance) {
        await api.patch(`/properties/${propertyId}/encumbrances/${editingEncumbrance.id}/`, payload);
        toast.success("Encumbrance updated", `"${encumbranceForm.title}" has been saved`);
      } else {
        await api.post(`/properties/${propertyId}/encumbrances/`, payload);
        toast.success("Encumbrance added", `"${encumbranceForm.title}" has been recorded`);
      }
      showEncumbranceForm = false;
      loadProperty();
    } catch (err) {
      toast.error("Failed to save encumbrance", apiErrorDetail(err));
    }
  }

  async function deleteEncumbrance(id: number) {
    if (!confirm("Delete this encumbrance?")) return;
    try {
      await api.delete(`/properties/${propertyId}/encumbrances/${id}/`);
      toast.success("Encumbrance deleted", "The encumbrance has been removed");
      loadProperty();
    } catch (err) {
      toast.error("Failed to delete encumbrance", apiErrorDetail(err));
    }
  }
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
  </div>
{:else if !property}
  <div class="text-center py-24">
    <p class="text-neutral-400">Property not found.</p>
    <a href="/properties" class="mt-4 inline-block text-sm font-medium text-neutral-900 hover:underline">Back to properties</a>
  </div>
{:else}
  <!-- Header -->
  <div class="flex items-start justify-between mb-8">
    <div>
      <Breadcrumb items={[{ label: "Properties", href: "/properties" }, { label: property.name }]} />
      <h1 class="text-2xl font-bold text-neutral-900 mt-3">{property.name}</h1>
      <div class="flex items-center gap-3 mt-2">
        <StatusBadge status={property.property_type} label={typeLabels[property.property_type]} />
        <StatusBadge status={property.classification} label={classificationLabels[property.classification]} />
        {#if property.is_active}
          <span class="inline-flex items-center gap-1.5 text-xs font-medium text-neutral-900">
            <span class="w-1.5 h-1.5 rounded-full bg-neutral-900"></span>Active
          </span>
        {:else}
          <span class="inline-flex items-center gap-1.5 text-xs font-medium text-neutral-400">
            <span class="w-1.5 h-1.5 rounded-full bg-neutral-300"></span>Inactive
          </span>
        {/if}
      </div>
    </div>
    <a
      href="/properties/{property.id}/edit"
      class="px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors"
    >
      Edit
    </a>
  </div>

  <!-- Tabs -->
  <div class="border-b border-neutral-200 mb-6">
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
          {#if tab.key === "units" && property.units}
            <span class="ml-1.5 text-xs text-neutral-400">({property.units.length})</span>
          {/if}
          {#if tab.key === "images" && property.images}
            <span class="ml-1.5 text-xs text-neutral-400">({property.images.length})</span>
          {/if}
          {#if tab.key === "ownership" && property.ownerships}
            <span class="ml-1.5 text-xs text-neutral-400">({property.ownerships.length})</span>
          {/if}
          {#if tab.key === "encumbrances" && property.encumbrances}
            <span class="ml-1.5 text-xs text-neutral-400">({property.encumbrances.length})</span>
          {/if}
        </button>
      {/each}
    </nav>
  </div>

  <!-- Tab: Overview -->
  {#if activeTab === "overview"}
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-4">
        <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Details</h3>
        <div class="space-y-3 text-sm">
          <div class="flex justify-between"><span class="text-neutral-400">Address</span><span class="text-neutral-900 text-right max-w-[60%]">{property.address}</span></div>
          <div class="flex justify-between"><span class="text-neutral-400">Type</span><span class="text-neutral-900">{typeLabels[property.property_type]}</span></div>
          <div class="flex justify-between"><span class="text-neutral-400">Classification</span><span class="text-neutral-900">{classificationLabels[property.classification]}</span></div>
          {#if property.plot_number}
            <div class="flex justify-between"><span class="text-neutral-400">Plot Number</span><span class="text-neutral-900">{property.plot_number}</span></div>
          {/if}
          <div class="flex justify-between"><span class="text-neutral-400">Total Area</span><span class="text-neutral-900 tabular-nums">{fmtArea(property.total_area_sqft)}</span></div>
          <div class="flex justify-between"><span class="text-neutral-400">Units</span><span class="text-neutral-900">{property.unit_count}</span></div>
          {#if property.gps_latitude && property.gps_longitude}
            <div class="flex justify-between"><span class="text-neutral-400">GPS Coordinates</span><span class="text-neutral-900 tabular-nums">{property.gps_latitude}, {property.gps_longitude}</span></div>
          {/if}
        </div>
      </div>
      <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-4">
        <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Financials</h3>
        <div class="space-y-3 text-sm">
          <div class="flex justify-between"><span class="text-neutral-400">Acquisition Price</span><span class="text-neutral-900 tabular-nums">{fmt(property.acquisition_price)}</span></div>
          <div class="flex justify-between"><span class="text-neutral-400">Acquisition Date</span><span class="text-neutral-900">{fmtDate(property.acquisition_date)}</span></div>
          <div class="flex justify-between"><span class="text-neutral-400">Current Value</span><span class="text-green-600 tabular-nums font-semibold">{fmt(property.current_value)}</span></div>
        </div>
      </div>
      {#if property.description}
        <div class="bg-white rounded-xl border border-neutral-200 p-6 md:col-span-2">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-3">Description</h3>
          <p class="text-sm text-neutral-600 leading-relaxed whitespace-pre-line">{property.description}</p>
        </div>
      {/if}
      {#if property.map_available}
        <div class="md:col-span-2">
          <PropertyMap
            latitude={Number(property.gps_latitude)}
            longitude={Number(property.gps_longitude)}
          />
        </div>
      {/if}
    </div>
  {/if}

  <!-- Tab: Units -->
  {#if activeTab === "units"}
    <div class="space-y-4">
      <div class="flex justify-end">
        <button onclick={openAddUnit} class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors">
          + Add Unit
        </button>
      </div>

      {#if showUnitForm}
        <div class="bg-white rounded-xl border border-neutral-200 p-6">
          <h3 class="text-sm font-semibold text-neutral-900 mb-4">{editingUnit ? "Edit Unit" : "New Unit"}</h3>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Unit Number</span>
                <input bind:value={unitForm.unit_number} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
              </label>
            </div>
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Floor</span>
                <input bind:value={unitForm.floor} type="number" class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
              </label>
            </div>
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Area (sqft)</span>
                <input bind:value={unitForm.area_sqft} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
              </label>
            </div>
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Status</span>
                <select bind:value={unitForm.status} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
                  <option value="available">Available</option>
                  <option value="reserved">Reserved</option>
                  <option value="sold">Sold</option>
                  <option value="leased">Leased</option>
                </select>
              </label>
            </div>
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Unit Category</span>
                <select bind:value={unitForm.unit_category} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
                  <option value="apartment">Apartment</option>
                  <option value="villa">Villa</option>
                  <option value="townhouse">Townhouse</option>
                  <option value="penthouse">Penthouse</option>
                  <option value="studio">Studio</option>
                  <option value="duplex">Duplex</option>
                  <option value="office">Office</option>
                  <option value="retail">Retail</option>
                  <option value="warehouse">Warehouse</option>
                  <option value="land">Land</option>
                  <option value="other">Other</option>
                </select>
              </label>
            </div>
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Bedrooms</span>
                <input bind:value={unitForm.bedrooms} type="number" class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
              </label>
            </div>
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Bathrooms</span>
                <input bind:value={unitForm.bathrooms} type="number" class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
              </label>
            </div>
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Asking Price</span>
                <input bind:value={unitForm.asking_price} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
              </label>
            </div>
            <div class="md:col-span-2">
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Location Description</span>
                <input bind:value={unitForm.location_description} placeholder="e.g. Block A, Level 3, East Wing" class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
              </label>
            </div>
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">GPS Latitude</span>
                <input bind:value={unitForm.gps_latitude} type="number" step="any" placeholder="-90 to 90" class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
              </label>
            </div>
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">GPS Longitude</span>
                <input bind:value={unitForm.gps_longitude} type="number" step="any" placeholder="-180 to 180" class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
              </label>
            </div>
          </div>
          <div class="flex gap-3 mt-4">
            <button onclick={saveUnit} class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors">
              {editingUnit ? "Update" : "Add"} Unit
            </button>
            <button onclick={() => (showUnitForm = false)} class="px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors">
              Cancel
            </button>
          </div>
        </div>
      {/if}

      {#if property.units.length === 0 && !showUnitForm}
        <div class="bg-white rounded-xl border border-neutral-200 p-12 text-center">
          <p class="text-sm text-neutral-400">No units yet.</p>
        </div>
      {:else if property.units.length > 0}
        <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-200">
                <th class="px-5 py-3 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Unit</th>
                <th class="px-5 py-3 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Floor</th>
                <th class="px-5 py-3 text-right text-xs font-medium text-neutral-400 uppercase tracking-wider">Area</th>
                <th class="px-5 py-3 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Category</th>
                <th class="px-5 py-3 text-center text-xs font-medium text-neutral-400 uppercase tracking-wider">Bed/Bath</th>
                <th class="px-5 py-3 text-right text-xs font-medium text-neutral-400 uppercase tracking-wider">Price</th>
                <th class="px-5 py-3 text-center text-xs font-medium text-neutral-400 uppercase tracking-wider">Status</th>
                <th class="px-5 py-3 text-right text-xs font-medium text-neutral-400 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each property.units as unit}
                <tr class="hover:bg-neutral-50 transition-colors">
                  <td class="px-5 py-3 font-medium text-neutral-900">
                    <a href={`/units/${unit.id}`} class="hover:underline">{unit.unit_number}</a>
                  </td>
                  <td class="px-5 py-3 text-neutral-500">{unit.floor ?? "\u2014"}</td>
                  <td class="px-5 py-3 text-right text-neutral-500 tabular-nums">{Number(unit.area_sqft).toLocaleString()} sqft</td>
                  <td class="px-5 py-3 text-neutral-500">{unitCategoryLabels[unit.unit_category] ?? unit.unit_category}</td>
                  <td class="px-5 py-3 text-center text-neutral-500">{unit.bedrooms ?? 0} / {unit.bathrooms ?? 0}</td>
                  <td class="px-5 py-3 text-right text-neutral-900 tabular-nums">{fmt(unit.asking_price)}</td>
                  <td class="px-5 py-3 text-center">
                    <StatusBadge status={unit.status} label={statusLabels[unit.status]} />
                  </td>
                  <td class="px-5 py-3 text-right">
                    <button onclick={() => openEditUnit(unit)} class="text-xs text-neutral-400 hover:text-neutral-900 mr-3 transition-colors">Edit</button>
                    <button onclick={() => deleteUnit(unit.id)} class="text-xs text-neutral-400 hover:text-red-600 transition-colors">Delete</button>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>
  {/if}

  <!-- Tab: Ownership -->
  {#if activeTab === "ownership"}
    <div class="space-y-4">
      <div class="flex justify-end">
        <button onclick={openAddOwnership} class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors">
          + Add Owner
        </button>
      </div>

      {#if showOwnershipForm}
        <div class="bg-white rounded-xl border border-neutral-200 p-6">
          <h3 class="text-sm font-semibold text-neutral-900 mb-4">{editingOwnership ? "Edit Ownership" : "New Ownership"}</h3>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Legal Owner Name</span>
                <input bind:value={ownershipForm.legal_owner_name} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
              </label>
            </div>
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Ownership Structure</span>
                <select bind:value={ownershipForm.ownership_structure} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
                  <option value="individual">Individual</option>
                  <option value="corporate">Corporate</option>
                  <option value="trust">Trust</option>
                  <option value="joint_venture">Joint Venture</option>
                </select>
              </label>
            </div>
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Ownership %</span>
                <input bind:value={ownershipForm.ownership_percentage} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="100.00" />
              </label>
            </div>
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Title Deed Number</span>
                <input bind:value={ownershipForm.title_deed_number} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
              </label>
            </div>
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Registration Authority</span>
                <input bind:value={ownershipForm.registration_authority} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
              </label>
            </div>
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Date of Registration</span>
                <DateInput bind:value={ownershipForm.date_of_registration} />
              </label>
            </div>
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Deed Expiry</span>
                <DateInput bind:value={ownershipForm.deed_expiry} />
              </label>
            </div>
          </div>
          <div class="flex gap-3 mt-4">
            <button onclick={saveOwnership} class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors">
              {editingOwnership ? "Update" : "Add"} Ownership
            </button>
            <button onclick={() => (showOwnershipForm = false)} class="px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors">
              Cancel
            </button>
          </div>
        </div>
      {/if}

      {#if property.ownerships.length === 0 && !showOwnershipForm}
        <div class="bg-white rounded-xl border border-neutral-200 p-12 text-center">
          <p class="text-sm text-neutral-400">No ownership records yet.</p>
        </div>
      {:else if property.ownerships.length > 0}
        <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-200">
                <th class="px-5 py-3 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Owner</th>
                <th class="px-5 py-3 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Structure</th>
                <th class="px-5 py-3 text-right text-xs font-medium text-neutral-400 uppercase tracking-wider">Ownership %</th>
                <th class="px-5 py-3 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Title Deed</th>
                <th class="px-5 py-3 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Registered</th>
                <th class="px-5 py-3 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Expiry</th>
                <th class="px-5 py-3 text-right text-xs font-medium text-neutral-400 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each property.ownerships as own}
                <tr class="hover:bg-neutral-50 transition-colors">
                  <td class="px-5 py-3 font-medium text-neutral-900">{own.legal_owner_name}</td>
                  <td class="px-5 py-3">
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-neutral-100 text-neutral-600">
                      {ownershipStructureLabels[own.ownership_structure]}
                    </span>
                  </td>
                  <td class="px-5 py-3 text-right text-neutral-900 tabular-nums">{own.ownership_percentage}%</td>
                  <td class="px-5 py-3 text-neutral-500">{own.title_deed_number}</td>
                  <td class="px-5 py-3 text-neutral-500">{fmtDate(own.date_of_registration)}</td>
                  <td class="px-5 py-3 text-neutral-500">{fmtDate(own.deed_expiry)}</td>
                  <td class="px-5 py-3 text-right">
                    <button onclick={() => openEditOwnership(own)} class="text-xs text-neutral-400 hover:text-neutral-900 mr-3 transition-colors">Edit</button>
                    <button onclick={() => deleteOwnership(own.id)} class="text-xs text-neutral-400 hover:text-red-600 transition-colors">Delete</button>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>
  {/if}

  <!-- Tab: Images -->
  {#if activeTab === "images"}
    <div class="space-y-4">
      <div class="flex justify-end">
        <label class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors cursor-pointer">
          {uploadingImage ? "Uploading..." : "+ Upload Images"}
          <input type="file" accept="image/*" multiple onchange={handleImageUpload} class="hidden" disabled={uploadingImage} />
        </label>
      </div>

      {#if property.images.length === 0}
        <div class="bg-white rounded-xl border border-neutral-200 p-12 text-center">
          <p class="text-sm text-neutral-400">No images yet.</p>
        </div>
      {:else}
        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {#each property.images as image}
            <div class="group relative bg-white rounded-xl border border-neutral-200 overflow-hidden">
              <img src={image.image} alt={image.caption || "Property image"} class="w-full h-48 object-cover" />
              {#if image.is_primary}
                <span class="absolute top-2 left-2 px-2 py-0.5 bg-neutral-900 text-white text-xs font-medium rounded">
                  Primary
                </span>
              {/if}
              <div class="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-colors flex items-end justify-center opacity-0 group-hover:opacity-100 pb-3 gap-2">
                {#if !image.is_primary}
                  <button onclick={() => setPrimaryImage(image.id)} class="px-3 py-1.5 bg-white rounded-lg text-xs font-medium text-neutral-900 hover:bg-neutral-100 transition-colors">
                    Set Primary
                  </button>
                {/if}
                <button onclick={() => deleteImage(image.id)} class="px-3 py-1.5 bg-white rounded-lg text-xs font-medium text-red-600 hover:bg-red-50 transition-colors">
                  Delete
                </button>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}

  <!-- Tab: Documents -->
  {#if activeTab === "documents"}
    <div class="space-y-4">
      <DocumentRecordsTable
        title="Repository Documents"
        subtitle="Controlled repository records linked to this land/property."
        query={{ land: Number(propertyId) }}
        pageSize={10}
        showViewAll={true}
        viewAllHref={`/documents/repository?land=${propertyId}`}
        emptyMessage="No controlled repository documents are linked to this property yet."
      />

      <div class="flex justify-end">
        <button onclick={() => (showDocForm = true)} class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors">
          + Upload Document
        </button>
      </div>

      {#if showDocForm}
        <div class="bg-white rounded-xl border border-neutral-200 p-6">
          <h3 class="text-sm font-semibold text-neutral-900 mb-4">Upload Document</h3>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Title</span>
                <input bind:value={docForm.title} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
              </label>
            </div>
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Type</span>
                <select bind:value={docForm.document_type} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
                  <option value="deed">Deed</option>
                  <option value="contract">Contract</option>
                  <option value="survey">Survey</option>
                  <option value="permit">Permit</option>
                  <option value="inspection">Inspection Report</option>
                  <option value="appraisal">Appraisal</option>
                  <option value="insurance">Insurance</option>
                  <option value="tax">Tax Document</option>
                  <option value="certificate_of_occupancy">Certificate of Occupancy</option>
                  <option value="lease_agreement">Lease Agreement</option>
                  <option value="easement">Easement</option>
                  <option value="mortgage">Mortgage</option>
                  <option value="government_approval">Government Approval</option>
                  <option value="other">Other</option>
                </select>
              </label>
            </div>
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">File</span>
                <input type="file" onchange={(e) => { const t = e.target as HTMLInputElement; docForm.file = t.files?.[0] ?? null; }} class="w-full text-sm text-neutral-500 file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border file:border-neutral-200 file:text-sm file:font-medium file:bg-white file:text-neutral-600 hover:file:bg-neutral-50" />
              </label>
            </div>
          </div>
          <div class="flex gap-3 mt-4">
            <button onclick={saveDocument} class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors">
              Upload
            </button>
            <button onclick={() => (showDocForm = false)} class="px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors">
              Cancel
            </button>
          </div>
        </div>
      {/if}

      {#if property.documents.length === 0 && !showDocForm}
        <div class="bg-white rounded-xl border border-neutral-200 p-12 text-center">
          <p class="text-sm text-neutral-400">No documents yet.</p>
        </div>
      {:else if property.documents.length > 0}
        <div class="bg-white rounded-xl border border-neutral-200 divide-y divide-neutral-100">
          {#each property.documents as doc}
            <div class="flex items-center justify-between px-5 py-4">
              <div class="flex items-center gap-4">
                <div class="w-10 h-10 rounded-lg bg-neutral-100 flex items-center justify-center">
                  <svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
                  </svg>
                </div>
                <div>
                  <p class="text-sm font-medium text-neutral-900">{doc.title}</p>
                  <div class="flex items-center gap-2 mt-0.5">
                    <span class="text-xs text-neutral-400">{docTypeLabels[doc.document_type]}</span>
                    <span class="text-xs text-neutral-300">&middot;</span>
                    <span class="text-xs text-neutral-400">{fmtDate(doc.uploaded_at)}</span>
                  </div>
                </div>
              </div>
              <div class="flex items-center gap-3">
                <a href={doc.file} target="_blank" rel="noopener" class="text-xs text-neutral-400 hover:text-neutral-900 transition-colors">View</a>
                <a href={doc.file} download class="text-xs text-neutral-400 hover:text-neutral-900 transition-colors">Download</a>
                <button onclick={() => deleteDocument(doc.id)} class="text-xs text-neutral-400 hover:text-red-600 transition-colors">Delete</button>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}

  <!-- Tab: Valuations -->
  {#if activeTab === "valuations"}
    <div class="space-y-4">
      <div class="flex justify-end">
        <button onclick={() => (showValForm = true)} class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors">
          + Add Valuation
        </button>
      </div>

      {#if showValForm}
        <div class="bg-white rounded-xl border border-neutral-200 p-6">
          <h3 class="text-sm font-semibold text-neutral-900 mb-4">New Valuation</h3>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Date</span>
                <DateInput bind:value={valForm.valuation_date} />
              </label>
            </div>
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Value ({currency.config.symbol})</span>
                <input bind:value={valForm.value} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
              </label>
            </div>
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Type</span>
                <select bind:value={valForm.valuation_type} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
                  <option value="appraisal">Professional Appraisal</option>
                  <option value="internal">Internal Estimate</option>
                  <option value="market">Market Comparable</option>
                  <option value="tax">Tax Assessment</option>
                </select>
              </label>
            </div>
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Appraiser</span>
                <input bind:value={valForm.appraiser} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
              </label>
            </div>
            <div class="md:col-span-2">
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Notes</span>
                <input bind:value={valForm.notes} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
              </label>
            </div>
          </div>
          <div class="flex gap-3 mt-4">
            <button onclick={saveValuation} class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors">
              Save Valuation
            </button>
            <button onclick={() => (showValForm = false)} class="px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors">
              Cancel
            </button>
          </div>
        </div>
      {/if}

      {#if property.valuations.length === 0 && !showValForm}
        <div class="bg-white rounded-xl border border-neutral-200 p-12 text-center">
          <p class="text-sm text-neutral-400">No valuations yet.</p>
        </div>
      {:else if property.valuations.length > 0}
        <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-200">
                <th class="px-5 py-3 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Date</th>
                <th class="px-5 py-3 text-right text-xs font-medium text-neutral-400 uppercase tracking-wider">Value</th>
                <th class="px-5 py-3 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Type</th>
                <th class="px-5 py-3 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Appraiser</th>
                <th class="px-5 py-3 text-right text-xs font-medium text-neutral-400 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each property.valuations as val}
                <tr class="hover:bg-neutral-50 transition-colors">
                  <td class="px-5 py-3 text-neutral-900">{fmtDate(val.valuation_date)}</td>
                  <td class="px-5 py-3 text-right text-neutral-900 tabular-nums font-medium">{fmt(val.value)}</td>
                  <td class="px-5 py-3">
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-neutral-100 text-neutral-600">
                      {valTypeLabels[val.valuation_type]}
                    </span>
                  </td>
                  <td class="px-5 py-3 text-neutral-500">{val.appraiser || "\u2014"}</td>
                  <td class="px-5 py-3 text-right">
                    <button onclick={() => deleteValuation(val.id)} class="text-xs text-neutral-400 hover:text-red-600 transition-colors">Delete</button>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>
  {/if}

  <!-- Tab: Encumbrances -->
  {#if activeTab === "encumbrances"}
    <div class="space-y-4">
      <div class="flex justify-end">
        <button onclick={openAddEncumbrance} class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors">
          + Add Encumbrance
        </button>
      </div>

      {#if showEncumbranceForm}
        <div class="bg-white rounded-xl border border-neutral-200 p-6">
          <h3 class="text-sm font-semibold text-neutral-900 mb-4">{editingEncumbrance ? "Edit Encumbrance" : "New Encumbrance"}</h3>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Type</span>
                <select bind:value={encumbranceForm.encumbrance_type} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
                  <option value="mortgage">Mortgage</option>
                  <option value="lien">Lien</option>
                  <option value="legal_dispute">Legal Dispute</option>
                  <option value="court_case">Court Case</option>
                  <option value="tax_arrears">Tax Arrears</option>
                </select>
              </label>
            </div>
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Title</span>
                <input bind:value={encumbranceForm.title} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
              </label>
            </div>
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Amount ({currency.config.symbol})</span>
                <input bind:value={encumbranceForm.amount} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-neutral-900" placeholder="0.00" />
              </label>
            </div>
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Status</span>
                <select bind:value={encumbranceForm.status} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900">
                  <option value="active">Active</option>
                  <option value="resolved">Resolved</option>
                  <option value="pending">Pending</option>
                </select>
              </label>
            </div>
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Date Filed</span>
                <DateInput bind:value={encumbranceForm.date_filed} />
              </label>
            </div>
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Date Resolved</span>
                <DateInput bind:value={encumbranceForm.date_resolved} />
              </label>
            </div>
            <div>
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Reference Number</span>
                <input bind:value={encumbranceForm.reference_number} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
              </label>
            </div>
            <div class="md:col-span-2">
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Description</span>
                <input bind:value={encumbranceForm.description} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900" />
              </label>
            </div>
            <div class="md:col-span-3">
              <label class="block">
                <span class="block text-xs font-medium text-neutral-500 mb-1">Notes</span>
                <textarea bind:value={encumbranceForm.notes} rows={2} class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-neutral-900"></textarea>
              </label>
            </div>
          </div>
          <div class="flex gap-3 mt-4">
            <button onclick={saveEncumbrance} class="px-4 py-2 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 transition-colors">
              {editingEncumbrance ? "Update" : "Add"} Encumbrance
            </button>
            <button onclick={() => (showEncumbranceForm = false)} class="px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors">
              Cancel
            </button>
          </div>
        </div>
      {/if}

      {#if property.encumbrances.length === 0 && !showEncumbranceForm}
        <div class="bg-white rounded-xl border border-neutral-200 p-12 text-center">
          <p class="text-sm text-neutral-400">No encumbrances recorded.</p>
        </div>
      {:else if property.encumbrances.length > 0}
        <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-200">
                <th class="px-5 py-3 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Type</th>
                <th class="px-5 py-3 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Title</th>
                <th class="px-5 py-3 text-right text-xs font-medium text-neutral-400 uppercase tracking-wider">Amount</th>
                <th class="px-5 py-3 text-center text-xs font-medium text-neutral-400 uppercase tracking-wider">Status</th>
                <th class="px-5 py-3 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Filed</th>
                <th class="px-5 py-3 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Resolved</th>
                <th class="px-5 py-3 text-right text-xs font-medium text-neutral-400 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each property.encumbrances as enc}
                <tr class="hover:bg-neutral-50 transition-colors">
                  <td class="px-5 py-3">
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-neutral-100 text-neutral-600">
                      {encumbranceTypeLabels[enc.encumbrance_type]}
                    </span>
                  </td>
                  <td class="px-5 py-3 font-medium text-neutral-900">{enc.title}</td>
                  <td class="px-5 py-3 text-right text-neutral-900 tabular-nums">{fmt(enc.amount)}</td>
                  <td class="px-5 py-3 text-center">
                    <StatusBadge status={enc.status} />
                  </td>
                  <td class="px-5 py-3 text-neutral-500">{fmtDate(enc.date_filed)}</td>
                  <td class="px-5 py-3 text-neutral-500">{fmtDate(enc.date_resolved)}</td>
                  <td class="px-5 py-3 text-right">
                    <button onclick={() => openEditEncumbrance(enc)} class="text-xs text-neutral-400 hover:text-neutral-900 mr-3 transition-colors">Edit</button>
                    <button onclick={() => deleteEncumbrance(enc.id)} class="text-xs text-neutral-400 hover:text-red-600 transition-colors">Delete</button>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>
  {/if}
{/if}

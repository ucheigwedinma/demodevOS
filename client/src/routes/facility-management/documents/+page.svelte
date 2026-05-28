<script lang="ts">
  import { ApiError, api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { PaginatedResponse } from "$lib/types";

  type DocumentsTab = "blueprints" | "manuals" | "logs" | "certificates";
  type FacilityDocumentType =
    | "blueprint"
    | "drawing"
    | "equipment_manual"
    | "maintenance_log"
    | "inspection_report"
    | "manual"
    | "certificate"
    | "warranty"
    | "compliance_certificate"
    | "compliance";
  type FacilityDocumentStatus = "active" | "review_due" | "expired" | "archived";
  type FacilityDocumentSource = "manual" | "generated";

  interface FacilityLookupItem {
    id: number;
    facility_code: string;
    property_name: string;
  }

  interface SpaceLookupItem {
    id: number;
    facility: number;
    facility_code: string;
    zone_code: string;
    unit_number: string;
    space_label: string;
    property_name: string;
  }

  interface AssetLookupItem {
    id: number;
    component_id: string;
    label: string;
    facility: number | null;
    facility_code: string;
  }

  interface WorkOrderLookupItem {
    id: number;
    title: string;
    status: string;
    facility: number | null;
    facility_code: string;
  }

  interface InspectionLookupItem {
    id: number;
    title: string;
    status: string;
    scheduled_date: string;
    facility: number | null;
  }

  interface FacilityDocumentItem {
    id: number;
    property: number;
    property_name: string;
    facility: number | null;
    facility_code: string;
    facility_space: number | null;
    space_label: string;
    asset_component: number | null;
    asset_component_name: string;
    linked_work_order: number | null;
    work_order_title: string;
    linked_inspection: number | null;
    inspection_title: string;
    title: string;
    document_type: FacilityDocumentType;
    document_type_display: string;
    description: string;
    version_label: string;
    reference_number: string;
    issued_date: string | null;
    expiry_date: string | null;
    review_due_date: string | null;
    status: FacilityDocumentStatus;
    status_display: string;
    source: FacilityDocumentSource;
    source_display: string;
    generated_summary: string;
    uploaded_by: number | null;
    uploaded_by_name: string;
    file_url: string;
    notes: string;
    created_at: string;
    updated_at: string;
  }

  interface DocumentsOverview {
    generated_at: string;
    kpis: {
      total_documents: number;
      blueprints_drawings: number;
      equipment_manuals: number;
      maintenance_logs: number;
      generated_maintenance_logs: number;
      compliance_certificates: number;
      review_due_documents: number;
      expired_documents: number;
    };
    document_type_breakdown: Array<{ key: FacilityDocumentType; count: number }>;
    review_watchlist: FacilityDocumentItem[];
    maintenance_log_watchlist: FacilityDocumentItem[];
    blueprint_watchlist: FacilityDocumentItem[];
  }

  interface DocumentsLookupsResponse {
    facilities: FacilityLookupItem[];
    spaces: SpaceLookupItem[];
    assets: AssetLookupItem[];
    work_orders: WorkOrderLookupItem[];
    inspections: InspectionLookupItem[];
  }

  interface WorkflowSyncResult {
    documents_synced: number;
    maintenance_logs_generated: number;
    review_due_documents: number;
    expired_documents: number;
    compliance_certificates_flagged: number;
  }

  const tabs: { key: DocumentsTab; label: string }[] = [
    { key: "blueprints", label: "Blueprints & Drawings" },
    { key: "manuals", label: "Equipment Manuals" },
    { key: "logs", label: "Maintenance Logs" },
    { key: "certificates", label: "Compliance Certificates" },
  ];

  const documentTypeOptions: { value: FacilityDocumentType; label: string }[] = [
    { value: "blueprint", label: "Facility Blueprint" },
    { value: "drawing", label: "Technical Drawing" },
    { value: "equipment_manual", label: "Equipment Manual" },
    { value: "maintenance_log", label: "Maintenance Log" },
    { value: "compliance_certificate", label: "Compliance Certificate" },
    { value: "manual", label: "Manual" },
    { value: "certificate", label: "Certificate" },
    { value: "warranty", label: "Warranty" },
  ];

  const statusOptions: { value: FacilityDocumentStatus; label: string }[] = [
    { value: "active", label: "Active" },
    { value: "review_due", label: "Review Due" },
    { value: "expired", label: "Expired" },
    { value: "archived", label: "Archived" },
  ];

  let activeTab = $state<DocumentsTab>("blueprints");
  let loading = $state(true);
  let refreshing = $state(false);
  let syncingWorkflows = $state(false);

  let overview = $state<DocumentsOverview | null>(null);
  let documents = $state<FacilityDocumentItem[]>([]);

  let facilitiesLookup = $state<FacilityLookupItem[]>([]);
  let spacesLookup = $state<SpaceLookupItem[]>([]);
  let assetsLookup = $state<AssetLookupItem[]>([]);
  let workOrdersLookup = $state<WorkOrderLookupItem[]>([]);
  let inspectionsLookup = $state<InspectionLookupItem[]>([]);

  let search = $state("");
  let facilityFilter = $state("");
  let statusFilter = $state("");

  let showDocumentDrawer = $state(false);
  let saving = $state(false);
  let selectedFile = $state<File | null>(null);

  let documentForm = $state({
    facility: "",
    facility_space: "",
    asset_component: "",
    linked_work_order: "",
    linked_inspection: "",
    title: "",
    document_type: "blueprint" as FacilityDocumentType,
    description: "",
    version_label: "",
    reference_number: "",
    issued_date: todayInput(),
    expiry_date: "",
    review_due_date: "",
    generated_summary: "",
    notes: "",
  });

  function todayInput(offsetDays = 0): string {
    const value = new Date();
    value.setDate(value.getDate() + offsetDays);
    return value.toISOString().slice(0, 10);
  }

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  function devFillDocForm() {
    const titles = ["As-Built Drawing — Block A Foundation", "HVAC System O&M Manual", "Fire Suppression System Schematic", "Elevator Maintenance Certificate", "Building Energy Audit Report", "Structural Load Assessment v2"];
    const types: FacilityDocumentType[] = ["blueprint", "manual", "certificate", "inspection_report", "warranty", "compliance"];
    const idx = Math.floor(Math.random() * titles.length);
    documentForm.title = titles[idx];
    documentForm.document_type = types[idx % types.length];
    documentForm.description = `${titles[idx]} — uploaded for facility records and compliance tracking.`;
    documentForm.version_label = `v${Math.floor(Math.random() * 3) + 1}.${Math.floor(Math.random() * 10)}`;
    documentForm.reference_number = `DOC-${Math.floor(Math.random() * 90000) + 10000}`;
    documentForm.issued_date = todayInput(-30);
    documentForm.expiry_date = todayInput(335);
    documentForm.review_due_date = todayInput(300);
    documentForm.generated_summary = "";
    documentForm.notes = "Original stored in facility document vault. Digital copy for reference.";
    if (facilitiesLookup.length > 0 && !documentForm.facility) documentForm.facility = String(facilitiesLookup[0].id);
  }

  function toNumber(value: unknown): number {
    const parsed = Number(value ?? 0);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function fmtInt(value: unknown): string {
    return toNumber(value).toLocaleString("en-US");
  }

  function fmtDate(value: string | null | undefined): string {
    if (!value) return "--";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "--";
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function fmtDateTime(value: string | null | undefined): string {
    if (!value) return "--";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "--";
    return date.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function fmtLabel(value: string): string {
    return value.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
  }

  function parseApiMessage(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      if (typeof error.data.detail === "string") return error.data.detail;
      const firstField = Object.values(error.fieldErrors)[0]?.[0];
      if (typeof firstField === "string") return firstField;
    }
    return fallback;
  }

  function defaultTypeForTab(tab: DocumentsTab): FacilityDocumentType {
    if (tab === "manuals") return "equipment_manual";
    if (tab === "logs") return "maintenance_log";
    if (tab === "certificates") return "compliance_certificate";
    return "blueprint";
  }

  function matchesTab(document: FacilityDocumentItem, tab: DocumentsTab): boolean {
    if (tab === "blueprints") return ["blueprint", "drawing"].includes(document.document_type);
    if (tab === "manuals") return document.document_type === "equipment_manual";
    if (tab === "logs") return document.document_type === "maintenance_log";
    if (tab === "certificates") return document.document_type === "compliance_certificate";
    return true;
  }

  function badgeClass(status: FacilityDocumentStatus): string {
    if (status === "expired") return "bg-red-50 text-red-700";
    if (status === "review_due") return "bg-amber-50 text-amber-700";
    if (status === "archived") return "bg-neutral-100 text-neutral-600";
    return "bg-emerald-50 text-emerald-700";
  }

  function filteredSpacesFor(facilityId: string): SpaceLookupItem[] {
    if (!facilityId) return spacesLookup;
    return spacesLookup.filter((space) => space.facility === Number(facilityId));
  }

  function filteredAssetsFor(facilityId: string): AssetLookupItem[] {
    if (!facilityId) return assetsLookup;
    return assetsLookup.filter((asset) => asset.facility === Number(facilityId));
  }

  function filteredWorkOrdersFor(facilityId: string): WorkOrderLookupItem[] {
    if (!facilityId) return workOrdersLookup;
    return workOrdersLookup.filter((workOrder) => workOrder.facility === Number(facilityId));
  }

  function filteredInspectionsFor(facilityId: string): InspectionLookupItem[] {
    if (!facilityId) return inspectionsLookup;
    return inspectionsLookup.filter((inspection) => inspection.facility === Number(facilityId));
  }

  function resetDocumentForm() {
    documentForm = {
      facility: "",
      facility_space: "",
      asset_component: "",
      linked_work_order: "",
      linked_inspection: "",
      title: "",
      document_type: defaultTypeForTab(activeTab),
      description: "",
      version_label: "",
      reference_number: "",
      issued_date: todayInput(),
      expiry_date: "",
      review_due_date: "",
      generated_summary: "",
      notes: "",
    };
    selectedFile = null;
  }

  function openDocumentDrawer(tab: DocumentsTab = activeTab) {
    resetDocumentForm();
    documentForm.document_type = defaultTypeForTab(tab);
    showDocumentDrawer = true;
  }

  function closeDocumentDrawer() {
    showDocumentDrawer = false;
    resetDocumentForm();
  }

  async function fetchOverview() {
    overview = await api.get<DocumentsOverview>("/facility-management/documents/overview/");
  }

  async function fetchLookups() {
    const response = await api.get<DocumentsLookupsResponse>("/facility-management/documents/lookups/");
    facilitiesLookup = response.facilities;
    spacesLookup = response.spaces;
    assetsLookup = response.assets;
    workOrdersLookup = response.work_orders;
    inspectionsLookup = response.inspections;
  }

  async function fetchDocuments() {
    const response = await api.get<PaginatedResponse<FacilityDocumentItem>>("/facility-management/documents/records/", {
      page_size: "400",
    });
    documents = response.results;
  }

  async function refreshAll(showLoader = false) {
    if (showLoader) {
      loading = true;
    } else if (!loading) {
      refreshing = true;
    }

    try {
      await Promise.all([fetchOverview(), fetchLookups(), fetchDocuments()]);
    } catch {
      overview = null;
      documents = [];
      toast.error("Load failed", "Could not load facility documents.");
    } finally {
      loading = false;
      refreshing = false;
    }
  }

  async function runWorkflows() {
    syncingWorkflows = true;
    try {
      const result = await api.post<WorkflowSyncResult>("/facility-management/documents/sync/", {});
      toast.success(
        "Workflows completed",
        `${fmtInt(result.documents_synced)} docs synced, ${fmtInt(result.maintenance_logs_generated)} maintenance logs generated.`,
      );
      await refreshAll();
    } catch (error) {
      toast.error("Workflow failed", parseApiMessage(error, "Could not run document workflows."));
    } finally {
      syncingWorkflows = false;
    }
  }

  async function handleCreate(event: SubmitEvent) {
    event.preventDefault();
    saving = true;

    try {
      const payload = new FormData();
      payload.set("facility", documentForm.facility);
      if (documentForm.facility_space) payload.set("facility_space", documentForm.facility_space);
      if (documentForm.asset_component) payload.set("asset_component", documentForm.asset_component);
      if (documentForm.linked_work_order) payload.set("linked_work_order", documentForm.linked_work_order);
      if (documentForm.linked_inspection) payload.set("linked_inspection", documentForm.linked_inspection);
      payload.set("title", documentForm.title);
      payload.set("document_type", documentForm.document_type);
      payload.set("description", documentForm.description);
      payload.set("version_label", documentForm.version_label);
      payload.set("reference_number", documentForm.reference_number);
      if (documentForm.issued_date) payload.set("issued_date", documentForm.issued_date);
      if (documentForm.expiry_date) payload.set("expiry_date", documentForm.expiry_date);
      if (documentForm.review_due_date) payload.set("review_due_date", documentForm.review_due_date);
      if (documentForm.generated_summary) payload.set("generated_summary", documentForm.generated_summary);
      payload.set("notes", documentForm.notes);
      if (selectedFile) payload.set("file", selectedFile);

      await api.upload<FacilityDocumentItem>("/facility-management/documents/records/", payload);
      toast.success("Document added", "The facility document record has been saved.");
      closeDocumentDrawer();
      await refreshAll();
    } catch (error) {
      toast.error("Save failed", parseApiMessage(error, "Could not save the facility document."));
    } finally {
      saving = false;
    }
  }

  function handleFileChange(event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    selectedFile = input.files?.[0] ?? null;
  }

  function currentDocuments(): FacilityDocumentItem[] {
    const query = search.trim().toLowerCase();
    return documents.filter((document) => {
      if (!matchesTab(document, activeTab)) return false;
      if (facilityFilter && String(document.facility ?? "") !== facilityFilter) return false;
      if (statusFilter && document.status !== statusFilter) return false;
      if (!query) return true;
      return [
        document.title,
        document.document_type_display,
        document.property_name,
        document.facility_code,
        document.asset_component_name,
        document.work_order_title,
        document.reference_number,
      ]
        .join(" ")
        .toLowerCase()
        .includes(query);
    });
  }

  $effect(() => {
    refreshAll(true);
  });
</script>

<div class="space-y-6">
  <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-violet-600">Facility Management</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Documents & Drawings</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Facility blueprints, equipment manuals, maintenance logs, and compliance certificates in one controlled register.
      </p>
      {#if overview?.generated_at}
        <p class="mt-1 text-xs text-neutral-400">Last refreshed: {fmtDateTime(overview.generated_at)}</p>
      {/if}
    </div>

    <div class="flex items-center gap-2">
      <button
        type="button"
        onclick={runWorkflows}
        disabled={syncingWorkflows}
        class="inline-flex items-center gap-2 rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        <svg
          class={`h-4 w-4 ${syncingWorkflows ? "animate-spin" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          stroke-width="1.8"
          aria-hidden="true"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992V4.356m-1.636 14.288A9 9 0 1 1 21 12.003" />
        </svg>
        {syncingWorkflows ? "Running Workflows..." : "Run Workflows"}
      </button>
      <button
        onclick={() => refreshAll()}
        disabled={refreshing}
        class="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-neutral-300 bg-white text-neutral-700 hover:border-neutral-900 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-60"
        aria-label={refreshing ? "Refreshing facility documents" : "Refresh facility documents"}
        title={refreshing ? "Refreshing facility documents" : "Refresh facility documents"}
      >
        <svg
          class={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          stroke-width="1.8"
          aria-hidden="true"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992V4.356m-1.636 14.288A9 9 0 1 1 21 12.003" />
        </svg>
      </button>
    </div>
  </div>

  {#if loading}
    <div class="rounded-2xl border border-neutral-200 bg-white p-10 text-center text-sm text-neutral-500">
      Loading facility documents...
    </div>
  {:else if !overview}
    <div class="rounded-2xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">
      Facility documents are unavailable right now.
    </div>
  {:else}
    <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <section class="rounded-2xl border border-violet-200/80 bg-linear-to-br from-violet-100 via-fuchsia-50 to-indigo-100 p-5 shadow-sm shadow-violet-200/40">
        <p class="text-xs font-semibold uppercase tracking-wide text-violet-700">Blueprints & Drawings</p>
        <p class="mt-3 text-2xl font-semibold text-violet-950">{fmtInt(overview.kpis.blueprints_drawings)}</p>
        <p class="mt-2 text-xs text-violet-800">Controlled layout and technical drawing records.</p>
      </section>
      <section class="rounded-2xl border border-violet-200/80 bg-linear-to-br from-violet-100 via-fuchsia-50 to-indigo-100 p-5 shadow-sm shadow-violet-200/40">
        <p class="text-xs font-semibold uppercase tracking-wide text-violet-700">Equipment Manuals</p>
        <p class="mt-3 text-2xl font-semibold text-violet-950">{fmtInt(overview.kpis.equipment_manuals)}</p>
        <p class="mt-2 text-xs text-violet-800">Manufacturer and operating references tied to assets.</p>
      </section>
      <section class="rounded-2xl border border-violet-200/80 bg-linear-to-br from-violet-100 via-fuchsia-50 to-indigo-100 p-5 shadow-sm shadow-violet-200/40">
        <p class="text-xs font-semibold uppercase tracking-wide text-violet-700">Maintenance Logs</p>
        <p class="mt-3 text-2xl font-semibold text-violet-950">{fmtInt(overview.kpis.maintenance_logs)}</p>
        <p class="mt-2 text-xs text-violet-800">
          Generated logs: {fmtInt(overview.kpis.generated_maintenance_logs)}
        </p>
      </section>
      <section class="rounded-2xl border border-violet-200/80 bg-linear-to-br from-violet-100 via-fuchsia-50 to-indigo-100 p-5 shadow-sm shadow-violet-200/40">
        <p class="text-xs font-semibold uppercase tracking-wide text-violet-700">Compliance Certificates</p>
        <p class="mt-3 text-2xl font-semibold text-violet-950">{fmtInt(overview.kpis.compliance_certificates)}</p>
        <p class="mt-2 text-xs text-violet-800">
          Review due: {fmtInt(overview.kpis.review_due_documents)} | Expired: {fmtInt(overview.kpis.expired_documents)}
        </p>
      </section>
    </div>

    <section class="rounded-2xl border border-neutral-200 bg-white p-5">
      <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Document Register</h2>
          <p class="text-xs text-neutral-500">Upload and track facility records with automated maintenance log generation.</p>
        </div>
        <button
          type="button"
          onclick={() => openDocumentDrawer()}
          class="inline-flex items-center justify-center rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-neutral-800"
        >
          Add Document
        </button>
      </div>

      <div class="mt-4 flex flex-wrap gap-2">
        {#each tabs as tab}
          <button
            type="button"
            onclick={() => (activeTab = tab.key)}
            class={`rounded-full px-4 py-2 text-sm font-medium transition ${
              activeTab === tab.key
                ? "bg-neutral-900 text-white"
                : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200 hover:text-neutral-900"
            }`}
          >
            {tab.label}
          </button>
        {/each}
      </div>

      <div class="mt-4 grid gap-3 md:grid-cols-3">
        <input
          bind:value={search}
          class="rounded-lg border border-neutral-200 px-3 py-2.5 text-sm"
          placeholder="Search title, asset, reference, or facility"
        />
        <select bind:value={facilityFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
          <option value="">All facilities</option>
          {#each facilitiesLookup as facility}
            <option value={String(facility.id)}>{facility.facility_code} - {facility.property_name}</option>
          {/each}
        </select>
        <select bind:value={statusFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
          <option value="">All statuses</option>
          {#each statusOptions as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
      </div>

      <div class="mt-5 overflow-x-auto">
        <table class="min-w-full divide-y divide-neutral-200 text-sm">
          <thead class="bg-neutral-50 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">
            <tr>
              <th class="px-4 py-3">Document</th>
              <th class="px-4 py-3">Location</th>
              <th class="px-4 py-3">Linkage</th>
              <th class="px-4 py-3">Status</th>
              <th class="px-4 py-3">Review / Expiry</th>
              <th class="px-4 py-3">Source</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-200 bg-white text-neutral-700">
            {#each currentDocuments() as document}
              <tr class="align-top">
                <td class="px-4 py-3">
                  <div class="font-medium text-neutral-900">{document.title}</div>
                  <div class="mt-1 text-xs text-neutral-500">
                    {document.document_type_display}
                    {#if document.version_label}
                      • {document.version_label}
                    {/if}
                    {#if document.reference_number}
                      • Ref {document.reference_number}
                    {/if}
                  </div>
                  {#if document.file_url}
                    <a href={document.file_url} target="_blank" rel="noreferrer" class="mt-2 inline-flex text-xs font-medium text-neutral-900 underline decoration-neutral-300 underline-offset-2 hover:decoration-neutral-900">
                      Open file
                    </a>
                  {/if}
                </td>
                <td class="px-4 py-3 text-xs text-neutral-600">
                  <div>{document.facility_code || "--"}</div>
                  <div class="mt-1">{document.space_label || document.property_name}</div>
                  {#if document.asset_component_name}
                    <div class="mt-1 text-neutral-500">Asset: {document.asset_component_name}</div>
                  {/if}
                </td>
                <td class="px-4 py-3 text-xs text-neutral-600">
                  <div>{document.work_order_title || "--"}</div>
                  <div class="mt-1">{document.inspection_title || "--"}</div>
                </td>
                <td class="px-4 py-3">
                  <span class={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${badgeClass(document.status)}`}>
                    {document.status_display}
                  </span>
                </td>
                <td class="px-4 py-3 text-xs text-neutral-600">
                  <div>Issued: {fmtDate(document.issued_date)}</div>
                  <div class="mt-1">Review: {fmtDate(document.review_due_date)}</div>
                  <div class="mt-1">Expiry: {fmtDate(document.expiry_date)}</div>
                </td>
                <td class="px-4 py-3 text-xs text-neutral-600">
                  <div>{document.source_display}</div>
                  <div class="mt-1">{document.uploaded_by_name || "--"}</div>
                </td>
              </tr>
            {/each}
            {#if currentDocuments().length === 0}
              <tr>
                <td colspan="6" class="px-4 py-8 text-center text-sm text-neutral-500">
                  No documents match this view yet.
                </td>
              </tr>
            {/if}
          </tbody>
        </table>
      </div>
    </section>

    <div class="grid gap-4 xl:grid-cols-3">
      <section class="rounded-2xl border border-violet-200/80 bg-linear-to-br from-violet-100 via-fuchsia-50 to-indigo-100 p-5 shadow-sm shadow-violet-200/40">
        <h2 class="text-sm font-semibold uppercase tracking-wide text-violet-700">Review Watchlist</h2>
        <div class="mt-4 space-y-3">
          {#each overview.review_watchlist as document}
            <div class="rounded-xl border border-violet-200/70 bg-white/65 p-3 backdrop-blur-sm">
              <div class="flex items-start justify-between gap-3">
                <div>
                  <p class="font-medium text-violet-950">{document.title}</p>
                  <p class="mt-1 text-xs text-violet-700">{document.facility_code || document.property_name}</p>
                </div>
                <span class={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold ${badgeClass(document.status)}`}>
                  {document.status_display}
                </span>
              </div>
              <p class="mt-2 text-xs text-violet-800">
                Review: {fmtDate(document.review_due_date)} | Expiry: {fmtDate(document.expiry_date)}
              </p>
            </div>
          {/each}
          {#if overview.review_watchlist.length === 0}
            <p class="text-sm text-violet-700">No documents are due for review right now.</p>
          {/if}
        </div>
      </section>

      <section class="rounded-2xl border border-violet-200/80 bg-linear-to-br from-violet-100 via-fuchsia-50 to-indigo-100 p-5 shadow-sm shadow-violet-200/40">
        <h2 class="text-sm font-semibold uppercase tracking-wide text-violet-700">Maintenance Log Feed</h2>
        <div class="mt-4 space-y-3">
          {#each overview.maintenance_log_watchlist as document}
            <div class="rounded-xl border border-violet-200/70 bg-white/65 p-3 backdrop-blur-sm">
              <p class="font-medium text-violet-950">{document.title}</p>
              <p class="mt-1 text-xs text-violet-700">{document.work_order_title || document.asset_component_name || document.facility_code}</p>
              <p class="mt-2 text-xs text-violet-800 line-clamp-3">
                {document.generated_summary || document.description || "Maintenance record available."}
              </p>
            </div>
          {/each}
          {#if overview.maintenance_log_watchlist.length === 0}
            <p class="text-sm text-violet-700">Generated maintenance logs will appear here after workflow runs.</p>
          {/if}
        </div>
      </section>

      <section class="rounded-2xl border border-violet-200/80 bg-linear-to-br from-violet-100 via-fuchsia-50 to-indigo-100 p-5 shadow-sm shadow-violet-200/40">
        <h2 class="text-sm font-semibold uppercase tracking-wide text-violet-700">Recent Blueprint Set</h2>
        <div class="mt-4 space-y-3">
          {#each overview.blueprint_watchlist as document}
            <div class="rounded-xl border border-violet-200/70 bg-white/65 p-3 backdrop-blur-sm">
              <p class="font-medium text-violet-950">{document.title}</p>
              <p class="mt-1 text-xs text-violet-700">{document.document_type_display} • {document.facility_code || document.property_name}</p>
              <p class="mt-2 text-xs text-violet-800">
                Version {document.version_label || "--"} • Updated {fmtDate(document.updated_at)}
              </p>
            </div>
          {/each}
          {#if overview.blueprint_watchlist.length === 0}
            <p class="text-sm text-violet-700">Blueprint and drawing uploads will show here.</p>
          {/if}
        </div>
      </section>
    </div>
  {/if}
</div>

{#if showDocumentDrawer}
  <button
    type="button"
    class="fixed inset-0 z-40 bg-neutral-900/35"
    onclick={closeDocumentDrawer}
    tabindex="-1"
    aria-label="Close facility document drawer"
  ></button>
  <aside class="fixed inset-y-0 right-0 z-50 flex w-full max-w-3xl flex-col bg-white shadow-2xl animate-slide-in-right">
    <div class="flex items-center justify-between border-b border-neutral-100 px-6 py-4">
      <div>
        <h2 class="text-lg font-semibold text-neutral-900">Add Facility Document</h2>
        <p class="mt-1 text-xs text-neutral-500">All facility management forms stay in drawers for consistent workflow handling.</p>
      </div>
      <button
        type="button"
        onclick={closeDocumentDrawer}
        class="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        aria-label="Close facility document drawer"
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div class="flex-1 overflow-y-auto px-6 py-5">
      <form id="facility-document-form" class="grid gap-4 md:grid-cols-2" onsubmit={handleCreate}>
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Facility</span>
          <select bind:value={documentForm.facility} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Select facility</option>
            {#each facilitiesLookup as facility}
              <option value={String(facility.id)}>{facility.facility_code} - {facility.property_name}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Document Type</span>
          <select bind:value={documentForm.document_type} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            {#each documentTypeOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Room / Space</span>
          <select bind:value={documentForm.facility_space} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Optional room / space</option>
            {#each filteredSpacesFor(documentForm.facility) as space}
              <option value={String(space.id)}>{space.facility_code} • {space.space_label || space.unit_number} • {space.zone_code}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Asset</span>
          <select bind:value={documentForm.asset_component} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Optional asset linkage</option>
            {#each filteredAssetsFor(documentForm.facility) as asset}
              <option value={String(asset.id)}>{asset.component_id} - {asset.label}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700 md:col-span-2">
          <span class="mb-1.5 block">Title</span>
          <input bind:value={documentForm.title} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Main mechanical room blueprint revision A3" />
        </label>

        <label class="text-sm font-medium text-neutral-700 md:col-span-2">
          <span class="mb-1.5 block">Description</span>
          <textarea bind:value={documentForm.description} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Capture what the document covers, intended audience, and revision scope."></textarea>
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Version</span>
          <input bind:value={documentForm.version_label} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="v2.1 / Rev-A" />
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Reference Number</span>
          <input bind:value={documentForm.reference_number} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="DOC-PLN-401" />
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Issued Date</span>
          <input bind:value={documentForm.issued_date} type="date" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Review Due Date</span>
          <input bind:value={documentForm.review_due_date} type="date" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Expiry Date</span>
          <input bind:value={documentForm.expiry_date} type="date" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Upload File</span>
          <input type="file" onchange={handleFileChange} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm file:mr-3 file:rounded-md file:border-0 file:bg-neutral-900 file:px-3 file:py-2 file:text-sm file:font-medium file:text-white" />
          <span class="mt-1 block text-xs text-neutral-500">{selectedFile?.name || "No file selected"}</span>
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Linked Work Order</span>
          <select bind:value={documentForm.linked_work_order} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Optional work order linkage</option>
            {#each filteredWorkOrdersFor(documentForm.facility) as workOrder}
              <option value={String(workOrder.id)}>WO-{workOrder.id} • {workOrder.title}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700 md:col-span-2">
          <span class="mb-1.5 block">Linked Inspection</span>
          <select bind:value={documentForm.linked_inspection} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Optional inspection linkage</option>
            {#each filteredInspectionsFor(documentForm.facility) as inspection}
              <option value={String(inspection.id)}>{inspection.title} • {fmtDate(inspection.scheduled_date)}</option>
            {/each}
          </select>
        </label>

        {#if documentForm.document_type === "maintenance_log"}
          <label class="text-sm font-medium text-neutral-700 md:col-span-2">
            <span class="mb-1.5 block">Maintenance Summary</span>
            <textarea bind:value={documentForm.generated_summary} rows="5" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Add summary notes if you are recording a maintenance log without uploading a file."></textarea>
          </label>
        {/if}

        <label class="text-sm font-medium text-neutral-700 md:col-span-2">
          <span class="mb-1.5 block">Notes</span>
          <textarea bind:value={documentForm.notes} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Access restrictions, issuance details, retention notes, or revision comments."></textarea>
        </label>
      </form>
    </div>

    <div class="flex items-center justify-end gap-3 border-t border-neutral-100 px-6 py-4">
      {#if isDev}
        <button type="button" onclick={devFillDocForm} class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>
      {/if}
      <button
        type="button"
        onclick={closeDocumentDrawer}
        class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-600 transition hover:border-neutral-300 hover:text-neutral-900"
      >
        Cancel
      </button>
      <button
        type="submit"
        form="facility-document-form"
        disabled={saving}
        class="inline-flex items-center justify-center rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {saving ? "Saving..." : "Save Document"}
      </button>
    </div>
  </aside>
{/if}

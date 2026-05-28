<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import Modal from "$lib/components/Modal.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    CustomerListItem,
    Department,
    DivisionListItem,
    DocumentExpiryTriggerCategory,
    DocumentOwnerRoleOption,
    DocumentRecord,
    DocumentRetentionPolicyOption,
    DocumentTypeOption,
    DocumentVersionRecord,
    DocumentWorkflowPhaseOption,
    PaginatedResponse,
    ProjectListItem,
    PropertyListItem,
    Unit,
    VendorListItem,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  let {
    open = false,
    onclose,
    oncreated,
    initialProjectId = null,
    lockProject = false,
  }: {
    open: boolean;
    onclose: () => void;
    oncreated?: (documentId: number) => void;
    initialProjectId?: number | null;
    lockProject?: boolean;
  } = $props();

  type CreateForm = {
    title: string;
    project_code: string;
    document_type: string;
    confidentiality_level: "public" | "internal" | "confidential" | "restricted";
    owner_role: string;
    phase: string;
    retention_policy: string;
    contract_value: string | number;
    project: string;
    land: string;
    unit: string;
    client: string;
    vendor: string;
    business_unit_division: string;
    business_unit_department: string;
    version_major: string;
    version_minor: string;
    change_summary: string;
    file: File | null;
    track_expiry: boolean;
    trigger_category: DocumentExpiryTriggerCategory;
    expiry_date: string;
    alert_90_days: boolean;
    alert_30_days: boolean;
    alert_expired: boolean;
    submit_for_workflow: boolean;
  };

  const initialForm: CreateForm = {
    title: "",
    project_code: "",
    document_type: "",
    confidentiality_level: "internal",
    owner_role: "",
    phase: "",
    retention_policy: "",
    contract_value: "",
    project: "",
    land: "",
    unit: "",
    client: "",
    vendor: "",
    business_unit_division: "",
    business_unit_department: "",
    version_major: "1",
    version_minor: "0",
    change_summary: "",
    file: null,
    track_expiry: false,
    trigger_category: "building_permit",
    expiry_date: "",
    alert_90_days: true,
    alert_30_days: true,
    alert_expired: true,
    submit_for_workflow: true,
  };

  const confidentialityOptions = [
    { value: "public", label: "Public" },
    { value: "internal", label: "Internal" },
    { value: "confidential", label: "Confidential" },
    { value: "restricted", label: "Restricted" },
  ] as const;

  const expiryTriggerOptions: Array<{ value: DocumentExpiryTriggerCategory; label: string }> = [
    { value: "building_permit", label: "Building Permit" },
    { value: "insurance", label: "Insurance" },
    { value: "performance_bond", label: "Performance Bond" },
    { value: "eia_renewal", label: "EIA Renewal" },
    { value: "warranty_end", label: "Warranty End" },
  ];

  function defaultProjectSelection(): string {
    if (typeof initialProjectId === "number" && Number.isInteger(initialProjectId) && initialProjectId > 0) {
      return String(initialProjectId);
    }
    return "";
  }

  let form = $state<CreateForm>({ ...initialForm, project: defaultProjectSelection() });
  let formErrors = $state<Record<string, string[]>>({});
  let submitting = $state(false);
  let loadingLookups = $state(false);
  let lookupError = $state("");

  let documentTypes = $state<DocumentTypeOption[]>([]);
  let ownerRoles = $state<DocumentOwnerRoleOption[]>([]);
  let workflowPhases = $state<DocumentWorkflowPhaseOption[]>([]);
  let retentionPolicies = $state<DocumentRetentionPolicyOption[]>([]);
  let projects = $state<ProjectListItem[]>([]);
  let properties = $state<PropertyListItem[]>([]);
  let units = $state<Unit[]>([]);
  let vendors = $state<VendorListItem[]>([]);
  let clients = $state<CustomerListItem[]>([]);
  let divisions = $state<DivisionListItem[]>([]);
  let departments = $state<Department[]>([]);

  let loadedLookups = $state(false);
  let lastDivisionLoaded = $state<number | null>(null);
  let lastLandLoaded = $state<number | null>(null);

  const propertyNameById = $derived.by(() => {
    const map = new Map<number, string>();
    for (const property of properties) {
      map.set(property.id, property.name);
    }
    return map;
  });

  const selectedDocumentType = $derived(
    documentTypes.find((item) => String(item.id) === form.document_type) ?? null,
  );

  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  function devFill() {
    const today = new Date();
    const plusDays = (d: Date, n: number) => { const r = new Date(d); r.setDate(r.getDate() + n); return r; };
    const fmt = (d: Date) => d.toISOString().slice(0, 10);

    form.title = "EIA Compliance Certificate - Phase 1";
    form.project_code = "LUA";
    form.confidentiality_level = "confidential";
    form.contract_value = "2500000";
    form.version_major = "1";
    form.version_minor = "0";
    form.change_summary = "Initial submission for regulatory review and approval.";
    form.submit_for_workflow = true;
    form.track_expiry = true;
    form.trigger_category = "eia_renewal";
    form.expiry_date = fmt(plusDays(today, 365));
    form.alert_90_days = true;
    form.alert_30_days = true;
    form.alert_expired = true;

    if (documentTypes.length > 0) form.document_type = String(documentTypes[0].id);
    if (ownerRoles.length > 0) form.owner_role = String(ownerRoles[0].id);
    if (workflowPhases.length > 0) form.phase = String(workflowPhases[0].id);
    if (retentionPolicies.length > 0) form.retention_policy = String(retentionPolicies[0].id);
    if (properties.length > 0) form.land = String(properties[0].id);
  }

  function resetForm() {
    form = { ...initialForm, project: defaultProjectSelection() };
    formErrors = {};
    lookupError = "";
    departments = [];
    lastDivisionLoaded = null;
  }

  function closeModal() {
    if (submitting) return;
    resetForm();
    onclose();
  }

  function fieldError(field: string): string {
    return formErrors[field]?.[0] ?? "";
  }

  function parseNumberOrNull(value: string): number | null {
    if (!value) return null;
    const parsed = Number.parseInt(value, 10);
    if (Number.isNaN(parsed)) return null;
    return parsed;
  }

  function parseDecimalOrZero(value: string | number | null | undefined): string {
    if (typeof value === "number") {
      if (!Number.isFinite(value)) return "0.00";
      return String(value);
    }
    const normalized = String(value ?? "").trim();
    if (!normalized) return "0.00";
    return normalized;
  }

  function setLocalValidationErrors(): boolean {
    const errors: Record<string, string[]> = {};

    if (!form.title.trim()) errors.title = ["Title is required."];
    if (!form.document_type) errors.document_type = ["Document type is required."];
    if (!form.owner_role) errors.owner_role = ["Owner role is required."];
    if (!form.phase) errors.phase = ["Workflow phase is required."];
    if (!form.retention_policy) errors.retention_policy = ["Retention policy is required."];
    if (!form.file) errors.file = ["Please upload a document file."];
    if (lockProject && !form.project) errors.project = ["Project context is required."];

    const major = Number.parseInt(form.version_major, 10);
    if (Number.isNaN(major) || major < 1) {
      errors.version_major = ["Version major must be at least 1."];
    }

    const minor = Number.parseInt(form.version_minor, 10);
    if (Number.isNaN(minor) || minor < 0) {
      errors.version_minor = ["Version minor cannot be negative."];
    }

    if (form.track_expiry && !form.expiry_date) {
      errors.expiry_date = ["Expiry date is required when compliance tracking is enabled."];
    }

    if (Object.keys(errors).length > 0) {
      formErrors = errors;
      return false;
    }
    return true;
  }

  async function fetchAllPages<T>(
    endpoint: string,
    params: Record<string, string> = {},
    maxPages = 50,
  ): Promise<T[]> {
    const results: T[] = [];
    let page = 1;

    while (page <= maxPages) {
      const response = await api.get<PaginatedResponse<T> | T[]>(endpoint, {
        ...params,
        page: String(page),
      });

      if (Array.isArray(response)) {
        results.push(...response);
        break;
      }

      const pageResults = Array.isArray(response.results) ? response.results : [];
      results.push(...pageResults);
      if (!response.next || pageResults.length === 0) break;
      page += 1;
    }

    return results;
  }

  async function fetchOptionalLookup<T>(
    endpoint: string,
    params: Record<string, string> = {},
  ): Promise<T[]> {
    try {
      return await fetchAllPages<T>(endpoint, params);
    } catch {
      return [];
    }
  }

  async function loadDepartments(divisionId: number) {
    try {
      const list = await fetchAllPages<Department>(`/settings/divisions/${divisionId}/departments/`, {
        page_size: "200",
      });
      departments = list;
      const hasCurrent = list.some((item) => String(item.id) === form.business_unit_department);
      if (!hasCurrent) {
        form.business_unit_department = "";
      }
    } catch {
      departments = [];
      form.business_unit_department = "";
    }
  }

  async function loadLookups() {
    if (loadedLookups || loadingLookups) return;

    loadingLookups = true;
    lookupError = "";

    try {
      const [
        fetchedDocumentTypes,
        fetchedOwnerRoles,
        fetchedWorkflowPhases,
        fetchedRetentionPolicies,
      ] = await Promise.all([
        fetchAllPages<DocumentTypeOption>("/documents/control/lookups/document-types/", {
          is_active: "true",
          ordering: "name",
          page_size: "200",
        }),
        fetchAllPages<DocumentOwnerRoleOption>("/documents/control/lookups/owner-roles/", {
          is_active: "true",
          ordering: "name",
          page_size: "200",
        }),
        fetchAllPages<DocumentWorkflowPhaseOption>("/documents/control/lookups/workflow-phases/", {
          is_active: "true",
          ordering: "sort_order",
          page_size: "200",
        }),
        fetchAllPages<DocumentRetentionPolicyOption>("/documents/control/lookups/retention-policies/", {
          is_active: "true",
          ordering: "name",
          page_size: "200",
        }),
      ]);

      documentTypes = fetchedDocumentTypes;
      ownerRoles = fetchedOwnerRoles;
      workflowPhases = fetchedWorkflowPhases;
      retentionPolicies = fetchedRetentionPolicies;

      const [
        fetchedProjects,
        fetchedProperties,
        fetchedVendors,
        fetchedClients,
        fetchedDivisions,
      ] = await Promise.all([
        fetchOptionalLookup<ProjectListItem>("/projects/", {
          ordering: "name",
          page_size: "200",
        }),
        fetchOptionalLookup<PropertyListItem>("/properties/", {
          ordering: "name",
          page_size: "200",
        }),
        fetchOptionalLookup<VendorListItem>("/procurement/vendors/", {
          ordering: "name",
          page_size: "200",
        }),
        fetchOptionalLookup<CustomerListItem>("/finance/customers/", {
          ordering: "name",
          page_size: "200",
        }),
        fetchOptionalLookup<DivisionListItem>("/settings/divisions/", {
          ordering: "name",
          page_size: "200",
        }),
      ]);

      projects = fetchedProjects;
      properties = fetchedProperties;
      vendors = fetchedVendors;
      clients = fetchedClients;
      divisions = fetchedDivisions;

      if (
        fetchedDocumentTypes.length === 0
        || fetchedOwnerRoles.length === 0
        || fetchedWorkflowPhases.length === 0
        || fetchedRetentionPolicies.length === 0
      ) {
        lookupError = "Document setup is incomplete. Seed document types, owner roles, workflow phases, and retention policies.";
        loadedLookups = false;
        return;
      }

      loadedLookups = true;
    } catch (error) {
      if (error instanceof ApiError) {
        const detail = error.data?.detail;
        if (error.status === 401) {
          lookupError = "Your session expired. Please sign in again.";
        } else if (error.status === 403) {
          lookupError = "You do not have permission to load document setup options.";
        } else if (typeof detail === "string" && detail.trim()) {
          lookupError = detail;
        } else {
          lookupError = "Could not load required document setup options. Check access/seed data and retry.";
        }
      } else {
        lookupError = "Could not load required document setup options. Check access/seed data and retry.";
      }
    } finally {
      loadingLookups = false;
    }
  }

  async function loadUnitsForLand(landId: number) {
    let loadedUnits: Unit[] = [];

    // Preferred: nested property units endpoint.
    try {
      loadedUnits = await fetchAllPages<Unit>(`/properties/${landId}/units/`, {
        ordering: "unit_number",
        page_size: "200",
      });
    } catch {
      // Fallback: flat units endpoint if available.
      loadedUnits = await fetchOptionalLookup<Unit>("/properties/units/", {
        property: String(landId),
        ordering: "unit_number",
        page_size: "200",
      });
    }

    units = loadedUnits;
    const hasSelectedUnit = loadedUnits.some((item) => String(item.id) === form.unit);
    if (!hasSelectedUnit) {
      form.unit = "";
    }
  }

  function onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    form.file = input.files?.[0] ?? null;
  }

  function parseApiErrorMessage(error: ApiError): string {
    if (error.status >= 500) {
      return "A server error occurred. Please try again or contact support if the problem persists.";
    }
    const detail = error.data?.detail;
    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }
    const nonFieldError = error.fieldErrors.non_field_errors?.[0];
    if (nonFieldError) {
      return nonFieldError;
    }
    const fieldNames = Object.keys(error.fieldErrors);
    if (fieldNames.length > 0) {
      const first = fieldNames[0];
      const label = first.replace(/_/g, " ");
      return `${label}: ${error.fieldErrors[first][0]}`;
    }
    if (error.status === 403) {
      return "You do not have permission to perform this action.";
    }
    return "An unexpected error occurred. Please try again.";
  }

  async function handleSubmit(event: Event) {
    event.preventDefault();
    if (!setLocalValidationErrors()) {
      toast.error("Validation error", "Please complete required fields before continuing.");
      return;
    }

    submitting = true;
    formErrors = {};

    const documentPayload: Record<string, unknown> = {
      title: form.title.trim(),
      project_code: form.project_code.trim(),
      document_type: parseNumberOrNull(form.document_type),
      confidentiality_level: form.confidentiality_level,
      owner_role: parseNumberOrNull(form.owner_role),
      phase: parseNumberOrNull(form.phase),
      retention_policy: parseNumberOrNull(form.retention_policy),
      contract_value: parseDecimalOrZero(form.contract_value),
      business_unit_division: parseNumberOrNull(form.business_unit_division),
      business_unit_department: parseNumberOrNull(form.business_unit_department),
      project: parseNumberOrNull(form.project),
      land: parseNumberOrNull(form.land),
      unit: parseNumberOrNull(form.unit),
      client: parseNumberOrNull(form.client),
      vendor: parseNumberOrNull(form.vendor),
    };

    let createdDocument: DocumentRecord;
    try {
      createdDocument = await api.post<DocumentRecord>("/documents/control/records/", documentPayload);
    } catch (error) {
      if (error instanceof ApiError) {
        formErrors = error.fieldErrors;
        toast.error("Could not add document", parseApiErrorMessage(error));
      } else {
        toast.error("Could not add document", "An unexpected error occurred while saving the document.");
      }
      submitting = false;
      return;
    }

    const versionPayload = new FormData();
    versionPayload.append("version_major", form.version_major);
    versionPayload.append("version_minor", form.version_minor);
    versionPayload.append("change_summary", form.change_summary.trim());
    if (form.file) {
      versionPayload.append("file", form.file);
    }

    try {
      await api.upload<DocumentVersionRecord>(
        `/documents/control/records/${createdDocument.id}/upload-version/`,
        versionPayload,
      );
    } catch (error) {
      const message = error instanceof ApiError
        ? parseApiErrorMessage(error)
        : "File upload failed after creating the document.";
      toast.error(
        "Document created, file upload failed",
        `${createdDocument.document_number} was created but initial version upload failed. ${message}`,
      );
      submitting = false;
      oncreated?.(createdDocument.id);
      closeModal();
      return;
    }

    let complianceMessage: string | null = null;
    if (form.track_expiry) {
      try {
        await api.post("/documents/control/expiries/", {
          document: createdDocument.id,
          trigger_category: form.trigger_category,
          expiry_date: form.expiry_date,
          alert_90_days: form.alert_90_days,
          alert_30_days: form.alert_30_days,
          alert_expired: form.alert_expired,
        });
      } catch (error) {
        complianceMessage = error instanceof ApiError
          ? parseApiErrorMessage(error)
          : "Compliance tracking could not be configured.";
      }
    }

    let workflowMessage: string | null = null;
    if (form.submit_for_workflow) {
      try {
        await api.post(`/documents/control/records/${createdDocument.id}/submit-workflow/`, {});
      } catch (error) {
        if (error instanceof ApiError) {
          workflowMessage = parseApiErrorMessage(error);
        } else {
          workflowMessage = "Document was created but workflow submission did not complete.";
        }
      }
    }

    toast.success("Document added", `${createdDocument.document_number} has been added to the repository.`);
    if (complianceMessage) {
      toast.warning("Compliance setup pending", complianceMessage);
    }
    if (workflowMessage) {
      toast.warning("Workflow submission pending", workflowMessage);
    }

    submitting = false;
    oncreated?.(createdDocument.id);
    closeModal();
  }

  $effect(() => {
    if (!open) {
      return;
    }
    const defaultProject = defaultProjectSelection();
    if (defaultProject && (lockProject || !form.project)) {
      form.project = defaultProject;
    }
    void loadLookups();
  });

  $effect(() => {
    if (!open) return;

    const divisionId = parseNumberOrNull(form.business_unit_division);
    if (!divisionId) {
      departments = [];
      form.business_unit_department = "";
      lastDivisionLoaded = null;
      return;
    }

    if (lastDivisionLoaded === divisionId) return;
    lastDivisionLoaded = divisionId;
    void loadDepartments(divisionId);
  });

  $effect(() => {
    if (!open) return;

    const landId = parseNumberOrNull(form.land);
    if (!landId) {
      units = [];
      form.unit = "";
      lastLandLoaded = null;
      return;
    }

    if (lastLandLoaded === landId) return;
    lastLandLoaded = landId;
    void loadUnitsForLand(landId);
  });
</script>

<Modal open={open} onclose={closeModal} title="Add Document" maxWidth="max-w-5xl">
  {#if loadingLookups}
    <div class="flex items-center justify-center py-14">
      <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
    </div>
  {:else}
    <form onsubmit={handleSubmit} class="space-y-6">
      {#if isDev}
        <div class="flex justify-end">
          <button
            type="button"
            onclick={devFill}
            class="px-3 py-1.5 text-xs font-mono font-medium text-orange-700 bg-orange-50 border border-orange-200 rounded-lg hover:bg-orange-100 transition-colors"
          >
            Dev: Autofill
          </button>
        </div>
      {/if}
      {#if lookupError}
        <div class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {lookupError}
        </div>
      {/if}
      {#if fieldError("non_field_errors")}
        <div class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {fieldError("non_field_errors")}
        </div>
      {/if}

      <div class="rounded-xl border border-neutral-200">
        <div class="border-b border-neutral-200 px-4 py-3">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Taxonomy & Metadata</h3>
          <p class="mt-1 text-xs text-neutral-500">Select classification and ownership so numbering, routing, and governance rules apply automatically.</p>
        </div>
        <div class="grid gap-4 p-4 md:grid-cols-2">
          <label>
            <span class="mb-1.5 block text-sm font-medium text-neutral-700">Title</span>
            <input
              type="text"
              bind:value={form.title}
              class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
              placeholder="Document title"
            />
            {#if fieldError("title")}<p class="mt-1 text-xs text-red-500">{fieldError("title")}</p>{/if}
          </label>

          <label>
            <span class="mb-1.5 block text-sm font-medium text-neutral-700">Project Code (optional)</span>
            <input
              type="text"
              bind:value={form.project_code}
              maxlength="10"
              class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
              placeholder="e.g. LUA"
            />
          </label>

          <label>
            <span class="mb-1.5 block text-sm font-medium text-neutral-700">Document Type</span>
            <select
              bind:value={form.document_type}
              class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
            >
              <option value="">Select document type</option>
              {#each documentTypes as item}
                <option value={String(item.id)}>{item.name} ({item.category_code})</option>
              {/each}
            </select>
            {#if selectedDocumentType}
              <p class="mt-1 text-xs text-neutral-500">Category: {selectedDocumentType.category_code}</p>
            {/if}
            {#if fieldError("document_type")}<p class="mt-1 text-xs text-red-500">{fieldError("document_type")}</p>{/if}
          </label>

          <label>
            <span class="mb-1.5 block text-sm font-medium text-neutral-700">Confidentiality</span>
            <select
              bind:value={form.confidentiality_level}
              class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
            >
              {#each confidentialityOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </label>

          <label>
            <span class="mb-1.5 block text-sm font-medium text-neutral-700">Owner Role</span>
            <select
              bind:value={form.owner_role}
              class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
            >
              <option value="">Select owner role</option>
              {#each ownerRoles as role}
                <option value={String(role.id)}>{role.name}</option>
              {/each}
            </select>
            {#if fieldError("owner_role")}<p class="mt-1 text-xs text-red-500">{fieldError("owner_role")}</p>{/if}
          </label>

          <label>
            <span class="mb-1.5 block text-sm font-medium text-neutral-700">Workflow Phase</span>
            <select
              bind:value={form.phase}
              class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
            >
              <option value="">Select workflow phase</option>
              {#each workflowPhases as phase}
                <option value={String(phase.id)}>{phase.name} ({phase.numbering_code})</option>
              {/each}
            </select>
            {#if fieldError("phase")}<p class="mt-1 text-xs text-red-500">{fieldError("phase")}</p>{/if}
          </label>

          <label>
            <span class="mb-1.5 block text-sm font-medium text-neutral-700">Retention Policy</span>
            <select
              bind:value={form.retention_policy}
              class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
            >
              <option value="">Select retention policy</option>
              {#each retentionPolicies as policy}
                <option value={String(policy.id)}>{policy.name}</option>
              {/each}
            </select>
            {#if fieldError("retention_policy")}<p class="mt-1 text-xs text-red-500">{fieldError("retention_policy")}</p>{/if}
          </label>

          <label>
            <span class="mb-1.5 block text-sm font-medium text-neutral-700">Contract Value (optional)</span>
            <input
              type="number"
              step="0.01"
              min="0"
              bind:value={form.contract_value}
              class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
              placeholder="0.00"
            />
          </label>
        </div>
        <div class="border-t border-neutral-200 px-4 py-3 text-xs text-neutral-500">
          Document number is generated automatically using project-phase-category-revision rules.
        </div>
      </div>

      <div class="rounded-xl border border-neutral-200">
        <div class="border-b border-neutral-200 px-4 py-3">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Linked Entities</h3>
          <p class="mt-1 text-xs text-neutral-500">Connect the document to operational context for search, permissions, and audit traceability.</p>
        </div>
        <div class="grid gap-4 p-4 md:grid-cols-2">
          <label>
            <span class="mb-1.5 block text-sm font-medium text-neutral-700">Project (optional)</span>
            <select
              bind:value={form.project}
              disabled={lockProject}
              class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900 disabled:cursor-not-allowed disabled:bg-neutral-50"
            >
              <option value="">None</option>
              {#each projects as project}
                <option value={String(project.id)}>{project.name}</option>
              {/each}
            </select>
            {#if lockProject}
              <p class="mt-1 text-xs text-neutral-500">Project is locked to the current context.</p>
            {/if}
            {#if fieldError("project")}<p class="mt-1 text-xs text-red-500">{fieldError("project")}</p>{/if}
          </label>

          <label>
            <span class="mb-1.5 block text-sm font-medium text-neutral-700">Land/Property (optional)</span>
            <select
              bind:value={form.land}
              class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
            >
              <option value="">None</option>
              {#each properties as property}
                <option value={String(property.id)}>{property.name}</option>
              {/each}
            </select>
          </label>

          <label>
            <span class="mb-1.5 block text-sm font-medium text-neutral-700">Unit (optional)</span>
            <select
              bind:value={form.unit}
              disabled={!form.land}
              class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900 disabled:cursor-not-allowed disabled:bg-neutral-50"
            >
              <option value="">{form.land ? "None" : "Select land/property first"}</option>
              {#each units as unit}
                <option value={String(unit.id)}>
                  {unit.unit_number}
                  {#if propertyNameById.get(unit.property)}
                    - {propertyNameById.get(unit.property)}
                  {/if}
                </option>
              {/each}
            </select>
          </label>

          <label>
            <span class="mb-1.5 block text-sm font-medium text-neutral-700">Vendor (optional)</span>
            <select
              bind:value={form.vendor}
              class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
            >
              <option value="">None</option>
              {#each vendors as vendor}
                <option value={String(vendor.id)}>{vendor.name}</option>
              {/each}
            </select>
          </label>

          <label>
            <span class="mb-1.5 block text-sm font-medium text-neutral-700">Client (optional)</span>
            <select
              bind:value={form.client}
              class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
            >
              <option value="">None</option>
              {#each clients as client}
                <option value={String(client.id)}>{client.name}</option>
              {/each}
            </select>
          </label>

          <label>
            <span class="mb-1.5 block text-sm font-medium text-neutral-700">Business Unit Division (optional)</span>
            <select
              bind:value={form.business_unit_division}
              class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
            >
              <option value="">None</option>
              {#each divisions as division}
                <option value={String(division.id)}>{division.name}</option>
              {/each}
            </select>
          </label>

          <label>
            <span class="mb-1.5 block text-sm font-medium text-neutral-700">Business Unit Department (optional)</span>
            <select
              bind:value={form.business_unit_department}
              disabled={!form.business_unit_division}
              class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900 disabled:cursor-not-allowed disabled:bg-neutral-50"
            >
              <option value="">None</option>
              {#each departments as department}
                <option value={String(department.id)}>{department.name}</option>
              {/each}
            </select>
          </label>
        </div>
      </div>

      <div class="rounded-xl border border-neutral-200">
        <div class="border-b border-neutral-200 px-4 py-3">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Version Upload</h3>
          <p class="mt-1 text-xs text-neutral-500">Upload the controlled file and define revision metadata.</p>
        </div>
        <div class="grid gap-4 p-4 md:grid-cols-2">
          <label class="md:col-span-2">
            <span class="mb-1.5 block text-sm font-medium text-neutral-700">File</span>
            <input
              type="file"
              onchange={onFileSelected}
              class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm file:mr-3 file:rounded-md file:border-0 file:bg-neutral-900 file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-white"
            />
            {#if form.file}
              <p class="mt-1 text-xs text-neutral-500">Selected: {form.file.name}</p>
            {/if}
            {#if fieldError("file")}
              <p class="mt-1 text-xs text-red-500">{fieldError("file")}</p>
            {:else if fieldError("file_path")}
              <p class="mt-1 text-xs text-red-500">{fieldError("file_path")}</p>
            {/if}
          </label>

          <label>
            <span class="mb-1.5 block text-sm font-medium text-neutral-700">Version Major</span>
            <input
              type="number"
              min="1"
              bind:value={form.version_major}
              class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
            />
            {#if fieldError("version_major")}<p class="mt-1 text-xs text-red-500">{fieldError("version_major")}</p>{/if}
          </label>

          <label>
            <span class="mb-1.5 block text-sm font-medium text-neutral-700">Version Minor</span>
            <input
              type="number"
              min="0"
              bind:value={form.version_minor}
              class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
            />
            {#if fieldError("version_minor")}<p class="mt-1 text-xs text-red-500">{fieldError("version_minor")}</p>{/if}
          </label>

          <label class="md:col-span-2">
            <span class="mb-1.5 block text-sm font-medium text-neutral-700">Change Summary (optional)</span>
            <textarea
              rows="3"
              bind:value={form.change_summary}
              class="w-full resize-none rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
              placeholder="Describe what changed in this revision"
            ></textarea>
            {#if fieldError("change_summary")}<p class="mt-1 text-xs text-red-500">{fieldError("change_summary")}</p>{/if}
          </label>
        </div>
      </div>

      <div class="rounded-xl border border-neutral-200">
        <div class="border-b border-neutral-200 px-4 py-3">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Approval Workflow</h3>
          <p class="mt-1 text-xs text-neutral-500">Automatically submit this document into the configured approval route after upload.</p>
        </div>
        <div class="p-4">
          <label class="inline-flex items-center gap-2 text-sm text-neutral-700">
            <input type="checkbox" bind:checked={form.submit_for_workflow} class="h-4 w-4 rounded border-neutral-300" />
            Submit for approval workflow after upload
          </label>
        </div>
      </div>

      <div class="rounded-xl border border-neutral-200">
        <div class="border-b border-neutral-200 px-4 py-3">
          <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Compliance & Expiry</h3>
          <p class="mt-1 text-xs text-neutral-500">Enable expiry monitoring for permits, insurance, bonds, EIA, or warranties.</p>
        </div>
        <div class="space-y-4 p-4">
          <label class="inline-flex items-center gap-2 text-sm text-neutral-700">
            <input type="checkbox" bind:checked={form.track_expiry} class="h-4 w-4 rounded border-neutral-300" />
            Track expiry/compliance alerts for this document
          </label>

          {#if form.track_expiry}
            <div class="grid gap-4 md:grid-cols-2">
              <label>
                <span class="mb-1.5 block text-sm font-medium text-neutral-700">Trigger Category</span>
                <select
                  bind:value={form.trigger_category}
                  class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
                >
                  {#each expiryTriggerOptions as option}
                    <option value={option.value}>{option.label}</option>
                  {/each}
                </select>
              </label>

              <label>
                <span class="mb-1.5 block text-sm font-medium text-neutral-700">Expiry Date</span>
                <DateInput bind:value={form.expiry_date} />
                {#if fieldError("expiry_date")}<p class="mt-1 text-xs text-red-500">{fieldError("expiry_date")}</p>{/if}
              </label>
            </div>

            <div class="flex flex-wrap gap-4 text-sm text-neutral-700">
              <label class="inline-flex items-center gap-2">
                <input type="checkbox" bind:checked={form.alert_90_days} class="h-4 w-4 rounded border-neutral-300" />
                90-day alert
              </label>
              <label class="inline-flex items-center gap-2">
                <input type="checkbox" bind:checked={form.alert_30_days} class="h-4 w-4 rounded border-neutral-300" />
                30-day alert
              </label>
              <label class="inline-flex items-center gap-2">
                <input type="checkbox" bind:checked={form.alert_expired} class="h-4 w-4 rounded border-neutral-300" />
                Expired alert + escalation
              </label>
            </div>
          {/if}
        </div>
      </div>

      <div class="flex justify-end gap-3 border-t border-neutral-100 pt-2">
        <button
          type="button"
          onclick={closeModal}
          class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={submitting || loadingLookups || !!lookupError}
          class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting ? "Saving..." : "Add Document"}
        </button>
      </div>
    </form>
  {/if}
</Modal>

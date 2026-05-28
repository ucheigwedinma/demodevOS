<script lang="ts">
  import { ApiError, api } from "$lib/api";
  import DateInput from "$lib/components/DateInput.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import type { PaginatedResponse } from "$lib/types";

  type TenantType = "individual" | "corporate";
  type TenantStatus = "pending_move_in" | "active" | "moved_out" | "inactive";
  type RegistryPaymentStatus = "debt_free" | "delinquent" | "unknown";
  type RegistryQuickFilter = "all" | "active" | "past" | "prospective";
  type RegistryExportFormat = "csv" | "xlsx";

  interface TenantRegistryOverview {
    generated_at: string;
    totals: {
      profiles: number;
      active: number;
      pending_move_in: number;
      moved_out: number;
      inactive: number;
    };
    hygiene: {
      missing_customer_links: number;
      missing_contact_channels: number;
      missing_location_mapping: number;
    };
    allocation: {
      assigned_units: number;
      assigned_spaces: number;
      unassigned_profiles: number;
    };
    lease_watch: {
      expiring_next_60_days: number;
      move_ins_next_30_days: number;
      recent_move_outs: number;
    };
    tenant_types: Array<{
      key: TenantType;
      label: string;
      count: number;
    }>;
  }

  interface CustomerLookup {
    id: number;
    name: string;
    email: string;
    phone: string;
  }

  interface ContactAccountLookup {
    id: number;
    name: string;
    email: string;
    phone: string;
    finance_customer_id: number | null;
  }

  interface UserLookup {
    id: number;
    name: string;
    email: string;
  }

  interface PropertyLookup {
    id: number;
    name: string;
    location: string;
    address: string;
  }

  interface FacilityLookup {
    id: number;
    property_id: number;
    property_name: string;
    facility_code: string;
    label: string;
  }

  interface UnitLookup {
    id: number;
    property_id: number;
    property_name: string;
    unit_number: string;
    location_description: string;
    status: string;
    status_display: string;
    label: string;
  }

  interface SpaceLookup {
    id: number;
    facility_id: number;
    facility_code: string;
    property_id: number;
    property_name: string;
    unit_id: number;
    unit_number: string;
    space_label: string;
    label: string;
  }

  interface TenantRegistryLookups {
    generated_at: string;
    customers: CustomerLookup[];
    contact_accounts: ContactAccountLookup[];
    users: UserLookup[];
    properties: PropertyLookup[];
    facilities: FacilityLookup[];
    units: UnitLookup[];
    spaces: SpaceLookup[];
  }

  interface TenantRegistryRow {
    id: number;
    customer: number | null;
    customer_name: string;
    contact_account: number | null;
    contact_account_name: string;
    primary_user: number | null;
    primary_user_name: string;
    property: number | null;
    property_name: string;
    property_location: string;
    unit: number | null;
    unit_number: string;
    facility: number | null;
    facility_code: string;
    facility_space: number | null;
    space_label: string;
    tenant_type: TenantType;
    tenant_type_display: string;
    status: TenantStatus;
    status_display: string;
    display_name: string;
    resolved_display_name: string;
    contact_email: string;
    contact_phone: string;
    payment_status: RegistryPaymentStatus;
    payment_status_display: string;
    lease_start_date: string | null;
    lease_end_date: string | null;
    move_in_date: string | null;
    move_out_date: string | null;
    occupant_count: number;
    notes: string;
    created_at: string;
    updated_at: string;
  }

  interface TenantRegistryFormState {
    customer: string;
    contact_account: string;
    primary_user: string;
    property: string;
    unit: string;
    facility: string;
    facility_space: string;
    tenant_type: TenantType;
    status: TenantStatus;
    display_name: string;
    lease_start_date: string;
    lease_end_date: string;
    move_in_date: string;
    move_out_date: string;
    occupant_count: string;
    notes: string;
  }

  interface RegistrySearchSuggestion {
    id: string;
    kind: "tenant" | "phone" | "unit" | "site";
    label: string;
    helper: string;
    value: string;
  }

  interface TenantRegistryImportResult {
    detail: string;
    source_format: string;
    created_count: number;
    created_profiles: Array<{ id: number; display_name: string }>;
    failed_rows: Array<{
      row: number;
      display_name: string;
      errors: Record<string, string[] | string>;
    }>;
  }

  interface RegistryOnboardingStage {
    key: "applicant" | "due_diligence" | "allocation" | "lease_setup" | "registered";
    label: string;
    description: string;
    count: number;
    className: string;
    stepClass: string;
  }

  type RegistryProfileTab = "identity" | "financial" | "inventory" | "incidents";
  type RegistryProfileDrawerMode = "identity" | "contact" | "inventory" | "incident";
  type IdentityDocumentType =
    | "nin"
    | "passport"
    | "drivers_license"
    | "national_id"
    | "rc_certificate"
    | "tax_id"
    | "other";
  type RelationshipContactRole = "next_of_kin" | "emergency";
  type InventoryCondition = "new" | "good" | "fair" | "poor";
  type InventoryItemStatus = "provided" | "returned" | "missing" | "damaged";
  type IncidentType =
    | "lease_violation"
    | "maintenance_issue"
    | "damage"
    | "noise"
    | "security"
    | "payment_breach"
    | "other";
  type IncidentSeverity = "low" | "medium" | "high" | "critical" | "urgent";
  type IncidentStatus =
    | "open"
    | "under_review"
    | "resolved"
    | "closed"
    | "assigned"
    | "in_progress"
    | "on_hold"
    | "completed"
    | "verified"
    | "cancelled"
    | TenantStatus;
  type IncidentEntryType = "incident" | "work_order";

  interface TenantIdentityDocumentRecord {
    id: number;
    document_type: IdentityDocumentType;
    document_type_display: string;
    document_number: string;
    holder_name: string;
    issuing_country: string;
    issue_date: string | null;
    expiry_date: string | null;
    scan_on_file: boolean;
    scan_reference: string;
    is_verified: boolean;
    notes: string;
    created_at: string;
    updated_at: string;
  }

  interface TenantRelationshipContactRecord {
    id: number;
    contact_role: RelationshipContactRole;
    contact_role_display: string;
    full_name: string;
    relationship: string;
    phone: string;
    email: string;
    address: string;
    is_primary: boolean;
    notes: string;
    created_at: string;
    updated_at: string;
  }

  interface TenantLedgerLineItem {
    id: number;
    description: string;
    quantity: string;
    unit_price: string;
    amount: string;
    sort_order: number;
  }

  interface TenantLedgerPayment {
    id: number;
    amount: string;
    payment_date: string;
    payment_method: string;
    reference_number: string;
    notes: string;
    created_at: string;
  }

  interface TenantFinancialLedgerEntry {
    id: number;
    invoice_number: string;
    status: string;
    status_display: string;
    issue_date: string;
    due_date: string;
    total_amount: string;
    paid_amount: string;
    balance_due: string;
    notes: string;
    line_items: TenantLedgerLineItem[];
    payments: TenantLedgerPayment[];
  }

  interface TenantInventoryItemRecord {
    id: number;
    item_name: string;
    quantity: number;
    condition: InventoryCondition;
    condition_display: string;
    status: InventoryItemStatus;
    status_display: string;
    notes: string;
    created_at: string;
    updated_at: string;
  }

  interface TenantIncidentRecordItem {
    id: number;
    incident_type: IncidentType;
    incident_type_display: string;
    severity: Exclude<IncidentSeverity, "urgent">;
    severity_display: string;
    status: Exclude<IncidentStatus, TenantStatus>;
    status_display: string;
    title: string;
    description: string;
    occurred_at: string;
    resolved_at: string | null;
    notes: string;
    work_order: number | null;
    work_order_title: string;
    created_at: string;
    updated_at: string;
  }

  interface TenantIncidentLogEntry {
    id: string;
    entry_type: IncidentEntryType;
    title: string;
    incident_type: string;
    incident_type_display: string;
    severity: IncidentSeverity;
    severity_display: string;
    status: IncidentStatus;
    status_display: string;
    occurred_at: string;
    resolved_at: string | null;
    description: string;
    notes: string;
    work_order_id: number | null;
    work_order_title: string;
    source_label: string;
  }

  interface TenantMaintenanceIncidentRecord {
    id: number;
    title: string;
    priority: IncidentSeverity;
    priority_display: string;
    status: IncidentStatus;
    status_display: string;
    reported_date: string;
    completed_date: string | null;
    description: string;
    notes: string;
    is_breakdown: boolean;
  }

  interface TenantSourceOfTruthResponse {
    generated_at: string;
    tenant: TenantRegistryRow;
    identity: {
      documents: TenantIdentityDocumentRecord[];
      next_of_kin: TenantRelationshipContactRecord[];
      emergency_contacts: TenantRelationshipContactRecord[];
    };
    financial: {
      summary: {
        invoice_count: number;
        billed_total: string;
        paid_total: string;
        outstanding_total: string;
        overdue_total: string;
      };
      ledger: TenantFinancialLedgerEntry[];
      current_balance: string;
      overdue_balance: string;
    };
    inventory: {
      items: TenantInventoryItemRecord[];
      summary: {
        item_count: number;
        quantity_total: number;
      };
    };
    incident_log: {
      entries: TenantIncidentLogEntry[];
      manual_records: TenantIncidentRecordItem[];
      maintenance_records: TenantMaintenanceIncidentRecord[];
    };
  }

  interface IdentityDocumentFormState {
    document_type: IdentityDocumentType;
    document_number: string;
    holder_name: string;
    issuing_country: string;
    issue_date: string;
    expiry_date: string;
    scan_on_file: boolean;
    scan_reference: string;
    is_verified: boolean;
    notes: string;
  }

  interface RelationshipContactFormState {
    contact_role: RelationshipContactRole;
    full_name: string;
    relationship: string;
    phone: string;
    email: string;
    address: string;
    is_primary: boolean;
    notes: string;
  }

  interface InventoryItemFormState {
    item_name: string;
    quantity: string;
    condition: InventoryCondition;
    status: InventoryItemStatus;
    notes: string;
  }

  interface IncidentRecordFormState {
    incident_type: IncidentType;
    severity: Exclude<IncidentSeverity, "urgent">;
    status: Exclude<IncidentStatus, TenantStatus>;
    title: string;
    description: string;
    occurred_at: string;
    resolved_at: string;
    notes: string;
  }

  const shellClass =
    "relative overflow-hidden rounded-xl border border-slate-200/75 bg-white/64 shadow-[0_18px_52px_-34px_rgba(15,23,42,0.28)] backdrop-blur-xl";
  const onboardingSteps = [
    {
      title: "Identity",
      caption: "Tenant identity, linked records, and operating status.",
    },
    {
      title: "Assignment",
      caption: "Property, facility, unit, and space mapping.",
    },
    {
      title: "Lease",
      caption: "Dates, move window, and occupancy count.",
    },
    {
      title: "Review",
      caption: "Notes and final onboarding review.",
    },
  ] as const;
  const REGISTRY_ROW_HEIGHT = 182;
  const REGISTRY_OVERSCAN = 5;

  const emptyForm = (): TenantRegistryFormState => ({
    customer: "",
    contact_account: "",
    primary_user: "",
    property: "",
    unit: "",
    facility: "",
    facility_space: "",
    tenant_type: "corporate",
    status: "pending_move_in",
    display_name: "",
    lease_start_date: "",
    lease_end_date: "",
    move_in_date: "",
    move_out_date: "",
    occupant_count: "1",
    notes: "",
  });

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  function devFillTenant() {
    const today = new Date().toISOString().slice(0, 10);
    const nextYear = new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
    const names = ["Crescent Holdings Ltd", "Alpha Solar Energy", "Greenfield Logistics", "Zenith Property Group", "Coastal Imports Ltd", "Victory Construction Co"];
    const idx = Math.floor(Math.random() * names.length);
    form.display_name = names[idx];
    form.tenant_type = Math.random() > 0.3 ? "corporate" : "individual";
    form.status = "pending_move_in";
    form.lease_start_date = today;
    form.lease_end_date = nextYear;
    form.move_in_date = today;
    form.occupant_count = String(Math.floor(Math.random() * 10) + 1);
    form.notes = `Tenant registration for ${names[idx]}. Lease agreement pending final review.`;
    if (lookups?.customers?.length && !form.customer) form.customer = String(lookups.customers[0].id);
    if (lookups?.properties?.length && !form.property) form.property = String(lookups.properties[0].id);
    if (lookups?.facilities?.length && !form.facility) form.facility = String(lookups.facilities[0].id);
  }

  const statusOptions: Array<{ value: TenantStatus; label: string }> = [
    { value: "pending_move_in", label: "Pending Move In" },
    { value: "active", label: "Active" },
    { value: "moved_out", label: "Moved Out" },
    { value: "inactive", label: "Inactive" },
  ];

  const tenantTypeOptions: Array<{ value: TenantType; label: string }> = [
    { value: "corporate", label: "Corporate" },
    { value: "individual", label: "Individual" },
  ];
  const profileTabs: Array<{ value: RegistryProfileTab; label: string }> = [
    { value: "identity", label: "Identity" },
    { value: "financial", label: "Financial" },
    { value: "inventory", label: "Inventory" },
    { value: "incidents", label: "Incident Log" },
  ];
  const identityDocumentOptions: Array<{ value: IdentityDocumentType; label: string }> = [
    { value: "nin", label: "NIN" },
    { value: "passport", label: "Passport" },
    { value: "drivers_license", label: "Driver's License" },
    { value: "national_id", label: "National ID" },
    { value: "rc_certificate", label: "RC Certificate" },
    { value: "tax_id", label: "Tax ID" },
    { value: "other", label: "Other" },
  ];
  const relationshipContactOptions: Array<{ value: RelationshipContactRole; label: string }> = [
    { value: "next_of_kin", label: "Next of Kin" },
    { value: "emergency", label: "Emergency Contact" },
  ];
  const inventoryConditionOptions: Array<{ value: InventoryCondition; label: string }> = [
    { value: "new", label: "New" },
    { value: "good", label: "Good" },
    { value: "fair", label: "Fair" },
    { value: "poor", label: "Poor" },
  ];
  const inventoryStatusOptions: Array<{ value: InventoryItemStatus; label: string }> = [
    { value: "provided", label: "Provided" },
    { value: "returned", label: "Returned" },
    { value: "missing", label: "Missing" },
    { value: "damaged", label: "Damaged" },
  ];
  const incidentTypeOptions: Array<{ value: IncidentType; label: string }> = [
    { value: "lease_violation", label: "Lease Violation" },
    { value: "maintenance_issue", label: "Maintenance Issue" },
    { value: "damage", label: "Damage" },
    { value: "noise", label: "Noise Complaint" },
    { value: "security", label: "Security Incident" },
    { value: "payment_breach", label: "Payment Breach" },
    { value: "other", label: "Other" },
  ];
  const incidentSeverityOptions: Array<{ value: Exclude<IncidentSeverity, "urgent">; label: string }> = [
    { value: "low", label: "Low" },
    { value: "medium", label: "Medium" },
    { value: "high", label: "High" },
    { value: "critical", label: "Critical" },
  ];
  const incidentStatusOptions: Array<{ value: Exclude<IncidentStatus, TenantStatus>; label: string }> = [
    { value: "open", label: "Open" },
    { value: "under_review", label: "Under Review" },
    { value: "resolved", label: "Resolved" },
    { value: "closed", label: "Closed" },
  ];

  const emptyIdentityDocumentForm = (): IdentityDocumentFormState => ({
    document_type: "nin",
    document_number: "",
    holder_name: "",
    issuing_country: "",
    issue_date: "",
    expiry_date: "",
    scan_on_file: false,
    scan_reference: "",
    is_verified: false,
    notes: "",
  });

  const emptyRelationshipContactForm = (): RelationshipContactFormState => ({
    contact_role: "next_of_kin",
    full_name: "",
    relationship: "",
    phone: "",
    email: "",
    address: "",
    is_primary: false,
    notes: "",
  });

  const emptyInventoryItemForm = (): InventoryItemFormState => ({
    item_name: "",
    quantity: "1",
    condition: "good",
    status: "provided",
    notes: "",
  });

  const emptyIncidentRecordForm = (): IncidentRecordFormState => ({
    incident_type: "lease_violation",
    severity: "medium",
    status: "open",
    title: "",
    description: "",
    occurred_at: "",
    resolved_at: "",
    notes: "",
  });

  let loading = $state(true);
  let refreshing = $state(false);
  let saving = $state(false);
  let overview = $state<TenantRegistryOverview | null>(null);
  let lookups = $state<TenantRegistryLookups | null>(null);
  let profiles = $state<TenantRegistryRow[]>([]);
  let search = $state("");
  let quickFilter = $state<RegistryQuickFilter>("all");
  let statusFilter = $state<"all" | TenantStatus>("all");
  let showAdvancedFilters = $state(false);
  let showMasterListDrawer = $state(false);
  let selectedPropertyFilters = $state<string[]>([]);
  let leaseEndFrom = $state("");
  let leaseEndTo = $state("");
  let selectedPaymentFilters = $state<Array<Exclude<RegistryPaymentStatus, "unknown">>>([]);
  let selectedTenantTypeFilters = $state<TenantType[]>([]);
  let showDrawer = $state(false);
  let showOnboardingModal = $state(false);
  let onboardingStep = $state(0);
  let showingSearchSuggestions = $state(false);
  let showExportMenu = $state(false);
  let exportingFormat = $state<RegistryExportFormat | null>(null);
  let importing = $state(false);
  let editingTenantId = $state<number | null>(null);
  let form = $state<TenantRegistryFormState>(emptyForm());
  let importInput: HTMLInputElement | null = null;
  let showProfileModal = $state(false);
  let profileLoading = $state(false);
  let selectedProfileId = $state<number | null>(null);
  let selectedProfileSummary = $state<TenantRegistryRow | null>(null);
  let profileSourceOfTruth = $state<TenantSourceOfTruthResponse | null>(null);
  let activeProfileTab = $state<RegistryProfileTab>("identity");
  let showProfileRecordDrawer = $state(false);
  let profileDrawerMode = $state<RegistryProfileDrawerMode>("identity");
  let savingProfileRecord = $state(false);
  let identityDocumentForm = $state<IdentityDocumentFormState>(emptyIdentityDocumentForm());
  let relationshipContactForm = $state<RelationshipContactFormState>(emptyRelationshipContactForm());
  let inventoryItemForm = $state<InventoryItemFormState>(emptyInventoryItemForm());
  let incidentRecordForm = $state<IncidentRecordFormState>(emptyIncidentRecordForm());
  let registryViewport = $state<HTMLDivElement | null>(null);
  let registryScrollTop = $state(0);
  let registryViewportHeight = $state(760);
  let registryVirtualWindow = $derived.by(() => virtualRegistryWindow());

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

  function fmtMoney(value: string | number | null | undefined): string {
    const amount = typeof value === "string" ? Number(value) : Number(value ?? 0);
    return new Intl.NumberFormat("en-NG", {
      style: "currency",
      currency: "NGN",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(Number.isFinite(amount) ? amount : 0);
  }

  function parseDateOnly(value: string | null | undefined): Date | null {
    if (!value) return null;
    const parsed = new Date(`${value}T00:00:00`);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
  }

  function isoDateValue(value: Date): string {
    const localDate = new Date(value.getTime() - value.getTimezoneOffset() * 60_000);
    return localDate.toISOString().slice(0, 10);
  }

  function parseApiMessage(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      if (typeof error.data.detail === "string" && error.data.detail) return error.data.detail;
      const firstFieldError = Object.values(error.fieldErrors)[0]?.[0];
      if (firstFieldError) return firstFieldError;
    }
    return fallback;
  }

  function todayIso(): string {
    return isoDateValue(new Date());
  }

  function unwrapList<T>(payload: PaginatedResponse<T> | T[]): T[] {
    return Array.isArray(payload) ? payload : (payload?.results ?? []);
  }

  async function fetchAllRegistryProfiles(): Promise<TenantRegistryRow[]> {
    const rows: TenantRegistryRow[] = [];
    let page = 1;

    while (page <= 40) {
      const payload = await api.get<PaginatedResponse<TenantRegistryRow> | TenantRegistryRow[]>("/tenants/profiles/", {
        ordering: "display_name",
        page: String(page),
        page_size: "200",
      });

      if (Array.isArray(payload)) return payload;

      rows.push(...unwrapList(payload));

      if (!payload.next || payload.results.length === 0 || rows.length >= payload.count) {
        break;
      }

      page += 1;
    }

    return rows;
  }

  function boolLabel(value: boolean): string {
    return value ? "Yes" : "No";
  }

  function statusBadgeClass(status: TenantStatus): string {
    switch (status) {
      case "active":
        return "border-[#b7e8cf] bg-[#ecfff4] text-[#157347]";
      case "pending_move_in":
        return "border-sky-200 bg-sky-50 text-sky-700";
      case "moved_out":
        return "border-slate-200 bg-slate-100 text-slate-700";
      default:
        return "border-neutral-200 bg-neutral-100 text-neutral-600";
    }
  }

  function tenantTypeBadgeClass(type: TenantType): string {
    return type === "corporate"
      ? "border-violet-200 bg-violet-50 text-violet-700"
      : "border-amber-200 bg-amber-50 text-amber-700";
  }

  function hygieneBadgeClass(count: number): string {
    return count > 0
      ? "border-rose-200 bg-rose-50 text-rose-700"
      : "border-[#b7e8cf] bg-[#ecfff4] text-[#157347]";
  }

  function profileTabClass(tab: RegistryProfileTab): string {
    return activeProfileTab === tab
      ? "border-sky-200 bg-sky-50 text-sky-700 shadow-sm"
      : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:text-slate-950";
  }

  function paymentStateBadgeClass(balance: string): string {
    return Number(balance) > 0
      ? "border-rose-200 bg-rose-50 text-rose-700"
      : "border-[#b7e8cf] bg-[#ecfff4] text-[#157347]";
  }

  function documentStatusBadgeClass(record: TenantIdentityDocumentRecord): string {
    if (record.is_verified) return "border-[#b7e8cf] bg-[#ecfff4] text-[#157347]";
    if (record.scan_on_file) return "border-sky-200 bg-sky-50 text-sky-700";
    return "border-slate-200 bg-slate-100 text-slate-600";
  }

  function relationshipRoleBadgeClass(role: RelationshipContactRole): string {
    return role === "next_of_kin"
      ? "border-violet-200 bg-violet-50 text-violet-700"
      : "border-rose-200 bg-rose-50 text-rose-700";
  }

  function inventoryConditionBadgeClass(condition: InventoryCondition): string {
    switch (condition) {
      case "new":
        return "border-sky-200 bg-sky-50 text-sky-700";
      case "good":
        return "border-[#b7e8cf] bg-[#ecfff4] text-[#157347]";
      case "fair":
        return "border-amber-200 bg-amber-50 text-amber-700";
      default:
        return "border-rose-200 bg-rose-50 text-rose-700";
    }
  }

  function inventoryStatusBadgeClass(status: InventoryItemStatus): string {
    switch (status) {
      case "provided":
        return "border-[#b7e8cf] bg-[#ecfff4] text-[#157347]";
      case "returned":
        return "border-sky-200 bg-sky-50 text-sky-700";
      case "missing":
        return "border-rose-200 bg-rose-50 text-rose-700";
      default:
        return "border-orange-200 bg-orange-50 text-orange-700";
    }
  }

  function incidentSeverityBadgeClass(severity: IncidentSeverity): string {
    switch (severity) {
      case "critical":
      case "urgent":
        return "border-rose-200 bg-rose-50 text-rose-700";
      case "high":
        return "border-orange-200 bg-orange-50 text-orange-700";
      case "medium":
        return "border-amber-200 bg-amber-50 text-amber-700";
      default:
        return "border-sky-200 bg-sky-50 text-sky-700";
    }
  }

  function incidentStatusBadgeClass(status: IncidentStatus): string {
    switch (status) {
      case "resolved":
      case "closed":
      case "completed":
      case "verified":
      case "active":
        return "border-[#b7e8cf] bg-[#ecfff4] text-[#157347]";
      case "under_review":
      case "in_progress":
      case "assigned":
        return "border-sky-200 bg-sky-50 text-sky-700";
      case "open":
      case "pending_move_in":
        return "border-amber-200 bg-amber-50 text-amber-700";
      default:
        return "border-slate-200 bg-slate-100 text-slate-700";
    }
  }

  function financialStatusBadgeClass(status: string): string {
    switch (status) {
      case "paid":
        return "border-[#b7e8cf] bg-[#ecfff4] text-[#157347]";
      case "overdue":
        return "border-rose-200 bg-rose-50 text-rose-700";
      case "sent":
        return "border-sky-200 bg-sky-50 text-sky-700";
      default:
        return "border-slate-200 bg-slate-100 text-slate-700";
    }
  }

  function profileDrawerTitle(mode: RegistryProfileDrawerMode): string {
    switch (mode) {
      case "identity":
        return "Add Identity Document";
      case "contact":
        return "Add Relationship Contact";
      case "inventory":
        return "Add Inventory Item";
      default:
        return "Add Incident Record";
    }
  }

  function profileDrawerDescription(mode: RegistryProfileDrawerMode): string {
    switch (mode) {
      case "identity":
        return "Store scanned ID coverage, verification, and document metadata against the tenant profile.";
      case "contact":
        return "Record next-of-kin and emergency contacts for compliance and escalation readiness.";
      case "inventory":
        return "Capture the handover checklist for furniture, devices, and unit accessories.";
      default:
        return "Log lease violations, notable maintenance issues, or other tenant-facing incidents.";
    }
  }

  function currentProfileRecord(): TenantRegistryRow | null {
    if (profileSourceOfTruth?.tenant) return profileSourceOfTruth.tenant;
    if (selectedProfileSummary) return selectedProfileSummary;
    if (selectedProfileId !== null) {
      return profiles.find((profile) => profile.id === selectedProfileId) ?? null;
    }
    return null;
  }

  function handleRegistryScroll(event: Event) {
    const target = event.currentTarget as HTMLDivElement;
    registryScrollTop = target.scrollTop;
    registryViewportHeight = target.clientHeight;
  }

  function resetRegistryViewport() {
    registryScrollTop = 0;
    if (registryViewport) {
      registryViewport.scrollTop = 0;
      registryViewportHeight = registryViewport.clientHeight || 760;
    }
  }

  function virtualRegistryWindow() {
    const rows = filteredProfiles();
    const total = rows.length;
    const viewportHeight = registryViewportHeight || 760;
    const visibleCount = Math.max(
      8,
      Math.ceil(viewportHeight / REGISTRY_ROW_HEIGHT) + REGISTRY_OVERSCAN * 2,
    );
    const start = Math.max(0, Math.floor(registryScrollTop / REGISTRY_ROW_HEIGHT) - REGISTRY_OVERSCAN);
    const end = Math.min(total, start + visibleCount);
    return {
      rows,
      start,
      end,
      visibleRows: rows.slice(start, end),
      topSpacer: start * REGISTRY_ROW_HEIGHT,
      bottomSpacer: Math.max(0, (total - end) * REGISTRY_ROW_HEIGHT),
    };
  }

  function onboardingStageMetrics(): RegistryOnboardingStage[] {
    const counts = {
      applicant: 0,
      due_diligence: 0,
      allocation: 0,
      lease_setup: 0,
      registered: 0,
    };

    for (const profile of profiles) {
      if (profile.status === "moved_out" || profile.status === "inactive") continue;

      const hasIdentityAnchor = Boolean(
        profile.display_name.trim() || profile.customer || profile.contact_account || profile.primary_user,
      );
      const hasContactChannel = Boolean(profile.contact_email || profile.contact_phone);
      const hasAssignment = Boolean(profile.property || profile.unit || profile.facility || profile.facility_space);
      const hasLeaseWindow = Boolean(profile.lease_start_date || profile.lease_end_date || profile.move_in_date);

      if (!hasIdentityAnchor) {
        counts.applicant += 1;
      } else if (!profile.customer || !hasContactChannel) {
        counts.due_diligence += 1;
      } else if (!hasAssignment) {
        counts.allocation += 1;
      } else if (!hasLeaseWindow) {
        counts.lease_setup += 1;
      } else {
        counts.registered += 1;
      }
    }

    return [
      {
        key: "applicant",
        label: "Applicant",
        description: "Intake captured, but core identity still needs to be anchored to the master record.",
        count: counts.applicant,
        className: "border-slate-200 bg-slate-50/80 text-slate-700",
        stepClass: "bg-slate-700 text-white",
      },
      {
        key: "due_diligence",
        label: "Due Diligence",
        description: "Customer link and reachable contact channel are being completed for the tenant profile.",
        count: counts.due_diligence,
        className: "border-amber-200 bg-amber-50 text-amber-700",
        stepClass: "bg-amber-500 text-white",
      },
      {
        key: "allocation",
        label: "Space Allocation",
        description: "The tenant is approved, but unit, facility, or mapped space still needs assignment.",
        count: counts.allocation,
        className: "border-sky-200 bg-sky-50 text-sky-700",
        stepClass: "bg-sky-500 text-white",
      },
      {
        key: "lease_setup",
        label: "Lease Setup",
        description: "Assignment exists, but lease dates and move window still need to be finalized.",
        count: counts.lease_setup,
        className: "border-violet-200 bg-violet-50 text-violet-700",
        stepClass: "bg-violet-500 text-white",
      },
      {
        key: "registered",
        label: "Registered",
        description: "The tenant record is fully structured and ready for operational monitoring and billing sync.",
        count: counts.registered,
        className: "border-emerald-200 bg-emerald-50 text-emerald-700",
        stepClass: "bg-emerald-500 text-white",
      },
    ];
  }

  function onboardingPendingCount(): number {
    return profiles.filter((profile) => profile.status === "pending_move_in").length;
  }

  function onboardingReadyCount(): number {
    return onboardingStageMetrics().find((stage) => stage.key === "registered")?.count ?? 0;
  }

  function onboardingArchivedCount(): number {
    return profiles.filter((profile) => profile.status === "moved_out" || profile.status === "inactive").length;
  }

  function recordFlags(profile: TenantRegistryRow): string[] {
    const flags: string[] = [];
    if (!profile.customer) flags.push("Missing customer");
    if (!profile.contact_email && !profile.contact_phone) flags.push("Missing contact");
    if (!profile.property && !profile.unit && !profile.facility && !profile.facility_space) flags.push("Missing location");
    return flags;
  }

  function registryTenantCode(profile: TenantRegistryRow): string {
    return `T-${String(profile.id).padStart(3, "0")}`;
  }

  function registryPreferredContact(profile: TenantRegistryRow): string {
    return profile.contact_phone || profile.contact_email || "No contact channel linked";
  }

  function registryAssignedUnitLabel(profile: TenantRegistryRow): string {
    if (profile.space_label) return profile.space_label;
    if (profile.unit_number) return profile.unit_number;
    return "Unassigned";
  }

  function registryAssignedUnitMeta(profile: TenantRegistryRow): string {
    const parts = [profile.unit_number && profile.space_label ? `Unit ${profile.unit_number}` : "", profile.facility_code]
      .filter(Boolean)
      .join(" · ");
    return parts || "No mapped unit or facility";
  }

  function registryPropertyLabel(profile: TenantRegistryRow): string {
    return profile.property_name || "No property linked";
  }

  function registryPropertyMeta(profile: TenantRegistryRow): string {
    return profile.property_location || "Location not mapped";
  }

  function registryLeaseState(profile: TenantRegistryRow): { label: string; className: string; meta: string } {
    const today = new Date();
    const currentDate = new Date(today.getFullYear(), today.getMonth(), today.getDate());
    const leaseEnd = parseDateOnly(profile.lease_end_date);

    if (profile.status === "moved_out" || profile.status === "inactive") {
      return {
        label: "Archived",
        className: "border-slate-200 bg-slate-100 text-slate-700",
        meta: profile.move_out_date ? `Moved out ${fmtDate(profile.move_out_date)}` : "Historical tenant record",
      };
    }

    if (profile.status === "pending_move_in") {
      return {
        label: "Prospective",
        className: "border-sky-200 bg-sky-50 text-sky-700",
        meta: profile.move_in_date ? `Move in ${fmtDate(profile.move_in_date)}` : "Pending occupancy",
      };
    }

    if (leaseEnd) {
      const msPerDay = 24 * 60 * 60 * 1000;
      const daysToExpiry = Math.floor((leaseEnd.getTime() - currentDate.getTime()) / msPerDay);

      if (daysToExpiry < 0) {
        return {
          label: "Expired",
          className: "border-rose-200 bg-rose-50 text-rose-700",
          meta: `Ended ${fmtDate(profile.lease_end_date)}`,
        };
      }

      if (daysToExpiry <= 60) {
        return {
          label: "Expiring Soon",
          className: "border-amber-200 bg-amber-50 text-amber-700",
          meta: `Ends ${fmtDate(profile.lease_end_date)}`,
        };
      }
    }

    return {
      label: "Active",
      className: "border-[#b7e8cf] bg-[#ecfff4] text-[#157347]",
      meta: profile.lease_end_date ? `Ends ${fmtDate(profile.lease_end_date)}` : "Active lease record",
    };
  }

  function registryTags(
    profile: TenantRegistryRow,
  ): Array<{ label: string; className: string }> {
    const tags: Array<{ label: string; className: string }> = [
      profile.tenant_type === "corporate"
        ? { label: "Commercial", className: "border-violet-200 bg-violet-50 text-violet-700" }
        : { label: "Residential", className: "border-amber-200 bg-amber-50 text-amber-700" },
    ];

    if (!profile.customer) {
      tags.push({ label: "Unlinked", className: "border-rose-200 bg-rose-50 text-rose-700" });
    } else if (!profile.unit && !profile.facility_space) {
      tags.push({ label: "Unassigned", className: "border-slate-200 bg-slate-100 text-slate-700" });
    } else if (!profile.contact_email && !profile.contact_phone) {
      tags.push({ label: "Needs Contact", className: "border-orange-200 bg-orange-50 text-orange-700" });
    } else {
      tags.push({ label: "Mapped", className: "border-emerald-200 bg-emerald-50 text-emerald-700" });
    }

    return tags;
  }

  function toggleSelection<T extends string>(values: T[], value: T): T[] {
    return values.includes(value) ? values.filter((entry) => entry !== value) : [...values, value];
  }

  function togglePropertyFilter(propertyId: string) {
    selectedPropertyFilters = toggleSelection(selectedPropertyFilters, propertyId);
  }

  function togglePaymentFilter(status: Exclude<RegistryPaymentStatus, "unknown">) {
    selectedPaymentFilters = toggleSelection(selectedPaymentFilters, status);
  }

  function toggleTenantTypeFilter(type: TenantType) {
    selectedTenantTypeFilters = toggleSelection(selectedTenantTypeFilters, type);
  }

  function clearAdvancedFilters() {
    selectedPropertyFilters = [];
    leaseEndFrom = "";
    leaseEndTo = "";
    selectedPaymentFilters = [];
    selectedTenantTypeFilters = [];
  }

  function setLeaseRangeNext60Days() {
    const today = new Date();
    const end = new Date(today);
    end.setDate(end.getDate() + 60);
    leaseEndFrom = isoDateValue(today);
    leaseEndTo = isoDateValue(end);
  }

  function advancedFilterCount(): number {
    let count = 0;
    if (selectedPropertyFilters.length) count += 1;
    if (leaseEndFrom || leaseEndTo) count += 1;
    if (selectedPaymentFilters.length) count += 1;
    if (selectedTenantTypeFilters.length) count += 1;
    return count;
  }

  function advancedFilterSummaries(): string[] {
    const summaries: string[] = [];
    if (selectedPropertyFilters.length) {
      const propertyNames = propertyOptions()
        .filter((propertyRecord) => selectedPropertyFilters.includes(String(propertyRecord.id)))
        .map((propertyRecord) => propertyRecord.name);
      summaries.push(
        propertyNames.length <= 2
          ? `Properties: ${propertyNames.join(", ")}`
          : `Properties: ${propertyNames.length} selected`,
      );
    }
    if (leaseEndFrom || leaseEndTo) {
      summaries.push(`Lease End: ${fmtDate(leaseEndFrom || null)} - ${fmtDate(leaseEndTo || null)}`);
    }
    if (selectedPaymentFilters.length) {
      summaries.push(
        `Payment: ${selectedPaymentFilters.map((value) => (value === "debt_free" ? "Debt-Free" : "Delinquent")).join(", ")}`,
      );
    }
    if (selectedTenantTypeFilters.length) {
      summaries.push(
        `Type: ${selectedTenantTypeFilters.map((value) => (value === "corporate" ? "Corporate" : "Individual")).join(", ")}`,
      );
    }
    return summaries;
  }

  function propertyOptions(): PropertyLookup[] {
    return lookups?.properties ?? [];
  }

  function profileMatchesQuickFilter(profile: TenantRegistryRow): boolean {
    switch (quickFilter) {
      case "active":
        return profile.status === "active";
      case "past":
        return profile.status === "moved_out" || profile.status === "inactive";
      case "prospective":
        return profile.status === "pending_move_in";
      default:
        return true;
    }
  }

  function quickFilterCount(filter: Exclude<RegistryQuickFilter, "all">): number {
    return profiles.filter((profile) => {
      switch (filter) {
        case "active":
          return profile.status === "active";
        case "past":
          return profile.status === "moved_out" || profile.status === "inactive";
        case "prospective":
          return profile.status === "pending_move_in";
      }
    }).length;
  }

  function quickFilterButtonClass(filter: RegistryQuickFilter): string {
    const active = quickFilter === filter;
    switch (filter) {
      case "active":
        return active
          ? "border-emerald-300 bg-emerald-50 text-emerald-700 shadow-sm"
          : "border-slate-200 bg-white/80 text-slate-600 hover:border-emerald-200 hover:text-emerald-700";
      case "past":
        return active
          ? "border-rose-300 bg-rose-50 text-rose-700 shadow-sm"
          : "border-slate-200 bg-white/80 text-slate-600 hover:border-rose-200 hover:text-rose-700";
      case "prospective":
        return active
          ? "border-sky-300 bg-sky-50 text-sky-700 shadow-sm"
          : "border-slate-200 bg-white/80 text-slate-600 hover:border-sky-200 hover:text-sky-700";
      default:
        return active
          ? "border-slate-300 bg-slate-100 text-slate-700 shadow-sm"
          : "border-slate-200 bg-white/80 text-slate-600 hover:border-slate-300";
    }
  }

  function quickFilterLabel(filter: RegistryQuickFilter): string {
    switch (filter) {
      case "active":
        return "Active";
      case "past":
        return "Past";
      case "prospective":
        return "Prospective";
      default:
        return "All";
    }
  }

  function registrySearchSuggestions(): RegistrySearchSuggestion[] {
    const query = search.trim().toLowerCase();
    if (!query) return [];

    const suggestions: RegistrySearchSuggestion[] = [];
    const seen = new Set<string>();
    const pushSuggestion = (kind: RegistrySearchSuggestion["kind"], value: string, label: string, helper: string) => {
      const trimmed = value.trim();
      if (!trimmed) return;
      const key = `${kind}:${trimmed.toLowerCase()}`;
      if (seen.has(key)) return;
      seen.add(key);
      suggestions.push({
        id: key,
        kind,
        value: trimmed,
        label,
        helper,
      });
    };

    for (const profile of profiles) {
      if (profile.resolved_display_name.toLowerCase().includes(query)) {
        pushSuggestion("tenant", profile.resolved_display_name, profile.resolved_display_name, profile.property_name || "Tenant name");
      }
      if ((profile.contact_phone || "").toLowerCase().includes(query)) {
        pushSuggestion("phone", profile.contact_phone, profile.contact_phone, profile.resolved_display_name || "Phone");
      }
      if ((profile.unit_number || "").toLowerCase().includes(query)) {
        pushSuggestion("unit", profile.unit_number, `Unit ${profile.unit_number}`, profile.property_name || "Unit");
      }
      if ((profile.property_location || "").toLowerCase().includes(query)) {
        pushSuggestion("site", profile.property_location, profile.property_location, profile.property_name || "Site");
      }
      if (suggestions.length >= 8) break;
    }

    return suggestions.slice(0, 8);
  }

  function selectSearchSuggestion(suggestion: RegistrySearchSuggestion) {
    search = suggestion.value;
    showingSearchSuggestions = false;
  }

  function profilePropertyId(profile: TenantRegistryRow): number | null {
    if (profile.property) return profile.property;
    const space = lookups?.spaces.find((item) => item.id === profile.facility_space);
    if (space) return space.property_id;
    const unit = lookups?.units.find((item) => item.id === profile.unit);
    if (unit) return unit.property_id;
    const facility = lookups?.facilities.find((item) => item.id === profile.facility);
    if (facility) return facility.property_id;
    return null;
  }

  function filteredFacilities(): FacilityLookup[] {
    if (!lookups) return [];
    if (!form.property) return lookups.facilities;
    const propertyId = Number(form.property);
    return lookups.facilities.filter((facility) => facility.property_id === propertyId);
  }

  function filteredUnits(): UnitLookup[] {
    if (!lookups) return [];
    if (!form.property) return lookups.units;
    const propertyId = Number(form.property);
    return lookups.units.filter((unit) => unit.property_id === propertyId);
  }

  function filteredSpaces(): SpaceLookup[] {
    if (!lookups) return [];
    if (form.facility) {
      const facilityId = Number(form.facility);
      return lookups.spaces.filter((space) => space.facility_id === facilityId);
    }
    if (form.property) {
      const propertyId = Number(form.property);
      return lookups.spaces.filter((space) => space.property_id === propertyId);
    }
    return lookups.spaces;
  }

  function matchesSelectedProperties(profile: TenantRegistryRow): boolean {
    if (!selectedPropertyFilters.length) return true;
    const propertyId = profilePropertyId(profile);
    return propertyId !== null && selectedPropertyFilters.includes(String(propertyId));
  }

  function matchesLeaseEndRange(profile: TenantRegistryRow): boolean {
    if (!leaseEndFrom && !leaseEndTo) return true;
    const leaseEnd = parseDateOnly(profile.lease_end_date);
    if (!leaseEnd) return false;
    const fromDate = parseDateOnly(leaseEndFrom);
    const toDate = parseDateOnly(leaseEndTo);
    if (fromDate && leaseEnd < fromDate) return false;
    if (toDate && leaseEnd > toDate) return false;
    return true;
  }

  function matchesPaymentFilters(profile: TenantRegistryRow): boolean {
    if (!selectedPaymentFilters.length) return true;
    return profile.payment_status !== "unknown" && selectedPaymentFilters.includes(profile.payment_status);
  }

  function matchesTenantTypeFilters(profile: TenantRegistryRow): boolean {
    if (!selectedTenantTypeFilters.length) return true;
    return selectedTenantTypeFilters.includes(profile.tenant_type);
  }

  function filteredProfiles(): TenantRegistryRow[] {
    const query = search.trim().toLowerCase();

    return profiles.filter((profile) => {
      if (!profileMatchesQuickFilter(profile)) return false;
      if (statusFilter !== "all" && profile.status !== statusFilter) return false;
      if (!matchesSelectedProperties(profile)) return false;
      if (!matchesLeaseEndRange(profile)) return false;
      if (!matchesPaymentFilters(profile)) return false;
      if (!matchesTenantTypeFilters(profile)) return false;
      if (!query) return true;

      return [
        profile.resolved_display_name,
        profile.customer_name,
        profile.contact_account_name,
        profile.primary_user_name,
        profile.property_name,
        profile.unit_number,
        profile.facility_code,
        profile.space_label,
        profile.property_location,
        profile.contact_email,
        profile.contact_phone,
      ]
        .join(" ")
        .toLowerCase()
        .includes(query);
    });
  }

  function deriveEditPropertyId(profile: TenantRegistryRow): string {
    if (profile.property) return String(profile.property);
    const space = lookups?.spaces.find((item) => item.id === profile.facility_space);
    if (space) return String(space.property_id);
    const unit = lookups?.units.find((item) => item.id === profile.unit);
    if (unit) return String(unit.property_id);
    const facility = lookups?.facilities.find((item) => item.id === profile.facility);
    if (facility) return String(facility.property_id);
    return "";
  }

  function resetForm() {
    form = emptyForm();
  }

  function resetProfileRecordForms() {
    identityDocumentForm = emptyIdentityDocumentForm();
    relationshipContactForm = emptyRelationshipContactForm();
    inventoryItemForm = emptyInventoryItemForm();
    incidentRecordForm = {
      ...emptyIncidentRecordForm(),
      occurred_at: todayIso(),
    };
  }

  function openCreateModal() {
    showMasterListDrawer = false;
    showDrawer = false;
    editingTenantId = null;
    resetForm();
    onboardingStep = 0;
    showExportMenu = false;
    showOnboardingModal = true;
  }

  function closeOnboardingModal() {
    showOnboardingModal = false;
    onboardingStep = 0;
    editingTenantId = null;
    showExportMenu = false;
    saving = false;
    resetForm();
  }

  function openMasterListDrawer() {
    showMasterListDrawer = true;
    if (typeof window !== "undefined") {
      window.requestAnimationFrame(() => resetRegistryViewport());
    }
  }

  function closeMasterListDrawer() {
    showMasterListDrawer = false;
  }

  function closeProfileModal() {
    showProfileModal = false;
    selectedProfileId = null;
    selectedProfileSummary = null;
    profileSourceOfTruth = null;
    profileLoading = false;
    activeProfileTab = "identity";
    closeProfileRecordDrawer();
  }

  function openProfileRecordDrawer(mode: RegistryProfileDrawerMode) {
    if (!selectedProfileId) {
      toast.info("Select tenant", "Open a tenant profile before adding source-of-truth records.");
      return;
    }
    profileDrawerMode = mode;
    resetProfileRecordForms();
    if (mode === "contact") {
      relationshipContactForm.contact_role = "next_of_kin";
    }
    showProfileRecordDrawer = true;
  }

  function closeProfileRecordDrawer() {
    showProfileRecordDrawer = false;
    savingProfileRecord = false;
    resetProfileRecordForms();
  }

  function validateOnboardingStep(step = onboardingStep): boolean {
    if (step === 0) {
      const hasIdentity = Boolean(form.display_name.trim() || form.customer || form.contact_account || form.primary_user);
      if (!hasIdentity) {
        toast.info("Identity required", "Add a display name or link a customer, contact account, or primary user.");
        return false;
      }
    }

    if (step === 2) {
      const occupantCount = Number(form.occupant_count || "1");
      if (!Number.isFinite(occupantCount) || occupantCount < 1) {
        toast.info("Occupancy required", "Occupant count must be at least 1.");
        return false;
      }
    }

    return true;
  }

  function nextOnboardingStep() {
    if (!validateOnboardingStep()) return;
    onboardingStep = Math.min(onboardingStep + 1, onboardingSteps.length - 1);
  }

  function previousOnboardingStep() {
    onboardingStep = Math.max(onboardingStep - 1, 0);
  }

  async function submitOnboarding() {
    if (!validateOnboardingStep()) return;
    await submitForm();
  }

  function authToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("access_token") || sessionStorage.getItem("access_token");
  }

  function suggestedDisplayName(): string {
    if (!lookups) return form.display_name.trim();
    const customer = lookups.customers.find((item) => item.id === Number(form.customer));
    const contact = lookups.contact_accounts.find((item) => item.id === Number(form.contact_account));
    const user = lookups.users.find((item) => item.id === Number(form.primary_user));
    return form.display_name.trim() || customer?.name || contact?.name || user?.name || "New tenant";
  }

  async function exportRegistry(format: RegistryExportFormat) {
    exportingFormat = format;
    showExportMenu = false;

    try {
      const token = authToken();
      const response = await fetch(`/api/tenants/profiles/export/?export_format=${format}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!response.ok) throw new Error("Export failed");

      const blob = await response.blob();
      const disposition = response.headers.get("Content-Disposition") || "";
      const fileNameMatch = disposition.match(/filename=\"?([^"]+)\"?/i);
      const fileName = fileNameMatch?.[1] || `tenant-registry.${format}`;
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      toast.success("Registry exported", `${format === "csv" ? "CSV" : "Excel"} download has started.`);
    } catch {
      toast.error("Export failed", "Could not export the tenant registry file.");
    } finally {
      exportingFormat = null;
    }
  }

  function triggerImportPicker() {
    importInput?.click();
  }

  async function handleImportSelection(event: Event) {
    const target = event.currentTarget as HTMLInputElement;
    const file = target.files?.[0];
    target.value = "";
    if (!file) return;

    importing = true;
    try {
      const payload = new FormData();
      payload.append("file", file);
      const result = await api.upload<TenantRegistryImportResult>("/tenants/profiles/import/", payload);
      await fetchRegistry();
      toast.success("Import complete", result.detail);
      if (result.failed_rows.length > 0) {
        toast.info("Import review", `${result.failed_rows.length} row${result.failed_rows.length === 1 ? "" : "s"} could not be imported.`);
      }
    } catch (error) {
      toast.error("Import failed", parseApiMessage(error, "Could not import the tenant registry file."));
    } finally {
      importing = false;
    }
  }

  function autofillDisplayName() {
    if (form.display_name.trim() || !lookups) return;
    const customer = lookups.customers.find((item) => item.id === Number(form.customer));
    const contact = lookups.contact_accounts.find((item) => item.id === Number(form.contact_account));
    const user = lookups.users.find((item) => item.id === Number(form.primary_user));
    form.display_name = customer?.name || contact?.name || user?.name || form.display_name;
  }

  function handlePropertyChange(value: string) {
    form.property = value;
    if (form.facility) {
      const facility = lookups?.facilities.find((item) => item.id === Number(form.facility));
      if (facility && String(facility.property_id) !== value) {
        form.facility = "";
      }
    }
    if (form.unit) {
      const unit = lookups?.units.find((item) => item.id === Number(form.unit));
      if (unit && String(unit.property_id) !== value) {
        form.unit = "";
      }
    }
    if (form.facility_space) {
      const space = lookups?.spaces.find((item) => item.id === Number(form.facility_space));
      if (space && String(space.property_id) !== value) {
        form.facility_space = "";
      }
    }
  }

  function handleUnitChange(value: string) {
    form.unit = value;
    if (!lookups || !value) return;
    const unit = lookups.units.find((item) => item.id === Number(value));
    if (!unit) return;
    form.property = String(unit.property_id);
    const linkedSpace = lookups.spaces.find((item) => item.unit_id === unit.id);
    if (linkedSpace) {
      form.facility_space = String(linkedSpace.id);
      form.facility = String(linkedSpace.facility_id);
    }
  }

  function handleFacilityChange(value: string) {
    form.facility = value;
    if (!lookups || !value) return;
    const facility = lookups.facilities.find((item) => item.id === Number(value));
    if (!facility) return;
    form.property = String(facility.property_id);
    if (form.facility_space) {
      const space = lookups.spaces.find((item) => item.id === Number(form.facility_space));
      if (space && space.facility_id !== facility.id) {
        form.facility_space = "";
      }
    }
  }

  function handleSpaceChange(value: string) {
    form.facility_space = value;
    if (!lookups || !value) return;
    const space = lookups.spaces.find((item) => item.id === Number(value));
    if (!space) return;
    form.facility = String(space.facility_id);
    form.unit = String(space.unit_id);
    form.property = String(space.property_id);
  }

  async function fetchProfileSourceOfTruth(profileId: number) {
    profileLoading = true;
    try {
      profileSourceOfTruth = await api.get<TenantSourceOfTruthResponse>(`/tenants/profiles/${profileId}/source-of-truth/`);
    } catch (error) {
      profileSourceOfTruth = null;
      toast.error("Profile load failed", parseApiMessage(error, "Could not load the tenant source-of-truth view."));
    } finally {
      profileLoading = false;
    }
  }

  async function openProfileModal(profile: TenantRegistryRow) {
    showMasterListDrawer = false;
    showDrawer = false;
    showOnboardingModal = false;
    showExportMenu = false;
    closeProfileRecordDrawer();
    selectedProfileId = profile.id;
    selectedProfileSummary = profile;
    profileSourceOfTruth = null;
    activeProfileTab = "identity";
    showProfileModal = true;
    await fetchProfileSourceOfTruth(profile.id);
  }

  async function refreshProfileSourceOfTruth() {
    if (!selectedProfileId) return;
    await fetchProfileSourceOfTruth(selectedProfileId);
  }

  async function fetchRegistry() {
    if (!loading) refreshing = true;

    const [overviewResult, lookupsResult, profilesResult] = await Promise.allSettled([
      api.get<TenantRegistryOverview>("/tenants/registry/overview/"),
      api.get<TenantRegistryLookups>("/tenants/registry/lookups/"),
      fetchAllRegistryProfiles(),
    ]);

    const failedSections: string[] = [];

    if (overviewResult.status === "fulfilled") {
      overview = overviewResult.value;
    } else {
      overview = null;
      failedSections.push("registry overview");
    }

    if (lookupsResult.status === "fulfilled") {
      lookups = lookupsResult.value;
    } else {
      lookups = null;
      failedSections.push("registry lookups");
    }

    if (profilesResult.status === "fulfilled") {
      profiles = profilesResult.value;
      if (selectedProfileId !== null) {
        selectedProfileSummary = profilesResult.value.find((profile) => profile.id === selectedProfileId) ?? selectedProfileSummary;
      }
    } else {
      profiles = [];
      failedSections.push("tenant profiles");
    }

    if (failedSections.length === 1) {
      toast.error("Load failed", `Could not load ${failedSections[0]}.`);
    } else if (failedSections.length > 1) {
      toast.error("Load failed", "Could not load the tenant registry.");
    }

    loading = false;
    refreshing = false;
  }

  function openEditDrawer(profile: TenantRegistryRow) {
    showMasterListDrawer = false;
    showOnboardingModal = false;
    showExportMenu = false;
    editingTenantId = profile.id;
    form = {
      customer: profile.customer ? String(profile.customer) : "",
      contact_account: profile.contact_account ? String(profile.contact_account) : "",
      primary_user: profile.primary_user ? String(profile.primary_user) : "",
      property: deriveEditPropertyId(profile),
      unit: profile.unit ? String(profile.unit) : "",
      facility: profile.facility ? String(profile.facility) : "",
      facility_space: profile.facility_space ? String(profile.facility_space) : "",
      tenant_type: profile.tenant_type,
      status: profile.status,
      display_name: profile.display_name || profile.resolved_display_name,
      lease_start_date: profile.lease_start_date ?? "",
      lease_end_date: profile.lease_end_date ?? "",
      move_in_date: profile.move_in_date ?? "",
      move_out_date: profile.move_out_date ?? "",
      occupant_count: String(profile.occupant_count ?? 1),
      notes: profile.notes ?? "",
    };
    showDrawer = true;
  }

  function closeDrawer() {
    showDrawer = false;
    editingTenantId = null;
    showExportMenu = false;
    saving = false;
    resetForm();
  }

  function buildPayload() {
    return {
      customer: form.customer ? Number(form.customer) : null,
      contact_account: form.contact_account ? Number(form.contact_account) : null,
      primary_user: form.primary_user ? Number(form.primary_user) : null,
      property: form.property ? Number(form.property) : null,
      unit: form.unit ? Number(form.unit) : null,
      facility: form.facility ? Number(form.facility) : null,
      facility_space: form.facility_space ? Number(form.facility_space) : null,
      tenant_type: form.tenant_type,
      status: form.status,
      display_name: form.display_name.trim(),
      lease_start_date: form.lease_start_date || null,
      lease_end_date: form.lease_end_date || null,
      move_in_date: form.move_in_date || null,
      move_out_date: form.move_out_date || null,
      occupant_count: Math.max(1, Number(form.occupant_count || "1")),
      notes: form.notes.trim(),
    };
  }

  async function submitForm() {
    saving = true;
    try {
      const payload = buildPayload();
      const editedProfileId = editingTenantId;
      let successTitle = "Tenant updated";
      let successMessage = "The tenant registry record has been updated.";
      if (editingTenantId) {
        await api.patch<TenantRegistryRow>(`/tenants/profiles/${editingTenantId}/`, payload);
      } else {
        await api.post<TenantRegistryRow>("/tenants/profiles/", payload);
        successTitle = "Tenant created";
        successMessage = "The new tenant registry record has been created and added to the registry.";
        if (payload.lease_start_date && payload.lease_end_date) {
          successMessage = "The new tenant registry record has been created, and a draft lease has been added to Lease Management.";
        }
      }
      if (editingTenantId) {
        closeDrawer();
      } else {
        closeOnboardingModal();
      }
      await fetchRegistry();
      toast.success(successTitle, successMessage);
      if (editedProfileId && selectedProfileId === editedProfileId) {
        await refreshProfileSourceOfTruth();
      }
    } catch (error) {
      toast.error("Save failed", parseApiMessage(error, "Could not save the tenant registry record."));
    } finally {
      saving = false;
    }
  }

  async function submitProfileRecordDrawer() {
    if (!selectedProfileId) {
      toast.info("Select tenant", "Open a tenant profile before adding source-of-truth records.");
      return;
    }

    let endpoint = "";
    let payload: Record<string, unknown> = {};
    let successTitle = "Record saved";
    let successMessage = "The tenant source-of-truth record has been saved.";

    if (profileDrawerMode === "identity") {
      endpoint = `/tenants/profiles/${selectedProfileId}/identity-documents/`;
      payload = {
        document_type: identityDocumentForm.document_type,
        document_number: identityDocumentForm.document_number.trim(),
        holder_name: identityDocumentForm.holder_name.trim(),
        issuing_country: identityDocumentForm.issuing_country.trim(),
        issue_date: identityDocumentForm.issue_date || null,
        expiry_date: identityDocumentForm.expiry_date || null,
        scan_on_file: identityDocumentForm.scan_on_file,
        scan_reference: identityDocumentForm.scan_reference.trim(),
        is_verified: identityDocumentForm.is_verified,
        notes: identityDocumentForm.notes.trim(),
      };
      successTitle = "Identity document added";
      successMessage = "The tenant identity document has been added to the registry profile.";
    } else if (profileDrawerMode === "contact") {
      endpoint = `/tenants/profiles/${selectedProfileId}/relationship-contacts/`;
      payload = {
        contact_role: relationshipContactForm.contact_role,
        full_name: relationshipContactForm.full_name.trim(),
        relationship: relationshipContactForm.relationship.trim(),
        phone: relationshipContactForm.phone.trim(),
        email: relationshipContactForm.email.trim(),
        address: relationshipContactForm.address.trim(),
        is_primary: relationshipContactForm.is_primary,
        notes: relationshipContactForm.notes.trim(),
      };
      successTitle = "Contact added";
      successMessage = "The relationship contact is now attached to this tenant profile.";
    } else if (profileDrawerMode === "inventory") {
      endpoint = `/tenants/profiles/${selectedProfileId}/inventory-items/`;
      payload = {
        item_name: inventoryItemForm.item_name.trim(),
        quantity: Math.max(1, Number(inventoryItemForm.quantity || "1")),
        condition: inventoryItemForm.condition,
        status: inventoryItemForm.status,
        notes: inventoryItemForm.notes.trim(),
      };
      successTitle = "Inventory item added";
      successMessage = "The handover checklist item has been added to the tenant profile.";
    } else {
      endpoint = `/tenants/profiles/${selectedProfileId}/incident-records/`;
      payload = {
        incident_type: incidentRecordForm.incident_type,
        severity: incidentRecordForm.severity,
        status: incidentRecordForm.status,
        title: incidentRecordForm.title.trim(),
        description: incidentRecordForm.description.trim(),
        occurred_at: incidentRecordForm.occurred_at || todayIso(),
        resolved_at: incidentRecordForm.resolved_at || null,
        notes: incidentRecordForm.notes.trim(),
      };
      successTitle = "Incident record added";
      successMessage = "The incident has been added to the tenant profile timeline.";
    }

    savingProfileRecord = true;
    try {
      await api.post(endpoint, payload);
      toast.success(successTitle, successMessage);
      closeProfileRecordDrawer();
      await refreshProfileSourceOfTruth();
    } catch (error) {
      toast.error("Save failed", parseApiMessage(error, "Could not save the tenant profile record."));
    } finally {
      savingProfileRecord = false;
    }
  }

  $effect(() => {
    filteredProfiles();
    resetRegistryViewport();
  });

  $effect(() => {
    if (registryViewport) {
      registryViewportHeight = registryViewport.clientHeight || 760;
    }
  });

  $effect(() => {
    fetchRegistry();
  });
</script>

<div class="space-y-6">
  <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
    <div class="space-y-3">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-600">Tenants</p>
        <h1 class="mt-2 text-2xl font-bold tracking-wide text-slate-800">Tenant Registry</h1>
        <p class="mt-2 max-w-3xl text-sm text-slate-600">
          Core tenant records across customers, contacts, property assignments, lease windows, and occupancy linkage.
        </p>
      </div>

      {#if overview?.generated_at || lookups?.generated_at}
        <p class="text-xs text-slate-500">Last refreshed: {fmtDateTime(overview?.generated_at ?? lookups?.generated_at)}</p>
      {/if}
    </div>

    <div class="flex items-center gap-2 self-start lg:self-auto">
      <button
        type="button"
        onclick={openCreateModal}
        class="inline-flex items-center gap-2 rounded-xl border border-emerald-200/80 bg-[linear-gradient(135deg,rgba(220,252,231,0.98),rgba(236,253,245,0.96))] px-4 py-2.5 text-sm font-semibold text-emerald-900 shadow-[0_16px_36px_-26px_rgba(16,185,129,0.28)] backdrop-blur transition hover:border-emerald-300 hover:shadow-[0_20px_42px_-26px_rgba(16,185,129,0.34)]"
      >
        <svg class="h-4 w-4 text-emerald-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
        Add Tenant
      </button>

      <label class="inline-flex">
        <input bind:this={importInput} type="file" accept=".csv,.xlsx" class="hidden" onchange={handleImportSelection} />
        <button
          type="button"
          onclick={triggerImportPicker}
          disabled={importing}
          class="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-white/70 bg-white/72 text-slate-700 shadow-sm backdrop-blur transition hover:border-slate-300 hover:text-slate-950 disabled:cursor-not-allowed disabled:opacity-60"
          aria-label={importing ? "Importing tenant registry file" : "Import tenant registry CSV or Excel"}
          title={importing ? "Importing tenant registry file" : "Import tenant registry CSV or Excel"}
        >
          <svg class={`h-4 w-4 ${importing ? "animate-pulse" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 16.5v-9m0 0L8.5 11m3.5-3.5 3.5 3.5M4.5 16.5v.75A2.25 2.25 0 0 0 6.75 19.5h10.5a2.25 2.25 0 0 0 2.25-2.25v-.75" />
          </svg>
        </button>
      </label>

      <div class="relative">
        <button
          type="button"
          onclick={() => (showExportMenu = !showExportMenu)}
          disabled={Boolean(exportingFormat)}
          class="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-white/70 bg-white/72 text-slate-700 shadow-sm backdrop-blur transition hover:border-slate-300 hover:text-slate-950 disabled:cursor-not-allowed disabled:opacity-60"
          aria-label={exportingFormat ? `Exporting tenant registry ${exportingFormat}` : "Export tenant registry"}
          title={exportingFormat ? `Exporting tenant registry ${exportingFormat}` : "Export tenant registry"}
        >
          <svg class={`h-4 w-4 ${exportingFormat ? "animate-pulse" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 7.5v9m0 0 3.5-3.5M12 16.5 8.5 13M4.5 7.5v-.75A2.25 2.25 0 0 1 6.75 4.5h10.5a2.25 2.25 0 0 1 2.25 2.25v.75" />
          </svg>
        </button>

        {#if showExportMenu}
          <div class="absolute right-0 top-12 z-20 w-36 rounded-xl border border-slate-200/80 bg-white/96 p-2 shadow-[0_22px_50px_-34px_rgba(15,23,42,0.28)] backdrop-blur">
            <button
              type="button"
              onclick={() => exportRegistry("csv")}
              class="flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm font-medium text-slate-700 transition hover:bg-slate-50"
            >
              <span>CSV</span>
              <span class="text-[11px] uppercase tracking-[0.18em] text-slate-400">File</span>
            </button>
            <button
              type="button"
              onclick={() => exportRegistry("xlsx")}
              class="flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm font-medium text-slate-700 transition hover:bg-slate-50"
            >
              <span>Excel</span>
              <span class="text-[11px] uppercase tracking-[0.18em] text-slate-400">XLSX</span>
            </button>
          </div>
        {/if}
      </div>

      <button
        type="button"
        onclick={fetchRegistry}
        disabled={refreshing}
        class="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-white/70 bg-white/72 text-slate-700 shadow-sm backdrop-blur hover:border-slate-300 hover:text-slate-950 disabled:cursor-not-allowed disabled:opacity-60"
        aria-label={refreshing ? "Refreshing tenant registry" : "Refresh tenant registry"}
        title={refreshing ? "Refreshing tenant registry" : "Refresh tenant registry"}
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

  <section class={`${shellClass} p-5`}>
    <div class="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
      <div class="min-w-0 flex-1">
        <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-sky-700">Registry Header &amp; Global Actions</p>
        <div class="relative mt-3 max-w-4xl">
          <div class="pointer-events-none absolute inset-y-0 left-4 flex items-center text-slate-400">
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-4.35-4.35m1.6-5.15a6.75 6.75 0 1 1-13.5 0 6.75 6.75 0 0 1 13.5 0Z" />
            </svg>
          </div>
          <input
            bind:value={search}
            type="search"
            placeholder="Search by name, phone, unit, or Abuja / Lagos site..."
            class="w-full rounded-[22px] border border-white/80 bg-white/82 py-3 pl-11 pr-24 text-sm text-slate-700 shadow-[0_16px_40px_-34px_rgba(15,23,42,0.28)] backdrop-blur placeholder:text-slate-400 focus:border-sky-200 focus:outline-none"
            onfocus={() => (showingSearchSuggestions = true)}
            onblur={() => window.setTimeout(() => (showingSearchSuggestions = false), 120)}
          />
          <div class="pointer-events-none absolute inset-y-0 right-4 flex items-center">
            <span class="rounded-full border border-sky-100 bg-sky-50 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-sky-700">
              Auto-suggest
            </span>
          </div>

          {#if showingSearchSuggestions && registrySearchSuggestions().length > 0}
            <div class="absolute left-0 right-0 top-[calc(100%+0.65rem)] z-20 overflow-hidden rounded-[22px] border border-slate-200/80 bg-white/96 shadow-[0_28px_70px_-44px_rgba(15,23,42,0.32)] backdrop-blur">
              {#each registrySearchSuggestions() as suggestion}
                <button
                  type="button"
                  onclick={() => selectSearchSuggestion(suggestion)}
                  class="flex w-full items-center justify-between gap-3 border-t border-slate-100/80 px-4 py-3 text-left first:border-t-0 hover:bg-slate-50/80"
                >
                  <div>
                    <p class="text-sm font-semibold text-slate-900">{suggestion.label}</p>
                    <p class="mt-1 text-xs text-slate-500">{suggestion.helper}</p>
                  </div>
                  <span class="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                    {suggestion.kind}
                  </span>
                </button>
              {/each}
            </div>
          {/if}
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-2 xl:max-w-md xl:justify-end">
        <button
          type="button"
          onclick={() => (quickFilter = "all")}
          class={`inline-flex items-center gap-2 rounded-full border px-3.5 py-2 text-xs font-semibold transition ${quickFilterButtonClass("all")}`}
        >
          All
          <span class="text-[11px] text-slate-400">{fmtInt(profiles.length)}</span>
        </button>
        <button
          type="button"
          onclick={() => (quickFilter = quickFilter === "active" ? "all" : "active")}
          class={`inline-flex items-center gap-2 rounded-full border px-3.5 py-2 text-xs font-semibold transition ${quickFilterButtonClass("active")}`}
        >
          Active
          <span class="text-[11px] opacity-70">{fmtInt(quickFilterCount("active"))}</span>
        </button>
        <button
          type="button"
          onclick={() => (quickFilter = quickFilter === "past" ? "all" : "past")}
          class={`inline-flex items-center gap-2 rounded-full border px-3.5 py-2 text-xs font-semibold transition ${quickFilterButtonClass("past")}`}
        >
          Past
          <span class="text-[11px] opacity-70">{fmtInt(quickFilterCount("past"))}</span>
        </button>
        <button
          type="button"
          onclick={() => (quickFilter = quickFilter === "prospective" ? "all" : "prospective")}
          class={`inline-flex items-center gap-2 rounded-full border px-3.5 py-2 text-xs font-semibold transition ${quickFilterButtonClass("prospective")}`}
        >
          Prospective
          <span class="text-[11px] opacity-70">{fmtInt(quickFilterCount("prospective"))}</span>
        </button>
      </div>
    </div>
  </section>

  <section class="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
    <article class={`${shellClass} p-5`}>
      <div class="absolute inset-0 bg-linear-to-br from-sky-100/36 via-white/8 to-cyan-100/24"></div>
      <div class="relative">
        <p class="text-[11px] font-semibold uppercase tracking-[0.22em] text-sky-800">Profiles</p>
        <p class="mt-4 text-2xl font-semibold tracking-tight text-slate-900">{fmtInt(overview?.totals.profiles ?? 0)}</p>
        <p class="mt-2 text-sm text-slate-600">Total tenant master records across the managed portfolio.</p>
      </div>
    </article>

    <article class={`${shellClass} p-5`}>
      <div class="absolute inset-0 bg-linear-to-br from-emerald-100/34 via-white/8 to-teal-100/22"></div>
      <div class="relative">
        <p class="text-[11px] font-semibold uppercase tracking-[0.22em] text-emerald-800">Active</p>
        <p class="mt-4 text-2xl font-semibold tracking-tight text-slate-900">{fmtInt(overview?.totals.active ?? 0)}</p>
        <p class="mt-2 text-sm text-slate-600">Currently occupied or live tenancy records.</p>
      </div>
    </article>

    <article class={`${shellClass} p-5`}>
      <div class="absolute inset-0 bg-linear-to-br from-sky-100/34 via-white/8 to-indigo-100/22"></div>
      <div class="relative">
        <p class="text-[11px] font-semibold uppercase tracking-[0.22em] text-sky-800">Pending Move In</p>
        <p class="mt-4 text-2xl font-semibold tracking-tight text-slate-900">{fmtInt(overview?.totals.pending_move_in ?? 0)}</p>
        <p class="mt-2 text-sm text-slate-600">Pre-occupancy records reserved for onboarding.</p>
      </div>
    </article>

    <article class={`${shellClass} p-5`}>
      <div class="absolute inset-0 bg-linear-to-br from-violet-100/34 via-white/8 to-fuchsia-100/22"></div>
      <div class="relative">
        <p class="text-[11px] font-semibold uppercase tracking-[0.22em] text-violet-800">Expiring 60 Days</p>
        <p class="mt-4 text-2xl font-semibold tracking-tight text-slate-900">{fmtInt(overview?.lease_watch.expiring_next_60_days ?? 0)}</p>
        <p class="mt-2 text-sm text-slate-600">Lease watchlist for near-term renewals or exits.</p>
      </div>
    </article>

    <article class={`${shellClass} p-5`}>
      <div class="absolute inset-0 bg-linear-to-br from-rose-100/34 via-white/8 to-orange-100/22"></div>
      <div class="relative">
        <p class="text-[11px] font-semibold uppercase tracking-[0.22em] text-rose-800">Missing Contact</p>
        <p class="mt-4 text-2xl font-semibold tracking-tight text-slate-900">{fmtInt(overview?.hygiene.missing_contact_channels ?? 0)}</p>
        <p class="mt-2 text-sm text-slate-600">Records without a reachable email or phone channel.</p>
      </div>
    </article>

    <article class={`${shellClass} p-5`}>
      <div class="absolute inset-0 bg-linear-to-br from-amber-100/34 via-white/8 to-yellow-100/22"></div>
      <div class="relative">
        <p class="text-[11px] font-semibold uppercase tracking-[0.22em] text-amber-800">Unassigned</p>
        <p class="mt-4 text-2xl font-semibold tracking-tight text-slate-900">{fmtInt(overview?.allocation.unassigned_profiles ?? 0)}</p>
        <p class="mt-2 text-sm text-slate-600">Profiles that still need a unit or mapped facility space.</p>
      </div>
    </article>
  </section>

  <section class="grid gap-5 xl:grid-cols-[minmax(0,1.45fr)_360px]">
    <article class={`${shellClass} p-5`}>
      <div class="rounded-[24px] border border-white/75 bg-white/72 p-5 shadow-[0_18px_44px_-34px_rgba(15,23,42,0.2)] backdrop-blur-xl">
        <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div class="min-w-0 flex-1">
            <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-sky-700">Tenant Registry (Master Data)</p>
            <h2 class="mt-2 text-sm font-bold tracking-wide text-neutral-800 uppercase">Master Ledger Access</h2>
            <p class="mt-2 max-w-3xl text-sm text-slate-600">
              The dense registry table now opens in a drawer so the page can stay focused on onboarding, hygiene, and portfolio-level control.
            </p>
          </div>
          <div class="flex items-center gap-2">
            <button
              type="button"
              onclick={openMasterListDrawer}
              class="inline-flex items-center gap-2 rounded-full border border-sky-200 bg-sky-50 px-4 py-2.5 text-sm font-semibold text-sky-700 transition hover:border-sky-300"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5m-16.5 5.25h16.5m-16.5 5.25h10.5" />
              </svg>
              Open Master List
            </button>
          </div>
        </div>

        <div class="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div class="rounded-2xl border border-slate-200/80 bg-white/88 p-4">
            <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Matched Rows</p>
            <p class="mt-2 text-lg font-semibold text-slate-950">{fmtInt(filteredProfiles().length)}</p>
            <p class="mt-1 text-xs text-slate-500">Current filters and search state ready for the drawer ledger.</p>
          </div>
          <div class="rounded-2xl border border-slate-200/80 bg-white/88 p-4">
            <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Quick Filter</p>
            <p class="mt-2 text-lg font-semibold text-slate-950">{quickFilterLabel(quickFilter)}</p>
            <p class="mt-1 text-xs text-slate-500">Portfolio scope stays synced with the master list drawer.</p>
          </div>
          <div class="rounded-2xl border border-slate-200/80 bg-white/88 p-4">
            <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Advanced Filters</p>
            <p class="mt-2 text-lg font-semibold text-slate-950">{advancedFilterCount() > 0 ? fmtInt(advancedFilterCount()) : "None"}</p>
            <p class="mt-1 text-xs text-slate-500">
              {advancedFilterCount() > 0 ? advancedFilterSummaries().slice(0, 1)[0] : "No deep filters applied right now."}
            </p>
          </div>
          <div class="rounded-2xl border border-slate-200/80 bg-white/88 p-4">
            <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Search State</p>
            <p class="mt-2 truncate text-lg font-semibold text-slate-950">{search.trim() || "Command Bar Ready"}</p>
            <p class="mt-1 text-xs text-slate-500">Global search terms also drive the drawer table and suggestions.</p>
          </div>
        </div>
      </div>

      <section class="mt-5 rounded-[24px] border border-white/75 bg-white/72 p-5 shadow-[0_18px_44px_-34px_rgba(15,23,42,0.2)] backdrop-blur-xl">
        <div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-emerald-700">Tenant Onboarding Workflow</p>
            <h3 class="mt-2 text-sm font-bold tracking-wide text-neutral-800 uppercase">Applicant to Registered</h3>
            <p class="mt-2 max-w-3xl text-sm text-slate-600">
              Administrative path from intake to full registration, showing where tenants are waiting on diligence, mapping, or lease setup before they become fully operational records.
            </p>
          </div>

          <button
            type="button"
            onclick={openCreateModal}
            class="inline-flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-sm font-semibold text-emerald-700 transition hover:border-emerald-300"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            Start Onboarding
          </button>
        </div>

        <div class="mt-5 grid gap-4 xl:grid-cols-5">
          {#each onboardingStageMetrics() as stage, stageIndex}
            <article class={`relative rounded-2xl border px-4 py-4 ${stage.className}`}>
              <div class="flex items-start justify-between gap-3">
                <span class={`inline-flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold ${stage.stepClass}`}>
                  {stageIndex + 1}
                </span>
                <span class="text-[11px] font-semibold uppercase tracking-[0.18em] opacity-70">
                  {fmtInt(stage.count)}
                </span>
              </div>
              <p class="mt-4 text-sm font-semibold">{stage.label}</p>
              <p class="mt-2 text-sm leading-6 opacity-80">{stage.description}</p>

              {#if stageIndex < onboardingStageMetrics().length - 1}
                <div class="pointer-events-none absolute -right-2 top-1/2 hidden h-px w-4 -translate-y-1/2 bg-slate-300/70 xl:block"></div>
              {/if}
            </article>
          {/each}
        </div>

        <div class="mt-5 grid gap-3 md:grid-cols-3">
          <div class="rounded-2xl border border-white/80 bg-white/85 px-4 py-4 shadow-sm">
            <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Pending Pipeline</p>
            <p class="mt-3 text-xl font-semibold text-slate-900">{fmtInt(onboardingPendingCount())}</p>
            <p class="mt-1 text-sm text-slate-600">Tenant records still moving through applicant, diligence, allocation, or lease setup.</p>
          </div>
          <div class="rounded-2xl border border-white/80 bg-white/85 px-4 py-4 shadow-sm">
            <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Ready / Registered</p>
            <p class="mt-3 text-xl font-semibold text-emerald-700">{fmtInt(onboardingReadyCount())}</p>
            <p class="mt-1 text-sm text-slate-600">Records that are structured enough for portfolio monitoring, billing sync, and profile operations.</p>
          </div>
          <div class="rounded-2xl border border-white/80 bg-white/85 px-4 py-4 shadow-sm">
            <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Archived History</p>
            <p class="mt-3 text-xl font-semibold text-slate-900">{fmtInt(onboardingArchivedCount())}</p>
            <p class="mt-1 text-sm text-slate-600">Moved-out or inactive tenant records retained for compliance and historical lookup.</p>
          </div>
        </div>
      </section>
    </article>

    <div class="space-y-5">
      <article class={`${shellClass} p-5`}>
        <div class="absolute inset-0 bg-linear-to-br from-rose-100/28 via-white/8 to-orange-100/16"></div>
        <div class="relative">
          <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-rose-700">Registry Hygiene</p>
          <div class="mt-4 space-y-3">
            <div class="flex items-center justify-between rounded-[22px] border border-white/75 bg-white/82 px-4 py-3 shadow-sm">
              <div>
                <p class="text-sm font-semibold text-slate-950">Missing customer link</p>
                <p class="mt-1 text-xs text-slate-500">Finance and receivables sync is incomplete.</p>
              </div>
              <span class={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${hygieneBadgeClass(overview?.hygiene.missing_customer_links ?? 0)}`}>
                {fmtInt(overview?.hygiene.missing_customer_links ?? 0)}
              </span>
            </div>

            <div class="flex items-center justify-between rounded-[22px] border border-white/75 bg-white/82 px-4 py-3 shadow-sm">
              <div>
                <p class="text-sm font-semibold text-slate-950">Missing contact channel</p>
                <p class="mt-1 text-xs text-slate-500">No email or phone for reminders and notices.</p>
              </div>
              <span class={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${hygieneBadgeClass(overview?.hygiene.missing_contact_channels ?? 0)}`}>
                {fmtInt(overview?.hygiene.missing_contact_channels ?? 0)}
              </span>
            </div>

            <div class="flex items-center justify-between rounded-[22px] border border-white/75 bg-white/82 px-4 py-3 shadow-sm">
              <div>
                <p class="text-sm font-semibold text-slate-950">Missing location mapping</p>
                <p class="mt-1 text-xs text-slate-500">Property, unit, facility, or space still needs linking.</p>
              </div>
              <span class={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${hygieneBadgeClass(overview?.hygiene.missing_location_mapping ?? 0)}`}>
                {fmtInt(overview?.hygiene.missing_location_mapping ?? 0)}
              </span>
            </div>
          </div>
        </div>
      </article>

      <article class={`${shellClass} p-5`}>
        <div class="absolute inset-0 bg-linear-to-br from-violet-100/28 via-white/8 to-fuchsia-100/16"></div>
        <div class="relative">
          <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-violet-700">Lease Watch</p>
          <div class="mt-4 space-y-3">
            <div class="rounded-[22px] border border-white/75 bg-white/82 px-4 py-3 shadow-sm">
              <p class="text-sm font-semibold text-slate-950">Expiring in 60 days</p>
              <p class="mt-2 text-2xl font-semibold tracking-tight text-slate-950">{fmtInt(overview?.lease_watch.expiring_next_60_days ?? 0)}</p>
            </div>
            <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
              <div class="rounded-[22px] border border-white/75 bg-white/82 px-4 py-3 shadow-sm">
                <p class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Move-ins next 30 days</p>
                <p class="mt-2 text-lg font-semibold text-slate-950">{fmtInt(overview?.lease_watch.move_ins_next_30_days ?? 0)}</p>
              </div>
              <div class="rounded-[22px] border border-white/75 bg-white/82 px-4 py-3 shadow-sm">
                <p class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Recent move-outs</p>
                <p class="mt-2 text-lg font-semibold text-slate-950">{fmtInt(overview?.lease_watch.recent_move_outs ?? 0)}</p>
              </div>
            </div>
          </div>
        </div>
      </article>

      <article class={`${shellClass} p-5`}>
        <div class="absolute inset-0 bg-linear-to-br from-emerald-100/28 via-white/8 to-teal-100/16"></div>
        <div class="relative">
          <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-emerald-700">Allocation Coverage</p>
          <div class="mt-4 space-y-3">
            <div class="rounded-[22px] border border-white/75 bg-white/82 px-4 py-3 shadow-sm">
              <div class="flex items-center justify-between">
                <span class="text-sm font-semibold text-slate-950">Assigned units</span>
                <span class="text-sm font-semibold text-slate-700">{fmtInt(overview?.allocation.assigned_units ?? 0)}</span>
              </div>
              <div class="mt-3 h-2 overflow-hidden rounded-full bg-slate-200/70">
                <div
                  class="h-full rounded-full bg-linear-to-r from-emerald-500 to-teal-400"
                  style={`width: ${Math.min(100, ((overview?.allocation.assigned_units ?? 0) / Math.max(overview?.totals.profiles ?? 1, 1)) * 100)}%`}
                ></div>
              </div>
            </div>

            <div class="rounded-[22px] border border-white/75 bg-white/82 px-4 py-3 shadow-sm">
              <div class="flex items-center justify-between">
                <span class="text-sm font-semibold text-slate-950">Assigned spaces</span>
                <span class="text-sm font-semibold text-slate-700">{fmtInt(overview?.allocation.assigned_spaces ?? 0)}</span>
              </div>
              <div class="mt-3 h-2 overflow-hidden rounded-full bg-slate-200/70">
                <div
                  class="h-full rounded-full bg-linear-to-r from-sky-500 to-cyan-400"
                  style={`width: ${Math.min(100, ((overview?.allocation.assigned_spaces ?? 0) / Math.max(overview?.totals.profiles ?? 1, 1)) * 100)}%`}
                ></div>
              </div>
            </div>

            <div class="rounded-[22px] border border-white/75 bg-white/82 px-4 py-3 shadow-sm">
              <p class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Tenant type split</p>
              <div class="mt-3 space-y-2">
                {#each overview?.tenant_types ?? [] as typeRow}
                  <div>
                    <div class="flex items-center justify-between text-xs font-medium text-slate-600">
                      <span>{typeRow.label}</span>
                      <span>{fmtInt(typeRow.count)}</span>
                    </div>
                    <div class="mt-1 h-2 overflow-hidden rounded-full bg-slate-200/70">
                      <div
                        class={`h-full rounded-full ${typeRow.key === "corporate" ? "bg-linear-to-r from-violet-500 to-fuchsia-400" : "bg-linear-to-r from-amber-500 to-orange-400"}`}
                        style={`width: ${Math.min(100, (typeRow.count / Math.max(overview?.totals.profiles ?? 1, 1)) * 100)}%`}
                      ></div>
                    </div>
                  </div>
                {/each}
              </div>
            </div>
          </div>
        </div>
      </article>
    </div>
  </section>
</div>

{#if showProfileModal}
  {@const profileRecord = currentProfileRecord()}
  {@const leaseState = profileRecord ? registryLeaseState(profileRecord) : null}
  <div class="fixed inset-0 z-50">
    <button
      type="button"
      class="absolute inset-0 bg-slate-950/42 backdrop-blur-[3px]"
      onclick={closeProfileModal}
      aria-label="Close tenant source of truth profile"
    ></button>

    <div class="relative z-10 flex min-h-full items-center justify-center px-4 py-6 sm:px-6">
      <section class="max-h-[94vh] w-full max-w-6xl overflow-hidden rounded-xl border border-white/75 bg-white shadow-[0_42px_120px_-58px_rgba(15,23,42,0.42)]">
        <div class="border-b border-slate-200/80 px-6 py-5">
          <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div class="space-y-3">
              <div>
                <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-sky-700">Tenant Source of Truth</p>
                <h2 class="mt-2 text-lg font-bold tracking-wide text-slate-800">
                  {profileRecord?.resolved_display_name || "Tenant profile"}
                </h2>
                <p class="mt-1 text-sm text-slate-600">
                  {profileRecord ? `${registryTenantCode(profileRecord)} · ${registryPropertyLabel(profileRecord)} · ${registryAssignedUnitLabel(profileRecord)}` : "Full registry profile for identity, ledger, inventory, and incident history."}
                </p>
              </div>

              <div class="flex flex-wrap items-center gap-2">
                {#if profileRecord}
                  <span class={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${statusBadgeClass(profileRecord.status)}`}>
                    {profileRecord.status_display}
                  </span>
                  <span class={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${tenantTypeBadgeClass(profileRecord.tenant_type)}`}>
                    {profileRecord.tenant_type_display}
                  </span>
                {/if}
                {#if leaseState}
                  <span class={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${leaseState.className}`}>
                    {leaseState.label}
                  </span>
                {/if}
                {#if profileSourceOfTruth}
                  <span class={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${paymentStateBadgeClass(profileSourceOfTruth.financial.current_balance)}`}>
                    {Number(profileSourceOfTruth.financial.current_balance) > 0 ? "Balance Outstanding" : "Ledger Clear"}
                  </span>
                {/if}
              </div>
            </div>

            <div class="flex items-center gap-2 self-start">
              {#if profileRecord}
                <button
                  type="button"
                  onclick={() => openEditDrawer(profileRecord)}
                  class="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:border-slate-300 hover:text-slate-950"
                >
                  <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8" aria-hidden="true">
                    <path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.687a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Z" />
                  </svg>
                  Edit Profile
                </button>
              {/if}
              <button
                type="button"
                onclick={refreshProfileSourceOfTruth}
                disabled={profileLoading}
                class="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200/80 bg-white text-slate-700 shadow-sm transition hover:border-slate-300 hover:text-slate-950 disabled:cursor-not-allowed disabled:opacity-60"
                aria-label={profileLoading ? "Refreshing tenant profile" : "Refresh tenant profile"}
                title={profileLoading ? "Refreshing tenant profile" : "Refresh tenant profile"}
              >
                <svg class={`h-4 w-4 ${profileLoading ? "animate-spin" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992V4.356m-1.636 14.288A9 9 0 1 1 21 12.003" />
                </svg>
              </button>
              <button
                type="button"
                onclick={closeProfileModal}
                class="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200/80 bg-white text-slate-700 shadow-sm hover:text-slate-950"
                aria-label="Close tenant source of truth profile"
              >
                <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8" aria-hidden="true">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          <div class="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <div class="rounded-2xl border border-slate-200/80 bg-slate-50/80 p-4">
              <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Location</p>
              <p class="mt-2 text-sm font-semibold text-slate-950">{profileRecord ? registryAssignedUnitLabel(profileRecord) : "--"}</p>
              <p class="mt-1 text-sm text-slate-600">{profileRecord ? registryPropertyLabel(profileRecord) : "No property linked"}</p>
            </div>
            <div class="rounded-2xl border border-slate-200/80 bg-slate-50/80 p-4">
              <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Lease Window</p>
              <p class="mt-2 text-sm font-semibold text-slate-950">{profileRecord ? `${fmtDate(profileRecord.lease_start_date)} - ${fmtDate(profileRecord.lease_end_date)}` : "--"}</p>
              <p class="mt-1 text-sm text-slate-600">{leaseState?.meta || "Lease dates unavailable"}</p>
            </div>
            <div class="rounded-2xl border border-slate-200/80 bg-slate-50/80 p-4">
              <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Current Balance</p>
              <p class="mt-2 text-sm font-semibold text-slate-950">{fmtMoney(profileSourceOfTruth?.financial.current_balance)}</p>
              <p class="mt-1 text-sm text-slate-600">Overdue {fmtMoney(profileSourceOfTruth?.financial.overdue_balance)}</p>
            </div>
            <div class="rounded-2xl border border-slate-200/80 bg-slate-50/80 p-4">
              <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Registry Stamp</p>
              <p class="mt-2 text-sm font-semibold text-slate-950">{fmtDateTime(profileSourceOfTruth?.generated_at ?? profileRecord?.updated_at)}</p>
              <p class="mt-1 text-sm text-slate-600">{profileRecord ? `Occupants ${fmtInt(profileRecord.occupant_count)}` : "Awaiting tenant payload"}</p>
            </div>
          </div>

          <div class="mt-5 flex flex-wrap gap-2">
            {#each profileTabs as tab}
              <button
                type="button"
                onclick={() => (activeProfileTab = tab.value)}
                class={`inline-flex items-center rounded-full border px-4 py-2 text-sm font-semibold transition ${profileTabClass(tab.value)}`}
              >
                {tab.label}
              </button>
            {/each}
          </div>
        </div>

        <div class="max-h-[68vh] overflow-y-auto px-6 py-6">
          {#if profileLoading && !profileSourceOfTruth}
            <div class="flex min-h-88 items-center justify-center rounded-[28px] border border-dashed border-slate-200 bg-slate-50/70 px-6 py-16 text-center">
              <div>
                <div class="mx-auto h-9 w-9 animate-spin rounded-full border-2 border-slate-200 border-t-sky-500"></div>
                <p class="mt-4 text-sm font-semibold text-slate-900">Loading tenant source of truth...</p>
                <p class="mt-1 text-sm text-slate-500">Pulling identity, ledger, inventory, and incident history from the registry.</p>
              </div>
            </div>
          {:else if !profileSourceOfTruth}
            <div class="rounded-[28px] border border-dashed border-slate-200 bg-slate-50/70 px-6 py-16 text-center">
              <p class="text-sm font-semibold text-slate-900">Tenant profile unavailable</p>
              <p class="mt-2 text-sm text-slate-500">The registry could not load this tenant profile right now. Try refreshing the profile view.</p>
            </div>
          {:else if activeProfileTab === "identity"}
            <div class="space-y-5">
              <section class="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_16px_40px_-30px_rgba(15,23,42,0.12)]">
                <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-sky-700">Identity Tab</p>
                    <h3 class="mt-2 text-sm font-bold tracking-wide text-neutral-800 uppercase">Scanned IDs &amp; Personal Safeguards</h3>
                    <p class="mt-2 text-sm text-slate-600">Track government IDs, next of kin, and emergency contacts for onboarding and incident escalation.</p>
                  </div>
                  <div class="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onclick={() => openProfileRecordDrawer("identity")}
                      class="inline-flex items-center rounded-full border border-sky-200 bg-sky-50 px-4 py-2 text-sm font-semibold text-sky-700 transition hover:border-sky-300"
                    >
                      Add ID
                    </button>
                    <button
                      type="button"
                      onclick={() => openProfileRecordDrawer("contact")}
                      class="inline-flex items-center rounded-full border border-violet-200 bg-violet-50 px-4 py-2 text-sm font-semibold text-violet-700 transition hover:border-violet-300"
                    >
                      Add Contact
                    </button>
                  </div>
                </div>

                <div class="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
                  <div class="space-y-3">
                    <div class="flex items-center justify-between">
                      <p class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Identity Documents</p>
                      <span class="text-xs text-slate-500">{fmtInt(profileSourceOfTruth.identity.documents.length)} on file</span>
                    </div>
                    {#if profileSourceOfTruth.identity.documents.length === 0}
                      <div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50/70 px-5 py-10 text-center text-sm text-slate-500">
                        No identity documents recorded yet.
                      </div>
                    {:else}
                      {#each profileSourceOfTruth.identity.documents as document}
                        <article class="rounded-2xl border border-slate-200/80 bg-slate-50/70 p-4">
                          <div class="flex flex-wrap items-start justify-between gap-3">
                            <div>
                              <div class="flex flex-wrap items-center gap-2">
                                <span class="inline-flex items-center rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-600">
                                  {document.document_type_display}
                                </span>
                                <span class={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold ${documentStatusBadgeClass(document)}`}>
                                  {document.is_verified ? "Verified" : document.scan_on_file ? "Scan on File" : "Pending Scan"}
                                </span>
                              </div>
                              <p class="mt-3 text-sm font-semibold text-slate-950">{document.document_number}</p>
                              <p class="mt-1 text-sm text-slate-600">{document.holder_name || profileSourceOfTruth.tenant.resolved_display_name}</p>
                            </div>
                            <div class="text-right text-xs text-slate-500">
                              <p>Issued {fmtDate(document.issue_date)}</p>
                              <p class="mt-1">Expires {fmtDate(document.expiry_date)}</p>
                            </div>
                          </div>
                          <div class="mt-4 grid gap-3 text-sm text-slate-600 sm:grid-cols-2">
                            <p><span class="font-semibold text-slate-900">Country:</span> {document.issuing_country || "--"}</p>
                            <p><span class="font-semibold text-slate-900">Scan Ref:</span> {document.scan_reference || "--"}</p>
                          </div>
                          {#if document.notes}
                            <p class="mt-3 text-sm text-slate-600">{document.notes}</p>
                          {/if}
                        </article>
                      {/each}
                    {/if}
                  </div>

                  <div class="space-y-4">
                    <section class="rounded-2xl border border-slate-200/80 bg-slate-50/70 p-4">
                      <div class="flex items-center justify-between">
                        <p class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Next of Kin</p>
                        <span class="text-xs text-slate-500">{fmtInt(profileSourceOfTruth.identity.next_of_kin.length)}</span>
                      </div>
                      <div class="mt-3 space-y-3">
                        {#if profileSourceOfTruth.identity.next_of_kin.length === 0}
                          <p class="rounded-2xl border border-dashed border-slate-200 bg-white px-4 py-6 text-sm text-slate-500">No next-of-kin records added.</p>
                        {:else}
                          {#each profileSourceOfTruth.identity.next_of_kin as contact}
                            <div class="rounded-2xl border border-white/80 bg-white px-4 py-3 shadow-sm">
                              <div class="flex items-start justify-between gap-3">
                                <div>
                                  <p class="text-sm font-semibold text-slate-950">{contact.full_name}</p>
                                  <p class="mt-1 text-sm text-slate-600">{contact.relationship}</p>
                                </div>
                                <span class={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold ${relationshipRoleBadgeClass(contact.contact_role)}`}>
                                  {contact.is_primary ? "Primary" : "Linked"}
                                </span>
                              </div>
                              <div class="mt-3 space-y-1 text-sm text-slate-600">
                                <p>{contact.phone || "--"}</p>
                                <p>{contact.email || "--"}</p>
                                {#if contact.address}
                                  <p>{contact.address}</p>
                                {/if}
                              </div>
                            </div>
                          {/each}
                        {/if}
                      </div>
                    </section>

                    <section class="rounded-2xl border border-slate-200/80 bg-slate-50/70 p-4">
                      <div class="flex items-center justify-between">
                        <p class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Emergency Contacts</p>
                        <span class="text-xs text-slate-500">{fmtInt(profileSourceOfTruth.identity.emergency_contacts.length)}</span>
                      </div>
                      <div class="mt-3 space-y-3">
                        {#if profileSourceOfTruth.identity.emergency_contacts.length === 0}
                          <p class="rounded-2xl border border-dashed border-slate-200 bg-white px-4 py-6 text-sm text-slate-500">No emergency contacts recorded.</p>
                        {:else}
                          {#each profileSourceOfTruth.identity.emergency_contacts as contact}
                            <div class="rounded-2xl border border-white/80 bg-white px-4 py-3 shadow-sm">
                              <div class="flex items-start justify-between gap-3">
                                <div>
                                  <p class="text-sm font-semibold text-slate-950">{contact.full_name}</p>
                                  <p class="mt-1 text-sm text-slate-600">{contact.relationship}</p>
                                </div>
                                <span class={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold ${relationshipRoleBadgeClass(contact.contact_role)}`}>
                                  {contact.contact_role_display}
                                </span>
                              </div>
                              <div class="mt-3 space-y-1 text-sm text-slate-600">
                                <p>{contact.phone || "--"}</p>
                                <p>{contact.email || "--"}</p>
                                {#if contact.notes}
                                  <p>{contact.notes}</p>
                                {/if}
                              </div>
                            </div>
                          {/each}
                        {/if}
                      </div>
                    </section>
                  </div>
                </div>
              </section>
            </div>
          {:else if activeProfileTab === "financial"}
            <div class="space-y-5">
              <section class="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_16px_40px_-30px_rgba(15,23,42,0.12)]">
                <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-emerald-700">Financial Tab</p>
                    <h3 class="mt-2 text-sm font-bold tracking-wide text-neutral-800 uppercase">Tenant Mini-Ledger</h3>
                    <p class="mt-2 text-sm text-slate-600">Every invoice ever raised against this tenant, with payment coverage and outstanding balance history.</p>
                  </div>
                  <span class={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${paymentStateBadgeClass(profileSourceOfTruth.financial.current_balance)}`}>
                    {Number(profileSourceOfTruth.financial.current_balance) > 0 ? "Action Required" : "Debt Free"}
                  </span>
                </div>

                <div class="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                  <div class="rounded-2xl border border-slate-200/80 bg-slate-50/70 p-4">
                    <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Invoices</p>
                    <p class="mt-3 text-xl font-semibold text-slate-950">{fmtInt(profileSourceOfTruth.financial.summary.invoice_count)}</p>
                    <p class="mt-1 text-sm text-slate-600">All billed records on this tenant ledger.</p>
                  </div>
                  <div class="rounded-2xl border border-slate-200/80 bg-slate-50/70 p-4">
                    <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Billed Total</p>
                    <p class="mt-3 text-xl font-semibold text-emerald-700">{fmtMoney(profileSourceOfTruth.financial.summary.billed_total)}</p>
                    <p class="mt-1 text-sm text-slate-600">Gross invoices issued across the tenant record.</p>
                  </div>
                  <div class="rounded-2xl border border-slate-200/80 bg-slate-50/70 p-4">
                    <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Outstanding</p>
                    <p class="mt-3 text-xl font-semibold text-slate-950">{fmtMoney(profileSourceOfTruth.financial.summary.outstanding_total)}</p>
                    <p class="mt-1 text-sm text-slate-600">Current unpaid balance still sitting in flight.</p>
                  </div>
                  <div class="rounded-2xl border border-slate-200/80 bg-slate-50/70 p-4">
                    <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Overdue</p>
                    <p class="mt-3 text-xl font-semibold text-rose-700">{fmtMoney(profileSourceOfTruth.financial.summary.overdue_total)}</p>
                    <p class="mt-1 text-sm text-slate-600">Receivables already past due for recovery.</p>
                  </div>
                </div>

                <div class="mt-5 space-y-4">
                  {#if profileSourceOfTruth.financial.ledger.length === 0}
                    <div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50/70 px-5 py-10 text-center text-sm text-slate-500">
                      No invoice history is attached to this tenant yet.
                    </div>
                  {:else}
                    {#each profileSourceOfTruth.financial.ledger as invoice}
                      <article class="rounded-2xl border border-slate-200/80 bg-slate-50/70 p-4">
                        <div class="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                          <div>
                            <div class="flex flex-wrap items-center gap-2">
                              <p class="text-sm font-semibold text-slate-950">{invoice.invoice_number || `Invoice #${invoice.id}`}</p>
                              <span class={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold ${financialStatusBadgeClass(invoice.status)}`}>
                                {invoice.status_display}
                              </span>
                            </div>
                            <p class="mt-2 text-sm text-slate-600">Issued {fmtDate(invoice.issue_date)} · Due {fmtDate(invoice.due_date)}</p>
                            {#if invoice.notes}
                              <p class="mt-2 text-sm text-slate-600">{invoice.notes}</p>
                            {/if}
                          </div>
                          <div class="grid gap-2 text-sm text-slate-600 sm:grid-cols-3 xl:min-w-100">
                            <div class="rounded-2xl border border-white/80 bg-white px-3 py-2 shadow-sm">
                              <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">Total</p>
                              <p class="mt-1 font-semibold text-slate-950">{fmtMoney(invoice.total_amount)}</p>
                            </div>
                            <div class="rounded-2xl border border-white/80 bg-white px-3 py-2 shadow-sm">
                              <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">Paid</p>
                              <p class="mt-1 font-semibold text-emerald-700">{fmtMoney(invoice.paid_amount)}</p>
                            </div>
                            <div class="rounded-2xl border border-white/80 bg-white px-3 py-2 shadow-sm">
                              <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">Balance</p>
                              <p class="mt-1 font-semibold text-slate-950">{fmtMoney(invoice.balance_due)}</p>
                            </div>
                          </div>
                        </div>

                        <div class="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,0.9fr)]">
                          <section class="rounded-2xl border border-white/80 bg-white p-4 shadow-sm">
                            <div class="flex items-center justify-between">
                              <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Line Items</p>
                              <span class="text-xs text-slate-500">{fmtInt(invoice.line_items.length)}</span>
                            </div>
                            <div class="mt-3 space-y-2">
                              {#if invoice.line_items.length === 0}
                                <p class="text-sm text-slate-500">No line items recorded.</p>
                              {:else}
                                {#each invoice.line_items as item}
                                  <div class="flex items-start justify-between gap-3 rounded-2xl border border-slate-100 bg-slate-50/80 px-3 py-2">
                                    <div>
                                      <p class="text-sm font-medium text-slate-900">{item.description}</p>
                                      <p class="mt-1 text-xs text-slate-500">Qty {item.quantity} × {fmtMoney(item.unit_price)}</p>
                                    </div>
                                    <span class="text-sm font-semibold text-slate-900">{fmtMoney(item.amount)}</span>
                                  </div>
                                {/each}
                              {/if}
                            </div>
                          </section>

                          <section class="rounded-2xl border border-white/80 bg-white p-4 shadow-sm">
                            <div class="flex items-center justify-between">
                              <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Payments</p>
                              <span class="text-xs text-slate-500">{fmtInt(invoice.payments.length)}</span>
                            </div>
                            <div class="mt-3 space-y-2">
                              {#if invoice.payments.length === 0}
                                <p class="text-sm text-slate-500">No payments applied yet.</p>
                              {:else}
                                {#each invoice.payments as payment}
                                  <div class="rounded-2xl border border-slate-100 bg-slate-50/80 px-3 py-2">
                                    <div class="flex items-start justify-between gap-3">
                                      <div>
                                        <p class="text-sm font-medium text-slate-900">{fmtMoney(payment.amount)}</p>
                                        <p class="mt-1 text-xs text-slate-500">{fmtDate(payment.payment_date)} · {payment.payment_method.replaceAll("_", " ")}</p>
                                      </div>
                                      <span class="text-xs text-slate-500">{payment.reference_number || "No ref"}</span>
                                    </div>
                                    {#if payment.notes}
                                      <p class="mt-2 text-sm text-slate-600">{payment.notes}</p>
                                    {/if}
                                  </div>
                                {/each}
                              {/if}
                            </div>
                          </section>
                        </div>
                      </article>
                    {/each}
                  {/if}
                </div>
              </section>
            </div>
          {:else if activeProfileTab === "inventory"}
            <div class="space-y-5">
              <section class="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_16px_40px_-30px_rgba(15,23,42,0.12)]">
                <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-violet-700">Inventory Tab</p>
                    <h3 class="mt-2 text-sm font-bold tracking-wide text-neutral-800 uppercase">Unit Handover Checklist</h3>
                    <p class="mt-2 text-sm text-slate-600">Track the equipment, accessories, and provided items that belong with this assigned unit.</p>
                  </div>
                  <button
                    type="button"
                    onclick={() => openProfileRecordDrawer("inventory")}
                    class="inline-flex items-center rounded-full border border-violet-200 bg-violet-50 px-4 py-2 text-sm font-semibold text-violet-700 transition hover:border-violet-300"
                  >
                    Add Inventory Item
                  </button>
                </div>

                <div class="mt-5 grid gap-3 md:grid-cols-2">
                  <div class="rounded-2xl border border-slate-200/80 bg-slate-50/70 p-4">
                    <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Checklist Rows</p>
                    <p class="mt-3 text-xl font-semibold text-slate-950">{fmtInt(profileSourceOfTruth.inventory.summary.item_count)}</p>
                    <p class="mt-1 text-sm text-slate-600">Distinct unit and fixture items attached to this tenant handover.</p>
                  </div>
                  <div class="rounded-2xl border border-slate-200/80 bg-slate-50/70 p-4">
                    <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Total Quantity</p>
                    <p class="mt-3 text-xl font-semibold text-slate-950">{fmtInt(profileSourceOfTruth.inventory.summary.quantity_total)}</p>
                    <p class="mt-1 text-sm text-slate-600">Combined count across inverters, ACs, keys, devices, and other inventory.</p>
                  </div>
                </div>

                <div class="mt-5 space-y-3">
                  {#if profileSourceOfTruth.inventory.items.length === 0}
                    <div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50/70 px-5 py-10 text-center text-sm text-slate-500">
                      No handover inventory has been recorded for this tenant yet.
                    </div>
                  {:else}
                    {#each profileSourceOfTruth.inventory.items as item}
                      <article class="rounded-2xl border border-slate-200/80 bg-slate-50/70 px-4 py-4">
                        <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                          <div class="flex items-start gap-3">
                            <span class="mt-0.5 inline-flex h-5 w-5 items-center justify-center rounded-full border border-emerald-200 bg-emerald-50 text-emerald-700">
                              <svg class="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" aria-hidden="true">
                                <path stroke-linecap="round" stroke-linejoin="round" d="m5 12 5 5L20 7" />
                              </svg>
                            </span>
                            <div>
                              <p class="text-sm font-semibold text-slate-950">{item.item_name}</p>
                              <p class="mt-1 text-sm text-slate-600">Quantity {fmtInt(item.quantity)}</p>
                              {#if item.notes}
                                <p class="mt-2 text-sm text-slate-600">{item.notes}</p>
                              {/if}
                            </div>
                          </div>
                          <div class="flex flex-wrap gap-2">
                            <span class={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold ${inventoryConditionBadgeClass(item.condition)}`}>
                              {item.condition_display}
                            </span>
                            <span class={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold ${inventoryStatusBadgeClass(item.status)}`}>
                              {item.status_display}
                            </span>
                          </div>
                        </div>
                      </article>
                    {/each}
                  {/if}
                </div>
              </section>
            </div>
          {:else}
            <div class="space-y-5">
              <section class="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_16px_40px_-30px_rgba(15,23,42,0.12)]">
                <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-rose-700">Incident Log</p>
                    <h3 class="mt-2 text-sm font-bold tracking-wide text-neutral-800 uppercase">Violations &amp; Major Maintenance History</h3>
                    <p class="mt-2 text-sm text-slate-600">A unified timeline of recorded lease incidents and serious maintenance work linked to the tenant location.</p>
                  </div>
                  <button
                    type="button"
                    onclick={() => openProfileRecordDrawer("incident")}
                    class="inline-flex items-center rounded-full border border-rose-200 bg-rose-50 px-4 py-2 text-sm font-semibold text-rose-700 transition hover:border-rose-300"
                  >
                    Add Incident
                  </button>
                </div>

                <div class="mt-5 grid gap-3 md:grid-cols-3">
                  <div class="rounded-2xl border border-slate-200/80 bg-slate-50/70 p-4">
                    <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Timeline Entries</p>
                    <p class="mt-3 text-xl font-semibold text-slate-950">{fmtInt(profileSourceOfTruth.incident_log.entries.length)}</p>
                    <p class="mt-1 text-sm text-slate-600">Combined registry incidents and maintenance escalations.</p>
                  </div>
                  <div class="rounded-2xl border border-slate-200/80 bg-slate-50/70 p-4">
                    <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Manual Records</p>
                    <p class="mt-3 text-xl font-semibold text-slate-950">{fmtInt(profileSourceOfTruth.incident_log.manual_records.length)}</p>
                    <p class="mt-1 text-sm text-slate-600">Violations or incidents logged directly on this tenant profile.</p>
                  </div>
                  <div class="rounded-2xl border border-slate-200/80 bg-slate-50/70 p-4">
                    <p class="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Major Work Orders</p>
                    <p class="mt-3 text-xl font-semibold text-slate-950">{fmtInt(profileSourceOfTruth.incident_log.maintenance_records.length)}</p>
                    <p class="mt-1 text-sm text-slate-600">High-severity or breakdown maintenance history at the tenant location.</p>
                  </div>
                </div>

                <div class="mt-5 space-y-3">
                  {#if profileSourceOfTruth.incident_log.entries.length === 0}
                    <div class="rounded-2xl border border-dashed border-slate-200 bg-slate-50/70 px-5 py-10 text-center text-sm text-slate-500">
                      No incident or major maintenance events have been recorded yet.
                    </div>
                  {:else}
                    {#each profileSourceOfTruth.incident_log.entries as entry}
                      <article class={`rounded-2xl border px-4 py-4 ${entry.entry_type === "work_order" ? "border-sky-200/80 bg-sky-50/60" : "border-slate-200/80 bg-slate-50/70"}`}>
                        <div class="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
                          <div>
                            <div class="flex flex-wrap items-center gap-2">
                              <span class="inline-flex items-center rounded-full border border-white/90 bg-white/90 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-600">
                                {entry.source_label}
                              </span>
                              <span class={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold ${incidentSeverityBadgeClass(entry.severity)}`}>
                                {entry.severity_display}
                              </span>
                              <span class={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold ${incidentStatusBadgeClass(entry.status)}`}>
                                {entry.status_display}
                              </span>
                            </div>
                            <p class="mt-3 text-sm font-semibold text-slate-950">{entry.title}</p>
                            <p class="mt-1 text-sm text-slate-600">{entry.incident_type_display}</p>
                          </div>
                          <div class="text-sm text-slate-600 xl:text-right">
                            <p>Occurred {fmtDate(entry.occurred_at)}</p>
                            <p class="mt-1">Resolved {fmtDate(entry.resolved_at)}</p>
                          </div>
                        </div>
                        {#if entry.description}
                          <p class="mt-3 text-sm text-slate-600">{entry.description}</p>
                        {/if}
                        <div class="mt-3 flex flex-wrap gap-3 text-xs text-slate-500">
                          {#if entry.work_order_id}
                            <span>Work Order #{entry.work_order_id}</span>
                          {/if}
                          {#if entry.notes}
                            <span>{entry.notes}</span>
                          {/if}
                        </div>
                      </article>
                    {/each}
                  {/if}
                </div>
              </section>
            </div>
          {/if}
        </div>
      </section>
    </div>
  </div>
{/if}

{#if showProfileRecordDrawer}
  <div class="fixed inset-0 z-60">
    <button
      type="button"
      class="absolute inset-0 bg-slate-950/34 backdrop-blur-[2px]"
      onclick={closeProfileRecordDrawer}
      aria-label="Close tenant profile record drawer"
    ></button>

    <aside class="absolute inset-y-0 right-0 flex w-full max-w-136">
      <div class="ml-auto flex h-full w-full flex-col overflow-hidden border-l border-slate-200/80 bg-white shadow-[-24px_0_70px_-42px_rgba(15,23,42,0.32)]">
        <div class="flex items-start justify-between gap-4 border-b border-slate-200/80 px-5 py-5">
          <div>
            <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-sky-700">Tenant Source of Truth</p>
            <h2 class="mt-2 text-sm font-bold tracking-wide text-neutral-800 uppercase">{profileDrawerTitle(profileDrawerMode)}</h2>
            <p class="mt-2 text-sm text-slate-600">{profileDrawerDescription(profileDrawerMode)}</p>
          </div>
          <button
            type="button"
            onclick={closeProfileRecordDrawer}
            class="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200/80 bg-white text-slate-700 shadow-sm hover:text-slate-950"
            aria-label="Close tenant profile record drawer"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="flex-1 overflow-y-auto px-5 py-5">
          {#if profileDrawerMode === "identity"}
            <section class="space-y-4">
              <label class="block">
                <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Document Type</span>
                <select bind:value={identityDocumentForm.document_type} class="w-full rounded-2xl border border-slate-200/80 bg-white px-4 py-2.5 text-sm text-slate-700 shadow-sm focus:border-slate-300 focus:outline-none">
                  {#each identityDocumentOptions as option}
                    <option value={option.value}>{option.label}</option>
                  {/each}
                </select>
              </label>
              <label class="block">
                <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Document Number</span>
                <input bind:value={identityDocumentForm.document_number} type="text" class="w-full rounded-2xl border border-slate-200/80 bg-white px-4 py-2.5 text-sm text-slate-700 shadow-sm focus:border-slate-300 focus:outline-none" placeholder="Document number" />
              </label>
              <div class="grid gap-4 sm:grid-cols-2">
                <label class="block">
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Holder Name</span>
                  <input bind:value={identityDocumentForm.holder_name} type="text" class="w-full rounded-2xl border border-slate-200/80 bg-white px-4 py-2.5 text-sm text-slate-700 shadow-sm focus:border-slate-300 focus:outline-none" placeholder="Name on the document" />
                </label>
                <label class="block">
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Issuing Country</span>
                  <input bind:value={identityDocumentForm.issuing_country} type="text" class="w-full rounded-2xl border border-slate-200/80 bg-white px-4 py-2.5 text-sm text-slate-700 shadow-sm focus:border-slate-300 focus:outline-none" placeholder="Nigeria" />
                </label>
              <label class="block">
                <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Issue Date</span>
                <DateInput bind:value={identityDocumentForm.issue_date} />
              </label>
              <label class="block">
                <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Expiry Date</span>
                <DateInput bind:value={identityDocumentForm.expiry_date} />
              </label>
              </div>
              <label class="block">
                <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Scan Reference</span>
                <input bind:value={identityDocumentForm.scan_reference} type="text" class="w-full rounded-2xl border border-slate-200/80 bg-white px-4 py-2.5 text-sm text-slate-700 shadow-sm focus:border-slate-300 focus:outline-none" placeholder="Drive path, vault ref, or scan tag" />
              </label>
              <div class="grid gap-3 sm:grid-cols-2">
                <label class="flex items-center gap-3 rounded-2xl border border-slate-200/80 bg-slate-50/70 px-4 py-3 text-sm text-slate-700">
                  <input bind:checked={identityDocumentForm.scan_on_file} type="checkbox" class="h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500" />
                  <span>Scan on file</span>
                </label>
                <label class="flex items-center gap-3 rounded-2xl border border-slate-200/80 bg-slate-50/70 px-4 py-3 text-sm text-slate-700">
                  <input bind:checked={identityDocumentForm.is_verified} type="checkbox" class="h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500" />
                  <span>Verified</span>
                </label>
              </div>
              <label class="block">
                <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Notes</span>
                <textarea bind:value={identityDocumentForm.notes} rows="4" class="w-full rounded-2xl border border-slate-200/80 bg-white px-4 py-3 text-sm text-slate-700 shadow-sm focus:border-slate-300 focus:outline-none" placeholder="Any review or compliance notes."></textarea>
              </label>
            </section>
          {:else if profileDrawerMode === "contact"}
            <section class="space-y-4">
              <label class="block">
                <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Contact Role</span>
                <select bind:value={relationshipContactForm.contact_role} class="w-full rounded-2xl border border-slate-200/80 bg-white px-4 py-2.5 text-sm text-slate-700 shadow-sm focus:border-slate-300 focus:outline-none">
                  {#each relationshipContactOptions as option}
                    <option value={option.value}>{option.label}</option>
                  {/each}
                </select>
              </label>
              <div class="grid gap-4 sm:grid-cols-2">
                <label class="block sm:col-span-2">
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Full Name</span>
                  <input bind:value={relationshipContactForm.full_name} type="text" class="w-full rounded-2xl border border-slate-200/80 bg-white px-4 py-2.5 text-sm text-slate-700 shadow-sm focus:border-slate-300 focus:outline-none" placeholder="Contact full name" />
                </label>
                <label class="block">
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Relationship</span>
                  <input bind:value={relationshipContactForm.relationship} type="text" class="w-full rounded-2xl border border-slate-200/80 bg-white px-4 py-2.5 text-sm text-slate-700 shadow-sm focus:border-slate-300 focus:outline-none" placeholder="Brother, spouse, HR lead..." />
                </label>
                <label class="flex items-center gap-3 rounded-2xl border border-slate-200/80 bg-slate-50/70 px-4 py-3 text-sm text-slate-700">
                  <input bind:checked={relationshipContactForm.is_primary} type="checkbox" class="h-4 w-4 rounded border-slate-300 text-violet-600 focus:ring-violet-500" />
                  <span>Primary contact for this role</span>
                </label>
                <label class="block">
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Phone</span>
                  <input bind:value={relationshipContactForm.phone} type="text" class="w-full rounded-2xl border border-slate-200/80 bg-white px-4 py-2.5 text-sm text-slate-700 shadow-sm focus:border-slate-300 focus:outline-none" placeholder="+234..." />
                </label>
                <label class="block">
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Email</span>
                  <input bind:value={relationshipContactForm.email} type="email" class="w-full rounded-2xl border border-slate-200/80 bg-white px-4 py-2.5 text-sm text-slate-700 shadow-sm focus:border-slate-300 focus:outline-none" placeholder="contact@example.com" />
                </label>
              </div>
              <label class="block">
                <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Address</span>
                <textarea bind:value={relationshipContactForm.address} rows="3" class="w-full rounded-2xl border border-slate-200/80 bg-white px-4 py-3 text-sm text-slate-700 shadow-sm focus:border-slate-300 focus:outline-none" placeholder="Home or office address"></textarea>
              </label>
              <label class="block">
                <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Notes</span>
                <textarea bind:value={relationshipContactForm.notes} rows="4" class="w-full rounded-2xl border border-slate-200/80 bg-white px-4 py-3 text-sm text-slate-700 shadow-sm focus:border-slate-300 focus:outline-none" placeholder="Escalation notes or special handling"></textarea>
              </label>
            </section>
          {:else if profileDrawerMode === "inventory"}
            <section class="space-y-4">
              <label class="block">
                <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Item Name</span>
                <input bind:value={inventoryItemForm.item_name} type="text" class="w-full rounded-2xl border border-slate-200/80 bg-white px-4 py-2.5 text-sm text-slate-700 shadow-sm focus:border-slate-300 focus:outline-none" placeholder="3 Bluegate Inverters" />
              </label>
              <div class="grid gap-4 sm:grid-cols-2">
                <label class="block">
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Quantity</span>
                  <input bind:value={inventoryItemForm.quantity} type="number" min="1" step="1" class="w-full rounded-2xl border border-slate-200/80 bg-white px-4 py-2.5 text-sm text-slate-700 shadow-sm focus:border-slate-300 focus:outline-none" />
                </label>
                <label class="block">
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Condition</span>
                  <select bind:value={inventoryItemForm.condition} class="w-full rounded-2xl border border-slate-200/80 bg-white px-4 py-2.5 text-sm text-slate-700 shadow-sm focus:border-slate-300 focus:outline-none">
                    {#each inventoryConditionOptions as option}
                      <option value={option.value}>{option.label}</option>
                    {/each}
                  </select>
                </label>
                <label class="block sm:col-span-2">
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Checklist Status</span>
                  <select bind:value={inventoryItemForm.status} class="w-full rounded-2xl border border-slate-200/80 bg-white px-4 py-2.5 text-sm text-slate-700 shadow-sm focus:border-slate-300 focus:outline-none">
                    {#each inventoryStatusOptions as option}
                      <option value={option.value}>{option.label}</option>
                    {/each}
                  </select>
                </label>
              </div>
              <label class="block">
                <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Notes</span>
                <textarea bind:value={inventoryItemForm.notes} rows="4" class="w-full rounded-2xl border border-slate-200/80 bg-white px-4 py-3 text-sm text-slate-700 shadow-sm focus:border-slate-300 focus:outline-none" placeholder="Brand, serials, or handover notes"></textarea>
              </label>
            </section>
          {:else}
            <section class="space-y-4">
              <div class="grid gap-4 sm:grid-cols-2">
                <label class="block sm:col-span-2">
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Incident Title</span>
                  <input bind:value={incidentRecordForm.title} type="text" class="w-full rounded-2xl border border-slate-200/80 bg-white px-4 py-2.5 text-sm text-slate-700 shadow-sm focus:border-slate-300 focus:outline-none" placeholder="Lease violation or major incident title" />
                </label>
                <label class="block">
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Incident Type</span>
                  <select bind:value={incidentRecordForm.incident_type} class="w-full rounded-2xl border border-slate-200/80 bg-white px-4 py-2.5 text-sm text-slate-700 shadow-sm focus:border-slate-300 focus:outline-none">
                    {#each incidentTypeOptions as option}
                      <option value={option.value}>{option.label}</option>
                    {/each}
                  </select>
                </label>
                <label class="block">
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Severity</span>
                  <select bind:value={incidentRecordForm.severity} class="w-full rounded-2xl border border-slate-200/80 bg-white px-4 py-2.5 text-sm text-slate-700 shadow-sm focus:border-slate-300 focus:outline-none">
                    {#each incidentSeverityOptions as option}
                      <option value={option.value}>{option.label}</option>
                    {/each}
                  </select>
                </label>
                <label class="block">
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Status</span>
                  <select bind:value={incidentRecordForm.status} class="w-full rounded-2xl border border-slate-200/80 bg-white px-4 py-2.5 text-sm text-slate-700 shadow-sm focus:border-slate-300 focus:outline-none">
                    {#each incidentStatusOptions as option}
                      <option value={option.value}>{option.label}</option>
                    {/each}
                  </select>
                </label>
                <label class="block">
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Occurred At</span>
                  <DateInput bind:value={incidentRecordForm.occurred_at} />
                </label>
                <label class="block sm:col-span-2">
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Resolved At</span>
                  <DateInput bind:value={incidentRecordForm.resolved_at} />
                </label>
              </div>
              <label class="block">
                <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Description</span>
                <textarea bind:value={incidentRecordForm.description} rows="4" class="w-full rounded-2xl border border-slate-200/80 bg-white px-4 py-3 text-sm text-slate-700 shadow-sm focus:border-slate-300 focus:outline-none" placeholder="Narrative of the issue or violation"></textarea>
              </label>
              <label class="block">
                <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Notes</span>
                <textarea bind:value={incidentRecordForm.notes} rows="4" class="w-full rounded-2xl border border-slate-200/80 bg-white px-4 py-3 text-sm text-slate-700 shadow-sm focus:border-slate-300 focus:outline-none" placeholder="Follow-up notes or resolution guidance"></textarea>
              </label>
            </section>
          {/if}
        </div>

        <div class="flex items-center justify-between gap-3 border-t border-slate-200/80 px-5 py-4">
          <div class="text-sm text-slate-500">
            Linked to {currentProfileRecord()?.resolved_display_name || "selected tenant"}.
          </div>
          <div class="flex items-center gap-2">
            <button
              type="button"
              onclick={closeProfileRecordDrawer}
              class="inline-flex items-center rounded-full border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:border-slate-300"
            >
              Cancel
            </button>
            <button
              type="button"
              onclick={submitProfileRecordDrawer}
              disabled={savingProfileRecord}
              class="inline-flex items-center rounded-full border border-sky-600 bg-sky-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-sky-500 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {savingProfileRecord ? "Saving..." : "Save Record"}
            </button>
          </div>
        </div>
      </div>
    </aside>
  </div>
{/if}

{#if showMasterListDrawer}
  <div class="fixed inset-0 z-40">
    <button
      type="button"
      class="absolute inset-0 bg-slate-950/34 backdrop-blur-[2px]"
      onclick={closeMasterListDrawer}
      aria-label="Close tenant master list drawer"
    ></button>

    <aside class="absolute inset-y-0 right-0 flex w-full max-w-384">
      <div class="ml-auto flex h-full w-full flex-col overflow-hidden border-l border-slate-200/80 bg-white shadow-[-24px_0_70px_-42px_rgba(15,23,42,0.32)]">
        <div class="flex items-start justify-between gap-4 border-b border-slate-200/80 px-5 py-5">
          <div>
            <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-sky-700">Tenant Registry (Master Data)</p>
            <h2 class="mt-2 text-sm font-bold tracking-wide text-neutral-800 uppercase">Master List</h2>
            <p class="mt-2 text-sm text-slate-600">
              Search, filter, and review the full tenant ledger without crowding the main registry page.
            </p>
          </div>
          <div class="flex items-center gap-2">
            <button
              type="button"
              onclick={openCreateModal}
              class="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm font-semibold text-emerald-700 transition hover:border-emerald-300"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
              </svg>
              Add Tenant
            </button>
            <button
              type="button"
              onclick={closeMasterListDrawer}
              class="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200/80 bg-white text-slate-700 shadow-sm hover:text-slate-950"
              aria-label="Close tenant master list drawer"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        <div class="border-b border-slate-200/80 px-5 py-4">
          <div class="grid gap-3 xl:grid-cols-[minmax(0,1.4fr)_minmax(0,0.8fr)_auto_auto]">
            <label>
              <span class="sr-only">Search tenant registry</span>
              <input
                bind:value={search}
                type="search"
                placeholder="Search tenant, customer, property, unit..."
                class="w-full rounded-2xl border border-white/70 bg-white/80 px-4 py-2.5 text-sm text-slate-700 shadow-sm backdrop-blur placeholder:text-slate-400 focus:border-slate-300 focus:outline-none"
              />
            </label>

            <label>
              <span class="sr-only">Filter by status</span>
              <select
                bind:value={statusFilter}
                class="w-full rounded-2xl border border-white/70 bg-white/80 px-4 py-2.5 text-sm text-slate-700 shadow-sm backdrop-blur focus:border-slate-300 focus:outline-none"
              >
                <option value="all">All statuses</option>
                {#each statusOptions as option}
                  <option value={option.value}>{option.label}</option>
                {/each}
              </select>
            </label>

            <button
              type="button"
              onclick={() => (showAdvancedFilters = true)}
              class="inline-flex items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white/82 px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-sm backdrop-blur transition hover:border-slate-300 hover:text-slate-950"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5m-13.5 5.25h10.5m-7.5 5.25h4.5" />
              </svg>
              Advanced Filters
              {#if advancedFilterCount() > 0}
                <span class="rounded-full border border-sky-200 bg-sky-50 px-2 py-0.5 text-[11px] font-semibold text-sky-700">
                  {advancedFilterCount()}
                </span>
              {/if}
            </button>

            <button
              type="button"
              onclick={clearAdvancedFilters}
              disabled={advancedFilterCount() === 0}
              class="inline-flex items-center justify-center rounded-2xl border border-slate-200 bg-white/82 px-4 py-2.5 text-sm font-semibold text-slate-600 shadow-sm backdrop-blur transition hover:border-slate-300 hover:text-slate-950 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Clear Filters
            </button>
          </div>

          <div class="mt-3 flex flex-wrap items-center gap-2">
            <span class="inline-flex items-center rounded-full border border-white/80 bg-white/80 px-3 py-1 text-xs font-semibold text-slate-700 shadow-sm">
              Rows {fmtInt(filteredProfiles().length)}
            </span>
            <span class="inline-flex items-center rounded-full border border-violet-200 bg-violet-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-violet-700">
              Virtual Scroller Active
            </span>
            {#if advancedFilterCount() > 0}
              {#each advancedFilterSummaries() as summary}
                <span class="inline-flex items-center rounded-full border border-sky-100 bg-sky-50/80 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-sky-700">
                  {summary}
                </span>
              {/each}
            {/if}
          </div>
        </div>

        <div class="flex-1 overflow-hidden px-5 py-5">
          <div class="h-full overflow-hidden rounded-[24px] border border-white/75 bg-white/76 shadow-[0_18px_44px_-34px_rgba(15,23,42,0.24)] backdrop-blur-xl">
            <div bind:this={registryViewport} class="h-full overflow-auto" onscroll={handleRegistryScroll}>
              <div class="min-w-[1024px]">
                <div class="sticky top-0 z-10 grid grid-cols-[0.9fr_1.35fr_1.1fr_1.1fr_0.9fr_1fr] bg-white/95 text-left text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500 backdrop-blur">
                  <div class="px-4 py-3">Tenant ID</div>
                  <div class="px-4 py-3">Name &amp; Contact</div>
                  <div class="px-4 py-3">Assigned Unit</div>
                  <div class="px-4 py-3">Property Location</div>
                  <div class="px-4 py-3">Lease Status</div>
                  <div class="px-4 py-3">Tags</div>
                </div>

                {#if loading}
                  <div class="px-4 py-10 text-center text-sm text-slate-500">Loading tenant registry...</div>
                {:else if registryVirtualWindow.rows.length === 0}
                  <div class="px-4 py-10 text-center text-sm text-slate-500">No tenant registry rows match the current filters.</div>
                {:else}
                  {#if registryVirtualWindow.topSpacer > 0}
                    <div style={`height: ${registryVirtualWindow.topSpacer}px;`}></div>
                  {/if}

                  {#each registryVirtualWindow.visibleRows as profile, localIndex}
                    {@const index = registryVirtualWindow.start + localIndex}
                    {@const leaseState = registryLeaseState(profile)}
                    {@const flags = recordFlags(profile)}
                    <div
                      class={`group grid grid-cols-[0.9fr_1.35fr_1.1fr_1.1fr_0.9fr_1fr] transition-all duration-200 ${index % 2 === 0 ? "bg-white/82" : "bg-slate-50/72"} hover:bg-white/92 hover:[backdrop-filter:blur(10px)] hover:[box-shadow:inset_0_0_0_1px_rgba(226,232,240,0.94)]`}
                      style={`height: ${REGISTRY_ROW_HEIGHT}px;`}
                    >
                      <div class="border-t border-white/80 px-4 py-3 transition-colors group-hover:border-white/95">
                        <div class="flex h-full flex-col justify-between gap-3 overflow-hidden">
                          <div>
                            <p class="truncate font-semibold tracking-[0.16em] text-slate-950">{registryTenantCode(profile)}</p>
                            <p class="mt-1 text-xs text-slate-500">Created {fmtDate(profile.created_at)}</p>
                          </div>
                          <button
                            type="button"
                            onclick={() => openProfileModal(profile)}
                            class="inline-flex w-fit items-center rounded-full border border-slate-200 bg-white px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-600 transition hover:border-slate-300 hover:text-slate-950"
                          >
                            Profile
                          </button>
                        </div>
                      </div>

                      <div class="border-t border-white/80 px-4 py-3 transition-colors group-hover:border-white/95">
                        <div class="flex h-full flex-col gap-2 overflow-hidden">
                          <button
                            type="button"
                            onclick={() => openProfileModal(profile)}
                            class="truncate text-left font-semibold text-slate-950 transition hover:text-sky-700"
                          >
                            {profile.resolved_display_name}
                          </button>
                          <p class="truncate text-sm text-slate-600">{registryPreferredContact(profile)}</p>
                          {#if profile.customer_name || profile.contact_account_name}
                            <p class="truncate text-xs text-slate-500">
                              {profile.customer_name || profile.contact_account_name}
                            </p>
                          {/if}
                        </div>
                      </div>

                      <div class="border-t border-white/80 px-4 py-3 transition-colors group-hover:border-white/95">
                        <div class="flex h-full flex-col gap-2 overflow-hidden">
                          <p class="truncate font-medium text-slate-900">{registryAssignedUnitLabel(profile)}</p>
                          <p class="truncate text-xs text-slate-500">{registryAssignedUnitMeta(profile)}</p>
                          {#if flags.length > 0}
                            <div class="mt-auto flex flex-wrap gap-2 overflow-hidden">
                              {#each flags.slice(0, 2) as flag}
                                <span class="inline-flex items-center rounded-full border border-rose-200 bg-rose-50 px-2.5 py-1 text-[11px] font-semibold text-rose-700">
                                  {flag}
                                </span>
                              {/each}
                              {#if flags.length > 2}
                                <span class="inline-flex items-center rounded-full border border-slate-200 bg-slate-100 px-2.5 py-1 text-[11px] font-semibold text-slate-600">
                                  +{flags.length - 2}
                                </span>
                              {/if}
                            </div>
                          {/if}
                        </div>
                      </div>

                      <div class="border-t border-white/80 px-4 py-3 transition-colors group-hover:border-white/95">
                        <div class="flex h-full flex-col gap-2 overflow-hidden">
                          <p class="truncate font-medium text-slate-900">{registryPropertyLabel(profile)}</p>
                          <p class="truncate text-sm text-slate-600">{registryPropertyMeta(profile)}</p>
                          {#if profile.facility_code}
                            <div class="mt-auto">
                              <span class="inline-flex items-center rounded-full border border-sky-200 bg-sky-50 px-2.5 py-1 text-[11px] font-semibold text-sky-700">
                                {profile.facility_code}
                              </span>
                            </div>
                          {/if}
                        </div>
                      </div>

                      <div class="border-t border-white/80 px-4 py-3 transition-colors group-hover:border-white/95">
                        <div class="flex h-full flex-col items-start gap-2 overflow-hidden">
                          <span class={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold ${leaseState.className}`}>
                            {leaseState.label}
                          </span>
                          <span class="text-xs text-slate-500">{leaseState.meta}</span>
                        </div>
                      </div>

                      <div class="border-t border-white/80 px-4 py-3 transition-colors group-hover:border-white/95">
                        <div class="flex h-full flex-wrap content-start gap-2 overflow-hidden">
                          {#each registryTags(profile) as tag}
                            <span class={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold ${tag.className}`}>
                              {tag.label}
                            </span>
                          {/each}
                        </div>
                      </div>
                    </div>
                  {/each}

                  {#if registryVirtualWindow.bottomSpacer > 0}
                    <div style={`height: ${registryVirtualWindow.bottomSpacer}px;`}></div>
                  {/if}
                {/if}
              </div>
            </div>
          </div>
        </div>
      </div>
    </aside>
  </div>
{/if}

{#if showAdvancedFilters}
  <div class="fixed inset-0 z-50">
    <button
      type="button"
      class="absolute inset-0 bg-slate-950/34 backdrop-blur-[2px]"
      onclick={() => (showAdvancedFilters = false)}
      aria-label="Close advanced tenant filters"
    ></button>

    <aside class="absolute inset-y-0 right-0 flex w-full max-w-120">
      <div class="ml-auto flex h-full w-full flex-col overflow-hidden border-l border-slate-200/80 bg-white shadow-[-24px_0_70px_-42px_rgba(15,23,42,0.32)]">
        <div class="flex items-start justify-between gap-4 border-b border-slate-200/80 px-5 py-5">
          <div>
            <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-sky-700">3. Advanced Filtering Sidebar</p>
            <h2 class="mt-2 text-sm font-bold tracking-wide text-neutral-800 uppercase">Portfolio Filters</h2>
            <p class="mt-2 text-sm text-slate-600">
              Narrow the registry by building, lease exits, payment position, and tenant type across Lagos, Abuja, and beyond.
            </p>
          </div>
          <button
            type="button"
            onclick={() => (showAdvancedFilters = false)}
            class="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200/80 bg-white text-slate-700 shadow-sm hover:text-slate-950"
            aria-label="Close advanced tenant filters"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="flex-1 space-y-5 overflow-y-auto px-5 py-5">
          <section class="rounded-xl border border-slate-200/80 bg-white p-5 shadow-[0_16px_40px_-30px_rgba(15,23,42,0.14)]">
            <div class="flex items-center justify-between gap-3">
              <div>
                <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-sky-700">By Property</p>
                <p class="mt-2 text-sm text-slate-600">Multi-select all managed buildings in the portfolio.</p>
              </div>
              {#if selectedPropertyFilters.length > 0}
                <span class="rounded-full border border-sky-200 bg-sky-50 px-3 py-1 text-[11px] font-semibold text-sky-700">
                  {selectedPropertyFilters.length} selected
                </span>
              {/if}
            </div>
            <div class="mt-4 space-y-2">
              {#each propertyOptions() as propertyRecord}
                <label class="flex items-start gap-3 rounded-2xl border border-slate-200/80 bg-slate-50/70 px-4 py-3 text-sm text-slate-700 transition hover:border-slate-300">
                  <input
                    type="checkbox"
                    checked={selectedPropertyFilters.includes(String(propertyRecord.id))}
                    onchange={() => togglePropertyFilter(String(propertyRecord.id))}
                    class="mt-0.5 h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
                  />
                  <span class="min-w-0">
                    <span class="block font-semibold text-slate-900">{propertyRecord.name}</span>
                    <span class="mt-1 block text-xs text-slate-500">{propertyRecord.location || propertyRecord.address}</span>
                  </span>
                </label>
              {/each}
            </div>
          </section>

          <section class="rounded-xl border border-slate-200/80 bg-white p-5 shadow-[0_16px_40px_-30px_rgba(15,23,42,0.14)]">
            <div class="flex items-center justify-between gap-3">
              <div>
                <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-violet-700">By Lease End</p>
                <p class="mt-2 text-sm text-slate-600">Pick a date window to find leases ending in the next 60 days or any custom range.</p>
              </div>
              <button
                type="button"
                onclick={setLeaseRangeNext60Days}
                class="inline-flex items-center rounded-full border border-violet-200 bg-violet-50 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.16em] text-violet-700 transition hover:border-violet-300"
              >
                Next 60 Days
              </button>
            </div>
            <div class="mt-4 grid gap-3 sm:grid-cols-2">
              <label>
                <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">From</span>
                <DateInput bind:value={leaseEndFrom} />
              </label>
              <label>
                <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">To</span>
                <DateInput bind:value={leaseEndTo} />
              </label>
            </div>
          </section>

          <section class="rounded-xl border border-slate-200/80 bg-white p-5 shadow-[0_16px_40px_-30px_rgba(15,23,42,0.14)]">
            <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-amber-700">By Payment Status</p>
            <p class="mt-2 text-sm text-slate-600">Separate debt-free tenants from delinquent rent and service-charge accounts.</p>
            <div class="mt-4 space-y-2">
              <label class="flex items-start gap-3 rounded-2xl border border-slate-200/80 bg-slate-50/70 px-4 py-3 text-sm text-slate-700 transition hover:border-slate-300">
                <input
                  type="checkbox"
                  checked={selectedPaymentFilters.includes("debt_free")}
                  onchange={() => togglePaymentFilter("debt_free")}
                  class="mt-0.5 h-4 w-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
                />
                <span>
                  <span class="block font-semibold text-slate-900">Debt-Free</span>
                  <span class="mt-1 block text-xs text-slate-500">No outstanding rent or service charge balance.</span>
                </span>
              </label>
              <label class="flex items-start gap-3 rounded-2xl border border-slate-200/80 bg-slate-50/70 px-4 py-3 text-sm text-slate-700 transition hover:border-slate-300">
                <input
                  type="checkbox"
                  checked={selectedPaymentFilters.includes("delinquent")}
                  onchange={() => togglePaymentFilter("delinquent")}
                  class="mt-0.5 h-4 w-4 rounded border-slate-300 text-rose-600 focus:ring-rose-500"
                />
                <span>
                  <span class="block font-semibold text-slate-900">Delinquent</span>
                  <span class="mt-1 block text-xs text-slate-500">Outstanding receivables that need debt recovery attention.</span>
                </span>
              </label>
            </div>
          </section>

          <section class="rounded-xl border border-slate-200/80 bg-white p-5 shadow-[0_16px_40px_-30px_rgba(15,23,42,0.14)]">
            <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-emerald-700">By Nationality / Type</p>
            <p class="mt-2 text-sm text-slate-600">Filter the registry by corporate entities versus individual occupants.</p>
            <div class="mt-4 space-y-2">
              {#each tenantTypeOptions as option}
                <label class="flex items-start gap-3 rounded-2xl border border-slate-200/80 bg-slate-50/70 px-4 py-3 text-sm text-slate-700 transition hover:border-slate-300">
                  <input
                    type="checkbox"
                    checked={selectedTenantTypeFilters.includes(option.value)}
                    onchange={() => toggleTenantTypeFilter(option.value)}
                    class="mt-0.5 h-4 w-4 rounded border-slate-300 text-sky-600 focus:ring-sky-500"
                  />
                  <span>
                    <span class="block font-semibold text-slate-900">{option.label}</span>
                    <span class="mt-1 block text-xs text-slate-500">
                      {option.value === "corporate" ? "Corporate and commercial lease records." : "Individual and residential occupancy records."}
                    </span>
                  </span>
                </label>
              {/each}
            </div>
          </section>
        </div>

        <div class="flex items-center justify-between gap-3 border-t border-slate-200/80 px-5 py-4">
          <div>
            <p class="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Matched Rows</p>
            <p class="mt-1 text-sm text-slate-900">{fmtInt(filteredProfiles().length)} tenant records</p>
          </div>
          <div class="flex items-center gap-2">
            <button
              type="button"
              onclick={clearAdvancedFilters}
              disabled={advancedFilterCount() === 0}
              class="inline-flex items-center rounded-full border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:border-slate-300 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Clear All
            </button>
            <button
              type="button"
              onclick={() => (showAdvancedFilters = false)}
              class="inline-flex items-center rounded-full border border-sky-200 bg-sky-50 px-4 py-2.5 text-sm font-semibold text-sky-700 transition hover:border-sky-300"
            >
              Done
            </button>
          </div>
        </div>
      </div>
    </aside>
  </div>
{/if}

{#if showOnboardingModal}
  <div class="fixed inset-0 z-50">
    <button
      type="button"
      class="absolute inset-0 bg-slate-950/40 backdrop-blur-[3px]"
      onclick={closeOnboardingModal}
      aria-label="Close tenant onboarding modal"
    ></button>

    <div class="relative z-10 flex min-h-full items-center justify-center px-4 py-6 sm:px-6">
      <section class="max-h-[92vh] w-full max-w-6xl overflow-hidden rounded-[30px] border border-white/70 bg-[linear-gradient(180deg,rgba(255,255,255,0.98),rgba(248,250,252,0.97))] shadow-[0_42px_120px_-58px_rgba(15,23,42,0.45)]">
        <div class="flex items-start justify-between gap-4 border-b border-slate-200/80 px-6 py-5">
          <div>
            <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-emerald-700">Tenant Registry Onboarding</p>
            <h2 class="mt-2 text-lg font-bold tracking-wide text-slate-900">Add New Tenant</h2>
            <p class="mt-1 text-sm text-slate-600">
              Create a master tenant record with guided steps for identity, assignment, occupancy, and review.
            </p>
          </div>
          <button
            type="button"
            onclick={closeOnboardingModal}
            class="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200/80 bg-white text-slate-700 shadow-sm hover:text-slate-950"
            aria-label="Close tenant onboarding modal"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="grid gap-0 xl:grid-cols-[260px_minmax(0,1fr)]">
          <aside class="border-b border-slate-200/70 bg-slate-50/70 p-5 xl:border-r xl:border-b-0">
            <div class="space-y-3">
              {#each onboardingSteps as step, index}
                <button
                  type="button"
                  onclick={() => {
                    if (index <= onboardingStep || validateOnboardingStep()) onboardingStep = index;
                  }}
                  class={`flex w-full items-start gap-3 rounded-2xl border px-4 py-3 text-left transition ${
                    index === onboardingStep
                      ? "border-emerald-200 bg-emerald-50 text-emerald-800 shadow-sm"
                      : index < onboardingStep
                        ? "border-sky-200 bg-sky-50/70 text-sky-700"
                        : "border-slate-200 bg-white text-slate-500"
                  }`}
                >
                  <span class={`inline-flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold ${index === onboardingStep ? "bg-emerald-600 text-white" : index < onboardingStep ? "bg-sky-600 text-white" : "bg-slate-200 text-slate-600"}`}>
                    {index + 1}
                  </span>
                  <span>
                    <span class="block text-sm font-semibold">{step.title}</span>
                    <span class="mt-1 block text-xs leading-5 opacity-80">{step.caption}</span>
                  </span>
                </button>
              {/each}
            </div>

            <div class="mt-5 rounded-2xl border border-white/80 bg-white/90 p-4 shadow-sm">
              <p class="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">Onboarding Snapshot</p>
              <div class="mt-3 space-y-2 text-sm text-slate-600">
                <div>
                  <span class="text-xs uppercase tracking-[0.18em] text-slate-400">Tenant</span>
                  <p class="mt-1 font-semibold text-slate-900">{suggestedDisplayName()}</p>
                </div>
                <div>
                  <span class="text-xs uppercase tracking-[0.18em] text-slate-400">Assignment</span>
                  <p class="mt-1">{form.unit || form.facility_space ? `${form.unit ? `Unit ${form.unit}` : ""}${form.unit && form.facility_space ? " / " : ""}${form.facility_space ? `Space ${form.facility_space}` : ""}` : "Pending mapping"}</p>
                </div>
                <div>
                  <span class="text-xs uppercase tracking-[0.18em] text-slate-400">Status</span>
                  <p class="mt-1">{statusOptions.find((option) => option.value === form.status)?.label ?? "Pending Move In"}</p>
                </div>
              </div>
            </div>
          </aside>

          <div class="min-h-0">
            <div class="max-h-[68vh] overflow-y-auto px-6 py-6">
              {#if onboardingStep === 0}
                <section class="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_16px_40px_-30px_rgba(15,23,42,0.14)]">
                  <div class="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                    <div>
                      <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-emerald-700">Step 1</p>
                      <h3 class="mt-2 text-sm font-bold tracking-wide text-neutral-800 uppercase">Identity &amp; Linked Records</h3>
                    </div>
                    <p class="text-xs text-slate-500">Link a customer, contact, or primary user to preserve master-data integrity.</p>
                  </div>

                  <div class="mt-5 grid gap-4 sm:grid-cols-2">
                    <label class="sm:col-span-2">
                      <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Display Name</span>
                      <input
                        bind:value={form.display_name}
                        type="text"
                        class="w-full rounded-2xl border border-white/70 bg-white/85 px-4 py-2.5 text-sm text-slate-700 shadow-sm backdrop-blur focus:border-slate-300 focus:outline-none"
                        placeholder="Tenant display name"
                      />
                      <p class="mt-2 text-xs text-slate-500">If left blank, the registry derives it from the linked customer, contact account, or primary user.</p>
                    </label>

                    <label>
                      <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Customer</span>
                      <select
                        bind:value={form.customer}
                        onchange={() => autofillDisplayName()}
                        class="w-full rounded-2xl border border-white/70 bg-white/85 px-4 py-2.5 text-sm text-slate-700 shadow-sm backdrop-blur focus:border-slate-300 focus:outline-none"
                      >
                        <option value="">None</option>
                        {#each lookups?.customers ?? [] as customer}
                          <option value={String(customer.id)}>{customer.name}</option>
                        {/each}
                      </select>
                    </label>

                    <label>
                      <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Contact Account</span>
                      <select
                        bind:value={form.contact_account}
                        onchange={() => autofillDisplayName()}
                        class="w-full rounded-2xl border border-white/70 bg-white/85 px-4 py-2.5 text-sm text-slate-700 shadow-sm backdrop-blur focus:border-slate-300 focus:outline-none"
                      >
                        <option value="">None</option>
                        {#each lookups?.contact_accounts ?? [] as contact}
                          <option value={String(contact.id)}>{contact.name}</option>
                        {/each}
                      </select>
                    </label>

                    <label class="sm:col-span-2">
                      <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Primary User</span>
                      <select
                        bind:value={form.primary_user}
                        onchange={() => autofillDisplayName()}
                        class="w-full rounded-2xl border border-white/70 bg-white/85 px-4 py-2.5 text-sm text-slate-700 shadow-sm backdrop-blur focus:border-slate-300 focus:outline-none"
                      >
                        <option value="">None</option>
                        {#each lookups?.users ?? [] as user}
                          <option value={String(user.id)}>{user.name}</option>
                        {/each}
                      </select>
                    </label>

                    <label>
                      <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Tenant Type</span>
                      <select
                        bind:value={form.tenant_type}
                        class="w-full rounded-2xl border border-white/70 bg-white/85 px-4 py-2.5 text-sm text-slate-700 shadow-sm backdrop-blur focus:border-slate-300 focus:outline-none"
                      >
                        {#each tenantTypeOptions as option}
                          <option value={option.value}>{option.label}</option>
                        {/each}
                      </select>
                    </label>

                    <label>
                      <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Status</span>
                      <select
                        bind:value={form.status}
                        class="w-full rounded-2xl border border-white/70 bg-white/85 px-4 py-2.5 text-sm text-slate-700 shadow-sm backdrop-blur focus:border-slate-300 focus:outline-none"
                      >
                        {#each statusOptions as option}
                          <option value={option.value}>{option.label}</option>
                        {/each}
                      </select>
                    </label>
                  </div>
                </section>
              {:else if onboardingStep === 1}
                <section class="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_16px_40px_-30px_rgba(15,23,42,0.14)]">
                  <div class="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                    <div>
                      <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-violet-700">Step 2</p>
                      <h3 class="mt-2 text-sm font-bold tracking-wide text-neutral-800 uppercase">Space &amp; Assignment</h3>
                    </div>
                    <p class="text-xs text-slate-500">Map the tenant to a property, unit, facility, or space. Leave blank for unassigned prospects.</p>
                  </div>

                  <div class="mt-5 grid gap-4 sm:grid-cols-2">
                    <label class="sm:col-span-2">
                      <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Property</span>
                      <select
                        bind:value={form.property}
                        onchange={(event) => handlePropertyChange((event.currentTarget as HTMLSelectElement).value)}
                        class="w-full rounded-2xl border border-white/70 bg-white/85 px-4 py-2.5 text-sm text-slate-700 shadow-sm backdrop-blur focus:border-slate-300 focus:outline-none"
                      >
                        <option value="">None</option>
                        {#each propertyOptions() as propertyRecord}
                          <option value={String(propertyRecord.id)}>{propertyRecord.name}</option>
                        {/each}
                      </select>
                    </label>

                    <label>
                      <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Facility</span>
                      <select
                        bind:value={form.facility}
                        onchange={(event) => handleFacilityChange((event.currentTarget as HTMLSelectElement).value)}
                        class="w-full rounded-2xl border border-white/70 bg-white/85 px-4 py-2.5 text-sm text-slate-700 shadow-sm backdrop-blur focus:border-slate-300 focus:outline-none"
                      >
                        <option value="">None</option>
                        {#each filteredFacilities() as facility}
                          <option value={String(facility.id)}>{facility.label}</option>
                        {/each}
                      </select>
                    </label>

                    <label>
                      <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Unit</span>
                      <select
                        bind:value={form.unit}
                        onchange={(event) => handleUnitChange((event.currentTarget as HTMLSelectElement).value)}
                        class="w-full rounded-2xl border border-white/70 bg-white/85 px-4 py-2.5 text-sm text-slate-700 shadow-sm backdrop-blur focus:border-slate-300 focus:outline-none"
                      >
                        <option value="">None</option>
                        {#each filteredUnits() as unit}
                          <option value={String(unit.id)}>{unit.label}</option>
                        {/each}
                      </select>
                    </label>

                    <label class="sm:col-span-2">
                      <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Facility Space</span>
                      <select
                        bind:value={form.facility_space}
                        onchange={(event) => handleSpaceChange((event.currentTarget as HTMLSelectElement).value)}
                        class="w-full rounded-2xl border border-white/70 bg-white/85 px-4 py-2.5 text-sm text-slate-700 shadow-sm backdrop-blur focus:border-slate-300 focus:outline-none"
                      >
                        <option value="">None</option>
                        {#each filteredSpaces() as space}
                          <option value={String(space.id)}>{space.label}</option>
                        {/each}
                      </select>
                      <p class="mt-2 text-xs text-slate-500">Selecting a mapped space auto-aligns the unit, facility, and property wherever possible.</p>
                    </label>
                  </div>
                </section>
              {:else if onboardingStep === 2}
                <section class="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_16px_40px_-30px_rgba(15,23,42,0.14)]">
                  <div class="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                    <div>
                      <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-sky-700">Step 3</p>
                      <h3 class="mt-2 text-sm font-bold tracking-wide text-neutral-800 uppercase">Lease &amp; Occupancy</h3>
                    </div>
                    <p class="text-xs text-slate-500">Capture the lease window and basic occupancy metrics for ledger continuity.</p>
                  </div>

                  <div class="mt-5 grid gap-4 sm:grid-cols-2">
                    <label>
                      <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Lease Start</span>
                      <DateInput bind:value={form.lease_start_date} />
                    </label>

                    <label>
                      <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Lease End</span>
                      <DateInput bind:value={form.lease_end_date} />
                    </label>

                    <label>
                      <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Move In</span>
                      <DateInput bind:value={form.move_in_date} />
                    </label>

                    <label>
                      <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Move Out</span>
                      <DateInput bind:value={form.move_out_date} />
                    </label>

                    <label class="sm:col-span-2">
                      <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Occupant Count</span>
                      <input
                        bind:value={form.occupant_count}
                        type="number"
                        min="1"
                        step="1"
                        class="w-full rounded-2xl border border-white/70 bg-white/85 px-4 py-2.5 text-sm text-slate-700 shadow-sm backdrop-blur focus:border-slate-300 focus:outline-none"
                      />
                    </label>
                  </div>
                </section>
              {:else}
                <div class="space-y-4">
                  <section class="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_16px_40px_-30px_rgba(15,23,42,0.14)]">
                    <div class="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                      <div>
                        <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-amber-700">Step 4</p>
                        <h3 class="mt-2 text-sm font-bold tracking-wide text-neutral-800 uppercase">Review &amp; Notes</h3>
                      </div>
                      <p class="text-xs text-slate-500">Confirm the ledger record before it is created.</p>
                    </div>

                    <label class="mt-5 block">
                      <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Internal Notes</span>
                      <textarea
                        bind:value={form.notes}
                        rows="5"
                        class="w-full rounded-2xl border border-white/70 bg-white/85 px-4 py-3 text-sm text-slate-700 shadow-sm backdrop-blur focus:border-slate-300 focus:outline-none"
                        placeholder="Lease notes, onboarding context, or special handling."
                      ></textarea>
                    </label>
                  </section>

                  <section class="rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_16px_40px_-30px_rgba(15,23,42,0.14)]">
                    <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">Review Summary</p>
                    <div class="mt-4 grid gap-4 sm:grid-cols-2">
                      <div class="rounded-2xl border border-slate-200/80 bg-slate-50/70 p-4">
                        <p class="text-xs uppercase tracking-[0.18em] text-slate-400">Identity</p>
                        <p class="mt-2 text-sm font-semibold text-slate-950">{suggestedDisplayName()}</p>
                        <p class="mt-2 text-sm text-slate-600">
                          {tenantTypeOptions.find((option) => option.value === form.tenant_type)?.label ?? "Corporate"} · {statusOptions.find((option) => option.value === form.status)?.label ?? "Pending Move In"}
                        </p>
                      </div>
                      <div class="rounded-2xl border border-slate-200/80 bg-slate-50/70 p-4">
                        <p class="text-xs uppercase tracking-[0.18em] text-slate-400">Assignment</p>
                        <p class="mt-2 text-sm font-semibold text-slate-950">
                          {propertyOptions().find((item) => String(item.id) === form.property)?.name || "Unassigned property"}
                        </p>
                        <p class="mt-2 text-sm text-slate-600">
                          {filteredUnits().find((item) => String(item.id) === form.unit)?.label || filteredSpaces().find((item) => String(item.id) === form.facility_space)?.label || "No unit or space selected"}
                        </p>
                      </div>
                      <div class="rounded-2xl border border-slate-200/80 bg-slate-50/70 p-4">
                        <p class="text-xs uppercase tracking-[0.18em] text-slate-400">Lease Window</p>
                        <p class="mt-2 text-sm font-semibold text-slate-950">{fmtDate(form.lease_start_date || null)} - {fmtDate(form.lease_end_date || null)}</p>
                        <p class="mt-2 text-sm text-slate-600">Move {fmtDate(form.move_in_date || null)} - {fmtDate(form.move_out_date || null)}</p>
                      </div>
                      <div class="rounded-2xl border border-slate-200/80 bg-slate-50/70 p-4">
                        <p class="text-xs uppercase tracking-[0.18em] text-slate-400">Occupancy</p>
                        <p class="mt-2 text-sm font-semibold text-slate-950">{fmtInt(form.occupant_count || 1)} occupants</p>
                        <p class="mt-2 text-sm text-slate-600">{form.notes.trim() ? "Notes ready to save" : "No internal notes added yet"}</p>
                      </div>
                    </div>
                  </section>
                </div>
              {/if}
            </div>

            <div class="flex items-center justify-between gap-3 border-t border-slate-200/80 px-6 py-4">
              <div class="flex items-center gap-2">
                <button
                  type="button"
                  onclick={onboardingStep === 0 ? closeOnboardingModal : previousOnboardingStep}
                  class="inline-flex items-center rounded-full border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:border-slate-300"
                >
                  {onboardingStep === 0 ? "Cancel" : "Back"}
                </button>
                {#if isDev}
                  <button type="button" onclick={devFillTenant} class="rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>
                {/if}
              </div>

              <div class="flex items-center gap-2">
                <span class="text-xs text-slate-500">Step {onboardingStep + 1} of {onboardingSteps.length}</span>
                {#if onboardingStep < onboardingSteps.length - 1}
                  <button
                    type="button"
                    onclick={nextOnboardingStep}
                    class="inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 px-4 py-2.5 text-sm font-semibold text-emerald-700 transition hover:border-emerald-300"
                  >
                    Continue
                  </button>
                {:else}
                  <button
                    type="button"
                    onclick={submitOnboarding}
                    disabled={saving}
                    class="inline-flex items-center rounded-full border border-emerald-600 bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {saving ? "Creating..." : "Create Tenant"}
                  </button>
                {/if}
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
{/if}

{#if showDrawer}
  <div class="fixed inset-0 z-50">
    <button
      type="button"
      class="absolute inset-0 bg-slate-950/38 backdrop-blur-[2px]"
      onclick={closeDrawer}
      aria-label="Close tenant registry drawer"
    ></button>

    <aside class="absolute inset-y-0 right-0 flex w-full max-w-176">
      <div class="ml-auto flex h-full w-full flex-col overflow-hidden border-l border-slate-200/80 bg-white shadow-[-24px_0_70px_-42px_rgba(15,23,42,0.38)]">
        <div class="flex items-start justify-between gap-4 border-b border-slate-200/80 px-5 py-5">
          <div>
            <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-sky-700">2. Tenant Registry (Master Data)</p>
            <h2 class="mt-2 text-sm font-bold tracking-wide text-neutral-800 uppercase">
              {editingTenantId ? "Edit Tenant" : "Add Tenant"}
            </h2>
            <p class="mt-2 text-sm text-slate-600">
              Maintain tenant identity, linked records, location mapping, and lease metadata from a single drawer.
            </p>
          </div>
          <button
            type="button"
            onclick={closeDrawer}
            class="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200/80 bg-white text-slate-700 shadow-sm hover:text-slate-950"
            aria-label="Close tenant registry drawer"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8" aria-hidden="true">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="flex-1 overflow-y-auto px-5 py-5">
          <div class="space-y-5">
            <section class="rounded-xl border border-slate-200/80 bg-white p-5 shadow-[0_16px_40px_-30px_rgba(15,23,42,0.14)]">
              <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-sky-700">Identity &amp; Links</p>
              <div class="mt-4 grid gap-4 sm:grid-cols-2">
                <label class="sm:col-span-2">
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Display Name</span>
                  <input
                    bind:value={form.display_name}
                    type="text"
                    class="w-full rounded-2xl border border-white/70 bg-white/85 px-4 py-2.5 text-sm text-slate-700 shadow-sm backdrop-blur focus:border-slate-300 focus:outline-none"
                    placeholder="Tenant display name"
                  />
                </label>

                <label>
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Customer</span>
                  <select
                    bind:value={form.customer}
                    onchange={() => autofillDisplayName()}
                    class="w-full rounded-2xl border border-white/70 bg-white/85 px-4 py-2.5 text-sm text-slate-700 shadow-sm backdrop-blur focus:border-slate-300 focus:outline-none"
                  >
                    <option value="">None</option>
                    {#each lookups?.customers ?? [] as customer}
                      <option value={String(customer.id)}>{customer.name}</option>
                    {/each}
                  </select>
                </label>

                <label>
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Contact Account</span>
                  <select
                    bind:value={form.contact_account}
                    onchange={() => autofillDisplayName()}
                    class="w-full rounded-2xl border border-white/70 bg-white/85 px-4 py-2.5 text-sm text-slate-700 shadow-sm backdrop-blur focus:border-slate-300 focus:outline-none"
                  >
                    <option value="">None</option>
                    {#each lookups?.contact_accounts ?? [] as contact}
                      <option value={String(contact.id)}>{contact.name}</option>
                    {/each}
                  </select>
                </label>

                <label class="sm:col-span-2">
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Primary User</span>
                  <select
                    bind:value={form.primary_user}
                    onchange={() => autofillDisplayName()}
                    class="w-full rounded-2xl border border-white/70 bg-white/85 px-4 py-2.5 text-sm text-slate-700 shadow-sm backdrop-blur focus:border-slate-300 focus:outline-none"
                  >
                    <option value="">None</option>
                    {#each lookups?.users ?? [] as user}
                      <option value={String(user.id)}>{user.name}</option>
                    {/each}
                  </select>
                </label>

                <label>
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Tenant Type</span>
                  <select
                    bind:value={form.tenant_type}
                    class="w-full rounded-2xl border border-white/70 bg-white/85 px-4 py-2.5 text-sm text-slate-700 shadow-sm backdrop-blur focus:border-slate-300 focus:outline-none"
                  >
                    {#each tenantTypeOptions as option}
                      <option value={option.value}>{option.label}</option>
                    {/each}
                  </select>
                </label>

                <label>
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Status</span>
                  <select
                    bind:value={form.status}
                    class="w-full rounded-2xl border border-white/70 bg-white/85 px-4 py-2.5 text-sm text-slate-700 shadow-sm backdrop-blur focus:border-slate-300 focus:outline-none"
                  >
                    {#each statusOptions as option}
                      <option value={option.value}>{option.label}</option>
                    {/each}
                  </select>
                </label>
              </div>
            </section>

            <section class="rounded-xl border border-slate-200/80 bg-white p-5 shadow-[0_16px_40px_-30px_rgba(15,23,42,0.14)]">
              <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-violet-700">Assignment</p>
              <div class="mt-4 grid gap-4 sm:grid-cols-2">
                <label class="sm:col-span-2">
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Property</span>
                  <select
                    bind:value={form.property}
                    onchange={(event) => handlePropertyChange((event.currentTarget as HTMLSelectElement).value)}
                    class="w-full rounded-2xl border border-white/70 bg-white/85 px-4 py-2.5 text-sm text-slate-700 shadow-sm backdrop-blur focus:border-slate-300 focus:outline-none"
                  >
                    <option value="">None</option>
                    {#each propertyOptions() as propertyRecord}
                      <option value={String(propertyRecord.id)}>{propertyRecord.name}</option>
                    {/each}
                  </select>
                </label>

                <label>
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Facility</span>
                  <select
                    bind:value={form.facility}
                    onchange={(event) => handleFacilityChange((event.currentTarget as HTMLSelectElement).value)}
                    class="w-full rounded-2xl border border-white/70 bg-white/85 px-4 py-2.5 text-sm text-slate-700 shadow-sm backdrop-blur focus:border-slate-300 focus:outline-none"
                  >
                    <option value="">None</option>
                    {#each filteredFacilities() as facility}
                      <option value={String(facility.id)}>{facility.label}</option>
                    {/each}
                  </select>
                </label>

                <label>
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Unit</span>
                  <select
                    bind:value={form.unit}
                    onchange={(event) => handleUnitChange((event.currentTarget as HTMLSelectElement).value)}
                    class="w-full rounded-2xl border border-white/70 bg-white/85 px-4 py-2.5 text-sm text-slate-700 shadow-sm backdrop-blur focus:border-slate-300 focus:outline-none"
                  >
                    <option value="">None</option>
                    {#each filteredUnits() as unit}
                      <option value={String(unit.id)}>{unit.label}</option>
                    {/each}
                  </select>
                </label>

                <label class="sm:col-span-2">
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Facility Space</span>
                  <select
                    bind:value={form.facility_space}
                    onchange={(event) => handleSpaceChange((event.currentTarget as HTMLSelectElement).value)}
                    class="w-full rounded-2xl border border-white/70 bg-white/85 px-4 py-2.5 text-sm text-slate-700 shadow-sm backdrop-blur focus:border-slate-300 focus:outline-none"
                  >
                    <option value="">None</option>
                    {#each filteredSpaces() as space}
                      <option value={String(space.id)}>{space.label}</option>
                    {/each}
                  </select>
                  <p class="mt-2 text-xs text-slate-500">
                    Selecting a mapped space automatically aligns the facility, unit, and property.
                  </p>
                </label>
              </div>
            </section>

            <section class="rounded-xl border border-slate-200/80 bg-white p-5 shadow-[0_16px_40px_-30px_rgba(15,23,42,0.14)]">
              <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-emerald-700">Lease &amp; Occupancy</p>
              <div class="mt-4 grid gap-4 sm:grid-cols-2">
                <label>
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Lease Start</span>
                  <DateInput bind:value={form.lease_start_date} />
                </label>

                <label>
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Lease End</span>
                  <DateInput bind:value={form.lease_end_date} />
                </label>

                <label>
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Move In</span>
                  <DateInput bind:value={form.move_in_date} />
                </label>

                <label>
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Move Out</span>
                  <DateInput bind:value={form.move_out_date} />
                </label>

                <label class="sm:col-span-2">
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Occupant Count</span>
                  <input
                    bind:value={form.occupant_count}
                    type="number"
                    min="1"
                    step="1"
                    class="w-full rounded-2xl border border-white/70 bg-white/85 px-4 py-2.5 text-sm text-slate-700 shadow-sm backdrop-blur focus:border-slate-300 focus:outline-none"
                  />
                </label>
              </div>
            </section>

            <section class="rounded-xl border border-slate-200/80 bg-white p-5 shadow-[0_16px_40px_-30px_rgba(15,23,42,0.14)]">
              <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-amber-700">Notes</p>
              <label class="mt-4 block">
                <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Internal Notes</span>
                <textarea
                  bind:value={form.notes}
                  rows="5"
                  class="w-full rounded-2xl border border-white/70 bg-white/85 px-4 py-3 text-sm text-slate-700 shadow-sm backdrop-blur focus:border-slate-300 focus:outline-none"
                  placeholder="Lease notes, onboarding context, or special handling."
                ></textarea>
              </label>
            </section>
          </div>
        </div>

        <div class="border-t border-slate-200/80 px-5 py-4">
          <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <p class="text-xs text-slate-500">
              Registry automations derive property and occupancy context where possible and prevent duplicate active assignments.
            </p>
            <div class="flex items-center gap-2">
              {#if isDev && !editingTenantId}
                <button type="button" onclick={devFillTenant} class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>
              {/if}
              <button
                type="button"
                onclick={closeDrawer}
                class="inline-flex items-center rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-300"
              >
                Cancel
              </button>
              <button
                type="button"
                onclick={submitForm}
                disabled={saving}
                class="inline-flex items-center rounded-full border border-sky-200 bg-sky-50 px-4 py-2 text-sm font-semibold text-sky-700 transition hover:border-sky-300 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {saving ? "Saving..." : editingTenantId ? "Save Changes" : "Create Tenant"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </aside>
  </div>
{/if}

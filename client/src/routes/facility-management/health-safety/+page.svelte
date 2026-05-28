<script lang="ts">
  import { ApiError, api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { PaginatedResponse } from "$lib/types";

  type HealthSafetyTab = "incidents" | "inspections" | "checklists" | "documents" | "audit";
  type IncidentCategory = "safety" | "security" | "fire" | "environmental" | "health" | "other";
  type IncidentSeverity = "low" | "medium" | "high" | "critical";
  type IncidentStatus = "open" | "investigating" | "resolved" | "closed";
  type InspectionStatus = "scheduled" | "in_progress" | "completed" | "cancelled";
  type ChecklistStatus = "draft" | "active" | "in_progress" | "completed" | "overdue" | "cancelled";
  type ChecklistFrequency = "one_time" | "daily" | "weekly" | "monthly" | "quarterly" | "annual";
  type RegulatoryDocumentStatus = "pending_review" | "valid" | "expiring_soon" | "expired" | "superseded";
  type AuditEntityType = "incident" | "inspection" | "checklist" | "document" | "compliance" | "workflow";
  type PropertyDocumentType =
    | "permit"
    | "inspection"
    | "insurance"
    | "government_approval"
    | "certificate_of_occupancy"
    | "other";

  interface LookupUserItem {
    id: number;
    label: string;
    email: string;
  }

  interface LookupFacilityItem {
    id: number;
    facility_code: string;
    property_name: string;
  }

  interface LookupSpaceItem {
    id: number;
    facility: number;
    facility_code: string;
    zone_code: string;
    zone_name: string;
    unit_number: string;
    space_label: string;
    property_name: string;
  }

  interface LookupRequirementItem {
    id: number;
    name: string;
    category: string;
    category_display: string;
  }

  interface FacilityIncidentItem {
    id: number;
    incident_code: string;
    property: number | null;
    property_name: string;
    facility: number | null;
    facility_code: string;
    facility_space: number | null;
    space_label: string;
    unit_number: string;
    work_order: number | null;
    work_order_status: string;
    follow_up_inspection: number | null;
    follow_up_inspection_status: string;
    title: string;
    description: string;
    category: IncidentCategory;
    category_display: string;
    severity: IncidentSeverity;
    severity_display: string;
    status: IncidentStatus;
    status_display: string;
    occurred_at: string;
    resolved_at: string | null;
    reported_by: string;
    assigned_to: string;
    requires_regulatory_report: boolean;
    created_at: string;
    updated_at: string;
  }

  interface FacilityInspectionItem {
    id: number;
    property: number;
    property_name: string;
    facility: number | null;
    facility_code: string;
    facility_space: number | null;
    space_label: string;
    unit: number | null;
    unit_number: string;
    linked_incident: number | null;
    linked_incident_code: string;
    title: string;
    inspection_type: string;
    inspection_type_display: string;
    status: InspectionStatus;
    status_display: string;
    scheduled_date: string;
    completed_date: string | null;
    inspector: string;
    findings: string;
    rating: string;
    rating_display: string;
    risk_level: string;
    risk_level_display: string;
    corrective_action_required: boolean;
    compliance_status: string;
    compliance_status_display: string;
    expiry_date: string | null;
    follow_up_required: boolean;
    follow_up_notes: string;
    notes: string;
    created_at: string;
    updated_at: string;
  }

  interface FacilityChecklistItem {
    id: number;
    property: number;
    property_name: string;
    facility: number | null;
    facility_code: string;
    facility_space: number | null;
    space_label: string;
    linked_incident: number | null;
    linked_incident_code: string;
    linked_inspection: number | null;
    linked_inspection_title: string;
    compliance_requirement: number | null;
    compliance_requirement_name: string;
    title: string;
    checklist_type: string;
    checklist_type_display: string;
    frequency: ChecklistFrequency;
    status: ChecklistStatus;
    status_display: string;
    responsible_person: string;
    due_date: string;
    completed_at: string | null;
    last_completed_date: string | null;
    next_due_date: string | null;
    overall_score: string;
    compliant_items_count: number;
    total_items_count: number;
    failure_count: number;
    auto_create_violation: boolean;
    auto_create_follow_up_inspection: boolean;
    notes: string;
    created_at: string;
    updated_at: string;
  }

  interface FacilityRegulatoryDocumentItem {
    id: number;
    property: number;
    property_name: string;
    facility: number | null;
    facility_code: string;
    property_document: number;
    title: string;
    description: string;
    document_type: string;
    document_type_display: string;
    file_url: string;
    compliance_requirement: number | null;
    compliance_requirement_name: string;
    status: RegulatoryDocumentStatus;
    status_display: string;
    issuing_authority: string;
    reference_number: string;
    issue_date: string | null;
    expiry_date: string | null;
    review_due_date: string | null;
    uploaded_by: number | null;
    uploaded_by_name: string;
    notes: string;
    created_at: string;
    updated_at: string;
  }

  interface FacilityComplianceViolationItem {
    id: number;
    property: number;
    property_name: string;
    title: string;
    description: string;
    violation_type: string;
    severity: string;
    severity_display: string;
    status: string;
    status_display: string;
    reported_date: string;
    due_date: string | null;
    resolved_date: string | null;
    corrective_action: string;
    assigned_to: string;
    created_at: string;
    updated_at: string;
  }

  interface FacilityAuditLogItem {
    id: number;
    property: number | null;
    property_name: string;
    facility: number | null;
    facility_code: string;
    entity_type: AuditEntityType;
    entity_type_display: string;
    event_type: string;
    event_type_display: string;
    entity_id: number | null;
    actor: number | null;
    actor_name: string;
    summary: string;
    details: Record<string, unknown>;
    created_at: string;
  }

  interface HealthSafetyOverview {
    generated_at: string;
    kpis: {
      open_incidents: number;
      critical_incidents: number;
      investigating_incidents: number;
      scheduled_inspections: number;
      overdue_inspections: number;
      open_checklists: number;
      overdue_checklists: number;
      total_regulatory_documents: number;
      expiring_documents: number;
      expired_documents: number;
      open_violations: number;
      audit_events_7d: number;
    };
    incident_watchlist: FacilityIncidentItem[];
    inspection_watchlist: FacilityInspectionItem[];
    checklist_watchlist: FacilityChecklistItem[];
    document_watchlist: FacilityRegulatoryDocumentItem[];
    violation_watchlist: FacilityComplianceViolationItem[];
    audit_log_watchlist: FacilityAuditLogItem[];
  }

  interface HealthSafetyLookupsResponse {
    users: LookupUserItem[];
    facilities: LookupFacilityItem[];
    spaces: LookupSpaceItem[];
    compliance_requirements: LookupRequirementItem[];
    incidents: FacilityIncidentItem[];
    inspections: FacilityInspectionItem[];
  }

  interface WorkflowSyncResult {
    incidents_synced: number;
    incidents_resolved: number;
    follow_up_inspections_created: number;
    corrective_work_orders_created: number;
    inspections_synced: number;
    checklists_synced: number;
    checklist_failures: number;
    compliance_records_synced: number;
    violations_created: number;
    regulatory_documents_synced: number;
    expired_documents_flagged: number;
    audit_logs_created: number;
  }

  interface ChecklistItemFormRow {
    title: string;
    description: string;
    is_mandatory: boolean;
    is_compliant: "pending" | "true" | "false";
    response_note: string;
    corrective_action: string;
    sort_order: number;
  }

  const tabs: { key: HealthSafetyTab; label: string }[] = [
    { key: "incidents", label: "Incident Reporting" },
    { key: "inspections", label: "Safety Inspections" },
    { key: "checklists", label: "Compliance Checklists" },
    { key: "documents", label: "Regulatory Documentation" },
    { key: "audit", label: "Audit Logs" },
  ];

  const incidentCategoryOptions: { value: IncidentCategory; label: string }[] = [
    { value: "fire", label: "Fire" },
    { value: "safety", label: "Safety" },
    { value: "health", label: "Health" },
    { value: "environmental", label: "Environmental" },
    { value: "security", label: "Security" },
    { value: "other", label: "Other" },
  ];

  const incidentSeverityOptions: { value: IncidentSeverity; label: string }[] = [
    { value: "critical", label: "Critical" },
    { value: "high", label: "High" },
    { value: "medium", label: "Medium" },
    { value: "low", label: "Low" },
  ];

  const inspectionTypeOptions: { value: string; label: string }[] = [
    { value: "safety", label: "Safety" },
    { value: "fire_safety", label: "Fire Safety" },
    { value: "electrical", label: "Electrical Inspection" },
    { value: "health_safety", label: "Health & Safety" },
    { value: "environmental_audit", label: "Environmental Audit" },
    { value: "compliance", label: "Compliance" },
    { value: "post_incident", label: "Post-Incident" },
  ];

  const inspectionStatusOptions: { value: InspectionStatus; label: string }[] = [
    { value: "scheduled", label: "Scheduled" },
    { value: "in_progress", label: "In Progress" },
    { value: "completed", label: "Completed" },
    { value: "cancelled", label: "Cancelled" },
  ];

  const inspectionRatingOptions: { value: string; label: string }[] = [
    { value: "pass", label: "Pass" },
    { value: "conditional", label: "Conditional Pass" },
    { value: "fail", label: "Fail" },
  ];

  const inspectionRiskOptions: { value: string; label: string }[] = [
    { value: "critical", label: "Critical" },
    { value: "high", label: "High" },
    { value: "medium", label: "Medium" },
    { value: "low", label: "Low" },
  ];

  const inspectionComplianceOptions: { value: string; label: string }[] = [
    { value: "non_compliant", label: "Non-Compliant" },
    { value: "partially_compliant", label: "Partially Compliant" },
    { value: "compliant", label: "Compliant" },
    { value: "pending_review", label: "Pending Review" },
  ];

  const checklistTypeOptions: { value: string; label: string }[] = [
    { value: "safety", label: "Safety" },
    { value: "fire_safety", label: "Fire Safety" },
    { value: "electrical", label: "Electrical" },
    { value: "environmental", label: "Environmental" },
    { value: "occupational_health", label: "Occupational Health" },
    { value: "regulatory", label: "Regulatory" },
    { value: "housekeeping", label: "Housekeeping" },
    { value: "incident_follow_up", label: "Incident Follow-Up" },
  ];

  const checklistFrequencyOptions: { value: ChecklistFrequency; label: string }[] = [
    { value: "one_time", label: "One-Time" },
    { value: "daily", label: "Daily" },
    { value: "weekly", label: "Weekly" },
    { value: "monthly", label: "Monthly" },
    { value: "quarterly", label: "Quarterly" },
    { value: "annual", label: "Annual" },
  ];

  const checklistStatusOptions: { value: ChecklistStatus; label: string }[] = [
    { value: "active", label: "Active" },
    { value: "in_progress", label: "In Progress" },
    { value: "completed", label: "Completed" },
    { value: "overdue", label: "Overdue" },
    { value: "draft", label: "Draft" },
    { value: "cancelled", label: "Cancelled" },
  ];

  const regulatoryDocumentTypeOptions: { value: PropertyDocumentType; label: string }[] = [
    { value: "permit", label: "Permit" },
    { value: "inspection", label: "Inspection Report" },
    { value: "insurance", label: "Insurance" },
    { value: "government_approval", label: "Government Approval" },
    { value: "certificate_of_occupancy", label: "Certificate of Occupancy" },
    { value: "other", label: "Other" },
  ];

  const tabsWithCreateAction = new Set<HealthSafetyTab>(["incidents", "inspections", "checklists", "documents"]);
  const operationalRegisterPageSize = 8;

  let activeTab = $state<HealthSafetyTab>("incidents");
  let loading = $state(true);
  let refreshing = $state(false);
  let syncingWorkflows = $state(false);

  let overview = $state<HealthSafetyOverview | null>(null);
  let incidents = $state<FacilityIncidentItem[]>([]);
  let inspections = $state<FacilityInspectionItem[]>([]);
  let checklists = $state<FacilityChecklistItem[]>([]);
  let regulatoryDocuments = $state<FacilityRegulatoryDocumentItem[]>([]);
  let auditLogs = $state<FacilityAuditLogItem[]>([]);

  let usersLookup = $state<LookupUserItem[]>([]);
  let facilitiesLookup = $state<LookupFacilityItem[]>([]);
  let spacesLookup = $state<LookupSpaceItem[]>([]);
  let requirementsLookup = $state<LookupRequirementItem[]>([]);
  let incidentLookup = $state<FacilityIncidentItem[]>([]);
  let inspectionLookup = $state<FacilityInspectionItem[]>([]);

  let incidentSearch = $state("");
  let incidentFacilityFilter = $state("");
  let incidentStatusFilter = $state("");

  let inspectionSearch = $state("");
  let inspectionFacilityFilter = $state("");
  let inspectionStatusFilter = $state("");

  let checklistSearch = $state("");
  let checklistStatusFilter = $state("");

  let documentSearch = $state("");
  let documentStatusFilter = $state("");

  let auditSearch = $state("");
  let auditEntityFilter = $state("");

  let incidentPage = $state(1);
  let inspectionPage = $state(1);
  let checklistPage = $state(1);
  let documentPage = $state(1);
  let auditPage = $state(1);

  let showIncidentDrawer = $state(false);
  let showInspectionDrawer = $state(false);
  let showChecklistDrawer = $state(false);
  let showDocumentDrawer = $state(false);

  let incidentSaving = $state(false);
  let inspectionSaving = $state(false);
  let checklistSaving = $state(false);
  let documentSaving = $state(false);
  let selectedRegulatoryFile = $state<File | null>(null);

  let incidentForm = $state({
    facility: "",
    facility_space: "",
    title: "",
    description: "",
    category: "safety" as IncidentCategory,
    severity: "medium" as IncidentSeverity,
    status: "open" as IncidentStatus,
    occurred_at: dateTimeInput(-1),
    assigned_to: "",
    requires_regulatory_report: false,
  });

  let inspectionForm = $state({
    facility: "",
    facility_space: "",
    incident: "",
    title: "",
    inspection_type: "safety",
    status: "scheduled" as InspectionStatus,
    scheduled_date: todayInput(),
    completed_date: "",
    inspector: "",
    findings: "",
    rating: "",
    risk_level: "",
    corrective_action_required: false,
    compliance_status: "",
    expiry_date: "",
    follow_up_required: false,
    follow_up_notes: "",
    notes: "",
  });

  let checklistForm = $state({
    facility: "",
    facility_space: "",
    linked_incident: "",
    linked_inspection: "",
    compliance_requirement: "",
    title: "",
    checklist_type: "safety",
    frequency: "one_time" as ChecklistFrequency,
    status: "active" as ChecklistStatus,
    responsible_person: "",
    due_date: todayInput(),
    completed_at: "",
    auto_create_violation: true,
    auto_create_follow_up_inspection: false,
    notes: "",
  });

  let checklistItems = $state<ChecklistItemFormRow[]>([]);

  let documentForm = $state({
    facility: "",
    title: "",
    document_type: "permit" as PropertyDocumentType,
    description: "",
    compliance_requirement: "",
    issuing_authority: "",
    reference_number: "",
    issue_date: todayInput(),
    expiry_date: "",
    review_due_date: "",
    notes: "",
  });

  function todayInput(offsetDays = 0): string {
    const value = new Date();
    value.setDate(value.getDate() + offsetDays);
    return value.toISOString().slice(0, 10);
  }

  function dateTimeInput(offsetHours = 0): string {
    const value = new Date();
    value.setHours(value.getHours() + offsetHours);
    return value.toISOString().slice(0, 16);
  }

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  function devFillIncident() {
    const titles = ["Slip and fall near wet floor — Block A lobby", "Electrical panel sparking — Basement B2", "Fire alarm triggered — Zone 4 kitchen area", "Gas leak detected — Generator room", "Scaffolding collapse — Construction Phase 2", "Chemical spill in maintenance workshop"];
    const cats: IncidentCategory[] = ["safety", "fire", "environmental", "structural", "electrical", "chemical"];
    const sevs: IncidentSeverity[] = ["low", "medium", "high", "critical"];
    const idx = Math.floor(Math.random() * titles.length);
    incidentForm.title = titles[idx];
    incidentForm.description = `${titles[idx]}. Immediate area was cordoned off and first response team notified. No injuries reported at this time.`;
    incidentForm.category = cats[idx % cats.length];
    incidentForm.severity = sevs[Math.floor(Math.random() * sevs.length)];
    incidentForm.status = "open";
    incidentForm.occurred_at = dateTimeInput(-1);
    incidentForm.requires_regulatory_report = incidentForm.severity === "critical" || incidentForm.severity === "high";
    if (facilitiesLookup.length > 0 && !incidentForm.facility) incidentForm.facility = String(facilitiesLookup[0].id);
  }

  function devFillInspection() {
    const titles = ["Quarterly fire safety inspection", "Monthly elevator safety check", "Annual structural integrity assessment", "Bi-weekly electrical panel inspection", "Emergency exit route verification"];
    const types = ["safety", "fire", "structural", "electrical", "environmental"];
    const ratings = ["excellent", "good", "satisfactory", "needs_improvement", "unsatisfactory"];
    const idx = Math.floor(Math.random() * titles.length);
    inspectionForm.title = titles[idx];
    inspectionForm.inspection_type = types[idx % types.length];
    inspectionForm.status = "scheduled";
    inspectionForm.scheduled_date = todayInput(7);
    inspectionForm.inspector = "External Safety Assessor";
    inspectionForm.findings = "Inspection pending — findings to be documented upon completion.";
    inspectionForm.rating = ratings[Math.floor(Math.random() * ratings.length)];
    inspectionForm.risk_level = ["low", "medium", "high"][Math.floor(Math.random() * 3)];
    inspectionForm.corrective_action_required = Math.random() > 0.5;
    inspectionForm.follow_up_required = Math.random() > 0.6;
    inspectionForm.follow_up_notes = inspectionForm.follow_up_required ? "Schedule follow-up inspection within 30 days." : "";
    inspectionForm.notes = "Ensure all areas are accessible before scheduled date.";
    if (facilitiesLookup.length > 0 && !inspectionForm.facility) inspectionForm.facility = String(facilitiesLookup[0].id);
    if (incidentLookup.length > 0 && !inspectionForm.incident) inspectionForm.incident = String(incidentLookup[0].id);
  }

  function devFillChecklist() {
    const titles = ["Daily fire exit clearance check", "Weekly emergency equipment verification", "Monthly first aid kit inventory", "Quarterly evacuation drill checklist", "Annual safety training compliance"];
    const types = ["safety", "fire", "environmental", "maintenance", "compliance"];
    const freqs: ChecklistFrequency[] = ["one_time", "daily", "weekly", "monthly", "quarterly", "annually"];
    const idx = Math.floor(Math.random() * titles.length);
    checklistForm.title = titles[idx];
    checklistForm.checklist_type = types[idx % types.length];
    checklistForm.frequency = freqs[Math.floor(Math.random() * freqs.length)];
    checklistForm.status = "active";
    checklistForm.responsible_person = "Facilities Safety Officer";
    checklistForm.due_date = todayInput(14);
    checklistForm.auto_create_violation = true;
    checklistForm.auto_create_follow_up_inspection = Math.random() > 0.5;
    checklistForm.notes = "Ensure all items are checked and signed off by the responsible person.";
    if (facilitiesLookup.length > 0 && !checklistForm.facility) checklistForm.facility = String(facilitiesLookup[0].id);
    if (requirementsLookup.length > 0 && !checklistForm.compliance_requirement) checklistForm.compliance_requirement = String(requirementsLookup[0].id);
  }

  function devFillDocument() {
    const titles = ["Fire Safety Certificate", "Building Occupancy Permit", "Environmental Impact Assessment", "Electrical Safety Compliance Report", "Structural Integrity Certificate"];
    const types: PropertyDocumentType[] = ["permit", "certificate", "license", "report", "compliance"];
    const authorities = ["Lagos State Safety Commission", "Federal Ministry of Environment", "LASBCA", "Standards Organisation of Nigeria", "State Fire Service"];
    const idx = Math.floor(Math.random() * titles.length);
    documentForm.title = titles[idx];
    documentForm.document_type = types[idx % types.length];
    documentForm.description = `${titles[idx]} — issued following successful completion of all regulatory requirements.`;
    documentForm.issuing_authority = authorities[idx % authorities.length];
    documentForm.reference_number = `REG-${Math.floor(Math.random() * 90000) + 10000}`;
    documentForm.issue_date = todayInput(-30);
    documentForm.expiry_date = todayInput(335);
    documentForm.review_due_date = todayInput(300);
    documentForm.notes = "Keep original copy in the facility safe. Digital copy uploaded.";
    if (facilitiesLookup.length > 0 && !documentForm.facility) documentForm.facility = String(facilitiesLookup[0].id);
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

  function fmtInt(value: unknown): string {
    const parsed = Number(value ?? 0);
    return Number.isFinite(parsed) ? parsed.toLocaleString("en-US") : "0";
  }

  function parseApiMessage(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      if (typeof error.data.detail === "string") return error.data.detail;
      const firstField = Object.values(error.fieldErrors)[0]?.[0];
      if (typeof firstField === "string") return firstField;
    }
    return fallback;
  }

  function incidentSeverityBadge(value: IncidentSeverity): string {
    if (value === "critical") return "bg-red-100 text-red-700";
    if (value === "high") return "bg-amber-100 text-amber-700";
    if (value === "low") return "bg-sky-100 text-sky-700";
    return "bg-neutral-100 text-neutral-700";
  }

  function incidentStatusBadge(value: IncidentStatus): string {
    if (value === "resolved" || value === "closed") return "bg-emerald-100 text-emerald-700";
    if (value === "investigating") return "bg-amber-100 text-amber-700";
    return "bg-rose-100 text-rose-700";
  }

  function inspectionStatusBadge(value: InspectionStatus): string {
    if (value === "completed") return "bg-emerald-100 text-emerald-700";
    if (value === "in_progress") return "bg-amber-100 text-amber-700";
    if (value === "cancelled") return "bg-neutral-100 text-neutral-600";
    return "bg-sky-100 text-sky-700";
  }

  function checklistStatusBadge(value: ChecklistStatus): string {
    if (value === "completed") return "bg-emerald-100 text-emerald-700";
    if (value === "overdue") return "bg-red-100 text-red-700";
    if (value === "in_progress") return "bg-amber-100 text-amber-700";
    if (value === "cancelled") return "bg-neutral-100 text-neutral-600";
    if (value === "draft") return "bg-neutral-100 text-neutral-700";
    return "bg-sky-100 text-sky-700";
  }

  function documentStatusBadge(value: RegulatoryDocumentStatus): string {
    if (value === "expired") return "bg-red-100 text-red-700";
    if (value === "expiring_soon") return "bg-amber-100 text-amber-700";
    if (value === "valid") return "bg-emerald-100 text-emerald-700";
    if (value === "superseded") return "bg-neutral-100 text-neutral-600";
    return "bg-sky-100 text-sky-700";
  }

  function managementControlButtonClass(active: boolean, tone: "neutral" | "rose" | "amber" | "sky" | "emerald" | "violet" = "neutral"): string {
    const base = "inline-flex items-center rounded-full border px-3 py-1.5 text-xs font-medium transition";
    if (!active) return `${base} border-neutral-200 bg-white text-neutral-600 hover:border-neutral-300 hover:text-neutral-900`;
    if (tone === "rose") return `${base} border-rose-200 bg-rose-50 text-rose-700`;
    if (tone === "amber") return `${base} border-amber-200 bg-amber-50 text-amber-700`;
    if (tone === "sky") return `${base} border-sky-200 bg-sky-50 text-sky-700`;
    if (tone === "emerald") return `${base} border-emerald-200 bg-emerald-50 text-emerald-700`;
    if (tone === "violet") return `${base} border-violet-200 bg-violet-50 text-violet-700`;
    return `${base} border-neutral-300 bg-neutral-900 text-white`;
  }

  function totalPagesFor(totalItems: number): number {
    return Math.max(1, Math.ceil(totalItems / operationalRegisterPageSize));
  }

  function clampPage(page: number, totalItems: number): number {
    return Math.min(Math.max(page, 1), totalPagesFor(totalItems));
  }

  function pagedItems<T>(items: T[], page: number): T[] {
    const safePage = clampPage(page, items.length);
    const start = (safePage - 1) * operationalRegisterPageSize;
    return items.slice(start, start + operationalRegisterPageSize);
  }

  function pageStart(totalItems: number, page: number): number {
    if (totalItems === 0) return 0;
    return (clampPage(page, totalItems) - 1) * operationalRegisterPageSize + 1;
  }

  function pageEnd(totalItems: number, page: number): number {
    if (totalItems === 0) return 0;
    return Math.min(clampPage(page, totalItems) * operationalRegisterPageSize, totalItems);
  }

  function filteredSpacesFor(facilityId: string): LookupSpaceItem[] {
    if (!facilityId) return spacesLookup;
    return spacesLookup.filter((space) => space.facility === Number(facilityId));
  }

  function filteredIncidentOptions(facilityId: string): FacilityIncidentItem[] {
    if (!facilityId) return incidentLookup;
    return incidentLookup.filter((incident) => incident.facility === Number(facilityId));
  }

  function filteredInspectionOptions(facilityId: string): FacilityInspectionItem[] {
    if (!facilityId) return inspectionLookup;
    return inspectionLookup.filter((inspection) => inspection.facility === Number(facilityId));
  }

  function defaultChecklistItems(): ChecklistItemFormRow[] {
    return [
      {
        title: "",
        description: "",
        is_mandatory: true,
        is_compliant: "pending",
        response_note: "",
        corrective_action: "",
        sort_order: 1,
      },
    ];
  }

  function resetIncidentForm() {
    incidentForm = {
      facility: "",
      facility_space: "",
      title: "",
      description: "",
      category: "safety",
      severity: "medium",
      status: "open",
      occurred_at: dateTimeInput(-1),
      assigned_to: "",
      requires_regulatory_report: false,
    };
  }

  function resetInspectionForm() {
    inspectionForm = {
      facility: "",
      facility_space: "",
      incident: "",
      title: "",
      inspection_type: "safety",
      status: "scheduled",
      scheduled_date: todayInput(),
      completed_date: "",
      inspector: "",
      findings: "",
      rating: "",
      risk_level: "",
      corrective_action_required: false,
      compliance_status: "",
      expiry_date: "",
      follow_up_required: false,
      follow_up_notes: "",
      notes: "",
    };
  }

  function resetChecklistForm() {
    checklistForm = {
      facility: "",
      facility_space: "",
      linked_incident: "",
      linked_inspection: "",
      compliance_requirement: "",
      title: "",
      checklist_type: "safety",
      frequency: "one_time",
      status: "active",
      responsible_person: "",
      due_date: todayInput(),
      completed_at: "",
      auto_create_violation: true,
      auto_create_follow_up_inspection: false,
      notes: "",
    };
    checklistItems = defaultChecklistItems();
  }

  function resetDocumentForm() {
    documentForm = {
      facility: "",
      title: "",
      document_type: "permit",
      description: "",
      compliance_requirement: "",
      issuing_authority: "",
      reference_number: "",
      issue_date: todayInput(),
      expiry_date: "",
      review_due_date: "",
      notes: "",
    };
    selectedRegulatoryFile = null;
  }

  function openIncidentDrawer() {
    resetIncidentForm();
    showIncidentDrawer = true;
  }

  function openInspectionDrawer() {
    resetInspectionForm();
    showInspectionDrawer = true;
  }

  function openChecklistDrawer() {
    resetChecklistForm();
    showChecklistDrawer = true;
  }

  function openDocumentDrawer() {
    resetDocumentForm();
    showDocumentDrawer = true;
  }

  function closeIncidentDrawer() {
    showIncidentDrawer = false;
    resetIncidentForm();
  }

  function closeInspectionDrawer() {
    showInspectionDrawer = false;
    resetInspectionForm();
  }

  function closeChecklistDrawer() {
    showChecklistDrawer = false;
    resetChecklistForm();
  }

  function closeDocumentDrawer() {
    showDocumentDrawer = false;
    resetDocumentForm();
  }

  function openActiveDrawer() {
    if (activeTab === "incidents") {
      openIncidentDrawer();
      return;
    }
    if (activeTab === "inspections") {
      openInspectionDrawer();
      return;
    }
    if (activeTab === "checklists") {
      openChecklistDrawer();
      return;
    }
    if (activeTab === "documents") {
      openDocumentDrawer();
    }
  }

  function addChecklistItem() {
    checklistItems = [
      ...checklistItems,
      {
        title: "",
        description: "",
        is_mandatory: true,
        is_compliant: "pending",
        response_note: "",
        corrective_action: "",
        sort_order: checklistItems.length + 1,
      },
    ];
  }

  function removeChecklistItem(index: number) {
    checklistItems = checklistItems
      .filter((_, itemIndex) => itemIndex !== index)
      .map((item, itemIndex) => ({ ...item, sort_order: itemIndex + 1 }));
    if (checklistItems.length === 0) {
      checklistItems = defaultChecklistItems();
    }
  }

  function updateChecklistItem(index: number, key: keyof ChecklistItemFormRow, value: string | boolean | number) {
    checklistItems = checklistItems.map((item, itemIndex) =>
      itemIndex === index ? { ...item, [key]: value } : item,
    );
  }

  function checklistBooleanValue(value: ChecklistItemFormRow["is_compliant"]): boolean | null {
    if (value === "true") return true;
    if (value === "false") return false;
    return null;
  }

  async function fetchOverview() {
    overview = await api.get<HealthSafetyOverview>("/facility-management/health-safety/overview/");
  }

  async function fetchLookups() {
    const response = await api.get<HealthSafetyLookupsResponse>("/facility-management/health-safety/lookups/");
    usersLookup = response.users;
    facilitiesLookup = response.facilities;
    spacesLookup = response.spaces;
    requirementsLookup = response.compliance_requirements;
    incidentLookup = response.incidents;
    inspectionLookup = response.inspections;
  }

  async function fetchIncidents() {
    const response = await api.get<PaginatedResponse<FacilityIncidentItem>>(
      "/facility-management/health-safety/incidents/",
      { page_size: "300" },
    );
    incidents = response.results;
  }

  async function fetchInspections() {
    const response = await api.get<PaginatedResponse<FacilityInspectionItem>>(
      "/facility-management/health-safety/inspections/",
      { page_size: "300" },
    );
    inspections = response.results;
  }

  async function fetchChecklists() {
    const response = await api.get<PaginatedResponse<FacilityChecklistItem>>(
      "/facility-management/health-safety/checklists/",
      { page_size: "300" },
    );
    checklists = response.results;
  }

  async function fetchDocuments() {
    const response = await api.get<PaginatedResponse<FacilityRegulatoryDocumentItem>>(
      "/facility-management/health-safety/regulatory-documents/",
      { page_size: "300" },
    );
    regulatoryDocuments = response.results;
  }

  async function fetchAuditLogs() {
    const response = await api.get<PaginatedResponse<FacilityAuditLogItem>>(
      "/facility-management/health-safety/audit-logs/",
      { page_size: "300" },
    );
    auditLogs = response.results;
  }

  async function refreshAll(showLoader = false) {
    if (showLoader) {
      loading = true;
    } else if (!loading) {
      refreshing = true;
    }

    try {
      await Promise.all([
        fetchOverview(),
        fetchLookups(),
        fetchIncidents(),
        fetchInspections(),
        fetchChecklists(),
        fetchDocuments(),
        fetchAuditLogs(),
      ]);
    } catch {
      overview = null;
      incidents = [];
      inspections = [];
      checklists = [];
      regulatoryDocuments = [];
      auditLogs = [];
      toast.error("Load failed", "Could not load health, safety, and compliance data.");
    } finally {
      loading = false;
      refreshing = false;
    }
  }

  async function runWorkflows() {
    syncingWorkflows = true;
    try {
      const result = await api.post<WorkflowSyncResult>("/facility-management/health-safety/sync/", {});
      toast.success(
        "Workflows completed",
        `${fmtInt(result.follow_up_inspections_created)} follow-ups, ${fmtInt(result.violations_created)} violations, ${fmtInt(result.corrective_work_orders_created)} corrective work orders.`,
      );
      await refreshAll();
    } catch (error) {
      toast.error("Workflow failed", parseApiMessage(error, "Could not run health and safety workflows."));
    } finally {
      syncingWorkflows = false;
    }
  }

  async function handleIncidentCreate(event: SubmitEvent) {
    event.preventDefault();
    incidentSaving = true;
    try {
      await api.post("/facility-management/health-safety/incidents/", {
        facility: incidentForm.facility || null,
        facility_space: incidentForm.facility_space || null,
        title: incidentForm.title,
        description: incidentForm.description,
        category: incidentForm.category,
        severity: incidentForm.severity,
        status: incidentForm.status,
        occurred_at: incidentForm.occurred_at,
        assigned_to: incidentForm.assigned_to,
        requires_regulatory_report: incidentForm.requires_regulatory_report,
      });
      toast.success("Incident reported", "The incident was logged and linked workflows were triggered.");
      closeIncidentDrawer();
      await refreshAll();
    } catch (error) {
      toast.error("Save failed", parseApiMessage(error, "Could not save the incident."));
    } finally {
      incidentSaving = false;
    }
  }

  async function handleInspectionCreate(event: SubmitEvent) {
    event.preventDefault();
    inspectionSaving = true;
    try {
      await api.post("/facility-management/health-safety/inspections/", {
        facility: inspectionForm.facility || null,
        facility_space: inspectionForm.facility_space || null,
        incident: inspectionForm.incident || null,
        title: inspectionForm.title,
        inspection_type: inspectionForm.inspection_type,
        status: inspectionForm.status,
        scheduled_date: inspectionForm.scheduled_date,
        completed_date: inspectionForm.completed_date || null,
        inspector: inspectionForm.inspector,
        findings: inspectionForm.findings,
        rating: inspectionForm.rating || "",
        risk_level: inspectionForm.risk_level || "",
        corrective_action_required: inspectionForm.corrective_action_required,
        compliance_status: inspectionForm.compliance_status || "",
        expiry_date: inspectionForm.expiry_date || null,
        follow_up_required: inspectionForm.follow_up_required,
        follow_up_notes: inspectionForm.follow_up_notes,
        notes: inspectionForm.notes,
      });
      toast.success("Inspection saved", "The safety inspection was recorded successfully.");
      closeInspectionDrawer();
      await refreshAll();
    } catch (error) {
      toast.error("Save failed", parseApiMessage(error, "Could not save the inspection."));
    } finally {
      inspectionSaving = false;
    }
  }

  async function handleChecklistCreate(event: SubmitEvent) {
    event.preventDefault();
    checklistSaving = true;
    try {
      await api.post("/facility-management/health-safety/checklists/", {
        facility: checklistForm.facility || null,
        facility_space: checklistForm.facility_space || null,
        linked_incident: checklistForm.linked_incident || null,
        linked_inspection: checklistForm.linked_inspection || null,
        compliance_requirement: checklistForm.compliance_requirement || null,
        title: checklistForm.title,
        checklist_type: checklistForm.checklist_type,
        frequency: checklistForm.frequency,
        status: checklistForm.status,
        responsible_person: checklistForm.responsible_person,
        due_date: checklistForm.due_date,
        completed_at: checklistForm.completed_at || null,
        auto_create_violation: checklistForm.auto_create_violation,
        auto_create_follow_up_inspection: checklistForm.auto_create_follow_up_inspection,
        notes: checklistForm.notes,
        items: checklistItems.map((item, index) => ({
          title: item.title,
          description: item.description,
          is_mandatory: item.is_mandatory,
          is_compliant: checklistBooleanValue(item.is_compliant),
          response_note: item.response_note,
          corrective_action: item.corrective_action,
          sort_order: index + 1,
        })),
      });
      toast.success("Checklist saved", "The compliance checklist was recorded successfully.");
      closeChecklistDrawer();
      await refreshAll();
    } catch (error) {
      toast.error("Save failed", parseApiMessage(error, "Could not save the checklist."));
    } finally {
      checklistSaving = false;
    }
  }

  async function handleDocumentCreate(event: SubmitEvent) {
    event.preventDefault();
    documentSaving = true;
    try {
      const payload = new FormData();
      payload.set("facility", documentForm.facility);
      payload.set("title", documentForm.title);
      payload.set("document_type", documentForm.document_type);
      payload.set("description", documentForm.description);
      if (documentForm.compliance_requirement) payload.set("compliance_requirement", documentForm.compliance_requirement);
      payload.set("issuing_authority", documentForm.issuing_authority);
      payload.set("reference_number", documentForm.reference_number);
      if (documentForm.issue_date) payload.set("issue_date", documentForm.issue_date);
      if (documentForm.expiry_date) payload.set("expiry_date", documentForm.expiry_date);
      if (documentForm.review_due_date) payload.set("review_due_date", documentForm.review_due_date);
      payload.set("notes", documentForm.notes);
      if (selectedRegulatoryFile) payload.set("file", selectedRegulatoryFile);

      await api.upload("/facility-management/health-safety/regulatory-documents/", payload);
      toast.success("Document saved", "The regulatory document was uploaded successfully.");
      closeDocumentDrawer();
      await refreshAll();
    } catch (error) {
      toast.error("Save failed", parseApiMessage(error, "Could not save the regulatory document."));
    } finally {
      documentSaving = false;
    }
  }

  function handleRegulatoryFileChange(event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    selectedRegulatoryFile = input.files?.[0] ?? null;
  }

  function currentIncidents(): FacilityIncidentItem[] {
    const query = incidentSearch.trim().toLowerCase();
    return incidents.filter((incident) => {
      if (incidentFacilityFilter && String(incident.facility ?? "") !== incidentFacilityFilter) return false;
      if (incidentStatusFilter && incident.status !== incidentStatusFilter) return false;
      if (!query) return true;
      return [
        incident.incident_code,
        incident.title,
        incident.description,
        incident.facility_code,
        incident.space_label,
        incident.assigned_to,
      ]
        .join(" ")
        .toLowerCase()
        .includes(query);
    });
  }

  function currentInspections(): FacilityInspectionItem[] {
    const query = inspectionSearch.trim().toLowerCase();
    return inspections.filter((inspection) => {
      if (inspectionFacilityFilter && String(inspection.facility ?? "") !== inspectionFacilityFilter) return false;
      if (inspectionStatusFilter && inspection.status !== inspectionStatusFilter) return false;
      if (!query) return true;
      return [
        inspection.title,
        inspection.inspection_type_display,
        inspection.linked_incident_code,
        inspection.facility_code,
        inspection.space_label,
        inspection.inspector,
      ]
        .join(" ")
        .toLowerCase()
        .includes(query);
    });
  }

  function currentChecklists(): FacilityChecklistItem[] {
    const query = checklistSearch.trim().toLowerCase();
    return checklists.filter((checklist) => {
      if (checklistStatusFilter && checklist.status !== checklistStatusFilter) return false;
      if (!query) return true;
      return [
        checklist.title,
        checklist.checklist_type_display,
        checklist.compliance_requirement_name,
        checklist.facility_code,
        checklist.responsible_person,
      ]
        .join(" ")
        .toLowerCase()
        .includes(query);
    });
  }

  function currentDocuments(): FacilityRegulatoryDocumentItem[] {
    const query = documentSearch.trim().toLowerCase();
    return regulatoryDocuments.filter((document) => {
      if (documentStatusFilter && document.status !== documentStatusFilter) return false;
      if (!query) return true;
      return [
        document.title,
        document.reference_number,
        document.issuing_authority,
        document.facility_code,
        document.compliance_requirement_name,
      ]
        .join(" ")
        .toLowerCase()
        .includes(query);
    });
  }

  function currentAuditLogs(): FacilityAuditLogItem[] {
    const query = auditSearch.trim().toLowerCase();
    return auditLogs.filter((log) => {
      if (auditEntityFilter && log.entity_type !== auditEntityFilter) return false;
      if (!query) return true;
      return [
        log.summary,
        log.entity_type_display,
        log.event_type_display,
        log.actor_name,
        log.facility_code,
      ]
        .join(" ")
        .toLowerCase()
        .includes(query);
    });
  }

  function currentIncidentPageItems(): FacilityIncidentItem[] {
    return pagedItems(currentIncidents(), incidentPage);
  }

  function currentInspectionPageItems(): FacilityInspectionItem[] {
    return pagedItems(currentInspections(), inspectionPage);
  }

  function currentChecklistPageItems(): FacilityChecklistItem[] {
    return pagedItems(currentChecklists(), checklistPage);
  }

  function currentDocumentPageItems(): FacilityRegulatoryDocumentItem[] {
    return pagedItems(currentDocuments(), documentPage);
  }

  function currentAuditPageItems(): FacilityAuditLogItem[] {
    return pagedItems(currentAuditLogs(), auditPage);
  }

  function resetIncidentControls() {
    incidentSearch = "";
    incidentFacilityFilter = "";
    incidentStatusFilter = "";
    incidentPage = 1;
  }

  function resetInspectionControls() {
    inspectionSearch = "";
    inspectionFacilityFilter = "";
    inspectionStatusFilter = "";
    inspectionPage = 1;
  }

  function resetChecklistControls() {
    checklistSearch = "";
    checklistStatusFilter = "";
    checklistPage = 1;
  }

  function resetDocumentControls() {
    documentSearch = "";
    documentStatusFilter = "";
    documentPage = 1;
  }

  function resetAuditControls() {
    auditSearch = "";
    auditEntityFilter = "";
    auditPage = 1;
  }

  function currentActionLabel(): string {
    if (activeTab === "incidents") return "Add Incident";
    if (activeTab === "inspections") return "Add Inspection";
    if (activeTab === "checklists") return "Add Checklist";
    if (activeTab === "documents") return "Add Regulatory Document";
    return "";
  }

  $effect(() => {
    refreshAll(true);
  });

  $effect(() => {
    incidentPage = clampPage(incidentPage, currentIncidents().length);
  });

  $effect(() => {
    inspectionPage = clampPage(inspectionPage, currentInspections().length);
  });

  $effect(() => {
    checklistPage = clampPage(checklistPage, currentChecklists().length);
  });

  $effect(() => {
    documentPage = clampPage(documentPage, currentDocuments().length);
  });

  $effect(() => {
    auditPage = clampPage(auditPage, currentAuditLogs().length);
  });
</script>

<div class="space-y-6">
  <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-600">Facility Management</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Health, Safety & Compliance</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Incident reporting, safety inspections, compliance checklists, regulatory documentation, and audit history for managed facilities.
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
        aria-label={refreshing ? "Refreshing health and safety data" : "Refresh health and safety data"}
        title={refreshing ? "Refreshing health and safety data" : "Refresh health and safety data"}
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
      Loading health, safety, and compliance data...
    </div>
  {:else if !overview}
    <div class="rounded-2xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">
      Health, safety, and compliance data is unavailable right now.
    </div>
  {:else}
    <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
      <section class="rounded-2xl border border-rose-200 bg-rose-50 p-5">
        <p class="text-xs font-semibold uppercase tracking-wide text-rose-700">Open Incidents</p>
        <p class="mt-3 text-2xl font-semibold text-rose-900">{fmtInt(overview.kpis.open_incidents)}</p>
        <p class="mt-2 text-xs text-rose-800">
          Critical: {fmtInt(overview.kpis.critical_incidents)} | Investigating: {fmtInt(overview.kpis.investigating_incidents)}
        </p>
      </section>
      <section class="rounded-2xl border border-amber-200 bg-amber-50 p-5">
        <p class="text-xs font-semibold uppercase tracking-wide text-amber-700">Safety Inspections</p>
        <p class="mt-3 text-2xl font-semibold text-amber-900">{fmtInt(overview.kpis.scheduled_inspections)}</p>
        <p class="mt-2 text-xs text-amber-800">Overdue: {fmtInt(overview.kpis.overdue_inspections)}</p>
      </section>
      <section class="rounded-2xl border border-sky-200 bg-sky-50 p-5">
        <p class="text-xs font-semibold uppercase tracking-wide text-sky-700">Compliance Checklists</p>
        <p class="mt-3 text-2xl font-semibold text-sky-900">{fmtInt(overview.kpis.open_checklists)}</p>
        <p class="mt-2 text-xs text-sky-800">Overdue: {fmtInt(overview.kpis.overdue_checklists)}</p>
      </section>
      <section class="rounded-2xl border border-emerald-200 bg-emerald-50 p-5">
        <p class="text-xs font-semibold uppercase tracking-wide text-emerald-700">Regulatory Documents</p>
        <p class="mt-3 text-2xl font-semibold text-emerald-900">{fmtInt(overview.kpis.total_regulatory_documents)}</p>
        <p class="mt-2 text-xs text-emerald-800">
          Expiring soon: {fmtInt(overview.kpis.expiring_documents)} | Expired: {fmtInt(overview.kpis.expired_documents)}
        </p>
      </section>
      <section class="rounded-2xl border border-violet-200 bg-violet-50 p-5">
        <p class="text-xs font-semibold uppercase tracking-wide text-violet-700">Violations & Audit</p>
        <p class="mt-3 text-2xl font-semibold text-violet-900">{fmtInt(overview.kpis.open_violations)}</p>
        <p class="mt-2 text-xs text-violet-800">Audit events (7d): {fmtInt(overview.kpis.audit_events_7d)}</p>
      </section>
    </div>

    <section class="rounded-2xl border border-neutral-200 bg-white p-5">
      <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Operational Register</h2>
          <p class="text-xs text-neutral-500">
            Monitor active incidents, inspections, checklist progress, regulatory documentation, and audit trail entries.
          </p>
        </div>
        {#if tabsWithCreateAction.has(activeTab)}
          <button
            type="button"
            onclick={openActiveDrawer}
            class="inline-flex items-center justify-center rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-neutral-800"
          >
            {currentActionLabel()}
          </button>
        {/if}
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

      {#if activeTab === "incidents"}
        <div class="mt-4 grid gap-3 md:grid-cols-3">
          <input
            bind:value={incidentSearch}
            class="rounded-lg border border-neutral-200 px-3 py-2.5 text-sm"
            placeholder="Search incident code, title, assignee, or location"
          />
          <select bind:value={incidentFacilityFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">All facilities</option>
            {#each facilitiesLookup as facility}
              <option value={String(facility.id)}>{facility.facility_code} - {facility.property_name}</option>
            {/each}
          </select>
          <select bind:value={incidentStatusFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">All statuses</option>
            <option value="open">Open</option>
            <option value="investigating">Investigating</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option>
          </select>
        </div>

        <div class="mt-4 rounded-xl border border-neutral-200 bg-neutral-50/70 p-4">
          <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Management Controls</p>
              <p class="mt-1 text-xs text-neutral-500">
                Showing {pageStart(currentIncidents().length, incidentPage)}-{pageEnd(currentIncidents().length, incidentPage)} of {fmtInt(currentIncidents().length)} incidents.
              </p>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onclick={() => { incidentStatusFilter = ""; incidentPage = 1; }}
                class={managementControlButtonClass(!incidentStatusFilter, "neutral")}
              >
                All {fmtInt(currentIncidents().length)}
              </button>
              <button
                type="button"
                onclick={() => { incidentStatusFilter = incidentStatusFilter === "open" ? "" : "open"; incidentPage = 1; }}
                class={managementControlButtonClass(incidentStatusFilter === "open", "rose")}
              >
                Open {fmtInt(incidents.filter((incident) => incident.status === "open").length)}
              </button>
              <button
                type="button"
                onclick={() => { incidentStatusFilter = incidentStatusFilter === "investigating" ? "" : "investigating"; incidentPage = 1; }}
                class={managementControlButtonClass(incidentStatusFilter === "investigating", "amber")}
              >
                Investigating {fmtInt(incidents.filter((incident) => incident.status === "investigating").length)}
              </button>
              <button
                type="button"
                onclick={() => { incidentStatusFilter = incidentStatusFilter === "resolved" ? "" : "resolved"; incidentPage = 1; }}
                class={managementControlButtonClass(incidentStatusFilter === "resolved", "emerald")}
              >
                Resolved {fmtInt(incidents.filter((incident) => incident.status === "resolved").length)}
              </button>
              <button
                type="button"
                onclick={resetIncidentControls}
                disabled={!incidentSearch && !incidentFacilityFilter && !incidentStatusFilter}
                class="inline-flex items-center rounded-full border border-neutral-200 bg-white px-3 py-1.5 text-xs font-medium text-neutral-600 transition hover:border-neutral-300 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Clear filters
              </button>
            </div>
          </div>
        </div>

        <div class="mt-5 overflow-hidden rounded-xl border border-neutral-200">
          <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-neutral-200 text-sm">
            <thead class="bg-neutral-50 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">
              <tr>
                <th class="px-4 py-3">Incident</th>
                <th class="px-4 py-3">Location</th>
                <th class="px-4 py-3">Severity / Status</th>
                <th class="px-4 py-3">Follow-Up</th>
                <th class="px-4 py-3">Occurrence</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-200 bg-white text-neutral-700">
              {#each currentIncidentPageItems() as incident}
                <tr class="align-top">
                  <td class="px-4 py-3">
                    <div class="font-medium text-neutral-900">
                      {incident.incident_code || `INC-${incident.id}`} {incident.title}
                    </div>
                    <div class="mt-1 text-xs text-neutral-500">
                      {incident.category_display}
                      {#if incident.requires_regulatory_report}
                        • Regulatory report required
                      {/if}
                    </div>
                    {#if incident.description}
                      <p class="mt-2 max-w-md text-xs text-neutral-600">{incident.description}</p>
                    {/if}
                  </td>
                  <td class="px-4 py-3 text-xs text-neutral-600">
                    <div>{incident.facility_code || "--"}</div>
                    <div class="mt-1">{incident.space_label || incident.property_name}</div>
                    {#if incident.assigned_to}
                      <div class="mt-1 text-neutral-500">Assigned: {incident.assigned_to}</div>
                    {/if}
                  </td>
                  <td class="px-4 py-3">
                    <div class="flex flex-wrap gap-2">
                      <span class={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${incidentSeverityBadge(incident.severity)}`}>
                        {incident.severity_display}
                      </span>
                      <span class={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${incidentStatusBadge(incident.status)}`}>
                        {incident.status_display}
                      </span>
                    </div>
                  </td>
                  <td class="px-4 py-3 text-xs text-neutral-600">
                    <div>Work order: {incident.work_order_status || "--"}</div>
                    <div class="mt-1">Inspection: {incident.follow_up_inspection_status || "--"}</div>
                  </td>
                  <td class="px-4 py-3 text-xs text-neutral-600">
                    <div>{fmtDateTime(incident.occurred_at)}</div>
                    <div class="mt-1">Resolved: {fmtDateTime(incident.resolved_at)}</div>
                  </td>
                </tr>
              {/each}
              {#if currentIncidents().length === 0}
                <tr>
                  <td colspan="5" class="px-4 py-8 text-center text-sm text-neutral-500">
                    No incidents match this view yet.
                  </td>
                </tr>
              {/if}
            </tbody>
          </table>
          </div>
          {#if currentIncidents().length > 0}
            <div class="flex flex-col gap-3 border-t border-neutral-200 bg-white px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
              <p class="text-xs text-neutral-500">
                Showing {pageStart(currentIncidents().length, incidentPage)}-{pageEnd(currentIncidents().length, incidentPage)} of {fmtInt(currentIncidents().length)} incidents
              </p>
              <div class="flex items-center gap-2">
                <button
                  type="button"
                  onclick={() => incidentPage = Math.max(1, incidentPage - 1)}
                  disabled={incidentPage === 1}
                  class="rounded-lg border border-neutral-200 bg-white px-3 py-1.5 text-xs font-medium text-neutral-600 transition hover:border-neutral-300 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Previous
                </button>
                <span class="rounded-full border border-neutral-200 bg-neutral-50 px-3 py-1 text-xs font-medium text-neutral-600">
                  Page {incidentPage} of {totalPagesFor(currentIncidents().length)}
                </span>
                <button
                  type="button"
                  onclick={() => incidentPage = Math.min(totalPagesFor(currentIncidents().length), incidentPage + 1)}
                  disabled={incidentPage >= totalPagesFor(currentIncidents().length)}
                  class="rounded-lg border border-neutral-200 bg-white px-3 py-1.5 text-xs font-medium text-neutral-600 transition hover:border-neutral-300 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          {/if}
        </div>
      {/if}

      {#if activeTab === "inspections"}
        <div class="mt-4 grid gap-3 md:grid-cols-3">
          <input
            bind:value={inspectionSearch}
            class="rounded-lg border border-neutral-200 px-3 py-2.5 text-sm"
            placeholder="Search inspection, linked incident, inspector, or location"
          />
          <select bind:value={inspectionFacilityFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">All facilities</option>
            {#each facilitiesLookup as facility}
              <option value={String(facility.id)}>{facility.facility_code} - {facility.property_name}</option>
            {/each}
          </select>
          <select bind:value={inspectionStatusFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">All statuses</option>
            {#each inspectionStatusOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </div>

        <div class="mt-4 rounded-xl border border-neutral-200 bg-neutral-50/70 p-4">
          <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Management Controls</p>
              <p class="mt-1 text-xs text-neutral-500">
                Showing {pageStart(currentInspections().length, inspectionPage)}-{pageEnd(currentInspections().length, inspectionPage)} of {fmtInt(currentInspections().length)} inspections.
              </p>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onclick={() => { inspectionStatusFilter = ""; inspectionPage = 1; }}
                class={managementControlButtonClass(!inspectionStatusFilter, "neutral")}
              >
                All {fmtInt(currentInspections().length)}
              </button>
              <button
                type="button"
                onclick={() => { inspectionStatusFilter = inspectionStatusFilter === "scheduled" ? "" : "scheduled"; inspectionPage = 1; }}
                class={managementControlButtonClass(inspectionStatusFilter === "scheduled", "sky")}
              >
                Scheduled {fmtInt(inspections.filter((inspection) => inspection.status === "scheduled").length)}
              </button>
              <button
                type="button"
                onclick={() => { inspectionStatusFilter = inspectionStatusFilter === "in_progress" ? "" : "in_progress"; inspectionPage = 1; }}
                class={managementControlButtonClass(inspectionStatusFilter === "in_progress", "amber")}
              >
                In Progress {fmtInt(inspections.filter((inspection) => inspection.status === "in_progress").length)}
              </button>
              <button
                type="button"
                onclick={() => { inspectionStatusFilter = inspectionStatusFilter === "completed" ? "" : "completed"; inspectionPage = 1; }}
                class={managementControlButtonClass(inspectionStatusFilter === "completed", "emerald")}
              >
                Completed {fmtInt(inspections.filter((inspection) => inspection.status === "completed").length)}
              </button>
              <button
                type="button"
                onclick={resetInspectionControls}
                disabled={!inspectionSearch && !inspectionFacilityFilter && !inspectionStatusFilter}
                class="inline-flex items-center rounded-full border border-neutral-200 bg-white px-3 py-1.5 text-xs font-medium text-neutral-600 transition hover:border-neutral-300 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Clear filters
              </button>
            </div>
          </div>
        </div>

        <div class="mt-5 overflow-hidden rounded-xl border border-neutral-200">
          <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-neutral-200 text-sm">
            <thead class="bg-neutral-50 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">
              <tr>
                <th class="px-4 py-3">Inspection</th>
                <th class="px-4 py-3">Location</th>
                <th class="px-4 py-3">Risk / Compliance</th>
                <th class="px-4 py-3">Status</th>
                <th class="px-4 py-3">Dates</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-200 bg-white text-neutral-700">
              {#each currentInspectionPageItems() as inspection}
                <tr class="align-top">
                  <td class="px-4 py-3">
                    <div class="font-medium text-neutral-900">{inspection.title}</div>
                    <div class="mt-1 text-xs text-neutral-500">
                      {inspection.inspection_type_display}
                      {#if inspection.linked_incident_code}
                        • {inspection.linked_incident_code}
                      {/if}
                    </div>
                    {#if inspection.inspector}
                      <div class="mt-2 text-xs text-neutral-600">Inspector: {inspection.inspector}</div>
                    {/if}
                  </td>
                  <td class="px-4 py-3 text-xs text-neutral-600">
                    <div>{inspection.facility_code || "--"}</div>
                    <div class="mt-1">{inspection.space_label || inspection.property_name}</div>
                  </td>
                  <td class="px-4 py-3 text-xs text-neutral-600">
                    <div>Risk: {inspection.risk_level_display || "--"}</div>
                    <div class="mt-1">Compliance: {inspection.compliance_status_display || "--"}</div>
                    <div class="mt-1">Rating: {inspection.rating_display || "--"}</div>
                  </td>
                  <td class="px-4 py-3">
                    <span class={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${inspectionStatusBadge(inspection.status)}`}>
                      {inspection.status_display}
                    </span>
                    {#if inspection.corrective_action_required}
                      <div class="mt-2 text-xs font-medium text-amber-700">Corrective action required</div>
                    {/if}
                  </td>
                  <td class="px-4 py-3 text-xs text-neutral-600">
                    <div>Scheduled: {fmtDate(inspection.scheduled_date)}</div>
                    <div class="mt-1">Completed: {fmtDate(inspection.completed_date)}</div>
                    <div class="mt-1">Expiry: {fmtDate(inspection.expiry_date)}</div>
                  </td>
                </tr>
              {/each}
              {#if currentInspections().length === 0}
                <tr>
                  <td colspan="5" class="px-4 py-8 text-center text-sm text-neutral-500">
                    No inspections match this view yet.
                  </td>
                </tr>
              {/if}
            </tbody>
          </table>
          </div>
          {#if currentInspections().length > 0}
            <div class="flex flex-col gap-3 border-t border-neutral-200 bg-white px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
              <p class="text-xs text-neutral-500">
                Showing {pageStart(currentInspections().length, inspectionPage)}-{pageEnd(currentInspections().length, inspectionPage)} of {fmtInt(currentInspections().length)} inspections
              </p>
              <div class="flex items-center gap-2">
                <button
                  type="button"
                  onclick={() => inspectionPage = Math.max(1, inspectionPage - 1)}
                  disabled={inspectionPage === 1}
                  class="rounded-lg border border-neutral-200 bg-white px-3 py-1.5 text-xs font-medium text-neutral-600 transition hover:border-neutral-300 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Previous
                </button>
                <span class="rounded-full border border-neutral-200 bg-neutral-50 px-3 py-1 text-xs font-medium text-neutral-600">
                  Page {inspectionPage} of {totalPagesFor(currentInspections().length)}
                </span>
                <button
                  type="button"
                  onclick={() => inspectionPage = Math.min(totalPagesFor(currentInspections().length), inspectionPage + 1)}
                  disabled={inspectionPage >= totalPagesFor(currentInspections().length)}
                  class="rounded-lg border border-neutral-200 bg-white px-3 py-1.5 text-xs font-medium text-neutral-600 transition hover:border-neutral-300 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          {/if}
        </div>
      {/if}

      {#if activeTab === "checklists"}
        <div class="mt-4 grid gap-3 md:grid-cols-2">
          <input
            bind:value={checklistSearch}
            class="rounded-lg border border-neutral-200 px-3 py-2.5 text-sm"
            placeholder="Search checklist, requirement, responsible person, or facility"
          />
          <select bind:value={checklistStatusFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">All statuses</option>
            {#each checklistStatusOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </div>

        <div class="mt-4 rounded-xl border border-neutral-200 bg-neutral-50/70 p-4">
          <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Management Controls</p>
              <p class="mt-1 text-xs text-neutral-500">
                Showing {pageStart(currentChecklists().length, checklistPage)}-{pageEnd(currentChecklists().length, checklistPage)} of {fmtInt(currentChecklists().length)} compliance checklists.
              </p>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onclick={() => { checklistStatusFilter = ""; checklistPage = 1; }}
                class={managementControlButtonClass(!checklistStatusFilter, "neutral")}
              >
                All {fmtInt(currentChecklists().length)}
              </button>
              <button
                type="button"
                onclick={() => { checklistStatusFilter = checklistStatusFilter === "active" ? "" : "active"; checklistPage = 1; }}
                class={managementControlButtonClass(checklistStatusFilter === "active", "sky")}
              >
                Active {fmtInt(checklists.filter((checklist) => checklist.status === "active").length)}
              </button>
              <button
                type="button"
                onclick={() => { checklistStatusFilter = checklistStatusFilter === "overdue" ? "" : "overdue"; checklistPage = 1; }}
                class={managementControlButtonClass(checklistStatusFilter === "overdue", "rose")}
              >
                Overdue {fmtInt(checklists.filter((checklist) => checklist.status === "overdue").length)}
              </button>
              <button
                type="button"
                onclick={() => { checklistStatusFilter = checklistStatusFilter === "completed" ? "" : "completed"; checklistPage = 1; }}
                class={managementControlButtonClass(checklistStatusFilter === "completed", "emerald")}
              >
                Completed {fmtInt(checklists.filter((checklist) => checklist.status === "completed").length)}
              </button>
              <button
                type="button"
                onclick={resetChecklistControls}
                disabled={!checklistSearch && !checklistStatusFilter}
                class="inline-flex items-center rounded-full border border-neutral-200 bg-white px-3 py-1.5 text-xs font-medium text-neutral-600 transition hover:border-neutral-300 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Clear filters
              </button>
            </div>
          </div>
        </div>

        <div class="mt-5 overflow-hidden rounded-xl border border-neutral-200">
          <div class="overflow-x-auto">
          <table class="min-w-full table-fixed divide-y divide-neutral-200 text-sm">
            <colgroup>
              <col class="w-[30%]" />
              <col class="w-[24%]" />
              <col class="w-[14%]" />
              <col class="w-[14%]" />
              <col class="w-[18%]" />
            </colgroup>
            <thead class="bg-neutral-50 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">
              <tr>
                <th class="px-5 py-3.5">Checklist</th>
                <th class="px-5 py-3.5">Requirement</th>
                <th class="px-5 py-3.5">Status</th>
                <th class="px-5 py-3.5">Score</th>
                <th class="px-5 py-3.5">Schedule</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-200 bg-white text-neutral-700">
              {#each currentChecklistPageItems() as checklist}
                <tr class="align-top">
                  <td class="px-5 py-4">
                    <div class="space-y-1.5">
                      <div class="font-medium leading-5 text-neutral-900">{checklist.title}</div>
                      <div class="text-xs leading-5 text-neutral-500">
                        {checklist.checklist_type_display}
                        {#if checklist.facility_code}
                          • {checklist.facility_code}
                        {/if}
                      </div>
                    </div>
                    {#if checklist.responsible_person}
                      <div class="mt-3 text-xs leading-5 text-neutral-600">Owner: {checklist.responsible_person}</div>
                    {/if}
                  </td>
                  <td class="px-5 py-4 text-xs leading-5 text-neutral-600">
                    <div class="space-y-1.5">
                      <div class="font-medium text-neutral-700">{checklist.compliance_requirement_name || "--"}</div>
                      <div>Incident: {checklist.linked_incident_code || "--"}</div>
                      <div>Inspection: {checklist.linked_inspection_title || "--"}</div>
                    </div>
                  </td>
                  <td class="px-5 py-4 whitespace-nowrap">
                    <span class={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${checklistStatusBadge(checklist.status)}`}>
                      {checklist.status_display}
                    </span>
                  </td>
                  <td class="px-5 py-4 text-xs leading-5 text-neutral-600">
                    <div class="space-y-1.5">
                      <div class="font-medium text-neutral-700">{checklist.overall_score}%</div>
                      <div>{checklist.compliant_items_count}/{checklist.total_items_count} compliant</div>
                      <div>Failures: {fmtInt(checklist.failure_count)}</div>
                    </div>
                  </td>
                  <td class="px-5 py-4 text-xs leading-5 text-neutral-600">
                    <div class="space-y-1.5">
                      <div>Due: {fmtDate(checklist.due_date)}</div>
                      <div>Completed: {fmtDateTime(checklist.completed_at)}</div>
                      <div>Next due: {fmtDate(checklist.next_due_date)}</div>
                    </div>
                  </td>
                </tr>
              {/each}
              {#if currentChecklists().length === 0}
                <tr>
                  <td colspan="5" class="px-5 py-8 text-center text-sm text-neutral-500">
                    No checklists match this view yet.
                  </td>
                </tr>
              {/if}
            </tbody>
          </table>
          </div>
          {#if currentChecklists().length > 0}
            <div class="flex flex-col gap-3 border-t border-neutral-200 bg-white px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
              <p class="text-xs text-neutral-500">
                Showing {pageStart(currentChecklists().length, checklistPage)}-{pageEnd(currentChecklists().length, checklistPage)} of {fmtInt(currentChecklists().length)} checklists
              </p>
              <div class="flex items-center gap-2">
                <button
                  type="button"
                  onclick={() => checklistPage = Math.max(1, checklistPage - 1)}
                  disabled={checklistPage === 1}
                  class="rounded-lg border border-neutral-200 bg-white px-3 py-1.5 text-xs font-medium text-neutral-600 transition hover:border-neutral-300 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Previous
                </button>
                <span class="rounded-full border border-neutral-200 bg-neutral-50 px-3 py-1 text-xs font-medium text-neutral-600">
                  Page {checklistPage} of {totalPagesFor(currentChecklists().length)}
                </span>
                <button
                  type="button"
                  onclick={() => checklistPage = Math.min(totalPagesFor(currentChecklists().length), checklistPage + 1)}
                  disabled={checklistPage >= totalPagesFor(currentChecklists().length)}
                  class="rounded-lg border border-neutral-200 bg-white px-3 py-1.5 text-xs font-medium text-neutral-600 transition hover:border-neutral-300 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          {/if}
        </div>
      {/if}

      {#if activeTab === "documents"}
        <div class="mt-4 grid gap-3 md:grid-cols-2">
          <input
            bind:value={documentSearch}
            class="rounded-lg border border-neutral-200 px-3 py-2.5 text-sm"
            placeholder="Search document title, reference, authority, or requirement"
          />
          <select bind:value={documentStatusFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">All statuses</option>
            <option value="pending_review">Pending Review</option>
            <option value="valid">Valid</option>
            <option value="expiring_soon">Expiring Soon</option>
            <option value="expired">Expired</option>
            <option value="superseded">Superseded</option>
          </select>
        </div>

        <div class="mt-4 rounded-xl border border-neutral-200 bg-neutral-50/70 p-4">
          <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Management Controls</p>
              <p class="mt-1 text-xs text-neutral-500">
                Showing {pageStart(currentDocuments().length, documentPage)}-{pageEnd(currentDocuments().length, documentPage)} of {fmtInt(currentDocuments().length)} regulatory documents.
              </p>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onclick={() => { documentStatusFilter = ""; documentPage = 1; }}
                class={managementControlButtonClass(!documentStatusFilter, "neutral")}
              >
                All {fmtInt(currentDocuments().length)}
              </button>
              <button
                type="button"
                onclick={() => { documentStatusFilter = documentStatusFilter === "valid" ? "" : "valid"; documentPage = 1; }}
                class={managementControlButtonClass(documentStatusFilter === "valid", "emerald")}
              >
                Valid {fmtInt(regulatoryDocuments.filter((document) => document.status === "valid").length)}
              </button>
              <button
                type="button"
                onclick={() => { documentStatusFilter = documentStatusFilter === "expiring_soon" ? "" : "expiring_soon"; documentPage = 1; }}
                class={managementControlButtonClass(documentStatusFilter === "expiring_soon", "amber")}
              >
                Expiring Soon {fmtInt(regulatoryDocuments.filter((document) => document.status === "expiring_soon").length)}
              </button>
              <button
                type="button"
                onclick={() => { documentStatusFilter = documentStatusFilter === "expired" ? "" : "expired"; documentPage = 1; }}
                class={managementControlButtonClass(documentStatusFilter === "expired", "rose")}
              >
                Expired {fmtInt(regulatoryDocuments.filter((document) => document.status === "expired").length)}
              </button>
              <button
                type="button"
                onclick={resetDocumentControls}
                disabled={!documentSearch && !documentStatusFilter}
                class="inline-flex items-center rounded-full border border-neutral-200 bg-white px-3 py-1.5 text-xs font-medium text-neutral-600 transition hover:border-neutral-300 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Clear filters
              </button>
            </div>
          </div>
        </div>

        <div class="mt-5 overflow-hidden rounded-xl border border-neutral-200">
          <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-neutral-200 text-sm">
            <thead class="bg-neutral-50 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">
              <tr>
                <th class="px-4 py-3">Document</th>
                <th class="px-4 py-3">Requirement / Facility</th>
                <th class="px-4 py-3">Status</th>
                <th class="px-4 py-3">Dates</th>
                <th class="px-4 py-3">Access</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-200 bg-white text-neutral-700">
              {#each currentDocumentPageItems() as document}
                <tr class="align-top">
                  <td class="px-4 py-3">
                    <div class="font-medium text-neutral-900">{document.title}</div>
                    <div class="mt-1 text-xs text-neutral-500">
                      {document.document_type_display}
                      {#if document.reference_number}
                        • Ref {document.reference_number}
                      {/if}
                    </div>
                    {#if document.description}
                      <p class="mt-2 max-w-md text-xs text-neutral-600">{document.description}</p>
                    {/if}
                  </td>
                  <td class="px-4 py-3 text-xs text-neutral-600">
                    <div>{document.compliance_requirement_name || "--"}</div>
                    <div class="mt-1">{document.facility_code || document.property_name}</div>
                    <div class="mt-1">{document.issuing_authority || "--"}</div>
                  </td>
                  <td class="px-4 py-3">
                    <span class={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${documentStatusBadge(document.status)}`}>
                      {document.status_display}
                    </span>
                  </td>
                  <td class="px-4 py-3 text-xs text-neutral-600">
                    <div>Issue: {fmtDate(document.issue_date)}</div>
                    <div class="mt-1">Review: {fmtDate(document.review_due_date)}</div>
                    <div class="mt-1">Expiry: {fmtDate(document.expiry_date)}</div>
                  </td>
                  <td class="px-4 py-3 text-xs text-neutral-600">
                    <div>{document.uploaded_by_name || "--"}</div>
                    {#if document.file_url}
                      <a
                        href={document.file_url}
                        target="_blank"
                        rel="noreferrer"
                        class="mt-2 inline-flex font-medium text-neutral-900 underline decoration-neutral-300 underline-offset-2 hover:decoration-neutral-900"
                      >
                        Open file
                      </a>
                    {/if}
                  </td>
                </tr>
              {/each}
              {#if currentDocuments().length === 0}
                <tr>
                  <td colspan="5" class="px-4 py-8 text-center text-sm text-neutral-500">
                    No regulatory documents match this view yet.
                  </td>
                </tr>
              {/if}
            </tbody>
          </table>
          </div>
          {#if currentDocuments().length > 0}
            <div class="flex flex-col gap-3 border-t border-neutral-200 bg-white px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
              <p class="text-xs text-neutral-500">
                Showing {pageStart(currentDocuments().length, documentPage)}-{pageEnd(currentDocuments().length, documentPage)} of {fmtInt(currentDocuments().length)} documents
              </p>
              <div class="flex items-center gap-2">
                <button
                  type="button"
                  onclick={() => documentPage = Math.max(1, documentPage - 1)}
                  disabled={documentPage === 1}
                  class="rounded-lg border border-neutral-200 bg-white px-3 py-1.5 text-xs font-medium text-neutral-600 transition hover:border-neutral-300 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Previous
                </button>
                <span class="rounded-full border border-neutral-200 bg-neutral-50 px-3 py-1 text-xs font-medium text-neutral-600">
                  Page {documentPage} of {totalPagesFor(currentDocuments().length)}
                </span>
                <button
                  type="button"
                  onclick={() => documentPage = Math.min(totalPagesFor(currentDocuments().length), documentPage + 1)}
                  disabled={documentPage >= totalPagesFor(currentDocuments().length)}
                  class="rounded-lg border border-neutral-200 bg-white px-3 py-1.5 text-xs font-medium text-neutral-600 transition hover:border-neutral-300 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          {/if}
        </div>
      {/if}

      {#if activeTab === "audit"}
        <div class="mt-4 grid gap-3 md:grid-cols-2">
          <input
            bind:value={auditSearch}
            class="rounded-lg border border-neutral-200 px-3 py-2.5 text-sm"
            placeholder="Search summary, event type, actor, or facility"
          />
          <select bind:value={auditEntityFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">All entity types</option>
            <option value="incident">Incident</option>
            <option value="inspection">Inspection</option>
            <option value="checklist">Checklist</option>
            <option value="document">Document</option>
            <option value="compliance">Compliance</option>
            <option value="workflow">Workflow</option>
          </select>
        </div>

        <div class="mt-4 rounded-xl border border-neutral-200 bg-neutral-50/70 p-4">
          <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p class="text-[11px] font-semibold uppercase tracking-[0.28em] text-neutral-500">Management Controls</p>
              <p class="mt-1 text-xs text-neutral-500">
                Showing {pageStart(currentAuditLogs().length, auditPage)}-{pageEnd(currentAuditLogs().length, auditPage)} of {fmtInt(currentAuditLogs().length)} audit events.
              </p>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onclick={() => { auditEntityFilter = ""; auditPage = 1; }}
                class={managementControlButtonClass(!auditEntityFilter, "neutral")}
              >
                All {fmtInt(currentAuditLogs().length)}
              </button>
              <button
                type="button"
                onclick={() => { auditEntityFilter = auditEntityFilter === "incident" ? "" : "incident"; auditPage = 1; }}
                class={managementControlButtonClass(auditEntityFilter === "incident", "rose")}
              >
                Incidents {fmtInt(auditLogs.filter((log) => log.entity_type === "incident").length)}
              </button>
              <button
                type="button"
                onclick={() => { auditEntityFilter = auditEntityFilter === "inspection" ? "" : "inspection"; auditPage = 1; }}
                class={managementControlButtonClass(auditEntityFilter === "inspection", "amber")}
              >
                Inspections {fmtInt(auditLogs.filter((log) => log.entity_type === "inspection").length)}
              </button>
              <button
                type="button"
                onclick={() => { auditEntityFilter = auditEntityFilter === "workflow" ? "" : "workflow"; auditPage = 1; }}
                class={managementControlButtonClass(auditEntityFilter === "workflow", "violet")}
              >
                Workflow {fmtInt(auditLogs.filter((log) => log.entity_type === "workflow").length)}
              </button>
              <button
                type="button"
                onclick={resetAuditControls}
                disabled={!auditSearch && !auditEntityFilter}
                class="inline-flex items-center rounded-full border border-neutral-200 bg-white px-3 py-1.5 text-xs font-medium text-neutral-600 transition hover:border-neutral-300 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Clear filters
              </button>
            </div>
          </div>
        </div>

        <div class="mt-5 overflow-hidden rounded-xl border border-neutral-200">
          <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-neutral-200 text-sm">
            <thead class="bg-neutral-50 text-left text-xs font-semibold uppercase tracking-wide text-neutral-500">
              <tr>
                <th class="px-4 py-3">Event</th>
                <th class="px-4 py-3">Entity</th>
                <th class="px-4 py-3">Facility</th>
                <th class="px-4 py-3">Actor</th>
                <th class="px-4 py-3">Time</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-200 bg-white text-neutral-700">
              {#each currentAuditPageItems() as log}
                <tr class="align-top">
                  <td class="px-4 py-3">
                    <div class="font-medium text-neutral-900">{log.summary}</div>
                    <div class="mt-1 text-xs text-neutral-500">{log.event_type_display}</div>
                  </td>
                  <td class="px-4 py-3 text-xs text-neutral-600">
                    <div>{log.entity_type_display}</div>
                    <div class="mt-1">Entity ID: {log.entity_id ?? "--"}</div>
                  </td>
                  <td class="px-4 py-3 text-xs text-neutral-600">
                    <div>{log.facility_code || "--"}</div>
                    <div class="mt-1">{log.property_name || "--"}</div>
                  </td>
                  <td class="px-4 py-3 text-xs text-neutral-600">{log.actor_name || "--"}</td>
                  <td class="px-4 py-3 text-xs text-neutral-600">{fmtDateTime(log.created_at)}</td>
                </tr>
              {/each}
              {#if currentAuditLogs().length === 0}
                <tr>
                  <td colspan="5" class="px-4 py-8 text-center text-sm text-neutral-500">
                    No audit log entries match this view yet.
                  </td>
                </tr>
              {/if}
            </tbody>
          </table>
          </div>
          {#if currentAuditLogs().length > 0}
            <div class="flex flex-col gap-3 border-t border-neutral-200 bg-white px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
              <p class="text-xs text-neutral-500">
                Showing {pageStart(currentAuditLogs().length, auditPage)}-{pageEnd(currentAuditLogs().length, auditPage)} of {fmtInt(currentAuditLogs().length)} audit events
              </p>
              <div class="flex items-center gap-2">
                <button
                  type="button"
                  onclick={() => auditPage = Math.max(1, auditPage - 1)}
                  disabled={auditPage === 1}
                  class="rounded-lg border border-neutral-200 bg-white px-3 py-1.5 text-xs font-medium text-neutral-600 transition hover:border-neutral-300 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Previous
                </button>
                <span class="rounded-full border border-neutral-200 bg-neutral-50 px-3 py-1 text-xs font-medium text-neutral-600">
                  Page {auditPage} of {totalPagesFor(currentAuditLogs().length)}
                </span>
                <button
                  type="button"
                  onclick={() => auditPage = Math.min(totalPagesFor(currentAuditLogs().length), auditPage + 1)}
                  disabled={auditPage >= totalPagesFor(currentAuditLogs().length)}
                  class="rounded-lg border border-neutral-200 bg-white px-3 py-1.5 text-xs font-medium text-neutral-600 transition hover:border-neutral-300 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          {/if}
        </div>
      {/if}
    </section>

    <div class="grid gap-4 xl:grid-cols-2 2xl:grid-cols-3">
      <section class="rounded-2xl border border-neutral-200 bg-white p-5">
        <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Incident Watchlist</h2>
        <div class="mt-4 space-y-3">
          {#each overview.incident_watchlist as incident}
            <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
              <div class="flex items-start justify-between gap-3">
                <div>
                  <p class="font-medium text-neutral-900">{incident.incident_code || `INC-${incident.id}`} {incident.title}</p>
                  <p class="mt-1 text-xs text-neutral-500">{incident.facility_code || incident.property_name}</p>
                </div>
                <span class={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold ${incidentSeverityBadge(incident.severity)}`}>
                  {incident.severity_display}
                </span>
              </div>
              <p class="mt-2 text-xs text-neutral-600">Occurred {fmtDateTime(incident.occurred_at)}</p>
            </div>
          {/each}
          {#if overview.incident_watchlist.length === 0}
            <p class="text-sm text-neutral-500">No active incidents need attention right now.</p>
          {/if}
        </div>
      </section>

      <section class="rounded-2xl border border-neutral-200 bg-white p-5">
        <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Inspection Queue</h2>
        <div class="mt-4 space-y-3">
          {#each overview.inspection_watchlist as inspection}
            <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
              <p class="font-medium text-neutral-900">{inspection.title}</p>
              <p class="mt-1 text-xs text-neutral-500">{inspection.inspection_type_display} • {inspection.facility_code || inspection.property_name}</p>
              <p class="mt-2 text-xs text-neutral-600">
                Scheduled {fmtDate(inspection.scheduled_date)} • Status {inspection.status_display}
              </p>
            </div>
          {/each}
          {#if overview.inspection_watchlist.length === 0}
            <p class="text-sm text-neutral-500">No scheduled inspections are pending right now.</p>
          {/if}
        </div>
      </section>

      <section class="rounded-2xl border border-neutral-200 bg-white p-5">
        <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Checklist Risk</h2>
        <div class="mt-4 space-y-3">
          {#each overview.checklist_watchlist as checklist}
            <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
              <div class="flex items-start justify-between gap-3">
                <div>
                  <p class="font-medium text-neutral-900">{checklist.title}</p>
                  <p class="mt-1 text-xs text-neutral-500">{checklist.compliance_requirement_name || checklist.checklist_type_display}</p>
                </div>
                <span class={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold ${checklistStatusBadge(checklist.status)}`}>
                  {checklist.status_display}
                </span>
              </div>
              <p class="mt-2 text-xs text-neutral-600">
                Due {fmtDate(checklist.due_date)} • Failures {fmtInt(checklist.failure_count)}
              </p>
            </div>
          {/each}
          {#if overview.checklist_watchlist.length === 0}
            <p class="text-sm text-neutral-500">No checklist exposures are pending right now.</p>
          {/if}
        </div>
      </section>

      <section class="rounded-2xl border border-neutral-200 bg-white p-5">
        <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Regulatory Risks</h2>
        <div class="mt-4 space-y-3">
          {#each overview.document_watchlist as document}
            <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
              <div class="flex items-start justify-between gap-3">
                <div>
                  <p class="font-medium text-neutral-900">{document.title}</p>
                  <p class="mt-1 text-xs text-neutral-500">{document.facility_code || document.property_name}</p>
                </div>
                <span class={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold ${documentStatusBadge(document.status)}`}>
                  {document.status_display}
                </span>
              </div>
              <p class="mt-2 text-xs text-neutral-600">
                Review {fmtDate(document.review_due_date)} • Expiry {fmtDate(document.expiry_date)}
              </p>
            </div>
          {/each}
          {#if overview.document_watchlist.length === 0}
            <p class="text-sm text-neutral-500">No document review or expiry risks right now.</p>
          {/if}
        </div>
      </section>

      <section class="rounded-2xl border border-neutral-200 bg-white p-5">
        <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Open Violations</h2>
        <div class="mt-4 space-y-3">
          {#each overview.violation_watchlist as violation}
            <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
              <p class="font-medium text-neutral-900">{violation.title}</p>
              <p class="mt-1 text-xs text-neutral-500">{violation.property_name}</p>
              <p class="mt-2 text-xs text-neutral-600">
                {violation.severity_display} • Due {fmtDate(violation.due_date)} • {violation.assigned_to || "Unassigned"}
              </p>
            </div>
          {/each}
          {#if overview.violation_watchlist.length === 0}
            <p class="text-sm text-neutral-500">No open compliance violations right now.</p>
          {/if}
        </div>
      </section>

      <section class="rounded-2xl border border-neutral-200 bg-white p-5">
        <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Audit Feed</h2>
        <div class="mt-4 space-y-3">
          {#each overview.audit_log_watchlist as log}
            <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-3">
              <p class="font-medium text-neutral-900">{log.summary}</p>
              <p class="mt-1 text-xs text-neutral-500">{log.event_type_display} • {log.facility_code || log.property_name || "Global"}</p>
              <p class="mt-2 text-xs text-neutral-600">{fmtDateTime(log.created_at)}</p>
            </div>
          {/each}
          {#if overview.audit_log_watchlist.length === 0}
            <p class="text-sm text-neutral-500">New automation and safety audit events will appear here.</p>
          {/if}
        </div>
      </section>
    </div>
  {/if}
</div>

{#if showIncidentDrawer}
  <button
    type="button"
    class="fixed inset-0 z-40 bg-neutral-900/35"
    onclick={closeIncidentDrawer}
    tabindex="-1"
    aria-label="Close incident drawer"
  ></button>
  <aside class="fixed inset-y-0 right-0 z-50 flex w-full max-w-2xl flex-col bg-white shadow-2xl animate-slide-in-right">
    <div class="flex items-center justify-between border-b border-neutral-100 px-6 py-4">
      <div>
        <h2 class="text-lg font-semibold text-neutral-900">Report Incident</h2>
        <p class="mt-1 text-xs text-neutral-500">All facility management forms stay in drawers for consistent workflow handling.</p>
      </div>
      <button
        type="button"
        onclick={closeIncidentDrawer}
        class="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        aria-label="Close incident drawer"
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div class="flex-1 overflow-y-auto px-6 py-5">
      <form id="health-safety-incident-form" class="grid gap-4 md:grid-cols-2" onsubmit={handleIncidentCreate}>
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Facility</span>
          <select bind:value={incidentForm.facility} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Select facility</option>
            {#each facilitiesLookup as facility}
              <option value={String(facility.id)}>{facility.facility_code} - {facility.property_name}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Room / Space</span>
          <select bind:value={incidentForm.facility_space} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Optional room / space</option>
            {#each filteredSpacesFor(incidentForm.facility) as space}
              <option value={String(space.id)}>{space.facility_code} • {space.space_label || space.unit_number} • {space.zone_code}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700 md:col-span-2">
          <span class="mb-1.5 block">Title</span>
          <input bind:value={incidentForm.title} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Fire alarm discharge at control room" />
        </label>

        <label class="text-sm font-medium text-neutral-700 md:col-span-2">
          <span class="mb-1.5 block">Description</span>
          <textarea bind:value={incidentForm.description} rows="4" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Describe the incident, people affected, and immediate actions taken."></textarea>
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Category</span>
          <select bind:value={incidentForm.category} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            {#each incidentCategoryOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Severity</span>
          <select bind:value={incidentForm.severity} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            {#each incidentSeverityOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Status</span>
          <select bind:value={incidentForm.status} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="open">Open</option>
            <option value="investigating">Investigating</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option>
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Occurred At</span>
          <input bind:value={incidentForm.occurred_at} type="datetime-local" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
        </label>

        <label class="text-sm font-medium text-neutral-700 md:col-span-2">
          <span class="mb-1.5 block">Assigned Lead</span>
          <select bind:value={incidentForm.assigned_to} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Unassigned</option>
            {#each usersLookup as user}
              <option value={user.label}>{user.label}</option>
            {/each}
          </select>
        </label>

        <label class="inline-flex items-center gap-2 text-sm font-medium text-neutral-700 md:col-span-2">
          <input bind:checked={incidentForm.requires_regulatory_report} type="checkbox" class="rounded border-neutral-300" />
          Flag as requiring regulatory reporting
        </label>
      </form>
    </div>

    <div class="flex items-center justify-end gap-3 border-t border-neutral-100 px-6 py-4">
      {#if isDev}
        <button type="button" onclick={devFillIncident} class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>
      {/if}
      <button
        type="button"
        onclick={closeIncidentDrawer}
        class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-600 transition hover:border-neutral-300 hover:text-neutral-900"
      >
        Cancel
      </button>
      <button
        type="submit"
        form="health-safety-incident-form"
        disabled={incidentSaving}
        class="inline-flex items-center justify-center rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {incidentSaving ? "Saving..." : "Save Incident"}
      </button>
    </div>
  </aside>
{/if}

{#if showInspectionDrawer}
  <button
    type="button"
    class="fixed inset-0 z-40 bg-neutral-900/35"
    onclick={closeInspectionDrawer}
    tabindex="-1"
    aria-label="Close inspection drawer"
  ></button>
  <aside class="fixed inset-y-0 right-0 z-50 flex w-full max-w-3xl flex-col bg-white shadow-2xl animate-slide-in-right">
    <div class="flex items-center justify-between border-b border-neutral-100 px-6 py-4">
      <div>
        <h2 class="text-lg font-semibold text-neutral-900">Add Safety Inspection</h2>
        <p class="mt-1 text-xs text-neutral-500">Use this drawer for inspections tied to facility spaces, incidents, or ongoing compliance checks.</p>
      </div>
      <button
        type="button"
        onclick={closeInspectionDrawer}
        class="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        aria-label="Close inspection drawer"
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div class="flex-1 overflow-y-auto px-6 py-5">
      <form id="health-safety-inspection-form" class="grid gap-4 md:grid-cols-2" onsubmit={handleInspectionCreate}>
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Facility</span>
          <select bind:value={inspectionForm.facility} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Optional facility</option>
            {#each facilitiesLookup as facility}
              <option value={String(facility.id)}>{facility.facility_code} - {facility.property_name}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Room / Space</span>
          <select bind:value={inspectionForm.facility_space} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Optional room / space</option>
            {#each filteredSpacesFor(inspectionForm.facility) as space}
              <option value={String(space.id)}>{space.facility_code} • {space.space_label || space.unit_number} • {space.zone_code}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700 md:col-span-2">
          <span class="mb-1.5 block">Linked Incident</span>
          <select bind:value={inspectionForm.incident} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Optional linked incident</option>
            {#each filteredIncidentOptions(inspectionForm.facility) as incident}
              <option value={String(incident.id)}>{incident.incident_code || `INC-${incident.id}`} • {incident.title}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700 md:col-span-2">
          <span class="mb-1.5 block">Title</span>
          <input bind:value={inspectionForm.title} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Safety walkway inspection" />
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Inspection Type</span>
          <select bind:value={inspectionForm.inspection_type} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            {#each inspectionTypeOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Status</span>
          <select bind:value={inspectionForm.status} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            {#each inspectionStatusOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Scheduled Date</span>
          <input bind:value={inspectionForm.scheduled_date} type="date" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Completed Date</span>
          <input bind:value={inspectionForm.completed_date} type="date" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Inspector</span>
          <select bind:value={inspectionForm.inspector} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Select inspector</option>
            {#each usersLookup as user}
              <option value={user.label}>{user.label}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Expiry Date</span>
          <input bind:value={inspectionForm.expiry_date} type="date" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Rating</span>
          <select bind:value={inspectionForm.rating} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Select rating</option>
            {#each inspectionRatingOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Risk Level</span>
          <select bind:value={inspectionForm.risk_level} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Select risk level</option>
            {#each inspectionRiskOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700 md:col-span-2">
          <span class="mb-1.5 block">Compliance Status</span>
          <select bind:value={inspectionForm.compliance_status} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Select compliance status</option>
            {#each inspectionComplianceOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700 md:col-span-2">
          <span class="mb-1.5 block">Findings</span>
          <textarea bind:value={inspectionForm.findings} rows="4" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Summarize key findings, defects, or hazards identified during inspection."></textarea>
        </label>

        <label class="text-sm font-medium text-neutral-700 md:col-span-2">
          <span class="mb-1.5 block">Follow-Up Notes</span>
          <textarea bind:value={inspectionForm.follow_up_notes} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Enter required corrective actions or next steps."></textarea>
        </label>

        <label class="text-sm font-medium text-neutral-700 md:col-span-2">
          <span class="mb-1.5 block">Notes</span>
          <textarea bind:value={inspectionForm.notes} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Additional scheduling, access, or site notes."></textarea>
        </label>

        <label class="inline-flex items-center gap-2 text-sm font-medium text-neutral-700">
          <input bind:checked={inspectionForm.corrective_action_required} type="checkbox" class="rounded border-neutral-300" />
          Corrective action required
        </label>

        <label class="inline-flex items-center gap-2 text-sm font-medium text-neutral-700">
          <input bind:checked={inspectionForm.follow_up_required} type="checkbox" class="rounded border-neutral-300" />
          Follow-up required
        </label>
      </form>
    </div>

    <div class="flex items-center justify-end gap-3 border-t border-neutral-100 px-6 py-4">
      {#if isDev}
        <button type="button" onclick={devFillInspection} class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>
      {/if}
      <button
        type="button"
        onclick={closeInspectionDrawer}
        class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-600 transition hover:border-neutral-300 hover:text-neutral-900"
      >
        Cancel
      </button>
      <button
        type="submit"
        form="health-safety-inspection-form"
        disabled={inspectionSaving}
        class="inline-flex items-center justify-center rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {inspectionSaving ? "Saving..." : "Save Inspection"}
      </button>
    </div>
  </aside>
{/if}

{#if showChecklistDrawer}
  <button
    type="button"
    class="fixed inset-0 z-40 bg-neutral-900/35"
    onclick={closeChecklistDrawer}
    tabindex="-1"
    aria-label="Close checklist drawer"
  ></button>
  <aside class="fixed inset-y-0 right-0 z-50 flex w-full max-w-3xl flex-col bg-white shadow-2xl animate-slide-in-right">
    <div class="flex items-center justify-between border-b border-neutral-100 px-6 py-4">
      <div>
        <h2 class="text-lg font-semibold text-neutral-900">Add Compliance Checklist</h2>
        <p class="mt-1 text-xs text-neutral-500">Capture checklist items, responses, follow-up triggers, and compliance requirement mapping in one drawer flow.</p>
      </div>
      <button
        type="button"
        onclick={closeChecklistDrawer}
        class="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        aria-label="Close checklist drawer"
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div class="flex-1 overflow-y-auto px-6 py-5">
      <form id="health-safety-checklist-form" class="grid gap-4 md:grid-cols-2" onsubmit={handleChecklistCreate}>
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Facility</span>
          <select bind:value={checklistForm.facility} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Select facility</option>
            {#each facilitiesLookup as facility}
              <option value={String(facility.id)}>{facility.facility_code} - {facility.property_name}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Room / Space</span>
          <select bind:value={checklistForm.facility_space} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Optional room / space</option>
            {#each filteredSpacesFor(checklistForm.facility) as space}
              <option value={String(space.id)}>{space.facility_code} • {space.space_label || space.unit_number} • {space.zone_code}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Linked Incident</span>
          <select bind:value={checklistForm.linked_incident} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Optional linked incident</option>
            {#each filteredIncidentOptions(checklistForm.facility) as incident}
              <option value={String(incident.id)}>{incident.incident_code || `INC-${incident.id}`} • {incident.title}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Linked Inspection</span>
          <select bind:value={checklistForm.linked_inspection} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Optional linked inspection</option>
            {#each filteredInspectionOptions(checklistForm.facility) as inspection}
              <option value={String(inspection.id)}>{inspection.title} • {fmtDate(inspection.scheduled_date)}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700 md:col-span-2">
          <span class="mb-1.5 block">Checklist Title</span>
          <input bind:value={checklistForm.title} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Quarterly fire readiness checklist" />
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Checklist Type</span>
          <select bind:value={checklistForm.checklist_type} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            {#each checklistTypeOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Frequency</span>
          <select bind:value={checklistForm.frequency} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            {#each checklistFrequencyOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Status</span>
          <select bind:value={checklistForm.status} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            {#each checklistStatusOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Owner</span>
          <select bind:value={checklistForm.responsible_person} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Select owner</option>
            {#each usersLookup as user}
              <option value={user.label}>{user.label}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Compliance Requirement</span>
          <select bind:value={checklistForm.compliance_requirement} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Optional requirement</option>
            {#each requirementsLookup as requirement}
              <option value={String(requirement.id)}>{requirement.name} • {requirement.category_display}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Due Date</span>
          <input bind:value={checklistForm.due_date} type="date" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
        </label>

        <label class="text-sm font-medium text-neutral-700 md:col-span-2">
          <span class="mb-1.5 block">Completed At</span>
          <input bind:value={checklistForm.completed_at} type="datetime-local" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
        </label>

        <label class="inline-flex items-center gap-2 text-sm font-medium text-neutral-700">
          <input bind:checked={checklistForm.auto_create_violation} type="checkbox" class="rounded border-neutral-300" />
          Auto-create compliance violation
        </label>

        <label class="inline-flex items-center gap-2 text-sm font-medium text-neutral-700">
          <input bind:checked={checklistForm.auto_create_follow_up_inspection} type="checkbox" class="rounded border-neutral-300" />
          Auto-create follow-up inspection
        </label>

        <label class="text-sm font-medium text-neutral-700 md:col-span-2">
          <span class="mb-1.5 block">Notes</span>
          <textarea bind:value={checklistForm.notes} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Add scope notes, special access instructions, or escalation context."></textarea>
        </label>

        <div class="md:col-span-2 rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
          <div class="flex items-center justify-between gap-3">
            <div>
              <h3 class="text-sm font-semibold text-neutral-900">Checklist Items</h3>
              <p class="mt-1 text-xs text-neutral-500">Capture each checklist line item and its current response.</p>
            </div>
            <button
              type="button"
              onclick={addChecklistItem}
              class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm font-medium text-neutral-700 hover:border-neutral-300 hover:text-neutral-900"
            >
              Add Item
            </button>
          </div>

          <div class="mt-4 space-y-4">
            {#each checklistItems as item, index}
              <div class="rounded-xl border border-neutral-200 bg-white p-4">
                <div class="flex items-center justify-between gap-3">
                  <p class="text-sm font-semibold text-neutral-900">Item {index + 1}</p>
                  <button
                    type="button"
                    onclick={() => removeChecklistItem(index)}
                    class="text-xs font-medium text-red-600 hover:text-red-700"
                  >
                    Remove
                  </button>
                </div>

                <div class="mt-3 grid gap-3 md:grid-cols-2">
                  <label class="text-sm font-medium text-neutral-700 md:col-span-2">
                    <span class="mb-1.5 block">Title</span>
                    <input
                      value={item.title}
                      oninput={(event) => updateChecklistItem(index, "title", (event.currentTarget as HTMLInputElement).value)}
                      class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm"
                      placeholder="Emergency exit signage visible"
                    />
                  </label>

                  <label class="text-sm font-medium text-neutral-700">
                    <span class="mb-1.5 block">Response</span>
                    <select
                      value={item.is_compliant}
                      onchange={(event) => updateChecklistItem(index, "is_compliant", (event.currentTarget as HTMLSelectElement).value)}
                      class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm"
                    >
                      <option value="pending">Pending</option>
                      <option value="true">Compliant</option>
                      <option value="false">Failed</option>
                    </select>
                  </label>

                  <label class="inline-flex items-center gap-2 text-sm font-medium text-neutral-700">
                    <input
                      checked={item.is_mandatory}
                      onchange={(event) => updateChecklistItem(index, "is_mandatory", (event.currentTarget as HTMLInputElement).checked)}
                      type="checkbox"
                      class="rounded border-neutral-300"
                    />
                    Mandatory item
                  </label>

                  <label class="text-sm font-medium text-neutral-700 md:col-span-2">
                    <span class="mb-1.5 block">Description</span>
                    <textarea
                      rows="2"
                      oninput={(event) => updateChecklistItem(index, "description", (event.currentTarget as HTMLTextAreaElement).value)}
                      class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm"
                    >{item.description}</textarea>
                  </label>

                  <label class="text-sm font-medium text-neutral-700 md:col-span-2">
                    <span class="mb-1.5 block">Response Note</span>
                    <textarea
                      rows="2"
                      oninput={(event) => updateChecklistItem(index, "response_note", (event.currentTarget as HTMLTextAreaElement).value)}
                      class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm"
                    >{item.response_note}</textarea>
                  </label>

                  <label class="text-sm font-medium text-neutral-700 md:col-span-2">
                    <span class="mb-1.5 block">Corrective Action</span>
                    <textarea
                      rows="2"
                      oninput={(event) => updateChecklistItem(index, "corrective_action", (event.currentTarget as HTMLTextAreaElement).value)}
                      class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm"
                    >{item.corrective_action}</textarea>
                  </label>
                </div>
              </div>
            {/each}
          </div>
        </div>
      </form>
    </div>

    <div class="flex items-center justify-end gap-3 border-t border-neutral-100 px-6 py-4">
      {#if isDev}
        <button type="button" onclick={devFillChecklist} class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>
      {/if}
      <button
        type="button"
        onclick={closeChecklistDrawer}
        class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-600 transition hover:border-neutral-300 hover:text-neutral-900"
      >
        Cancel
      </button>
      <button
        type="submit"
        form="health-safety-checklist-form"
        disabled={checklistSaving}
        class="inline-flex items-center justify-center rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {checklistSaving ? "Saving..." : "Save Checklist"}
      </button>
    </div>
  </aside>
{/if}

{#if showDocumentDrawer}
  <button
    type="button"
    class="fixed inset-0 z-40 bg-neutral-900/35"
    onclick={closeDocumentDrawer}
    tabindex="-1"
    aria-label="Close regulatory document drawer"
  ></button>
  <aside class="fixed inset-y-0 right-0 z-50 flex w-full max-w-2xl flex-col bg-white shadow-2xl animate-slide-in-right">
    <div class="flex items-center justify-between border-b border-neutral-100 px-6 py-4">
      <div>
        <h2 class="text-lg font-semibold text-neutral-900">Add Regulatory Document</h2>
        <p class="mt-1 text-xs text-neutral-500">Upload certificates, permits, and government approvals with review and expiry tracking.</p>
      </div>
      <button
        type="button"
        onclick={closeDocumentDrawer}
        class="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        aria-label="Close regulatory document drawer"
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div class="flex-1 overflow-y-auto px-6 py-5">
      <form id="health-safety-document-form" class="grid gap-4 md:grid-cols-2" onsubmit={handleDocumentCreate}>
        <label class="text-sm font-medium text-neutral-700 md:col-span-2">
          <span class="mb-1.5 block">Facility</span>
          <select bind:value={documentForm.facility} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Select facility</option>
            {#each facilitiesLookup as facility}
              <option value={String(facility.id)}>{facility.facility_code} - {facility.property_name}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700 md:col-span-2">
          <span class="mb-1.5 block">Title</span>
          <input bind:value={documentForm.title} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Lift operations certificate" />
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Document Type</span>
          <select bind:value={documentForm.document_type} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            {#each regulatoryDocumentTypeOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Requirement</span>
          <select bind:value={documentForm.compliance_requirement} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Optional requirement</option>
            {#each requirementsLookup as requirement}
              <option value={String(requirement.id)}>{requirement.name} • {requirement.category_display}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700 md:col-span-2">
          <span class="mb-1.5 block">Description</span>
          <textarea bind:value={documentForm.description} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Capture document scope, compliance context, and renewal notes."></textarea>
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Issuing Authority</span>
          <input bind:value={documentForm.issuing_authority} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Lagos Fire Service" />
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Reference Number</span>
          <input bind:value={documentForm.reference_number} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="FIRE-PERMIT-001" />
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Issue Date</span>
          <input bind:value={documentForm.issue_date} type="date" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Review Due Date</span>
          <input bind:value={documentForm.review_due_date} type="date" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
        </label>

        <label class="text-sm font-medium text-neutral-700 md:col-span-2">
          <span class="mb-1.5 block">Expiry Date</span>
          <input bind:value={documentForm.expiry_date} type="date" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
        </label>

        <label class="text-sm font-medium text-neutral-700 md:col-span-2">
          <span class="mb-1.5 block">Upload File</span>
          <input type="file" onchange={handleRegulatoryFileChange} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm file:mr-3 file:rounded-md file:border-0 file:bg-neutral-900 file:px-3 file:py-2 file:text-sm file:font-medium file:text-white" />
          <span class="mt-1 block text-xs text-neutral-500">{selectedRegulatoryFile?.name || "No file selected"}</span>
        </label>

        <label class="text-sm font-medium text-neutral-700 md:col-span-2">
          <span class="mb-1.5 block">Notes</span>
          <textarea bind:value={documentForm.notes} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Add renewal reminders, authority notes, or filing comments."></textarea>
        </label>
      </form>
    </div>

    <div class="flex items-center justify-end gap-3 border-t border-neutral-100 px-6 py-4">
      {#if isDev}
        <button type="button" onclick={devFillDocument} class="mr-auto rounded-lg bg-amber-500 px-3 py-2 text-xs font-medium text-white hover:bg-amber-600">Dev Fill</button>
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
        form="health-safety-document-form"
        disabled={documentSaving}
        class="inline-flex items-center justify-center rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {documentSaving ? "Saving..." : "Save Document"}
      </button>
    </div>
  </aside>
{/if}

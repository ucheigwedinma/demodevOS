/**
 * Shared TypeScript types — mirrors Django model shapes.
 */

export interface PropertyImage {
  id: number;
  property: number;
  image: string;
  caption: string;
  is_primary: boolean;
  sort_order: number;
  uploaded_at: string;
}

export interface PropertyDocument {
  id: number;
  property: number;
  file: string;
  title: string;
  document_type:
    | "deed"
    | "contract"
    | "survey"
    | "permit"
    | "inspection"
    | "appraisal"
    | "insurance"
    | "tax"
    | "certificate_of_occupancy"
    | "lease_agreement"
    | "easement"
    | "mortgage"
    | "government_approval"
    | "other";
  description: string;
  uploaded_at: string;
}

export interface PropertyValuation {
  id: number;
  property: number;
  valuation_date: string;
  value: string;
  valuation_type: "appraisal" | "internal" | "market" | "tax";
  appraiser: string;
  notes: string;
  created_at: string;
}

export interface PropertyOwnership {
  id: number;
  property: number;
  legal_owner_name: string;
  ownership_structure: "individual" | "corporate" | "trust" | "joint_venture";
  ownership_percentage: string;
  title_deed_number: string;
  registration_authority: string;
  date_of_registration: string;
  deed_expiry: string | null;
  created_at: string;
  updated_at: string;
}

export interface PropertyEncumbrance {
  id: number;
  property: number;
  encumbrance_type: "mortgage" | "lien" | "legal_dispute" | "court_case" | "tax_arrears";
  title: string;
  description: string;
  amount: string | null;
  status: "active" | "resolved" | "pending";
  date_filed: string;
  date_resolved: string | null;
  reference_number: string;
  notes: string;
  created_at: string;
}

export interface PropertyListItem {
  id: number;
  name: string;
  property_type: "land" | "building" | "mixed" | "estate" | "warehouse" | "industrial";
  classification: "owned" | "lease" | "concession" | "under_development";
  address: string;
  acquisition_date: string | null;
  current_value: string | null;
  total_area_sqft: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  unit_count: number;
  primary_image: string | null;
}

export interface Property {
  id: number;
  name: string;
  property_type: "land" | "building" | "mixed" | "estate" | "warehouse" | "industrial";
  classification: "owned" | "lease" | "concession" | "under_development";
  address: string;
  description: string;
  gps_latitude: string | null;
  gps_longitude: string | null;
  map_available: boolean;
  plot_number: string;
  acquisition_date: string | null;
  acquisition_price: string | null;
  current_value: string | null;
  total_area_sqft: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  unit_count: number;
  units: Unit[];
  images: PropertyImage[];
  documents: PropertyDocument[];
  valuations: PropertyValuation[];
  ownerships: PropertyOwnership[];
  encumbrances: PropertyEncumbrance[];
}

export interface Unit {
  id: number;
  property: number;
  unit_number: string;
  floor: number | null;
  area_sqft: string;
  bedrooms: number | null;
  bathrooms: number | null;
  unit_category: "apartment" | "villa" | "townhouse" | "penthouse" | "studio" | "duplex" | "office" | "retail" | "warehouse" | "land" | "other";
  asking_price: string | null;
  gps_latitude: string | null;
  gps_longitude: string | null;
  location_description: string;
  status: "available" | "reserved" | "sold" | "leased";
  inventory?: PropertyInventoryInline | null;
  created_at: string;
  updated_at: string;
}

export interface PropertyInventoryInline {
  id: number;
  status: PropertyInventoryStatus;
  held_by: string;
  held_until: string | null;
  allocated_to: string;
  allocated_on: string | null;
  list_price: string | null;
  notes: string;
  updated_at: string;
}

export type PropertyInventoryStatus = "available" | "held" | "reserved" | "sold" | "leased" | "unavailable";

export interface PropertyInventory {
  id: number;
  organization: number;
  unit: number;
  unit_number: string;
  property_id: number;
  property_name: string;
  status: PropertyInventoryStatus;
  held_by: string;
  held_until: string | null;
  reservation: number | null;
  allocated_to: string;
  allocated_on: string | null;
  list_price: string | null;
  notes: string;
  events?: PropertyInventoryEvent[];
  created_at: string;
  updated_at: string;
}

export interface PropertyInventoryEvent {
  id: number;
  event_type: string;
  from_status: string;
  to_status: string;
  actor_name: string;
  actor_user: number | null;
  reservation: number | null;
  hold_expires_at: string | null;
  metadata: Record<string, unknown>;
  notes: string;
  created_at: string;
}

// --- Facilities & Maintenance types ---

export type MaintenanceCategory = "plumbing" | "electrical" | "hvac" | "structural" | "mechanical" | "cleaning" | "landscaping" | "security" | "painting" | "fire_safety" | "elevator" | "generator" | "water_systems" | "general";
export type WorkOrderPriority = "low" | "medium" | "high" | "critical" | "urgent";
export type WorkOrderStatus = "open" | "assigned" | "in_progress" | "on_hold" | "completed" | "verified" | "cancelled";
export type WorkOrderMaintenanceMode = "corrective" | "preventive" | "predictive";
export type WorkOrderSlaStatus = "on_track" | "at_risk" | "overdue" | "met" | "breached" | "completed" | "verified" | "inactive";

// Maintenance Vendor
export type VendorSpecialization = "plumbing" | "electrical" | "hvac" | "structural" | "mechanical" | "fire_safety" | "elevator" | "generator" | "water_systems" | "security" | "cleaning" | "landscaping" | "painting" | "general";

export interface MaintenanceVendorListItem {
  id: number;
  name: string;
  contact_person: string;
  email: string;
  phone: string;
  specialization: VendorSpecialization;
  license_number: string;
  license_expiry: string | null;
  insurance_expiry: string | null;
  rating: string | null;
  hourly_rate: string | null;
  is_active: boolean;
  work_order_count: number;
  created_at: string;
  updated_at: string;
}

export interface MaintenanceVendor extends MaintenanceVendorListItem {
  address: string;
  notes: string;
}

// Asset Component Register
export type AssetCategory = "structural" | "electrical" | "mechanical" | "plumbing" | "hvac" | "fire_safety" | "elevator" | "generator" | "water_systems" | "security";
export type ConditionRating = "excellent" | "good" | "fair" | "poor" | "critical";
export type AssetLifecycleStage = "install" | "operate" | "maintain" | "retire";
export type AssetMaintenanceFrequency = "" | "daily" | "weekly" | "biweekly" | "monthly" | "quarterly" | "semi_annual" | "annual";
export type AssetDepreciationMethod = "straight_line";
export type AssetIoTStatus = "not_connected" | "connected" | "offline" | "fault";

export interface AssetComponentListItem {
  id: number;
  component_id: string;
  name: string;
  category: AssetCategory;
  condition_rating: ConditionRating;
  property: number;
  property_name: string;
  facility: number | null;
  facility_code: string | null;
  facility_name: string | null;
  facility_space: number | null;
  facility_space_label: string | null;
  unit: number | null;
  unit_number: string | null;
  vendor: number | null;
  vendor_name: string | null;
  lifecycle_stage: AssetLifecycleStage;
  manufacturer: string;
  model_number: string;
  serial_number: string;
  location_description: string;
  installation_date: string | null;
  commissioned_date: string | null;
  warranty_expiry: string | null;
  maintenance_frequency: AssetMaintenanceFrequency;
  maintenance_next_due_date: string | null;
  warranty_status: "active" | "expiring" | "expired" | "not_covered";
  maintenance_status: "not_scheduled" | "scheduled" | "due_soon" | "overdue" | "retired";
  amc_vendor: number | null;
  amc_vendor_name: string | null;
  amc_start_date: string | null;
  amc_end_date: string | null;
  amc_amount: string | null;
  amc_reference: string;
  amc_status: "active" | "expiring" | "expired" | "not_covered";
  depreciation_enabled: boolean;
  depreciation_method: AssetDepreciationMethod;
  depreciation_start_date: string | null;
  acquisition_cost: string | null;
  salvage_value: string | null;
  monthly_depreciation: string | null;
  accumulated_depreciation: string | null;
  current_book_value: string | null;
  last_depreciation_sync_at: string | null;
  is_iot_enabled: boolean;
  iot_device_id: string;
  iot_status: AssetIoTStatus;
  iot_last_seen_at: string | null;
  expected_useful_life_years: number | null;
  last_inspection_date: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AssetComponent extends AssetComponentListItem {
  description: string;
  auto_schedule_maintenance: boolean;
  retired_date: string | null;
  amc_notes: string;
  notes: string;
}

// Work Order (Corrective / Reactive)
export interface WorkOrderListItem {
  id: number;
  property: number;
  property_name: string;
  facility: number | null;
  facility_code: string | null;
  facility_name: string | null;
  facility_space: number | null;
  facility_space_label: string | null;
  unit: number | null;
  unit_number: string | null;
  asset_component: number | null;
  asset_component_name: string | null;
  vendor: number | null;
  vendor_name: string | null;
  title: string;
  maintenance_mode: WorkOrderMaintenanceMode;
  category: MaintenanceCategory;
  priority: WorkOrderPriority;
  status: WorkOrderStatus;
  sla_status: WorkOrderSlaStatus;
  assigned_to: string;
  reported_by: string;
  reported_date: string;
  started_at: string | null;
  due_date: string | null;
  sla_target_hours: number | null;
  sla_due_at: string | null;
  completed_date: string | null;
  verified_at: string | null;
  verified_by: string;
  preventive_schedule: number | null;
  is_breakdown: boolean;
  root_cause: string;
  estimated_cost: string | null;
  actual_cost: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkOrder extends WorkOrderListItem {
  description: string;
  verification_notes: string;
  notes: string;
}

// Preventive Maintenance Schedule
export type PreventiveFrequency = "daily" | "weekly" | "biweekly" | "monthly" | "quarterly" | "semi_annual" | "annual";
export type PreventiveStatus = "active" | "paused" | "completed";

export interface PreventiveScheduleListItem {
  id: number;
  property: number;
  property_name: string;
  facility: number | null;
  facility_code: string | null;
  facility_name: string | null;
  facility_space: number | null;
  facility_space_label: string | null;
  asset_component: number | null;
  asset_component_name: string | null;
  vendor: number | null;
  vendor_name: string | null;
  title: string;
  category: MaintenanceCategory;
  frequency: PreventiveFrequency;
  priority: WorkOrderPriority;
  status: PreventiveStatus;
  assigned_to: string;
  next_due_date: string;
  last_completed_date: string | null;
  sla_target_hours: number | null;
  generate_days_before: number;
  auto_create_work_orders: boolean;
  last_work_order: number | null;
  last_generated_date: string | null;
  estimated_cost: string | null;
  created_at: string;
  updated_at: string;
}

export interface PreventiveSchedule extends PreventiveScheduleListItem {
  description: string;
  auto_generated: boolean;
  notes: string;
}

export interface PredictiveMaintenanceRuleListItem {
  id: number;
  property: number;
  property_name: string;
  facility: number | null;
  facility_code: string | null;
  facility_name: string | null;
  facility_space: number | null;
  facility_space_label: string | null;
  asset_component: number | null;
  asset_component_name: string | null;
  title: string;
  priority: WorkOrderPriority;
  assigned_to: string;
  sla_target_hours: number | null;
  runtime_hours_threshold: string | null;
  cycle_threshold: number | null;
  runtime_hours_reading: string | null;
  cycle_reading: number | null;
  alert_on_offline: boolean;
  alert_on_fault: boolean;
  auto_create_work_order: boolean;
  is_active: boolean;
  last_evaluated_at: string | null;
  last_triggered_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PredictiveMaintenanceRule extends PredictiveMaintenanceRuleListItem {
  description: string;
  notes: string;
}

export type PredictiveAlertTrigger = "iot_offline" | "iot_fault" | "runtime_hours" | "cycle_count";
export type PredictiveAlertStatus = "open" | "acknowledged" | "work_order_created" | "resolved";

export interface PredictiveMaintenanceAlertListItem {
  id: number;
  rule: number;
  property: number;
  property_name: string;
  facility: number | null;
  facility_code: string | null;
  facility_space: number | null;
  asset_component: number | null;
  asset_component_name: string | null;
  work_order: number | null;
  work_order_title: string | null;
  title: string;
  message: string;
  priority: WorkOrderPriority;
  trigger_type: PredictiveAlertTrigger;
  status: PredictiveAlertStatus;
  runtime_hours_reading: string | null;
  cycle_reading: number | null;
  iot_status: AssetIoTStatus | "";
  triggered_at: string;
  resolved_at: string | null;
  updated_at: string;
}

export interface PredictiveMaintenanceAlert extends PredictiveMaintenanceAlertListItem {
  notes: string;
}

// Inspection
export type InspectionType = "routine" | "safety" | "compliance" | "pre_handover" | "post_incident" | "condition_survey" | "fire_safety" | "electrical" | "structural_integrity" | "elevator_certification" | "environmental_audit" | "health_safety";
export type InspectionStatus = "scheduled" | "in_progress" | "completed" | "cancelled";
export type InspectionRating = "pass" | "fail" | "conditional";
export type InspectionRiskLevel = "low" | "medium" | "high" | "critical";
export type InspectionComplianceStatus = "compliant" | "non_compliant" | "partially_compliant" | "pending_review";

export interface InspectionListItem {
  id: number;
  property: number;
  property_name: string;
  unit: number | null;
  unit_number: string | null;
  asset_component: number | null;
  asset_component_name: string | null;
  title: string;
  inspection_type: InspectionType;
  status: InspectionStatus;
  scheduled_date: string;
  completed_date: string | null;
  inspector: string;
  rating: InspectionRating | "";
  risk_level: InspectionRiskLevel | "";
  corrective_action_required: boolean;
  compliance_status: InspectionComplianceStatus | "";
  expiry_date: string | null;
  follow_up_required: boolean;
  created_at: string;
  updated_at: string;
}

export interface Inspection extends InspectionListItem {
  findings: string;
  follow_up_notes: string;
  notes: string;
}

// Service Request
export type ServiceRequestStatus = "open" | "acknowledged" | "in_progress" | "resolved" | "closed";

export interface ServiceRequestListItem {
  id: number;
  property: number;
  property_name: string;
  unit: number | null;
  unit_number: string | null;
  title: string;
  category: MaintenanceCategory;
  priority: WorkOrderPriority;
  status: ServiceRequestStatus;
  requested_by: string;
  assigned_to: string;
  requested_date: string;
  resolved_date: string | null;
  work_order: number | null;
  created_at: string;
  updated_at: string;
}

export interface ServiceRequest extends ServiceRequestListItem {
  description: string;
  resolution_notes: string;
  notes: string;
}

// --- Project lifecycle types ---

export type ProjectPhaseStatus = "not_started" | "in_progress" | "completed" | "skipped";
export type ProjectTaskStatus = "pending" | "in_progress" | "completed";
export type CostCategory = "materials" | "labor" | "permits" | "equipment" | "subcontractor" | "other";

export interface ProjectPhase {
  id: number;
  project: number;
  name: string;
  description: string;
  sort_order: number;
  status: ProjectPhaseStatus;
  baseline_start_date: string | null;
  baseline_end_date: string | null;
  revised_start_date: string | null;
  revised_end_date: string | null;
  schedule_revision_reason: string;
  planned_start_date: string | null;
  planned_end_date: string | null;
  actual_start_date: string | null;
  actual_end_date: string | null;
  planned_budget: string | null;
  actual_cost: string;
  weight: number;
  // Section A
  objective: string;
  estimated_duration_days: number | null;
  phase_owner_role: string;
  // Section B
  raci_matrix: { task: string; responsible: string; accountable: string; consulted: string; informed: string }[];
  approval_authority: string;
  // Section C
  key_tasks: { name: string; description: string }[];
  deliverables: { name: string; description: string; is_mandatory: boolean }[];
  out_of_scope: string;
  // Section D
  resource_requirements: { type: string; description: string; quantity: string }[];
  phase_risks: { risk: string; likelihood: string; impact: string; mitigation: string }[];
  budget_notes: string;
  // Section E
  success_metrics: { metric: string; target: string; measurement_method: string }[];
  exit_criteria: { criterion: string; verification_method: string }[];
  lessons_learned_prompt: string;
  // Computed
  budget_variance: string | null;
  task_count: number;
  completed_task_count: number;
  milestone_count: number;
  cost_total: string | null;
  schedule_variance_days: number | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectMilestone {
  id: number;
  phase: number;
  name: string;
  description: string;
  baseline_target_date: string | null;
  revised_target_date: string | null;
  schedule_revision_reason: string;
  target_date: string | null;
  completed_date: string | null;
  is_completed: boolean;
  approval_required: boolean;
  approval_status: "not_required" | "pending" | "approved" | "rejected";
  approved_by: number | null;
  approved_at: string | null;
  sort_order: number;
  // Section A: Milestone Identification
  reference_code: string;
  // Section B: Scheduling & Status
  typical_offset_days: number | null;
  // Section C: Completion Requirements
  success_criteria: { criterion: string; verification_method: string }[];
  key_deliverables: { name: string; description: string; is_mandatory: boolean }[];
  predecessors: { milestone: string; dependency_type: string; lag_days: number }[];
  successors: { milestone: string; dependency_type: string; lag_days: number }[];
  // Section D: Accountability & Approval
  owner_role: string;
  approver_role: string;
  stakeholders_to_notify: { role: string; notification_trigger: string }[];
  schedule_variance_days: number | null;
  approval_history: ProjectMilestoneApprovalDecision[];
  created_at: string;
  updated_at: string;
}

export interface ProjectPhaseDependency {
  id: number;
  project: number;
  predecessor_phase: number;
  predecessor_phase_name: string;
  successor_phase: number;
  successor_phase_name: string;
  dependency_type: "fs" | "ss" | "ff" | "sf";
  lag_days: number;
  notes: string;
  created_at: string;
}

export interface ProjectMilestoneApprovalRule {
  id: number;
  project: number;
  phase: number | null;
  phase_name: string | null;
  required_role: number;
  required_role_name: string;
  sequence_order: number;
  is_mandatory: boolean;
  is_active: boolean;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectMilestoneApprovalDecision {
  id: number;
  milestone: number;
  milestone_name: string;
  rule: number | null;
  approver_role: number | null;
  approver_role_name: string | null;
  approver: number | null;
  approver_name: string | null;
  decision: "pending" | "approved" | "rejected";
  comments: string;
  decided_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectScheduleDelayLog {
  id: number;
  project: number;
  project_name: string;
  phase: number | null;
  phase_name: string | null;
  milestone: number | null;
  milestone_name: string | null;
  source_issue: number | null;
  source_issue_title: string | null;
  delay_date: string;
  delay_type:
    | "weather"
    | "permit"
    | "design"
    | "procurement"
    | "workforce"
    | "equipment"
    | "safety"
    | "financial"
    | "client"
    | "other";
  impact_days: string;
  reason: string;
  mitigation_action: string;
  created_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectTask {
  id: number;
  project: number;
  project_name: string;
  phase: number;
  phase_name: string;
  name: string;
  description: string;
  work_package: string;
  status: ProjectTaskStatus;
  priority: "low" | "medium" | "high" | "critical";
  assigned_to: string;
  assigned_user: number | null;
  assigned_user_name: string | null;
  assigned_external_ref: string;
  linked_documents: number[];
  linked_document_records: {
    id: number;
    title: string;
    document_number: string;
    status: DocumentStatus;
    project: number | null;
  }[];
  linked_variation_orders: number[];
  linked_contract_records: {
    id: number;
    project: number;
    variation_number: string;
    title: string;
    status: ProjectVariationOrderStatus;
    contract_value: string;
  }[];
  linked_risks: number[];
  linked_risk_records: {
    id: number;
    project: number;
    title: string;
    severity: RiskSeverity;
    status: ProjectRiskStatus;
    risk_score: number;
  }[];
  sla_target_at: string | null;
  sla_breached_at: string | null;
  sla_status: "completed" | "not_configured" | "breached" | "at_risk" | "on_track";
  sla_time_remaining_seconds: number | null;
  due_date: string | null;
  completed_date: string | null;
  sort_order: number;
  // Section A: Task Definition & Context
  reference_code: string;
  // Section B: Assignment & Ownership
  reviewer_role: string;
  collaborators: { role: string; responsibility: string }[];
  // Section C: Scheduling & Effort
  estimated_effort_hours: string | null;
  // Section D: Execution Details
  predecessors: { task: string; dependency_type: string; lag_days: number }[];
  successors: { task: string; dependency_type: string; lag_days: number }[];
  definition_of_done: { criterion: string; is_required: boolean }[];
  // Section E: Resources & Attachments
  tools_required: { name: string; description: string }[];
  reference_links: { title: string; url: string }[];
  comments_count: number;
  created_by: number | null;
  updated_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectTaskComment {
  id: number;
  task: number;
  author: number | null;
  author_name: string | null;
  comment: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectWorkPackage {
  id: number;
  package_id: string | null;
  project: number;
  project_name: string;
  phase: number | null;
  phase_name: string | null;
  name: string;
  scope_description: string;
  contractor: number | null;
  contractor_name: string | null;
  boq_items: string[];
  budget: string;
  start_date: string | null;
  end_date: string | null;
  drawings: number[];
  drawings_records: {
    id: number;
    title: string;
    document_number: string;
    status: DocumentStatus;
    project: number | null;
  }[];
  quality_requirements: string;
  safety_requirements: string;
  inspection_plan: string;
  linked_purchase_orders: number[];
  linked_purchase_order_records: {
    id: number;
    po_number: string;
    status: string;
    project: number | null;
    vendor_name: string;
    expected_delivery_date: string | null;
    total_amount: string;
  }[];
  linked_cost_entries: number[];
  linked_cost_entry_records: {
    id: number;
    phase: number;
    description: string;
    amount: string;
    date: string;
    category: CostCategory;
  }[];
  linked_contractors: number[];
  linked_contractor_records: {
    id: number;
    name: string;
    category: string;
    compliance_status: string;
  }[];
  linked_inspections: number[];
  linked_inspection_records: {
    id: number;
    inspection_number: string;
    status: string;
    inspected_on: string;
    work_package: string;
    inspector_name: string;
  }[];
  linked_modules: {
    procurement: {
      purchase_orders: number;
    };
    finance: {
      cost_entries: number;
    };
    contractors: {
      count: number;
    };
    inspections: {
      count: number;
    };
  };
  created_by: number | null;
  updated_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectCostEntry {
  id: number;
  phase: number;
  description: string;
  amount: string;
  date: string;
  category: CostCategory;
  vendor: string;
  reference_number: string;
  created_at: string;
}

export type ProjectType = "residential" | "mixed_use" | "commercial" | "infrastructure";
export type LandStatus = "freehold" | "leasehold" | "under_contract" | "to_acquire" | "joint_venture";

export interface ProjectListItem {
  id: number;
  name: string;
  property: number | null;
  property_name: string | null;
  status: "planning" | "in_progress" | "on_hold" | "completed";
  project_type: ProjectType;
  number_of_units: number | null;
  location: string;
  gps_latitude: string | null;
  gps_longitude: string | null;
  map_available: boolean;
  spv_entity: string;
  land_status: LandStatus | "";
  risk_rating: "low" | "medium" | "high" | "critical";
  compliance_score: string;
  compliance_status: "compliant" | "warning" | "non_compliant";
  compliance_last_evaluated_at: string | null;
  start_date: string | null;
  target_end_date: string | null;
  actual_end_date: string | null;
  budget: string | null;
  target_irr: string | null;
  project_manager: string;
  description: string;
  created_at: string;
  updated_at: string;
  phase_count: number;
  progress: number;
}

export interface RaciSummary {
  [role: string]: string;
}

export interface ProjectOwnershipAllocation {
  investor_id: number;
  party_name: string;
  ownership_percentage: string;
  capital_committed: string;
  capital_contributed: string;
  sort_order: number;
  notes: string;
}

export interface Project {
  id: number;
  property: number | null;
  property_name: string | null;
  name: string;
  description: string;
  status: "planning" | "in_progress" | "on_hold" | "completed";
  project_type: ProjectType;
  number_of_units: number | null;
  location: string;
  gps_latitude: string | null;
  gps_longitude: string | null;
  map_available: boolean;
  spv_entity: string;
  ownership_structure: string;
  ownership_allocations?: ProjectOwnershipAllocation[];
  land_status: LandStatus | "";
  start_date: string | null;
  target_end_date: string | null;
  actual_end_date: string | null;
  land_acquisition_date: string | null;
  permit_approval_date: string | null;
  construction_start_date: string | null;
  budget: string | null;
  target_irr: string | null;
  raci_summary: RaciSummary;
  risk_rating: "low" | "medium" | "high" | "critical";
  compliance_score: string;
  compliance_status: "compliant" | "warning" | "non_compliant";
  compliance_last_evaluated_at: string | null;
  project_manager: string;
  created_at: string;
  updated_at: string;
  phases: ProjectPhase[];
  progress: number;
  total_planned_budget: string;
  total_actual_cost: string;
  total_budget_variance: string;
}

export interface ProjectTimelineData {
  project: {
    id: number;
    name: string;
    start_date: string | null;
    target_end_date: string | null;
  };
  dependencies: Array<{
    id: number;
    predecessor_phase_id: number;
    predecessor_phase_name: string;
    successor_phase_id: number;
    successor_phase_name: string;
    dependency_type: "fs" | "ss" | "ff" | "sf";
    lag_days: number;
  }>;
  critical_path_phase_ids: number[];
  phases: Array<{
    id: number;
    name: string;
    status: ProjectPhaseStatus;
    baseline_start_date: string | null;
    baseline_end_date: string | null;
    revised_start_date: string | null;
    revised_end_date: string | null;
    schedule_revision_reason: string;
    planned_start_date: string | null;
    planned_end_date: string | null;
    actual_start_date: string | null;
    actual_end_date: string | null;
    slack_days: number | null;
    is_critical_path: boolean;
    milestones: Array<{
      id: number;
      name: string;
      baseline_target_date: string | null;
      revised_target_date: string | null;
      schedule_revision_reason: string;
      target_date: string | null;
      completed_date: string | null;
      is_completed: boolean;
      approval_required: boolean;
      approval_status: "not_required" | "pending" | "approved" | "rejected";
      approved_at: string | null;
      approved_by_id: number | null;
      approvals: Array<{
        id: number;
        decision: "pending" | "approved" | "rejected";
        comments: string;
        decided_at: string | null;
        approver_id: number | null;
        approver_name: string | null;
        approver_role_id: number | null;
        approver_role_name: string | null;
      }>;
    }>;
  }>;
}

export type FieldShift = "day" | "night" | "full_day";
export type SiteWeather = "clear" | "cloudy" | "rain" | "storm" | "windy" | "other";
export type SiteReportStatus = "draft" | "submitted" | "reviewed" | "closed";
export type EscalationSeverity = "info" | "review" | "action_required" | "escalation";
export type EscalationStatus = "open" | "acknowledged" | "in_progress" | "resolved" | "closed";
export type WorkforceAttendanceStatus = "present" | "absent" | "late" | "half_day" | "excused";
export type ProjectIssueCategory =
  | "weather"
  | "safety"
  | "quality"
  | "schedule"
  | "cost"
  | "workforce"
  | "procurement"
  | "equipment"
  | "design"
  | "compliance"
  | "logistics"
  | "community"
  | "operations"
  | "external"
  | "other";
export type ProjectIssueType =
  | "weather_delay"
  | "extreme_rain_flooding"
  | "high_wind"
  | "lightning_storm"
  | "extreme_heat"
  | "material_shortage"
  | "material_damage"
  | "late_delivery"
  | "vendor_non_performance"
  | "subcontractor_non_performance"
  | "workforce_shortage"
  | "labor_dispute"
  | "equipment_breakdown"
  | "equipment_unavailable"
  | "quality_defect"
  | "rework_required"
  | "inspection_failure"
  | "test_failure"
  | "safety_incident"
  | "near_miss"
  | "accident_injury"
  | "security_breach"
  | "theft_vandalism"
  | "design_change"
  | "drawing_conflict"
  | "rfi_pending"
  | "permit_hold"
  | "regulatory_stop_notice"
  | "environmental_non_compliance"
  | "access_restriction"
  | "traffic_logistics"
  | "utility_outage"
  | "community_complaint"
  | "scope_change"
  | "schedule_slippage"
  | "cost_overrun"
  | "payment_delay"
  | "it_system_outage"
  | "data_loss"
  | "handover_defect"
  | "force_majeure"
  | "general_site_issue"
  | "other";

export interface ProjectWorkforceLog {
  id: number;
  project: number;
  project_name: string;
  worker_id: string;
  employee: number | null;
  employee_name: string | null;
  trade: string;
  contractor: number | null;
  contractor_name: string | null;
  report_date: string;
  daily_attendance: WorkforceAttendanceStatus;
  shift: FieldShift;
  task_assigned: number | null;
  task_assigned_name: string | null;
  productivity: string | null;
  overtime_hours: string;
  laborers_count: number;
  skilled_count: number;
  supervisors_count: number;
  subcontractors_count: number;
  equipment_operators_count: number;
  notes: string;
  hr_employment_status: string | null;
  payroll_status: "not_linked" | "pending" | "synced";
  latest_payslip_period_end: string | null;
  latest_payslip_net_salary: string | null;
  safety_training_status: "not_linked" | "pending" | "compliant";
  total_headcount: number;
  created_by: number | null;
  updated_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectWorkforceSetupEmployee {
  id: number;
  worker_id: string;
  name: string;
  employment_status: string;
}

export interface ProjectWorkforceSetupContractor {
  id: number;
  name: string;
  category: string;
  compliance_status: string;
}

export interface ProjectWorkforceSetupTask {
  id: number;
  name: string;
  project: number | null;
  project_name: string | null;
  status: string;
  due_date: string | null;
}

export interface ProjectWorkforceSetupOptions {
  employees: ProjectWorkforceSetupEmployee[];
  contractors: ProjectWorkforceSetupContractor[];
  tasks: ProjectWorkforceSetupTask[];
}

export interface ProjectDailySiteReportPhoto {
  id: number;
  report: number;
  image: string;
  image_url: string | null;
  caption: string;
  taken_at: string | null;
  uploaded_by: number | null;
  created_at: string;
}

export interface ProjectDailySiteReport {
  id: number;
  project: number;
  project_name: string;
  report_date: string;
  shift: FieldShift;
  weather: SiteWeather;
  weather_notes: string;
  weather_delay_hours: string;
  progress_percent: string;
  laborers_count: number;
  skilled_count: number;
  supervisors_count: number;
  subcontractors_count: number;
  equipment_operators_count: number;
  workforce_summary: string;
  work_completed: string;
  planned_next_day: string;
  equipment_used: string;
  materials_delivered: string;
  materials_consumed: string;
  material_updates: string;
  visitors_log: string;
  instructions_issued: string;
  safety_observations: string;
  quality_observations: string;
  incidents: string;
  blockers: string;
  status: SiteReportStatus;
  escalation_required: boolean;
  submitted_by: number | null;
  reviewed_by: number | null;
  reviewed_at: string | null;
  created_by: number | null;
  updated_by: number | null;
  created_at: string;
  updated_at: string;
  photo_count: number;
  photos: ProjectDailySiteReportPhoto[];
}

export interface ProjectDeliveryConfirmation {
  id: number;
  grn_number: string;
  project: number | null;
  project_name: string | null;
  purchase_order: number;
  po_number: string;
  vendor: number;
  vendor_name: string;
  status: GRNStatus;
  received_date: string;
  expected_delivery_date: string | null;
  received_by: string;
  delivery_note_number: string;
  inspection_notes: string;
  notes: string;
  item_count: number;
  accepted_quantity: string;
  rejected_quantity: string;
  is_late: boolean;
  delay_days: number;
  created_at: string;
}

export interface ProjectDeliveryConfirmationSummary {
  total: number;
  on_time: number;
  late: number;
  pending_inspection: number;
  partial_acceptance: number;
  rejected: number;
  accepted: number;
  open_late_delivery_escalations: number;
}

export interface ProjectFieldEscalation {
  id: number;
  project: number;
  project_name: string;
  source_report: number | null;
  source_report_date: string | null;
  issue_date: string;
  issue_category: ProjectIssueCategory;
  issue_type: ProjectIssueType;
  location: string;
  weather_condition: SiteWeather | "";
  weather_delay_hours: string;
  estimated_schedule_impact_days: string | null;
  estimated_cost_impact: string | null;
  impact_summary: string;
  root_cause: string;
  immediate_action: string;
  title: string;
  description: string;
  severity: EscalationSeverity;
  status: EscalationStatus;
  owner_name: string;
  due_date: string | null;
  resolved_at: string | null;
  resolution_notes: string;
  created_by: number | null;
  updated_by: number | null;
  created_at: string;
  updated_at: string;
  is_overdue: boolean;
}

export interface ProjectFieldEscalationSummary {
  total: number;
  open: number;
  critical: number;
  overdue: number;
  weather_issues?: number;
  weather_delay_hours_total?: string;
}

export type ProjectExecutionInspectionType =
  | "material_receipt"
  | "workmanship"
  | "mep"
  | "finishes"
  | "safety_quality"
  | "pre_handover"
  | "other";

export type ProjectExecutionInspectionStatus =
  | "planned"
  | "in_progress"
  | "passed"
  | "failed"
  | "blocked"
  | "closed";

export type ProjectExecutionChecklistResult = "pass" | "fail" | "hold" | "na";

export interface ProjectExecutionInspectionItem {
  id: number;
  inspection: number;
  sort_order: number;
  checklist_group: string;
  checklist_item: string;
  result: ProjectExecutionChecklistResult;
  remarks: string;
  action_owner: string;
  action_due_date: string | null;
  resolved_on: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectExecutionInspection {
  id: number;
  project: number;
  project_name: string;
  phase: number | null;
  phase_name: string | null;
  source_report: number | null;
  source_report_date: string | null;
  inspection_number: string;
  inspection_type: ProjectExecutionInspectionType;
  status: ProjectExecutionInspectionStatus;
  inspected_on: string;
  shift: FieldShift;
  work_package: string;
  location: string;
  inspector_name: string;
  inspector_role: string;
  overall_score: string | null;
  critical_findings: number;
  major_findings: number;
  minor_findings: number;
  observations: string;
  corrective_actions: string;
  due_date: string | null;
  closed_at: string | null;
  created_by: number | null;
  updated_by: number | null;
  created_at: string;
  updated_at: string;
  checklist_items: ProjectExecutionInspectionItem[];
  failed_items_count: number;
  pending_actions_count: number;
}

export interface ProjectExecutionInspectionSummary {
  total: number;
  open: number;
  failed: number;
  due_actions: number;
}

// ── Project Pipeline ────────────────────────────────────────────────

export type DevPipelineStage =
  | "opportunity"
  | "feasibility"
  | "financial_model"
  | "due_diligence"
  | "ic_review"
  | "approved"
  | "on_hold"
  | "rejected";

export type DevPipelineDevType =
  | "residential"
  | "commercial"
  | "mixed_use"
  | "industrial"
  | "hospitality"
  | "retail"
  | "infrastructure"
  | "other";

export type DevPipelineICDecision = "pending" | "approved" | "deferred" | "rejected";

export interface PipelineOpportunityListItem {
  id: number;
  pipeline_ref: string;
  name: string;
  location: string;
  description: string;
  stage: DevPipelineStage;
  stage_display: string;
  stage_order: number;
  development_type: DevPipelineDevType;
  development_type_display: string;
  land_size_sqm: string | null;
  land_cost: string;
  land_status: string;
  estimated_gdv: string;
  estimated_cost: string;
  expected_irr: string;
  hurdle_rate: string;
  expected_margin_pct: string;
  number_of_units: number;
  meets_hurdle: boolean;
  profit: string;
  ic_decision: DevPipelineICDecision;
  ic_decision_display: string;
  project: number | null;
  project_name: string | null;
  identified_date: string | null;
  target_start_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface PipelineOpportunityDetail extends PipelineOpportunityListItem {
  gps_coordinates: string;
  market_analysis: string;
  feasibility_notes: string;
  ic_review_date: string | null;
  ic_conditions: string;
  ic_reviewers: string;
  target_completion_date: string | null;
  notes: string;
  created_by: number | null;
}

export interface PipelineSummary {
  total: number;
  total_gdv: string;
  approved: number;
  stages: { stage: string; label: string; count: number; total_gdv: string }[];
}

// ── Project Setup ───────────────────────────────────────────────────

export type TeamMemberRole =
  | "project_manager"
  | "lead_architect"
  | "structural_engineer"
  | "mep_consultant"
  | "quantity_surveyor"
  | "site_engineer"
  | "safety_officer"
  | "project_director"
  | "legal_counsel"
  | "finance_controller"
  | "other";

export type TeamAccessLevel = "read_only" | "contributor" | "financial_edit" | "full_access";
export type SetupStep = "basic_info" | "team_allocation" | "phase_definition" | "boq_baseline" | "completed";

export interface ProjectTeamMemberItem {
  id: number;
  project: number;
  user: number | null;
  name: string;
  role: TeamMemberRole;
  role_display: string;
  access_level: TeamAccessLevel;
  access_level_display: string;
  email: string;
  phone: string;
  company: string;
  is_active: boolean;
  assigned_date: string;
  notes: string;
}

export interface ProjectSetupConfigItem {
  id: number;
  project: number;
  project_name: string;
  project_status: string;
  pipeline_source: number | null;
  pipeline_source_name: string | null;
  pipeline_source_ref: string | null;
  current_step: SetupStep;
  current_step_display: string;
  is_complete: boolean;
  survey_plan_ref: string;
  certificate_of_occupancy: string;
  planned_phases: number;
  boq_initialized: boolean;
  template_applied: boolean;
  template_name: string;
  notes: string;
  completed_at: string | null;
  team_members: ProjectTeamMemberItem[];
  created_at: string;
  updated_at: string;
}

// ── Feasibility & Viability ──────────────────────────────────────────

export type FeasibilityStatus = "draft" | "in_review" | "approved" | "rejected" | "superseded";
export type FeasibilityRiskLevel = "low" | "medium" | "high";

export interface FeasibilityStudyListItem {
  id: number;
  study_ref: string;
  version: string;
  project: number;
  project_name: string;
  status: FeasibilityStatus;
  status_display: string;
  total_sales_value: string;
  other_income: string;
  gdv: string;
  total_development_cost: string;
  profit: string;
  profit_on_cost: number;
  margin_pct: number;
  expected_irr: string;
  hurdle_rate: string;
  meets_hurdle: boolean;
  breakeven_units_pct: string;
  sales_velocity: string;
  market_risk: FeasibilityRiskLevel;
  finance_risk: FeasibilityRiskLevel;
  construction_risk: FeasibilityRiskLevel;
  prepared_by: string;
  created_at: string;
  updated_at: string;
}

export interface FeasibilityStudyDetail extends FeasibilityStudyListItem {
  pipeline_source: number | null;
  number_of_units: number;
  avg_price_per_unit: string;
  avg_price_per_sqm: string;
  land_cost: string;
  land_legal_fees: string;
  construction_cost: string;
  professional_fees: string;
  professional_fees_pct: string;
  marketing_sales_cost: string;
  sales_commission_pct: string;
  finance_cost: string;
  contingency: string;
  contingency_pct: string;
  target_irr: string;
  project_duration_months: number;
  demand_analysis: string;
  competitor_projects: { name: string; units: number; price_per_unit: string; price_per_sqm: string; status: string }[];
  pricing_benchmarks: string;
  sensitivity_matrix: Record<string, Record<string, number>>;
  reviewed_by: string;
  notes: string;
  created_by: number | null;
}

// ── Land Acquisition ────────────────────────────────────────────────

export type LandTitleType = "c_of_o" | "governors_consent" | "excision" | "deed_of_assignment" | "right_of_occupancy" | "freehold" | "leasehold" | "pending";
export type LandVerificationStatus = "not_started" | "in_progress" | "encumbrance_found" | "verified" | "registered";
export type LandAcquisitionStatus = "prospecting" | "negotiation" | "mou_signed" | "due_diligence" | "contract_signed" | "payment_in_progress" | "completed" | "cancelled";
export type LandPaymentStatus = "scheduled" | "invoiced" | "paid" | "overdue";

export interface LandPaymentMilestoneItem {
  id: number;
  land_acquisition: number;
  title: string;
  amount: string;
  due_date: string | null;
  paid_date: string | null;
  status: LandPaymentStatus;
  status_display: string;
  payment_reference: string;
  recipient: string;
  notes: string;
  sort_order: number;
  created_at: string;
}

export interface LandAcquisitionListItem {
  id: number;
  parcel_id: string;
  project: number;
  project_name: string;
  location: string;
  land_size_sqm: string | null;
  title_type: LandTitleType;
  title_type_display: string;
  verification_status: LandVerificationStatus;
  verification_status_display: string;
  acquisition_status: LandAcquisitionStatus;
  acquisition_status_display: string;
  purchase_price: string;
  total_acquisition_cost: string;
  total_paid: string;
  balance_remaining: string;
  seller_name: string;
  escrow_secured: boolean;
  created_at: string;
  updated_at: string;
}

export interface LandAcquisitionDetail extends LandAcquisitionListItem {
  gps_latitude: string | null;
  gps_longitude: string | null;
  description: string;
  survey_plan_ref: string;
  title_document_ref: string;
  agency_fees: string;
  legal_fees: string;
  stamp_duty: string;
  registration_fees: string;
  land_search_date: string | null;
  land_search_registry: string;
  encumbrance_check: boolean;
  encumbrance_notes: string;
  govt_approval_status: string;
  govt_approval_tracking: string;
  govt_approval_days_elapsed: number;
  escrow_holder: string;
  seller_contact: string;
  notes: string;
  payment_milestones: LandPaymentMilestoneItem[];
  created_by: number | null;
}

// ── Development Budget ──────────────────────────────────────────────

export type DevBudgetStatus = "draft" | "baseline" | "revised" | "approved";
export type BudgetCostType = "hard" | "soft";
export type BudgetCategoryStatus = "draft" | "estimated" | "planned" | "contracted" | "locked";

export interface DevBudgetCategoryItem {
  id: number;
  budget: number;
  name: string;
  cost_type: BudgetCostType;
  cost_type_display: string;
  allocated_amount: string;
  actual_amount: string;
  variance: string;
  status: BudgetCategoryStatus;
  status_display: string;
  pct_of_tdc: number;
  sub_items: { name: string; amount: number }[];
  sort_order: number;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface DevBudgetListItem {
  id: number;
  project: number;
  project_name: string;
  version: string;
  status: DevBudgetStatus;
  status_display: string;
  is_baseline: boolean;
  total_development_cost: string;
  cost_per_sqm: number;
  equity_amount: string;
  debt_amount: string;
  total_land_area_sqm: string | null;
  contingency_pct: string;
  category_count: number;
  prepared_by: string;
  locked_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface DevBudgetDetail extends DevBudgetListItem {
  approved_by: string;
  notes: string;
  categories: DevBudgetCategoryItem[];
  created_by: number | null;
}

// ── Project Financing ────────────────────────────────────────────────

export type FinancingSourceType = "bank_loan" | "mezzanine" | "equity" | "joint_venture" | "private_placement" | "grant" | "other";
export type FinancingSourceStatus = "pending" | "active" | "fully_drawn" | "repaid" | "expired";
export type FinancingRateType = "fixed" | "variable";
export type DrawdownStatus = "requested" | "approved" | "disbursed" | "rejected";
export type RepaymentStatus = "scheduled" | "paid" | "overdue" | "waived";
export type CovenantStatus = "compliant" | "at_risk" | "breached" | "not_tested";

export interface FinancingDrawdown {
  id: number;
  source: number;
  reference: string;
  request_date: string;
  amount_requested: string;
  amount_received: string | null;
  status: DrawdownStatus;
  status_display: string;
  disbursement_date: string | null;
  milestone_reference: string;
  notes: string;
  created_at: string;
}

export interface FinancingRepayment {
  id: number;
  source: number;
  payment_date: string;
  principal_amount: string;
  interest_amount: string;
  total_payment: string;
  ending_balance: string;
  status: RepaymentStatus;
  status_display: string;
  actual_payment_date: string | null;
  notes: string;
  created_at: string;
}

export interface FinancingCovenant {
  id: number;
  source: number;
  name: string;
  description: string;
  threshold: string;
  current_value: string;
  status: CovenantStatus;
  status_display: string;
  last_tested: string | null;
  next_test_date: string | null;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface FinancingSourceListItem {
  id: number;
  reference: string;
  name: string;
  project: number;
  project_name: string;
  source_type: FinancingSourceType;
  source_type_display: string;
  status: FinancingSourceStatus;
  status_display: string;
  committed_amount: string;
  drawn_amount: string;
  available_amount: string;
  interest_rate: string | null;
  rate_type: FinancingRateType;
  rate_type_display: string;
  tenor_months: number;
  maturity_date: string | null;
  next_repayment_date: string | null;
  institution: string;
  created_at: string;
  updated_at: string;
}

export interface FinancingSourceDetail extends FinancingSourceListItem {
  rate_benchmark: string;
  arrangement_fee_pct: string;
  grace_period_months: number;
  repayment_frequency: string;
  agreement_date: string | null;
  first_drawdown_date: string | null;
  contact_person: string;
  contact_email: string;
  notes: string;
  drawdowns: FinancingDrawdown[];
  repayments: FinancingRepayment[];
  covenants: FinancingCovenant[];
  created_by: number | null;
}

export interface FinancingDashboard {
  total_committed: string;
  total_drawn: string;
  available_liquidity: string;
  wacc: number;
  equity_total: string;
  debt_total: string;
  next_repayment: { payment_date: string; principal_amount: string; interest_amount: string } | null;
  upcoming_drawdowns: number;
  at_risk_covenants: number;
}

// ── Consultants & Stakeholders ───────────────────────────────────────

export type ConsultantDiscipline = "architectural" | "structural" | "mep" | "quantity_surveying" | "legal" | "geotechnical" | "environmental" | "town_planning" | "land_surveying" | "project_management" | "interior_design" | "landscape" | "other";
export type ConsultantEngagementStatus = "onboarding" | "active" | "on_hold" | "completed" | "terminated";
export type ConsultantComplianceStatus = "green" | "yellow" | "red";
export type ConsultantPaymentMilestoneStatus = "pending" | "invoiced" | "paid" | "cancelled";
export type ConsultantDeliverableStatus = "pending" | "submitted" | "under_review" | "accepted" | "rejected";

export interface ConsultantPaymentMilestoneItem {
  id: number;
  consultant: number;
  description: string;
  amount: string;
  trigger_date: string | null;
  status: ConsultantPaymentMilestoneStatus;
  status_display: string;
  paid_date: string | null;
  notes: string;
  sort_order: number;
  created_at: string;
}

export interface ConsultantDeliverableItem {
  id: number;
  consultant: number;
  name: string;
  due_date: string | null;
  format: string;
  format_display: string;
  status: ConsultantDeliverableStatus;
  status_display: string;
  submitted_date: string | null;
  notes: string;
  sort_order: number;
  created_at: string;
}

export interface ConsultantCommunicationLogItem {
  id: number;
  consultant: number;
  entry_type: string;
  entry_type_display: string;
  date: string;
  subject: string;
  summary: string;
  attendees: string;
  action_items: string;
  logged_by: string;
  created_at: string;
}

export interface ProjectConsultantListItem {
  id: number;
  project: number;
  project_name: string;
  firm_name: string;
  contact_person: string;
  contact_role: string;
  email: string;
  phone: string;
  whatsapp: string;
  discipline: ConsultantDiscipline;
  discipline_display: string;
  status: ConsultantEngagementStatus;
  status_display: string;
  contract_value: string;
  amount_paid: string;
  amount_remaining: string;
  payment_progress: number;
  compliance_status: ConsultantComplianceStatus;
  compliance_status_display: string;
  insurance_expiry: string | null;
  license_expiry: string | null;
  contract_start_date: string | null;
  contract_end_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectConsultantDetail extends ProjectConsultantListItem {
  address: string;
  scope_of_work: string;
  insurance_policy: string;
  license_number: string;
  reports_to: string;
  collaborates_with: string[];
  notes: string;
  payment_milestones: ConsultantPaymentMilestoneItem[];
  deliverables: ConsultantDeliverableItem[];
  communication_logs: ConsultantCommunicationLogItem[];
  created_by: number | null;
}

// ── Approvals & Permits ──────────────────────────────────────────────

export type PermitType = "environmental" | "planning" | "building" | "fire_safety" | "utility_water" | "utility_power" | "utility_sewer" | "road_closure" | "heritage" | "aviation" | "occupancy" | "other";
export type PermitStatus = "not_started" | "application_filed" | "under_review" | "clarification" | "approved" | "conditional" | "rejected" | "expired" | "renewed";

export interface PermitSubmissionItem {
  id: number;
  permit: number;
  version: string;
  description: string;
  documents_list: string;
  submission_date: string;
  submitted_by: string;
  authority_receipt_ref: string;
  notes: string;
  created_at: string;
}

export interface PermitQueryItem {
  id: number;
  permit: number;
  query_date: string;
  subject: string;
  description: string;
  assigned_consultant: string;
  response: string;
  response_date: string | null;
  status: "open" | "in_progress" | "resolved";
  status_display: string;
  notes: string;
  created_at: string;
}

export interface ProjectPermitListItem {
  id: number;
  reference: string;
  name: string;
  project: number;
  project_name: string;
  permit_type: PermitType;
  permit_type_display: string;
  status: PermitStatus;
  status_display: string;
  is_critical_path: boolean;
  is_delayed: boolean;
  authority_name: string;
  application_date: string | null;
  expected_approval_date: string | null;
  actual_approval_date: string | null;
  expiry_date: string | null;
  days_until_expiry: number | null;
  application_fee: string;
  fee_paid: boolean;
  depends_on: number | null;
  depends_on_name: string | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectPermitDetail extends ProjectPermitListItem {
  authority_contact: string;
  authority_portal: string;
  renewal_date: string | null;
  approval_certificate_ref: string;
  conditions: string;
  rejection_reason: string;
  notes: string;
  submissions: PermitSubmissionItem[];
  queries: PermitQueryItem[];
  created_by: number | null;
}

export interface PermitSummary {
  total: number;
  pending: number;
  approved: number;
  rejected: number;
  expired: number;
  delayed: number;
  critical_path_pending: number;
}

// ── Design Management ────────────────────────────────────────────────

export type DesignStage = "concept" | "schematic" | "detailed" | "construction" | "as_built";
export type DesignStageStatus = "not_started" | "in_progress" | "in_review" | "closed";
export type DrawingDiscipline = "architectural" | "structural" | "mep_mechanical" | "mep_electrical" | "mep_plumbing" | "civil" | "landscape" | "interior" | "other";
export type DrawingApprovalState = "draft" | "for_review" | "approved_noted" | "afc" | "superseded" | "revise_resubmit";

export interface DesignPhaseItem {
  id: number;
  project: number;
  stage: DesignStage;
  stage_display: string;
  status: DesignStageStatus;
  status_display: string;
  total_deliverables: number;
  approved_deliverables: number;
  progress: number;
  closeout_checked: boolean;
  sort_order: number;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface DrawingRevisionItem {
  id: number;
  drawing: number;
  revision_code: string;
  change_description: string;
  submitted_by: string;
  submitted_date: string;
  approval_state: DrawingApprovalState;
  approval_state_display: string;
  reviewer_comments: string;
  reviewed_by: string;
  reviewed_date: string | null;
  created_at: string;
}

export interface DrawingListItem {
  id: number;
  project: number;
  project_name: string;
  design_phase: number | null;
  design_phase_stage: string | null;
  drawing_number: string;
  title: string;
  discipline: DrawingDiscipline;
  discipline_display: string;
  current_revision: string;
  approval_state: DrawingApprovalState;
  approval_state_display: string;
  scale: string;
  submitted_by: string;
  last_updated: string;
  created_at: string;
}

export interface DrawingDetail extends DrawingListItem {
  notes: string;
  revisions: DrawingRevisionItem[];
  created_by: number | null;
}

export interface DesignReviewMeetingItem {
  id: number;
  project: number;
  project_name: string;
  date: string;
  title: string;
  attendees: string;
  key_decisions: string;
  action_items: { description: string; assigned_to: string; due_date: string }[];
  linked_drawings: number[];
  minutes_notes: string;
  recorded_by: string;
  created_at: string;
}

// ── Procurement Planning ─────────────────────────────────────────────

export type ProcurementPackageStatus = "planning" | "pqq" | "tendering" | "evaluation" | "negotiation" | "awarded" | "signed" | "on_hold" | "cancelled";

export interface PackageBidderItem {
  id: number;
  package: number;
  firm_name: string;
  specialization: string;
  bid_amount: string | null;
  proposed_duration_days: number | null;
  score_price: string | null;
  score_technical: string | null;
  score_timeline: string | null;
  score_safety: string | null;
  total_score: string | null;
  is_recommended: boolean;
  is_prequalified: boolean;
  compliance_notes: string;
  notes: string;
  created_at: string;
}

export interface ProcurementPackageListItem {
  id: number;
  plan: number;
  name: string;
  description: string;
  status: ProcurementPackageStatus;
  status_display: string;
  estimated_budget: string;
  contract_value: string;
  budget_variance: string | null;
  pqq_issue_date: string | null;
  rfp_issue_date: string | null;
  tender_return_date: string | null;
  evaluation_end_date: string | null;
  award_date: string | null;
  contract_start_date: string | null;
  awarded_to: string;
  is_behind_schedule: boolean;
  bidder_count: number;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface ProcurementPackageDetail extends ProcurementPackageListItem {
  award_justification: string;
  notes: string;
  bidders: PackageBidderItem[];
}

export interface ProcurementPlanListItem {
  id: number;
  project: number;
  project_name: string;
  strategy: string;
  strategy_display: string;
  total_budget: string;
  contingency_pct: string;
  package_count: number;
  total_allocated: string;
  total_contracted: string;
  created_at: string;
  updated_at: string;
}

export interface ProcurementPlanDetail extends ProcurementPlanListItem {
  notes: string;
  packages: ProcurementPackageListItem[];
  created_by: number | null;
}

// ── Sales & Revenue Forecast ─────────────────────────────────────────

export type SaleableUnitType = "studio" | "1_bed" | "2_bed" | "3_bed" | "4_bed" | "penthouse" | "duplex" | "commercial" | "office" | "parking" | "storage" | "other";
export type SaleableUnitStatus = "available" | "reserved" | "under_contract" | "sold" | "held";

export interface SaleableUnitItem {
  id: number;
  forecast: number;
  unit_id: string;
  unit_type: SaleableUnitType;
  unit_type_display: string;
  floor_location: string;
  size_sqm: string | null;
  asking_price: string;
  minimum_price: string;
  sold_price: string | null;
  price_per_sqm: number | null;
  status: SaleableUnitStatus;
  status_display: string;
  buyer_name: string;
  reserved_date: string | null;
  sold_date: string | null;
  notes: string;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface SalesPhaseTargetItem {
  id: number;
  forecast: number;
  phase_name: string;
  start_date: string;
  end_date: string;
  target_units: number;
  target_revenue: string;
  actual_units: number;
  actual_revenue: string;
  variance: string;
  unit_variance: number;
  milestone_trigger: string;
  sort_order: number;
  created_at: string;
}

export interface SalesRevenueForecastListItem {
  id: number;
  project: number;
  project_name: string;
  gross_development_value: string;
  marketing_budget: string;
  marketing_budget_pct: string;
  sales_launch_date: string | null;
  target_sellout_date: string | null;
  total_units: number;
  sold_units: number;
  reserved_units: number;
  actual_revenue: string;
  created_at: string;
  updated_at: string;
}

export interface SalesRevenueForecastDetail extends SalesRevenueForecastListItem {
  payment_structure: { stage: string; pct: number }[];
  agents: { firm: string; commission_pct: number }[];
  notes: string;
  units: SaleableUnitItem[];
  phase_targets: SalesPhaseTargetItem[];
  created_by: number | null;
}

// ── Stage Gates ──────────────────────────────────────────────────────

export type StageGateType = "feasibility" | "investment_approval" | "pre_construction" | "design_completion" | "procurement_completion" | "construction_midpoint" | "practical_completion" | "testing_commissioning" | "handover" | "closeout" | "custom";
export type StageGateStatus = "locked" | "under_review" | "open" | "conditional" | "failed";

export interface StageGatePrerequisiteMilestone {
  id: number;
  name: string;
  is_completed: boolean;
  target_date: string | null;
  completed_date: string | null;
  reference_code: string;
}

export interface StageGateListItem {
  id: number;
  project: number;
  project_name: string;
  gate_type: StageGateType;
  gate_type_display: string;
  name: string;
  description: string;
  status: StageGateStatus;
  status_display: string;
  sort_order: number;
  scheduled_review_date: string | null;
  actual_review_date: string | null;
  decided_by: string;
  decision_date: string | null;
  baseline_date: string | null;
  delay_days: number;
  is_overdue: boolean;
  prerequisites_met: boolean;
  prerequisite_count: number;
  financial_release_triggered: boolean;
  created_at: string;
  updated_at: string;
}

export interface StageGateDetail extends StageGateListItem {
  prerequisite_notes: string;
  prerequisite_milestones: number[];
  prerequisite_milestones_detail: StageGatePrerequisiteMilestone[];
  conditions: string;
  rejection_reason: string;
  delay_root_cause: string;
  recovery_plan: string;
  financial_release_notes: string;
  notes: string;
  created_by: number | null;
}

export interface StageGateSummary {
  total: number;
  locked: number;
  under_review: number;
  passed: number;
  overdue: number;
  upcoming: { id: number; name: string; scheduled_review_date: string; status: string }[];
}

// ── Document Control ─────────────────────────────────────────────────

export type DocumentFolder = "01_feasibility" | "02_legal" | "03_design" | "04_permits" | "05_governance" | "06_financial" | "07_procurement" | "08_construction" | "09_hse" | "10_closeout" | "other";
export type DocumentClassification = "public" | "internal" | "confidential" | "restricted";
export type DocumentExecutionStatus = "draft" | "for_review" | "approved" | "executed" | "scanned" | "superseded";

export interface DocumentVersionItem {
  id: number;
  document: number;
  version_label: string;
  change_summary: string;
  uploaded_by: string;
  uploaded_date: string;
  is_current: boolean;
  notes: string;
  created_at: string;
}

export interface DocumentTransmittalItem {
  id: number;
  document: number;
  transmittal_ref: string;
  recipient: string;
  purpose: string;
  purpose_display: string;
  sent_date: string;
  acknowledged: boolean;
  acknowledged_date: string | null;
  sent_by: string;
  notes: string;
  created_at: string;
}

export interface ProjectDocumentListItem {
  id: number;
  reference: string;
  title: string;
  project: number;
  project_name: string;
  folder: DocumentFolder;
  folder_display: string;
  classification: DocumentClassification;
  classification_display: string;
  execution_status: DocumentExecutionStatus;
  execution_status_display: string;
  current_version: string;
  author: string;
  source: string;
  expiry_date: string | null;
  is_expiring_soon: boolean;
  linked_module: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectDocumentDetail extends ProjectDocumentListItem {
  description: string;
  retention_years: number | null;
  notes: string;
  versions: DocumentVersionItem[];
  transmittals: DocumentTransmittalItem[];
  created_by: number | null;
}

export interface MeetingMinutesItem {
  id: number;
  project: number;
  project_name: string;
  series: string;
  date: string;
  title: string;
  attendees: string;
  minutes_text: string;
  action_items: { description: string; assigned_to: string; due_date: string; status: string }[];
  recorded_by: string;
  created_at: string;
}

// ── Project Communications ───────────────────────────────────────────

export type AnnouncementPriority = "critical" | "high" | "normal" | "low";
export type AnnouncementAudience = "all" | "internal" | "external" | "investors" | "consultants";

export interface ProjectAnnouncementItem {
  id: number;
  project: number;
  project_name: string;
  subject: string;
  body: string;
  priority: AnnouncementPriority;
  priority_display: string;
  audience: AnnouncementAudience;
  audience_display: string;
  is_pinned: boolean;
  published_by: string;
  published_at: string;
}

export interface ProjectDecisionLogItem {
  id: number;
  project: number;
  project_name: string;
  decision_id: string;
  subject: string;
  description: string;
  decided_by: string;
  rationale: string;
  decision_date: string;
  meeting_reference: string;
  impact_modules: string[];
  status: "active" | "superseded" | "reversed";
  notes: string;
  created_at: string;
}

export interface StakeholderUpdateListItem {
  id: number;
  project: number;
  project_name: string;
  title: string;
  frequency: string;
  frequency_display: string;
  report_date: string;
  distribution_group: string;
  prepared_by: string;
  sent_at: string | null;
  read_count: number;
  recipient_count: number;
  created_at: string;
}

export interface StakeholderUpdateDetail extends StakeholderUpdateListItem {
  executive_summary: string;
  schedule_status: string;
  financial_status: string;
  risk_blockers: string;
  recipients: { name: string; email: string; read: boolean }[];
  notes: string;
}

// ── Project Reporting ────────────────────────────────────────────────

export type ProjectReportType = "executive" | "financial" | "schedule" | "risk" | "investor" | "monthly" | "custom";
export type RAGStatus = "green" | "amber" | "red";

export interface ProjectReportListItem {
  id: number;
  reference: string;
  title: string;
  project: number;
  project_name: string;
  report_type: ProjectReportType;
  report_type_display: string;
  report_date: string;
  period_start: string | null;
  period_end: string | null;
  schedule_rag: RAGStatus;
  budget_rag: RAGStatus;
  quality_rag: RAGStatus;
  safety_rag: RAGStatus;
  overall_completion_pct: string | null;
  original_budget: string | null;
  forecast_at_completion: string | null;
  budget_variance: string | null;
  budget_variance_pct: number | null;
  is_frozen: boolean;
  prepared_by: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectReportDetail extends ProjectReportListItem {
  executive_summary: string;
  key_achievements: string[];
  key_issues: string[];
  committed_spend: string | null;
  actual_spend: string | null;
  contingency_used_pct: string | null;
  schedule_variance_summary: string;
  critical_path_impact: string;
  top_risks: { risk: string; impact: string; probability: string; mitigation: string; owner: string }[];
  approved_by: string;
  notes: string;
  created_by: number | null;
}

// ── Construction Reports ─────────────────────────────────────────────

export type ReportCategory = "progress" | "financial" | "hse" | "contractual" | "quality";
export type ReportStatus = "draft" | "in_review" | "published" | "archived";
export type ReportFrequency = "daily" | "weekly" | "fortnightly" | "monthly" | "quarterly" | "ad_hoc";

export interface ConstructionReportListItem {
  id: number;
  reference: string;
  title: string;
  project: number;
  project_name: string;
  category: ReportCategory;
  category_display: string;
  status: ReportStatus;
  status_display: string;
  frequency: ReportFrequency;
  frequency_display: string;
  reporting_period_start: string | null;
  reporting_period_end: string | null;
  prepared_by: string;
  published_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConstructionReportDetail extends ConstructionReportListItem {
  executive_summary: string;
  key_highlights: string;
  key_risks: string;
  recommendations: string;
  recipients: string;
  notes: string;
  created_by: number | null;
}

export interface ReportsSummary {
  total: number;
  draft: number;
  in_review: number;
  published: number;
  by_category: { category: string; count: number }[];
}

// ── Project Closeout ─────────────────────────────────────────────────

export type CloseoutStatus = "in_progress" | "pending_review" | "completed" | "archived";
export type SnagStatus = "open" | "in_progress" | "resolved" | "accepted";

export interface FinalAccountEntryItem {
  id: number;
  closeout: number;
  contractor_name: string;
  original_contract_value: string;
  approved_variations: string;
  final_settled_amount: string;
  variance: string;
  retention_held: string;
  retention_released: boolean;
  closeout_certificate_issued: boolean;
  performance_rating: number | null;
  performance_notes: string;
  created_at: string;
}

export interface SnagListItemType {
  id: number;
  closeout: number;
  location: string;
  description: string;
  responsible_contractor: string;
  status: SnagStatus;
  status_display: string;
  reported_date: string;
  resolved_date: string | null;
  notes: string;
  created_at: string;
}

export interface WarrantyTrackerItem {
  id: number;
  closeout: number;
  asset_system: string;
  provider: string;
  warranty_start: string;
  warranty_end: string;
  is_active: boolean;
  days_remaining: number;
  claim_log: { date: string; issue: string; resolution: string; status: string }[];
  notes: string;
  created_at: string;
}

export interface ProjectCloseoutListItem {
  id: number;
  project: number;
  project_name: string;
  status: CloseoutStatus;
  status_display: string;
  completion_pct: number;
  practical_completion_date: string | null;
  final_completion_date: string | null;
  final_project_cost: string | null;
  original_budget: string | null;
  budget_variance: string | null;
  retention_held: string;
  retention_released: string;
  snag_count: number;
  open_snag_count: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectCloseoutDetail extends ProjectCloseoutListItem {
  total_variations: string;
  retention_release_date: string | null;
  financial_reconciliation_done: boolean;
  contracts_closed: boolean;
  handover_completed: boolean;
  snags_resolved: boolean;
  documentation_archived: boolean;
  warranties_registered: boolean;
  notes: string;
  final_accounts: FinalAccountEntryItem[];
  snag_items: SnagListItemType[];
  warranties: WarrantyTrackerItem[];
  created_by: number | null;
}

// ── Contracts & Agreements ───────────────────────────────────────────

export type ContractType = "construction" | "supply" | "service" | "framework" | "consultancy" | "lease" | "subcontract" | "jv" | "other";
export type ContractStatus = "draft" | "negotiation" | "pending_approval" | "executed" | "suspended" | "completed" | "terminated" | "expired";

export interface ContractAmendmentItem {
  id: number;
  contract: number;
  amendment_number: string;
  amendment_type: string;
  amendment_type_display: string;
  title: string;
  description: string;
  status: string;
  status_display: string;
  value_change: string;
  time_extension_days: number;
  effective_date: string | null;
  approved_by: string;
  approved_date: string | null;
  reason: string;
  notes: string;
  created_at: string;
}

export interface ContractClauseItem {
  id: number;
  contract: number;
  clause_number: string;
  title: string;
  category: string;
  category_display: string;
  body: string;
  is_critical: boolean;
  sort_order: number;
  notes: string;
  created_at: string;
}

export interface ContractListItem {
  id: number;
  contract_number: string;
  title: string;
  vendor: number;
  vendor_name: string;
  project: number | null;
  project_name: string | null;
  contract_type: ContractType;
  contract_type_display: string;
  status: ContractStatus;
  status_display: string;
  is_active: boolean;
  original_value: string;
  revised_value: string;
  currency: string;
  is_price_locked: boolean;
  effective_date: string | null;
  expiry_date: string | null;
  days_until_expiry: number | null;
  payment_terms_summary: string;
  retention_pct: string;
  amendment_count: number;
  created_at: string;
  updated_at: string;
}

export interface ContractDetail extends ContractListItem {
  purchase_order: number | null;
  price_escalation_clause: string;
  locked_rates: { item: string; unit: string; rate: number; valid_until: string }[];
  completion_date: string | null;
  renewal_date: string | null;
  notice_period_days: number;
  advance_payment_pct: string;
  defects_liability_months: number;
  sla_response_hours: number | null;
  sla_resolution_hours: number | null;
  sla_uptime_pct: string | null;
  sla_penalty_per_breach: string;
  sla_notes: string;
  insurance_required: boolean;
  insurance_minimum_cover: string;
  performance_bond_pct: string;
  liquidated_damages_rate: string;
  liquidated_damages_cap_pct: string;
  signed_by_org: string;
  signed_by_vendor: string;
  signed_date: string | null;
  witness: string;
  scope_of_work: string;
  exclusions: string;
  dispute_resolution: string;
  governing_law: string;
  total_amendments_value: string;
  amendments: ContractAmendmentItem[];
  clauses: ContractClauseItem[];
  notes: string;
  created_by: number | null;
}

export interface ContractSummary {
  total: number;
  active: number;
  draft_negotiation: number;
  completed: number;
  expired: number;
  expiring_30d: number;
  total_value: string;
  framework_agreements: number;
  price_locked: number;
}

export type ProjectVariationOrderStatus =
  | "draft"
  | "submitted"
  | "under_review"
  | "approved"
  | "rejected"
  | "superseded"
  | "archived";

export interface ProjectVariationOrder {
  id: number;
  project: number;
  project_name: string;
  project_risk_rating: "low" | "medium" | "high" | "critical";
  variation_number: string;
  title: string;
  change_summary: string;
  reason: string;
  status: ProjectVariationOrderStatus;
  contract_value: string;
  currency: string;
  requested_date: string;
  due_date: string | null;
  related_document: number | null;
  related_document_number: string | null;
  related_document_title: string | null;
  created_by: number | null;
  updated_by: number | null;
  created_at: string;
  updated_at: string;
  is_high_value: boolean;
}

export interface ProjectVariationSummary {
  total: number;
  pending: number;
  high_value_pending: number;
  approved_value: number;
  pending_value: number;
  projects_impacted: number;
}

export type ConstructionContractorPerformanceBand = "strong" | "watch" | "weak";

export interface ConstructionSiteOverviewKpis {
  project_progress_percent: number;
  schedule_variance_days: number;
  cost_variance_amount: number;
  cost_variance_percent: number;
  open_rfis: number;
  pending_inspections: number;
  safety_incidents: number;
  material_shortages: number;
  workforce_count: number;
  equipment_utilization_percent: number;
  quality_issues: number;
  delayed_tasks: number;
  contractor_performance_score: number;
  contractor_performance_band: ConstructionContractorPerformanceBand;
}

export interface ConstructionSiteOverviewWidgets {
  progress_curve: Array<{
    date: string;
    progress_percent: number;
  }>;
  cost_vs_budget: Array<{
    project_id: number;
    project_name: string;
    planned: number;
    actual: number;
  }>;
  labour_distribution: Array<{
    label: string;
    count: number;
  }>;
  material_consumption: Array<{
    period: string;
    amount: number;
  }>;
  safety_index: Array<{
    period: string;
    index: number;
    incidents: number;
    workforce_count: number;
  }>;
  inspection_status: Array<{
    status: ProjectExecutionInspectionStatus;
    count: number;
  }>;
}

export interface ConstructionSiteOverview {
  filters: {
    project: number | null;
    start_date: string;
    end_date: string;
  };
  currency_code: string;
  projects: Array<{
    id: number;
    name: string;
  }>;
  kpis: ConstructionSiteOverviewKpis;
  widgets: ConstructionSiteOverviewWidgets;
}

export type SiteMobilizationPreparationStatus =
  | "not_started"
  | "in_progress"
  | "completed"
  | "blocked";

export interface ConstructionSiteMobilization {
  id: number;
  project: number;
  project_name: string;
  planned_start_date: string | null;
  actual_start_date: string | null;
  site_preparation: {
    fencing: SiteMobilizationPreparationStatus;
    site_offices: SiteMobilizationPreparationStatus;
    storage_yards: SiteMobilizationPreparationStatus;
    worker_welfare_facilities: SiteMobilizationPreparationStatus;
    utilities_connection: SiteMobilizationPreparationStatus;
    temporary_roads: SiteMobilizationPreparationStatus;
    security_deployment: SiteMobilizationPreparationStatus;
  };
  checklist: {
    contractors_mobilized: boolean;
    equipment_delivered: boolean;
    material_staging: boolean;
    survey_control_established: boolean;
    permits_obtained: boolean;
    insurance_certificates: boolean;
    safety_induction: boolean;
    _linked_fields: string[];
    _manual_fields: string[];
  };
  linked_sources: {
    procurement: {
      contractors_count: number;
      material_staging_count: number;
    };
    hr: {
      equipment_delivery_count: number;
      safety_induction_count: number;
    };
  };
  completion: {
    site_preparation_percent: number;
    checklist_percent: number;
    overall_percent: number;
    blocked_items: number;
  };
  notes: string;
  last_integrations_synced_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConstructionSiteMobilizationResponse {
  filters: {
    project: number | null;
  };
  projects: Array<{
    id: number;
    name: string;
  }>;
  mobilization: ConstructionSiteMobilization | null;
}

export interface ConstructionScheduleSectionNotes {
  master_schedule: string;
  phase_schedules: string;
  lookahead_schedules: string;
  task_dependencies: string;
  critical_path: string;
  resource_assignments: string;
}

export interface ConstructionScheduleTimelineSections {
  project_manager: string;
  task_assignees: string;
  site_workers: string;
}

export interface ConstructionSchedulePhaseRow {
  phase_id: number;
  phase_name: string;
  status: ProjectPhaseStatus;
  planned_start_date: string | null;
  planned_end_date: string | null;
  actual_start_date: string | null;
  actual_end_date: string | null;
  duration_days: number | null;
  planned_budget: number;
  actual_cost: number;
  task_count: number;
  assigned_tasks_count: number;
  unassigned_tasks_count: number;
  progress_percent: number;
  slack_days: number;
  is_critical_path: boolean;
}

export interface ConstructionScheduleLookaheadTask {
  task_id: number;
  task_name: string;
  phase_id: number;
  phase_name: string;
  status: ProjectTaskStatus;
  priority: "low" | "medium" | "high" | "critical";
  due_date: string | null;
  assignee: string;
  dependency_count: number;
}

export interface ConstructionScheduleDependencyRow {
  scope: "phase" | "task";
  from: string;
  to: string;
  dependency_type: string;
  lag_days: number;
}

export interface ConstructionSchedule {
  id: number;
  project: number;
  project_name: string;
  lookahead_window_days: number;
  section_notes: ConstructionScheduleSectionNotes;
  timeline_sections: ConstructionScheduleTimelineSections;
  notes: string;
  created_at: string;
  updated_at: string;
  example_phases: Array<{
    name: string;
    present: boolean;
  }>;
  master_schedule: {
    planned_start_date: string | null;
    planned_end_date: string | null;
    actual_end_date: string | null;
    duration_days: number | null;
    phase_count: number;
    task_count: number;
    task_completion_percent: number;
    critical_phase_count: number;
  };
  phase_schedules: ConstructionSchedulePhaseRow[];
  lookahead_schedules: {
    window_days: number;
    start_date: string;
    end_date: string;
    tasks: ConstructionScheduleLookaheadTask[];
    overdue_open_tasks: number;
  };
  task_dependencies: ConstructionScheduleDependencyRow[];
  critical_path: {
    phase_ids: number[];
    phases: Array<{
      phase_id: number;
      phase_name: string;
      slack_days: number;
    }>;
    total_duration_days: number;
  };
  resource_assignments: {
    project_manager: string;
    assigned_user_count: number;
    assigned_people: string[];
    open_tasks_count: number;
    unassigned_open_tasks: number;
    site_workers_count: number;
    equipment_allocated_count: number;
  };
  linked_sources: {
    procurement_deliveries: {
      upcoming: number;
      overdue: number;
      received: number;
      goods_receipts_logged: number;
    };
    labour_availability: {
      active_employees: number;
      assigned_to_schedule: number;
      unassigned_open_tasks: number;
    };
    equipment_scheduling: {
      allocated: number;
      pending: number;
    };
  };
}

export interface ConstructionScheduleResponse {
  filters: {
    project: number | null;
  };
  projects: Array<{
    id: number;
    name: string;
  }>;
  schedule: ConstructionSchedule | null;
}

export interface ConstructionContractorProfile {
  id: number;
  project: number;
  project_name: string;
  contractor: number;
  contractor_name: string;
  company_snapshot: {
    id: number;
    name: string;
    category: string;
    contact_person: string;
    email: string;
    phone: string;
    address: string;
    compliance_status: string;
    performance_rating: string;
  };
  company_profile: string;
  trade_specialization: string;
  contract_value: string;
  insurance: string;
  licenses: string;
  performance_rating: string;
  payment_history: string;
  safety_record: string;
  quality_record: string;
  site_instructions: string;
  work_packages: number[];
  work_package_records: Array<{
    id: number;
    package_id: string | null;
    name: string;
    budget: string;
    start_date: string | null;
    end_date: string | null;
  }>;
  rfis: number[];
  rfi_records: Array<{
    id: number;
    title: string;
    status: EscalationStatus;
    issue_date: string;
    severity: EscalationSeverity;
  }>;
  inspection_results: number[];
  inspection_result_records: Array<{
    id: number;
    inspection_number: string;
    status: ProjectExecutionInspectionStatus;
    inspected_on: string;
    overall_score: string | null;
  }>;
  received_items: {
    site_instructions: {
      count: number;
      items: string[];
    };
    rfis: {
      count: number;
    };
    inspection_results: {
      count: number;
    };
  };
  created_by: number | null;
  updated_by: number | null;
  created_at: string;
  updated_at: string;
}

// --- Document repository types ---

export type DocumentStatus =
  | "draft"
  | "submitted"
  | "under_review"
  | "approved"
  | "rejected"
  | "superseded"
  | "archived";

export type DocumentConfidentiality =
  | "public"
  | "internal"
  | "confidential"
  | "restricted";

export interface DocumentRecord {
  id: number;
  title: string;
  document_number: string;
  status: DocumentStatus;
  confidentiality_level: DocumentConfidentiality;
  project: number | null;
  project_name: string | null;
  land: number | null;
  land_name: string | null;
  unit: number | null;
  unit_number: string | null;
  vendor: number | null;
  vendor_name: string | null;
  client: number | null;
  client_name: string | null;
  document_type: number;
  document_type_name: string;
  category: string;
  phase: number;
  phase_name: string;
  contract_value: string;
  project_risk_rating: "low" | "medium" | "high" | "critical" | null;
  business_unit_division: number | null;
  business_unit_division_name: string | null;
  business_unit_department: number | null;
  business_unit_department_name: string | null;
  created_at: string;
  index_status: "pending" | "indexed" | "failed" | null;
  indexed_at: string | null;
}

export interface DocumentTypeOption {
  id: number;
  code: string;
  name: string;
  category_code: string;
  description: string;
  is_active: boolean;
}

export interface DocumentOwnerRoleOption {
  id: number;
  code: string;
  name: string;
  description: string;
  is_active: boolean;
}

export interface DocumentWorkflowPhaseOption {
  id: number;
  code: string;
  name: string;
  numbering_code: string;
  description: string;
  sort_order: number;
  is_active: boolean;
}

export interface DocumentRetentionPolicyOption {
  id: number;
  code: string;
  name: string;
  retention_years: number;
  is_indefinite: boolean;
  description: string;
  is_active: boolean;
}

export interface DocumentVersionRecord {
  id: number;
  document: number;
  document_number: string;
  version_major: number;
  version_minor: number;
  file_path: string;
  change_summary: string;
  uploaded_by: number | null;
  uploaded_by_name: string | null;
  approval_status: "pending" | "approved" | "rejected";
  uploaded_at: string;
}

export interface DocumentApprovalRecord {
  id: number;
  document_version: number;
  document_version_label: string;
  role: number;
  role_name: string;
  user: number;
  user_name: string;
  decision: "approved" | "rejected";
  comments: string;
  timestamp: string;
}

export type DocumentExpiryTriggerCategory =
  | "building_permit"
  | "insurance"
  | "performance_bond"
  | "eia_renewal"
  | "warranty_end";

export interface DocumentExpiryRecord {
  id: number;
  document: number;
  document_number: string;
  trigger_category: DocumentExpiryTriggerCategory;
  expiry_date: string;
  alert_90_days: boolean;
  alert_30_days: boolean;
  alert_expired: boolean;
  alert_90_days_sent_at: string | null;
  alert_30_days_sent_at: string | null;
  expired_alert_sent_at: string | null;
  escalated_at: string | null;
  last_checked_at: string | null;
}

export interface DocumentCommentRecord {
  id: number;
  document: number;
  document_number: string;
  document_version: number | null;
  author: number;
  author_name: string | null;
  comment: string;
  created_at: string;
}

export type DocumentAuditEventType =
  | "document_created"
  | "metadata_changed"
  | "version_uploaded"
  | "document_generated"
  | "approval_decision"
  | "workflow_submitted"
  | "workflow_step_decision"
  | "comment_added"
  | "document_downloaded"
  | "document_shared"
  | "signature_request_sent"
  | "signature_completed"
  | "signature_cancelled"
  | "document_archived"
  | "document_superseded"
  | "document_deleted";

export interface DocumentAuditEventRecord {
  id: number;
  document: number | null;
  document_number: string;
  document_title: string;
  document_version: number | null;
  version_label: string;
  event_type: DocumentAuditEventType;
  event_type_display: string;
  summary: string;
  actor: number | null;
  actor_name: string;
  actor_email: string | null;
  actor_role: number | null;
  actor_role_name: string;
  ip_address: string | null;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface DocumentWorkflowStepRecord {
  id: number;
  workflow_instance: number;
  sequence: number;
  approver_label: string;
  approver_role_slug: string;
  decision: "pending" | "approved" | "rejected";
  decided_by: number | null;
  decided_by_name: string | null;
  comments: string;
  decided_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentWorkflowInstanceRecord {
  id: number;
  document: number;
  document_number: string;
  document_title: string;
  template: number;
  template_name: string;
  matched_rule: number | null;
  matched_rule_name: string | null;
  state: DocumentStatus;
  submitted_at: string | null;
  completed_at: string | null;
  steps: DocumentWorkflowStepRecord[];
  created_at: string;
  updated_at: string;
}

export interface DocumentSearchIndexRecord {
  id: number;
  document: number;
  document_number: string;
  document_title: string;
  document_version: number | null;
  index_status: "pending" | "indexed" | "failed";
  indexed_at: string | null;
  error_message: string;
  updated_at: string;
}

export interface DocumentSearchIndexContentRecord {
  id: number;
  document: number;
  document_number: string;
  document_title: string;
  document_version: number | null;
  version_label: string;
  index_status: "pending" | "indexed" | "failed";
  indexed_at: string | null;
  updated_at: string;
  extracted_text: string;
  ocr_text: string;
  clause_text: string;
  indexed_clauses: string[];
  error_message: string;
}

export type DocumentSignatureProvider =
  | "docusign"
  | "adobe_acrobat_sign"
  | "dropbox_sign"
  | "signnow";

export type DocumentSignatureStatus =
  | "draft"
  | "sent"
  | "completed"
  | "declined"
  | "cancelled"
  | "failed";

export interface DocumentSignatureRequestRecord {
  id: number;
  document: number;
  document_number: string;
  document_title: string;
  document_version: number | null;
  version_label: string;
  provider: DocumentSignatureProvider;
  provider_display: string;
  status: DocumentSignatureStatus;
  status_display: string;
  provider_envelope_id: string;
  signing_url: string;
  signers: Array<{
    name: string;
    email: string;
    role: string;
    order: number;
    status: string;
  }>;
  subject: string;
  message: string;
  provider_payload: Record<string, unknown>;
  requested_by: number | null;
  requested_by_name: string | null;
  requested_at: string;
  sent_at: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  updated_at: string;
}

export interface DocumentSignatureProviderOption {
  key: DocumentSignatureProvider;
  label: string;
}

export interface DocumentSignatureProvidersResponse {
  providers: DocumentSignatureProviderOption[];
  default_provider: DocumentSignatureProvider;
}

export type DocumentGenerationKind = "contract" | "invoice" | "report";

export interface DocumentGenerationRecord {
  id: number;
  generation_kind: DocumentGenerationKind;
  title: string;
  template_code: string;
  document: number | null;
  document_number: string;
  document_title: string;
  document_version: number | null;
  version_label: string;
  branding_snapshot: Record<string, unknown>;
  context_payload: Record<string, unknown>;
  file_path: string;
  requested_by: number | null;
  requested_by_name: string | null;
  created_at: string;
}

export interface DocumentGenerationResult {
  generation_record: DocumentGenerationRecord;
  document: DocumentRecord;
  version: DocumentVersionRecord;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// --- Finance types ---

export type BillStatus = "draft" | "approved" | "paid" | "cancelled";
export type InvoiceStatus = "draft" | "sent" | "paid" | "overdue" | "cancelled";
export type FinancePaymentMethod = "bank_transfer" | "check" | "cash" | "credit_card" | "other";

export interface CustomerListItem {
  id: number;
  name: string;
  contact_person: string;
  email: string;
  phone: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  invoice_count: number;
}

export interface Customer extends CustomerListItem {
  address: string;
  tax_id: string;
  notes: string;
}

export interface BillLineItem {
  id: number;
  bill: number;
  description: string;
  quantity: string;
  unit_price: string;
  amount: string;
  sort_order: number;
}

export interface BillPayment {
  id: number;
  bill: number;
  amount: string;
  payment_date: string;
  payment_method: FinancePaymentMethod;
  reference_number: string;
  notes: string;
  created_at: string;
}

export interface BillListItem {
  id: number;
  bill_number: string;
  vendor: number;
  vendor_name: string;
  property: number | null;
  property_name: string | null;
  purchase_order: number | null;
  status: BillStatus;
  issue_date: string;
  due_date: string;
  total_amount: string;
  paid_amount: string;
  balance_due: string;
  is_overdue: boolean;
  days_overdue: number;
  created_at: string;
  updated_at: string;
}

export interface Bill extends BillListItem {
  subtotal: string;
  tax_amount: string;
  notes: string;
  line_items: BillLineItem[];
  payments: BillPayment[];
}

// --- Payment Voucher types ---

export type PaymentVoucherStatus = "draft" | "pending" | "approved" | "paid" | "voided" | "cancelled";

export type PaymentVoucherPriority = "standard" | "high";

export interface PaymentVoucherListItem {
  id: number;
  voucher_number: string;
  vendor: number | null;
  vendor_name: string;
  bill: number | null;
  bill_number: string | null;
  property_id: number | null;
  property_name: string | null;
  status: PaymentVoucherStatus;
  priority: PaymentVoucherPriority;
  issue_date: string;
  amount: string;
  payment_method: string;
  created_at: string;
}

export interface PaymentVoucherVendorDetail {
  id: number;
  name: string;
  contact_person: string;
  email: string;
  phone: string;
  bank_name: string;
  bank_account_number: string;
  bank_branch: string;
}

export interface PaymentVoucher extends PaymentVoucherListItem {
  description: string;
  notes: string;
  approved_by: number | null;
  approved_by_name: string | null;
  approved_at: string | null;
  paid_at: string | null;
  vendor_detail: PaymentVoucherVendorDetail | null;
}

// --- Payment Runs ---

export type PaymentRunStatus = "draft" | "scheduled" | "processing" | "completed" | "failed" | "cancelled";

export interface PaymentRunListItem {
  id: number;
  batch_id: string;
  status: PaymentRunStatus;
  total_value: string;
  payment_count: number;
  funding_account: number | null;
  funding_account_name: string | null;
  funding_account_label: string;
  scheduled_date: string | null;
  executed_at: string | null;
  created_at: string;
  created_by_name: string | null;
}

export interface PaymentRunVoucherItem {
  id: number;
  voucher_number: string;
  vendor_name: string;
  amount: string;
  status: PaymentVoucherStatus;
  priority: PaymentVoucherPriority;
  bank_name: string;
  bank_account_number: string;
}

export interface PaymentRun extends PaymentRunListItem {
  notes: string;
  executed_by_name: string | null;
  approved_by: number | null;
  approved_by_name: string | null;
  approved_at: string | null;
  funding_balance: string | null;
  voucher_items: PaymentRunVoucherItem[];
}

// --- Payment Receipts ---

export type PaymentReceiptStatus = "successful" | "settled" | "reversed" | "failed";

export interface PaymentReceiptListItem {
  id: number;
  receipt_number: string;
  transaction_reference: string;
  status: PaymentReceiptStatus;
  payment_date: string;
  amount: string;
  payment_method: string;
  vendor: number | null;
  vendor_name: string | null;
  voucher: number | null;
  voucher_number: string | null;
  created_at: string;
  created_by_name: string | null;
}

export interface PaymentReceiptAllocationItem {
  id: number;
  voucher_number: string;
  vendor_name: string;
  property_name: string | null;
  description: string;
  amount: string;
}

export interface PaymentReceipt extends PaymentReceiptListItem {
  payment_run: number | null;
  payment_run_batch_id: string | null;
  payer_account: string;
  payee_account: string;
  description: string;
  notes: string;
  allocation_items: PaymentReceiptAllocationItem[];
}

// --- Banking ---

export type BankAccountType = "current" | "savings" | "domiciliary" | "fixed_deposit";
export type BankAccountStatus = "active" | "inactive" | "closed";

export interface BankAccountListItem {
  id: number;
  account_name: string;
  bank_name: string;
  account_number: string;
  account_type: BankAccountType;
  currency: string;
  status: BankAccountStatus;
  current_balance: string;
  gl_account: number | null;
  gl_account_name: string | null;
  branch: string;
  created_at: string;
}

export interface BankLiquidityOverview {
  total_cash_on_hand: string;
  account_count: number;
  primary_account: {
    id: number;
    account_name: string;
    bank_name: string;
    current_balance: string;
  } | null;
  pending_outflow: string;
  pending_run_count: number;
}

export interface BankAccountAuthorizedUser {
  id: number;
  email: string;
  full_name: string;
}

export interface BankAccount extends BankAccountListItem {
  opening_balance: string;
  swift_code: string;
  sort_code: string;
  daily_transfer_limit: string | null;
  webhook_url: string;
  api_provider: string;
  api_key_ref: string;
  authorized_user_list: BankAccountAuthorizedUser[];
  notes: string;
}

export type BankTransactionType = "credit" | "debit";
export type BankTransactionStatus = "pending" | "cleared" | "reconciled" | "voided";

export interface BankTransactionListItem {
  id: number;
  bank_account: number;
  bank_account_name: string;
  bank_name: string;
  transaction_date: string;
  transaction_type: BankTransactionType;
  amount: string;
  reference: string;
  counterparty: string;
  status: BankTransactionStatus;
  created_at: string;
}

export interface BankTransaction extends BankTransactionListItem {
  value_date: string | null;
  description: string;
  receipt: number | null;
  receipt_number: string | null;
  voucher: number | null;
  voucher_number: string | null;
  notes: string;
}

export type BankReconciliationStatus = "in_progress" | "completed" | "cancelled";

export interface BankReconciliationListItem {
  id: number;
  bank_account: number;
  bank_account_name: string;
  bank_name: string;
  period_start: string;
  period_end: string;
  statement_balance: string;
  book_balance: string;
  difference: string;
  reconciled_count: number;
  unreconciled_count: number;
  status: BankReconciliationStatus;
  created_at: string;
  created_by_name: string | null;
}

export interface BankReconciliation extends BankReconciliationListItem {
  completed_by_name: string | null;
  completed_at: string | null;
  notes: string;
}

export interface InvoiceLineItem {
  id: number;
  invoice: number;
  description: string;
  quantity: string;
  unit_price: string;
  amount: string;
  sort_order: number;
}

export interface InvoicePayment {
  id: number;
  invoice: number;
  amount: string;
  payment_date: string;
  payment_method: FinancePaymentMethod;
  reference_number: string;
  notes: string;
  created_at: string;
}

export interface InvoiceListItem {
  id: number;
  invoice_number: string;
  customer: number;
  customer_name: string;
  property: number | null;
  property_name: string | null;
  status: InvoiceStatus;
  issue_date: string;
  due_date: string;
  total_amount: string;
  paid_amount: string;
  balance_due: string;
  is_overdue: boolean;
  days_overdue: number;
  created_at: string;
  updated_at: string;
}

export interface Invoice extends InvoiceListItem {
  subtotal: string;
  tax_amount: string;
  notes: string;
  line_items: InvoiceLineItem[];
  payments: InvoicePayment[];
}

export interface StatusCount {
  status: string;
  count: number;
}

export interface FinanceOverview {
  total_payable: string;
  total_receivable: string;
  overdue_payable_count: number;
  overdue_payable_amount: string;
  overdue_receivable_count: number;
  overdue_receivable_amount: string;
  recent_bills: BillListItem[];
  recent_invoices: InvoiceListItem[];
  bills_by_status: StatusCount[];
  invoices_by_status: StatusCount[];
}

// --- Chart of Accounts types ---

export type AccountType = "asset" | "liability" | "equity" | "revenue" | "expense";
export type AccountSubType =
  | "current_asset"
  | "fixed_asset"
  | "other_asset"
  | "current_liability"
  | "long_term_liability"
  | "owners_equity"
  | "retained_earnings"
  | "operating_revenue"
  | "other_revenue"
  | "operating_expense"
  | "cost_of_goods_sold"
  | "other_expense";

export interface AccountListItem {
  id: number;
  code: string;
  name: string;
  account_type: AccountType;
  sub_type: AccountSubType;
  parent: number | null;
  parent_name: string | null;
  is_active: boolean;
  is_system: boolean;
  created_at: string;
  updated_at: string;
}

export interface Account extends AccountListItem {
  organization: number;
  description: string;
}

// --- Journal & GL types ---

export type JournalStatus = "draft" | "posted" | "reversed";
export type JournalSourceType =
  | "manual"
  | "bill"
  | "invoice"
  | "payment"
  | "adjustment"
  | "closing"
  | "opening"
  | "payroll";

export interface JournalLineRecord {
  id: number;
  journal: number;
  line_number: number;
  account: number;
  account_code: string;
  account_name: string;
  debit_amount: string;
  credit_amount: string;
  memo: string;
  department: number | null;
  department_name: string | null;
  cost_center: number | null;
  cost_center_name: string | null;
}

export interface JournalEntryListItem {
  id: number;
  journal_number: string;
  entry_date: string;
  description: string;
  reference: string;
  source_type: JournalSourceType;
  source_id: number | null;
  status: JournalStatus;
  line_count: number;
  total_debit: string;
  total_credit: string;
  posted_at: string | null;
  posted_by: number | null;
  posted_by_name: string | null;
  created_by: number | null;
  created_by_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface JournalEntryDetail extends JournalEntryListItem {
  organization: number;
  reversed_entry: number | null;
  is_reversal: boolean;
  lines: JournalLineRecord[];
}

export interface LedgerEntryRecord {
  id: number;
  organization: number;
  journal_entry: number;
  journal_number: string;
  journal_line: number;
  account: number;
  account_code: string;
  account_name: string;
  entry_date: string;
  debit_amount: string;
  credit_amount: string;
  description: string;
  source_type: JournalSourceType;
  source_id: number | null;
  department: number | null;
  department_name: string | null;
  cost_center: number | null;
  cost_center_name: string | null;
  posted_at: string;
  created_at: string;
}

export interface GeneralLedgerResponse {
  page: number;
  page_size: any;
  count: number;
  limit: number;
  total_pages: number;
  totals: {
    debit: string;
    credit: string;
  };
  results: LedgerEntryRecord[];
}

export interface TrialBalanceRow {
  account_id: number;
  account_code: string;
  account_name: string;
  account_type: AccountType;
  movement_debit: string;
  movement_credit: string;
  debit_balance: string;
  credit_balance: string;
}

export interface TrialBalanceResponse {
  as_of: string;
  rows: TrialBalanceRow[];
  totals: {
    debit: string;
    credit: string;
    difference: string;
  };
  draft_journal_count: number;
  row_count: number;
}

// --- Notification types ---

export type NotificationSeverity = "info" | "warning" | "critical";
export type NotificationCategory =
  | "budget_warning"
  | "budget_exceeded"
  | "budget_digest"
  | "reports_ready"
  | "system"
  | "workflow_pending"
  | "workflow_approved"
  | "workflow_rejected"
  | "workflow_escalated"
  | "workflow_sla_warning"
  | "delegation_assigned"
  | "delegation_expired"
  | "project_update"
  | "project_risk"
  | "property_status"
  | "property_maint"
  | "procurement_order"
  | "procurement_grn"
  | "hr_leave"
  | "hr_lifecycle"
  | "partner_onboarding"
  | "crm_lead"
  | "crm_reservation";

export interface Notification {
  id: number;
  title: string;
  message: string;
  severity: NotificationSeverity;
  category: NotificationCategory;
  is_read: boolean;
  link_url: string;
  created_at: string;
  read_at: string | null;
  /** Only present in admin/org-scoped responses */
  recipient_email?: string;
  recipient_name?: string;
}

// --- Budget types ---

export type BudgetStatus = "draft" | "active" | "closed";
export type BudgetPeriodType = "annual" | "quarterly" | "monthly";

export interface BudgetLineItemRead {
  id: number;
  budget: number;
  account: number;
  account_code: string;
  account_name: string;
  department: number | null;
  department_name: string | null;
  cost_center: number | null;
  cost_center_name: string | null;
  budgeted_amount: string;
  actual_spent: string;
  pct_used: string;
  notes: string;
  sort_order: number;
}

export interface BudgetListItem {
  id: number;
  name: string;
  status: BudgetStatus;
  period_type: BudgetPeriodType;
  start_date: string;
  end_date: string;
  total_amount: string;
  overspend_tolerance_pct: string;
  warning_threshold_pct: string;
  total_spent: string;
  pct_used: string;
  line_item_count: number;
  created_at: string;
  updated_at: string;
}

export interface BudgetDetail extends BudgetListItem {
  notes: string;
  created_by: number | null;
  line_items: BudgetLineItemRead[];
}

export interface ReforecastLineItemRead {
  id: number;
  budget_line_item: number;
  account_code: string;
  account_name: string;
  current_amount: string;
  suggested_amount: string;
  actual_spent: string;
  delta: string;
}

export interface ReforecastSuggestion {
  id: number;
  budget: number;
  status: "pending" | "approved" | "rejected";
  reason: string;
  generated_at: string;
  reviewed_by: number | null;
  reviewed_at: string | null;
  line_items: ReforecastLineItemRead[];
}

export interface BudgetOverview {
  active_budgets: number;
  total_budgeted: string;
  total_spent: string;
  pct_used: string;
  warning_count: number;
  exceeded_count: number;
}

export interface MonthlyFlow {
  month: string;
  income: string;
  expenses: string;
}

export interface CategoryBreakdown {
  label: string;
  value: string;
}

export interface FinanceCashFlow {
  year: number;
  net_balance: string;
  total_income: string;
  total_expenses: string;
  monthly_flow: MonthlyFlow[];
  expense_by_vendor: CategoryBreakdown[];
  income_by_customer: CategoryBreakdown[];
  budget_pct_remaining: number;
}

export type FinanceTransactionType = "bill" | "invoice" | "bill_payment" | "invoice_payment";
export type FinanceTransactionDirection = "incoming" | "outgoing";

export interface FinanceTransaction {
  id: string;
  type: FinanceTransactionType;
  reference: string;
  counterparty: string;
  date: string;
  amount: string;
  status: string;
  direction: FinanceTransactionDirection;
}

export interface FinanceTransactionsResponse {
  count: number;
  page: number;
  page_size: number;
  type_counts: Record<string, number>;
  results: FinanceTransaction[];
}

// --- Compliance types ---

export type ComplianceCategory = "regulatory" | "environmental" | "safety" | "building_code" | "zoning" | "accessibility" | "fire_safety" | "occupational_health";
export type ComplianceRenewalFrequency = "one_time" | "annual" | "biannual" | "quarterly";
export type PropertyComplianceStatus = "compliant" | "non_compliant" | "pending_review" | "expired" | "exempt" | "not_applicable";
export type ViolationSeverity = "minor" | "moderate" | "major" | "critical";
export type ViolationStatus = "open" | "under_review" | "remediation" | "resolved" | "closed" | "appealed";
export type ComplianceAuditType = "internal" | "external" | "regulatory";
export type ComplianceAuditStatus = "scheduled" | "in_progress" | "completed" | "cancelled";
export type ComplianceAuditRating = "compliant" | "partially_compliant" | "non_compliant";

export interface ComplianceRequirementListItem {
  id: number;
  name: string;
  category: ComplianceCategory;
  regulatory_reference: string;
  renewal_frequency: ComplianceRenewalFrequency;
  is_mandatory: boolean;
  is_active: boolean;
  property_count: number;
  created_at: string;
  updated_at: string;
}

export interface ComplianceRequirement extends ComplianceRequirementListItem {
  description: string;
}

export interface PropertyComplianceListItem {
  id: number;
  property: number;
  property_name: string;
  requirement: number;
  requirement_name: string;
  requirement_category: ComplianceCategory;
  status: PropertyComplianceStatus;
  certificate_number: string;
  issuing_authority: string;
  expiry_date: string | null;
  next_review_date: string | null;
  responsible_person: string;
  created_at: string;
  updated_at: string;
}

export interface PropertyComplianceItem extends PropertyComplianceListItem {
  issue_date: string | null;
  last_reviewed_date: string | null;
  notes: string;
}

export interface ComplianceViolationListItem {
  id: number;
  property: number;
  property_name: string;
  compliance_item: number | null;
  title: string;
  violation_type: ComplianceCategory;
  severity: ViolationSeverity;
  status: ViolationStatus;
  reported_date: string;
  due_date: string | null;
  resolved_date: string | null;
  fine_amount: string | null;
  assigned_to: string;
  created_at: string;
  updated_at: string;
}

export interface ComplianceViolation extends ComplianceViolationListItem {
  description: string;
  corrective_action: string;
  notes: string;
}

export interface ComplianceAuditListItem {
  id: number;
  property: number;
  property_name: string;
  title: string;
  audit_type: ComplianceAuditType;
  status: ComplianceAuditStatus;
  scheduled_date: string;
  completed_date: string | null;
  auditor: string;
  overall_rating: ComplianceAuditRating | "";
  follow_up_required: boolean;
  created_at: string;
  updated_at: string;
}

export interface ComplianceAuditItem extends ComplianceAuditListItem {
  scope: string;
  findings: string;
  follow_up_notes: string;
  notes: string;
}

// --- Valuation types ---

export type ValuationType = "appraisal" | "internal" | "market" | "tax";
export type ComparableSaleSource = "mls" | "public_records" | "broker" | "auction" | "other";
export type ValuationAppealType = "tax_assessment" | "insurance" | "dispute";
export type ValuationAppealStatus = "filed" | "under_review" | "hearing_scheduled" | "decided" | "withdrawn";
export type ValuationAppealOutcome = "pending" | "upheld" | "reduced" | "increased" | "dismissed";

export interface ValuationListItem {
  id: number;
  property: number;
  property_name: string;
  valuation_date: string;
  value: string;
  valuation_type: ValuationType;
  appraiser: string;
  created_at: string;
}

export interface ValuationDetail extends ValuationListItem {
  notes: string;
}

export interface ComparableSaleListItem {
  id: number;
  property: number | null;
  property_name: string | null;
  address: string;
  sale_date: string;
  sale_price: string;
  property_type: string;
  area_sqft: string | null;
  price_per_sqft: string | null;
  source: ComparableSaleSource;
  proximity_km: string | null;
  created_at: string;
  updated_at: string;
}

export interface ComparableSaleDetail extends ComparableSaleListItem {
  notes: string;
}

export interface ValuationAppealListItem {
  id: number;
  property: number;
  property_name: string;
  valuation: number | null;
  appeal_type: ValuationAppealType;
  status: ValuationAppealStatus;
  filed_date: string;
  hearing_date: string | null;
  decision_date: string | null;
  assessed_value: string;
  requested_value: string;
  decided_value: string | null;
  outcome: ValuationAppealOutcome;
  created_at: string;
  updated_at: string;
}

export interface ValuationAppealDetail extends ValuationAppealListItem {
  filing_reference: string;
  representative: string;
  notes: string;
}

// --- Portfolio analytics types ---

export interface PortfolioKpis {
  total_value: string;
  total_acquisition: string;
  property_count: number;
  total_area_sqft: string;
  avg_price_per_sqft: string;
  unrealized_gain: string;
}

export interface TypeDistributionItem {
  type: string;
  count: number;
  total_value: string;
  total_area: string;
}

export interface ClassificationBreakdownItem {
  classification: string;
  count: number;
  total_value: string;
}

export interface ValuationHistoryItem {
  month: string;
  total_value: string;
  valuation_count: number;
}

export interface UnitOccupancyItem {
  status: string;
  count: number;
  total_area: string;
  total_asking_price: string;
}

export interface ProjectBudgetItem {
  id: number;
  name: string;
  status: string;
  budget: string | null;
  total_planned: string;
  total_actual: string;
  variance: string;
}

export interface PropertyGainItem {
  id: number;
  name: string;
  property_type: string;
  acquisition_price: string;
  current_value: string;
  gain: string;
  gain_pct: string;
}

export interface EncumbranceTypeItem {
  type: string;
  count: number;
  total_amount: string;
}

export interface EncumbranceSummary {
  by_type: EncumbranceTypeItem[];
  total_count: number;
  total_amount: string;
}

export interface ConstructionSummary {
  active_site_reports: number;
  avg_progress_percent: number;
  open_field_issues: number;
  recent_delay_entries: number;
}

export interface CrmSummary {
  active_leads: number;
  tenant_leads: number;
  active_reservations: number;
  converted_reservations: number;
  converted_value: string;
}

export interface HrSummary {
  active_employees: number;
  employees_on_leave: number;
  open_vacancies: number;
  staffing_gap: number;
}

export interface ProcurementSummary {
  open_commitments: number;
  committed_amount: string;
  overdue_deliveries: number;
  pending_requisitions: number;
}

export interface FacilitySummary {
  open_work_orders: number;
  urgent_work_orders: number;
  open_service_requests: number;
  pending_inspections: number;
}

export interface TenantSummary {
  active_tenants: number;
  open_tenant_requests: number;
  tenant_leads: number;
  active_tenant_reservations: number;
}

export interface PortfolioAnalytics {
  kpis: PortfolioKpis;
  type_distribution: TypeDistributionItem[];
  classification_breakdown: ClassificationBreakdownItem[];
  valuation_history: ValuationHistoryItem[];
  unit_occupancy: UnitOccupancyItem[];
  project_budget_summary: ProjectBudgetItem[];
  top_appreciating: PropertyGainItem[];
  top_depreciating: PropertyGainItem[];
  encumbrance_summary: EncumbranceSummary;
  construction_summary: ConstructionSummary;
  crm_summary: CrmSummary;
  hr_summary: HrSummary;
  procurement_summary: ProcurementSummary;
  facility_summary: FacilitySummary;
  tenant_summary: TenantSummary;
}

export interface BoardKpiPeriod {
  start_date: string;
  end_date: string;
  days: number;
}

export interface BoardProcurementCycleKpi {
  value: number;
  sample_size: number;
  unit: "days";
}

export interface BoardCostVarianceKpi {
  value: number;
  project_count: number;
  over_budget_projects: number;
  unit: "percentage";
}

export interface BoardVendorReliabilityKpi {
  value: number;
  vendor_count: number;
  unit: "score_0_100";
}

export interface BoardEmergencyPurchasesKpi {
  value: number;
  emergency_count: number;
  total_requisitions: number;
  unit: "percentage";
}

export interface BoardBudgetOverrunKpi {
  value: number;
  overrun_items: number;
  tracked_items: number;
  unit: "percentage";
}

export interface BoardApprovalTimeKpi {
  value: number;
  completed_workflows: number;
  unit: "hours";
}

export interface BoardKpiSnapshot {
  period: BoardKpiPeriod;
  kpis: {
    procurement_cycle_time_days: BoardProcurementCycleKpi;
    cost_variance_per_project_pct: BoardCostVarianceKpi;
    vendor_reliability_score: BoardVendorReliabilityKpi;
    emergency_purchases_pct: BoardEmergencyPurchasesKpi;
    budget_overrun_frequency_pct: BoardBudgetOverrunKpi;
    average_approval_time_hours: BoardApprovalTimeKpi;
  };
}

// --- Analytics freshness types ---

export interface SnapshotFreshnessItem {
  status: "fresh" | "stale" | "missing";
  last_computed: string | null;
  age_hours: number | null;
  is_stale: boolean;
}

export interface AnalyticsHealth {
  checked_at: string;
  portfolio: SnapshotFreshnessItem;
  board_kpis: SnapshotFreshnessItem;
}

// --- Risk alerts dashboard types ---

export type RiskAlertSeverity = "critical" | "high" | "medium" | "low";

export type RiskAlertAckStatus = "open" | "acknowledged" | "resolved";

export interface RiskAlertAck {
  status: RiskAlertAckStatus;
  assigned_to: number | null;
  assigned_to_name: string | null;
  note: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
  updated_by_name: string | null;
  updated_at: string | null;
}

export interface RiskAlertOverview {
  total_open_alerts: number;
  critical_alerts: number;
  high_alerts: number;
  medium_alerts: number;
  low_alerts: number;
  watch_alerts: number;
  resolved_last_7_days: number;
  modules_affected: number;
  acknowledged_alerts: number;
  resolved_alerts: number;
}

export interface RiskAlertModuleTotal {
  module: "projects" | "workflows" | "finance" | "procurement" | "facilities" | "crm";
  label: string;
  open_alerts: number;
  critical_alerts: number;
  high_alerts: number;
  medium_alerts: number;
  low_alerts: number;
}

export interface RiskAlertItem {
  id: string;
  module: "projects" | "workflows" | "finance" | "procurement" | "facilities" | "crm";
  module_label: string;
  alert_type: string;
  title: string;
  subject: string;
  severity: RiskAlertSeverity;
  status: string;
  owner: string;
  due_date: string | null;
  amount: string | null;
  risk_score: number | null;
  note: string;
  updated_at: string | null;
  acknowledgement: RiskAlertAck | null;
}

export interface RiskAlertModuleFeed {
  label: string;
  open_alerts: number;
  critical_alerts: number;
  high_alerts: number;
  medium_alerts: number;
  low_alerts: number;
  last_event_at: string | null;
  summary: Record<string, string | number | null>;
  items: RiskAlertItem[];
}

export interface RiskAlertsPayload {
  generated_at: string;
  overview: RiskAlertOverview;
  severity_distribution: Record<RiskAlertSeverity, number>;
  module_totals: RiskAlertModuleTotal[];
  feeds: {
    projects: RiskAlertModuleFeed;
    workflows: RiskAlertModuleFeed;
    finance: RiskAlertModuleFeed;
    procurement: RiskAlertModuleFeed;
    facilities: RiskAlertModuleFeed;
    crm: RiskAlertModuleFeed;
  };
  recent_alerts: RiskAlertItem[];
}

// --- Drilldown types ---

export interface HistogramBucket {
  bucket: string;
  count: number;
}

export interface ProcurementCycleDrilldown {
  histogram: HistogramBucket[];
  slowest_pos: {
    po_number: string;
    vendor: string;
    duration_days: number;
    issue_date: string;
    requisition_date: string;
  }[];
  summary: {
    median_days: number;
    p90_days: number;
    min_days: number;
    max_days: number;
  };
}

export interface CostVarianceProjectItem {
  id: number;
  name: string;
  planned: string;
  actual: string;
  variance_pct: number;
}

export interface CostVarianceDrilldown {
  per_project: CostVarianceProjectItem[];
  over_budget_projects: CostVarianceProjectItem[];
  summary: {
    worst_variance_pct: number;
    best_variance_pct: number;
    total_planned: string;
    total_actual: string;
  };
}

export interface VendorScoreItem {
  id: number;
  name: string;
  score: number;
  performance: number;
  timeliness: number;
  compliance: string;
  po_count: number;
}

export interface VendorReliabilityDrilldown {
  top_vendors: VendorScoreItem[];
  bottom_vendors: VendorScoreItem[];
  score_distribution: HistogramBucket[];
  summary: { median_score: number; vendor_count: number };
}

export interface EmergencyTrendItem {
  month: string;
  total: number;
  emergency: number;
  pct: number;
}

export interface EmergencyPurchasesDrilldown {
  trend: EmergencyTrendItem[];
  by_category: {
    category: string;
    total: number;
    emergency: number;
    pct: number;
  }[];
  recent_emergencies: {
    pr_number: string;
    title: string;
    requester: string;
    created_at: string;
    project: string | null;
  }[];
}

export interface BudgetOverrunBudgetItem {
  id: number;
  name: string;
  tracked_items: number;
  overrun_items: number;
  frequency_pct: number;
}

export interface BudgetOverrunDrilldown {
  per_budget: BudgetOverrunBudgetItem[];
  worst_line_items: {
    budget_name: string;
    account_code: string;
    account_name: string;
    budgeted: string;
    actual: string;
    overrun_pct: number;
  }[];
  summary: {
    total_budgeted: string;
    total_actual: string;
    net_overrun: string;
  };
}

export interface ApprovalTimeByType {
  template_name: string;
  avg_hours: number;
  count: number;
  median_hours: number;
}

export interface ApprovalTimeDrilldown {
  by_workflow_type: ApprovalTimeByType[];
  slowest_approvals: {
    id: number;
    template_name: string;
    submitted_at: string;
    completed_at: string;
    hours: number;
    state: string;
  }[];
  summary: {
    median_hours: number;
    p90_hours: number;
    fastest_hours: number;
    slowest_hours: number;
  };
}

// --- Custom Dashboard types ---

export type WidgetType =
  | "board_kpi_card"
  | "portfolio_kpi_summary"
  | "portfolio_type_distribution"
  | "portfolio_classification"
  | "portfolio_valuation_history"
  | "portfolio_unit_occupancy"
  | "portfolio_budget_summary"
  | "portfolio_construction_budget_burn"
  | "portfolio_property_inventory"
  | "portfolio_procurement_commitments"
  | "portfolio_rental_occupancy"
  | "portfolio_maintenance_backlog"
  | "portfolio_cash_flow_forecast"
  | "portfolio_top_appreciating"
  | "portfolio_top_depreciating"
  | "portfolio_encumbrance"
  // Portfolio scalar KPIs
  | "portfolio_total_acquisition"
  | "portfolio_total_area"
  | "portfolio_avg_price_per_sqft"
  // Operations
  | "hr_active_headcount"
  | "hr_open_vacancies"
  | "tenant_active_count"
  | "crm_active_leads"
  | "crm_closed_reservations"
  // Finance status
  | "finance_bills_by_status"
  | "finance_invoices_by_status"
  | "finance_recent_invoices"
  | "finance_recent_bills"
  // Cash flow (FinanceCashFlow source)
  | "cashflow_top_customers"
  | "cashflow_top_vendors"
  | "cashflow_monthly_trend"
  | "cashflow_annual_totals"
  | "cashflow_budget_remaining";

export interface WidgetPosition {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface WidgetConfig {
  widget_type: WidgetType;
  kpi_key?: string;
  position: WidgetPosition;
  config: Record<string, unknown>;
}

export interface CustomDashboard {
  id: number;
  name: string;
  is_default: boolean;
  layout: WidgetConfig[];
  created_at: string;
  updated_at: string;
}

// --- Procurement types ---

export type VendorCategory = "materials" | "contractor" | "consultant" | "other";
export type PriceCompetitiveness = "low" | "average" | "high" | "premium";
export type ComplianceStatus = "compliant" | "non_compliant" | "pending_review" | "expired";

export interface VendorListItem {
  id: number;
  name: string;
  contact_person: string;
  email: string;
  phone: string;
  category: VendorCategory;
  is_active: boolean;
  is_blacklisted: boolean;
  performance_rating: string;
  compliance_status: ComplianceStatus;
  created_at: string;
  updated_at: string;
  po_count: number;
  total_po_value: string | null;
}

export interface Vendor extends VendorListItem {
  address: string;
  tax_id: string;
  notes: string;
  bank_name: string;
  bank_account_number: string;
  bank_branch: string;
  approved_projects: number[];
  approved_projects_detail: { id: number; name: string }[];
  delivery_timeliness_score: string;
  price_competitiveness: PriceCompetitiveness;
  blacklist_reason: string;
}

export type PRStatus = "draft" | "submitted" | "approved" | "rejected" | "cancelled" | "ordered";
export type PRPriority = "low" | "medium" | "high" | "urgent";
export type POStatus = "draft" | "approved" | "issued" | "partially_received" | "received" | "cancelled";
export type GRNStatus = "pending" | "inspected" | "accepted" | "partially_accepted" | "rejected";

export interface PurchaseRequisitionItem {
  id: number;
  requisition: number;
  description: string;
  quantity: string;
  unit_of_measure: string;
  estimated_unit_price: string;
  estimated_amount: string;
  sort_order: number;
}

export interface PurchaseRequisitionListItem {
  id: number;
  pr_number: string;
  title: string;
  status: PRStatus;
  requester: string;
  project: number | null;
  project_name: string | null;
  property: number | null;
  property_name: string | null;
  priority: PRPriority;
  required_date: string;
  estimated_total: string;
  budget_line_item: number | null;
  budget_code: string;
  cost_code: string;
  item_count: number;
  created_at: string;
  updated_at: string;
}

export interface PurchaseRequisition extends PurchaseRequisitionListItem {
  justification: string;
  notes: string;
  approved_by: string;
  approved_date: string | null;
  rejected_reason: string;
  items: PurchaseRequisitionItem[];
}

export interface PurchaseOrderItem {
  id: number;
  purchase_order: number;
  description: string;
  quantity: string;
  unit_of_measure: string;
  unit_price: string;
  amount: string;
  sort_order: number;
  quantity_received: string;
  quantity_remaining: string;
}

export interface GoodsReceiptItem {
  id: number;
  goods_receipt: number;
  po_item: number;
  po_item_description: string;
  quantity_received: string;
  quantity_accepted: string;
  quantity_rejected: string;
  rejection_reason: string;
  notes: string;
}

export interface GoodsReceiptListItem {
  id: number;
  grn_number: string;
  purchase_order: number;
  po_number: string;
  vendor_name: string;
  status: GRNStatus;
  received_date: string;
  received_by: string;
  delivery_note_number: string;
  item_count: number;
  created_at: string;
}

export interface GoodsReceipt extends GoodsReceiptListItem {
  inspection_notes: string;
  notes: string;
  items: GoodsReceiptItem[];
}

export interface ThreeWayMatch {
  po_total: string;
  grn_accepted_total: string;
  invoice_total: string;
  qty_match: boolean;
  amount_match: boolean;
  status: "full_match" | "partial_match" | "mismatch" | "pending";
}

export interface PurchaseOrderListItem {
  id: number;
  po_number: string;
  vendor: number;
  vendor_name: string;
  project: number | null;
  project_name: string | null;
  property: number | null;
  property_name: string | null;
  requisition: number | null;
  requisition_number: string | null;
  status: POStatus;
  issue_date: string;
  expected_delivery_date: string | null;
  budget_line_item: number | null;
  budget_code: string;
  cost_code: string;
  total_amount: string;
  is_fully_received: boolean;
  item_count: number;
  created_at: string;
  updated_at: string;
}

export interface PurchaseOrder extends PurchaseOrderListItem {
  subtotal: string;
  tax_amount: string;
  delivery_address: string;
  payment_terms: string;
  notes: string;
  approved_by: string;
  approved_date: string | null;
  items: PurchaseOrderItem[];
  goods_receipts: GoodsReceiptListItem[];
  bills: BillListItem[];
  three_way_match: ThreeWayMatch;
}

export interface ProcurementOverview {
  budget_consumption: any;
  delayed_delivery_count: any;
  delayed_deliveries: any;
  vendor_alerts: never[];
  open_requisitions_count: number;
  open_requisitions_value: string;
  pending_approval_count: number;
  active_po_count: number;
  active_po_value: string;
  pending_delivery_count: number;
  recent_requisitions: PurchaseRequisitionListItem[];
  recent_purchase_orders: PurchaseOrderListItem[];
  prs_by_status: StatusCount[];
  pos_by_status: StatusCount[];
  rfq_open_count?: number;
  rfq_submitted_count?: number;
}

export type RFQStatus = "draft" | "issued" | "evaluation" | "submitted" | "approved" | "cancelled" | "closed";
export type RFQQuoteStatus = "pending" | "shortlisted" | "rejected" | "winner";

export interface RFQQuote {
  id: number;
  rfq: number;
  vendor: number;
  vendor_name: string;
  quote_number: string;
  quote_date: string;
  validity_date: string | null;
  quoted_amount: string;
  delivery_days: number | null;
  warranty_terms: string;
  payment_terms: string;
  compliance_score: string;
  technical_score: string;
  commercial_score: string;
  total_score: string;
  status: RFQQuoteStatus;
  notes: string;
  submitted_at: string;
  updated_at: string;
}

export interface RFQListItem {
  id: number;
  rfq_number: string;
  title: string;
  status: RFQStatus;
  requisition: number | null;
  requisition_number: string | null;
  project: number | null;
  project_name: string | null;
  property: number | null;
  property_name: string | null;
  issue_date: string;
  submission_deadline: string | null;
  estimated_value: string;
  budget_line_item: number | null;
  budget_code: string;
  cost_code: string;
  selected_vendor: number | null;
  selected_vendor_name: string | null;
  quote_count: number;
  lowest_quote: string | null;
  created_at: string;
  updated_at: string;
}

export interface RFQ extends RFQListItem {
  selection_notes: string;
  selection_date: string | null;
  notes: string;
  quotes: RFQQuote[];
}

// --- Inventory types ---

export type InventoryItemCategory =
  | "structural"
  | "finishing"
  | "mep"
  | "electrical"
  | "plumbing"
  | "safety"
  | "consumable"
  | "spare"
  | "equipment"
  | "other";

export type InventoryTransactionType =
  | "receipt"
  | "issue"
  | "adjustment_in"
  | "adjustment_out"
  | "transfer_in"
  | "transfer_out";

export interface InventoryWarehouse {
  id: number;
  code: string;
  name: string;
  location: string;
  project: number | null;
  project_name: string | null;
  is_active: boolean;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface InventoryItemListItem {
  id: number;
  sku: string;
  name: string;
  category: InventoryItemCategory;
  unit_of_measure: string;
  reorder_level: string;
  target_stock_level: string;
  default_unit_cost: string;
  preferred_vendor: number | null;
  preferred_vendor_name: string | null;
  expense_account: number | null;
  expense_account_code: string | null;
  expense_account_name: string | null;
  cost_center: number | null;
  cost_center_name: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface InventoryItem extends InventoryItemListItem {
  description: string;
}

// ---------------------------------------------------------------------------
// Material Master Database
// ---------------------------------------------------------------------------

export interface MaterialMasterListItem {
  id: number;
  sku: string;
  name: string;
  category: string;
  subcategory: string;
  unit_of_measure: string;
  default_unit_cost: string;
  preferred_vendor: number | null;
  preferred_vendor_name: string | null;
  lead_time_days: number | null;
  target_stock_level: string;
  reorder_level: string;
  storage_requirements: string;
  quality_specification: string;
  material_grade: string;
  alternative_materials: string;
  hs_code: string;
  compliance_requirements: string;
  expense_account: number | null;
  expense_account_code: string | null;
  expense_account_name: string | null;
  cost_center: number | null;
  cost_center_name: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface MaterialMasterItem extends MaterialMasterListItem {
  description: string;
}

export interface InventoryStockRecord {
  id: number;
  warehouse: number;
  warehouse_name: string;
  warehouse_code: string;
  item: number;
  item_sku: string;
  item_name: string;
  item_category: InventoryItemCategory;
  reorder_level: string;
  target_stock_level: string;
  quantity_on_hand: string;
  quantity_reserved: string;
  available_quantity: string;
  average_unit_cost: string;
  is_low_stock: boolean;
  last_transaction_at: string | null;
  updated_at: string;
}

export interface InventoryTransaction {
  id: number;
  transaction_type: InventoryTransactionType;
  transaction_type_display: string;
  warehouse: number;
  warehouse_name: string;
  warehouse_code: string;
  item: number;
  item_sku: string;
  item_name: string;
  item_uom: string;
  project: number | null;
  project_name: string | null;
  purchase_order: number | null;
  purchase_order_number: string | null;
  goods_receipt: number | null;
  goods_receipt_number: string | null;
  goods_receipt_item: number | null;
  quantity: string;
  unit_cost: string | null;
  total_cost: string;
  transaction_date: string;
  source_module: string;
  source_reference: string;
  notes: string;
  performed_by: number | null;
  performed_by_name: string;
  created_at: string;
}

export interface InventoryOverviewLowStockItem {
  stock_id: number;
  warehouse_id: number;
  warehouse_name: string;
  item_id: number;
  item_sku: string;
  item_name: string;
  quantity_on_hand: string;
  reorder_level: string;
  shortfall: string;
}

export interface InventoryOverviewRecentTransaction {
  id: number;
  transaction_type: InventoryTransactionType;
  transaction_type_display: string;
  transaction_date: string;
  item_sku: string;
  item_name: string;
  warehouse_name: string;
  project_name: string | null;
  quantity: string;
  total_cost: string;
  source_module: string;
  source_reference: string;
}

export interface InventoryOverviewProjectConsumption {
  project_id: number;
  project_name: string;
  total_cost: string;
  movement_count: number;
}

export interface InventoryOverview {
  as_of_date: string;
  active_items_count: number;
  warehouse_count: number;
  stock_records_count: number;
  low_stock_count: number;
  stock_value_total: string;
  receipts_30d_value: string;
  issues_30d_value: string;
  procurement_linked_receipts: number;
  project_linked_issues: number;
  budget_covered_issue_value: string;
  unbudgeted_issue_value: string;
  low_stock_items: InventoryOverviewLowStockItem[];
  recent_transactions: InventoryOverviewRecentTransaction[];
  project_consumption_30d: InventoryOverviewProjectConsumption[];
}

// ---------------------------------------------------------------------------
// Bill of Materials (BOM)
// ---------------------------------------------------------------------------

export interface BOMItemEntry {
  id?: number;
  inventory_item?: number | null;
  inventory_item_name?: string | null;
  material_name: string;
  category: string;
  quantity: number;
  unit_of_measure: string;
  unit_cost: number;
  line_total?: number;
  notes: string;
  sort_order: number;
}

export interface BOMListItem {
  id: number;
  bom_number: string;
  name: string;
  project: number | null;
  project_name: string | null;
  unit_type: string;
  quantity_of_units: number;
  status: string;
  total_estimated_cost: string;
  item_count: number;
  created_at: string;
  created_by: number | null;
  created_by_name: string | null;
}

export interface BOMDetail extends BOMListItem {
  description: string;
  items: (BOMItemEntry & { id: number; line_total: number })[];
}

// ---------------------------------------------------------------------------
// Settings — Organization Configuration
// ---------------------------------------------------------------------------

export interface CompanyProfile {
  id: number;
  name: string;
  legal_name: string;
  trading_name: string;
  industry: string;
  size: string;
  description: string;
  registration_number: string;
  tax_id: string;
  fiscal_year_start_month: number;
  email: string;
  phone: string;
  website: string;
  address_line_1: string;
  address_line_2: string;
  city: string;
  state_province: string;
  postal_code: string;
  country: string;
  logo: string | null;
  founded_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface SubsidiaryListItem {
  id: number;
  name: string;
  relationship_type: "subsidiary" | "branch" | "joint_venture" | "associate";
  status: "active" | "dormant" | "dissolved";
  city: string;
  country: string;
  created_at: string;
}

export interface Subsidiary extends SubsidiaryListItem {
  organization: number;
  legal_name: string;
  registration_number: string;
  tax_id: string;
  address: string;
  contact_email: string;
  contact_phone: string;
  notes: string;
  updated_at: string;
}

export interface DivisionListItem {
  id: number;
  name: string;
  code: string;
  head: number | null;
  head_name: string | null;
  unit_category: "profit_center" | "cost_center";
  unit_category_display: string;
  location_region: string;
  is_active: boolean;
  department_count: number;
  total_headcount: number;
  operating_budget: string;
  sort_order: number;
  created_at: string;
}

export interface Division {
  id: number;
  name: string;
  code: string;
  description: string;
  head: number | null;
  head_name: string | null;
  unit_category: "profit_center" | "cost_center";
  unit_category_display: string;
  location_region: string;
  is_active: boolean;
  sort_order: number;
  total_headcount: number;
  operating_budget: string;
  departments: Department[];
  created_at: string;
  updated_at: string;
}

export interface Department {
  id: number;
  name: string;
  code: string;
  description: string;
  head: number | null;
  head_name: string | null;
  parent_business_unit_id?: number;
  parent_business_unit_name?: string | null;
  parent_business_unit_code?: string;
  cost_center_id?: string | null;
  employee_directory?: DepartmentEmployeeDirectoryEntry[];
  headcount_summary?: DepartmentHeadcountSummary;
  skills_matrix?: DepartmentSkillSummary[];
  project_allocation?: DepartmentProjectAllocationEntry[];
  utilization_rate?: DepartmentUtilizationRate;
  sop_library?: DepartmentSopLibrary;
  is_active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface DepartmentEmployeeDirectoryEntry {
  user_id: number;
  employee_id: string;
  full_name: string;
  job_title: string;
  email: string;
}

export interface DepartmentHeadcountSummary {
  active_employees: number;
  approved_roles: number;
  filled_vs_approved: string;
  vacant_roles: number;
}

export interface DepartmentSkillSummary {
  skill_name: string;
  employee_count: number;
  summary: string;
}

export interface DepartmentProjectAllocationEntry {
  project_id: number;
  project_name: string;
  project_status: string;
  task_count: number;
  open_task_count: number;
  logged_hours: number;
}

export interface DepartmentUtilizationRate {
  percent: number;
  hours_logged: number;
  available_hours: number;
  staff_count: number;
  period_label: string;
  formula: string;
}

export interface DepartmentSopLibraryDocument {
  id: number;
  title: string;
  document_number: string;
  status: string;
  document_type_name: string;
  project_id: number | null;
  project_name: string | null;
  is_sop: boolean;
  created_at: string | null;
}

export interface DepartmentSopLibrary {
  document_count: number;
  sop_count: number;
  documents: DepartmentSopLibraryDocument[];
}

export interface CostCenter {
  id: number;
  code: string;
  name: string;
  department: number | null;
  department_name: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProfitCenter {
  id: number;
  code: string;
  name: string;
  department: number | null;
  department_name: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface DocumentAutomationSettings {
  id: number;
  default_signature_provider: DocumentSignatureProvider;
  enabled_signature_providers: DocumentSignatureProvider[];
  default_generation_owner_role: number | null;
  default_generation_owner_role_name: string | null;
  default_generation_phase: number | null;
  default_generation_phase_name: string | null;
  default_generation_retention_policy: number | null;
  default_generation_retention_policy_name: string | null;
  default_generation_confidentiality_level: DocumentConfidentiality;
  default_generation_template_code: string;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// Security Settings
// ---------------------------------------------------------------------------

export interface SecuritySettings {
  id: number;
  // Authentication
  mfa_enforced: boolean;
  password_min_length: number;
  password_require_uppercase: boolean;
  password_require_lowercase: boolean;
  password_require_digits: boolean;
  password_require_special: boolean;
  session_timeout_minutes: number;
  // Encryption (read-only)
  encryption_at_rest: boolean;
  encryption_in_transit: boolean;
  // IP Restrictions
  ip_restriction_enabled: boolean;
  whitelisted_cidrs: string[];
  geo_blocking_enabled: boolean;
  blocked_countries: string[];
  // Metadata
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// System Preferences
// ---------------------------------------------------------------------------

export interface SystemPreferencesRole {
  slug: string;
  name: string;
}

export interface LandingPageOption {
  value: string;
  label: string;
}

export interface CurrencyOption {
  code: string;
  label: string;
}

export interface SystemPreferences {
  id: number;
  // Dashboard
  dashboard_by_role: Record<string, string>;
  available_roles: SystemPreferencesRole[];
  available_landing_pages: LandingPageOption[];
  available_currencies: CurrencyOption[];
  // Theme
  theme_mode: "light" | "dark" | "auto";
  accent_color: string;
  // Localization
  date_format: "DD/MM/YYYY" | "MM/DD/YYYY" | "YYYY-MM-DD";
  number_format: "1,234.56" | "1.234,56";
  measurement_unit: "sqm" | "sqft";
  // Currency
  default_currency: string;
  currency_position: "prefix" | "suffix";
  currency_decimal_places: number;
  // Metadata
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// Audit & Compliance Settings
// ---------------------------------------------------------------------------

export interface AuditStatus {
  models_tracked: number;
  middleware_active: boolean;
  total_log_entries: number;
}

export interface AuditComplianceSettings {
  id: number;
  // Audit Logging
  audit_logging_enabled: boolean;
  audit_retention_days: number;
  audit_status: AuditStatus;
  // Compliance Controls
  mandatory_fields_enforced: boolean;
  financial_period_locking: boolean;
  locked_before_date: string | null;
  change_approval_required: boolean;
  // Data Access
  access_log_retention_days: number;
  // Metadata
  created_at: string;
  updated_at: string;
}

export interface AuditLogEntry {
  id: number;
  timestamp: string;
  actor_email: string;
  actor_role: string;
  action_display: string;
  object_repr: string;
  content_type_name: string;
  ip_address: string | null;
  changes: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Backup & Disaster Recovery Settings
// ---------------------------------------------------------------------------

export interface RestoreTestLogEntry {
  date: string;
  status: "pass" | "fail" | "partial";
  duration_seconds: number;
  notes: string;
}

export interface BackupDisasterRecoverySettings {
  id: number;
  backup_frequency: "hourly" | "every_6h" | "every_12h" | "daily" | "weekly";
  backup_frequency_display: string;
  backup_region: string;
  backup_region_display: string;
  rto_minutes: number;
  rto_display: string;
  rpo_minutes: number;
  rpo_display: string;
  failover_on_db_failure: boolean;
  failover_on_network_outage: boolean;
  failover_on_storage_failure: boolean;
  failover_on_app_crash: boolean;
  failover_on_manual_trigger: boolean;
  restore_test_logs: RestoreTestLogEntry[];
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// Integration Governance Settings
// ---------------------------------------------------------------------------

export interface VersionCompatibilityEntry {
  integration_name: string;
  current_version: string;
  min_compatible_version: string;
  status: "compatible" | "deprecated" | "incompatible" | "unknown";
  last_checked: string;
}

export interface IntegrationGovernanceSettings {
  id: number;
  // Data Sync
  default_sync_frequency: "real_time" | "every_5m" | "every_15m" | "every_30m" | "hourly" | "every_6h" | "daily";
  default_sync_frequency_display: string;
  sync_retry_attempts: number;
  sync_retry_delay_seconds: number;
  sync_enabled: boolean;
  // Conflict Resolution
  conflict_resolution_strategy: "source_wins" | "target_wins" | "most_recent" | "manual_review";
  conflict_resolution_strategy_display: string;
  conflict_auto_resolve: boolean;
  conflict_notify_on_resolution: boolean;
  conflict_escalation_after_hours: number;
  // Source of Truth
  primary_source_of_truth: "erp" | "crm" | "property_management" | "finance_system" | "project_management" | "custom";
  primary_source_of_truth_display: string;
  source_override_allowed: boolean;
  // Error Log Routing
  error_routing_email: boolean;
  error_routing_webhook: boolean;
  error_routing_in_app: boolean;
  error_routing_syslog: boolean;
  error_webhook_url: string;
  error_email_recipients: string[];
  error_severity_threshold: "info" | "warning" | "error" | "critical";
  error_severity_threshold_display: string;
  // Integration SLA
  sla_target_uptime_pct: string;
  sla_max_response_time_ms: number;
  sla_max_response_time_display: string;
  sla_max_sync_latency_seconds: number;
  sla_max_sync_latency_display: string;
  sla_alert_on_breach: boolean;
  // Version Compatibility
  version_compatibility_log: VersionCompatibilityEntry[];
  // Metadata
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// KPI & Performance Configuration
// ---------------------------------------------------------------------------

export type KpiCategory = "construction" | "sales" | "finance" | "operations" | "compliance" | "hr" | "procurement" | "project_management" | "property" | "safety" | "quality";
export type KpiUnit = "percentage" | "currency" | "count" | "ratio" | "days" | "score";
export type KpiDirection = "higher_is_better" | "lower_is_better";
export type KpiFrequency = "daily" | "weekly" | "monthly" | "quarterly" | "annual";

export interface KpiDefinitionListItem {
  id: number;
  name: string;
  code: string;
  category: KpiCategory;
  category_display: string;
  unit: KpiUnit;
  unit_display: string;
  direction: KpiDirection;
  direction_display: string;
  frequency: KpiFrequency;
  frequency_display: string;
  green_threshold: string;
  amber_threshold: string;
  bonus_green_pct: string | null;
  bonus_amber_pct: string | null;
  bonus_red_pct: string | null;
  is_active: boolean;
  is_system: boolean;
  sort_order: number;
  assignment_count: number;
  created_at: string;
  updated_at: string;
}

export interface KpiDefinition extends KpiDefinitionListItem {
  description: string;
  formula_expression: string;
  data_source: string;
}

export interface KpiAssignment {
  id: number;
  kpi: number;
  kpi_name: string;
  kpi_code: string;
  kpi_category: KpiCategory;
  kpi_category_display: string;
  kpi_unit: KpiUnit;
  kpi_unit_display: string;
  role: number | null;
  role_name: string | null;
  department: number | null;
  department_name: string | null;
  target_value: string;
  weight: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// Notification & SLA Settings
// ---------------------------------------------------------------------------

export type SlaSeverityLevel = "info" | "review" | "action_required" | "escalation";
export type NotificationTemplateChannel = "email" | "in_app" | "sms" | "push";

export interface NotificationChannelSettings {
  id: number;
  email_enabled: boolean;
  in_app_enabled: boolean;
  sms_enabled: boolean;
  push_enabled: boolean;
  category_overrides: Record<string, { enabled: boolean; channels: string[] }>;
  muted_event_keys: string[];
  created_at: string;
  updated_at: string;
}

export interface SlaSeverityTier {
  id: number;
  level: SlaSeverityLevel;
  level_display: string;
  sort_order: number;
  response_time_hours: number;
  escalation_path: string[];
  notification_channels: NotificationTemplateChannel[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface NotificationTemplateListItem {
  id: number;
  code: string;
  name: string;
  description: string;
  channel: NotificationTemplateChannel;
  channel_display: string;
  event_key: string;
  severity_tier: SlaSeverityLevel;
  severity_tier_display: string;
  subject: string;
  is_active: boolean;
  is_system: boolean;
  updated_at: string;
  created_at: string;
}

export interface NotificationTemplateDetail extends NotificationTemplateListItem {
  body_text: string;
  body_html: string;
  variables: string[];
}

export interface NotificationWorkflowCatalogItem {
  key: string;
  label: string;
  module: string;
  description: string;
  default_channels: NotificationTemplateChannel[];
  variables: string[];
  default_severity_tier: SlaSeverityLevel;
  template_count: number;
  active_template_count: number;
  configured_channels: NotificationTemplateChannel[];
  active_channels: NotificationTemplateChannel[];
}

export interface NotificationWorkflowCatalogResponse {
  events: NotificationWorkflowCatalogItem[];
}

// ---------------------------------------------------------------------------
// RBAC — Roles & Permissions
// ---------------------------------------------------------------------------

export type RbacAction =
  | "view"
  | "comment"
  | "create"
  | "edit"
  | "upload_version"
  | "approve"
  | "archive"
  | "admin_override"
  | "delete"
  | "export"
  | "assign"
  | "configure";

export interface RoleListItem {
  id: number;
  name: string;
  slug: string;
  description: string;
  is_system: boolean;
  user_count: number;
  created_at: string;
}

export interface RolePermissionItem {
  id: number;
  module: string;
  sub_module: string;
  action: RbacAction;
}

export interface RoleDetail extends RoleListItem {
  permissions: RolePermissionItem[];
  updated_at: string;
}

export interface PermissionRegistrySubModule {
  key: string;
  label: string;
  actions: RbacAction[];
}

export interface PermissionRegistryModule {
  module: string;
  label: string;
  sub_modules: PermissionRegistrySubModule[];
}

// ---------------------------------------------------------------------------
// Workflow & Approval Engine
// ---------------------------------------------------------------------------

export type WorkflowStepMode = "sequential" | "parallel";
export type WorkflowStepType = "approval" | "notification" | "condition";
export type WorkflowState = "draft" | "pending" | "in_progress" | "approved" | "rejected" | "cancelled" | "escalated";
export type StepDecision = "pending" | "approved" | "rejected" | "skipped" | "escalated";
export type ApprovalPolicyType = "financial_threshold" | "procurement_threshold" | "contract_review" | "change_order";
export type DelegationStatus = "active" | "expired" | "revoked";

export interface WorkflowTemplateStep {
  id: number;
  template: number;
  sequence: number;
  name: string;
  step_type: WorkflowStepType;
  execution_mode: WorkflowStepMode;
  approver_role_slug: string;
  approver_user: number | null;
  sla_hours: number | null;
  escalation_role_slug: string;
  condition_field: string;
  condition_operator: string;
  condition_value: string;
  condition_true_step: number | null;
  condition_false_step: number | null;
  is_active: boolean;
  created_at: string;
}

export interface WorkflowTemplateListItem {
  id: number;
  code: string;
  name: string;
  description: string;
  default_step_mode: WorkflowStepMode;
  is_default: boolean;
  is_active: boolean;
  step_count: number;
  applicable_models: string[];
  created_at: string;
  updated_at: string;
}

export interface WorkflowTemplateDetail extends WorkflowTemplateListItem {
  steps: WorkflowTemplateStep[];
  applicable_content_types: number[];
}

export interface ApprovalPolicyListItem {
  id: number;
  name: string;
  policy_type: ApprovalPolicyType;
  content_type: number;
  content_type_label: string;
  amount_field: string;
  min_amount: string | null;
  max_amount: string | null;
  template: number;
  template_name: string;
  priority: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface UserDelegationListItem {
  id: number;
  delegator: number;
  delegator_name: string;
  delegate: number;
  delegate_name: string;
  role_scope: number | null;
  role_scope_name: string | null;
  content_type_scope: number | null;
  starts_at: string;
  ends_at: string;
  reason: string;
  status: DelegationStatus;
  created_at: string;
  revoked_at: string | null;
  revoked_by: number | null;
}

export interface WorkflowStepRecord {
  id: number;
  sequence: number;
  name: string;
  execution_mode: WorkflowStepMode;
  approver_role_slug: string;
  approver_user: number | null;
  decision: StepDecision;
  decided_by: number | null;
  decided_by_name: string | null;
  acting_on_behalf_of: number | null;
  on_behalf_of_name: string | null;
  comments: string;
  decided_at: string | null;
  sla_deadline: string | null;
  sla_breached: boolean;
  escalated_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowInstanceListItem {
  id: number;
  content_type: number;
  content_type_label: string;
  object_id: number;
  template: number;
  template_name: string;
  state: WorkflowState;
  submitted_by: number | null;
  submitted_by_name: string | null;
  submitted_at: string | null;
  completed_at: string | null;
  pending_step: { sequence: number; name: string } | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowInstanceDetail extends WorkflowInstanceListItem {
  matched_policy: number | null;
  steps: WorkflowStepRecord[];
}

export interface WorkflowAuditEvent {
  id: number;
  workflow_instance: number | null;
  event_type: string;
  actor: number | null;
  actor_name: string | null;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface ContentTypeOption {
  id: number;
  app_label: string;
  model: string;
  label: string;
}

export interface MyApprovalItem {
  step_id: number;
  step_name: string;
  step_sequence: number;
  workflow_instance_id: number;
  template_name: string;
  content_type: string;
  object_id: number;
  state: WorkflowState;
  sla_deadline: string | null;
  sla_breached: boolean;
  submitted_at: string | null;
}

// =======================
// Equity Waterfall Types
// =======================

export type InvestorType = "individual" | "institutional" | "family_office" | "fund" | "corporate";

export interface InvestorListItem {
  id: number;
  name: string;
  investor_type: InvestorType;
  contact_person: string;
  email: string;
  phone: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  investment_count: number;
  total_invested: string;
}

export interface Investor {
  id: number;
  name: string;
  investor_type: InvestorType;
  contact_person: string;
  email: string;
  phone: string;
  address: string;
  tax_id: string;
  entity_name: string;
  registration_number: string;
  notes: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  investment_count: number;
  total_invested?: string;
}

export interface ProjectInvestor {
  id: number;
  project?: number;
  project_name?: string;
  investor: number;
  investor_name: string;
  ownership_percentage: string;
  capital_committed: string;
  capital_contributed: string;
  total_capital_returned: string;
  total_profit_distributed: string;
  unreturned_capital: string;
  custom_profit_split_pct: string | null;
  sort_order: number;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface DistributionLineItem {
  id: number;
  project_investor: number;
  investor_name: string;
  ownership_pct: string;
  tier1_capital_amount: string;
  tier2_profit_amount: string;
  total_amount: string;
  capital_returned_to_date: string;
  profit_distributed_to_date: string;
}

export type DistributionStatus = "draft" | "calculated" | "approved" | "distributed" | "cancelled";

export interface WaterfallDistributionListItem {
  id: number;
  distribution_number: string;
  project: number;
  project_name: string;
  status: DistributionStatus;
  distribution_date: string;
  total_amount: string;
  tier1_capital_returned: string;
  tier2_profit_split: string;
  sponsor_amount: string;
  investor_count: number;
  created_at: string;
  updated_at: string;
}

export interface WaterfallDistribution {
  id: number;
  distribution_number: string;
  project: number;
  project_name: string;
  status: DistributionStatus;
  distribution_date: string;
  total_amount: string;
  tier1_capital_returned: string;
  tier2_profit_split: string;
  sponsor_amount: string;
  notes: string;
  line_items: DistributionLineItem[];
  created_by: number | null;
  created_by_name: string | null;
  approved_by: number | null;
  approved_by_name: string | null;
  approved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface InvestorReturns {
  investor_name: string;
  capital_contributed: string;
  capital_returned: string;
  unreturned_capital: string;
  profit_distributed: string;
  total_distributed: string;
  equity_multiple: string | null;
  cash_flows: Array<{
    date: string;
    amount: string;
  }>;
}

// ---------------------------------------------------------------------------
// SPV Entity
// ---------------------------------------------------------------------------

export type SPVEntityType = "company" | "llp" | "trust" | "fund" | "llc" | "other";
export type SPVStatus = "active" | "dormant" | "dissolved" | "under_formation";

export interface SPVEntity {
  id: number;
  name: string;
  entity_type: SPVEntityType;
  status: SPVStatus;
  registration_number: string;
  registration_date: string | null;
  registered_address: string;
  tax_id: string;
  jurisdiction: string;
  authorized_capital: string | null;
  paid_up_capital: string | null;
  purpose: string;
  parent_entity: number | null;
  parent_entity_name: string | null;
  notes: string;
  is_active: boolean;
  subsidiary_count: number;
  project_count: number;
  organization: number;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// Payment Plan & Installments
// ---------------------------------------------------------------------------

export type PaymentPlanStatus = "draft" | "active" | "paused" | "completed" | "cancelled";
export type PaymentPlanType = "fixed_installment" | "milestone_based" | "percentage_based" | "custom";
export type PaymentPlanDirection = "receivable" | "payable";
export type PaymentPlanFrequency = "weekly" | "biweekly" | "monthly" | "quarterly" | "semi_annual" | "annual" | "one_time";
export type InstallmentStatus = "scheduled" | "due" | "paid" | "partially_paid" | "overdue" | "waived" | "cancelled";

export interface PaymentInstallment {
  id: number;
  installment_number: number;
  label: string;
  amount: string;
  paid_amount: string;
  balance_due: string;
  scheduled_date: string;
  due_date: string;
  paid_date: string | null;
  milestone: number | null;
  milestone_name: string | null;
  percentage_of_total: string | null;
  status: InstallmentStatus;
  payment_method: string;
  reference_number: string;
  notes: string;
  is_overdue: boolean;
  created_at: string;
  updated_at: string;
}

export interface PaymentPlanListItem {
  id: number;
  plan_number: string;
  title: string;
  status: PaymentPlanStatus;
  plan_type: PaymentPlanType;
  direction: PaymentPlanDirection;
  frequency: PaymentPlanFrequency;
  total_amount: string;
  currency: string;
  paid_amount: string;
  balance_due: string;
  installment_count: number;
  start_date: string;
  end_date: string | null;
  number_of_installments: number;
  customer: number | null;
  customer_name: string | null;
  vendor: number | null;
  vendor_name: string | null;
  investor: number | null;
  investor_name: string | null;
  project: number | null;
  project_name: string | null;
  spv_entity: number | null;
  spv_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaymentPlan extends PaymentPlanListItem {
  description: string;
  unit: number | null;
  notes: string;
  created_by: number | null;
  created_by_name: string | null;
  approved_by: number | null;
  approved_by_name: string | null;
  approved_at: string | null;
  installments: PaymentInstallment[];
}

// ---------------------------------------------------------------------------
// Project Governance Settings
// ---------------------------------------------------------------------------

export interface ProjectGovernanceSettings {
  id: number;
  stage_gate_enforcement_enabled: boolean;
  require_template_selection: boolean;
  risk_assessment_mandatory: boolean;
  created_at: string;
  updated_at: string;
}

export type TemplateType = "residential" | "mixed_use" | "commercial" | "infrastructure";
export type DocumentCategory = "permit" | "contract" | "plan" | "report" | "certificate" | "other";
export type StageGateStage = "feasibility" | "design" | "pre_sales" | "construction_start" | "handover";
export type RiskCategoryType = "financial" | "regulatory" | "construction" | "market" | "operational" | "environmental" | "legal" | "technical";
export type RiskSeverity = "low" | "medium" | "high" | "critical";

export interface TemplateMilestone {
  id: number;
  name: string;
  description: string;
  sort_order: number;
  days_from_phase_start: number | null;
}

export interface TemplateRequiredDocument {
  id: number;
  name: string;
  category: DocumentCategory;
  category_display: string;
  description: string;
  is_mandatory: boolean;
}

export interface TemplateComplianceCheckpoint {
  id: number;
  name: string;
  description: string;
  regulatory_reference: string;
  is_mandatory: boolean;
}

export interface TemplatePhase {
  id: number;
  name: string;
  description: string;
  sort_order: number;
  duration_days: number | null;
  weight: number;
  milestones: TemplateMilestone[];
  required_documents: TemplateRequiredDocument[];
  compliance_checkpoints: TemplateComplianceCheckpoint[];
}

export interface ProjectTemplateListItem {
  id: number;
  name: string;
  template_type: TemplateType;
  template_type_display: string;
  description: string;
  is_active: boolean;
  is_system: boolean;
  phase_count: number;
  created_at: string;
}

export interface ProjectTemplate {
  id: number;
  name: string;
  template_type: TemplateType;
  template_type_display: string;
  description: string;
  is_active: boolean;
  is_system: boolean;
  phases: TemplatePhase[];
  created_at: string;
  updated_at: string;
}

export interface StageGateChecklistItem {
  id: number;
  item: string;
  is_mandatory: boolean;
  sort_order: number;
}

export interface StageGateRuleListItem {
  id: number;
  name: string;
  stage: StageGateStage;
  stage_display: string;
  template: number | null;
  template_name: string | null;
  is_active: boolean;
  checklist_count: number;
  created_at: string;
}

export interface StageGateRule {
  id: number;
  name: string;
  stage: StageGateStage;
  stage_display: string;
  template: number | null;
  template_name: string | null;
  description: string;
  is_active: boolean;
  checklist_items: StageGateChecklistItem[];
  created_at: string;
  updated_at: string;
}

export interface RiskCategory {
  id: number;
  name: string;
  category_type: RiskCategoryType;
  category_type_display: string;
  description: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RiskScoreMatrix {
  id: number;
  matrix_config: {
    likelihood: Record<string, number>;
    impact: Record<string, number>;
    thresholds: Record<string, number>;
  };
  created_at: string;
  updated_at: string;
}

export interface RiskMitigationRule {
  id: number;
  risk_category: number;
  risk_category_name: string;
  risk_category_type_display: string;
  severity: RiskSeverity;
  severity_display: string;
  assign_to_role: number | null;
  assign_to_role_name: string | null;
  escalation_required: boolean;
  response_time_hours: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type ProjectRiskStatus = "open" | "in_progress" | "mitigated" | "accepted" | "closed";
export type ProjectRiskTreatment = "mitigate" | "avoid" | "transfer" | "accept";

export interface ProjectRiskRegisterEntry {
  id: number;
  project: number;
  project_name: string;
  title: string;
  description: string;
  risk_category: number | null;
  risk_category_name: string | null;
  risk_category_type_display: string | null;
  likelihood_key: string;
  likelihood_score: number;
  impact_key: string;
  impact_score: number;
  risk_score: number;
  severity: RiskSeverity;
  severity_display: string;
  status: ProjectRiskStatus;
  status_display: string;
  treatment: ProjectRiskTreatment;
  treatment_display: string;
  mitigation_plan: string;
  mitigation_actions: string;
  contingency_plan: string;
  owner_role: number | null;
  owner_role_name: string | null;
  response_time_hours: number | null;
  escalation_required: boolean;
  identified_on: string;
  target_resolution_date: string | null;
  last_reviewed_on: string | null;
  resolved_on: string | null;
  created_by: number | null;
  created_by_name: string | null;
  updated_by: number | null;
  updated_by_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectRiskRegisterSummary {
  total_risks: number;
  high_and_critical_risks: number;
  open_risks: number;
  mitigated_risks: number;
  overdue_mitigation_risks: number;
  by_severity: Record<RiskSeverity, number>;
  by_status: Record<ProjectRiskStatus, number>;
}

// ---------------------------------------------------------------------------
// Master Data Management (MDM)
// ---------------------------------------------------------------------------

export type MasterDataCategory =
  | "vendor_type"
  | "client_type"
  | "consultant_specialization"
  | "contractor_classification"
  | "investor_type"
  | "property_type"
  | "property_classification"
  | "unit_typology"
  | "asset_category"
  | "ownership_structure"
  | "maintenance_category"
  | "inspection_type"
  | "cost_code"
  | "material_category"
  | "payment_method"
  | "currency"
  | "risk_category"
  | "issue_category"
  | "compliance_category"
  | "project_type"
  | "land_status"
  | "document_type"
  | "status_badge";

export interface MasterDataEntry {
  id: number;
  category: MasterDataCategory;
  code: string;
  label: string;
  description: string;
  metadata: Record<string, unknown>;
  sort_order: number;
  is_active: boolean;
  is_system: boolean;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// Feature Flags & Module Activation
// ---------------------------------------------------------------------------

export type SubscriptionTier = "starter" | "professional" | "enterprise";

export type ModuleKey =
  | "properties"
  | "projects"
  | "finance"
  | "procurement"
  | "documents"
  | "analytics"
  | "crm"
  | "tenants"
  | "contracts"
  | "compliance";

export interface ModuleOption {
  key: ModuleKey;
  label: string;
  available: boolean;
}

export type FlagScope = "global" | "org" | "project" | "region";
export type FlagType = "boolean" | "percentage";

export interface FeatureFlagDefinition {
  id: number;
  key: string;
  name: string;
  description: string;
  module: string;
  module_display: string;
  flag_type: FlagType;
  flag_type_display: string;
  scope: FlagScope;
  scope_display: string;
  default_enabled: boolean;
  rollout_percentage: number;
  minimum_tier: SubscriptionTier;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface FeatureFlagOverride {
  id: number;
  flag: number;
  flag_key: string;
  flag_name: string;
  flag_scope: FlagScope;
  flag_module: string;
  flag_description: string;
  enabled: boolean;
  scoped_project_ids: number[];
  scoped_regions: string[];
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface FeatureFlagDashboard {
  tier: SubscriptionTier;
  tier_display: string;
  enabled_modules: string[];
  available_modules: ModuleOption[];
  flags: Record<string, boolean>;
  flag_definitions: FeatureFlagDefinition[];
  overrides: FeatureFlagOverride[];
}


// ---------------------------------------------------------------------------
// Reporting Engine Settings
// ---------------------------------------------------------------------------

export type PageSize = "a4" | "letter" | "legal" | "a3";
export type PageOrientation = "portrait" | "landscape";
export type WatermarkPosition = "center" | "diagonal" | "top" | "bottom";
export type DispatchFormat = "pdf" | "xlsx" | "csv";
export type BoardPackFrequency = "monthly" | "quarterly" | "semi_annual" | "annual";

export interface ReportingEngineSettings {
  id: number;
  // PDF Formatting
  page_size: PageSize;
  page_size_display: string;
  orientation: PageOrientation;
  orientation_display: string;
  margin_top_mm: number;
  margin_bottom_mm: number;
  margin_left_mm: number;
  margin_right_mm: number;
  header_enabled: boolean;
  header_text: string;
  footer_enabled: boolean;
  footer_text: string;
  font_family: string;
  font_size_pt: number;
  include_cover_page: boolean;
  include_table_of_contents: boolean;
  // Watermark
  watermark_enabled: boolean;
  watermark_text: string;
  watermark_opacity: number;
  watermark_position: WatermarkPosition;
  watermark_position_display: string;
  watermark_color: string;
  // Board Pack
  board_pack_enabled: boolean;
  board_pack_frequency: BoardPackFrequency;
  board_pack_frequency_display: string;
  board_pack_recipients: string[];
  board_pack_sections: string[];
  // Dispatch Defaults
  default_dispatch_format: DispatchFormat;
  default_dispatch_format_display: string;
  dispatch_retention_days: number;
  dispatch_reply_to_email: string;
  created_at: string;
  updated_at: string;
}

export type ConfidentialityAccessLevel = "public" | "internal" | "confidential" | "strictly_confidential";

export interface ConfidentialityLabel {
  id: number;
  name: string;
  code: string;
  description: string;
  access_level: ConfidentialityAccessLevel;
  access_level_display: string;
  color: string;
  watermark_override: boolean;
  restrict_printing: boolean;
  restrict_download: boolean;
  is_active: boolean;
  is_system: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export type ReportTemplateType = "financial" | "operational" | "compliance" | "executive" | "project" | "property" | "custom";
export type ReportOutputFormat = "pdf" | "xlsx" | "csv" | "pdf_xlsx";

export interface DataSourceEntry {
  module: string;
  entity: string;
  fields: string[];
  filters: Record<string, unknown>;
}

export interface CrossModuleJoinEntry {
  left_source: string;
  right_source: string;
  join_key: string;
  join_type: "inner" | "left" | "right" | "full";
}

export interface ReportTemplateListItem {
  id: number;
  name: string;
  code: string;
  description: string;
  module_source: string;
  module_source_display: string;
  template_type: ReportTemplateType;
  template_type_display: string;
  output_format: ReportOutputFormat;
  output_format_display: string;
  owner: number | null;
  owner_name: string | null;
  visibility: "private" | "department" | "shared";
  shared_department: number | null;
  confidentiality_label: number | null;
  confidentiality_label_name: string | null;
  confidentiality_restrict_download: boolean;
  confidentiality_restrict_printing: boolean;
  allow_simple_builder: boolean;
  is_active: boolean;
  is_system: boolean;
  schedule_count: number;
  created_at: string;
  updated_at: string;
}

export interface ReportTemplate extends ReportTemplateListItem {
  data_sources: DataSourceEntry[];
  cross_module_joins: CrossModuleJoinEntry[];
}

export interface ReportLibraryCategory {
  key: "my_reports" | "department_reports" | "shared_reports" | "scheduled_reports" | "recently_viewed";
  label: string;
  count: number;
}

export interface ReportLibraryItem {
  id: number;
  code: string;
  name: string;
  description: string;
  module_source: string;
  module_source_display: string;
  owner_name: string | null;
  confidentiality_label: string | null;
  visibility: "private" | "department" | "shared";
  category: string;
  last_run_at: string | null;
}

export interface ReportLibraryResponse {
  categories: ReportLibraryCategory[];
  results: ReportLibraryItem[];
}

export type ScheduledReportStatus = "delivered" | "failed" | "pending";

export interface MyScheduledReportItem {
  id: number;
  name: string;
  report_template: number;
  report_template_name: string;
  schedule_text: string;
  status: ScheduledReportStatus;
  status_display: string;
  last_dispatched_at: string | null;
  latest_run_at: string | null;
}

export interface MyScheduledReportResponse {
  results: MyScheduledReportItem[];
}

export interface ReportRunRecord {
  id: number;
  report_template: number;
  report_template_name: string;
  report_template_code: string;
  requested_by: number | null;
  requested_by_name: string | null;
  scheduled_dispatch: number | null;
  subscription: number | null;
  trigger: "manual" | "scheduled" | "subscription";
  trigger_display: string;
  status: "queued" | "running" | "succeeded" | "failed";
  status_display: string;
  output_format: ReportOutputFormat;
  output_format_display: string;
  filters: Record<string, unknown>;
  result_summary: Record<string, unknown>;
  row_count: number;
  file_path: string;
  error_message: string;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface ReportSavedView {
  id: number;
  name: string;
  report_template: number;
  report_template_name: string;
  user: number;
  user_name: string | null;
  filters: Record<string, unknown>;
  column_visibility: Record<string, unknown>;
  rows_per_page: number;
  is_default: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type ReportSubscriptionFrequency = "daily" | "weekly" | "monthly" | "quarterly";
export type ReportSubscriptionDeliveryChannel = "email" | "in_app" | "dashboard_widget";

export interface ReportSubscription {
  id: number;
  report_template: number;
  report_template_name: string;
  report_template_code: string;
  user: number;
  user_name: string | null;
  frequency: ReportSubscriptionFrequency;
  frequency_display: string;
  output_format: ReportOutputFormat;
  output_format_display: string;
  recipients: string[];
  delivery_channels: ReportSubscriptionDeliveryChannel[];
  delivery_channels_display: string[];
  is_active: boolean;
  last_sent_at: string | null;
  created_at: string;
  updated_at: string;
}

export type ScheduleFrequency = "daily" | "weekly" | "monthly" | "quarterly" | "annual";

export interface ScheduledReportDispatch {
  id: number;
  name: string;
  report_template: number;
  report_template_name: string;
  report_template_code: string;
  frequency: ScheduleFrequency;
  frequency_display: string;
  dispatch_time: string;
  dispatch_day_of_week: number | null;
  dispatch_day_of_week_display: string | null;
  dispatch_day_of_month: number | null;
  output_format: ReportOutputFormat;
  output_format_display: string;
  recipients: string[];
  is_active: boolean;
  last_dispatched_at: string | null;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// Escalation Matrix Settings
// ---------------------------------------------------------------------------

export type CrisisActivationSeverity = "high" | "critical";
export type BoardSeverityThreshold = "critical_only" | "high_and_above";
export type EscalationTierSeverity = "info" | "low" | "medium" | "high" | "critical";
export type EscalationRuleType = "time_based" | "parallel";
export type EscalationConditionType = "no_response" | "no_resolution" | "threshold_breach" | "severity_match";
export type BoardTriggerType =
  | "severity_threshold"
  | "concurrent_issues"
  | "financial_impact"
  | "regulatory_breach"
  | "escalation_exhausted"
  | "manual";

export interface EscalationMatrixSettings {
  id: number;
  // Global Escalation
  escalation_enabled: boolean;
  default_response_time_minutes: number;
  max_escalation_levels: number;
  auto_escalation_enabled: boolean;
  require_acknowledgment: boolean;
  // Crisis Mode
  crisis_mode_enabled: boolean;
  crisis_activation_severity: CrisisActivationSeverity;
  crisis_activation_severity_display: string;
  crisis_activation_threshold: number;
  crisis_notification_channels: string[];
  crisis_war_room_enabled: boolean;
  crisis_auto_deactivate_hours: number;
  // Board Notifications
  board_notification_enabled: boolean;
  board_severity_threshold: BoardSeverityThreshold;
  board_severity_threshold_display: string;
  board_notification_recipients: string[];
  board_notification_cooldown_hours: number;
  // Metadata
  created_at: string;
  updated_at: string;
}

export interface EscalationTier {
  id: number;
  severity: EscalationTierSeverity;
  severity_display: string;
  tier_level: number;
  name: string;
  description: string;
  response_time_minutes: number;
  escalate_to_roles: string[];
  notification_channels: string[];
  requires_acknowledgment: boolean;
  is_active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface AutoEscalationRule {
  id: number;
  name: string;
  description: string;
  rule_type: EscalationRuleType;
  rule_type_display: string;
  // Time-based
  source_tier: number | null;
  source_tier_name: string | null;
  target_tier: number | null;
  target_tier_name: string | null;
  escalate_after_minutes: number | null;
  condition_type: EscalationConditionType;
  condition_type_display: string;
  condition_threshold: number | null;
  notify_original_assignee: boolean;
  // Parallel
  trigger_severity: EscalationTierSeverity | "";
  trigger_severity_display: string | null;
  parallel_notify_roles: string[];
  parallel_notify_emails: string[];
  parallel_channels: string[];
  // Status
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface BoardNotificationTrigger {
  id: number;
  name: string;
  description: string;
  trigger_type: BoardTriggerType;
  trigger_type_display: string;
  severity_threshold: EscalationTierSeverity | "";
  severity_threshold_display: string | null;
  concurrent_issue_count: number | null;
  financial_threshold_amount: string | null;
  notification_message_template: string;
  recipients: string[];
  notification_channels: string[];
  cooldown_hours: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// Communication & Branding Settings
// ---------------------------------------------------------------------------

export type PaperSize = "a4" | "letter" | "legal";

export interface CommunicationBrandingSettings {
  id: number;
  // Email Branding
  email_sender_name: string;
  email_sender_address: string;
  email_reply_to: string;
  email_header_html: string;
  email_footer_html: string;
  email_primary_color: string;
  email_logo_url: string;
  // Notification Branding
  notification_brand_color: string;
  notification_accent_color: string;
  notification_logo_url: string;
  notification_app_name: string;
  notification_include_logo: boolean;
  // SMS Configuration
  sms_sender_id: string;
  sms_prefix: string;
  sms_opt_out_message: string;
  sms_character_limit: number;
  sms_enabled: boolean;
  // Letterhead
  letterhead_header_html: string;
  letterhead_footer_html: string;
  letterhead_paper_size: PaperSize;
  letterhead_paper_size_display: string;
  letterhead_margin_top_mm: number;
  letterhead_margin_bottom_mm: number;
  letterhead_watermark_text: string;
  letterhead_watermark_opacity: number;
  // Document Footer Disclaimers
  default_footer_disclaimer: string;
  contract_footer_disclaimer: string;
  invoice_footer_disclaimer: string;
  report_footer_disclaimer: string;
  // Digital Signature
  signature_email_subject: string;
  signature_email_body: string;
  signature_reminder_enabled: boolean;
  signature_reminder_frequency_hours: number;
  signature_expiry_days: number;
  signature_branding_enabled: boolean;
  // Metadata
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// CRM — Leads & Opportunity Management
// ---------------------------------------------------------------------------

export type PipelineStage = "inquiry" | "qualified" | "site_visit" | "offer_made" | "reservation" | "spa_issued" | "closed";
export type LeadStatus = "active" | "won" | "lost" | "disqualified";
export type LeadPriority = "low" | "medium" | "high" | "urgent";
export type LeadType = "buyer" | "tenant" | "investor";
export type PaymentCapability = "cash" | "mortgage" | "installment" | "mixed" | "undetermined";
export type BrokerStatus = "active" | "inactive" | "suspended";
export type InterestLevel = "low" | "medium" | "high";
export type LeadActivityType = "call" | "email" | "meeting" | "site_visit" | "note" | "follow_up" | "document" | "other";
export type UnitPreferenceType = "apartment" | "villa" | "townhouse" | "penthouse" | "studio" | "duplex" | "office" | "retail" | "warehouse" | "land" | "other";

export interface LeadSource {
  id: number;
  name: string;
  code: string;
  description: string;
  is_active: boolean;
  sort_order: number;
  organization: number;
  created_at: string;
  updated_at: string;
}

export interface CRMBroker {
  id: number;
  name: string;
  company: string;
  license_number: string;
  email: string;
  phone: string;
  commission_rate: string | null;
  status: BrokerStatus;
  notes: string;
  lead_count: number;
  organization: number;
  created_at: string;
  updated_at: string;
}

export interface LeadProjectInterest {
  id: number;
  lead: number;
  project: number;
  project_name: string;
  interest_level: InterestLevel;
  notes: string;
  created_at: string;
}

export interface LeadUnitPreference {
  id: number;
  lead: number;
  unit_type: UnitPreferenceType;
  unit_type_display: string;
  min_bedrooms: number | null;
  max_bedrooms: number | null;
  min_area_sqft: string | null;
  max_area_sqft: string | null;
  floor_preference: string;
  view_preference: string;
  notes: string;
  created_at: string;
}

export interface LeadActivity {
  id: number;
  lead: number;
  lead_name: string;
  activity_type: LeadActivityType;
  activity_type_display: string;
  subject: string;
  description: string;
  scheduled_at: string | null;
  completed_at: string | null;
  is_completed: boolean;
  performed_by: number | null;
  performed_by_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface LeadStageTransition {
  id: number;
  lead: number;
  from_stage: PipelineStage;
  to_stage: PipelineStage;
  transitioned_by: number | null;
  transitioned_by_name: string | null;
  notes: string;
  transitioned_at: string;
}

export interface LeadListItem {
  id: number;
  first_name: string;
  last_name: string;
  full_name: string;
  email: string;
  phone: string;
  company: string;
  lead_type: LeadType;
  pipeline_stage: PipelineStage;
  pipeline_stage_display: string;
  status: LeadStatus;
  status_display: string;
  priority: LeadPriority;
  score: number;
  tags: string[];
  source: number | null;
  source_name: string | null;
  broker: number | null;
  broker_name: string | null;
  budget_min: string | null;
  budget_max: string | null;
  payment_capability: PaymentCapability;
  preferred_locations: string[];
  assigned_to: number | null;
  assigned_to_name: string | null;
  inquiry_date: string;
  days_in_pipeline: number;
  activity_count: number;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface LeadDetail extends LeadListItem {
  secondary_phone: string;
  nationality: string;
  referral_name: string;
  qualified_date: string | null;
  site_visit_date: string | null;
  offer_date: string | null;
  reservation_date: string | null;
  spa_issued_date: string | null;
  closed_date: string | null;
  converted_customer: number | null;
  converted_customer_name: string | null;
  lost_reason: string;
  notes: string;
  archived_at: string | null;
  archived_reason: string;
  organization: number;
  project_interests: LeadProjectInterest[];
  unit_preferences: LeadUnitPreference[];
  activities: LeadActivity[];
  stage_transitions: LeadStageTransition[];
}

export interface PipelineStageCount {
  stage: PipelineStage;
  label: string;
  count: number;
}

export interface PipelineOverview {
  total_leads: number;
  active_leads: number;
  won_leads: number;
  lost_leads: number;
  conversion_rate: number;
  avg_days_to_close: number | null;
  pipeline_stages: PipelineStageCount[];
  by_source: Array<{ source: string; count: number }>;
}

// --- Contact & Account Management ---

export type ContactEntityType = "individual" | "organization";
export type ContactKYCStatus = "not_submitted" | "pending_review" | "under_review" | "verified" | "rejected";
export type ContactRiskProfile = "undisclosed" | "conservative" | "balanced" | "aggressive";
export type ContactInteractionType = "call" | "email" | "meeting" | "site_visit" | "whatsapp" | "note";
export type ContactDealStatus = "active" | "won" | "lost" | "on_hold";
export type ContactRelationshipType = "interested" | "shortlisted" | "reserved" | "purchased" | "leased" | "investor_target";
export type ContactDocumentType = "id_card" | "passport" | "company_registration" | "proof_of_funds" | "utility_bill" | "other";
export type ContactComplianceStatus = "pending_review" | "in_review" | "approved" | "rejected";

export interface ContactInteraction {
  id: number;
  contact: number;
  interaction_type: ContactInteractionType;
  interaction_type_display: string;
  subject: string;
  details: string;
  happened_at: string;
  follow_up_required: boolean;
  follow_up_due_at: string | null;
  performed_by: number | null;
  performed_by_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface ContactDealLink {
  id: number;
  contact: number;
  lead: number | null;
  lead_name: string | null;
  reservation: number | null;
  reservation_number: string | null;
  deal_name: string;
  stage: string;
  status: ContactDealStatus;
  status_display: string;
  deal_value: string | null;
  close_probability: number;
  notes: string;
  linked_at: string;
}

export interface ContactPropertyLink {
  id: number;
  contact: number;
  project: number | null;
  project_name: string | null;
  property: number | null;
  property_name: string | null;
  unit: number | null;
  unit_number: string | null;
  relationship_type: ContactRelationshipType;
  relationship_type_display: string;
  budget_estimate: string | null;
  notes: string;
  linked_at: string;
}

export interface ContactDocument {
  id: number;
  contact: number;
  document_type: ContactDocumentType;
  document_type_display: string;
  file_name: string;
  file_url: string;
  reference_number: string;
  issued_at: string | null;
  expires_at: string | null;
  is_kyc_document: boolean;
  latest_review_status: ContactComplianceStatus | null;
  uploaded_by: number | null;
  uploaded_by_name: string | null;
  notes: string;
  uploaded_at: string;
}

export interface ContactComplianceReview {
  id: number;
  contact: number;
  document: number | null;
  document_name: string | null;
  status: ContactComplianceStatus;
  status_display: string;
  requested_by: number | null;
  requested_by_name: string | null;
  reviewed_by: number | null;
  reviewed_by_name: string | null;
  notes: string;
  requested_at: string;
  reviewed_at: string | null;
  updated_at: string;
}

export interface ContactAccountListItem {
  id: number;
  entity_type: ContactEntityType;
  entity_type_display: string;
  display_name: string;
  first_name: string;
  last_name: string;
  legal_name: string;
  trade_name: string;
  email: string;
  phone: string;
  city: string;
  country: string;
  kyc_status: ContactKYCStatus;
  kyc_status_display: string;
  budget_min: string | null;
  budget_max: string | null;
  risk_profile: ContactRiskProfile;
  risk_profile_display: string;
  preferred_locations: string[];
  preferred_property_types: string[];
  finance_customer: number | null;
  finance_customer_name: string | null;
  finance_synced_at: string | null;
  is_active: boolean;
  interaction_count: number;
  active_deal_count: number;
  document_count: number;
  created_at: string;
  updated_at: string;
}

export interface ContactAccountDetail extends ContactAccountListItem {
  middle_name: string;
  title: string;
  date_of_birth: string | null;
  nationality: string;
  registration_number: string;
  tax_identification_number: string;
  primary_contact_name: string;
  address: string;
  secondary_phone: string;
  kyc_reference_number: string;
  kyc_last_uploaded_at: string | null;
  annual_income: string | null;
  net_worth: string | null;
  liquidity_estimate: string | null;
  preference_notes: string;
  interaction_summary: string;
  notes: string;
  created_by: number | null;
  updated_by: number | null;
  interactions: ContactInteraction[];
  deal_links: ContactDealLink[];
  property_links: ContactPropertyLink[];
  documents: ContactDocument[];
  compliance_reviews: ContactComplianceReview[];
}

export interface ContactAccountOverview {
  total_contacts: number;
  individual_contacts: number;
  organization_accounts: number;
  kyc_verified: number;
  kyc_pending: number;
  finance_synced: number;
  high_value_contacts: number;
  follow_up_due: number;
  entity_breakdown: Array<{ entity_type: ContactEntityType; label: string; count: number }>;
  kyc_breakdown: Array<{ status: ContactKYCStatus; label: string; count: number }>;
}

export type PropertyMatchCandidateType = "unit" | "project";
export type PropertyMatchStatus = "suggested" | "viewed" | "shortlisted" | "dismissed" | "converted";

export interface LeadPropertyMatch {
  id: number;
  organization: number;
  lead: number;
  lead_name: string;
  candidate_type: PropertyMatchCandidateType;
  candidate_type_display: string;
  property: number | null;
  property_name: string | null;
  unit: number | null;
  unit_number: string | null;
  project: number | null;
  project_name: string | null;
  match_score: string;
  score_breakdown: {
    budget: number;
    location: number;
    unit_type: number;
    payment_eligibility: number;
  };
  reason_summary: string;
  budget_fit: boolean;
  location_fit: boolean;
  unit_type_fit: boolean;
  payment_eligibility_fit: boolean;
  status: PropertyMatchStatus;
  status_display: string;
  source: "qualified_lead" | "property_launch" | "manual_refresh";
  source_display: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PropertyMatchOverview {
  total_matches: number;
  suggested_matches: number;
  shortlisted_matches: number;
  unit_matches: number;
  project_matches: number;
  average_score: string;
  by_status: Array<{ status: PropertyMatchStatus; count: number }>;
  by_candidate_type: Array<{ candidate_type: PropertyMatchCandidateType; count: number }>;
}

// --- Financial Pre-Assessment ---

export type AssessmentStatus = "pending" | "in_progress" | "completed" | "expired";
export type EmploymentStatus = "employed" | "self_employed" | "business_owner" | "retired" | "unemployed" | "other";
export type RiskLevel = "low" | "medium" | "high" | "critical";
export type RecommendedPlan = "cash" | "mortgage" | "installment" | "mixed";
export type ScenarioPlanType = "cash" | "mortgage" | "installment" | "mixed";

export interface LeadPaymentScenario {
  id: number;
  assessment: number;
  label: string;
  plan_type: ScenarioPlanType;
  plan_type_display: string;
  property_price: string;
  down_payment_pct: string;
  down_payment_amount: string;
  financed_amount: string | null;
  interest_rate: string | null;
  tenure_months: number;
  monthly_payment: string | null;
  total_cost: string | null;
  is_recommended: boolean;
  is_affordable: boolean;
  notes: string;
  created_at: string;
}

export interface FinancialAssessmentListItem {
  id: number;
  lead_id: number;
  lead_name: string;
  lead_email: string;
  lead_pipeline_stage: PipelineStage;
  lead_budget_min: string | null;
  lead_budget_max: string | null;
  status: AssessmentStatus;
  status_display: string;
  affordability_score: number | null;
  risk_score: number | null;
  risk_level: RiskLevel | "";
  risk_level_display: string;
  mortgage_prequalified: boolean;
  mortgage_prequalification_amount: string | null;
  employment_status: EmploymentStatus | "";
  employment_status_display: string;
  recommended_plan: RecommendedPlan | "";
  max_affordable_price: string | null;
  assessed_by: number | null;
  assessed_by_name: string | null;
  assessment_date: string | null;
  scenario_count: number;
  created_at: string;
  updated_at: string;
}

export interface FinancialAssessmentDetail extends FinancialAssessmentListItem {
  lead_phone: string;
  lead_company: string;
  lead_pipeline_stage_display: string;
  lead_payment_capability: string;
  lead: number;
  monthly_income: string | null;
  monthly_expenses: string | null;
  existing_liabilities: string | null;
  liquid_assets: string | null;
  net_worth: string | null;
  employment_duration_months: number | null;
  employer_name: string;
  debt_to_income_ratio: string | null;
  mortgage_provider: string;
  mortgage_tenure_months: number | null;
  mortgage_interest_rate: string | null;
  mortgage_notes: string;
  risk_factors: string[];
  recommended_plan_display: string;
  recommended_down_payment_pct: string | null;
  recommended_monthly_payment: string | null;
  disposable_income: string | null;
  notes: string;
  scenarios: LeadPaymentScenario[];
}

// --- Broker & Channel Partner Management ---

export type CommissionType = "percentage" | "fixed" | "tiered";
export type CommissionTriggerStage = "reservation" | "spa_issued" | "closed" | "milestone";
export type CommissionPaymentSplit = "upfront" | "split_50_50" | "split_30_70" | "milestone";
export type CommissionEarningStatus = "pending" | "approved" | "processing" | "paid" | "cancelled";

export interface BrokerTier {
  id: number;
  name: string;
  code: string;
  min_deals: number;
  min_revenue: string;
  commission_multiplier: string;
  bonus_pct: string;
  evaluation_period_months: number;
  benefits: string;
  color: string;
  sort_order: number;
  is_active: boolean;
  broker_count: number;
  created_at: string;
  updated_at: string;
}

export interface BrokerListItem {
  id: number;
  name: string;
  company: string;
  license_number: string;
  email: string;
  phone: string;
  commission_rate: string | null;
  tier: number | null;
  tier_name: string | null;
  tier_color: string;
  commission_multiplier: string | null;
  status: BrokerStatus;
  lead_count: number;
  deals_closed: number;
  total_earnings: string | number;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface BrokerDetail extends BrokerListItem {
  organization: number;
  tier_data: BrokerTier | null;
  pending_earnings: string | number;
  active_leads: number;
  conversion_rate: number;
}

export interface CommissionStructure {
  id: number;
  name: string;
  description: string;
  commission_type: CommissionType;
  commission_type_display: string;
  base_rate: string;
  fixed_amount: string | null;
  tiered_brackets: Array<{ min: number; max: number; rate: number }>;
  trigger_stage: CommissionTriggerStage;
  trigger_stage_display: string;
  payment_split: CommissionPaymentSplit;
  payment_split_display: string;
  broker: number | null;
  broker_name: string | null;
  project: number | null;
  project_name: string | null;
  is_default: boolean;
  is_active: boolean;
  effective_from: string | null;
  effective_to: string | null;
  earning_count: number;
  created_at: string;
  updated_at: string;
}

export interface CommissionEarning {
  id: number;
  broker: number;
  broker_name: string;
  lead: number;
  lead_name: string;
  project: number | null;
  project_name: string | null;
  commission_structure: number | null;
  structure_name: string | null;
  deal_value: string;
  commission_rate: string;
  base_commission: string;
  tier_multiplier: string;
  bonus_amount: string;
  total_commission: string;
  trigger_stage: CommissionTriggerStage;
  trigger_stage_display: string;
  triggered_at: string;
  status: CommissionEarningStatus;
  status_display: string;
  approved_by: number | null;
  approved_by_name?: string | null;
  approved_at: string | null;
  paid_at: string | null;
  payment_reference: string;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface BrokerPerformance {
  period_months: number;
  total_leads: number;
  won_leads: number;
  lost_leads: number;
  active_leads: number;
  conversion_rate: number;
  avg_days_to_close: number | null;
  total_deal_value: string | number;
  total_commission: string | number;
  paid_commission: string | number;
  pending_commission: string | number;
  monthly_deals: Array<{ month: string; count: number }>;
}

export interface BrokerForecast {
  broker_id: number;
  broker_name: string;
  commission_rate: number;
  tier_multiplier: number;
  active_pipeline_count: number;
  total_pipeline_value: number;
  best_case_commission: number;
  weighted_forecast: number;
  pipeline_deals: Array<{
    lead_id: number;
    lead_name: string;
    pipeline_stage: PipelineStage;
    deal_value: number;
    probability: number;
    estimated_commission: number;
    weighted_commission: number;
  }>;
}

export interface BrokerPerformanceOverview {
  period_months: number;
  total_active_brokers: number;
  total_broker_leads: number;
  won_broker_leads: number;
  conversion_rate: number;
  total_commission: string | number;
  total_deal_value: string | number;
  paid_commission: string | number;
  pending_commission: string | number;
  top_by_deals: Array<{ broker_id: number; broker_name: string; deals: number }>;
  top_by_commission: Array<{ broker_id: number; broker_name: string; total: string | number }>;
  tier_distribution: Array<{ tier: string; count: number }>;
}


// ---------------------------------------------------------------------------
// Communication Engine
// ---------------------------------------------------------------------------

export type CommunicationChannel = 'email' | 'whatsapp' | 'sms' | 'phone' | 'video_call' | 'in_person' | 'other';
export type CommunicationDirection = 'inbound' | 'outbound';
export type CommunicationStatus = 'draft' | 'sent' | 'delivered' | 'read' | 'failed' | 'received';
export type CampaignStatus = 'draft' | 'scheduled' | 'running' | 'paused' | 'completed' | 'cancelled';
export type CampaignType = 'email_blast' | 'whatsapp_campaign' | 'sms_blast' | 'digital_ads' | 'drip' | 'follow_up';
export type CampaignRecipientStatus = 'pending' | 'sent' | 'delivered' | 'opened' | 'clicked' | 'bounced' | 'failed' | 'unsubscribed';
export type CallDisposition = 'answered' | 'no_answer' | 'voicemail' | 'busy' | 'wrong_number' | 'dropped';
export type FollowUpTaskStatus = 'pending' | 'in_progress' | 'completed' | 'breached' | 'escalated' | 'cancelled';
export type MeetingOutcome = 'positive' | 'neutral' | 'negative' | 'follow_up_needed' | 'no_show';
export type MeetingType = 'in_person' | 'video_call' | 'phone_conference' | 'site_visit';
export type LeadDocumentEventType =
  | 'proposal_sent' | 'proposal_viewed'
  | 'spa_sent' | 'spa_downloaded' | 'spa_signed'
  | 'brochure_sent' | 'brochure_viewed'
  | 'price_list_sent' | 'price_list_viewed'
  | 'floor_plan_sent' | 'floor_plan_viewed'
  | 'contract_sent' | 'contract_downloaded'
  | 'other';

export interface CallRecording {
  id: number;
  duration_seconds: number;
  duration_display: string;
  recording_url: string;
  recording_storage_path: string;
  disposition: CallDisposition;
  disposition_display: string;
  caller_number: string;
  callee_number: string;
  transcription: string;
  call_started_at: string | null;
  call_ended_at: string | null;
  notes: string;
  created_at: string;
}

export interface CommunicationLogListItem {
  id: number;
  lead: number;
  lead_name: string;
  channel: CommunicationChannel;
  channel_display: string;
  direction: CommunicationDirection;
  direction_display: string;
  status: CommunicationStatus;
  status_display: string;
  subject: string;
  summary: string;
  from_address: string;
  to_address: string;
  campaign: number | null;
  campaign_name: string | null;
  performed_by: number | null;
  performed_by_name: string | null;
  has_recording: boolean;
  communicated_at: string;
  created_at: string;
}

export interface CommunicationLogDetail extends CommunicationLogListItem {
  body: string;
  external_message_id: string;
  cc: string;
  attachments: Array<{ name: string; url: string; size?: number }>;
  activity: number | null;
  call_recording: CallRecording | null;
  updated_at: string;
}

export interface CampaignListItem {
  id: number;
  name: string;
  description: string;
  campaign_type: CampaignType;
  campaign_type_display: string;
  status: CampaignStatus;
  status_display: string;
  channel: CommunicationChannel;
  channel_display: string;
  target_pipeline_stages: string[];
  target_lead_sources: number[];
  target_projects: number[];
  target_lead_types: string[];
  auto_create_leads_on_launch: boolean;
  auto_create_leads_count: number;
  auto_create_lead_type: "buyer" | "tenant" | "investor";
  auto_created_leads_count: number;
  total_recipients: number;
  sent_count: number;
  delivered_count: number;
  opened_count: number;
  clicked_count: number;
  failed_count: number;
  spend_amount: string;
  revenue_attributed: string;
  open_rate: number;
  click_rate: number;
  delivery_rate: number;
  roi_percent: number;
  scheduled_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_by: number | null;
  created_by_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface CampaignRecipient {
  id: number;
  lead: number;
  lead_name: string;
  lead_email: string;
  lead_phone: string;
  status: CampaignRecipientStatus;
  status_display: string;
  sent_at: string | null;
  delivered_at: string | null;
  opened_at: string | null;
  clicked_at: string | null;
  failed_reason: string;
  communication_log: number | null;
  created_at: string;
}

export interface CampaignDetail extends CampaignListItem {
  notification_template: number | null;
  template_name: string | null;
  subject: string;
  body: string;
  recipients: CampaignRecipient[];
}

export interface FollowUpRule {
  id: number;
  name: string;
  description: string;
  trigger_stage: string;
  trigger_stage_display: string;
  follow_up_within_hours: number;
  sla_severity: number | null;
  sla_severity_level: string | null;
  sla_response_hours: number | null;
  required_activity_type: string;
  required_activity_type_display: string;
  auto_assign_to_owner: boolean;
  is_active: boolean;
  active_task_count: number;
  created_at: string;
  updated_at: string;
}

export interface FollowUpTaskListItem {
  id: number;
  rule: number;
  rule_name: string;
  lead: number;
  lead_id: number;
  lead_name: string;
  assigned_to: number | null;
  assigned_to_name: string | null;
  status: FollowUpTaskStatus;
  status_display: string;
  due_at: string;
  is_overdue: boolean;
  completed_at: string | null;
  breached_at: string | null;
  escalated_at: string | null;
  completed_activity: number | null;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface ActivityTaskTimelineEntry {
  kind: "activity" | "task";
  id: number;
  timestamp: string;
  lead_id: number;
  lead_name: string;
  title: string;
  subtitle: string;
  status: string;
  status_display: string;
}

export interface ActivityTaskCalendarIntegration {
  timezone_override: string;
  default_meeting_duration_minutes: number;
  meeting_buffer_minutes: number;
  google_sync_enabled: boolean;
  outlook_sync_enabled: boolean;
  ical_sync_enabled: boolean;
}

export interface ActivityTaskOverviewUpcoming {
  id: number;
  lead: number;
  lead_name: string;
  subject: string;
  activity_type: LeadActivityType;
  activity_type_display: string;
  scheduled_at: string;
  is_completed: boolean;
  performed_by_name: string | null;
}

export interface ActivityTaskOverview {
  window_days: number;
  total_activities: number;
  completed_activities: number;
  scheduled_upcoming_count: number;
  missed_activities_count: number;
  activities_by_type: Array<{ activity_type: LeadActivityType; label: string; count: number }>;
  total_tasks: number;
  open_task_count: number;
  overdue_task_count: number;
  escalated_task_count: number;
  task_status_breakdown: Array<{ status: FollowUpTaskStatus; label: string; count: number }>;
  calendar_integration: ActivityTaskCalendarIntegration;
  upcoming_activities: ActivityTaskOverviewUpcoming[];
  timeline: ActivityTaskTimelineEntry[];
}

export interface LeadDocumentEvent {
  id: number;
  lead: number;
  lead_name: string;
  event_type: LeadDocumentEventType;
  event_type_display: string;
  document_name: string;
  document: number | null;
  audit_event: number | null;
  delivered_via: CommunicationChannel | '';
  delivered_via_display: string;
  delivered_to: string;
  viewed_at: string | null;
  downloaded_at: string | null;
  performed_by: number | null;
  performed_by_name: string | null;
  notes: string;
  created_at: string;
}

export interface MeetingRecordListItem {
  id: number;
  lead: number;
  lead_name: string;
  title: string;
  meeting_type: MeetingType;
  meeting_type_display: string;
  outcome: MeetingOutcome | '';
  outcome_display: string;
  scheduled_start: string;
  scheduled_end: string | null;
  actual_start: string | null;
  actual_end: string | null;
  location: string;
  meeting_link: string;
  organized_by: number | null;
  organized_by_name: string | null;
  project: number | null;
  project_name: string | null;
  duration_minutes: number | null;
  created_at: string;
  updated_at: string;
}

export interface MeetingRecordDetail extends MeetingRecordListItem {
  activity: number | null;
  attendees: Array<{ name: string; email?: string; role?: string }>;
  agenda: string;
  minutes: string;
  action_items: Array<{ description: string; assignee?: string; due_date?: string }>;
  property_unit: number | null;
  notes: string;
}

export interface CommunicationOverview {
  period_months: number;
  total_communications: number;
  channel_breakdown: Array<{ channel: string; count: number }>;
  direction_breakdown: Array<{ direction: string; count: number }>;
  active_campaigns: number;
  follow_up_pending: number;
  follow_up_overdue: number;
  follow_up_breached: number;
  document_events: number;
  meetings_this_month: number;
}

// ---------------------------------------------------------------------------
// Reservation & Conversion
// ---------------------------------------------------------------------------

export type ReservationStatus =
  | "hold"
  | "reserved"
  | "payment_pending"
  | "paid"
  | "converting"
  | "converted"
  | "expired"
  | "cancelled";

export interface ReservationEvent {
  id: number;
  reservation: number;
  event_type: string;
  event_type_display: string;
  performed_by: number | null;
  performed_by_name: string | null;
  notes: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface ReservationListItem {
  id: number;
  reservation_number: string;
  status: ReservationStatus;
  status_display: string;
  lead: number;
  lead_id: number;
  lead_name: string;
  unit: number;
  unit_id: number;
  unit_number: string;
  property_name: string;
  project: number | null;
  project_name: string | null;
  total_price: string;
  deposit_amount: string;
  reservation_fee: string;
  hold_expires_at: string;
  payment_deadline: string | null;
  reservation_date: string | null;
  confirmation_date: string | null;
  performed_by: number | null;
  performed_by_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReservationDetail extends ReservationListItem {
  organization: number;
  converted_customer: number | null;
  converted_customer_name: string | null;
  payment_plan: number | null;
  payment_plan_number: string | null;
  reservation_agreement: number | null;
  lead_email: string;
  lead_phone: string;
  lead_type: string;
  lead_payment_capability: string;
  unit_floor: number | null;
  unit_area_sqft: string;
  unit_bedrooms: number | null;
  unit_bathrooms: number | null;
  unit_asking_price: string | null;
  unit_status: string;
  cancelled_reason: string;
  notes: string;
  events: ReservationEvent[];
}

export interface ReservationOverview {
  active_holds: number;
  pending_payments: number;
  paid: number;
  converted: number;
  expired: number;
  cancelled: number;
  total_converted_value: number;
}

// --- CRM Analytics & Reporting ---

export interface CRMAnalyticsStageConversion {
  from_stage: PipelineStage;
  to_stage: PipelineStage;
  label: string;
  eligible_count: number;
  progressed_count: number;
  conversion_rate: number;
  avg_days_to_progress: number | null;
}

export interface CRMAnalyticsStageDuration {
  label: string;
  from_stage: PipelineStage;
  to_stage: PipelineStage;
  avg_days: number | null;
  sample_size: number;
}

export interface CRMAnalyticsRevenueStageBreakdown {
  stage: string;
  count: number;
  deal_value: string;
  weighted_value: string;
}

export interface CRMAnalyticsLeadSourcePerformance {
  source_id: number | null;
  source_name: string;
  total_leads: number;
  active_leads: number;
  won_leads: number;
  lost_leads: number;
  disqualified_leads: number;
  average_score: number;
  conversion_rate: number;
  deal_count: number;
  pipeline_value: string;
  weighted_forecast: string;
  closed_won_value: string;
}

export interface CRMAnalyticsAgentPerformance {
  agent_id: number;
  agent_name: string;
  total_leads: number;
  active_leads: number;
  won_leads: number;
  lost_leads: number;
  average_score: number;
  avg_days_in_pipeline: number | null;
  avg_days_to_close: number | null;
  conversion_rate: number;
  deal_count: number;
  active_deals: number;
  won_deals: number;
  pipeline_value: string;
  weighted_forecast: string;
  activity_count: number;
}

export interface CRMAnalyticsPipelineDropMonitor {
  lookback_days: number;
  current_period_start: string;
  current_period_end: string;
  previous_period_start: string;
  previous_period_end: string;
  current_additions_count: number;
  previous_additions_count: number;
  current_additions_value: string;
  previous_additions_value: string;
  volume_drop_percent: number;
  value_drop_percent: number;
  drop_percent: number;
  is_alert: boolean;
}

export interface CRMAnalyticsCampaignPerformanceRow {
  campaign_id: number;
  name: string;
  status: CampaignStatus;
  channel: CommunicationChannel;
  campaign_type: CampaignType;
  total_recipients: number;
  auto_created_leads_count: number;
  open_rate: number;
  click_rate: number;
  delivery_rate: number;
  spend_amount: string;
  revenue_attributed: string;
  roi_percent: number;
  target_lead_types: string[];
}

export interface CRMAnalyticsCampaignPerformance {
  total_campaigns: number;
  running_campaigns: number;
  completed_campaigns: number;
  generated_leads: number;
  total_spend: string;
  total_revenue: string;
  roi_percent: number;
  campaigns: CRMAnalyticsCampaignPerformanceRow[];
}

export interface CRMProjectsIntegrationInsight {
  area_name: string;
  title: string;
  summary: string;
  demand_share_percent: number;
  lead_count: number;
  qualified_lead_count: number;
  won_lead_count: number;
  window_days: number;
  threshold_percent: number;
  is_active: boolean;
  last_triggered_at: string | null;
  updated_at: string | null;
}

export interface CRMProjectsIntegrationSummary {
  last_synced_at: string | null;
  demand_insight_count: number;
  high_demand_insight_count: number;
  top_demand_areas: CRMProjectsIntegrationInsight[];
  high_demand_areas: CRMProjectsIntegrationInsight[];
}

export interface CRMProcurementIntegrationInsight {
  area_name: string;
  insight_type: string;
  title: string;
  summary: string;
  demand_share_percent: number;
  lead_count: number;
  qualified_lead_count: number;
  won_lead_count: number;
  bulk_buyer_lead_count: number;
  window_days: number;
  threshold_percent: number;
  min_bulk_leads: number;
  is_active: boolean;
  last_triggered_at: string | null;
  updated_at: string | null;
}

export interface CRMProcurementIntegrationSummary {
  last_synced_at: string | null;
  bulk_demand_insight_count: number;
  furnishing_package_count: number;
  add_on_package_count: number;
  triggered_areas: string[];
  package_recommendations: CRMProcurementIntegrationInsight[];
}

export interface CRMAnalyticsReportingOverview {
  generated_at: string;
  window_days: number;
  summary: {
    total_leads: number;
    active_leads: number;
    won_leads: number;
    lost_leads: number;
    conversion_rate: number;
    sales_velocity_days: number | null;
    sales_velocity_deals_per_month: number;
    pipeline_value: string;
    weighted_forecast: string;
    closed_won_revenue: string;
    active_deals: number;
  };
  conversion_rates: {
    overall_conversion_rate: number;
    qualified_conversion_rate: number;
    win_rate: number;
    qualified_or_beyond_count: number;
    closed_outcomes_count: number;
    stage_conversion: CRMAnalyticsStageConversion[];
  };
  sales_velocity: {
    avg_days_to_close: number | null;
    median_days_to_close: number | null;
    closed_won_count: number;
    deals_per_month: number;
    stage_durations: CRMAnalyticsStageDuration[];
  };
  revenue_forecast: {
    total_deals: number;
    active_deals: number;
    pipeline_value: string;
    weighted_forecast: string;
    closed_won_value: string;
    forecast_coverage_ratio: number;
    stage_breakdown: CRMAnalyticsRevenueStageBreakdown[];
  };
  lead_source_performance: CRMAnalyticsLeadSourcePerformance[];
  agent_performance: CRMAnalyticsAgentPerformance[];
  pipeline_drop_monitor: CRMAnalyticsPipelineDropMonitor;
  campaign_performance: CRMAnalyticsCampaignPerformance;
  projects_integration: CRMProjectsIntegrationSummary;
  procurement_integration: CRMProcurementIntegrationSummary;
}

export interface CRMAnalyticsAutomationRunResult {
  organization_id: number;
  recipients?: number;
  notifications_sent: number;
  emails_sent: number;
  skipped?: boolean;
  suppressed?: boolean;
  reason: string;
  alert_triggered?: boolean;
  pipeline_drop?: CRMAnalyticsPipelineDropMonitor;
  areas_evaluated?: number;
  insights_upserted?: number;
  high_demand_triggered?: number;
  high_demand_areas?: string[];
  package_triggers?: number;
  triggered_areas?: string[];
}

// --- Partner Onboarding Gateway ---

export type PartnerType = "client" | "contractor" | "investor";
export type PartnerOnboardingStatus =
  | "draft"
  | "in_progress"
  | "under_review"
  | "approved"
  | "rejected"
  | "active"
  | "suspended"
  | "cancelled";

export type OnboardingStageStatus =
  | "not_started"
  | "in_progress"
  | "completed"
  | "waived"
  | "blocked";

export type PartnerPortalRole = "client" | "contractor" | "investor" | "lead_investor";
export type PartnerBudgetScope = "none" | "boq_only" | "aggregated" | "full";

export interface OnboardingTemplateStage {
  id: number;
  template: number;
  sequence: number;
  code: string;
  name: string;
  description: string;
  is_required: boolean;
  approval_required: boolean;
  approval_role_label: string;
  sla_hours: number | null;
  auto_complete: boolean;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export type PartnerIntakeSourceChannel =
  | "physical_scan"
  | "email"
  | "secure_upload_link"
  | "tender_portal"
  | "data_room"
  | "internal_generated"
  | "other";

export type PartnerIntakeReviewStatus =
  | "received"
  | "under_review"
  | "approved"
  | "rejected"
  | "waived";

export interface OnboardingTemplateDocumentRequirement {
  id: number;
  template: number;
  sequence: number;
  code: string;
  name: string;
  description: string;
  is_required: boolean;
  applies_to_stage: number | null;
  stage_code: string | null;
  stage_name: string | null;
  accepted_sources: PartnerIntakeSourceChannel[];
  allowed_extensions: string[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface OnboardingTemplate {
  id: number;
  organization: number | null;
  partner_type: PartnerType;
  code: string;
  name: string;
  description: string;
  version: number;
  is_default: boolean;
  is_active: boolean;
  created_by: number | null;
  updated_by: number | null;
  created_at: string;
  updated_at: string;
  stage_count: number;
  stages: OnboardingTemplateStage[];
}

export interface PartnerOnboardingStageProgress {
  id: number;
  case: number;
  template_stage: number;
  stage_sequence: number;
  stage_code: string;
  stage_name: string;
  status: OnboardingStageStatus;
  is_required: boolean;
  started_at: string | null;
  completed_at: string | null;
  completed_by: number | null;
  notes: string;
  evidence_links: unknown[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface PartnerOnboardingApproval {
  created_at: string | null;
  approver_name: any;
  id: number;
  case: number;
  stage_progress: number | null;
  stage_code: string | null;
  stage_name: string | null;
  decision: "approved" | "rejected" | "changes_required";
  approver_role_label: string;
  comments: string;
  metadata: Record<string, unknown>;
  decided_by: number | null;
  decided_at: string;
}

export interface PartnerOnboardingIntakeDocument {
  id: number;
  case: number;
  requirement: number | null;
  requirement_code: string | null;
  requirement_name: string | null;
  template_stage: number | null;
  stage_code: string | null;
  stage_name: string | null;
  document_code: string;
  document_name: string;
  source_channel: PartnerIntakeSourceChannel;
  file: string | null;
  external_reference_url: string;
  external_reference_number: string;
  received_at: string;
  status: PartnerIntakeReviewStatus;
  submitted_by: number | null;
  submitted_by_name: string | null;
  reviewed_by: number | null;
  reviewed_by_name: string | null;
  reviewed_at: string | null;
  review_notes: string;
  linked_repository_document: number | null;
  linked_repository_document_title: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface PartnerEntitlement {
  id: number;
  case: number;
  organization: number;
  portal_role: PartnerPortalRole;
  project: number | null;
  project_name: string | null;
  spv_entity: number | null;
  spv_name: string | null;
  contract_reference: string;
  investment_vehicle_reference: string;
  budget_scope: PartnerBudgetScope;
  can_view_other_investors: boolean;
  can_edit: boolean;
  can_approve: boolean;
  can_comment: boolean;
  can_download_documents: boolean;
  is_active: boolean;
  effective_from: string;
  expires_at: string | null;
  created_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface PartnerOnboardingAuditEvent {
  actor_name: any;
  description: any;
  id: number;
  case: number;
  event_type:
    | "case_created"
    | "stages_initialized"
    | "stage_status_changed"
    | "case_status_changed"
    | "approval_recorded"
    | "entitlement_provisioned"
    | "portal_access_granted"
    | "erp_entity_created"
    | "lead_archived";
  actor: number | null;
  actor_email: string | null;
  actor_role_label: string;
  ip_address: string | null;
  message: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface PartnerOnboardingCaseListItem {
  id: number;
  organization: number;
  partner_type: PartnerType;
  partner_type_display: string;
  status: PartnerOnboardingStatus;
  status_display: string;
  template: number | null;
  template_name: string | null;
  title: string;
  contact_name: string;
  contact_email: string;
  lead: number | null;
  lead_name: string | null;
  vendor: number | null;
  vendor_name: string | null;
  investor: number | null;
  investor_name: string | null;
  customer: number | null;
  customer_name: string | null;
  project: number | null;
  spv_entity: number | null;
  contract_reference: string;
  investment_vehicle_reference: string;
  current_stage: number | null;
  current_stage_name: string | null;
  portal_access_granted: boolean;
  portal_access_granted_at: string | null;
  assigned_owner: number | null;
  assigned_owner_name: string | null;
  required_stage_total: number;
  required_stage_completed: number;
  completion_percent: number;
  required_document_total: number;
  approved_document_total: number;
  pending_document_review_count: number;
  missing_required_document_count: number;
  intake_gate_passed: boolean;
  has_erp_profile: boolean;
  created_by: number | null;
  updated_by: number | null;
  created_at: string;
  updated_at: string;
}

export interface PartnerOnboardingCaseDetail extends PartnerOnboardingCaseListItem {
  has_portal_access: any;
  contractor_name: string | null;
  contact_phone: string;
  notes: string;
  stage_progress: PartnerOnboardingStageProgress[];
  approvals: PartnerOnboardingApproval[];
  entitlements: PartnerEntitlement[];
  required_documents: OnboardingTemplateDocumentRequirement[];
  intake_documents: PartnerOnboardingIntakeDocument[];
}

export interface PartnerOnboardingOverview {
  total_cases: number;
  draft: number;
  in_progress: number;
  under_review: number;
  approved: number;
  active: number;
  rejected: number;
  suspended: number;
  cancelled: number;
  by_partner_type: { client: number; contractor: number; investor: number };
  portal_access_granted: number;
  avg_completion_percent: number;
}

// --- Partner Portal (operations layer) ---

export interface PartnerPortalScopeRef {
  id: number;
  name: string;
}

export interface PartnerPortalPermissions {
  can_view_other_investors: boolean;
  can_edit: boolean;
  can_approve: boolean;
  can_comment: boolean;
  can_download_documents: boolean;
}

export interface PartnerPortalLegalContext {
  accepted: boolean;
  accepted_at: string | null;
  terms_version: string;
  privacy_version: string;
}

export interface PartnerPortalContextResponse {
  is_partner_user: boolean;
  is_preview_mode: boolean;
  portal_roles: PartnerPortalRole[];
  partner_types: PartnerType[];
  budget_scope: PartnerBudgetScope;
  permissions: PartnerPortalPermissions;
  scopes: {
    projects: PartnerPortalScopeRef[];
    spv_entities: PartnerPortalScopeRef[];
    contract_references: string[];
    investment_vehicle_references: string[];
    allowed_confidentiality_levels: DocumentConfidentiality[];
  };
  linked_record_ids: {
    customers: number[];
    vendors: number[];
    investors: number[];
    leads: number[];
  };
  contact_emails: string[];
  legal: PartnerPortalLegalContext;
  cases: PartnerOnboardingCaseListItem[];
  entitlements: PartnerEntitlement[];
}

export interface PartnerPortalLegalStatusResponse extends PartnerPortalLegalContext {
  requires_acceptance: boolean;
}

export interface PartnerPortalLegalAcceptResponse extends PartnerPortalLegalContext {
  detail: string;
}

export interface PartnerPortalKpi {
  key: string;
  label: string;
  value: number;
}

export interface PartnerPortalDashboardResponse {
  primary_role: PartnerPortalRole | null;
  is_preview_mode: boolean;
  kpis: PartnerPortalKpi[];
  role_summary: Record<string, unknown>;
  recent_documents: PartnerPortalDocumentItem[];
  upcoming_expiries: DocumentExpiryRecord[];
  pending_signoffs: DocumentVersionRecord[];
}

export interface PartnerPortalDocumentItem extends DocumentRecord {
  current_version_id: number | null;
  current_version_file_path: string | null;
  current_version_label: string | null;
  expiry_date: string | null;
  expiry_trigger_category: DocumentExpiryTriggerCategory | null;
}

export interface PartnerPortalCommunicationItem {
  id: number;
  lead: number;
  lead_name: string;
  channel: string;
  direction: "inbound" | "outbound";
  status: string;
  subject: string;
  summary: string;
  body: string;
  from_address: string;
  to_address: string;
  attachments: Array<Record<string, unknown>>;
  performed_by: number | null;
  performed_by_name: string | null;
  communicated_at: string;
  created_at: string;
}

export interface PartnerPortalOnboardingDecision {
  id: number;
  case_id: number;
  decision: "approved" | "rejected" | "changes_required";
  approver_role_label: string;
  comments: string;
  stage_code: string | null;
  stage_name: string | null;
  decided_by: string | null;
  decided_at: string;
}

export interface PartnerPortalApprovalsResponse {
  can_approve: boolean;
  pending_count: number;
  pending_versions: DocumentVersionRecord[];
  recent_document_decisions: DocumentApprovalRecord[];
  onboarding_decisions: PartnerPortalOnboardingDecision[];
}

export interface PartnerPortalClientFinancialSection {
  summary: Record<string, string | number>;
  payment_plans: PaymentPlanListItem[];
  installments: PaymentInstallment[];
  invoices: InvoiceListItem[];
}

export interface PartnerPortalContractorFinancialSection {
  summary: Record<string, string | number>;
  purchase_orders: PurchaseOrderListItem[];
  bills: BillListItem[];
}

export interface PartnerPortalInvestorContribution {
  id: number;
  investor_name: string;
  project_name: string;
  amount: string;
  contribution_date: string;
  payment_method: string;
  reference_number: string;
}

export interface PartnerPortalInvestorFinancialSection {
  summary: Record<string, string | number>;
  positions: ProjectInvestor[];
  contributions: PartnerPortalInvestorContribution[];
  distributions: DistributionLineItem[];
}

export interface PartnerPortalFinancialResponse {
  primary_role: PartnerPortalRole | null;
  client: PartnerPortalClientFinancialSection | null;
  contractor: PartnerPortalContractorFinancialSection | null;
  investor: PartnerPortalInvestorFinancialSection | null;
}

export interface PartnerPortalProjectCompliance {
  project_id: number;
  project_name: string;
  compliance_score: string;
  compliance_status: string;
  compliance_last_evaluated_at: string | null;
}

export interface PartnerPortalVendorCompliance {
  id: number;
  name: string;
  compliance_status: string;
  performance_rating: string;
}

export interface PartnerPortalComplianceResponse {
  summary: {
    expired_documents: number;
    documents_expiring_30_days: number;
    open_risks: number;
    open_issues: number;
  };
  project_compliance: PartnerPortalProjectCompliance[];
  document_expiries: DocumentExpiryRecord[];
  open_risks_list: ProjectRiskRegisterEntry[];
  open_issues_list: ProjectFieldEscalation[];
  vendor_compliance: PartnerPortalVendorCompliance[];
}

export interface PartnerPortalProfileResponse {
  user: {
    id: number;
    full_name: string;
    email: string;
    profile_photo_url: string | null;
  };
  portal_roles: PartnerPortalRole[];
  partner_types: PartnerType[];
  budget_scope: PartnerBudgetScope;
  permissions: PartnerPortalPermissions;
  contact_emails: string[];
  contract_references: string[];
  investment_vehicle_references: string[];
  cases: PartnerOnboardingCaseListItem[];
  entitlements: PartnerEntitlement[];
  legal: {
    agreement_acceptance_required: boolean;
    device_fingerprinting_enabled: boolean;
  };
}

export interface PartnerPortalProfilePhotoResponse {
  detail: string;
  profile_photo_url: string | null;
}

/* ── IAM ─────────────────────────────────────────────── */

export interface UserDirectoryItem {
  id: number;
  profile_id: number;
  full_name: string;
  email: string;
  phone: string;
  job_title: string;
  department_name: string;
  role_name: string;
  user_status: string;
  user_status_display: string;
  last_login: string | null;
  mfa_enabled: boolean;
  identity_type: string;
  identity_type_display: string;
  partner_type: string;
  partner_type_display: string;
  profile_photo: string | null;
  date_joined: string;
}

export interface UserDetailItem extends UserDirectoryItem {
  first_name: string;
  last_name: string;
  assigned_role_id: number | null;
  department_id: number | null;
  reporting_manager_id: number | null;
  reporting_manager_name: string;
  authentication_methods: string[];
  has_completed_onboarding: boolean;
}

export interface UserOverview {
  total: number;
  active: number;
  suspended: number;
  locked: number;
}

export interface UserListResponse {
  count: number;
  results: UserDirectoryItem[];
  overview: UserOverview;
}

export interface InvitationItem {
  id: number;
  email: string;
  status: string;
  status_display: string;
  invited_by_name: string;
  created_at: string;
  token: string;
}

export interface InvitationListResponse {
  count: number;
  results: InvitationItem[];
}

export interface ServiceAccountAPIKey {
  id: number;
  label: string;
  prefix: string;
  scopes: string[];
  is_active: boolean;
  expires_at: string | null;
  last_used_at: string | null;
  created_at: string;
}

export interface ServiceAccountItem {
  id: number;
  name: string;
  description: string;
  owner_name: string;
  owner_id: number | null;
  status: string;
  status_display: string;
  key_count: number;
  created_at: string;
  updated_at: string;
}

export interface ServiceAccountDetail extends ServiceAccountItem {
  api_keys: ServiceAccountAPIKey[];
}

export interface ServiceAccountOverview {
  total: number;
  active: number;
  suspended: number;
  revoked: number;
}

export interface ServiceAccountListResponse {
  count: number;
  results: ServiceAccountItem[];
  overview: ServiceAccountOverview;
}

export interface APIKeyDirectoryItem {
  id: number;
  prefix: string;
  label: string;
  service_account_id: number;
  service_account_name: string;
  scopes: string[];
  is_active: boolean;
  status_display: string;
  expires_at: string | null;
  last_used_at: string | null;
  created_at: string;
}

export interface APIKeyOverview {
  total: number;
  active: number;
  revoked: number;
  expired: number;
}

export interface APIKeyListResponse {
  count: number;
  results: APIKeyDirectoryItem[];
  overview: APIKeyOverview;
}

export interface UserSettingsDepartmentOption {
  id: number;
  name: string;
  division_name: string;
}

export type UserProfileVisibility = "private" | "team" | "organization";

export interface UserSettingsVisibilityOption {
  value: UserProfileVisibility;
  label: string;
}

export interface UserSettingsLanguageOption {
  value: string;
  label: string;
}

export interface UserPrivacyVisibilitySettings {
  profile_visibility: UserProfileVisibility;
  email_visibility: UserProfileVisibility;
  phone_visibility: UserProfileVisibility;
  activity_visibility: UserProfileVisibility;
  online_status_visibility: UserProfileVisibility;
  search_discoverable: boolean;
  visibility_options: UserSettingsVisibilityOption[];
}

export type UserWorkspaceTheme = "light" | "dark" | "system";
export type UserWorkspaceDensity = "compact" | "comfortable";
export type UserWorkspaceSidebarBehavior = "expanded" | "collapsed";
export type UserWorkspaceDashboard = "portfolio_analytics" | "board_metrics";

export interface UserWorkspacePreferenceOption {
  value: string;
  label: string;
}

export interface UserWorkspaceWidgetPreference {
  key: string;
  label: string;
  description: string;
  visible: boolean;
}

export interface UserWorkspacePreferences {
  theme: UserWorkspaceTheme;
  layout_density: UserWorkspaceDensity;
  sidebar_behavior: UserWorkspaceSidebarBehavior;
  default_landing_page: string;
  default_dashboard: UserWorkspaceDashboard;
  widgets: UserWorkspaceWidgetPreference[];
  theme_options: UserWorkspacePreferenceOption[];
  layout_density_options: UserWorkspacePreferenceOption[];
  sidebar_behavior_options: UserWorkspacePreferenceOption[];
  landing_page_options: UserWorkspacePreferenceOption[];
  dashboard_options: UserWorkspacePreferenceOption[];
}

export type UserTaskDefaultView = "list" | "kanban" | "calendar";
export type UserApprovalDelegationRule = "manual_only" | "use_active_delegations" | "auto_when_out_of_office";

export interface UserTaskWorkflowPreferenceOption {
  value: string;
  label: string;
}

export interface UserTaskWorkflowNumericOption {
  value: number;
  label: string;
}

export interface UserTaskWorkflowPreferences {
  default_task_view: UserTaskDefaultView;
  task_reminder_minutes_before: number;
  task_default_due_date_offset_days: number;
  auto_follow_assigned_tasks: boolean;
  auto_subscribe_project_updates: boolean;
  approval_delegation_rule: UserApprovalDelegationRule;
  default_task_view_options: UserTaskWorkflowPreferenceOption[];
  task_reminder_timing_options: UserTaskWorkflowNumericOption[];
  default_due_date_offset_options: UserTaskWorkflowNumericOption[];
  approval_delegation_rule_options: UserTaskWorkflowPreferenceOption[];
  delegations_path: string;
}

export interface UserCalendarWorkingDayOption {
  value: number;
  label: string;
}

export interface UserCalendarSchedulingPreferences {
  working_hours_start: string;
  working_hours_end: string;
  working_days: number[];
  default_meeting_duration_minutes: number;
  meeting_buffer_minutes: number;
  timezone_override: string;
  calendar_sync_google: boolean;
  calendar_sync_outlook: boolean;
  calendar_sync_ical: boolean;
  default_reminder_minutes: number;
  working_day_options: UserCalendarWorkingDayOption[];
  timezone_options: string[];
}

// ---------------------------------------------------------------------------
// Workspace > Calendar (apps.calendar)
// See docs/workspace-calendar-design.md.
// ---------------------------------------------------------------------------

export type CalendarEventKind = "meeting" | "focus" | "out_of_office" | "reminder";
export type CalendarEventVisibility = "private" | "team" | "org";
export type CalendarMyRole = "creator" | "attendee" | "viewer" | null;

export interface CalendarOccurrenceRow {
  event_id: number;
  title: string;
  kind: CalendarEventKind;
  visibility: CalendarEventVisibility;
  creator_id: number;
  team_id: number | null;
  all_day: boolean;
  timezone: string;
  is_recurring: boolean;
  original_start: string;
  starts_at: string;
  ends_at: string | null;
  is_override: boolean;
  is_cancelled: boolean;
  my_role: CalendarMyRole;
}

export interface CalendarEventListItem {
  id: number;
  title: string;
  kind: CalendarEventKind;
  visibility: CalendarEventVisibility;
  creator: number;
  team: number | null;
  starts_at: string;
  ends_at: string | null;
  all_day: boolean;
  timezone: string;
  recurrence_rule: string;
  is_cancelled: boolean;
  my_role: CalendarMyRole;
}

export interface CalendarEventCreator {
  id: number;
  name: string;
  email: string;
  initials: string;
}

export interface CalendarEventDetail {
  id: number;
  title: string;
  description: string;
  location: string;
  meeting_link: string;
  external_attendee_emails: string[];
  kind: CalendarEventKind;
  visibility: CalendarEventVisibility;
  team: number | null;
  starts_at: string;
  ends_at: string | null;
  all_day: boolean;
  timezone: string;
  recurrence_rule: string;
  recurrence_end: string | null;
  reminder_minutes_before: number | null;
  is_cancelled: boolean;
  creator: CalendarEventCreator;
  created_at: string;
  updated_at: string;
  my_role: CalendarMyRole;
  attendees_count: number;
  overrides_count: number;
  has_external_attendees: boolean;
}

export interface CalendarEventCreatePayload {
  title: string;
  description?: string;
  location?: string;
  meeting_link?: string;
  external_attendee_emails?: string[];
  kind: CalendarEventKind;
  visibility: CalendarEventVisibility;
  team?: number | null;
  starts_at: string;
  ends_at?: string | null;
  all_day?: boolean;
  timezone: string;
  recurrence_rule?: string;
  reminder_minutes_before?: number | null;
}

export interface CalendarEventAttendeeUser {
  id: number;
  name: string;
  email: string;
  initials: string;
}

export interface CalendarEventAttendee {
  id: number;
  user: CalendarEventAttendeeUser;
  invited_at: string;
}

export interface CalendarEventOccurrenceOverride {
  id: number;
  event: number;
  original_start: string;
  is_cancelled: boolean;
  starts_at: string | null;
  ends_at: string | null;
  title: string;
  location: string;
  description: string;
  is_orphan: boolean;
  created_at: string;
  updated_at: string;
}

export interface CalendarMeetingsOverlayRow {
  source: "meeting";
  id: number;
  title: string;
  kind: "meeting";
  starts_at: string;
  ends_at: string | null;
  timezone: string;
  location: string;
  meeting_link: string;
  meeting_type: string;
  status: string;
  project_id: number | null;
  project_name: string | null;
  edit_url: string;
  edit_in_app: string;
}

export interface CalendarIcalRotateResponse {
  token: string;
  feed_url_path: string;
}

// ---------------------------------------------------------------------------
// Workspace > Internal Tasks (apps.internal_tasks)
// See docs/workspace-internal-tasks-design.md.
// ---------------------------------------------------------------------------

export type InternalTaskStatus = "todo" | "in_progress" | "blocked" | "done";
export type InternalTaskPriority = "low" | "medium" | "high" | "urgent";
export type InternalTaskVisibility = "private" | "team" | "org";
export type InternalTaskRole = "creator" | "assignee" | "viewer" | null;

export interface InternalTaskChecklistItem {
  label: string;
  checked: boolean;
}

export interface InternalTaskListItem {
  id: number;
  title: string;
  status: InternalTaskStatus;
  priority: InternalTaskPriority;
  visibility: InternalTaskVisibility;
  assignee_id: number | null;
  team_id: number | null;
  due_date: string | null;
  overdue: boolean;
  tags: string[];
  comments_count: number;
  my_role: InternalTaskRole;
  created_at: string;
  updated_at: string;
}

export interface InternalTaskUserMini {
  id: number;
  name: string;
  email: string;
  initials: string;
}

export interface InternalTaskDetail {
  id: number;
  title: string;
  description: string;
  status: InternalTaskStatus;
  priority: InternalTaskPriority;
  visibility: InternalTaskVisibility;
  creator: InternalTaskUserMini;
  assignee: InternalTaskUserMini | null;
  team: number | null;
  due_date: string | null;
  completed_at: string | null;
  overdue: boolean;
  tags: string[];
  checklist_items: InternalTaskChecklistItem[];
  comments_count: number;
  my_role: InternalTaskRole;
  created_at: string;
  updated_at: string;
}

export interface InternalTaskCreatePayload {
  title: string;
  description?: string;
  status?: InternalTaskStatus;
  priority?: InternalTaskPriority;
  visibility?: InternalTaskVisibility;
  assignee?: number | null;
  team?: number | null;
  due_date?: string | null;
  tags?: string[];
  checklist_items?: InternalTaskChecklistItem[];
}

export interface InternalTaskComment {
  id: number;
  body: string;
  author: InternalTaskUserMini;
  mentions: number[];
  created_at: string;
  updated_at: string;
}

export type InternalTaskOverlaySource = "project_task" | "crm_follow_up";

export interface InternalTaskOverlayRow {
  source: InternalTaskOverlaySource;
  id: number;
  title: string;
  status: InternalTaskStatus;
  priority: InternalTaskPriority;
  due_date: string | null;
  assignee_id: number | null;
  team_id: number | null;
  project_id?: number | null;
  project_name?: string | null;
  lead_id?: number | null;
  lead_name?: string | null;
  edit_url: string;
  edit_in_app: string;
  unmapped_source_status: string | null;
}

export interface InternalTaskTagBucket {
  tag: string;
  count: number;
}

export type UserDataExportFormat = "pdf" | "excel" | "csv";

export interface UserDataExportPreferenceOption {
  value: UserDataExportFormat;
  label: string;
}

export interface UserDataSavedView {
  id: string;
  name: string;
  filters: Record<string, unknown>;
  column_visibility: Record<string, boolean>;
  rows_per_page: number | null;
}

export interface UserDataExportPreferences {
  default_export_format: UserDataExportFormat;
  default_report_filters: Record<string, unknown>;
  rows_per_page: number;
  column_visibility: Record<string, boolean>;
  saved_views: UserDataSavedView[];
  export_format_options: UserDataExportPreferenceOption[];
  rows_per_page_options: number[];
}

export type UserIntegrationProvider =
  | "google_drive"
  | "dropbox"
  | "slack"
  | "teams"
  | "zapier"
  | "webhooks";

export type UserIntegrationStatus = "connected" | "revoked" | "error" | "disconnected";

export interface UserIntegrationConnection {
  provider: UserIntegrationProvider;
  provider_display: string;
  status: UserIntegrationStatus;
  status_display: string;
  account_label: string;
  webhook_url: string;
  connected_at: string | null;
  revoked_at: string | null;
  last_token_refresh_at: string | null;
  token_expires_at: string | null;
  supports_token_refresh: boolean;
  supports_webhook_url: boolean;
  is_connected: boolean;
}

export interface UserIntegrationsSettings {
  integrations: UserIntegrationConnection[];
  detail?: string;
}

export type UserAccessibilityFontSize = "small" | "medium" | "large";

export interface UserAccessibilityPreferenceOption {
  value: UserAccessibilityFontSize;
  label: string;
}

export interface UserAccessibilityPreferences {
  font_size: UserAccessibilityFontSize;
  high_contrast_mode: boolean;
  reduced_motion: boolean;
  screen_reader_support: boolean;
  keyboard_navigation: boolean;
  font_size_options: UserAccessibilityPreferenceOption[];
}

export type UserNotificationChannelKey = "in_app" | "email" | "push" | "sms";
export type UserNotificationFrequencyKey = "instant" | "hourly_digest" | "daily_digest" | "weekly_summary";

export interface UserNotificationOption {
  key: UserNotificationChannelKey | UserNotificationFrequencyKey;
  label: string;
}

export interface UserNotificationCategoryPreference {
  key: string;
  label: string;
  enabled: boolean;
  channels: UserNotificationChannelKey[];
  frequency: UserNotificationFrequencyKey;
}

export interface UserNotificationPreferences {
  channel_in_app_enabled: boolean;
  channel_email_enabled: boolean;
  channel_push_enabled: boolean;
  channel_sms_enabled: boolean;
  channel_options: UserNotificationOption[];
  frequency_options: UserNotificationOption[];
  categories: UserNotificationCategoryPreference[];
}

export interface UserSettingsProfile {
  id: number;
  profile_photo_url: string | null;
  full_name: string;
  display_name: string;
  preferred_display_name: string;
  job_title: string;
  department_id: number | null;
  department_name: string;
  department_options: UserSettingsDepartmentOption[];
  organization_name: string;
  business_unit: string;
  employee_id: string;
  bio: string;
  email: string;
  phone: string;
  secondary_phone: string;
  office_location: string;
  timezone: string;
  timezone_options: string[];
  profile_visibility: UserProfileVisibility;
  profile_visibility_options: UserSettingsVisibilityOption[];
  approval_signature: string;
  default_language: string;
  language_options: UserSettingsLanguageOption[];
}

export interface UserProfilePhotoResponse {
  detail: string;
  profile_photo_url: string | null;
}

export interface UserLinkedAuthProvider {
  id: number;
  provider: string;
  provider_display: string;
  email: string;
  connected_at: string;
  last_login_at: string | null;
}

export interface UserAccountSession {
  sid: string;
  auth_provider: string;
  auth_provider_display: string;
  ip_address: string | null;
  device_label: string;
  user_agent: string;
  created_at: string;
  last_seen_at: string;
  is_current: boolean;
}

export interface UserSecurityLogItem {
  id: number;
  event_type: string;
  event_type_display: string;
  status: string;
  status_display: string;
  provider: string;
  ip_address: string | null;
  device_label: string;
  user_agent: string;
  detail: string;
  occurred_at: string;
}

export interface UserDeviceHistoryItem {
  device_label: string;
  ip_address: string | null;
  user_agent: string;
  first_seen_at: string;
  last_seen_at: string;
  auth_provider: string;
  auth_provider_display: string;
}

export interface UserAccountSecurity {
  username: string;
  email: string;
  mfa_enabled: boolean;
  passkey_enabled: boolean;
  mfa_policy: string;
  mfa_policy_display: string;
  linked_providers: UserLinkedAuthProvider[];
  active_sessions: UserAccountSession[];
  login_history: UserSecurityLogItem[];
  failed_login_attempts: UserSecurityLogItem[];
  device_history: UserDeviceHistoryItem[];
}

/* ── HR — Organization Structure ─────────────────────── */

export type HREmploymentType = "full_time" | "part_time" | "contract" | "temporary" | "intern";
export type HRPositionLevel = "intern" | "junior" | "mid" | "senior" | "lead" | "manager" | "director" | "vp" | "c_suite";
export type HRPositionStatus = "active" | "frozen" | "abolished";
export type HRPositionSlotStatus = "vacant" | "filled" | "proposed";

export interface HRPositionRoleListItem {
  id: number;
  name: string;
  grade: string;
  code: string;
  position_count: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface HRPositionRole extends HRPositionRoleListItem {
  description: string;
  requirements: string;
  key_responsibilities: string;
  hard_skills: string[];
  soft_skills: string[];
  kpi_metrics: string[];
}
export type HRBudgetStatus = "draft" | "approved" | "frozen";
export type HRPositionBudgetSource = "corporate_overhead" | "project_funding";
export type HRVacancyStatus = "open" | "on_hold" | "filled" | "cancelled";
export type HRVacancyPriority = "low" | "medium" | "high" | "urgent";
export type HRTeamType = "permanent" | "project_based";
export type HRTeamMemberAvailability = "active" | "on_leave" | "reassigned";
export type HRTeamWorkloadHeat = "low" | "medium" | "high" | "critical";
export type HRTeamMilestoneHealth = "on_track" | "at_risk" | "delayed" | "no_milestones";

export interface HRTeamListItem {
  id: number;
  name: string;
  code: string;
  department: number;
  department_name: string;
  business_unit_id: number;
  business_unit_name: string;
  team_type: HRTeamType;
  team_type_display: string;
  lead: number | null;
  lead_name: string | null;
  member_count: number;
  is_active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface HRTeam extends HRTeamListItem {
  description: string;
  member_roster: HRTeamMemberRosterItem[];
  operational_performance: HRTeamOperationalPerformance;
  automation_triggers: HRTeamAutomationTriggers;
}

export interface HRTeamMemberPickerEmployee {
  user_id: number;
  employee_record_id: number;
  employee_id: string;
  full_name: string;
  job_title: string;
  department_name: string | null;
  employment_status: string;
  is_locked: boolean;
  is_picker_managed: boolean;
}

export interface HRTeamMemberPickerPayload {
  team_id: number;
  team_name: string;
  picker_position_id: number;
  assigned: HRTeamMemberPickerEmployee[];
  available: HRTeamMemberPickerEmployee[];
  locked_assigned_count: number;
  picker_assigned_count: number;
}

export interface HRTeamMemberRosterItem {
  user_id: number;
  full_name: string;
  profile_photo_url: string | null;
  role_title: string;
  role_titles: string[];
  home_department_name: string;
  is_cross_functional: boolean;
  availability_status: HRTeamMemberAvailability;
  availability_label: string;
}

export interface HRTeamActiveProjectLink {
  project_id: number;
  project_name: string;
  project_status: string;
  project_href: string;
  task_count: number;
  open_task_count: number;
  overdue_open_task_count: number;
  booked_hours: number;
}

export interface HRTeamWorkloadSummary {
  booked_hours: number;
  capacity_hours: number;
  workload_percent: number;
  active_member_count: number;
  heat_level: HRTeamWorkloadHeat;
  heat_label: string;
  period_label: string;
  formula: string;
}

export interface HRTeamMilestoneProgress {
  health: HRTeamMilestoneHealth;
  health_label: string;
  total_milestones: number;
  completed_milestones: number;
  due_soon_milestones: number;
  overdue_milestones: number;
  completion_percent: number;
  on_time_completion_percent: number;
}

export interface HRTeamOperationalPerformance {
  active_project_links: HRTeamActiveProjectLink[];
  workload: HRTeamWorkloadSummary;
  milestone_progress: HRTeamMilestoneProgress;
}

export type HRTeamAutomationTriggerStatus = "pending" | "triggered" | "not_applicable";

export interface HRTeamBudgetAllocation {
  project_id: number;
  project_name: string;
  project_href: string;
  budget_id: number | null;
  budget_name: string | null;
  allocated_billable_hours: number;
}

export interface HRTeamTimesheetTrigger {
  feature: string;
  data_field: string;
  total_hours_logged: number;
  billable_hours: number;
  project_budget_allocations: HRTeamBudgetAllocation[];
  trigger_status: HRTeamAutomationTriggerStatus;
  trigger_message: string;
  trigger_automation: string;
}

export interface HRTeamExpenseTrigger {
  feature: string;
  data_field: string;
  team_petty_cash: number;
  reimbursement_item_count: number;
  trigger_status: HRTeamAutomationTriggerStatus;
  trigger_message: string;
  trigger_automation: string;
}

export interface HRTeamKPITrigger {
  feature: string;
  data_field: string;
  team_success_rate: number;
  high_performance_threshold: number;
  high_performance_tag: boolean;
  trigger_status: HRTeamAutomationTriggerStatus;
  trigger_message: string;
  trigger_automation: string;
}

export interface HRTeamAutomationTriggers {
  timesheets: HRTeamTimesheetTrigger;
  expense_claims: HRTeamExpenseTrigger;
  kpis: HRTeamKPITrigger;
}

export interface HRPositionListItem {
  id: number;
  role: number | null;
  role_name: string | null;
  role_grade: string | null;
  role_code: string | null;
  salary_structure: number | null;
  salary_structure_name: string | null;
  salary_range_min: string | null;
  salary_range_max: string | null;
  salary_currency: string | null;
  salary_band_link: string | null;
  title: string;
  code: string;
  department: number;
  department_name: string;
  team: number | null;
  team_name: string | null;
  reports_to: number | null;
  reports_to_title: string | null;
  direct_report_count: number;
  cost_center: number | null;
  cost_center_code: string | null;
  employment_type: HREmploymentType;
  level: HRPositionLevel;
  status: HRPositionStatus;
  slot_status: HRPositionSlotStatus;
  criticality_score: number;
  vacant_since: string | null;
  vacancy_alert_sent_at: string | null;
  headcount_budget: number;
  filled_count: number;
  vacancy_count: number;
  active_requisition_id: number | null;
  active_requisition_status: string | null;
  budget_guard_active: boolean;
  vacancy_days_open: number;
  succession_alert_due: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface HRPosition extends HRPositionListItem {
  description: string;
  requirements: string;
}

export interface HRPositionAssignmentListItem {
  id: number;
  user: number;
  user_name: string;
  position: number;
  position_title: string;
  position_code: string;
  start_date: string;
  end_date: string | null;
  is_primary: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface HRPositionAssignment extends HRPositionAssignmentListItem {
  notes: string;
}

export interface HRPositionBudgetListItem {
  id: number;
  department: number;
  department_name: string;
  position: number | null;
  position_title: string | null;
  fiscal_period_label: string;
  fiscal_year: number;
  budget_source: HRPositionBudgetSource;
  budget_source_display: string;
  currency: string;
  fte: string;
  statutory_benefits_rate: string;
  allowances_rate: string;
  local_tax_rate: string;
  insurance_rate: string;
  base_salary_min: string | null;
  base_salary_mid: string | null;
  base_salary_max: string | null;
  salary_band_currency: string;
  burden_multiplier: string | null;
  statutory_benefits_cost: string | null;
  allowances_cost: string | null;
  local_tax_cost: string | null;
  insurance_cost: string | null;
  fully_burdened_cost: string | null;
  approved_headcount: number;
  filled_headcount: number;
  budget_amount: string;
  status: HRBudgetStatus;
  variance: number;
  created_at: string;
  updated_at: string;
}

export interface HRPositionBudget extends HRPositionBudgetListItem {
  notes: string;
  approved_by: number | null;
  approved_by_name: string | null;
  approved_at: string | null;
}

export type HRPositionBudgetRevisionStatus = "pending_approval" | "approved" | "rejected" | "cancelled";

export interface HRPositionBudgetRevisionListItem {
  id: number;
  budget: number;
  revision_number: number;
  status: HRPositionBudgetRevisionStatus;
  reason: string;
  budget_department_name: string;
  budget_position_title: string | null;
  requested_by: number | null;
  requested_by_name: string | null;
  reviewed_by: number | null;
  reviewed_by_name: string | null;
  reviewed_at: string | null;
  review_notes: string;
  created_at: string;
  updated_at: string;
}

export interface HRPositionBudgetRevision extends HRPositionBudgetRevisionListItem {
  proposed_changes: Record<string, unknown>;
  snapshot_before: Record<string, unknown>;
}

export interface HRPositionBudgetWhatIfResponse {
  fiscal_year: number | null;
  department_id: number | null;
  position_id: number | null;
  currency: string | null;
  assumptions: {
    additional_headcount: number;
    per_head_cost: string;
    project_revenue: string | null;
    other_project_costs: string;
  };
  baseline: {
    budgeted: string;
    committed: string;
    pipeline: string;
    variance: string;
    project_margin_percent: number | null;
  };
  scenario: {
    additional_cost: string;
    committed: string;
    variance: string;
    project_margin_percent: number | null;
    margin_delta_percent: number | null;
  };
}

export interface HRVacancyListItem {
  id: number;
  title: string;
  position: number;
  position_title: string;
  position_code: string;
  department_name: string;
  status: HRVacancyStatus;
  priority: HRVacancyPriority;
  hiring_manager: number | null;
  hiring_manager_name: string | null;
  opened_date: string;
  target_fill_date: string | null;
  filled_date: string | null;
  days_open: number | null;
  created_at: string;
  updated_at: string;
}

export interface HRVacancy extends HRVacancyListItem {
  approved_by: number | null;
  approved_by_name: string | null;
  filled_by: number | null;
  filled_by_name: string | null;
  reason: string;
  notes: string;
}

export interface OrgChartAssignedUser {
  id: number;
  name: string;
  title: string;
  department_name: string;
  direct_report_count: number;
  email: string;
  phone: string;
  office_location: string;
  employment_type: HREmploymentType;
  salary_band: string | null;
  is_primary: boolean;
  is_acting: boolean;
  acting_roles: string[];
  project_assignment_count: number;
  project_assignments: OrgChartProjectAssignment[];
}

export interface OrgChartProjectAssignment {
  project_id: number;
  project_name: string;
  task_id: number;
  task_name: string;
  status: ProjectTaskStatus;
  due_date: string | null;
}

export interface OrgChartPosition {
  id: number;
  title: string;
  code: string;
  level: HRPositionLevel;
  employment_type: HREmploymentType;
  is_vacant: boolean;
  assigned_users: OrgChartAssignedUser[];
}

export interface OrgChartTeam {
  id: number;
  name: string;
  code: string;
  lead: number | null;
  lead_name: string | null;
  positions: OrgChartPosition[];
}

export interface OrgChartDepartment {
  id: number;
  name: string;
  code: string;
  head_name: string | null;
  teams: OrgChartTeam[];
  positions: OrgChartPosition[];
}

export interface OrgChartDivision {
  id: number;
  name: string;
  code: string;
  head_name: string | null;
  departments: OrgChartDepartment[];
}

export interface ReportingLineUser {
  id: number;
  full_name: string;
  job_title: string;
  department: string | null;
  reports_to: number | null;
  direct_report_count: number;
}

export interface HeadcountSummaryDepartment {
  department_id: number;
  department_name: string;
  approved_headcount: number;
  filled_headcount: number;
  vacant: number;
  budget_amount: string;
}

export interface HeadcountBudgetVsActual {
  budgeted: string;
  committed: string;
  pipeline: string;
  variance: string;
  merit_pool: string;
  variance_status: "buffer" | "over_budget";
}

export interface HeadcountUtilizationHeatmapItem {
  budgeted: string;
  committed: string;
  pipeline: string;
  utilization_ratio: number;
  utilization_percent: number;
  heat_status: "green" | "yellow" | "red";
  heat_label: string;
}

export interface HeadcountDepartmentHeatmapItem extends HeadcountUtilizationHeatmapItem {
  department_id: number;
  department_name: string;
}

export interface HeadcountProjectHeatmapItem extends HeadcountUtilizationHeatmapItem {
  key: string;
  label: string;
}

export interface HeadcountBusinessUnitGuardrail {
  division_id: number;
  division_name: string;
  budget_cap: string;
  committed: string;
  pipeline: string;
  variance: string;
  unallocated_budget: string;
  hiring_freeze: boolean;
}

export interface HeadcountSummaryResponse {
  fiscal_year: number | null;
  currency: string | null;
  departments: HeadcountSummaryDepartment[];
  totals: {
    approved_headcount: number;
    filled_headcount: number;
    vacant: number;
    budget_amount: string;
    open_vacancies: number;
  };
  budget_vs_actual: HeadcountBudgetVsActual;
  utilization_heatmap: {
    departments: HeadcountDepartmentHeatmapItem[];
    projects: HeadcountProjectHeatmapItem[];
  };
  business_units: HeadcountBusinessUnitGuardrail[];
}

export interface PositionBudgetGuardrailsResponse {
  business_units: HeadcountBusinessUnitGuardrail[];
  all_frozen: boolean;
}

// ---------------------------------------------------------------------------
// HR — Employee Directory
// ---------------------------------------------------------------------------

export interface EmployeeChoice {
  id: number;
  full_name: string;
  employee_id: string;
}

export interface EmployeeDirectoryItem {
  id: number;
  user_id: number;
  full_name: string;
  email: string;
  employee_id: string;
  job_title: string;
  department_name: string | null;
  position_title: string | null;
  employment_type: string | null;
  manager_name: string | null;
  office_location: string;
  profile_photo: string | null;
  user_status: string;
  employment_status: string;
  hire_date: string | null;
  contract_type: string;
  created_at: string;
  updated_at: string;
}

export interface EmployeeRecord {
  id: number;
  user: number;
  hire_date: string | null;
  probation_end_date: string | null;
  contract_start_date: string | null;
  contract_end_date: string | null;
  contract_type: string;
  employment_status: string;
  termination_date: string | null;
  termination_reason: string;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface EmergencyContact {
  id: number;
  user: number;
  user_name: string;
  name: string;
  relationship: string;
  phone: string;
  secondary_phone: string;
  email: string;
  address: string;
  is_primary: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface IdentificationDocument {
  id: number;
  user: number;
  user_name: string;
  document_type: string;
  document_number: string;
  issuing_authority: string;
  issuing_country: string;
  issue_date: string | null;
  expiry_date: string | null;
  file: string | null;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface CompensationRecord {
  id: number;
  user: number;
  user_name: string;
  effective_date: string;
  end_date: string | null;
  base_salary: string;
  currency: string;
  pay_frequency: string;
  allowances: string;
  bonus: string;
  total_package: string;
  status: string;
  approved_by: number | null;
  approved_by_name: string | null;
  approved_at: string | null;
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface HRDocument {
  id: number;
  user: number;
  user_name: string;
  title: string;
  category: string;
  file: string;
  file_size: number;
  description: string;
  uploaded_by: number | null;
  uploaded_by_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface EmploymentHistoryEntry {
  id: number;
  position_title: string;
  position_code: string;
  department_name: string;
  start_date: string;
  end_date: string | null;
  is_primary: boolean;
  is_active: boolean;
}

export interface ContactDirectoryItem {
  user_id: number;
  full_name: string;
  department_name: string | null;
  phone: string;
  email: string;
  office_location: string;
}

// ---------------------------------------------------------------------------
// HR — Recruitment & Hiring
// ---------------------------------------------------------------------------

export type RequisitionStatus = "draft" | "pending_approval" | "approved" | "rejected" | "cancelled" | "filled";
export type RequisitionPriority = "low" | "medium" | "high" | "urgent";
export type ListingStatus = "draft" | "active" | "closed" | "archived";
export type SalaryDisplay = "hidden" | "range" | "exact";
export type CandidateStage = "applied" | "screening" | "shortlisted" | "interviewing" | "evaluated" | "offer_pending" | "hired" | "rejected" | "withdrawn";
export type InterviewStatus = "scheduled" | "completed" | "cancelled" | "no_show";
export type EvaluationRecommendation = "strongly_hire" | "hire" | "maybe" | "no_hire" | "strongly_no_hire";
export type OfferStatus = "draft" | "pending_approval" | "approved" | "extended" | "accepted" | "rejected" | "withdrawn" | "expired";

export interface JobRequisitionListItem {
  id: number;
  title: string;
  position: number | null;
  position_title: string | null;
  department: number | null;
  department_name: string | null;
  requisition_type: string;
  headcount_requested: number;
  priority: RequisitionPriority;
  status: RequisitionStatus;
  requested_by: number;
  requested_by_name: string;
  salary_range_min: string | null;
  salary_range_max: string | null;
  currency: string;
  target_start_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface JobRequisition extends JobRequisitionListItem {
  vacancy: number | null;
  justification: string;
  approved_by: number | null;
  approved_by_name: string | null;
  approved_at: string | null;
  notes: string;
}

export interface JobListingListItem {
  id: number;
  requisition: number;
  requisition_title: string | null;
  title: string;
  location: string;
  employment_type: string;
  is_internal: boolean;
  is_external: boolean;
  posted_date: string | null;
  closing_date: string | null;
  status: ListingStatus;
  candidate_count: number;
  created_at: string;
  updated_at: string;
}

export interface JobListing extends JobListingListItem {
  description: string;
  requirements: string;
  salary_display: SalaryDisplay;
  salary_min: string | null;
  salary_max: string | null;
  currency: string;
  posted_by: number | null;
  posted_by_name: string | null;
  notes: string;
}

export interface CandidateListItem {
  id: number;
  full_name: string;
  email: string;
  phone: string;
  job_listing: number | null;
  listing_title: string | null;
  job_requisition: number | null;
  requisition_title: string | null;
  source: string;
  stage: CandidateStage;
  current_title: string;
  current_employer: string;
  applied_date: string;
  interview_count: number;
  evaluation_count: number;
  avg_rating: number | null;
  created_at: string;
  updated_at: string;
}

export interface Candidate extends CandidateListItem {
  first_name: string;
  last_name: string;
  resume: string | null;
  expected_salary: string | null;
  currency: string;
  referred_by: number | null;
  referred_by_name: string | null;
  rejection_reason: string;
  notes: string;
}

export interface InterviewListItem {
  id: number;
  candidate: number;
  candidate_name: string;
  interview_type: string;
  interviewer: number;
  interviewer_name: string;
  scheduled_date: string;
  scheduled_time: string;
  duration_minutes: number;
  location: string;
  meeting_link: string;
  status: InterviewStatus;
  has_evaluation: boolean;
  created_at: string;
  updated_at: string;
}

export interface Interview extends InterviewListItem {
  notes: string;
}

export interface CandidateEvaluationListItem {
  id: number;
  candidate: number;
  candidate_name: string;
  interview: number | null;
  evaluator: number;
  evaluator_name: string;
  overall_rating: number;
  recommendation: EvaluationRecommendation;
  evaluated_at: string;
  created_at: string;
  updated_at: string;
}

export interface CandidateEvaluation extends CandidateEvaluationListItem {
  strengths: string;
  concerns: string;
  notes: string;
}

export interface JobOfferListItem {
  id: number;
  candidate: number;
  candidate_name: string;
  requisition: number | null;
  requisition_title: string | null;
  position: number | null;
  position_title: string | null;
  offered_salary: string;
  currency: string;
  start_date: string | null;
  expiry_date: string | null;
  status: OfferStatus;
  cfo_override_approved: boolean;
  created_at: string;
  updated_at: string;
}

export interface JobOffer extends JobOfferListItem {
  offer_letter: string | null;
  terms: string;
  approved_by: number | null;
  approved_by_name: string | null;
  approved_at: string | null;
  cfo_override_by: number | null;
  cfo_override_by_name: string | null;
  cfo_override_at: string | null;
  cfo_override_reason: string;
  extended_at: string | null;
  responded_at: string | null;
  response_notes: string;
  notes: string;
}

export interface HiringWorkflowStep {
  id: number;
  sequence: number;
  name: string;
  decision: string;
  decided_by_name: string | null;
  decided_at: string | null;
  comments: string;
}

export interface HiringWorkflowItem {
  id: number;
  object_type: "requisition" | "offer";
  object_id: number;
  object_label: string;
  template_name: string;
  state: string;
  submitted_by_name: string | null;
  submitted_at: string | null;
  completed_at: string | null;
  steps: HiringWorkflowStep[];
}

/* ── HR — Onboarding ─────────────────────────────────── */

export type OnboardingTaskCategory = "documentation" | "training" | "access" | "introduction" | "compliance" | "other";
export type OnboardingTaskStatus = "pending" | "in_progress" | "completed" | "skipped";
export type DocumentCollectionStatus = "pending" | "submitted" | "verified" | "rejected";
export type EquipmentCategory = "laptop" | "phone" | "access_card" | "desk" | "vehicle" | "uniform" | "other";
export type EquipmentStatus = "pending" | "allocated" | "returned" | "lost";
export type OrientationCategory = "company_overview" | "team_introduction" | "system_training" | "safety_training" | "policy_review" | "facility_tour";
export type ProbationStatus = "in_progress" | "passed" | "failed" | "extended";
export type ProbationRecommendation = "confirm" | "extend" | "terminate";

export interface OnboardingTemplateListItem {
  id: number;
  name: string;
  description: string;
  department: number | null;
  department_name: string | null;
  position: number | null;
  position_title: string | null;
  is_active: boolean;
  task_count: number;
  created_by: number | null;
  created_by_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface OnboardingTaskListItem {
  id: number;
  employee: number;
  employee_name: string;
  template: number | null;
  template_name: string | null;
  title: string;
  description: string;
  category: OnboardingTaskCategory;
  assigned_to: number | null;
  assigned_to_name: string | null;
  status: OnboardingTaskStatus;
  is_required: boolean;
  due_date: string | null;
  completed_date: string | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentCollectionListItem {
  id: number;
  employee: number;
  employee_name: string;
  document_name: string;
  description: string;
  status: DocumentCollectionStatus;
  due_date: string | null;
  submitted_date: string | null;
  verified_by: number | null;
  verified_by_name: string | null;
  verified_date: string | null;
  rejection_reason: string;
  created_at: string;
  updated_at: string;
}

export interface EquipmentAllocationListItem {
  id: number;
  employee: number;
  employee_name: string;
  item_name: string;
  description: string;
  category: EquipmentCategory;
  serial_number: string;
  asset_tag: string;
  status: EquipmentStatus;
  allocated_date: string | null;
  return_date: string | null;
  allocated_by: number | null;
  allocated_by_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface OrientationChecklistListItem {
  id: number;
  employee: number;
  employee_name: string;
  title: string;
  description: string;
  category: OrientationCategory;
  is_completed: boolean;
  completed_date: string | null;
  completed_by: number | null;
  completed_by_name: string | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface ProbationRecordListItem {
  id: number;
  employee: number;
  employee_name: string;
  start_date: string;
  end_date: string;
  extended_end_date: string | null;
  status: ProbationStatus;
  review_date: string | null;
  next_review_date: string | null;
  reviewer: number | null;
  reviewer_name: string | null;
  performance_rating: number | null;
  recommendation: ProbationRecommendation | "";
  created_at: string;
  updated_at: string;
}

export interface ProbationRecord extends ProbationRecordListItem {
  notes: string;
  outcome_notes: string;
}

/* ── HR — Performance Management ─────────────────────── */

export type PerformanceGoalType = "okr" | "kpi" | "project" | "development";
export type PerformanceGoalStatus = "draft" | "active" | "completed" | "cancelled";
export type PerformanceGoalPriority = "low" | "medium" | "high" | "critical";
export type PerformanceReviewType = "annual" | "semi_annual" | "quarterly" | "probation";
export type PerformanceReviewStatus = "draft" | "in_progress" | "submitted" | "acknowledged";
export type FeedbackType = "praise" | "constructive" | "suggestion" | "concern";
export type FeedbackVisibility = "private" | "manager" | "public";
export type PeerReviewStatus = "pending" | "submitted" | "declined";
export type PIPStatus = "draft" | "active" | "completed" | "extended" | "terminated";
export type PIPOutcome = "improved" | "no_improvement" | "partial" | "terminated";

export interface PerformanceGoalListItem {
  id: number;
  employee: number;
  employee_name: string;
  title: string;
  goal_type: PerformanceGoalType;
  status: PerformanceGoalStatus;
  priority: PerformanceGoalPriority;
  target_value: string;
  current_value: string;
  unit: string;
  weight: string;
  start_date: string | null;
  due_date: string | null;
  completed_date: string | null;
  progress: number;
  parent_goal: number | null;
  created_at: string;
  updated_at: string;
}

export interface PerformanceGoal extends PerformanceGoalListItem {
  description: string;
  notes: string;
}

export interface PerformanceReviewListItem {
  id: number;
  employee: number;
  employee_name: string;
  reviewer: number;
  reviewer_name: string;
  review_type: PerformanceReviewType;
  review_period_start: string;
  review_period_end: string;
  status: PerformanceReviewStatus;
  overall_rating: number | null;
  submitted_at: string | null;
  acknowledged_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PerformanceReview extends PerformanceReviewListItem {
  strengths: string;
  areas_for_improvement: string;
  goals_summary: string;
  employee_comments: string;
  reviewer_comments: string;
  notes: string;
}

export interface ContinuousFeedbackListItem {
  id: number;
  employee: number;
  employee_name: string;
  given_by: number;
  given_by_name: string;
  feedback_type: FeedbackType;
  visibility: FeedbackVisibility;
  subject: string;
  is_anonymous: boolean;
  created_at: string;
  updated_at: string;
}

export interface ContinuousFeedback extends ContinuousFeedbackListItem {
  content: string;
}

export interface ManagerEvaluationListItem {
  id: number;
  employee: number;
  employee_name: string;
  review: number | null;
  evaluator: number;
  evaluator_name: string;
  evaluation_date: string;
  overall_rating: number;
  leadership_rating: number | null;
  communication_rating: number | null;
  technical_rating: number | null;
  teamwork_rating: number | null;
  created_at: string;
  updated_at: string;
}

export interface ManagerEvaluation extends ManagerEvaluationListItem {
  strengths: string;
  areas_for_improvement: string;
  goals_for_next_period: string;
  comments: string;
}

export interface PeerReviewListItem {
  id: number;
  employee: number;
  employee_name: string;
  reviewer: number;
  reviewer_name: string;
  review: number | null;
  status: PeerReviewStatus;
  overall_rating: number | null;
  collaboration_rating: number | null;
  communication_rating: number | null;
  is_anonymous: boolean;
  submitted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PeerReview extends PeerReviewListItem {
  strengths: string;
  areas_for_improvement: string;
  comments: string;
}

export interface PIPListItem {
  id: number;
  employee: number;
  employee_name: string;
  created_by: number;
  created_by_name: string;
  title: string;
  start_date: string;
  end_date: string;
  extended_end_date: string | null;
  status: PIPStatus;
  outcome: PIPOutcome | "";
  created_at: string;
  updated_at: string;
}

export interface PIP extends PIPListItem {
  reason: string;
  objectives: string;
  support_provided: string;
  success_criteria: string;
  outcome_notes: string;
  review_dates: string;
  notes: string;
}

export type SupportTicketCategory =
  | "access"
  | "billing"
  | "technical"
  | "workflow"
  | "account"
  | "complaint"
  | "request"
  | "other";

export type SupportTicketPriority = "low" | "medium" | "high" | "critical";
export type SupportTicketStatus =
  | "open"
  | "in_progress"
  | "pending_requester"
  | "escalated"
  | "resolved"
  | "closed";

export interface SupportDeskBreakdownItem {
  key: string;
  label: string;
  count: number;
}

export interface SupportDeskAgentWorkloadItem {
  agent_id: number;
  agent_name: string;
  active_tickets: number;
  sla_breaches: number;
}

export interface SupportDeskLookupUserOption {
  id: number;
  label: string;
  email: string;
}

export interface SupportDeskLookupDepartmentOption {
  id: number;
  name: string;
}

export interface SupportDeskLookupCustomerOption {
  id: number;
  label: string;
  email: string;
  phone: string;
  support_ticketing_enabled: boolean;
}

export interface SupportDeskLookupContactAccountOption {
  id: number;
  label: string;
  email: string;
  phone: string;
  finance_customer: number | null;
  support_ticketing_enabled: boolean;
}

export interface SupportDeskTicketLookups {
  requesters: SupportDeskLookupUserOption[];
  agents: SupportDeskLookupUserOption[];
  departments: SupportDeskLookupDepartmentOption[];
  customers: SupportDeskLookupCustomerOption[];
  contact_accounts: SupportDeskLookupContactAccountOption[];
  categories: SupportDeskBreakdownItem[];
  priorities: SupportDeskBreakdownItem[];
  statuses: SupportDeskBreakdownItem[];
}

export interface SupportTicketAttachmentRecord {
  id: number;
  label: string;
  file: string;
  file_url: string;
  uploaded_by: number | null;
  uploaded_by_name: string;
  created_at: string;
}

export interface SupportTicketCommentRecord {
  id: number;
  comment_type: "internal_note" | "requester_reply";
  body: string;
  author: number | null;
  author_name: string;
  created_at: string;
}

export interface SupportTicketLinkedRecord {
  id: number;
  ticket_id: string;
  subject: string;
  requester_name: string;
  customer_name: string;
  contact_account_name: string;
  department_name: string;
  category: SupportTicketCategory;
  category_display: string;
  priority: SupportTicketPriority;
  priority_display: string;
  status: SupportTicketStatus;
  status_display: string;
  assigned_agent_name: string;
  created_at: string;
  updated_at: string;
  sla_deadline: string | null;
  sla_breached: boolean;
}

export interface SupportTicketListItem {
  id: number;
  ticket_id: string;
  subject: string;
  description: string;
  requester: number | null;
  requester_name: string;
  requester_email: string;
  customer: number | null;
  customer_name: string;
  contact_account: number | null;
  contact_account_name: string;
  department: number | null;
  department_name: string;
  category: SupportTicketCategory;
  category_display: string;
  priority: SupportTicketPriority;
  priority_display: string;
  status: SupportTicketStatus;
  status_display: string;
  assigned_agent: number | null;
  assigned_agent_name: string;
  created_at: string;
  updated_at: string;
  sla_deadline: string | null;
  first_response_at: string | null;
  resolved_at: string | null;
  closed_at: string | null;
  escalated_at: string | null;
  sla_breached: boolean;
}

export interface SupportTicketDetail extends SupportTicketListItem {
  organization: number;
  resolution_notes: string;
  customer_satisfaction_score: number | null;
  internal_notes: SupportTicketCommentRecord[];
  requester_replies: SupportTicketCommentRecord[];
  attachments: SupportTicketAttachmentRecord[];
  linked_tickets: SupportTicketLinkedRecord[];
}

export interface SupportDeskOverview {
  open_tickets: number;
  tickets_by_priority: SupportDeskBreakdownItem[];
  tickets_by_status: SupportDeskBreakdownItem[];
  sla_breaches: number;
  average_resolution_time_hours: number | null;
  average_resolution_time_display: string;
  agent_workload: SupportDeskAgentWorkloadItem[];
  recent_requests: SupportTicketListItem[];
  first_response_time_hours: number | null;
  first_response_time_display: string;
  ticket_backlog: number;
  escalated_tickets: number;
  customer_satisfaction_score: number | null;
  customer_satisfaction_display: string;
}

export type SupportKnowledgeArticleStatus =
  | "draft"
  | "in_review"
  | "published"
  | "archived";

export type SupportKnowledgeArticleVisibility =
  | "internal"
  | "portal"
  | "public";

export interface SupportKnowledgeArticleListItem {
  id: number;
  title: string;
  slug: string;
  summary: string;
  category: string;
  status: SupportKnowledgeArticleStatus;
  status_display: string;
  visibility: SupportKnowledgeArticleVisibility;
  visibility_display: string;
  owner: number | null;
  owner_name: string;
  reviewer: number | null;
  reviewer_name: string;
  published_at: string | null;
  last_reviewed_at: string | null;
  next_review_due_at: string | null;
  view_count: number;
  helpful_votes: number;
  not_helpful_votes: number;
  created_at: string;
  updated_at: string;
}

export interface SupportKnowledgeArticleDetail
  extends SupportKnowledgeArticleListItem {
  organization: number;
  body: string;
}

export interface SupportKnowledgeBaseOverview {
  total_articles: number;
  published_articles: number;
  in_review_articles: number;
  draft_articles: number;
  archived_articles: number;
  due_for_review_count: number;
  total_views: number;
  helpful_feedback_ratio: number | null;
  top_articles: SupportKnowledgeArticleListItem[];
}

export interface SupportSlaPolicy {
  id: number;
  name: string;
  description: string;
  category: SupportTicketCategory | "";
  category_display: string;
  priority: SupportTicketPriority | "";
  priority_display: string;
  response_target_hours: number | string;
  response_target_display: string;
  resolution_target_hours: number | string;
  resolution_target_display: string;
  escalate_after_hours: number;
  escalation_path: unknown[];
  agent_notify_threshold_percent: number;
  manager_notify_threshold_percent: number;
  breach_escalation_role: string;
  notify_assigned_agent: boolean;
  notify_manager: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SupportSlaEscalationTicket extends SupportTicketListItem {
  overdue_hours: number | null;
  policy_name: string;
  first_response_deadline: string | null;
  resolution_deadline: string | null;
  first_response_progress_percent: number;
  resolution_progress_percent: number;
  first_response_breached: boolean;
  resolution_breached: boolean;
  first_response_target_display: string;
  resolution_target_display: string;
  escalation_stage: "on_track" | "agent_warning" | "manager_warning" | "escalated" | "breached";
}

export interface SupportSlaPolicyMatrixItem {
  priority: SupportTicketPriority;
  priority_label: string;
  policy_name: string;
  first_response_target_display: string;
  resolution_target_display: string;
  agent_notify_threshold_percent: number;
  manager_notify_threshold_percent: number;
  breach_escalation_role: string;
}

export interface SupportSlaEscalationsOverview {
  active_policy_count: number;
  active_ticket_count: number;
  breached_ticket_count: number;
  escalated_ticket_count: number;
  upcoming_deadline_count: number;
  warning_50_count: number;
  warning_80_count: number;
  average_overdue_hours: number | null;
  max_overdue_hours: number | null;
  breaches_by_priority: SupportDeskBreakdownItem[];
  policy_matrix: SupportSlaPolicyMatrixItem[];
  top_breached_tickets: SupportSlaEscalationTicket[];
  recent_escalations: SupportTicketListItem[];
}

export type SupportCommunicationInteractionType =
  | "ticket_conversation"
  | "internal_note"
  | "email_reply"
  | "chat_transcript"
  | "call_log"
  | "whatsapp";

export type SupportCommunicationDirection = "inbound" | "outbound" | "internal";

export type SupportCommunicationChannel =
  | "portal"
  | "email"
  | "chat"
  | "phone"
  | "whatsapp"
  | "other";

export interface SupportCommunicationLogRecord {
  id: number;
  ticket: number | null;
  ticket_ref: string;
  ticket_subject: string;
  author: number | null;
  author_name: string;
  interaction_type: SupportCommunicationInteractionType;
  interaction_type_display: string;
  direction: SupportCommunicationDirection;
  direction_display: string;
  channel: SupportCommunicationChannel;
  channel_display: string;
  subject: string;
  message_preview: string;
  participants: string[];
  call_duration_seconds: number | null;
  external_message_id: string;
  happened_at: string;
  created_at: string;
  message?: string;
  transcript?: string;
  metadata?: Record<string, unknown>;
  updated_at?: string;
}

export interface SupportCommunicationOverview {
  total_interactions: number;
  ticket_conversations_count: number;
  internal_notes_count: number;
  email_replies_count: number;
  chat_transcripts_count: number;
  call_logs_count: number;
  whatsapp_messages_count: number;
  inbound_count: number;
  outbound_count: number;
  internal_count: number;
  interactions_by_channel: SupportDeskBreakdownItem[];
  recent_logs: SupportCommunicationLogRecord[];
}

export type SupportAutomationTriggerType =
  | "ticket_created"
  | "ticket_updated"
  | "sla_threshold"
  | "status_changed";

export interface SupportAutomationRule {
  id: number;
  name: string;
  description: string;
  trigger_type: SupportAutomationTriggerType;
  trigger_type_display: string;
  conditions: Record<string, unknown>;
  actions: Record<string, unknown>;
  priority: number;
  run_once_per_ticket: boolean;
  is_active: boolean;
  created_by: number | null;
  created_by_name: string;
  created_at: string;
  updated_at: string;
}

export interface SupportAutomationRun {
  id: number;
  rule: number | null;
  rule_name: string;
  ticket: number | null;
  ticket_ref: string;
  ticket_subject: string;
  trigger_type: SupportAutomationTriggerType;
  trigger_type_display: string;
  status: "matched" | "failed";
  status_display: string;
  summary: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface SupportAutomationOverview {
  active_rule_count: number;
  total_rule_count: number;
  recent_run_count: number;
  last_run_at: string | null;
  runs_by_status: SupportDeskBreakdownItem[];
  runs_by_trigger: SupportDeskBreakdownItem[];
  recent_runs: SupportAutomationRun[];
}

export interface SupportDeskStandardReport {
  key: string;
  title: string;
  description: string;
}

export interface SupportDeskTicketTrendPoint {
  date: string;
  created_count: number;
  resolved_count: number;
}

export interface SupportDeskResolutionTrendPoint {
  date: string;
  resolved_count: number;
  average_resolution_hours: number | null;
  average_resolution_display: string;
}

export interface SupportDeskSlaTrendPoint {
  date: string;
  compliant_count: number;
  breached_count: number;
  compliance_rate: number;
}

export interface SupportDeskAgentPerformance {
  agent_id: number;
  agent_name: string;
  total_tickets: number;
  resolved_tickets: number;
  sla_breaches: number;
  average_resolution_hours: number | null;
  average_resolution_display: string;
  customer_satisfaction_score: number | null;
  customer_satisfaction_display: string;
}

export interface SupportDeskSlaCompliance {
  compliant_count: number;
  breached_count: number;
  compliance_rate: number;
}

export interface SupportDeskEscalationRate {
  escalated_count: number;
  total_tickets: number;
  escalation_rate: number;
}

export interface SupportDeskCustomerSatisfaction {
  average_score: number | null;
  response_count: number;
  display: string;
}

export interface SupportDeskReportsOverview {
  window_start: string;
  window_end: string;
  total_tickets: number;
  standard_reports: SupportDeskStandardReport[];
  tickets_by_department: SupportDeskBreakdownItem[];
  tickets_by_category: SupportDeskBreakdownItem[];
  resolution_time_average_hours: number | null;
  resolution_time_average_display: string;
  agent_performance: SupportDeskAgentPerformance[];
  sla_compliance: SupportDeskSlaCompliance;
  escalation_rate: SupportDeskEscalationRate;
  customer_satisfaction: SupportDeskCustomerSatisfaction;
  ticket_trend: SupportDeskTicketTrendPoint[];
  resolution_trend: SupportDeskResolutionTrendPoint[];
  sla_performance_trend: SupportDeskSlaTrendPoint[];
}

export interface SupportDeskConfigurationTeam {
  id: number;
  name: string;
  head_name: string;
  is_active: boolean;
}

export interface SupportDeskConfigurationRole {
  id: number;
  name: string;
  slug: string;
  user_count: number;
}

export interface SupportDeskConfigurationRequestType {
  key: string;
  label: string;
  description: string;
  approval_required: boolean;
  sla_target_hours: number;
  is_active: boolean;
}

export interface SupportDeskConfigurationEmailTemplate {
  id: number;
  code: string;
  name: string;
  event_key: string;
  severity_tier: string;
  is_active: boolean;
  updated_at: string;
}

export interface SupportDeskConfigurationNotificationRule {
  key: string;
  label: string;
  description: string;
  default_channels: string[];
  configured_channels: string[];
  active_channels: string[];
  total_templates: number;
  active_templates: number;
  is_enabled: boolean;
}

export interface SupportDeskConfigurationChannelSettings {
  email_enabled: boolean;
  in_app_enabled: boolean;
  sms_enabled: boolean;
  push_enabled: boolean;
}

export interface SupportDeskConfigurationOverview {
  ticket_categories: SupportDeskBreakdownItem[];
  priority_levels: SupportDeskBreakdownItem[];
  ticket_statuses: SupportDeskBreakdownItem[];
  support_teams: SupportDeskConfigurationTeam[];
  agent_roles: SupportDeskConfigurationRole[];
  sla_policies: SupportSlaPolicy[];
  automation_rules: SupportAutomationRule[];
  request_types: SupportDeskConfigurationRequestType[];
  email_templates: SupportDeskConfigurationEmailTemplate[];
  notification_rules: SupportDeskConfigurationNotificationRule[];
  channel_settings: SupportDeskConfigurationChannelSettings;
}

// ---------------------------------------------------------------------------
// HR – Skills & Capability Management
// ---------------------------------------------------------------------------

export type SkillCategory = "technical" | "management" | "soft" | "domain" | "regulatory";
export type SkillProficiency = "beginner" | "intermediate" | "advanced" | "expert";
export type CertificationStatus = "active" | "expired" | "pending" | "revoked";
export type LicenseStatus = "active" | "expired" | "pending" | "suspended";
export type CompetencyAssessmentStatus = "scheduled" | "in_progress" | "completed" | "cancelled";
export type TrainingStatus = "enrolled" | "in_progress" | "completed" | "failed" | "cancelled";
export type TrainingDeliveryMethod = "in_person" | "online" | "hybrid" | "self_paced";

export interface SkillListItem {
  id: number;
  employee: number;
  employee_name: string;
  name: string;
  category: SkillCategory;
  proficiency: SkillProficiency;
  years_experience: string;
  is_primary: boolean;
  verified: boolean;
  verified_by: number | null;
  verified_by_name: string | null;
  verified_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface SkillDetail extends SkillListItem {
  notes: string;
}

export interface CertificationListItem {
  id: number;
  employee: number;
  employee_name: string;
  name: string;
  issuing_body: string;
  credential_id: string;
  issue_date: string;
  expiry_date: string | null;
  status: CertificationStatus;
  created_at: string;
  updated_at: string;
}

export interface CertificationDetail extends CertificationListItem {
  verification_url: string;
  notes: string;
}

export interface ProfessionalLicenseListItem {
  id: number;
  employee: number;
  employee_name: string;
  license_type: string;
  license_number: string;
  issuing_authority: string;
  jurisdiction: string;
  issue_date: string;
  expiry_date: string | null;
  status: LicenseStatus;
  is_mandatory: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProfessionalLicenseDetail extends ProfessionalLicenseListItem {
  notes: string;
}

export interface CompetencyAssessmentListItem {
  id: number;
  employee: number;
  employee_name: string;
  assessor: number;
  assessor_name: string;
  competency_area: string;
  assessment_date: string;
  score: string | null;
  max_score: string;
  status: CompetencyAssessmentStatus;
  next_assessment_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface CompetencyAssessmentDetail extends CompetencyAssessmentListItem {
  strengths: string;
  gaps: string;
  development_plan: string;
  notes: string;
}

export interface TrainingRecordListItem {
  id: number;
  employee: number;
  employee_name: string;
  title: string;
  provider: string;
  delivery_method: TrainingDeliveryMethod;
  start_date: string;
  end_date: string | null;
  duration_hours: string | null;
  status: TrainingStatus;
  score: string | null;
  cost: string | null;
  currency: string;
  is_mandatory: boolean;
  created_at: string;
  updated_at: string;
}

export interface TrainingRecordDetail extends TrainingRecordListItem {
  notes: string;
}

// ---------------------------------------------------------------------------
// HR – Learning & Development
// ---------------------------------------------------------------------------

export type CourseFormat = "in_person" | "online" | "hybrid" | "self_paced" | "workshop";
export type CourseLevel = "beginner" | "intermediate" | "advanced";
export type CourseStatus = "draft" | "active" | "archived";
export type TrainingPlanStatus = "draft" | "active" | "completed" | "cancelled";
export type EnrollmentStatus = "enrolled" | "in_progress" | "completed" | "failed" | "withdrawn" | "waitlisted";
export type LearningResourceType = "document" | "video" | "article" | "ebook" | "template" | "link";
export type LearningResourceStatus = "published" | "draft" | "archived";
export type TrainingResult = "pass" | "fail" | "distinction";
export type ExpiryAlertStatus = "pending" | "sent" | "acknowledged" | "renewed" | "expired";
export type ExpiryAlertType = "certification" | "license" | "training";

export interface TrainingCourseListItem {
  id: number;
  title: string;
  code: string;
  provider: string;
  format: CourseFormat;
  level: CourseLevel;
  duration_hours: string | null;
  max_participants: number | null;
  cost_per_participant: string | null;
  currency: string;
  is_mandatory: boolean;
  status: CourseStatus;
  created_by: number | null;
  created_by_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface TrainingCourseDetail extends TrainingCourseListItem {
  description: string;
  prerequisites: string;
  learning_objectives: string;
  syllabus: string;
}

export interface TrainingPlanListItem {
  id: number;
  title: string;
  department: number | null;
  department_name: string | null;
  employee: number | null;
  employee_name: string | null;
  start_date: string;
  end_date: string | null;
  budget: string | null;
  currency: string;
  status: TrainingPlanStatus;
  created_by: number | null;
  created_by_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface TrainingPlanDetail extends TrainingPlanListItem {
  description: string;
  objectives: string;
  notes: string;
}

export interface CourseEnrollmentListItem {
  id: number;
  employee: number;
  employee_name: string;
  course: number;
  course_title: string;
  training_plan: number | null;
  training_plan_title: string | null;
  enrolled_date: string;
  start_date: string | null;
  completion_date: string | null;
  status: EnrollmentStatus;
  score: string | null;
  progress: number;
  created_at: string;
  updated_at: string;
}

export interface CourseEnrollmentDetail extends CourseEnrollmentListItem {
  feedback: string;
  enrolled_by: number | null;
  notes: string;
}

export interface LearningResourceListItem {
  id: number;
  title: string;
  resource_type: LearningResourceType;
  category: string;
  url: string;
  duration_minutes: number | null;
  tags: string;
  status: LearningResourceStatus;
  view_count: number;
  uploaded_by: number | null;
  uploaded_by_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface LearningResourceDetail extends LearningResourceListItem {
  description: string;
}

export interface TrainingCompletionListItem {
  id: number;
  employee: number;
  employee_name: string;
  course: number | null;
  course_title: string | null;
  enrollment: number | null;
  completion_date: string;
  result: TrainingResult;
  score: string | null;
  certificate_number: string;
  certificate_expiry: string | null;
  hours_completed: string | null;
  verified_by: number | null;
  verified_by_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface TrainingCompletionDetail extends TrainingCompletionListItem {
  notes: string;
}

export interface CertificationExpiryAlertListItem {
  id: number;
  employee: number;
  employee_name: string;
  alert_type: ExpiryAlertType;
  reference_name: string;
  reference_id: number | null;
  expiry_date: string;
  alert_date: string;
  days_before_expiry: number;
  status: ExpiryAlertStatus;
  renewal_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface CertificationExpiryAlertDetail extends CertificationExpiryAlertListItem {
  notes: string;
}

// ---------------------------------------------------------------------------
// HR – Attendance & Leave
// ---------------------------------------------------------------------------

export type AttendanceStatus = "present" | "absent" | "late" | "half_day" | "on_leave" | "remote" | "holiday";
export type LeaveRequestStatus = "draft" | "pending" | "approved" | "rejected" | "cancelled";
export type OvertimeRequestStatus = "draft" | "pending" | "approved" | "rejected" | "cancelled";
export type RemoteWorkStatus = "planned" | "active" | "completed" | "cancelled";

export interface AttendanceLogListItem {
  id: number;
  employee: number;
  employee_name: string;
  date: string;
  status: AttendanceStatus;
  clock_in: string | null;
  clock_out: string | null;
  break_minutes: number;
  total_hours: string | null;
  location: string;
  created_at: string;
  updated_at: string;
}

export interface AttendanceLogDetail extends AttendanceLogListItem {
  notes: string;
}

export interface LeaveTypeListItem {
  id: number;
  name: string;
  code: string;
  default_days_per_year: string;
  is_paid: boolean;
  is_carry_over_allowed: boolean;
  max_carry_over_days: string;
  requires_approval: boolean;
  requires_attachment: boolean;
  min_days_notice: number;
  is_active: boolean;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface LeaveTypeDetail extends LeaveTypeListItem {
  description: string;
}

export interface LeaveRequestListItem {
  id: number;
  employee: number;
  employee_name: string;
  leave_type: number;
  leave_type_name: string;
  start_date: string;
  end_date: string;
  total_days: string;
  is_half_day: boolean;
  status: LeaveRequestStatus;
  reviewed_by: number | null;
  reviewed_by_name: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface LeaveRequestDetail extends LeaveRequestListItem {
  reason: string;
  reviewer_notes: string;
}

export interface LeaveBalanceListItem {
  id: number;
  employee: number;
  employee_name: string;
  leave_type: number;
  leave_type_name: string;
  fiscal_year: number;
  entitled_days: string;
  carried_over: string;
  used_days: string;
  pending_days: string;
  adjustment: string;
  available_days: string;
  created_at: string;
  updated_at: string;
}

export interface LeaveBalanceDetail extends LeaveBalanceListItem {
  notes: string;
}

export interface OvertimeRequestListItem {
  id: number;
  employee: number;
  employee_name: string;
  date: string;
  start_time: string;
  end_time: string;
  total_hours: string;
  status: OvertimeRequestStatus;
  approved_by: number | null;
  approved_by_name: string | null;
  approved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface OvertimeRequestDetail extends OvertimeRequestListItem {
  reason: string;
  approver_notes: string;
}

export interface RemoteWorkLogListItem {
  id: number;
  employee: number;
  employee_name: string;
  date: string;
  status: RemoteWorkStatus;
  location: string;
  work_hours: string | null;
  approved_by: number | null;
  approved_by_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface RemoteWorkLogDetail extends RemoteWorkLogListItem {
  tasks_completed: string;
  notes: string;
}

// ---------------------------------------------------------------------------
// Payroll & Compensation
// ---------------------------------------------------------------------------

export type PayrollRunStatus = "draft" | "processing" | "completed" | "cancelled";
export type AllowanceType = "housing" | "transport" | "meal" | "phone" | "medical" | "education" | "other";
export type AllowanceFrequency = "monthly" | "quarterly" | "annually" | "one_time";
export type DeductionType = "tax" | "insurance" | "pension" | "loan" | "union" | "other";
export type BonusType = "performance" | "annual" | "signing" | "referral" | "project" | "other";
export type BonusStatus = "pending" | "approved" | "paid" | "cancelled";
export type PayslipStatus = "draft" | "generated" | "sent" | "acknowledged";
export type TaxType = "income_tax" | "social_security" | "municipal" | "other";
export type FilingStatus = "pending" | "filed" | "assessed" | "paid";

export interface SalaryStructureListItem {
  id: number;
  name: string;
  code: string;
  grade_level: number | null;
  min_salary: string;
  max_salary: string;
  currency: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}
export interface SalaryStructureDetail extends SalaryStructureListItem {
  description: string;
}

export interface PayrollRunListItem {
  id: number;
  name: string;
  period_start: string;
  period_end: string;
  run_date: string | null;
  status: PayrollRunStatus;
  total_gross: string;
  total_deductions: string;
  total_net: string;
  currency: string;
  processed_by: number | null;
  processed_by_name: string | null;
  created_at: string;
  updated_at: string;
}
export interface PayrollRunDetail extends PayrollRunListItem {
  notes: string;
}

export type PayrollGLLineKind = "gross_salary" | "employee_deductions" | "net_payable";
export type PayrollGLPostingStatus = "draft" | "posted" | "reversed" | "failed";

export interface PayrollGLMapping {
  id: number;
  line_kind: PayrollGLLineKind;
  line_kind_display: string;
  account: number;
  account_code: string | null;
  account_name: string | null;
  updated_at: string;
}

export interface PayrollGLPosting {
  id: number;
  payroll_run: number;
  payroll_run_name: string | null;
  journal_entry: number | null;
  journal_number: string | null;
  status: PayrollGLPostingStatus;
  status_display: string;
  posted_at: string | null;
  posted_by: number | null;
  posted_by_name: string | null;
  error_message: string;
  created_at: string;
  updated_at: string;
}

export interface PayrollGLBulkSyncResult {
  posted: number[];
  skipped: number[];
  errors: Array<{ run_id: number; error: string }>;
}

export interface AllowanceListItem {
  id: number;
  employee: number;
  employee_name: string;
  allowance_type: AllowanceType;
  name: string;
  amount: string;
  currency: string;
  frequency: AllowanceFrequency;
  is_taxable: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}
export interface AllowanceDetail extends AllowanceListItem {
  start_date: string | null;
  end_date: string | null;
}

export interface DeductionListItem {
  id: number;
  employee: number;
  employee_name: string;
  deduction_type: DeductionType;
  name: string;
  amount: string;
  currency: string;
  frequency: AllowanceFrequency;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}
export interface DeductionDetail extends DeductionListItem {
  start_date: string | null;
  end_date: string | null;
}

export interface BonusListItem {
  id: number;
  employee: number;
  employee_name: string;
  bonus_type: BonusType;
  amount: string;
  currency: string;
  date: string;
  status: BonusStatus;
  approved_by: number | null;
  approved_by_name: string | null;
  created_at: string;
  updated_at: string;
}
export interface BonusDetail extends BonusListItem {
  reason: string;
  approved_at: string | null;
}

export interface PayslipListItem {
  id: number;
  employee: number;
  employee_name: string;
  payroll_run: number | null;
  payroll_run_name: string | null;
  period_start: string;
  period_end: string;
  gross_salary: string;
  net_salary: string;
  currency: string;
  status: PayslipStatus;
  created_at: string;
  updated_at: string;
}
export interface PayslipDetail extends PayslipListItem {
  basic_salary: string;
  total_allowances: string;
  total_deductions: string;
  generated_at: string | null;
  sent_at: string | null;
}

export interface TaxRecordListItem {
  id: number;
  employee: number;
  employee_name: string;
  fiscal_year: string;
  tax_type: TaxType;
  tax_amount: string;
  tax_paid: string;
  balance: string;
  currency: string;
  filing_status: FilingStatus;
  created_at: string;
  updated_at: string;
}
export interface TaxRecordDetail extends TaxRecordListItem {
  taxable_income: string;
  filed_date: string | null;
  notes: string;
}

// ---------------------------------------------------------------------------
// 10. Employee Lifecycle Management
// ---------------------------------------------------------------------------

export type PromotionStatus = "pending" | "approved" | "effective" | "cancelled";
export type TransferType = "lateral" | "relocation" | "temporary" | "permanent";
export type TransferStatus = "pending" | "approved" | "effective" | "cancelled";
export type RoleChangeType = "promotion" | "lateral" | "demotion" | "restructure";
export type RoleChangeStatus = "pending" | "approved" | "effective" | "cancelled";
export type DisciplinaryCategory = "misconduct" | "performance" | "attendance" | "policy_violation" | "other";
export type DisciplinarySeverity = "verbal_warning" | "written_warning" | "final_warning" | "suspension" | "termination";
export type DisciplinaryStatus = "open" | "under_review" | "resolved" | "appealed";
export type ExitType = "resignation" | "termination" | "retirement" | "end_of_contract" | "redundancy" | "other";
export type ClearanceStatus = "pending" | "in_progress" | "completed";
export type SettlementStatus = "pending" | "processing" | "paid";

export interface PromotionListItem {
  id: number;
  employee: number;
  employee_name: string;
  from_position: string;
  to_position: string;
  effective_date: string;
  salary_adjustment: string;
  currency: string;
  status: PromotionStatus;
  approved_by_name: string | null;
  created_at: string;
  updated_at: string;
}
export interface PromotionDetail extends PromotionListItem {
  from_grade: string;
  to_grade: string;
  new_salary: string | null;
  reason: string;
}

export interface TransferListItem {
  id: number;
  employee: number;
  employee_name: string;
  transfer_type: TransferType;
  from_department: string;
  to_department: string;
  effective_date: string;
  status: TransferStatus;
  approved_by_name: string | null;
  created_at: string;
  updated_at: string;
}
export interface TransferDetail extends TransferListItem {
  from_location: string;
  to_location: string;
  reason: string;
}

export interface RoleChangeListItem {
  id: number;
  employee: number;
  employee_name: string;
  change_type: RoleChangeType;
  from_role: string;
  to_role: string;
  effective_date: string;
  status: RoleChangeStatus;
  approved_by_name: string | null;
  created_at: string;
  updated_at: string;
}
export interface RoleChangeDetail extends RoleChangeListItem {
  reason: string;
}

export interface DisciplinaryRecordListItem {
  id: number;
  employee: number;
  employee_name: string;
  incident_date: string;
  category: DisciplinaryCategory;
  severity: DisciplinarySeverity;
  status: DisciplinaryStatus;
  reported_by_name: string | null;
  created_at: string;
  updated_at: string;
}
export interface DisciplinaryRecordDetail extends DisciplinaryRecordListItem {
  description: string;
  action_taken: string;
  follow_up_date: string | null;
}

export interface ExitManagementListItem {
  id: number;
  employee: number;
  employee_name: string;
  exit_type: ExitType;
  notice_date: string;
  last_working_day: string;
  clearance_status: ClearanceStatus;
  final_settlement_status: SettlementStatus;
  processed_by_name: string | null;
  created_at: string;
  updated_at: string;
}
export interface ExitManagementDetail extends ExitManagementListItem {
  reason: string;
  notes: string;
}

export interface ExitInterviewListItem {
  id: number;
  employee: number;
  employee_name: string;
  interview_date: string;
  overall_satisfaction: number;
  would_recommend: boolean;
  would_rejoin: boolean;
  interviewer_name: string | null;
  created_at: string;
  updated_at: string;
}
export interface ExitInterviewDetail extends ExitInterviewListItem {
  exit_record: number | null;
  reason_for_leaving: string;
  feedback: string;
  key_concerns: string;
  suggestions: string;
}

// ---------------------------------------------------------------------------
// 11. Workforce Analytics
// ---------------------------------------------------------------------------

export type DiversityDimension = "gender" | "age_group" | "ethnicity" | "nationality" | "disability";

export interface HeadcountSnapshotListItem {
  id: number;
  snapshot_date: string;
  department: string;
  team: string;
  active_count: number;
  inactive_count: number;
  total_headcount: number;
  new_hires: number;
  departures: number;
  contractors: number;
  created_at: string;
  updated_at: string;
}
export interface HeadcountSnapshotDetail extends HeadcountSnapshotListItem {
  notes: string;
}

export interface TurnoverRecordListItem {
  id: number;
  period_start: string;
  period_end: string;
  department: string;
  starting_headcount: number;
  ending_headcount: number;
  voluntary_departures: number;
  involuntary_departures: number;
  total_departures: number;
  turnover_rate: string;
  created_at: string;
  updated_at: string;
}
export interface TurnoverRecordDetail extends TurnoverRecordListItem {
  notes: string;
}

export interface DepartmentStaffingReportListItem {
  id: number;
  report_date: string;
  department: string;
  budgeted_positions: number;
  filled_positions: number;
  vacant_positions: number;
  pending_hires: number;
  fill_rate: string;
  created_at: string;
  updated_at: string;
}
export interface DepartmentStaffingReportDetail extends DepartmentStaffingReportListItem {
  notes: string;
}

export interface HiringFunnelMetricListItem {
  id: number;
  period_start: string;
  period_end: string;
  department: string;
  requisitions_opened: number;
  applications_received: number;
  candidates_screened: number;
  candidates_interviewed: number;
  offers_made: number;
  offers_accepted: number;
  offer_acceptance_rate: string;
  avg_time_to_hire_days: string;
  avg_cost_per_hire: string;
  currency: string;
  created_at: string;
  updated_at: string;
}
export interface HiringFunnelMetricDetail extends HiringFunnelMetricListItem {
  notes: string;
}

export interface WorkforceCostReportListItem {
  id: number;
  period_start: string;
  period_end: string;
  department: string;
  total_salary: string;
  total_allowances: string;
  total_bonuses: string;
  total_benefits: string;
  total_overtime: string;
  total_cost: string;
  headcount: number;
  cost_per_employee: string;
  currency: string;
  created_at: string;
  updated_at: string;
}
export interface WorkforceCostReportDetail extends WorkforceCostReportListItem {
  notes: string;
}

export interface DiversityMetricListItem {
  id: number;
  snapshot_date: string;
  department: string;
  dimension: DiversityDimension;
  category_value: string;
  count: number;
  percentage: string;
  created_at: string;
  updated_at: string;
}
export interface DiversityMetricDetail extends DiversityMetricListItem {
  notes: string;
}

// HR Documents & Policies
export type HRPolicyCategory = "general" | "employment" | "compensation" | "leave" | "conduct" | "safety" | "data_privacy" | "other";
export type HRPolicyStatus = "draft" | "under_review" | "active" | "archived";
export type HandbookSectionStatus = "draft" | "published" | "archived";
export type ComplianceDocumentType = "regulation" | "certification" | "audit_report" | "legal" | "policy" | "other";
export type ComplianceDocumentStatus = "current" | "expired" | "pending_review" | "archived";
export type HRDocumentTemplateCategory = "offer_letter" | "contract" | "warning_letter" | "termination" | "promotion" | "transfer" | "general" | "other";
export type HRDocumentTemplateStatus = "active" | "draft" | "archived";

export interface HRPolicyListItem {
  id: number;
  title: string;
  category: HRPolicyCategory;
  status: HRPolicyStatus;
  version: string;
  effective_date: string | null;
  expiry_date: string | null;
  department: string;
  created_at: string;
  updated_at: string;
}
export interface HRPolicyDetail extends HRPolicyListItem {
  description: string;
  content: string;
  created_by: number | null;
  approved_by: number | null;
  approval_date: string | null;
}

export interface EmployeeHandbookSectionListItem {
  id: number;
  handbook_version: string;
  section_number: string;
  title: string;
  order: number;
  status: HandbookSectionStatus;
  created_at: string;
  updated_at: string;
}
export interface EmployeeHandbookSectionDetail extends EmployeeHandbookSectionListItem {
  content: string;
  last_updated_by: number | null;
}

export interface ComplianceDocumentListItem {
  id: number;
  title: string;
  document_type: ComplianceDocumentType;
  status: ComplianceDocumentStatus;
  reference_number: string;
  issuing_authority: string;
  issue_date: string | null;
  expiry_date: string | null;
  department: string;
  created_at: string;
  updated_at: string;
}
export interface ComplianceDocumentDetail extends ComplianceDocumentListItem {
  description: string;
}

export interface PolicyAcknowledgementListItem {
  id: number;
  employee: number;
  employee_name: string;
  policy: number;
  policy_title: string;
  acknowledged: boolean;
  acknowledged_date: string | null;
  created_at: string;
  updated_at: string;
}
export interface PolicyAcknowledgementDetail extends PolicyAcknowledgementListItem {
  ip_address: string | null;
  notes: string;
}

export interface HRDocumentTemplateListItem {
  id: number;
  title: string;
  category: HRDocumentTemplateCategory;
  version: string;
  status: HRDocumentTemplateStatus;
  created_at: string;
  updated_at: string;
}
export interface HRDocumentTemplateDetail extends HRDocumentTemplateListItem {
  description: string;
  content: string;
  created_by: number | null;
}

// ---------------------------------------------------------------------------
// Platform Editions & Subscriptions
// ---------------------------------------------------------------------------

export type SupportTier = "community" | "standard" | "priority" | "dedicated";
export type SubscriptionStatus = "trialing" | "active" | "past_due" | "suspended" | "cancelled" | "expired";
export type BillingCycle = "monthly" | "annual";
export type SubscriptionEventType =
  | "created" | "activated" | "upgraded" | "downgraded"
  | "renewed" | "payment_failed" | "payment_recovered"
  | "suspended" | "cancelled" | "reactivated" | "expired"
  | "trial_started" | "trial_ended";

export interface PlatformEdition {
  id: number;
  key: string;
  name: string;
  tier_level: number;
  is_custom: boolean;
  description: string;
  included_modules: string[];
  max_users: number | null;
  max_storage_gb: number | null;
  api_rate_limit_rpm: number | null;
  data_retention_days: number | null;
  max_projects: number | null;
  support_tier: SupportTier;
  support_response_hours: number | null;
  support_resolution_hours: number | null;
  monthly_price: string | null;
  annual_price: string | null;
  currency: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SubscriptionAddOn {
  id: number;
  key: string;
  name: string;
  add_on_type: "module" | "storage";
  module_key: string;
  storage_gb: number;
  monthly_price: string;
  description: string;
  is_active: boolean;
}

export interface ActiveSubscriptionAddOn {
  id: number;
  add_on: SubscriptionAddOn;
  activated_at: string;
}

export interface OrganizationSubscription {
  id: number;
  organization: number;
  edition: number;
  edition_name: string;
  edition_key: string;
  status: SubscriptionStatus;
  billing_cycle: BillingCycle;
  current_period_start: string | null;
  current_period_end: string | null;
  trial_start: string | null;
  trial_end: string | null;
  seats_purchased: number;
  seats_used: number;
  effective_max_users: number | null;
  storage_used_gb: string;
  effective_max_storage_gb: number | null;
  cancelled_at: string | null;
  cancel_reason: string;
  payment_method_summary: string;
  auto_renew: boolean;
  active_add_ons: ActiveSubscriptionAddOn[];
  created_at: string;
  updated_at: string;
}

export interface SubscriptionEvent {
  id: number;
  subscription: number;
  event_type: SubscriptionEventType;
  from_edition: number | null;
  from_edition_name: string | null;
  to_edition: number | null;
  to_edition_name: string | null;
  metadata: Record<string, unknown>;
  actor: number | null;
  actor_email: string | null;
  occurred_at: string;
}

// ---------------------------------------------------------------------------
// Global Search / Command Palette
// ---------------------------------------------------------------------------

export interface NavSubItem {
  href: string;
  label: string;
  /** i18n key path (e.g. "nav.crm.leads"); falls back to `label` if missing. */
  labelKey?: string;
  badge?: string;
  exact?: boolean;
  group?: string;
  matchPaths?: string[];
}

export interface NavSection {
  key: string;
  label: string;
  /** i18n key path; falls back to `label` if missing. */
  labelKey?: string;
  href: string;
  subItems: NavSubItem[];
}

/** A section within a domain (same shape as NavSection). */
export type NavDomainSection = NavSection;

/** A top-level navigation domain grouping multiple sections. */
export interface NavDomain {
  key: string;
  label: string;
  /** i18n key path; falls back to `label` if missing. */
  labelKey?: string;
  sections: NavDomainSection[];
}

export interface SearchResultItem {
  id: number | string;
  title: string;
  subtitle?: string;
  href: string;
  module?: string;
}

export interface SearchResultCategory {
  key: string;
  label: string;
  results: SearchResultItem[];
  total_count: number;
}

export interface SearchResponse {
  query: string;
  categories: SearchResultCategory[];
}

// ---------------------------------------------------------------------------
// Equipment & Machinery
// ---------------------------------------------------------------------------

export type EquipmentType = "earthmoving" | "lifting" | "material_handling" | "concrete" | "piling" | "compaction" | "transport" | "scaffolding" | "power_generation" | "other";
export type FuelType = "diesel" | "petrol" | "electric" | "hybrid" | "na";
export type EquipmentOwnership = "owned" | "leased" | "rented";

export interface EquipmentListItem {
  id: number;
  asset_id: string;
  name: string;
  equipment_type: EquipmentType;
  equipment_type_display: string;
  status: EquipmentStatus;
  status_display: string;
  make: string;
  model_name: string;
  current_project: number | null;
  current_project_name: string | null;
  current_location: string;
  ownership: EquipmentOwnership;
  ownership_display: string;
  last_service_date: string | null;
  next_service_due: string | null;
  maintenance_due: boolean;
  current_book_value: string | null;
  internal_daily_rate: string | null;
  created_at: string;
  updated_at: string;
}

export interface EquipmentMaintenanceLog {
  id: number;
  equipment: number;
  log_type: string;
  log_type_display: string;
  date: string;
  description: string;
  parts_replaced: string;
  cost: string;
  performed_by: string;
  hour_meter_at_service: string | null;
  downtime_hours: string;
  created_at: string;
}

export interface EquipmentDeploymentLog {
  id: number;
  equipment: number;
  project: number;
  project_name: string;
  site_name: string;
  operator: string;
  deployed_date: string;
  returned_date: string | null;
  hours_used: string;
  notes: string;
  created_at: string;
}

export interface Equipment extends EquipmentListItem {
  serial_number: string;
  engine_number: string;
  fuel_type: FuelType;
  fuel_type_display: string;
  fuel_consumption_rate: string | null;
  capacity: string;
  weight_kg: string | null;
  year_of_manufacture: number | null;
  gps_latitude: string | null;
  gps_longitude: string | null;
  current_operator: string;
  operator_license_verified: boolean;
  hour_meter_reading: string;
  odometer_reading: string;
  service_interval_hours: number | null;
  purchase_price: string | null;
  internal_hourly_rate: string | null;
  mobilization_cost: string | null;
  insurance_policy_number: string;
  insurance_expiry: string | null;
  notes: string;
  maintenance_logs: EquipmentMaintenanceLog[];
  deployment_logs: EquipmentDeploymentLog[];
}

export interface EquipmentFleetKpis {
  total_fleet: number;
  operational: number;
  in_repair: number;
  idle: number;
  deployment_rate: number;
  maintenance_due: number;
  total_book_value: string;
  utilization_index: number;
}

// =====================================================================
// Workspace > Teams (apps.workspace)
// See docs/workspace-teams-design.md and docs/workspace-teams-ui-spec.md.
// =====================================================================

export type WorkspaceTeamPurpose = "project" | "initiative" | "guild";
export type WorkspaceTeamVisibility = "public" | "private" | "secret";
export type WorkspaceTeamRole = "owner" | "admin" | "member" | "guest";
export type WorkspaceDigestFrequency = "daily" | "weekly" | "off";
export type WorkspaceTeamColor =
  | "rose"
  | "orange"
  | "amber"
  | "lime"
  | "emerald"
  | "teal"
  | "sky"
  | "indigo"
  | "violet"
  | "fuchsia";

export interface WorkspaceTeamUserMini {
  id: number;
  name: string;
  email: string;
  initials: string;
}

export interface WorkspaceTeamListItem {
  id: number;
  name: string;
  slug: string;
  description: string;
  purpose: WorkspaceTeamPurpose;
  visibility: WorkspaceTeamVisibility;
  emoji: string;
  color: WorkspaceTeamColor;
  is_archived: boolean;
  members_count: number;
  my_role: WorkspaceTeamRole | null;
  created_at: string;
}

export interface WorkspaceTeamDetail extends WorkspaceTeamListItem {
  archived_at: string | null;
  project: number | null;
  project_name: string | null;
  open_tickets_count: number;
  is_orphaned: boolean;
  created_by: WorkspaceTeamUserMini | null;
  updated_at: string;
}

export interface WorkspaceTeamMembership {
  id: number;
  user: WorkspaceTeamUserMini;
  role: WorkspaceTeamRole;
  joined_at: string;
  notify_realtime: boolean;
  digest_frequency: WorkspaceDigestFrequency;
  updated_at: string;
}

export interface WorkspaceTeamCreatePayload {
  name: string;
  description?: string;
  purpose: WorkspaceTeamPurpose;
  visibility: WorkspaceTeamVisibility;
  project?: number | null;
  emoji?: string;
  color?: WorkspaceTeamColor;
}


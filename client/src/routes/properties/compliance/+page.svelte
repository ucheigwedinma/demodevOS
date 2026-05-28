<script lang="ts">
  import { currency } from "$lib/stores/currency.svelte";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    ComplianceRequirementListItem, ComplianceRequirement,
    PropertyComplianceListItem, PropertyComplianceItem,
    ComplianceViolationListItem, ComplianceViolation,
    ComplianceAuditListItem, ComplianceAuditItem,
    PropertyListItem, PaginatedResponse,
    ComplianceCategory, ComplianceRenewalFrequency,
    PropertyComplianceStatus, ViolationSeverity, ViolationStatus,
    ComplianceAuditType, ComplianceAuditStatus, ComplianceAuditRating,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  type Tab = "requirements" | "tracker" | "violations" | "audits";
  let activeTab = $state<Tab>("requirements");
  const tabs: { key: Tab; label: string }[] = [
    { key: "requirements", label: "Requirements" },
    { key: "tracker", label: "Compliance Tracker" },
    { key: "violations", label: "Violations" },
    { key: "audits", label: "Audits" },
  ];

  // --- Shared lookups ---
  let properties = $state<PropertyListItem[]>([]);
  let requirements = $state<ComplianceRequirementListItem[]>([]);

  $effect(() => {
    api.get<PaginatedResponse<PropertyListItem>>("/properties/", { page_size: "200" })
      .then((r) => { properties = r.results; }).catch(() => {});
  });

  let requirementsLoaded = $state(false);
  function ensureRequirements() {
    if (requirementsLoaded) return;
    requirementsLoaded = true;
    api.get<PaginatedResponse<ComplianceRequirementListItem>>("/compliance/requirements/", { page_size: "500" })
      .then((r) => { requirements = r.results; }).catch(() => {});
  }

  // --- Shared helpers ---
  const PAGE_SIZE = 25;

  function getVisiblePages(current: number, total: number): number[] {
    if (total <= 0) return [];
    const pages: number[] = [];
    const maxVisible = 7;
    let start = Math.max(1, current - Math.floor(maxVisible / 2));
    let end = Math.min(total, start + maxVisible - 1);
    if (end - start + 1 < maxVisible) start = Math.max(1, end - maxVisible + 1);
    for (let i = start; i <= end; i++) pages.push(i);
    return pages;
  }

  function formatCurrency(v: string | null): string { return v ? currency.formatCompact(v) : "\u2014"; }
  function formatDate(v: string | null): string {
    if (!v) return "\u2014";
    return new Date(v + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }
  function formatDateTime(v: string | null): string {
    if (!v) return "\u2014";
    return new Date(v).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" });
  }

  const categoryLabels: Record<string, string> = {
    regulatory: "Regulatory", environmental: "Environmental", safety: "Safety",
    building_code: "Building Code", zoning: "Zoning", accessibility: "Accessibility",
    fire_safety: "Fire Safety", occupational_health: "Occupational Health",
  };
  const categoryColors: Record<string, string> = {
    regulatory: "bg-blue-50 text-blue-700", environmental: "bg-emerald-50 text-emerald-700",
    safety: "bg-amber-50 text-amber-700", building_code: "bg-violet-50 text-violet-700",
    zoning: "bg-orange-50 text-orange-700", accessibility: "bg-teal-50 text-teal-700",
    fire_safety: "bg-red-50 text-red-700", occupational_health: "bg-pink-50 text-pink-700",
  };
  const frequencyLabels: Record<string, string> = {
    one_time: "One-Time", annual: "Annual", biannual: "Bi-Annual", quarterly: "Quarterly",
  };
  const complianceStatusLabels: Record<string, string> = {
    compliant: "Compliant", non_compliant: "Non-Compliant", pending_review: "Pending Review",
    expired: "Expired", exempt: "Exempt", not_applicable: "N/A",
  };
  const complianceStatusColors: Record<string, string> = {
    compliant: "bg-emerald-50 text-emerald-700", non_compliant: "bg-red-50 text-red-700",
    pending_review: "bg-amber-50 text-amber-700", expired: "bg-red-50 text-red-600",
    exempt: "bg-neutral-100 text-neutral-600", not_applicable: "bg-neutral-50 text-neutral-400",
  };
  const severityLabels: Record<string, string> = { minor: "Minor", moderate: "Moderate", major: "Major", critical: "Critical" };
  const severityColors: Record<string, string> = {
    minor: "bg-neutral-100 text-neutral-600", moderate: "bg-amber-50 text-amber-700",
    major: "bg-orange-50 text-orange-700", critical: "bg-red-50 text-red-700",
  };
  const auditTypeLabels: Record<string, string> = { internal: "Internal", external: "External", regulatory: "Regulatory" };
  const auditRatingLabels: Record<string, string> = {
    compliant: "Compliant", partially_compliant: "Partially Compliant", non_compliant: "Non-Compliant",
  };
  const auditRatingColors: Record<string, string> = {
    compliant: "bg-emerald-50 text-emerald-700", partially_compliant: "bg-amber-50 text-amber-700",
    non_compliant: "bg-red-50 text-red-700",
  };

  function statusDot(s: string): string {
    const map: Record<string, string> = {
      open: "bg-blue-500", under_review: "bg-violet-500", remediation: "bg-amber-500",
      resolved: "bg-emerald-500", closed: "bg-neutral-400", appealed: "bg-orange-500",
      scheduled: "bg-blue-500", in_progress: "bg-amber-500", completed: "bg-emerald-500",
      cancelled: "bg-red-400",
    };
    return map[s] ?? "bg-neutral-300";
  }
  function statusLabel(s: string): string {
    return s.split("_").map(w => w[0].toUpperCase() + w.slice(1)).join(" ");
  }

  let searchTimeout: ReturnType<typeof setTimeout>;
  function debounceSearch(setter: (v: string) => void) {
    return (e: Event) => {
      clearTimeout(searchTimeout);
      const val = (e.target as HTMLInputElement).value;
      searchTimeout = setTimeout(() => setter(val), 300);
    };
  }

  function fieldErr(errors: Record<string, string[]>, key: string): string {
    return errors[key]?.join(", ") ?? "";
  }

  const inputCls = "w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent";
  const selectCls = inputCls;

  // =========================================================================
  //  1. REQUIREMENTS
  // =========================================================================
  let reqData = $state<ComplianceRequirementListItem[]>([]);
  let reqCount = $state(0); let reqPage = $state(1); let reqLoading = $state(false);
  let reqSearch = $state(""); let reqCategory = $state(""); let reqMandatory = $state("");
  const reqPages = $derived(Math.ceil(reqCount / PAGE_SIZE));

  // Create/Edit
  let showReqModal = $state(false); let reqEditingId = $state<number | null>(null);
  let reqSaving = $state(false); let reqErrors = $state<Record<string, string[]>>({});
  let reqForm = $state({ name: "", category: "regulatory" as ComplianceCategory, description: "", regulatory_reference: "", renewal_frequency: "annual" as ComplianceRenewalFrequency, is_mandatory: true, is_active: true });

  // Expand / View / Delete
  let reqExpandedId = $state<number | null>(null);
  let reqDetail = $state<ComplianceRequirement | null>(null);
  let reqViewing = $state<ComplianceRequirement | null>(null);
  let reqDeleteId = $state<number | null>(null); let reqDeleting = $state(false);

  async function fetchReqs() {
    reqLoading = true;
    try {
      const p: Record<string, string> = { page: String(reqPage) };
      if (reqSearch) p.search = reqSearch;
      if (reqCategory) p.category = reqCategory;
      if (reqMandatory) p.is_mandatory = reqMandatory;
      const res = await api.get<PaginatedResponse<ComplianceRequirementListItem>>("/compliance/requirements/", p);
      reqData = res.results; reqCount = res.count;
    } catch { reqData = []; reqCount = 0; }
    reqLoading = false;
  }
  $effect(() => {
    if (activeTab !== "requirements") return;
    void reqSearch; void reqCategory; void reqMandatory; void reqPage;
    fetchReqs();
  });

  async function toggleReqExpand(id: number) {
    if (reqExpandedId === id) { reqExpandedId = null; reqDetail = null; return; }
    try {
      reqDetail = await api.get<ComplianceRequirement>(`/compliance/requirements/${id}/`);
      reqExpandedId = id;
    } catch { toast.error("Error", "Could not load details."); }
  }

  async function viewReq(id: number) {
    try { reqViewing = await api.get<ComplianceRequirement>(`/compliance/requirements/${id}/`); }
    catch { toast.error("Error", "Could not load details."); }
  }

  function openCreateReq() {
    reqEditingId = null;
    reqForm = { name: "", category: "regulatory", description: "", regulatory_reference: "", renewal_frequency: "annual", is_mandatory: true, is_active: true };
    reqErrors = {}; showReqModal = true;
  }

  async function openEditReq(id: number) {
    try {
      const d = await api.get<ComplianceRequirement>(`/compliance/requirements/${id}/`);
      reqEditingId = id;
      reqForm = { name: d.name, category: d.category, description: d.description, regulatory_reference: d.regulatory_reference, renewal_frequency: d.renewal_frequency, is_mandatory: d.is_mandatory, is_active: d.is_active };
      reqErrors = {}; showReqModal = true;
    } catch { toast.error("Error", "Could not load requirement."); }
  }

  function editFromViewReq() {
    if (!reqViewing) return;
    const d = reqViewing; reqViewing = null;
    reqEditingId = d.id;
    reqForm = { name: d.name, category: d.category, description: d.description, regulatory_reference: d.regulatory_reference, renewal_frequency: d.renewal_frequency, is_mandatory: d.is_mandatory, is_active: d.is_active };
    reqErrors = {}; showReqModal = true;
  }

  async function saveReq() {
    reqSaving = true; reqErrors = {};
    try {
      if (reqEditingId) {
        await api.patch(`/compliance/requirements/${reqEditingId}/`, reqForm);
        toast.success("Updated", "Requirement updated");
      } else {
        await api.post("/compliance/requirements/", reqForm);
        toast.success("Created", `"${reqForm.name}" added`);
      }
      showReqModal = false; reqExpandedId = null; reqDetail = null; fetchReqs();
    } catch (e) {
      if (e instanceof ApiError) { reqErrors = e.fieldErrors; toast.error("Validation error", "Fix highlighted fields"); }
      else toast.error("Error", `Could not ${reqEditingId ? "update" : "create"} requirement`);
    }
    reqSaving = false;
  }

  async function deleteReq() {
    if (!reqDeleteId) return;
    reqDeleting = true;
    try {
      await api.delete(`/compliance/requirements/${reqDeleteId}/`);
      toast.success("Deleted", "Requirement removed");
      reqDeleteId = null; reqExpandedId = null; reqDetail = null; fetchReqs();
    } catch { toast.error("Error", "Could not delete requirement"); }
    reqDeleting = false;
  }

  // =========================================================================
  //  2. COMPLIANCE TRACKER
  // =========================================================================
  let trackerData = $state<PropertyComplianceListItem[]>([]);
  let trackerCount = $state(0); let trackerPage = $state(1); let trackerLoading = $state(false);
  let trackerSearch = $state(""); let trackerProperty = $state(""); let trackerStatus = $state("");
  const trackerPages = $derived(Math.ceil(trackerCount / PAGE_SIZE));

  let showTrackerModal = $state(false); let trackerEditingId = $state<number | null>(null);
  let trackerSaving = $state(false); let trackerErrors = $state<Record<string, string[]>>({});
  let trackerForm = $state({ property: 0, requirement: 0, status: "pending_review" as PropertyComplianceStatus, certificate_number: "", issuing_authority: "", issue_date: "", expiry_date: "", next_review_date: "", responsible_person: "", notes: "" });

  let trackerExpandedId = $state<number | null>(null);
  let trackerDetail = $state<PropertyComplianceItem | null>(null);
  let trackerViewing = $state<PropertyComplianceItem | null>(null);
  let trackerDeleteId = $state<number | null>(null); let trackerDeleting = $state(false);

  async function fetchTracker() {
    trackerLoading = true;
    try {
      const p: Record<string, string> = { page: String(trackerPage) };
      if (trackerSearch) p.search = trackerSearch;
      if (trackerProperty) p.property = trackerProperty;
      if (trackerStatus) p.status = trackerStatus;
      const res = await api.get<PaginatedResponse<PropertyComplianceListItem>>("/compliance/tracker/", p);
      trackerData = res.results; trackerCount = res.count;
    } catch { trackerData = []; trackerCount = 0; }
    trackerLoading = false;
  }
  $effect(() => {
    if (activeTab !== "tracker") return;
    ensureRequirements();
    void trackerSearch; void trackerProperty; void trackerStatus; void trackerPage;
    fetchTracker();
  });

  async function toggleTrackerExpand(id: number) {
    if (trackerExpandedId === id) { trackerExpandedId = null; trackerDetail = null; return; }
    try {
      trackerDetail = await api.get<PropertyComplianceItem>(`/compliance/tracker/${id}/`);
      trackerExpandedId = id;
    } catch { toast.error("Error", "Could not load details."); }
  }

  async function viewTracker(id: number) {
    try { trackerViewing = await api.get<PropertyComplianceItem>(`/compliance/tracker/${id}/`); }
    catch { toast.error("Error", "Could not load details."); }
  }

  function openCreateTracker() {
    trackerEditingId = null;
    trackerForm = { property: 0, requirement: 0, status: "pending_review", certificate_number: "", issuing_authority: "", issue_date: "", expiry_date: "", next_review_date: "", responsible_person: "", notes: "" };
    trackerErrors = {}; showTrackerModal = true; ensureRequirements();
  }

  async function openEditTracker(id: number) {
    try {
      const d = await api.get<PropertyComplianceItem>(`/compliance/tracker/${id}/`);
      trackerEditingId = id;
      trackerForm = { property: d.property, requirement: d.requirement, status: d.status, certificate_number: d.certificate_number, issuing_authority: d.issuing_authority, issue_date: d.issue_date ?? "", expiry_date: d.expiry_date ?? "", next_review_date: d.next_review_date ?? "", responsible_person: d.responsible_person, notes: d.notes };
      trackerErrors = {}; showTrackerModal = true; ensureRequirements();
    } catch { toast.error("Error", "Could not load record."); }
  }

  function editFromViewTracker() {
    if (!trackerViewing) return;
    const d = trackerViewing; trackerViewing = null;
    trackerEditingId = d.id;
    trackerForm = { property: d.property, requirement: d.requirement, status: d.status, certificate_number: d.certificate_number, issuing_authority: d.issuing_authority, issue_date: d.issue_date ?? "", expiry_date: d.expiry_date ?? "", next_review_date: d.next_review_date ?? "", responsible_person: d.responsible_person, notes: d.notes };
    trackerErrors = {}; showTrackerModal = true; ensureRequirements();
  }

  async function saveTracker() {
    trackerSaving = true; trackerErrors = {};
    try {
      const payload: Record<string, unknown> = { ...trackerForm };
      if (!trackerForm.issue_date) payload.issue_date = null;
      if (!trackerForm.expiry_date) payload.expiry_date = null;
      if (!trackerForm.next_review_date) payload.next_review_date = null;
      if (trackerEditingId) {
        await api.patch(`/compliance/tracker/${trackerEditingId}/`, payload);
        toast.success("Updated", "Compliance record updated");
      } else {
        await api.post("/compliance/tracker/", payload);
        toast.success("Created", "Compliance record added");
      }
      showTrackerModal = false; trackerExpandedId = null; trackerDetail = null; fetchTracker();
    } catch (e) {
      if (e instanceof ApiError) { trackerErrors = e.fieldErrors; toast.error("Validation error", "Fix highlighted fields"); }
      else toast.error("Error", `Could not ${trackerEditingId ? "update" : "create"} record`);
    }
    trackerSaving = false;
  }

  async function deleteTracker() {
    if (!trackerDeleteId) return;
    trackerDeleting = true;
    try {
      await api.delete(`/compliance/tracker/${trackerDeleteId}/`);
      toast.success("Deleted", "Compliance record removed");
      trackerDeleteId = null; trackerExpandedId = null; trackerDetail = null; fetchTracker();
    } catch { toast.error("Error", "Could not delete record"); }
    trackerDeleting = false;
  }

  // =========================================================================
  //  3. VIOLATIONS
  // =========================================================================
  let violData = $state<ComplianceViolationListItem[]>([]);
  let violCount = $state(0); let violPage = $state(1); let violLoading = $state(false);
  let violSearch = $state(""); let violProperty = $state(""); let violSeverity = $state(""); let violStatus = $state("");
  const violPages = $derived(Math.ceil(violCount / PAGE_SIZE));

  let showViolModal = $state(false); let violEditingId = $state<number | null>(null);
  let violSaving = $state(false); let violErrors = $state<Record<string, string[]>>({});
  let violForm = $state({ property: 0, compliance_item: null as number | null, title: "", description: "", violation_type: "regulatory" as ComplianceCategory, severity: "moderate" as ViolationSeverity, status: "open" as ViolationStatus, reported_date: new Date().toISOString().slice(0, 10), due_date: "", resolved_date: "", corrective_action: "", fine_amount: "", assigned_to: "", notes: "" });

  let violExpandedId = $state<number | null>(null);
  let violDetail = $state<ComplianceViolation | null>(null);
  let violViewing = $state<ComplianceViolation | null>(null);
  let violDeleteId = $state<number | null>(null); let violDeleting = $state(false);

  async function fetchViolations() {
    violLoading = true;
    try {
      const p: Record<string, string> = { page: String(violPage) };
      if (violSearch) p.search = violSearch;
      if (violProperty) p.property = violProperty;
      if (violSeverity) p.severity = violSeverity;
      if (violStatus) p.status = violStatus;
      const res = await api.get<PaginatedResponse<ComplianceViolationListItem>>("/compliance/violations/", p);
      violData = res.results; violCount = res.count;
    } catch { violData = []; violCount = 0; }
    violLoading = false;
  }
  $effect(() => {
    if (activeTab !== "violations") return;
    void violSearch; void violProperty; void violSeverity; void violStatus; void violPage;
    fetchViolations();
  });

  async function toggleViolExpand(id: number) {
    if (violExpandedId === id) { violExpandedId = null; violDetail = null; return; }
    try {
      violDetail = await api.get<ComplianceViolation>(`/compliance/violations/${id}/`);
      violExpandedId = id;
    } catch { toast.error("Error", "Could not load details."); }
  }

  async function viewViol(id: number) {
    try { violViewing = await api.get<ComplianceViolation>(`/compliance/violations/${id}/`); }
    catch { toast.error("Error", "Could not load details."); }
  }

  function openCreateViol() {
    violEditingId = null;
    violForm = { property: 0, compliance_item: null, title: "", description: "", violation_type: "regulatory", severity: "moderate", status: "open", reported_date: new Date().toISOString().slice(0, 10), due_date: "", resolved_date: "", corrective_action: "", fine_amount: "", assigned_to: "", notes: "" };
    violErrors = {}; showViolModal = true;
  }

  async function openEditViol(id: number) {
    try {
      const d = await api.get<ComplianceViolation>(`/compliance/violations/${id}/`);
      violEditingId = id;
      violForm = { property: d.property, compliance_item: d.compliance_item, title: d.title, description: d.description, violation_type: d.violation_type, severity: d.severity, status: d.status, reported_date: d.reported_date, due_date: d.due_date ?? "", resolved_date: d.resolved_date ?? "", corrective_action: d.corrective_action, fine_amount: d.fine_amount ?? "", assigned_to: d.assigned_to, notes: d.notes };
      violErrors = {}; showViolModal = true;
    } catch { toast.error("Error", "Could not load violation."); }
  }

  function editFromViewViol() {
    if (!violViewing) return;
    const d = violViewing; violViewing = null;
    violEditingId = d.id;
    violForm = { property: d.property, compliance_item: d.compliance_item, title: d.title, description: d.description, violation_type: d.violation_type, severity: d.severity, status: d.status, reported_date: d.reported_date, due_date: d.due_date ?? "", resolved_date: d.resolved_date ?? "", corrective_action: d.corrective_action, fine_amount: d.fine_amount ?? "", assigned_to: d.assigned_to, notes: d.notes };
    violErrors = {}; showViolModal = true;
  }

  async function saveViol() {
    violSaving = true; violErrors = {};
    try {
      const payload: Record<string, unknown> = { ...violForm };
      if (!violForm.due_date) payload.due_date = null;
      if (!violForm.resolved_date) payload.resolved_date = null;
      if (!violForm.fine_amount) payload.fine_amount = null;
      if (!violForm.compliance_item) payload.compliance_item = null;
      if (violEditingId) {
        await api.patch(`/compliance/violations/${violEditingId}/`, payload);
        toast.success("Updated", "Violation updated");
      } else {
        await api.post("/compliance/violations/", payload);
        toast.success("Created", `"${violForm.title}" logged`);
      }
      showViolModal = false; violExpandedId = null; violDetail = null; fetchViolations();
    } catch (e) {
      if (e instanceof ApiError) { violErrors = e.fieldErrors; toast.error("Validation error", "Fix highlighted fields"); }
      else toast.error("Error", `Could not ${violEditingId ? "update" : "create"} violation`);
    }
    violSaving = false;
  }

  async function deleteViol() {
    if (!violDeleteId) return;
    violDeleting = true;
    try {
      await api.delete(`/compliance/violations/${violDeleteId}/`);
      toast.success("Deleted", "Violation removed");
      violDeleteId = null; violExpandedId = null; violDetail = null; fetchViolations();
    } catch { toast.error("Error", "Could not delete violation"); }
    violDeleting = false;
  }

  // =========================================================================
  //  4. AUDITS
  // =========================================================================
  let auditData = $state<ComplianceAuditListItem[]>([]);
  let auditCount = $state(0); let auditPage = $state(1); let auditLoading = $state(false);
  let auditSearch = $state(""); let auditProperty = $state(""); let auditType = $state(""); let auditStatus = $state("");
  const auditPages = $derived(Math.ceil(auditCount / PAGE_SIZE));

  let showAuditModal = $state(false); let auditEditingId = $state<number | null>(null);
  let auditSaving = $state(false); let auditErrors = $state<Record<string, string[]>>({});
  let auditForm = $state({ property: 0, title: "", audit_type: "internal" as ComplianceAuditType, status: "scheduled" as ComplianceAuditStatus, scheduled_date: "", completed_date: "", auditor: "", scope: "", findings: "", overall_rating: "" as ComplianceAuditRating | "", follow_up_required: false, follow_up_notes: "", notes: "" });

  let auditExpandedId = $state<number | null>(null);
  let auditDetail = $state<ComplianceAuditItem | null>(null);
  let auditViewing = $state<ComplianceAuditItem | null>(null);
  let auditDeleteId = $state<number | null>(null); let auditDeleting = $state(false);

  async function fetchAudits() {
    auditLoading = true;
    try {
      const p: Record<string, string> = { page: String(auditPage) };
      if (auditSearch) p.search = auditSearch;
      if (auditProperty) p.property = auditProperty;
      if (auditType) p.audit_type = auditType;
      if (auditStatus) p.status = auditStatus;
      const res = await api.get<PaginatedResponse<ComplianceAuditListItem>>("/compliance/audits/", p);
      auditData = res.results; auditCount = res.count;
    } catch { auditData = []; auditCount = 0; }
    auditLoading = false;
  }
  $effect(() => {
    if (activeTab !== "audits") return;
    void auditSearch; void auditProperty; void auditType; void auditStatus; void auditPage;
    fetchAudits();
  });

  async function toggleAuditExpand(id: number) {
    if (auditExpandedId === id) { auditExpandedId = null; auditDetail = null; return; }
    try {
      auditDetail = await api.get<ComplianceAuditItem>(`/compliance/audits/${id}/`);
      auditExpandedId = id;
    } catch { toast.error("Error", "Could not load details."); }
  }

  async function viewAudit(id: number) {
    try { auditViewing = await api.get<ComplianceAuditItem>(`/compliance/audits/${id}/`); }
    catch { toast.error("Error", "Could not load details."); }
  }

  function openCreateAudit() {
    auditEditingId = null;
    auditForm = { property: 0, title: "", audit_type: "internal", status: "scheduled", scheduled_date: "", completed_date: "", auditor: "", scope: "", findings: "", overall_rating: "", follow_up_required: false, follow_up_notes: "", notes: "" };
    auditErrors = {}; showAuditModal = true;
  }

  async function openEditAudit(id: number) {
    try {
      const d = await api.get<ComplianceAuditItem>(`/compliance/audits/${id}/`);
      auditEditingId = id;
      auditForm = { property: d.property, title: d.title, audit_type: d.audit_type, status: d.status, scheduled_date: d.scheduled_date, completed_date: d.completed_date ?? "", auditor: d.auditor, scope: d.scope, findings: d.findings, overall_rating: d.overall_rating ?? "", follow_up_required: d.follow_up_required, follow_up_notes: d.follow_up_notes, notes: d.notes };
      auditErrors = {}; showAuditModal = true;
    } catch { toast.error("Error", "Could not load audit."); }
  }

  function editFromViewAudit() {
    if (!auditViewing) return;
    const d = auditViewing; auditViewing = null;
    auditEditingId = d.id;
    auditForm = { property: d.property, title: d.title, audit_type: d.audit_type, status: d.status, scheduled_date: d.scheduled_date, completed_date: d.completed_date ?? "", auditor: d.auditor, scope: d.scope, findings: d.findings, overall_rating: d.overall_rating ?? "", follow_up_required: d.follow_up_required, follow_up_notes: d.follow_up_notes, notes: d.notes };
    auditErrors = {}; showAuditModal = true;
  }

  async function saveAudit() {
    auditSaving = true; auditErrors = {};
    try {
      const payload: Record<string, unknown> = { ...auditForm };
      if (!auditForm.completed_date) payload.completed_date = null;
      if (!auditForm.overall_rating) payload.overall_rating = null;
      if (auditEditingId) {
        await api.patch(`/compliance/audits/${auditEditingId}/`, payload);
        toast.success("Updated", "Audit updated");
      } else {
        await api.post("/compliance/audits/", payload);
        toast.success("Created", `"${auditForm.title}" scheduled`);
      }
      showAuditModal = false; auditExpandedId = null; auditDetail = null; fetchAudits();
    } catch (e) {
      if (e instanceof ApiError) { auditErrors = e.fieldErrors; toast.error("Validation error", "Fix highlighted fields"); }
      else toast.error("Error", `Could not ${auditEditingId ? "update" : "create"} audit`);
    }
    auditSaving = false;
  }

  async function deleteAudit() {
    if (!auditDeleteId) return;
    auditDeleting = true;
    try {
      await api.delete(`/compliance/audits/${auditDeleteId}/`);
      toast.success("Deleted", "Audit removed");
      auditDeleteId = null; auditExpandedId = null; auditDetail = null; fetchAudits();
    } catch { toast.error("Error", "Could not delete audit"); }
    auditDeleting = false;
  }
</script>

{#snippet searchIcon()}
  <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
{/snippet}

{#snippet chevron(expanded: boolean)}
  <svg class="w-3.5 h-3.5 text-neutral-400 transition-transform shrink-0 {expanded ? 'rotate-90' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" /></svg>
{/snippet}

{#snippet pagination(page: number, pages: number, setPage: (p: number) => void)}
  {#if pages > 1}
    <div class="flex items-center justify-between border-t border-neutral-200 px-5 py-3.5">
      <p class="text-sm text-neutral-500">Page {page} of {pages}</p>
      <div class="flex items-center gap-1">
        <button onclick={() => setPage(Math.max(1, page - 1))} disabled={page === 1} class="rounded-lg border border-neutral-200 px-2.5 py-1.5 text-sm text-neutral-600 hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed">Prev</button>
        {#each getVisiblePages(page, pages) as pg}
          <button onclick={() => setPage(pg)} class="min-w-8 rounded-lg px-2.5 py-1.5 text-sm font-medium transition-colors {pg === page ? 'bg-neutral-900 text-white' : 'text-neutral-600 hover:bg-neutral-50'}">{pg}</button>
        {/each}
        <button onclick={() => setPage(Math.min(pages, page + 1))} disabled={page === pages} class="rounded-lg border border-neutral-200 px-2.5 py-1.5 text-sm text-neutral-600 hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed">Next</button>
      </div>
    </div>
  {/if}
{/snippet}

{#snippet detailField(label: string, value: string, wide?: boolean)}
  <div class={wide ? "col-span-full" : ""}>
    <p class="text-xs font-medium text-neutral-400 uppercase tracking-wider mb-1">{label}</p>
    <p class="text-sm text-neutral-700 whitespace-pre-wrap">{value || "\u2014"}</p>
  </div>
{/snippet}

{#snippet actionBtns(onView: () => void, onEdit: () => void, onDelete: () => void)}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <td class="px-5 py-4 text-right" onclick={(e: MouseEvent) => e.stopPropagation()}>
    <div class="flex items-center justify-end gap-1">
      <button onclick={onView} class="rounded-lg px-2.5 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 transition-colors">View</button>
      <button onclick={onEdit} class="rounded-lg px-2.5 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 transition-colors">Edit</button>
      <button onclick={onDelete} class="rounded-lg px-2.5 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 transition-colors">Delete</button>
    </div>
  </td>
{/snippet}

<div class="space-y-6">
  <!-- Header -->
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Compliance</h1>
    <p class="text-sm text-neutral-400 mt-1">Manage compliance requirements, track property compliance, violations, and audits</p>
  </div>

  <!-- Tabs -->
  <div class="border-b border-neutral-200">
    <nav class="flex gap-6" aria-label="Tabs">
      {#each tabs as tab}
        <button onclick={() => { activeTab = tab.key; }} class="pb-3 text-sm font-medium border-b-2 transition-colors -mb-px {activeTab === tab.key ? 'border-neutral-900 text-neutral-900' : 'border-transparent text-neutral-400 hover:text-neutral-600 hover:border-neutral-300'}">
          {tab.label}
        </button>
      {/each}
    </nav>
  </div>

  <!-- ================================================================ -->
  <!--  1. REQUIREMENTS TAB                                             -->
  <!-- ================================================================ -->
  {#if activeTab === "requirements"}
    <div class="flex items-center justify-between">
      <p class="text-sm text-neutral-400">{reqCount} requirement{reqCount !== 1 ? "s" : ""}</p>
      <button onclick={openCreateReq} class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg hover:bg-neutral-800 text-sm font-medium transition-colors">+ New Requirement</button>
    </div>

    <div class="flex gap-3 items-center">
      <div class="relative flex-1 max-w-sm">
        {@render searchIcon()}
        <input type="text" placeholder="Search requirements..." oninput={debounceSearch(v => { reqSearch = v; reqPage = 1; })} class="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent placeholder:text-neutral-400" />
      </div>
      <select bind:value={reqCategory} onchange={() => (reqPage = 1)} class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent">
        <option value="">All Categories</option>
        {#each Object.entries(categoryLabels) as [k, v]}<option value={k}>{v}</option>{/each}
      </select>
      <select bind:value={reqMandatory} onchange={() => (reqPage = 1)} class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent">
        <option value="">All</option>
        <option value="true">Mandatory</option>
        <option value="false">Optional</option>
      </select>
    </div>

    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      {#if reqLoading}
        <div class="p-16 text-center"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div><p class="mt-3 text-sm text-neutral-400">Loading...</p></div>
      {:else if reqData.length === 0}
        <div class="p-16 text-center"><p class="text-sm font-medium text-neutral-900">No requirements found</p><p class="mt-1 text-sm text-neutral-400">Add your first compliance requirement to get started.</p></div>
      {:else}
        <table class="w-full text-sm">
          <thead><tr class="border-b border-neutral-200">
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Name</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Category</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Reg. Reference</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Frequency</th>
            <th class="px-5 py-3.5 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Mandatory</th>
            <th class="px-5 py-3.5 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Active</th>
            <th class="px-5 py-3.5 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Properties</th>
            <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Actions</th>
          </tr></thead>
          <tbody class="divide-y divide-neutral-100">
            {#each reqData as item}
              <tr onclick={() => toggleReqExpand(item.id)} class="hover:bg-neutral-50 cursor-pointer transition-colors">
                <td class="px-5 py-4"><div class="flex items-center gap-2">{@render chevron(reqExpandedId === item.id)}<span class="font-medium text-neutral-900">{item.name}</span></div></td>
                <td class="px-5 py-4"><span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {categoryColors[item.category] ?? 'bg-neutral-100 text-neutral-600'}">{categoryLabels[item.category] ?? item.category}</span></td>
                <td class="px-5 py-4 text-neutral-500">{item.regulatory_reference || "\u2014"}</td>
                <td class="px-5 py-4 text-neutral-500">{frequencyLabels[item.renewal_frequency] ?? item.renewal_frequency}</td>
                <td class="px-5 py-4 text-center">
                  {#if item.is_mandatory}<span class="inline-flex items-center gap-1.5 text-xs font-medium text-neutral-900"><span class="w-1.5 h-1.5 rounded-full bg-neutral-900"></span>Yes</span>
                  {:else}<span class="text-xs text-neutral-400">No</span>{/if}
                </td>
                <td class="px-5 py-4 text-center">
                  {#if item.is_active}<span class="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-700"><span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>Active</span>
                  {:else}<span class="inline-flex items-center gap-1.5 text-xs font-medium text-neutral-400"><span class="w-1.5 h-1.5 rounded-full bg-neutral-300"></span>Inactive</span>{/if}
                </td>
                <td class="px-5 py-4 text-center text-neutral-500">{item.property_count}</td>
                {@render actionBtns(() => viewReq(item.id), () => openEditReq(item.id), () => (reqDeleteId = item.id))}
              </tr>
              {#if reqExpandedId === item.id && reqDetail}
                <tr class="bg-neutral-50">
                  <td colspan="8" class="px-8 py-5">
                    <div class="grid grid-cols-3 gap-x-8 gap-y-4">
                      {@render detailField("Description", reqDetail.description, true)}
                      {@render detailField("Created", formatDateTime(reqDetail.created_at))}
                      {@render detailField("Last Updated", formatDateTime(reqDetail.updated_at))}
                    </div>
                  </td>
                </tr>
              {/if}
            {/each}
          </tbody>
        </table>
        {@render pagination(reqPage, reqPages, (p) => (reqPage = p))}
      {/if}
    </div>

  <!-- ================================================================ -->
  <!--  2. COMPLIANCE TRACKER TAB                                       -->
  <!-- ================================================================ -->
  {:else if activeTab === "tracker"}
    <div class="flex items-center justify-between">
      <p class="text-sm text-neutral-400">{trackerCount} record{trackerCount !== 1 ? "s" : ""}</p>
      <button onclick={openCreateTracker} class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg hover:bg-neutral-800 text-sm font-medium transition-colors">+ New Record</button>
    </div>

    <div class="flex gap-3 items-center">
      <div class="relative flex-1 max-w-sm">
        {@render searchIcon()}
        <input type="text" placeholder="Search records..." oninput={debounceSearch(v => { trackerSearch = v; trackerPage = 1; })} class="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent placeholder:text-neutral-400" />
      </div>
      <select bind:value={trackerProperty} onchange={() => (trackerPage = 1)} class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent">
        <option value="">All Properties</option>
        {#each properties as p}<option value={String(p.id)}>{p.name}</option>{/each}
      </select>
      <select bind:value={trackerStatus} onchange={() => (trackerPage = 1)} class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent">
        <option value="">All Statuses</option>
        {#each Object.entries(complianceStatusLabels) as [k, v]}<option value={k}>{v}</option>{/each}
      </select>
    </div>

    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      {#if trackerLoading}
        <div class="p-16 text-center"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div><p class="mt-3 text-sm text-neutral-400">Loading...</p></div>
      {:else if trackerData.length === 0}
        <div class="p-16 text-center"><p class="text-sm font-medium text-neutral-900">No compliance records found</p><p class="mt-1 text-sm text-neutral-400">Start tracking property compliance.</p></div>
      {:else}
        <table class="w-full text-sm">
          <thead><tr class="border-b border-neutral-200">
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Property</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Requirement</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Certificate #</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Expiry</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Next Review</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Responsible</th>
            <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Actions</th>
          </tr></thead>
          <tbody class="divide-y divide-neutral-100">
            {#each trackerData as item}
              {@const isExpired = item.expiry_date && new Date(item.expiry_date) < new Date()}
              <tr onclick={() => toggleTrackerExpand(item.id)} class="hover:bg-neutral-50 cursor-pointer transition-colors">
                <td class="px-5 py-4"><div class="flex items-center gap-2">{@render chevron(trackerExpandedId === item.id)}<span class="font-medium text-neutral-900">{item.property_name}</span></div></td>
                <td class="px-5 py-4 text-neutral-700">{item.requirement_name}</td>
                <td class="px-5 py-4"><span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {complianceStatusColors[item.status] ?? 'bg-neutral-100 text-neutral-600'}">{complianceStatusLabels[item.status] ?? item.status}</span></td>
                <td class="px-5 py-4 text-neutral-500">{item.certificate_number || "\u2014"}</td>
                <td class="px-5 py-4 {isExpired ? 'text-red-600 font-medium' : 'text-neutral-500'}">{formatDate(item.expiry_date)}</td>
                <td class="px-5 py-4 text-neutral-500">{formatDate(item.next_review_date)}</td>
                <td class="px-5 py-4 text-neutral-500">{item.responsible_person || "\u2014"}</td>
                {@render actionBtns(() => viewTracker(item.id), () => openEditTracker(item.id), () => (trackerDeleteId = item.id))}
              </tr>
              {#if trackerExpandedId === item.id && trackerDetail}
                <tr class="bg-neutral-50">
                  <td colspan="8" class="px-8 py-5">
                    <div class="grid grid-cols-3 gap-x-8 gap-y-4">
                      {@render detailField("Category", categoryLabels[trackerDetail.requirement_category] ?? trackerDetail.requirement_category)}
                      {@render detailField("Issuing Authority", trackerDetail.issuing_authority)}
                      {@render detailField("Issue Date", formatDate(trackerDetail.issue_date))}
                      {@render detailField("Last Reviewed", formatDate(trackerDetail.last_reviewed_date))}
                      {@render detailField("Created", formatDateTime(trackerDetail.created_at))}
                      {@render detailField("Last Updated", formatDateTime(trackerDetail.updated_at))}
                      {@render detailField("Notes", trackerDetail.notes, true)}
                    </div>
                  </td>
                </tr>
              {/if}
            {/each}
          </tbody>
        </table>
        {@render pagination(trackerPage, trackerPages, (p) => (trackerPage = p))}
      {/if}
    </div>

  <!-- ================================================================ -->
  <!--  3. VIOLATIONS TAB                                               -->
  <!-- ================================================================ -->
  {:else if activeTab === "violations"}
    <div class="flex items-center justify-between">
      <p class="text-sm text-neutral-400">{violCount} violation{violCount !== 1 ? "s" : ""}</p>
      <button onclick={openCreateViol} class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg hover:bg-neutral-800 text-sm font-medium transition-colors">+ New Violation</button>
    </div>

    <div class="flex gap-3 items-center">
      <div class="relative flex-1 max-w-sm">
        {@render searchIcon()}
        <input type="text" placeholder="Search violations..." oninput={debounceSearch(v => { violSearch = v; violPage = 1; })} class="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent placeholder:text-neutral-400" />
      </div>
      <select bind:value={violProperty} onchange={() => (violPage = 1)} class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent">
        <option value="">All Properties</option>
        {#each properties as p}<option value={String(p.id)}>{p.name}</option>{/each}
      </select>
      <select bind:value={violSeverity} onchange={() => (violPage = 1)} class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent">
        <option value="">All Severities</option>
        {#each Object.entries(severityLabels) as [k, v]}<option value={k}>{v}</option>{/each}
      </select>
      <select bind:value={violStatus} onchange={() => (violPage = 1)} class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent">
        <option value="">All Statuses</option>
        <option value="open">Open</option><option value="under_review">Under Review</option>
        <option value="remediation">Remediation</option><option value="resolved">Resolved</option>
        <option value="closed">Closed</option><option value="appealed">Appealed</option>
      </select>
    </div>

    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      {#if violLoading}
        <div class="p-16 text-center"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div><p class="mt-3 text-sm text-neutral-400">Loading...</p></div>
      {:else if violData.length === 0}
        <div class="p-16 text-center"><p class="text-sm font-medium text-neutral-900">No violations found</p><p class="mt-1 text-sm text-neutral-400">A clean record. Violations will appear here when logged.</p></div>
      {:else}
        <table class="w-full text-sm">
          <thead><tr class="border-b border-neutral-200">
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Title</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Property</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Severity</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Reported</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Due</th>
            <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Fine</th>
            <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Actions</th>
          </tr></thead>
          <tbody class="divide-y divide-neutral-100">
            {#each violData as item}
              {@const isOverdue = item.due_date && !item.resolved_date && new Date(item.due_date) < new Date()}
              <tr onclick={() => toggleViolExpand(item.id)} class="hover:bg-neutral-50 cursor-pointer transition-colors">
                <td class="px-5 py-4"><div class="flex items-center gap-2">{@render chevron(violExpandedId === item.id)}<span class="font-medium text-neutral-900">{item.title}</span></div></td>
                <td class="px-5 py-4 text-neutral-500">{item.property_name}</td>
                <td class="px-5 py-4"><span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {severityColors[item.severity] ?? 'bg-neutral-100 text-neutral-600'}">{severityLabels[item.severity] ?? item.severity}</span></td>
                <td class="px-5 py-4"><span class="inline-flex items-center gap-1.5 text-xs font-medium"><span class="w-1.5 h-1.5 rounded-full {statusDot(item.status)}"></span>{statusLabel(item.status)}</span></td>
                <td class="px-5 py-4 text-neutral-500">{formatDate(item.reported_date)}</td>
                <td class="px-5 py-4 {isOverdue ? 'text-red-600 font-medium' : 'text-neutral-500'}">{formatDate(item.due_date)}</td>
                <td class="px-5 py-4 text-right text-neutral-900 tabular-nums">{formatCurrency(item.fine_amount)}</td>
                {@render actionBtns(() => viewViol(item.id), () => openEditViol(item.id), () => (violDeleteId = item.id))}
              </tr>
              {#if violExpandedId === item.id && violDetail}
                <tr class="bg-neutral-50">
                  <td colspan="8" class="px-8 py-5">
                    <div class="grid grid-cols-3 gap-x-8 gap-y-4">
                      {@render detailField("Type", categoryLabels[violDetail.violation_type] ?? violDetail.violation_type)}
                      {@render detailField("Assigned To", violDetail.assigned_to)}
                      {@render detailField("Resolved", formatDate(violDetail.resolved_date))}
                      {@render detailField("Description", violDetail.description, true)}
                      {@render detailField("Corrective Action", violDetail.corrective_action, true)}
                      {@render detailField("Notes", violDetail.notes, true)}
                      {@render detailField("Created", formatDateTime(violDetail.created_at))}
                      {@render detailField("Last Updated", formatDateTime(violDetail.updated_at))}
                    </div>
                  </td>
                </tr>
              {/if}
            {/each}
          </tbody>
        </table>
        {@render pagination(violPage, violPages, (p) => (violPage = p))}
      {/if}
    </div>

  <!-- ================================================================ -->
  <!--  4. AUDITS TAB                                                   -->
  <!-- ================================================================ -->
  {:else if activeTab === "audits"}
    <div class="flex items-center justify-between">
      <p class="text-sm text-neutral-400">{auditCount} audit{auditCount !== 1 ? "s" : ""}</p>
      <button onclick={openCreateAudit} class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg hover:bg-neutral-800 text-sm font-medium transition-colors">+ New Audit</button>
    </div>

    <div class="flex gap-3 items-center">
      <div class="relative flex-1 max-w-sm">
        {@render searchIcon()}
        <input type="text" placeholder="Search audits..." oninput={debounceSearch(v => { auditSearch = v; auditPage = 1; })} class="w-full pl-10 pr-4 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent placeholder:text-neutral-400" />
      </div>
      <select bind:value={auditProperty} onchange={() => (auditPage = 1)} class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent">
        <option value="">All Properties</option>
        {#each properties as p}<option value={String(p.id)}>{p.name}</option>{/each}
      </select>
      <select bind:value={auditType} onchange={() => (auditPage = 1)} class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent">
        <option value="">All Types</option>
        {#each Object.entries(auditTypeLabels) as [k, v]}<option value={k}>{v}</option>{/each}
      </select>
      <select bind:value={auditStatus} onchange={() => (auditPage = 1)} class="px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white text-neutral-600 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent">
        <option value="">All Statuses</option>
        <option value="scheduled">Scheduled</option><option value="in_progress">In Progress</option>
        <option value="completed">Completed</option><option value="cancelled">Cancelled</option>
      </select>
    </div>

    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      {#if auditLoading}
        <div class="p-16 text-center"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div><p class="mt-3 text-sm text-neutral-400">Loading...</p></div>
      {:else if auditData.length === 0}
        <div class="p-16 text-center"><p class="text-sm font-medium text-neutral-900">No audits found</p><p class="mt-1 text-sm text-neutral-400">Schedule your first compliance audit.</p></div>
      {:else}
        <table class="w-full text-sm">
          <thead><tr class="border-b border-neutral-200">
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Title</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Property</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Type</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Scheduled</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Auditor</th>
            <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Rating</th>
            <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Actions</th>
          </tr></thead>
          <tbody class="divide-y divide-neutral-100">
            {#each auditData as item}
              <tr onclick={() => toggleAuditExpand(item.id)} class="hover:bg-neutral-50 cursor-pointer transition-colors">
                <td class="px-5 py-4"><div class="flex items-center gap-2">{@render chevron(auditExpandedId === item.id)}<span class="font-medium text-neutral-900">{item.title}</span></div></td>
                <td class="px-5 py-4 text-neutral-500">{item.property_name}</td>
                <td class="px-5 py-4 text-neutral-500">{auditTypeLabels[item.audit_type] ?? item.audit_type}</td>
                <td class="px-5 py-4"><span class="inline-flex items-center gap-1.5 text-xs font-medium"><span class="w-1.5 h-1.5 rounded-full {statusDot(item.status)}"></span>{statusLabel(item.status)}</span></td>
                <td class="px-5 py-4 text-neutral-500">{formatDate(item.scheduled_date)}</td>
                <td class="px-5 py-4 text-neutral-500">{item.auditor || "\u2014"}</td>
                <td class="px-5 py-4">
                  {#if item.overall_rating}<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {auditRatingColors[item.overall_rating] ?? 'bg-neutral-100 text-neutral-600'}">{auditRatingLabels[item.overall_rating] ?? item.overall_rating}</span>
                  {:else}<span class="text-neutral-400">{"\u2014"}</span>{/if}
                </td>
                {@render actionBtns(() => viewAudit(item.id), () => openEditAudit(item.id), () => (auditDeleteId = item.id))}
              </tr>
              {#if auditExpandedId === item.id && auditDetail}
                <tr class="bg-neutral-50">
                  <td colspan="8" class="px-8 py-5">
                    <div class="grid grid-cols-3 gap-x-8 gap-y-4">
                      {@render detailField("Completed", formatDate(auditDetail.completed_date))}
                      {@render detailField("Follow-up Required", auditDetail.follow_up_required ? "Yes" : "No")}
                      {@render detailField("Created", formatDateTime(auditDetail.created_at))}
                      {@render detailField("Scope", auditDetail.scope, true)}
                      {@render detailField("Findings", auditDetail.findings, true)}
                      {@render detailField("Follow-up Notes", auditDetail.follow_up_notes, true)}
                      {@render detailField("Notes", auditDetail.notes, true)}
                    </div>
                  </td>
                </tr>
              {/if}
            {/each}
          </tbody>
        </table>
        {@render pagination(auditPage, auditPages, (p) => (auditPage = p))}
      {/if}
    </div>
  {/if}
</div>

<!-- ======================================================================== -->
<!--  CREATE / EDIT MODALS                                                     -->
<!-- ======================================================================== -->

<!-- Requirement Modal -->
{#if showReqModal}
  <div class="fixed inset-0 z-50 flex items-start justify-center pt-[10vh]">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (showReqModal = false)} aria-label="Close"></button>
    <div class="relative w-full max-w-lg mx-4 rounded-2xl bg-white shadow-2xl border border-neutral-200 overflow-hidden">
      <div class="h-1 bg-neutral-900"></div>
      <form onsubmit={(e) => { e.preventDefault(); saveReq(); }} class="p-6 space-y-4">
        <h2 class="text-lg font-bold text-neutral-900">{reqEditingId ? "Edit Requirement" : "New Compliance Requirement"}</h2>
        <div>
          <label for="req-name" class="block text-sm font-medium text-neutral-700 mb-1">Name *</label>
          <input id="req-name" bind:value={reqForm.name} required class={inputCls} />
          {#if fieldErr(reqErrors, "name")}<p class="text-xs text-red-600 mt-1">{fieldErr(reqErrors, "name")}</p>{/if}
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="req-cat" class="block text-sm font-medium text-neutral-700 mb-1">Category *</label>
            <select id="req-cat" bind:value={reqForm.category} class={selectCls}>{#each Object.entries(categoryLabels) as [k, v]}<option value={k}>{v}</option>{/each}</select>
          </div>
          <div>
            <label for="req-freq" class="block text-sm font-medium text-neutral-700 mb-1">Renewal Frequency</label>
            <select id="req-freq" bind:value={reqForm.renewal_frequency} class={selectCls}>{#each Object.entries(frequencyLabels) as [k, v]}<option value={k}>{v}</option>{/each}</select>
          </div>
        </div>
        <div>
          <label for="req-ref" class="block text-sm font-medium text-neutral-700 mb-1">Regulatory Reference</label>
          <input id="req-ref" bind:value={reqForm.regulatory_reference} class={inputCls} placeholder="e.g., OSHA 29 CFR 1926" />
        </div>
        <div>
          <label for="req-desc" class="block text-sm font-medium text-neutral-700 mb-1">Description</label>
          <textarea id="req-desc" bind:value={reqForm.description} rows="2" class={inputCls}></textarea>
        </div>
        <div class="flex items-center gap-6">
          <label class="flex items-center gap-2 text-sm text-neutral-700"><input type="checkbox" bind:checked={reqForm.is_mandatory} class="rounded border-neutral-300" /> Mandatory</label>
          <label class="flex items-center gap-2 text-sm text-neutral-700"><input type="checkbox" bind:checked={reqForm.is_active} class="rounded border-neutral-300" /> Active</label>
        </div>
        <div class="flex justify-end gap-3 pt-2">
          <button type="button" onclick={() => (showReqModal = false)} class="px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">Cancel</button>
          <button type="submit" disabled={reqSaving} class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">{reqSaving ? "Saving..." : reqEditingId ? "Update" : "Create"}</button>
        </div>
      </form>
    </div>
  </div>
{/if}

<!-- Tracker Modal -->
{#if showTrackerModal}
  <div class="fixed inset-0 z-50 flex items-start justify-center pt-[10vh]">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (showTrackerModal = false)} aria-label="Close"></button>
    <div class="relative w-full max-w-lg mx-4 rounded-2xl bg-white shadow-2xl border border-neutral-200 overflow-hidden">
      <div class="h-1 bg-neutral-900"></div>
      <form onsubmit={(e) => { e.preventDefault(); saveTracker(); }} class="p-6 space-y-4">
        <h2 class="text-lg font-bold text-neutral-900">{trackerEditingId ? "Edit Compliance Record" : "New Compliance Record"}</h2>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="tr-prop" class="block text-sm font-medium text-neutral-700 mb-1">Property *</label>
            <select id="tr-prop" bind:value={trackerForm.property} required class={selectCls}>
              <option value={0} disabled>Select property</option>
              {#each properties as p}<option value={p.id}>{p.name}</option>{/each}
            </select>
            {#if fieldErr(trackerErrors, "property")}<p class="text-xs text-red-600 mt-1">{fieldErr(trackerErrors, "property")}</p>{/if}
          </div>
          <div>
            <label for="tr-req" class="block text-sm font-medium text-neutral-700 mb-1">Requirement *</label>
            <select id="tr-req" bind:value={trackerForm.requirement} required class={selectCls}>
              <option value={0} disabled>Select requirement</option>
              {#each requirements as r}<option value={r.id}>{r.name}</option>{/each}
            </select>
            {#if fieldErr(trackerErrors, "requirement")}<p class="text-xs text-red-600 mt-1">{fieldErr(trackerErrors, "requirement")}</p>{/if}
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="tr-status" class="block text-sm font-medium text-neutral-700 mb-1">Status</label>
            <select id="tr-status" bind:value={trackerForm.status} class={selectCls}>{#each Object.entries(complianceStatusLabels) as [k, v]}<option value={k}>{v}</option>{/each}</select>
          </div>
          <div>
            <label for="tr-cert" class="block text-sm font-medium text-neutral-700 mb-1">Certificate #</label>
            <input id="tr-cert" bind:value={trackerForm.certificate_number} class={inputCls} />
          </div>
        </div>
        <div>
          <label for="tr-auth" class="block text-sm font-medium text-neutral-700 mb-1">Issuing Authority</label>
          <input id="tr-auth" bind:value={trackerForm.issuing_authority} class={inputCls} />
        </div>
        <div class="grid grid-cols-3 gap-4">
          <div>
            <label for="tr-issue" class="block text-sm font-medium text-neutral-700 mb-1">Issue Date</label>
            <DateInput id="tr-issue" bind:value={trackerForm.issue_date} />
          </div>
          <div>
            <label for="tr-expiry" class="block text-sm font-medium text-neutral-700 mb-1">Expiry Date</label>
            <DateInput id="tr-expiry" bind:value={trackerForm.expiry_date} />
          </div>
          <div>
            <label for="tr-review" class="block text-sm font-medium text-neutral-700 mb-1">Next Review</label>
            <DateInput id="tr-review" bind:value={trackerForm.next_review_date} />
          </div>
        </div>
        <div>
          <label for="tr-resp" class="block text-sm font-medium text-neutral-700 mb-1">Responsible Person</label>
          <input id="tr-resp" bind:value={trackerForm.responsible_person} class={inputCls} />
        </div>
        <div>
          <label for="tr-notes" class="block text-sm font-medium text-neutral-700 mb-1">Notes</label>
          <textarea id="tr-notes" bind:value={trackerForm.notes} rows="2" class={inputCls}></textarea>
        </div>
        <div class="flex justify-end gap-3 pt-2">
          <button type="button" onclick={() => (showTrackerModal = false)} class="px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">Cancel</button>
          <button type="submit" disabled={trackerSaving} class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">{trackerSaving ? "Saving..." : trackerEditingId ? "Update" : "Create"}</button>
        </div>
      </form>
    </div>
  </div>
{/if}

<!-- Violation Modal -->
{#if showViolModal}
  <div class="fixed inset-0 z-50 flex items-start justify-center pt-[10vh]">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (showViolModal = false)} aria-label="Close"></button>
    <div class="relative w-full max-w-lg mx-4 rounded-2xl bg-white shadow-2xl border border-neutral-200 overflow-hidden max-h-[80vh] overflow-y-auto">
      <div class="h-1 bg-neutral-900"></div>
      <form onsubmit={(e) => { e.preventDefault(); saveViol(); }} class="p-6 space-y-4">
        <h2 class="text-lg font-bold text-neutral-900">{violEditingId ? "Edit Violation" : "New Violation"}</h2>
        <div>
          <label for="viol-title" class="block text-sm font-medium text-neutral-700 mb-1">Title *</label>
          <input id="viol-title" bind:value={violForm.title} required class={inputCls} />
          {#if fieldErr(violErrors, "title")}<p class="text-xs text-red-600 mt-1">{fieldErr(violErrors, "title")}</p>{/if}
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="viol-prop" class="block text-sm font-medium text-neutral-700 mb-1">Property *</label>
            <select id="viol-prop" bind:value={violForm.property} required class={selectCls}>
              <option value={0} disabled>Select property</option>
              {#each properties as p}<option value={p.id}>{p.name}</option>{/each}
            </select>
          </div>
          <div>
            <label for="viol-type" class="block text-sm font-medium text-neutral-700 mb-1">Type</label>
            <select id="viol-type" bind:value={violForm.violation_type} class={selectCls}>{#each Object.entries(categoryLabels) as [k, v]}<option value={k}>{v}</option>{/each}</select>
          </div>
        </div>
        <div class="grid grid-cols-3 gap-4">
          <div>
            <label for="viol-sev" class="block text-sm font-medium text-neutral-700 mb-1">Severity</label>
            <select id="viol-sev" bind:value={violForm.severity} class={selectCls}>{#each Object.entries(severityLabels) as [k, v]}<option value={k}>{v}</option>{/each}</select>
          </div>
          <div>
            <label for="viol-status" class="block text-sm font-medium text-neutral-700 mb-1">Status</label>
            <select id="viol-status" bind:value={violForm.status} class={selectCls}>
              <option value="open">Open</option><option value="under_review">Under Review</option>
              <option value="remediation">Remediation</option><option value="resolved">Resolved</option>
              <option value="closed">Closed</option><option value="appealed">Appealed</option>
            </select>
          </div>
          <div>
            <label for="viol-reported" class="block text-sm font-medium text-neutral-700 mb-1">Reported *</label>
            <DateInput id="viol-reported" bind:value={violForm.reported_date} required />
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="viol-due" class="block text-sm font-medium text-neutral-700 mb-1">Due Date</label>
            <DateInput id="viol-due" bind:value={violForm.due_date} />
          </div>
          <div>
            <label for="viol-resolved" class="block text-sm font-medium text-neutral-700 mb-1">Resolved Date</label>
            <DateInput id="viol-resolved" bind:value={violForm.resolved_date} />
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="viol-fine" class="block text-sm font-medium text-neutral-700 mb-1">Fine Amount</label>
            <input id="viol-fine" type="number" step="0.01" bind:value={violForm.fine_amount} class={inputCls} placeholder="0.00" />
          </div>
          <div>
            <label for="viol-assign" class="block text-sm font-medium text-neutral-700 mb-1">Assigned To</label>
            <input id="viol-assign" bind:value={violForm.assigned_to} class={inputCls} />
          </div>
        </div>
        <div>
          <label for="viol-desc" class="block text-sm font-medium text-neutral-700 mb-1">Description</label>
          <textarea id="viol-desc" bind:value={violForm.description} rows="2" class={inputCls}></textarea>
        </div>
        <div>
          <label for="viol-action" class="block text-sm font-medium text-neutral-700 mb-1">Corrective Action</label>
          <textarea id="viol-action" bind:value={violForm.corrective_action} rows="2" class={inputCls}></textarea>
        </div>
        <div>
          <label for="viol-notes" class="block text-sm font-medium text-neutral-700 mb-1">Notes</label>
          <textarea id="viol-notes" bind:value={violForm.notes} rows="2" class={inputCls}></textarea>
        </div>
        <div class="flex justify-end gap-3 pt-2">
          <button type="button" onclick={() => (showViolModal = false)} class="px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">Cancel</button>
          <button type="submit" disabled={violSaving} class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">{violSaving ? "Saving..." : violEditingId ? "Update" : "Create"}</button>
        </div>
      </form>
    </div>
  </div>
{/if}

<!-- Audit Modal -->
{#if showAuditModal}
  <div class="fixed inset-0 z-50 flex items-start justify-center pt-[10vh]">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (showAuditModal = false)} aria-label="Close"></button>
    <div class="relative w-full max-w-lg mx-4 rounded-2xl bg-white shadow-2xl border border-neutral-200 overflow-hidden max-h-[80vh] overflow-y-auto">
      <div class="h-1 bg-neutral-900"></div>
      <form onsubmit={(e) => { e.preventDefault(); saveAudit(); }} class="p-6 space-y-4">
        <h2 class="text-lg font-bold text-neutral-900">{auditEditingId ? "Edit Audit" : "New Compliance Audit"}</h2>
        <div>
          <label for="aud-title" class="block text-sm font-medium text-neutral-700 mb-1">Title *</label>
          <input id="aud-title" bind:value={auditForm.title} required class={inputCls} />
          {#if fieldErr(auditErrors, "title")}<p class="text-xs text-red-600 mt-1">{fieldErr(auditErrors, "title")}</p>{/if}
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="aud-prop" class="block text-sm font-medium text-neutral-700 mb-1">Property *</label>
            <select id="aud-prop" bind:value={auditForm.property} required class={selectCls}>
              <option value={0} disabled>Select property</option>
              {#each properties as p}<option value={p.id}>{p.name}</option>{/each}
            </select>
          </div>
          <div>
            <label for="aud-type" class="block text-sm font-medium text-neutral-700 mb-1">Audit Type</label>
            <select id="aud-type" bind:value={auditForm.audit_type} class={selectCls}>{#each Object.entries(auditTypeLabels) as [k, v]}<option value={k}>{v}</option>{/each}</select>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="aud-status" class="block text-sm font-medium text-neutral-700 mb-1">Status</label>
            <select id="aud-status" bind:value={auditForm.status} class={selectCls}>
              <option value="scheduled">Scheduled</option><option value="in_progress">In Progress</option>
              <option value="completed">Completed</option><option value="cancelled">Cancelled</option>
            </select>
          </div>
          <div>
            <label for="aud-rating" class="block text-sm font-medium text-neutral-700 mb-1">Overall Rating</label>
            <select id="aud-rating" bind:value={auditForm.overall_rating} class={selectCls}>
              <option value="">Not Rated</option>
              {#each Object.entries(auditRatingLabels) as [k, v]}<option value={k}>{v}</option>{/each}
            </select>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="aud-date" class="block text-sm font-medium text-neutral-700 mb-1">Scheduled Date *</label>
            <DateInput id="aud-date" bind:value={auditForm.scheduled_date} required />
          </div>
          <div>
            <label for="aud-completed" class="block text-sm font-medium text-neutral-700 mb-1">Completed Date</label>
            <DateInput id="aud-completed" bind:value={auditForm.completed_date} />
          </div>
        </div>
        <div>
          <label for="aud-auditor" class="block text-sm font-medium text-neutral-700 mb-1">Auditor</label>
          <input id="aud-auditor" bind:value={auditForm.auditor} class={inputCls} />
        </div>
        <div>
          <label for="aud-scope" class="block text-sm font-medium text-neutral-700 mb-1">Scope</label>
          <textarea id="aud-scope" bind:value={auditForm.scope} rows="2" class={inputCls}></textarea>
        </div>
        <div>
          <label for="aud-findings" class="block text-sm font-medium text-neutral-700 mb-1">Findings</label>
          <textarea id="aud-findings" bind:value={auditForm.findings} rows="2" class={inputCls}></textarea>
        </div>
        <div class="flex items-center gap-6">
          <label class="flex items-center gap-2 text-sm text-neutral-700"><input type="checkbox" bind:checked={auditForm.follow_up_required} class="rounded border-neutral-300" /> Follow-up Required</label>
        </div>
        {#if auditForm.follow_up_required}
          <div>
            <label for="aud-followup" class="block text-sm font-medium text-neutral-700 mb-1">Follow-up Notes</label>
            <textarea id="aud-followup" bind:value={auditForm.follow_up_notes} rows="2" class={inputCls}></textarea>
          </div>
        {/if}
        <div>
          <label for="aud-notes" class="block text-sm font-medium text-neutral-700 mb-1">Notes</label>
          <textarea id="aud-notes" bind:value={auditForm.notes} rows="2" class={inputCls}></textarea>
        </div>
        <div class="flex justify-end gap-3 pt-2">
          <button type="button" onclick={() => (showAuditModal = false)} class="px-4 py-2 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">Cancel</button>
          <button type="submit" disabled={auditSaving} class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors">{auditSaving ? "Saving..." : auditEditingId ? "Update" : "Create"}</button>
        </div>
      </form>
    </div>
  </div>
{/if}

<!-- ======================================================================== -->
<!--  DELETE CONFIRMATION MODALS                                               -->
<!-- ======================================================================== -->

{#if reqDeleteId !== null}
  {@const item = reqData.find(r => r.id === reqDeleteId)}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (reqDeleteId = null)} aria-label="Close"></button>
    <div class="relative w-full max-w-sm rounded-2xl bg-white shadow-2xl border border-neutral-200 p-6">
      <h3 class="text-lg font-bold text-neutral-900">Delete Requirement</h3>
      <p class="mt-2 text-sm text-neutral-600">Are you sure you want to delete <strong>{item?.name}</strong>? This action cannot be undone.</p>
      <div class="mt-6 flex items-center justify-end gap-3">
        <button onclick={() => (reqDeleteId = null)} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">Cancel</button>
        <button onclick={deleteReq} disabled={reqDeleting} class="rounded-lg bg-red-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-red-700 transition-colors disabled:opacity-60">{reqDeleting ? "Deleting..." : "Delete"}</button>
      </div>
    </div>
  </div>
{/if}

{#if trackerDeleteId !== null}
  {@const item = trackerData.find(r => r.id === trackerDeleteId)}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (trackerDeleteId = null)} aria-label="Close"></button>
    <div class="relative w-full max-w-sm rounded-2xl bg-white shadow-2xl border border-neutral-200 p-6">
      <h3 class="text-lg font-bold text-neutral-900">Delete Compliance Record</h3>
      <p class="mt-2 text-sm text-neutral-600">Are you sure you want to delete the compliance record for <strong>{item?.property_name}</strong> &mdash; <strong>{item?.requirement_name}</strong>? This action cannot be undone.</p>
      <div class="mt-6 flex items-center justify-end gap-3">
        <button onclick={() => (trackerDeleteId = null)} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">Cancel</button>
        <button onclick={deleteTracker} disabled={trackerDeleting} class="rounded-lg bg-red-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-red-700 transition-colors disabled:opacity-60">{trackerDeleting ? "Deleting..." : "Delete"}</button>
      </div>
    </div>
  </div>
{/if}

{#if violDeleteId !== null}
  {@const item = violData.find(r => r.id === violDeleteId)}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (violDeleteId = null)} aria-label="Close"></button>
    <div class="relative w-full max-w-sm rounded-2xl bg-white shadow-2xl border border-neutral-200 p-6">
      <h3 class="text-lg font-bold text-neutral-900">Delete Violation</h3>
      <p class="mt-2 text-sm text-neutral-600">Are you sure you want to delete <strong>{item?.title}</strong>? This action cannot be undone.</p>
      <div class="mt-6 flex items-center justify-end gap-3">
        <button onclick={() => (violDeleteId = null)} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">Cancel</button>
        <button onclick={deleteViol} disabled={violDeleting} class="rounded-lg bg-red-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-red-700 transition-colors disabled:opacity-60">{violDeleting ? "Deleting..." : "Delete"}</button>
      </div>
    </div>
  </div>
{/if}

{#if auditDeleteId !== null}
  {@const item = auditData.find(r => r.id === auditDeleteId)}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (auditDeleteId = null)} aria-label="Close"></button>
    <div class="relative w-full max-w-sm rounded-2xl bg-white shadow-2xl border border-neutral-200 p-6">
      <h3 class="text-lg font-bold text-neutral-900">Delete Audit</h3>
      <p class="mt-2 text-sm text-neutral-600">Are you sure you want to delete <strong>{item?.title}</strong>? This action cannot be undone.</p>
      <div class="mt-6 flex items-center justify-end gap-3">
        <button onclick={() => (auditDeleteId = null)} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">Cancel</button>
        <button onclick={deleteAudit} disabled={auditDeleting} class="rounded-lg bg-red-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-red-700 transition-colors disabled:opacity-60">{auditDeleting ? "Deleting..." : "Delete"}</button>
      </div>
    </div>
  </div>
{/if}

<!-- ======================================================================== -->
<!--  VIEW DETAIL MODALS                                                       -->
<!-- ======================================================================== -->

{#if reqViewing}
  <div class="fixed inset-0 z-50 flex items-start justify-center pt-[8vh]">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (reqViewing = null)} aria-label="Close"></button>
    <div class="relative w-full max-w-2xl mx-4 rounded-2xl bg-white shadow-2xl border border-neutral-200 overflow-hidden max-h-[80vh] overflow-y-auto">
      <div class="h-1 bg-neutral-900"></div>
      <div class="p-6 space-y-6">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-bold text-neutral-900">Requirement Details</h2>
          <div class="flex items-center gap-2">
            <button onclick={editFromViewReq} class="px-3 py-1.5 text-sm font-medium text-neutral-600 hover:bg-neutral-100 rounded-lg transition-colors">Edit</button>
            <button onclick={() => (reqViewing = null)} class="px-3 py-1.5 text-sm font-medium text-neutral-600 hover:bg-neutral-100 rounded-lg transition-colors">Close</button>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-x-8 gap-y-5">
          {@render detailField("Name", reqViewing.name)}
          {@render detailField("Category", categoryLabels[reqViewing.category] ?? reqViewing.category)}
          {@render detailField("Regulatory Reference", reqViewing.regulatory_reference)}
          {@render detailField("Renewal Frequency", frequencyLabels[reqViewing.renewal_frequency] ?? reqViewing.renewal_frequency)}
          {@render detailField("Mandatory", reqViewing.is_mandatory ? "Yes" : "No")}
          {@render detailField("Active", reqViewing.is_active ? "Yes" : "No")}
          {@render detailField("Properties Linked", String(reqViewing.property_count))}
        </div>
        {#if reqViewing.description}
          <div>{@render detailField("Description", reqViewing.description, true)}</div>
        {/if}
        <div class="border-t border-neutral-100 pt-4 flex gap-6">
          <p class="text-xs text-neutral-400">Created {formatDateTime(reqViewing.created_at)}</p>
          <p class="text-xs text-neutral-400">Updated {formatDateTime(reqViewing.updated_at)}</p>
        </div>
      </div>
    </div>
  </div>
{/if}

{#if trackerViewing}
  <div class="fixed inset-0 z-50 flex items-start justify-center pt-[8vh]">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (trackerViewing = null)} aria-label="Close"></button>
    <div class="relative w-full max-w-2xl mx-4 rounded-2xl bg-white shadow-2xl border border-neutral-200 overflow-hidden max-h-[80vh] overflow-y-auto">
      <div class="h-1 bg-neutral-900"></div>
      <div class="p-6 space-y-6">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-bold text-neutral-900">Compliance Record Details</h2>
          <div class="flex items-center gap-2">
            <button onclick={editFromViewTracker} class="px-3 py-1.5 text-sm font-medium text-neutral-600 hover:bg-neutral-100 rounded-lg transition-colors">Edit</button>
            <button onclick={() => (trackerViewing = null)} class="px-3 py-1.5 text-sm font-medium text-neutral-600 hover:bg-neutral-100 rounded-lg transition-colors">Close</button>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-x-8 gap-y-5">
          {@render detailField("Property", trackerViewing.property_name)}
          {@render detailField("Requirement", trackerViewing.requirement_name)}
          {@render detailField("Category", categoryLabels[trackerViewing.requirement_category] ?? trackerViewing.requirement_category)}
          {@render detailField("Status", complianceStatusLabels[trackerViewing.status] ?? trackerViewing.status)}
          {@render detailField("Certificate #", trackerViewing.certificate_number)}
          {@render detailField("Issuing Authority", trackerViewing.issuing_authority)}
          {@render detailField("Issue Date", formatDate(trackerViewing.issue_date))}
          {@render detailField("Expiry Date", formatDate(trackerViewing.expiry_date))}
          {@render detailField("Last Reviewed", formatDate(trackerViewing.last_reviewed_date))}
          {@render detailField("Next Review", formatDate(trackerViewing.next_review_date))}
          {@render detailField("Responsible Person", trackerViewing.responsible_person)}
        </div>
        {#if trackerViewing.notes}
          <div>{@render detailField("Notes", trackerViewing.notes, true)}</div>
        {/if}
        <div class="border-t border-neutral-100 pt-4 flex gap-6">
          <p class="text-xs text-neutral-400">Created {formatDateTime(trackerViewing.created_at)}</p>
          <p class="text-xs text-neutral-400">Updated {formatDateTime(trackerViewing.updated_at)}</p>
        </div>
      </div>
    </div>
  </div>
{/if}

{#if violViewing}
  <div class="fixed inset-0 z-50 flex items-start justify-center pt-[8vh]">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (violViewing = null)} aria-label="Close"></button>
    <div class="relative w-full max-w-2xl mx-4 rounded-2xl bg-white shadow-2xl border border-neutral-200 overflow-hidden max-h-[80vh] overflow-y-auto">
      <div class="h-1 bg-neutral-900"></div>
      <div class="p-6 space-y-6">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-bold text-neutral-900">Violation Details</h2>
          <div class="flex items-center gap-2">
            <button onclick={editFromViewViol} class="px-3 py-1.5 text-sm font-medium text-neutral-600 hover:bg-neutral-100 rounded-lg transition-colors">Edit</button>
            <button onclick={() => (violViewing = null)} class="px-3 py-1.5 text-sm font-medium text-neutral-600 hover:bg-neutral-100 rounded-lg transition-colors">Close</button>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-x-8 gap-y-5">
          {@render detailField("Title", violViewing.title)}
          {@render detailField("Property", violViewing.property_name)}
          {@render detailField("Type", categoryLabels[violViewing.violation_type] ?? violViewing.violation_type)}
          {@render detailField("Severity", severityLabels[violViewing.severity] ?? violViewing.severity)}
          {@render detailField("Status", statusLabel(violViewing.status))}
          {@render detailField("Reported", formatDate(violViewing.reported_date))}
          {@render detailField("Due Date", formatDate(violViewing.due_date))}
          {@render detailField("Resolved", formatDate(violViewing.resolved_date))}
          {@render detailField("Fine Amount", formatCurrency(violViewing.fine_amount))}
          {@render detailField("Assigned To", violViewing.assigned_to)}
        </div>
        {#if violViewing.description}
          <div>{@render detailField("Description", violViewing.description, true)}</div>
        {/if}
        {#if violViewing.corrective_action}
          <div>{@render detailField("Corrective Action", violViewing.corrective_action, true)}</div>
        {/if}
        {#if violViewing.notes}
          <div>{@render detailField("Notes", violViewing.notes, true)}</div>
        {/if}
        <div class="border-t border-neutral-100 pt-4 flex gap-6">
          <p class="text-xs text-neutral-400">Created {formatDateTime(violViewing.created_at)}</p>
          <p class="text-xs text-neutral-400">Updated {formatDateTime(violViewing.updated_at)}</p>
        </div>
      </div>
    </div>
  </div>
{/if}

{#if auditViewing}
  <div class="fixed inset-0 z-50 flex items-start justify-center pt-[8vh]">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (auditViewing = null)} aria-label="Close"></button>
    <div class="relative w-full max-w-2xl mx-4 rounded-2xl bg-white shadow-2xl border border-neutral-200 overflow-hidden max-h-[80vh] overflow-y-auto">
      <div class="h-1 bg-neutral-900"></div>
      <div class="p-6 space-y-6">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-bold text-neutral-900">Audit Details</h2>
          <div class="flex items-center gap-2">
            <button onclick={editFromViewAudit} class="px-3 py-1.5 text-sm font-medium text-neutral-600 hover:bg-neutral-100 rounded-lg transition-colors">Edit</button>
            <button onclick={() => (auditViewing = null)} class="px-3 py-1.5 text-sm font-medium text-neutral-600 hover:bg-neutral-100 rounded-lg transition-colors">Close</button>
          </div>
        </div>
        <div class="grid grid-cols-2 gap-x-8 gap-y-5">
          {@render detailField("Title", auditViewing.title)}
          {@render detailField("Property", auditViewing.property_name)}
          {@render detailField("Audit Type", auditTypeLabels[auditViewing.audit_type] ?? auditViewing.audit_type)}
          {@render detailField("Status", statusLabel(auditViewing.status))}
          {@render detailField("Scheduled Date", formatDate(auditViewing.scheduled_date))}
          {@render detailField("Completed Date", formatDate(auditViewing.completed_date))}
          {@render detailField("Auditor", auditViewing.auditor)}
          {@render detailField("Overall Rating", auditViewing.overall_rating ? (auditRatingLabels[auditViewing.overall_rating] ?? auditViewing.overall_rating) : "\u2014")}
          {@render detailField("Follow-up Required", auditViewing.follow_up_required ? "Yes" : "No")}
        </div>
        {#if auditViewing.scope}
          <div>{@render detailField("Scope", auditViewing.scope, true)}</div>
        {/if}
        {#if auditViewing.findings}
          <div>{@render detailField("Findings", auditViewing.findings, true)}</div>
        {/if}
        {#if auditViewing.follow_up_notes}
          <div>{@render detailField("Follow-up Notes", auditViewing.follow_up_notes, true)}</div>
        {/if}
        {#if auditViewing.notes}
          <div>{@render detailField("Notes", auditViewing.notes, true)}</div>
        {/if}
        <div class="border-t border-neutral-100 pt-4 flex gap-6">
          <p class="text-xs text-neutral-400">Created {formatDateTime(auditViewing.created_at)}</p>
          <p class="text-xs text-neutral-400">Updated {formatDateTime(auditViewing.updated_at)}</p>
        </div>
      </div>
    </div>
  </div>
{/if}

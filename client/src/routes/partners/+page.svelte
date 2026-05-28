<script lang="ts">
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type {
    PartnerOnboardingOverview,
    PartnerOnboardingCaseListItem,
    PartnerOnboardingCaseDetail,
    PartnerOnboardingStageProgress,
    PartnerOnboardingApproval,
    PartnerEntitlement,
    PartnerOnboardingAuditEvent,
    OnboardingStageStatus,
    PartnerPortalRole,
    OnboardingTemplate,
    PartnerType,
    PaginatedResponse,
  } from "$lib/types";

  // --- Overview ---
  let overview = $state<PartnerOnboardingOverview | null>(null);
  let overviewLoading = $state(true);

  // --- Cases Table ---
  let cases = $state<PartnerOnboardingCaseListItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 20;

  // --- Filters ---
  let search = $state("");
  let partnerTypeFilter = $state("");
  let statusFilter = $state("");
  let templateFilter = $state("");

  // --- Reference Data ---
  let templates = $state<OnboardingTemplate[]>([]);
  let leads = $state<{ id: number; first_name: string; last_name: string; email: string; phone: string; status: string }[]>([]);

  // --- Slide-over ---
  let showSlideOver = $state(false);
  let saving = $state(false);
  let createErrors = $state<Record<string, string[]>>({});
  let createForm = $state({
    partner_type: "" as PartnerType | "",
    title: "",
    template: "",
    lead: "",
    contact_name: "",
    contact_email: "",
    contact_phone: "",
    contract_reference: "",
    notes: "",
  });

  // --- Templates for slide-over (filtered by partner_type) ---
  let slideOverTemplates = $state<OnboardingTemplate[]>([]);

  function createFieldError(field: string): string {
    return createErrors[field]?.[0] ?? "";
  }

  function resetCreateForm() {
    createForm = {
      partner_type: "",
      title: "",
      template: "",
      lead: "",
      contact_name: "",
      contact_email: "",
      contact_phone: "",
      contract_reference: "",
      notes: "",
    };
    createErrors = {};
    slideOverTemplates = [];
  }

  // --- Derived ---
  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));

  let pageNumbers = $derived.by(() => {
    const pages: number[] = [];
    const maxVisible = 5;
    let start = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let end = Math.min(totalPages, start + maxVisible - 1);
    if (end - start + 1 < maxVisible) {
      start = Math.max(1, end - maxVisible + 1);
    }
    for (let i = start; i <= end; i++) {
      pages.push(i);
    }
    return pages;
  });

  let filteredTemplates = $derived.by(() => {
    if (!partnerTypeFilter) return templates;
    return templates.filter((t) => t.partner_type === partnerTypeFilter);
  });

  // --- Helpers ---
  function formatDateShort(dateStr: string | null): string {
    if (!dateStr) return "\u2014";
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  // --- Data Fetching ---
  async function fetchOverview() {
    overviewLoading = true;
    try {
      overview = await api.get<PartnerOnboardingOverview>("/partners/overview/");
    } catch {
      overview = null;
    } finally {
      overviewLoading = false;
    }
  }

  async function fetchCases() {
    loading = true;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        page_size: String(pageSize),
      };
      if (search) params.search = search;
      if (partnerTypeFilter) params.partner_type = partnerTypeFilter;
      if (statusFilter) params.status = statusFilter;
      if (templateFilter) params.template = templateFilter;

      const res = await api.get<PaginatedResponse<PartnerOnboardingCaseListItem>>(
        "/partners/cases/",
        params,
      );
      cases = res.results;
      totalCount = res.count;
    } catch {
      cases = [];
      totalCount = 0;
    } finally {
      loading = false;
    }
  }

  async function fetchTemplates() {
    try {
      const res = await api.get<PaginatedResponse<OnboardingTemplate>>(
        "/partners/templates/",
        { is_active: "true", page_size: "100" },
      );
      templates = res.results;
    } catch {
      templates = [];
    }
  }

  async function fetchLeads() {
    try {
      const res = await api.get<PaginatedResponse<{ id: number; first_name: string; last_name: string; email: string; phone: string; status: string }>>(
        "/crm/leads/",
        { status: "active", is_archived: "false", page_size: "100" },
      );
      leads = res.results;
    } catch {
      leads = [];
    }
  }

  async function fetchSlideOverTemplates(partnerType: PartnerType) {
    try {
      const res = await api.get<PaginatedResponse<OnboardingTemplate>>(
        "/partners/templates/",
        { is_active: "true", partner_type: partnerType, page_size: "100" },
      );
      slideOverTemplates = res.results;
    } catch {
      slideOverTemplates = [];
    }
  }

  // --- Event Handlers ---
  let debounceTimer: ReturnType<typeof setTimeout>;

  function handleSearchInput(value: string) {
    search = value;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      currentPage = 1;
      fetchCases();
    }, 300);
  }

  function handlePartnerTypeChange(value: string) {
    partnerTypeFilter = value;
    templateFilter = "";
    currentPage = 1;
    fetchCases();
  }

  function handleStatusChange(value: string) {
    statusFilter = value;
    currentPage = 1;
    fetchCases();
  }

  function handleTemplateChange(value: string) {
    templateFilter = value;
    currentPage = 1;
    fetchCases();
  }

  function goToPage(page: number) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    fetchCases();
  }

  function handlePartnerTypeRadio(type: PartnerType) {
    createForm.partner_type = type;
    createForm.template = "";
    fetchSlideOverTemplates(type);
  }

  function handleLeadSelect(leadId: string) {
    createForm.lead = leadId;
    if (leadId) {
      const selectedLead = leads.find((l) => String(l.id) === leadId);
      if (selectedLead) {
        createForm.contact_name = `${selectedLead.first_name} ${selectedLead.last_name}`.trim();
        createForm.contact_email = selectedLead.email ?? "";
        createForm.contact_phone = selectedLead.phone ?? "";
      }
    }
  }

  async function handleCreateCase(e: Event) {
    e.preventDefault();
    createErrors = {};
    saving = true;

    try {
      const payload: Record<string, unknown> = {
        partner_type: createForm.partner_type,
        title: createForm.title,
        template: createForm.template ? Number(createForm.template) : null,
        lead: createForm.lead ? Number(createForm.lead) : null,
        contact_name: createForm.contact_name,
        contact_email: createForm.contact_email,
        contact_phone: createForm.contact_phone || "",
        contract_reference: createForm.contract_reference || "",
        notes: createForm.notes || "",
      };

      const newCase = await api.post<PartnerOnboardingCaseDetail>("/partners/cases/", payload);
      toast.success("Case created", "The onboarding case has been created successfully");
      showSlideOver = false;
      resetCreateForm();
      fetchCases();
      fetchOverview();
      openDetailModal(newCase.id);
    } catch (err) {
      if (err instanceof ApiError) {
        createErrors = err.fieldErrors;
        toast.error("Validation error", "Please fix the highlighted fields");
      } else {
        toast.error("Something went wrong", "Could not create the onboarding case");
      }
    }
    saving = false;
  }

  function openSlideOver() {
    resetCreateForm();
    fetchLeads();
    showSlideOver = true;
  }

  function closeSlideOver() {
    showSlideOver = false;
    resetCreateForm();
  }

  // --- Initialize ---
  $effect(() => {
    fetchOverview();
    fetchCases();
    fetchTemplates();
    // Auto-open detail modal from URL query param
    const detailParam = $page.url.searchParams.get("detail");
    if (detailParam && !showDetailModal) {
      openDetailModal(Number(detailParam));
    }
  });

  // ═══════════════════════════════════════════════════════════════════
  // DETAIL MODAL (from [id]/+page.svelte)
  // ═══════════════════════════════════════════════════════════════════
  let showDetailModal = $state(false);
  let detailId = $state<number | null>(null);
  let detailData = $state<PartnerOnboardingCaseDetail | null>(null);
  let detailTimeline = $state<PartnerOnboardingAuditEvent[]>([]);
  let detailLoading = $state(false);
  let timelineLoading = $state(false);

  let showStageModal = $state(false);
  let showSubmitReviewModal = $state(false);
  let showCreateErpModal = $state(false);
  let showGrantPortalModal = $state(false);
  let showApprovalModal = $state(false);
  let showEntitlementModal = $state(false);
  let showPayloadIndex = $state<number | null>(null);

  let savingStage = $state(false);
  let submittingReview = $state(false);
  let creatingErp = $state(false);
  let grantingPortal = $state(false);
  let recordingApproval = $state(false);
  let provisioningEntitlement = $state(false);

  let stageForm = $state({ stage_progress_id: 0, stage_name: "", current_status: "" as OnboardingStageStatus | "", new_status: "not_started" as OnboardingStageStatus, notes: "" });
  let approvalForm = $state({ stage_progress_id: null as number | null, decision: "approved" as "approved" | "rejected" | "changes_required", approver_role_label: "", comments: "" });
  let entitlementForm = $state({ portal_role: "client" as PartnerPortalRole, contract_reference: "" });

  const sortedStages = $derived(detailData ? [...detailData.stage_progress].sort((a, b) => a.stage_sequence - b.stage_sequence) : []);
  const canSubmitForReview = $derived(detailData !== null && detailData.status === "in_progress" && detailData.required_stage_total > 0 && detailData.required_stage_completed === detailData.required_stage_total);
  const canCreateErp = $derived(detailData !== null && !detailData.has_erp_profile && ["in_progress", "under_review", "approved"].includes(detailData.status));
  const canGrantPortal = $derived(detailData !== null && detailData.status === "approved" && detailData.has_erp_profile && detailData.entitlements.some((e) => e.is_active));
  const sortedTimeline = $derived([...detailTimeline].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()));

  function formatDateTime(dateStr: string | null): string { if (!dateStr) return "--"; return new Date(dateStr).toLocaleString(undefined, { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }); }
  function formatDate(dateStr: string | null): string { if (!dateStr) return "--"; return new Date(dateStr).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" }); }
  function partnerTypeBadgeClass(ptype: string): string { return ptype === "investor" ? "bg-neutral-800 text-white" : ptype === "contractor" ? "bg-neutral-200 text-neutral-800" : "bg-neutral-100 text-neutral-700"; }
  function stageBadgeClass(status: OnboardingStageStatus): string { return status === "completed" ? "bg-emerald-50 text-emerald-700" : status === "in_progress" ? "bg-blue-50 text-blue-700" : status === "blocked" ? "bg-red-50 text-red-700" : status === "waived" ? "bg-neutral-200 text-neutral-500" : "bg-neutral-100 text-neutral-600"; }
  function stageCircleClass(status: OnboardingStageStatus): string { return status === "completed" || status === "waived" ? "bg-neutral-800 text-white" : status === "in_progress" ? "bg-blue-600 text-white" : status === "blocked" ? "bg-red-600 text-white" : "bg-white border-2 border-neutral-300 text-neutral-400"; }
  function decisionBadgeClass(decision: string): string { return decision === "approved" ? "bg-emerald-50 text-emerald-700" : decision === "rejected" ? "bg-red-50 text-red-700" : decision === "changes_required" ? "bg-amber-50 text-amber-700" : "bg-neutral-100 text-neutral-600"; }
  function eventCircleClass(eventType: string): string { return eventType === "stage_completed" || eventType === "case_approved" || eventType === "portal_access_granted" ? "bg-emerald-500 text-white" : eventType === "approval_rejected" || eventType === "stage_blocked" ? "bg-red-500 text-white" : eventType === "stage_status_changed" || eventType === "submitted_for_review" ? "bg-blue-500 text-white" : "bg-neutral-200 text-neutral-600"; }
  function formatEventType(eventType: string): string { return eventType.split("_").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" "); }
  function formatLabel(value: string): string { return value.split("_").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" "); }

  async function openDetailModal(caseId: number) {
    detailId = caseId;
    detailLoading = true;
    showDetailModal = true;
    goto(`/partners?detail=${caseId}`, { replaceState: true, noScroll: true });
    try {
      const [caseRes, timelineRes] = await Promise.all([
        api.get<PartnerOnboardingCaseDetail>(`/partners/cases/${caseId}/`),
        api.get<PartnerOnboardingAuditEvent[]>(`/partners/cases/${caseId}/timeline/`),
      ]);
      detailData = caseRes;
      detailTimeline = timelineRes;
    } catch { toast.error("Error", "Failed to load case details"); showDetailModal = false; }
    finally { detailLoading = false; }
  }

  function closeDetailModal() {
    showDetailModal = false; detailData = null; detailTimeline = []; detailId = null;
    goto("/partners", { replaceState: true, noScroll: true });
  }

  async function refreshDetail() {
    if (!detailId) return;
    const [c, t] = await Promise.all([
      api.get<PartnerOnboardingCaseDetail>(`/partners/cases/${detailId}/`),
      api.get<PartnerOnboardingAuditEvent[]>(`/partners/cases/${detailId}/timeline/`),
    ]);
    detailData = c;
    detailTimeline = t;
  }

  async function handleMarkStage() { savingStage = true; try { await api.post(`/partners/cases/${detailId}/mark-stage/`, { stage_progress_id: stageForm.stage_progress_id, status: stageForm.new_status, notes: stageForm.notes }); toast.success("Stage Updated", `Stage "${stageForm.stage_name}" marked as ${formatLabel(stageForm.new_status)}`); showStageModal = false; stageForm = { stage_progress_id: 0, stage_name: "", current_status: "", new_status: "not_started", notes: "" }; await refreshDetail(); } catch (err) { toast.error("Error", err instanceof ApiError ? String(err.data?.detail || "Could not update stage") : "Could not update stage"); } finally { savingStage = false; } }
  async function handleSubmitReview() { submittingReview = true; try { await api.post(`/partners/cases/${detailId}/submit-review/`, {}); toast.success("Submitted", "Case submitted for review"); showSubmitReviewModal = false; await refreshDetail(); } catch (err) { toast.error("Error", err instanceof ApiError ? String(err.data?.detail || "Could not submit") : "Could not submit"); } finally { submittingReview = false; } }
  async function handleCreateErp() { creatingErp = true; try { await api.post(`/partners/cases/${detailId}/create-erp-entity/`, {}); toast.success("ERP Entity Created"); showCreateErpModal = false; await refreshDetail(); } catch (err) { toast.error("Error", err instanceof ApiError ? String(err.data?.detail || "Could not create") : "Could not create"); } finally { creatingErp = false; } }
  async function handleGrantPortal() { grantingPortal = true; try { await api.post(`/partners/cases/${detailId}/grant-portal-access/`, {}); toast.success("Portal Access Granted"); showGrantPortalModal = false; await refreshDetail(); } catch (err) { toast.error("Error", err instanceof ApiError ? String(err.data?.detail || "Could not grant") : "Could not grant"); } finally { grantingPortal = false; } }
  async function handleRecordApproval() { recordingApproval = true; try { await api.post(`/partners/cases/${detailId}/record-approval/`, { stage_progress_id: approvalForm.stage_progress_id || undefined, decision: approvalForm.decision, approver_role_label: approvalForm.approver_role_label || undefined, comments: approvalForm.comments || undefined }); toast.success("Approval Recorded"); showApprovalModal = false; approvalForm = { stage_progress_id: null, decision: "approved", approver_role_label: "", comments: "" }; await refreshDetail(); } catch (err) { toast.error("Error", err instanceof ApiError ? String(err.data?.detail || "Could not record") : "Could not record"); } finally { recordingApproval = false; } }
  async function handleProvisionEntitlement() { provisioningEntitlement = true; try { await api.post(`/partners/cases/${detailId}/provision-entitlement/`, { portal_role: entitlementForm.portal_role, contract_reference: entitlementForm.contract_reference || undefined }); toast.success("Entitlement Provisioned"); showEntitlementModal = false; entitlementForm = { portal_role: "client", contract_reference: "" }; await refreshDetail(); } catch (err) { toast.error("Error", err instanceof ApiError ? String(err.data?.detail || "Could not provision") : "Could not provision"); } finally { provisioningEntitlement = false; } }

  function openStageModal(stage: PartnerOnboardingStageProgress) { stageForm = { stage_progress_id: stage.id, stage_name: stage.stage_name, current_status: stage.status, new_status: stage.status, notes: "" }; showStageModal = true; }
  function togglePayload(index: number) { showPayloadIndex = showPayloadIndex === index ? null : index; }
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-slate-700">Partners</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Onboarding Hub</h1>
      <p class="mt-1 text-sm text-neutral-500">Monitor and manage partner onboarding workflows</p>
    </div>
    <button
      onclick={openSlideOver}
      class="inline-flex items-center gap-2 px-4 py-2 bg-neutral-800 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
      </svg>
      New Case
    </button>
  </div>

  <!-- KPI Strip: Row 1 - Status counts -->
  {#if overviewLoading}
    <div class="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-4">
      {#each Array(8) as _}
        <div class="bg-white border border-neutral-200 rounded-lg p-4 animate-pulse">
          <div class="h-3 w-20 bg-neutral-200 rounded mb-3"></div>
          <div class="h-7 w-14 bg-neutral-200 rounded"></div>
        </div>
      {/each}
    </div>
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
      {#each Array(4) as _}
        <div class="bg-white border border-neutral-200 rounded-lg p-4 animate-pulse">
          <div class="h-3 w-20 bg-neutral-200 rounded mb-3"></div>
          <div class="h-7 w-14 bg-neutral-200 rounded"></div>
        </div>
      {/each}
    </div>
  {:else if overview}
    <div class="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-4">
      <div class="bg-slate-50 border border-slate-200 rounded-lg p-4">
        <p class="text-[10px] font-medium uppercase tracking-wider text-slate-500">Total Cases</p>
        <p class="mt-1.5 text-lg font-semibold text-slate-900 tabular-nums">{overview.total_cases.toLocaleString()}</p>
      </div>
      <div class="bg-neutral-50 border border-neutral-200 rounded-lg p-4">
        <p class="text-[10px] font-medium uppercase tracking-wider text-neutral-400">Draft</p>
        <p class="mt-1.5 text-lg font-semibold text-neutral-600 tabular-nums">{overview.draft.toLocaleString()}</p>
      </div>
      <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p class="text-[10px] font-medium uppercase tracking-wider text-blue-500">In Progress</p>
        <p class="mt-1.5 text-lg font-semibold text-blue-800 tabular-nums">{overview.in_progress.toLocaleString()}</p>
      </div>
      <div class="bg-amber-50 border border-amber-200 rounded-lg p-4">
        <p class="text-[10px] font-medium uppercase tracking-wider text-amber-500">Under Review</p>
        <p class="mt-1.5 text-lg font-semibold text-amber-800 tabular-nums">{overview.under_review.toLocaleString()}</p>
      </div>
      <div class="bg-emerald-50 border border-emerald-200 rounded-lg p-4">
        <p class="text-[10px] font-medium uppercase tracking-wider text-emerald-500">Approved</p>
        <p class="mt-1.5 text-lg font-semibold text-emerald-800 tabular-nums">{overview.approved.toLocaleString()}</p>
      </div>
      <div class="bg-violet-50 border border-violet-200 rounded-lg p-4">
        <p class="text-[10px] font-medium uppercase tracking-wider text-violet-500">Active</p>
        <p class="mt-1.5 text-lg font-semibold text-violet-800 tabular-nums">{overview.active.toLocaleString()}</p>
      </div>
      <div class="bg-rose-50 border border-rose-200 rounded-lg p-4">
        <p class="text-[10px] font-medium uppercase tracking-wider text-rose-400">Rejected</p>
        <p class="mt-1.5 text-lg font-semibold text-rose-700 tabular-nums">{overview.rejected.toLocaleString()}</p>
      </div>
      <div class="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
        <p class="text-[10px] font-medium uppercase tracking-wider text-indigo-500">Portal Access</p>
        <p class="mt-1.5 text-lg font-semibold text-indigo-800 tabular-nums">{overview.portal_access_granted.toLocaleString()}</p>
      </div>
    </div>

    <!-- KPI Strip: Row 2 - Partner type breakdown + avg completion -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
      <div class="bg-sky-50 border border-sky-200 rounded-lg p-4">
        <p class="text-[10px] font-medium uppercase tracking-wider text-sky-500">Clients</p>
        <p class="mt-1.5 text-lg font-semibold text-sky-800 tabular-nums">{overview.by_partner_type.client.toLocaleString()}</p>
      </div>
      <div class="bg-orange-50 border border-orange-200 rounded-lg p-4">
        <p class="text-[10px] font-medium uppercase tracking-wider text-orange-500">Contractors</p>
        <p class="mt-1.5 text-lg font-semibold text-orange-800 tabular-nums">{overview.by_partner_type.contractor.toLocaleString()}</p>
      </div>
      <div class="bg-teal-50 border border-teal-200 rounded-lg p-4">
        <p class="text-[10px] font-medium uppercase tracking-wider text-teal-500">Investors</p>
        <p class="mt-1.5 text-lg font-semibold text-teal-800 tabular-nums">{overview.by_partner_type.investor.toLocaleString()}</p>
      </div>
      <div class="bg-fuchsia-50 border border-fuchsia-200 rounded-lg p-4">
        <p class="text-[10px] font-medium uppercase tracking-wider text-fuchsia-500">Avg Completion</p>
        <p class="mt-1.5 text-lg font-semibold text-fuchsia-800 tabular-nums">{overview.avg_completion_percent.toFixed(0)}%</p>
      </div>
    </div>
  {/if}

  <!-- Filters -->
  <div class="bg-white rounded-xl border border-neutral-200 p-5">
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Search</span>
        <div class="relative">
          <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
          </svg>
          <input
            type="text"
            placeholder="Search cases..."
            value={search}
            oninput={(e) => handleSearchInput((e.target as HTMLInputElement).value)}
            class="w-full rounded-lg border border-neutral-300 pl-9 pr-3 py-2 text-sm focus:border-neutral-800 focus:ring-1 focus:ring-neutral-800 focus:outline-none"
          />
        </div>
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Partner Type</span>
        <select
          value={partnerTypeFilter}
          onchange={(e) => handlePartnerTypeChange((e.target as HTMLSelectElement).value)}
          class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-800 focus:ring-1 focus:ring-neutral-800 focus:outline-none"
        >
          <option value="">All Types</option>
          <option value="client">Client</option>
          <option value="contractor">Contractor</option>
          <option value="investor">Investor</option>
        </select>
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Status</span>
        <select
          value={statusFilter}
          onchange={(e) => handleStatusChange((e.target as HTMLSelectElement).value)}
          class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-800 focus:ring-1 focus:ring-neutral-800 focus:outline-none"
        >
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="in_progress">In Progress</option>
          <option value="under_review">Under Review</option>
          <option value="approved">Approved</option>
          <option value="active">Active</option>
          <option value="rejected">Rejected</option>
          <option value="suspended">Suspended</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Template</span>
        <select
          value={templateFilter}
          onchange={(e) => handleTemplateChange((e.target as HTMLSelectElement).value)}
          class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-800 focus:ring-1 focus:ring-neutral-800 focus:outline-none"
        >
          <option value="">All Templates</option>
          {#each filteredTemplates as tmpl}
            <option value={String(tmpl.id)}>{tmpl.name}</option>
          {/each}
        </select>
      </label>
    </div>
  </div>

  <!-- Cases Table -->
  <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
    {#if loading}
      <!-- Skeleton loader -->
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-neutral-200">
          <thead class="bg-neutral-50">
            <tr>
              {#each ["Title", "Partner Type", "Status", "Current Stage", "Progress", "ERP Profile", "Portal Access", "Created"] as col}
                <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">{col}</th>
              {/each}
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each Array(8) as _}
              <tr class="animate-pulse">
                <td class="px-5 py-4"><div class="h-4 w-36 bg-neutral-200 rounded"></div></td>
                <td class="px-5 py-4"><div class="h-5 w-20 bg-neutral-200 rounded-full"></div></td>
                <td class="px-5 py-4"><div class="h-5 w-22 bg-neutral-200 rounded-full"></div></td>
                <td class="px-5 py-4"><div class="h-4 w-28 bg-neutral-200 rounded"></div></td>
                <td class="px-5 py-4"><div class="h-4 w-24 bg-neutral-200 rounded"></div></td>
                <td class="px-5 py-4"><div class="h-4 w-8 bg-neutral-200 rounded"></div></td>
                <td class="px-5 py-4"><div class="h-4 w-8 bg-neutral-200 rounded"></div></td>
                <td class="px-5 py-4"><div class="h-4 w-24 bg-neutral-200 rounded"></div></td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {:else if cases.length === 0}
      <!-- Empty state -->
      <div class="flex flex-col items-center justify-center py-20 text-center">
        <div class="text-neutral-400 mb-2">
          <svg class="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm6 3a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Zm-13.5 0a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Z" />
          </svg>
        </div>
        <p class="text-neutral-500 text-sm">No onboarding cases found</p>
        <p class="text-neutral-400 text-xs mt-1">Adjust your filters or create a new onboarding case to get started</p>
        <button
          onclick={openSlideOver}
          class="mt-3 text-sm font-medium text-neutral-800 hover:underline"
        >
          Create your first case
        </button>
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-neutral-200">
          <thead class="bg-neutral-50">
            <tr>
              <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Title</th>
              <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Partner Type</th>
              <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Status</th>
              <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Current Stage</th>
              <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Progress</th>
              <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">ERP Profile</th>
              <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Portal Access</th>
              <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Created</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each cases as onboardingCase}
              <tr
                class="hover:bg-neutral-50 cursor-pointer transition-colors"
                onclick={() => openDetailModal(onboardingCase.id)}
              >
                <!-- Title -->
                <td class="px-5 py-4 text-sm font-medium text-neutral-800 whitespace-nowrap max-w-[240px] truncate">
                  {onboardingCase.title}
                </td>

                <!-- Partner Type -->
                <td class="px-5 py-4 whitespace-nowrap">
                  <StatusBadge status={onboardingCase.partner_type} label={onboardingCase.partner_type_display} />
                </td>

                <!-- Status -->
                <td class="px-5 py-4 whitespace-nowrap">
                  <StatusBadge status={onboardingCase.status} label={onboardingCase.status_display} />
                </td>

                <!-- Current Stage -->
                <td class="px-5 py-4 text-sm text-neutral-600 whitespace-nowrap">
                  {onboardingCase.current_stage_name ?? "\u2014"}
                </td>

                <!-- Progress -->
                <td class="px-5 py-4 whitespace-nowrap">
                  <div class="flex items-center gap-2">
                    <div class="w-20 h-1.5 bg-neutral-100 rounded-full overflow-hidden">
                      <div
                        class="h-full bg-neutral-800 rounded-full transition-all duration-300"
                        style="width: {onboardingCase.completion_percent}%"
                      ></div>
                    </div>
                    <span class="text-xs text-neutral-500 tabular-nums">
                      {onboardingCase.required_stage_completed}/{onboardingCase.required_stage_total}
                    </span>
                  </div>
                </td>

                <!-- ERP Profile -->
                <td class="px-5 py-4 text-sm text-neutral-600 whitespace-nowrap text-center">
                  {#if onboardingCase.has_erp_profile}
                    <span class="text-neutral-800 font-medium">{"\u2713"}</span>
                  {:else}
                    <span class="text-neutral-400">{"\u2014"}</span>
                  {/if}
                </td>

                <!-- Portal Access -->
                <td class="px-5 py-4 text-sm text-neutral-600 whitespace-nowrap text-center">
                  {#if onboardingCase.portal_access_granted}
                    <span class="text-neutral-800 font-medium">{"\u2713"}</span>
                  {:else}
                    <span class="text-neutral-400">{"\u2014"}</span>
                  {/if}
                </td>

                <!-- Created -->
                <td class="px-5 py-4 text-sm text-neutral-500 whitespace-nowrap">
                  {formatDateShort(onboardingCase.created_at)}
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div class="flex items-center justify-between border-t border-neutral-200 px-5 py-4">
        <p class="text-sm text-neutral-400">
          Showing {(currentPage - 1) * pageSize + 1}&ndash;{Math.min(currentPage * pageSize, totalCount)} of {totalCount}
        </p>
        {#if totalPages > 1}
          <div class="flex items-center gap-1">
            <button
              onclick={() => goToPage(currentPage - 1)}
              disabled={currentPage <= 1}
              aria-label="Previous page"
              class="px-3 py-1.5 text-sm rounded-lg border border-neutral-200 hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
              </svg>
            </button>
            {#each pageNumbers as pg}
              <button
                onclick={() => goToPage(pg)}
                class="px-3 py-1.5 text-sm rounded-lg border transition-colors {pg === currentPage
                  ? 'bg-neutral-800 text-white border-neutral-800'
                  : 'border-neutral-200 hover:bg-neutral-50'}"
              >
                {pg}
              </button>
            {/each}
            <button
              onclick={() => goToPage(currentPage + 1)}
              disabled={currentPage >= totalPages}
              aria-label="Next page"
              class="px-3 py-1.5 text-sm rounded-lg border border-neutral-200 hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
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
</div>

<!-- Slide-Over: New Case -->
{#if showSlideOver}
  <!-- Backdrop -->
  <button
    class="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm cursor-default"
    onclick={closeSlideOver}
    tabindex="-1"
    aria-label="Close panel"
  ></button>

  <!-- Panel -->
  <div class="fixed inset-y-0 right-0 z-50 w-full max-w-lg flex flex-col bg-white shadow-2xl slide-over-enter">
    <!-- Header -->
    <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-100 shrink-0">
      <h2 class="text-lg font-semibold text-neutral-800">New Case</h2>
      <button
        onclick={closeSlideOver}
        class="p-1.5 rounded-lg text-neutral-400 hover:text-neutral-800 hover:bg-neutral-100 transition-colors"
        aria-label="Close"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- Body -->
    <div class="flex-1 overflow-y-auto px-6 py-5">
      <form id="create-case-form" onsubmit={handleCreateCase} class="space-y-5">
        <!-- Partner Type -->
        <fieldset>
          <legend class="block text-sm font-medium text-neutral-700 mb-2">Partner Type <span class="text-neutral-400">*</span></legend>
          <div class="flex gap-3">
            {#each [
              { value: "client", label: "Client" },
              { value: "contractor", label: "Contractor" },
              { value: "investor", label: "Investor" },
            ] as option}
              <label
                class="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg border text-sm font-medium cursor-pointer transition-colors {createForm.partner_type === option.value
                  ? 'border-neutral-800 bg-neutral-800 text-white'
                  : 'border-neutral-300 bg-white text-neutral-700 hover:bg-neutral-50'}"
              >
                <input
                  type="radio"
                  name="partner_type"
                  value={option.value}
                  checked={createForm.partner_type === option.value}
                  onchange={() => handlePartnerTypeRadio(option.value as PartnerType)}
                  required
                  class="sr-only"
                />
                {option.label}
              </label>
            {/each}
          </div>
          {#if createFieldError("partner_type")}<p class="mt-1 text-xs text-neutral-500">{createFieldError("partner_type")}</p>{/if}
        </fieldset>

        <!-- Title -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Title <span class="text-neutral-400">*</span></span>
          <input
            type="text"
            bind:value={createForm.title}
            required
            placeholder="e.g. Acme Corp onboarding"
            class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-800 focus:ring-1 focus:ring-neutral-800 focus:outline-none"
          />
          {#if createFieldError("title")}<p class="mt-1 text-xs text-neutral-500">{createFieldError("title")}</p>{/if}
        </label>

        <!-- Template -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Template</span>
          <select
            bind:value={createForm.template}
            disabled={!createForm.partner_type}
            class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-800 focus:ring-1 focus:ring-neutral-800 focus:outline-none disabled:bg-neutral-50 disabled:text-neutral-400"
          >
            <option value="">{createForm.partner_type ? "Select a template" : "Select partner type first"}</option>
            {#each slideOverTemplates as tmpl}
              <option value={String(tmpl.id)}>{tmpl.name}</option>
            {/each}
          </select>
          {#if createFieldError("template")}<p class="mt-1 text-xs text-neutral-500">{createFieldError("template")}</p>{/if}
        </label>

        <!-- Source Lead -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Source Lead <span class="text-neutral-400">(optional)</span></span>
          <select
            value={createForm.lead}
            onchange={(e) => handleLeadSelect((e.target as HTMLSelectElement).value)}
            class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-800 focus:ring-1 focus:ring-neutral-800 focus:outline-none"
          >
            <option value="">None</option>
            {#each leads as lead}
              <option value={String(lead.id)}>{lead.first_name} {lead.last_name}</option>
            {/each}
          </select>
          {#if createFieldError("lead")}<p class="mt-1 text-xs text-neutral-500">{createFieldError("lead")}</p>{/if}
        </label>

        <!-- Contact Name -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Contact Name</span>
          <input
            type="text"
            bind:value={createForm.contact_name}
            placeholder="Full name"
            class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-800 focus:ring-1 focus:ring-neutral-800 focus:outline-none"
          />
          {#if createFieldError("contact_name")}<p class="mt-1 text-xs text-neutral-500">{createFieldError("contact_name")}</p>{/if}
        </label>

        <!-- Contact Email & Phone (2-col) -->
        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Contact Email</span>
            <input
              type="email"
              bind:value={createForm.contact_email}
              placeholder="email@example.com"
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-800 focus:ring-1 focus:ring-neutral-800 focus:outline-none"
            />
            {#if createFieldError("contact_email")}<p class="mt-1 text-xs text-neutral-500">{createFieldError("contact_email")}</p>{/if}
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Contact Phone</span>
            <input
              type="tel"
              bind:value={createForm.contact_phone}
              placeholder="+1 (555) 000-0000"
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-800 focus:ring-1 focus:ring-neutral-800 focus:outline-none"
            />
            {#if createFieldError("contact_phone")}<p class="mt-1 text-xs text-neutral-500">{createFieldError("contact_phone")}</p>{/if}
          </label>
        </div>

        <!-- Contract Reference -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Contract Reference <span class="text-neutral-400">(optional)</span></span>
          <input
            type="text"
            bind:value={createForm.contract_reference}
            placeholder="e.g. CNT-2026-001"
            class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-800 focus:ring-1 focus:ring-neutral-800 focus:outline-none"
          />
          {#if createFieldError("contract_reference")}<p class="mt-1 text-xs text-neutral-500">{createFieldError("contract_reference")}</p>{/if}
        </label>

        <!-- Notes -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Notes <span class="text-neutral-400">(optional)</span></span>
          <textarea
            bind:value={createForm.notes}
            rows="3"
            placeholder="Any additional details about this onboarding case..."
            class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-800 focus:ring-1 focus:ring-neutral-800 focus:outline-none resize-none"
          ></textarea>
          {#if createFieldError("notes")}<p class="mt-1 text-xs text-neutral-500">{createFieldError("notes")}</p>{/if}
        </label>
      </form>
    </div>

    <!-- Footer -->
    <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-neutral-100 shrink-0">
      <button
        type="button"
        onclick={closeSlideOver}
        class="px-4 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors"
      >
        Cancel
      </button>
      <button
        type="submit"
        form="create-case-form"
        disabled={saving}
        class="px-4 py-2.5 bg-neutral-800 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
      >
        {saving ? "Creating..." : "Create Case"}
      </button>
    </div>
  </div>
{/if}

<svelte:window onkeydown={(e) => { if (e.key === "Escape" && showDetailModal) closeDetailModal(); else if (e.key === "Escape" && showSlideOver) closeSlideOver(); }} />

<!-- ═══════════════════════ DETAIL FULLSCREEN MODAL ═══════════════════════ -->
{#if showDetailModal}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-6" style="backdrop-filter: blur(4px)" onclick={closeDetailModal}>
    <div class="w-full max-w-5xl max-h-[92vh] flex flex-col rounded-2xl border border-neutral-200 bg-white shadow-2xl overflow-hidden" onclick={(e) => e.stopPropagation()}>
    {#if detailLoading}
      <div class="flex items-center justify-center py-20"><div class="animate-pulse text-sm text-neutral-400">Loading case details...</div></div>
    {:else if detailData}
      <div class="bg-linear-to-br from-neutral-800 to-neutral-800 px-6 py-5 shrink-0 rounded-t-2xl">
        <div class="flex items-start justify-between">
          <div>
            <h2 class="text-lg font-semibold text-white">{detailData.title}</h2>
            <p class="mt-0.5 text-sm text-neutral-400">{detailData.contact_name} &middot; {detailData.contact_email}</p>
            <div class="mt-2 flex items-center gap-2">
              <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-medium {partnerTypeBadgeClass(detailData.partner_type)}">{detailData.partner_type_display}</span>
              <StatusBadge status={detailData.status} label={detailData.status_display} />
            </div>
          </div>
          <div class="flex items-center gap-2">
            {#if canSubmitForReview}<button onclick={() => (showSubmitReviewModal = true)} class="rounded-md border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-medium text-white hover:bg-white/20">Submit for Review</button>{/if}
            {#if canCreateErp}<button onclick={() => (showCreateErpModal = true)} class="rounded-md border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-medium text-white hover:bg-white/20">Create ERP Entity</button>{/if}
            {#if canGrantPortal}<button onclick={() => (showGrantPortalModal = true)} class="rounded-md border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-medium text-white hover:bg-white/20">Grant Portal Access</button>{/if}
            <button onclick={() => { closeDetailModal(); fetchCases(); fetchOverview(); }} class="rounded-md p-1.5 text-neutral-400 hover:text-white" aria-label="Close">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
            </button>
          </div>
        </div>
      </div>
      <div class="flex-1 overflow-y-auto">
        <div class="px-6 py-6 space-y-6">
          <!-- Stage Progress Stepper -->
          <div class="bg-white border border-neutral-200 rounded-lg shadow-sm p-6">
            <h2 class="text-sm font-semibold text-neutral-800 uppercase tracking-wider mb-5">Stage Progress</h2>
            {#if sortedStages.length === 0}<p class="text-sm text-neutral-400 italic">No stages configured.</p>
            {:else}
              <div class="relative">
                {#each sortedStages as stage, i}
                  {@const isLast = i === sortedStages.length - 1}
                  <button type="button" onclick={() => openStageModal(stage)} class="flex gap-4 w-full text-left group pb-6 last:pb-0 cursor-pointer hover:bg-neutral-50 -mx-2 px-2 rounded-lg transition-colors">
                    <div class="flex flex-col items-center shrink-0 pt-0.5">
                      <div class="w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold {stageCircleClass(stage.status)}">
                        {#if stage.status === "completed"}<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" /></svg>
                        {:else if stage.status === "waived"}<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M3 8.689c0-.864.933-1.406 1.683-.977l7.108 4.061a1.125 1.125 0 0 1 0 1.954l-7.108 4.061A1.125 1.125 0 0 1 3 16.811V8.69ZM12.75 8.689c0-.864.933-1.406 1.683-.977l7.108 4.061a1.125 1.125 0 0 1 0 1.954l-7.108 4.061a1.125 1.125 0 0 1-1.683-.977V8.69Z" /></svg>
                        {:else if stage.status === "blocked"}<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M18.364 18.364A9 9 0 0 0 5.636 5.636m12.728 12.728A9 9 0 0 1 5.636 5.636m12.728 12.728L5.636 5.636" /></svg>
                        {:else}{stage.stage_sequence}{/if}
                      </div>
                      {#if !isLast}<div class="w-px flex-1 bg-neutral-200 mt-1 min-h-[24px]"></div>{/if}
                    </div>
                    <div class="flex-1 min-w-0 -mt-0.5">
                      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
                        <div class="flex items-center gap-2 flex-wrap">
                          <span class="text-sm font-medium text-neutral-800 group-hover:underline">{stage.stage_name}</span>
                          <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {stageBadgeClass(stage.status)}">{formatLabel(stage.status)}</span>
                          {#if stage.is_required}<span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-neutral-800 text-white">Required</span>{:else}<span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-neutral-100 text-neutral-500">Optional</span>{/if}
                        </div>
                        {#if stage.completed_at}<span class="text-xs text-neutral-400">Completed {formatDate(stage.completed_at)}</span>{/if}
                      </div>
                      {#if stage.notes}<p class="text-xs text-neutral-500 mt-1 line-clamp-2">{stage.notes}</p>{/if}
                    </div>
                  </button>
                {/each}
              </div>
            {/if}
          </div>
          <!-- Three-Card Grid -->
          <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div class="bg-white border border-neutral-200 rounded-lg shadow-sm p-6">
              <h2 class="text-sm font-semibold text-neutral-800 uppercase tracking-wider mb-4">Case Information</h2>
              <div class="space-y-3">
                <div><p class="text-sm text-neutral-500">Title</p><p class="text-sm font-medium text-neutral-800 mt-0.5">{detailData.title}</p></div>
                <div><p class="text-sm text-neutral-500">Partner Type</p><p class="text-sm font-medium text-neutral-800 mt-0.5">{detailData.partner_type_display}</p></div>
                <div><p class="text-sm text-neutral-500">Template</p><p class="text-sm font-medium text-neutral-800 mt-0.5">{detailData.template_name || "--"}</p></div>
                <div><p class="text-sm text-neutral-500">Contract Reference</p><p class="text-sm font-medium text-neutral-800 mt-0.5">{detailData.contract_reference || "--"}</p></div>
                <div class="pt-2 border-t border-neutral-100"><p class="text-sm text-neutral-500">Contact</p><p class="text-sm font-medium text-neutral-800 mt-0.5">{detailData.contact_name}</p><p class="text-xs text-neutral-500 mt-0.5">{detailData.contact_email}</p>{#if detailData.contact_phone}<p class="text-xs text-neutral-500 mt-0.5">{detailData.contact_phone}</p>{/if}</div>
                <div><p class="text-sm text-neutral-500">Assigned Owner</p><p class="text-sm font-medium text-neutral-800 mt-0.5">{detailData.assigned_owner_name || "--"}</p></div>
                <div><p class="text-sm text-neutral-500">Created</p><p class="text-sm font-medium text-neutral-800 mt-0.5">{formatDateTime(detailData.created_at)}</p></div>
                <div class="pt-2 border-t border-neutral-100"><p class="text-sm text-neutral-500 mb-1">Notes</p>{#if detailData.notes}<p class="text-sm text-neutral-700 whitespace-pre-wrap">{detailData.notes}</p>{:else}<p class="text-sm text-neutral-400 italic">No notes</p>{/if}</div>
              </div>
            </div>
            <div class="bg-white border border-neutral-200 rounded-lg shadow-sm p-6">
              <h2 class="text-sm font-semibold text-neutral-800 uppercase tracking-wider mb-4">Source & Target Entities</h2>
              <div class="space-y-5">
                <div><p class="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-2">Source Lead</p>{#if detailData.lead}<div class="p-3 bg-neutral-50 rounded-lg"><p class="text-sm font-medium text-neutral-800">{detailData.lead_name}</p><p class="text-xs text-neutral-500 mt-1">{detailData.contact_email}</p></div>{:else}<p class="text-sm text-neutral-400 italic">No source lead</p>{/if}</div>
                <div><p class="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-2">Target Entity</p><div class="p-3 bg-neutral-50 rounded-lg"><p class="text-xs text-neutral-500 mb-1">{detailData.partner_type_display}</p><p class="text-sm font-medium text-neutral-800">{detailData.customer_name || detailData.contractor_name || detailData.investor_name || "--"}</p></div></div>
                <div><p class="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-2">ERP Profile</p>{#if detailData.has_erp_profile}<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-700">Active</span>{:else}<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-neutral-100 text-neutral-500">Not Created</span>{/if}</div>
              </div>
            </div>
            <div class="bg-white border border-neutral-200 rounded-lg shadow-sm p-6">
              <h2 class="text-sm font-semibold text-neutral-800 uppercase tracking-wider mb-4">Portal Access & Entitlements</h2>
              <div class="space-y-5">
                <div><p class="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-2">Portal Access</p>{#if detailData.has_portal_access}<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-700">Granted</span>{:else}<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-neutral-100 text-neutral-500">Not Granted</span>{/if}</div>
                <div>
                  <div class="flex items-center justify-between mb-2"><p class="text-xs font-semibold text-neutral-500 uppercase tracking-wider">Entitlements</p><button onclick={() => (showEntitlementModal = true)} class="text-xs text-neutral-500 hover:text-neutral-800 underline">+ Add</button></div>
                  {#if detailData.entitlements.length === 0}<p class="text-sm text-neutral-400 italic">No entitlements</p>
                  {:else}<div class="space-y-2">{#each detailData.entitlements as ent}<div class="p-2 bg-neutral-50 rounded-lg flex items-center justify-between"><div><span class="text-xs font-medium text-neutral-800 capitalize">{ent.portal_role}</span>{#if ent.contract_reference}<span class="text-xs text-neutral-400 ml-2">{ent.contract_reference}</span>{/if}</div><span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium {ent.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-neutral-100 text-neutral-400'}">{ent.is_active ? "Active" : "Inactive"}</span></div>{/each}</div>{/if}
                </div>
              </div>
            </div>
          </div>
          <!-- Approvals -->
          {#if detailData.approvals.length > 0}
            <div class="bg-white border border-neutral-200 rounded-lg shadow-sm p-6">
              <div class="flex items-center justify-between mb-4"><h2 class="text-sm font-semibold text-neutral-800 uppercase tracking-wider">Approval History</h2><button onclick={() => (showApprovalModal = true)} class="text-xs text-neutral-500 hover:text-neutral-800 underline">+ Record</button></div>
              <div class="space-y-3">{#each detailData.approvals as approval}<div class="flex items-start gap-3 p-3 bg-neutral-50 rounded-lg"><div class="flex-1"><div class="flex items-center gap-2"><span class="text-sm font-medium text-neutral-800">{approval.approver_name}</span><span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {decisionBadgeClass(approval.decision)}">{formatLabel(approval.decision)}</span></div>{#if approval.comments}<p class="text-xs text-neutral-500 mt-1">{approval.comments}</p>{/if}</div><span class="text-xs text-neutral-400 shrink-0">{formatDateTime(approval.created_at)}</span></div>{/each}</div>
            </div>
          {/if}
          <!-- Audit Timeline -->
          <div class="bg-white border border-neutral-200 rounded-lg shadow-sm p-6">
            <h2 class="text-sm font-semibold text-neutral-800 uppercase tracking-wider mb-5">Audit Timeline</h2>
            {#if timelineLoading}<p class="text-sm text-neutral-400">Loading...</p>
            {:else if sortedTimeline.length === 0}<p class="text-sm text-neutral-400 italic">No events recorded.</p>
            {:else}
              <div class="relative">{#each sortedTimeline as event, i}{@const isLast = i === sortedTimeline.length - 1}<div class="flex gap-4 pb-5 last:pb-0"><div class="flex flex-col items-center shrink-0"><div class="w-7 h-7 rounded-full flex items-center justify-center text-xs {eventCircleClass(event.event_type)}"><svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" /></svg></div>{#if !isLast}<div class="w-px flex-1 bg-neutral-200 mt-1"></div>{/if}</div><div class="flex-1 min-w-0 -mt-0.5"><div class="flex items-center justify-between gap-2"><span class="text-sm font-medium text-neutral-800">{formatEventType(event.event_type)}</span><span class="text-xs text-neutral-400 shrink-0">{formatDateTime(event.created_at)}</span></div>{#if event.description}<p class="text-xs text-neutral-500 mt-0.5">{event.description}</p>{/if}<p class="text-xs text-neutral-400 mt-0.5">by {event.actor_name}</p></div></div>{/each}</div>
            {/if}
          </div>
        </div>
      </div>
    {/if}
    </div>
  </div>
  <!-- Sub-modals (z-60 to stack above) -->
  {#if showStageModal}<div class="fixed inset-0 z-60 flex items-center justify-center bg-black/30 p-4" style="backdrop-filter: blur(4px)"><div class="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl"><h3 class="text-lg font-semibold text-neutral-800 mb-2">Update Stage Status</h3><p class="text-sm text-neutral-500 mb-4">Stage: <strong>{stageForm.stage_name}</strong></p><div class="space-y-4"><label class="block text-sm font-medium text-neutral-700"><span class="block mb-1 text-xs">New Status</span><select bind:value={stageForm.new_status} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800"><option value="not_started">Not Started</option><option value="in_progress">In Progress</option><option value="completed">Completed</option><option value="waived">Waived</option><option value="blocked">Blocked</option></select></label><label class="block text-sm font-medium text-neutral-700"><span class="block mb-1 text-xs">Notes</span><textarea bind:value={stageForm.notes} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 resize-none"></textarea></label></div><div class="mt-5 flex justify-end gap-3"><button onclick={() => (showStageModal = false)} class="px-4 py-2 text-sm font-medium text-neutral-600">Cancel</button><button onclick={handleMarkStage} disabled={savingStage} class="px-4 py-2 text-sm font-semibold text-white bg-neutral-800 rounded-lg hover:bg-neutral-800 disabled:opacity-50">{savingStage ? "Saving..." : "Update"}</button></div></div></div>{/if}
  {#if showSubmitReviewModal}<div class="fixed inset-0 z-60 flex items-center justify-center bg-black/30 p-4" style="backdrop-filter: blur(4px)"><div class="w-full max-w-sm rounded-2xl bg-white p-6 shadow-2xl"><h3 class="text-lg font-semibold text-neutral-800 mb-2">Submit for Review</h3><p class="text-sm text-neutral-500 mb-4">All required stages are complete. Submit?</p><div class="flex justify-end gap-3"><button onclick={() => (showSubmitReviewModal = false)} class="px-4 py-2 text-sm font-medium text-neutral-600">Cancel</button><button onclick={handleSubmitReview} disabled={submittingReview} class="px-4 py-2 text-sm font-semibold text-white bg-neutral-800 rounded-lg hover:bg-neutral-800 disabled:opacity-50">{submittingReview ? "Submitting..." : "Submit"}</button></div></div></div>{/if}
  {#if showCreateErpModal}<div class="fixed inset-0 z-60 flex items-center justify-center bg-black/30 p-4" style="backdrop-filter: blur(4px)"><div class="w-full max-w-sm rounded-2xl bg-white p-6 shadow-2xl"><h3 class="text-lg font-semibold text-neutral-800 mb-2">Create ERP Entity</h3><p class="text-sm text-neutral-500 mb-4">Create the {detailData?.partner_type_display} record?</p><div class="flex justify-end gap-3"><button onclick={() => (showCreateErpModal = false)} class="px-4 py-2 text-sm font-medium text-neutral-600">Cancel</button><button onclick={handleCreateErp} disabled={creatingErp} class="px-4 py-2 text-sm font-semibold text-white bg-neutral-800 rounded-lg hover:bg-neutral-800 disabled:opacity-50">{creatingErp ? "Creating..." : "Create"}</button></div></div></div>{/if}
  {#if showGrantPortalModal}<div class="fixed inset-0 z-60 flex items-center justify-center bg-black/30 p-4" style="backdrop-filter: blur(4px)"><div class="w-full max-w-sm rounded-2xl bg-white p-6 shadow-2xl"><h3 class="text-lg font-semibold text-neutral-800 mb-2">Grant Portal Access</h3><p class="text-sm text-neutral-500 mb-4">Grant partner access to the self-service portal?</p><div class="flex justify-end gap-3"><button onclick={() => (showGrantPortalModal = false)} class="px-4 py-2 text-sm font-medium text-neutral-600">Cancel</button><button onclick={handleGrantPortal} disabled={grantingPortal} class="px-4 py-2 text-sm font-semibold text-white bg-neutral-800 rounded-lg hover:bg-neutral-800 disabled:opacity-50">{grantingPortal ? "Granting..." : "Grant Access"}</button></div></div></div>{/if}
  {#if showApprovalModal}<div class="fixed inset-0 z-60 flex items-center justify-center bg-black/30 p-4" style="backdrop-filter: blur(4px)"><div class="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl"><h3 class="text-lg font-semibold text-neutral-800 mb-4">Record Approval</h3><div class="space-y-4"><label class="block text-sm font-medium text-neutral-700"><span class="block mb-1 text-xs">Decision</span><select bind:value={approvalForm.decision} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800"><option value="approved">Approved</option><option value="rejected">Rejected</option><option value="changes_required">Changes Required</option></select></label><label class="block text-sm font-medium text-neutral-700"><span class="block mb-1 text-xs">Approver Role</span><input bind:value={approvalForm.approver_role_label} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" /></label><label class="block text-sm font-medium text-neutral-700"><span class="block mb-1 text-xs">Comments</span><textarea bind:value={approvalForm.comments} rows="3" class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 resize-none"></textarea></label></div><div class="mt-5 flex justify-end gap-3"><button onclick={() => (showApprovalModal = false)} class="px-4 py-2 text-sm font-medium text-neutral-600">Cancel</button><button onclick={handleRecordApproval} disabled={recordingApproval} class="px-4 py-2 text-sm font-semibold text-white bg-neutral-800 rounded-lg hover:bg-neutral-800 disabled:opacity-50">{recordingApproval ? "Recording..." : "Record"}</button></div></div></div>{/if}
  {#if showEntitlementModal}<div class="fixed inset-0 z-60 flex items-center justify-center bg-black/30 p-4" style="backdrop-filter: blur(4px)"><div class="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl"><h3 class="text-lg font-semibold text-neutral-800 mb-4">Provision Entitlement</h3><div class="space-y-4"><label class="block text-sm font-medium text-neutral-700"><span class="block mb-1 text-xs">Portal Role</span><select bind:value={entitlementForm.portal_role} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800"><option value="client">Client</option><option value="contractor">Contractor</option><option value="investor">Investor</option><option value="vendor">Vendor</option></select></label><label class="block text-sm font-medium text-neutral-700"><span class="block mb-1 text-xs">Contract Reference</span><input bind:value={entitlementForm.contract_reference} class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" placeholder="Optional" /></label></div><div class="mt-5 flex justify-end gap-3"><button onclick={() => (showEntitlementModal = false)} class="px-4 py-2 text-sm font-medium text-neutral-600">Cancel</button><button onclick={handleProvisionEntitlement} disabled={provisioningEntitlement} class="px-4 py-2 text-sm font-semibold text-white bg-neutral-800 rounded-lg hover:bg-neutral-800 disabled:opacity-50">{provisioningEntitlement ? "Provisioning..." : "Provision"}</button></div></div></div>{/if}
{/if}

<style>
  .slide-over-enter {
    animation: slide-in-right 0.25s ease-out;
  }

  @keyframes slide-in-right {
    from {
      transform: translateX(100%);
    }
    to {
      transform: translateX(0);
    }
  }
</style>

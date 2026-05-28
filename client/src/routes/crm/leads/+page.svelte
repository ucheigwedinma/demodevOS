<script lang="ts">
  import { onMount } from "svelte";
  import { api, ApiError } from "$lib/api";
  import { useAutoRefresh } from "$lib/realtime.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import { can } from "$lib/permissions";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DataStateBanner from "$lib/components/DataStateBanner.svelte";
  import type {
    LeadDetail,
    LeadListItem,
    LeadActivity,
    LeadProjectInterest,
    LeadUnitPreference,
    PipelineOverview,
    PipelineStage,
    LeadSource,
    CRMBroker,
    PaginatedResponse,
  } from "$lib/types";

  // --- Pipeline Overview ---
  let overview = $state<PipelineOverview | null>(null);
  let overviewLoading = $state(true);

  // --- Leads Table ---
  let leads = $state<LeadListItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let listError = $state<string | null>(null);
  let currentPage = $state(1);
  const pageSize = 25;

  // --- Filters ---
  let search = $state("");
  let stageFilter = $state("");
  let statusFilter = $state("");
  let priorityFilter = $state("");

  // --- Reference Data ---
  let sources = $state<LeadSource[]>([]);
  let brokers = $state<CRMBroker[]>([]);

  // --- Slide-over ---
  let showSlideOver = $state(false);
  let savingLead = $state(false);
  let createErrors = $state<Record<string, string[]>>({});
  let createForm = $state({
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    secondary_phone: "",
    company: "",
    nationality: "",
    lead_type: "buyer" as string,
    source: "",
    broker: "",
    referral_name: "",
    budget_min: "",
    budget_max: "",
    preferred_locations: "",
    payment_capability: "undetermined" as string,
    priority: "medium" as string,
    score: "50",
    tags: "",
    notes: "",
  });

  type AccordionSection = "overview" | "activities" | "preferences" | "timeline" | "actions";

  type LeadInlineEditForm = {
    first_name: string;
    last_name: string;
    email: string;
    phone: string;
    secondary_phone: string;
    company: string;
    nationality: string;
    lead_type: "buyer" | "tenant" | "investor";
    priority: "low" | "medium" | "high" | "urgent";
    score: number;
    tags: string;
    budget_min: string;
    budget_max: string;
    preferred_locations: string;
    payment_capability: "cash" | "mortgage" | "installment" | "mixed" | "undetermined";
    notes: string;
  };

  const pipelineStages: { key: PipelineStage; label: string }[] = [
    { key: "inquiry", label: "Inquiry" },
    { key: "qualified", label: "Qualified" },
    { key: "site_visit", label: "Site Visit" },
    { key: "offer_made", label: "Offer Made" },
    { key: "reservation", label: "Reservation" },
    { key: "spa_issued", label: "SPA Issued" },
    { key: "closed", label: "Closed" },
  ];

  const leadTypeLabels: Record<string, string> = {
    buyer: "Buyer",
    tenant: "Tenant",
    investor: "Investor",
  };

  const priorityLabels: Record<string, string> = {
    low: "Low",
    medium: "Medium",
    high: "High",
    urgent: "Urgent",
  };

  let expandedSectionsByLeadId = $state<Record<number, AccordionSection[]>>({});
  let expandedLeadId = $state<number | null>(null);
  let detailsByLeadId = $state<Record<number, LeadDetail>>({});
  let detailLoadingByLeadId = $state<Record<number, boolean>>({});
  let detailErrorByLeadId = $state<Record<number, string>>({});

  let stageChangeNotesByLeadId = $state<Record<number, string>>({});
  let stageChangingByLeadId = $state<Record<number, boolean>>({});
  let convertNotesByLeadId = $state<Record<number, string>>({});
  let convertingByLeadId = $state<Record<number, boolean>>({});
  let lostReasonByLeadId = $state<Record<number, string>>({});
  let markingLostByLeadId = $state<Record<number, boolean>>({});

  let editModeByLeadId = $state<Record<number, boolean>>({});
  let editFormsByLeadId = $state<Record<number, LeadInlineEditForm>>({});
  let savingEditByLeadId = $state<Record<number, boolean>>({});

  const canViewLeadDetails = $derived(can("crm.all", "view"));
  const canEditLeads = $derived(can("crm.all", "edit"));

  // Dev fill
  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  const LEAD_SAMPLES = [
    { first_name: "Chukwuemeka", last_name: "Obi", email: "c.obi@obiholdings.ng", phone: "+2348031234567", secondary_phone: "+2348091234568", company: "Obi Holdings Ltd", nationality: "Nigerian", lead_type: "buyer", referral_name: "Adaeze Nwosu", budget_min: "85000000", budget_max: "150000000", preferred_locations: "Lekki Phase 1, Ikoyi", payment_capability: "cash", priority: "high", score: "82", tags: "HNI, cash buyer, diaspora referral", notes: "MD of Obi Holdings. Interested in 4-bed waterfront property. Prefers ground floor with private garden." },
    { first_name: "Amina", last_name: "Bello", email: "amina.bello@bellocapital.com", phone: "+2348051234569", secondary_phone: "", company: "Bello Capital Partners", nationality: "Nigerian", lead_type: "investor", referral_name: "", budget_min: "120000000", budget_max: "250000000", preferred_locations: "Victoria Island, Eko Atlantic", payment_capability: "mixed", priority: "urgent", score: "91", tags: "institutional investor, portfolio buyer", notes: "Looking to acquire 3-5 units for rental portfolio. Prefers new builds with property management." },
    { first_name: "Tunde", last_name: "Ogundimu", email: "tunde@ogundimugroup.com", phone: "+2348061234570", secondary_phone: "+2348071234571", company: "Ogundimu Group", nationality: "Nigerian", lead_type: "buyer", referral_name: "Femi Adeyemi", budget_min: "30000000", budget_max: "55000000", preferred_locations: "Lekki Phase 2, Ajah", payment_capability: "mortgage", priority: "medium", score: "65", tags: "first-time buyer, mortgage pre-approved", notes: "Young professional. GTBank mortgage pre-approval in hand. Wants 3-bed with BQ." },
    { first_name: "Ngozi", last_name: "Eze", email: "ngozi.eze@ezelegal.ng", phone: "+2348081234572", secondary_phone: "", company: "Eze & Associates Legal", nationality: "Nigerian", lead_type: "buyer", referral_name: "Kemi Adekunle", budget_min: "60000000", budget_max: "95000000", preferred_locations: "Ikoyi, Banana Island", payment_capability: "installment", priority: "high", score: "78", tags: "legal professional, instalment plan", notes: "Senior partner at Eze & Associates. Prefers 18-month payment plan. Wants quiet neighbourhood." },
  ];

  let devIdx = $state(0);

  function devFillLead() {
    const sample = LEAD_SAMPLES[devIdx % LEAD_SAMPLES.length];
    devIdx++;
    createForm.first_name = sample.first_name;
    createForm.last_name = sample.last_name;
    createForm.email = sample.email;
    createForm.phone = sample.phone;
    createForm.secondary_phone = sample.secondary_phone;
    createForm.company = sample.company;
    createForm.nationality = sample.nationality;
    createForm.lead_type = sample.lead_type;
    createForm.referral_name = sample.referral_name;
    createForm.budget_min = sample.budget_min;
    createForm.budget_max = sample.budget_max;
    createForm.preferred_locations = sample.preferred_locations;
    createForm.payment_capability = sample.payment_capability;
    createForm.priority = sample.priority;
    createForm.score = sample.score;
    createForm.tags = sample.tags;
    createForm.notes = sample.notes;
    if (sources.length > 0) createForm.source = String(sources[devIdx % sources.length].id);
    if (brokers.length > 0) createForm.broker = String(brokers[devIdx % brokers.length].id);
  }

  function createFieldError(field: string): string {
    return createErrors[field]?.[0] ?? "";
  }

  function resetCreateForm() {
    createForm = {
      first_name: "",
      last_name: "",
      email: "",
      phone: "",
      secondary_phone: "",
      company: "",
      nationality: "",
      lead_type: "buyer",
      source: "",
      broker: "",
      referral_name: "",
      budget_min: "",
      budget_max: "",
      preferred_locations: "",
      payment_capability: "undetermined",
      priority: "medium",
      score: "50",
      tags: "",
      notes: "",
    };
    createErrors = {};
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

  let totalFunnelCount = $derived(
    overview ? overview.pipeline_stages.reduce((sum, s) => sum + s.count, 0) : 0,
  );

  // --- Priority styling ---
  const priorityDotClasses: Record<string, string> = {
    low: "bg-neutral-200",
    medium: "bg-neutral-400",
    high: "bg-neutral-600",
    urgent: "bg-neutral-900",
  };

  const funnelSegmentClasses: Record<string, string> = {
    inquiry: "bg-neutral-200",
    qualified: "bg-neutral-300",
    site_visit: "bg-neutral-400",
    offer_made: "bg-neutral-500",
    reservation: "bg-neutral-600",
    spa_issued: "bg-neutral-700",
    closed: "bg-neutral-900",
  };

  const funnelTextClasses: Record<string, string> = {
    inquiry: "text-neutral-700",
    qualified: "text-neutral-800",
    site_visit: "text-neutral-900",
    offer_made: "text-white",
    reservation: "text-white",
    spa_issued: "text-white",
    closed: "text-white",
  };

  const stageDateKeys: Record<PipelineStage, keyof LeadDetail> = {
    inquiry: "inquiry_date",
    qualified: "qualified_date",
    site_visit: "site_visit_date",
    offer_made: "offer_date",
    reservation: "reservation_date",
    spa_issued: "spa_issued_date",
    closed: "closed_date",
  };

  // --- Helpers ---
  function formatDate(dateStr: string): string {
    if (!dateStr) return "";
    const d = new Date(dateStr + "T00:00:00");
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function formatBudget(min: string | null, max: string | null): string {
    if (!min && !max) return "\u2014";
    const parts: string[] = [];
    if (min) parts.push(currency.format(parseFloat(min)));
    if (max) parts.push(currency.format(parseFloat(max)));
    return parts.join(" \u2013 ");
  }

  function parseTags(raw: string): string[] {
    return raw
      .split(",")
      .map((entry) => entry.trim())
      .filter(Boolean);
  }

  function parseList(raw: string): string[] {
    return raw
      .split(",")
      .map((entry) => entry.trim())
      .filter(Boolean);
  }

  function fmtDateTime(value: string | null | undefined): string {
    if (!value) return "\u2014";
    const dt = new Date(value);
    if (Number.isNaN(dt.getTime())) return "\u2014";
    return dt.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function stageLabel(stage: PipelineStage): string {
    return pipelineStages.find((item) => item.key === stage)?.label ?? stage;
  }

  function stageIndex(stage: PipelineStage): number {
    return pipelineStages.findIndex((item) => item.key === stage);
  }

  function nextStage(stage: PipelineStage): PipelineStage | null {
    const idx = stageIndex(stage);
    if (idx < 0 || idx >= pipelineStages.length - 1) return null;
    return pipelineStages[idx + 1].key;
  }

  function buildInlineEditForm(detail: LeadDetail): LeadInlineEditForm {
    return {
      first_name: detail.first_name,
      last_name: detail.last_name,
      email: detail.email ?? "",
      phone: detail.phone ?? "",
      secondary_phone: detail.secondary_phone ?? "",
      company: detail.company ?? "",
      nationality: detail.nationality ?? "",
      lead_type: detail.lead_type,
      priority: detail.priority,
      score: detail.score,
      tags: detail.tags.join(", "),
      budget_min: detail.budget_min ?? "",
      budget_max: detail.budget_max ?? "",
      preferred_locations: detail.preferred_locations.join(", "),
      payment_capability: detail.payment_capability,
      notes: detail.notes ?? "",
    };
  }

  function normalizeError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      if (error.status === 403) return "You do not have permission for this action.";
      const detail = error.data?.detail;
      if (typeof detail === "string" && detail.trim().length > 0) return detail;
    }
    return fallback;
  }

  function sectionIsOpen(leadId: number, section: AccordionSection): boolean {
    const sections = expandedSectionsByLeadId[leadId] ?? [];
    return sections.includes(section);
  }

  function ensureDefaultSections(leadId: number) {
    if (expandedSectionsByLeadId[leadId]) return;
    expandedSectionsByLeadId = {
      ...expandedSectionsByLeadId,
      [leadId]: ["overview", "actions"],
    };
  }

  function toggleSection(leadId: number, section: AccordionSection) {
    const current = expandedSectionsByLeadId[leadId] ?? [];
    const next = current.includes(section)
      ? current.filter((item) => item !== section)
      : [...current, section];
    expandedSectionsByLeadId = {
      ...expandedSectionsByLeadId,
      [leadId]: next,
    };
  }

  async function loadLeadDetail(leadId: number, force = false) {
    if (!force && detailsByLeadId[leadId]) return;
    detailLoadingByLeadId = { ...detailLoadingByLeadId, [leadId]: true };
    detailErrorByLeadId = { ...detailErrorByLeadId, [leadId]: "" };
    try {
      const detail = await api.get<LeadDetail>(`/crm/leads/${leadId}/`);
      detailsByLeadId = { ...detailsByLeadId, [leadId]: detail };
      editFormsByLeadId = {
        ...editFormsByLeadId,
        [leadId]: buildInlineEditForm(detail),
      };
    } catch (error) {
      console.error("[crm/leads]", error);
      detailErrorByLeadId = {
        ...detailErrorByLeadId,
        [leadId]: normalizeError(error, "Could not load lead details."),
      };
    } finally {
      detailLoadingByLeadId = { ...detailLoadingByLeadId, [leadId]: false };
    }
  }

  async function toggleLeadExpanded(leadId: number) {
    if (expandedLeadId === leadId) {
      expandedLeadId = null;
      return;
    }
    expandedLeadId = leadId;
    ensureDefaultSections(leadId);
    if (canViewLeadDetails) {
      await loadLeadDetail(leadId);
    }
  }

  async function refreshLeadAfterMutation(leadId: number) {
    await Promise.all([
      fetchLeads(),
      fetchOverview(),
      loadLeadDetail(leadId, true),
    ]);
  }

  function openInlineEdit(leadId: number) {
    const detail = detailsByLeadId[leadId];
    if (!detail) return;
    editFormsByLeadId = {
      ...editFormsByLeadId,
      [leadId]: buildInlineEditForm(detail),
    };
    editModeByLeadId = { ...editModeByLeadId, [leadId]: true };
  }

  function updateInlineEditField(
    leadId: number,
    field: keyof LeadInlineEditForm,
    value: LeadInlineEditForm[keyof LeadInlineEditForm],
  ) {
    const current = editFormsByLeadId[leadId];
    if (!current) return;
    editFormsByLeadId = {
      ...editFormsByLeadId,
      [leadId]: {
        ...current,
        [field]: value,
      },
    };
  }

  function cancelInlineEdit(leadId: number) {
    const detail = detailsByLeadId[leadId];
    if (detail) {
      editFormsByLeadId = {
        ...editFormsByLeadId,
        [leadId]: buildInlineEditForm(detail),
      };
    }
    editModeByLeadId = { ...editModeByLeadId, [leadId]: false };
  }

  async function saveInlineEdit(leadId: number) {
    const form = editFormsByLeadId[leadId];
    if (!form) return;
    savingEditByLeadId = { ...savingEditByLeadId, [leadId]: true };
    try {
      const payload: Record<string, unknown> = {
        first_name: form.first_name,
        last_name: form.last_name,
        email: form.email || null,
        phone: form.phone || null,
        secondary_phone: form.secondary_phone || null,
        company: form.company || null,
        nationality: form.nationality || null,
        lead_type: form.lead_type,
        priority: form.priority,
        score: form.score,
        tags: parseTags(form.tags),
        budget_min: form.budget_min || null,
        budget_max: form.budget_max || null,
        preferred_locations: parseList(form.preferred_locations),
        payment_capability: form.payment_capability,
        notes: form.notes || "",
      };
      const updated = await api.patch<LeadDetail>(`/crm/leads/${leadId}/`, payload);
      detailsByLeadId = { ...detailsByLeadId, [leadId]: updated };
      editFormsByLeadId = {
        ...editFormsByLeadId,
        [leadId]: buildInlineEditForm(updated),
      };
      editModeByLeadId = { ...editModeByLeadId, [leadId]: false };
      toast.success("Lead updated", "Changes saved successfully.");
      await Promise.all([fetchLeads(), fetchOverview()]);
    } catch (error) {
      console.error("[crm/leads]", error);
      toast.error("Update failed", normalizeError(error, "Could not update lead."));
    } finally {
      savingEditByLeadId = { ...savingEditByLeadId, [leadId]: false };
    }
  }

  async function advanceStageForLead(leadId: number) {
    const detail = detailsByLeadId[leadId];
    if (!detail) return;
    const stage = nextStage(detail.pipeline_stage);
    if (!stage) return;
    stageChangingByLeadId = { ...stageChangingByLeadId, [leadId]: true };
    try {
      await api.post(`/crm/leads/${leadId}/change_stage/`, {
        stage,
        notes: stageChangeNotesByLeadId[leadId] ?? "",
      });
      stageChangeNotesByLeadId = { ...stageChangeNotesByLeadId, [leadId]: "" };
      toast.success("Stage updated", `Lead moved to ${stageLabel(stage)}.`);
      await refreshLeadAfterMutation(leadId);
    } catch (error) {
      console.error("[crm/leads]", error);
      toast.error("Stage update failed", normalizeError(error, "Could not change stage."));
    } finally {
      stageChangingByLeadId = { ...stageChangingByLeadId, [leadId]: false };
    }
  }

  async function convertLeadForRow(leadId: number) {
    convertingByLeadId = { ...convertingByLeadId, [leadId]: true };
    try {
      await api.post(`/crm/leads/${leadId}/convert/`, {
        notes: convertNotesByLeadId[leadId] ?? "",
      });
      convertNotesByLeadId = { ...convertNotesByLeadId, [leadId]: "" };
      toast.success("Lead converted", "Lead has been converted to customer.");
      await refreshLeadAfterMutation(leadId);
    } catch (error) {
      console.error("[crm/leads]", error);
      toast.error("Conversion failed", normalizeError(error, "Could not convert lead."));
    } finally {
      convertingByLeadId = { ...convertingByLeadId, [leadId]: false };
    }
  }

  async function markLeadLostForRow(leadId: number) {
    const reason = (lostReasonByLeadId[leadId] ?? "").trim();
    if (!reason) {
      toast.error("Reason required", "Please provide a reason before marking as lost.");
      return;
    }
    markingLostByLeadId = { ...markingLostByLeadId, [leadId]: true };
    try {
      await api.post(`/crm/leads/${leadId}/mark_lost/`, { reason });
      lostReasonByLeadId = { ...lostReasonByLeadId, [leadId]: "" };
      toast.success("Lead marked lost", "Lead status has been updated.");
      await refreshLeadAfterMutation(leadId);
    } catch (error) {
      console.error("[crm/leads]", error);
      toast.error("Action failed", normalizeError(error, "Could not mark lead as lost."));
    } finally {
      markingLostByLeadId = { ...markingLostByLeadId, [leadId]: false };
    }
  }

  async function toggleActivityComplete(leadId: number, activity: LeadActivity) {
    try {
      await api.patch(`/crm/leads/${leadId}/activities/${activity.id}/`, {
        is_completed: !activity.is_completed,
        completed_at: !activity.is_completed ? new Date().toISOString() : null,
      });
      await Promise.all([loadLeadDetail(leadId, true), fetchLeads()]);
    } catch (error) {
      console.error("[crm/leads]", error);
      toast.error("Update failed", normalizeError(error, "Could not update activity."));
    }
  }

  async function deleteActivity(leadId: number, activityId: number) {
    if (!confirm("Delete this activity?")) return;
    try {
      await api.delete(`/crm/leads/${leadId}/activities/${activityId}/`);
      toast.success("Deleted", "Activity removed.");
      await Promise.all([loadLeadDetail(leadId, true), fetchLeads()]);
    } catch (error) {
      console.error("[crm/leads]", error);
      toast.error("Delete failed", normalizeError(error, "Could not delete activity."));
    }
  }

  function interestLevelClass(interest: LeadProjectInterest): string {
    if (interest.interest_level === "high") return "bg-neutral-900 text-white";
    if (interest.interest_level === "medium") return "bg-neutral-200 text-neutral-700";
    return "bg-neutral-100 text-neutral-500";
  }

  function preferenceSummary(preference: LeadUnitPreference): string {
    const segments: string[] = [];
    if (preference.min_bedrooms !== null || preference.max_bedrooms !== null) {
      segments.push(`Bedrooms ${preference.min_bedrooms ?? "?"}-${preference.max_bedrooms ?? "?"}`);
    }
    if (preference.min_area_sqft || preference.max_area_sqft) {
      segments.push(`Area ${preference.min_area_sqft ?? "?"}-${preference.max_area_sqft ?? "?"} sqft`);
    }
    if (preference.floor_preference) segments.push(`Floor: ${preference.floor_preference}`);
    if (preference.view_preference) segments.push(`View: ${preference.view_preference}`);
    return segments.length > 0 ? segments.join(" • ") : "No specific constraints recorded.";
  }

  function paymentLabel(p: string): string {
    const map: Record<string, string> = {
      cash: "Cash",
      mortgage: "Mortgage",
      installment: "Installment",
      mixed: "Mixed",
      undetermined: "TBD",
    };
    return map[p] ?? p;
  }

  function normalizeListResponse<T>(
    response: T[] | PaginatedResponse<T> | null | undefined,
  ): T[] {
    if (Array.isArray(response)) return response;
    if (response && Array.isArray(response.results)) return response.results;
    return [];
  }

  // --- Data Fetching ---
  async function fetchOverview() {
    overviewLoading = true;
    try {
      overview = await api.get<PipelineOverview>("/crm/pipeline/overview/");
    } catch (err) {
      console.error("[crm/leads]", err);
      overview = null;
    } finally {
      overviewLoading = false;
    }
  }

  async function fetchLeads() {
    loading = true;
    listError = null;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        page_size: String(pageSize),
      };
      if (search) params.search = search;
      if (stageFilter) params.pipeline_stage = stageFilter;
      if (statusFilter) params.status = statusFilter;
      if (priorityFilter) params.priority = priorityFilter;

      const res = await api.get<PaginatedResponse<LeadListItem>>(
        "/crm/leads/",
        params,
      );
      leads = res.results;
      totalCount = res.count;
      if (expandedLeadId !== null && !res.results.some((row) => row.id === expandedLeadId)) {
        expandedLeadId = null;
      }
    } catch (err) {
      console.error("[crm/leads]", err);
      leads = [];
      totalCount = 0;
      expandedLeadId = null;
      listError = err instanceof Error ? err.message : "Could not load leads.";
    } finally {
      loading = false;
    }
  }

  async function fetchSources() {
    try {
      const res = await api.get<LeadSource[] | PaginatedResponse<LeadSource>>("/crm/sources/");
      sources = normalizeListResponse(res);
    } catch (err) {
      console.error("[crm/leads]", err);
      sources = [];
    }
  }

  async function fetchBrokers() {
    try {
      const res = await api.get<CRMBroker[] | PaginatedResponse<CRMBroker>>("/crm/brokers/");
      brokers = normalizeListResponse(res);
    } catch (err) {
      console.error("[crm/leads]", err);
      brokers = [];
    }
  }

  // --- Event Handlers ---
  let debounceTimer: ReturnType<typeof setTimeout>;

  function handleSearchInput(value: string) {
    search = value;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      currentPage = 1;
      fetchLeads();
    }, 300);
  }

  function handleStageChange(value: string) {
    stageFilter = value;
    currentPage = 1;
    fetchLeads();
  }

  function handleStatusChange(value: string) {
    statusFilter = value;
    currentPage = 1;
    fetchLeads();
  }

  function handlePriorityChange(value: string) {
    priorityFilter = value;
    currentPage = 1;
    fetchLeads();
  }

  function handleFunnelClick(stage: string) {
    stageFilter = stage;
    currentPage = 1;
    fetchLeads();
  }

  function goToPage(page: number) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    fetchLeads();
  }

  async function handleCreateLead(e: Event) {
    e.preventDefault();
    createErrors = {};
    savingLead = true;

    try {
      const payload: Record<string, unknown> = {
        first_name: createForm.first_name,
        last_name: createForm.last_name,
        email: createForm.email || null,
        phone: createForm.phone || null,
        secondary_phone: createForm.secondary_phone || null,
        company: createForm.company || null,
        nationality: createForm.nationality || null,
        lead_type: createForm.lead_type,
        referral_name: createForm.referral_name || null,
        payment_capability: createForm.payment_capability,
        priority: createForm.priority,
        score: createForm.score ? Number(createForm.score) : 50,
        tags: parseTags(createForm.tags),
        preferred_locations: parseList(createForm.preferred_locations),
        notes: createForm.notes || "",
      };
      if (createForm.source) payload.source = Number(createForm.source);
      if (createForm.broker) payload.broker = Number(createForm.broker);
      if (createForm.budget_min) payload.budget_min = createForm.budget_min;
      if (createForm.budget_max) payload.budget_max = createForm.budget_max;

      const result = await api.post<LeadListItem>("/crm/leads/", payload);
      toast.success("Lead created", `${result.full_name} has been added to the pipeline`);
      showSlideOver = false;
      resetCreateForm();
      fetchLeads();
      fetchOverview();
    } catch (err) {
      console.error("[crm/leads]", err);
      if (err instanceof ApiError) {
        createErrors = err.fieldErrors;
        toast.error("Validation error", "Please fix the highlighted fields");
      } else {
        toast.error("Something went wrong", "Could not create the lead");
      }
    }
    savingLead = false;
  }

  function openSlideOver() {
    resetCreateForm();
    showSlideOver = true;
  }

  function closeSlideOver() {
    showSlideOver = false;
    resetCreateForm();
  }

  // --- Initialize ---
  onMount(() => {
    void fetchOverview();
    void fetchLeads();
    void fetchSources();
    void fetchBrokers();
  });

  useAutoRefresh("Lead", fetchLeads);
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-neutral-400">CRM</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Leads</h1>
      <p class="mt-1 text-sm text-neutral-500">Lead Tracking and Sales Pipeline management</p>
    </div>
    <button
      onclick={openSlideOver}
      class="inline-flex items-center gap-2 px-4 py-2.5 bg-neutral-900 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
      </svg>
      New Lead
    </button>
  </div>

  <!-- ============================================ -->
  <!-- SECTION 1: Pipeline Overview                 -->
  <!-- ============================================ -->
  {#if overviewLoading}
    <div class="bg-white rounded-xl border border-neutral-200 p-12 flex items-center justify-center">
      <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
    </div>
  {:else if overview}
    <!-- KPI Strip -->
    <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
      <div class="bg-white rounded-xl border border-neutral-200 p-5">
        <p class="text-xs font-medium uppercase tracking-wider text-neutral-400">Total Leads</p>
        <p class="mt-2 text-2xl font-semibold text-neutral-900 tabular-nums">{overview.total_leads.toLocaleString()}</p>
      </div>
      <div class="bg-white rounded-xl border border-neutral-200 p-5">
        <p class="text-xs font-medium uppercase tracking-wider text-neutral-400">Active</p>
        <p class="mt-2 text-2xl font-semibold text-neutral-900 tabular-nums">{overview.active_leads.toLocaleString()}</p>
      </div>
      <div class="bg-white rounded-xl border border-neutral-200 p-5">
        <p class="text-xs font-medium uppercase tracking-wider text-neutral-400">Won</p>
        <p class="mt-2 text-2xl font-semibold text-neutral-900 tabular-nums">{overview.won_leads.toLocaleString()}</p>
      </div>
      <div class="bg-white rounded-xl border border-neutral-200 p-5">
        <p class="text-xs font-medium uppercase tracking-wider text-neutral-400">Lost</p>
        <p class="mt-2 text-2xl font-semibold text-neutral-900 tabular-nums">{overview.lost_leads.toLocaleString()}</p>
      </div>
      <div class="bg-white rounded-xl border border-neutral-200 p-5">
        <p class="text-xs font-medium uppercase tracking-wider text-neutral-400">Conversion Rate</p>
        <p class="mt-2 text-2xl font-semibold text-neutral-900 tabular-nums">
          {overview.conversion_rate.toFixed(1)}%
        </p>
        {#if overview.avg_days_to_close !== null}
          <p class="mt-1 text-xs text-neutral-400">
            Avg {overview.avg_days_to_close} days to close
          </p>
        {/if}
      </div>
    </div>

    <!-- Pipeline Funnel Bar -->
    {#if totalFunnelCount > 0}
      <div class="bg-white rounded-xl border border-neutral-200 p-5">
        <p class="text-xs font-medium uppercase tracking-wider text-neutral-400 mb-4">Pipeline Stages</p>
        <div class="flex rounded-lg overflow-hidden h-12">
          {#each overview.pipeline_stages as stage}
            {@const pct = (stage.count / totalFunnelCount) * 100}
            {#if stage.count > 0}
              <button
                onclick={() => handleFunnelClick(stage.stage)}
                class="relative flex items-center justify-center transition-opacity hover:opacity-80 {funnelSegmentClasses[stage.stage] ?? 'bg-neutral-400'}"
                style="width: {Math.max(pct, 4)}%;"
                title="{stage.label}: {stage.count}"
              >
                {#if pct >= 10}
                  <span class="text-[11px] font-medium truncate px-1.5 {funnelTextClasses[stage.stage] ?? 'text-white'}">
                    {stage.label}
                  </span>
                {/if}
              </button>
            {/if}
          {/each}
        </div>
        <div class="flex flex-wrap gap-x-5 gap-y-1.5 mt-3">
          {#each overview.pipeline_stages as stage}
            <button
              onclick={() => handleFunnelClick(stage.stage)}
              class="flex items-center gap-1.5 text-xs text-neutral-500 hover:text-neutral-900 transition-colors"
            >
              <span class="inline-block w-2.5 h-2.5 rounded-sm {funnelSegmentClasses[stage.stage] ?? 'bg-neutral-400'}"></span>
              {stage.label}
              <span class="font-medium text-neutral-700 tabular-nums">{stage.count}</span>
            </button>
          {/each}
        </div>
      </div>
    {/if}
  {/if}

  <!-- ============================================ -->
  <!-- SECTION 2: Leads Table                       -->
  <!-- ============================================ -->

  <!-- Filters -->
  <div class="bg-white rounded-xl border border-neutral-200 p-5">
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Search</span>
        <input
          type="text"
          placeholder="Name, email, or phone..."
          value={search}
          oninput={(e) => handleSearchInput((e.target as HTMLInputElement).value)}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        />
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Stage</span>
        <select
          value={stageFilter}
          onchange={(e) => handleStageChange((e.target as HTMLSelectElement).value)}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        >
          <option value="">All Stages</option>
          <option value="inquiry">Inquiry</option>
          <option value="qualified">Qualified</option>
          <option value="site_visit">Site Visit</option>
          <option value="offer_made">Offer Made</option>
          <option value="reservation">Reservation</option>
          <option value="spa_issued">SPA Issued</option>
          <option value="closed">Closed</option>
        </select>
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Status</span>
        <select
          value={statusFilter}
          onchange={(e) => handleStatusChange((e.target as HTMLSelectElement).value)}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        >
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="won">Won</option>
          <option value="lost">Lost</option>
          <option value="disqualified">Disqualified</option>
        </select>
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Priority</span>
        <select
          value={priorityFilter}
          onchange={(e) => handlePriorityChange((e.target as HTMLSelectElement).value)}
          class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        >
          <option value="">All Priorities</option>
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="urgent">Urgent</option>
        </select>
      </label>
    </div>
  </div>

  <!-- Table -->
  <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
    {#if loading}
      <div class="flex items-center justify-center py-20">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
      </div>
    {:else if listError}
      <div class="px-4 py-6">
        <DataStateBanner
          title="Couldn't load leads"
          message={listError}
          onretry={fetchLeads}
        />
      </div>
    {:else if leads.length === 0}
      <div class="flex flex-col items-center justify-center py-20 text-center">
        <div class="text-neutral-400 mb-2">
          <svg class="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="1.5"
              d="M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm6 3a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Zm-13.5 0a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Z"
            />
          </svg>
        </div>
        <p class="text-neutral-500 text-sm">No leads found</p>
        <button
          onclick={openSlideOver}
          class="mt-3 text-sm font-medium text-neutral-900 hover:underline"
        >
          Add your first lead
        </button>
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead class="border-b border-neutral-200 bg-neutral-50/50">
            <tr>
              <th class="w-10 px-3 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider"></th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Name</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Stage</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Priority</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Source</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Budget Range</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Payment</th>
              <th class="px-5 py-3.5 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Assigned To</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Days</th>
              <th class="px-5 py-3.5 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Score</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each leads as lead (lead.id)}
              <tr class="hover:bg-neutral-50 transition-colors">
                <td class="px-3 py-4 align-top">
                  <button
                    type="button"
                    onclick={() => toggleLeadExpanded(lead.id)}
                    class="inline-flex h-6 w-6 items-center justify-center rounded border border-neutral-200 text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700 transition-colors"
                    aria-expanded={expandedLeadId === lead.id}
                    aria-label={expandedLeadId === lead.id ? "Collapse lead details" : "Expand lead details"}
                  >
                    <span class={`transition-transform ${expandedLeadId === lead.id ? "rotate-180" : ""}`}>▾</span>
                  </button>
                </td>

                <!-- Name -->
                <td class="px-5 py-4">
                  <div class="text-sm font-medium text-neutral-900">{lead.first_name} {lead.last_name}</div>
                  {#if lead.company}
                    <div class="text-xs text-neutral-400 mt-0.5">{lead.company}</div>
                  {/if}
                </td>

                <!-- Stage -->
                <td class="px-5 py-4">
                  <StatusBadge status={lead.pipeline_stage} label={lead.pipeline_stage_display} />
                </td>

                <!-- Status -->
                <td class="px-5 py-4">
                  <StatusBadge status={lead.status} label={lead.status_display} />
                </td>

                <!-- Priority -->
                <td class="px-5 py-4">
                  <div class="flex items-center gap-2">
                    <span class="inline-block w-2 h-2 rounded-full {priorityDotClasses[lead.priority] ?? 'bg-neutral-300'}"></span>
                    <span class="text-sm text-neutral-600 capitalize">{lead.priority}</span>
                  </div>
                </td>

                <!-- Source -->
                <td class="px-5 py-4 text-sm text-neutral-600">
                  {lead.source_name ?? "\u2014"}
                </td>

                <!-- Budget Range -->
                <td class="px-5 py-4 text-sm text-neutral-600 tabular-nums">
                  {formatBudget(lead.budget_min, lead.budget_max)}
                </td>

                <!-- Payment -->
                <td class="px-5 py-4 text-sm text-neutral-600">
                  {paymentLabel(lead.payment_capability)}
                </td>

                <!-- Assigned To -->
                <td class="px-5 py-4 text-sm text-neutral-600">
                  {lead.assigned_to_name ?? "\u2014"}
                </td>

                <!-- Days in Pipeline -->
                <td class="px-5 py-4 text-sm text-neutral-500 text-right tabular-nums">
                  {lead.days_in_pipeline}
                </td>

                <!-- Score -->
                <td class="px-5 py-4 text-right">
                  <span class="inline-flex items-center justify-center min-w-8 px-2 py-0.5 rounded-full text-xs font-medium tabular-nums bg-neutral-100 text-neutral-700">
                    {lead.score}
                  </span>
                </td>
              </tr>

              {#if expandedLeadId === lead.id}
                <tr>
                  <td colspan="11" class="px-5 pb-4 pt-0">
                    <div class="rounded-lg border border-neutral-200 bg-neutral-50/70 px-4 py-3">
                      {#if !canViewLeadDetails}
                        <div class="rounded-lg border border-dashed border-neutral-300 bg-white px-4 py-6 text-center text-sm text-neutral-500">
                          You do not have permission to view full lead details.
                        </div>
                      {:else if detailLoadingByLeadId[lead.id]}
                        <div class="flex items-center justify-center py-10">
                          <div class="inline-block h-5 w-5 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
                        </div>
                      {:else if detailErrorByLeadId[lead.id]}
                        <div class="rounded-lg border border-red-200 bg-red-50 px-4 py-4 text-sm text-red-700">
                          <div class="flex flex-wrap items-center justify-between gap-3">
                            <p>{detailErrorByLeadId[lead.id]}</p>
                            <button
                              type="button"
                              onclick={() => loadLeadDetail(lead.id, true)}
                              class="rounded border border-red-200 bg-white px-3 py-1 text-xs font-medium text-red-700 hover:bg-red-100"
                            >
                              Retry
                            </button>
                          </div>
                        </div>
                      {:else if detailsByLeadId[lead.id]}
                        {@const detail = detailsByLeadId[lead.id]}
                        {@const next = nextStage(detail.pipeline_stage)}

                        <div class="mb-3 flex flex-wrap items-start justify-between gap-3">
                          <div class="min-w-0">
                            <div class="flex flex-wrap items-center gap-2">
                              <h3 class="text-sm font-semibold text-neutral-900">{detail.full_name}</h3>
                              <StatusBadge status={detail.status} label={detail.status_display} />
                              <StatusBadge status={detail.pipeline_stage} label={detail.pipeline_stage_display} />
                            </div>
                            <p class="mt-1 text-xs text-neutral-500">
                              {detail.email || "\u2014"} • {detail.phone || "\u2014"} • Updated {fmtDateTime(detail.updated_at)}
                            </p>
                          </div>
                          <div class="text-xs text-neutral-500">
                            Created {fmtDateTime(detail.created_at)}
                          </div>
                        </div>

                        <div class="mb-3 rounded-lg border border-neutral-200 bg-white p-4">
                          <p class="mb-3 text-xs font-semibold uppercase tracking-wide text-neutral-500">Pipeline Progress</p>
                          <div class="flex items-center">
                            {#each pipelineStages as stage, i}
                              {@const currentIdx = stageIndex(detail.pipeline_stage)}
                              {@const isCompleted = i <= currentIdx}
                              {@const isCurrent = i === currentIdx}
                              {@const dateKey = stageDateKeys[stage.key]}
                              {@const dateValue = detail[dateKey] as string | null}

                              {#if i > 0}
                                <div class="flex-1 h-0.5 {i <= currentIdx ? 'bg-neutral-900' : 'bg-neutral-200'} transition-colors"></div>
                              {/if}

                              <div class="flex flex-col items-center relative">
                                <div
                                  class="w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-semibold transition-colors
                                         {isCompleted ? 'bg-neutral-900 text-white' : 'bg-neutral-200 text-neutral-400'}
                                         {isCurrent ? 'ring-2 ring-neutral-900 ring-offset-2' : ''}"
                                  title={stage.label}
                                >
                                  {#if isCompleted && !isCurrent}
                                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5">
                                      <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                                    </svg>
                                  {:else}
                                    {i + 1}
                                  {/if}
                                </div>
                                <span class="mt-1 text-[10px] font-medium whitespace-nowrap {isCompleted ? 'text-neutral-900' : 'text-neutral-400'}">
                                  {stage.label}
                                </span>
                                {#if dateValue}
                                  <span class="mt-0.5 text-[9px] text-neutral-400 whitespace-nowrap">
                                    {formatDate(dateValue)}
                                  </span>
                                {/if}
                              </div>
                            {/each}
                          </div>
                        </div>

                        <div class="space-y-3">
                          <div class="rounded-lg border border-neutral-200 bg-white">
                            <button
                              type="button"
                              onclick={() => toggleSection(lead.id, "overview")}
                              class="flex w-full items-center justify-between px-4 py-3 text-left"
                            >
                              <div>
                                <p class="text-sm font-semibold text-neutral-900">Overview</p>
                                <p class="text-xs text-neutral-500">Contact profile, lead qualifiers, and budget summary.</p>
                              </div>
                              <span class={`text-neutral-500 transition-transform ${sectionIsOpen(lead.id, "overview") ? "rotate-180" : ""}`}>▾</span>
                            </button>
                            {#if sectionIsOpen(lead.id, "overview")}
                              <div class="border-t border-neutral-200 px-4 py-4">
                                <div class="grid grid-cols-1 gap-4 text-sm md:grid-cols-2 xl:grid-cols-4">
                                  <div><p class="text-xs uppercase tracking-wide text-neutral-400">Company</p><p class="mt-1 text-neutral-800">{detail.company || "\u2014"}</p></div>
                                  <div><p class="text-xs uppercase tracking-wide text-neutral-400">Lead Type</p><p class="mt-1 text-neutral-800">{leadTypeLabels[detail.lead_type]}</p></div>
                                  <div><p class="text-xs uppercase tracking-wide text-neutral-400">Priority</p><p class="mt-1 text-neutral-800">{priorityLabels[detail.priority]}</p></div>
                                  <div><p class="text-xs uppercase tracking-wide text-neutral-400">Assigned To</p><p class="mt-1 text-neutral-800">{detail.assigned_to_name || "\u2014"}</p></div>
                                  <div><p class="text-xs uppercase tracking-wide text-neutral-400">Source</p><p class="mt-1 text-neutral-800">{detail.source_name || "\u2014"}</p></div>
                                  <div><p class="text-xs uppercase tracking-wide text-neutral-400">Broker</p><p class="mt-1 text-neutral-800">{detail.broker_name || "\u2014"}</p></div>
                                  <div><p class="text-xs uppercase tracking-wide text-neutral-400">Budget</p><p class="mt-1 text-neutral-800 tabular-nums">{formatBudget(detail.budget_min, detail.budget_max)}</p></div>
                                  <div><p class="text-xs uppercase tracking-wide text-neutral-400">Payment</p><p class="mt-1 text-neutral-800">{paymentLabel(detail.payment_capability)}</p></div>
                                </div>
                                <div class="mt-4">
                                  <p class="text-xs uppercase tracking-wide text-neutral-400">Preferred Locations</p>
                                  <p class="mt-1 text-sm text-neutral-800">{detail.preferred_locations.join(", ") || "\u2014"}</p>
                                </div>
                                <div class="mt-3">
                                  <p class="text-xs uppercase tracking-wide text-neutral-400">Notes</p>
                                  <p class="mt-1 text-sm text-neutral-700 whitespace-pre-line">{detail.notes || "No notes recorded."}</p>
                                </div>
                              </div>
                            {/if}
                          </div>

                          <div class="rounded-lg border border-neutral-200 bg-white">
                            <button
                              type="button"
                              onclick={() => toggleSection(lead.id, "activities")}
                              class="flex w-full items-center justify-between px-4 py-3 text-left"
                            >
                              <div>
                                <p class="text-sm font-semibold text-neutral-900">Activities</p>
                                <p class="text-xs text-neutral-500">{detail.activities.length} activities logged for this lead.</p>
                              </div>
                              <span class={`text-neutral-500 transition-transform ${sectionIsOpen(lead.id, "activities") ? "rotate-180" : ""}`}>▾</span>
                            </button>
                            {#if sectionIsOpen(lead.id, "activities")}
                              <div class="border-t border-neutral-200 px-4 py-4">
                                {#if detail.activities.length === 0}
                                  <p class="rounded-lg border border-dashed border-neutral-200 px-4 py-6 text-center text-sm text-neutral-500">
                                    No activities yet.
                                  </p>
                                {:else}
                                  <div class="space-y-3">
                                    {#each [...detail.activities].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()) as activity}
                                      <div class="rounded-lg border border-neutral-200 px-4 py-3">
                                        <div class="flex flex-wrap items-start justify-between gap-3">
                                          <div class="min-w-0">
                                            <div class="flex flex-wrap items-center gap-2">
                                              <p class="text-sm font-medium text-neutral-900">{activity.subject}</p>
                                              <span class="rounded bg-neutral-100 px-2 py-0.5 text-[11px] font-medium text-neutral-600">
                                                {activity.activity_type_display}
                                              </span>
                                              {#if activity.is_completed}
                                                <span class="rounded bg-neutral-900 px-2 py-0.5 text-[11px] font-medium text-white">Completed</span>
                                              {/if}
                                            </div>
                                            {#if activity.description}
                                              <p class="mt-1 text-sm text-neutral-600 whitespace-pre-line">{activity.description}</p>
                                            {/if}
                                            <p class="mt-1 text-xs text-neutral-400">
                                              Scheduled: {fmtDateTime(activity.scheduled_at)} • Logged: {fmtDateTime(activity.created_at)}
                                              {#if activity.performed_by_name} • By: {activity.performed_by_name}{/if}
                                            </p>
                                          </div>
                                          {#if canEditLeads}
                                            <div class="flex items-center gap-2">
                                              <button
                                                type="button"
                                                onclick={() => toggleActivityComplete(lead.id, activity)}
                                                class="text-xs font-medium text-neutral-700 hover:text-neutral-900"
                                              >
                                                {activity.is_completed ? "Mark Incomplete" : "Mark Complete"}
                                              </button>
                                              <button
                                                type="button"
                                                onclick={() => deleteActivity(lead.id, activity.id)}
                                                class="text-xs font-medium text-red-600 hover:text-red-700"
                                              >
                                                Delete
                                              </button>
                                            </div>
                                          {/if}
                                        </div>
                                      </div>
                                    {/each}
                                  </div>
                                {/if}
                              </div>
                            {/if}
                          </div>

                          <div class="rounded-lg border border-neutral-200 bg-white">
                            <button
                              type="button"
                              onclick={() => toggleSection(lead.id, "preferences")}
                              class="flex w-full items-center justify-between px-4 py-3 text-left"
                            >
                              <div>
                                <p class="text-sm font-semibold text-neutral-900">Preferences</p>
                                <p class="text-xs text-neutral-500">
                                  {detail.project_interests.length} interests • {detail.unit_preferences.length} unit preferences
                                </p>
                              </div>
                              <span class={`text-neutral-500 transition-transform ${sectionIsOpen(lead.id, "preferences") ? "rotate-180" : ""}`}>▾</span>
                            </button>
                            {#if sectionIsOpen(lead.id, "preferences")}
                              <div class="grid grid-cols-1 gap-4 border-t border-neutral-200 px-4 py-4 lg:grid-cols-2">
                                <div>
                                  <p class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Project Interests</p>
                                  {#if detail.project_interests.length === 0}
                                    <p class="mt-2 text-sm text-neutral-500">No project interests recorded.</p>
                                  {:else}
                                    <div class="mt-2 space-y-2">
                                      {#each detail.project_interests as interest}
                                        <div class="rounded border border-neutral-200 px-3 py-2">
                                          <div class="flex items-center gap-2">
                                            <p class="text-sm font-medium text-neutral-800">{interest.project_name}</p>
                                            <span class="rounded px-2 py-0.5 text-[11px] font-medium {interestLevelClass(interest)}">
                                              {interest.interest_level}
                                            </span>
                                          </div>
                                          {#if interest.notes}
                                            <p class="mt-1 text-xs text-neutral-500">{interest.notes}</p>
                                          {/if}
                                        </div>
                                      {/each}
                                    </div>
                                  {/if}
                                </div>
                                <div>
                                  <p class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Unit Preferences</p>
                                  {#if detail.unit_preferences.length === 0}
                                    <p class="mt-2 text-sm text-neutral-500">No unit preferences recorded.</p>
                                  {:else}
                                    <div class="mt-2 space-y-2">
                                      {#each detail.unit_preferences as preference}
                                        <div class="rounded border border-neutral-200 px-3 py-2">
                                          <p class="text-sm font-medium text-neutral-800">{preference.unit_type_display || preference.unit_type}</p>
                                          <p class="mt-1 text-xs text-neutral-500">{preferenceSummary(preference)}</p>
                                          {#if preference.notes}
                                            <p class="mt-1 text-xs text-neutral-500">{preference.notes}</p>
                                          {/if}
                                        </div>
                                      {/each}
                                    </div>
                                  {/if}
                                </div>
                              </div>
                            {/if}
                          </div>

                          <div class="rounded-lg border border-neutral-200 bg-white">
                            <button
                              type="button"
                              onclick={() => toggleSection(lead.id, "timeline")}
                              class="flex w-full items-center justify-between px-4 py-3 text-left"
                            >
                              <div>
                                <p class="text-sm font-semibold text-neutral-900">Timeline</p>
                                <p class="text-xs text-neutral-500">{detail.stage_transitions.length} stage transitions recorded.</p>
                              </div>
                              <span class={`text-neutral-500 transition-transform ${sectionIsOpen(lead.id, "timeline") ? "rotate-180" : ""}`}>▾</span>
                            </button>
                            {#if sectionIsOpen(lead.id, "timeline")}
                              <div class="border-t border-neutral-200 px-4 py-4">
                                {#if detail.stage_transitions.length === 0}
                                  <p class="text-sm text-neutral-500">No stage transitions recorded yet.</p>
                                {:else}
                                  <div class="space-y-3">
                                    {#each [...detail.stage_transitions].sort((a, b) => new Date(b.transitioned_at).getTime() - new Date(a.transitioned_at).getTime()) as transition}
                                      <div class="rounded-lg border border-neutral-200 px-4 py-3">
                                        <div class="flex flex-wrap items-center gap-2">
                                          <StatusBadge status={transition.from_stage} label={stageLabel(transition.from_stage)} />
                                          <span class="text-xs text-neutral-400">→</span>
                                          <StatusBadge status={transition.to_stage} label={stageLabel(transition.to_stage)} />
                                        </div>
                                        <p class="mt-1 text-xs text-neutral-500">
                                          {fmtDateTime(transition.transitioned_at)}
                                          {#if transition.transitioned_by_name} • By {transition.transitioned_by_name}{/if}
                                        </p>
                                        {#if transition.notes}
                                          <p class="mt-1 text-xs text-neutral-600 whitespace-pre-line">{transition.notes}</p>
                                        {/if}
                                      </div>
                                    {/each}
                                  </div>
                                {/if}
                              </div>
                            {/if}
                          </div>

                          <div class="rounded-lg border border-neutral-200 bg-white">
                            <button
                              type="button"
                              onclick={() => toggleSection(lead.id, "actions")}
                              class="flex w-full items-center justify-between px-4 py-3 text-left"
                            >
                              <div>
                                <p class="text-sm font-semibold text-neutral-900">Pipeline Actions</p>
                                <p class="text-xs text-neutral-500">Stage transitions, conversion, loss handling, and complex edits.</p>
                              </div>
                              <span class={`text-neutral-500 transition-transform ${sectionIsOpen(lead.id, "actions") ? "rotate-180" : ""}`}>▾</span>
                            </button>
                            {#if sectionIsOpen(lead.id, "actions")}
                              <div class="space-y-4 border-t border-neutral-200 px-4 py-4">
                                {#if !canEditLeads}
                                  <p class="rounded-lg border border-dashed border-neutral-300 px-4 py-6 text-center text-sm text-neutral-500">
                                    You have read-only access for this lead.
                                  </p>
                                {:else}
                                  <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
                                    <div class="rounded-lg border border-neutral-200 p-3">
                                      <p class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Advance Stage</p>
                                      {#if detail.status !== "active"}
                                        <p class="mt-2 text-sm text-neutral-500">Lead is not active.</p>
                                      {:else if !next}
                                        <p class="mt-2 text-sm text-neutral-500">Lead is already at final stage.</p>
                                      {:else}
                                        <p class="mt-2 text-sm text-neutral-700">Current: {stageLabel(detail.pipeline_stage)}</p>
                                        <p class="text-sm text-neutral-700">Next: {stageLabel(next)}</p>
                                        <textarea
                                          rows={2}
                                          placeholder="Notes (optional)"
                                          value={stageChangeNotesByLeadId[lead.id] ?? ""}
                                          oninput={(event) => {
                                            stageChangeNotesByLeadId = {
                                              ...stageChangeNotesByLeadId,
                                              [lead.id]: (event.target as HTMLTextAreaElement).value,
                                            };
                                          }}
                                          class="mt-2 w-full rounded border border-neutral-200 px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-neutral-900"
                                        ></textarea>
                                        <button
                                          type="button"
                                          onclick={() => advanceStageForLead(lead.id)}
                                          disabled={stageChangingByLeadId[lead.id]}
                                          class="mt-2 rounded bg-neutral-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
                                        >
                                          {stageChangingByLeadId[lead.id] ? "Updating..." : `Move to ${stageLabel(next)}`}
                                        </button>
                                      {/if}
                                    </div>

                                    <div class="rounded-lg border border-neutral-200 p-3">
                                      <p class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Convert to Customer</p>
                                      {#if detail.status !== "active" || (detail.pipeline_stage !== "closed" && detail.pipeline_stage !== "spa_issued")}
                                        <p class="mt-2 text-sm text-neutral-500">Available for active leads at SPA Issued or Closed stage.</p>
                                      {:else}
                                        <textarea
                                          rows={2}
                                          placeholder="Conversion notes (optional)"
                                          value={convertNotesByLeadId[lead.id] ?? ""}
                                          oninput={(event) => {
                                            convertNotesByLeadId = {
                                              ...convertNotesByLeadId,
                                              [lead.id]: (event.target as HTMLTextAreaElement).value,
                                            };
                                          }}
                                          class="mt-2 w-full rounded border border-neutral-200 px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-neutral-900"
                                        ></textarea>
                                        <button
                                          type="button"
                                          onclick={() => convertLeadForRow(lead.id)}
                                          disabled={convertingByLeadId[lead.id]}
                                          class="mt-2 rounded bg-neutral-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
                                        >
                                          {convertingByLeadId[lead.id] ? "Converting..." : "Convert Lead"}
                                        </button>
                                      {/if}
                                    </div>

                                    <div class="rounded-lg border border-neutral-200 p-3">
                                      <p class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Mark Lost</p>
                                      {#if detail.status !== "active"}
                                        <p class="mt-2 text-sm text-neutral-500">Lead is already {detail.status_display}.</p>
                                      {:else}
                                        <textarea
                                          rows={2}
                                          placeholder="Required reason for loss"
                                          value={lostReasonByLeadId[lead.id] ?? ""}
                                          oninput={(event) => {
                                            lostReasonByLeadId = {
                                              ...lostReasonByLeadId,
                                              [lead.id]: (event.target as HTMLTextAreaElement).value,
                                            };
                                          }}
                                          class="mt-2 w-full rounded border border-neutral-200 px-2 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-neutral-900"
                                        ></textarea>
                                        <button
                                          type="button"
                                          onclick={() => markLeadLostForRow(lead.id)}
                                          disabled={markingLostByLeadId[lead.id]}
                                          class="mt-2 rounded border border-red-300 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
                                        >
                                          {markingLostByLeadId[lead.id] ? "Updating..." : "Mark Lost"}
                                        </button>
                                      {/if}
                                    </div>
                                  </div>

                                  <div class="rounded-lg border border-neutral-200 p-4">
                                    <div class="flex flex-wrap items-center justify-between gap-2">
                                      <p class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Complex Edit</p>
                                      {#if editModeByLeadId[lead.id]}
                                        <div class="flex items-center gap-2">
                                          <button
                                            type="button"
                                            onclick={() => cancelInlineEdit(lead.id)}
                                            class="rounded border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50"
                                          >
                                            Cancel
                                          </button>
                                          <button
                                            type="button"
                                            onclick={() => saveInlineEdit(lead.id)}
                                            disabled={savingEditByLeadId[lead.id]}
                                            class="rounded bg-neutral-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
                                          >
                                            {savingEditByLeadId[lead.id] ? "Saving..." : "Save"}
                                          </button>
                                        </div>
                                      {:else}
                                        <button
                                          type="button"
                                          onclick={() => openInlineEdit(lead.id)}
                                          class="rounded border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50"
                                        >
                                          Edit Lead
                                        </button>
                                      {/if}
                                    </div>

                                    {#if editModeByLeadId[lead.id] && editFormsByLeadId[lead.id]}
                                      {@const editForm = editFormsByLeadId[lead.id]}
                                      <div class="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
                                        <label class="text-xs text-neutral-600">
                                          First Name
                                          <input
                                            type="text"
                                            value={editForm.first_name}
                                            oninput={(event) => updateInlineEditField(lead.id, "first_name", (event.target as HTMLInputElement).value)}
                                            class="mt-1 w-full rounded border border-neutral-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
                                          />
                                        </label>
                                        <label class="text-xs text-neutral-600">
                                          Last Name
                                          <input
                                            type="text"
                                            value={editForm.last_name}
                                            oninput={(event) => updateInlineEditField(lead.id, "last_name", (event.target as HTMLInputElement).value)}
                                            class="mt-1 w-full rounded border border-neutral-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
                                          />
                                        </label>
                                        <label class="text-xs text-neutral-600">
                                          Email
                                          <input
                                            type="email"
                                            value={editForm.email}
                                            oninput={(event) => updateInlineEditField(lead.id, "email", (event.target as HTMLInputElement).value)}
                                            class="mt-1 w-full rounded border border-neutral-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
                                          />
                                        </label>
                                        <label class="text-xs text-neutral-600">
                                          Phone
                                          <input
                                            type="text"
                                            value={editForm.phone}
                                            oninput={(event) => updateInlineEditField(lead.id, "phone", (event.target as HTMLInputElement).value)}
                                            class="mt-1 w-full rounded border border-neutral-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
                                          />
                                        </label>
                                        <label class="text-xs text-neutral-600">
                                          Secondary Phone
                                          <input
                                            type="text"
                                            value={editForm.secondary_phone}
                                            oninput={(event) => updateInlineEditField(lead.id, "secondary_phone", (event.target as HTMLInputElement).value)}
                                            class="mt-1 w-full rounded border border-neutral-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
                                          />
                                        </label>
                                        <label class="text-xs text-neutral-600">
                                          Company
                                          <input
                                            type="text"
                                            value={editForm.company}
                                            oninput={(event) => updateInlineEditField(lead.id, "company", (event.target as HTMLInputElement).value)}
                                            class="mt-1 w-full rounded border border-neutral-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
                                          />
                                        </label>
                                        <label class="text-xs text-neutral-600">
                                          Nationality
                                          <input
                                            type="text"
                                            value={editForm.nationality}
                                            oninput={(event) => updateInlineEditField(lead.id, "nationality", (event.target as HTMLInputElement).value)}
                                            class="mt-1 w-full rounded border border-neutral-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
                                          />
                                        </label>
                                        <label class="text-xs text-neutral-600">
                                          Lead Type
                                          <select
                                            value={editForm.lead_type}
                                            onchange={(event) => updateInlineEditField(lead.id, "lead_type", (event.target as HTMLSelectElement).value as LeadInlineEditForm["lead_type"])}
                                            class="mt-1 w-full rounded border border-neutral-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
                                          >
                                            <option value="buyer">Buyer</option>
                                            <option value="tenant">Tenant</option>
                                            <option value="investor">Investor</option>
                                          </select>
                                        </label>
                                        <label class="text-xs text-neutral-600">
                                          Priority
                                          <select
                                            value={editForm.priority}
                                            onchange={(event) => updateInlineEditField(lead.id, "priority", (event.target as HTMLSelectElement).value as LeadInlineEditForm["priority"])}
                                            class="mt-1 w-full rounded border border-neutral-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
                                          >
                                            <option value="low">Low</option>
                                            <option value="medium">Medium</option>
                                            <option value="high">High</option>
                                            <option value="urgent">Urgent</option>
                                          </select>
                                        </label>
                                        <label class="text-xs text-neutral-600">
                                          Score
                                          <input
                                            type="number"
                                            min="0"
                                            max="100"
                                            value={editForm.score}
                                            oninput={(event) => updateInlineEditField(lead.id, "score", Number((event.target as HTMLInputElement).value || 0))}
                                            class="mt-1 w-full rounded border border-neutral-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
                                          />
                                        </label>
                                        <label class="text-xs text-neutral-600">
                                          Budget Min
                                          <input
                                            type="text"
                                            value={editForm.budget_min}
                                            oninput={(event) => updateInlineEditField(lead.id, "budget_min", (event.target as HTMLInputElement).value)}
                                            class="mt-1 w-full rounded border border-neutral-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
                                          />
                                        </label>
                                        <label class="text-xs text-neutral-600">
                                          Budget Max
                                          <input
                                            type="text"
                                            value={editForm.budget_max}
                                            oninput={(event) => updateInlineEditField(lead.id, "budget_max", (event.target as HTMLInputElement).value)}
                                            class="mt-1 w-full rounded border border-neutral-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
                                          />
                                        </label>
                                        <label class="text-xs text-neutral-600">
                                          Payment
                                          <select
                                            value={editForm.payment_capability}
                                            onchange={(event) => updateInlineEditField(lead.id, "payment_capability", (event.target as HTMLSelectElement).value as LeadInlineEditForm["payment_capability"])}
                                            class="mt-1 w-full rounded border border-neutral-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
                                          >
                                            <option value="cash">Cash</option>
                                            <option value="mortgage">Mortgage</option>
                                            <option value="installment">Installment</option>
                                            <option value="mixed">Mixed</option>
                                            <option value="undetermined">Undetermined</option>
                                          </select>
                                        </label>
                                        <label class="text-xs text-neutral-600 md:col-span-2 xl:col-span-2">
                                          Tags (comma separated)
                                          <input
                                            type="text"
                                            value={editForm.tags}
                                            oninput={(event) => updateInlineEditField(lead.id, "tags", (event.target as HTMLInputElement).value)}
                                            class="mt-1 w-full rounded border border-neutral-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
                                          />
                                        </label>
                                        <label class="text-xs text-neutral-600 md:col-span-2 xl:col-span-2">
                                          Preferred Locations (comma separated)
                                          <input
                                            type="text"
                                            value={editForm.preferred_locations}
                                            oninput={(event) => updateInlineEditField(lead.id, "preferred_locations", (event.target as HTMLInputElement).value)}
                                            class="mt-1 w-full rounded border border-neutral-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
                                          />
                                        </label>
                                        <label class="text-xs text-neutral-600 md:col-span-2 xl:col-span-4">
                                          Notes
                                          <textarea
                                            rows={3}
                                            value={editForm.notes}
                                            oninput={(event) => updateInlineEditField(lead.id, "notes", (event.target as HTMLTextAreaElement).value)}
                                            class="mt-1 w-full rounded border border-neutral-200 px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
                                          ></textarea>
                                        </label>
                                      </div>
                                    {/if}
                                  </div>
                                {/if}
                              </div>
                            {/if}
                          </div>
                        </div>
                      {/if}
                    </div>
                  </td>
                </tr>
              {/if}
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
                  ? 'bg-neutral-900 text-white border-neutral-900'
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

<!-- ============================================ -->
<!-- SLIDE-OVER: New Lead                         -->
<!-- ============================================ -->
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
      <h2 class="text-lg font-semibold text-neutral-900">New Lead</h2>
      <button
        onclick={closeSlideOver}
        class="p-1.5 rounded-lg text-neutral-400 hover:text-neutral-900 hover:bg-neutral-100 transition-colors"
        aria-label="Close"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- Body -->
    <div class="flex-1 overflow-y-auto px-6 py-5">
      <form id="create-lead-form" onsubmit={handleCreateLead} class="space-y-5">
        <!-- Name (2-col) -->
        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">First Name</span>
            <input
              type="text"
              bind:value={createForm.first_name}
              required
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if createFieldError("first_name")}<p class="mt-1 text-xs text-red-500">{createFieldError("first_name")}</p>{/if}
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Last Name</span>
            <input
              type="text"
              bind:value={createForm.last_name}
              required
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if createFieldError("last_name")}<p class="mt-1 text-xs text-red-500">{createFieldError("last_name")}</p>{/if}
          </label>
        </div>

        <!-- Email & Phone (2-col) -->
        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Email</span>
            <input
              type="email"
              bind:value={createForm.email}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if createFieldError("email")}<p class="mt-1 text-xs text-red-500">{createFieldError("email")}</p>{/if}
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Phone</span>
            <input
              type="tel"
              bind:value={createForm.phone}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if createFieldError("phone")}<p class="mt-1 text-xs text-red-500">{createFieldError("phone")}</p>{/if}
          </label>
        </div>

        <!-- Secondary Phone & Company (2-col) -->
        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Secondary Phone</span>
            <input
              type="tel"
              bind:value={createForm.secondary_phone}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if createFieldError("secondary_phone")}<p class="mt-1 text-xs text-red-500">{createFieldError("secondary_phone")}</p>{/if}
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Company</span>
            <input
              type="text"
              bind:value={createForm.company}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if createFieldError("company")}<p class="mt-1 text-xs text-red-500">{createFieldError("company")}</p>{/if}
          </label>
        </div>

        <!-- Nationality & Lead Type -->
        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Nationality</span>
            <input
              type="text"
              bind:value={createForm.nationality}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
            {#if createFieldError("nationality")}<p class="mt-1 text-xs text-red-500">{createFieldError("nationality")}</p>{/if}
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Lead Type</span>
            <select
              bind:value={createForm.lead_type}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            >
              <option value="buyer">Buyer</option>
              <option value="tenant">Tenant</option>
              <option value="investor">Investor</option>
            </select>
            {#if createFieldError("lead_type")}<p class="mt-1 text-xs text-red-500">{createFieldError("lead_type")}</p>{/if}
          </label>
        </div>

        <!-- Source & Broker -->
        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Source</span>
            <select
              bind:value={createForm.source}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            >
              <option value="">Select source</option>
              {#each sources.filter(s => s.is_active) as source}
                <option value={String(source.id)}>{source.name}</option>
              {/each}
            </select>
            {#if createFieldError("source")}<p class="mt-1 text-xs text-red-500">{createFieldError("source")}</p>{/if}
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Broker</span>
            <select
              bind:value={createForm.broker}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            >
              <option value="">Select broker</option>
              {#each brokers as broker}
                <option value={String(broker.id)}>{broker.name}</option>
              {/each}
            </select>
            {#if createFieldError("broker")}<p class="mt-1 text-xs text-red-500">{createFieldError("broker")}</p>{/if}
          </label>
        </div>

        <!-- Referral Name -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Referral Name</span>
          <input
            type="text"
            bind:value={createForm.referral_name}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          />
          {#if createFieldError("referral_name")}<p class="mt-1 text-xs text-red-500">{createFieldError("referral_name")}</p>{/if}
        </label>

        <!-- Budget (2-col) -->
        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Budget Min</span>
            <input
              type="number"
              step="0.01"
              min="0"
              bind:value={createForm.budget_min}
              placeholder="0.00"
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent tabular-nums"
            />
            {#if createFieldError("budget_min")}<p class="mt-1 text-xs text-red-500">{createFieldError("budget_min")}</p>{/if}
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Budget Max</span>
            <input
              type="number"
              step="0.01"
              min="0"
              bind:value={createForm.budget_max}
              placeholder="0.00"
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent tabular-nums"
            />
            {#if createFieldError("budget_max")}<p class="mt-1 text-xs text-red-500">{createFieldError("budget_max")}</p>{/if}
          </label>
        </div>

        <!-- Payment Capability -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Payment Capability</span>
          <select
            bind:value={createForm.payment_capability}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            <option value="undetermined">Undetermined</option>
            <option value="cash">Cash</option>
            <option value="mortgage">Mortgage</option>
            <option value="installment">Installment</option>
            <option value="mixed">Mixed</option>
          </select>
          {#if createFieldError("payment_capability")}<p class="mt-1 text-xs text-red-500">{createFieldError("payment_capability")}</p>{/if}
        </label>

        <!-- Preferred Locations -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Preferred Locations</span>
          <input
            type="text"
            bind:value={createForm.preferred_locations}
            placeholder="Lekki, Victoria Island, Ikoyi"
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          />
          <p class="mt-1 text-xs text-neutral-400">Comma-separated preferred areas for matching.</p>
          {#if createFieldError("preferred_locations")}<p class="mt-1 text-xs text-red-500">{createFieldError("preferred_locations")}</p>{/if}
        </label>

        <!-- Priority & Score (2-col) -->
        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Priority</span>
            <select
              bind:value={createForm.priority}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="urgent">Urgent</option>
            </select>
            {#if createFieldError("priority")}<p class="mt-1 text-xs text-red-500">{createFieldError("priority")}</p>{/if}
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Score <span class="text-neutral-400 font-normal">(0-100)</span></span>
            <input
              type="number"
              min="0"
              max="100"
              bind:value={createForm.score}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent tabular-nums"
            />
            {#if createFieldError("score")}<p class="mt-1 text-xs text-red-500">{createFieldError("score")}</p>{/if}
          </label>
        </div>

        <!-- Tags -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Tags</span>
          <input
            type="text"
            bind:value={createForm.tags}
            placeholder="high net worth, mortgage needed"
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          />
          <p class="mt-1 text-xs text-neutral-400">Comma-separated labels for segmentation.</p>
          {#if createFieldError("tags")}<p class="mt-1 text-xs text-red-500">{createFieldError("tags")}</p>{/if}
        </label>

        <!-- Notes -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Notes</span>
          <textarea
            bind:value={createForm.notes}
            rows="3"
            placeholder="Any additional details..."
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent resize-none"
          ></textarea>
          {#if createFieldError("notes")}<p class="mt-1 text-xs text-red-500">{createFieldError("notes")}</p>{/if}
        </label>
      </form>
    </div>

    <!-- Footer -->
    <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-neutral-100 shrink-0">
      {#if isDev}
        <button type="button" onclick={devFillLead} class="mr-auto rounded-lg bg-orange-500 px-4 py-2 text-sm font-semibold text-white hover:bg-orange-600 transition-colors">Dev Fill</button>
      {/if}
      <button
        type="button"
        onclick={closeSlideOver}
        class="px-4 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors"
      >
        Cancel
      </button>
      <button
        type="submit"
        form="create-lead-form"
        disabled={savingLead}
        class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
      >
        {savingLead ? "Creating..." : "Create Lead"}
      </button>
    </div>
  </div>
{/if}

<svelte:window onkeydown={(e) => { if (e.key === "Escape" && showSlideOver) closeSlideOver(); }} />

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

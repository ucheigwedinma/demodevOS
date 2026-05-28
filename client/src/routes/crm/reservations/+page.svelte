<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DataStateBanner from "$lib/components/DataStateBanner.svelte";
  import type {
    LeadDetail,
    PipelineStage,
    ReservationListItem,
    ReservationDetail,
    ReservationOverview,
    ReservationStatus,
    PaginatedResponse,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  // --- Overview ---
  let overview = $state<ReservationOverview | null>(null);
  let overviewLoading = $state(true);

  // --- Reservations Table ---
  let reservations = $state<ReservationListItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let listError = $state<string | null>(null);
  let currentPage = $state(1);
  const pageSize = 25;

  // --- Filters ---
  let search = $state("");
  let statusFilter = $state("");
  let projectFilter = $state("");

  // --- Reference Data ---
  let projects = $state<{ id: number; name: string }[]>([]);
  let leads = $state<{ id: number; first_name: string; last_name: string; status: string }[]>([]);
  let units = $state<{ id: number; unit_number: string; property_name: string; asking_price: string }[]>([]);

  // --- Slide-over ---
  let showSlideOver = $state(false);
  let saving = $state(false);
  let createErrors = $state<Record<string, string[]>>({});
  let createForm = $state({
    lead: "",
    unit: "",
    project: "",
    total_price: "",
    deposit_amount: "",
    reservation_fee: "0",
    hold_hours: "48",
    payment_deadline: "",
    notes: "",
  });

  // --- Detail Drawer ---
  let showDetailDrawer = $state(false);
  let detailLoading = $state(false);
  let detailError = $state("");
  let selectedReservationId = $state<number | null>(null);
  let selectedReservation = $state<ReservationDetail | null>(null);

  type DetailAccordionSection =
    | "progress"
    | "unit"
    | "lead"
    | "payment"
    | "timeline"
    | "actions"
    | "financial"
    | "notes"
    | "details";
  let activeDetailSection = $state<DetailAccordionSection | null>("progress");

  let confirming = $state(false);
  let recordingPayment = $state(false);
  let converting = $state(false);
  let cancelling = $state(false);
  let extending = $state(false);
  let deleting = $state(false);

  let confirmNotes = $state("");
  let cancelReason = $state("");
  let paymentForm = $state({
    amount: "",
    payment_method: "bank_transfer" as "bank_transfer" | "check" | "cash" | "credit_card" | "other",
    reference_number: "",
    notes: "",
  });
  let extendForm = $state({
    extend_hours: 24,
    notes: "",
  });

  // --- Lead Detail Modal ---
  type LeadModalTab = "overview" | "activities" | "preferences" | "timeline";
  let showLeadModal = $state(false);
  let leadDetailLoading = $state(false);
  let leadDetailError = $state("");
  let leadDetail = $state<LeadDetail | null>(null);
  let activeLeadTab = $state<LeadModalTab>("overview");

  const leadTabs: { key: LeadModalTab; label: string }[] = [
    { key: "overview", label: "Overview" },
    { key: "activities", label: "Activities" },
    { key: "preferences", label: "Preferences" },
    { key: "timeline", label: "Timeline" },
  ];

  const leadPipelineStages: { key: PipelineStage; label: string }[] = [
    { key: "inquiry", label: "Inquiry" },
    { key: "qualified", label: "Qualified" },
    { key: "site_visit", label: "Site Visit" },
    { key: "offer_made", label: "Offer Made" },
    { key: "reservation", label: "Reservation" },
    { key: "spa_issued", label: "SPA Issued" },
    { key: "closed", label: "Closed" },
  ];

  const leadPriorityLabels: Record<string, string> = {
    low: "Low",
    medium: "Medium",
    high: "High",
    urgent: "Urgent",
  };

  const leadTypeLabels: Record<string, string> = {
    buyer: "Buyer",
    tenant: "Tenant",
    investor: "Investor",
  };

  const leadPaymentCapabilityLabels: Record<string, string> = {
    cash: "Cash",
    mortgage: "Mortgage",
    installment: "Installment",
    mixed: "Mixed",
    undetermined: "Undetermined",
  };

  const leadStageDateKeys: Record<PipelineStage, keyof LeadDetail> = {
    inquiry: "inquiry_date",
    qualified: "qualified_date",
    site_visit: "site_visit_date",
    offer_made: "offer_date",
    reservation: "reservation_date",
    spa_issued: "spa_issued_date",
    closed: "closed_date",
  };

  // Dev fill
  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  const RESERVATION_SAMPLES = [
    { total_price: "85000000", deposit_amount: "8500000", reservation_fee: "500000", hold_hours: "72", notes: "Client confirmed via phone. Bank pre-approval pending." },
    { total_price: "120000000", deposit_amount: "12000000", reservation_fee: "750000", hold_hours: "48", notes: "Investor client. Cash buyer, awaiting proof of funds." },
    { total_price: "45000000", deposit_amount: "4500000", reservation_fee: "300000", hold_hours: "96", notes: "First-time buyer. Mortgage application in progress with GTBank." },
    { total_price: "250000000", deposit_amount: "25000000", reservation_fee: "1500000", hold_hours: "72", notes: "Diaspora client. Dollar-denominated payment plan agreed verbally." },
  ];

  let devIdx = $state(0);

  function devFillReservation() {
    const sample = RESERVATION_SAMPLES[devIdx % RESERVATION_SAMPLES.length];
    devIdx++;
    createForm.total_price = sample.total_price;
    createForm.deposit_amount = sample.deposit_amount;
    createForm.reservation_fee = sample.reservation_fee;
    createForm.hold_hours = sample.hold_hours;
    createForm.payment_deadline = new Date(Date.now() + 14 * 86400000).toISOString().slice(0, 10);
    createForm.notes = sample.notes;
    if (leads.length > 0) createForm.lead = String(leads[devIdx % leads.length].id);
    if (units.length > 0) createForm.unit = String(units[devIdx % units.length].id);
    if (projects.length > 0) createForm.project = String(projects[devIdx % projects.length].id);
  }

  function createFieldError(field: string): string {
    return createErrors[field]?.[0] ?? "";
  }

  function resetCreateForm() {
    createForm = {
      lead: "",
      unit: "",
      project: "",
      total_price: "",
      deposit_amount: "",
      reservation_fee: "0",
      hold_hours: "48",
      payment_deadline: "",
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

  // --- Detail Drawer Derived ---
  const detailTotalPrice = $derived(selectedReservation ? parseFloat(selectedReservation.total_price || "0") : 0);
  const detailDepositAmount = $derived(selectedReservation ? parseFloat(selectedReservation.deposit_amount || "0") : 0);
  const detailReservationFee = $derived(selectedReservation ? parseFloat(selectedReservation.reservation_fee || "0") : 0);
  const detailNetAmount = $derived(detailTotalPrice - detailDepositAmount - detailReservationFee);

  const detailIsTerminal = $derived(
    selectedReservation
      ? ["converted", "expired", "cancelled"].includes(selectedReservation.status)
      : false,
  );

  const LIFECYCLE_STEPS = [
    { key: "hold", label: "Hold" },
    { key: "payment_pending", label: "Payment Pending" },
    { key: "paid", label: "Paid" },
    { key: "converted", label: "Converted" },
  ] as const;

  const statusOrder: Record<string, number> = {
    hold: 0,
    reserved: 0,
    payment_pending: 1,
    paid: 2,
    converting: 2,
    converted: 3,
    expired: -1,
    cancelled: -1,
  };

  const currentStepIndex = $derived(
    selectedReservation ? (statusOrder[selectedReservation.status] ?? -1) : -1,
  );

  const isCancelledOrExpired = $derived(
    selectedReservation
      ? selectedReservation.status === "cancelled" || selectedReservation.status === "expired"
      : false,
  );

  const terminalAtStep = $derived(() => {
    if (!selectedReservation || !isCancelledOrExpired) return -1;
    const events = selectedReservation.events || [];
    const lastNonTerminalEvent = [...events]
      .reverse()
      .find(
        (e) =>
          !e.event_type.includes("cancel") &&
          !e.event_type.includes("expir"),
      );
    if (lastNonTerminalEvent) {
      if (lastNonTerminalEvent.event_type.includes("paid") || lastNonTerminalEvent.event_type.includes("payment")) return 2;
      if (lastNonTerminalEvent.event_type.includes("confirm") || lastNonTerminalEvent.event_type.includes("payment_pending")) return 1;
    }
    return 0;
  });

  const computedNewExpiry = $derived(() => {
    if (!selectedReservation?.hold_expires_at) return null;
    const d = new Date(selectedReservation.hold_expires_at);
    d.setHours(d.getHours() + extendForm.extend_hours);
    return d;
  });

  const sortedDetailEvents = $derived(
    selectedReservation
      ? [...(selectedReservation.events || [])].sort(
          (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
        )
      : [],
  );

  const sortedLeadActivities = $derived(
    leadDetail
      ? [...leadDetail.activities].sort(
          (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
        )
      : [],
  );

  const sortedLeadTransitions = $derived(
    leadDetail
      ? [...leadDetail.stage_transitions].sort(
          (a, b) => new Date(b.transitioned_at).getTime() - new Date(a.transitioned_at).getTime(),
        )
      : [],
  );

  const leadCurrentStageIndex = $derived.by(() => {
    const detail = leadDetail;
    if (!detail) return -1;
    return leadPipelineStages.findIndex((stage) => stage.key === detail.pipeline_stage);
  });

  // --- Helpers ---
  function formatDateTime(dateStr: string | null): string {
    if (!dateStr) return "\u2014";
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function formatDateShort(dateStr: string | null): string {
    if (!dateStr) return "\u2014";
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function isHoldExpired(holdExpiresAt: string, status: ReservationStatus): boolean {
    if (status !== "hold" || !holdExpiresAt) return false;
    return new Date(holdExpiresAt) < new Date();
  }

  function formatRelativeTime(dateStr: string): string {
    const d = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    return `${days}d ago`;
  }

  function formatLeadDate(value: string | null | undefined): string {
    if (!value) return "\u2014";
    return new Date(value + "T00:00:00").toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function formatLeadDateTime(value: string | null | undefined): string {
    if (!value) return "\u2014";
    return new Date(value).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function formatLeadAmount(value: string | null | undefined): string {
    if (!value) return "\u2014";
    return currency.format(parseFloat(value));
  }

  function leadStageLabel(stage: PipelineStage): string {
    return leadPipelineStages.find((entry) => entry.key === stage)?.label ?? stage;
  }

  function toggleDetailSection(section: DetailAccordionSection) {
    activeDetailSection = activeDetailSection === section ? null : section;
  }

  function resetDetailActionForms() {
    confirmNotes = "";
    cancelReason = "";
    paymentForm = {
      amount: "",
      payment_method: "bank_transfer",
      reference_number: "",
      notes: "",
    };
    extendForm = { extend_hours: 24, notes: "" };
  }

  // --- Data Fetching ---
  async function fetchOverview() {
    overviewLoading = true;
    try {
      overview = await api.get<ReservationOverview>("/crm/reservations/overview/");
    } catch (err) {
      console.error("[crm/reservations]", err);
      overview = null;
    } finally {
      overviewLoading = false;
    }
  }

  async function fetchReservations() {
    loading = true;
    listError = null;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        page_size: String(pageSize),
      };
      if (search) params.search = search;
      if (statusFilter) params.status = statusFilter;
      if (projectFilter) params.project = projectFilter;

      const res = await api.get<PaginatedResponse<ReservationListItem>>(
        "/crm/reservations/",
        params,
      );
      reservations = res.results;
      totalCount = res.count;
    } catch (err) {
      console.error("[crm/reservations]", err);
      reservations = [];
      totalCount = 0;
      listError = err instanceof Error ? err.message : "Could not load reservations.";
    } finally {
      loading = false;
    }
  }

  async function fetchProjects() {
    try {
      const res = await api.get<PaginatedResponse<{ id: number; name: string }>>(
        "/projects/projects/",
        { page_size: "100" },
      );
      projects = res.results;
    } catch (err) {
      console.error("[crm/reservations]", err);
      projects = [];
    }
  }

  async function fetchLeads() {
    try {
      const res = await api.get<PaginatedResponse<{ id: number; first_name: string; last_name: string; status: string }>>(
        "/crm/leads/",
        { status: "active", page_size: "100" },
      );
      leads = res.results;
    } catch (err) {
      console.error("[crm/reservations]", err);
      leads = [];
    }
  }

  async function fetchUnits() {
    try {
      const res = await api.get<PaginatedResponse<{ id: number; unit_number: string; property_name: string; asking_price: string }>>(
        "/properties/units/",
        { status: "available", page_size: "100" },
      );
      units = res.results;
    } catch (err) {
      console.error("[crm/reservations]", err);
      units = [];
    }
  }

  async function fetchReservationDetail(id: number) {
    detailLoading = true;
    detailError = "";
    try {
      selectedReservation = await api.get<ReservationDetail>(`/crm/reservations/${id}/`);
      if (selectedReservation.status === "payment_pending" && !paymentForm.amount) {
        paymentForm.amount = selectedReservation.deposit_amount || "";
      }
    } catch (err) {
      console.error("[crm/reservations]", err);
      selectedReservation = null;
      detailError = "Could not load reservation details.";
      if (!(err instanceof ApiError && err.status === 404)) {
        toast.error("Error", "Could not load reservation details");
      }
    } finally {
      detailLoading = false;
    }
  }

  async function fetchLeadDetail(id: number) {
    leadDetailLoading = true;
    leadDetailError = "";
    try {
      leadDetail = await api.get<LeadDetail>(`/crm/leads/${id}/`);
    } catch (err) {
      console.error("[crm/reservations]", err);
      leadDetail = null;
      if (err instanceof ApiError) {
        if (err.status === 403) {
          leadDetailError = "You do not have permission to view this lead.";
        } else if (err.status === 404) {
          leadDetailError = "Lead not found.";
        } else {
          leadDetailError = "Could not load lead details.";
          toast.error("Error", "Could not load lead details");
        }
      } else {
        leadDetailError = "Could not load lead details.";
        toast.error("Error", "Could not load lead details");
      }
    } finally {
      leadDetailLoading = false;
    }
  }

  async function openLeadModal(id: number) {
    showLeadModal = true;
    activeLeadTab = "overview";
    await fetchLeadDetail(id);
  }

  function closeLeadModal() {
    showLeadModal = false;
    leadDetailLoading = false;
    leadDetailError = "";
    leadDetail = null;
    activeLeadTab = "overview";
  }

  async function openDetailDrawer(id: number) {
    selectedReservationId = id;
    showDetailDrawer = true;
    activeDetailSection = "progress";
    resetDetailActionForms();
    await fetchReservationDetail(id);
  }

  function closeDetailDrawer() {
    showDetailDrawer = false;
    selectedReservationId = null;
    selectedReservation = null;
    detailError = "";
    resetDetailActionForms();
    if ($page.url.searchParams.has("open")) {
      goto("/crm/reservations", { replaceState: true, noScroll: true, keepFocus: true });
    }
  }

  async function refreshDetailDrawer() {
    if (!selectedReservationId) return;
    await Promise.all([fetchReservationDetail(selectedReservationId), fetchReservations(), fetchOverview()]);
  }

  async function handleConfirmReservation() {
    if (!selectedReservationId) return;
    confirming = true;
    try {
      await api.post(`/crm/reservations/${selectedReservationId}/confirm/`, { notes: confirmNotes });
      toast.success("Reservation Confirmed", "Payment instructions have been sent");
      confirmNotes = "";
      await refreshDetailDrawer();
    } catch (err) {
      console.error("[crm/reservations]", err);
      if (err instanceof ApiError) {
        const msg = err.data?.detail || err.data?.error || "Could not confirm reservation";
        toast.error("Error", String(msg));
      } else {
        toast.error("Error", "Could not confirm reservation");
      }
    } finally {
      confirming = false;
    }
  }

  async function handleRecordPayment() {
    if (!selectedReservationId) return;
    recordingPayment = true;
    try {
      await api.post(`/crm/reservations/${selectedReservationId}/record_payment/`, {
        amount: paymentForm.amount,
        payment_method: paymentForm.payment_method,
        reference_number: paymentForm.reference_number,
        notes: paymentForm.notes,
      });
      toast.success("Payment Recorded", "Deposit payment has been recorded");
      paymentForm = { amount: "", payment_method: "bank_transfer", reference_number: "", notes: "" };
      await refreshDetailDrawer();
    } catch (err) {
      console.error("[crm/reservations]", err);
      if (err instanceof ApiError) {
        const msgs = Object.values(err.fieldErrors).flat().join(", ");
        toast.error("Validation Error", msgs || "Could not record payment");
      } else {
        toast.error("Error", "Could not record payment");
      }
    } finally {
      recordingPayment = false;
    }
  }

  async function handleConvertReservation() {
    if (!selectedReservationId) return;
    converting = true;
    try {
      await api.post(`/crm/reservations/${selectedReservationId}/convert/`, {});
      toast.success("Converted", "Lead has been converted to a customer");
      await refreshDetailDrawer();
    } catch (err) {
      console.error("[crm/reservations]", err);
      if (err instanceof ApiError) {
        const msg = err.data?.detail || err.data?.error || "Could not convert reservation";
        toast.error("Error", String(msg));
      } else {
        toast.error("Error", "Could not convert reservation");
      }
    } finally {
      converting = false;
    }
  }

  async function handleCancelReservation() {
    if (!selectedReservationId) return;
    if (!cancelReason.trim()) {
      toast.error("Required", "Please provide a cancellation reason");
      return;
    }
    cancelling = true;
    try {
      await api.post(`/crm/reservations/${selectedReservationId}/cancel/`, { reason: cancelReason });
      toast.success("Cancelled", "Reservation has been cancelled");
      cancelReason = "";
      await refreshDetailDrawer();
    } catch (err) {
      console.error("[crm/reservations]", err);
      if (err instanceof ApiError) {
        const msg = err.data?.detail || err.data?.error || "Could not cancel reservation";
        toast.error("Error", String(msg));
      } else {
        toast.error("Error", "Could not cancel reservation");
      }
    } finally {
      cancelling = false;
    }
  }

  async function handleExtendReservation() {
    if (!selectedReservationId) return;
    extending = true;
    try {
      await api.post(`/crm/reservations/${selectedReservationId}/extend_hold/`, {
        extend_hours: extendForm.extend_hours,
        notes: extendForm.notes,
      });
      toast.success("Hold Extended", `Hold extended by ${extendForm.extend_hours} hours`);
      extendForm = { extend_hours: 24, notes: "" };
      await refreshDetailDrawer();
    } catch (err) {
      console.error("[crm/reservations]", err);
      if (err instanceof ApiError) {
        const msg = err.data?.detail || err.data?.error || "Could not extend hold";
        toast.error("Error", String(msg));
      } else {
        toast.error("Error", "Could not extend hold");
      }
    } finally {
      extending = false;
    }
  }

  async function handleDeleteReservation() {
    if (!selectedReservationId) return;
    if (!confirm("Are you sure you want to delete this reservation? This action cannot be undone.")) {
      return;
    }
    deleting = true;
    try {
      await api.delete(`/crm/reservations/${selectedReservationId}/`);
      toast.success("Deleted", "Reservation has been deleted");
      closeDetailDrawer();
      await Promise.all([fetchReservations(), fetchOverview()]);
    } catch (err) {
      console.error("[crm/reservations]", err);
      toast.error("Error", "Could not delete reservation");
    } finally {
      deleting = false;
    }
  }

  // --- Event Handlers ---
  let debounceTimer: ReturnType<typeof setTimeout>;

  function handleSearchInput(value: string) {
    search = value;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      currentPage = 1;
      fetchReservations();
    }, 300);
  }

  function handleStatusChange(value: string) {
    statusFilter = value;
    currentPage = 1;
    fetchReservations();
  }

  function handleProjectChange(value: string) {
    projectFilter = value;
    currentPage = 1;
    fetchReservations();
  }

  function goToPage(page: number) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    fetchReservations();
  }

  async function handleCreateReservation(e: Event) {
    e.preventDefault();
    createErrors = {};
    saving = true;

    try {
      const holdHours = Number(createForm.hold_hours) || 48;
      const holdExpiresAt = new Date(Date.now() + holdHours * 60 * 60 * 1000).toISOString();

      const payload: Record<string, unknown> = {
        lead: Number(createForm.lead),
        unit: Number(createForm.unit),
        project: createForm.project ? Number(createForm.project) : null,
        total_price: createForm.total_price,
        deposit_amount: createForm.deposit_amount,
        reservation_fee: createForm.reservation_fee || "0",
        hold_expires_at: holdExpiresAt,
        payment_deadline: createForm.payment_deadline
          ? new Date(createForm.payment_deadline + "T23:59:59").toISOString()
          : null,
        notes: createForm.notes || "",
      };

      await api.post<ReservationListItem>("/crm/reservations/", payload);
      toast.success("Reservation created", "The reservation has been recorded successfully");
      showSlideOver = false;
      resetCreateForm();
      fetchReservations();
      fetchOverview();
    } catch (err) {
      console.error("[crm/reservations]", err);
      if (err instanceof ApiError) {
        createErrors = err.fieldErrors;
        toast.error("Validation error", "Please fix the highlighted fields");
      } else {
        toast.error("Something went wrong", "Could not create the reservation");
      }
    }
    saving = false;
  }

  function openSlideOver() {
    resetCreateForm();
    fetchLeads();
    fetchUnits();
    showSlideOver = true;
  }

  function closeSlideOver() {
    showSlideOver = false;
    resetCreateForm();
  }

  // --- Initialize ---
  onMount(() => {
    void fetchOverview();
    void fetchReservations();
    void fetchProjects();
  });

  $effect(() => {
    const openParam = $page.url.searchParams.get("open");
    if (!openParam) return;
    const id = Number(openParam);
    if (!Number.isInteger(id) || id <= 0) return;
    if (showDetailDrawer && selectedReservationId === id) return;
    void openDetailDrawer(id);
  });
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-orange-400">CRM</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Reservations</h1>
      <p class="mt-1 text-sm text-neutral-500">Track unit holds, payments, and conversions</p>
    </div>
    <button
      onclick={openSlideOver}
      class="inline-flex items-center gap-2 px-4 py-2 bg-neutral-900 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
      </svg>
      New Reservation
    </button>
  </div>

  <!-- KPI Strip -->
  {#if overviewLoading}
    <div class="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-4">
      {#each Array(6) as _}
        <div class="bg-orange-50 border border-orange-200 rounded-lg p-4 animate-pulse">
          <div class="h-3 w-20 bg-orange-100 rounded mb-3"></div>
          <div class="h-7 w-14 bg-orange-100 rounded"></div>
        </div>
      {/each}
    </div>
  {:else if overview}
    <div class="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-4">
      <div class="min-w-0 bg-orange-50 border border-orange-200 rounded-lg p-4">
        <p class="text-xs font-medium uppercase tracking-wider text-neutral-500">Active Holds</p>
        <p class="mt-2 text-2xl font-semibold text-neutral-900 tabular-nums">{overview.active_holds.toLocaleString()}</p>
      </div>
      <div class="min-w-0 bg-orange-50 border border-orange-200 rounded-lg p-4">
        <p class="text-xs font-medium uppercase tracking-wider text-neutral-500">Pending Payments</p>
        <p class="mt-2 text-2xl font-semibold text-neutral-900 tabular-nums">{overview.pending_payments.toLocaleString()}</p>
      </div>
      <div class="min-w-0 bg-orange-50 border border-orange-200 rounded-lg p-4">
        <p class="text-xs font-medium uppercase tracking-wider text-neutral-500">Paid</p>
        <p class="mt-2 text-2xl font-semibold text-neutral-900 tabular-nums">{overview.paid.toLocaleString()}</p>
      </div>
      <div class="min-w-0 bg-orange-50 border border-orange-200 rounded-lg p-4">
        <p class="text-xs font-medium uppercase tracking-wider text-neutral-500">Converted</p>
        <p class="mt-2 text-2xl font-semibold text-neutral-900 tabular-nums">{overview.converted.toLocaleString()}</p>
      </div>
      <div class="min-w-0 bg-orange-50 border border-orange-200 rounded-lg p-4">
        <p class="text-xs font-medium uppercase tracking-wider text-neutral-500">Expired</p>
        <p class="mt-2 text-2xl font-semibold text-neutral-900 tabular-nums">{overview.expired.toLocaleString()}</p>
      </div>
      <div class="min-w-0 bg-orange-50 border border-orange-200 rounded-lg p-4">
        <p class="text-xs font-medium uppercase tracking-wider text-neutral-500 leading-tight">Total Converted Value</p>
        <p
          class="mt-2 text-lg lg:text-xl font-semibold text-neutral-900 tabular-nums leading-tight wrap-anywhere"
          title={currency.format(overview.total_converted_value)}
        >
          {currency.format(overview.total_converted_value)}
        </p>
      </div>
    </div>
  {/if}

  <!-- Filters -->
  <div class="bg-white rounded-xl border border-neutral-200 p-5">
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Search</span>
        <div class="relative">
          <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
          </svg>
          <input
            type="text"
            placeholder="Search reservations..."
            value={search}
            oninput={(e) => handleSearchInput((e.target as HTMLInputElement).value)}
            class="w-full rounded-lg border border-neutral-300 pl-9 pr-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 focus:outline-none"
          />
        </div>
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Status</span>
        <select
          value={statusFilter}
          onchange={(e) => handleStatusChange((e.target as HTMLSelectElement).value)}
          class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 focus:outline-none"
        >
          <option value="">All Statuses</option>
          <option value="hold">Hold</option>
          <option value="reserved">Reserved</option>
          <option value="payment_pending">Payment Pending</option>
          <option value="paid">Paid</option>
          <option value="converting">Converting</option>
          <option value="converted">Converted</option>
          <option value="expired">Expired</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </label>

      <label>
        <span class="block text-sm font-medium text-neutral-700 mb-1.5">Project</span>
        <select
          value={projectFilter}
          onchange={(e) => handleProjectChange((e.target as HTMLSelectElement).value)}
          class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 focus:outline-none"
        >
          <option value="">All Projects</option>
          {#each projects as proj}
            <option value={String(proj.id)}>{proj.name}</option>
          {/each}
        </select>
      </label>
    </div>
  </div>

  <!-- Table -->
  <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
    {#if loading}
      <!-- Skeleton loader -->
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-neutral-200">
          <thead class="bg-neutral-50">
            <tr>
              {#each ["Reservation #", "Lead", "Unit", "Property", "Project", "Status", "Total Price", "Deposit", "Hold Expires", "Created"] as col}
                <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">{col}</th>
              {/each}
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each Array(8) as _}
              <tr class="animate-pulse">
                <td class="px-5 py-4"><div class="h-4 w-24 bg-neutral-200 rounded"></div></td>
                <td class="px-5 py-4"><div class="h-4 w-28 bg-neutral-200 rounded"></div></td>
                <td class="px-5 py-4"><div class="h-4 w-16 bg-neutral-200 rounded"></div></td>
                <td class="px-5 py-4"><div class="h-4 w-24 bg-neutral-200 rounded"></div></td>
                <td class="px-5 py-4"><div class="h-4 w-20 bg-neutral-200 rounded"></div></td>
                <td class="px-5 py-4"><div class="h-5 w-20 bg-neutral-200 rounded-full"></div></td>
                <td class="px-5 py-4"><div class="h-4 w-20 bg-neutral-200 rounded"></div></td>
                <td class="px-5 py-4"><div class="h-4 w-18 bg-neutral-200 rounded"></div></td>
                <td class="px-5 py-4"><div class="h-4 w-28 bg-neutral-200 rounded"></div></td>
                <td class="px-5 py-4"><div class="h-4 w-24 bg-neutral-200 rounded"></div></td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {:else if listError}
      <div class="px-5 py-6">
        <DataStateBanner
          title="Couldn't load reservations"
          message={listError}
          onretry={fetchReservations}
        />
      </div>
    {:else if reservations.length === 0}
      <!-- Empty state -->
      <div class="flex flex-col items-center justify-center py-20 text-center">
        <div class="text-neutral-400 mb-2">
          <svg class="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m6.75 12H9.75m-1.5 3h7.5M6.75 21h10.5a2.25 2.25 0 0 0 2.25-2.25V8.625a2.25 2.25 0 0 0-.659-1.591L15.409 3.66A2.25 2.25 0 0 0 13.818 3H6.75A2.25 2.25 0 0 0 4.5 5.25v13.5A2.25 2.25 0 0 0 6.75 21Z" />
          </svg>
        </div>
        <p class="text-neutral-500 text-sm">No reservations found</p>
        <button
          onclick={openSlideOver}
          class="mt-3 text-sm font-medium text-neutral-900 hover:underline"
        >
          Create your first reservation
        </button>
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-neutral-200">
          <thead class="bg-neutral-50">
            <tr>
              <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Reservation #</th>
              <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Lead</th>
              <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Unit</th>
              <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Property</th>
              <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Project</th>
              <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Status</th>
              <th class="px-5 py-3.5 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Total Price</th>
              <th class="px-5 py-3.5 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider">Deposit</th>
              <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Hold Expires</th>
              <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider">Created</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each reservations as reservation}
              {@const holdExpired = isHoldExpired(reservation.hold_expires_at, reservation.status)}
              <tr
                class="hover:bg-neutral-50 cursor-pointer transition-colors"
                onclick={() => openDetailDrawer(reservation.id)}
              >
                <!-- Reservation # -->
                <td class="px-5 py-4 text-sm font-medium text-neutral-900 whitespace-nowrap">
                  {reservation.reservation_number}
                </td>

                <!-- Lead -->
                <td class="px-5 py-4 text-sm whitespace-nowrap">
                  <button
                    class="text-neutral-900 hover:underline font-medium"
                    onclick={(event) => {
                      event.stopPropagation();
                      void openLeadModal(reservation.lead_id);
                    }}
                  >
                    {reservation.lead_name}
                  </button>
                </td>

                <!-- Unit -->
                <td class="px-5 py-4 text-sm text-neutral-600 whitespace-nowrap">
                  {reservation.unit_number}
                </td>

                <!-- Property -->
                <td class="px-5 py-4 text-sm text-neutral-600 whitespace-nowrap">
                  {reservation.property_name}
                </td>

                <!-- Project -->
                <td class="px-5 py-4 text-sm text-neutral-600 whitespace-nowrap">
                  {reservation.project_name ?? "\u2014"}
                </td>

                <!-- Status -->
                <td class="px-5 py-4 whitespace-nowrap">
                  <StatusBadge status={reservation.status} label={reservation.status_display} />
                </td>

                <!-- Total Price -->
                <td class="px-5 py-4 text-sm text-neutral-900 text-right tabular-nums whitespace-nowrap">
                  {currency.format(reservation.total_price)}
                </td>

                <!-- Deposit -->
                <td class="px-5 py-4 text-sm text-neutral-600 text-right tabular-nums whitespace-nowrap">
                  {currency.format(reservation.deposit_amount)}
                </td>

                <!-- Hold Expires -->
                <td class="px-5 py-4 text-sm whitespace-nowrap {holdExpired ? 'text-neutral-400' : 'text-neutral-600'}">
                  {formatDateTime(reservation.hold_expires_at)}
                  {#if holdExpired}
                    <span class="ml-1 text-xs text-neutral-400">(expired)</span>
                  {/if}
                </td>

                <!-- Created -->
                <td class="px-5 py-4 text-sm text-neutral-500 whitespace-nowrap">
                  {formatDateShort(reservation.created_at)}
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

<!-- Slide-Over: New Reservation -->
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
      <h2 class="text-lg font-semibold text-neutral-900">New Reservation</h2>
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
      <form id="create-reservation-form" onsubmit={handleCreateReservation} class="space-y-5">
        <!-- Lead -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Lead <span class="text-neutral-400">*</span></span>
          <select
            bind:value={createForm.lead}
            required
            class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 focus:outline-none"
          >
            <option value="">Select a lead</option>
            {#each leads as lead}
              <option value={String(lead.id)}>{lead.first_name} {lead.last_name}</option>
            {/each}
          </select>
          {#if createFieldError("lead")}<p class="mt-1 text-xs text-neutral-500">{createFieldError("lead")}</p>{/if}
        </label>

        <!-- Unit -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Unit <span class="text-neutral-400">*</span></span>
          <select
            bind:value={createForm.unit}
            required
            class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 focus:outline-none"
          >
            <option value="">Select an available unit</option>
            {#each units as unit}
              <option value={String(unit.id)}>{unit.unit_number} - {unit.property_name} ({currency.format(unit.asking_price)})</option>
            {/each}
          </select>
          {#if createFieldError("unit")}<p class="mt-1 text-xs text-neutral-500">{createFieldError("unit")}</p>{/if}
        </label>

        <!-- Project -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Project <span class="text-neutral-400">(optional)</span></span>
          <select
            bind:value={createForm.project}
            class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 focus:outline-none"
          >
            <option value="">None</option>
            {#each projects as proj}
              <option value={String(proj.id)}>{proj.name}</option>
            {/each}
          </select>
          {#if createFieldError("project")}<p class="mt-1 text-xs text-neutral-500">{createFieldError("project")}</p>{/if}
        </label>

        <!-- Total Price & Deposit (2-col) -->
        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Total Price <span class="text-neutral-400">*</span></span>
            <input
              type="number"
              step="0.01"
              min="0"
              bind:value={createForm.total_price}
              required
              placeholder="0.00"
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 focus:outline-none tabular-nums"
            />
            {#if createFieldError("total_price")}<p class="mt-1 text-xs text-neutral-500">{createFieldError("total_price")}</p>{/if}
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Deposit Amount <span class="text-neutral-400">*</span></span>
            <input
              type="number"
              step="0.01"
              min="0"
              bind:value={createForm.deposit_amount}
              required
              placeholder="0.00"
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 focus:outline-none tabular-nums"
            />
            {#if createFieldError("deposit_amount")}<p class="mt-1 text-xs text-neutral-500">{createFieldError("deposit_amount")}</p>{/if}
          </label>
        </div>

        <!-- Reservation Fee & Hold Duration (2-col) -->
        <div class="grid grid-cols-2 gap-4">
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Reservation Fee</span>
            <input
              type="number"
              step="0.01"
              min="0"
              bind:value={createForm.reservation_fee}
              placeholder="0.00"
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 focus:outline-none tabular-nums"
            />
            {#if createFieldError("reservation_fee")}<p class="mt-1 text-xs text-neutral-500">{createFieldError("reservation_fee")}</p>{/if}
          </label>
          <label>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Hold Duration <span class="text-neutral-400">(hours)</span></span>
            <input
              type="number"
              min="1"
              step="1"
              bind:value={createForm.hold_hours}
              placeholder="48"
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 focus:outline-none tabular-nums"
            />
            {#if createFieldError("hold_expires_at")}<p class="mt-1 text-xs text-neutral-500">{createFieldError("hold_expires_at")}</p>{/if}
          </label>
        </div>

        <!-- Payment Deadline -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Payment Deadline <span class="text-neutral-400">(optional)</span></span>
          <DateInput bind:value={createForm.payment_deadline} />
          {#if createFieldError("payment_deadline")}<p class="mt-1 text-xs text-neutral-500">{createFieldError("payment_deadline")}</p>{/if}
        </label>

        <!-- Notes -->
        <label>
          <span class="block text-sm font-medium text-neutral-700 mb-1.5">Notes</span>
          <textarea
            bind:value={createForm.notes}
            rows="3"
            placeholder="Any additional details..."
            class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:border-neutral-500 focus:ring-1 focus:ring-neutral-500 focus:outline-none resize-none"
          ></textarea>
          {#if createFieldError("notes")}<p class="mt-1 text-xs text-neutral-500">{createFieldError("notes")}</p>{/if}
        </label>
      </form>
    </div>

    <!-- Footer -->
    <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-neutral-100 shrink-0">
      {#if isDev}
        <button type="button" onclick={devFillReservation} class="mr-auto rounded-lg bg-orange-500 px-4 py-2 text-sm font-semibold text-white hover:bg-orange-600 transition-colors">Dev Fill</button>
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
        form="create-reservation-form"
        disabled={saving}
        class="px-4 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium hover:bg-neutral-800 disabled:opacity-50 transition-colors"
      >
        {saving ? "Creating..." : "Create Reservation"}
      </button>
    </div>
  </div>
{/if}

<!-- Slide-Over: Reservation Details -->
{#if showDetailDrawer}
  <button
    class="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm cursor-default"
    onclick={closeDetailDrawer}
    tabindex="-1"
    aria-label="Close panel"
  ></button>

  <aside class="fixed inset-y-0 right-0 z-50 w-full max-w-4xl flex flex-col bg-white shadow-2xl slide-over-enter">
    <div class="flex items-start justify-between gap-4 px-6 py-4 border-b border-neutral-100 shrink-0">
      <div>
        <h2 class="text-lg font-semibold text-neutral-900">
          {selectedReservation?.reservation_number || "Reservation Detail"}
        </h2>
        {#if selectedReservation}
          <div class="mt-2">
            <StatusBadge status={selectedReservation.status} label={selectedReservation.status_display} />
          </div>
        {/if}
      </div>
      <div class="flex items-center gap-2">
        {#if selectedReservation && !detailIsTerminal}
          <button
            onclick={handleDeleteReservation}
            disabled={deleting}
            class="border border-neutral-300 text-neutral-500 rounded-lg px-3 py-2 text-sm font-medium hover:bg-neutral-50 disabled:opacity-50 transition-colors"
          >
            {deleting ? "Deleting..." : "Delete"}
          </button>
        {/if}
        <button
          onclick={closeDetailDrawer}
          class="p-1.5 rounded-lg text-neutral-400 hover:text-neutral-900 hover:bg-neutral-100 transition-colors"
          aria-label="Close"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto px-6 py-5">
      {#if detailLoading}
        <div class="animate-pulse space-y-3">
          <div class="h-10 bg-neutral-100 rounded-lg"></div>
          <div class="h-48 bg-neutral-100 rounded-lg"></div>
          <div class="h-10 bg-neutral-100 rounded-lg"></div>
          <div class="h-40 bg-neutral-100 rounded-lg"></div>
        </div>
      {:else if detailError || !selectedReservation}
        <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-4">
          <p class="text-sm text-neutral-600">{detailError || "Could not load reservation details."}</p>
        </div>
      {:else}
        <div class="space-y-3">
          <section class="rounded-2xl border border-neutral-200 bg-white">
            <button
              type="button"
              class="flex w-full items-center justify-between gap-3 px-4 py-3 text-left sm:px-5"
              aria-expanded={activeDetailSection === "progress"}
              onclick={() => toggleDetailSection("progress")}
            >
              <span class="text-sm font-semibold text-neutral-900 sm:text-base">Reservation Progress</span>
              <span class="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                {activeDetailSection === "progress" ? "Collapse" : "Expand"}
              </span>
            </button>
          </section>
          {#if activeDetailSection === "progress"}
            <section class="bg-white border border-neutral-200 rounded-lg p-6">
              <div class="flex items-center justify-between">
                {#each LIFECYCLE_STEPS as step, i}
                  {@const completed = !isCancelledOrExpired && currentStepIndex > i}
                  {@const current = !isCancelledOrExpired && currentStepIndex === i}
                  {@const cancelledAtThis = isCancelledOrExpired && terminalAtStep() === i}
                  {@const pastCancelPoint = isCancelledOrExpired && i < terminalAtStep()}

                  {#if i > 0}
                    <div class="flex-1 h-0.5 mx-2 {completed || pastCancelPoint ? 'bg-neutral-900' : 'bg-neutral-200'}"></div>
                  {/if}

                  <div class="flex flex-col items-center gap-2 shrink-0">
                    {#if cancelledAtThis}
                      <div class="w-9 h-9 rounded-full bg-neutral-200 flex items-center justify-center">
                        <svg class="w-4 h-4 text-neutral-400" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
                        </svg>
                      </div>
                      <div class="text-center">
                        <span class="text-xs font-medium text-neutral-400 line-through">{step.label}</span>
                        <span class="block text-xs text-neutral-400">{selectedReservation.status_display}</span>
                      </div>
                    {:else if completed || pastCancelPoint}
                      <div class="w-9 h-9 rounded-full bg-neutral-900 flex items-center justify-center">
                        <svg class="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                        </svg>
                      </div>
                      <span class="text-xs font-semibold text-neutral-900">{step.label}</span>
                    {:else if current}
                      <div class="w-9 h-9 rounded-full bg-neutral-900 ring-4 ring-neutral-200 flex items-center justify-center">
                        <span class="text-sm font-semibold text-white">{i + 1}</span>
                      </div>
                      <span class="text-xs font-semibold text-neutral-900">{step.label}</span>
                    {:else}
                      <div class="w-9 h-9 rounded-full bg-neutral-200 flex items-center justify-center">
                        <span class="text-sm font-medium text-neutral-400">{i + 1}</span>
                      </div>
                      <span class="text-xs font-medium text-neutral-400">{step.label}</span>
                    {/if}
                  </div>
                {/each}
              </div>
            </section>
          {/if}

          <section class="rounded-2xl border border-neutral-200 bg-white">
            <button
              type="button"
              class="flex w-full items-center justify-between gap-3 px-4 py-3 text-left sm:px-5"
              aria-expanded={activeDetailSection === "unit"}
              onclick={() => toggleDetailSection("unit")}
            >
              <span class="text-sm font-semibold text-neutral-900 sm:text-base">Unit Information</span>
              <span class="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                {activeDetailSection === "unit" ? "Collapse" : "Expand"}
              </span>
            </button>
          </section>
          {#if activeDetailSection === "unit"}
            <section class="bg-white border border-neutral-200 rounded-lg p-6">
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
                <div><dt class="text-sm text-neutral-500">Unit Number</dt><dd class="text-sm font-medium text-neutral-900 mt-0.5">{selectedReservation.unit_number}</dd></div>
                <div><dt class="text-sm text-neutral-500">Property</dt><dd class="text-sm font-medium text-neutral-900 mt-0.5">{selectedReservation.property_name}</dd></div>
                <div><dt class="text-sm text-neutral-500">Project</dt><dd class="text-sm font-medium text-neutral-900 mt-0.5">{selectedReservation.project_name || "--"}</dd></div>
                <div><dt class="text-sm text-neutral-500">Floor</dt><dd class="text-sm font-medium text-neutral-900 mt-0.5">{selectedReservation.unit_floor ?? "--"}</dd></div>
                <div><dt class="text-sm text-neutral-500">Area (sqft)</dt><dd class="text-sm font-medium text-neutral-900 mt-0.5">{selectedReservation.unit_area_sqft ? parseFloat(selectedReservation.unit_area_sqft).toLocaleString() : "--"}</dd></div>
                <div><dt class="text-sm text-neutral-500">Bedrooms</dt><dd class="text-sm font-medium text-neutral-900 mt-0.5">{selectedReservation.unit_bedrooms ?? "--"}</dd></div>
                <div><dt class="text-sm text-neutral-500">Bathrooms</dt><dd class="text-sm font-medium text-neutral-900 mt-0.5">{selectedReservation.unit_bathrooms ?? "--"}</dd></div>
                <div><dt class="text-sm text-neutral-500">Asking Price</dt><dd class="text-sm font-medium text-neutral-900 mt-0.5">{selectedReservation.unit_asking_price ? currency.format(selectedReservation.unit_asking_price) : "--"}</dd></div>
                <div>
                  <dt class="text-sm text-neutral-500">Current Status</dt>
                  <dd class="mt-0.5">
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-neutral-100 text-neutral-700 capitalize">
                      {selectedReservation.unit_status?.replace(/_/g, " ") || "--"}
                    </span>
                  </dd>
                </div>
              </div>
            </section>
          {/if}

          <section class="rounded-2xl border border-neutral-200 bg-white">
            <button
              type="button"
              class="flex w-full items-center justify-between gap-3 px-4 py-3 text-left sm:px-5"
              aria-expanded={activeDetailSection === "lead"}
              onclick={() => toggleDetailSection("lead")}
            >
              <span class="text-sm font-semibold text-neutral-900 sm:text-base">Lead Information</span>
              <span class="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                {activeDetailSection === "lead" ? "Collapse" : "Expand"}
              </span>
            </button>
          </section>
          {#if activeDetailSection === "lead"}
            <section class="bg-white border border-neutral-200 rounded-lg p-6">
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
                <div>
                  <dt class="text-sm text-neutral-500">Lead Name</dt>
                  <dd class="mt-0.5">
                    <button
                      class="text-sm font-medium text-neutral-900 underline decoration-neutral-300 hover:decoration-neutral-900"
                      onclick={() => {
                        if (selectedReservation) void openLeadModal(selectedReservation.lead_id);
                      }}
                    >
                      {selectedReservation.lead_name}
                    </button>
                  </dd>
                </div>
                <div><dt class="text-sm text-neutral-500">Email</dt><dd class="text-sm font-medium text-neutral-900 mt-0.5">{selectedReservation.lead_email || "--"}</dd></div>
                <div><dt class="text-sm text-neutral-500">Phone</dt><dd class="text-sm font-medium text-neutral-900 mt-0.5">{selectedReservation.lead_phone || "--"}</dd></div>
                <div>
                  <dt class="text-sm text-neutral-500">Type</dt>
                  <dd class="mt-0.5">
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-neutral-100 text-neutral-700 capitalize">
                      {selectedReservation.lead_type?.replace(/_/g, " ") || "--"}
                    </span>
                  </dd>
                </div>
                <div>
                  <dt class="text-sm text-neutral-500">Payment Capability</dt>
                  <dd class="mt-0.5">
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-neutral-100 text-neutral-700 capitalize">
                      {selectedReservation.lead_payment_capability?.replace(/_/g, " ") || "--"}
                    </span>
                  </dd>
                </div>
              </div>
            </section>
          {/if}

          <section class="rounded-2xl border border-neutral-200 bg-white">
            <button
              type="button"
              class="flex w-full items-center justify-between gap-3 px-4 py-3 text-left sm:px-5"
              aria-expanded={activeDetailSection === "payment"}
              onclick={() => toggleDetailSection("payment")}
            >
              <span class="text-sm font-semibold text-neutral-900 sm:text-base">Payment Status</span>
              <span class="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                {activeDetailSection === "payment" ? "Collapse" : "Expand"}
              </span>
            </button>
          </section>
          {#if activeDetailSection === "payment"}
            <section class="bg-white border border-neutral-200 rounded-lg p-6">
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
                <div><dt class="text-sm text-neutral-500">Total Price</dt><dd class="text-sm font-medium text-neutral-900 mt-0.5">{currency.format(detailTotalPrice)}</dd></div>
                <div><dt class="text-sm text-neutral-500">Deposit Required</dt><dd class="text-sm font-medium text-neutral-900 mt-0.5">{currency.format(detailDepositAmount)}</dd></div>
                <div><dt class="text-sm text-neutral-500">Reservation Fee</dt><dd class="text-sm font-medium text-neutral-900 mt-0.5">{currency.format(detailReservationFee)}</dd></div>
                {#if selectedReservation.payment_plan_number}
                  <div>
                    <dt class="text-sm text-neutral-500">Payment Plan</dt>
                    <dd class="mt-0.5">
                      <a
                        href="/finance/payment-plans/{selectedReservation.payment_plan}"
                        class="text-sm font-medium text-neutral-900 underline decoration-neutral-300 hover:decoration-neutral-900 transition-colors"
                      >
                        {selectedReservation.payment_plan_number}
                      </a>
                    </dd>
                  </div>
                {/if}
                {#if selectedReservation.converted_customer_name}
                  <div><dt class="text-sm text-neutral-500">Converted Customer</dt><dd class="text-sm font-medium text-neutral-900 mt-0.5">{selectedReservation.converted_customer_name}</dd></div>
                {/if}
              </div>
              {#if detailDepositAmount > 0}
                <div class="mt-6 pt-4 border-t border-neutral-100">
                  <div class="flex items-center justify-between mb-2">
                    <span class="text-sm text-neutral-500">Deposit Progress</span>
                    <span class="text-sm font-medium text-neutral-900">
                      {selectedReservation.status === "paid" || selectedReservation.status === "converted" || selectedReservation.status === "converting"
                        ? currency.format(detailDepositAmount)
                        : currency.format(0)}
                      / {currency.format(detailDepositAmount)}
                    </span>
                  </div>
                  <div class="w-full bg-neutral-100 rounded-full h-2">
                    <div
                      class="bg-neutral-900 h-2 rounded-full transition-all duration-500"
                      style="width: {selectedReservation.status === 'paid' || selectedReservation.status === 'converted' || selectedReservation.status === 'converting' ? '100' : '0'}%"
                    ></div>
                  </div>
                </div>
              {/if}
            </section>
          {/if}

          <section class="rounded-2xl border border-neutral-200 bg-white">
            <button
              type="button"
              class="flex w-full items-center justify-between gap-3 px-4 py-3 text-left sm:px-5"
              aria-expanded={activeDetailSection === "timeline"}
              onclick={() => toggleDetailSection("timeline")}
            >
              <span class="text-sm font-semibold text-neutral-900 sm:text-base">Timeline</span>
              <span class="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                {activeDetailSection === "timeline" ? "Collapse" : "Expand"}
              </span>
            </button>
          </section>
          {#if activeDetailSection === "timeline"}
            <section class="bg-white border border-neutral-200 rounded-lg p-6">
              {#if sortedDetailEvents.length === 0}
                <p class="text-sm text-neutral-400 italic">No events recorded yet.</p>
              {:else}
                <div class="relative">
                  {#each sortedDetailEvents as event, i}
                    {@const isLast = i === sortedDetailEvents.length - 1}
                    <div class="flex gap-4 pb-6 last:pb-0">
                      <div class="flex flex-col items-center shrink-0">
                        {#if isLast}
                          <div class="w-3 h-3 rounded-full border-2 border-neutral-900 bg-white mt-1"></div>
                        {:else}
                          <div class="w-3 h-3 rounded-full bg-neutral-900 mt-1"></div>
                        {/if}
                        {#if !isLast}
                          <div class="w-px flex-1 bg-neutral-200 mt-1"></div>
                        {/if}
                      </div>
                      <div class="flex-1 min-w-0 -mt-0.5">
                        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
                          <p class="text-sm font-medium text-neutral-900">{event.event_type_display}</p>
                          <div class="flex items-center gap-2 text-xs text-neutral-400">
                            {#if event.performed_by_name}
                              <span>{event.performed_by_name}</span>
                              <span>·</span>
                            {/if}
                            <time title={formatDateTime(event.created_at)}>{formatRelativeTime(event.created_at)}</time>
                          </div>
                        </div>
                        {#if event.notes}
                          <p class="text-sm text-neutral-500 mt-1">{event.notes}</p>
                        {/if}
                      </div>
                    </div>
                  {/each}
                </div>
              {/if}
            </section>
          {/if}

          <section class="rounded-2xl border border-neutral-200 bg-white">
            <button
              type="button"
              class="flex w-full items-center justify-between gap-3 px-4 py-3 text-left sm:px-5"
              aria-expanded={activeDetailSection === "actions"}
              onclick={() => toggleDetailSection("actions")}
            >
              <span class="text-sm font-semibold text-neutral-900 sm:text-base">Actions</span>
              <span class="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                {activeDetailSection === "actions" ? "Collapse" : "Expand"}
              </span>
            </button>
          </section>
          {#if activeDetailSection === "actions"}
            <section class="bg-white border border-neutral-200 rounded-lg p-6 space-y-6">
              {#if selectedReservation.status === "hold"}
                <div class="space-y-3 border border-neutral-100 rounded-lg p-4">
                  <p class="text-sm font-semibold text-neutral-900">Confirm Reservation</p>
                  <textarea
                    bind:value={confirmNotes}
                    rows="2"
                    placeholder="Notes (optional)"
                    class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent resize-none"
                  ></textarea>
                  <button
                    onclick={handleConfirmReservation}
                    disabled={confirming}
                    class="w-full bg-neutral-900 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-neutral-800 disabled:opacity-50"
                  >
                    {confirming ? "Confirming..." : "Confirm Reservation"}
                  </button>
                </div>

                <div class="space-y-3 border border-neutral-100 rounded-lg p-4">
                  <p class="text-sm font-semibold text-neutral-900">Extend Hold</p>
                  <input
                    type="number"
                    min="1"
                    max="168"
                    bind:value={extendForm.extend_hours}
                    class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
                  />
                  <textarea
                    bind:value={extendForm.notes}
                    rows="2"
                    placeholder="Notes (optional)"
                    class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent resize-none"
                  ></textarea>
                  {#if selectedReservation.hold_expires_at}
                    <div class="p-3 bg-neutral-50 rounded-lg space-y-2">
                      <div class="flex items-center justify-between">
                        <span class="text-xs text-neutral-500">Current Expiry</span>
                        <span class="text-xs font-medium text-neutral-700">{formatDateTime(selectedReservation.hold_expires_at)}</span>
                      </div>
                      {#if computedNewExpiry()}
                        <div class="flex items-center justify-between">
                          <span class="text-xs text-neutral-500">New Expiry</span>
                          <span class="text-xs font-medium text-neutral-900">{formatDateTime(computedNewExpiry()!.toISOString())}</span>
                        </div>
                      {/if}
                    </div>
                  {/if}
                  <button
                    onclick={handleExtendReservation}
                    disabled={extending || extendForm.extend_hours < 1 || extendForm.extend_hours > 168}
                    class="w-full border border-neutral-300 text-neutral-700 rounded-lg px-4 py-2 text-sm font-medium hover:bg-neutral-50 disabled:opacity-50"
                  >
                    {extending ? "Extending..." : "Extend Hold"}
                  </button>
                </div>

                <div class="space-y-3 border border-neutral-100 rounded-lg p-4">
                  <p class="text-sm font-semibold text-neutral-900">Cancel Reservation</p>
                  <textarea
                    bind:value={cancelReason}
                    rows="2"
                    placeholder="Cancellation reason (required)"
                    class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent resize-none"
                  ></textarea>
                  <button
                    onclick={handleCancelReservation}
                    disabled={cancelling || !cancelReason.trim()}
                    class="w-full border border-neutral-400 text-neutral-600 rounded-lg px-4 py-2 text-sm font-medium hover:bg-neutral-50 disabled:opacity-50"
                  >
                    {cancelling ? "Cancelling..." : "Cancel Reservation"}
                  </button>
                </div>
              {:else if selectedReservation.status === "payment_pending"}
                <div class="space-y-3 border border-neutral-100 rounded-lg p-4">
                  <p class="text-sm font-semibold text-neutral-900">Record Payment</p>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    bind:value={paymentForm.amount}
                    placeholder="Amount"
                    class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
                  />
                  <select
                    bind:value={paymentForm.payment_method}
                    class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
                  >
                    <option value="bank_transfer">Bank Transfer</option>
                    <option value="check">Check</option>
                    <option value="cash">Cash</option>
                    <option value="credit_card">Credit Card</option>
                    <option value="other">Other</option>
                  </select>
                  <input
                    type="text"
                    bind:value={paymentForm.reference_number}
                    placeholder="Reference Number"
                    class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
                  />
                  <textarea
                    bind:value={paymentForm.notes}
                    rows="2"
                    placeholder="Notes (optional)"
                    class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent resize-none"
                  ></textarea>
                  {#if selectedReservation.payment_deadline}
                    <div class="px-3 py-2 bg-neutral-50 rounded-lg">
                      <p class="text-xs text-neutral-500">Payment deadline</p>
                      <p class="text-sm font-medium text-neutral-900">{formatDateTime(selectedReservation.payment_deadline)}</p>
                    </div>
                  {/if}
                  <button
                    onclick={handleRecordPayment}
                    disabled={recordingPayment || !paymentForm.amount}
                    class="w-full bg-neutral-900 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-neutral-800 disabled:opacity-50"
                  >
                    {recordingPayment ? "Recording..." : "Record Payment"}
                  </button>
                </div>

                <div class="space-y-3 border border-neutral-100 rounded-lg p-4">
                  <p class="text-sm font-semibold text-neutral-900">Cancel Reservation</p>
                  <textarea
                    bind:value={cancelReason}
                    rows="2"
                    placeholder="Cancellation reason (required)"
                    class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent resize-none"
                  ></textarea>
                  <button
                    onclick={handleCancelReservation}
                    disabled={cancelling || !cancelReason.trim()}
                    class="w-full border border-neutral-400 text-neutral-600 rounded-lg px-4 py-2 text-sm font-medium hover:bg-neutral-50 disabled:opacity-50"
                  >
                    {cancelling ? "Cancelling..." : "Cancel Reservation"}
                  </button>
                </div>
              {:else if selectedReservation.status === "paid"}
                <div class="space-y-3 border border-neutral-100 rounded-lg p-4">
                  <p class="text-sm font-semibold text-neutral-900">Convert</p>
                  <button
                    onclick={handleConvertReservation}
                    disabled={converting}
                    class="w-full bg-neutral-900 text-white rounded-lg px-4 py-2 text-sm font-medium hover:bg-neutral-800 disabled:opacity-50"
                  >
                    {converting ? "Converting..." : "Convert to Customer"}
                  </button>
                </div>
                <div class="space-y-3 border border-neutral-100 rounded-lg p-4">
                  <p class="text-sm font-semibold text-neutral-900">Cancel Reservation</p>
                  <textarea
                    bind:value={cancelReason}
                    rows="2"
                    placeholder="Cancellation reason (required)"
                    class="w-full px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent resize-none"
                  ></textarea>
                  <button
                    onclick={handleCancelReservation}
                    disabled={cancelling || !cancelReason.trim()}
                    class="w-full border border-neutral-400 text-neutral-600 rounded-lg px-4 py-2 text-sm font-medium hover:bg-neutral-50 disabled:opacity-50"
                  >
                    {cancelling ? "Cancelling..." : "Cancel Reservation"}
                  </button>
                </div>
              {:else}
                <div class="text-center py-4">
                  <div class="inline-flex items-center justify-center w-10 h-10 rounded-full bg-neutral-100 mb-3">
                    {#if selectedReservation.status === "converted"}
                      <svg class="w-5 h-5 text-neutral-700" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                      </svg>
                    {:else}
                      <svg class="w-5 h-5 text-neutral-400" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
                      </svg>
                    {/if}
                  </div>
                  <p class="text-sm font-medium text-neutral-700">
                    This reservation is {selectedReservation.status_display.toLowerCase()}
                  </p>
                  {#if selectedReservation.status === "cancelled" && selectedReservation.cancelled_reason}
                    <div class="mt-3 p-3 bg-neutral-50 rounded-lg text-left">
                      <p class="text-xs text-neutral-500 mb-1">Cancellation Reason</p>
                      <p class="text-sm text-neutral-700">{selectedReservation.cancelled_reason}</p>
                    </div>
                  {/if}
                </div>
              {/if}
            </section>
          {/if}

          <section class="rounded-2xl border border-neutral-200 bg-white">
            <button
              type="button"
              class="flex w-full items-center justify-between gap-3 px-4 py-3 text-left sm:px-5"
              aria-expanded={activeDetailSection === "financial"}
              onclick={() => toggleDetailSection("financial")}
            >
              <span class="text-sm font-semibold text-neutral-900 sm:text-base">Financial Summary</span>
              <span class="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                {activeDetailSection === "financial" ? "Collapse" : "Expand"}
              </span>
            </button>
          </section>
          {#if activeDetailSection === "financial"}
            <section class="bg-white border border-neutral-200 rounded-lg p-6">
              <div class="space-y-0">
                <div class="flex items-center justify-between py-3 border-b border-neutral-100">
                  <span class="text-sm text-neutral-500">Total Price</span>
                  <span class="text-sm font-medium text-neutral-900">{currency.format(detailTotalPrice)}</span>
                </div>
                <div class="flex items-center justify-between py-3 border-b border-neutral-100">
                  <span class="text-sm text-neutral-500">Deposit Amount</span>
                  <span class="text-sm font-medium text-neutral-900">{currency.format(detailDepositAmount)}</span>
                </div>
                <div class="flex items-center justify-between py-3 border-b border-neutral-100">
                  <span class="text-sm text-neutral-500">Reservation Fee</span>
                  <span class="text-sm font-medium text-neutral-900">{currency.format(detailReservationFee)}</span>
                </div>
                <div class="flex items-center justify-between py-3">
                  <span class="text-sm font-semibold text-neutral-900">Net Amount</span>
                  <span class="text-sm font-semibold text-neutral-900">{currency.format(detailNetAmount)}</span>
                </div>
              </div>
            </section>
          {/if}

          <section class="rounded-2xl border border-neutral-200 bg-white">
            <button
              type="button"
              class="flex w-full items-center justify-between gap-3 px-4 py-3 text-left sm:px-5"
              aria-expanded={activeDetailSection === "notes"}
              onclick={() => toggleDetailSection("notes")}
            >
              <span class="text-sm font-semibold text-neutral-900 sm:text-base">Notes</span>
              <span class="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                {activeDetailSection === "notes" ? "Collapse" : "Expand"}
              </span>
            </button>
          </section>
          {#if activeDetailSection === "notes"}
            <section class="bg-white border border-neutral-200 rounded-lg p-6">
              {#if selectedReservation.notes}
                <p class="text-sm text-neutral-700 whitespace-pre-wrap">{selectedReservation.notes}</p>
              {:else}
                <p class="text-sm text-neutral-400 italic">No notes</p>
              {/if}
            </section>
          {/if}

          <section class="rounded-2xl border border-neutral-200 bg-white">
            <button
              type="button"
              class="flex w-full items-center justify-between gap-3 px-4 py-3 text-left sm:px-5"
              aria-expanded={activeDetailSection === "details"}
              onclick={() => toggleDetailSection("details")}
            >
              <span class="text-sm font-semibold text-neutral-900 sm:text-base">Details</span>
              <span class="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                {activeDetailSection === "details" ? "Collapse" : "Expand"}
              </span>
            </button>
          </section>
          {#if activeDetailSection === "details"}
            <section class="bg-white border border-neutral-200 rounded-lg p-6">
              <div class="space-y-3">
                <div>
                  <p class="text-sm text-neutral-500">Created</p>
                  <p class="text-sm font-medium text-neutral-900 mt-0.5">{formatDateTime(selectedReservation.created_at)}</p>
                </div>
                <div>
                  <p class="text-sm text-neutral-500">Updated</p>
                  <p class="text-sm font-medium text-neutral-900 mt-0.5">{formatDateTime(selectedReservation.updated_at)}</p>
                </div>
                {#if selectedReservation.performed_by_name}
                  <div>
                    <p class="text-sm text-neutral-500">Created By</p>
                    <p class="text-sm font-medium text-neutral-900 mt-0.5">{selectedReservation.performed_by_name}</p>
                  </div>
                {/if}
                {#if selectedReservation.reservation_date}
                  <div>
                    <p class="text-sm text-neutral-500">Reservation Date</p>
                    <p class="text-sm font-medium text-neutral-900 mt-0.5">{formatDateShort(selectedReservation.reservation_date)}</p>
                  </div>
                {/if}
                {#if selectedReservation.confirmation_date}
                  <div>
                    <p class="text-sm text-neutral-500">Confirmation Date</p>
                    <p class="text-sm font-medium text-neutral-900 mt-0.5">{formatDateTime(selectedReservation.confirmation_date)}</p>
                  </div>
                {/if}
              </div>
            </section>
          {/if}
        </div>
      {/if}
    </div>
  </aside>
{/if}

<!-- Lead Detail Modal -->
{#if showLeadModal}
  <button
    class="fixed inset-0 z-70 bg-black/50 backdrop-blur-sm cursor-default"
    onclick={closeLeadModal}
    tabindex="-1"
    aria-label="Close lead details"
  ></button>

  <div class="fixed inset-0 z-80 flex items-center justify-center p-4 sm:p-6">
    <div class="h-[92vh] w-full max-w-6xl overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-2xl">
      <div class="flex h-full flex-col">
        <div class="flex items-start justify-between gap-4 border-b border-neutral-100 px-6 py-4">
          <div class="min-w-0">
            <h2 class="truncate text-xl font-semibold text-neutral-900">
              {leadDetail?.full_name || "Lead Details"}
            </h2>
            {#if leadDetail}
              <div class="mt-2 flex items-center gap-2">
                <StatusBadge status={leadDetail.status} label={leadDetail.status_display} />
                <StatusBadge status={leadDetail.pipeline_stage} label={leadDetail.pipeline_stage_display} />
              </div>
            {/if}
          </div>
          <button
            onclick={closeLeadModal}
            class="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
            aria-label="Close"
          >
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="flex-1 overflow-y-auto px-6 py-5">
          {#if leadDetailLoading}
            <div class="space-y-4 animate-pulse">
              <div class="h-16 rounded-lg bg-neutral-100"></div>
              <div class="h-12 rounded-lg bg-neutral-100"></div>
              <div class="h-48 rounded-lg bg-neutral-100"></div>
              <div class="h-48 rounded-lg bg-neutral-100"></div>
            </div>
          {:else if leadDetailError || !leadDetail}
            <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-5">
              <p class="text-sm text-neutral-600">{leadDetailError || "Could not load lead details."}</p>
            </div>
          {:else}
            <div class="space-y-5">
              <div class="rounded-xl border border-neutral-200 bg-white p-5">
                <div class="flex items-center">
                  {#each leadPipelineStages as stage, i}
                    {@const isCompleted = i <= leadCurrentStageIndex}
                    {@const isCurrent = i === leadCurrentStageIndex}
                    {@const stageDate = leadDetail[leadStageDateKeys[stage.key]] as string | null}

                    {#if i > 0}
                      <div class="h-0.5 flex-1 transition-colors {i <= leadCurrentStageIndex ? 'bg-neutral-900' : 'bg-neutral-200'}"></div>
                    {/if}

                    <div class="relative flex flex-col items-center">
                      <div
                        class="flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold transition-colors
                        {isCompleted ? 'bg-neutral-900 text-white' : 'bg-neutral-200 text-neutral-400'}
                        {isCurrent ? 'ring-2 ring-neutral-900 ring-offset-2' : ''}"
                      >
                        {#if isCompleted && !isCurrent}
                          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5">
                            <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                          </svg>
                        {:else}
                          {i + 1}
                        {/if}
                      </div>
                      <span class="mt-1.5 whitespace-nowrap text-[10px] font-medium {isCompleted ? 'text-neutral-900' : 'text-neutral-400'}">
                        {stage.label}
                      </span>
                      {#if stageDate}
                        <span class="mt-0.5 whitespace-nowrap text-[9px] text-neutral-400">
                          {formatLeadDate(stageDate)}
                        </span>
                      {/if}
                    </div>
                  {/each}
                </div>
              </div>

              <div class="border-b border-neutral-200">
                <nav class="flex gap-6">
                  {#each leadTabs as tab}
                    <button
                      type="button"
                      onclick={() => (activeLeadTab = tab.key)}
                      class="pb-3 text-sm font-medium border-b-2 transition-colors
                      {activeLeadTab === tab.key
                        ? 'border-neutral-900 text-neutral-900'
                        : 'border-transparent text-neutral-400 hover:text-neutral-600'}"
                    >
                      {tab.label}
                    </button>
                  {/each}
                </nav>
              </div>

              {#if activeLeadTab === "overview"}
                <div class="grid gap-5 md:grid-cols-2">
                  <section class="space-y-3 rounded-xl border border-neutral-200 bg-white p-5">
                    <h3 class="text-xs font-semibold uppercase tracking-wider text-neutral-900">Contact Information</h3>
                    <div class="space-y-2 text-sm">
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Email</span><span class="text-right text-neutral-900">{leadDetail.email || "\u2014"}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Phone</span><span class="text-right text-neutral-900">{leadDetail.phone || "\u2014"}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Secondary Phone</span><span class="text-right text-neutral-900">{leadDetail.secondary_phone || "\u2014"}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Company</span><span class="text-right text-neutral-900">{leadDetail.company || "\u2014"}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Nationality</span><span class="text-right text-neutral-900">{leadDetail.nationality || "\u2014"}</span></div>
                    </div>
                  </section>

                  <section class="space-y-3 rounded-xl border border-neutral-200 bg-white p-5">
                    <h3 class="text-xs font-semibold uppercase tracking-wider text-neutral-900">Lead Details</h3>
                    <div class="space-y-2 text-sm">
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Lead Type</span><span class="text-right text-neutral-900">{leadTypeLabels[leadDetail.lead_type]}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Priority</span><span class="text-right text-neutral-900">{leadPriorityLabels[leadDetail.priority]}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Score</span><span class="text-right tabular-nums text-neutral-900">{leadDetail.score}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Source</span><span class="text-right text-neutral-900">{leadDetail.source_name || "\u2014"}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Broker</span><span class="text-right text-neutral-900">{leadDetail.broker_name || "\u2014"}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Referral</span><span class="text-right text-neutral-900">{leadDetail.referral_name || "\u2014"}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Assigned To</span><span class="text-right text-neutral-900">{leadDetail.assigned_to_name || "\u2014"}</span></div>
                    </div>
                    <div class="space-y-1">
                      <p class="text-xs text-neutral-400">Tags</p>
                      {#if leadDetail.tags.length > 0}
                        <div class="flex flex-wrap gap-1.5">
                          {#each leadDetail.tags as tag}
                            <span class="inline-flex items-center rounded-full bg-neutral-100 px-2 py-0.5 text-[11px] font-medium text-neutral-700">
                              {tag}
                            </span>
                          {/each}
                        </div>
                      {:else}
                        <p class="text-sm text-neutral-900">\u2014</p>
                      {/if}
                    </div>
                  </section>

                  <section class="space-y-3 rounded-xl border border-neutral-200 bg-white p-5">
                    <h3 class="text-xs font-semibold uppercase tracking-wider text-neutral-900">Budget & Payment</h3>
                    <div class="space-y-2 text-sm">
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Budget Min</span><span class="text-right tabular-nums text-neutral-900">{formatLeadAmount(leadDetail.budget_min)}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Budget Max</span><span class="text-right tabular-nums text-neutral-900">{formatLeadAmount(leadDetail.budget_max)}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Payment Capability</span><span class="text-right text-neutral-900">{leadPaymentCapabilityLabels[leadDetail.payment_capability]}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Preferred Locations</span><span class="text-right text-neutral-900">{leadDetail.preferred_locations.join(", ") || "\u2014"}</span></div>
                    </div>
                  </section>

                  <section class="space-y-3 rounded-xl border border-neutral-200 bg-white p-5">
                    <h3 class="text-xs font-semibold uppercase tracking-wider text-neutral-900">Key Dates</h3>
                    <div class="space-y-2 text-sm">
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Inquiry Date</span><span class="text-right text-neutral-900">{formatLeadDate(leadDetail.inquiry_date)}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Qualified Date</span><span class="text-right text-neutral-900">{formatLeadDate(leadDetail.qualified_date)}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Site Visit Date</span><span class="text-right text-neutral-900">{formatLeadDate(leadDetail.site_visit_date)}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Offer Date</span><span class="text-right text-neutral-900">{formatLeadDate(leadDetail.offer_date)}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Reservation Date</span><span class="text-right text-neutral-900">{formatLeadDate(leadDetail.reservation_date)}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">SPA Issued Date</span><span class="text-right text-neutral-900">{formatLeadDate(leadDetail.spa_issued_date)}</span></div>
                      <div class="flex justify-between gap-4"><span class="text-neutral-400">Closed Date</span><span class="text-right text-neutral-900">{formatLeadDate(leadDetail.closed_date)}</span></div>
                      <div class="flex justify-between gap-4 border-t border-neutral-100 pt-2.5"><span class="font-medium text-neutral-500">Days in Pipeline</span><span class="text-right font-semibold tabular-nums text-neutral-900">{leadDetail.days_in_pipeline}</span></div>
                    </div>
                  </section>

                  <section class="space-y-3 rounded-xl border border-neutral-200 bg-white p-5 md:col-span-2">
                    <h3 class="text-xs font-semibold uppercase tracking-wider text-neutral-900">Notes</h3>
                    <p class="whitespace-pre-line text-sm text-neutral-600">
                      {leadDetail.notes || "No notes recorded."}
                    </p>
                    {#if leadDetail.status === "lost" && leadDetail.lost_reason}
                      <div class="rounded-lg border border-neutral-100 bg-neutral-50 p-3">
                        <p class="text-xs text-neutral-400">Lost Reason</p>
                        <p class="mt-1 whitespace-pre-line text-sm text-neutral-700">{leadDetail.lost_reason}</p>
                      </div>
                    {/if}
                    {#if leadDetail.converted_customer_name}
                      <div class="rounded-lg border border-neutral-100 bg-neutral-50 p-3">
                        <p class="text-xs text-neutral-400">Converted Customer</p>
                        <p class="mt-1 text-sm font-medium text-neutral-900">{leadDetail.converted_customer_name}</p>
                      </div>
                    {/if}
                  </section>
                </div>
              {/if}

              {#if activeLeadTab === "activities"}
                {#if sortedLeadActivities.length === 0}
                  <div class="rounded-xl border border-neutral-200 bg-white p-8 text-center">
                    <p class="text-sm text-neutral-400">No activities recorded yet.</p>
                  </div>
                {:else}
                  <div class="rounded-xl border border-neutral-200 bg-white divide-y divide-neutral-100">
                    {#each sortedLeadActivities as activity}
                      <div class="p-5">
                        <div class="flex items-start justify-between gap-4">
                          <div class="min-w-0">
                            <div class="flex items-center gap-2">
                              <p class="text-sm font-medium text-neutral-900">{activity.subject}</p>
                              <span class="inline-flex items-center rounded bg-neutral-100 px-2 py-0.5 text-[10px] font-medium text-neutral-600">
                                {activity.activity_type_display}
                              </span>
                              {#if activity.is_completed}
                                <span class="inline-flex items-center rounded bg-neutral-900 px-2 py-0.5 text-[10px] font-medium text-white">
                                  Completed
                                </span>
                              {/if}
                            </div>
                            {#if activity.description}
                              <p class="mt-1 whitespace-pre-line text-sm text-neutral-500">{activity.description}</p>
                            {/if}
                            <div class="mt-2 flex flex-wrap items-center gap-3 text-xs text-neutral-400">
                              {#if activity.scheduled_at}
                                <span>Scheduled: {formatLeadDateTime(activity.scheduled_at)}</span>
                              {/if}
                              {#if activity.completed_at}
                                <span>Completed: {formatLeadDateTime(activity.completed_at)}</span>
                              {/if}
                              {#if activity.performed_by_name}
                                <span>By: {activity.performed_by_name}</span>
                              {/if}
                              <span>Logged: {formatLeadDateTime(activity.created_at)}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    {/each}
                  </div>
                {/if}
              {/if}

              {#if activeLeadTab === "preferences"}
                <div class="space-y-5">
                  <section class="rounded-xl border border-neutral-200 bg-white p-5">
                    <h3 class="mb-4 text-xs font-semibold uppercase tracking-wider text-neutral-900">Project Interests</h3>
                    {#if leadDetail.project_interests.length === 0}
                      <p class="text-sm text-neutral-400">No project interests recorded.</p>
                    {:else}
                      <div class="space-y-3">
                        {#each leadDetail.project_interests as interest}
                          <div class="rounded-lg border border-neutral-100 p-3">
                            <div class="flex items-center gap-2">
                              <p class="text-sm font-medium text-neutral-900">{interest.project_name}</p>
                              <span class="inline-flex items-center rounded px-2 py-0.5 text-[10px] font-medium
                                {interest.interest_level === 'high' ? 'bg-neutral-900 text-white' :
                                  interest.interest_level === 'medium' ? 'bg-neutral-200 text-neutral-700' :
                                  'bg-neutral-100 text-neutral-500'}"
                              >
                                {interest.interest_level}
                              </span>
                            </div>
                            {#if interest.notes}
                              <p class="mt-1 text-xs text-neutral-500">{interest.notes}</p>
                            {/if}
                            <p class="mt-1 text-xs text-neutral-400">Added {formatLeadDate(interest.created_at?.slice(0, 10))}</p>
                          </div>
                        {/each}
                      </div>
                    {/if}
                  </section>

                  <section class="rounded-xl border border-neutral-200 bg-white p-5">
                    <h3 class="mb-4 text-xs font-semibold uppercase tracking-wider text-neutral-900">Unit Preferences</h3>
                    {#if leadDetail.unit_preferences.length === 0}
                      <p class="text-sm text-neutral-400">No unit preferences recorded.</p>
                    {:else}
                      <div class="space-y-3">
                        {#each leadDetail.unit_preferences as pref}
                          <div class="rounded-lg border border-neutral-100 p-3">
                            <p class="text-sm font-medium text-neutral-900">{pref.unit_type_display || pref.unit_type}</p>
                            <div class="mt-2 grid grid-cols-2 gap-x-6 gap-y-1 text-xs">
                              {#if pref.min_bedrooms != null || pref.max_bedrooms != null}
                                <p><span class="text-neutral-400">Bedrooms:</span> <span class="text-neutral-700">{pref.min_bedrooms ?? "?"} - {pref.max_bedrooms ?? "?"}</span></p>
                              {/if}
                              {#if pref.min_area_sqft || pref.max_area_sqft}
                                <p><span class="text-neutral-400">Area:</span> <span class="text-neutral-700">{pref.min_area_sqft ?? "?"} - {pref.max_area_sqft ?? "?"} sqft</span></p>
                              {/if}
                              {#if pref.floor_preference}
                                <p><span class="text-neutral-400">Floor:</span> <span class="text-neutral-700">{pref.floor_preference}</span></p>
                              {/if}
                              {#if pref.view_preference}
                                <p><span class="text-neutral-400">View:</span> <span class="text-neutral-700">{pref.view_preference}</span></p>
                              {/if}
                            </div>
                            {#if pref.notes}
                              <p class="mt-2 text-xs text-neutral-500">{pref.notes}</p>
                            {/if}
                          </div>
                        {/each}
                      </div>
                    {/if}
                  </section>
                </div>
              {/if}

              {#if activeLeadTab === "timeline"}
                {#if sortedLeadTransitions.length === 0}
                  <div class="rounded-xl border border-neutral-200 bg-white p-8 text-center">
                    <p class="text-sm text-neutral-400">No stage transitions recorded.</p>
                  </div>
                {:else}
                  <div class="relative">
                    <div class="absolute bottom-3 left-[17px] top-3 w-px bg-neutral-200"></div>
                    <div class="space-y-0">
                      {#each sortedLeadTransitions as transition, i}
                        <div class="relative flex gap-4 pb-6">
                          <div class="relative z-10 shrink-0">
                            <div class="flex h-[35px] w-[35px] items-center justify-center rounded-full border-2 border-neutral-300 bg-white {i === 0 ? 'border-neutral-900' : ''}">
                              <svg class="h-4 w-4 {i === 0 ? 'text-neutral-900' : 'text-neutral-400'}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5" />
                              </svg>
                            </div>
                          </div>
                          <div class="min-w-0 flex-1 rounded-xl border border-neutral-200 bg-white p-4">
                            <div class="flex flex-wrap items-center gap-2">
                              <StatusBadge status={transition.from_stage} label={leadStageLabel(transition.from_stage)} />
                              <svg class="h-3.5 w-3.5 shrink-0 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                              </svg>
                              <StatusBadge status={transition.to_stage} label={leadStageLabel(transition.to_stage)} />
                            </div>
                            <div class="mt-2 flex flex-wrap items-center gap-3 text-xs text-neutral-400">
                              {#if transition.transitioned_by_name}
                                <span>By {transition.transitioned_by_name}</span>
                              {/if}
                              <span>{formatLeadDateTime(transition.transitioned_at)}</span>
                            </div>
                            {#if transition.notes}
                              <p class="mt-2 whitespace-pre-line text-xs text-neutral-500">{transition.notes}</p>
                            {/if}
                          </div>
                        </div>
                      {/each}
                    </div>
                  </div>
                {/if}
              {/if}
            </div>
          {/if}
        </div>
      </div>
    </div>
  </div>
{/if}

<svelte:window
  onkeydown={(e) => {
    if (e.key !== "Escape") return;
    if (showLeadModal) {
      closeLeadModal();
      return;
    }
    if (showDetailDrawer) {
      closeDetailDrawer();
      return;
    }
    if (showSlideOver) closeSlideOver();
  }}
/>

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

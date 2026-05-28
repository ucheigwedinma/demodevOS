<script lang="ts">
  import { ApiError, api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    FinancePaymentMethod,
    InvoiceStatus,
    MaintenanceCategory,
    PaginatedResponse,
  } from "$lib/types";

  type ServiceRequestTab = "requests" | "billing" | "collections" | "feedback";
  type ServiceRequestPriority = "low" | "medium" | "high" | "urgent";
  type ServiceRequestStatus = "open" | "acknowledged" | "in_progress" | "escalated" | "resolved" | "closed";
  type ServiceRequestSourceChannel = "web" | "mobile";
  type SupportTicketPriority = "low" | "medium" | "high" | "critical";
  type SupportTicketStatus = "open" | "in_progress" | "pending_requester" | "escalated" | "resolved" | "closed";
  type ServiceRequestSlaStatus = "on_track" | "at_risk" | "breached" | "completed" | "untracked";

  interface FacilityServiceRequestListItem {
    id: number;
    property: number;
    property_name: string;
    facility: number | null;
    facility_code: string;
    facility_space: number | null;
    unit: number | null;
    unit_number: string;
    title: string;
    description: string;
    category: MaintenanceCategory;
    category_display: string;
    priority: ServiceRequestPriority;
    priority_display: string;
    status: ServiceRequestStatus;
    status_display: string;
    source_channel: ServiceRequestSourceChannel;
    source_channel_display: string;
    requester: number | null;
    requester_name: string;
    requested_by: string;
    assigned_agent: number | null;
    assigned_agent_name: string;
    assigned_to: string;
    requested_date: string;
    first_response_at: string | null;
    sla_target_hours: number | null;
    sla_due_at: string | null;
    sla_status: ServiceRequestSlaStatus;
    escalated_at: string | null;
    resolved_date: string | null;
    feedback_rating: number | null;
    location_label: string;
    work_order: number | null;
    work_order_status: string;
    created_at: string;
    updated_at: string;
  }

  interface FacilityBillingTicketListItem {
    id: number;
    ticket_id: string;
    subject: string;
    description: string;
    customer: number | null;
    customer_name: string;
    invoice: number | null;
    invoice_number: string;
    property_name: string;
    requester: number | null;
    requester_name: string;
    assigned_agent: number | null;
    assigned_agent_name: string;
    priority: SupportTicketPriority;
    priority_display: string;
    status: SupportTicketStatus;
    status_display: string;
    sla_deadline: string | null;
    escalated_at: string | null;
    resolved_at: string | null;
    closed_at: string | null;
    sla_breached: boolean;
    created_at: string;
    updated_at: string;
  }

  interface FacilityInvoiceListItem {
    id: number;
    invoice_number: string;
    customer: number | null;
    customer_name: string;
    property: number | null;
    property_name: string;
    status: InvoiceStatus;
    issue_date: string;
    due_date: string;
    total_amount: string;
    paid_amount: string;
    balance_due: string;
    created_at: string;
    updated_at: string;
    open_billing_ticket_count: number;
  }

  interface ServiceRequestOverview {
    generated_at: string;
    kpis: {
      open_requests: number;
      escalated_requests: number;
      sla_at_risk: number;
      avg_feedback_rating: number | null;
      open_billing_tickets: number;
      overdue_invoices: number;
      outstanding_balance: string;
    };
    service_request_watchlist: FacilityServiceRequestListItem[];
    billing_watchlist: FacilityBillingTicketListItem[];
    overdue_invoice_watchlist: FacilityInvoiceListItem[];
  }

  interface WorkflowSyncResult {
    service_requests_synced: number;
    service_requests_escalated: number;
    work_orders_created: number;
    overdue_invoices_flagged: number;
    billing_tickets_synced: number;
    billing_tickets_escalated: number;
    billing_tickets_resolved: number;
  }

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

  interface LookupCustomerItem {
    id: number;
    label: string;
    email: string;
    phone: string;
  }

  interface ServiceRequestLookupsResponse {
    users: LookupUserItem[];
    facilities: LookupFacilityItem[];
    spaces: LookupSpaceItem[];
    customers: LookupCustomerItem[];
    invoices: FacilityInvoiceListItem[];
  }

  const tabs: { key: ServiceRequestTab; label: string }[] = [
    { key: "requests", label: "Service Requests" },
    { key: "billing", label: "Billing Helpdesk" },
    { key: "collections", label: "Collections" },
    { key: "feedback", label: "Feedback & Ratings" },
  ];

  const categoryOptions: { value: MaintenanceCategory; label: string }[] = [
    { value: "electrical", label: "Electrical" },
    { value: "plumbing", label: "Plumbing" },
    { value: "hvac", label: "HVAC" },
    { value: "cleaning", label: "Cleaning" },
    { value: "security", label: "Security" },
    { value: "mechanical", label: "Mechanical" },
    { value: "generator", label: "Generators" },
    { value: "fire_safety", label: "Fire Safety" },
    { value: "general", label: "General" },
  ];

  const requestPriorityOptions: { value: ServiceRequestPriority; label: string }[] = [
    { value: "urgent", label: "Urgent" },
    { value: "high", label: "High" },
    { value: "medium", label: "Medium" },
    { value: "low", label: "Low" },
  ];

  const sourceChannelOptions: { value: ServiceRequestSourceChannel; label: string }[] = [
    { value: "web", label: "Web" },
    { value: "mobile", label: "Mobile" },
  ];

  const billingPriorityOptions: { value: SupportTicketPriority; label: string }[] = [
    { value: "critical", label: "Critical" },
    { value: "high", label: "High" },
    { value: "medium", label: "Medium" },
    { value: "low", label: "Low" },
  ];

  const paymentMethodOptions: { value: FinancePaymentMethod; label: string }[] = [
    { value: "bank_transfer", label: "Bank Transfer" },
    { value: "check", label: "Check" },
    { value: "cash", label: "Cash" },
    { value: "credit_card", label: "Credit Card" },
    { value: "other", label: "Other" },
  ];

  let activeTab = $state<ServiceRequestTab>("requests");
  let loading = $state(true);
  let refreshing = $state(false);
  let syncingWorkflows = $state(false);

  let overview = $state<ServiceRequestOverview | null>(null);
  let serviceRequests = $state<FacilityServiceRequestListItem[]>([]);
  let billingTickets = $state<FacilityBillingTicketListItem[]>([]);
  let invoices = $state<FacilityInvoiceListItem[]>([]);

  let usersLookup = $state<LookupUserItem[]>([]);
  let facilitiesLookup = $state<LookupFacilityItem[]>([]);
  let spacesLookup = $state<LookupSpaceItem[]>([]);
  let invoicesLookup = $state<FacilityInvoiceListItem[]>([]);

  let requestSearch = $state("");
  let requestFacilityFilter = $state("");
  let requestStatusFilter = $state("");
  let requestPriorityFilter = $state("");

  let billingSearch = $state("");
  let billingStatusFilter = $state("");
  let billingPriorityFilter = $state("");

  let collectionSearch = $state("");
  let collectionStatusFilter = $state("");

  let showServiceRequestDrawer = $state(false);
  let showBillingTicketDrawer = $state(false);
  let showPaymentDrawer = $state(false);
  let showFeedbackDrawer = $state(false);

  let serviceRequestSaving = $state(false);
  let billingTicketSaving = $state(false);
  let paymentSaving = $state(false);
  let feedbackSaving = $state(false);
  let escalatingRequestId = $state<number | null>(null);

  let serviceRequestForm = $state({
    facility: "",
    facility_space: "",
    title: "",
    description: "",
    category: "general" as MaintenanceCategory,
    priority: "medium" as ServiceRequestPriority,
    source_channel: "web" as ServiceRequestSourceChannel,
    assigned_agent: "",
  });

  let billingTicketForm = $state({
    invoice: "",
    subject: "",
    description: "",
    priority: "medium" as SupportTicketPriority,
    assigned_agent: "",
  });

  let paymentForm = $state({
    invoiceId: null as number | null,
    invoice_number: "",
    amount: "",
    payment_date: todayInput(),
    payment_method: "bank_transfer" as FinancePaymentMethod,
    reference_number: "",
    notes: "",
  });

  let feedbackForm = $state({
    requestId: null as number | null,
    requestTitle: "",
    feedback_rating: "5",
    feedback_comment: "",
  });

  function todayInput(): string {
    return new Date().toISOString().slice(0, 10);
  }

  function toNumber(value: unknown): number {
    const parsed = Number(value ?? 0);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function fmtInt(value: unknown): string {
    return toNumber(value).toLocaleString("en-US");
  }

  function fmtMoney(value: string | number | null | undefined): string {
    const amount = toNumber(value);
    return amount.toLocaleString("en-US", {
      style: "currency",
      currency: "NGN",
      maximumFractionDigits: 2,
    });
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
      const fieldMessage = Object.values(error.fieldErrors).flat().join(" ");
      if (fieldMessage) return fieldMessage;
    }
    return fallback;
  }

  function requestStatusClass(statusValue: string): string {
    switch (statusValue) {
      case "resolved":
      case "closed":
        return "bg-emerald-50 text-emerald-700";
      case "escalated":
        return "bg-red-50 text-red-700";
      case "in_progress":
      case "acknowledged":
        return "bg-blue-50 text-blue-700";
      default:
        return "bg-amber-50 text-amber-700";
    }
  }

  function billingStatusClass(statusValue: string): string {
    switch (statusValue) {
      case "resolved":
      case "closed":
        return "bg-emerald-50 text-emerald-700";
      case "escalated":
        return "bg-red-50 text-red-700";
      case "in_progress":
        return "bg-blue-50 text-blue-700";
      case "pending_requester":
        return "bg-amber-50 text-amber-700";
      default:
        return "bg-neutral-100 text-neutral-700";
    }
  }

  function priorityClass(priorityValue: string): string {
    switch (priorityValue) {
      case "urgent":
      case "critical":
        return "bg-red-50 text-red-700";
      case "high":
        return "bg-orange-50 text-orange-700";
      case "medium":
        return "bg-amber-50 text-amber-700";
      default:
        return "bg-neutral-100 text-neutral-700";
    }
  }

  function invoiceStatusClass(statusValue: InvoiceStatus): string {
    switch (statusValue) {
      case "paid":
        return "bg-emerald-50 text-emerald-700";
      case "overdue":
        return "bg-red-50 text-red-700";
      case "sent":
        return "bg-amber-50 text-amber-700";
      case "cancelled":
        return "bg-neutral-100 text-neutral-700";
      default:
        return "bg-blue-50 text-blue-700";
    }
  }

  function slaStatusClass(statusValue: ServiceRequestSlaStatus): string {
    switch (statusValue) {
      case "breached":
        return "bg-red-50 text-red-700";
      case "at_risk":
        return "bg-amber-50 text-amber-700";
      case "completed":
        return "bg-emerald-50 text-emerald-700";
      default:
        return "bg-neutral-100 text-neutral-700";
    }
  }

  function filteredSpacesFor(facilityId: string): LookupSpaceItem[] {
    if (!facilityId) return spacesLookup;
    const normalized = Number(facilityId);
    return spacesLookup.filter((space) => space.facility === normalized);
  }

  function selectedLookupInvoice(): FacilityInvoiceListItem | null {
    const invoiceId = Number(billingTicketForm.invoice);
    if (!invoiceId) return null;
    return invoicesLookup.find((invoice) => invoice.id === invoiceId) ?? null;
  }

  function requestsForFeedback(): FacilityServiceRequestListItem[] {
    return serviceRequests.filter((request) => request.status === "resolved" || request.status === "closed");
  }

  function filteredServiceRequests(): FacilityServiceRequestListItem[] {
    const searchValue = requestSearch.trim().toLowerCase();
    return serviceRequests.filter((request) => {
      if (requestFacilityFilter && String(request.facility ?? "") !== requestFacilityFilter) return false;
      if (requestStatusFilter && request.status !== requestStatusFilter) return false;
      if (requestPriorityFilter && request.priority !== requestPriorityFilter) return false;
      if (!searchValue) return true;
      return [
        request.title,
        request.description,
        request.facility_code,
        request.location_label,
        request.requester_name,
        request.assigned_agent_name,
      ]
        .join(" ")
        .toLowerCase()
        .includes(searchValue);
    });
  }

  function filteredBillingTickets(): FacilityBillingTicketListItem[] {
    const searchValue = billingSearch.trim().toLowerCase();
    return billingTickets.filter((ticket) => {
      if (billingStatusFilter && ticket.status !== billingStatusFilter) return false;
      if (billingPriorityFilter && ticket.priority !== billingPriorityFilter) return false;
      if (!searchValue) return true;
      return [
        ticket.ticket_id,
        ticket.subject,
        ticket.customer_name,
        ticket.invoice_number,
        ticket.property_name,
      ]
        .join(" ")
        .toLowerCase()
        .includes(searchValue);
    });
  }

  function filteredInvoices(): FacilityInvoiceListItem[] {
    const searchValue = collectionSearch.trim().toLowerCase();
    return invoices.filter((invoice) => {
      if (collectionStatusFilter && invoice.status !== collectionStatusFilter) return false;
      if (!searchValue) return true;
      return [
        invoice.invoice_number,
        invoice.customer_name,
        invoice.property_name,
      ]
        .join(" ")
        .toLowerCase()
        .includes(searchValue);
    });
  }

  function resetServiceRequestForm() {
    serviceRequestForm = {
      facility: "",
      facility_space: "",
      title: "",
      description: "",
      category: "general",
      priority: "medium",
      source_channel: "web",
      assigned_agent: "",
    };
  }

  function resetBillingTicketForm() {
    billingTicketForm = {
      invoice: "",
      subject: "",
      description: "",
      priority: "medium",
      assigned_agent: "",
    };
  }

  function resetPaymentForm(invoice?: FacilityInvoiceListItem | null) {
    paymentForm = {
      invoiceId: invoice?.id ?? null,
      invoice_number: invoice?.invoice_number ?? "",
      amount: invoice?.balance_due ?? "",
      payment_date: todayInput(),
      payment_method: "bank_transfer",
      reference_number: "",
      notes: "",
    };
  }

  function resetFeedbackForm(request?: FacilityServiceRequestListItem | null) {
    feedbackForm = {
      requestId: request?.id ?? null,
      requestTitle: request?.title ?? "",
      feedback_rating: request?.feedback_rating ? String(request.feedback_rating) : "5",
      feedback_comment: "",
    };
  }

  async function fetchOverview() {
    overview = await api.get<ServiceRequestOverview>("/facility-management/service-requests/overview/");
  }

  async function fetchServiceRequests() {
    const response = await api.get<PaginatedResponse<FacilityServiceRequestListItem>>(
      "/facility-management/service-requests/requests/",
      { page_size: "200" },
    );
    serviceRequests = response.results;
  }

  async function fetchBillingTickets() {
    const response = await api.get<PaginatedResponse<FacilityBillingTicketListItem>>(
      "/facility-management/service-requests/billing-tickets/",
      { page_size: "200" },
    );
    billingTickets = response.results;
  }

  async function fetchInvoices() {
    const response = await api.get<PaginatedResponse<FacilityInvoiceListItem>>(
      "/facility-management/service-requests/invoices/",
      { page_size: "200" },
    );
    invoices = response.results;
  }

  async function fetchLookups() {
    const response = await api.get<ServiceRequestLookupsResponse>("/facility-management/service-requests/lookups/");
    usersLookup = response.users;
    facilitiesLookup = response.facilities;
    spacesLookup = response.spaces;
    invoicesLookup = response.invoices;
  }

  async function syncWorkflows(options: { silent?: boolean } = {}): Promise<WorkflowSyncResult | null> {
    syncingWorkflows = true;
    try {
      const result = await api.post<WorkflowSyncResult>("/facility-management/service-requests/sync/", {});
      if (!options.silent) {
        toast.success(
          "Workflows completed",
          [
            `${result.service_requests_escalated} requests escalated`,
            `${result.work_orders_created} work orders created`,
            `${result.billing_tickets_resolved} billing tickets resolved`,
          ].join(" • "),
        );
      }
      return result;
    } catch (error) {
      if (!options.silent) {
        toast.error("Workflow run failed", parseApiMessage(error, "The workflow engine could not be executed."));
      }
      return null;
    } finally {
      syncingWorkflows = false;
    }
  }

  async function refreshAll() {
    if (!loading) refreshing = true;
    try {
      await Promise.all([
        fetchOverview(),
        fetchServiceRequests(),
        fetchBillingTickets(),
        fetchInvoices(),
        fetchLookups(),
      ]);
    } catch {
      overview = null;
      toast.error("Load failed", "Could not load service requests and bill payments.");
    } finally {
      loading = false;
      refreshing = false;
    }
  }

  async function handleRunWorkflows() {
    const result = await syncWorkflows();
    if (result) {
      await refreshAll();
    }
  }

  function openServiceRequestDrawer() {
    resetServiceRequestForm();
    showServiceRequestDrawer = true;
    void fetchLookups();
  }

  function closeServiceRequestDrawer() {
    showServiceRequestDrawer = false;
    resetServiceRequestForm();
  }

  function openBillingTicketDrawer() {
    resetBillingTicketForm();
    showBillingTicketDrawer = true;
    void fetchLookups();
  }

  function closeBillingTicketDrawer() {
    showBillingTicketDrawer = false;
    resetBillingTicketForm();
  }

  function openPaymentDrawer(invoice: FacilityInvoiceListItem) {
    resetPaymentForm(invoice);
    showPaymentDrawer = true;
  }

  function closePaymentDrawer() {
    showPaymentDrawer = false;
    resetPaymentForm();
  }

  function openFeedbackDrawer(request: FacilityServiceRequestListItem) {
    resetFeedbackForm(request);
    showFeedbackDrawer = true;
  }

  function closeFeedbackDrawer() {
    showFeedbackDrawer = false;
    resetFeedbackForm();
  }

  async function handleServiceRequestCreate(event: SubmitEvent) {
    event.preventDefault();
    if (!serviceRequestForm.title.trim()) {
      toast.error("Missing data", "Service request title is required.");
      return;
    }
    if (!serviceRequestForm.facility && !serviceRequestForm.facility_space) {
      toast.error("Missing data", "Select a facility or mapped room / space.");
      return;
    }

    serviceRequestSaving = true;
    try {
      await api.post("/facility-management/service-requests/requests/", {
        facility: serviceRequestForm.facility ? Number(serviceRequestForm.facility) : null,
        facility_space: serviceRequestForm.facility_space ? Number(serviceRequestForm.facility_space) : null,
        title: serviceRequestForm.title.trim(),
        description: serviceRequestForm.description.trim(),
        category: serviceRequestForm.category,
        priority: serviceRequestForm.priority,
        source_channel: serviceRequestForm.source_channel,
        assigned_agent: serviceRequestForm.assigned_agent ? Number(serviceRequestForm.assigned_agent) : null,
      });

      closeServiceRequestDrawer();
      toast.success("Service request logged", "The request was created and corrective workflow automation was applied.");
      await refreshAll();
    } catch (error) {
      toast.error("Create failed", parseApiMessage(error, "Could not create the service request."));
    } finally {
      serviceRequestSaving = false;
    }
  }

  async function handleBillingTicketCreate(event: SubmitEvent) {
    event.preventDefault();
    if (!billingTicketForm.invoice) {
      toast.error("Missing data", "Select an invoice for the billing ticket.");
      return;
    }
    if (!billingTicketForm.subject.trim()) {
      toast.error("Missing data", "Billing ticket subject is required.");
      return;
    }

    billingTicketSaving = true;
    try {
      await api.post("/facility-management/service-requests/billing-tickets/", {
        invoice: Number(billingTicketForm.invoice),
        subject: billingTicketForm.subject.trim(),
        description: billingTicketForm.description.trim(),
        priority: billingTicketForm.priority,
        assigned_agent: billingTicketForm.assigned_agent ? Number(billingTicketForm.assigned_agent) : null,
      });

      closeBillingTicketDrawer();
      toast.success("Billing ticket created", "The helpdesk ticket was logged and SLA tracking is active.");
      await refreshAll();
    } catch (error) {
      toast.error("Create failed", parseApiMessage(error, "Could not create the billing helpdesk ticket."));
    } finally {
      billingTicketSaving = false;
    }
  }

  async function handleRecordPayment(event: SubmitEvent) {
    event.preventDefault();
    if (!paymentForm.invoiceId) {
      toast.error("Missing data", "Choose an invoice to record payment against.");
      return;
    }
    if (!paymentForm.amount || Number(paymentForm.amount) <= 0) {
      toast.error("Missing data", "Payment amount must be greater than zero.");
      return;
    }

    paymentSaving = true;
    try {
      const result = await api.post<{
        detail: string;
        billing_tickets_resolved: number;
        invoice: FacilityInvoiceListItem;
      }>(
        `/facility-management/service-requests/invoices/${paymentForm.invoiceId}/record-payment/`,
        {
          amount: paymentForm.amount,
          payment_date: paymentForm.payment_date,
          payment_method: paymentForm.payment_method,
          reference_number: paymentForm.reference_number.trim(),
          notes: paymentForm.notes.trim(),
        },
      );

      closePaymentDrawer();
      toast.success(
        "Payment recorded",
        `${result.invoice.invoice_number} updated. ${result.billing_tickets_resolved} billing tickets resolved.`,
      );
      await refreshAll();
    } catch (error) {
      toast.error("Payment failed", parseApiMessage(error, "Could not record invoice payment."));
    } finally {
      paymentSaving = false;
    }
  }

  async function handleEscalateRequest(request: FacilityServiceRequestListItem) {
    escalatingRequestId = request.id;
    try {
      await api.post(`/facility-management/service-requests/requests/${request.id}/escalate/`, {});
      toast.success("Request escalated", `${request.title} has been escalated.`);
      await refreshAll();
    } catch (error) {
      toast.error("Escalation failed", parseApiMessage(error, "Could not escalate the service request."));
    } finally {
      escalatingRequestId = null;
    }
  }

  async function handleFeedbackSubmit(event: SubmitEvent) {
    event.preventDefault();
    if (!feedbackForm.requestId) {
      toast.error("Missing data", "Select a resolved request first.");
      return;
    }

    feedbackSaving = true;
    try {
      await api.post(
        `/facility-management/service-requests/requests/${feedbackForm.requestId}/feedback/`,
        {
          feedback_rating: Number(feedbackForm.feedback_rating),
          feedback_comment: feedbackForm.feedback_comment.trim(),
        },
      );

      closeFeedbackDrawer();
      toast.success("Feedback saved", "The service request rating has been recorded.");
      await refreshAll();
    } catch (error) {
      toast.error("Feedback failed", parseApiMessage(error, "Could not save service request feedback."));
    } finally {
      feedbackSaving = false;
    }
  }

  $effect(() => {
    if (!serviceRequestForm.facility_space) return;
    const selectedSpace = spacesLookup.find((space) => space.id === Number(serviceRequestForm.facility_space));
    if (!selectedSpace) return;
    if (serviceRequestForm.facility !== String(selectedSpace.facility)) {
      serviceRequestForm.facility = String(selectedSpace.facility);
    }
  });

  $effect(() => {
    if (!serviceRequestForm.facility || !serviceRequestForm.facility_space) return;
    const selectedSpace = spacesLookup.find((space) => space.id === Number(serviceRequestForm.facility_space));
    if (selectedSpace && String(selectedSpace.facility) !== serviceRequestForm.facility) {
      serviceRequestForm.facility_space = "";
    }
  });

  $effect(() => {
    refreshAll();
  });
</script>

<div class="space-y-6">
  <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-indigo-600">Facility Management</p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-900">Service Requests & Bill Payments</h1>
      <p class="mt-1 max-w-3xl text-sm text-neutral-500">
        Streamlined service request tracking and secure payments for tenants.
      </p>
      {#if overview?.generated_at}
        <p class="mt-1 text-xs text-neutral-400">Last refreshed: {fmtDateTime(overview.generated_at)}</p>
      {/if}
    </div>

    <div class="flex items-center gap-3 self-start lg:self-auto">
      <button
        type="button"
        onclick={handleRunWorkflows}
        disabled={syncingWorkflows}
        class="inline-flex items-center gap-2 rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        <svg
          class={`h-4 w-4 ${syncingWorkflows ? "animate-spin" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          stroke-width="1.8"
          aria-hidden="true"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12a7.5 7.5 0 0 1 12.47-5.606M19.5 12a7.5 7.5 0 0 1-12.47 5.606M16.5 3.75h.75A2.25 2.25 0 0 1 19.5 6v.75m-15 10.5H3.75A2.25 2.25 0 0 1 1.5 15v-.75" />
        </svg>
        {syncingWorkflows ? "Running Workflows..." : "Run Workflows"}
      </button>

      <button
        type="button"
        onclick={refreshAll}
        disabled={refreshing}
        class="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-neutral-300 bg-white text-neutral-700 transition-colors hover:border-neutral-900 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-60"
        aria-label={refreshing ? "Refreshing service requests and bill payments" : "Refresh service requests and bill payments"}
        title={refreshing ? "Refreshing service requests and bill payments" : "Refresh service requests and bill payments"}
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
      Loading service request operations...
    </div>
  {:else if !overview}
    <div class="rounded-2xl border border-red-200 bg-red-50 p-6 text-sm text-red-700">
      Service requests and bill payments are unavailable right now.
    </div>
  {:else}
    <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
      <section class="rounded-2xl border border-blue-200 bg-blue-50 p-5">
        <p class="text-xs font-semibold uppercase tracking-wide text-blue-700">Open Requests</p>
        <p class="mt-3 text-2xl font-semibold text-blue-900">{fmtInt(overview.kpis.open_requests)}</p>
      </section>

      <section class="rounded-2xl border border-red-200 bg-red-50 p-5">
        <p class="text-xs font-semibold uppercase tracking-wide text-red-700">Escalated Requests</p>
        <p class="mt-3 text-2xl font-semibold text-red-900">{fmtInt(overview.kpis.escalated_requests)}</p>
      </section>

      <section class="rounded-2xl border border-amber-200 bg-amber-50 p-5">
        <p class="text-xs font-semibold uppercase tracking-wide text-amber-700">SLA At Risk</p>
        <p class="mt-3 text-2xl font-semibold text-amber-900">{fmtInt(overview.kpis.sla_at_risk)}</p>
      </section>

      <section class="rounded-2xl border border-teal-200 bg-teal-50 p-5">
        <p class="text-xs font-semibold uppercase tracking-wide text-teal-700">Feedback Score</p>
        <p class="mt-3 text-2xl font-semibold text-teal-900">
          {overview.kpis.avg_feedback_rating === null ? "--" : overview.kpis.avg_feedback_rating.toFixed(1)}
        </p>
      </section>

      <section class="rounded-2xl border border-orange-200 bg-orange-50 p-5">
        <p class="text-xs font-semibold uppercase tracking-wide text-orange-700">Open Billing Tickets</p>
        <p class="mt-3 text-2xl font-semibold text-orange-900">{fmtInt(overview.kpis.open_billing_tickets)}</p>
      </section>

      <section class="rounded-2xl border border-emerald-200 bg-emerald-50 p-5">
        <p class="text-xs font-semibold uppercase tracking-wide text-emerald-700">Outstanding Balance</p>
        <p class="mt-3 text-2xl font-semibold text-emerald-900">{fmtMoney(overview.kpis.outstanding_balance)}</p>
        <p class="mt-2 text-xs text-emerald-800">{fmtInt(overview.kpis.overdue_invoices)} overdue invoices</p>
      </section>
    </div>

    <div class="grid gap-4 xl:grid-cols-3">
      <section class="rounded-2xl border border-neutral-200 bg-white p-5">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Request Watchlist</h2>
            <p class="text-xs text-neutral-500">Requests needing attention first</p>
          </div>
          <button type="button" onclick={() => (activeTab = "requests")} class="text-xs font-medium text-neutral-500 hover:text-neutral-900">
            Open Tab
          </button>
        </div>
        <div class="mt-4 space-y-3">
          {#if overview.service_request_watchlist.length === 0}
            <p class="rounded-xl border border-dashed border-neutral-200 bg-neutral-50 p-4 text-sm text-neutral-500">
              No active requests need immediate attention.
            </p>
          {:else}
            {#each overview.service_request_watchlist as request}
              <article class="rounded-xl border border-neutral-200 p-3">
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <p class="text-sm font-semibold text-neutral-900">{request.title}</p>
                    <p class="mt-1 text-xs text-neutral-500">{request.facility_code} • {request.location_label || "No room mapping"}</p>
                  </div>
                  <span class={`rounded-full px-2 py-1 text-[11px] font-semibold ${requestStatusClass(request.status)}`}>
                    {request.status_display}
                  </span>
                </div>
                <div class="mt-3 flex flex-wrap gap-2 text-[11px] text-neutral-500">
                  <span class={`rounded-full px-2 py-1 font-semibold ${priorityClass(request.priority)}`}>{request.priority_display}</span>
                  <span class={`rounded-full px-2 py-1 font-semibold ${slaStatusClass(request.sla_status)}`}>{fmtLabel(request.sla_status)}</span>
                  <span class="rounded-full bg-neutral-100 px-2 py-1 font-semibold text-neutral-700">
                    WO {request.work_order ? `#${request.work_order}` : "Pending"}
                  </span>
                </div>
              </article>
            {/each}
          {/if}
        </div>
      </section>

      <section class="rounded-2xl border border-neutral-200 bg-white p-5">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Billing Watchlist</h2>
            <p class="text-xs text-neutral-500">Tenant-facing billing tickets surfaced for ops</p>
          </div>
          <button type="button" onclick={() => (activeTab = "billing")} class="text-xs font-medium text-neutral-500 hover:text-neutral-900">
            Open Tab
          </button>
        </div>
        <div class="mt-4 space-y-3">
          {#if overview.billing_watchlist.length === 0}
            <p class="rounded-xl border border-dashed border-neutral-200 bg-neutral-50 p-4 text-sm text-neutral-500">
              No open billing tickets right now.
            </p>
          {:else}
            {#each overview.billing_watchlist as ticket}
              <article class="rounded-xl border border-neutral-200 p-3">
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <p class="text-sm font-semibold text-neutral-900">{ticket.subject}</p>
                    <p class="mt-1 text-xs text-neutral-500">{ticket.customer_name} • {ticket.invoice_number}</p>
                  </div>
                  <span class={`rounded-full px-2 py-1 text-[11px] font-semibold ${billingStatusClass(ticket.status)}`}>
                    {ticket.status_display}
                  </span>
                </div>
                <div class="mt-3 flex flex-wrap gap-2 text-[11px] text-neutral-500">
                  <span class={`rounded-full px-2 py-1 font-semibold ${priorityClass(ticket.priority)}`}>{ticket.priority_display}</span>
                  <span class="rounded-full bg-neutral-100 px-2 py-1 font-semibold text-neutral-700">
                    Due {fmtDateTime(ticket.sla_deadline)}
                  </span>
                </div>
              </article>
            {/each}
          {/if}
        </div>
      </section>

      <section class="rounded-2xl border border-neutral-200 bg-white p-5">
        <div class="flex items-center justify-between">
          <div>
            <h2 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Overdue Invoices</h2>
            <p class="text-xs text-neutral-500">Collections queue with open balances</p>
          </div>
          <button type="button" onclick={() => (activeTab = "collections")} class="text-xs font-medium text-neutral-500 hover:text-neutral-900">
            Open Tab
          </button>
        </div>
        <div class="mt-4 space-y-3">
          {#if overview.overdue_invoice_watchlist.length === 0}
            <p class="rounded-xl border border-dashed border-neutral-200 bg-neutral-50 p-4 text-sm text-neutral-500">
              No overdue invoices at the moment.
            </p>
          {:else}
            {#each overview.overdue_invoice_watchlist as invoice}
              <article class="rounded-xl border border-neutral-200 p-3">
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <p class="text-sm font-semibold text-neutral-900">{invoice.invoice_number}</p>
                    <p class="mt-1 text-xs text-neutral-500">{invoice.customer_name} • {invoice.property_name}</p>
                  </div>
                  <span class={`rounded-full px-2 py-1 text-[11px] font-semibold ${invoiceStatusClass(invoice.status)}`}>
                    {fmtLabel(invoice.status)}
                  </span>
                </div>
                <div class="mt-3 flex items-center justify-between text-xs text-neutral-500">
                  <span>Due {fmtDate(invoice.due_date)}</span>
                  <span class="font-semibold text-emerald-700">{fmtMoney(invoice.balance_due)}</span>
                </div>
              </article>
            {/each}
          {/if}
        </div>
      </section>
    </div>

    <div class="rounded-2xl border border-neutral-200 bg-white p-2">
      <div class="flex flex-wrap gap-2">
        {#each tabs as tab}
          <button
            type="button"
            onclick={() => (activeTab = tab.key)}
            class={`rounded-xl px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? "bg-neutral-900 text-white"
                : "text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900"
            }`}
          >
            {tab.label}
          </button>
        {/each}
      </div>
    </div>

    {#if activeTab === "requests"}
      <section class="rounded-2xl border border-neutral-200 bg-white p-5">
        <div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h2 class="text-lg font-semibold text-neutral-900">Internal Service Requests</h2>
            <p class="mt-1 text-sm text-neutral-500">
              For app users and company employees. Each request can auto-create and sync a corrective work order.
            </p>
          </div>
          <button
            type="button"
            onclick={openServiceRequestDrawer}
            class="inline-flex items-center gap-2 rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-neutral-800"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            Log Service Request
          </button>
        </div>

        <div class="mt-4 grid gap-3 md:grid-cols-4">
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Search</span>
            <input bind:value={requestSearch} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Title, facility, requester..." />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Facility</span>
            <select bind:value={requestFacilityFilter} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="">All facilities</option>
              {#each facilitiesLookup as facility}
                <option value={String(facility.id)}>{facility.facility_code}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Status</span>
            <select bind:value={requestStatusFilter} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="">All statuses</option>
              <option value="open">Open</option>
              <option value="acknowledged">Acknowledged</option>
              <option value="in_progress">In Progress</option>
              <option value="escalated">Escalated</option>
              <option value="resolved">Resolved</option>
              <option value="closed">Closed</option>
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Priority</span>
            <select bind:value={requestPriorityFilter} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="">All priorities</option>
              {#each requestPriorityOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </label>
        </div>

        <div class="mt-5 overflow-x-auto">
          <table class="min-w-full divide-y divide-neutral-200 text-left text-sm">
            <thead class="bg-neutral-50 text-xs uppercase tracking-wide text-neutral-500">
              <tr>
                <th class="px-4 py-3">Request</th>
                <th class="px-4 py-3">Location</th>
                <th class="px-4 py-3">Requester</th>
                <th class="px-4 py-3">Priority</th>
                <th class="px-4 py-3">SLA</th>
                <th class="px-4 py-3">Status</th>
                <th class="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-200">
              {#if filteredServiceRequests().length === 0}
                <tr>
                  <td colspan="7" class="px-4 py-10 text-center text-sm text-neutral-500">No service requests match the current filters.</td>
                </tr>
              {:else}
                {#each filteredServiceRequests() as request}
                  <tr class="align-top">
                    <td class="px-4 py-4">
                      <p class="font-semibold text-neutral-900">{request.title}</p>
                      <p class="mt-1 text-xs text-neutral-500">{request.category_display} • {request.source_channel_display}</p>
                      {#if request.work_order}
                        <p class="mt-1 text-xs text-neutral-400">Work order #{request.work_order} • {fmtLabel(request.work_order_status || "pending")}</p>
                      {/if}
                    </td>
                    <td class="px-4 py-4 text-neutral-600">
                      <p>{request.facility_code || "--"}</p>
                      <p class="mt-1 text-xs text-neutral-500">{request.location_label || request.unit_number || "No room mapping"}</p>
                    </td>
                    <td class="px-4 py-4 text-neutral-600">
                      <p>{request.requester_name || request.requested_by || "--"}</p>
                      <p class="mt-1 text-xs text-neutral-500">{request.assigned_agent_name || "Unassigned"}</p>
                    </td>
                    <td class="px-4 py-4">
                      <span class={`rounded-full px-2 py-1 text-[11px] font-semibold ${priorityClass(request.priority)}`}>
                        {request.priority_display}
                      </span>
                    </td>
                    <td class="px-4 py-4 text-neutral-600">
                      <span class={`inline-flex rounded-full px-2 py-1 text-[11px] font-semibold ${slaStatusClass(request.sla_status)}`}>
                        {fmtLabel(request.sla_status)}
                      </span>
                      <p class="mt-1 text-xs text-neutral-500">{fmtDateTime(request.sla_due_at)}</p>
                    </td>
                    <td class="px-4 py-4">
                      <span class={`rounded-full px-2 py-1 text-[11px] font-semibold ${requestStatusClass(request.status)}`}>
                        {request.status_display}
                      </span>
                      {#if request.feedback_rating}
                        <p class="mt-1 text-xs text-neutral-500">Rating {request.feedback_rating}/5</p>
                      {/if}
                    </td>
                    <td class="px-4 py-4">
                      <div class="flex flex-wrap gap-2">
                        {#if !["escalated", "resolved", "closed"].includes(request.status)}
                          <button
                            type="button"
                            onclick={() => handleEscalateRequest(request)}
                            disabled={escalatingRequestId === request.id}
                            class="rounded-lg border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-700 transition-colors hover:bg-neutral-50 disabled:opacity-60"
                          >
                            {escalatingRequestId === request.id ? "Escalating..." : "Escalate"}
                          </button>
                        {/if}
                        {#if ["resolved", "closed"].includes(request.status)}
                          <button
                            type="button"
                            onclick={() => openFeedbackDrawer(request)}
                            class="rounded-lg border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-700 transition-colors hover:bg-neutral-50"
                          >
                            {request.feedback_rating ? "Update Feedback" : "Add Feedback"}
                          </button>
                        {/if}
                      </div>
                    </td>
                  </tr>
                {/each}
              {/if}
            </tbody>
          </table>
        </div>
      </section>
    {:else if activeTab === "billing"}
      <section class="rounded-2xl border border-neutral-200 bg-white p-5">
        <div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h2 class="text-lg font-semibold text-neutral-900">Billing Helpdesk Integration</h2>
            <p class="mt-1 text-sm text-neutral-500">
              Customer-facing billing issues stay in the helpdesk module, and this view gives operations a synchronized window into them.
            </p>
          </div>
          <button
            type="button"
            onclick={openBillingTicketDrawer}
            class="inline-flex items-center gap-2 rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-neutral-800"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            Create Billing Ticket
          </button>
        </div>

        <div class="mt-4 grid gap-3 md:grid-cols-3">
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Search</span>
            <input bind:value={billingSearch} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Ticket, invoice, customer..." />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Status</span>
            <select bind:value={billingStatusFilter} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="">All statuses</option>
              <option value="open">Open</option>
              <option value="in_progress">In Progress</option>
              <option value="pending_requester">Pending Customer</option>
              <option value="escalated">Escalated</option>
              <option value="resolved">Resolved</option>
              <option value="closed">Closed</option>
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Priority</span>
            <select bind:value={billingPriorityFilter} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="">All priorities</option>
              {#each billingPriorityOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </label>
        </div>

        <div class="mt-5 overflow-x-auto">
          <table class="min-w-full divide-y divide-neutral-200 text-left text-sm">
            <thead class="bg-neutral-50 text-xs uppercase tracking-wide text-neutral-500">
              <tr>
                <th class="px-4 py-3">Ticket</th>
                <th class="px-4 py-3">Customer / Invoice</th>
                <th class="px-4 py-3">Assignment</th>
                <th class="px-4 py-3">Priority</th>
                <th class="px-4 py-3">SLA</th>
                <th class="px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-200">
              {#if filteredBillingTickets().length === 0}
                <tr>
                  <td colspan="6" class="px-4 py-10 text-center text-sm text-neutral-500">No billing helpdesk tickets match the current filters.</td>
                </tr>
              {:else}
                {#each filteredBillingTickets() as ticket}
                  <tr class="align-top">
                    <td class="px-4 py-4">
                      <p class="font-semibold text-neutral-900">{ticket.subject}</p>
                      <p class="mt-1 text-xs text-neutral-500">{ticket.ticket_id}</p>
                    </td>
                    <td class="px-4 py-4 text-neutral-600">
                      <p>{ticket.customer_name || "--"}</p>
                      <p class="mt-1 text-xs text-neutral-500">{ticket.invoice_number || "--"} • {ticket.property_name || "--"}</p>
                    </td>
                    <td class="px-4 py-4 text-neutral-600">
                      <p>{ticket.assigned_agent_name || "Unassigned"}</p>
                      <p class="mt-1 text-xs text-neutral-500">{ticket.requester_name || "--"}</p>
                    </td>
                    <td class="px-4 py-4">
                      <span class={`rounded-full px-2 py-1 text-[11px] font-semibold ${priorityClass(ticket.priority)}`}>
                        {ticket.priority_display}
                      </span>
                    </td>
                    <td class="px-4 py-4 text-neutral-600">
                      <p>{fmtDateTime(ticket.sla_deadline)}</p>
                      <p class={`mt-1 text-xs ${ticket.sla_breached ? "text-red-600" : "text-neutral-500"}`}>
                        {ticket.sla_breached ? "Breached" : "Tracked"}
                      </p>
                    </td>
                    <td class="px-4 py-4">
                      <span class={`rounded-full px-2 py-1 text-[11px] font-semibold ${billingStatusClass(ticket.status)}`}>
                        {ticket.status_display}
                      </span>
                    </td>
                  </tr>
                {/each}
              {/if}
            </tbody>
          </table>
        </div>
      </section>
    {:else if activeTab === "collections"}
      <section class="rounded-2xl border border-neutral-200 bg-white p-5">
        <div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h2 class="text-lg font-semibold text-neutral-900">Invoice Collections</h2>
            <p class="mt-1 text-sm text-neutral-500">
              Record payments, monitor open balances, and auto-resolve billing tickets once invoices are fully settled.
            </p>
          </div>
          <div class="rounded-xl bg-emerald-50 px-4 py-3 text-right">
            <p class="text-xs font-semibold uppercase tracking-wide text-emerald-700">Outstanding</p>
            <p class="mt-1 text-lg font-semibold text-emerald-900">{fmtMoney(overview.kpis.outstanding_balance)}</p>
          </div>
        </div>

        <div class="mt-4 grid gap-3 md:grid-cols-2">
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Search</span>
            <input bind:value={collectionSearch} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Invoice, customer, property..." />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Status</span>
            <select bind:value={collectionStatusFilter} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="">All statuses</option>
              <option value="draft">Draft</option>
              <option value="sent">Sent</option>
              <option value="overdue">Overdue</option>
              <option value="paid">Paid</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </label>
        </div>

        <div class="mt-5 overflow-x-auto">
          <table class="min-w-full divide-y divide-neutral-200 text-left text-sm">
            <thead class="bg-neutral-50 text-xs uppercase tracking-wide text-neutral-500">
              <tr>
                <th class="px-4 py-3">Invoice</th>
                <th class="px-4 py-3">Customer / Property</th>
                <th class="px-4 py-3">Dates</th>
                <th class="px-4 py-3">Amounts</th>
                <th class="px-4 py-3">Status</th>
                <th class="px-4 py-3">Action</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-200">
              {#if filteredInvoices().length === 0}
                <tr>
                  <td colspan="6" class="px-4 py-10 text-center text-sm text-neutral-500">No invoices match the current filters.</td>
                </tr>
              {:else}
                {#each filteredInvoices() as invoice}
                  <tr class="align-top">
                    <td class="px-4 py-4">
                      <p class="font-semibold text-neutral-900">{invoice.invoice_number}</p>
                      <p class="mt-1 text-xs text-neutral-500">{fmtInt(invoice.open_billing_ticket_count)} open billing tickets</p>
                    </td>
                    <td class="px-4 py-4 text-neutral-600">
                      <p>{invoice.customer_name}</p>
                      <p class="mt-1 text-xs text-neutral-500">{invoice.property_name}</p>
                    </td>
                    <td class="px-4 py-4 text-neutral-600">
                      <p>Issued {fmtDate(invoice.issue_date)}</p>
                      <p class="mt-1 text-xs text-neutral-500">Due {fmtDate(invoice.due_date)}</p>
                    </td>
                    <td class="px-4 py-4 text-neutral-600">
                      <p class="font-semibold text-neutral-900">{fmtMoney(invoice.total_amount)}</p>
                      <p class="mt-1 text-xs text-neutral-500">Paid {fmtMoney(invoice.paid_amount)}</p>
                      <p class="mt-1 text-xs font-semibold text-emerald-700">Balance {fmtMoney(invoice.balance_due)}</p>
                    </td>
                    <td class="px-4 py-4">
                      <span class={`rounded-full px-2 py-1 text-[11px] font-semibold ${invoiceStatusClass(invoice.status)}`}>
                        {fmtLabel(invoice.status)}
                      </span>
                    </td>
                    <td class="px-4 py-4">
                      <button
                        type="button"
                        onclick={() => openPaymentDrawer(invoice)}
                        disabled={invoice.status === "paid" || invoice.status === "cancelled"}
                        class="rounded-lg border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-700 transition-colors hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        Record Payment
                      </button>
                    </td>
                  </tr>
                {/each}
              {/if}
            </tbody>
          </table>
        </div>
      </section>
    {:else}
      <section class="rounded-2xl border border-neutral-200 bg-white p-5">
        <div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h2 class="text-lg font-semibold text-neutral-900">Feedback & Ratings</h2>
            <p class="mt-1 text-sm text-neutral-500">
              Capture close-out sentiment after requests are resolved so service quality can be tracked over time.
            </p>
          </div>
          <div class="rounded-xl bg-teal-50 px-4 py-3 text-right">
            <p class="text-xs font-semibold uppercase tracking-wide text-teal-700">Average Rating</p>
            <p class="mt-1 text-lg font-semibold text-teal-900">
              {overview.kpis.avg_feedback_rating === null ? "--" : `${overview.kpis.avg_feedback_rating.toFixed(1)} / 5`}
            </p>
          </div>
        </div>

        <div class="mt-5 grid gap-4 xl:grid-cols-2">
          <div class="rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
            <h3 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Resolved Requests Awaiting Feedback</h3>
            <div class="mt-4 space-y-3">
              {#if requestsForFeedback().filter((request) => !request.feedback_rating).length === 0}
                <p class="rounded-xl border border-dashed border-neutral-200 bg-white p-4 text-sm text-neutral-500">
                  No resolved requests are waiting on a rating.
                </p>
              {:else}
                {#each requestsForFeedback().filter((request) => !request.feedback_rating) as request}
                  <article class="rounded-xl border border-neutral-200 bg-white p-3">
                    <div class="flex items-start justify-between gap-3">
                      <div>
                        <p class="font-semibold text-neutral-900">{request.title}</p>
                        <p class="mt-1 text-xs text-neutral-500">{request.facility_code} • Resolved {fmtDate(request.resolved_date)}</p>
                      </div>
                      <button
                        type="button"
                        onclick={() => openFeedbackDrawer(request)}
                        class="rounded-lg border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-700 transition-colors hover:bg-neutral-50"
                      >
                        Add Feedback
                      </button>
                    </div>
                  </article>
                {/each}
              {/if}
            </div>
          </div>

          <div class="rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
            <h3 class="text-sm font-semibold uppercase tracking-wide text-neutral-600">Rated Requests</h3>
            <div class="mt-4 space-y-3">
              {#if requestsForFeedback().filter((request) => request.feedback_rating).length === 0}
                <p class="rounded-xl border border-dashed border-neutral-200 bg-white p-4 text-sm text-neutral-500">
                  No feedback has been captured yet.
                </p>
              {:else}
                {#each requestsForFeedback().filter((request) => request.feedback_rating) as request}
                  <article class="rounded-xl border border-neutral-200 bg-white p-3">
                    <div class="flex items-start justify-between gap-3">
                      <div>
                        <p class="font-semibold text-neutral-900">{request.title}</p>
                        <p class="mt-1 text-xs text-neutral-500">{request.facility_code} • {request.requester_name || request.requested_by}</p>
                      </div>
                      <span class="rounded-full bg-teal-50 px-2 py-1 text-[11px] font-semibold text-teal-700">
                        {request.feedback_rating}/5
                      </span>
                    </div>
                  </article>
                {/each}
              {/if}
            </div>
          </div>
        </div>
      </section>
    {/if}
  {/if}
</div>

{#if showServiceRequestDrawer}
  <button
    type="button"
    class="fixed inset-0 z-40 bg-neutral-900/35"
    onclick={closeServiceRequestDrawer}
    tabindex="-1"
    aria-label="Close service request drawer"
  ></button>
  <aside class="fixed inset-y-0 right-0 z-50 flex w-full max-w-3xl flex-col bg-white shadow-2xl animate-slide-in-right">
    <div class="flex items-center justify-between border-b border-neutral-100 px-6 py-4">
      <div>
        <h2 class="text-lg font-semibold text-neutral-900">Log Internal Service Request</h2>
        <p class="mt-1 text-xs text-neutral-500">All forms stay in drawers to keep the facility workflow consistent.</p>
      </div>
      <button
        type="button"
        onclick={closeServiceRequestDrawer}
        class="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        aria-label="Close service request drawer"
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div class="flex-1 overflow-y-auto px-6 py-5">
      <form id="facility-service-request-form" class="grid gap-4 md:grid-cols-2" onsubmit={handleServiceRequestCreate}>
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Facility</span>
          <select bind:value={serviceRequestForm.facility} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Select facility</option>
            {#each facilitiesLookup as facility}
              <option value={String(facility.id)}>{facility.facility_code} - {facility.property_name}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Room / Space</span>
          <select bind:value={serviceRequestForm.facility_space} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Select room / space</option>
            {#each filteredSpacesFor(serviceRequestForm.facility) as space}
              <option value={String(space.id)}>{space.facility_code} • {space.space_label || space.unit_number} • {space.zone_code}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700 md:col-span-2">
          <span class="mb-1.5 block">Request Title</span>
          <input bind:value={serviceRequestForm.title} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Restore power to east stairwell lighting" />
        </label>

        <label class="text-sm font-medium text-neutral-700 md:col-span-2">
          <span class="mb-1.5 block">Description</span>
          <textarea bind:value={serviceRequestForm.description} rows="4" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Describe the issue, impact, and any access restrictions."></textarea>
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Category</span>
          <select bind:value={serviceRequestForm.category} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            {#each categoryOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Priority</span>
          <select bind:value={serviceRequestForm.priority} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            {#each requestPriorityOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Channel</span>
          <select bind:value={serviceRequestForm.source_channel} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            {#each sourceChannelOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Assigned Agent</span>
          <select bind:value={serviceRequestForm.assigned_agent} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Assign later</option>
            {#each usersLookup as user}
              <option value={String(user.id)}>{user.label}</option>
            {/each}
          </select>
        </label>
      </form>
    </div>

    <div class="flex items-center justify-end gap-3 border-t border-neutral-100 px-6 py-4">
      <button
        type="button"
        onclick={closeServiceRequestDrawer}
        class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50"
      >
        Cancel
      </button>
      <button
        type="submit"
        form="facility-service-request-form"
        disabled={serviceRequestSaving}
        class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-neutral-800 disabled:opacity-50"
      >
        {serviceRequestSaving ? "Saving..." : "Save Request"}
      </button>
    </div>
  </aside>
{/if}

{#if showBillingTicketDrawer}
  <button
    type="button"
    class="fixed inset-0 z-40 bg-neutral-900/35"
    onclick={closeBillingTicketDrawer}
    tabindex="-1"
    aria-label="Close billing ticket drawer"
  ></button>
  <aside class="fixed inset-y-0 right-0 z-50 flex w-full max-w-2xl flex-col bg-white shadow-2xl animate-slide-in-right">
    <div class="flex items-center justify-between border-b border-neutral-100 px-6 py-4">
      <div>
        <h2 class="text-lg font-semibold text-neutral-900">Create Billing Helpdesk Ticket</h2>
        <p class="mt-1 text-xs text-neutral-500">This ticket stays customer-facing in helpdesk, while operations can work it from here.</p>
      </div>
      <button
        type="button"
        onclick={closeBillingTicketDrawer}
        class="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        aria-label="Close billing ticket drawer"
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div class="flex-1 overflow-y-auto px-6 py-5">
      <form id="facility-billing-ticket-form" class="space-y-4" onsubmit={handleBillingTicketCreate}>
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Invoice</span>
          <select bind:value={billingTicketForm.invoice} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Select invoice</option>
            {#each invoicesLookup as invoice}
              <option value={String(invoice.id)}>{invoice.invoice_number} • {invoice.customer_name} • {fmtMoney(invoice.balance_due)}</option>
            {/each}
          </select>
        </label>

        {#if selectedLookupInvoice()}
          <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-4 text-sm text-neutral-600">
            <p><span class="font-semibold text-neutral-900">Customer:</span> {selectedLookupInvoice()?.customer_name}</p>
            <p class="mt-1"><span class="font-semibold text-neutral-900">Property:</span> {selectedLookupInvoice()?.property_name}</p>
            <p class="mt-1"><span class="font-semibold text-neutral-900">Open Balance:</span> {fmtMoney(selectedLookupInvoice()?.balance_due)}</p>
          </div>
        {/if}

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Subject</span>
          <input bind:value={billingTicketForm.subject} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Request invoice breakdown for disputed service charge" />
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Description</span>
          <textarea bind:value={billingTicketForm.description} rows="4" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Summarize the customer request, dispute, or payment clarification needed."></textarea>
        </label>

        <div class="grid gap-4 md:grid-cols-2">
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Priority</span>
            <select bind:value={billingTicketForm.priority} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              {#each billingPriorityOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Assigned Agent</span>
            <select bind:value={billingTicketForm.assigned_agent} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              <option value="">Assign later</option>
              {#each usersLookup as user}
                <option value={String(user.id)}>{user.label}</option>
              {/each}
            </select>
          </label>
        </div>
      </form>
    </div>

    <div class="flex items-center justify-end gap-3 border-t border-neutral-100 px-6 py-4">
      <button
        type="button"
        onclick={closeBillingTicketDrawer}
        class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50"
      >
        Cancel
      </button>
      <button
        type="submit"
        form="facility-billing-ticket-form"
        disabled={billingTicketSaving}
        class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-neutral-800 disabled:opacity-50"
      >
        {billingTicketSaving ? "Saving..." : "Save Ticket"}
      </button>
    </div>
  </aside>
{/if}

{#if showPaymentDrawer}
  <button
    type="button"
    class="fixed inset-0 z-40 bg-neutral-900/35"
    onclick={closePaymentDrawer}
    tabindex="-1"
    aria-label="Close payment drawer"
  ></button>
  <aside class="fixed inset-y-0 right-0 z-50 flex w-full max-w-xl flex-col bg-white shadow-2xl animate-slide-in-right">
    <div class="flex items-center justify-between border-b border-neutral-100 px-6 py-4">
      <div>
        <h2 class="text-lg font-semibold text-neutral-900">Record Invoice Payment</h2>
        <p class="mt-1 text-xs text-neutral-500">{paymentForm.invoice_number || "Select an invoice"} payment details</p>
      </div>
      <button
        type="button"
        onclick={closePaymentDrawer}
        class="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        aria-label="Close payment drawer"
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div class="flex-1 overflow-y-auto px-6 py-5">
      <form id="facility-payment-form" class="space-y-4" onsubmit={handleRecordPayment}>
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Amount</span>
          <input type="number" min="0" step="0.01" bind:value={paymentForm.amount} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="0.00" />
        </label>

        <div class="grid gap-4 md:grid-cols-2">
          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Payment Date</span>
            <input type="date" bind:value={paymentForm.payment_date} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" />
          </label>

          <label class="text-sm font-medium text-neutral-700">
            <span class="mb-1.5 block">Payment Method</span>
            <select bind:value={paymentForm.payment_method} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
              {#each paymentMethodOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </label>
        </div>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Reference Number</span>
          <input bind:value={paymentForm.reference_number} class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Bank reference or receipt number" />
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Notes</span>
          <textarea bind:value={paymentForm.notes} rows="4" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Capture remittance notes or reconciliation context."></textarea>
        </label>
      </form>
    </div>

    <div class="flex items-center justify-end gap-3 border-t border-neutral-100 px-6 py-4">
      <button
        type="button"
        onclick={closePaymentDrawer}
        class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50"
      >
        Cancel
      </button>
      <button
        type="submit"
        form="facility-payment-form"
        disabled={paymentSaving}
        class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-neutral-800 disabled:opacity-50"
      >
        {paymentSaving ? "Saving..." : "Save Payment"}
      </button>
    </div>
  </aside>
{/if}

{#if showFeedbackDrawer}
  <button
    type="button"
    class="fixed inset-0 z-40 bg-neutral-900/35"
    onclick={closeFeedbackDrawer}
    tabindex="-1"
    aria-label="Close feedback drawer"
  ></button>
  <aside class="fixed inset-y-0 right-0 z-50 flex w-full max-w-lg flex-col bg-white shadow-2xl animate-slide-in-right">
    <div class="flex items-center justify-between border-b border-neutral-100 px-6 py-4">
      <div>
        <h2 class="text-lg font-semibold text-neutral-900">Capture Feedback</h2>
        <p class="mt-1 text-xs text-neutral-500">{feedbackForm.requestTitle || "Resolved request"} close-out rating</p>
      </div>
      <button
        type="button"
        onclick={closeFeedbackDrawer}
        class="rounded-lg p-1.5 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-900"
        aria-label="Close feedback drawer"
      >
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <div class="flex-1 overflow-y-auto px-6 py-5">
      <form id="facility-feedback-form" class="space-y-4" onsubmit={handleFeedbackSubmit}>
        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Rating</span>
          <select bind:value={feedbackForm.feedback_rating} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="5">5 - Excellent</option>
            <option value="4">4 - Good</option>
            <option value="3">3 - Fair</option>
            <option value="2">2 - Poor</option>
            <option value="1">1 - Very Poor</option>
          </select>
        </label>

        <label class="text-sm font-medium text-neutral-700">
          <span class="mb-1.5 block">Comment</span>
          <textarea bind:value={feedbackForm.feedback_comment} rows="5" class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm" placeholder="Summarize how the request was handled and any improvement areas."></textarea>
        </label>
      </form>
    </div>

    <div class="flex items-center justify-end gap-3 border-t border-neutral-100 px-6 py-4">
      <button
        type="button"
        onclick={closeFeedbackDrawer}
        class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-50"
      >
        Cancel
      </button>
      <button
        type="submit"
        form="facility-feedback-form"
        disabled={feedbackSaving}
        class="rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-neutral-800 disabled:opacity-50"
      >
        {feedbackSaving ? "Saving..." : "Save Feedback"}
      </button>
    </div>
  </aside>
{/if}

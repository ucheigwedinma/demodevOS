<script lang="ts">
  import { onMount } from "svelte";

  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type {
    PaginatedResponse,
    SupportDeskTicketLookups,
    SupportKnowledgeArticleListItem,
    SupportTicketDetail,
    SupportTicketListItem,
    SupportTicketPriority,
    SupportTicketStatus,
  } from "$lib/types";

  type RequestListViewKey =
    | "all"
    | "open"
    | "mine"
    | "unassigned"
    | "escalated"
    | "resolved"
    | "closed";

  type RequestListView = {
    key: RequestListViewKey;
    label: string;
    helper: string;
  };

  type ServiceRequestTypeKey =
    | "it_access"
    | "software_installation"
    | "password_reset"
    | "hr_policy"
    | "finance_payment"
    | "facility_maintenance";

  type ServiceRequestFieldType = "text" | "textarea" | "select";

  type ServiceRequestField = {
    key: string;
    label: string;
    type: ServiceRequestFieldType;
    required?: boolean;
    placeholder?: string;
    options?: Array<{ value: string; label: string }>;
  };

  type ServiceRequestType = {
    key: ServiceRequestTypeKey;
    label: string;
    description: string;
    approvalRequired: boolean;
    slaTargetHours: number;
    defaultPriority: SupportTicketPriority;
    departmentLabel: string;
    departmentKeywords: string[];
    fulfillmentProcess: string;
    formFields: ServiceRequestField[];
  };

  type CreateRequestDraft = {
    subject: string;
    description: string;
    requester: string;
    department: string;
    priority: SupportTicketPriority;
    status: SupportTicketStatus;
    assigned_agent: string;
  };

  type ParsedRequestDescription = {
    metadata: Record<string, string>;
    formEntries: Array<{ label: string; value: string }>;
    additionalContext: string;
  };

  type WorkflowVisualStep = {
    label: string;
    detail: string;
    state: "done" | "active" | "upcoming";
  };

  const listViews: RequestListView[] = [
    { key: "all", label: "All Requests", helper: "Every service request currently in the desk." },
    { key: "open", label: "Open", helper: "Requests still in active fulfillment." },
    { key: "mine", label: "Assigned to Me", helper: "Requests owned by the current user." },
    { key: "unassigned", label: "Unassigned", helper: "Requests waiting for team ownership." },
    { key: "escalated", label: "Escalated", helper: "Requests requiring elevated intervention." },
    { key: "resolved", label: "Resolved", helper: "Fulfilled requests awaiting closure." },
    { key: "closed", label: "Closed", helper: "Completed request history." },
  ];

  const serviceRequestCatalog: ServiceRequestType[] = [
    {
      key: "it_access",
      label: "IT Access Request",
      description: "Provision system access, role permissions, or shared tools for a user.",
      approvalRequired: true,
      slaTargetHours: 8,
      defaultPriority: "high",
      departmentLabel: "IT Support",
      departmentKeywords: ["it", "technology", "information"],
      fulfillmentProcess: "Identity and access validation, role assignment, then requester confirmation.",
      formFields: [
        {
          key: "access_scope",
          label: "Access Scope",
          type: "select",
          required: true,
          options: [
            { value: "application", label: "Application Access" },
            { value: "folder", label: "Shared Folder Access" },
            { value: "vpn", label: "VPN / Remote Access" },
            { value: "admin", label: "Administrative Access" },
          ],
        },
        {
          key: "systems",
          label: "Systems / Platforms",
          type: "text",
          required: true,
          placeholder: "ERP, CRM, Analytics, Shared Drive...",
        },
        {
          key: "business_justification",
          label: "Business Justification",
          type: "textarea",
          required: true,
          placeholder: "Why is this access needed?",
        },
      ],
    },
    {
      key: "software_installation",
      label: "Software Installation",
      description: "Install or update approved software on a workstation or endpoint.",
      approvalRequired: true,
      slaTargetHours: 24,
      defaultPriority: "medium",
      departmentLabel: "IT Support",
      departmentKeywords: ["it", "technology", "information"],
      fulfillmentProcess: "License validation, compatibility checks, remote or onsite installation.",
      formFields: [
        {
          key: "software_name",
          label: "Software Name",
          type: "text",
          required: true,
          placeholder: "Application name and version",
        },
        {
          key: "device_owner",
          label: "Device / User",
          type: "text",
          required: true,
          placeholder: "Hostname or user receiving installation",
        },
        {
          key: "license_status",
          label: "License Status",
          type: "select",
          required: true,
          options: [
            { value: "existing", label: "Existing License" },
            { value: "purchase_needed", label: "Purchase Needed" },
            { value: "trial", label: "Trial" },
          ],
        },
      ],
    },
    {
      key: "password_reset",
      label: "Password Reset",
      description: "Reset a locked or expired account password for an internal user.",
      approvalRequired: false,
      slaTargetHours: 2,
      defaultPriority: "high",
      departmentLabel: "IT Support",
      departmentKeywords: ["it", "technology", "information"],
      fulfillmentProcess: "Identity verification, secure reset, and post-reset login confirmation.",
      formFields: [
        {
          key: "account_identifier",
          label: "Account Email / Username",
          type: "text",
          required: true,
          placeholder: "user@company.com",
        },
        {
          key: "impact_level",
          label: "Business Impact",
          type: "select",
          required: true,
          options: [
            { value: "single_user", label: "Single User" },
            { value: "team_blocked", label: "Team Blocked" },
            { value: "critical_function", label: "Critical Function Blocked" },
          ],
        },
        {
          key: "error_message",
          label: "Error Message",
          type: "textarea",
          placeholder: "Paste lockout or auth error details if available.",
        },
      ],
    },
    {
      key: "hr_policy",
      label: "HR Policy Clarification",
      description: "Clarify internal policy interpretation, leave rules, or employee procedures.",
      approvalRequired: false,
      slaTargetHours: 16,
      defaultPriority: "medium",
      departmentLabel: "Human Resources",
      departmentKeywords: ["hr", "human", "people"],
      fulfillmentProcess: "Policy review by HR operations, response drafting, and requester confirmation.",
      formFields: [
        {
          key: "policy_area",
          label: "Policy Area",
          type: "select",
          required: true,
          options: [
            { value: "leave", label: "Leave & Attendance" },
            { value: "benefits", label: "Benefits" },
            { value: "performance", label: "Performance" },
            { value: "conduct", label: "Code of Conduct" },
          ],
        },
        {
          key: "employee_group",
          label: "Employee Group",
          type: "text",
          placeholder: "Department, location, or grade level",
        },
        {
          key: "question",
          label: "Clarification Required",
          type: "textarea",
          required: true,
          placeholder: "What policy point needs clarification?",
        },
      ],
    },
    {
      key: "finance_payment",
      label: "Finance Payment Inquiry",
      description: "Track payment status, remittance timing, or invoice settlement questions.",
      approvalRequired: true,
      slaTargetHours: 24,
      defaultPriority: "medium",
      departmentLabel: "Finance",
      departmentKeywords: ["finance", "account", "treasury"],
      fulfillmentProcess: "Invoice verification, payment run check, then status update to requester.",
      formFields: [
        {
          key: "invoice_reference",
          label: "Invoice / Payment Reference",
          type: "text",
          required: true,
          placeholder: "INV-12345 or payment reference",
        },
        {
          key: "counterparty",
          label: "Vendor / Beneficiary",
          type: "text",
          required: true,
          placeholder: "Supplier or payee name",
        },
        {
          key: "inquiry_details",
          label: "Inquiry Details",
          type: "textarea",
          required: true,
          placeholder: "What payment information is needed?",
        },
      ],
    },
    {
      key: "facility_maintenance",
      label: "Facility Maintenance Request",
      description: "Report building, utility, or workspace maintenance issues requiring action.",
      approvalRequired: false,
      slaTargetHours: 12,
      defaultPriority: "high",
      departmentLabel: "Facilities",
      departmentKeywords: ["facility", "maintenance", "operations"],
      fulfillmentProcess: "Issue triage, technician assignment, onsite fix, and completion confirmation.",
      formFields: [
        {
          key: "location",
          label: "Location",
          type: "text",
          required: true,
          placeholder: "Building, floor, room, or area",
        },
        {
          key: "issue_type",
          label: "Issue Type",
          type: "select",
          required: true,
          options: [
            { value: "electrical", label: "Electrical" },
            { value: "plumbing", label: "Plumbing" },
            { value: "hvac", label: "HVAC" },
            { value: "furniture", label: "Furniture" },
            { value: "general", label: "General" },
          ],
        },
        {
          key: "safety_risk",
          label: "Safety Risk",
          type: "select",
          required: true,
          options: [
            { value: "none", label: "No Immediate Safety Risk" },
            { value: "moderate", label: "Moderate Risk" },
            { value: "high", label: "High / Urgent Risk" },
          ],
        },
      ],
    },
  ];

  const catalogByKey = Object.fromEntries(
    serviceRequestCatalog.map((item) => [item.key, item]),
  ) as Record<ServiceRequestTypeKey, ServiceRequestType>;

  const pageSize = 15;

  let loadingLookups = $state(true);
  let loadingList = $state(true);
  let detailLoading = $state(false);
  let suggestionsLoading = $state(false);

  let actionKey = $state("");
  let errorMessage = $state("");
  let suggestionsError = $state("");

  let lookups = $state<SupportDeskTicketLookups | null>(null);
  let requests = $state<SupportTicketListItem[]>([]);
  let totalCount = $state(0);
  let currentPage = $state(1);

  let activeView = $state<RequestListViewKey>("all");
  let search = $state("");
  let selectedPriority = $state("");
  let selectedStatus = $state("");
  let selectedAgent = $state("");

  let selectedRequestId = $state<number | null>(null);
  let selectedRequest = $state<SupportTicketDetail | null>(null);
  let showCreateForm = $state(false);

  let selectedRequestTypeKey = $state<ServiceRequestTypeKey>("it_access");
  let requestFieldValues = $state<Record<string, string>>({});

  let suggestedArticles = $state<SupportKnowledgeArticleListItem[]>([]);

  let createDraft = $state<CreateRequestDraft>({
    subject: "",
    description: "",
    requester: "",
    department: "",
    priority: "high",
    status: "open",
    assigned_agent: "",
  });

  let assignAgentId = $state("");
  let internalNote = $state("");
  let requesterReply = $state("");
  let escalationReason = $state("");
  let closeResolutionNotes = $state("");
  let closeCustomerScore = $state("");

  let queueSearchDebounceTimer: ReturnType<typeof setTimeout>;
  let suggestionDebounceTimer: ReturnType<typeof setTimeout>;

  const exampleWorkflow = [
    "User submits request",
    "Approval required?",
    "Task assigned to team",
    "Request fulfilled",
    "Closed",
  ];

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let pageNumbers = $derived.by(() => {
    const pages: number[] = [];
    const maxVisible = 5;
    let start = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let end = Math.min(totalPages, start + maxVisible - 1);

    if (end - start + 1 < maxVisible) {
      start = Math.max(1, end - maxVisible + 1);
    }

    for (let index = start; index <= end; index += 1) pages.push(index);
    return pages;
  });

  let currentRequestType = $derived(catalogByKey[selectedRequestTypeKey]);
  let selectedParsedRequest = $derived(
    selectedRequest ? parseRequestDescription(selectedRequest.description || "") : null,
  );
  let selectedWorkflow = $derived(
    selectedRequest
      ? buildWorkflowState(
          selectedRequest,
          selectedParsedRequest?.metadata["Request Type"] || "",
        )
      : [],
  );

  function parseError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      const fieldMessage = Object.values(error.fieldErrors).flat()[0];
      if (fieldMessage) return fieldMessage;
      if (typeof error.data.detail === "string") return error.data.detail;
    }
    return fallback;
  }

  function isBusy(key: string): boolean {
    return actionKey === key;
  }

  function formatDateTime(value: string | null): string {
    if (!value) return "-";
    return new Date(value).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function formatRelative(value: string | null): string {
    if (!value) return "Never";
    const date = new Date(value);
    const diffMinutes = Math.floor((Date.now() - date.getTime()) / 60000);
    if (diffMinutes < 1) return "Just now";
    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays}d ago`;
    return formatDateTime(value);
  }

  function priorityBadgeClass(priority: SupportTicketPriority): string {
    if (priority === "critical") return "bg-red-50 text-red-700 border-red-200";
    if (priority === "high") return "bg-orange-50 text-orange-700 border-orange-200";
    if (priority === "medium") return "bg-amber-50 text-amber-700 border-amber-200";
    return "bg-emerald-50 text-emerald-700 border-emerald-200";
  }


  function workflowStepClass(state: WorkflowVisualStep["state"]): string {
    if (state === "done") return "border-emerald-200 bg-emerald-50 text-emerald-700";
    if (state === "active") return "border-amber-200 bg-amber-50 text-amber-700";
    return "border-neutral-200 bg-white text-neutral-500";
  }

  function buildParams(): Record<string, string> {
    const params: Record<string, string> = {
      page: String(currentPage),
      page_size: String(pageSize),
      view: activeView,
    };
    if (search.trim()) params.search = search.trim();
    if (selectedPriority) params.priority = selectedPriority;
    if (selectedStatus) params.status = selectedStatus;
    if (selectedAgent) params.assigned_agent = selectedAgent;
    return params;
  }

  function initializeRequestFieldValues(typeKey: ServiceRequestTypeKey) {
    const typeConfig = catalogByKey[typeKey];
    const nextValues: Record<string, string> = {};
    for (const field of typeConfig.formFields) {
      nextValues[field.key] =
        field.type === "select" ? field.options?.[0]?.value ?? "" : "";
    }
    requestFieldValues = nextValues;
  }

  function updateRequestFieldValue(fieldKey: string, value: string) {
    requestFieldValues = { ...requestFieldValues, [fieldKey]: value };
  }

  function resolveDepartmentName(departmentId: string): string {
    if (!departmentId || !lookups) return "";
    return (
      lookups.departments.find((department) => String(department.id) === departmentId)
        ?.name ?? ""
    );
  }

  function inferDepartmentForType(typeConfig: ServiceRequestType): string {
    if (!lookups) return "";
    const keywords = typeConfig.departmentKeywords.map((item) => item.toLowerCase());

    const directMatch = lookups.departments.find((department) => {
      const name = department.name.toLowerCase();
      return keywords.some((keyword) => name.includes(keyword));
    });

    return directMatch ? String(directMatch.id) : "";
  }

  function selectRequestType(typeKey: ServiceRequestTypeKey) {
    selectedRequestTypeKey = typeKey;
    const typeConfig = catalogByKey[typeKey];

    initializeRequestFieldValues(typeKey);

    if (!createDraft.subject.trim()) {
      createDraft.subject = `${typeConfig.label} request`;
    }

    createDraft.priority = typeConfig.defaultPriority;

    if (!createDraft.department) {
      const inferredDepartmentId = inferDepartmentForType(typeConfig);
      if (inferredDepartmentId) {
        createDraft.department = inferredDepartmentId;
      }
    }

    triggerSuggestionLookup(typeConfig.label);
  }

  function resetCreateDraft() {
    const typeConfig = catalogByKey[selectedRequestTypeKey];
    createDraft = {
      subject: "",
      description: "",
      requester: "",
      department: inferDepartmentForType(typeConfig),
      priority: typeConfig.defaultPriority,
      status: "open",
      assigned_agent: "",
    };
    initializeRequestFieldValues(selectedRequestTypeKey);
    triggerSuggestionLookup(typeConfig.label);
  }

  function parseRequestDescription(description: string): ParsedRequestDescription {
    const metadata: Record<string, string> = {};
    const formEntries: Array<{ label: string; value: string }> = [];
    const contextLines: string[] = [];

    let inWorkflow = false;
    let inRequestForm = false;
    let inContext = false;

    for (const line of description.split(/\r?\n/)) {
      const trimmed = line.trim();

      if (trimmed === "Workflow:") {
        inWorkflow = true;
        inRequestForm = false;
        inContext = false;
        continue;
      }

      if (trimmed === "Request Form:") {
        inRequestForm = true;
        inWorkflow = false;
        inContext = false;
        continue;
      }

      if (trimmed === "Additional Context:") {
        inContext = true;
        inWorkflow = false;
        inRequestForm = false;
        continue;
      }

      if (!trimmed) {
        if (inContext) contextLines.push("");
        continue;
      }

      if (inContext) {
        contextLines.push(line);
        continue;
      }

      if (inRequestForm && trimmed.startsWith("-")) {
        const fieldLine = trimmed.slice(1).trim();
        const [label, ...valueParts] = fieldLine.split(":");
        formEntries.push({
          label: label.trim(),
          value: valueParts.join(":").trim() || "-",
        });
        continue;
      }

      if (inWorkflow) {
        continue;
      }

      const metadataMatch = trimmed.match(/^([^:]+):\s*(.+)$/);
      if (metadataMatch) {
        metadata[metadataMatch[1].trim()] = metadataMatch[2].trim();
      }
    }

    return {
      metadata,
      formEntries,
      additionalContext: contextLines.join("\n").trim(),
    };
  }

  function resolveRequestTypeByLabel(label: string): ServiceRequestType | null {
    const normalized = label.trim().toLowerCase();
    if (!normalized) return null;
    return (
      serviceRequestCatalog.find((item) => item.label.toLowerCase() === normalized) ?? null
    );
  }

  function buildWorkflowState(
    requestItem: SupportTicketDetail,
    requestTypeLabel: string,
  ): WorkflowVisualStep[] {
    const requestType = resolveRequestTypeByLabel(requestTypeLabel);
    const requiresApproval = requestType ? requestType.approvalRequired : true;

    const approvalComplete =
      !requiresApproval ||
      [
        "in_progress",
        "pending_requester",
        "escalated",
        "resolved",
        "closed",
      ].includes(requestItem.status);

    const assignmentComplete =
      Boolean(requestItem.assigned_agent) ||
      ["in_progress", "pending_requester", "escalated", "resolved", "closed"].includes(
        requestItem.status,
      );

    const fulfilledComplete = ["resolved", "closed"].includes(requestItem.status);
    const closedComplete = requestItem.status === "closed";

    const completion = [true, approvalComplete, assignmentComplete, fulfilledComplete, closedComplete];

    const labels: Array<{ label: string; detail: string }> = [
      {
        label: "Submitted",
        detail: "Requester submitted the service request.",
      },
      {
        label: "Approval",
        detail: requiresApproval
          ? "Approval gate required for this request type."
          : "No approval gate required for this request type.",
      },
      {
        label: "Assigned",
        detail: "Task assigned to fulfillment team.",
      },
      {
        label: "Fulfilled",
        detail: "Request delivery completed by assignee.",
      },
      {
        label: "Closed",
        detail: "Request closed after verification.",
      },
    ];

    return labels.map((step, index) => {
      if (completion[index]) {
        return { ...step, state: "done" };
      }

      const previousStepsComplete = completion.slice(0, index).every(Boolean);
      return {
        ...step,
        state: previousStepsComplete ? "active" : "upcoming",
      };
    });
  }

  function buildRequestDescription(): string {
    const requestType = catalogByKey[selectedRequestTypeKey];
    const departmentName =
      resolveDepartmentName(createDraft.department) || requestType.departmentLabel;

    const lines: string[] = [
      `Request Type: ${requestType.label}`,
      `Assigned Department: ${departmentName}`,
      `SLA Target: ${requestType.slaTargetHours} hours`,
      `Approval Required: ${requestType.approvalRequired ? "Yes" : "No"}`,
      `Fulfillment Process: ${requestType.fulfillmentProcess}`,
      "",
      "Workflow:",
      "1. User submits request",
      requestType.approvalRequired
        ? "2. Approval required and routed to approver"
        : "2. No approval checkpoint required",
      "3. Task assigned to team",
      "4. Request fulfilled",
      "5. Closed",
      "",
      "Request Form:",
    ];

    for (const field of requestType.formFields) {
      const value = (requestFieldValues[field.key] ?? "").trim();
      lines.push(`- ${field.label}: ${value || "Not provided"}`);
    }

    if (createDraft.description.trim()) {
      lines.push("", "Additional Context:", createDraft.description.trim());
    }

    return lines.join("\n");
  }

  function triggerSuggestionLookup(input: string) {
    clearTimeout(suggestionDebounceTimer);
    suggestionDebounceTimer = setTimeout(() => {
      void loadSuggestedArticles(input);
    }, 260);
  }

  async function loadSuggestedArticles(query: string) {
    const trimmed = query.trim();
    if (trimmed.length < 3) {
      suggestedArticles = [];
      suggestionsError = "";
      return;
    }

    suggestionsLoading = true;
    suggestionsError = "";

    try {
      const response = await api.get<PaginatedResponse<SupportKnowledgeArticleListItem>>(
        "/support-desk/knowledge-base/articles/",
        {
          status: "published",
          page_size: "5",
          search: trimmed,
        },
      );
      suggestedArticles = response.results;
    } catch (error) {
      suggestedArticles = [];
      suggestionsError = parseError(
        error,
        "Could not load suggested knowledge articles.",
      );
    } finally {
      suggestionsLoading = false;
    }
  }

  function syncDetailForms(requestItem: SupportTicketDetail) {
    assignAgentId = requestItem.assigned_agent ? String(requestItem.assigned_agent) : "";
    internalNote = "";
    requesterReply = "";
    escalationReason = "";
    closeResolutionNotes = requestItem.resolution_notes || "";
    closeCustomerScore = requestItem.customer_satisfaction_score
      ? String(requestItem.customer_satisfaction_score)
      : "";
  }

  async function loadLookups() {
    loadingLookups = true;
    try {
      lookups = await api.get<SupportDeskTicketLookups>("/support-desk/requests/lookups/");
      if (!createDraft.department) {
        createDraft.department = inferDepartmentForType(currentRequestType);
      }
    } catch (error) {
      lookups = null;
      toast.error(
        "Lookups unavailable",
        parseError(error, "Could not load request lookup data."),
      );
    } finally {
      loadingLookups = false;
    }
  }

  async function loadRequestDetail(requestId: number, showSpinner = true) {
    if (showSpinner) detailLoading = true;
    try {
      const detail = await api.get<SupportTicketDetail>(
        `/support-desk/requests/${requestId}/`,
      );
      selectedRequest = detail;
      selectedRequestId = detail.id;
      syncDetailForms(detail);
    } catch (error) {
      selectedRequest = null;
      toast.error("Request unavailable", parseError(error, "Could not load this request."));
    } finally {
      if (showSpinner) detailLoading = false;
    }
  }

  async function loadRequests() {
    loadingList = true;
    errorMessage = "";
    try {
      const response = await api.get<PaginatedResponse<SupportTicketListItem>>(
        "/support-desk/requests/",
        buildParams(),
      );
      requests = response.results;
      totalCount = response.count;

      if (response.results.length === 0) {
        selectedRequestId = null;
        selectedRequest = null;
        return;
      }

      const selectedStillVisible =
        selectedRequestId !== null &&
        response.results.some((requestItem) => requestItem.id === selectedRequestId);
      const nextRequestId = selectedStillVisible
        ? selectedRequestId!
        : response.results[0].id;
      await loadRequestDetail(nextRequestId, false);
    } catch (error) {
      requests = [];
      totalCount = 0;
      selectedRequestId = null;
      selectedRequest = null;
      errorMessage = parseError(error, "Could not load support requests.");
    } finally {
      loadingList = false;
    }
  }

  function setView(view: RequestListViewKey) {
    if (activeView === view) return;
    activeView = view;
    currentPage = 1;
    void loadRequests();
  }

  function handleSearchInput(value: string) {
    search = value;
    clearTimeout(queueSearchDebounceTimer);
    queueSearchDebounceTimer = setTimeout(() => {
      currentPage = 1;
      void loadRequests();
    }, 300);
  }

  function handleFilterChange() {
    currentPage = 1;
    void loadRequests();
  }

  function resetFilters() {
    search = "";
    selectedPriority = "";
    selectedStatus = "";
    selectedAgent = "";
    currentPage = 1;
    void loadRequests();
  }

  function goToPage(page: number) {
    if (page < 1 || page > totalPages || page === currentPage) return;
    currentPage = page;
    void loadRequests();
  }

  async function handleCreateRequest(event: SubmitEvent) {
    event.preventDefault();
    const requestType = catalogByKey[selectedRequestTypeKey];

    const missingRequiredFields = requestType.formFields.filter(
      (field) => field.required && !(requestFieldValues[field.key] ?? "").trim(),
    );

    if (!createDraft.subject.trim()) {
      toast.error("Missing subject", "Provide a short subject for this request.");
      return;
    }

    if (missingRequiredFields.length > 0) {
      toast.error(
        "Incomplete request form",
        `Complete required field: ${missingRequiredFields[0].label}.`,
      );
      return;
    }

    actionKey = "create";
    try {
      const payload: Record<string, unknown> = {
        subject: createDraft.subject.trim(),
        description: buildRequestDescription(),
        priority: createDraft.priority,
        status: createDraft.status,
      };

      if (createDraft.requester) payload.requester = Number(createDraft.requester);
      if (createDraft.department) payload.department = Number(createDraft.department);
      if (createDraft.assigned_agent) {
        payload.assigned_agent = Number(createDraft.assigned_agent);
      }

      const created = await api.post<{ id: number }>("/support-desk/requests/", payload);
      toast.success(
        "Request created",
        `${requestType.label} request submitted to Support Desk.`,
      );
      showCreateForm = false;
      resetCreateDraft();
      currentPage = 1;
      await loadRequests();
      if (created.id) await loadRequestDetail(created.id);
    } catch (error) {
      toast.error("Create failed", parseError(error, "Could not create support request."));
    } finally {
      actionKey = "";
    }
  }

  async function runDetailAction(
    key: string,
    requestFn: () => Promise<SupportTicketDetail>,
    successTitle: string,
    successMessage: string,
  ) {
    if (!selectedRequestId) return;
    actionKey = key;
    try {
      const updated = await requestFn();
      selectedRequest = updated;
      selectedRequestId = updated.id;
      syncDetailForms(updated);
      toast.success(successTitle, successMessage);
      await loadRequests();
    } catch (error) {
      toast.error("Action failed", parseError(error, "Request action failed."));
    } finally {
      actionKey = "";
    }
  }

  async function handleAssignAgent(event: SubmitEvent) {
    event.preventDefault();
    if (!selectedRequestId || !assignAgentId) return;
    await runDetailAction(
      "assign",
      () =>
        api.post<SupportTicketDetail>(
          `/support-desk/requests/${selectedRequestId}/assign/`,
          {
            assigned_agent_id: Number(assignAgentId),
          },
        ),
      "Agent assigned",
      "Request assignment updated.",
    );
  }

  async function handleInternalNote(event: SubmitEvent) {
    event.preventDefault();
    if (!selectedRequestId || !internalNote.trim()) return;
    await runDetailAction(
      "internal-note",
      () =>
        api.post<SupportTicketDetail>(
          `/support-desk/requests/${selectedRequestId}/internal-notes/`,
          {
            body: internalNote.trim(),
          },
        ),
      "Note added",
      "Internal note saved.",
    );
  }

  async function handleRequesterReply(event: SubmitEvent) {
    event.preventDefault();
    if (!selectedRequestId || !requesterReply.trim()) return;
    await runDetailAction(
      "reply",
      () =>
        api.post<SupportTicketDetail>(
          `/support-desk/requests/${selectedRequestId}/reply/`,
          {
            body: requesterReply.trim(),
          },
        ),
      "Reply sent",
      "Requester reply was recorded.",
    );
  }

  async function handleEscalate(event: SubmitEvent) {
    event.preventDefault();
    if (!selectedRequestId) return;
    await runDetailAction(
      "escalate",
      () =>
        api.post<SupportTicketDetail>(
          `/support-desk/requests/${selectedRequestId}/escalate/`,
          {
            reason: escalationReason.trim(),
          },
        ),
      "Request escalated",
      "Escalation status applied.",
    );
  }

  async function handleCloseRequest(event: SubmitEvent) {
    event.preventDefault();
    if (!selectedRequestId) return;

    const payload: Record<string, unknown> = {
      resolution_notes: closeResolutionNotes.trim(),
    };
    if (closeCustomerScore) {
      payload.customer_satisfaction_score = Number(closeCustomerScore);
    }

    await runDetailAction(
      "close",
      () =>
        api.post<SupportTicketDetail>(
          `/support-desk/requests/${selectedRequestId}/close/`,
          payload,
        ),
      "Request closed",
      "Request has been closed.",
    );
  }

  onMount(async () => {
    initializeRequestFieldValues(selectedRequestTypeKey);
    await Promise.all([loadLookups(), loadRequests()]);
    if (!createDraft.department) {
      createDraft.department = inferDepartmentForType(currentRequestType);
    }
    void loadSuggestedArticles(currentRequestType.label);
  });
</script>

<div class="flex flex-col gap-8">
  <section class="space-y-4">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div class="max-w-3xl">
        <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-600">Support Desk</p>
        <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Requests</h1>
        <p class="mt-1 max-w-2xl text-sm text-neutral-500">
          Requests are separate from problem tickets and represent standard services.
          <code class="rounded bg-white px-1 py-0.5 text-xs"></code>enforces request-type workflow metadata.
        </p>
      </div>

      <div class="w-full max-w-sm rounded-xl border border-neutral-200 bg-white p-5">
        <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-neutral-400">Queue Snapshot</p>
        <div class="mt-4 grid gap-3 sm:grid-cols-2">
          <div class="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-4">
            <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Visible</p>
            <p class="mt-2 text-2xl font-semibold text-neutral-950">{requests.length}</p>
          </div>
          <div class="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-4">
            <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Total</p>
            <p class="mt-2 text-2xl font-semibold text-neutral-950">{totalCount}</p>
          </div>
        </div>
        <button
          type="button"
          onclick={() => {
            showCreateForm = !showCreateForm;
            if (showCreateForm) resetCreateDraft();
          }}
          class="mt-5 inline-flex items-center gap-2 rounded-2xl border border-neutral-800 bg-neutral-800 px-4 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800"
        >
          {showCreateForm ? "Hide Request Form" : "Create Service Request"}
        </button>
      </div>
    </div>

    <div class="mt-6 rounded-xl border border-neutral-200 bg-white p-5">
      <p class="text-[11px] font-semibold uppercase tracking-[0.15em] text-neutral-400">Standard Workflow</p>
      <div class="mt-4 grid gap-3 md:grid-cols-5">
        {#each exampleWorkflow as step, index}
          <div class="relative rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3">
            <p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-400">Step {index + 1}</p>
            <p class="mt-1 text-sm font-medium text-neutral-800">{step}</p>
            {#if index < exampleWorkflow.length - 1}
              <span class="absolute -right-2 top-1/2 hidden -translate-y-1/2 text-neutral-300 md:inline">→</span>
            {/if}
          </div>
        {/each}
      </div>
    </div>
  </section>

  <section class="order-3 rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h2 class="text-lg font-semibold text-neutral-950">Request Type Catalog</h2>
        <p class="mt-1 text-sm text-neutral-500">Each request type includes a form template, approval pattern, fulfillment process, and SLA target.</p>
      </div>
      <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">{serviceRequestCatalog.length} standardized request types</p>
    </div>

    <div class="mt-5 grid gap-4 lg:grid-cols-2 2xl:grid-cols-3">
      {#each serviceRequestCatalog as requestType}
        <article class={`rounded-3xl border p-5 transition-colors ${selectedRequestTypeKey === requestType.key ? "border-emerald-400 bg-emerald-50/50" : "border-neutral-200 bg-neutral-50 hover:border-neutral-300"}`}>
          <div class="flex items-start justify-between gap-3">
            <div>
              <h3 class="text-base font-semibold text-neutral-800">{requestType.label}</h3>
              <p class="mt-1 text-sm leading-6 text-neutral-600">{requestType.description}</p>
            </div>
            <button
              type="button"
              onclick={() => selectRequestType(requestType.key)}
              class={`rounded-xl px-3 py-1.5 text-xs font-semibold ${selectedRequestTypeKey === requestType.key ? "bg-emerald-600 text-white" : "border border-neutral-300 bg-white text-neutral-700 hover:border-neutral-400"}`}
            >
              {selectedRequestTypeKey === requestType.key ? "Selected" : "Use Type"}
            </button>
          </div>

          <div class="mt-4 grid gap-2 sm:grid-cols-2">
            <div class="rounded-2xl border border-white bg-white px-3 py-3">
              <p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-400">Approval</p>
              <p class="mt-1 text-sm font-medium text-neutral-800">{requestType.approvalRequired ? "Required" : "Not Required"}</p>
            </div>
            <div class="rounded-2xl border border-white bg-white px-3 py-3">
              <p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-400">SLA Target</p>
              <p class="mt-1 text-sm font-medium text-neutral-800">{requestType.slaTargetHours} hours</p>
            </div>
            <div class="rounded-2xl border border-white bg-white px-3 py-3 sm:col-span-2">
              <p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-400">Assigned Department</p>
              <p class="mt-1 text-sm font-medium text-neutral-800">{requestType.departmentLabel}</p>
            </div>
          </div>
        </article>
      {/each}
    </div>
  </section>

  <section class="order-2 rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
    <div class="flex flex-wrap gap-3">
      {#each listViews as view}
        <button
          type="button"
          onclick={() => setView(view.key)}
          class={`rounded-2xl border px-4 py-3 text-left transition-colors ${
            activeView === view.key
              ? "border-neutral-800 bg-neutral-800 text-white"
              : "border-neutral-200 bg-neutral-50 text-neutral-700 hover:border-neutral-300 hover:bg-white"
          }`}
        >
          <div class="text-sm font-semibold">{view.label}</div>
          <div class={`mt-1 text-xs leading-5 ${activeView === view.key ? "text-neutral-300" : "text-neutral-500"}`}>
            {view.helper}
          </div>
        </button>
      {/each}
    </div>
  </section>

  <div class="order-2 grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(360px,0.95fr)]">
    <section class="space-y-6">
      <article class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
        <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <label class="block xl:col-span-2">
            <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Search</span>
            <input
              type="text"
              value={search}
              oninput={(event) => handleSearchInput((event.currentTarget as HTMLInputElement).value)}
              placeholder="Search by ID, subject, requester..."
              class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 placeholder:text-neutral-400 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
            />
          </label>

          <label class="block">
            <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Priority</span>
            <select bind:value={selectedPriority} onchange={handleFilterChange} class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10">
              <option value="">All priorities</option>
              {#each lookups?.priorities ?? [] as option}
                <option value={option.key}>{option.label}</option>
              {/each}
            </select>
          </label>

          <label class="block">
            <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Status</span>
            <select bind:value={selectedStatus} onchange={handleFilterChange} class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10">
              <option value="">All statuses</option>
              {#each lookups?.statuses ?? [] as option}
                <option value={option.key}>{option.label}</option>
              {/each}
            </select>
          </label>

          <label class="block">
            <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Agent</span>
            <select bind:value={selectedAgent} onchange={handleFilterChange} class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10">
              <option value="">All assignments</option>
              {#each lookups?.agents ?? [] as agent}
                <option value={agent.id}>{agent.label}</option>
              {/each}
            </select>
          </label>
        </div>

        <div class="mt-4 flex justify-end">
          <button type="button" onclick={resetFilters} class="text-sm font-semibold text-neutral-500 hover:text-neutral-800">Reset filters</button>
        </div>

        <div class="mt-6 overflow-hidden rounded-3xl border border-neutral-200">
          {#if loadingList}
            <div class="flex items-center justify-center py-16">
              <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-800"></div>
            </div>
          {:else if errorMessage}
            <div class="px-6 py-14 text-center">
              <h3 class="text-base font-semibold text-red-900">Request queue unavailable</h3>
              <p class="mt-2 text-sm text-red-700">{errorMessage}</p>
              <button type="button" onclick={() => loadRequests()} class="mt-4 rounded-xl border border-red-300 bg-white px-4 py-2 text-sm font-semibold text-red-800 hover:bg-red-100">
                Retry
              </button>
            </div>
          {:else if requests.length === 0}
            <div class="px-6 py-14 text-center">
              <h3 class="text-base font-semibold text-neutral-950">No requests found</h3>
              <p class="mt-2 text-sm leading-6 text-neutral-500">Change filters or create a new service request.</p>
            </div>
          {:else}
            <div class="overflow-x-auto">
              <table class="min-w-[1080px] w-full">
                <thead class="bg-neutral-50">
                  <tr>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Request ID</th>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Subject</th>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Requester</th>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Priority</th>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Status</th>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Assigned Agent</th>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {#each requests as requestItem}
                    <tr
                      class={`cursor-pointer border-b border-neutral-100 transition-colors hover:bg-neutral-50 ${selectedRequestId === requestItem.id ? "bg-emerald-50/60" : "bg-white"}`}
                      onclick={() => loadRequestDetail(requestItem.id)}
                    >
                      <td class="whitespace-nowrap px-4 py-4 text-sm font-semibold text-neutral-800">{requestItem.ticket_id}</td>
                      <td class="px-4 py-4 text-sm font-medium text-neutral-800">{requestItem.subject}</td>
                      <td class="px-4 py-4 text-sm text-neutral-700">{requestItem.requester_name || "-"}</td>
                      <td class="px-4 py-4 text-sm">
                        <span class={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${priorityBadgeClass(requestItem.priority)}`}>
                          {requestItem.priority_display}
                        </span>
                      </td>
                      <td class="px-4 py-4 text-sm">
                        <StatusBadge status={requestItem.status} label={requestItem.status_display} />
                      </td>
                      <td class="px-4 py-4 text-sm text-neutral-700">{requestItem.assigned_agent_name || "Unassigned"}</td>
                      <td class="whitespace-nowrap px-4 py-4 text-sm text-neutral-500">{formatRelative(requestItem.updated_at)}</td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {/if}
        </div>

        {#if requests.length > 0}
          <div class="mt-6 flex flex-wrap items-center justify-between gap-4">
            <p class="text-sm text-neutral-500">
              Showing {(currentPage - 1) * pageSize + 1} to {Math.min(currentPage * pageSize, totalCount)} of {totalCount} requests
            </p>
            <div class="flex items-center gap-2">
              <button type="button" onclick={() => goToPage(currentPage - 1)} disabled={currentPage === 1} class="rounded-xl border border-neutral-200 px-3 py-2 text-sm font-semibold text-neutral-700 disabled:cursor-not-allowed disabled:opacity-50">
                Previous
              </button>
              {#each pageNumbers as page}
                <button
                  type="button"
                  onclick={() => goToPage(page)}
                  class={`rounded-xl px-3 py-2 text-sm font-semibold ${page === currentPage ? "bg-neutral-800 text-white" : "border border-neutral-200 text-neutral-700"}`}
                >
                  {page}
                </button>
              {/each}
              <button type="button" onclick={() => goToPage(currentPage + 1)} disabled={currentPage === totalPages} class="rounded-xl border border-neutral-200 px-3 py-2 text-sm font-semibold text-neutral-700 disabled:cursor-not-allowed disabled:opacity-50">
                Next
              </button>
            </div>
          </div>
        {/if}
      </article>
    </section>

    <aside class="space-y-6">
      {#if showCreateForm}
        <article class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
          <div class="flex items-start justify-between gap-4">
            <div>
              <h2 class="text-lg font-semibold text-neutral-950">Create Service Request</h2>
              <p class="mt-1 text-sm text-neutral-500">Standardized request form with approval, SLA, and fulfillment metadata.</p>
            </div>
            <button type="button" onclick={() => (showCreateForm = false)} class="text-sm font-semibold text-neutral-500 hover:text-neutral-800">Close</button>
          </div>

          <form class="mt-6 space-y-4" onsubmit={handleCreateRequest}>
            <label class="block">
              <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Request Type</span>
              <select
                value={selectedRequestTypeKey}
                onchange={(event) => selectRequestType((event.currentTarget as HTMLSelectElement).value as ServiceRequestTypeKey)}
                class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
              >
                {#each serviceRequestCatalog as requestType}
                  <option value={requestType.key}>{requestType.label}</option>
                {/each}
              </select>
            </label>

            <div class="rounded-2xl border border-emerald-200 bg-emerald-50/60 px-4 py-4">
              <p class="text-sm font-semibold text-emerald-900">{currentRequestType.label}</p>
              <p class="mt-1 text-sm leading-6 text-emerald-800">{currentRequestType.description}</p>
              <div class="mt-3 grid gap-2 sm:grid-cols-3">
                <div class="rounded-xl border border-white/70 bg-white/70 px-3 py-2">
                  <p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-700">Approval</p>
                  <p class="mt-1 text-sm font-medium text-emerald-900">{currentRequestType.approvalRequired ? "Required" : "Not Required"}</p>
                </div>
                <div class="rounded-xl border border-white/70 bg-white/70 px-3 py-2">
                  <p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-700">SLA</p>
                  <p class="mt-1 text-sm font-medium text-emerald-900">{currentRequestType.slaTargetHours}h</p>
                </div>
                <div class="rounded-xl border border-white/70 bg-white/70 px-3 py-2">
                  <p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-700">Department</p>
                  <p class="mt-1 text-sm font-medium text-emerald-900">{resolveDepartmentName(createDraft.department) || currentRequestType.departmentLabel}</p>
                </div>
              </div>
            </div>

            <label class="block">
              <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Subject</span>
              <input
                bind:value={createDraft.subject}
                required
                type="text"
                placeholder="Short request summary"
                oninput={(event) => triggerSuggestionLookup((event.currentTarget as HTMLInputElement).value)}
                class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
              />
            </label>

            <div class="grid gap-4 md:grid-cols-2">
              {#each currentRequestType.formFields as field}
                <label class={`block ${field.type === "textarea" ? "md:col-span-2" : ""}`}>
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">
                    {field.label}{field.required ? " *" : ""}
                  </span>

                  {#if field.type === "textarea"}
                    <textarea
                      rows="3"
                      value={requestFieldValues[field.key] ?? ""}
                      oninput={(event) => updateRequestFieldValue(field.key, (event.currentTarget as HTMLTextAreaElement).value)}
                      placeholder={field.placeholder ?? ""}
                      class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
                    ></textarea>
                  {:else if field.type === "select"}
                    <select
                      value={requestFieldValues[field.key] ?? ""}
                      onchange={(event) => updateRequestFieldValue(field.key, (event.currentTarget as HTMLSelectElement).value)}
                      class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
                    >
                      {#each field.options ?? [] as option}
                        <option value={option.value}>{option.label}</option>
                      {/each}
                    </select>
                  {:else}
                    <input
                      type="text"
                      value={requestFieldValues[field.key] ?? ""}
                      oninput={(event) => updateRequestFieldValue(field.key, (event.currentTarget as HTMLInputElement).value)}
                      placeholder={field.placeholder ?? ""}
                      class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
                    />
                  {/if}
                </label>
              {/each}
            </div>

            <label class="block">
              <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Additional Context</span>
              <textarea bind:value={createDraft.description} rows="3" placeholder="Optional context for fulfillment team" class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"></textarea>
            </label>

            <div class="grid gap-4 md:grid-cols-2">
              <label class="block">
                <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Requester</span>
                <select bind:value={createDraft.requester} class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10">
                  <option value="">Current user</option>
                  {#each lookups?.requesters ?? [] as requester}
                    <option value={requester.id}>{requester.label}</option>
                  {/each}
                </select>
              </label>
              <label class="block">
                <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Assigned Department</span>
                <select bind:value={createDraft.department} class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10">
                  <option value="">Auto from request type</option>
                  {#each lookups?.departments ?? [] as department}
                    <option value={department.id}>{department.name}</option>
                  {/each}
                </select>
              </label>
            </div>

            <div class="grid gap-4 md:grid-cols-2">
              <label class="block">
                <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Priority</span>
                <select bind:value={createDraft.priority} class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10">
                  {#each lookups?.priorities ?? [] as option}
                    <option value={option.key}>{option.label}</option>
                  {/each}
                </select>
              </label>
              <label class="block">
                <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Assigned Agent</span>
                <select bind:value={createDraft.assigned_agent} class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10">
                  <option value="">Unassigned</option>
                  {#each lookups?.agents ?? [] as agent}
                    <option value={agent.id}>{agent.label}</option>
                  {/each}
                </select>
              </label>
            </div>

            <div class="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-4">
              <div class="flex items-start justify-between gap-3">
                <div>
                  <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Suggested Knowledge Articles</p>
                  <p class="mt-1 text-sm text-neutral-600">Suggestions update from your request subject and type to reduce duplicate tickets.</p>
                </div>
                <button
                  type="button"
                  onclick={() => triggerSuggestionLookup(`${currentRequestType.label} ${createDraft.subject}`)}
                  class="rounded-xl border border-neutral-300 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:border-neutral-400"
                >
                  Refresh
                </button>
              </div>

              {#if suggestionsLoading}
                <div class="mt-3 flex items-center gap-2 text-sm text-neutral-500">
                  <div class="inline-block h-4 w-4 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-700"></div>
                  Finding relevant articles...
                </div>
              {:else if suggestionsError}
                <p class="mt-3 text-sm text-red-700">{suggestionsError}</p>
              {:else if suggestedArticles.length === 0}
                <p class="mt-3 text-sm text-neutral-500">No article suggestions yet. Add a more specific subject.</p>
              {:else}
                <div class="mt-3 space-y-2">
                  {#each suggestedArticles as article}
                    <a href={`/support-desk/knowledge-base?article=${article.id}`} class="block rounded-xl border border-neutral-200 bg-white px-3 py-3 hover:border-neutral-300">
                      <p class="text-sm font-semibold text-neutral-800">{article.title}</p>
                      <p class="mt-1 text-xs text-neutral-500">{article.category || "General"} • {article.view_count} views</p>
                    </a>
                  {/each}
                </div>
              {/if}
            </div>

            <button type="submit" disabled={isBusy("create") || loadingLookups} class="w-full rounded-2xl border border-neutral-800 bg-neutral-800 px-4 py-3 text-sm font-semibold text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60">
              {isBusy("create") ? "Creating..." : "Submit Request"}
            </button>
          </form>
        </article>
      {/if}

      <article class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
        {#if detailLoading}
          <div class="flex items-center justify-center py-12">
            <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-800"></div>
          </div>
        {:else if !selectedRequest}
          <div class="rounded-2xl border border-dashed border-neutral-300 bg-neutral-50 px-5 py-6">
            <p class="text-sm font-medium text-neutral-800">No request selected</p>
            <p class="mt-2 text-sm leading-6 text-neutral-500">Select a request to inspect workflow status and perform actions.</p>
          </div>
        {:else}
          <div class="space-y-5">
            <div>
              <h2 class="text-xl font-semibold text-neutral-950">{selectedRequest.ticket_id} • {selectedRequest.subject}</h2>
              <p class="mt-2 text-sm leading-6 text-neutral-600">{selectedParsedRequest?.additionalContext || selectedRequest.description || "No description provided."}</p>
            </div>

            <div class="grid gap-3 sm:grid-cols-2">
              <div class="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-4">
                <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Requester</p>
                <p class="mt-2 text-sm font-medium text-neutral-800">{selectedRequest.requester_name || "-"}</p>
              </div>
              <div class="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-4">
                <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Assigned Agent</p>
                <p class="mt-2 text-sm font-medium text-neutral-800">{selectedRequest.assigned_agent_name || "Unassigned"}</p>
              </div>
              <div class="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-4">
                <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Status</p>
                <p class="mt-2 text-sm font-medium text-neutral-800">{selectedRequest.status_display}</p>
              </div>
              <div class="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-4">
                <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Updated</p>
                <p class="mt-2 text-sm font-medium text-neutral-800">{formatDateTime(selectedRequest.updated_at)}</p>
              </div>
            </div>

            {#if selectedParsedRequest}
              <div class="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-4">
                <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Request Metadata</p>
                <div class="mt-3 grid gap-2 sm:grid-cols-2">
                  {#each Object.entries(selectedParsedRequest.metadata) as [label, value]}
                    <div class="rounded-xl border border-white bg-white px-3 py-2">
                      <p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-400">{label}</p>
                      <p class="mt-1 text-sm font-medium text-neutral-800">{value}</p>
                    </div>
                  {/each}
                </div>
              </div>
            {/if}

            <div class="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-4">
              <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Workflow State</p>
              <div class="mt-3 space-y-2">
                {#each selectedWorkflow as step}
                  <div class={`rounded-xl border px-3 py-3 ${workflowStepClass(step.state)}`}>
                    <p class="text-sm font-semibold">{step.label}</p>
                    <p class="mt-1 text-xs">{step.detail}</p>
                  </div>
                {/each}
              </div>
            </div>

            {#if selectedParsedRequest?.formEntries.length}
              <div>
                <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Submitted Request Form</p>
                <div class="mt-2 space-y-2">
                  {#each selectedParsedRequest.formEntries as entry}
                    <div class="rounded-2xl border border-neutral-200 bg-white px-4 py-3">
                      <p class="text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-400">{entry.label}</p>
                      <p class="mt-1 text-sm text-neutral-800">{entry.value}</p>
                    </div>
                  {/each}
                </div>
              </div>
            {/if}

            <form class="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto]" onsubmit={handleAssignAgent}>
              <label class="block">
                <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Assign Agent</span>
                <select bind:value={assignAgentId} class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10">
                  <option value="">Select agent</option>
                  {#each lookups?.agents ?? [] as agent}
                    <option value={agent.id}>{agent.label}</option>
                  {/each}
                </select>
              </label>
              <button type="submit" disabled={isBusy("assign") || !assignAgentId} class="self-end rounded-2xl border border-neutral-800 bg-neutral-800 px-4 py-3 text-sm font-semibold text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60">
                {isBusy("assign") ? "Assigning..." : "Assign"}
              </button>
            </form>

            <form class="space-y-3" onsubmit={handleInternalNote}>
              <label class="block">
                <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Internal Note</span>
                <textarea bind:value={internalNote} rows="3" class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"></textarea>
              </label>
              <button type="submit" disabled={isBusy("internal-note") || !internalNote.trim()} class="w-full rounded-2xl border border-neutral-800 bg-neutral-800 px-4 py-3 text-sm font-semibold text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60">
                {isBusy("internal-note") ? "Saving..." : "Save Note"}
              </button>
            </form>

            <form class="space-y-3" onsubmit={handleRequesterReply}>
              <label class="block">
                <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Reply to Requester</span>
                <textarea bind:value={requesterReply} rows="3" class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"></textarea>
              </label>
              <button type="submit" disabled={isBusy("reply") || !requesterReply.trim()} class="w-full rounded-2xl border border-neutral-800 bg-neutral-800 px-4 py-3 text-sm font-semibold text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60">
                {isBusy("reply") ? "Sending..." : "Send Reply"}
              </button>
            </form>

            <form class="space-y-3" onsubmit={handleEscalate}>
              <label class="block">
                <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Escalation Reason</span>
                <textarea bind:value={escalationReason} rows="3" class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"></textarea>
              </label>
              <button type="submit" disabled={isBusy("escalate")} class="w-full rounded-2xl border border-rose-300 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700 hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-60">
                {isBusy("escalate") ? "Escalating..." : "Escalate Request"}
              </button>
            </form>

            <form class="space-y-3" onsubmit={handleCloseRequest}>
              <label class="block">
                <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Resolution Notes</span>
                <textarea bind:value={closeResolutionNotes} rows="3" class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"></textarea>
              </label>
              <label class="block">
                <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Customer Satisfaction Score</span>
                <select bind:value={closeCustomerScore} class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10">
                  <option value="">Not captured</option>
                  <option value="1">1</option>
                  <option value="2">2</option>
                  <option value="3">3</option>
                  <option value="4">4</option>
                  <option value="5">5</option>
                </select>
              </label>
              <button type="submit" disabled={isBusy("close")} class="w-full rounded-2xl border border-emerald-300 bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-700 hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-60">
                {isBusy("close") ? "Closing..." : "Close Request"}
              </button>
            </form>

            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Internal Notes</p>
              <div class="mt-2 space-y-2">
                {#if selectedRequest.internal_notes.length === 0}
                  <p class="rounded-2xl border border-dashed border-neutral-300 bg-neutral-50 px-4 py-4 text-sm text-neutral-500">No internal notes yet.</p>
                {:else}
                  {#each selectedRequest.internal_notes as note}
                    <div class="rounded-2xl border border-neutral-200 px-4 py-4">
                      <p class="text-sm font-medium text-neutral-800">{note.author_name || "Unknown author"}</p>
                      <p class="mt-1 text-sm leading-6 text-neutral-600">{note.body}</p>
                    </div>
                  {/each}
                {/if}
              </div>
            </div>

            <div>
              <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Requester Replies</p>
              <div class="mt-2 space-y-2">
                {#if selectedRequest.requester_replies.length === 0}
                  <p class="rounded-2xl border border-dashed border-neutral-300 bg-neutral-50 px-4 py-4 text-sm text-neutral-500">No requester replies yet.</p>
                {:else}
                  {#each selectedRequest.requester_replies as reply}
                    <div class="rounded-2xl border border-neutral-200 px-4 py-4">
                      <p class="text-sm font-medium text-neutral-800">{reply.author_name || "Unknown author"}</p>
                      <p class="mt-1 text-sm leading-6 text-neutral-600">{reply.body}</p>
                    </div>
                  {/each}
                {/if}
              </div>
            </div>
          </div>
        {/if}
      </article>
    </aside>
  </div>
</div>

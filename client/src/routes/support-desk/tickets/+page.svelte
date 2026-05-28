<script lang="ts">
  import { onMount } from "svelte";
  import { useAutoRefresh } from "$lib/realtime.svelte";

  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type {
    PaginatedResponse,
    SupportDeskTicketLookups,
    SupportTicketAttachmentRecord,
    SupportTicketCategory,
    SupportTicketDetail,
    SupportTicketListItem,
    SupportTicketPriority,
    SupportTicketStatus,
  } from "$lib/types";

  type TicketListViewKey =
    | "all"
    | "open"
    | "mine"
    | "unassigned"
    | "escalated"
    | "resolved"
    | "closed";

  type TicketListView = {
    key: TicketListViewKey;
    label: string;
    helper: string;
  };

  type CreateTicketDraft = {
    subject: string;
    description: string;
    requester: string;
    customer: string;
    contact_account: string;
    department: string;
    category: SupportTicketCategory;
    priority: SupportTicketPriority;
    status: SupportTicketStatus;
    assigned_agent: string;
  };

  const listViews: TicketListView[] = [
    { key: "all", label: "All Tickets", helper: "Full operational queue across every support intake." },
    { key: "open", label: "Open Tickets", helper: "Active tickets that still require handling." },
    { key: "mine", label: "My Tickets", helper: "Items assigned to the current support agent." },
    { key: "unassigned", label: "Unassigned Tickets", helper: "New work waiting for ownership." },
    { key: "escalated", label: "Escalated Tickets", helper: "Tickets routed above the standard support queue." },
    { key: "resolved", label: "Resolved Tickets", helper: "Handled tickets pending final closure confirmation." },
    { key: "closed", label: "Closed Tickets", helper: "Completed records kept for service history and audit." },
  ];

  const pageSize = 15;

  let loadingList = $state(true);
  let loadingLookups = $state(true);
  let detailLoading = $state(false);
  let actionKey = $state("");
  let errorMessage = $state("");
  let lookups = $state<SupportDeskTicketLookups | null>(null);
  let tickets = $state<SupportTicketListItem[]>([]);
  let totalCount = $state(0);
  let currentPage = $state(1);

  let activeView = $state<TicketListViewKey>("all");
  let search = $state("");
  let selectedCategory = $state("");
  let selectedPriority = $state("");
  let selectedStatus = $state("");
  let selectedAgent = $state("");

  let selectedTicketId = $state<number | null>(null);
  let selectedTicket = $state<SupportTicketDetail | null>(null);
  let showCreateForm = $state(false);

  let createDraft = $state<CreateTicketDraft>({
    subject: "",
    description: "",
    requester: "",
    customer: "",
    contact_account: "",
    department: "",
    category: "other",
    priority: "medium",
    status: "open",
    assigned_agent: "",
  });

  let assignAgentId = $state("");
  let priorityValue = $state<SupportTicketPriority>("medium");
  let internalNote = $state("");
  let requesterReply = $state("");
  let attachmentLabel = $state("");
  let attachmentFile = $state<File | null>(null);
  let attachmentInputVersion = $state(0);
  let relatedTicketRef = $state("");
  let escalationReason = $state("");
  let closeResolutionNotes = $state("");
  let closeCustomerScore = $state("");

  let searchDebounceTimer: ReturnType<typeof setTimeout>;

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let pageNumbers = $derived.by(() => {
    const pages: number[] = [];
    const maxVisible = 5;
    let start = Math.max(1, currentPage - Math.floor(maxVisible / 2));
    let end = Math.min(totalPages, start + maxVisible - 1);
    if (end - start + 1 < maxVisible) {
      start = Math.max(1, end - maxVisible + 1);
    }
    for (let index = start; index <= end; index += 1) {
      pages.push(index);
    }
    return pages;
  });
  let hasFilters = $derived(Boolean(search || selectedCategory || selectedPriority || selectedStatus || selectedAgent));

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

  function currentViewMeta(): TicketListView {
    return listViews.find((view) => view.key === activeView) ?? listViews[0];
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


  function syncDetailForms(ticket: SupportTicketDetail) {
    assignAgentId = ticket.assigned_agent ? String(ticket.assigned_agent) : "";
    priorityValue = ticket.priority;
    closeResolutionNotes = ticket.resolution_notes || "";
    closeCustomerScore = ticket.customer_satisfaction_score ? String(ticket.customer_satisfaction_score) : "";
    internalNote = "";
    requesterReply = "";
    relatedTicketRef = "";
    escalationReason = "";
    attachmentLabel = "";
    attachmentFile = null;
    attachmentInputVersion += 1;
  }

  function resetCreateDraft() {
    createDraft = {
      subject: "",
      description: "",
      requester: "",
      customer: "",
      contact_account: "",
      department: "",
      category: lookups?.categories[0]?.key as SupportTicketCategory ?? "other",
      priority: "medium",
      status: "open",
      assigned_agent: "",
    };
  }

  function buildTicketParams(): Record<string, string> {
    const params: Record<string, string> = {
      page: String(currentPage),
      page_size: String(pageSize),
      view: activeView,
    };
    if (search.trim()) params.search = search.trim();
    if (selectedCategory) params.category = selectedCategory;
    if (selectedPriority) params.priority = selectedPriority;
    if (selectedStatus) params.status = selectedStatus;
    if (selectedAgent) params.assigned_agent = selectedAgent;
    return params;
  }

  async function loadLookups() {
    loadingLookups = true;
    try {
      lookups = await api.get<SupportDeskTicketLookups>("/support-desk/tickets/lookups/");
      if (!createDraft.category && lookups.categories[0]) {
        createDraft.category = lookups.categories[0].key as SupportTicketCategory;
      }
    } catch (error) {
      lookups = null;
      toast.error("Lookups unavailable", parseError(error, "Could not load Support Desk lookup data."));
    } finally {
      loadingLookups = false;
    }
  }

  async function loadTicketDetail(ticketId: number, showSpinner = true) {
    if (showSpinner) detailLoading = true;
    try {
      const detail = await api.get<SupportTicketDetail>(`/support-desk/tickets/${ticketId}/`);
      selectedTicket = detail;
      selectedTicketId = detail.id;
      syncDetailForms(detail);
    } catch (error) {
      selectedTicket = null;
      toast.error("Ticket unavailable", parseError(error, "Could not load this ticket."));
    } finally {
      if (showSpinner) detailLoading = false;
    }
  }

  async function loadTickets() {
    loadingList = true;
    errorMessage = "";
    try {
      const response = await api.get<PaginatedResponse<SupportTicketListItem>>("/support-desk/tickets/", buildTicketParams());
      tickets = response.results;
      totalCount = response.count;

      if (response.results.length === 0) {
        selectedTicketId = null;
        selectedTicket = null;
        return;
      }

      const selectedStillVisible = selectedTicketId !== null && response.results.some((ticket) => ticket.id === selectedTicketId);
      const nextTicketId = selectedStillVisible ? selectedTicketId! : response.results[0].id;
      await loadTicketDetail(nextTicketId, false);
    } catch (error) {
      tickets = [];
      totalCount = 0;
      selectedTicketId = null;
      selectedTicket = null;
      errorMessage = parseError(error, "Could not load the Support Desk ticket queue.");
    } finally {
      loadingList = false;
    }
  }

  function handleSearchInput(value: string) {
    search = value;
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
      currentPage = 1;
      void loadTickets();
    }, 300);
  }

  function handleFilterChange() {
    currentPage = 1;
    void loadTickets();
  }

  function handleFilterReset() {
    search = "";
    selectedCategory = "";
    selectedPriority = "";
    selectedStatus = "";
    selectedAgent = "";
    currentPage = 1;
    void loadTickets();
  }

  function setView(view: TicketListViewKey) {
    if (activeView === view) return;
    activeView = view;
    currentPage = 1;
    void loadTickets();
  }

  function goToPage(page: number) {
    if (page < 1 || page > totalPages || page === currentPage) return;
    currentPage = page;
    void loadTickets();
  }

  async function handleCreateTicket(event: SubmitEvent) {
    event.preventDefault();
    actionKey = "create";
    try {
      const payload: Record<string, unknown> = {
        subject: createDraft.subject.trim(),
        description: createDraft.description.trim(),
        category: createDraft.category,
        priority: createDraft.priority,
        status: createDraft.status,
      };
      if (createDraft.requester) payload.requester = Number(createDraft.requester);
      if (createDraft.customer) payload.customer = Number(createDraft.customer);
      if (createDraft.contact_account) payload.contact_account = Number(createDraft.contact_account);
      if (createDraft.department) payload.department = Number(createDraft.department);
      if (createDraft.assigned_agent) payload.assigned_agent = Number(createDraft.assigned_agent);

      const created = await api.post<{ id: number }>("/support-desk/tickets/", payload);
      toast.success("Ticket created", "Support ticket created successfully.");
      showCreateForm = false;
      resetCreateDraft();
      currentPage = 1;
      await loadTickets();
      if (created.id) {
        await loadTicketDetail(created.id);
      }
    } catch (error) {
      toast.error("Create failed", parseError(error, "Could not create the ticket."));
    } finally {
      actionKey = "";
    }
  }

  async function runDetailAction<T extends SupportTicketDetail>(
    key: string,
    request: () => Promise<T>,
    successTitle: string,
    successMessage: string,
  ) {
    if (!selectedTicketId) return;
    actionKey = key;
    try {
      const updated = await request();
      selectedTicket = updated;
      selectedTicketId = updated.id;
      syncDetailForms(updated);
      toast.success(successTitle, successMessage);
      await loadTickets();
    } catch (error) {
      toast.error("Action failed", parseError(error, `Could not ${successTitle.toLowerCase()}.`));
    } finally {
      actionKey = "";
    }
  }

  async function handleAssignAgent(event: SubmitEvent) {
    event.preventDefault();
    if (!selectedTicketId || !assignAgentId) return;
    await runDetailAction(
      "assign",
      () => api.post<SupportTicketDetail>(`/support-desk/tickets/${selectedTicketId}/assign/`, { assigned_agent_id: Number(assignAgentId) }),
      "Agent assigned",
      "Ticket assignment updated.",
    );
  }

  async function handlePriorityChange(event: SubmitEvent) {
    event.preventDefault();
    if (!selectedTicketId) return;
    await runDetailAction(
      "priority",
      () => api.post<SupportTicketDetail>(`/support-desk/tickets/${selectedTicketId}/priority/`, { priority: priorityValue }),
      "Priority updated",
      "Ticket priority and SLA were updated.",
    );
  }

  async function handleInternalNote(event: SubmitEvent) {
    event.preventDefault();
    if (!selectedTicketId || !internalNote.trim()) return;
    await runDetailAction(
      "internal-note",
      () => api.post<SupportTicketDetail>(`/support-desk/tickets/${selectedTicketId}/internal-notes/`, { body: internalNote.trim() }),
      "Note added",
      "Internal note saved on the ticket.",
    );
  }

  async function handleRequesterReply(event: SubmitEvent) {
    event.preventDefault();
    if (!selectedTicketId || !requesterReply.trim()) return;
    await runDetailAction(
      "reply",
      () => api.post<SupportTicketDetail>(`/support-desk/tickets/${selectedTicketId}/reply/`, { body: requesterReply.trim() }),
      "Reply sent",
      "Requester reply was recorded on the ticket.",
    );
  }

  async function handleLinkTicket(event: SubmitEvent) {
    event.preventDefault();
    if (!selectedTicketId || !relatedTicketRef.trim()) return;
    await runDetailAction(
      "link-related",
      () => api.post<SupportTicketDetail>(`/support-desk/tickets/${selectedTicketId}/link-related/`, { related_ticket_ref: relatedTicketRef.trim() }),
      "Related ticket linked",
      "Ticket relationship saved.",
    );
  }

  async function handleEscalate(event: SubmitEvent) {
    event.preventDefault();
    if (!selectedTicketId) return;
    await runDetailAction(
      "escalate",
      () => api.post<SupportTicketDetail>(`/support-desk/tickets/${selectedTicketId}/escalate/`, { reason: escalationReason.trim() }),
      "Ticket escalated",
      "Escalation status has been applied.",
    );
  }

  async function handleCloseTicket(event: SubmitEvent) {
    event.preventDefault();
    if (!selectedTicketId) return;
    const payload: Record<string, unknown> = {
      resolution_notes: closeResolutionNotes.trim(),
    };
    if (closeCustomerScore) payload.customer_satisfaction_score = Number(closeCustomerScore);

    await runDetailAction(
      "close",
      () => api.post<SupportTicketDetail>(`/support-desk/tickets/${selectedTicketId}/close/`, payload),
      "Ticket closed",
      "Ticket has been closed successfully.",
    );
  }

  async function handleAttachmentUpload(event: SubmitEvent) {
    event.preventDefault();
    if (!selectedTicketId || !attachmentFile) return;
    actionKey = "attachment";
    try {
      const payload = new FormData();
      payload.append("label", attachmentLabel.trim());
      payload.append("file", attachmentFile);
      await api.upload<SupportTicketAttachmentRecord>(`/support-desk/tickets/${selectedTicketId}/attachments/`, payload);
      toast.success("Attachment uploaded", "File attached to the ticket.");
      attachmentLabel = "";
      attachmentFile = null;
      attachmentInputVersion += 1;
      await loadTicketDetail(selectedTicketId);
      await loadTickets();
    } catch (error) {
      toast.error("Upload failed", parseError(error, "Could not upload the attachment."));
    } finally {
      actionKey = "";
    }
  }

  onMount(async () => {
    await Promise.all([loadLookups(), loadTickets()]);
  });

  useAutoRefresh("Ticket", loadTickets);
</script>

<div class="space-y-8">
  <section class="space-y-4">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div class="max-w-3xl">
        <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-emerald-600">Support Desk</p>
        <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Tickets</h1>
        <p class="mt-1 max-w-2xl text-sm text-neutral-500">
          Queue views, ticket lists, agent actions, comments, and escalation
        </p>
      </div>

      <div class="w-full max-w-sm rounded-xl border border-neutral-200 bg-white p-5">
        <p class="text-[11px] font-semibold uppercase tracking-[0.16em] text-neutral-400">Current View</p>
        <div class="mt-3 space-y-2">
          <p class="text-xl font-semibold text-neutral-950">{currentViewMeta().label}</p>
          <p class="text-sm leading-6 text-neutral-600">{currentViewMeta().helper}</p>
        </div>
        <div class="mt-5 grid gap-3 sm:grid-cols-2">
          <div class="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-4">
            <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Rows</p>
            <p class="mt-2 text-2xl font-semibold text-neutral-950">{tickets.length}</p>
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
          {showCreateForm ? "Hide Ticket Form" : "Create Ticket"}
        </button>
      </div>
    </div>
  </section>

  <section class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
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

  <div class="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(360px,0.95fr)]">
    <section class="space-y-6">
      <article class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 class="text-lg font-semibold text-neutral-950">Ticket List</h2>
            <p class="mt-1 text-sm text-neutral-500">Queue view with operational filters and live Support Desk records.</p>
          </div>
          <div class="rounded-full bg-neutral-100 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-neutral-500">
            {currentViewMeta().label}
          </div>
        </div>

        <div class="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
          <label class="block xl:col-span-2">
            <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Search Tickets</span>
            <input
              type="text"
              value={search}
              oninput={(event) => handleSearchInput((event.currentTarget as HTMLInputElement).value)}
              placeholder="Search by ticket ID, subject, requester..."
              class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 placeholder:text-neutral-400 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
            />
          </label>

          <label class="block">
            <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Category</span>
            <select bind:value={selectedCategory} onchange={handleFilterChange} class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10">
              <option value="">All categories</option>
              {#each lookups?.categories ?? [] as option}
                <option value={option.key}>{option.label}</option>
              {/each}
            </select>
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

          <label class="block md:col-span-2 xl:col-span-5">
            <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Assigned Agent</span>
            <select bind:value={selectedAgent} onchange={handleFilterChange} class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10">
              <option value="">All assignments</option>
              {#each lookups?.agents ?? [] as agent}
                <option value={agent.id}>{agent.label}</option>
              {/each}
            </select>
          </label>
        </div>

        {#if hasFilters}
          <div class="mt-4 flex justify-end">
            <button type="button" onclick={handleFilterReset} class="text-sm font-semibold text-neutral-500 hover:text-neutral-800">
              Reset filters
            </button>
          </div>
        {/if}

        <div class="mt-6 overflow-hidden rounded-3xl border border-neutral-200">
          {#if loadingList}
            <div class="flex items-center justify-center py-16">
              <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-800"></div>
            </div>
          {:else if errorMessage}
            <div class="px-6 py-14 text-center">
              <h3 class="text-base font-semibold text-red-900">Ticket queue unavailable</h3>
              <p class="mt-2 text-sm text-red-700">{errorMessage}</p>
              <button type="button" onclick={() => loadTickets()} class="mt-4 rounded-xl border border-red-300 bg-white px-4 py-2 text-sm font-semibold text-red-800 hover:bg-red-100">
                Retry
              </button>
            </div>
          {:else if tickets.length === 0}
            <div class="px-6 py-14 text-center">
              <div class="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-neutral-100 text-neutral-700">
                <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.75">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M4.5 7.5A2.25 2.25 0 0 1 6.75 5.25h10.5A2.25 2.25 0 0 1 19.5 7.5v2.25a1.5 1.5 0 0 0 0 3V15a2.25 2.25 0 0 1-2.25 2.25H6.75A2.25 2.25 0 0 1 4.5 15v-2.25a1.5 1.5 0 0 0 0-3V7.5Z" />
                </svg>
              </div>
              <h3 class="mt-4 text-base font-semibold text-neutral-950">No tickets matched this queue view</h3>
              <p class="mt-2 text-sm leading-6 text-neutral-500">Change the queue view, clear your filters, or create a new ticket.</p>
              <button
                type="button"
                onclick={() => {
                  showCreateForm = true;
                  resetCreateDraft();
                }}
                class="mt-4 rounded-2xl border border-neutral-800 bg-neutral-800 px-4 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800"
              >
                Create ticket
              </button>
            </div>
          {:else}
            <div class="overflow-x-auto">
              <table class="min-w-[1320px] w-full">
                <thead class="bg-neutral-50">
                  <tr>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Ticket ID</th>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Subject</th>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Description</th>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Requester</th>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Department</th>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Category</th>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Priority</th>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Status</th>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Assigned Agent</th>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Created Date</th>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Last Updated</th>
                    <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">SLA Deadline</th>
                  </tr>
                </thead>
                <tbody>
                  {#each tickets as ticket}
                    <tr
                      class={`cursor-pointer border-b border-neutral-100 transition-colors hover:bg-neutral-50 ${selectedTicketId === ticket.id ? 'bg-teal-50/50' : 'bg-white'}`}
                      onclick={() => loadTicketDetail(ticket.id)}
                    >
                      <td class="whitespace-nowrap px-4 py-4 text-sm font-semibold text-neutral-800">{ticket.ticket_id}</td>
                      <td class="px-4 py-4 text-sm font-medium text-neutral-800">{ticket.subject}</td>
                      <td class="max-w-xs px-4 py-4 text-sm text-neutral-500">
                        <div class="line-clamp-2">{ticket.description || "-"}</div>
                      </td>
                      <td class="px-4 py-4 text-sm text-neutral-700">{ticket.requester_name || "-"}</td>
                      <td class="px-4 py-4 text-sm text-neutral-700">{ticket.department_name || "-"}</td>
                      <td class="px-4 py-4 text-sm text-neutral-700">{ticket.category_display}</td>
                      <td class="px-4 py-4 text-sm">
                        <span class={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${priorityBadgeClass(ticket.priority)}`}>
                          {ticket.priority_display}
                        </span>
                      </td>
                      <td class="px-4 py-4 text-sm">
                        <StatusBadge status={ticket.status} label={ticket.status_display} />
                      </td>
                      <td class="px-4 py-4 text-sm text-neutral-700">{ticket.assigned_agent_name || "Unassigned"}</td>
                      <td class="whitespace-nowrap px-4 py-4 text-sm text-neutral-500">{formatDateTime(ticket.created_at)}</td>
                      <td class="whitespace-nowrap px-4 py-4 text-sm text-neutral-500">{formatRelative(ticket.updated_at)}</td>
                      <td class="whitespace-nowrap px-4 py-4 text-sm">
                        <span class={ticket.sla_breached ? "font-semibold text-red-700" : "text-neutral-500"}>
                          {formatDateTime(ticket.sla_deadline)}
                        </span>
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {/if}
        </div>

        {#if tickets.length > 0}
          <div class="mt-6 flex flex-wrap items-center justify-between gap-4">
            <p class="text-sm text-neutral-500">
              Showing {(currentPage - 1) * pageSize + 1} to {Math.min(currentPage * pageSize, totalCount)} of {totalCount} tickets
            </p>
            <div class="flex items-center gap-2">
              <button type="button" onclick={() => goToPage(currentPage - 1)} disabled={currentPage === 1} class="rounded-xl border border-neutral-200 px-3 py-2 text-sm font-semibold text-neutral-700 disabled:cursor-not-allowed disabled:opacity-50">
                Previous
              </button>
              {#each pageNumbers as page}
                <button
                  type="button"
                  onclick={() => goToPage(page)}
                  class={`rounded-xl px-3 py-2 text-sm font-semibold ${page === currentPage ? 'bg-neutral-800 text-white' : 'border border-neutral-200 text-neutral-700'}`}
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
              <h2 class="text-lg font-semibold text-neutral-950">Create Ticket</h2>
              <p class="mt-1 text-sm text-neutral-500">Create a new Support Desk ticket with a real API write.</p>
            </div>
            <button type="button" onclick={() => (showCreateForm = false)} class="text-sm font-semibold text-neutral-500 hover:text-neutral-800">Close</button>
          </div>

          <form class="mt-6 space-y-4" onsubmit={handleCreateTicket}>
            <label class="block">
              <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Subject</span>
              <input bind:value={createDraft.subject} required type="text" class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10" />
            </label>

            <label class="block">
              <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Description</span>
              <textarea bind:value={createDraft.description} rows="4" class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"></textarea>
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
                <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Department</span>
                <select bind:value={createDraft.department} class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10">
                  <option value="">Auto from requester</option>
                  {#each lookups?.departments ?? [] as department}
                    <option value={department.id}>{department.name}</option>
                  {/each}
                </select>
              </label>
            </div>

            <div class="grid gap-4 md:grid-cols-2">
              <label class="block">
                <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Customer Profile</span>
                <select bind:value={createDraft.customer} class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10">
                  <option value="">Auto-link from complaint context</option>
                  {#each lookups?.customers ?? [] as customer}
                    <option value={customer.id}>
                      {customer.label}{customer.support_ticketing_enabled ? "" : " (Ticketing locked)"}
                    </option>
                  {/each}
                </select>
              </label>

              <label class="block">
                <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Contact Account</span>
                <select bind:value={createDraft.contact_account} class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10">
                  <option value="">Optional (linked contact)</option>
                  {#each lookups?.contact_accounts ?? [] as contact}
                    <option value={contact.id}>{contact.label}</option>
                  {/each}
                </select>
              </label>
            </div>

            <div class="grid gap-4 md:grid-cols-2">
              <label class="block">
                <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Category</span>
                <select bind:value={createDraft.category} class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10">
                  {#each lookups?.categories ?? [] as option}
                    <option value={option.key}>{option.label}</option>
                  {/each}
                </select>
              </label>

              <label class="block">
                <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Priority</span>
                <select bind:value={createDraft.priority} class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10">
                  {#each lookups?.priorities ?? [] as option}
                    <option value={option.key}>{option.label}</option>
                  {/each}
                </select>
              </label>
            </div>

            <div class="grid gap-4 md:grid-cols-2">
              <label class="block">
                <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Status</span>
                <select bind:value={createDraft.status} class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10">
                  {#each lookups?.statuses ?? [] as option}
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

            {#if createDraft.category === "complaint"}
              <p class="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs font-medium text-amber-800">
                Complaint tickets require a customer profile with support ticketing enabled.
              </p>
            {/if}

            <button type="submit" disabled={isBusy('create') || loadingLookups} class="w-full rounded-2xl border border-neutral-800 bg-neutral-800 px-4 py-3 text-sm font-semibold text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60">
              {isBusy("create") ? "Creating..." : "Create Ticket"}
            </button>
          </form>
        </article>
      {/if}

      <article class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
        {#if detailLoading}
          <div class="flex items-center justify-center py-12">
            <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-800"></div>
          </div>
        {:else if !selectedTicket}
          <div class="rounded-2xl border border-dashed border-neutral-300 bg-neutral-50 px-5 py-6">
            <p class="text-sm font-medium text-neutral-800">No ticket selected</p>
            <p class="mt-2 text-sm leading-6 text-neutral-500">Select a ticket from the list to view details and run actions.</p>
          </div>
        {:else}
          <div class="space-y-6">
            <div>
              <div class="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Selected Ticket</p>
                  <h2 class="mt-2 text-xl font-semibold text-neutral-950">{selectedTicket.ticket_id} • {selectedTicket.subject}</h2>
                </div>
                <div class="flex flex-wrap gap-2">
                  <span class={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${priorityBadgeClass(selectedTicket.priority)}`}>
                    {selectedTicket.priority_display}
                  </span>
                  <StatusBadge status={selectedTicket.status} label={selectedTicket.status_display} />
                </div>
              </div>
              <p class="mt-3 text-sm leading-6 text-neutral-600">{selectedTicket.description || "No description provided."}</p>
            </div>

            <div class="grid gap-3 sm:grid-cols-2">
              <div class="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-4">
                <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Requester</p>
                <p class="mt-2 text-sm font-medium text-neutral-800">{selectedTicket.requester_name || "-"}</p>
              </div>
              <div class="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-4">
                <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Customer Profile</p>
                <p class="mt-2 text-sm font-medium text-neutral-800">{selectedTicket.customer_name || "-"}</p>
              </div>
              <div class="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-4">
                <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Contact Account</p>
                <p class="mt-2 text-sm font-medium text-neutral-800">{selectedTicket.contact_account_name || "-"}</p>
              </div>
              <div class="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-4">
                <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Assigned Agent</p>
                <p class="mt-2 text-sm font-medium text-neutral-800">{selectedTicket.assigned_agent_name || "Unassigned"}</p>
              </div>
              <div class="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-4">
                <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Department</p>
                <p class="mt-2 text-sm font-medium text-neutral-800">{selectedTicket.department_name || "-"}</p>
              </div>
              <div class="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-4">
                <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">SLA Deadline</p>
                <p class={`mt-2 text-sm font-medium ${selectedTicket.sla_breached ? 'text-red-700' : 'text-neutral-800'}`}>{formatDateTime(selectedTicket.sla_deadline)}</p>
              </div>
              <div class="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-4">
                <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Created</p>
                <p class="mt-2 text-sm font-medium text-neutral-800">{formatDateTime(selectedTicket.created_at)}</p>
              </div>
              <div class="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-4">
                <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Updated</p>
                <p class="mt-2 text-sm font-medium text-neutral-800">{formatRelative(selectedTicket.updated_at)}</p>
              </div>
            </div>

            <div class="space-y-5 rounded-3xl border border-neutral-200 p-5">
              <div>
                <h3 class="text-base font-semibold text-neutral-950">Ticket Actions</h3>
                <p class="mt-1 text-sm text-neutral-500">Assign ownership, change urgency, escalate, and close the ticket.</p>
              </div>

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
                <button type="submit" disabled={isBusy('assign') || !assignAgentId} class="self-end rounded-2xl border border-neutral-800 bg-neutral-800 px-4 py-3 text-sm font-semibold text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60">
                  {isBusy("assign") ? "Assigning..." : "Assign"}
                </button>
              </form>

              <form class="grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto]" onsubmit={handlePriorityChange}>
                <label class="block">
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Change Priority</span>
                  <select bind:value={priorityValue} class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10">
                    {#each lookups?.priorities ?? [] as option}
                      <option value={option.key}>{option.label}</option>
                    {/each}
                  </select>
                </label>
                <button type="submit" disabled={isBusy('priority')} class="self-end rounded-2xl border border-neutral-800 bg-neutral-800 px-4 py-3 text-sm font-semibold text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60">
                  {isBusy("priority") ? "Saving..." : "Update"}
                </button>
              </form>

              <form class="space-y-3" onsubmit={handleEscalate}>
                <label class="block">
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Escalation Reason</span>
                  <textarea bind:value={escalationReason} rows="3" class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10" placeholder="Optional rationale for escalation"></textarea>
                </label>
                <button type="submit" disabled={isBusy('escalate')} class="w-full rounded-2xl border border-rose-300 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700 hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-60">
                  {isBusy("escalate") ? "Escalating..." : "Escalate Ticket"}
                </button>
              </form>

              <form class="space-y-3" onsubmit={handleCloseTicket}>
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
                <button type="submit" disabled={isBusy('close')} class="w-full rounded-2xl border border-emerald-300 bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-700 hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-60">
                  {isBusy("close") ? "Closing..." : "Close Ticket"}
                </button>
              </form>
            </div>

            <div class="space-y-5 rounded-3xl border border-neutral-200 p-5">
              <div>
                <h3 class="text-base font-semibold text-neutral-950">Notes & Replies</h3>
                <p class="mt-1 text-sm text-neutral-500">Capture internal notes and requester-facing responses.</p>
              </div>

              <form class="space-y-3" onsubmit={handleInternalNote}>
                <label class="block">
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Add Internal Note</span>
                  <textarea bind:value={internalNote} rows="3" class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"></textarea>
                </label>
                <button type="submit" disabled={isBusy('internal-note') || !internalNote.trim()} class="w-full rounded-2xl border border-neutral-800 bg-neutral-800 px-4 py-3 text-sm font-semibold text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60">
                  {isBusy("internal-note") ? "Saving..." : "Save Internal Note"}
                </button>
              </form>

              <form class="space-y-3" onsubmit={handleRequesterReply}>
                <label class="block">
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Reply to Requester</span>
                  <textarea bind:value={requesterReply} rows="3" class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"></textarea>
                </label>
                <button type="submit" disabled={isBusy('reply') || !requesterReply.trim()} class="w-full rounded-2xl border border-neutral-800 bg-neutral-800 px-4 py-3 text-sm font-semibold text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60">
                  {isBusy("reply") ? "Sending..." : "Reply to Requester"}
                </button>
              </form>

              <div class="space-y-3">
                <div>
                  <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Internal Notes</p>
                  <div class="mt-3 space-y-2">
                    {#if selectedTicket.internal_notes.length === 0}
                      <p class="rounded-2xl border border-dashed border-neutral-300 bg-neutral-50 px-4 py-4 text-sm text-neutral-500">No internal notes yet.</p>
                    {:else}
                      {#each selectedTicket.internal_notes as note}
                        <div class="rounded-2xl border border-neutral-200 px-4 py-4">
                          <p class="text-sm font-medium text-neutral-800">{note.author_name || 'Unknown author'}</p>
                          <p class="mt-2 text-sm leading-6 text-neutral-600">{note.body}</p>
                          <p class="mt-2 text-xs text-neutral-500">{formatDateTime(note.created_at)}</p>
                        </div>
                      {/each}
                    {/if}
                  </div>
                </div>

                <div>
                  <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Requester Replies</p>
                  <div class="mt-3 space-y-2">
                    {#if selectedTicket.requester_replies.length === 0}
                      <p class="rounded-2xl border border-dashed border-neutral-300 bg-neutral-50 px-4 py-4 text-sm text-neutral-500">No requester-facing replies yet.</p>
                    {:else}
                      {#each selectedTicket.requester_replies as reply}
                        <div class="rounded-2xl border border-neutral-200 px-4 py-4">
                          <p class="text-sm font-medium text-neutral-800">{reply.author_name || 'Unknown author'}</p>
                          <p class="mt-2 text-sm leading-6 text-neutral-600">{reply.body}</p>
                          <p class="mt-2 text-xs text-neutral-500">{formatDateTime(reply.created_at)}</p>
                        </div>
                      {/each}
                    {/if}
                  </div>
                </div>
              </div>
            </div>

            <div class="space-y-5 rounded-3xl border border-neutral-200 p-5">
              <div>
                <h3 class="text-base font-semibold text-neutral-950">Attachments & Related Tickets</h3>
                <p class="mt-1 text-sm text-neutral-500">Attach files and link related incidents or duplicate records.</p>
              </div>

              <form class="space-y-3" onsubmit={handleAttachmentUpload}>
                <label class="block">
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Attachment Label</span>
                  <input bind:value={attachmentLabel} type="text" class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10" placeholder="Screenshot, invoice, log bundle..." />
                </label>
                {#key attachmentInputVersion}
                  <label class="block">
                    <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Attach File</span>
                    <input type="file" onchange={(event) => (attachmentFile = (event.currentTarget as HTMLInputElement).files?.[0] ?? null)} class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 file:mr-4 file:rounded-xl file:border-0 file:bg-neutral-800 file:px-3 file:py-2 file:text-sm file:font-semibold file:text-white" />
                  </label>
                {/key}
                <button type="submit" disabled={isBusy('attachment') || !attachmentFile} class="w-full rounded-2xl border border-neutral-800 bg-neutral-800 px-4 py-3 text-sm font-semibold text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60">
                  {isBusy("attachment") ? "Uploading..." : "Attach File"}
                </button>
              </form>

              <div class="space-y-2">
                {#if selectedTicket.attachments.length === 0}
                  <p class="rounded-2xl border border-dashed border-neutral-300 bg-neutral-50 px-4 py-4 text-sm text-neutral-500">No files attached yet.</p>
                {:else}
                  {#each selectedTicket.attachments as attachment}
                    <a href={attachment.file_url || attachment.file} target="_blank" rel="noreferrer" class="block rounded-2xl border border-neutral-200 px-4 py-4 hover:border-neutral-300 hover:bg-neutral-50">
                      <p class="text-sm font-medium text-neutral-800">{attachment.label || 'Attachment'}</p>
                      <p class="mt-1 text-xs text-neutral-500">{attachment.uploaded_by_name || 'Unknown uploader'} • {formatDateTime(attachment.created_at)}</p>
                    </a>
                  {/each}
                {/if}
              </div>

              <form class="space-y-3" onsubmit={handleLinkTicket}>
                <label class="block">
                  <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Link Related Ticket</span>
                  <input bind:value={relatedTicketRef} type="text" placeholder="Enter ticket reference e.g. SD-000123" class="w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10" />
                </label>
                <button type="submit" disabled={isBusy('link-related') || !relatedTicketRef.trim()} class="w-full rounded-2xl border border-neutral-800 bg-neutral-800 px-4 py-3 text-sm font-semibold text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60">
                  {isBusy("link-related") ? "Linking..." : "Link Related Ticket"}
                </button>
              </form>

              <div class="space-y-2">
                {#if selectedTicket.linked_tickets.length === 0}
                  <p class="rounded-2xl border border-dashed border-neutral-300 bg-neutral-50 px-4 py-4 text-sm text-neutral-500">No related tickets linked yet.</p>
                {:else}
                  {#each selectedTicket.linked_tickets as linkedTicket}
                    <div class="rounded-2xl border border-neutral-200 px-4 py-4">
                      <p class="text-sm font-medium text-neutral-800">{linkedTicket.ticket_id} • {linkedTicket.subject}</p>
                      <p class="mt-1 text-xs text-neutral-500">{linkedTicket.status_display} • {linkedTicket.priority_display}</p>
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

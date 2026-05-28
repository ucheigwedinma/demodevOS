<script lang="ts">
  import { onMount } from "svelte";

  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    PaginatedResponse,
    SupportCommunicationChannel,
    SupportCommunicationDirection,
    SupportCommunicationInteractionType,
    SupportCommunicationLogRecord,
    SupportCommunicationOverview,
    SupportTicketListItem,
  } from "$lib/types";

  type InteractionTypeFilter = "all" | SupportCommunicationInteractionType;
  type ChannelFilter = "all" | SupportCommunicationChannel;
  type DirectionFilter = "all" | SupportCommunicationDirection;

  type ComposeDraft = {
    ticketId: string;
    interactionType: SupportCommunicationInteractionType;
    direction: SupportCommunicationDirection;
    channel: SupportCommunicationChannel;
    subject: string;
    message: string;
    transcript: string;
    participantsText: string;
    callDurationSeconds: string;
    externalMessageId: string;
  };

  type WhatsAppDraft = {
    ticketId: string;
    recipientPhone: string;
    message: string;
    externalMessageId: string;
  };

  const pageSize = 20;

  const interactionTypeOptions: Array<{
    key: SupportCommunicationInteractionType;
    label: string;
  }> = [
    { key: "ticket_conversation", label: "Ticket Conversation" },
    { key: "internal_note", label: "Internal Note" },
    { key: "email_reply", label: "Email Reply" },
    { key: "chat_transcript", label: "Chat Transcript" },
    { key: "call_log", label: "Call Log" },
    { key: "whatsapp", label: "WhatsApp" },
  ];

  const channelOptions: Array<{ key: SupportCommunicationChannel; label: string }> = [
    { key: "portal", label: "Portal" },
    { key: "email", label: "Email" },
    { key: "chat", label: "Chat" },
    { key: "phone", label: "Phone" },
    { key: "whatsapp", label: "WhatsApp" },
    { key: "other", label: "Other" },
  ];

  const directionOptions: Array<{ key: SupportCommunicationDirection; label: string }> = [
    { key: "inbound", label: "Inbound" },
    { key: "outbound", label: "Outbound" },
    { key: "internal", label: "Internal" },
  ];

  let loadingOverview = $state(true);
  let loadingLogs = $state(true);
  let loadingTickets = $state(true);
  let actionKey = $state("");
  let errorMessage = $state("");

  let overview = $state<SupportCommunicationOverview | null>(null);
  let logs = $state<SupportCommunicationLogRecord[]>([]);
  let tickets = $state<SupportTicketListItem[]>([]);

  let currentPage = $state(1);
  let totalCount = $state(0);

  let search = $state("");
  let selectedType = $state<InteractionTypeFilter>("all");
  let selectedChannel = $state<ChannelFilter>("all");
  let selectedDirection = $state<DirectionFilter>("all");
  let selectedTicketFilter = $state("");

  let composeDraft = $state<ComposeDraft>({
    ticketId: "",
    interactionType: "ticket_conversation",
    direction: "outbound",
    channel: "portal",
    subject: "",
    message: "",
    transcript: "",
    participantsText: "",
    callDurationSeconds: "",
    externalMessageId: "",
  });

  let whatsAppDraft = $state<WhatsAppDraft>({
    ticketId: "",
    recipientPhone: "",
    message: "",
    externalMessageId: "",
  });

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

    for (let i = start; i <= end; i += 1) pages.push(i);
    return pages;
  });

  function parseError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      const fieldMessage = Object.values(error.fieldErrors).flat()[0];
      if (fieldMessage) return fieldMessage;
      if (typeof error.data.detail === "string") return error.data.detail;
    }
    return fallback;
  }

  function formatDateTime(value: string): string {
    return new Date(value).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function durationLabel(seconds: number | null): string {
    if (!seconds || seconds <= 0) return "--";
    const minutes = Math.floor(seconds / 60);
    const remainder = seconds % 60;
    if (minutes === 0) return `${remainder}s`;
    if (remainder === 0) return `${minutes}m`;
    return `${minutes}m ${remainder}s`;
  }

  function interactionBadgeClass(interactionType: SupportCommunicationInteractionType): string {
    if (interactionType === "internal_note") return "border-neutral-300 bg-neutral-100 text-neutral-700";
    if (interactionType === "email_reply") return "border-sky-200 bg-sky-50 text-sky-700";
    if (interactionType === "chat_transcript") return "border-indigo-200 bg-indigo-50 text-indigo-700";
    if (interactionType === "call_log") return "border-orange-200 bg-orange-50 text-orange-700";
    if (interactionType === "whatsapp") return "border-emerald-200 bg-emerald-50 text-emerald-700";
    return "border-cyan-200 bg-cyan-50 text-cyan-700";
  }

  function directionBadgeClass(direction: SupportCommunicationDirection): string {
    if (direction === "internal") return "border-neutral-300 bg-neutral-100 text-neutral-700";
    if (direction === "inbound") return "border-violet-200 bg-violet-50 text-violet-700";
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }

  function applyInteractionDefaults(interactionType: SupportCommunicationInteractionType) {
    const defaults: Record<
      SupportCommunicationInteractionType,
      { channel: SupportCommunicationChannel; direction: SupportCommunicationDirection }
    > = {
      ticket_conversation: { channel: "portal", direction: "outbound" },
      internal_note: { channel: "portal", direction: "internal" },
      email_reply: { channel: "email", direction: "outbound" },
      chat_transcript: { channel: "chat", direction: "inbound" },
      call_log: { channel: "phone", direction: "inbound" },
      whatsapp: { channel: "whatsapp", direction: "outbound" },
    };

    composeDraft = {
      ...composeDraft,
      interactionType,
      channel: defaults[interactionType].channel,
      direction: defaults[interactionType].direction,
    };
  }

  function buildLogParams(): Record<string, string> {
    const params: Record<string, string> = {
      page: String(currentPage),
      page_size: String(pageSize),
    };

    if (search.trim()) params.search = search.trim();
    if (selectedType !== "all") params.interaction_type = selectedType;
    if (selectedChannel !== "all") params.channel = selectedChannel;
    if (selectedDirection !== "all") params.direction = selectedDirection;
    if (selectedTicketFilter) params.ticket = selectedTicketFilter;

    return params;
  }

  async function loadOverview() {
    loadingOverview = true;
    try {
      overview = await api.get<SupportCommunicationOverview>(
        "/support-desk/communication/overview/",
      );
    } catch (error) {
      overview = null;
      toast.error(
        "Communication overview unavailable",
        parseError(error, "Could not load communication metrics."),
      );
    } finally {
      loadingOverview = false;
    }
  }

  async function loadTickets() {
    loadingTickets = true;
    try {
      const response = await api.get<PaginatedResponse<SupportTicketListItem>>(
        "/support-desk/tickets/",
        { view: "open", page_size: "200" },
      );
      tickets = response.results;
    } catch (error) {
      tickets = [];
      toast.error(
        "Tickets unavailable",
        parseError(error, "Could not load support tickets for communication linkage."),
      );
    } finally {
      loadingTickets = false;
    }
  }

  async function loadLogs() {
    loadingLogs = true;
    errorMessage = "";

    try {
      const response = await api.get<PaginatedResponse<SupportCommunicationLogRecord>>(
        "/support-desk/communication/logs/",
        buildLogParams(),
      );
      logs = response.results;
      totalCount = response.count;
    } catch (error) {
      logs = [];
      totalCount = 0;
      errorMessage = parseError(error, "Could not load communication logs.");
    } finally {
      loadingLogs = false;
    }
  }

  function handleSearchInput(value: string) {
    search = value;
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
      currentPage = 1;
      void loadLogs();
    }, 240);
  }

  function applyFilters() {
    currentPage = 1;
    void loadLogs();
  }

  function goToPage(pageNumber: number) {
    if (pageNumber === currentPage) return;
    currentPage = pageNumber;
    void loadLogs();
  }

  function parseParticipants(value: string): string[] {
    return value
      .split(/[\n,]+/)
      .map((item) => item.trim())
      .filter(Boolean)
      .slice(0, 40);
  }

  async function createCommunicationLog() {
    const message = composeDraft.message.trim();
    const transcript = composeDraft.transcript.trim();
    if (!message && !transcript) {
      toast.error("Content required", "Provide message or transcript content.");
      return;
    }

    if (composeDraft.interactionType === "call_log" && !composeDraft.callDurationSeconds.trim()) {
      toast.error("Call duration required", "Call log entries require call duration in seconds.");
      return;
    }

    actionKey = "create-log";
    try {
      const payload = {
        ticket: composeDraft.ticketId ? Number(composeDraft.ticketId) : null,
        interaction_type: composeDraft.interactionType,
        direction: composeDraft.direction,
        channel: composeDraft.channel,
        subject: composeDraft.subject.trim(),
        message,
        transcript,
        participants: parseParticipants(composeDraft.participantsText),
        call_duration_seconds: composeDraft.callDurationSeconds
          ? Number(composeDraft.callDurationSeconds)
          : null,
        external_message_id: composeDraft.externalMessageId.trim(),
        metadata: {},
      };

      await api.post<SupportCommunicationLogRecord>("/support-desk/communication/logs/", payload);
      toast.success("Interaction logged", "Communication record has been saved.");

      composeDraft = {
        ...composeDraft,
        subject: "",
        message: "",
        transcript: "",
        participantsText: "",
        callDurationSeconds: "",
        externalMessageId: "",
      };

      currentPage = 1;
      await Promise.all([loadLogs(), loadOverview()]);
    } catch (error) {
      toast.error(
        "Could not save interaction",
        parseError(error, "Communication record creation failed."),
      );
    } finally {
      actionKey = "";
    }
  }

  async function sendWhatsAppMessage() {
    if (!whatsAppDraft.recipientPhone.trim() || !whatsAppDraft.message.trim()) {
      toast.error("Missing fields", "Recipient phone and message are required.");
      return;
    }

    actionKey = "send-whatsapp";
    try {
      const payload = {
        ticket_id: whatsAppDraft.ticketId ? Number(whatsAppDraft.ticketId) : undefined,
        recipient_phone: whatsAppDraft.recipientPhone.trim(),
        message: whatsAppDraft.message.trim(),
        external_message_id: whatsAppDraft.externalMessageId.trim(),
      };

      await api.post<SupportCommunicationLogRecord>(
        "/support-desk/communication/logs/whatsapp/",
        payload,
      );
      toast.success(
        "WhatsApp queued",
        "WhatsApp communication has been recorded and queued.",
      );

      whatsAppDraft = {
        ...whatsAppDraft,
        message: "",
        externalMessageId: "",
      };

      currentPage = 1;
      await Promise.all([loadLogs(), loadOverview()]);
    } catch (error) {
      toast.error(
        "WhatsApp failed",
        parseError(error, "Could not queue WhatsApp communication."),
      );
    } finally {
      actionKey = "";
    }
  }

  onMount(async () => {
    await Promise.all([loadOverview(), loadLogs(), loadTickets()]);
  });
</script>

<div class="space-y-8">
  <section class="space-y-4">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div class="max-w-3xl">
        <h1 class="text-2xl font-bold text-neutral-800">Communication Hub</h1>
        <p class="mt-1 max-w-2xl text-sm text-neutral-500">
          Track ticket conversations, internal notes, email replies, chat transcripts, call logs,
          and WhatsApp interactions in a single operational timeline.
        </p>
      </div>

      <div class="grid w-full max-w-sm gap-3 sm:grid-cols-2">
        <div class="rounded-xl border border-neutral-200 bg-white px-4 py-4">
          <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Total Interactions</p>
          <p class="mt-2 text-2xl font-semibold text-neutral-950">{overview?.total_interactions ?? "--"}</p>
        </div>
        <div class="rounded-xl border border-neutral-200 bg-white px-4 py-4">
          <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">WhatsApp</p>
          <p class="mt-2 text-2xl font-semibold text-neutral-950">{overview?.whatsapp_messages_count ?? "--"}</p>
        </div>
        <div class="rounded-xl border border-neutral-200 bg-white px-4 py-4">
          <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Inbound</p>
          <p class="mt-2 text-2xl font-semibold text-neutral-950">{overview?.inbound_count ?? "--"}</p>
        </div>
        <div class="rounded-xl border border-neutral-200 bg-white px-4 py-4">
          <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Outbound</p>
          <p class="mt-2 text-2xl font-semibold text-neutral-950">{overview?.outbound_count ?? "--"}</p>
        </div>
      </div>
    </div>
  </section>

  <section class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
    <article class="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm">
      <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Ticket Conversations</p>
      <p class="mt-2 text-2xl font-semibold text-neutral-800">{overview?.ticket_conversations_count ?? "--"}</p>
    </article>
    <article class="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm">
      <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Internal Notes</p>
      <p class="mt-2 text-2xl font-semibold text-neutral-800">{overview?.internal_notes_count ?? "--"}</p>
    </article>
    <article class="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm">
      <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Email Replies</p>
      <p class="mt-2 text-2xl font-semibold text-neutral-800">{overview?.email_replies_count ?? "--"}</p>
    </article>
    <article class="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm">
      <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Chat Transcripts</p>
      <p class="mt-2 text-2xl font-semibold text-neutral-800">{overview?.chat_transcripts_count ?? "--"}</p>
    </article>
    <article class="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm">
      <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Call Logs</p>
      <p class="mt-2 text-2xl font-semibold text-neutral-800">{overview?.call_logs_count ?? "--"}</p>
    </article>
    <article class="rounded-2xl border border-neutral-200 bg-white p-4 shadow-sm">
      <p class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Internal Direction</p>
      <p class="mt-2 text-2xl font-semibold text-neutral-800">{overview?.internal_count ?? "--"}</p>
    </article>
  </section>

  <div class="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
    <section class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
      <div class="flex flex-wrap items-end gap-3">
        <label class="block min-w-[210px] flex-1">
          <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Search</span>
          <input
            type="search"
            value={search}
            oninput={(event) => handleSearchInput((event.currentTarget as HTMLInputElement).value)}
            placeholder="ticket id, subject, message, transcript..."
            class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
          />
        </label>

        <label class="block">
          <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Type</span>
          <select
            value={selectedType}
            onchange={(event) => { selectedType = (event.currentTarget as HTMLSelectElement).value as InteractionTypeFilter; applyFilters(); }}
            class="min-w-[190px] rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
          >
            <option value="all">All Types</option>
            {#each interactionTypeOptions as option}
              <option value={option.key}>{option.label}</option>
            {/each}
          </select>
        </label>

        <label class="block">
          <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Channel</span>
          <select
            value={selectedChannel}
            onchange={(event) => { selectedChannel = (event.currentTarget as HTMLSelectElement).value as ChannelFilter; applyFilters(); }}
            class="min-w-[150px] rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
          >
            <option value="all">All Channels</option>
            {#each channelOptions as option}
              <option value={option.key}>{option.label}</option>
            {/each}
          </select>
        </label>

        <label class="block">
          <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Direction</span>
          <select
            value={selectedDirection}
            onchange={(event) => { selectedDirection = (event.currentTarget as HTMLSelectElement).value as DirectionFilter; applyFilters(); }}
            class="min-w-[150px] rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
          >
            <option value="all">All Directions</option>
            {#each directionOptions as option}
              <option value={option.key}>{option.label}</option>
            {/each}
          </select>
        </label>

        <label class="block">
          <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Ticket</span>
          <select
            value={selectedTicketFilter}
            onchange={(event) => { selectedTicketFilter = (event.currentTarget as HTMLSelectElement).value; applyFilters(); }}
            class="min-w-[220px] rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
          >
            <option value="">All Tickets</option>
            {#each tickets as ticket}
              <option value={String(ticket.id)}>{ticket.ticket_id} - {ticket.subject}</option>
            {/each}
          </select>
        </label>
      </div>

      <div class="mt-5 overflow-hidden rounded-2xl border border-neutral-200">
        {#if loadingLogs}
          <div class="flex items-center justify-center py-14">
            <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-800"></div>
          </div>
        {:else if errorMessage}
          <div class="px-6 py-14 text-center">
            <h3 class="text-base font-semibold text-red-900">Communication logs unavailable</h3>
            <p class="mt-2 text-sm text-red-700">{errorMessage}</p>
            <button
              type="button"
              onclick={() => loadLogs()}
              class="mt-4 rounded-xl border border-red-300 bg-white px-4 py-2 text-sm font-semibold text-red-800 hover:bg-red-100"
            >
              Retry
            </button>
          </div>
        {:else if logs.length === 0}
          <div class="px-6 py-14 text-center">
            <h3 class="text-base font-semibold text-neutral-800">No communication records</h3>
            <p class="mt-2 text-sm text-neutral-500">No entries match the current communication filter set.</p>
          </div>
        {:else}
          <div class="overflow-x-auto">
            <table class="min-w-[980px] w-full">
              <thead class="bg-neutral-50">
                <tr>
                  <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Time</th>
                  <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Ticket</th>
                  <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Type</th>
                  <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Direction</th>
                  <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Summary</th>
                  <th class="border-b border-neutral-200 px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-neutral-500">Call Duration</th>
                </tr>
              </thead>
              <tbody>
                {#each logs as log}
                  <tr class="border-b border-neutral-100 bg-white">
                    <td class="px-4 py-4 text-sm text-neutral-700">
                      <p>{formatDateTime(log.happened_at)}</p>
                      <p class="mt-1 text-xs text-neutral-500">{log.author_name || "System"}</p>
                    </td>
                    <td class="px-4 py-4 text-sm text-neutral-700">
                      {#if log.ticket_ref}
                        <p class="font-semibold text-neutral-800">{log.ticket_ref}</p>
                        <p class="mt-1 text-xs text-neutral-500">{log.ticket_subject}</p>
                      {:else}
                        <span class="text-neutral-400">--</span>
                      {/if}
                    </td>
                    <td class="px-4 py-4">
                      <div class="flex flex-wrap gap-2">
                        <span class={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${interactionBadgeClass(log.interaction_type)}`}>
                          {log.interaction_type_display}
                        </span>
                        <span class="inline-flex rounded-full border border-neutral-200 bg-neutral-50 px-2.5 py-1 text-xs font-semibold text-neutral-600">
                          {log.channel_display}
                        </span>
                      </div>
                    </td>
                    <td class="px-4 py-4">
                      <span class={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${directionBadgeClass(log.direction)}`}>
                        {log.direction_display}
                      </span>
                    </td>
                    <td class="px-4 py-4 text-sm text-neutral-700">
                      <p class="font-medium text-neutral-800">{log.subject || "No subject"}</p>
                      <p class="mt-1 text-xs text-neutral-500">{log.message_preview || "--"}</p>
                    </td>
                    <td class="px-4 py-4 text-sm text-neutral-700">{durationLabel(log.call_duration_seconds)}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}
      </div>

      {#if !loadingLogs && totalPages > 1}
        <div class="mt-4 flex flex-wrap items-center justify-between gap-3">
          <p class="text-xs text-neutral-500">
            Showing page {currentPage} of {totalPages} ({totalCount} total)
          </p>
          <div class="flex items-center gap-2">
            <button
              type="button"
              onclick={() => goToPage(Math.max(1, currentPage - 1))}
              disabled={currentPage <= 1}
              class="rounded-lg border border-neutral-200 px-3 py-1.5 text-sm text-neutral-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Prev
            </button>
            {#each pageNumbers as pageNumber}
              <button
                type="button"
                onclick={() => goToPage(pageNumber)}
                class={`rounded-lg border px-3 py-1.5 text-sm ${
                  pageNumber === currentPage
                    ? "border-neutral-800 bg-neutral-800 text-white"
                    : "border-neutral-200 text-neutral-700"
                }`}
              >
                {pageNumber}
              </button>
            {/each}
            <button
              type="button"
              onclick={() => goToPage(Math.min(totalPages, currentPage + 1))}
              disabled={currentPage >= totalPages}
              class="rounded-lg border border-neutral-200 px-3 py-1.5 text-sm text-neutral-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      {/if}
    </section>

    <section class="space-y-6">
      <article class="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
        <h2 class="text-lg font-semibold text-neutral-950">Log Communication</h2>
        <p class="mt-1 text-sm text-neutral-500">Capture ticket conversations, notes, email, chat, and call interactions.</p>

        <div class="mt-4 space-y-3">
          <label class="block">
            <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Ticket</span>
            <select
              value={composeDraft.ticketId}
              onchange={(event) => composeDraft = { ...composeDraft, ticketId: (event.currentTarget as HTMLSelectElement).value }}
              class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
            >
              <option value="">No linked ticket</option>
              {#each tickets as ticket}
                <option value={String(ticket.id)}>{ticket.ticket_id} - {ticket.subject}</option>
              {/each}
            </select>
          </label>

          <div class="grid gap-3 sm:grid-cols-3">
            <label class="block">
              <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Type</span>
              <select
                value={composeDraft.interactionType}
                onchange={(event) => applyInteractionDefaults((event.currentTarget as HTMLSelectElement).value as SupportCommunicationInteractionType)}
                class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
              >
                {#each interactionTypeOptions as option}
                  <option value={option.key}>{option.label}</option>
                {/each}
              </select>
            </label>
            <label class="block">
              <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Channel</span>
              <select
                value={composeDraft.channel}
                onchange={(event) => composeDraft = { ...composeDraft, channel: (event.currentTarget as HTMLSelectElement).value as SupportCommunicationChannel }}
                class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
              >
                {#each channelOptions as option}
                  <option value={option.key}>{option.label}</option>
                {/each}
              </select>
            </label>
            <label class="block">
              <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Direction</span>
              <select
                value={composeDraft.direction}
                onchange={(event) => composeDraft = { ...composeDraft, direction: (event.currentTarget as HTMLSelectElement).value as SupportCommunicationDirection }}
                class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
              >
                {#each directionOptions as option}
                  <option value={option.key}>{option.label}</option>
                {/each}
              </select>
            </label>
          </div>

          <label class="block">
            <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Subject</span>
            <input
              type="text"
              value={composeDraft.subject}
              oninput={(event) => composeDraft = { ...composeDraft, subject: (event.currentTarget as HTMLInputElement).value }}
              class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
            />
          </label>

          <label class="block">
            <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Message</span>
            <textarea
              rows="4"
              value={composeDraft.message}
              oninput={(event) => composeDraft = { ...composeDraft, message: (event.currentTarget as HTMLTextAreaElement).value }}
              class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
            ></textarea>
          </label>

          <div class="grid gap-3 sm:grid-cols-2">
            <label class="block">
              <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Transcript</span>
              <textarea
                rows="3"
                value={composeDraft.transcript}
                oninput={(event) => composeDraft = { ...composeDraft, transcript: (event.currentTarget as HTMLTextAreaElement).value }}
                class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
              ></textarea>
            </label>
            <label class="block">
              <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Participants</span>
              <textarea
                rows="3"
                value={composeDraft.participantsText}
                oninput={(event) => composeDraft = { ...composeDraft, participantsText: (event.currentTarget as HTMLTextAreaElement).value }}
                placeholder="Agent One, user@company.com, +15551234567"
                class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
              ></textarea>
            </label>
          </div>

          <div class="grid gap-3 sm:grid-cols-2">
            <label class="block">
              <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">Call Duration (seconds)</span>
              <input
                type="number"
                min="1"
                value={composeDraft.callDurationSeconds}
                oninput={(event) => composeDraft = { ...composeDraft, callDurationSeconds: (event.currentTarget as HTMLInputElement).value }}
                class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
              />
            </label>
            <label class="block">
              <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">External Message ID</span>
              <input
                type="text"
                value={composeDraft.externalMessageId}
                oninput={(event) => composeDraft = { ...composeDraft, externalMessageId: (event.currentTarget as HTMLInputElement).value }}
                class="w-full rounded-xl border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
              />
            </label>
          </div>

          <button
            type="button"
            onclick={createCommunicationLog}
            disabled={actionKey === "create-log" || loadingTickets}
            class="w-full rounded-xl border border-neutral-800 bg-neutral-800 px-4 py-2.5 text-sm font-semibold text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {actionKey === "create-log" ? "Saving..." : "Save Communication Entry"}
          </button>
        </div>
      </article>

      <article class="rounded-3xl border border-emerald-200 bg-emerald-50 p-6 shadow-sm">
        <h2 class="text-lg font-semibold text-emerald-950">WhatsApp Integration</h2>
        <p class="mt-1 text-sm text-emerald-800/90">Queue outbound WhatsApp support updates and log them automatically.</p>

        <div class="mt-4 space-y-3">
          <label class="block">
            <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700">Ticket</span>
            <select
              value={whatsAppDraft.ticketId}
              onchange={(event) => whatsAppDraft = { ...whatsAppDraft, ticketId: (event.currentTarget as HTMLSelectElement).value }}
              class="w-full rounded-xl border border-emerald-300 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-emerald-800 focus:outline-none focus:ring-2 focus:ring-emerald-800/10"
            >
              <option value="">No linked ticket</option>
              {#each tickets as ticket}
                <option value={String(ticket.id)}>{ticket.ticket_id} - {ticket.subject}</option>
              {/each}
            </select>
          </label>

          <label class="block">
            <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700">Recipient Phone</span>
            <input
              type="text"
              value={whatsAppDraft.recipientPhone}
              oninput={(event) => whatsAppDraft = { ...whatsAppDraft, recipientPhone: (event.currentTarget as HTMLInputElement).value }}
              placeholder="+15551234567"
              class="w-full rounded-xl border border-emerald-300 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-emerald-800 focus:outline-none focus:ring-2 focus:ring-emerald-800/10"
            />
          </label>

          <label class="block">
            <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700">Message</span>
            <textarea
              rows="4"
              value={whatsAppDraft.message}
              oninput={(event) => whatsAppDraft = { ...whatsAppDraft, message: (event.currentTarget as HTMLTextAreaElement).value }}
              class="w-full rounded-xl border border-emerald-300 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-emerald-800 focus:outline-none focus:ring-2 focus:ring-emerald-800/10"
            ></textarea>
          </label>

          <label class="block">
            <span class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700">Provider Message ID (optional)</span>
            <input
              type="text"
              value={whatsAppDraft.externalMessageId}
              oninput={(event) => whatsAppDraft = { ...whatsAppDraft, externalMessageId: (event.currentTarget as HTMLInputElement).value }}
              class="w-full rounded-xl border border-emerald-300 bg-white px-3 py-2 text-sm text-neutral-800 focus:border-emerald-800 focus:outline-none focus:ring-2 focus:ring-emerald-800/10"
            />
          </label>

          <button
            type="button"
            onclick={sendWhatsAppMessage}
            disabled={actionKey === "send-whatsapp"}
            class="w-full rounded-xl border border-emerald-900 bg-emerald-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {actionKey === "send-whatsapp" ? "Queueing..." : "Send WhatsApp Update"}
          </button>
        </div>
      </article>
    </section>
  </div>
</div>

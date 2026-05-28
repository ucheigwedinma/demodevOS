<script lang="ts">
  import { onMount } from "svelte";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    DocumentRecord,
    DocumentSignatureProvider,
    DocumentSignatureProviderOption,
    DocumentSignatureProvidersResponse,
    DocumentSignatureRequestRecord,
    PaginatedResponse,
  } from "$lib/types";

  let loading = $state(true);
  let submitting = $state(false);
  let processingAction = $state<number | null>(null);

  let providers = $state<DocumentSignatureProviderOption[]>([]);
  let defaultProvider = $state<DocumentSignatureProvider>("docusign");
  let documents = $state<DocumentRecord[]>([]);

  let rows = $state<DocumentSignatureRequestRecord[]>([]);
  let totalCount = $state(0);
  let page = $state(1);
  let pageSize = $state(12);

  let filterProvider = $state("");
  let filterStatus = $state("");
  let filterSearch = $state("");

  let form = $state({
    document: "",
    subject: "",
    message: "",
    signers: "",
  });

  let completeTargetId = $state<number | null>(null);
  let completeComments = $state("");
  let completeFile = $state<File | null>(null);

  const totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  const defaultProviderLabel = $derived(
    providers.find((row) => row.key === defaultProvider)?.label || defaultProvider,
  );

  function parseApiError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      const detail = error.data?.detail;
      if (typeof detail === "string" && detail.trim()) return detail;
      const firstFieldError = Object.values(error.fieldErrors)[0]?.[0];
      if (firstFieldError) return firstFieldError;
      if (error.status === 403) return "You do not have permission for this action.";
    }
    return fallback;
  }

  function formatDate(value: string | null): string {
    if (!value) return "--";
    return new Date(value).toLocaleString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function statusClasses(status: DocumentSignatureRequestRecord["status"]): string {
    if (status === "completed") return "bg-emerald-50 text-emerald-700 border-emerald-100";
    if (status === "sent") return "bg-blue-50 text-blue-700 border-blue-100";
    if (status === "cancelled") return "bg-zinc-100 text-zinc-700 border-zinc-200";
    if (status === "failed" || status === "declined") return "bg-red-50 text-red-700 border-red-100";
    return "bg-amber-50 text-amber-700 border-amber-100";
  }

  function parseSignersInput(raw: string) {
    const signerRows = raw
      .split("\n")
      .map((row) => row.trim())
      .filter(Boolean);
    if (signerRows.length === 0) return [];

    return signerRows.map((row, idx) => {
      const [nameRaw, emailRaw, roleRaw, orderRaw] = row.split(",").map((x) => (x ?? "").trim());
      const singleToken = row.includes(",") ? "" : row.trim();
      const resolvedEmail = emailRaw || singleToken;
      if (!resolvedEmail) {
        throw new Error(`Signer row ${idx + 1} is missing email.`);
      }
      return {
        name: nameRaw || resolvedEmail,
        email: resolvedEmail,
        role: roleRaw || "",
        order: Number.parseInt(orderRaw || String(idx + 1), 10) || idx + 1,
        status: "pending",
      };
    });
  }

  async function loadProvidersAndDocuments() {
    const [providerResponse, documentsResponse] = await Promise.all([
      api.get<DocumentSignatureProvidersResponse>("/documents/control/signatures/providers/"),
      api.get<PaginatedResponse<DocumentRecord>>("/documents/records/", {
        page_size: "200",
        ordering: "-created_at",
      }),
    ]);
    providers = providerResponse.providers;
    defaultProvider = providerResponse.default_provider;
    documents = documentsResponse.results;
  }

  async function loadRows() {
    loading = true;
    try {
      const params: Record<string, string> = {
        page: String(page),
        page_size: String(pageSize),
        ordering: "-requested_at",
      };
      if (filterProvider) params.provider = filterProvider;
      if (filterStatus) params.status = filterStatus;
      if (filterSearch.trim()) params.search = filterSearch.trim();

      const response = await api.get<PaginatedResponse<DocumentSignatureRequestRecord>>(
        "/documents/control/signatures/",
        params,
      );
      rows = response.results;
      totalCount = response.count;
    } catch (error) {
      rows = [];
      totalCount = 0;
      toast.error("Load failed", parseApiError(error, "Could not load signature workflows."));
    }
    loading = false;
  }

  async function createRequest(sendNow = false) {
    if (!form.document) {
      toast.error("Validation error", "Select a document.");
      return;
    }

    submitting = true;
    try {
      const signers = parseSignersInput(form.signers);
      const payload = {
        document: Number.parseInt(form.document, 10),
        signers,
        subject: form.subject,
        message: form.message,
      };
      const created = await api.post<DocumentSignatureRequestRecord>("/documents/control/signatures/", payload);
      if (sendNow) {
        await api.post<DocumentSignatureRequestRecord>(`/documents/control/signatures/${created.id}/send/`, {});
      }
      toast.success(
        sendNow ? "Request sent" : "Draft created",
        sendNow
          ? `${defaultProviderLabel} signature request has been dispatched.`
          : "Signature request draft has been created.",
      );
      form.subject = "";
      form.message = "";
      form.signers = "";
      await loadRows();
    } catch (error) {
      const fallback = sendNow
        ? "Could not create and send e-signature request."
        : "Could not create e-signature draft.";
      toast.error("Save failed", parseApiError(error, fallback));
    }
    submitting = false;
  }

  async function sendRequest(row: DocumentSignatureRequestRecord) {
    processingAction = row.id;
    try {
      await api.post(`/documents/control/signatures/${row.id}/send/`, {});
      toast.success("Request sent", `${row.provider_display} request has been sent.`);
      await loadRows();
    } catch (error) {
      toast.error("Action failed", parseApiError(error, "Could not send signature request."));
    }
    processingAction = null;
  }

  async function cancelRequest(row: DocumentSignatureRequestRecord) {
    processingAction = row.id;
    try {
      await api.post(`/documents/control/signatures/${row.id}/cancel/`, {});
      toast.success("Request cancelled", "Signature request has been cancelled.");
      await loadRows();
    } catch (error) {
      toast.error("Action failed", parseApiError(error, "Could not cancel signature request."));
    }
    processingAction = null;
  }

  async function submitCompletion() {
    if (!completeTargetId) return;
    processingAction = completeTargetId;
    try {
      const payload = new FormData();
      payload.append("comments", completeComments);
      if (completeFile) payload.append("signed_file", completeFile);
      await api.upload(`/documents/control/signatures/${completeTargetId}/complete/`, payload);
      toast.success("Completed", "Signature request marked as completed.");
      completeTargetId = null;
      completeComments = "";
      completeFile = null;
      await loadRows();
    } catch (error) {
      toast.error("Action failed", parseApiError(error, "Could not complete signature request."));
    }
    processingAction = null;
  }

  function goToPage(nextPage: number) {
    if (nextPage < 1 || nextPage > totalPages) return;
    page = nextPage;
    void loadRows();
  }

  onMount(async () => {
    try {
      await loadProvidersAndDocuments();
    } catch (error) {
      toast.error("Load failed", parseApiError(error, "Could not load signature options."));
    }
    await loadRows();
  });
</script>

<div class="space-y-6">
  <div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900">E-Signature Workflows</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Signature requests run with the default provider configured in Settings. Users execute requests here without policy configuration.
      </p>
    </div>
    <a
      href="/settings/document-automation"
      class="inline-flex items-center rounded-lg border border-neutral-200 px-3 py-2 text-sm font-semibold text-neutral-700 transition-colors hover:border-neutral-300 hover:text-neutral-900"
    >
      Configure Document Automation
    </a>
  </div>

  <div class="rounded-xl border border-neutral-200 bg-white p-5">
    <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Create Signature Request</h2>
    <div class="mt-2 rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs text-neutral-600">
      Default provider for new requests: <span class="font-semibold text-neutral-800">{defaultProviderLabel}</span>
    </div>
    <div class="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      <div class="xl:col-span-2">
        <label class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Document</label>
        <select
          bind:value={form.document}
          class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
        >
          <option value="">Select document</option>
          {#each documents as doc}
            <option value={String(doc.id)}>{doc.document_number} — {doc.title}</option>
          {/each}
        </select>
      </div>
      <div>
        <label class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Subject</label>
        <input
          type="text"
          bind:value={form.subject}
          placeholder="Signature Request"
          class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
        />
      </div>
      <div>
        <label class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Mode</label>
        <div class="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2.5 text-sm text-neutral-600">Provider fixed by settings</div>
      </div>
      <div class="md:col-span-2 xl:col-span-3">
        <label class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Message</label>
        <textarea
          rows="2"
          bind:value={form.message}
          placeholder="Please review and sign this document."
          class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
        />
      </div>
      <div class="md:col-span-2 xl:col-span-4">
        <label class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Signers</label>
        <textarea
          rows="3"
          bind:value={form.signers}
          placeholder="One signer per line: Name,email,Role,Order"
          class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
        />
      </div>
    </div>
    <div class="mt-4 flex flex-wrap items-center gap-2">
      <button
        type="button"
        onclick={() => createRequest(false)}
        disabled={submitting}
        class="rounded-lg border border-neutral-200 px-3 py-2 text-sm font-semibold text-neutral-700 transition-colors hover:border-neutral-300 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {submitting ? "Saving..." : "Create Draft"}
      </button>
      <button
        type="button"
        onclick={() => createRequest(true)}
        disabled={submitting}
        class="rounded-lg bg-neutral-900 px-3 py-2 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {submitting ? "Sending..." : "Create & Send"}
      </button>
    </div>
  </div>

  {#if completeTargetId}
    <div class="rounded-xl border border-neutral-200 bg-white p-5">
      <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Complete Signature Request #{completeTargetId}</h2>
      <div class="mt-3 grid gap-3 md:grid-cols-2">
        <div>
          <label class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Completion Notes</label>
          <textarea
            rows="3"
            bind:value={completeComments}
            class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
          />
        </div>
        <div>
          <label class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Signed File (Optional)</label>
          <input
            type="file"
            onchange={(event) => {
              const target = event.currentTarget as HTMLInputElement;
              completeFile = target.files?.[0] ?? null;
            }}
            class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm"
          />
        </div>
      </div>
      <div class="mt-4 flex items-center gap-2">
        <button
          type="button"
          onclick={submitCompletion}
          disabled={processingAction === completeTargetId}
          class="rounded-lg bg-neutral-900 px-3 py-2 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {processingAction === completeTargetId ? "Saving..." : "Mark Completed"}
        </button>
        <button
          type="button"
          onclick={() => {
            completeTargetId = null;
            completeComments = "";
            completeFile = null;
          }}
          class="rounded-lg border border-neutral-200 px-3 py-2 text-sm font-semibold text-neutral-700 transition-colors hover:border-neutral-300 hover:text-neutral-900"
        >
          Cancel
        </button>
      </div>
    </div>
  {/if}

  <div class="rounded-xl border border-neutral-200 bg-white">
    <div class="border-b border-neutral-200 px-5 py-4">
      <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Signature Requests</h2>
    </div>
    <div class="grid gap-3 border-b border-neutral-200 px-5 py-4 md:grid-cols-4">
      <input
        type="text"
        bind:value={filterSearch}
        placeholder="Search number, title, envelope..."
        class="rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
      />
      <select
        bind:value={filterProvider}
        class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
      >
        <option value="">All providers</option>
        {#each providers as provider}
          <option value={provider.key}>{provider.label}</option>
        {/each}
      </select>
      <select
        bind:value={filterStatus}
        class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
      >
        <option value="">All statuses</option>
        <option value="draft">Draft</option>
        <option value="sent">Sent</option>
        <option value="completed">Completed</option>
        <option value="declined">Declined</option>
        <option value="cancelled">Cancelled</option>
        <option value="failed">Failed</option>
      </select>
      <button
        type="button"
        onclick={() => {
          page = 1;
          void loadRows();
        }}
        class="rounded-lg border border-neutral-200 px-3 py-2.5 text-sm font-medium text-neutral-700 transition-colors hover:border-neutral-300 hover:text-neutral-900"
      >
        Apply Filters
      </button>
    </div>
    {#if loading}
      <div class="py-14 text-center">
        <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
      </div>
    {:else if rows.length === 0}
      <div class="py-14 text-center text-sm text-neutral-400">No signature requests found.</div>
    {:else}
      <div class="overflow-x-auto">
        <table class="min-w-[980px] w-full text-sm">
          <thead>
            <tr class="border-b border-neutral-200">
              <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Document</th>
              <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Provider</th>
              <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Status</th>
              <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Requested</th>
              <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Envelope</th>
              <th class="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each rows as row}
              <tr>
                <td class="px-5 py-3.5">
                  <div class="font-medium text-neutral-900">{row.document_number}</div>
                  <div class="mt-0.5 text-xs text-neutral-500">{row.document_title}</div>
                </td>
                <td class="px-5 py-3.5 text-neutral-700">{row.provider_display}</td>
                <td class="px-5 py-3.5">
                  <span class={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-semibold ${statusClasses(row.status)}`}>
                    {row.status_display}
                  </span>
                </td>
                <td class="px-5 py-3.5 text-neutral-600">{formatDate(row.requested_at)}</td>
                <td class="px-5 py-3.5 text-neutral-600">{row.provider_envelope_id || "--"}</td>
                <td class="px-5 py-3.5">
                  <div class="flex justify-end gap-2">
                    {#if row.status === "draft" || row.status === "failed"}
                      <button
                        type="button"
                        onclick={() => sendRequest(row)}
                        disabled={processingAction === row.id}
                        class="rounded-lg border border-neutral-200 px-2.5 py-1.5 text-xs font-semibold text-neutral-700 transition-colors hover:border-neutral-300 hover:text-neutral-900 disabled:cursor-not-allowed disabled:opacity-45"
                      >
                        Send
                      </button>
                    {/if}
                    {#if row.status === "sent" || row.status === "declined"}
                      <button
                        type="button"
                        onclick={() => {
                          completeTargetId = row.id;
                          completeComments = "";
                          completeFile = null;
                        }}
                        class="rounded-lg border border-neutral-200 px-2.5 py-1.5 text-xs font-semibold text-neutral-700 transition-colors hover:border-neutral-300 hover:text-neutral-900"
                      >
                        Complete
                      </button>
                    {/if}
                    {#if row.status !== "completed" && row.status !== "cancelled"}
                      <button
                        type="button"
                        onclick={() => cancelRequest(row)}
                        disabled={processingAction === row.id}
                        class="rounded-lg border border-red-200 px-2.5 py-1.5 text-xs font-semibold text-red-700 transition-colors hover:border-red-300 hover:text-red-800 disabled:cursor-not-allowed disabled:opacity-45"
                      >
                        Cancel
                      </button>
                    {/if}
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}

    <div class="flex items-center justify-between border-t border-neutral-200 px-5 py-3 text-xs text-neutral-500">
      <div>
        Showing {(totalCount === 0 ? 0 : (page - 1) * pageSize + 1)}-
        {Math.min(page * pageSize, totalCount)} of {totalCount}
      </div>
      <div class="flex items-center gap-2">
        <button
          type="button"
          onclick={() => goToPage(page - 1)}
          disabled={page <= 1}
          class="rounded border border-neutral-200 px-2 py-1 disabled:cursor-not-allowed disabled:opacity-45"
        >
          Prev
        </button>
        <span>Page {page} / {totalPages}</span>
        <button
          type="button"
          onclick={() => goToPage(page + 1)}
          disabled={page >= totalPages}
          class="rounded border border-neutral-200 px-2 py-1 disabled:cursor-not-allowed disabled:opacity-45"
        >
          Next
        </button>
      </div>
    </div>
  </div>
</div>

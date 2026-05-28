<script lang="ts">
  import { page } from "$app/stores";
  import { api } from "$lib/api";
  import Breadcrumb from "$lib/components/Breadcrumb.svelte";
  import DocumentMetadataPanel from "$lib/components/documents/DocumentMetadataPanel.svelte";
  import DocumentLinkedEntities from "$lib/components/documents/DocumentLinkedEntities.svelte";
  import DocumentVersionTimeline from "$lib/components/documents/DocumentVersionTimeline.svelte";
  import DocumentApprovalHistory from "$lib/components/documents/DocumentApprovalHistory.svelte";
  import DocumentExpiryTracker from "$lib/components/documents/DocumentExpiryTracker.svelte";
  import DocumentAuditTrail from "$lib/components/documents/DocumentAuditTrail.svelte";
  import type {
    DocumentApprovalRecord,
    DocumentAuditEventRecord,
    DocumentExpiryRecord,
    DocumentRecord,
    DocumentVersionRecord,
    PaginatedResponse,
  } from "$lib/types";

  const documentId = $derived($page.params.id);
  const refPath = $derived($page.url.searchParams.get("ref"));

  let loading = $state(true);
  let documentRecord = $state<DocumentRecord | null>(null);
  let versions = $state<DocumentVersionRecord[]>([]);
  let approvals = $state<DocumentApprovalRecord[]>([]);
  let auditEvents = $state<DocumentAuditEventRecord[]>([]);
  let expiry = $state<DocumentExpiryRecord | null>(null);
  let eventTypeFilter = $state("all");
  let actorFilter = $state("");

  const eventTypeOptions = $derived.by(() => {
    const values = new Set<string>();
    for (const event of auditEvents) values.add(event.event_type);
    return Array.from(values).sort();
  });

  const filteredAuditEvents = $derived.by(() => {
    const actorQuery = actorFilter.trim().toLowerCase();
    return auditEvents
      .filter((event) => eventTypeFilter === "all" || event.event_type === eventTypeFilter)
      .filter((event) => {
        if (!actorQuery) return true;
        return (
          event.actor_name.toLowerCase().includes(actorQuery) ||
          (event.actor_email || "").toLowerCase().includes(actorQuery) ||
          (event.actor_role_name || "").toLowerCase().includes(actorQuery)
        );
      })
      .map((event) => ({
        id: event.id,
        timestamp: event.created_at,
        event_type: event.event_type,
        actor: event.actor_name,
        actor_role: event.actor_role_name || null,
        ip_address: event.ip_address,
        summary: event.summary,
      }));
  });

  async function loadDocumentDetails() {
    loading = true;
    try {
      const [
        metadata,
        versionsRes,
        auditRes,
        expiryRes,
      ] = await Promise.all([
        api.get<DocumentRecord>(`/documents/records/${documentId}/`),
        api.get<PaginatedResponse<DocumentVersionRecord>>("/documents/control/versions/", {
          document: String(documentId),
          ordering: "-uploaded_at",
          page_size: "100",
        }),
        api.get<PaginatedResponse<DocumentAuditEventRecord>>("/documents/control/audit-events/", {
          document: String(documentId),
          ordering: "-created_at",
          page_size: "100",
        }),
        api.get<PaginatedResponse<DocumentExpiryRecord>>("/documents/control/expiries/", {
          document: String(documentId),
          page_size: "1",
        }),
      ]);

      documentRecord = metadata;
      versions = versionsRes.results;
      auditEvents = auditRes.results;
      expiry = expiryRes.results[0] ?? null;

      if (versionsRes.results.length > 0) {
        const approvalBatches = await Promise.all(
          versionsRes.results.map((version) =>
            api.get<PaginatedResponse<DocumentApprovalRecord>>("/documents/control/approvals/", {
              document_version: String(version.id),
              ordering: "-timestamp",
              page_size: "100",
            })
          )
        );
        approvals = approvalBatches
          .flatMap((batch) => batch.results)
          .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
      } else {
        approvals = [];
      }
    } catch {
      documentRecord = null;
      versions = [];
      approvals = [];
      auditEvents = [];
      expiry = null;
    }
    loading = false;
  }

  $effect(() => {
    void documentId;
    loadDocumentDetails();
  });
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
  </div>
{:else if !documentRecord}
  <div class="text-center py-24">
    <p class="text-neutral-400">Document not found.</p>
    <a href={refPath ?? "/documents/repository"} class="mt-4 inline-block text-sm font-medium text-neutral-900 hover:underline">{refPath ? "Go back" : "Back to repository"}</a>
  </div>
{:else}
  <div class="space-y-6">
    <div>
      <Breadcrumb items={refPath?.startsWith("/projects")
        ? [
            { label: "Projects", href: "/projects" },
            { label: documentRecord.project_name || "Project", href: refPath },
            { label: documentRecord.document_number },
          ]
        : [{ label: "Documents", href: "/documents/repository" }, { label: documentRecord.document_number }]
      } />
      <h1 class="text-2xl font-bold text-neutral-900 mt-3">{documentRecord.title}</h1>
      <p class="mt-1 text-sm text-neutral-500">Document Detail Page</p>
    </div>

    <DocumentMetadataPanel document={documentRecord} />

    <div class="grid xl:grid-cols-3 gap-6">
      <div class="xl:col-span-2 space-y-6">
        <DocumentVersionTimeline versions={versions} />
        <DocumentApprovalHistory approvals={approvals} />
      </div>
      <div class="space-y-6">
        <DocumentLinkedEntities document={documentRecord} />
        <DocumentExpiryTracker expiry={expiry} />
      </div>
    </div>

    <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-4">
      <div class="flex flex-col md:flex-row gap-3 md:items-center md:justify-between">
        <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Activity Timeline Filters</h3>
        <div class="flex flex-col sm:flex-row gap-3 w-full md:w-auto">
          <select
            bind:value={eventTypeFilter}
            class="rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-700
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            <option value="all">All Event Types</option>
            {#each eventTypeOptions as eventType}
              <option value={eventType}>{eventType.split("_").join(" ")}</option>
            {/each}
          </select>
          <input
            type="text"
            bind:value={actorFilter}
            placeholder="Filter by actor or role"
            class="rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-700
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          />
        </div>
      </div>
    </div>

    <DocumentAuditTrail events={filteredAuditEvents} />
  </div>
{/if}

<script lang="ts">
  import { api } from "$lib/api";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import DocumentMetadataPanel from "./DocumentMetadataPanel.svelte";
  import DocumentVersionTimeline from "./DocumentVersionTimeline.svelte";
  import DocumentExpiryTracker from "./DocumentExpiryTracker.svelte";
  import type {
    DocumentRecord,
    DocumentVersionRecord,
    DocumentExpiryRecord,
    PaginatedResponse,
  } from "$lib/types";

  let {
    open = false,
    documentId = null,
    refPath = "",
    onclose,
  }: {
    open?: boolean;
    documentId?: number | null;
    refPath?: string;
    onclose?: () => void;
  } = $props();

  let loading = $state(true);
  let doc = $state<DocumentRecord | null>(null);
  let versions = $state<DocumentVersionRecord[]>([]);
  let expiry = $state<DocumentExpiryRecord | null>(null);

  let loadedDocId: number | null = null;

  $effect(() => {
    if (open && documentId && documentId !== loadedDocId) {
      loadedDocId = documentId;
      loadData(documentId);
    }
    if (!open) {
      loadedDocId = null;
    }
  });

  async function loadData(id: number) {
    loading = true;
    doc = null;
    versions = [];
    expiry = null;
    try {
      const [metadata, versionsRes, expiryRes] = await Promise.all([
        api.get<DocumentRecord>(`/documents/records/${id}/`),
        api.get<PaginatedResponse<DocumentVersionRecord>>("/documents/control/versions/", {
          document: String(id),
          ordering: "-uploaded_at",
          page_size: "20",
        }),
        api.get<PaginatedResponse<DocumentExpiryRecord>>("/documents/control/expiries/", {
          document: String(id),
          page_size: "1",
        }),
      ]);
      doc = metadata;
      versions = versionsRes.results;
      expiry = expiryRes.results[0] ?? null;
    } catch {
      doc = null;
    }
    loading = false;
  }

  function handleBackdropClick() {
    onclose?.();
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "Escape") onclose?.();
  }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if open}
  <!-- Backdrop -->
  <div
    class="fixed inset-0 bg-black/30 z-998 transition-opacity"
    onclick={handleBackdropClick}
    role="presentation"
  ></div>

  <!-- Drawer -->
  <div
    class="fixed inset-y-0 right-0 z-999 w-full max-w-[560px] bg-white shadow-2xl
           flex flex-col overflow-hidden animate-slide-in"
    role="dialog"
    aria-modal="true"
    aria-label="Document details"
  >
    <!-- Header -->
    <div class="flex items-center justify-between px-6 py-5 bg-linear-to-br from-neutral-900 to-neutral-800">
      <div class="min-w-0 flex-1">
        {#if loading}
          <div class="h-5 w-48 bg-white/10 rounded animate-pulse"></div>
          <div class="h-3.5 w-32 bg-white/5 rounded animate-pulse mt-1.5"></div>
        {:else if doc}
          <h2 class="text-base font-semibold text-white truncate">{doc.title}</h2>
          <p class="text-xs text-neutral-400 mt-0.5 flex items-center gap-2">
            {doc.document_number}
            <StatusBadge status={doc.status} size="sm" />
          </p>
        {:else}
          <h2 class="text-base font-semibold text-neutral-500">Document not found</h2>
        {/if}
      </div>

      <div class="flex items-center gap-2 ml-4 shrink-0">
        {#if doc}
          <a
            href="/documents/{doc.id}{refPath ? `?ref=${encodeURIComponent(refPath)}` : ''}"
            class="inline-flex items-center gap-1.5 rounded-lg border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-medium text-white hover:bg-white/20 transition-colors"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
            </svg>
            Full page
          </a>
        {/if}
        <button
          onclick={() => onclose?.()}
          class="w-8 h-8 flex items-center justify-center rounded-lg text-neutral-400 hover:text-white transition-colors"
          aria-label="Close"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Body -->
    <div class="flex-1 overflow-y-auto">
      {#if loading}
        <div class="flex items-center justify-center py-20">
          <div class="inline-block w-5 h-5 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
          <span class="ml-3 text-sm text-neutral-400">Loading document...</span>
        </div>
      {:else if !doc}
        <div class="text-center py-20">
          <p class="text-sm text-neutral-400">Could not load document details.</p>
        </div>
      {:else}
        <div class="p-6 space-y-5">
          <DocumentMetadataPanel document={doc} />
          <DocumentVersionTimeline {versions} />
          <DocumentExpiryTracker {expiry} />
        </div>
      {/if}
    </div>
  </div>
{/if}

<style>
  @keyframes slideIn {
    from { transform: translateX(100%); }
    to   { transform: translateX(0); }
  }
  .animate-slide-in {
    animation: slideIn 0.2s ease-out;
  }
</style>

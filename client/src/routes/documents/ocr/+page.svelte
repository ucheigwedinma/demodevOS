<script lang="ts">
  import { onMount } from "svelte";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    DocumentSearchIndexContentRecord,
    DocumentSearchIndexRecord,
    PaginatedResponse,
  } from "$lib/types";

  let loading = $state(true);
  let rebuildingAll = $state(false);
  let search = $state("");
  let statusFilter = $state<"" | "pending" | "indexed" | "failed">("");
  let page = $state(1);
  let pageSize = $state(15);
  let totalCount = $state(0);
  let rows = $state<DocumentSearchIndexRecord[]>([]);

  let selectedIndexId = $state<number | null>(null);
  let selectedContent = $state<DocumentSearchIndexContentRecord | null>(null);
  let loadingContent = $state(false);
  let contentView = $state<"extracted" | "ocr" | "clauses">("extracted");

  const totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  const hasRows = $derived(rows.length > 0);

  function parseApiError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      const detail = error.data?.detail;
      if (typeof detail === "string" && detail.trim()) return detail;
      if (error.status === 403) return "You do not have permission for this action.";
    }
    return fallback;
  }

  async function loadRows() {
    loading = true;
    try {
      const params: Record<string, string> = {
        page: String(page),
        page_size: String(pageSize),
        ordering: "-indexed_at",
      };
      if (statusFilter) params.index_status = statusFilter;
      if (search.trim()) params.search = search.trim();
      const response = await api.get<PaginatedResponse<DocumentSearchIndexRecord>>("/documents/search-index/", params);
      rows = response.results;
      totalCount = response.count;
    } catch (error) {
      rows = [];
      totalCount = 0;
      toast.error("Load failed", parseApiError(error, "Could not load OCR index records."));
    }
    loading = false;
  }

  async function rebuildAll() {
    rebuildingAll = true;
    try {
      await api.post("/documents/search-index/rebuild/", { force: true });
      toast.success("Rebuild started", "Document search index rebuild completed.");
      await loadRows();
    } catch (error) {
      toast.error("Rebuild failed", parseApiError(error, "Could not rebuild search index."));
    }
    rebuildingAll = false;
  }

  async function rebuildDocument(documentId: number) {
    try {
      await api.post("/documents/search-index/rebuild/", { document_id: documentId, force: true });
      toast.success("Reindexed", `Document #${documentId} was reindexed.`);
      await loadRows();
      if (selectedContent?.document === documentId && selectedIndexId) {
        await openContent(selectedIndexId);
      }
    } catch (error) {
      toast.error("Reindex failed", parseApiError(error, "Could not reindex selected document."));
    }
  }

  async function openContent(indexId: number) {
    selectedIndexId = indexId;
    loadingContent = true;
    try {
      selectedContent = await api.get<DocumentSearchIndexContentRecord>(`/documents/search-index/${indexId}/content/`);
    } catch (error) {
      selectedContent = null;
      toast.error("Load failed", parseApiError(error, "Could not load OCR content preview."));
    }
    loadingContent = false;
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

  function statusClasses(status: DocumentSearchIndexRecord["index_status"]): string {
    if (status === "indexed") return "bg-emerald-50 text-emerald-700 border-emerald-100";
    if (status === "failed") return "bg-red-50 text-red-700 border-red-100";
    return "bg-amber-50 text-amber-700 border-amber-100";
  }

  function excerpt(value: string, length = 260): string {
    if (!value) return "";
    if (value.length <= length) return value;
    return `${value.slice(0, length)}...`;
  }

  function textBlockForView(content: DocumentSearchIndexContentRecord | null): string {
    if (!content) return "";
    if (contentView === "ocr") return content.ocr_text || "";
    if (contentView === "clauses") return content.clause_text || "";
    return content.extracted_text || "";
  }

  function goToPage(nextPage: number) {
    if (nextPage < 1 || nextPage > totalPages) return;
    page = nextPage;
    void loadRows();
  }

  onMount(() => {
    void loadRows();
  });
</script>

<div class="space-y-6">
  <div class="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900">OCR & Extraction</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Review extracted document text, inspect OCR quality, and trigger targeted or full reindexing.
      </p>
    </div>
    <button
      type="button"
      onclick={rebuildAll}
      disabled={rebuildingAll}
      class="inline-flex items-center justify-center rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-50"
    >
      {#if rebuildingAll}
        Rebuilding...
      {:else}
        Rebuild Full Index
      {/if}
    </button>
  </div>

  <div class="grid gap-3 rounded-xl border border-neutral-200 bg-white p-4 md:grid-cols-4">
    <input
      type="text"
      bind:value={search}
      placeholder="Search document number or title"
      class="rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
    />
    <select
      bind:value={statusFilter}
      class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
    >
      <option value="">All statuses</option>
      <option value="pending">Pending</option>
      <option value="indexed">Indexed</option>
      <option value="failed">Failed</option>
    </select>
    <select
      bind:value={pageSize}
      class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
    >
      <option value={10}>10 per page</option>
      <option value={15}>15 per page</option>
      <option value={25}>25 per page</option>
      <option value={50}>50 per page</option>
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

  <div class="grid gap-6 xl:grid-cols-[1.45fr_1fr]">
    <div class="overflow-hidden rounded-xl border border-neutral-200 bg-white">
      <div class="border-b border-neutral-200 px-5 py-4">
        <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Index Records</h2>
      </div>
      {#if loading}
        <div class="py-14 text-center">
          <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
        </div>
      {:else if !hasRows}
        <div class="py-14 text-center text-sm text-neutral-400">No indexed documents match your filters.</div>
      {:else}
        <div class="overflow-x-auto">
          <table class="min-w-[860px] w-full text-sm">
            <thead>
              <tr class="border-b border-neutral-200">
                <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Document</th>
                <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Status</th>
                <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Indexed At</th>
                <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Errors</th>
                <th class="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each rows as row}
                <tr class={selectedIndexId === row.id ? "bg-neutral-50" : ""}>
                  <td class="px-5 py-3.5">
                    <div class="font-medium text-neutral-900">{row.document_number}</div>
                    <div class="mt-0.5 text-xs text-neutral-500">{excerpt(row.document_title, 80)}</div>
                  </td>
                  <td class="px-5 py-3.5">
                    <span class={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-semibold ${statusClasses(row.index_status)}`}>
                      {row.index_status}
                    </span>
                  </td>
                  <td class="px-5 py-3.5 text-neutral-600">{formatDate(row.indexed_at)}</td>
                  <td class="px-5 py-3.5 text-xs text-neutral-500">{excerpt(row.error_message || "--", 72)}</td>
                  <td class="px-5 py-3.5">
                    <div class="flex justify-end gap-2">
                      <button
                        type="button"
                        onclick={() => openContent(row.id)}
                        class="rounded-lg border border-neutral-200 px-2.5 py-1.5 text-xs font-semibold text-neutral-700 transition-colors hover:border-neutral-300 hover:text-neutral-900"
                      >
                        Preview
                      </button>
                      <button
                        type="button"
                        onclick={() => rebuildDocument(row.document)}
                        class="rounded-lg border border-neutral-200 px-2.5 py-1.5 text-xs font-semibold text-neutral-700 transition-colors hover:border-neutral-300 hover:text-neutral-900"
                      >
                        Reindex
                      </button>
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
            class="rounded border border-neutral-200 px-2 py-1 text-neutral-600 disabled:cursor-not-allowed disabled:opacity-45"
          >
            Prev
          </button>
          <span>Page {page} / {totalPages}</span>
          <button
            type="button"
            onclick={() => goToPage(page + 1)}
            disabled={page >= totalPages}
            class="rounded border border-neutral-200 px-2 py-1 text-neutral-600 disabled:cursor-not-allowed disabled:opacity-45"
          >
            Next
          </button>
        </div>
      </div>
    </div>

    <div class="overflow-hidden rounded-xl border border-neutral-200 bg-white">
      <div class="border-b border-neutral-200 px-5 py-4">
        <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Extraction Preview</h2>
      </div>
      {#if loadingContent}
        <div class="py-14 text-center">
          <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
        </div>
      {:else if !selectedContent}
        <div class="px-5 py-12 text-center text-sm text-neutral-400">
          Select an index row and click <span class="font-semibold text-neutral-600">Preview</span>.
        </div>
      {:else}
        <div class="space-y-4 p-5">
          <div>
            <div class="text-sm font-semibold text-neutral-900">{selectedContent.document_number}</div>
            <div class="mt-0.5 text-xs text-neutral-500">{selectedContent.document_title}</div>
            <div class="mt-1 text-xs text-neutral-500">Version {selectedContent.version_label || "--"}</div>
          </div>
          <div class="flex flex-wrap gap-2">
            <button
              type="button"
              onclick={() => (contentView = "extracted")}
              class={`rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition-colors ${
                contentView === "extracted"
                  ? "border-neutral-900 bg-neutral-900 text-white"
                  : "border-neutral-200 text-neutral-700 hover:border-neutral-300 hover:text-neutral-900"
              }`}
            >
              PDF Text
            </button>
            <button
              type="button"
              onclick={() => (contentView = "ocr")}
              class={`rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition-colors ${
                contentView === "ocr"
                  ? "border-neutral-900 bg-neutral-900 text-white"
                  : "border-neutral-200 text-neutral-700 hover:border-neutral-300 hover:text-neutral-900"
              }`}
            >
              OCR Text
            </button>
            <button
              type="button"
              onclick={() => (contentView = "clauses")}
              class={`rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition-colors ${
                contentView === "clauses"
                  ? "border-neutral-900 bg-neutral-900 text-white"
                  : "border-neutral-200 text-neutral-700 hover:border-neutral-300 hover:text-neutral-900"
              }`}
            >
              Clauses
            </button>
          </div>
          <textarea
            readonly
            value={textBlockForView(selectedContent)}
            class="h-[360px] w-full resize-none rounded-lg border border-neutral-200 bg-neutral-50 p-3 text-xs leading-5 text-neutral-700"
          />
        </div>
      {/if}
    </div>
  </div>
</div>

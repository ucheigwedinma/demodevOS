<script lang="ts">
  import { api } from "$lib/api";
  import { parsePortalError } from "$lib/partnerPortal";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    PaginatedResponse,
    PartnerPortalContextResponse,
    PartnerPortalDocumentItem,
  } from "$lib/types";

  let loading = $state(true);
  let context = $state<PartnerPortalContextResponse | null>(null);
  let rows = $state<PartnerPortalDocumentItem[]>([]);
  let page = $state(1);
  let pageSize = $state(20);
  let count = $state(0);
  let query = $state("");
  let statusFilter = $state("");
  let confidentialityFilter = $state("");

  const totalPages = $derived(Math.max(1, Math.ceil(count / pageSize)));

  function titleCase(value: string): string {
    return value
      .replaceAll("_", " ")
      .split(" ")
      .filter(Boolean)
      .map((part) => part[0]?.toUpperCase() + part.slice(1))
      .join(" ");
  }

  async function loadContext() {
    context = await api.get<PartnerPortalContextResponse>("/partners/portal/context/");
  }

  async function loadDocuments() {
    loading = true;
    try {
      if (!context) {
        await loadContext();
      }
      if (context && !context.is_partner_user && !context.is_preview_mode) {
        rows = [];
        count = 0;
        return;
      }
      const response = await api.get<PaginatedResponse<PartnerPortalDocumentItem>>(
        "/partners/portal/documents/",
        {
          page: String(page),
          page_size: String(pageSize),
          q: query.trim(),
          status: statusFilter,
          confidentiality: confidentialityFilter,
          ordering: "-created_at",
        },
      );
      rows = response.results;
      count = response.count;
    } catch (error) {
      toast.error("Load failed", parsePortalError(error, "Could not load portal documents."));
    } finally {
      loading = false;
    }
  }

  function runSearch() {
    page = 1;
    loadDocuments();
  }

  $effect(() => {
    loadDocuments();
  });
</script>

{#if context && !context.is_partner_user && !context.is_preview_mode}
  <div class="rounded-xl border border-amber-200 bg-amber-50 px-6 py-5">
    <h1 class="text-lg font-semibold text-amber-900">No document access yet</h1>
    <p class="mt-1 text-sm text-amber-800">Portal document access will appear once entitlement provisioning is completed.</p>
  </div>
{:else}
  <div class="space-y-6">
    <div class="flex items-start justify-between gap-4">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-slate-700">Partners</p>
        <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Data Room</h1>
        <p class="mt-1 text-sm text-neutral-500">Repository view of contracts awarded, ongoing projects, and portal permissions.</p>
      </div>
      <button
        onclick={() => loadDocuments()}
        class="rounded-lg border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
      >
        Refresh
      </button>
    </div>

    <div class="grid grid-cols-1 gap-3 rounded-xl border border-neutral-200 bg-white p-4 md:grid-cols-5">
      <input
        bind:value={query}
        placeholder="Search number, title, type"
        class="rounded-lg border border-neutral-200 px-3 py-2 text-sm md:col-span-2"
      />
      <select bind:value={statusFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="">All statuses</option>
        <option value="draft">Draft</option>
        <option value="submitted">Submitted</option>
        <option value="under_review">Under Review</option>
        <option value="approved">Approved</option>
        <option value="rejected">Rejected</option>
        <option value="superseded">Superseded</option>
        <option value="archived">Archived</option>
      </select>
      <select bind:value={confidentialityFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="">All confidentiality levels</option>
        <option value="public">Public</option>
        <option value="internal">Internal</option>
        <option value="confidential">Confidential</option>
        <option value="restricted">Restricted</option>
      </select>
      <button
        onclick={() => runSearch()}
        class="rounded-lg border border-neutral-900 bg-neutral-900 px-3 py-2 text-sm font-medium text-white hover:bg-neutral-800"
      >
        Apply Filters
      </button>
    </div>

    <div class="overflow-hidden rounded-xl border border-neutral-200 bg-white">
      {#if loading}
        <div class="flex items-center justify-center py-20">
          <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
        </div>
      {:else if rows.length === 0}
        <div class="px-6 py-16 text-center text-sm text-neutral-500">No documents found for this scope/filter.</div>
      {:else}
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-neutral-100 text-sm">
            <thead class="bg-neutral-50 text-xs uppercase tracking-wider text-neutral-500">
              <tr>
                <th class="px-4 py-3 text-left">Document</th>
                <th class="px-4 py-3 text-left">Type</th>
                <th class="px-4 py-3 text-left">Status</th>
                <th class="px-4 py-3 text-left">Confidentiality</th>
                <th class="px-4 py-3 text-left">Version</th>
                <th class="px-4 py-3 text-left">Expiry</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-neutral-100">
              {#each rows as row (row.id)}
                <tr>
                  <td class="px-4 py-3">
                    <p class="font-medium text-neutral-900">{row.document_number}</p>
                    <p class="text-xs text-neutral-500">{row.title}</p>
                  </td>
                  <td class="px-4 py-3 text-neutral-700">{row.document_type_name}</td>
                  <td class="px-4 py-3 text-neutral-700">{titleCase(row.status)}</td>
                  <td class="px-4 py-3 text-neutral-700">{titleCase(row.confidentiality_level)}</td>
                  <td class="px-4 py-3 text-neutral-700">{row.current_version_label ?? "--"}</td>
                  <td class="px-4 py-3 text-neutral-700">{row.expiry_date ?? "--"}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>

    <div class="flex items-center justify-between rounded-xl border border-neutral-200 bg-white px-4 py-3 text-sm">
      <p class="text-neutral-600">Showing {(page - 1) * pageSize + (rows.length === 0 ? 0 : 1)}-{(page - 1) * pageSize + rows.length} of {count}</p>
      <div class="flex items-center gap-2">
        <button
          onclick={() => {
            if (page > 1) {
              page -= 1;
              loadDocuments();
            }
          }}
          class="rounded-lg border border-neutral-200 px-3 py-1.5 text-neutral-700 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-40"
          disabled={page <= 1}
        >
          Previous
        </button>
        <span class="text-neutral-600">Page {page} of {totalPages}</span>
        <button
          onclick={() => {
            if (page < totalPages) {
              page += 1;
              loadDocuments();
            }
          }}
          class="rounded-lg border border-neutral-200 px-3 py-1.5 text-neutral-700 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-40"
          disabled={page >= totalPages}
        >
          Next
        </button>
      </div>
    </div>
  </div>
{/if}

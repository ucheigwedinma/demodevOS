<script lang="ts">
  import { goto } from "$app/navigation";
  import { api } from "$lib/api";
  import StatusBadge from "$lib/components/StatusBadge.svelte";
  import type { DocumentRecord, PaginatedResponse } from "$lib/types";

  let {
    title,
    subtitle = "",
    query = {},
    pageSize = 10,
    refreshKey = 0,
    emptyMessage = "No documents found for this view.",
    showHeader = true,
    showViewAll = false,
    viewAllHref = "/documents/repository",
    getRowHref = (row: DocumentRecord) => `/documents/${row.id}`,
    onRowClick,
  }: {
    title: string;
    subtitle?: string;
    query?: Record<string, string | number | null | undefined>;
    pageSize?: number;
    refreshKey?: number;
    emptyMessage?: string;
    showHeader?: boolean;
    showViewAll?: boolean;
    viewAllHref?: string;
    getRowHref?: (row: DocumentRecord) => string;
    onRowClick?: (row: DocumentRecord) => void;
  } = $props();

  let rows = $state<DocumentRecord[]>([]);
  let loading = $state(true);

  const queryKey = $derived(
    JSON.stringify(
      Object.entries(query)
        .filter(([, v]) => v !== null && v !== undefined && String(v).length > 0)
        .sort(([a], [b]) => a.localeCompare(b))
    )
  );

  function buildParams(): Record<string, string> {
    const params: Record<string, string> = {
      page_size: String(pageSize),
      ordering: "-created_at",
    };
    for (const [key, value] of Object.entries(query)) {
      if (value === null || value === undefined || String(value).length === 0) continue;
      params[key] = String(value);
    }
    return params;
  }

  async function loadRows() {
    loading = true;
    try {
      const res = await api.get<PaginatedResponse<DocumentRecord>>("/documents/records/", buildParams());
      rows = res.results;
    } catch {
      rows = [];
    }
    loading = false;
  }

  $effect(() => {
    void queryKey;
    void pageSize;
    void refreshKey;
    loadRows();
  });

  function contextLabel(row: DocumentRecord): string {
    if (row.project_name) return `Project: ${row.project_name}`;
    if (row.land_name) return `Land: ${row.land_name}`;
    if (row.unit_number) return `Unit: ${row.unit_number}`;
    if (row.vendor_name) return `Vendor: ${row.vendor_name}`;
    if (row.client_name) return `Client: ${row.client_name}`;
    return "Unlinked";
  }

  function fmtDate(value: string): string {
    return new Date(value).toLocaleDateString("en-US", { year: "numeric", month: "short", day: "numeric" });
  }
</script>

<div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
  {#if showHeader}
    <div class="px-5 py-4 border-b border-neutral-200 flex items-center justify-between gap-4">
      <div>
        <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">{title}</h3>
        {#if subtitle}
          <p class="mt-1 text-xs text-neutral-500">{subtitle}</p>
        {/if}
      </div>
      {#if showViewAll}
        <a href={viewAllHref} class="text-xs font-medium text-neutral-500 hover:text-neutral-900 transition-colors">View all</a>
      {/if}
    </div>
  {/if}

  {#if loading}
    <div class="py-16 text-center">
      <div class="inline-block w-5 h-5 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
      <p class="mt-3 text-sm text-neutral-400">Loading documents...</p>
    </div>
  {:else if rows.length === 0}
    <div class="py-14 text-center">
      <p class="text-sm text-neutral-400">{emptyMessage}</p>
    </div>
  {:else}
    <div class="overflow-x-auto">
      <table class="w-full text-sm min-w-[760px]">
        <thead>
          <tr class="border-b border-neutral-200">
            <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Document</th>
            <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Category</th>
            <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Status</th>
            <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Context</th>
            <th class="px-5 py-3.5 text-left text-xs font-medium text-neutral-400 uppercase tracking-wider">Created</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each rows as row}
            <tr class="hover:bg-neutral-50 cursor-pointer transition-colors" onclick={() => onRowClick ? onRowClick(row) : goto(getRowHref(row))}>
              <td class="px-5 py-3.5">
                <p class="font-medium text-neutral-900">{row.document_number}</p>
                <p class="text-xs text-neutral-500 mt-0.5 truncate max-w-[280px]">{row.title}</p>
              </td>
              <td class="px-5 py-3.5 text-neutral-600">
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs bg-neutral-100">{row.category}</span>
              </td>
              <td class="px-5 py-3.5">
                <StatusBadge status={row.status} size="sm" />
              </td>
              <td class="px-5 py-3.5 text-neutral-500">{contextLabel(row)}</td>
              <td class="px-5 py-3.5 text-neutral-500">{fmtDate(row.created_at)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>

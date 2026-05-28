<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { page } from "$app/stores";
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { ResourceConfig, PaginatedResponse } from "./types";
  import CellRenderer from "./CellRenderer.svelte";
  import FilterBar from "./FilterBar.svelte";
  import Pagination from "./Pagination.svelte";
  import DeleteConfirmation from "./DeleteConfirmation.svelte";
  import ExportMenu from "./ExportMenu.svelte";
  import BulkActionBar from "./BulkActionBar.svelte";
  import EmptyState from "$lib/components/ui/EmptyState.svelte";

  let { config }: { config: ResourceConfig } = $props();

  let data = $state<Record<string, unknown>[]>([]);
  let total = $state(0);
  let currentPage = $state(1);
  let loading = $state(true);
  let filterValues = $state<Record<string, string>>({});
  let deleteTarget = $state<Record<string, unknown> | null>(null);
  let deleting = $state(false);
  let selectedIds = $state<Set<number>>(new Set());
  let bulkDeleting = $state(false);

  let debounceTimer: ReturnType<typeof setTimeout>;

  let visibleColumns = $derived(config.columns.filter((c) => !c.hidden));
  let allSelected = $derived(data.length > 0 && data.every((r) => selectedIds.has(r.id as number)));
  let someSelected = $derived(selectedIds.size > 0 && !allSelected);

  function toggleSelectAll() {
    if (allSelected) {
      selectedIds = new Set();
    } else {
      selectedIds = new Set(data.map((r) => r.id as number));
    }
  }

  function toggleRow(id: number) {
    const next = new Set(selectedIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    selectedIds = next;
  }

  function clearSelection() {
    selectedIds = new Set();
  }

  async function fetchData() {
    loading = true;
    try {
      const params: Record<string, string> = {
        page: String(currentPage),
        page_size: String(config.pageSize ?? 25),
      };
      if (config.defaultSort) params.ordering = config.defaultSort;

      for (const [k, v] of Object.entries(filterValues)) {
        if (v) params[k] = v;
      }

      const res = await api.get<PaginatedResponse>(config.endpoint, params);
      data = res.results;
      total = res.count;
      selectedIds = new Set();
    } catch {
      toast.error("Load failed", `Could not load ${config.labelPlural.toLowerCase()}.`);
    } finally {
      loading = false;
    }
  }

  function handleFilterChange(key: string, value: string) {
    filterValues = { ...filterValues, [key]: value };
    currentPage = 1;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(fetchData, key === "search" ? 300 : 0);
  }

  function handlePageChange(p: number) {
    currentPage = p;
    fetchData();
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    deleting = true;
    try {
      await api.delete(`${config.endpoint}${deleteTarget.id}/`);
      toast.success(`${config.label} deleted`);
      deleteTarget = null;
      fetchData();
    } catch {
      toast.error(`Delete failed`);
    } finally {
      deleting = false;
    }
  }

  async function handleBulkDelete() {
    bulkDeleting = true;
    const ids = Array.from(selectedIds);
    let deleted = 0;
    let failed = 0;
    try {
      await Promise.all(
        ids.map(async (id) => {
          try {
            await api.delete(`${config.endpoint}${id}/`);
            deleted++;
          } catch {
            failed++;
          }
        }),
      );
      if (failed === 0) {
        toast.success(`Deleted ${deleted} ${deleted === 1 ? config.label.toLowerCase() : config.labelPlural.toLowerCase()}`);
      } else {
        toast.error(`Deleted ${deleted}, failed ${failed}`);
      }
      clearSelection();
      fetchData();
    } finally {
      bulkDeleting = false;
    }
  }

  onMount(fetchData);
</script>

<div class="space-y-4">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <h1 class="text-xl font-semibold text-neutral-900">{config.labelPlural}</h1>
    <div class="flex items-center gap-2">
      <ExportMenu columns={config.columns} {data} resourceLabel={config.labelPlural} />
      {#if config.canCreate !== false && config.formFields}
        <a
          href="/{$page.params.module}/{$page.params.resource}/new"
          class="px-4 py-2 text-sm font-medium text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 transition-colors"
        >
          Add {config.label}
        </a>
      {/if}
    </div>
  </div>

  <!-- Filters -->
  {#if config.filters}
    <FilterBar filters={config.filters} values={filterValues} onFilterChange={handleFilterChange} />
  {/if}

  <!-- Table -->
  <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
    {#if loading}
      <!-- Skeleton loader -->
      <div class="animate-pulse">
        <div class="border-b border-neutral-100 px-4 py-3 flex gap-4">
          <div class="h-3 bg-neutral-100 rounded w-8"></div>
          {#each { length: Math.min(visibleColumns.length, 5) } as _}
            <div class="h-3 bg-neutral-100 rounded flex-1"></div>
          {/each}
        </div>
        {#each { length: 8 } as _, i}
          <div class="border-b border-neutral-50 px-4 py-4 flex gap-4 {i % 2 !== 0 ? 'bg-neutral-25' : ''}">
            <div class="h-3 bg-neutral-100 rounded w-8"></div>
            {#each { length: Math.min(visibleColumns.length, 5) } as _}
              <div class="h-3 bg-neutral-{i % 3 === 0 ? '200' : '100'} rounded flex-1"></div>
            {/each}
          </div>
        {/each}
      </div>
    {:else if data.length === 0}
      <EmptyState title="No {config.labelPlural.toLowerCase()}" description="No records match your current filters." />
    {:else}
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="border-b border-neutral-100">
              <th class="px-4 py-3 w-10">
                <input
                  type="checkbox"
                  checked={allSelected}
                  indeterminate={someSelected}
                  onchange={toggleSelectAll}
                  class="w-3.5 h-3.5 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900 focus:ring-offset-0 cursor-pointer"
                />
              </th>
              {#each visibleColumns as col}
                <th class="px-4 py-3 text-left text-xs font-medium text-neutral-500 uppercase tracking-wider {col.width ?? ''}">
                  {col.label}
                </th>
              {/each}
              <th class="px-4 py-3 text-right text-xs font-medium text-neutral-500 uppercase tracking-wider w-24">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {#each data as row, i}
              <tr class="border-b border-neutral-50 hover:bg-neutral-50/50 transition-colors
                         {selectedIds.has(row.id as number) ? 'bg-neutral-50' : i % 2 !== 0 ? 'bg-neutral-25' : ''}">
                <td class="px-4 py-3">
                  <input
                    type="checkbox"
                    checked={selectedIds.has(row.id as number)}
                    onchange={() => toggleRow(row.id as number)}
                    class="w-3.5 h-3.5 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900 focus:ring-offset-0 cursor-pointer"
                  />
                </td>
                {#each visibleColumns as col}
                  <td class="px-4 py-3">
                    <CellRenderer column={col} value={row[col.key]} {row} />
                  </td>
                {/each}
                <td class="px-4 py-3 text-right">
                  <div class="flex items-center justify-end gap-1">
                    {#if config.canEdit !== false && config.formFields}
                      <a
                        href="/{$page.params.module}/{$page.params.resource}/{row.id}/edit"
                        class="p-1.5 rounded-lg text-neutral-400 hover:text-neutral-900 hover:bg-neutral-100 transition-colors"
                        title="Edit"
                      >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                          <path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125" />
                        </svg>
                      </a>
                    {/if}
                    {#if config.canDelete !== false}
                      <button
                        onclick={() => deleteTarget = row}
                        class="p-1.5 rounded-lg text-neutral-400 hover:text-red-600 hover:bg-red-50 transition-colors"
                        title="Delete"
                      >
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                          <path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                        </svg>
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
  </div>

  <!-- Pagination -->
  <Pagination page={currentPage} pageSize={config.pageSize ?? 25} {total} onPageChange={handlePageChange} />
</div>

<!-- Bulk Action Bar -->
{#if selectedIds.size > 0}
  <BulkActionBar
    count={selectedIds.size}
    label={config.label}
    labelPlural={config.labelPlural}
    canDelete={config.canDelete !== false}
    bulkActions={config.bulkActions}
    loading={bulkDeleting}
    onclear={clearSelection}
    ondelete={handleBulkDelete}
  />
{/if}

<DeleteConfirmation
  open={!!deleteTarget}
  label={config.label.toLowerCase()}
  loading={deleting}
  onconfirm={handleDelete}
  onclose={() => deleteTarget = null}
/>

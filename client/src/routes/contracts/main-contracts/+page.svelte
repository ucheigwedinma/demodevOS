<script lang="ts">
  import { goto } from "$app/navigation";
  import { toast } from "$lib/stores/toast.svelte";
  import { fetchAllPages, isMainContractDocument, toAmount } from "$lib/contracts";
  import type { DocumentRecord } from "$lib/types";
  import { currency } from "$lib/stores/currency.svelte";

  let loading = $state(true);
  let rows = $state<DocumentRecord[]>([]);
  let search = $state("");
  let status = $state("");

  function fmtCurrency(value: string | number | null): string {
    return currency.format(toAmount(value));
  }

  function fmtDate(value: string): string {
    return new Date(value).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  async function load() {
    loading = true;
    try {
      const docs = await fetchAllPages<DocumentRecord>("/documents/records/", {
        category: "CON",
        ordering: "-created_at",
        page_size: "200",
      });
      rows = docs.filter(isMainContractDocument);
    } catch {
      toast.error("Load failed", "Could not load main contracts.");
      rows = [];
    } finally {
      loading = false;
    }
  }

  const filtered = $derived.by(() =>
    rows.filter((row) => {
      if (status && row.status !== status) return false;
      if (!search.trim()) return true;
      const needle = search.trim().toLowerCase();
      const haystack = `${row.document_number} ${row.title} ${row.project_name ?? ""} ${row.vendor_name ?? ""}`.toLowerCase();
      return haystack.includes(needle);
    })
  );

  $effect(() => {
    load();
  });
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Main Contracts</h1>
    <p class="mt-1 text-sm text-neutral-500">Primary contract register linked to projects, vendors, and value exposure.</p>
  </div>

  <div class="flex flex-wrap items-center gap-3">
    <input
      bind:value={search}
      placeholder="Search contract #, title, project..."
      class="w-full max-w-sm rounded-lg border border-neutral-200 px-3 py-2.5 text-sm focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
    />
    <select
      bind:value={status}
      class="rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm text-neutral-700 focus:border-transparent focus:outline-none focus:ring-2 focus:ring-neutral-900"
    >
      <option value="">All statuses</option>
      <option value="draft">Draft</option>
      <option value="submitted">Submitted</option>
      <option value="under_review">Under Review</option>
      <option value="approved">Approved</option>
      <option value="rejected">Rejected</option>
      <option value="superseded">Superseded</option>
      <option value="archived">Archived</option>
    </select>
  </div>

  <div class="overflow-hidden rounded-xl border border-neutral-200 bg-white">
    {#if loading}
      <div class="py-20 text-center">
        <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-900"></div>
      </div>
    {:else if filtered.length === 0}
      <div class="px-6 py-12 text-sm text-neutral-500">No main contracts match current filters.</div>
    {:else}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-100 bg-neutral-50">
            <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Contract</th>
            <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Project</th>
            <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Vendor</th>
            <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Status</th>
            <th class="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Value</th>
            <th class="px-5 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Created</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each filtered as row}
            <tr class="cursor-pointer hover:bg-neutral-50" onclick={() => goto(`/documents/repository?document=${row.id}`)}>
              <td class="px-5 py-3">
                <p class="font-medium text-neutral-900">{row.document_number}</p>
                <p class="max-w-[340px] truncate text-xs text-neutral-500">{row.title}</p>
              </td>
              <td class="px-5 py-3 text-neutral-600">{row.project_name || "—"}</td>
              <td class="px-5 py-3 text-neutral-600">{row.vendor_name || "—"}</td>
              <td class="px-5 py-3 text-neutral-700">{row.status}</td>
              <td class="px-5 py-3 text-right font-medium tabular-nums text-neutral-900">{fmtCurrency(row.contract_value)}</td>
              <td class="px-5 py-3 text-right text-neutral-600">{fmtDate(row.created_at)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>
</div>

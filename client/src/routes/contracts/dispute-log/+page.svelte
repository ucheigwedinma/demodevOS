<script lang="ts">
  import { toast } from "$lib/stores/toast.svelte";
  import { fetchAllPages, isDisputeIssue } from "$lib/contracts";
  import type { ProjectFieldEscalation } from "$lib/types";

  let loading = $state(true);
  let rows = $state<ProjectFieldEscalation[]>([]);

  async function load() {
    loading = true;
    try {
      const issueRows = await fetchAllPages<ProjectFieldEscalation>("/projects/issues/", {
        ordering: "-issue_date",
        page_size: "200",
      });
      rows = issueRows.filter(isDisputeIssue);
    } catch {
      toast.error("Load failed", "Could not load dispute log.");
      rows = [];
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    load();
  });

  const openDisputes = $derived.by(() =>
    rows.filter((row) => row.status !== "resolved" && row.status !== "closed").length
  );
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Dispute Log</h1>
    <p class="mt-1 text-sm text-neutral-500">Active and historical disputes sourced from project issue escalations.</p>
  </div>

  <div class="grid grid-cols-2 gap-4 lg:grid-cols-3">
    <div class="rounded-xl border border-neutral-200 bg-white px-5 py-4">
      <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Total Disputes</p>
      <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{rows.length}</p>
    </div>
    <div class="rounded-xl border border-neutral-200 bg-white px-5 py-4">
      <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Open Disputes</p>
      <p class="mt-1 text-xl font-bold text-red-700 tabular-nums">{openDisputes}</p>
    </div>
    <div class="rounded-xl border border-neutral-200 bg-white px-5 py-4">
      <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">Closed/Resolved</p>
      <p class="mt-1 text-xl font-bold text-neutral-900 tabular-nums">{rows.length - openDisputes}</p>
    </div>
  </div>

  <div class="overflow-hidden rounded-xl border border-neutral-200 bg-white">
    {#if loading}
      <div class="py-20 text-center">
        <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-900"></div>
      </div>
    {:else if rows.length === 0}
      <div class="px-6 py-12 text-sm text-neutral-500">No disputes logged.</div>
    {:else}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-100 bg-neutral-50">
            <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Dispute</th>
            <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Project</th>
            <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Type</th>
            <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Severity</th>
            <th class="px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Status</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each rows as row}
            <tr>
              <td class="px-5 py-3">
                <p class="font-medium text-neutral-900">{row.title}</p>
                <p class="max-w-[320px] truncate text-xs text-neutral-500">{row.description}</p>
              </td>
              <td class="px-5 py-3 text-neutral-600">{row.project_name}</td>
              <td class="px-5 py-3 text-neutral-700">{row.issue_type}</td>
              <td class="px-5 py-3 text-neutral-700">{row.severity}</td>
              <td class="px-5 py-3 text-neutral-700">{row.status}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>
</div>

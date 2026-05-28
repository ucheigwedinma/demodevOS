<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { PaginatedResponse, ReportRunRecord } from "$lib/types";

  let loading = $state(true);
  let runs = $state<ReportRunRecord[]>([]);

  function unwrapList<T>(payload: PaginatedResponse<T> | T[]): T[] {
    return Array.isArray(payload) ? payload : (payload?.results ?? []);
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

  async function loadExports() {
    loading = true;
    try {
      const payload = await api.get<PaginatedResponse<ReportRunRecord> | ReportRunRecord[]>("/settings/report-runs/", {
        ordering: "-created_at",
      });
      runs = unwrapList(payload);
    } catch {
      runs = [];
      toast.error("Load failed", "Could not load export history.");
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    void loadExports();
  });
</script>

<div class="space-y-6">
  <section class="rounded-xl border border-neutral-200 bg-white p-5">
    <h1 class="text-2xl font-bold text-neutral-900">Export Results</h1>
    <p class="mt-2 text-sm text-neutral-600">Export options: PDF, Excel, CSV, and Print.</p>
    <p class="mt-1 text-xs text-neutral-500">Availability is enforced by admin confidentiality-label settings per report.</p>
    <div class="mt-3 flex flex-wrap gap-2 text-xs">
      <span class="rounded-lg border border-neutral-300 px-2.5 py-1 text-neutral-700">PDF</span>
      <span class="rounded-lg border border-neutral-300 px-2.5 py-1 text-neutral-700">Excel</span>
      <span class="rounded-lg border border-neutral-300 px-2.5 py-1 text-neutral-700">CSV</span>
      <span class="rounded-lg border border-neutral-300 px-2.5 py-1 text-neutral-700">Print</span>
    </div>
  </section>

  <section class="rounded-xl border border-neutral-200 bg-white p-5">
    {#if loading}
      <p class="text-sm text-neutral-500">Loading export history...</p>
    {:else if runs.length === 0}
      <p class="text-sm text-neutral-500">No report runs available yet.</p>
    {:else}
      <div class="overflow-x-auto">
        <table class="min-w-full text-sm">
          <thead class="bg-neutral-50">
            <tr>
              <th class="px-4 py-2 text-left font-medium text-neutral-600">Report</th>
              <th class="px-4 py-2 text-left font-medium text-neutral-600">Format</th>
              <th class="px-4 py-2 text-left font-medium text-neutral-600">Status</th>
              <th class="px-4 py-2 text-left font-medium text-neutral-600">Created</th>
              <th class="px-4 py-2 text-right font-medium text-neutral-600">Action</th>
            </tr>
          </thead>
          <tbody>
            {#each runs as run}
              <tr class="border-t border-neutral-100">
                <td class="px-4 py-2 text-neutral-900">{run.report_template_name}</td>
                <td class="px-4 py-2 text-neutral-700">{run.output_format_display}</td>
                <td class="px-4 py-2 text-neutral-700">{run.status_display}</td>
                <td class="px-4 py-2 text-neutral-700">{formatDateTime(run.created_at)}</td>
                <td class="px-4 py-2 text-right">
                  <a
                    href={`/reports/${run.report_template}`}
                    class="rounded-lg border border-neutral-300 px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-100"
                  >
                    Open Report
                  </a>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </section>
</div>

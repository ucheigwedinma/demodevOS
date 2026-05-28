<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { ReportLibraryItem, ReportLibraryResponse, ReportRunRecord } from "$lib/types";

  let loading = $state(true);
  let runningId = $state<number | null>(null);
  let reports = $state<ReportLibraryItem[]>([]);

  async function loadRunMenu() {
    loading = true;
    try {
      const payload = await api.get<ReportLibraryResponse>("/settings/reports/library/", {
        category: "my_reports",
      });
      reports = payload.results ?? [];
    } catch {
      reports = [];
      toast.error("Load failed", "Could not load reports for quick run.");
    } finally {
      loading = false;
    }
  }

  async function runReport(report: ReportLibraryItem) {
    runningId = report.id;
    try {
      const run = await api.post<ReportRunRecord>(`/settings/report-templates/${report.id}/run/`, {});
      toast.success("Run queued", `${report.name} queued (${run.status_display}).`);
    } catch {
      toast.error("Run failed", `Could not run ${report.name}.`);
    } finally {
      runningId = null;
    }
  }

  $effect(() => {
    void loadRunMenu();
  });
</script>

<div class="space-y-6">
  <section class="rounded-xl border border-neutral-200 bg-white p-5">
    <h1 class="text-2xl font-bold text-neutral-900">Run Reports</h1>
    <p class="mt-2 text-sm text-neutral-600">Execute report templates directly from this run menu.</p>
  </section>

  <section class="rounded-xl border border-neutral-200 bg-white p-5">
    {#if loading}
      <p class="text-sm text-neutral-500">Loading reports...</p>
    {:else if reports.length === 0}
      <p class="text-sm text-neutral-500">No reports available. Start from the reports library.</p>
    {:else}
      <div class="space-y-3">
        {#each reports as report (report.id)}
          <article class="rounded-lg border border-neutral-200 bg-neutral-50 p-4 flex items-center justify-between gap-3">
            <div>
              <h3 class="text-sm font-semibold text-neutral-900">{report.name}</h3>
              <p class="mt-1 text-xs text-neutral-600">{report.module_source_display} module</p>
            </div>
            <div class="flex items-center gap-2">
              <a
                href={`/reports/${report.id}`}
                class="rounded-lg border border-neutral-300 px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-100"
              >
                Open
              </a>
              <button
                type="button"
                onclick={() => runReport(report)}
                disabled={runningId === report.id}
                class="rounded-lg bg-neutral-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-neutral-800 disabled:opacity-60"
              >
                {runningId === report.id ? "Running..." : "Run"}
              </button>
            </div>
          </article>
        {/each}
      </div>
    {/if}
  </section>
</div>

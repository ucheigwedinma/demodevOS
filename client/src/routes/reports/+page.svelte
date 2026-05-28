<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { ReportLibraryCategory, ReportLibraryItem, ReportLibraryResponse, ReportRunRecord } from "$lib/types";

  const fallbackCategories: ReportLibraryCategory[] = [
    { key: "my_reports", label: "My Reports", count: 0 },
    { key: "department_reports", label: "Department Reports", count: 0 },
    { key: "shared_reports", label: "Shared Reports", count: 0 },
    { key: "scheduled_reports", label: "Scheduled Reports", count: 0 },
    { key: "recently_viewed", label: "Recently Viewed", count: 0 },
  ];

  let loading = $state(true);
  let runningReportId = $state<number | null>(null);
  let searchQuery = $state("");
  let activeCategory = $state<ReportLibraryCategory["key"]>("my_reports");

  let categories = $state<ReportLibraryCategory[]>(fallbackCategories);
  let reports = $state<ReportLibraryItem[]>([]);

  async function loadLibrary() {
    loading = true;
    try {
      const params: Record<string, string> = { category: activeCategory };
      if (searchQuery.trim()) params.q = searchQuery.trim();
      const payload = await api.get<ReportLibraryResponse>("/settings/reports/library/", params);

      categories = payload.categories?.length ? payload.categories : fallbackCategories;
      reports = payload.results ?? [];
    } catch {
      categories = fallbackCategories;
      reports = [];
      toast.error("Load failed", "Could not load reports library.");
    } finally {
      loading = false;
    }
  }

  async function runReport(report: ReportLibraryItem) {
    runningReportId = report.id;
    try {
      const run = await api.post<ReportRunRecord>(`/settings/report-templates/${report.id}/run/`, {});
      toast.success("Report queued", `${report.name} was run successfully (${run.status_display}).`);
      await loadLibrary();
    } catch {
      toast.error("Run failed", `Could not run ${report.name}.`);
    } finally {
      runningReportId = null;
    }
  }

  function formatLastRun(raw: string | null): string {
    if (!raw) return "Never";

    const runDate = new Date(raw);
    const now = new Date();

    const run = new Date(runDate.getFullYear(), runDate.getMonth(), runDate.getDate());
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const delta = Math.round((today.getTime() - run.getTime()) / 86400000);

    if (delta === 0) return "Today";
    if (delta === 1) return "Yesterday";
    return runDate.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  function activeCount(key: ReportLibraryCategory["key"]): number {
    const row = categories.find((item) => item.key === key);
    return row?.count ?? 0;
  }

  let searchDebounce: ReturnType<typeof setTimeout> | null = null;

  $effect(() => {
    void activeCategory;

    if (searchDebounce) clearTimeout(searchDebounce);
    searchDebounce = setTimeout(() => {
      loadLibrary();
    }, 220);

    return () => {
      if (searchDebounce) clearTimeout(searchDebounce);
    };
  });
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Reports</h1>
  </div>

  <div class="rounded-xl border border-neutral-200 bg-white p-4 sm:p-5">
    <input
      type="text"
      bind:value={searchQuery}
      placeholder="Search reports..."
      class="w-full rounded-lg border border-neutral-200 px-3 py-2 text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900"
    />
  </div>

  <div class="grid grid-cols-1 gap-6 lg:grid-cols-[260px_minmax(0,1fr)]">
    <aside class="rounded-xl border border-neutral-200 bg-white p-4 sm:p-5 h-fit">
      <h2 class="text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-3">Categories</h2>
      <div class="space-y-1">
        {#each categories as category}
          <button
            type="button"
            onclick={() => (activeCategory = category.key)}
            class="w-full rounded-lg px-3 py-2 text-left text-sm transition-colors flex items-center justify-between
              {activeCategory === category.key
                ? 'bg-neutral-900 text-white'
                : 'text-neutral-700 hover:bg-neutral-100'}"
          >
            <span>{category.label}</span>
            <span class="tabular-nums text-xs opacity-80">{activeCount(category.key)}</span>
          </button>
        {/each}
      </div>
    </aside>

    <section class="space-y-4">
      {#if loading}
        <div class="rounded-xl border border-neutral-200 bg-white p-8 text-center text-sm text-neutral-500">
          Loading reports...
        </div>
      {:else if reports.length === 0}
        <div class="rounded-xl border border-neutral-200 bg-white p-8 text-center text-sm text-neutral-500">
          No reports found for this category.
        </div>
      {:else}
        {#each reports as report (report.id)}
          <article class="rounded-xl border border-neutral-200 bg-white p-4 sm:p-5">
            <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div class="space-y-2">
                <h3 class="text-base font-semibold text-neutral-900">{report.name}</h3>
                <a
                  href={`/reports/${report.id}`}
                  class="inline-flex items-center gap-1 text-xs font-semibold text-neutral-700 hover:text-neutral-900"
                >
                  Open report
                  <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5H19.5m0 0V10.5m0-6L10.5 13.5" />
                    <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 13.5V18A1.5 1.5 0 0 1 18 19.5H6A1.5 1.5 0 0 1 4.5 18V6A1.5 1.5 0 0 1 6 4.5h4.5" />
                  </svg>
                </a>
                <p class="text-sm text-neutral-500">{report.module_source_display} Module</p>
                <p class="text-sm text-neutral-600">{report.description || "No description provided."}</p>

                <div class="grid grid-cols-1 gap-1 text-xs text-neutral-500 sm:grid-cols-2">
                  <p><span class="font-medium text-neutral-700">Owner:</span> {report.owner_name || "Unassigned"}</p>
                  <p>
                    <span class="font-medium text-neutral-700">Confidentiality:</span>
                    {report.confidentiality_label || "Not classified"}
                  </p>
                  <p>
                    <span class="font-medium text-neutral-700">Last Run:</span>
                    {formatLastRun(report.last_run_at)}
                  </p>
                </div>
              </div>

              <div class="shrink-0">
                <button
                  type="button"
                  onclick={() => runReport(report)}
                  disabled={runningReportId === report.id}
                  class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {runningReportId === report.id ? "Running..." : "Run"}
                </button>
              </div>
            </div>
          </article>
        {/each}
      {/if}
    </section>
  </div>
</div>

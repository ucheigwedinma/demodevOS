<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { MyScheduledReportItem, MyScheduledReportResponse } from "$lib/types";

  let loading = $state(true);
  let rows = $state<MyScheduledReportItem[]>([]);

  const statusClasses: Record<MyScheduledReportItem["status"], string> = {
    delivered: "bg-emerald-100 text-emerald-800 border-emerald-200",
    failed: "bg-rose-100 text-rose-800 border-rose-200",
    pending: "bg-amber-100 text-amber-800 border-amber-200",
  };

  function formatDateTime(value: string | null): string {
    if (!value) return "N/A";
    return new Date(value).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  async function loadMyScheduledReports() {
    loading = true;
    try {
      const payload = await api.get<MyScheduledReportResponse>("/settings/reports/my-scheduled/");
      rows = payload.results ?? [];
    } catch {
      rows = [];
      toast.error("Load failed", "Could not load your scheduled reports.");
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    void loadMyScheduledReports();
  });
</script>

<div class="space-y-6">
  <section class="rounded-xl border border-neutral-200 bg-white p-5">
    <h1 class="text-2xl font-bold text-neutral-900">My Scheduled Reports</h1>
    <p class="mt-2 text-sm text-neutral-600">Reports scheduled for you.</p>
  </section>

  <section class="rounded-xl border border-neutral-200 bg-white p-5">
    <div class="mb-4 flex flex-wrap items-center gap-2 text-xs text-neutral-700">
      <span>Status indicators:</span>
      <span class="rounded-full border border-emerald-200 bg-emerald-100 px-2.5 py-1">Delivered</span>
      <span class="rounded-full border border-rose-200 bg-rose-100 px-2.5 py-1">Failed</span>
      <span class="rounded-full border border-amber-200 bg-amber-100 px-2.5 py-1">Pending</span>
    </div>

    {#if loading}
      <p class="text-sm text-neutral-500">Loading scheduled reports...</p>
    {:else if rows.length === 0}
      <p class="text-sm text-neutral-500">No scheduled reports assigned to you yet.</p>
    {:else}
      <div class="space-y-3">
        {#each rows as row (row.id)}
          <article class="rounded-lg border border-neutral-200 bg-neutral-50 p-4">
            <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h3 class="text-sm font-semibold text-neutral-900">{row.name}</h3>
                <p class="mt-1 text-sm text-neutral-600">{row.schedule_text}</p>
                <p class="mt-2 text-xs text-neutral-500">Last dispatched: {formatDateTime(row.last_dispatched_at)}</p>
              </div>

              <div class="flex items-center gap-2">
                <span class={`rounded-full border px-2.5 py-1 text-xs font-semibold ${statusClasses[row.status]}`}>
                  {row.status_display}
                </span>
                <a
                  href={`/reports/${row.report_template}`}
                  class="rounded-lg border border-neutral-300 px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-100"
                >
                  Open Report
                </a>
              </div>
            </div>
          </article>
        {/each}
      </div>
    {/if}
  </section>
</div>

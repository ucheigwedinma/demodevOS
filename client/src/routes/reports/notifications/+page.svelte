<script lang="ts">
  import { ApiError, api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { Notification, PaginatedResponse, ReportRunRecord } from "$lib/types";

  let loading = $state(true);
  let rows = $state<Notification[]>([]);
  let downloadingId = $state<number | null>(null);

  function formatDateTime(value: string): string {
    return new Date(value).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function extractReportTemplateId(linkUrl: string): number | null {
    const match = linkUrl.match(/\/reports\/(\d+)/);
    if (!match) return null;
    const parsed = Number(match[1]);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
  }

  function viewUrl(row: Notification): string {
    return row.link_url || "/reports";
  }

  async function loadReportNotifications() {
    loading = true;
    try {
      const payload = await api.get<PaginatedResponse<Notification>>("/notifications/", {
        category: "reports_ready",
        page_size: "100",
      });
      rows = payload.results ?? [];
    } catch {
      rows = [];
      toast.error("Load failed", "Could not load report notifications.");
    } finally {
      loading = false;
    }
  }

  async function markNotificationRead(id: number) {
    const current = rows.find((item) => item.id === id);
    if (!current || current.is_read) return;

    try {
      await api.post<Notification>(`/notifications/${id}/read/`, {});
      rows = rows.map((item) =>
        item.id === id
          ? {
              ...item,
              is_read: true,
              read_at: item.read_at ?? new Date().toISOString(),
            }
          : item,
      );
    } catch {
      // non-blocking
    }
  }

  async function downloadReport(row: Notification) {
    const templateId = extractReportTemplateId(row.link_url || "");
    if (!templateId) {
      toast.error("Download unavailable", "This notification is missing a report link.");
      return;
    }

    downloadingId = row.id;
    try {
      await markNotificationRead(row.id);
      const run = await api.post<ReportRunRecord>(`/settings/report-templates/${templateId}/run/`, {
        requested_action: "export",
        output_format: "pdf",
      });
      toast.success("Download queued", `Report export queued (${run.output_format_display}).`);
    } catch (error) {
      if (error instanceof ApiError) {
        const message =
          error.fieldErrors.output_format?.[0] ||
          error.fieldErrors.non_field_errors?.[0] ||
          "Could not queue report export.";
        toast.error("Download failed", message);
      } else {
        toast.error("Download failed", "Could not queue report export.");
      }
    } finally {
      downloadingId = null;
    }
  }

  async function openReport(row: Notification) {
    await markNotificationRead(row.id);
  }

  $effect(() => {
    void loadReportNotifications();
  });
</script>

<div class="space-y-6">
  <section class="rounded-xl border border-neutral-200 bg-white p-5">
    <h1 class="text-2xl font-bold text-neutral-900">Report Notifications</h1>
    <p class="mt-2 text-sm text-neutral-600">Users get alerts when reports are generated.</p>
  </section>

  <section class="rounded-xl border border-neutral-200 bg-white p-5">
    {#if loading}
      <p class="text-sm text-neutral-500">Loading report notifications...</p>
    {:else if rows.length === 0}
      <p class="text-sm text-neutral-500">No report notifications yet.</p>
    {:else}
      <div class="space-y-3">
        {#each rows as row (row.id)}
          <article class={`rounded-lg border p-4 ${row.is_read ? 'border-neutral-200 bg-neutral-50' : 'border-neutral-300 bg-white'}`}>
            <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p class={`text-sm ${row.is_read ? 'font-medium text-neutral-700' : 'font-semibold text-neutral-900'}`}>{row.title}</p>
                <p class="mt-1 text-sm text-neutral-600">{row.message}</p>
                <p class="mt-2 text-xs text-neutral-500">{formatDateTime(row.created_at)}</p>
              </div>

              <div class="flex items-center gap-2">
                <button
                  type="button"
                  onclick={() => downloadReport(row)}
                  disabled={downloadingId === row.id}
                  class="rounded-lg border border-neutral-300 px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-100 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {downloadingId === row.id ? "Queueing..." : "Download"}
                </button>
                <a
                  href={viewUrl(row)}
                  onclick={() => openReport(row)}
                  class="rounded-lg bg-neutral-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-neutral-800"
                >
                  View
                </a>
              </div>
            </div>
          </article>
        {/each}
      </div>
    {/if}
  </section>
</div>

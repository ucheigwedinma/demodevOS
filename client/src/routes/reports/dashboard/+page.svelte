<script lang="ts">
  import { ApiError, api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    PaginatedResponse,
    ReportRunRecord,
    ReportSubscription,
    ReportSubscriptionFrequency,
    ReportTemplateListItem,
  } from "$lib/types";

  type RefreshOption = {
    value: ReportSubscriptionFrequency;
    label: string;
  };

  const refreshOptions: RefreshOption[] = [
    { value: "daily", label: "Daily" },
    { value: "weekly", label: "Weekly" },
    { value: "monthly", label: "Monthly" },
  ];

  let loading = $state(true);
  let saving = $state(false);
  let mutatingId = $state<number | null>(null);
  let runningTemplateId = $state<number | null>(null);

  let subscriptions = $state<ReportSubscription[]>([]);
  let templates = $state<ReportTemplateListItem[]>([]);
  let runs = $state<ReportRunRecord[]>([]);

  let form = $state({
    report_template: "",
    frequency: "daily" as ReportSubscriptionFrequency,
  });

  function unwrapList<T>(payload: PaginatedResponse<T> | T[]): T[] {
    return Array.isArray(payload) ? payload : (payload?.results ?? []);
  }

  function formatDateTime(value: string | null): string {
    if (!value) return "Pending first refresh";
    return new Date(value).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function widgetTitle(item: ReportSubscription): string {
    const code = item.report_template_code.toLowerCase();
    if (code.includes("headcount")) return "Headcount by Department";
    if (code.includes("budget") && code.includes("variance")) return "Project Budget Variance";
    if (code.includes("revenue") && code.includes("region")) return "Region Revenue";
    return item.report_template_name;
  }

  const templateById = $derived.by(() => {
    const map = new Map<number, ReportTemplateListItem>();
    for (const template of templates) map.set(template.id, template);
    return map;
  });

  const latestRunByTemplate = $derived.by(() => {
    const map = new Map<number, ReportRunRecord>();
    for (const run of runs) {
      if (!map.has(run.report_template)) map.set(run.report_template, run);
    }
    return map;
  });

  const dashboardWidgets = $derived.by(() =>
    subscriptions.filter((item) => item.delivery_channels.includes("dashboard_widget")),
  );

  async function loadDashboardIntegration() {
    loading = true;
    try {
      const [subscriptionsPayload, templatesPayload, runsPayload] = await Promise.all([
        api.get<PaginatedResponse<ReportSubscription> | ReportSubscription[]>("/settings/report-subscriptions/", {
          ordering: "-updated_at",
          page_size: "200",
        }),
        api.get<PaginatedResponse<ReportTemplateListItem> | ReportTemplateListItem[]>("/settings/report-templates/", {
          ordering: "name",
          is_active: "true",
          page_size: "200",
        }),
        api.get<PaginatedResponse<ReportRunRecord> | ReportRunRecord[]>("/settings/report-runs/", {
          ordering: "-created_at",
          page_size: "200",
        }),
      ]);

      subscriptions = unwrapList(subscriptionsPayload);
      templates = unwrapList(templatesPayload);
      runs = unwrapList(runsPayload);

      if (!form.report_template && templates.length > 0) {
        form = {
          ...form,
          report_template: String(templates[0].id),
        };
      }
    } catch {
      subscriptions = [];
      templates = [];
      runs = [];
      toast.error("Load failed", "Could not load dashboard integration data.");
    } finally {
      loading = false;
    }
  }

  async function addWidgetFeed() {
    if (!form.report_template) {
      toast.error("Missing report", "Select a report to feed the dashboard.");
      return;
    }

    const reportTemplateId = Number(form.report_template);
    const existing = subscriptions.find(
      (item) => item.report_template === reportTemplateId && item.frequency === form.frequency,
    );

    saving = true;
    try {
      let saved: ReportSubscription;

      if (existing) {
        const mergedChannels = Array.from(new Set([...(existing.delivery_channels ?? []), "dashboard_widget"]));
        saved = await api.patch<ReportSubscription>(`/settings/report-subscriptions/${existing.id}/`, {
          delivery_channels: mergedChannels,
          is_active: true,
        });
      } else {
        saved = await api.post<ReportSubscription>("/settings/report-subscriptions/", {
          report_template: reportTemplateId,
          frequency: form.frequency,
          output_format: "pdf",
          recipients: [],
          delivery_channels: ["dashboard_widget", "in_app"],
          is_active: true,
        });
      }

      subscriptions = [saved, ...subscriptions.filter((item) => item.id !== saved.id)];
      toast.success("Widget feed added", `${widgetTitle(saved)} now refreshes ${saved.frequency_display.toLowerCase()}.`);
    } catch (error) {
      if (error instanceof ApiError) {
        const message =
          error.fieldErrors.delivery_channels?.[0] ||
          error.fieldErrors.recipients?.[0] ||
          error.fieldErrors.non_field_errors?.[0] ||
          "Could not add dashboard widget feed.";
        toast.error("Save failed", message);
      } else {
        toast.error("Save failed", "Could not add dashboard widget feed.");
      }
    } finally {
      saving = false;
    }
  }

  async function removeWidgetFeed(subscription: ReportSubscription) {
    mutatingId = subscription.id;
    try {
      const remainingChannels = subscription.delivery_channels.filter((channel) => channel !== "dashboard_widget");

      if (remainingChannels.length === 0) {
        await api.delete(`/settings/report-subscriptions/${subscription.id}/`);
        subscriptions = subscriptions.filter((item) => item.id !== subscription.id);
      } else {
        const updated = await api.patch<ReportSubscription>(`/settings/report-subscriptions/${subscription.id}/`, {
          delivery_channels: remainingChannels,
        });
        subscriptions = subscriptions.map((item) => (item.id === updated.id ? updated : item));
      }

      toast.success("Widget feed removed", `${widgetTitle(subscription)} is no longer on your dashboard.`);
    } catch {
      toast.error("Update failed", "Could not remove widget feed.");
    } finally {
      mutatingId = null;
    }
  }

  async function refreshWidget(subscription: ReportSubscription) {
    runningTemplateId = subscription.report_template;
    try {
      await api.post<ReportRunRecord>(`/settings/report-templates/${subscription.report_template}/run/`, {});
      toast.success("Refresh queued", `${widgetTitle(subscription)} refresh has been queued.`);
      const runsPayload = await api.get<PaginatedResponse<ReportRunRecord> | ReportRunRecord[]>("/settings/report-runs/", {
        ordering: "-created_at",
        page_size: "200",
      });
      runs = unwrapList(runsPayload);
    } catch {
      toast.error("Refresh failed", "Could not refresh this dashboard widget.");
    } finally {
      runningTemplateId = null;
    }
  }

  $effect(() => {
    void loadDashboardIntegration();
  });
</script>

<div class="space-y-6">
  <section class="rounded-xl border border-neutral-200 bg-white p-5">
    <h1 class="text-2xl font-bold text-neutral-900">Dashboard Integration</h1>
    <p class="mt-2 text-sm text-neutral-600">Reports can feed dashboards through personal widget dispatch rules.</p>
  </section>

  <section class="rounded-xl border border-neutral-200 bg-white p-5">
    <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-700">Add Dashboard Widget Feed</h2>
    <p class="mt-1 text-xs text-neutral-500">Example: Headcount by Department | Source: HR Headcount Report | Refresh: Daily</p>

    <div class="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
      <label class="text-xs font-medium text-neutral-600 md:col-span-2">
        Source Report
        <select bind:value={form.report_template} class="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm text-neutral-800">
          {#if templates.length === 0}
            <option value="">No report templates available</option>
          {:else}
            {#each templates as template}
              <option value={String(template.id)}>{template.name}</option>
            {/each}
          {/if}
        </select>
      </label>

      <label class="text-xs font-medium text-neutral-600">
        Refresh
        <select bind:value={form.frequency} class="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm text-neutral-800">
          {#each refreshOptions as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
      </label>
    </div>

    <div class="mt-4 flex justify-end">
      <button
        type="button"
        onclick={addWidgetFeed}
        disabled={saving}
        class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {saving ? "Saving..." : "Add Widget Feed"}
      </button>
    </div>
  </section>

  <section class="rounded-xl border border-neutral-200 bg-white p-5">
    <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-700">Dashboard Widgets</h2>

    {#if loading}
      <p class="mt-3 text-sm text-neutral-500">Loading dashboard widgets...</p>
    {:else if dashboardWidgets.length === 0}
      <p class="mt-3 text-sm text-neutral-500">No dashboard widget feeds yet.</p>
    {:else}
      <div class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        {#each dashboardWidgets as widget (widget.id)}
          {@const sourceTemplate = templateById.get(widget.report_template)}
          {@const latestRun = latestRunByTemplate.get(widget.report_template)}
          <article class="rounded-lg border border-neutral-200 bg-neutral-50 p-4">
            <div class="flex items-start justify-between gap-3">
              <div>
                <h3 class="text-base font-semibold text-neutral-900">{widgetTitle(widget)}</h3>
                <p class="mt-1 text-xs text-neutral-600">
                  Source: {sourceTemplate?.module_source_display || "Unknown Module"} | {widget.report_template_name}
                </p>
              </div>
              <span class="rounded-full border border-neutral-300 bg-white px-2.5 py-1 text-[11px] font-semibold text-neutral-700">
                Refresh: {widget.frequency_display}
              </span>
            </div>

            <div class="mt-3 text-xs text-neutral-500 space-y-1">
              <p>Last widget refresh: {formatDateTime(widget.last_sent_at)}</p>
              <p>Last report run: {formatDateTime(latestRun?.created_at ?? null)}</p>
            </div>

            <div class="mt-4 flex flex-wrap gap-2">
              <a
                href={`/reports/${widget.report_template}`}
                class="rounded-lg border border-neutral-300 px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-100"
              >
                Open Report
              </a>
              <button
                type="button"
                onclick={() => refreshWidget(widget)}
                disabled={runningTemplateId === widget.report_template}
                class="rounded-lg border border-neutral-300 px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-100 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {runningTemplateId === widget.report_template ? "Refreshing..." : "Refresh Now"}
              </button>
              <button
                type="button"
                onclick={() => removeWidgetFeed(widget)}
                disabled={mutatingId === widget.id}
                class="rounded-lg bg-rose-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-rose-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {mutatingId === widget.id ? "Removing..." : "Remove"}
              </button>
            </div>
          </article>
        {/each}
      </div>
    {/if}
  </section>
</div>

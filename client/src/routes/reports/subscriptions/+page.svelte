<script lang="ts">
  import { ApiError, api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    PaginatedResponse,
    ReportSubscription,
    ReportSubscriptionDeliveryChannel,
    ReportSubscriptionFrequency,
    ReportTemplateListItem,
  } from "$lib/types";

  const frequencyOptions: { value: ReportSubscriptionFrequency; label: string }[] = [
    { value: "daily", label: "Daily" },
    { value: "weekly", label: "Weekly" },
    { value: "monthly", label: "Monthly" },
  ];

  const deliveryOptions: {
    value: ReportSubscriptionDeliveryChannel;
    label: string;
    description: string;
  }[] = [
    { value: "email", label: "Email", description: "Send report output to email recipients." },
    { value: "in_app", label: "In-app notification", description: "Notify inside the application." },
    { value: "dashboard_widget", label: "Dashboard widget", description: "Pin report updates to your dashboard." },
  ];

  let loading = $state(true);
  let creating = $state(false);
  let mutatingId = $state<number | null>(null);

  let subscriptions = $state<ReportSubscription[]>([]);
  let templates = $state<ReportTemplateListItem[]>([]);

  let form = $state({
    report_template: "",
    frequency: "weekly" as ReportSubscriptionFrequency,
    delivery_channels: ["email"] as ReportSubscriptionDeliveryChannel[],
    recipients: "",
  });

  function unwrapList<T>(payload: PaginatedResponse<T> | T[]): T[] {
    return Array.isArray(payload) ? payload : (payload?.results ?? []);
  }

  function formatDateTime(value: string | null): string {
    if (!value) return "Never";
    return new Date(value).toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function channelLabel(channel: ReportSubscriptionDeliveryChannel): string {
    const option = deliveryOptions.find((item) => item.value === channel);
    return option?.label ?? channel;
  }

  function parseRecipients(input: string): string[] {
    return input
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function toggleDeliveryChannel(channel: ReportSubscriptionDeliveryChannel) {
    if (form.delivery_channels.includes(channel)) {
      form = {
        ...form,
        delivery_channels: form.delivery_channels.filter((item) => item !== channel),
      };
      return;
    }

    form = {
      ...form,
      delivery_channels: [...form.delivery_channels, channel],
    };
  }

  async function loadSubscriptionsPage() {
    loading = true;
    try {
      const [subscriptionsPayload, templatesPayload] = await Promise.all([
        api.get<PaginatedResponse<ReportSubscription> | ReportSubscription[]>("/settings/report-subscriptions/", {
          ordering: "-updated_at",
        }),
        api.get<PaginatedResponse<ReportTemplateListItem> | ReportTemplateListItem[]>("/settings/report-templates/", {
          ordering: "name",
          is_active: "true",
        }),
      ]);

      subscriptions = unwrapList(subscriptionsPayload);
      templates = unwrapList(templatesPayload);

      if (!form.report_template && templates.length > 0) {
        form = {
          ...form,
          report_template: String(templates[0].id),
        };
      }
    } catch {
      subscriptions = [];
      templates = [];
      toast.error("Load failed", "Could not load report subscriptions.");
    } finally {
      loading = false;
    }
  }

  async function createOrUpdateSubscription() {
    if (!form.report_template) {
      toast.error("Missing report", "Select a report template.");
      return;
    }

    if (form.delivery_channels.length === 0) {
      toast.error("Missing delivery", "Select at least one delivery channel.");
      return;
    }

    const recipients = form.delivery_channels.includes("email")
      ? parseRecipients(form.recipients)
      : [];
    if (form.delivery_channels.includes("email") && recipients.length === 0) {
      toast.error("Missing recipients", "Add at least one email recipient for Email delivery.");
      return;
    }

    creating = true;

    const reportTemplateId = Number(form.report_template);
    const payload = {
      report_template: reportTemplateId,
      frequency: form.frequency,
      output_format: "pdf",
      recipients,
      delivery_channels: form.delivery_channels,
      is_active: true,
    };

    const existing = subscriptions.find(
      (item) => item.report_template === reportTemplateId && item.frequency === form.frequency,
    );

    try {
      let saved: ReportSubscription;
      if (existing) {
        saved = await api.patch<ReportSubscription>(`/settings/report-subscriptions/${existing.id}/`, payload);
        toast.success("Updated", `${saved.report_template_name} ${saved.frequency_display} subscription updated.`);
      } else {
        saved = await api.post<ReportSubscription>("/settings/report-subscriptions/", payload);
        toast.success("Created", `${saved.report_template_name} ${saved.frequency_display} subscription created.`);
      }

      subscriptions = [saved, ...subscriptions.filter((item) => item.id !== saved.id)];
      form = {
        ...form,
        recipients: form.delivery_channels.includes("email") ? form.recipients : "",
      };
    } catch (error) {
      if (error instanceof ApiError) {
        const fieldMessage =
          error.fieldErrors.delivery_channels?.[0] ||
          error.fieldErrors.recipients?.[0] ||
          error.fieldErrors.non_field_errors?.[0];

        if (fieldMessage) {
          toast.error("Save failed", fieldMessage);
        } else {
          toast.error("Save failed", "Could not save personal dispatch rule.");
        }
      } else {
        toast.error("Save failed", "Could not save personal dispatch rule.");
      }
    } finally {
      creating = false;
    }
  }

  async function toggleSubscription(subscription: ReportSubscription) {
    mutatingId = subscription.id;
    try {
      const updated = await api.patch<ReportSubscription>(`/settings/report-subscriptions/${subscription.id}/`, {
        is_active: !subscription.is_active,
      });
      subscriptions = subscriptions.map((item) => (item.id === updated.id ? updated : item));
      toast.success("Updated", `${updated.report_template_name} ${updated.is_active ? "activated" : "paused"}.`);
    } catch {
      toast.error("Update failed", "Could not update subscription.");
    } finally {
      mutatingId = null;
    }
  }

  $effect(() => {
    void loadSubscriptionsPage();
  });
</script>

<div class="space-y-6">
  <section class="rounded-xl border border-neutral-200 bg-white p-5">
    <h1 class="text-2xl font-bold text-neutral-900">Report Subscriptions</h1>
    <p class="mt-2 text-sm text-neutral-600">Create personal dispatch rules for reports without using admin scheduling.</p>
    <p class="mt-1 text-xs text-neutral-500">Admin dispatches are organization-level. User subscriptions are personal-level.</p>
  </section>

  <section class="rounded-xl border border-neutral-200 bg-white p-5 space-y-4">
    <div class="flex items-center justify-between">
      <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-700">Subscribe To A Report</h2>
      <span class="text-xs text-neutral-500">Personal Dispatch Rule</span>
    </div>

    <div class="grid grid-cols-1 gap-4 lg:grid-cols-3">
      <label class="text-xs font-medium text-neutral-600 lg:col-span-2">
        Report
        <select bind:value={form.report_template} class="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm text-neutral-800">
          {#if templates.length === 0}
            <option value="">No reports available</option>
          {:else}
            {#each templates as template}
              <option value={String(template.id)}>{template.name}</option>
            {/each}
          {/if}
        </select>
      </label>

      <label class="text-xs font-medium text-neutral-600">
        Frequency
        <select bind:value={form.frequency} class="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm text-neutral-800">
          {#each frequencyOptions as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
      </label>
    </div>

    <div>
      <p class="text-xs font-medium text-neutral-600">Delivery</p>
      <div class="mt-2 grid grid-cols-1 gap-3 md:grid-cols-3">
        {#each deliveryOptions as option}
          <label class="rounded-lg border border-neutral-300 bg-neutral-50 p-3 text-sm text-neutral-800">
            <div class="flex items-center gap-2">
              <input
                type="checkbox"
                checked={form.delivery_channels.includes(option.value)}
                onchange={() => toggleDeliveryChannel(option.value)}
              />
              <span class="font-semibold">{option.label}</span>
            </div>
            <p class="mt-1 text-xs text-neutral-500">{option.description}</p>
          </label>
        {/each}
      </div>
    </div>

    <label class="text-xs font-medium text-neutral-600 block">
      Email Recipients
      <input
        type="text"
        bind:value={form.recipients}
        placeholder="you@company.com, team@company.com"
        class="mt-1 w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm text-neutral-800"
      />
      <span class="mt-1 block text-xs text-neutral-500">Required only when Email delivery is selected.</span>
    </label>

    <button
      type="button"
      onclick={createOrUpdateSubscription}
      disabled={creating || loading || templates.length === 0}
      class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800 disabled:opacity-60"
    >
      {creating ? "Saving..." : "Save Subscription"}
    </button>
  </section>

  <section class="rounded-xl border border-neutral-200 bg-white p-5">
    <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-700">My Subscriptions</h2>

    {#if loading}
      <p class="mt-4 text-sm text-neutral-500">Loading subscriptions...</p>
    {:else if subscriptions.length === 0}
      <p class="mt-4 text-sm text-neutral-500">No personal dispatch rules yet.</p>
    {:else}
      <div class="mt-4 space-y-3">
        {#each subscriptions as subscription (subscription.id)}
          <article class="rounded-lg border border-neutral-200 bg-neutral-50 p-4">
            <div class="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <h3 class="text-sm font-semibold text-neutral-900">{subscription.report_template_name}</h3>
                <p class="mt-1 text-xs text-neutral-600">
                  {subscription.frequency_display} | {subscription.output_format_display}
                </p>
                <p class="mt-2 text-xs text-neutral-600">
                  Delivery:
                  {#if subscription.delivery_channels.length === 0}
                    None
                  {:else}
                    {subscription.delivery_channels.map((channel) => channelLabel(channel)).join(", ")}
                  {/if}
                </p>
                <p class="mt-1 text-xs text-neutral-600">
                  Recipients:
                  {subscription.recipients.length > 0 ? subscription.recipients.join(", ") : "N/A"}
                </p>
                <p class="mt-1 text-xs text-neutral-500">Last sent: {formatDateTime(subscription.last_sent_at)}</p>
              </div>

              <div class="flex items-center gap-2">
                <a
                  href={`/reports/${subscription.report_template}`}
                  class="rounded-lg border border-neutral-300 px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-100"
                >
                  Open Report
                </a>
                <button
                  type="button"
                  onclick={() => toggleSubscription(subscription)}
                  disabled={mutatingId === subscription.id}
                  class="rounded-lg bg-neutral-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-neutral-800 disabled:opacity-60"
                >
                  {subscription.is_active ? "Pause" : "Activate"}
                </button>
              </div>
            </div>
          </article>
        {/each}
      </div>
    {/if}
  </section>
</div>

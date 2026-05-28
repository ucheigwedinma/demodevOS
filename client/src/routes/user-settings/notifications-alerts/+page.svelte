<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    UserNotificationCategoryPreference,
    UserNotificationChannelKey,
    UserNotificationFrequencyKey,
    UserNotificationPreferences,
  } from "$lib/types";

  let loading = $state(true);
  let saving = $state(false);
  let preferences = $state<UserNotificationPreferences | null>(null);

  function parseError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      const messages = Object.values(error.fieldErrors).flat();
      if (messages.length > 0) return messages[0];
      if (typeof error.data.detail === "string") return error.data.detail;
    }
    return fallback;
  }

  async function loadPreferences() {
    loading = true;
    try {
      preferences = await api.get<UserNotificationPreferences>("/auth/notification-preferences/");
    } catch (error) {
      preferences = null;
      toast.error("Load failed", parseError(error, "Could not load notification preferences."));
    } finally {
      loading = false;
    }
  }

  function globalChannelEnabled(key: UserNotificationChannelKey): boolean {
    if (!preferences) return false;
    if (key === "in_app") return preferences.channel_in_app_enabled;
    if (key === "email") return preferences.channel_email_enabled;
    if (key === "push") return preferences.channel_push_enabled;
    return preferences.channel_sms_enabled;
  }

  function channelLabel(key: UserNotificationChannelKey): string {
    const label = preferences?.channel_options.find((row) => row.key === key)?.label;
    return label || key;
  }

  function setGlobalChannel(key: UserNotificationChannelKey, enabled: boolean) {
    if (!preferences) return;
    if (key === "in_app") preferences.channel_in_app_enabled = enabled;
    if (key === "email") preferences.channel_email_enabled = enabled;
    if (key === "push") preferences.channel_push_enabled = enabled;
    if (key === "sms") preferences.channel_sms_enabled = enabled;
  }

  function updateCategory(
    key: string,
    update: (row: UserNotificationCategoryPreference) => UserNotificationCategoryPreference
  ) {
    if (!preferences) return;
    preferences.categories = preferences.categories.map((row) => (row.key === key ? update(row) : row));
  }

  function toggleCategoryChannel(categoryKey: string, channel: UserNotificationChannelKey, enabled: boolean) {
    updateCategory(categoryKey, (row) => {
      const nextChannels = enabled ? [...row.channels, channel] : row.channels.filter((item) => item !== channel);
      return {
        ...row,
        channels: Array.from(new Set(nextChannels)),
      };
    });
  }

  async function savePreferences() {
    if (!preferences) return;
    saving = true;
    try {
      const updated = await api.patch<UserNotificationPreferences>("/auth/notification-preferences/", {
        channel_in_app_enabled: preferences.channel_in_app_enabled,
        channel_email_enabled: preferences.channel_email_enabled,
        channel_push_enabled: preferences.channel_push_enabled,
        channel_sms_enabled: preferences.channel_sms_enabled,
        categories: preferences.categories.map((row) => ({
          key: row.key,
          enabled: row.enabled,
          channels: row.channels,
          frequency: row.frequency,
        })),
      });
      preferences = updated;
      toast.success("Updated", "Notification and alert settings have been saved.");
    } catch (error) {
      toast.error("Save failed", parseError(error, "Could not save notification preferences."));
    } finally {
      saving = false;
    }
  }

  $effect(() => {
    loadPreferences();
  });
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
  </div>
{:else if !preferences}
  <div class="rounded-xl border border-red-200 bg-red-50 p-6">
    <h2 class="text-base font-semibold text-red-900">Notifications unavailable</h2>
    <p class="mt-1 text-sm text-red-700">Could not load your notification and alert settings.</p>
    <button
      onclick={() => loadPreferences()}
      class="mt-4 rounded-lg border border-red-300 bg-white px-3.5 py-2 text-sm font-medium text-red-800 hover:bg-red-100"
    >
      Retry
    </button>
  </div>
{:else}
  <div class="space-y-6">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-neutral-900">Notifications & Alerts</h1>
        <p class="mt-1 text-sm text-neutral-500">
          Choose channels, category-level preferences, and delivery frequency for workflow alerts.
        </p>
      </div>
      <button
        onclick={savePreferences}
        disabled={saving}
        class="rounded-lg bg-neutral-900 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {saving ? "Saving..." : "Save Changes"}
      </button>
    </div>

    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h2 class="text-sm font-semibold text-neutral-900 mb-4">Notification channels</h2>
      <div class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        {#each preferences.channel_options as channel}
          <label class="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
            <div class="flex items-start justify-between gap-2">
              <div>
                <p class="text-sm font-semibold text-neutral-900">{channel.label}</p>
                <p class="mt-1 text-xs text-neutral-500">Enable this channel for alert delivery.</p>
              </div>
              <input
                type="checkbox"
                checked={globalChannelEnabled(channel.key as UserNotificationChannelKey)}
                onchange={(event) =>
                  setGlobalChannel(
                    channel.key as UserNotificationChannelKey,
                    (event.currentTarget as HTMLInputElement).checked
                  )}
                class="rounded border-neutral-300"
              />
            </div>
          </label>
        {/each}
      </div>
    </section>

    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h2 class="text-sm font-semibold text-neutral-900 mb-4">Notification categories</h2>
      <div class="space-y-3">
        {#each preferences.categories as category}
          <article class="rounded-lg border border-neutral-200 p-4 {category.enabled ? 'bg-white' : 'bg-neutral-50'}">
            <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div class="min-w-0">
                <p class="truncate text-sm font-semibold text-neutral-900">{category.label}</p>
                <p class="mt-1 text-xs text-neutral-500">Configure per-channel delivery and digest timing.</p>
              </div>
              <label class="inline-flex items-center gap-2 text-sm text-neutral-700">
                <input
                  type="checkbox"
                  checked={category.enabled}
                  onchange={(event) =>
                    updateCategory(category.key, (row) => ({
                      ...row,
                      enabled: (event.currentTarget as HTMLInputElement).checked,
                    }))}
                  class="rounded border-neutral-300"
                />
                Enable
              </label>
            </div>

            <div class="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-[1fr_220px]">
              <div class="flex flex-wrap gap-2">
                {#each ["in_app", "email", "push", "sms"] as channelKey}
                  <label class="inline-flex items-center gap-2 rounded-lg border border-neutral-200 px-2.5 py-1.5 text-xs text-neutral-700 {(!category.enabled || !globalChannelEnabled(channelKey as UserNotificationChannelKey)) ? 'opacity-45' : ''}">
                    <input
                      type="checkbox"
                      checked={category.channels.includes(channelKey as UserNotificationChannelKey)}
                      disabled={!category.enabled || !globalChannelEnabled(channelKey as UserNotificationChannelKey)}
                      onchange={(event) =>
                        toggleCategoryChannel(
                          category.key,
                          channelKey as UserNotificationChannelKey,
                          (event.currentTarget as HTMLInputElement).checked
                        )}
                      class="rounded border-neutral-300"
                    />
                    {channelLabel(channelKey as UserNotificationChannelKey)}
                  </label>
                {/each}
              </div>

              <div>
                <label for={`frequency-${category.key}`} class="mb-1 block text-xs font-medium text-neutral-600">Frequency</label>
                <select
                  id={`frequency-${category.key}`}
                  value={category.frequency}
                  disabled={!category.enabled}
                  onchange={(event) =>
                    updateCategory(category.key, (row) => ({
                      ...row,
                      frequency: (event.currentTarget as HTMLSelectElement).value as UserNotificationFrequencyKey,
                    }))}
                  class="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent disabled:bg-neutral-100 disabled:text-neutral-500"
                >
                  {#each preferences.frequency_options as option}
                    <option value={option.key}>{option.label}</option>
                  {/each}
                </select>
              </div>
            </div>
          </article>
        {/each}
      </div>
    </section>
  </div>
{/if}

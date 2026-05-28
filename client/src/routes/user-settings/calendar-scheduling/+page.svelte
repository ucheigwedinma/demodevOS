<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { i18n } from "$lib/stores/i18n.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    CalendarIcalRotateResponse,
    UserCalendarSchedulingPreferences,
  } from "$lib/types";
  import ConfirmModal from "$lib/components/teams/ConfirmModal.svelte";

  let loading = $state(true);
  let saving = $state(false);
  let preferences = $state<UserCalendarSchedulingPreferences | null>(null);

  // iCal feed state — token is shown ONCE at allocation. Rotating mints a new
  // one and invalidates the old. We never persist the raw token in this app.
  let icalToken = $state<string>("");
  let icalRotating = $state(false);
  let rotateConfirmOpen = $state(false);

  const REMINDER_PRESETS = [
    { value: 0, label_key: "workspace.calendar.form.reminder.off" },
    { value: 5, label_key: "workspace.calendar.form.reminder.5min" },
    { value: 15, label_key: "workspace.calendar.form.reminder.15min" },
    { value: 30, label_key: "workspace.calendar.form.reminder.30min" },
    { value: 60, label_key: "workspace.calendar.form.reminder.1hr" },
    { value: 1440, label_key: "workspace.calendar.form.reminder.1day" },
  ];

  async function rotateIcalToken() {
    rotateConfirmOpen = false;
    icalRotating = true;
    try {
      const out = await api.post<CalendarIcalRotateResponse>(
        "/calendar/feed/rotate-token/",
        {},
      );
      icalToken = out.token;
      toast.success(
        i18n.t("workspace.calendar.ical.rotated"),
        i18n.t("workspace.calendar.ical.rotated_helper"),
      );
    } catch (err) {
      toast.error("Rotate failed", parseError(err, "Could not rotate iCal token."));
    } finally {
      icalRotating = false;
    }
  }

  async function copyFeedUrl() {
    if (!icalToken) return;
    const origin = typeof window !== "undefined" ? window.location.origin : "";
    const url = `${origin}/api/calendar/feed/?token=${icalToken}`;
    try {
      await navigator.clipboard.writeText(url);
      toast.success(i18n.t("workspace.calendar.ical.copied"));
    } catch {
      toast.error("Copy failed");
    }
  }

  function setReminder(minutes: number) {
    if (!preferences) return;
    preferences.default_reminder_minutes = minutes;
  }

  const DEFAULT_DURATION_OPTIONS = [15, 30, 45, 60, 90];
  const DEFAULT_BUFFER_OPTIONS = [0, 5, 10, 15, 30];

  function parseError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      const messages = Object.values(error.fieldErrors).flat();
      if (messages.length > 0) return messages[0];
      if (typeof error.data.detail === "string") return error.data.detail;
    }
    return fallback;
  }

  function normalizeTimeValue(value: string): string {
    const raw = String(value || "").trim();
    if (!raw) return "";
    const [hour = "00", minute = "00"] = raw.split(":");
    return `${hour.padStart(2, "0")}:${minute.padStart(2, "0")}`;
  }

  function withNumericOption(base: number[], value: number): number[] {
    if (base.includes(value)) return base;
    return [value, ...base];
  }

  function toggleWorkingDay(day: number, checked: boolean) {
    if (!preferences) return;
    const current = Array.isArray(preferences.working_days) ? preferences.working_days : [];
    if (checked) {
      if (!current.includes(day)) {
        preferences.working_days = [...current, day].sort((a, b) => a - b);
      }
      return;
    }
    preferences.working_days = current.filter((item) => item !== day);
  }

  function isWorkingDay(day: number): boolean {
    if (!preferences) return false;
    return preferences.working_days.includes(day);
  }

  async function loadPreferences() {
    loading = true;
    try {
      const data = await api.get<UserCalendarSchedulingPreferences>("/auth/calendar-scheduling-preferences/");
      preferences = {
        ...data,
        working_hours_start: normalizeTimeValue(data.working_hours_start),
        working_hours_end: normalizeTimeValue(data.working_hours_end),
      };
    } catch (error) {
      preferences = null;
      toast.error("Load failed", parseError(error, "Could not load calendar and scheduling preferences."));
    } finally {
      loading = false;
    }
  }

  async function savePreferences() {
    if (!preferences) return;
    saving = true;
    try {
      const updated = await api.patch<UserCalendarSchedulingPreferences>("/auth/calendar-scheduling-preferences/", {
        working_hours_start: preferences.working_hours_start,
        working_hours_end: preferences.working_hours_end,
        working_days: preferences.working_days,
        default_meeting_duration_minutes: Number(preferences.default_meeting_duration_minutes),
        meeting_buffer_minutes: Number(preferences.meeting_buffer_minutes),
        timezone_override: preferences.timezone_override.trim(),
        calendar_sync_google: preferences.calendar_sync_google,
        calendar_sync_outlook: preferences.calendar_sync_outlook,
        calendar_sync_ical: preferences.calendar_sync_ical,
        default_reminder_minutes: preferences.default_reminder_minutes,
      });
      preferences = {
        ...updated,
        working_hours_start: normalizeTimeValue(updated.working_hours_start),
        working_hours_end: normalizeTimeValue(updated.working_hours_end),
      };
      toast.success("Updated", "Calendar and scheduling preferences have been saved.");
    } catch (error) {
      toast.error("Save failed", parseError(error, "Could not save calendar and scheduling preferences."));
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
    <h2 class="text-base font-semibold text-red-900">Calendar settings unavailable</h2>
    <p class="mt-1 text-sm text-red-700">Could not load your calendar and scheduling preferences.</p>
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
        <h1 class="text-2xl font-bold text-neutral-900">Calendar & Scheduling</h1>
        <p class="mt-1 text-sm text-neutral-500">
          Configure working patterns, meeting defaults, timezone behavior, and calendar sync providers.
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
      <h2 class="text-sm font-semibold text-neutral-900 mb-4">Working schedule</h2>
      <div class="grid grid-cols-1 gap-5 md:grid-cols-2">
        <div>
          <label for="working_hours_start" class="mb-1.5 block text-sm font-medium text-neutral-700">Working hours start</label>
          <input
            id="working_hours_start"
            type="time"
            bind:value={preferences.working_hours_start}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          />
        </div>

        <div>
          <label for="working_hours_end" class="mb-1.5 block text-sm font-medium text-neutral-700">Working hours end</label>
          <input
            id="working_hours_end"
            type="time"
            bind:value={preferences.working_hours_end}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          />
        </div>
      </div>

      <div class="mt-5">
        <p class="mb-2 text-sm font-medium text-neutral-700">Working days</p>
        <div class="flex flex-wrap gap-2">
          {#each preferences.working_day_options as option}
            <label
              class="inline-flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-colors
                {isWorkingDay(option.value)
                  ? 'border-neutral-900 bg-neutral-900 text-white'
                  : 'border-neutral-300 bg-white text-neutral-700 hover:bg-neutral-50'}"
            >
              <input
                type="checkbox"
                checked={isWorkingDay(option.value)}
                onchange={(event) =>
                  toggleWorkingDay(
                    option.value,
                    (event.currentTarget as HTMLInputElement).checked
                  )}
                class="hidden"
              />
              {option.label}
            </label>
          {/each}
        </div>
      </div>
    </section>

    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h2 class="text-sm font-semibold text-neutral-900 mb-4">Meeting defaults</h2>
      <div class="grid grid-cols-1 gap-5 md:grid-cols-2">
        <div>
          <label for="default_meeting_duration_minutes" class="mb-1.5 block text-sm font-medium text-neutral-700">Default meeting duration</label>
          <select
            id="default_meeting_duration_minutes"
            bind:value={preferences.default_meeting_duration_minutes}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            {#each withNumericOption(DEFAULT_DURATION_OPTIONS, preferences.default_meeting_duration_minutes) as value}
              <option value={value}>{value} minutes</option>
            {/each}
          </select>
        </div>

        <div>
          <label for="meeting_buffer_minutes" class="mb-1.5 block text-sm font-medium text-neutral-700">Time buffer between meetings</label>
          <select
            id="meeting_buffer_minutes"
            bind:value={preferences.meeting_buffer_minutes}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            {#each withNumericOption(DEFAULT_BUFFER_OPTIONS, preferences.meeting_buffer_minutes) as value}
              <option value={value}>{value} minutes</option>
            {/each}
          </select>
        </div>

        <div class="md:col-span-2">
          <label for="timezone_override" class="mb-1.5 block text-sm font-medium text-neutral-700">Timezone override</label>
          <select
            id="timezone_override"
            bind:value={preferences.timezone_override}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            <option value="">Use profile timezone</option>
            {#each preferences.timezone_options as timezone}
              <option value={timezone}>{timezone}</option>
            {/each}
          </select>
        </div>
      </div>
    </section>

    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h2 class="text-sm font-semibold text-neutral-900 mb-4">Calendar sync</h2>
      <div class="grid grid-cols-1 gap-3 md:grid-cols-3">
        <label class="inline-flex items-center gap-2 rounded-lg border border-neutral-200 bg-neutral-50 px-3.5 py-2.5 text-sm text-neutral-700">
          <input
            type="checkbox"
            bind:checked={preferences.calendar_sync_google}
            class="rounded border-neutral-300"
          />
          Google
        </label>

        <label class="inline-flex items-center gap-2 rounded-lg border border-neutral-200 bg-neutral-50 px-3.5 py-2.5 text-sm text-neutral-700">
          <input
            type="checkbox"
            bind:checked={preferences.calendar_sync_outlook}
            class="rounded border-neutral-300"
          />
          Outlook
        </label>

        <label class="inline-flex items-center gap-2 rounded-lg border border-neutral-200 bg-neutral-50 px-3.5 py-2.5 text-sm text-neutral-700">
          <input
            type="checkbox"
            bind:checked={preferences.calendar_sync_ical}
            class="rounded border-neutral-300"
          />
          iCal
        </label>
      </div>
    </section>

    <!-- Default reminder (Calendar feature) -->
    <section class="rounded-2xl border border-neutral-200 bg-white p-5">
      <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-700">
        {i18n.t("workspace.calendar.settings.default_reminder")}
      </h2>
      <p class="mt-1 text-sm text-neutral-500">
        {i18n.t("workspace.calendar.settings.default_reminder_helper")}
      </p>
      <div class="mt-4 flex flex-wrap gap-2">
        {#each REMINDER_PRESETS as preset}
          {@const isActive = preferences.default_reminder_minutes === preset.value}
          <button
            type="button"
            onclick={() => setReminder(preset.value)}
            class="rounded-full border px-3 py-1 text-xs font-semibold {isActive ? 'border-neutral-900 bg-neutral-900 text-white' : 'border-neutral-300 bg-white text-neutral-700 hover:border-neutral-400'}"
          >
            {i18n.t(preset.label_key)}
          </button>
        {/each}
      </div>
    </section>

    <!-- iCal feed (Calendar feature) -->
    <section class="rounded-2xl border border-neutral-200 bg-white p-5">
      <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-700">
        {i18n.t("workspace.calendar.ical.title")}
      </h2>
      <p class="mt-1 text-sm text-neutral-500">
        {i18n.t("workspace.calendar.ical.helper")}
      </p>
      {#if icalToken}
        <div class="mt-4 space-y-2">
          <label class="block text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400" for="ical-url">
            {i18n.t("workspace.calendar.ical.url_label")}
          </label>
          <div class="flex flex-wrap items-center gap-2">
            <input
              id="ical-url"
              type="text"
              readonly
              value={`${typeof window !== "undefined" ? window.location.origin : ""}/api/calendar/feed/?token=${icalToken}`}
              class="flex-1 min-w-0 rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-2 text-xs font-mono text-neutral-700"
            />
            <button
              type="button"
              onclick={copyFeedUrl}
              class="rounded-xl border border-neutral-300 bg-white px-3 py-2 text-xs font-semibold text-neutral-700 hover:border-neutral-400"
            >
              {i18n.t("workspace.calendar.ical.copy")}
            </button>
          </div>
          <p class="text-[11px] text-neutral-400">
            {i18n.t("workspace.calendar.ical.shown_once")}
          </p>
        </div>
      {:else}
        <p class="mt-4 text-sm text-neutral-500">
          {i18n.t("workspace.calendar.ical.no_token_yet")}
        </p>
      {/if}
      <div class="mt-4">
        <button
          type="button"
          onclick={() => (rotateConfirmOpen = true)}
          disabled={icalRotating}
          class="rounded-xl border border-neutral-300 bg-white px-4 py-2 text-sm font-semibold text-neutral-700 hover:border-neutral-400 disabled:opacity-60"
        >
          {icalToken ? i18n.t("workspace.calendar.ical.rotate") : i18n.t("workspace.calendar.ical.create")}
        </button>
      </div>
      <p class="mt-3 text-[11px] text-neutral-400">
        💡 {i18n.t("workspace.calendar.ical.poll_helper")}
      </p>
    </section>
  </div>
{/if}

<ConfirmModal
  open={rotateConfirmOpen}
  destructive
  title={i18n.t("workspace.calendar.ical.rotate")}
  message={i18n.t("workspace.calendar.ical.rotate_confirm")}
  confirmLabel={i18n.t("workspace.calendar.ical.rotate")}
  onclose={() => (rotateConfirmOpen = false)}
  onconfirm={rotateIcalToken}
/>

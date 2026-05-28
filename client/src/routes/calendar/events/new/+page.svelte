<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { page } from "$app/stores";
  import { api, ApiError } from "$lib/api";
  import { i18n } from "$lib/stores/i18n.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    CalendarEventCreatePayload,
    CalendarEventDetail,
    UserCalendarSchedulingPreferences,
  } from "$lib/types";
  import EventForm from "$lib/components/calendar/EventForm.svelte";

  let submitting = $state(false);
  let prefs = $state<UserCalendarSchedulingPreferences | null>(null);

  // If launched with ?at=ISO, pre-fill starts_at to that time.
  let prefilledStart = $state<string | undefined>(undefined);

  onMount(() => {
    const at = $page.url.searchParams.get("at");
    if (at) prefilledStart = at;
    void loadPrefs();
  });

  async function loadPrefs() {
    try {
      prefs = await api.get<UserCalendarSchedulingPreferences>(
        "/auth/calendar-scheduling-preferences/",
      );
    } catch {
      prefs = null;
    }
  }

  async function submit(payload: CalendarEventCreatePayload) {
    submitting = true;
    try {
      const created = await api.post<CalendarEventDetail>("/calendar/events/", payload);
      toast.success(i18n.t("workspace.calendar.toast.created"));
      goto(`/calendar/events/${created.id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        const msg =
          (err.fieldErrors && Object.values(err.fieldErrors)[0]?.[0]) ||
          (err.data?.detail as string) ||
          i18n.t("workspace.calendar.toast.create_failed");
        toast.error(msg);
      } else {
        console.error(err);
        toast.error(i18n.t("workspace.calendar.toast.create_failed"));
      }
    } finally {
      submitting = false;
    }
  }

  function cancel() {
    goto("/calendar");
  }
</script>

<div class="space-y-4">
  <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-blue-600">
    <a href="/calendar" class="hover:text-blue-700">{i18n.t("workspace.calendar.eyebrow")}</a>
    <span class="text-neutral-300"> › </span>
    <a href="/calendar" class="hover:text-blue-700">{i18n.t("workspace.calendar.title")}</a>
  </p>
  <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">
    {i18n.t("workspace.calendar.new_event")}
  </h1>

  <EventForm
    initial={prefilledStart ? { starts_at: prefilledStart } : {}}
    mode="create"
    userDefaultReminder={prefs?.default_reminder_minutes ?? 15}
    onsubmit={submit}
    oncancel={cancel}
    {submitting}
  />
</div>

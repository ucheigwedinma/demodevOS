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
  import UpdateScopePrompt, { type UpdateScope } from "$lib/components/calendar/UpdateScopePrompt.svelte";

  let id = $derived(parseInt($page.params.id));

  let detail = $state<CalendarEventDetail | null>(null);
  let loading = $state(true);
  let notFound = $state(false);
  let submitting = $state(false);
  let prefs = $state<UserCalendarSchedulingPreferences | null>(null);

  // Scope prompt state — only triggered on submit for recurring events.
  let scopePromptOpen = $state(false);
  let pendingPayload = $state<CalendarEventCreatePayload | null>(null);

  onMount(load);

  async function load() {
    loading = true;
    notFound = false;
    try {
      [detail, prefs] = await Promise.all([
        api.get<CalendarEventDetail>(`/calendar/events/${id}/`),
        api
          .get<UserCalendarSchedulingPreferences>("/auth/calendar-scheduling-preferences/")
          .catch(() => null),
      ]);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) notFound = true;
      else console.error(err);
    } finally {
      loading = false;
    }
  }

  function isRecurring(): boolean {
    return !!detail?.recurrence_rule;
  }

  async function submit(payload: CalendarEventCreatePayload) {
    if (isRecurring()) {
      // Hold the payload and ask for the scope.
      pendingPayload = payload;
      scopePromptOpen = true;
      return;
    }
    await save(payload, "all");
  }

  async function save(payload: CalendarEventCreatePayload, scope: UpdateScope) {
    if (!detail) return;
    submitting = true;
    try {
      const qs = isRecurring() ? `?scope=${scope}` : "";
      await api.patch<CalendarEventDetail>(`/calendar/events/${detail.id}/${qs}`, payload);
      toast.success(i18n.t("workspace.calendar.toast.saved"));
      goto(`/calendar/events/${detail.id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        const msg =
          (err.fieldErrors && Object.values(err.fieldErrors)[0]?.[0]) ||
          (err.data?.detail as string) ||
          i18n.t("workspace.calendar.toast.save_failed");
        toast.error(msg);
      } else {
        console.error(err);
        toast.error(i18n.t("workspace.calendar.toast.save_failed"));
      }
    } finally {
      submitting = false;
    }
  }

  function confirmScope(scope: UpdateScope) {
    scopePromptOpen = false;
    if (pendingPayload) {
      const p = pendingPayload;
      pendingPayload = null;
      void save(p, scope);
    }
  }

  function cancel() {
    if (detail) goto(`/calendar/events/${detail.id}`);
    else goto("/calendar");
  }
</script>

{#if loading}
  <div class="flex items-center justify-center py-28">
    <div class="h-7 w-7 animate-spin rounded-full border-[2.5px] border-neutral-200 border-t-neutral-900"></div>
  </div>
{:else if notFound || !detail}
  <div class="mx-auto max-w-md rounded-2xl border border-dashed border-neutral-300 bg-white px-6 py-12 text-center">
    <p class="text-3xl">🔍</p>
    <p class="mt-3 text-base font-semibold text-neutral-800">
      {i18n.t("workspace.calendar.error.not_found")}
    </p>
    <a
      href="/calendar"
      class="mt-4 inline-flex items-center gap-2 rounded-xl border border-neutral-300 bg-white px-4 py-2 text-sm font-semibold text-neutral-700 hover:border-neutral-400"
    >
      {i18n.t("workspace.calendar.back_to_calendar")}
    </a>
  </div>
{:else}
  <div class="space-y-4">
    <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-blue-600">
      <a href="/calendar" class="hover:text-blue-700">{i18n.t("workspace.calendar.eyebrow")}</a>
      <span class="text-neutral-300"> › </span>
      <a href="/calendar" class="hover:text-blue-700">{i18n.t("workspace.calendar.title")}</a>
      <span class="text-neutral-300"> › </span>
      <a href={`/calendar/events/${detail.id}`} class="hover:text-blue-700 normal-case tracking-normal">{detail.title}</a>
    </p>
    <h1 class="text-2xl font-bold tracking-wide text-neutral-800">
      {i18n.t("workspace.calendar.edit_event")}
    </h1>

    <EventForm
      initial={detail}
      mode="edit"
      lockKind
      userDefaultReminder={prefs?.default_reminder_minutes ?? 15}
      onsubmit={submit}
      oncancel={cancel}
      {submitting}
    />
  </div>
{/if}

<UpdateScopePrompt
  open={scopePromptOpen}
  onclose={() => {
    scopePromptOpen = false;
    pendingPayload = null;
  }}
  onconfirm={confirmScope}
/>

<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { page } from "$app/stores";
  import { api, ApiError } from "$lib/api";
  import { i18n } from "$lib/stores/i18n.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    CalendarEventAttendee,
    CalendarEventDetail,
  } from "$lib/types";
  import DataStateBanner from "$lib/components/DataStateBanner.svelte";
  import ConfirmModal from "$lib/components/teams/ConfirmModal.svelte";
  import KindChip from "$lib/components/calendar/KindChip.svelte";
  import VisibilityChip from "$lib/components/calendar/VisibilityChip.svelte";

  let id = $derived(parseInt($page.params.id));

  let detail = $state<CalendarEventDetail | null>(null);
  let attendees = $state<CalendarEventAttendee[]>([]);
  let loading = $state(true);
  let notFound = $state(false);
  let error = $state<string | null>(null);

  let cancelOpen = $state(false);
  let deleteOpen = $state(false);
  let removingAttendeeId = $state<number | null>(null);

  onMount(load);

  async function load() {
    loading = true;
    notFound = false;
    error = null;
    try {
      const [det, atts] = await Promise.all([
        api.get<CalendarEventDetail>(`/calendar/events/${id}/`),
        api
          .get<CalendarEventAttendee[]>(`/calendar/events/${id}/attendees/`)
          .catch(() => [] as CalendarEventAttendee[]),
      ]);
      detail = det;
      attendees = atts;
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) notFound = true;
      else {
        console.error(err);
        error = i18n.t("workspace.calendar.error.load");
      }
    } finally {
      loading = false;
    }
  }

  function fmtTimeRange(d: CalendarEventDetail): string {
    const fmt = new Intl.DateTimeFormat(i18n.locale, {
      weekday: "long",
      month: "long",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
    const start = fmt.format(new Date(d.starts_at));
    if (!d.ends_at) return start;
    const endFmt = new Intl.DateTimeFormat(i18n.locale, {
      hour: "numeric",
      minute: "2-digit",
    });
    return `${start} – ${endFmt.format(new Date(d.ends_at))}`;
  }

  async function cancelEvent() {
    if (!detail) return;
    cancelOpen = false;
    try {
      await api.post(`/calendar/events/${detail.id}/cancel/`, {});
      toast.success(i18n.t("workspace.calendar.toast.cancelled"));
      await load();
    } catch (err) {
      console.error(err);
      toast.error(i18n.t("workspace.calendar.toast.cancel_failed"));
    }
  }

  async function deleteEvent() {
    if (!detail) return;
    deleteOpen = false;
    try {
      await api.delete(`/calendar/events/${detail.id}/`);
      toast.success(i18n.t("workspace.calendar.toast.deleted"));
      goto("/calendar");
    } catch (err) {
      console.error(err);
      toast.error(i18n.t("workspace.calendar.toast.delete_failed"));
    }
  }

  async function removeAttendee(userId: number) {
    if (!detail) return;
    const previous = attendees;
    attendees = attendees.filter((a) => a.user.id !== userId); // optimistic
    removingAttendeeId = userId;
    try {
      await api.delete(`/calendar/events/${detail.id}/attendees/${userId}/`);
      toast.success(i18n.t("workspace.calendar.toast.attendee_removed"));
    } catch (err) {
      attendees = previous; // rollback
      console.error(err);
      toast.error(i18n.t("workspace.calendar.toast.remove_failed"));
    } finally {
      removingAttendeeId = null;
    }
  }

  function edit() {
    if (detail) goto(`/calendar/events/${detail.id}/edit`);
  }

  let isCreator = $derived(detail?.my_role === "creator");
  let isAttendee = $derived(detail?.my_role === "attendee");
</script>

{#if loading}
  <div class="flex items-center justify-center py-28">
    <div class="h-7 w-7 animate-spin rounded-full border-[2.5px] border-neutral-200 border-t-neutral-900"></div>
  </div>
{:else if notFound}
  <div class="mx-auto max-w-md rounded-2xl border border-dashed border-neutral-300 bg-white px-6 py-12 text-center">
    <p class="text-3xl">🔍</p>
    <p class="mt-3 text-base font-semibold text-neutral-800">
      {i18n.t("workspace.calendar.error.not_found")}
    </p>
    <p class="mt-1 text-sm text-neutral-500">
      {i18n.t("workspace.calendar.error.not_found_helper")}
    </p>
    <a
      href="/calendar"
      class="mt-4 inline-flex items-center gap-2 rounded-xl border border-neutral-300 bg-white px-4 py-2 text-sm font-semibold text-neutral-700 hover:border-neutral-400"
    >
      {i18n.t("workspace.calendar.back_to_calendar")}
    </a>
  </div>
{:else if error || !detail}
  <DataStateBanner
    title={i18n.t("workspace.calendar.error.load")}
    message={i18n.t("workspace.calendar.error.load_helper")}
    onRetry={load}
  />
{:else}
  <div class="space-y-6">
    <!-- Breadcrumbs -->
    <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-blue-600">
      <a href="/calendar" class="hover:text-blue-700">{i18n.t("workspace.calendar.eyebrow")}</a>
      <span class="text-neutral-300"> › </span>
      <a href="/calendar" class="hover:text-blue-700">{i18n.t("workspace.calendar.title")}</a>
      <span class="text-neutral-300"> › </span>
      <span class="text-blue-600 normal-case tracking-normal">{detail.title}</span>
    </p>

    <!-- Header card -->
    <section class="rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm">
      <div class="flex flex-wrap items-start gap-3">
        <div class="flex flex-wrap items-center gap-2">
          <KindChip kind={detail.kind} size="md" />
          <VisibilityChip visibility={detail.visibility} size="md" />
          {#if detail.is_cancelled}
            <span class="rounded-full border border-rose-200 bg-rose-50 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-rose-700">
              {i18n.t("workspace.calendar.cancelled")}
            </span>
          {/if}
        </div>
      </div>

      <h1 class="mt-3 text-2xl font-bold tracking-wide text-neutral-800 {detail.is_cancelled ? 'line-through opacity-60' : ''}">
        {detail.title}
      </h1>
      {#if detail.description}
        <p class="mt-2 max-w-2xl text-sm text-neutral-600">{detail.description}</p>
      {/if}

      <dl class="mt-4 space-y-1 text-sm text-neutral-700">
        <div class="flex items-start gap-2">
          <span aria-hidden="true">🗓</span>
          <span>{fmtTimeRange(detail)} <span class="text-neutral-400">· {detail.timezone}</span></span>
        </div>
        {#if detail.recurrence_rule}
          <div class="flex items-start gap-2">
            <span aria-hidden="true">↻</span>
            <span class="font-mono text-xs text-neutral-500">RRULE:{detail.recurrence_rule}</span>
          </div>
        {/if}
        {#if detail.location}
          <div class="flex items-start gap-2">
            <span aria-hidden="true">📍</span>
            <span>{detail.location}</span>
          </div>
        {/if}
        {#if detail.meeting_link}
          <div class="flex items-start gap-2">
            <span aria-hidden="true">🔗</span>
            <a href={detail.meeting_link} target="_blank" rel="noopener" class="text-sky-700 hover:underline">
              {detail.meeting_link}
            </a>
          </div>
        {/if}
      </dl>

      <div class="mt-5 flex flex-wrap items-center gap-2">
        {#if isCreator}
          <button
            type="button"
            onclick={edit}
            class="rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800"
          >
            {i18n.t("workspace.calendar.actions.edit")}
          </button>
          {#if !detail.is_cancelled}
            <button
              type="button"
              onclick={() => (cancelOpen = true)}
              class="rounded-xl border border-neutral-300 bg-white px-4 py-2 text-sm font-semibold text-neutral-700 hover:border-neutral-400"
            >
              {i18n.t("workspace.calendar.actions.cancel")}
            </button>
          {/if}
          <button
            type="button"
            onclick={() => (deleteOpen = true)}
            class="rounded-xl border border-rose-200 bg-white px-4 py-2 text-sm font-semibold text-rose-700 hover:border-rose-400"
          >
            {i18n.t("workspace.calendar.actions.delete")}
          </button>
        {:else if isAttendee}
          <button
            type="button"
            onclick={() => removeAttendee($page.data?.user?.id ?? 0)}
            class="rounded-xl border border-neutral-300 bg-white px-4 py-2 text-sm font-semibold text-neutral-700 hover:border-neutral-400"
          >
            {i18n.t("workspace.calendar.actions.leave")}
          </button>
        {/if}
      </div>
    </section>

    <!-- Attendees + Recurrence + Project grid -->
    <div class="grid gap-4 lg:grid-cols-3">
      <!-- Attendees: span 2 cols -->
      {#if detail.kind === "meeting"}
        <section class="space-y-3 rounded-2xl border border-neutral-200 bg-white p-5 lg:col-span-2">
          <div class="flex items-center justify-between">
            <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-700">
              {i18n.t("workspace.calendar.attendees", { count: attendees.length })}
            </h2>
          </div>
          {#if attendees.length === 0}
            <p class="text-sm text-neutral-500">{i18n.t("workspace.calendar.no_attendees")}</p>
          {:else}
            <ul class="space-y-2">
              {#each attendees as a (a.id)}
                <li class="flex items-center justify-between rounded-2xl border border-neutral-200 bg-white px-4 py-3">
                  <div class="flex items-center gap-3">
                    <span class="inline-flex h-9 w-9 items-center justify-center rounded-full bg-neutral-200 text-xs font-semibold text-neutral-700">
                      {a.user.initials}
                    </span>
                    <div class="min-w-0">
                      <div class="truncate text-sm font-semibold text-neutral-900">{a.user.name}</div>
                      <div class="truncate text-xs text-neutral-500">{a.user.email}</div>
                    </div>
                  </div>
                  {#if isCreator}
                    <button
                      type="button"
                      onclick={() => removeAttendee(a.user.id)}
                      disabled={removingAttendeeId === a.user.id}
                      class="rounded-lg border border-neutral-300 bg-white px-3 py-1 text-xs font-semibold text-neutral-700 hover:border-neutral-400 disabled:opacity-50"
                    >
                      {i18n.t("workspace.calendar.actions.remove")}
                    </button>
                  {/if}
                </li>
              {/each}
            </ul>
          {/if}
        </section>
      {/if}

      <!-- Right column: recurrence + metadata -->
      <div class="space-y-4">
        {#if detail.recurrence_rule}
          <section class="rounded-2xl border border-neutral-200 bg-white p-5">
            <h3 class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">
              {i18n.t("workspace.calendar.recurrence")}
            </h3>
            <p class="mt-2 text-sm text-neutral-700">
              {i18n.t("workspace.calendar.overrides_count", { count: detail.overrides_count })}
            </p>
          </section>
        {/if}

        {#if detail.team}
          <section class="rounded-2xl border border-neutral-200 bg-white p-5">
            <h3 class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">
              {i18n.t("workspace.calendar.team")}
            </h3>
            <a class="mt-2 inline-flex items-center gap-1 text-sm font-semibold text-neutral-900 hover:text-neutral-700" href={`/teams/${detail.team}`}>
              {i18n.t("workspace.calendar.open_team")} →
            </a>
          </section>
        {/if}
      </div>
    </div>
  </div>
{/if}

<ConfirmModal
  open={cancelOpen}
  title={i18n.t("workspace.calendar.cancel_confirm.title")}
  message={i18n.t("workspace.calendar.cancel_confirm.message")}
  confirmLabel={i18n.t("workspace.calendar.actions.cancel")}
  onclose={() => (cancelOpen = false)}
  onconfirm={cancelEvent}
/>

<ConfirmModal
  open={deleteOpen}
  destructive
  title={i18n.t("workspace.calendar.delete_confirm.title")}
  message={i18n.t("workspace.calendar.delete_confirm.message")}
  confirmLabel={i18n.t("workspace.calendar.actions.delete")}
  onclose={() => (deleteOpen = false)}
  onconfirm={deleteEvent}
/>

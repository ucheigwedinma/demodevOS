<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { i18n } from "$lib/stores/i18n.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    CalendarOccurrenceRow,
    CalendarMeetingsOverlayRow,
    CalendarEventKind,
    UserCalendarSchedulingPreferences,
  } from "$lib/types";
  import DataStateBanner from "$lib/components/DataStateBanner.svelte";
  import MonthView from "$lib/components/calendar/MonthView.svelte";
  import WeekView from "$lib/components/calendar/WeekView.svelte";
  import AgendaView from "$lib/components/calendar/AgendaView.svelte";
  import { KIND_ORDER } from "$lib/components/calendar/event-kinds";

  type Row = CalendarOccurrenceRow | CalendarMeetingsOverlayRow;
  type View = "month" | "week" | "agenda";

  // ----- state ----------------------------------------------------------------

  let view = $state<View>("week");
  let anchor = $state<Date>(new Date());
  let teamFilter = $state<string>("");
  let kindFilter = $state<Set<CalendarEventKind>>(new Set(KIND_ORDER));
  let showMeetings = $state<boolean>(true);

  let events = $state<CalendarOccurrenceRow[]>([]);
  let meetings = $state<CalendarMeetingsOverlayRow[]>([]);
  let loading = $state(false);
  let error = $state<string | null>(null);
  let overlayError = $state<string | null>(null);
  let prefs = $state<UserCalendarSchedulingPreferences | null>(null);

  // Default view by breakpoint (best-effort on mount).
  onMount(() => {
    if (typeof window !== "undefined" && window.innerWidth < 640) view = "agenda";
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

  function windowForView(): { start: Date; end: Date } {
    const a = new Date(anchor);
    if (view === "month") {
      const start = new Date(a.getFullYear(), a.getMonth(), 1);
      start.setDate(start.getDate() - ((start.getDay() + 6) % 7) - 7);
      const end = new Date(a.getFullYear(), a.getMonth() + 1, 0);
      end.setDate(end.getDate() + 14);
      return { start, end };
    }
    if (view === "week") {
      const start = new Date(a);
      start.setDate(a.getDate() - ((a.getDay() + 6) % 7));
      start.setHours(0, 0, 0, 0);
      const end = new Date(start);
      end.setDate(start.getDate() + 7);
      return { start, end };
    }
    // agenda: 30 days forward
    const start = new Date(a);
    start.setHours(0, 0, 0, 0);
    const end = new Date(start);
    end.setDate(start.getDate() + 30);
    return { start, end };
  }

  function iso(d: Date): string {
    return d.toISOString();
  }

  let fetchSeq = 0;
  async function load() {
    const seq = ++fetchSeq;
    loading = true;
    error = null;
    overlayError = null;
    const { start, end } = windowForView();
    const params: Record<string, string> = { start: iso(start), end: iso(end) };
    if (teamFilter) params.team = teamFilter;

    try {
      const [evRes, meetingRes] = await Promise.allSettled([
        api.get<{ results: CalendarOccurrenceRow[] }>("/calendar/events/", params),
        showMeetings
          ? api.get<{ results: CalendarMeetingsOverlayRow[] }>(
              "/calendar/meetings-overlay/",
              params,
            )
          : Promise.resolve({ results: [] }),
      ]);
      if (seq !== fetchSeq) return;
      if (evRes.status === "fulfilled") events = evRes.value.results;
      else {
        error = i18n.t("workspace.calendar.error.load");
        events = [];
      }
      if (meetingRes.status === "fulfilled") meetings = (meetingRes.value as any).results ?? [];
      else {
        meetings = [];
        overlayError = i18n.t("workspace.calendar.error.overlay");
      }
    } catch (err) {
      console.error(err);
      if (seq === fetchSeq) error = i18n.t("workspace.calendar.error.load");
    } finally {
      if (seq === fetchSeq) loading = false;
    }
  }

  // Reload whenever any input changes.
  $effect(() => {
    void view;
    void anchor;
    void teamFilter;
    void showMeetings;
    void load();
  });

  // ----- filters applied to events ------------------------------------------

  let filteredEvents = $derived(events.filter((e) => kindFilter.has(e.kind)));
  let merged = $derived<Row[]>(
    showMeetings ? [...filteredEvents, ...meetings] : filteredEvents,
  );

  function toggleKind(k: CalendarEventKind) {
    const next = new Set(kindFilter);
    if (next.has(k)) next.delete(k);
    else next.add(k);
    kindFilter = next;
  }

  // ----- navigation helpers -------------------------------------------------

  function navPrev() {
    const d = new Date(anchor);
    if (view === "month") d.setMonth(d.getMonth() - 1);
    else if (view === "week") d.setDate(d.getDate() - 7);
    else d.setDate(d.getDate() - 7);
    anchor = d;
  }
  function navNext() {
    const d = new Date(anchor);
    if (view === "month") d.setMonth(d.getMonth() + 1);
    else if (view === "week") d.setDate(d.getDate() + 7);
    else d.setDate(d.getDate() + 7);
    anchor = d;
  }
  function navToday() {
    anchor = new Date();
  }

  function navLabel(): string {
    if (view === "month") {
      return new Intl.DateTimeFormat(i18n.locale, { month: "long", year: "numeric" }).format(
        anchor,
      );
    }
    if (view === "week") {
      const start = new Date(anchor);
      start.setDate(anchor.getDate() - ((anchor.getDay() + 6) % 7));
      const end = new Date(start);
      end.setDate(start.getDate() + 6);
      const fmt = new Intl.DateTimeFormat(i18n.locale, { month: "short", day: "numeric" });
      return `${fmt.format(start)} – ${fmt.format(end)}, ${anchor.getFullYear()}`;
    }
    return new Intl.DateTimeFormat(i18n.locale, {
      weekday: "long",
      month: "long",
      day: "numeric",
      year: "numeric",
    }).format(anchor);
  }

  function selectEvent(ev: Row) {
    if ("source" in ev && ev.source === "meeting") {
      // Read-only overlay row — click navigates to /meetings/{id}
      goto(`/meetings/${ev.id}`);
      return;
    }
    const occ = ev as CalendarOccurrenceRow;
    goto(`/calendar/events/${occ.event_id}`);
  }

  function createAt(d: Date) {
    const iso = d.toISOString();
    goto(`/calendar/events/new?at=${encodeURIComponent(iso)}`);
  }

  // For the new-event button:
  function newEvent() {
    goto("/calendar/events/new");
  }

  // Empty-state detection
  let isEmpty = $derived(!loading && merged.length === 0 && !error);
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
    <div>
      <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-blue-600">
        {i18n.t("workspace.calendar.eyebrow")}
      </p>
      <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">
        {i18n.t("workspace.calendar.title")}
      </h1>
      <p class="mt-1 max-w-xl text-sm text-neutral-500">
        {i18n.t("workspace.calendar.helper")}
      </p>
    </div>
    <button
      type="button"
      onclick={newEvent}
      class="inline-flex items-center gap-2 rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800"
    >
      <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
      </svg>
      {i18n.t("workspace.calendar.new_event")}
    </button>
  </div>

  <!-- Toolbar -->
  <div class="flex flex-wrap items-center gap-3 rounded-2xl border border-neutral-200 bg-white p-4 sm:p-5">
    <div class="flex items-center gap-1">
      <button
        type="button"
        onclick={navPrev}
        class="rounded-lg border border-neutral-300 bg-white p-2 hover:border-neutral-400"
        aria-label="Previous"
      >
        <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
        </svg>
      </button>
      <button
        type="button"
        onclick={navToday}
        class="rounded-full border border-neutral-300 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:border-neutral-400"
      >
        {i18n.t("workspace.calendar.today")}
      </button>
      <button
        type="button"
        onclick={navNext}
        class="rounded-lg border border-neutral-300 bg-white p-2 hover:border-neutral-400"
        aria-label="Next"
      >
        <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
        </svg>
      </button>
    </div>
    <span class="text-sm font-semibold text-neutral-700">{navLabel()}</span>

    <div class="ml-auto flex flex-wrap items-center gap-2">
      <!-- view switcher -->
      <div class="inline-flex rounded-full border border-neutral-300 bg-white p-0.5 text-xs">
        {#each ["month", "week", "agenda"] as v}
          <button
            type="button"
            onclick={() => (view = v as View)}
            class="rounded-full px-3 py-1 font-semibold {view === v ? 'bg-neutral-900 text-white' : 'text-neutral-600 hover:bg-neutral-50'}"
          >
            {i18n.t(`workspace.calendar.views.${v}`)}
          </button>
        {/each}
      </div>

      <!-- kind toggles -->
      <div class="hidden flex-wrap items-center gap-1 sm:flex">
        {#each KIND_ORDER as k}
          <button
            type="button"
            onclick={() => toggleKind(k)}
            class="rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider {kindFilter.has(k) ? 'border-neutral-900 bg-neutral-900 text-white' : 'border-neutral-300 bg-white text-neutral-500'}"
          >
            {i18n.t(`workspace.calendar.kind.${k}`)}
          </button>
        {/each}
      </div>

      <label class="inline-flex cursor-pointer items-center gap-1.5 text-xs">
        <input type="checkbox" bind:checked={showMeetings} class="h-4 w-4 accent-neutral-900" />
        <span class="text-neutral-700">{i18n.t("workspace.calendar.show_meetings_overlay")}</span>
      </label>
    </div>
  </div>

  {#if overlayError}
    <div class="rounded-xl border border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-700">
      {overlayError}
    </div>
  {/if}

  <!-- Canvas -->
  {#if loading && merged.length === 0}
    <div class="flex items-center justify-center py-28">
      <div class="h-7 w-7 animate-spin rounded-full border-[2.5px] border-neutral-200 border-t-neutral-900"></div>
    </div>
  {:else if error}
    <DataStateBanner
      title={i18n.t("workspace.calendar.error.load")}
      message={i18n.t("workspace.calendar.error.load_helper")}
      onRetry={load}
    />
  {:else if isEmpty}
    <div class="rounded-2xl border border-dashed border-neutral-300 bg-white px-6 py-12 text-center">
      <p class="text-3xl">📅</p>
      <p class="mt-3 text-base font-semibold text-neutral-800">
        {i18n.t("workspace.calendar.empty.no_events")}
      </p>
      <p class="mt-1 text-sm text-neutral-500">{i18n.t("workspace.calendar.empty.no_events_helper")}</p>
      <button
        type="button"
        onclick={newEvent}
        class="mt-4 inline-flex items-center gap-2 rounded-xl bg-neutral-900 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-800"
      >
        {i18n.t("workspace.calendar.empty.no_events_cta")}
      </button>
    </div>
  {:else if view === "month"}
    <MonthView {anchor} events={merged} onCreateAt={createAt} onSelect={selectEvent} />
  {:else if view === "week"}
    <WeekView
      {anchor}
      events={merged}
      workingStart={prefs?.working_hours_start ?? "07:00"}
      workingEnd={prefs?.working_hours_end ?? "20:00"}
      onCreateAt={createAt}
      onSelect={selectEvent}
    />
  {:else}
    <AgendaView events={merged} onSelect={selectEvent} canLoadMore={false} />
  {/if}
</div>

<!-- FAB on mobile -->
<button
  type="button"
  onclick={newEvent}
  class="fixed bottom-6 right-6 z-30 inline-flex h-14 w-14 items-center justify-center rounded-full bg-neutral-900 text-white shadow-lg hover:bg-neutral-800 sm:hidden"
  aria-label={i18n.t("workspace.calendar.new_event")}
>
  <svg class="h-6 w-6" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
  </svg>
</button>

<script lang="ts">
  import type { CalendarEventKind, CalendarOccurrenceRow, CalendarMeetingsOverlayRow } from "$lib/types";
  import { i18n } from "$lib/stores/i18n.svelte";
  import { KIND_TREATMENT, KIND_PATTERN, KIND_PATTERN_SIZE, KIND_ICON_PATH } from "./event-kinds";
  import { resolveTeamEdge } from "./team-edge-colors";

  /**
   * Chameleon: renders an event in three shapes depending on `view`.
   *
   *   month  → 1-line pill in a day cell
   *   week   → absolute-positioned block in the timeline
   *   agenda → wide row with time on the left
   *
   * Source can be a native CalendarOccurrenceRow OR a CalendarMeetingsOverlayRow
   * (read-only). Overlay rows get a dashed border + the M badge.
   *
   * Team color (if any) is fetched from the `teamColor` prop because the row
   * itself doesn't carry it — parent provides via team-color lookup.
   */

  type Row = CalendarOccurrenceRow | CalendarMeetingsOverlayRow;

  interface Props {
    event: Row;
    view: "month" | "week" | "agenda";
    /** Optional team-color token (looked up from a separate teams cache). */
    teamColor?: string | null;
    /** Click handler — opens detail or popover. */
    onclick?: (event: Row) => void;
    /** Used by Week view for absolute positioning. */
    style?: string;
  }

  let { event, view, teamColor = null, onclick, style = "" }: Props = $props();

  let isOverlay = $derived("source" in event && event.source === "meeting");
  let kind = $derived<CalendarEventKind>(
    (("kind" in event ? event.kind : "meeting") as CalendarEventKind),
  );
  let treatment = $derived(KIND_TREATMENT[kind]);

  let teamEdge = $derived(resolveTeamEdge(teamColor));
  let borderStyle = $derived(isOverlay ? "border-dashed" : "border-solid");

  let cancelled = $derived("is_cancelled" in event ? event.is_cancelled : false);

  // Build inline pattern style if kind needs it.
  let patternStyle = $derived(
    KIND_PATTERN[kind]
      ? `background-image:${KIND_PATTERN[kind]};background-size:${KIND_PATTERN_SIZE[kind] ?? "auto"};`
      : "",
  );

  let combinedStyle = $derived(`${style}${patternStyle ? ";" + patternStyle : ""}`);

  // Time formatting — uses Intl for locale-aware rendering.
  function fmtTime(iso: string): string {
    const d = new Date(iso);
    return new Intl.DateTimeFormat(i18n.locale, {
      hour: "numeric",
      minute: "2-digit",
    }).format(d);
  }

  function fmtRange(start: string, end: string | null): string {
    if (!end) return fmtTime(start);
    return `${fmtTime(start)}–${fmtTime(end)}`;
  }

  function ariaLabel(): string {
    const title = ("title" in event ? event.title : "") || "";
    const range =
      "starts_at" in event
        ? fmtRange(event.starts_at, "ends_at" in event ? event.ends_at : null)
        : "";
    return [i18n.t(`workspace.calendar.kind.${kind}`), title, range, cancelled ? i18n.t("workspace.calendar.cancelled") : ""]
      .filter(Boolean)
      .join(", ");
  }

  function handleClick() {
    onclick?.(event);
  }

  function handleKey(e: KeyboardEvent) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      handleClick();
    }
  }
</script>

{#if view === "month"}
  <button
    type="button"
    class="group relative flex w-full items-center gap-1 overflow-hidden rounded border-l-4 border border-l-4 px-1.5 py-0.5 text-left text-[11px] font-medium leading-tight {treatment.block} {teamEdge} {borderStyle} {cancelled ? 'line-clamp-1 opacity-60 line-through' : 'line-clamp-1'} hover:brightness-110"
    style={combinedStyle}
    onclick={handleClick}
    onkeydown={handleKey}
    aria-label={ariaLabel()}
  >
    {#if !("source" in event) && kind === "reminder"}
      <!-- Render reminder as a small dot inline -->
      <span class="inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-neutral-500" aria-hidden="true"></span>
    {/if}
    <span class="truncate">{"starts_at" in event ? fmtTime(event.starts_at) : ""} {"title" in event ? event.title : ""}</span>
    {#if isOverlay}
      <span
        class="ml-auto inline-flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded bg-neutral-200 text-[8px] font-bold text-neutral-700"
        aria-label={i18n.t("workspace.calendar.overlay.from_meetings")}
      >M</span>
    {/if}
  </button>
{:else if view === "week"}
  <button
    type="button"
    class="absolute left-0 right-0 m-0.5 flex flex-col gap-0.5 overflow-hidden rounded-md border-l-4 border px-2 py-1 text-left text-[11px] {treatment.block} {teamEdge} {borderStyle} {cancelled ? 'opacity-60 line-through' : ''} hover:brightness-110"
    style={combinedStyle}
    onclick={handleClick}
    onkeydown={handleKey}
    aria-label={ariaLabel()}
  >
    <div class="flex items-center gap-1 font-semibold">
      <span class="truncate">{"starts_at" in event ? fmtRange(event.starts_at, "ends_at" in event ? event.ends_at : null) : ""}</span>
    </div>
    <div class="truncate font-medium">{"title" in event ? event.title : ""}</div>
    {#if isOverlay}
      <span
        class="absolute right-1 top-1 inline-flex h-4 w-4 items-center justify-center rounded bg-neutral-200 text-[9px] font-bold text-neutral-700"
        aria-label={i18n.t("workspace.calendar.overlay.from_meetings")}
      >M</span>
    {/if}
  </button>
{:else}
  <!-- Agenda row -->
  <button
    type="button"
    class="relative flex w-full items-center gap-3 rounded-2xl border-l-4 border border-neutral-200 bg-white px-4 py-3 text-left transition hover:border-neutral-400 {teamEdge} {borderStyle} {cancelled ? 'opacity-60' : ''}"
    onclick={handleClick}
    onkeydown={handleKey}
    aria-label={ariaLabel()}
  >
    <div class="w-28 shrink-0 text-xs font-semibold tabular-nums text-neutral-500">
      {"starts_at" in event ? fmtRange(event.starts_at, "ends_at" in event ? event.ends_at : null) : ""}
    </div>
    <div
      class="flex h-7 w-7 shrink-0 items-center justify-center rounded {treatment.block}"
      style={patternStyle}
      aria-hidden="true"
    >
      <svg
        class="h-3.5 w-3.5 {treatment.iconColor}"
        fill="none"
        stroke="currentColor"
        stroke-width="1.5"
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" d={KIND_ICON_PATH[kind]} />
      </svg>
    </div>
    <div class="min-w-0 flex-1">
      <div class="truncate text-sm font-semibold text-neutral-900 {cancelled ? 'line-through' : ''}">
        {"title" in event ? event.title : ""}
      </div>
      {#if "location" in event && event.location}
        <div class="truncate text-xs text-neutral-500">{event.location}</div>
      {/if}
    </div>
    {#if isOverlay}
      <span
        class="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded bg-neutral-200 text-[10px] font-bold text-neutral-700"
        aria-label={i18n.t("workspace.calendar.overlay.from_meetings")}
      >M</span>
    {/if}
  </button>
{/if}

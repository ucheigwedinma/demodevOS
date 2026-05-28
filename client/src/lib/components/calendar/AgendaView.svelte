<script lang="ts">
  import { i18n } from "$lib/stores/i18n.svelte";
  import type { CalendarOccurrenceRow, CalendarMeetingsOverlayRow } from "$lib/types";
  import EventCell from "./EventCell.svelte";

  /**
   * Agenda view — linear list grouped by date.
   *
   * Days with zero events are skipped (no empty-day rows). Best on mobile;
   * also acts as the "what's next?" surface on desktop.
   */

  type Row = CalendarOccurrenceRow | CalendarMeetingsOverlayRow;

  interface Props {
    events: Row[];
    teamColors?: Record<number, string>;
    onSelect?: (event: Row) => void;
    onLoadMore?: () => void;
    /** When false, hides the Load more button. */
    canLoadMore?: boolean;
    loadingMore?: boolean;
  }

  let { events, teamColors = {}, onSelect, onLoadMore, canLoadMore = false, loadingMore = false }: Props = $props();

  function dayKey(iso: string): string {
    const d = new Date(iso);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }

  function dayHeaderLabel(key: string): string {
    const d = new Date(`${key}T00:00:00`);
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(today.getDate() + 1);
    const fmtDate = new Intl.DateTimeFormat(i18n.locale, {
      weekday: "long",
      month: "long",
      day: "numeric",
    });
    let prefix = "";
    if (sameDay(d, today)) prefix = i18n.t("workspace.calendar.today");
    else if (sameDay(d, tomorrow)) prefix = i18n.t("workspace.calendar.tomorrow");
    return prefix ? `${prefix.toUpperCase()} · ${fmtDate.format(d)}` : fmtDate.format(d);
  }

  function sameDay(a: Date, b: Date): boolean {
    return (
      a.getFullYear() === b.getFullYear() &&
      a.getMonth() === b.getMonth() &&
      a.getDate() === b.getDate()
    );
  }

  let grouped = $derived.by(() => {
    const map: Record<string, Row[]> = {};
    for (const ev of events) {
      const key = dayKey(ev.starts_at);
      (map[key] ||= []).push(ev);
    }
    return Object.entries(map).sort(([a], [b]) => (a < b ? -1 : 1));
  });
</script>

<div class="space-y-6">
  {#each grouped as [key, dayEvents]}
    <section class="space-y-2">
      <h3 class="text-xs font-semibold uppercase tracking-[0.16em] text-neutral-400">
        {dayHeaderLabel(key)}
      </h3>
      <div class="space-y-2">
        {#each dayEvents as ev}
          {@const tid = "team_id" in ev ? ev.team_id : null}
          <EventCell
            event={ev}
            view="agenda"
            teamColor={tid != null ? teamColors[tid] ?? null : null}
            onclick={() => onSelect?.(ev)}
          />
        {/each}
      </div>
    </section>
  {/each}

  {#if canLoadMore}
    <div class="flex justify-center pt-2">
      <button
        type="button"
        onclick={onLoadMore}
        disabled={loadingMore}
        class="rounded-xl border border-neutral-300 bg-white px-4 py-2 text-sm font-semibold text-neutral-700 hover:border-neutral-400 disabled:opacity-50"
      >
        {loadingMore ? i18n.t("common.actions.loading") : i18n.t("common.actions.load_more")}
      </button>
    </div>
  {/if}
</div>

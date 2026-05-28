<script lang="ts">
  import { i18n } from "$lib/stores/i18n.svelte";
  import type { CalendarOccurrenceRow, CalendarMeetingsOverlayRow } from "$lib/types";
  import EventCell from "./EventCell.svelte";

  /**
   * Month view — 7-col x 5-6-row grid. Overflow ("+N more") + all-day band.
   *
   * Anchor date determines the visible month. Today gets a highlight.
   * Click empty cell → onCreateAt(d). Click event → onSelect(event).
   */

  type Row = CalendarOccurrenceRow | CalendarMeetingsOverlayRow;

  interface Props {
    anchor: Date;
    events: Row[];
    /** Map team_id -> color token for left-edge accents. */
    teamColors?: Record<number, string>;
    onCreateAt?: (date: Date) => void;
    onSelect?: (event: Row) => void;
  }

  let { anchor, events, teamColors = {}, onCreateAt, onSelect }: Props = $props();

  // Build a 6-week grid anchored on the visible month, starting on the locale's
  // first day of the week (Mon for en/fr/es, Sat for ar in some locales —
  // Intl.Locale doesn't always expose weekInfo, so we default to Mon).
  function firstDayOfWeek(): number {
    try {
      // @ts-expect-error — weekInfo is widely supported in modern engines
      const wi = new Intl.Locale(i18n.locale).weekInfo;
      if (wi && typeof wi.firstDay === "number") return wi.firstDay - 1; // ICU 1=Mon to 0-indexed
    } catch {
      // fall through
    }
    return 1; // Monday
  }

  let weekStart = $derived(firstDayOfWeek());

  let grid = $derived.by(() => {
    const year = anchor.getFullYear();
    const month = anchor.getMonth();
    const first = new Date(year, month, 1);
    const lead = (first.getDay() - weekStart + 7) % 7;
    const start = new Date(year, month, 1 - lead);
    const cells: Date[] = [];
    for (let i = 0; i < 42; i++) {
      const d = new Date(start);
      d.setDate(start.getDate() + i);
      cells.push(d);
    }
    return cells;
  });

  function weekdays(): string[] {
    const fmt = new Intl.DateTimeFormat(i18n.locale, { weekday: "short" });
    const out: string[] = [];
    for (let i = 0; i < 7; i++) {
      // Pick a Monday of any year then offset
      const d = new Date(2024, 0, 1 + ((i + weekStart) % 7));
      out.push(fmt.format(d));
    }
    return out;
  }

  // Group events by yyyy-mm-dd of starts_at (in viewer local time).
  function dayKey(d: Date): string {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }

  let byDay = $derived.by(() => {
    const map: Record<string, Row[]> = {};
    for (const ev of events) {
      const d = new Date(ev.starts_at);
      const key = dayKey(d);
      (map[key] ||= []).push(ev);
    }
    return map;
  });

  function isToday(d: Date): boolean {
    const t = new Date();
    return (
      d.getFullYear() === t.getFullYear() &&
      d.getMonth() === t.getMonth() &&
      d.getDate() === t.getDate()
    );
  }

  function isInMonth(d: Date): boolean {
    return d.getMonth() === anchor.getMonth();
  }

  function handleCellClick(d: Date, e: MouseEvent) {
    // Only fire onCreateAt when the click is on the cell background (not on
    // an event button — buttons handle their own onclick).
    if ((e.target as HTMLElement).closest("button")) return;
    onCreateAt?.(d);
  }
</script>

<div class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
  <div class="grid grid-cols-7 border-b border-neutral-200 bg-neutral-50">
    {#each weekdays() as w}
      <div class="px-2 py-2 text-center text-[10px] font-semibold uppercase tracking-wider text-neutral-500">
        {w}
      </div>
    {/each}
  </div>
  <div class="grid grid-cols-7">
    {#each grid as d}
      {@const key = dayKey(d)}
      {@const dayEvents = byDay[key] ?? []}
      {@const visible = dayEvents.slice(0, 3)}
      {@const overflow = Math.max(0, dayEvents.length - 3)}
      <div
        class="min-h-24 border-b border-r border-neutral-100 p-1 last:border-r-0 sm:min-h-32 {isInMonth(d) ? 'bg-white' : 'bg-neutral-50/50'}"
        onclick={(e) => handleCellClick(d, e)}
        onkeydown={(e) => {
          if (e.key === "Enter") onCreateAt?.(d);
        }}
        role="gridcell"
        tabindex="0"
      >
        <div class="mb-1 flex items-center justify-between px-1">
          {#if isToday(d)}
            <span class="inline-flex h-6 w-6 items-center justify-center rounded-full bg-neutral-900 text-xs font-semibold text-white">
              {d.getDate()}
            </span>
          {:else}
            <span class="text-xs font-semibold {isInMonth(d) ? 'text-neutral-600' : 'text-neutral-300'}">
              {d.getDate()}
            </span>
          {/if}
        </div>
        <div class="space-y-0.5">
          {#each visible as ev}
            {@const tid = "team_id" in ev ? ev.team_id : null}
            <EventCell
              event={ev}
              view="month"
              teamColor={tid != null ? teamColors[tid] ?? null : null}
              onclick={() => onSelect?.(ev)}
            />
          {/each}
          {#if overflow > 0}
            <div class="px-1 text-[10px] font-semibold text-neutral-500">
              {i18n.t("workspace.calendar.more_events", { count: overflow })}
            </div>
          {/if}
        </div>
      </div>
    {/each}
  </div>
</div>

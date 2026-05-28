<script lang="ts">
  import { i18n } from "$lib/stores/i18n.svelte";
  import type { CalendarOccurrenceRow, CalendarMeetingsOverlayRow } from "$lib/types";
  import EventCell from "./EventCell.svelte";

  /**
   * Week view — 7-day vertical timeline.
   *
   * Per UI spec §3.5:
   *  - hour rows from working_hours_start to working_hours_end
   *  - overlap rendering via greedy column-split (cluster → columns)
   *  - all-day band above the timeline
   *  - current-time line on today's column
   */

  type Row = CalendarOccurrenceRow | CalendarMeetingsOverlayRow;

  interface Props {
    anchor: Date;
    events: Row[];
    teamColors?: Record<number, string>;
    /** Working hours [start, end] from user prefs (24h "HH:MM"). */
    workingStart?: string;
    workingEnd?: string;
    onCreateAt?: (date: Date) => void;
    onSelect?: (event: Row) => void;
  }

  let {
    anchor,
    events,
    teamColors = {},
    workingStart = "07:00",
    workingEnd = "20:00",
    onCreateAt,
    onSelect,
  }: Props = $props();

  function firstDayOfWeek(): number {
    try {
      // @ts-expect-error weekInfo
      const wi = new Intl.Locale(i18n.locale).weekInfo;
      if (wi && typeof wi.firstDay === "number") return wi.firstDay - 1;
    } catch {}
    return 1;
  }

  let weekStart = $derived(firstDayOfWeek());

  // Build the 7 day columns starting at the locale's first day of week.
  let weekDays = $derived.by(() => {
    const a = new Date(anchor);
    const day = (a.getDay() - weekStart + 7) % 7;
    a.setDate(a.getDate() - day);
    const out: Date[] = [];
    for (let i = 0; i < 7; i++) {
      const d = new Date(a);
      d.setDate(a.getDate() + i);
      d.setHours(0, 0, 0, 0);
      out.push(d);
    }
    return out;
  });

  function parseHM(hm: string): number {
    const [h, m] = hm.split(":").map((x) => parseInt(x));
    return h + (isNaN(m) ? 0 : m / 60);
  }

  let startH = $derived(parseHM(workingStart));
  let endH = $derived(parseHM(workingEnd));
  let hours = $derived.by(() => {
    const a: number[] = [];
    for (let h = Math.floor(startH); h <= Math.ceil(endH); h++) a.push(h);
    return a;
  });

  // Group events into all-day vs timed, keyed by day index.
  function dayIndex(d: Date): number {
    return weekDays.findIndex(
      (wd) =>
        wd.getFullYear() === d.getFullYear() &&
        wd.getMonth() === d.getMonth() &&
        wd.getDate() === d.getDate(),
    );
  }

  type Placed = { event: Row; col: number; cols: number; topPct: number; heightPct: number };

  let dayBuckets = $derived.by(() => {
    const buckets: { allDay: Row[]; timed: Row[] }[] = Array(7)
      .fill(null)
      .map(() => ({ allDay: [], timed: [] }));
    for (const ev of events) {
      const d = new Date(ev.starts_at);
      const idx = dayIndex(d);
      if (idx === -1) continue;
      const isAllDay = "all_day" in ev && ev.all_day;
      if (isAllDay) buckets[idx].allDay.push(ev);
      else buckets[idx].timed.push(ev);
    }
    return buckets;
  });

  // Column-split overlap layout — per UI spec §3.5.
  function placeOverlap(timed: Row[]): Placed[] {
    if (!timed.length) return [];
    const items = timed
      .map((event, i) => ({
        event,
        i,
        start: new Date(event.starts_at).getTime(),
        end: event.ends_at
          ? new Date(event.ends_at).getTime()
          : new Date(event.starts_at).getTime() + 30 * 60_000,
      }))
      .sort((a, b) => a.start - b.start || b.end - a.end);

    // Greedy column assignment per cluster
    type Box = (typeof items)[number] & { col: number };
    const placed: Box[] = [];
    const clusterMaxCols: number[] = [];
    let clusterStart = 0;
    let clusterEndTime = 0;
    let clusterCols: number[] = []; // last-end time per column

    for (const it of items) {
      if (it.start >= clusterEndTime && placed.length) {
        // Close current cluster — assign max cols to all members.
        for (let k = clusterStart; k < placed.length; k++) clusterMaxCols[k] = clusterCols.length;
        clusterStart = placed.length;
        clusterCols = [];
        clusterEndTime = 0;
      }
      // Find a column whose last event ended before this one starts.
      let col = -1;
      for (let c = 0; c < clusterCols.length; c++) {
        if (clusterCols[c] <= it.start) {
          col = c;
          clusterCols[c] = it.end;
          break;
        }
      }
      if (col === -1) {
        clusterCols.push(it.end);
        col = clusterCols.length - 1;
      }
      placed.push({ ...it, col });
      clusterEndTime = Math.max(clusterEndTime, it.end);
    }
    // Close final cluster.
    for (let k = clusterStart; k < placed.length; k++) clusterMaxCols[k] = clusterCols.length;

    const totalHours = endH - startH;
    const out: Placed[] = placed.map((p, idx) => {
      const d = new Date(p.event.starts_at);
      const localHour = d.getHours() + d.getMinutes() / 60;
      const localEnd = p.event.ends_at
        ? (() => {
            const e = new Date(p.event.ends_at);
            return e.getHours() + e.getMinutes() / 60;
          })()
        : localHour + 0.5;
      const topPct = ((localHour - startH) / totalHours) * 100;
      const heightPct = Math.max(2, ((localEnd - localHour) / totalHours) * 100);
      const cols = clusterMaxCols[idx] ?? 1;
      return { event: p.event, col: p.col, cols, topPct, heightPct };
    });
    return out;
  }

  function isToday(d: Date): boolean {
    const t = new Date();
    return (
      d.getFullYear() === t.getFullYear() &&
      d.getMonth() === t.getMonth() &&
      d.getDate() === t.getDate()
    );
  }

  let now = $state(new Date());
  // Refresh "now" line every minute.
  $effect(() => {
    const id = setInterval(() => (now = new Date()), 60_000);
    return () => clearInterval(id);
  });

  function nowTopPct(): number {
    const h = now.getHours() + now.getMinutes() / 60;
    if (h < startH || h > endH) return -1;
    return ((h - startH) / (endH - startH)) * 100;
  }

  function dayHeaderFmt(d: Date): string {
    return new Intl.DateTimeFormat(i18n.locale, { weekday: "short", day: "numeric" }).format(d);
  }

  function hourLabel(h: number): string {
    return new Intl.DateTimeFormat(i18n.locale, { hour: "numeric" }).format(
      new Date(2024, 0, 1, h, 0),
    );
  }

  function handleSlotClick(dayIdx: number, hour: number) {
    if (!onCreateAt) return;
    const d = new Date(weekDays[dayIdx]);
    d.setHours(hour, 0, 0, 0);
    onCreateAt(d);
  }
</script>

<div class="overflow-hidden rounded-2xl border border-neutral-200 bg-white">
  <div class="grid grid-cols-[56px_repeat(7,minmax(0,1fr))] border-b border-neutral-200 bg-neutral-50">
    <div class="px-2 py-2 text-center text-[10px] font-semibold uppercase tracking-wider text-neutral-400">
      {i18n.t("workspace.calendar.all_day")}
    </div>
    {#each weekDays as d, i}
      <div class="px-2 py-2 text-center text-xs font-semibold uppercase tracking-wider {isToday(d) ? 'text-neutral-900' : 'text-neutral-500'}">
        {dayHeaderFmt(d)}
      </div>
    {/each}
  </div>

  <!-- All-day band -->
  <div class="grid grid-cols-[56px_repeat(7,minmax(0,1fr))] border-b border-neutral-200 bg-neutral-50/40">
    <div class="border-r border-neutral-100"></div>
    {#each dayBuckets as bucket, i}
      <div class="min-h-[28px] space-y-0.5 border-r border-neutral-100 p-1 last:border-r-0">
        {#each bucket.allDay as ev}
          {@const tid = "team_id" in ev ? ev.team_id : null}
          <EventCell
            event={ev}
            view="month"
            teamColor={tid != null ? teamColors[tid] ?? null : null}
            onclick={() => onSelect?.(ev)}
          />
        {/each}
      </div>
    {/each}
  </div>

  <!-- Timeline -->
  <div class="relative grid grid-cols-[56px_repeat(7,minmax(0,1fr))]">
    <!-- Hour axis -->
    <div class="flex flex-col">
      {#each hours as h}
        <div class="h-12 border-b border-neutral-100 px-2 pt-0.5 text-[10px] tabular-nums text-neutral-400">
          {hourLabel(h)}
        </div>
      {/each}
    </div>

    {#each weekDays as d, i}
      {@const isTodayCol = isToday(d)}
      {@const placements = placeOverlap(dayBuckets[i].timed)}
      <div class="relative border-r border-neutral-100 last:border-r-0 {isTodayCol ? 'bg-neutral-50/40' : ''}">
        <!-- Hour grid lines (clickable slots) -->
        {#each hours as h}
          <button
            type="button"
            onclick={() => handleSlotClick(i, h)}
            class="h-12 w-full border-b border-neutral-100 text-left transition hover:bg-neutral-50"
            aria-label={i18n.t("workspace.calendar.create_at", { time: hourLabel(h) })}
          ></button>
        {/each}

        <!-- Current-time line (only on today's column) -->
        {#if isTodayCol}
          {@const top = nowTopPct()}
          {#if top >= 0}
            <div
              class="pointer-events-none absolute left-0 right-0 z-10 border-t border-dashed border-neutral-500"
              style="top: {top}%"
            >
              <span class="absolute -left-1 -top-1 inline-block h-2 w-2 rounded-full bg-neutral-700"></span>
            </div>
          {/if}
        {/if}

        <!-- Placed events -->
        {#each placements as p}
          {@const widthPct = 100 / p.cols}
          {@const leftPct = p.col * widthPct}
          {@const tid = "team_id" in p.event ? p.event.team_id : null}
          <div
            class="absolute"
            style="top: {p.topPct}%; height: {p.heightPct}%; left: {leftPct}%; width: {widthPct}%;"
          >
            <EventCell
              event={p.event}
              view="week"
              teamColor={tid != null ? teamColors[tid] ?? null : null}
              onclick={() => onSelect?.(p.event)}
            />
          </div>
        {/each}
      </div>
    {/each}
  </div>
</div>

<script lang="ts">
  import { i18n } from "$lib/stores/i18n.svelte";

  /**
   * RRULE editor — frequency / interval / end + a derived natural-language
   * summary.
   *
   * Binds to a single `rule` string (RFC 5545 without the "RRULE:" prefix).
   * Empty string = no recurrence.
   *
   * v1 supports:
   *   FREQ in {DAILY, WEEKLY, MONTHLY, YEARLY}
   *   INTERVAL ≥ 1
   *   Weekly: BYDAY day-of-week chips (MO TU WE TH FR SA SU)
   *   End: never | COUNT=N | UNTIL=YYYYMMDDTHHMMSSZ
   *
   * Advanced editing (BYMONTHDAY, BYSETPOS, etc.) is exposed via a read-only
   * "raw RRULE" line below. Power users can edit on the server-PATCH path.
   */

  type Freq = "DAILY" | "WEEKLY" | "MONTHLY" | "YEARLY";
  type EndMode = "never" | "count" | "until";
  const DAYS = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"] as const;
  type Day = (typeof DAYS)[number];

  interface Props {
    rule: string;
    /** Optional anchor date (used to localise "On the 15th of every month"). */
    anchor?: Date;
  }

  let { rule = $bindable(""), anchor = new Date() }: Props = $props();

  let freq = $state<Freq>("WEEKLY");
  let interval = $state<number>(1);
  let byday = $state<Day[]>([]);
  let endMode = $state<EndMode>("never");
  let count = $state<number>(10);
  let until = $state<string>("");

  // Parse initial rule into structured fields.
  function parse(r: string) {
    if (!r) {
      freq = "WEEKLY";
      interval = 1;
      byday = [];
      endMode = "never";
      count = 10;
      until = "";
      return;
    }
    const parts = Object.fromEntries(
      r.split(";").map((p) => {
        const [k, v] = p.split("=");
        return [k.toUpperCase(), v ?? ""];
      }),
    );
    if (parts.FREQ) freq = parts.FREQ as Freq;
    interval = parts.INTERVAL ? Math.max(1, parseInt(parts.INTERVAL)) : 1;
    byday = parts.BYDAY
      ? (parts.BYDAY.split(",").filter((d) => DAYS.includes(d as Day)) as Day[])
      : [];
    if (parts.COUNT) {
      endMode = "count";
      count = parseInt(parts.COUNT);
    } else if (parts.UNTIL) {
      endMode = "until";
      // 20261215T235959Z → 2026-12-15
      const m = parts.UNTIL.match(/^(\d{4})(\d{2})(\d{2})/);
      until = m ? `${m[1]}-${m[2]}-${m[3]}` : "";
    } else {
      endMode = "never";
    }
  }

  // One-time parse on mount; re-parse if `rule` is reset externally.
  let lastSeenRule = $state("");
  $effect(() => {
    if (rule !== lastSeenRule) {
      lastSeenRule = rule;
      parse(rule);
    }
  });

  // Emit changes back as a normalized RRULE.
  function emit() {
    const out: string[] = [`FREQ=${freq}`];
    if (interval > 1) out.push(`INTERVAL=${interval}`);
    if (freq === "WEEKLY" && byday.length) out.push(`BYDAY=${byday.join(",")}`);
    if (endMode === "count" && count > 0) out.push(`COUNT=${count}`);
    if (endMode === "until" && until) {
      const ymd = until.replace(/-/g, "");
      out.push(`UNTIL=${ymd}T235959Z`);
    }
    const next = out.join(";");
    if (next !== rule) {
      lastSeenRule = next;
      rule = next;
    }
  }

  $effect(() => {
    // Read all reactive deps so the effect re-runs on any change.
    void freq;
    void interval;
    void byday;
    void endMode;
    void count;
    void until;
    emit();
  });

  function toggleDay(d: Day) {
    byday = byday.includes(d) ? byday.filter((x) => x !== d) : [...byday, d];
  }

  // ---------------------------------------------------------------------------
  // Natural-language summary (very lightweight — locale-aware via i18n.t).
  // ---------------------------------------------------------------------------

  function dayName(d: Day): string {
    return i18n.t(`workspace.calendar.rrule.day.${d.toLowerCase()}`);
  }

  let summary = $derived.by(() => {
    const t = (k: string, params?: Record<string, string | number>) => i18n.t(k, params);
    const intervalLabel = interval > 1 ? `${interval} ` : "";
    let head = "";
    if (freq === "DAILY") head = t("workspace.calendar.rrule.summary.daily", { interval });
    else if (freq === "WEEKLY") {
      const days = byday.length
        ? byday.map(dayName).join(", ")
        : t("workspace.calendar.rrule.summary.no_days");
      head = t("workspace.calendar.rrule.summary.weekly", { interval, days });
    } else if (freq === "MONTHLY")
      head = t("workspace.calendar.rrule.summary.monthly", { interval });
    else head = t("workspace.calendar.rrule.summary.yearly", { interval });

    let tail = "";
    if (endMode === "never") tail = t("workspace.calendar.rrule.summary.forever");
    else if (endMode === "count")
      tail = t("workspace.calendar.rrule.summary.for_count", { count });
    else if (endMode === "until" && until)
      tail = t("workspace.calendar.rrule.summary.until", {
        date: new Intl.DateTimeFormat(i18n.locale, { dateStyle: "long" }).format(
          new Date(until),
        ),
      });
    return [head, tail].filter(Boolean).join(", ");
  });
</script>

<div class="space-y-4 rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
  <div class="flex flex-wrap items-center gap-3">
    <span class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">
      {i18n.t("workspace.calendar.rrule.repeats")}
    </span>
    {#each ["DAILY", "WEEKLY", "MONTHLY", "YEARLY"] as f}
      <button
        type="button"
        onclick={() => (freq = f as Freq)}
        class="rounded-full border px-3 py-1 text-xs font-semibold {freq === f ? 'border-neutral-900 bg-neutral-900 text-white' : 'border-neutral-300 bg-white text-neutral-700 hover:border-neutral-400'}"
      >
        {i18n.t(`workspace.calendar.rrule.frequency.${f.toLowerCase()}`)}
      </button>
    {/each}
  </div>

  <div class="flex flex-wrap items-center gap-2">
    <span class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">
      {i18n.t("workspace.calendar.rrule.every")}
    </span>
    <input
      type="number"
      min="1"
      bind:value={interval}
      class="w-16 rounded-2xl border border-neutral-200 bg-white px-3 py-1.5 text-sm focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
    />
    <span class="text-xs text-neutral-500">
      {i18n.t(`workspace.calendar.rrule.unit.${freq.toLowerCase()}`, { n: interval })}
    </span>
  </div>

  {#if freq === "WEEKLY"}
    <div class="flex flex-wrap items-center gap-2">
      <span class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">
        {i18n.t("workspace.calendar.rrule.on")}
      </span>
      {#each DAYS as d}
        <button
          type="button"
          onclick={() => toggleDay(d)}
          class="inline-flex h-9 w-9 items-center justify-center rounded-full border text-xs font-semibold {byday.includes(d) ? 'border-neutral-900 bg-neutral-900 text-white' : 'border-neutral-300 bg-white text-neutral-600 hover:border-neutral-400'}"
          aria-pressed={byday.includes(d)}
        >
          {i18n.t(`workspace.calendar.rrule.day_short.${d.toLowerCase()}`)}
        </button>
      {/each}
    </div>
  {/if}

  <div class="flex flex-col gap-2">
    <span class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">
      {i18n.t("workspace.calendar.rrule.ends_label")}
    </span>
    <label class="flex cursor-pointer items-center gap-2">
      <input type="radio" name="end" value="never" bind:group={endMode} class="h-4 w-4 accent-neutral-900" />
      <span class="text-sm">{i18n.t("workspace.calendar.rrule.ends.never")}</span>
    </label>
    <label class="flex cursor-pointer items-center gap-2">
      <input type="radio" name="end" value="count" bind:group={endMode} class="h-4 w-4 accent-neutral-900" />
      <span class="text-sm">{i18n.t("workspace.calendar.rrule.ends.after_prefix")}</span>
      <input
        type="number"
        min="1"
        max="999"
        bind:value={count}
        disabled={endMode !== "count"}
        class="w-20 rounded-xl border border-neutral-200 bg-white px-2 py-1 text-sm disabled:opacity-50"
      />
      <span class="text-sm">{i18n.t("workspace.calendar.rrule.ends.after_suffix")}</span>
    </label>
    <label class="flex cursor-pointer items-center gap-2">
      <input type="radio" name="end" value="until" bind:group={endMode} class="h-4 w-4 accent-neutral-900" />
      <span class="text-sm">{i18n.t("workspace.calendar.rrule.ends.on_prefix")}</span>
      <input
        type="date"
        bind:value={until}
        disabled={endMode !== "until"}
        class="rounded-xl border border-neutral-200 bg-white px-2 py-1 text-sm disabled:opacity-50"
      />
    </label>
  </div>

  <div class="border-t border-neutral-200 pt-3">
    <p class="text-sm text-neutral-700">
      <span class="font-semibold uppercase tracking-wider text-neutral-400 text-[11px]">{i18n.t("workspace.calendar.rrule.summary_label")}:</span>
      {summary}
    </p>
    <p class="mt-2 truncate font-mono text-[11px] text-neutral-400" title={rule}>
      RRULE:{rule}
    </p>
  </div>
</div>

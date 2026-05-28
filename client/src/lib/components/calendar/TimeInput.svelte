<script lang="ts">
  import { i18n } from "$lib/stores/i18n.svelte";

  /**
   * Date + time input pair, timezone-aware.
   *
   * Per UI spec §3.8:
   *  - Native <input type="date"> and <input type="time"> for v1
   *  - Shows the IANA timezone label to the right
   *  - "Originally in {tz}" hint when viewer TZ ≠ event TZ
   *
   * Binds an ISO 8601 string via `value`. We split into date+time pieces for
   * the inputs and reconstruct on change.
   */

  interface Props {
    value: string;
    timezone: string;
    /** When true, suppress the time input (used for all-day events). */
    dateOnly?: boolean;
    /** Label shown above the date input. */
    label: string;
    /** Show "Originally in" hint when viewer's locale TZ differs. */
    showOriginalTz?: boolean;
    id?: string;
  }

  let {
    value = $bindable(""),
    timezone,
    dateOnly = false,
    label,
    showOriginalTz = false,
    id,
  }: Props = $props();

  // Split ISO into date + time for the native inputs.
  function splitIso(iso: string): { date: string; time: string } {
    if (!iso) return { date: "", time: "" };
    // Strip Z / offset; we present the wall-clock time in the event's TZ.
    const m = iso.match(/^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})/);
    if (!m) return { date: "", time: "" };
    return { date: m[1], time: m[2] };
  }

  let parts = $derived(splitIso(value));

  let dateValue = $state(parts.date);
  let timeValue = $state(parts.time);

  // Re-sync local state when external value changes.
  $effect(() => {
    const { date, time } = splitIso(value);
    if (date !== dateValue) dateValue = date;
    if (time !== timeValue) timeValue = time;
  });

  function commit() {
    if (!dateValue) {
      value = "";
      return;
    }
    if (dateOnly) {
      value = `${dateValue}T00:00:00Z`;
      return;
    }
    value = `${dateValue}T${timeValue || "09:00"}:00Z`;
  }

  let viewerTz = $derived(
    typeof Intl !== "undefined"
      ? Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"
      : "UTC",
  );
  let showHint = $derived(showOriginalTz && viewerTz !== timezone);
</script>

<div class="flex flex-col gap-1">
  {#if label}
    <label for={id} class="text-xs font-semibold uppercase tracking-[0.14em] text-neutral-400">
      {label}
    </label>
  {/if}
  <div class="flex flex-wrap items-center gap-2">
    <input
      {id}
      type="date"
      bind:value={dateValue}
      onchange={commit}
      class="rounded-2xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
    />
    {#if !dateOnly}
      <input
        type="time"
        bind:value={timeValue}
        onchange={commit}
        class="rounded-2xl border border-neutral-200 bg-neutral-50 px-3 py-2 text-sm text-neutral-800 focus:border-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800/10"
      />
    {/if}
    <span class="text-xs text-neutral-500">{timezone}</span>
  </div>
  {#if showHint}
    <p class="text-[11px] text-neutral-400">
      {i18n.t("workspace.calendar.tz_hint", { tz: timezone })}
    </p>
  {/if}
</div>

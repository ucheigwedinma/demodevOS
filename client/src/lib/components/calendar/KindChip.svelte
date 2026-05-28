<script lang="ts">
  import type { CalendarEventKind } from "$lib/types";
  import { i18n } from "$lib/stores/i18n.svelte";
  import { KIND_TREATMENT, KIND_ICON_PATH } from "./event-kinds";

  /**
   * Small chip showing the event's kind with its icon + label.
   * Static class lookups via KIND_TREATMENT — no dynamic classes.
   */

  interface Props {
    kind: CalendarEventKind;
    size?: "sm" | "md";
  }

  let { kind, size = "sm" }: Props = $props();

  let treatment = $derived(KIND_TREATMENT[kind]);
  let labelKey = $derived(`workspace.calendar.kind.${kind}`);
  let label = $derived(i18n.t(labelKey));
  let isMd = $derived(size === "md");
</script>

<span
  class="inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 font-semibold uppercase tracking-wider {treatment.chip} {treatment.chipText} {treatment.chipBorder} {isMd ? 'text-xs' : 'text-[10px]'}"
  aria-label={label}
>
  <svg
    class="{isMd ? 'h-3.5 w-3.5' : 'h-3 w-3'} {treatment.iconColor}"
    fill="none"
    stroke="currentColor"
    stroke-width="1.5"
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    <path stroke-linecap="round" stroke-linejoin="round" d={KIND_ICON_PATH[kind]} />
  </svg>
  {label}
</span>

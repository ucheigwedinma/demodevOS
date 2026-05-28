<script lang="ts">
  import { i18n } from "$lib/stores/i18n.svelte";

  /**
   * Small "M" badge for read-only meetings-overlay rows.
   * Pair with `border-dashed` on the parent EventCell — both cues together
   * make these rows unmistakable (UI spec §2.2). Color-blind-safe by design
   * (uses shape + text, not hue).
   */
</script>

<span
  class="absolute right-1 top-1 inline-flex h-4 w-4 items-center justify-center rounded bg-neutral-200 text-[9px] font-bold text-neutral-700"
  aria-label={i18n.t("workspace.calendar.overlay.from_meetings")}
>
  M
</span>

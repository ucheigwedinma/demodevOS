<script lang="ts">
  import type { CalendarEventVisibility } from "$lib/types";
  import { i18n } from "$lib/stores/i18n.svelte";

  /**
   * Visibility chip. Neutral styling for all three tiers — visibility shouldn't
   * compete with kind for attention (UI spec §3.2).
   */

  interface Props {
    visibility: CalendarEventVisibility;
    size?: "sm" | "md";
  }

  let { visibility, size = "sm" }: Props = $props();

  let labelKey = $derived(`workspace.calendar.visibility.${visibility}`);
  let label = $derived(i18n.t(labelKey));
  let isMd = $derived(size === "md");

  // SVG paths for each visibility icon (heroicons outline 1.5)
  let iconPath = $derived(
    visibility === "private"
      ? "M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z"
      : visibility === "team"
        ? "M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z"
        : "M12 21a9.004 9.004 0 0 0 8.716-6.747M12 21a9.004 9.004 0 0 1-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 0 1 7.843 4.582M12 3a8.997 8.997 0 0 0-7.843 4.582m15.686 0A11.953 11.953 0 0 1 12 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0 1 21 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0 1 12 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 0 1 3 12c0-1.605.42-3.113 1.157-4.418",
  );
</script>

<span
  class="inline-flex items-center gap-1 rounded-full border border-neutral-200 bg-neutral-50 px-2.5 py-0.5 font-semibold uppercase tracking-wider text-neutral-600 {isMd ? 'text-xs' : 'text-[10px]'}"
  aria-label={`${label} visibility`}
>
  <svg
    class="{isMd ? 'h-3.5 w-3.5' : 'h-3 w-3'} text-neutral-500"
    fill="none"
    stroke="currentColor"
    stroke-width="1.5"
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    <path stroke-linecap="round" stroke-linejoin="round" d={iconPath} />
  </svg>
  {label}
</span>

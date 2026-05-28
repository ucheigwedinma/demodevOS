<script lang="ts">
  import type { InternalTaskPriority } from "$lib/types";
  import { i18n } from "$lib/stores/i18n.svelte";
  import { PRIORITY_TREATMENT } from "./task-priority";

  /**
   * Priority chip. Per UI spec §3 display rule: caller decides whether to
   * render at all using `treatment.showInRow` for list-row context.
   * This component always renders when invoked.
   */

  interface Props {
    priority: InternalTaskPriority;
    size?: "sm" | "md";
  }

  let { priority, size = "sm" }: Props = $props();

  let treatment = $derived(PRIORITY_TREATMENT[priority]);
  let label = $derived(i18n.t(treatment.labelKey));
  let isMd = $derived(size === "md");
</script>

<span
  class="inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 font-semibold uppercase tracking-wider {treatment.chip} {treatment.text} {treatment.border} {isMd ? 'text-xs' : 'text-[10px]'}"
  aria-label={i18n.t("workspace.internal_tasks.priority.aria_label", { label })}
>
  {#if treatment.iconPath}
    <svg
      class="{isMd ? 'h-3.5 w-3.5' : 'h-3 w-3'}"
      fill="none"
      stroke="currentColor"
      stroke-width="1.75"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path stroke-linecap="round" stroke-linejoin="round" d={treatment.iconPath} />
    </svg>
  {/if}
  {label}
</span>

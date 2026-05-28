<script lang="ts">
  import type { InternalTaskOverlaySource } from "$lib/types";
  import { i18n } from "$lib/stores/i18n.svelte";

  /**
   * Small "P" / "C" badge for read-only operational overlay rows.
   * Mirrors Calendar's "M" badge shape (top-right corner, neutral bg).
   * Color-blind safe: identifies via letter + dashed border on parent row.
   */

  interface Props {
    source: InternalTaskOverlaySource;
  }

  let { source }: Props = $props();

  let letter = $derived(source === "project_task" ? "P" : "C");
  let ariaKey = $derived(
    source === "project_task"
      ? "workspace.internal_tasks.overlay.from_projects"
      : "workspace.internal_tasks.overlay.from_crm",
  );
</script>

<span
  class="inline-flex h-4 w-4 items-center justify-center rounded bg-neutral-200 text-[9px] font-bold text-neutral-700"
  aria-label={i18n.t(ariaKey)}
>
  {letter}
</span>

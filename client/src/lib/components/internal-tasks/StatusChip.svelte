<script lang="ts">
  import type { InternalTaskStatus } from "$lib/types";
  import { i18n } from "$lib/stores/i18n.svelte";
  import { STATUS_TREATMENT, STATUS_ORDER } from "./task-status";

  /**
   * Status chip. Two modes:
   *   - static: just the chip
   *   - editable: chip with caret; click opens a small dropdown of statuses.
   *     Calls onChange when the user picks one. Caller handles the API call
   *     and optimistic update.
   */

  interface Props {
    status: InternalTaskStatus;
    editable?: boolean;
    onChange?: (next: InternalTaskStatus) => void;
    size?: "sm" | "md";
  }

  let { status, editable = false, onChange, size = "sm" }: Props = $props();

  let open = $state(false);
  let containerEl = $state<HTMLDivElement | null>(null);

  function toggle() {
    if (!editable) return;
    open = !open;
  }

  function pick(next: InternalTaskStatus) {
    open = false;
    if (next !== status) onChange?.(next);
  }

  function handleOutsideClick(e: MouseEvent) {
    if (!containerEl) return;
    if (!containerEl.contains(e.target as Node)) open = false;
  }

  $effect(() => {
    if (open) {
      document.addEventListener("click", handleOutsideClick);
      return () => document.removeEventListener("click", handleOutsideClick);
    }
  });

  let treatment = $derived(STATUS_TREATMENT[status]);
  let label = $derived(i18n.t(treatment.labelKey));
  let isMd = $derived(size === "md");
</script>

<div bind:this={containerEl} class="relative inline-block">
  <button
    type="button"
    onclick={toggle}
    disabled={!editable && !onChange}
    aria-haspopup={editable ? "listbox" : undefined}
    aria-expanded={editable ? open : undefined}
    aria-label={i18n.t("workspace.internal_tasks.status.aria_label", { label })}
    class="inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 font-semibold uppercase tracking-wider transition {treatment.chip} {treatment.text} {treatment.border} {isMd ? 'text-xs' : 'text-[10px]'} {editable ? 'cursor-pointer hover:brightness-95' : 'cursor-default'}"
  >
    <svg
      class="{isMd ? 'h-3.5 w-3.5' : 'h-3 w-3'}"
      fill="none"
      stroke="currentColor"
      stroke-width="1.5"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path stroke-linecap="round" stroke-linejoin="round" d={treatment.iconPath} />
    </svg>
    {label}
    {#if editable}
      <svg class="h-3 w-3 opacity-70" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
      </svg>
    {/if}
  </button>

  {#if editable && open}
    <ul
      class="absolute left-0 z-30 mt-1 min-w-[10rem] overflow-hidden rounded-xl border border-neutral-200 bg-white py-1 shadow-md"
      role="listbox"
    >
      {#each STATUS_ORDER as s}
        {@const t = STATUS_TREATMENT[s]}
        <li>
          <button
            type="button"
            onclick={() => pick(s)}
            class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs hover:bg-neutral-50 {s === status ? 'font-semibold text-neutral-900' : 'text-neutral-700'}"
            role="option"
            aria-selected={s === status}
          >
            <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d={t.iconPath} />
            </svg>
            {i18n.t(t.labelKey)}
          </button>
        </li>
      {/each}
    </ul>
  {/if}
</div>

<script lang="ts">
  import type { InternalTaskChecklistItem } from "$lib/types";
  import { i18n } from "$lib/stores/i18n.svelte";

  /**
   * Inline checklist editor. Per UI spec:
   *   - [ ] / [x] per item
   *   - Add: type label + Enter → appended (status: unchecked)
   *   - Remove: × button on each row
   *   - Soft limit 50: at >50 items, show inline warning. Hard limit 100
   *     enforced server-side (Service returns 400).
   *   - No drag-to-reorder in v1 (UI spec defers).
   *
   * `items` is two-way bound; callers persist via a debounced PATCH /checklist.
   */

  interface Props {
    items: InternalTaskChecklistItem[];
    readonly?: boolean;
    onChange?: (next: InternalTaskChecklistItem[]) => void;
  }

  let { items = $bindable([]), readonly = false, onChange }: Props = $props();

  let newLabel = $state("");

  function emit(next: InternalTaskChecklistItem[]) {
    items = next;
    onChange?.(next);
  }

  function toggle(index: number) {
    const next = items.map((it, i) =>
      i === index ? { ...it, checked: !it.checked } : it,
    );
    emit(next);
  }

  function remove(index: number) {
    emit(items.filter((_, i) => i !== index));
  }

  function add() {
    const label = newLabel.trim();
    if (!label) return;
    if (items.length >= 100) return; // hard limit; mirror server-side
    emit([...items, { label, checked: false }]);
    newLabel = "";
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "Enter") {
      e.preventDefault();
      add();
    }
  }

  let overSoftLimit = $derived(items.length > 50);
</script>

<div class="space-y-2">
  <ul class="space-y-1.5">
    {#each items as item, i (i)}
      <li class="flex items-center gap-2 rounded-lg px-1.5 py-1 hover:bg-neutral-50">
        <button
          type="button"
          onclick={() => toggle(i)}
          disabled={readonly}
          aria-label={item.checked
            ? i18n.t("workspace.internal_tasks.checklist.uncheck")
            : i18n.t("workspace.internal_tasks.checklist.check")}
          class="inline-flex h-4 w-4 shrink-0 items-center justify-center rounded border {item.checked ? 'border-neutral-900 bg-neutral-900 text-white' : 'border-neutral-300 bg-white text-transparent hover:border-neutral-400'} disabled:opacity-50"
        >
          <svg class="h-3 w-3" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
          </svg>
        </button>
        <span class="flex-1 text-sm {item.checked ? 'text-neutral-400 line-through' : 'text-neutral-800'}">
          {item.label}
        </span>
        {#if !readonly}
          <button
            type="button"
            onclick={() => remove(i)}
            aria-label={i18n.t("workspace.internal_tasks.checklist.remove")}
            class="text-neutral-300 hover:text-neutral-700"
          >
            <svg class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        {/if}
      </li>
    {/each}
  </ul>

  {#if !readonly}
    <div class="flex items-center gap-2 rounded-lg border border-dashed border-neutral-300 px-2.5 py-1.5">
      <span class="inline-flex h-4 w-4 items-center justify-center rounded border border-neutral-300 bg-white" aria-hidden="true">
        <svg class="h-3 w-3 text-neutral-400" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
      </span>
      <input
        type="text"
        bind:value={newLabel}
        onkeydown={handleKeydown}
        placeholder={i18n.t("workspace.internal_tasks.checklist.add_placeholder")}
        class="flex-1 bg-transparent text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none"
      />
      {#if newLabel.trim()}
        <button
          type="button"
          onclick={add}
          class="rounded-lg bg-neutral-900 px-2.5 py-1 text-xs font-semibold text-white hover:bg-neutral-800"
        >
          {i18n.t("workspace.internal_tasks.checklist.add")}
        </button>
      {/if}
    </div>

    {#if overSoftLimit}
      <p class="text-xs text-amber-700">
        {i18n.t("workspace.internal_tasks.checklist.soft_limit_warning", { count: items.length })}
      </p>
    {/if}
  {/if}
</div>

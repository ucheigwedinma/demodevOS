<script lang="ts">
  /**
   * Compact language picker. Renders as a small button with a globe icon
   * + the current locale's two-letter code; opens a floating popover
   * with the full list of supported languages on click.
   *
   * Positioning notes:
   * The component is meant to live in the dark sidebar rail, which is
   * only 52px wide and has parents that clip overflow. Using
   * `position: absolute` would clip the 176px-wide popover. We compute
   * the trigger's bounding rect on open and render the popover with
   * `position: fixed` + JS-driven coordinates so it escapes any
   * ancestor overflow rules and pops OUT to the right of the rail.
   */
  import { i18n } from "$lib/stores/i18n.svelte";
  import type { LocaleCode } from "$lib/i18n/locales";

  let open = $state(false);
  let trigger: HTMLButtonElement | undefined = $state();
  let popoverTop = $state(0);
  let popoverLeft = $state(0);

  const POPOVER_WIDTH = 176; // matches w-44

  function recomputePosition() {
    if (!trigger) return;
    const rect = trigger.getBoundingClientRect();
    const gap = 8;
    // Anchor the popover so its bottom-left sits 8px above the trigger's
    // top-right corner. That puts it OUT of the 52px rail, into the
    // section panel area where there's room for it.
    popoverLeft = Math.min(
      rect.right + gap,
      window.innerWidth - POPOVER_WIDTH - gap,
    );
    // Bottom-aligned with the trigger; drop the popover above it.
    popoverTop = Math.max(gap, rect.bottom - 1);
  }

  function toggle(event: MouseEvent) {
    event.stopPropagation();
    if (!open) recomputePosition();
    open = !open;
  }

  function pick(code: LocaleCode) {
    i18n.setLocale(code);
    open = false;
  }

  function onWindowClick(event: MouseEvent) {
    if (!open) return;
    const target = event.target as HTMLElement | null;
    if (target && trigger && trigger.contains(target)) return;
    if (target && target.closest("[data-language-selector-menu]")) return;
    open = false;
  }

  function onWindowResize() {
    if (open) recomputePosition();
  }
</script>

<svelte:window onclick={onWindowClick} onresize={onWindowResize} />

<button
  bind:this={trigger}
  type="button"
  onclick={toggle}
  aria-haspopup="listbox"
  aria-expanded={open}
  aria-label="Change language"
  class="inline-flex items-center gap-1.5 rounded-lg border border-neutral-700/60 bg-neutral-800/60 px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-neutral-200 hover:border-neutral-500 hover:bg-neutral-700 hover:text-white transition-colors"
>
  <!-- Heroicons globe-alt outline -->
  <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="1.75" viewBox="0 0 24 24" aria-hidden="true">
    <path
      stroke-linecap="round"
      stroke-linejoin="round"
      d="M12 21a9.004 9.004 0 0 0 8.716-6.747M12 21a9.004 9.004 0 0 1-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 0 1 7.843 4.582M12 3a8.997 8.997 0 0 0-7.843 4.582m15.686 0A11.953 11.953 0 0 1 12 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0 1 21 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0 1 12 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 0 1 3 12c0-1.605.42-3.113 1.157-4.418"
    />
  </svg>
  {i18n.locale.toUpperCase()}
</button>

{#if open}
  <div
    data-language-selector-menu
    role="listbox"
    aria-label="Available languages"
    class="fixed z-[60] w-44 overflow-hidden rounded-lg border border-neutral-200 bg-white shadow-xl"
    style="top: {popoverTop}px; left: {popoverLeft}px; transform: translateY(-100%);"
  >
    {#each i18n.available as locale (locale.code)}
      <button
        type="button"
        role="option"
        aria-selected={i18n.locale === locale.code}
        onclick={() => pick(locale.code)}
        class="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-xs transition-colors {i18n.locale === locale.code
          ? 'bg-neutral-900 text-white'
          : 'text-neutral-700 hover:bg-neutral-50'}"
      >
        <span class="flex flex-col">
          <span class="font-semibold">{locale.name}</span>
          <span class="text-[10px] {i18n.locale === locale.code ? 'text-neutral-300' : 'text-neutral-400'}">{locale.english}</span>
        </span>
        <span class="text-[10px] font-mono uppercase tabular-nums opacity-70">{locale.code}</span>
      </button>
    {/each}
  </div>
{/if}

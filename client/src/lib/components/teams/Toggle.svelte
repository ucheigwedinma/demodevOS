<script lang="ts">
  /**
   * iOS-style toggle. Lives under teams/ for now; promote to lib/components/
   * if other features adopt it.
   */
  interface Props {
    checked: boolean;
    onToggle?: (next: boolean) => void;
    label?: string;
    disabled?: boolean;
  }

  let { checked = $bindable(), onToggle, label, disabled = false }: Props = $props();

  function flip() {
    if (disabled) return;
    const next = !checked;
    checked = next;
    onToggle?.(next);
  }
</script>

<button
  type="button"
  role="switch"
  aria-checked={checked}
  aria-label={label}
  disabled={disabled}
  onclick={flip}
  class="relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-neutral-800/10 disabled:cursor-not-allowed disabled:opacity-60 {checked
    ? 'bg-neutral-900'
    : 'bg-neutral-200'}"
>
  <span
    aria-hidden="true"
    class="inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform {checked
      ? 'translate-x-5'
      : 'translate-x-0.5'}"
  ></span>
</button>

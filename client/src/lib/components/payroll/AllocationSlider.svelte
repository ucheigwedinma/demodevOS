<script lang="ts">
  type Props = {
    label: string;
    value: number;
    note?: string;
    amountLabel?: string;
    max?: number;
    disabled?: boolean;
    onChange: (value: number) => void;
  };

  let {
    label,
    value,
    note = "",
    amountLabel = "",
    max = 100,
    disabled = false,
    onChange,
  }: Props = $props();

  function handleChange(nextValue: number) {
    if (disabled) return;
    onChange(Math.max(0, Math.min(max, nextValue)));
  }
</script>

<div class="rounded-[24px] border border-white/50 bg-[linear-gradient(180deg,rgba(255,255,255,0.74),rgba(244,251,248,0.58))] p-4 shadow-[0_18px_45px_rgba(148,163,184,0.14)] backdrop-blur-xl">
  <div class="flex items-start justify-between gap-4">
    <div class="min-w-0">
      <p class="truncate text-sm font-semibold text-neutral-900">{label}</p>
      {#if note}
        <p class="mt-1 text-xs text-neutral-500">{note}</p>
      {/if}
    </div>
    <div class="text-right">
      <p class="text-lg font-semibold text-emerald-700 tabular-nums">{value.toFixed(0)}%</p>
      {#if amountLabel}
        <p class="mt-1 text-xs text-neutral-500">{amountLabel}</p>
      {/if}
    </div>
  </div>

  <div class="mt-4 flex items-center gap-3">
    <input
      type="range"
      min="0"
      max={String(max)}
      step="1"
      value={String(value)}
      disabled={disabled}
      oninput={(event) => handleChange(Number((event.currentTarget as HTMLInputElement).value))}
      class="h-2 w-full cursor-pointer appearance-none rounded-full bg-emerald-100 accent-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
    />
    <input
      type="number"
      min="0"
      max={String(max)}
      step="1"
      value={String(value.toFixed(0))}
      disabled={disabled}
      oninput={(event) => handleChange(Number((event.currentTarget as HTMLInputElement).value))}
      class="w-20 rounded-xl border border-emerald-200 bg-white/80 px-3 py-2 text-right text-sm font-semibold text-neutral-900 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-200 disabled:cursor-not-allowed disabled:opacity-50"
    />
  </div>
</div>

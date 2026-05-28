<script lang="ts">
  let {
    title,
    value,
    subtitle = "",
    accent = "neutral",
  }: {
    title: string;
    value: string;
    subtitle?: string;
    accent?: "neutral" | "blue" | "amber" | "red" | "emerald";
  } = $props();

  const accentClasses: Record<string, string> = {
    neutral: "border-neutral-400 bg-neutral-50/40",
    blue: "border-blue-500 bg-blue-50/45",
    amber: "border-amber-500 bg-amber-50/45",
    red: "border-red-500 bg-red-50/45",
    emerald: "border-emerald-500 bg-emerald-50/45",
  };
</script>

<div class="rounded-xl border-2 p-5 shadow-sm {accentClasses[accent] ?? accentClasses.neutral}">
  <p class="text-xs uppercase tracking-wider text-neutral-400 font-medium">{title}</p>
  <p class="mt-2 text-2xl font-semibold text-neutral-900 tabular-nums">{value}</p>
  {#if subtitle}
    <p class="mt-1 text-xs text-neutral-500">{subtitle}</p>
  {/if}
</div>

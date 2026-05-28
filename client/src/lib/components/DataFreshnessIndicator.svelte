<script lang="ts">
  let {
    status,
    label,
    ageHours,
  }: {
    status: "fresh" | "stale" | "missing";
    label: string;
    ageHours: number | null;
  } = $props();

  const dotColor = $derived(
    status === "fresh"
      ? "bg-emerald-500"
      : status === "stale"
        ? "bg-amber-500"
        : "bg-neutral-400"
  );

  const displayText = $derived(() => {
    if (status === "missing") return "No data";
    if (status === "stale" && ageHours !== null) return `${Math.round(ageHours)}h ago`;
    if (status === "fresh" && ageHours !== null) {
      if (ageHours < 1) return `${Math.round(ageHours * 60)}m ago`;
      return `${Math.round(ageHours)}h ago`;
    }
    return status;
  });
</script>

<div class="inline-flex items-center gap-1.5 rounded-full border border-neutral-200 bg-white px-2.5 py-1">
  <div class="w-1.5 h-1.5 rounded-full {dotColor}"></div>
  <span class="text-[10px] font-medium text-neutral-500 uppercase tracking-wider">{label}</span>
  <span class="text-[10px] text-neutral-400 tabular-nums">{displayText()}</span>
</div>

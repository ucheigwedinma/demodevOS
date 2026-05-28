<script lang="ts">
  import { statusRegistry } from "$lib/stores/statusRegistry.svelte";

  interface Props {
    status: string;
    label?: string;
    size?: "sm" | "md";
  }

  let { status, label, size = "sm" }: Props = $props();

  let entry = $derived(statusRegistry.get(status));
  let displayLabel = $derived(label ?? entry.label);
</script>

<span
  class="inline-flex items-center border rounded-md font-medium
         {size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs'}
         {entry.classes}"
>
  {displayLabel}
</span>

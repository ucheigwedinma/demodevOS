<script lang="ts">
  let {
    width = "w-full",
    height = "h-4",
    rounded = "rounded",
  }: {
    width?: string;
    height?: string;
    rounded?: string;
  } = $props();
</script>

<div class="animate-pulse bg-neutral-200 {width} {height} {rounded}"></div>

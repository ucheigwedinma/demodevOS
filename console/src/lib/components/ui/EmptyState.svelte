<script lang="ts">
  let {
    title = "No records found",
    description = "There are no records to display.",
    icon,
  }: {
    title?: string;
    description?: string;
    icon?: string;
  } = $props();
</script>

<div class="flex flex-col items-center justify-center py-16 text-center">
  <div class="w-12 h-12 rounded-xl bg-neutral-100 flex items-center justify-center mb-4">
    <svg class="w-6 h-6 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
      <path stroke-linecap="round" stroke-linejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
    </svg>
  </div>
  <p class="text-sm font-medium text-neutral-900">{title}</p>
  <p class="text-xs text-neutral-500 mt-1 max-w-xs">{description}</p>
</div>

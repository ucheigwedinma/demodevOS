<script lang="ts">
  let {
    page = 1,
    pageSize = 25,
    total = 0,
    onPageChange,
  }: {
    page: number;
    pageSize: number;
    total: number;
    onPageChange: (page: number) => void;
  } = $props();

  let totalPages = $derived(Math.ceil(total / pageSize));
  let from = $derived((page - 1) * pageSize + 1);
  let to = $derived(Math.min(page * pageSize, total));
</script>

{#if total > 0}
  <div class="flex items-center justify-between px-1 py-3">
    <p class="text-xs text-neutral-500">
      Showing <span class="font-medium text-neutral-700">{from}</span> to
      <span class="font-medium text-neutral-700">{to}</span> of
      <span class="font-medium text-neutral-700">{total}</span> results
    </p>
    <div class="flex items-center gap-1">
      <button
        onclick={() => onPageChange(page - 1)}
        disabled={page <= 1}
        class="px-2.5 py-1.5 text-xs font-medium rounded-lg border border-neutral-200 text-neutral-600
               hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        Previous
      </button>
      <span class="px-3 py-1.5 text-xs text-neutral-500">
        {page} / {totalPages}
      </span>
      <button
        onclick={() => onPageChange(page + 1)}
        disabled={page >= totalPages}
        class="px-2.5 py-1.5 text-xs font-medium rounded-lg border border-neutral-200 text-neutral-600
               hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        Next
      </button>
    </div>
  </div>
{/if}

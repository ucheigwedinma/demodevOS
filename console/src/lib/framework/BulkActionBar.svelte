<script lang="ts">
  import type { ResourceAction } from "./types";

  let {
    count,
    label,
    labelPlural,
    canDelete = true,
    bulkActions,
    loading = false,
    onclear,
    ondelete,
  }: {
    count: number;
    label: string;
    labelPlural: string;
    canDelete?: boolean;
    bulkActions?: ResourceAction[];
    loading?: boolean;
    onclear: () => void;
    ondelete: () => void;
  } = $props();

  let confirmDelete = $state(false);
</script>

<div class="fixed bottom-6 left-1/2 -translate-x-1/2 z-40">
  <div class="flex items-center gap-3 bg-neutral-900 text-white rounded-xl shadow-2xl px-5 py-3 min-w-[320px]">
    <!-- Count -->
    <span class="text-sm font-medium tabular-nums">
      {count} {count === 1 ? label.toLowerCase() : labelPlural.toLowerCase()} selected
    </span>

    <div class="w-px h-5 bg-neutral-700"></div>

    <!-- Actions -->
    <div class="flex items-center gap-2">
      {#if bulkActions}
        {#each bulkActions as action}
          <button
            class="px-3 py-1.5 text-xs font-medium rounded-lg transition-colors
                   {action.variant === 'danger'
                     ? 'bg-red-500/20 text-red-300 hover:bg-red-500/30'
                     : action.variant === 'primary'
                       ? 'bg-white/10 text-white hover:bg-white/20'
                       : 'bg-white/10 text-neutral-300 hover:bg-white/20'}"
          >
            {action.label}
          </button>
        {/each}
      {/if}

      {#if canDelete}
        {#if confirmDelete}
          <button
            onclick={() => { confirmDelete = false; ondelete(); }}
            disabled={loading}
            class="px-3 py-1.5 text-xs font-medium rounded-lg bg-red-500 text-white hover:bg-red-600 transition-colors disabled:opacity-50"
          >
            {#if loading}
              Deleting...
            {:else}
              Confirm delete
            {/if}
          </button>
          <button
            onclick={() => { confirmDelete = false; }}
            class="px-3 py-1.5 text-xs font-medium rounded-lg bg-white/10 text-neutral-300 hover:bg-white/20 transition-colors"
          >
            Cancel
          </button>
        {:else}
          <button
            onclick={() => { confirmDelete = true; }}
            class="px-3 py-1.5 text-xs font-medium rounded-lg bg-red-500/20 text-red-300 hover:bg-red-500/30 transition-colors"
          >
            Delete
          </button>
        {/if}
      {/if}
    </div>

    <div class="w-px h-5 bg-neutral-700"></div>

    <!-- Clear -->
    <button
      onclick={onclear}
      class="p-1 rounded-lg text-neutral-400 hover:text-white hover:bg-white/10 transition-colors"
      title="Clear selection"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
      </svg>
    </button>
  </div>
</div>

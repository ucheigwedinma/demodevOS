<script lang="ts">
  /**
   * Inline error state for list/dashboard fetches that have failed.
   *
   * Renders in place of (or above) an empty state so users can tell
   * "backend down" apart from "genuinely no data". Includes a Retry
   * button wired to the page's refetch function.
   *
   * Usage:
   *   {#if listError}
   *     <DataStateBanner message={listError} onretry={fetchLeads} />
   *   {:else if items.length === 0}
   *     <empty state>
   *   {:else}
   *     <table>
   *   {/if}
   */
  let {
    message = "We couldn't reach the server.",
    title = "Couldn't load this view",
    onretry,
    retrying = false,
  }: {
    message?: string;
    title?: string;
    onretry: () => void | Promise<void>;
    retrying?: boolean;
  } = $props();
</script>

<div class="rounded-xl border border-rose-200 bg-rose-50/60 px-4 py-8 text-center">
  <svg
    class="mx-auto mb-3 h-8 w-8 text-rose-500"
    fill="none"
    stroke="currentColor"
    stroke-width="1.5"
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    <path
      stroke-linecap="round"
      stroke-linejoin="round"
      d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z"
    />
  </svg>
  <p class="text-sm font-semibold text-rose-800">{title}</p>
  <p class="mt-1 text-xs text-rose-700/80">{message}</p>
  <button
    type="button"
    onclick={() => void onretry()}
    disabled={retrying}
    class="mt-4 inline-flex items-center gap-1.5 rounded-lg border border-rose-300 bg-white px-3 py-1.5 text-xs font-semibold text-rose-700 transition-colors hover:border-rose-400 hover:bg-rose-50 disabled:cursor-not-allowed disabled:opacity-50"
  >
    {#if retrying}
      <span class="inline-block h-3 w-3 animate-spin rounded-full border-[1.5px] border-rose-300 border-t-rose-700" aria-hidden="true"></span>
      Retrying…
    {:else}
      <svg class="h-3 w-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
      </svg>
      Retry
    {/if}
  </button>
</div>

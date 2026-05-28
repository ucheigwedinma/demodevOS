<script lang="ts">
  import { goto } from "$app/navigation";
  import { getToasts, dismissToast, type ToastType } from "$lib/stores/toast.svelte";

  const toasts = $derived(getToasts());

  const borderColors: Record<ToastType, string> = {
    success: "border-green-500/40",
    error: "border-red-500/40",
    warning: "border-amber-500/40",
    info: "border-blue-500/40",
  };

  const iconColors: Record<ToastType, string> = {
    success: "text-green-500",
    error: "text-red-500",
    warning: "text-amber-500",
    info: "text-blue-500",
  };

  const icons: Record<ToastType, { viewBox: string; d: string; fill?: boolean }> = {
    success: {
      viewBox: "0 0 24 24",
      d: "M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
    },
    error: {
      viewBox: "0 0 24 24",
      d: "m9.75 9.75 4.5 4.5m0-4.5-4.5 4.5M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
    },
    warning: {
      viewBox: "0 0 24 24",
      d: "M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z",
    },
    info: {
      viewBox: "0 0 24 24",
      d: "m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z",
    },
  };
</script>

{#if toasts.length > 0}
  <div class="fixed bottom-6 right-6 z-1200 flex max-w-sm w-full flex-col gap-3">
    {#each toasts as t (t.id)}
      <div
        class="flex items-start gap-3 px-4 py-3.5 rounded-xl border bg-neutral-950 shadow-2xl animate-in
               {borderColors[t.type]}"
        role="alert"
      >
        <svg
          class="w-5 h-5 shrink-0 mt-0.5 {iconColors[t.type]}"
          fill="none"
          stroke="currentColor"
          viewBox={icons[t.type].viewBox}
          stroke-width="1.5"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d={icons[t.type].d} />
        </svg>
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <p class="text-sm font-semibold text-white">{t.title}</p>
            {#if t.source === "notification"}
              <span class="shrink-0 rounded-full bg-indigo-500/20 border border-indigo-500/30 px-1.5 py-0.5 text-[8px] font-bold text-indigo-300 uppercase">Live</span>
            {/if}
          </div>
          {#if t.description}
            <p class="text-xs text-neutral-400 mt-0.5">{t.description}</p>
          {/if}
          {#if t.link_url}
            <button
              onclick={() => { dismissToast(t.id); goto(t.link_url!); }}
              class="mt-1 text-[11px] font-medium text-indigo-400 hover:text-indigo-300 transition-colors"
            >View details →</button>
          {/if}
        </div>
        <button
          onclick={() => dismissToast(t.id)}
          class="shrink-0 text-neutral-500 hover:text-neutral-300 transition-colors"
          aria-label="Dismiss"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    {/each}
  </div>
{/if}

<style>
  .animate-in {
    animation: slideIn 0.25s ease-out;
  }

  @keyframes slideIn {
    from {
      opacity: 0;
      transform: translateY(12px) scale(0.96);
    }
    to {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
  }
</style>

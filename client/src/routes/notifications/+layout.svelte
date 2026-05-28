<script lang="ts">
  let { children } = $props();
</script>

<div class="h-screen flex flex-col bg-neutral-50 font-sans">
  <!-- Top Nav -->
  <header class="bg-neutral-900 shrink-0">
    <div class="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
      <div class="flex items-center gap-6">
        <a href="/" class="text-lg">
          <span class="font-normal text-white">developer</span><span class="font-bold text-neutral-400">OS</span>
        </a>
        <span class="text-neutral-600">|</span>
        <h1 class="text-sm font-semibold text-white">Notifications</h1>
      </div>
      <a
        href="/"
        class="flex items-center gap-2 text-sm text-neutral-400 hover:text-white transition-colors"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
        </svg>
        Back to app
      </a>
    </div>
  </header>

  <!-- Content -->
  <div class="max-w-7xl mx-auto px-6 flex-1 min-h-0 w-full overflow-y-auto py-8">
    {@render children()}
  </div>
</div>

<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";

  // The portfolio analysis dashboard moved to /dashboard/portfolio-analysis
  // so it lives alongside the rest of the Dashboard cluster. Bookmarks and
  // any external links to the old path land here and are redirected, with
  // replaceState so the back button skips this stub.
  onMount(() => {
    void goto("/dashboard/portfolio-analysis", { replaceState: true });
  });
</script>

<div class="flex items-center justify-center py-28">
  <div class="h-7 w-7 animate-spin rounded-full border-[2.5px] border-neutral-200 border-t-neutral-900"></div>
</div>

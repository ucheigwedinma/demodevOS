<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";

  onMount(() => {
    void goto("/projects/blueprints", { replaceState: true });
  });
</script>

<div class="flex min-h-[40vh] items-center justify-center text-sm text-neutral-500">
  Redirecting to Project Setup…
</div>

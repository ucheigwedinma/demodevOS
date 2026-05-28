<script lang="ts">
  import { page } from "$app/stores";
  import { getResource } from "$lib/registry/index";
  import ResourceFormSlideOver from "$lib/framework/ResourceFormSlideOver.svelte";

  let config = $derived(getResource($page.params.module, $page.params.resource));
</script>

{#if config}
  <ResourceFormSlideOver {config} />
{:else}
  <p class="text-sm text-neutral-500">Resource not found.</p>
{/if}

<script lang="ts">
  import { page } from "$app/stores";
  import { getResource } from "$lib/registry/index";
  import ResourceListPage from "$lib/framework/ResourceListPage.svelte";
  import SingletonFormPage from "$lib/framework/SingletonFormPage.svelte";

  let config = $derived(getResource($page.params.module, $page.params.resource));
</script>

{#if config}
  {#if config.singleton}
    <SingletonFormPage {config} />
  {:else}
    <ResourceListPage {config} />
  {/if}
{:else}
  <div class="flex flex-col items-center justify-center py-16">
    <p class="text-sm text-neutral-500">Resource not found: {$page.params.module}/{$page.params.resource}</p>
  </div>
{/if}

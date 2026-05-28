<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { PaginatedResponse, ReportTemplateListItem } from "$lib/types";

  let loading = $state(true);
  let templates = $state<ReportTemplateListItem[]>([]);

  function unwrapList<T>(payload: PaginatedResponse<T> | T[]): T[] {
    return Array.isArray(payload) ? payload : (payload?.results ?? []);
  }

  async function loadBuilderTemplates() {
    loading = true;
    try {
      const payload = await api.get<PaginatedResponse<ReportTemplateListItem> | ReportTemplateListItem[]>("/settings/report-templates/", {
        ordering: "name",
        is_active: "true",
      });
      templates = unwrapList(payload).filter((template) => template.allow_simple_builder);
    } catch {
      templates = [];
      toast.error("Load failed", "Could not load simple builder templates.");
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    void loadBuilderTemplates();
  });
</script>

<div class="space-y-6">
  <section class="rounded-xl border border-neutral-200 bg-white p-5">
    <h1 class="text-2xl font-bold text-neutral-900">Simple Report Builder</h1>
    <p class="mt-2 text-sm text-neutral-600">Use templates flagged for simple builder access.</p>
  </section>

  <section class="rounded-xl border border-neutral-200 bg-white p-5">
    {#if loading}
      <p class="text-sm text-neutral-500">Loading builder templates...</p>
    {:else if templates.length === 0}
      <p class="text-sm text-neutral-500">No templates currently allow simple builder for your role.</p>
    {:else}
      <div class="space-y-3">
        {#each templates as template (template.id)}
          <article class="rounded-lg border border-neutral-200 bg-neutral-50 p-4 flex items-center justify-between gap-3">
            <div>
              <h3 class="text-sm font-semibold text-neutral-900">{template.name}</h3>
              <p class="mt-1 text-xs text-neutral-600">{template.module_source_display} | {template.template_type_display}</p>
            </div>
            <a
              href={`/reports/${template.id}`}
              class="rounded-lg bg-neutral-900 px-3 py-1.5 text-xs font-semibold text-white hover:bg-neutral-800"
            >
              Open Template
            </a>
          </article>
        {/each}
      </div>
    {/if}
  </section>
</div>

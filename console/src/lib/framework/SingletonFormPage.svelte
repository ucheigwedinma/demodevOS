<script lang="ts">
  import { onMount } from "svelte";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import FieldRenderer from "./FieldRenderer.svelte";
  import type { ResourceConfig } from "./types";

  let { config }: { config: ResourceConfig } = $props();

  let formData = $state<Record<string, unknown>>({});
  let errors = $state<Record<string, string>>({});
  let loading = $state(true);
  let saving = $state(false);

  onMount(() => {
    fetchData();
  });

  async function fetchData() {
    loading = true;
    try {
      formData = await api.get<Record<string, unknown>>(config.endpoint);
    } catch {
      toast.error("Failed to load settings");
    } finally {
      loading = false;
    }
  }

  function handleFieldChange(key: string, value: unknown) {
    formData = { ...formData, [key]: value };
    if (errors[key]) {
      const { [key]: _, ...rest } = errors;
      errors = rest;
    }
  }

  async function handleSave() {
    if (config.formSchema) {
      const result = config.formSchema.safeParse(formData);
      if (!result.success) {
        const fieldErrors: Record<string, string> = {};
        for (const issue of result.error.issues) {
          const key = issue.path.join(".");
          fieldErrors[key] = issue.message;
        }
        errors = fieldErrors;
        return;
      }
    }

    saving = true;
    errors = {};
    try {
      const payload: Record<string, unknown> = {};
      for (const field of config.formFields ?? []) {
        if (field.type !== "readonly" && formData[field.key] !== undefined) {
          payload[field.key] = formData[field.key];
        }
      }
      formData = await api.patch<Record<string, unknown>>(config.endpoint, payload);
      toast.success("Settings saved");
    } catch (e) {
      if (e instanceof ApiError && e.status === 400 && e.data) {
        const fieldErrors: Record<string, string> = {};
        for (const [key, val] of Object.entries(e.data)) {
          fieldErrors[key] = Array.isArray(val) ? val[0] : String(val);
        }
        errors = fieldErrors;
      } else {
        toast.error("Save failed");
      }
    } finally {
      saving = false;
    }
  }
</script>

<div class="max-w-3xl">
  <div class="flex items-center justify-between mb-6">
    <div>
      <h1 class="text-lg font-semibold text-neutral-900">{config.label}</h1>
      <p class="text-sm text-neutral-500 mt-0.5">{config.labelPlural}</p>
    </div>
    <button
      onclick={handleSave}
      disabled={saving || loading}
      class="px-4 py-2 bg-neutral-900 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 disabled:opacity-50 transition-colors"
    >
      {saving ? "Saving..." : "Save Changes"}
    </button>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-16">
      <div class="w-5 h-5 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div>
    </div>
  {:else if config.formSections}
    <div class="space-y-8">
      {#each config.formSections as section}
        <div class="bg-white rounded-xl border border-neutral-200 p-6">
          <h2 class="text-sm font-semibold text-neutral-900 mb-4">{section.label}</h2>
          <div class="grid grid-cols-2 gap-4">
            {#each (config.formFields ?? []).filter((f) => f.section === section.key) as field}
              {#if !field.showIf || field.showIf(formData)}
                <FieldRenderer
                  {field}
                  value={formData[field.key]}
                  error={errors[field.key]}
                  onchange={(val) => handleFieldChange(field.key, val)}
                />
              {/if}
            {/each}
          </div>
        </div>
      {/each}
    </div>
  {:else}
    <div class="bg-white rounded-xl border border-neutral-200 p-6">
      <div class="grid grid-cols-2 gap-4">
        {#each config.formFields ?? [] as field}
          {#if !field.showIf || field.showIf(formData)}
            <FieldRenderer
              {field}
              value={formData[field.key]}
              error={errors[field.key]}
              onchange={(val) => handleFieldChange(field.key, val)}
            />
          {/if}
        {/each}
      </div>
    </div>
  {/if}
</div>

<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { page } from "$app/stores";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { ResourceConfig } from "./types";
  import FieldRenderer from "./FieldRenderer.svelte";
  import SlideOver from "$lib/components/ui/SlideOver.svelte";

  let {
    config,
    recordId,
    open = true,
    onclose,
  }: {
    config: ResourceConfig;
    recordId?: string | number;
    open?: boolean;
    onclose?: () => void;
  } = $props();

  let formData = $state<Record<string, unknown>>({});
  let errors = $state<Record<string, string>>({});
  let loading = $state(false);
  let fetching = $state(false);
  let isEdit = $derived(!!recordId);

  function initDefaults() {
    const defaults: Record<string, unknown> = {};
    for (const field of config.formFields ?? []) {
      if (field.defaultValue !== undefined) {
        defaults[field.key] = field.defaultValue;
      }
    }
    formData = defaults;
  }

  async function fetchRecord() {
    if (!recordId) return;
    fetching = true;
    try {
      formData = await api.get<Record<string, unknown>>(`${config.endpoint}${recordId}/`);
    } catch {
      toast.error("Load failed");
    } finally {
      fetching = false;
    }
  }

  function handleFieldChange(key: string, value: unknown) {
    formData = { ...formData, [key]: value };
    if (errors[key]) {
      const { [key]: _, ...rest } = errors;
      errors = rest;
    }
  }

  async function handleSubmit() {
    if (config.formSchema) {
      const result = config.formSchema.safeParse(formData);
      if (!result.success) {
        const fieldErrors: Record<string, string> = {};
        for (const issue of result.error.issues) {
          const key = issue.path[0] as string;
          if (!fieldErrors[key]) fieldErrors[key] = issue.message;
        }
        errors = fieldErrors;
        return;
      }
    }

    loading = true;
    errors = {};
    try {
      if (isEdit) {
        await api.patch(`${config.endpoint}${recordId}/`, formData);
        toast.success(`${config.label} updated`);
      } else {
        await api.post(config.endpoint, formData);
        toast.success(`${config.label} created`);
      }
      handleClose();
    } catch (e) {
      if (e instanceof ApiError && e.fieldErrors) {
        const mapped: Record<string, string> = {};
        for (const [k, v] of Object.entries(e.fieldErrors)) {
          mapped[k] = v[0];
        }
        errors = mapped;
      }
      toast.error(isEdit ? "Update failed" : "Create failed");
    } finally {
      loading = false;
    }
  }

  function handleClose() {
    if (onclose) {
      onclose();
    } else {
      goto(`/${$page.params.module}/${$page.params.resource}`);
    }
  }

  onMount(() => {
    if (recordId) {
      fetchRecord();
    } else {
      initDefaults();
    }
  });
</script>

<SlideOver {open} onclose={handleClose} title={isEdit ? `Edit ${config.label}` : `New ${config.label}`}>
  {#if fetching}
    <div class="flex items-center justify-center py-16">
      <div class="w-5 h-5 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div>
    </div>
  {:else}
    <form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }} class="space-y-6">
      {#if config.formSections}
        {#each config.formSections as section}
          <div>
            <h3 class="text-sm font-medium text-neutral-900 mb-3">{section.label}</h3>
            <div class="grid grid-cols-2 gap-4">
              {#each (config.formFields ?? []).filter((f) => f.section === section.key) as field}
                {#if !field.showIf || field.showIf(formData)}
                  <FieldRenderer
                    {field}
                    value={formData[field.key]}
                    error={errors[field.key]}
                    onchange={(v) => handleFieldChange(field.key, v)}
                  />
                {/if}
              {/each}
            </div>
          </div>
        {/each}
      {:else}
        <div class="grid grid-cols-2 gap-4">
          {#each config.formFields ?? [] as field}
            {#if !field.showIf || field.showIf(formData)}
              <FieldRenderer
                {field}
                value={formData[field.key]}
                error={errors[field.key]}
                onchange={(v) => handleFieldChange(field.key, v)}
              />
            {/if}
          {/each}
        </div>
      {/if}

      <div class="flex justify-end gap-3 pt-4 border-t border-neutral-100">
        <button
          type="button"
          onclick={handleClose}
          class="px-4 py-2 text-sm font-medium text-neutral-700 border border-neutral-200 rounded-lg hover:bg-neutral-50 transition-colors"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={loading}
          class="px-4 py-2 text-sm font-medium text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 disabled:opacity-50 transition-colors"
        >
          {loading ? "Saving..." : isEdit ? "Save Changes" : `Create ${config.label}`}
        </button>
      </div>
    </form>
  {/if}
</SlideOver>

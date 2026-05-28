<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    UserAccessibilityFontSize,
    UserAccessibilityPreferences,
  } from "$lib/types";

  let loading = $state(true);
  let saving = $state(false);
  let preferences = $state<UserAccessibilityPreferences | null>(null);

  function parseError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      const messages = Object.values(error.fieldErrors).flat();
      if (messages.length > 0) return messages[0];
      if (typeof error.data.detail === "string") return error.data.detail;
    }
    return fallback;
  }

  function previewTextClass(fontSize: UserAccessibilityFontSize): string {
    if (fontSize === "small") return "text-sm";
    if (fontSize === "large") return "text-lg";
    return "text-base";
  }

  async function loadPreferences() {
    loading = true;
    try {
      preferences = await api.get<UserAccessibilityPreferences>("/auth/accessibility-preferences/");
    } catch (error) {
      preferences = null;
      toast.error("Load failed", parseError(error, "Could not load accessibility preferences."));
    } finally {
      loading = false;
    }
  }

  async function savePreferences() {
    if (!preferences) return;
    saving = true;
    try {
      const updated = await api.patch<UserAccessibilityPreferences>("/auth/accessibility-preferences/", {
        font_size: preferences.font_size,
        high_contrast_mode: preferences.high_contrast_mode,
        reduced_motion: preferences.reduced_motion,
        screen_reader_support: preferences.screen_reader_support,
        keyboard_navigation: preferences.keyboard_navigation,
      });
      preferences = updated;
      toast.success("Updated", "Accessibility preferences have been saved.");
    } catch (error) {
      toast.error("Save failed", parseError(error, "Could not save accessibility preferences."));
    } finally {
      saving = false;
    }
  }

  $effect(() => {
    loadPreferences();
  });
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
  </div>
{:else if !preferences}
  <div class="rounded-xl border border-red-200 bg-red-50 p-6">
    <h2 class="text-base font-semibold text-red-900">Accessibility settings unavailable</h2>
    <p class="mt-1 text-sm text-red-700">Could not load your accessibility preferences.</p>
    <button
      onclick={() => loadPreferences()}
      class="mt-4 rounded-lg border border-red-300 bg-white px-3.5 py-2 text-sm font-medium text-red-800 hover:bg-red-100"
    >
      Retry
    </button>
  </div>
{:else}
  <div class="space-y-6">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-neutral-900">Accessibility</h1>
        <p class="mt-1 text-sm text-neutral-500">
          Configure readability and input behavior to improve usability across different needs.
        </p>
      </div>
      <button
        onclick={savePreferences}
        disabled={saving}
        class="rounded-lg bg-neutral-900 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {saving ? "Saving..." : "Save Changes"}
      </button>
    </div>

    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h2 class="mb-4 text-sm font-semibold text-neutral-900">Display</h2>

      <div class="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <div>
          <p class="mb-1.5 text-sm font-medium text-neutral-700">Font size</p>
          <div class="flex flex-wrap gap-2">
            {#each preferences.font_size_options as option}
              <button
                type="button"
                onclick={() => {
                  if (!preferences) return;
                  preferences.font_size = option.value;
                }}
                class="rounded-lg border px-3.5 py-2 text-sm font-medium transition-colors
                  {preferences.font_size === option.value
                    ? 'border-neutral-900 bg-neutral-900 text-white'
                    : 'border-neutral-300 bg-white text-neutral-700 hover:bg-neutral-50'}"
              >
                {option.label}
              </button>
            {/each}
          </div>
        </div>

        <div class="space-y-3">
          <label class="inline-flex items-center gap-2 text-sm text-neutral-700">
            <input
              type="checkbox"
              bind:checked={preferences.high_contrast_mode}
              class="rounded border-neutral-300"
            />
            High contrast mode
          </label>

          <label class="inline-flex items-center gap-2 text-sm text-neutral-700">
            <input
              type="checkbox"
              bind:checked={preferences.reduced_motion}
              class="rounded border-neutral-300"
            />
            Reduced motion
          </label>
        </div>
      </div>
    </section>

    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h2 class="mb-4 text-sm font-semibold text-neutral-900">Assistive support</h2>

      <div class="space-y-3">
        <label class="inline-flex items-center gap-2 text-sm text-neutral-700">
          <input
            type="checkbox"
            bind:checked={preferences.screen_reader_support}
            class="rounded border-neutral-300"
          />
          Screen reader support
        </label>

        <label class="inline-flex items-center gap-2 text-sm text-neutral-700">
          <input
            type="checkbox"
            bind:checked={preferences.keyboard_navigation}
            class="rounded border-neutral-300"
          />
          Keyboard navigation
        </label>
      </div>
    </section>

    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h2 class="mb-3 text-sm font-semibold text-neutral-900">Preview</h2>
      <div
        class="rounded-lg border px-4 py-3
          {preferences.high_contrast_mode
            ? 'border-neutral-900 bg-neutral-900 text-white'
            : 'border-neutral-200 bg-neutral-50 text-neutral-800'}"
      >
        <p class={`font-medium ${previewTextClass(preferences.font_size)}`}>Accessibility preview text</p>
        <p class={`mt-1 ${previewTextClass(preferences.font_size)}`}>
          High contrast, font scale, motion preference, and assistive controls are configured here.
        </p>
      </div>
      <p class="mt-2 text-xs text-neutral-500">
        Reduced motion and assistive options are stored at profile level for future app-wide behavior.
      </p>
    </section>
  </div>
{/if}

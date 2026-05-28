<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    UserWorkspaceDensity,
    UserWorkspacePreferences,
    UserWorkspaceSidebarBehavior,
    UserWorkspaceTheme,
  } from "$lib/types";

  let loading = $state(true);
  let saving = $state(false);
  let preferences = $state<UserWorkspacePreferences | null>(null);

  function parseError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      const messages = Object.values(error.fieldErrors).flat();
      if (messages.length > 0) return messages[0];
      if (typeof error.data.detail === "string") return error.data.detail;
    }
    return fallback;
  }

  async function loadPreferences() {
    loading = true;
    try {
      preferences = await api.get<UserWorkspacePreferences>("/auth/workspace-preferences/");
    } catch (error) {
      preferences = null;
      toast.error("Load failed", parseError(error, "Could not load workspace preferences."));
    } finally {
      loading = false;
    }
  }

  function moveWidget(fromIndex: number, direction: -1 | 1) {
    if (!preferences) return;
    const toIndex = fromIndex + direction;
    if (toIndex < 0 || toIndex >= preferences.widgets.length) return;

    const next = [...preferences.widgets];
    const [moved] = next.splice(fromIndex, 1);
    next.splice(toIndex, 0, moved);
    preferences.widgets = next;
  }

  async function savePreferences() {
    if (!preferences) return;
    saving = true;
    try {
      const updated = await api.patch<UserWorkspacePreferences>("/auth/workspace-preferences/", {
        theme: preferences.theme,
        layout_density: preferences.layout_density,
        sidebar_behavior: preferences.sidebar_behavior,
        default_landing_page: preferences.default_landing_page,
        default_dashboard: preferences.default_dashboard,
        widgets: preferences.widgets.map((widget) => ({
          key: widget.key,
          visible: widget.visible,
        })),
      });
      preferences = updated;
      toast.success("Updated", "Workspace preferences have been saved.");
    } catch (error) {
      toast.error("Save failed", parseError(error, "Could not save workspace preferences."));
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
    <h2 class="text-base font-semibold text-red-900">Workspace preferences unavailable</h2>
    <p class="mt-1 text-sm text-red-700">Could not load your workspace preferences.</p>
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
        <h1 class="text-2xl font-bold text-neutral-900">Workspace Preferences</h1>
        <p class="mt-1 text-sm text-neutral-500">
          Personalize how your workspace looks and what dashboard blocks are shown by default.
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
      <h2 class="text-sm font-semibold text-neutral-900 mb-4">Interface</h2>

      <div class="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <div>
          <p class="mb-1.5 text-sm font-medium text-neutral-700">Theme</p>
          <div class="flex flex-wrap gap-2">
            {#each preferences.theme_options as option}
              <button
                type="button"
                onclick={() => {
                  if (!preferences) return;
                  preferences.theme = option.value as UserWorkspaceTheme;
                }}
                class="rounded-lg border px-3.5 py-2 text-sm font-medium transition-colors
                  {preferences.theme === option.value
                    ? 'border-neutral-900 bg-neutral-900 text-white'
                    : 'border-neutral-300 bg-white text-neutral-700 hover:bg-neutral-50'}"
              >
                {option.label}
              </button>
            {/each}
          </div>
        </div>

        <div>
          <p class="mb-1.5 text-sm font-medium text-neutral-700">Layout density</p>
          <div class="flex flex-wrap gap-2">
            {#each preferences.layout_density_options as option}
              <button
                type="button"
                onclick={() => {
                  if (!preferences) return;
                  preferences.layout_density = option.value as UserWorkspaceDensity;
                }}
                class="rounded-lg border px-3.5 py-2 text-sm font-medium transition-colors
                  {preferences.layout_density === option.value
                    ? 'border-neutral-900 bg-neutral-900 text-white'
                    : 'border-neutral-300 bg-white text-neutral-700 hover:bg-neutral-50'}"
              >
                {option.label}
              </button>
            {/each}
          </div>
        </div>

        <div>
          <p class="mb-1.5 text-sm font-medium text-neutral-700">Sidebar behavior</p>
          <div class="flex flex-wrap gap-2">
            {#each preferences.sidebar_behavior_options as option}
              <button
                type="button"
                onclick={() => {
                  if (!preferences) return;
                  preferences.sidebar_behavior = option.value as UserWorkspaceSidebarBehavior;
                }}
                class="rounded-lg border px-3.5 py-2 text-sm font-medium transition-colors
                  {preferences.sidebar_behavior === option.value
                    ? 'border-neutral-900 bg-neutral-900 text-white'
                    : 'border-neutral-300 bg-white text-neutral-700 hover:bg-neutral-50'}"
              >
                {option.label}
              </button>
            {/each}
          </div>
        </div>

        <div>
          <label for="default_landing_page" class="mb-1.5 block text-sm font-medium text-neutral-700">Default landing page</label>
          <select
            id="default_landing_page"
            bind:value={preferences.default_landing_page}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            {#each preferences.landing_page_options as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </div>
      </div>
    </section>

    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h2 class="text-sm font-semibold text-neutral-900 mb-4">Dashboard Preferences</h2>

      <div class="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <div>
          <label for="default_dashboard" class="mb-1.5 block text-sm font-medium text-neutral-700">Default dashboard</label>
          <select
            id="default_dashboard"
            bind:value={preferences.default_dashboard}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            {#each preferences.dashboard_options as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </div>
      </div>

      <div class="mt-5">
        <h3 class="text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-3">Dashboard widgets</h3>
        <div class="space-y-2">
          {#each preferences.widgets as widget, index (widget.key)}
            <article class="rounded-lg border border-neutral-200 bg-neutral-50 px-4 py-3">
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <p class="text-sm font-semibold text-neutral-900">{widget.label}</p>
                  <p class="mt-1 text-xs text-neutral-500">{widget.description}</p>
                </div>

                <div class="flex shrink-0 items-center gap-2">
                  <label class="inline-flex items-center gap-2 text-xs text-neutral-700">
                    <input
                      type="checkbox"
                      bind:checked={widget.visible}
                      class="rounded border-neutral-300"
                    />
                    Visible
                  </label>

                  <button
                    type="button"
                    onclick={() => moveWidget(index, -1)}
                    disabled={index === 0}
                    aria-label={`Move ${widget.label} up`}
                    title="Move up"
                    class="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-neutral-300 bg-white text-neutral-700 transition-colors hover:bg-neutral-100 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="m18 15-6-6-6 6" />
                    </svg>
                  </button>

                  <button
                    type="button"
                    onclick={() => moveWidget(index, 1)}
                    disabled={index === preferences.widgets.length - 1}
                    aria-label={`Move ${widget.label} down`}
                    title="Move down"
                    class="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-neutral-300 bg-white text-neutral-700 transition-colors hover:bg-neutral-100 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="m6 9 6 6 6-6" />
                    </svg>
                  </button>
                </div>
              </div>
            </article>
          {/each}
        </div>
      </div>
    </section>
  </div>
{/if}

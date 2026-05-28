<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    UserDataExportFormat,
    UserDataExportPreferences,
    UserDataSavedView,
  } from "$lib/types";

  type FilterEntry = { key: string; value: string };
  type ColumnVisibilityEntry = { key: string; visible: boolean };

  let loading = $state(true);
  let saving = $state(false);
  let preferences = $state<UserDataExportPreferences | null>(null);

  let filterEntries = $state<FilterEntry[]>([]);
  let columnVisibilityEntries = $state<ColumnVisibilityEntry[]>([]);
  let newSavedViewName = $state("");

  function parseError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      const messages = Object.values(error.fieldErrors).flat();
      if (messages.length > 0) return messages[0];
      if (typeof error.data.detail === "string") return error.data.detail;
    }
    return fallback;
  }

  function syncEntriesFromPreferences(data: UserDataExportPreferences) {
    filterEntries = Object.entries(data.default_report_filters ?? {})
      .map(([key, value]) => ({
        key,
        value: typeof value === "string" ? value : JSON.stringify(value),
      }))
      .filter((row) => row.key.trim().length > 0);

    columnVisibilityEntries = Object.entries(data.column_visibility ?? {})
      .map(([key, value]) => ({
        key,
        visible: Boolean(value),
      }))
      .filter((row) => row.key.trim().length > 0);
  }

  function buildReportFilters(): Record<string, string> {
    const next: Record<string, string> = {};
    for (const row of filterEntries) {
      const key = row.key.trim();
      if (!key) continue;
      next[key] = row.value.trim();
    }
    return next;
  }

  function buildColumnVisibility(): Record<string, boolean> {
    const next: Record<string, boolean> = {};
    for (const row of columnVisibilityEntries) {
      const key = row.key.trim();
      if (!key) continue;
      next[key] = Boolean(row.visible);
    }
    return next;
  }

  function addFilterEntry() {
    filterEntries = [...filterEntries, { key: "", value: "" }];
  }

  function removeFilterEntry(index: number) {
    filterEntries = filterEntries.filter((_row, idx) => idx !== index);
  }

  function addColumnVisibilityEntry() {
    columnVisibilityEntries = [...columnVisibilityEntries, { key: "", visible: true }];
  }

  function removeColumnVisibilityEntry(index: number) {
    columnVisibilityEntries = columnVisibilityEntries.filter((_row, idx) => idx !== index);
  }

  function addSavedViewFromCurrent() {
    if (!preferences) return;
    const name = newSavedViewName.trim();
    if (!name) {
      toast.error("Missing name", "Enter a name for the saved view.");
      return;
    }
    const duplicate = preferences.saved_views.some((row) => row.name.toLowerCase() === name.toLowerCase());
    if (duplicate) {
      toast.error("Duplicate name", "A saved view with this name already exists.");
      return;
    }

    const view: UserDataSavedView = {
      id: `view_${Date.now()}`,
      name,
      filters: buildReportFilters(),
      column_visibility: buildColumnVisibility(),
      rows_per_page: Number(preferences.rows_per_page),
    };
    preferences.saved_views = [...preferences.saved_views, view];
    newSavedViewName = "";
  }

  function applySavedView(view: UserDataSavedView) {
    if (!preferences) return;
    filterEntries = Object.entries(view.filters ?? {}).map(([key, value]) => ({
      key,
      value: typeof value === "string" ? value : JSON.stringify(value),
    }));
    columnVisibilityEntries = Object.entries(view.column_visibility ?? {}).map(([key, value]) => ({
      key,
      visible: Boolean(value),
    }));
    if (typeof view.rows_per_page === "number") {
      preferences.rows_per_page = view.rows_per_page;
    }
    toast.success("Applied", `Saved view "${view.name}" has been applied.`);
  }

  function removeSavedView(index: number) {
    if (!preferences) return;
    preferences.saved_views = preferences.saved_views.filter((_row, idx) => idx !== index);
  }

  async function loadPreferences() {
    loading = true;
    try {
      const data = await api.get<UserDataExportPreferences>("/auth/data-export-preferences/");
      preferences = data;
      syncEntriesFromPreferences(data);
    } catch (error) {
      preferences = null;
      filterEntries = [];
      columnVisibilityEntries = [];
      toast.error("Load failed", parseError(error, "Could not load data and export preferences."));
    } finally {
      loading = false;
    }
  }

  async function savePreferences() {
    if (!preferences) return;
    saving = true;
    try {
      const updated = await api.patch<UserDataExportPreferences>("/auth/data-export-preferences/", {
        default_export_format: preferences.default_export_format,
        default_report_filters: buildReportFilters(),
        rows_per_page: Number(preferences.rows_per_page),
        column_visibility: buildColumnVisibility(),
        saved_views: preferences.saved_views,
      });
      preferences = updated;
      syncEntriesFromPreferences(updated);
      toast.success("Updated", "Data and export preferences have been saved.");
    } catch (error) {
      toast.error("Save failed", parseError(error, "Could not save data and export preferences."));
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
    <h2 class="text-base font-semibold text-red-900">Data preferences unavailable</h2>
    <p class="mt-1 text-sm text-red-700">Could not load your data and export preferences.</p>
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
        <h1 class="text-2xl font-bold text-neutral-900">Data & Export Preferences</h1>
        <p class="mt-1 text-sm text-neutral-500">
          Configure your default export behavior, report filters, table settings, and reusable saved views.
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
      <h2 class="text-sm font-semibold text-neutral-900 mb-4">Default export format</h2>
      <div class="flex flex-wrap gap-2">
        {#each preferences.export_format_options as option}
          <button
            type="button"
            onclick={() => {
              if (!preferences) return;
              preferences.default_export_format = option.value as UserDataExportFormat;
            }}
            class="rounded-lg border px-3.5 py-2 text-sm font-medium transition-colors
              {preferences.default_export_format === option.value
                ? 'border-neutral-900 bg-neutral-900 text-white'
                : 'border-neutral-300 bg-white text-neutral-700 hover:bg-neutral-50'}"
          >
            {option.label}
          </button>
        {/each}
      </div>
    </section>

    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <div class="mb-4 flex items-center justify-between gap-3">
        <h2 class="text-sm font-semibold text-neutral-900">Default report filters</h2>
        <button
          type="button"
          onclick={addFilterEntry}
          class="rounded-lg border border-neutral-300 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-50"
        >
          Add Filter
        </button>
      </div>
      <div class="space-y-2">
        {#if filterEntries.length === 0}
          <p class="text-sm text-neutral-500">No default report filters configured.</p>
        {:else}
          {#each filterEntries as row, index (index)}
            <div class="grid grid-cols-1 gap-2 md:grid-cols-[1fr_1fr_auto]">
              <input
                type="text"
                bind:value={row.key}
                placeholder="Filter key (e.g. project_status)"
                class="rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
              />
              <input
                type="text"
                bind:value={row.value}
                placeholder="Filter value"
                class="rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
              />
              <button
                type="button"
                onclick={() => removeFilterEntry(index)}
                class="rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700 hover:bg-red-100"
              >
                Remove
              </button>
            </div>
          {/each}
        {/if}
      </div>
    </section>

    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <div class="mb-4 flex items-center justify-between gap-3">
        <h2 class="text-sm font-semibold text-neutral-900">Table display preferences</h2>
        <button
          type="button"
          onclick={addColumnVisibilityEntry}
          class="rounded-lg border border-neutral-300 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-50"
        >
          Add Column
        </button>
      </div>

      <div class="mb-4 max-w-xs">
        <label for="rows_per_page" class="mb-1.5 block text-sm font-medium text-neutral-700">Rows per page</label>
        <select
          id="rows_per_page"
          bind:value={preferences.rows_per_page}
          class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        >
          {#each preferences.rows_per_page_options as value}
            <option value={value}>{value}</option>
          {/each}
        </select>
      </div>

      <div class="space-y-2">
        {#if columnVisibilityEntries.length === 0}
          <p class="text-sm text-neutral-500">No column visibility overrides configured.</p>
        {:else}
          {#each columnVisibilityEntries as row, index (index)}
            <div class="grid grid-cols-1 gap-2 md:grid-cols-[1fr_auto_auto] md:items-center">
              <input
                type="text"
                bind:value={row.key}
                placeholder="Column key (e.g. owner_name)"
                class="rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
              />
              <label class="inline-flex items-center gap-2 text-sm text-neutral-700">
                <input
                  type="checkbox"
                  bind:checked={row.visible}
                  class="rounded border-neutral-300"
                />
                Visible
              </label>
              <button
                type="button"
                onclick={() => removeColumnVisibilityEntry(index)}
                class="rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-xs font-semibold text-red-700 hover:bg-red-100"
              >
                Remove
              </button>
            </div>
          {/each}
        {/if}
      </div>
    </section>

    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <div class="mb-4 flex items-center justify-between gap-3">
        <h2 class="text-sm font-semibold text-neutral-900">Saved views</h2>
      </div>

      <div class="mb-4 grid grid-cols-1 gap-2 md:grid-cols-[1fr_auto]">
        <input
          type="text"
          bind:value={newSavedViewName}
          placeholder="New saved view name"
          class="rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        />
        <button
          type="button"
          onclick={addSavedViewFromCurrent}
          class="rounded-lg border border-neutral-900 bg-neutral-900 px-3.5 py-2 text-sm font-semibold text-white hover:bg-neutral-800"
        >
          Save Current View
        </button>
      </div>

      <div class="space-y-2">
        {#if preferences.saved_views.length === 0}
          <p class="text-sm text-neutral-500">No saved views yet.</p>
        {:else}
          {#each preferences.saved_views as view, index (view.id || `${view.name}-${index}`)}
            <div class="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2">
              <div class="min-w-0">
                <p class="truncate text-sm font-medium text-neutral-900">{view.name}</p>
                <p class="text-xs text-neutral-500">
                  Rows: {view.rows_per_page ?? preferences.rows_per_page} · Filters: {Object.keys(view.filters ?? {}).length} · Columns: {Object.keys(view.column_visibility ?? {}).length}
                </p>
              </div>
              <div class="flex items-center gap-2">
                <button
                  type="button"
                  onclick={() => applySavedView(view)}
                  class="rounded-lg border border-neutral-300 bg-white px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:bg-neutral-100"
                >
                  Apply
                </button>
                <button
                  type="button"
                  onclick={() => removeSavedView(index)}
                  class="rounded-lg border border-red-300 bg-red-50 px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-100"
                >
                  Remove
                </button>
              </div>
            </div>
          {/each}
        {/if}
      </div>
    </section>
  </div>
{/if}

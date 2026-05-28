<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { UserPrivacyVisibilitySettings } from "$lib/types";

  let loading = $state(true);
  let saving = $state(false);
  let settings = $state<UserPrivacyVisibilitySettings | null>(null);

  function parseError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      const messages = Object.values(error.fieldErrors).flat();
      if (messages.length > 0) return messages[0];
      if (typeof error.data.detail === "string") return error.data.detail;
    }
    return fallback;
  }

  async function loadSettings() {
    loading = true;
    try {
      settings = await api.get<UserPrivacyVisibilitySettings>("/auth/privacy-visibility/");
    } catch (error) {
      settings = null;
      toast.error("Load failed", parseError(error, "Could not load privacy settings."));
    } finally {
      loading = false;
    }
  }

  async function saveSettings() {
    if (!settings) return;
    saving = true;
    try {
      const updated = await api.patch<UserPrivacyVisibilitySettings>("/auth/privacy-visibility/", {
        profile_visibility: settings.profile_visibility,
        email_visibility: settings.email_visibility,
        phone_visibility: settings.phone_visibility,
        activity_visibility: settings.activity_visibility,
        online_status_visibility: settings.online_status_visibility,
        search_discoverable: settings.search_discoverable,
      });
      settings = updated;
      toast.success("Updated", "Privacy and visibility settings have been saved.");
    } catch (error) {
      toast.error("Save failed", parseError(error, "Could not save privacy settings."));
    } finally {
      saving = false;
    }
  }

  $effect(() => {
    loadSettings();
  });
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
  </div>
{:else if !settings}
  <div class="rounded-xl border border-red-200 bg-red-50 p-6">
    <h2 class="text-base font-semibold text-red-900">Privacy settings unavailable</h2>
    <p class="mt-1 text-sm text-red-700">Could not load your privacy and visibility settings.</p>
    <button
      onclick={() => loadSettings()}
      class="mt-4 rounded-lg border border-red-300 bg-white px-3.5 py-2 text-sm font-medium text-red-800 hover:bg-red-100"
    >
      Retry
    </button>
  </div>
{:else}
  <div class="space-y-6">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-neutral-900">Privacy & Visibility</h1>
        <p class="mt-1 text-sm text-neutral-500">
          Control how your profile and activity are visible to others in the system.
        </p>
      </div>
      <button
        onclick={saveSettings}
        disabled={saving}
        class="rounded-lg bg-neutral-900 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {saving ? "Saving..." : "Save Changes"}
      </button>
    </div>

    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h2 class="text-sm font-semibold text-neutral-900 mb-4">Profile visibility</h2>
      <div class="max-w-sm">
        <label for="profile_visibility" class="mb-1.5 block text-sm font-medium text-neutral-700">Who can see your profile</label>
        <select
          id="profile_visibility"
          bind:value={settings.profile_visibility}
          class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
        >
          {#each settings.visibility_options as option}
            <option value={option.value}>{option.label}</option>
          {/each}
        </select>
      </div>
    </section>

    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h2 class="text-sm font-semibold text-neutral-900 mb-4">Contact visibility</h2>
      <div class="grid grid-cols-1 gap-5 md:grid-cols-2">
        <div>
          <label for="email_visibility" class="mb-1.5 block text-sm font-medium text-neutral-700">Who can view email</label>
          <select
            id="email_visibility"
            bind:value={settings.email_visibility}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            {#each settings.visibility_options as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </div>

        <div>
          <label for="phone_visibility" class="mb-1.5 block text-sm font-medium text-neutral-700">Who can view phone</label>
          <select
            id="phone_visibility"
            bind:value={settings.phone_visibility}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            {#each settings.visibility_options as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </div>
      </div>
    </section>

    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h2 class="text-sm font-semibold text-neutral-900 mb-4">Activity & discoverability</h2>
      <div class="grid grid-cols-1 gap-5 md:grid-cols-2">
        <div>
          <label for="activity_visibility" class="mb-1.5 block text-sm font-medium text-neutral-700">Activity visibility</label>
          <select
            id="activity_visibility"
            bind:value={settings.activity_visibility}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            {#each settings.visibility_options as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </div>

        <div>
          <label for="online_status_visibility" class="mb-1.5 block text-sm font-medium text-neutral-700">Online status visibility</label>
          <select
            id="online_status_visibility"
            bind:value={settings.online_status_visibility}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            {#each settings.visibility_options as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </div>

        <div class="md:col-span-2">
          <label class="inline-flex items-center gap-2 text-sm text-neutral-700">
            <input
              type="checkbox"
              bind:checked={settings.search_discoverable}
              class="rounded border-neutral-300"
            />
            Allow search discoverability
          </label>
        </div>
      </div>
    </section>
  </div>
{/if}

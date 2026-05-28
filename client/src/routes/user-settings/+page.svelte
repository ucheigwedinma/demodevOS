<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { onboarding } from "$lib/stores/onboarding.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import type { UserProfilePhotoResponse, UserSettingsProfile } from "$lib/types";

  let loading = $state(true);
  let saving = $state(false);
  let uploadingPhoto = $state(false);
  let photoInput = $state<HTMLInputElement | null>(null);
  let profile = $state<UserSettingsProfile | null>(null);
  let form = $state<UserSettingsProfile | null>(null);

  function initials(value: string): string {
    return value
      .split(" ")
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() ?? "")
      .join("") || "?";
  }

  function parseApiError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      const messages = Object.values(error.fieldErrors).flat();
      if (messages.length > 0) return messages[0];
      if (typeof error.data.detail === "string") return error.data.detail;
    }
    return fallback;
  }

  function syncOnboarding(next: UserSettingsProfile) {
    if (!onboarding.user) return;
    onboarding.user.full_name = next.full_name;
    onboarding.user.display_name = next.display_name;
    onboarding.user.profile_photo_url = next.profile_photo_url;
  }

  async function loadProfile() {
    loading = true;
    try {
      const data = await api.get<UserSettingsProfile>("/auth/profile/");
      profile = data;
      form = { ...data };
      syncOnboarding(data);
    } catch (error) {
      toast.error("Load failed", parseApiError(error, "Could not load your profile settings."));
      profile = null;
      form = null;
    } finally {
      loading = false;
    }
  }

  async function handleSave() {
    if (!form) return;

    saving = true;
    try {
      const payload = {
        full_name: form.full_name.trim(),
        preferred_display_name: form.preferred_display_name.trim(),
        job_title: form.job_title.trim(),
        department_id: form.department_id,
        business_unit: form.business_unit.trim(),
        employee_id: form.employee_id.trim(),
        bio: form.bio,
        email: form.email.trim().toLowerCase(),
        phone: form.phone.trim(),
        secondary_phone: form.secondary_phone.trim(),
        office_location: form.office_location.trim(),
        timezone: form.timezone.trim(),
        profile_visibility: form.profile_visibility,
        approval_signature: form.approval_signature,
        default_language: form.default_language.trim().toLowerCase(),
      };
      const updated = await api.patch<UserSettingsProfile>("/auth/profile/", payload);
      profile = updated;
      form = { ...updated };
      syncOnboarding(updated);
      toast.success("Profile saved", "Your profile settings have been updated.");
    } catch (error) {
      toast.error("Save failed", parseApiError(error, "Could not save your profile settings."));
    } finally {
      saving = false;
    }
  }

  async function uploadProfilePhoto(file: File) {
    if (!form) return;
    const payload = new FormData();
    payload.append("photo", file);

    uploadingPhoto = true;
    try {
      const response = await api.upload<UserProfilePhotoResponse>("/auth/profile/photo/", payload);
      form.profile_photo_url = response.profile_photo_url;
      if (profile) {
        profile.profile_photo_url = response.profile_photo_url;
      }
      if (onboarding.user) {
        onboarding.user.profile_photo_url = response.profile_photo_url;
      }
      toast.success("Photo updated", "Profile photo was uploaded successfully.");
    } catch (error) {
      toast.error("Upload failed", parseApiError(error, "Could not upload profile photo."));
    } finally {
      uploadingPhoto = false;
      if (photoInput) {
        photoInput.value = "";
      }
    }
  }

  async function removeProfilePhoto() {
    if (!form) return;
    uploadingPhoto = true;
    try {
      const response = await api.delete<UserProfilePhotoResponse>("/auth/profile/photo/");
      form.profile_photo_url = response.profile_photo_url;
      if (profile) {
        profile.profile_photo_url = response.profile_photo_url;
      }
      if (onboarding.user) {
        onboarding.user.profile_photo_url = response.profile_photo_url;
      }
      toast.success("Photo removed", "Profile photo has been removed.");
    } catch (error) {
      toast.error("Remove failed", parseApiError(error, "Could not remove profile photo."));
    } finally {
      uploadingPhoto = false;
      if (photoInput) {
        photoInput.value = "";
      }
    }
  }

  function openPhotoPicker() {
    if (uploadingPhoto) return;
    photoInput?.click();
  }

  function handlePhotoSelected(event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    void uploadProfilePhoto(file);
  }

  $effect(() => {
    loadProfile();
  });

  const avatarLabel = $derived(
    (form?.preferred_display_name || form?.full_name || form?.email || "").trim()
  );

  const timezoneOptions = $derived.by(() => {
    if (!form) return [];
    if (form.timezone_options?.length > 0) return form.timezone_options;

    const browserTimezone =
      typeof Intl !== "undefined" ? Intl.DateTimeFormat().resolvedOptions().timeZone : "";

    return Array.from(new Set([form.timezone, browserTimezone].filter(Boolean)));
  });

  const profileVisibilityOptions = $derived.by(() => {
    if (!form) return [];
    if (form.profile_visibility_options?.length > 0) return form.profile_visibility_options;
    return [{ value: form.profile_visibility, label: form.profile_visibility }];
  });

  const languageOptions = $derived.by(() => {
    if (!form) return [];
    if (form.language_options?.length > 0) return form.language_options;
    return [{ value: form.default_language, label: form.default_language }];
  });
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
  </div>
{:else if !form}
  <div class="rounded-xl border border-red-200 bg-red-50 p-6">
    <h2 class="text-base font-semibold text-red-900">Profile unavailable</h2>
    <p class="mt-1 text-sm text-red-700">We could not load your user settings profile.</p>
    <button
      onclick={() => loadProfile()}
      class="mt-4 rounded-lg border border-red-300 bg-white px-3.5 py-2 text-sm font-medium text-red-800 hover:bg-red-100"
    >
      Retry
    </button>
  </div>
{:else}
  <div class="space-y-6">
    <section class="overflow-hidden rounded-2xl border border-neutral-200 bg-white shadow-sm">
      <div class="relative h-48 w-full">
        <img
          src="https://v3.material-tailwind.com/dark-bg-pattern.jpg"
          alt="Profile background"
          class="absolute inset-0 h-full w-full object-cover object-center"
        />
        <div class="absolute inset-0 bg-linear-to-r from-neutral-950/70 via-neutral-900/50 to-neutral-900/20"></div>
        <div class="absolute inset-x-0 bottom-0 p-6">
          <p class="text-[11px] font-semibold uppercase tracking-[0.24em] text-white/80">User Profile</p>
          <p class="mt-1 text-sm text-white/85">
            Basic identity, professional details, contact details, and personal preferences.
          </p>
        </div>
      </div>

      <div class="p-6">
        <div class="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div class="flex min-w-0 items-center gap-4">
            <div class="flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-full border-4 border-white bg-neutral-100 text-lg font-semibold text-neutral-700 shadow-md">
              {#if form.profile_photo_url}
                <img src={form.profile_photo_url} alt={avatarLabel || "User avatar"} class="h-full w-full object-cover" />
              {:else}
                <span>{initials(avatarLabel || "User")}</span>
              {/if}
            </div>
            <div class="min-w-0">
              <h1 class="truncate text-2xl font-semibold text-neutral-900">{avatarLabel || "User"}</h1>
              <p class="truncate text-sm text-neutral-500">{form.email}</p>
              {#if form.job_title || form.department_name}
                <p class="mt-1 truncate text-xs text-neutral-500">
                  {form.job_title}{form.job_title && form.department_name ? " • " : ""}{form.department_name}
                </p>
              {/if}
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-2">
            <a
              href={form.email ? `mailto:${form.email}` : "/user-settings"}
              class="inline-flex items-center rounded-lg border border-neutral-200 px-3 py-1.5 text-xs font-semibold text-neutral-700 transition-colors hover:bg-neutral-50"
            >
              <svg class="mr-1.5 h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8">
                <path stroke-linecap="round" stroke-linejoin="round" d="M21.75 7.5v9A2.25 2.25 0 0 1 19.5 18.75h-15A2.25 2.25 0 0 1 2.25 16.5v-9m19.5 0A2.25 2.25 0 0 0 19.5 5.25h-15A2.25 2.25 0 0 0 2.25 7.5m19.5 0v.243a2.25 2.25 0 0 1-1.07 1.916l-7.5 4.615a2.25 2.25 0 0 1-2.36 0l-7.5-4.615a2.25 2.25 0 0 1-1.07-1.916V7.5" />
              </svg>
              Email
            </a>

            <button
              type="button"
              onclick={openPhotoPicker}
              disabled={uploadingPhoto}
              class="inline-flex items-center rounded-lg border border-neutral-200 px-3 py-1.5 text-xs font-semibold text-neutral-700 transition-colors hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <svg class="mr-1.5 h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.8">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6.75 7.5h2.25l1.5-2.25h3l1.5 2.25h2.25A2.25 2.25 0 0 1 19.5 9.75v7.5a2.25 2.25 0 0 1-2.25 2.25H6.75a2.25 2.25 0 0 1-2.25-2.25v-7.5A2.25 2.25 0 0 1 6.75 7.5Z" />
                <circle cx="12" cy="13.125" r="3.375"></circle>
              </svg>
              {uploadingPhoto ? "Uploading..." : "Upload photo"}
            </button>

            {#if form.profile_photo_url}
              <button
                type="button"
                onclick={() => removeProfilePhoto()}
                disabled={uploadingPhoto}
                class="inline-flex items-center rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-semibold text-red-700 transition-colors hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Remove photo
              </button>
            {/if}

            <button
              type="button"
              onclick={handleSave}
              disabled={saving}
              class="inline-flex items-center rounded-lg bg-neutral-900 px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {saving ? "Saving..." : "Save changes"}
            </button>
          </div>
        </div>
      </div>

      <div class="border-t border-neutral-200 bg-neutral-50 px-6 py-5">
        <p class="max-w-3xl text-sm leading-relaxed text-neutral-600">
          {form.bio?.trim() || "Add your bio to introduce your role, expertise, and what you are working on."}
        </p>
      </div>

      <input
        type="file"
        accept="image/*"
        bind:this={photoInput}
        onchange={handlePhotoSelected}
        class="hidden"
      />
    </section>

    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h2 class="text-sm font-semibold text-neutral-900 mb-5">Basic identity and professional information</h2>
      <div class="grid grid-cols-1 gap-5 md:grid-cols-2">
        <div>
          <label for="full_name" class="block text-sm font-medium text-neutral-700 mb-1.5">Full name</label>
          <input
            id="full_name"
            type="text"
            bind:value={form.full_name}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
          />
        </div>

        <div>
          <label for="preferred_display_name" class="block text-sm font-medium text-neutral-700 mb-1.5">Preferred display name</label>
          <input
            id="preferred_display_name"
            type="text"
            bind:value={form.preferred_display_name}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
          />
        </div>

        <div>
          <label for="job_title" class="block text-sm font-medium text-neutral-700 mb-1.5">Job title</label>
          <input
            id="job_title"
            type="text"
            bind:value={form.job_title}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
          />
        </div>

        <div>
          <label for="department_id" class="block text-sm font-medium text-neutral-700 mb-1.5">Department</label>
          <select
            id="department_id"
            value={form.department_id === null ? "" : String(form.department_id)}
            onchange={(event) => {
              if (!form) return;
              const value = (event.target as HTMLSelectElement).value;
              form.department_id = value ? Number(value) : null;
            }}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
          >
            <option value="">Not assigned</option>
            {#each form.department_options as option}
              <option value={option.id}>{option.name} {option.division_name ? `(${option.division_name})` : ""}</option>
            {/each}
          </select>
        </div>

        <div>
          <label for="organization_name" class="block text-sm font-medium text-neutral-700 mb-1.5">Organization</label>
          <input
            id="organization_name"
            type="text"
            value={form.organization_name || "Not assigned"}
            disabled
            class="w-full rounded-lg border border-neutral-200 bg-neutral-100 px-3.5 py-2.5 text-sm text-neutral-600"
          />
        </div>

        <div>
          <label for="business_unit" class="block text-sm font-medium text-neutral-700 mb-1.5">Business unit</label>
          <input
            id="business_unit"
            type="text"
            bind:value={form.business_unit}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
          />
        </div>

        <div>
          <label for="employee_id" class="block text-sm font-medium text-neutral-700 mb-1.5">Employee ID</label>
          <input
            id="employee_id"
            type="text"
            bind:value={form.employee_id}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
          />
        </div>

        <div class="md:col-span-2">
          <label for="bio" class="block text-sm font-medium text-neutral-700 mb-1.5">Bio / About</label>
          <textarea
            id="bio"
            rows="4"
            bind:value={form.bio}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
          ></textarea>
        </div>
      </div>
    </section>

    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h2 class="text-sm font-semibold text-neutral-900 mb-5">Contact details</h2>
      <div class="grid grid-cols-1 gap-5 md:grid-cols-2">
        <div>
          <label for="email" class="block text-sm font-medium text-neutral-700 mb-1.5">Email</label>
          <input
            id="email"
            type="email"
            bind:value={form.email}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
          />
        </div>

        <div>
          <label for="phone" class="block text-sm font-medium text-neutral-700 mb-1.5">Phone</label>
          <input
            id="phone"
            type="text"
            bind:value={form.phone}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
          />
        </div>

        <div>
          <label for="secondary_phone" class="block text-sm font-medium text-neutral-700 mb-1.5">Secondary phone</label>
          <input
            id="secondary_phone"
            type="text"
            bind:value={form.secondary_phone}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
          />
        </div>

        <div>
          <label for="office_location" class="block text-sm font-medium text-neutral-700 mb-1.5">Office location</label>
          <input
            id="office_location"
            type="text"
            bind:value={form.office_location}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
          />
        </div>

        <div>
          <label for="timezone" class="block text-sm font-medium text-neutral-700 mb-1.5">Timezone</label>
          <input
            id="timezone"
            list="timezone-options"
            bind:value={form.timezone}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
          />
          <datalist id="timezone-options">
            {#each timezoneOptions as tz}
              <option value={tz}></option>
            {/each}
          </datalist>
        </div>
      </div>
    </section>

    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h2 class="text-sm font-semibold text-neutral-900 mb-5">Advanced options</h2>
      <div class="grid grid-cols-1 gap-5 md:grid-cols-2">
        <div>
          <label for="profile_visibility" class="block text-sm font-medium text-neutral-700 mb-1.5">Profile visibility</label>
          <select
            id="profile_visibility"
            bind:value={form.profile_visibility}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
          >
            {#each profileVisibilityOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </div>

        <div>
          <label for="default_language" class="block text-sm font-medium text-neutral-700 mb-1.5">Default language</label>
          <select
            id="default_language"
            bind:value={form.default_language}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
          >
            {#each languageOptions as option}
              <option value={option.value}>{option.label}</option>
            {/each}
          </select>
        </div>

        <div class="md:col-span-2">
          <label for="approval_signature" class="block text-sm font-medium text-neutral-700 mb-1.5">Signature for approvals/comments</label>
          <textarea
            id="approval_signature"
            rows="3"
            bind:value={form.approval_signature}
            class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
            placeholder="For example: Jane Doe, Finance Manager"
          ></textarea>
        </div>
      </div>
    </section>
  </div>
{/if}

<script lang="ts">
  import { api } from "$lib/api";
  import { parsePortalError } from "$lib/partnerPortal";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    PartnerPortalContextResponse,
    PartnerPortalProfilePhotoResponse,
    PartnerPortalProfileResponse,
  } from "$lib/types";

  let loading = $state(true);
  let uploadingPhoto = $state(false);
  let context = $state<PartnerPortalContextResponse | null>(null);
  let profile = $state<PartnerPortalProfileResponse | null>(null);
  let photoInput = $state<HTMLInputElement | null>(null);

  function titleCase(value: string): string {
    return value
      .replaceAll("_", " ")
      .split(" ")
      .filter(Boolean)
      .map((part) => part[0]?.toUpperCase() + part.slice(1))
      .join(" ");
  }

  function initials(fullName: string): string {
    return fullName
      .split(" ")
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() ?? "")
      .join("") || "?";
  }

  async function loadProfile() {
    loading = true;
    try {
      const ctx = await api.get<PartnerPortalContextResponse>("/partners/portal/context/");
      context = ctx;
      if (!ctx.is_partner_user && !ctx.is_preview_mode) {
        profile = null;
        return;
      }
      const data = await api.get<PartnerPortalProfileResponse>("/partners/portal/profile/");
      profile = data;
    } catch (error) {
      toast.error("Load failed", parsePortalError(error, "Could not load portal profile."));
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    loadProfile();
  });

  async function uploadProfilePhoto(file: File) {
    if (!profile) return;
    const formData = new FormData();
    formData.append("photo", file);

    uploadingPhoto = true;
    try {
      const response = await api.upload<PartnerPortalProfilePhotoResponse>("/partners/portal/profile/photo/", formData);
      profile.user.profile_photo_url = response.profile_photo_url;
      toast.success("Photo updated", "Profile photo was saved successfully.");
    } catch (error) {
      toast.error("Photo upload failed", parsePortalError(error, "Could not upload profile photo."));
    } finally {
      uploadingPhoto = false;
      if (photoInput) {
        photoInput.value = "";
      }
    }
  }

  async function removeProfilePhoto() {
    if (!profile) return;
    uploadingPhoto = true;
    try {
      const response = await api.delete<PartnerPortalProfilePhotoResponse>("/partners/portal/profile/photo/");
      profile.user.profile_photo_url = response.profile_photo_url;
      toast.success("Photo removed", "Profile photo has been removed.");
    } catch (error) {
      toast.error("Photo removal failed", parsePortalError(error, "Could not remove profile photo."));
    } finally {
      uploadingPhoto = false;
      if (photoInput) {
        photoInput.value = "";
      }
    }
  }

  function openPhotoPicker() {
    if (!uploadingPhoto) {
      photoInput?.click();
    }
  }

  function handlePhotoSelected(event: Event) {
    const input = event.currentTarget as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    void uploadProfilePhoto(file);
  }
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
  </div>
{:else if context && !context.is_partner_user && !context.is_preview_mode}
  <div class="rounded-xl border border-amber-200 bg-amber-50 px-6 py-5">
    <h1 class="text-lg font-semibold text-amber-900">No profile access yet</h1>
    <p class="mt-1 text-sm text-amber-800">Portal profile and legal context become available after portal activation.</p>
  </div>
{:else if profile}
  <div class="space-y-6">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold text-neutral-900">Profile & Legal</h1>
        <p class="mt-1 text-sm text-neutral-500">Entitlement matrix, contract references, and legal access controls.</p>
      </div>
      <button
        onclick={() => loadProfile()}
        class="rounded-lg border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
      >
        Refresh
      </button>
    </div>

    <div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <div class="rounded-xl border border-neutral-200 bg-white p-5">
        <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Identity</h2>
        <div class="mt-3 flex flex-wrap items-center gap-3">
          <div class="flex h-16 w-16 items-center justify-center overflow-hidden rounded-full border border-neutral-200 bg-neutral-100 text-lg font-semibold text-neutral-700">
            {#if profile.user.profile_photo_url}
              <img src={profile.user.profile_photo_url} alt="Profile photo" class="h-full w-full object-cover" />
            {:else}
              <span>{initials(profile.user.full_name)}</span>
            {/if}
          </div>
          <div class="space-y-2">
            <p class="text-xs text-neutral-500">Used for KYC identity records.</p>
            <div class="flex flex-wrap gap-2">
              <button
                onclick={openPhotoPicker}
                class="rounded-lg border border-neutral-200 bg-white px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={uploadingPhoto}
              >
                {uploadingPhoto ? "Uploading..." : "Upload photo"}
              </button>
              {#if profile.user.profile_photo_url}
                <button
                  onclick={() => removeProfilePhoto()}
                  class="rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-medium text-rose-700 hover:bg-rose-100 disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={uploadingPhoto}
                >
                  Remove
                </button>
              {/if}
            </div>
          </div>
        </div>
        <input
          type="file"
          accept="image/*"
          class="hidden"
          bind:this={photoInput}
          onchange={handlePhotoSelected}
        />
        <dl class="mt-3 space-y-2 text-sm">
          <div>
            <dt class="text-neutral-500">Name</dt>
            <dd class="font-medium text-neutral-900">{profile.user.full_name || "--"}</dd>
          </div>
          <div>
            <dt class="text-neutral-500">Email</dt>
            <dd class="font-medium text-neutral-900">{profile.user.email}</dd>
          </div>
          <div>
            <dt class="text-neutral-500">Budget Scope</dt>
            <dd class="font-medium text-neutral-900">{titleCase(profile.budget_scope)}</dd>
          </div>
        </dl>
      </div>

      <div class="rounded-xl border border-neutral-200 bg-white p-5">
        <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Role & Types</h2>
        <div class="mt-3 flex flex-wrap gap-2">
          {#each profile.portal_roles as role (role)}
            <span class="rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-700">{titleCase(role)}</span>
          {/each}
          {#each profile.partner_types as type (type)}
            <span class="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">{titleCase(type)}</span>
          {/each}
        </div>
      </div>

      <div class="rounded-xl border border-neutral-200 bg-white p-5">
        <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Legal Controls</h2>
        <dl class="mt-3 space-y-2 text-sm">
          <div>
            <dt class="text-neutral-500">Agreement Acceptance</dt>
            <dd class="font-medium text-neutral-900">{profile.legal.agreement_acceptance_required ? "Required" : "Not required"}</dd>
          </div>
          <div>
            <dt class="text-neutral-500">Device Fingerprinting</dt>
            <dd class="font-medium text-neutral-900">{profile.legal.device_fingerprinting_enabled ? "Enabled" : "Disabled"}</dd>
          </div>
        </dl>
      </div>
    </div>

    <div class="rounded-xl border border-neutral-200 bg-white p-5">
      <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Permission Matrix</h2>
      <div class="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <div class="rounded-lg border border-neutral-100 bg-neutral-50 px-3 py-2">
          <p class="text-[10px] uppercase tracking-wide text-neutral-500">View Other Investors</p>
          <p class="mt-1 text-sm font-semibold text-neutral-900">{profile.permissions.can_view_other_investors ? "Yes" : "No"}</p>
        </div>
        <div class="rounded-lg border border-neutral-100 bg-neutral-50 px-3 py-2">
          <p class="text-[10px] uppercase tracking-wide text-neutral-500">Edit</p>
          <p class="mt-1 text-sm font-semibold text-neutral-900">{profile.permissions.can_edit ? "Yes" : "No"}</p>
        </div>
        <div class="rounded-lg border border-neutral-100 bg-neutral-50 px-3 py-2">
          <p class="text-[10px] uppercase tracking-wide text-neutral-500">Approve</p>
          <p class="mt-1 text-sm font-semibold text-neutral-900">{profile.permissions.can_approve ? "Yes" : "No"}</p>
        </div>
        <div class="rounded-lg border border-neutral-100 bg-neutral-50 px-3 py-2">
          <p class="text-[10px] uppercase tracking-wide text-neutral-500">Comment</p>
          <p class="mt-1 text-sm font-semibold text-neutral-900">{profile.permissions.can_comment ? "Yes" : "No"}</p>
        </div>
        <div class="rounded-lg border border-neutral-100 bg-neutral-50 px-3 py-2">
          <p class="text-[10px] uppercase tracking-wide text-neutral-500">Download Documents</p>
          <p class="mt-1 text-sm font-semibold text-neutral-900">{profile.permissions.can_download_documents ? "Yes" : "No"}</p>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 gap-6 xl:grid-cols-2">
      <div class="rounded-xl border border-neutral-200 bg-white">
        <div class="border-b border-neutral-100 px-5 py-4">
          <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Active Onboarding Cases</h2>
        </div>
        {#if profile.cases.length === 0}
          <div class="px-5 py-8 text-sm text-neutral-500">No active cases.</div>
        {:else}
          <div class="space-y-3 px-5 py-4">
            {#each profile.cases as row (row.id)}
              <div class="rounded-lg border border-neutral-100 bg-neutral-50 px-3 py-2">
                <p class="text-sm font-medium text-neutral-900">{row.title}</p>
                <p class="text-xs text-neutral-600">{titleCase(row.partner_type)} • {titleCase(row.status)} • {row.current_stage_name || "No stage"}</p>
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <div class="rounded-xl border border-neutral-200 bg-white">
        <div class="border-b border-neutral-100 px-5 py-4">
          <h2 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Entitlements</h2>
        </div>
        {#if profile.entitlements.length === 0}
          <div class="px-5 py-8 text-sm text-neutral-500">No active entitlements.</div>
        {:else}
          <div class="space-y-3 px-5 py-4">
            {#each profile.entitlements as row (row.id)}
              <div class="rounded-lg border border-neutral-100 bg-neutral-50 px-3 py-2">
                <p class="text-sm font-medium text-neutral-900">{titleCase(row.portal_role)} • {titleCase(row.budget_scope)}</p>
                <p class="text-xs text-neutral-600">Project: {row.project_name || "--"} • SPV: {row.spv_name || "--"}</p>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  </div>
{/if}

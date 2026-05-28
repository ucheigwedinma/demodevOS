<script lang="ts">
  import { goto } from "$app/navigation";
  import { onMount } from "svelte";
  import { api } from "$lib/api";
  import { parsePortalError } from "$lib/partnerPortal";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    PartnerPortalLegalAcceptResponse,
    PartnerPortalLegalStatusResponse,
  } from "$lib/types";

  let loading = $state(true);
  let saving = $state(false);
  let status = $state<PartnerPortalLegalStatusResponse | null>(null);
  let acceptTerms = $state(false);
  let acceptPrivacy = $state(false);
  let errorMessage = $state("");

  async function loadStatus() {
    const token = localStorage.getItem("access_token");
    if (!token) {
      await goto("/partner/login");
      return;
    }

    loading = true;
    errorMessage = "";
    try {
      const response = await api.get<PartnerPortalLegalStatusResponse>("/partners/portal/legal/");
      status = response;
      if (response.accepted) {
        await goto("/partner");
      }
    } catch (error) {
      errorMessage = parsePortalError(error, "Could not load legal acceptance status.");
    } finally {
      loading = false;
    }
  }

  async function submitAcceptance(event: SubmitEvent) {
    event.preventDefault();
    if (!acceptTerms || !acceptPrivacy) {
      toast.error("Acceptance required", "You must accept both agreements to continue.");
      return;
    }

    saving = true;
    errorMessage = "";
    try {
      const response = await api.post<PartnerPortalLegalAcceptResponse>("/partners/portal/legal/accept/", {
        terms_version: status?.terms_version ?? "v1",
        privacy_version: status?.privacy_version ?? "v1",
      });
      toast.success("Accepted", response.detail);
      await goto("/partner");
    } catch (error) {
      errorMessage = parsePortalError(error, "Could not complete legal acceptance.");
      toast.error("Acceptance failed", errorMessage);
    } finally {
      saving = false;
    }
  }

  onMount(() => {
    loadStatus();
  });
</script>

<div class="mx-auto flex min-h-screen w-full max-w-3xl items-center justify-center px-6 py-10">
  {#if loading}
    <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
  {:else}
    <div class="w-full rounded-3xl border border-neutral-200 bg-white p-8 shadow-sm sm:p-10">
      <div class="mb-4 inline-flex items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-amber-700">
        First-time Portal Access
      </div>
      <h1 class="text-2xl font-bold text-neutral-900">Legal Acceptance Required</h1>
      <p class="mt-2 text-sm text-neutral-600">
        You must accept our Terms of Use and Privacy Policy before accessing the partner portal.
      </p>

      {#if errorMessage}
        <div class="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{errorMessage}</div>
      {/if}

      <form class="mt-6 space-y-4" onsubmit={submitAcceptance}>
        <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-4">
          <p class="text-sm font-semibold text-neutral-900">Terms of Use ({status?.terms_version ?? "v1"})</p>
          <p class="mt-1 text-xs leading-relaxed text-neutral-600">
            Governs acceptable usage, permitted disclosures, restricted activities, and legal obligations for partner portal access.
          </p>
          <div class="mt-3 flex items-start gap-2">
            <input id="accept-terms" type="checkbox" bind:checked={acceptTerms} class="mt-0.5 h-4 w-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900" />
            <label for="accept-terms" class="text-sm text-neutral-700">
              I have read and accept the <a class="font-semibold text-neutral-900 hover:underline" href="/terms" target="_blank" rel="noreferrer">Terms of Use</a>.
            </label>
          </div>
        </div>

        <div class="rounded-xl border border-neutral-200 bg-neutral-50 p-4">
          <p class="text-sm font-semibold text-neutral-900">Privacy Policy ({status?.privacy_version ?? "v1"})</p>
          <p class="mt-1 text-xs leading-relaxed text-neutral-600">
            Describes how your activity and personal data are processed, stored, and audited within the portal infrastructure.
          </p>
          <div class="mt-3 flex items-start gap-2">
            <input id="accept-privacy" type="checkbox" bind:checked={acceptPrivacy} class="mt-0.5 h-4 w-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-900" />
            <label for="accept-privacy" class="text-sm text-neutral-700">
              I have read and accept the <a class="font-semibold text-neutral-900 hover:underline" href="/privacy" target="_blank" rel="noreferrer">Privacy Policy</a>.
            </label>
          </div>
        </div>

        <button
          type="submit"
          disabled={saving}
          class="w-full rounded-lg bg-neutral-900 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-60"
        >
          {saving ? "Saving acceptance..." : "Accept and continue"}
        </button>
      </form>
    </div>
  {/if}
</div>

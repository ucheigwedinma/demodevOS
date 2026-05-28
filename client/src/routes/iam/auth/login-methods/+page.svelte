<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";

  type LoginMethods = {
    allow_password_login: boolean;
    allow_oauth_login: boolean;
    allow_passkey_login: boolean;
    allow_sso_login: boolean;
  };

  let methods = $state<LoginMethods>({
    allow_password_login: true,
    allow_oauth_login: true,
    allow_passkey_login: true,
    allow_sso_login: false,
  });
  let original = $state<LoginMethods | null>(null);
  let loading = $state(true);
  let saving = $state(false);

  const METHOD_DEFS: { key: keyof LoginMethods; label: string; desc: string; icon: string }[] = [
    {
      key: "allow_password_login",
      label: "Email + password",
      desc: "Classic credential login. Subject to your password policy.",
      icon: "M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z",
    },
    {
      key: "allow_oauth_login",
      label: "OAuth (Google, etc.)",
      desc: "Sign in with a configured OAuth provider. See OAuth/SAML page for details.",
      icon: "M2.25 12c0-5.385 4.365-9.75 9.75-9.75 5.385 0 9.75 4.365 9.75 9.75s-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12Z",
    },
    {
      key: "allow_passkey_login",
      label: "Passkey / biometric",
      desc: "FIDO2 / WebAuthn — face, fingerprint, or hardware key.",
      icon: "M7.864 4.243A7.5 7.5 0 0 1 19.5 10.5c0 2.92-.556 5.709-1.568 8.268M5.742 6.364A7.465 7.465 0 0 0 4.5 10.5a7.464 7.464 0 0 1-1.15 3.993m1.989 3.559A11.209 11.209 0 0 0 8.25 10.5a3.75 3.75 0 1 1 7.5 0c0 .527-.021 1.049-.064 1.565M12 10.5a14.94 14.94 0 0 1-3.6 9.75m6.633-4.596a18.666 18.666 0 0 1-2.485 5.33",
    },
    {
      key: "allow_sso_login",
      label: "Enterprise SSO (SAML / OIDC)",
      desc: "Federated login. Requires per-org IdP config — see iam/federation/.",
      icon: "M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z",
    },
  ];

  async function load() {
    loading = true;
    try {
      const data = await api.get<LoginMethods>("/iam/auth/login-methods/");
      methods = data;
      original = { ...data };
    } catch {
      toast.error("Load failed", "Could not load login methods.");
    } finally {
      loading = false;
    }
  }

  async function save() {
    if (!Object.values(methods).some(Boolean)) {
      toast.error("Validation", "Keep at least one login method enabled.");
      return;
    }
    saving = true;
    try {
      const data = await api.patch<LoginMethods>("/iam/auth/login-methods/", methods);
      methods = data;
      original = { ...data };
      toast.success("Saved", "Login methods updated.");
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error("Save failed", err.message ?? "Please try again.");
      }
    } finally {
      saving = false;
    }
  }

  function reset() {
    if (original) methods = { ...original };
  }

  let dirty = $derived.by(() => {
    if (!original) return false;
    return METHOD_DEFS.some((m) => methods[m.key] !== original![m.key]);
  });

  $effect(() => { load(); });
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Login Methods</h1>
    <p class="mt-1 text-sm text-neutral-500">
      Per-org enable/disable of authentication methods. Disabling a method here removes it from
      the login screen for everyone in your organization. At least one method must stay enabled.
    </p>
  </div>

  {#if loading}
    <div class="rounded-xl border border-neutral-200 bg-white p-16 text-center">
      <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
    </div>
  {:else}
    <div class="rounded-xl border border-neutral-200 bg-white divide-y divide-neutral-100">
      {#each METHOD_DEFS as m}
        <label class="px-6 py-5 flex items-start justify-between gap-4 cursor-pointer hover:bg-neutral-50 transition-colors">
          <div class="flex items-start gap-4 min-w-0">
            <div class="w-10 h-10 rounded-lg bg-neutral-100 flex items-center justify-center shrink-0">
              <svg class="w-5 h-5 text-neutral-700" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d={m.icon} />
              </svg>
            </div>
            <div class="min-w-0">
              <p class="text-sm font-medium text-neutral-900">{m.label}</p>
              <p class="mt-0.5 text-xs text-neutral-500">{m.desc}</p>
            </div>
          </div>
          <div class="shrink-0">
            <input type="checkbox" bind:checked={methods[m.key]}
              class="h-5 w-5 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-800" />
          </div>
        </label>
      {/each}

      <div class="px-6 py-4 bg-neutral-50/50 rounded-b-xl flex items-center gap-3">
        <p class="text-xs text-neutral-400 mr-auto">
          {dirty ? "Unsaved changes" : "Saved"}
        </p>
        {#if dirty}
          <button onclick={reset} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">
            Discard
          </button>
        {/if}
        <button onclick={save} disabled={saving || !dirty}
          class="rounded-lg bg-neutral-900 px-5 py-2 text-sm font-semibold text-white hover:bg-neutral-800 transition-colors disabled:opacity-50">
          {saving ? "Saving..." : "Save changes"}
        </button>
      </div>
    </div>
  {/if}
</div>

<script lang="ts">
  import { api } from "$lib/api";

  type LoginMethods = {
    allow_password_login: boolean;
    allow_oauth_login: boolean;
    allow_passkey_login: boolean;
    allow_sso_login: boolean;
  };

  let loginMethods = $state<LoginMethods | null>(null);
  let loading = $state(true);

  async function load() {
    loading = true;
    try {
      loginMethods = await api.get<LoginMethods>("/iam/auth/login-methods/");
    } catch {
      loginMethods = null;
    } finally {
      loading = false;
    }
  }

  $effect(() => { load(); });
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">OAuth / SAML</h1>
    <p class="mt-1 text-sm text-neutral-500">
      Configured federated providers and protocol-level details.
    </p>
  </div>

  {#if loading}
    <div class="rounded-xl border border-neutral-200 bg-white p-12 text-center">
      <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
    </div>
  {:else}
    <!-- OAuth providers -->
    <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
      <div class="px-6 py-4 border-b border-neutral-100">
        <h2 class="text-sm font-semibold text-neutral-900">OAuth 2.0</h2>
        <p class="mt-0.5 text-xs text-neutral-500">Sign-in via OAuth. Provider configuration is platform-level.</p>
      </div>

      <div class="divide-y divide-neutral-100">
        <div class="px-6 py-4 flex items-center justify-between gap-4">
          <div class="flex items-center gap-3 min-w-0">
            <div class="w-10 h-10 rounded-lg bg-neutral-100 flex items-center justify-center shrink-0 text-sm font-semibold text-neutral-700">
              G
            </div>
            <div class="min-w-0">
              <p class="text-sm font-medium text-neutral-900">Google</p>
              <p class="mt-0.5 text-xs text-neutral-500">
                Configured via <code class="text-[10px] bg-neutral-100 px-1.5 py-0.5 rounded">OAUTH_GOOGLE_CLIENT_ID</code>
              </p>
            </div>
          </div>
          <span class="shrink-0 inline-flex items-center gap-1.5 rounded-full bg-green-50 px-3 py-1 text-xs font-medium text-green-700">
            <span class="w-1.5 h-1.5 rounded-full bg-green-500"></span>
            Available
          </span>
        </div>

        <div class="px-6 py-4 flex items-center justify-between gap-4 opacity-60">
          <div class="flex items-center gap-3 min-w-0">
            <div class="w-10 h-10 rounded-lg bg-neutral-100 flex items-center justify-center shrink-0 text-sm font-semibold text-neutral-700">
              M
            </div>
            <div class="min-w-0">
              <p class="text-sm font-medium text-neutral-900">Microsoft</p>
              <p class="mt-0.5 text-xs text-neutral-500">Pending — Cluster 8 (Federation)</p>
            </div>
          </div>
          <span class="shrink-0 inline-flex items-center rounded-full bg-neutral-100 px-3 py-1 text-xs font-medium text-neutral-600">
            Not configured
          </span>
        </div>

        <div class="px-6 py-4 flex items-center justify-between gap-4 opacity-60">
          <div class="flex items-center gap-3 min-w-0">
            <div class="w-10 h-10 rounded-lg bg-neutral-100 flex items-center justify-center shrink-0 text-sm font-semibold text-neutral-700">
              A
            </div>
            <div class="min-w-0">
              <p class="text-sm font-medium text-neutral-900">Apple</p>
              <p class="mt-0.5 text-xs text-neutral-500">Pending — Cluster 8 (Federation)</p>
            </div>
          </div>
          <span class="shrink-0 inline-flex items-center rounded-full bg-neutral-100 px-3 py-1 text-xs font-medium text-neutral-600">
            Not configured
          </span>
        </div>
      </div>
    </div>

    <!-- SAML -->
    <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
      <div class="px-6 py-4 border-b border-neutral-100">
        <h2 class="text-sm font-semibold text-neutral-900">SAML 2.0</h2>
        <p class="mt-0.5 text-xs text-neutral-500">Per-org SAML IdP configuration lives under Identity Federation.</p>
      </div>
      <div class="px-6 py-6 text-center">
        <p class="text-sm text-neutral-700 font-medium">Generic SAML / OIDC connector</p>
        <p class="mt-1 text-xs text-neutral-500">
          Configure entityId, SSO URL, signing certificate, and attribute mappings.
        </p>
        <a href="/iam/federation/external-idp"
          class="mt-4 inline-block rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">
          Open Federation →
        </a>
      </div>
    </div>

    {#if loginMethods}
      <div class="rounded-xl border border-neutral-200 bg-white p-5 flex items-center justify-between">
        <div>
          <p class="text-sm font-medium text-neutral-900">OAuth login is currently
            {#if loginMethods.allow_oauth_login}
              <span class="text-green-700">enabled</span>
            {:else}
              <span class="text-neutral-500">disabled</span>
            {/if}
            for this org
          </p>
          <p class="mt-0.5 text-xs text-neutral-500">SSO/SAML is
            {#if loginMethods.allow_sso_login}
              <span class="text-green-700">enabled</span>
            {:else}
              <span class="text-neutral-500">disabled</span>
            {/if}
          </p>
        </div>
        <a href="/iam/auth/login-methods"
          class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">
          Manage →
        </a>
      </div>
    {/if}
  {/if}
</div>

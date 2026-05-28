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
    <h1 class="text-2xl font-bold text-neutral-900">Single Sign-On (SSO)</h1>
    <p class="mt-1 text-sm text-neutral-500">
      Federated authentication via your identity provider. SSO is enabled at the org level here;
      provider-specific configuration lives under
      <a href="/iam/federation/external-idp" class="underline underline-offset-2 hover:text-neutral-800">Identity Federation</a>.
    </p>
  </div>

  {#if loading}
    <div class="rounded-xl border border-neutral-200 bg-white p-12 text-center">
      <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
    </div>
  {:else if loginMethods}
    <div class="rounded-xl border border-neutral-200 bg-white p-6">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-sm font-semibold text-neutral-900">Org-level SSO</h2>
          <p class="mt-0.5 text-xs text-neutral-500">
            Whether SSO appears as a sign-in option for this organization.
          </p>
        </div>
        {#if loginMethods.allow_sso_login}
          <span class="inline-flex items-center gap-1.5 rounded-full bg-green-50 px-3 py-1 text-xs font-medium text-green-700">
            <span class="w-1.5 h-1.5 rounded-full bg-green-500"></span>
            Enabled
          </span>
        {:else}
          <span class="inline-flex items-center gap-1.5 rounded-full bg-neutral-100 px-3 py-1 text-xs font-medium text-neutral-600">
            <span class="w-1.5 h-1.5 rounded-full bg-neutral-400"></span>
            Disabled
          </span>
        {/if}
      </div>
      <a href="/iam/auth/login-methods"
        class="mt-4 inline-block rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">
        Manage in Login Methods →
      </a>
    </div>
  {/if}

  <div class="rounded-xl border border-neutral-200 bg-white p-6">
    <h2 class="text-sm font-semibold text-neutral-900 mb-4">Identity providers</h2>
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
      {#each [
        { label: "Active Directory (on-prem)",  href: "/iam/federation/active-directory" },
        { label: "Azure AD / Entra ID",         href: "/iam/federation/azure-ad" },
        { label: "Google Workspace",            href: "/iam/federation/google-workspace" },
        { label: "LDAP",                         href: "/iam/federation/ldap" },
        { label: "Generic SAML / OIDC",         href: "/iam/federation/external-idp" },
      ] as p}
        <a href={p.href}
          class="rounded-lg border border-neutral-200 p-4 hover:border-neutral-400 hover:shadow-sm transition-all">
          <p class="text-sm font-medium text-neutral-800">{p.label}</p>
          <p class="mt-1 text-xs text-neutral-500">Configure connection →</p>
        </a>
      {/each}
    </div>
  </div>

  <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-4 text-xs text-neutral-600">
    <p class="font-medium text-neutral-700 mb-1">Implementation note</p>
    <p>
      Per-org IdP configuration (entityId, ACS URL, certificates, attribute mappings) is part of
      Cluster 8 of the IAM roadmap and is currently scaffolded. Until that lands, the platform supports
      Google OAuth at the deployment level — see <code class="text-xs bg-white px-1.5 py-0.5 rounded">OAUTH_GOOGLE_CLIENT_ID</code>.
    </p>
  </div>
</div>

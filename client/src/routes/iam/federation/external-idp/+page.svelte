<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";

  type IdentityProvider = {
    id: number; kind: string; name: string;
    is_enabled: boolean; config: Record<string, unknown>; secrets: Record<string, string>;
  };

  let providers = $state<IdentityProvider[]>([]);
  let loading = $state(true);
  let saving = $state(false);
  let editing = $state<IdentityProvider | null>(null);
  let isNew = $state(false);
  let testResult = $state<null | { ok: boolean; message: string; missing_config?: string[]; missing_secrets?: string[] }>(null);

  let form = $state({
    name: "", is_enabled: false,
    protocol: "oidc" as "oidc" | "saml",
    entity_id: "",
    discovery_url: "",            // OIDC
    sso_url: "",                  // SAML
    acs_url: "",                  // SAML
    signing_cert: "",             // SAML, secret-ish (we treat as cert text)
    signing_cert_set: false,
    scopes: "openid email profile",
    attribute_mapping: '{"email": "email", "name": "name"}',
  });

  async function fetchProviders() {
    loading = true;
    try {
      const res = await api.get<{ count: number; results: IdentityProvider[] }>(
        "/iam/identity-providers/", { kind: "saml_oidc" },
      );
      providers = res.results;
    } catch { providers = []; }
    finally { loading = false; }
  }

  function openNew() {
    isNew = true; editing = null; testResult = null;
    form = {
      name: "", is_enabled: false, protocol: "oidc",
      entity_id: "", discovery_url: "", sso_url: "", acs_url: "",
      signing_cert: "", signing_cert_set: false,
      scopes: "openid email profile",
      attribute_mapping: '{"email": "email", "name": "name"}',
    };
  }

  function openEdit(p: IdentityProvider) {
    isNew = false; editing = p; testResult = null;
    const c = p.config || {};
    form = {
      name: p.name, is_enabled: p.is_enabled,
      protocol: ((c.protocol as string) === "saml" ? "saml" : "oidc"),
      entity_id: (c.entity_id as string) ?? "",
      discovery_url: (c.discovery_url as string) ?? "",
      sso_url: (c.sso_url as string) ?? "",
      acs_url: (c.acs_url as string) ?? "",
      signing_cert: "", signing_cert_set: !!p.secrets?.signing_cert,
      scopes: (c.scopes as string) ?? "openid email profile",
      attribute_mapping: typeof c.attribute_mapping === "object"
        ? JSON.stringify(c.attribute_mapping, null, 2)
        : ((c.attribute_mapping as string) ?? '{"email": "email", "name": "name"}'),
    };
  }

  function close() { editing = null; isNew = false; testResult = null; }

  async function save() {
    if (!form.name.trim() || !form.entity_id.trim()) {
      toast.error("Validation", "Name and entity ID are required.");
      return;
    }
    let mapping: Record<string, string> = {};
    try { mapping = JSON.parse(form.attribute_mapping); }
    catch { toast.error("Validation", "Attribute mapping must be valid JSON."); return; }

    saving = true;
    try {
      const config: Record<string, unknown> = {
        protocol: form.protocol,
        entity_id: form.entity_id.trim(),
        attribute_mapping: mapping,
      };
      if (form.protocol === "oidc") {
        config.discovery_url = form.discovery_url.trim();
        config.scopes = form.scopes.trim();
      } else {
        config.sso_url = form.sso_url.trim();
        config.acs_url = form.acs_url.trim();
      }
      const payload: Record<string, unknown> = {
        kind: "saml_oidc", name: form.name.trim(), is_enabled: form.is_enabled, config,
      };
      if (form.signing_cert.trim()) payload.secrets = { signing_cert: form.signing_cert.trim() };

      if (isNew) {
        editing = await api.post<IdentityProvider>("/iam/identity-providers/", payload); isNew = false;
        toast.success("Saved", "External IdP created.");
      } else if (editing) {
        editing = await api.patch<IdentityProvider>(`/iam/identity-providers/${editing.id}/`, payload);
        toast.success("Saved", "Updated.");
      }
      form.signing_cert = ""; form.signing_cert_set = !!editing?.secrets?.signing_cert;
      await fetchProviders();
    } catch (err) {
      if (err instanceof ApiError) toast.error("Save failed", "Please review the form.");
    } finally { saving = false; }
  }

  async function runTest() {
    if (!editing) return; testResult = null;
    try {
      const res = await api.post(`/iam/identity-providers/${editing.id}/test/`, {});
      testResult = res as unknown as typeof testResult;
    } catch (err) {
      if (err instanceof ApiError && err.data) testResult = err.data as unknown as typeof testResult;
      else testResult = { ok: false, message: "Test failed." };
    }
  }
  async function runSync() {
    if (!editing) return;
    try { await api.post(`/iam/identity-providers/${editing.id}/sync/`, {}); toast.success("Synced", ""); await fetchProviders(); }
    catch (err) {
      if (err instanceof ApiError && err.status === 501) { toast.success("Stub sync recorded", ""); await fetchProviders(); }
      else toast.error("Sync failed", "");
    }
  }
  async function remove() {
    if (!editing || !confirm(`Delete "${editing.name}"?`)) return;
    try { await api.delete(`/iam/identity-providers/${editing.id}/`); toast.success("Deleted", ""); close(); await fetchProviders(); }
    catch { toast.error("Delete failed", ""); }
  }

  $effect(() => { fetchProviders(); });
</script>

<div class="space-y-6">
  <div class="flex items-center justify-between gap-4">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900">External Identity Providers</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Generic SAML 2.0 / OIDC connector — for Okta, Auth0, Ping, Keycloak, OneLogin, JumpCloud,
        and any other IdP without a dedicated page above. If you use Azure AD or Google Workspace,
        prefer those — they expose provider-specific sync features.
      </p>
    </div>
    <button onclick={openNew} class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-900">Add IdP</button>
  </div>

  <div class="rounded-lg border border-blue-200 bg-blue-50 p-4 text-xs text-blue-800">
    <p class="font-medium mb-1">Status: configuration only</p>
    <p>Stores SAML/OIDC connection metadata + attribute mapping. Live sign-in flow + assertion validation land in the integration phase.</p>
  </div>

  <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
    {#if loading}
      <div class="p-16 text-center"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div></div>
    {:else if providers.length === 0}
      <div class="p-16 text-center">
        <h3 class="text-sm font-semibold text-neutral-800">No external IdPs</h3>
      </div>
    {:else}
      <ul class="divide-y divide-neutral-100">
        {#each providers as p}
          <li>
            <button onclick={() => openEdit(p)} class="w-full text-left p-5 hover:bg-neutral-50 flex items-start gap-4">
              <div class="w-10 h-10 rounded-lg bg-neutral-100 flex items-center justify-center text-[10px] font-bold text-neutral-700 shrink-0 uppercase">
                {(p.config?.protocol as string) ?? "—"}
              </div>
              <div class="flex-1 min-w-0">
                <p class="font-semibold text-neutral-900 truncate">{p.name}</p>
                <p class="mt-1 text-xs text-neutral-500 font-mono truncate">entity: {(p.config?.entity_id as string) ?? "—"}</p>
              </div>
              <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium {p.is_enabled ? 'bg-green-50 text-green-700' : 'bg-neutral-100 text-neutral-500'}">
                {p.is_enabled ? "Enabled" : "Disabled"}
              </span>
            </button>
          </li>
        {/each}
      </ul>
    {/if}
  </div>
</div>

{#if editing || isNew}
  <div class="fixed inset-0 z-50 flex">
    <button class="flex-1 bg-black/40 backdrop-blur-sm" onclick={close} aria-label="Close"></button>
    <div class="w-full max-w-2xl bg-white shadow-2xl border-l border-neutral-200 overflow-y-auto">
      <div class="p-6 border-b border-neutral-100 flex items-start justify-between">
        <h2 class="text-lg font-bold text-neutral-900">{isNew ? "New external IdP" : editing?.name}</h2>
        <button onclick={close} class="text-neutral-400 hover:text-neutral-600 text-xl leading-none">×</button>
      </div>

      <div class="p-6 space-y-4">
        <div>
          <label for="ext-name" class="block text-sm font-medium text-neutral-700 mb-1.5">Name <span class="text-red-500">*</span></label>
          <input id="ext-name" type="text" bind:value={form.name} placeholder="e.g. Okta production"
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
        </div>

        <div>
          <label class="block text-sm font-medium text-neutral-700 mb-2">Protocol</label>
          <div class="grid grid-cols-2 gap-2">
            <button type="button" onclick={() => (form.protocol = "oidc")}
              class="rounded-lg border px-3 py-2.5 text-sm transition-colors
                     {form.protocol === 'oidc' ? 'border-neutral-800 bg-neutral-50 font-semibold text-neutral-900' : 'border-neutral-200 text-neutral-600 hover:border-neutral-400'}">
              OIDC
            </button>
            <button type="button" onclick={() => (form.protocol = "saml")}
              class="rounded-lg border px-3 py-2.5 text-sm transition-colors
                     {form.protocol === 'saml' ? 'border-neutral-800 bg-neutral-50 font-semibold text-neutral-900' : 'border-neutral-200 text-neutral-600 hover:border-neutral-400'}">
              SAML 2.0
            </button>
          </div>
        </div>

        <div>
          <label for="ext-entity" class="block text-sm font-medium text-neutral-700 mb-1.5">Entity ID <span class="text-red-500">*</span></label>
          <input id="ext-entity" type="text" bind:value={form.entity_id}
            placeholder={form.protocol === "oidc" ? "https://idp.example.com" : "urn:acme:idp"}
            class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800" />
        </div>

        {#if form.protocol === "oidc"}
          <div>
            <label for="ext-disc" class="block text-sm font-medium text-neutral-700 mb-1.5">Discovery URL</label>
            <input id="ext-disc" type="text" bind:value={form.discovery_url}
              placeholder="https://idp.example.com/.well-known/openid-configuration"
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          </div>
          <div>
            <label for="ext-scopes" class="block text-sm font-medium text-neutral-700 mb-1.5">Scopes</label>
            <input id="ext-scopes" type="text" bind:value={form.scopes}
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          </div>
        {:else}
          <div>
            <label for="ext-sso" class="block text-sm font-medium text-neutral-700 mb-1.5">SSO URL</label>
            <input id="ext-sso" type="text" bind:value={form.sso_url}
              placeholder="https://idp.example.com/sso"
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          </div>
          <div>
            <label for="ext-acs" class="block text-sm font-medium text-neutral-700 mb-1.5">ACS URL (this side)</label>
            <input id="ext-acs" type="text" bind:value={form.acs_url}
              placeholder="https://your-platform.example/saml/acs"
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          </div>
          <div>
            <label for="ext-cert" class="block text-sm font-medium text-neutral-700 mb-1.5">
              IdP signing certificate
              {#if form.signing_cert_set}<span class="ml-1 inline-flex items-center rounded-full bg-green-50 px-2 py-0.5 text-[10px] font-medium text-green-700">Set</span>{/if}
            </label>
            <textarea id="ext-cert" rows="4" bind:value={form.signing_cert}
              placeholder={form.signing_cert_set ? "•••••••• (set; paste a new cert to replace)" : "-----BEGIN CERTIFICATE-----..."}
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800 resize-none"></textarea>
          </div>
        {/if}

        <div>
          <label for="ext-map" class="block text-sm font-medium text-neutral-700 mb-1.5">Attribute mapping (JSON)</label>
          <textarea id="ext-map" rows="4" bind:value={form.attribute_mapping}
            class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800 resize-none"></textarea>
          <p class="mt-1 text-xs text-neutral-500">Maps IdP claim/attribute names to platform User fields.</p>
        </div>

        <label class="flex items-center gap-3 rounded-lg border border-neutral-200 px-4 py-3 cursor-pointer hover:bg-neutral-50">
          <input type="checkbox" bind:checked={form.is_enabled} class="h-4 w-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-800" />
          <span class="text-sm text-neutral-800">Enabled</span>
        </label>

        {#if testResult}
          <div class="rounded-lg p-4 text-sm {testResult.ok ? 'border border-green-200 bg-green-50 text-green-800' : 'border border-red-200 bg-red-50 text-red-800'}">
            <p class="font-semibold mb-1">{testResult.ok ? "Test result" : "Test failed"}</p>
            <p class="text-xs">{testResult.message}</p>
            {#if testResult.missing_config?.length}<p class="mt-2 text-xs"><span class="font-medium">Missing:</span> {testResult.missing_config.join(", ")}</p>{/if}
            {#if testResult.missing_secrets?.length}<p class="text-xs"><span class="font-medium">Missing secrets:</span> {testResult.missing_secrets.join(", ")}</p>{/if}
          </div>
        {/if}
      </div>

      <div class="p-6 border-t border-neutral-100 flex items-center gap-2 flex-wrap">
        {#if !isNew && editing}<button onclick={remove} class="rounded-lg px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 mr-auto">Delete</button>{:else}<div class="mr-auto"></div>{/if}
        {#if !isNew && editing}
          <button onclick={runTest} class="rounded-lg border border-neutral-200 px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Test</button>
          <button onclick={runSync} class="rounded-lg border border-neutral-200 px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Sync now</button>
        {/if}
        <button onclick={close} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Close</button>
        <button onclick={save} disabled={saving} class="rounded-lg bg-neutral-800 px-5 py-2 text-sm font-semibold text-white hover:bg-neutral-900 disabled:opacity-60">
          {saving ? "Saving..." : (isNew ? "Create" : "Save")}
        </button>
      </div>
    </div>
  </div>
{/if}

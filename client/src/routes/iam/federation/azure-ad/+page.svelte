<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";

  type IdentityProvider = {
    id: number; kind: string; kind_display: string; name: string;
    is_enabled: boolean;
    config: Record<string, unknown>;
    secrets: Record<string, string>;
    last_synced_at: string | null;
    last_sync_status: string;
    last_sync_status_display: string;
  };

  let providers = $state<IdentityProvider[]>([]);
  let loading = $state(true);
  let saving = $state(false);
  let editing = $state<IdentityProvider | null>(null);
  let isNew = $state(false);
  let testResult = $state<null | { ok: boolean; message: string; missing_config?: string[]; missing_secrets?: string[] }>(null);

  let form = $state({
    name: "", is_enabled: false,
    tenant_id: "", client_id: "", client_secret: "", client_secret_set: false,
    redirect_uri: "", scopes: "openid email profile",
    jit_provisioning: true,
  });

  async function fetchProviders() {
    loading = true;
    try {
      const res = await api.get<{ count: number; results: IdentityProvider[] }>(
        "/iam/identity-providers/", { kind: "azure_ad" },
      );
      providers = res.results;
    } catch { providers = []; }
    finally { loading = false; }
  }

  function openNew() {
    isNew = true; editing = null; testResult = null;
    form = {
      name: "", is_enabled: false,
      tenant_id: "", client_id: "", client_secret: "", client_secret_set: false,
      redirect_uri: typeof window !== "undefined" ? `${window.location.origin}/login/oauth/azure/callback` : "",
      scopes: "openid email profile",
      jit_provisioning: true,
    };
  }

  function openEdit(p: IdentityProvider) {
    isNew = false; editing = p; testResult = null;
    const c = p.config || {};
    form = {
      name: p.name, is_enabled: p.is_enabled,
      tenant_id: (c.tenant_id as string) ?? "",
      client_id: (c.client_id as string) ?? "",
      client_secret: "", client_secret_set: !!p.secrets?.client_secret,
      redirect_uri: (c.redirect_uri as string) ?? "",
      scopes: (c.scopes as string) ?? "openid email profile",
      jit_provisioning: c.jit_provisioning !== false,
    };
  }

  function close() { editing = null; isNew = false; testResult = null; }

  async function save() {
    if (!form.name.trim() || !form.tenant_id.trim() || !form.client_id.trim() || !form.redirect_uri.trim()) {
      toast.error("Validation", "Name, tenant ID, client ID, and redirect URI are required.");
      return;
    }
    saving = true;
    try {
      const payload: Record<string, unknown> = {
        kind: "azure_ad", name: form.name.trim(), is_enabled: form.is_enabled,
        config: {
          tenant_id: form.tenant_id.trim(),
          client_id: form.client_id.trim(),
          redirect_uri: form.redirect_uri.trim(),
          scopes: form.scopes.trim(),
          jit_provisioning: form.jit_provisioning,
        },
      };
      if (form.client_secret.trim()) payload.secrets = { client_secret: form.client_secret.trim() };

      if (isNew) {
        editing = await api.post<IdentityProvider>("/iam/identity-providers/", payload);
        isNew = false;
        toast.success("Saved", "Azure AD configuration created.");
      } else if (editing) {
        editing = await api.patch<IdentityProvider>(`/iam/identity-providers/${editing.id}/`, payload);
        toast.success("Saved", "Configuration updated.");
      }
      form.client_secret = "";
      form.client_secret_set = !!editing?.secrets?.client_secret;
      await fetchProviders();
    } catch (err) {
      if (err instanceof ApiError) toast.error("Save failed", "Please review the form.");
    } finally { saving = false; }
  }

  async function runTest() {
    if (!editing) return;
    testResult = null;
    try {
      const res = await api.post(`/iam/identity-providers/${editing.id}/test/`, {});
      testResult = res as unknown as typeof testResult;
    } catch (err) {
      if (err instanceof ApiError && err.data) testResult = err.data as unknown as typeof testResult;
      else testResult = { ok: false, message: "Test failed unexpectedly." };
    }
  }

  async function runSync() {
    if (!editing) return;
    try {
      await api.post(`/iam/identity-providers/${editing.id}/sync/`, {});
      toast.success("Sync triggered", "");
      await fetchProviders();
    } catch (err) {
      if (err instanceof ApiError && err.status === 501) {
        toast.success("Stub sync recorded", "Live sync runs once integration phase lands.");
        await fetchProviders();
      } else { toast.error("Sync failed", ""); }
    }
  }

  async function remove() {
    if (!editing || !confirm(`Delete "${editing.name}"?`)) return;
    try {
      await api.delete(`/iam/identity-providers/${editing.id}/`);
      toast.success("Deleted", "");
      close();
      await fetchProviders();
    } catch { toast.error("Delete failed", ""); }
  }

  $effect(() => { fetchProviders(); });
</script>

<div class="space-y-6">
  <div class="flex items-center justify-between gap-4">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900">Azure AD / Entra ID</h1>
      <p class="mt-1 text-sm text-neutral-500">
        OIDC integration with Microsoft Entra ID for SSO + JIT user provisioning. Per-org tenant config.
      </p>
    </div>
    <button onclick={openNew} class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-900">Add configuration</button>
  </div>

  <div class="rounded-lg border border-blue-200 bg-blue-50 p-4 text-xs text-blue-800">
    <p class="font-medium mb-1">Status: configuration only</p>
    <p>Stores per-org Entra app registration. Live OIDC sign-in flow + Microsoft Graph user/group sync land in the integration phase.</p>
  </div>

  <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
    {#if loading}
      <div class="p-16 text-center"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div></div>
    {:else if providers.length === 0}
      <div class="p-16 text-center">
        <h3 class="text-sm font-semibold text-neutral-800">No Azure AD configurations</h3>
        <p class="mt-1.5 text-sm text-neutral-500">Click Add configuration to register a tenant.</p>
      </div>
    {:else}
      <ul class="divide-y divide-neutral-100">
        {#each providers as p}
          <li>
            <button onclick={() => openEdit(p)} class="w-full text-left p-5 hover:bg-neutral-50 flex items-start gap-4">
              <div class="w-10 h-10 rounded-lg bg-neutral-100 flex items-center justify-center text-sm font-bold text-neutral-700 shrink-0">M</div>
              <div class="flex-1 min-w-0">
                <p class="font-semibold text-neutral-900 truncate">{p.name}</p>
                <p class="mt-1 text-xs text-neutral-500 font-mono truncate">tenant: {(p.config?.tenant_id as string) ?? "—"}</p>
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
        <h2 class="text-lg font-bold text-neutral-900">{isNew ? "New Azure AD configuration" : editing?.name}</h2>
        <button onclick={close} class="text-neutral-400 hover:text-neutral-600 text-xl leading-none">×</button>
      </div>

      <div class="p-6 space-y-4">
        <div>
          <label for="az-name" class="block text-sm font-medium text-neutral-700 mb-1.5">Name <span class="text-red-500">*</span></label>
          <input id="az-name" type="text" bind:value={form.name} placeholder="e.g. Acme primary tenant"
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="az-tenant" class="block text-sm font-medium text-neutral-700 mb-1.5">Tenant ID <span class="text-red-500">*</span></label>
            <input id="az-tenant" type="text" bind:value={form.tenant_id} placeholder="UUID"
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          </div>
          <div>
            <label for="az-client" class="block text-sm font-medium text-neutral-700 mb-1.5">Client ID <span class="text-red-500">*</span></label>
            <input id="az-client" type="text" bind:value={form.client_id} placeholder="UUID"
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          </div>
        </div>
        <div>
          <label for="az-secret" class="block text-sm font-medium text-neutral-700 mb-1.5">
            Client secret
            {#if form.client_secret_set}
              <span class="ml-1 inline-flex items-center rounded-full bg-green-50 px-2 py-0.5 text-[10px] font-medium text-green-700">Set</span>
            {/if}
          </label>
          <input id="az-secret" type="password" bind:value={form.client_secret}
            placeholder={form.client_secret_set ? "•••••••• (already set; type to replace)" : "App registration client secret"}
            class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
        </div>
        <div>
          <label for="az-redirect" class="block text-sm font-medium text-neutral-700 mb-1.5">Redirect URI <span class="text-red-500">*</span></label>
          <input id="az-redirect" type="text" bind:value={form.redirect_uri}
            class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          <p class="mt-1 text-xs text-neutral-500">Add this exact URI to the Entra app registration's Web platform → Redirect URIs.</p>
        </div>
        <div>
          <label for="az-scopes" class="block text-sm font-medium text-neutral-700 mb-1.5">Requested scopes</label>
          <input id="az-scopes" type="text" bind:value={form.scopes}
            class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          <p class="mt-1 text-xs text-neutral-500">Space-separated. Add <code>GroupMember.Read.All</code> for group sync.</p>
        </div>

        <label class="flex items-center gap-3 rounded-lg border border-neutral-200 px-4 py-3 cursor-pointer hover:bg-neutral-50">
          <input type="checkbox" bind:checked={form.jit_provisioning} class="h-4 w-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-800" />
          <div class="flex-1">
            <p class="text-sm font-medium text-neutral-900">JIT provisioning on first sign-in</p>
            <p class="text-xs text-neutral-500">Auto-create platform users on their first successful Azure AD sign-in.</p>
          </div>
        </label>

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

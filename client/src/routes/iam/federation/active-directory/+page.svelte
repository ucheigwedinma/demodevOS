<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";

  type IdentityProvider = {
    id: number;
    kind: string;
    kind_display: string;
    name: string;
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
    name: "",
    is_enabled: false,
    server_uri: "",
    domain: "",
    base_dn: "",
    bind_dn: "",
    bind_password: "",
    bind_password_set: false,
    use_kerberos: false,
    user_attribute: "sAMAccountName",
    email_attribute: "mail",
    name_attribute: "displayName",
  });

  function formatDate(d: string | null): string {
    return d ? new Date(d).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) : "—";
  }

  async function fetchProviders() {
    loading = true;
    try {
      const res = await api.get<{ count: number; results: IdentityProvider[] }>(
        "/iam/identity-providers/", { kind: "active_directory" },
      );
      providers = res.results;
    } catch { providers = []; }
    finally { loading = false; }
  }

  function openNew() {
    isNew = true; editing = null; testResult = null;
    form = {
      name: "", is_enabled: false,
      server_uri: "ldaps://", domain: "", base_dn: "", bind_dn: "",
      bind_password: "", bind_password_set: false,
      use_kerberos: false,
      user_attribute: "sAMAccountName", email_attribute: "mail", name_attribute: "displayName",
    };
  }

  function openEdit(p: IdentityProvider) {
    isNew = false; editing = p; testResult = null;
    const c = p.config || {};
    form = {
      name: p.name,
      is_enabled: p.is_enabled,
      server_uri: (c.server_uri as string) ?? "",
      domain: (c.domain as string) ?? "",
      base_dn: (c.base_dn as string) ?? "",
      bind_dn: (c.bind_dn as string) ?? "",
      bind_password: "",
      bind_password_set: !!p.secrets?.bind_password,
      use_kerberos: !!c.use_kerberos,
      user_attribute: (c.user_attribute as string) ?? "sAMAccountName",
      email_attribute: (c.email_attribute as string) ?? "mail",
      name_attribute: (c.name_attribute as string) ?? "displayName",
    };
  }

  function close() { editing = null; isNew = false; testResult = null; }

  async function save() {
    if (!form.name.trim() || !form.server_uri.trim() || !form.base_dn.trim()) {
      toast.error("Validation", "Name, server URI, and base DN are required.");
      return;
    }
    saving = true;
    try {
      const payload: Record<string, unknown> = {
        kind: "active_directory",
        name: form.name.trim(),
        is_enabled: form.is_enabled,
        config: {
          server_uri: form.server_uri.trim(),
          domain: form.domain.trim(),
          base_dn: form.base_dn.trim(),
          bind_dn: form.bind_dn.trim(),
          use_kerberos: form.use_kerberos,
          user_attribute: form.user_attribute.trim() || "sAMAccountName",
          email_attribute: form.email_attribute.trim() || "mail",
          name_attribute: form.name_attribute.trim() || "displayName",
        },
      };
      if (form.bind_password.trim()) payload.secrets = { bind_password: form.bind_password.trim() };

      if (isNew) {
        editing = await api.post<IdentityProvider>("/iam/identity-providers/", payload);
        isNew = false;
        toast.success("Saved", "AD configuration created.");
      } else if (editing) {
        editing = await api.patch<IdentityProvider>(`/iam/identity-providers/${editing.id}/`, payload);
        toast.success("Saved", "AD configuration updated.");
      }
      form.bind_password = "";
      form.bind_password_set = !!editing?.secrets?.bind_password;
      await fetchProviders();
    } catch (err) {
      if (err instanceof ApiError) toast.error("Save failed", "Please review the form.");
    } finally {
      saving = false;
    }
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
      toast.success("Sync triggered", "See the row for last_sync status.");
      await fetchProviders();
    } catch (err) {
      if (err instanceof ApiError && err.status === 501) {
        toast.success("Stub sync recorded", "Live sync runs once integration phase lands.");
        await fetchProviders();
      } else {
        toast.error("Sync failed", "Could not trigger sync.");
      }
    }
  }

  async function remove() {
    if (!editing || !confirm(`Delete "${editing.name}"?`)) return;
    try {
      await api.delete(`/iam/identity-providers/${editing.id}/`);
      toast.success("Deleted", "Configuration removed.");
      close();
      await fetchProviders();
    } catch { toast.error("Delete failed", ""); }
  }

  $effect(() => { fetchProviders(); });
</script>

<div class="space-y-6">
  <div class="flex items-center justify-between gap-4">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900">Active Directory</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Bind to an on-premises Active Directory for user, group, and OU sync. Choose between
        LDAP-bind authentication and Kerberos pass-through.
      </p>
    </div>
    <button onclick={openNew} class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-900">
      Add configuration
    </button>
  </div>

  <div class="rounded-lg border border-blue-200 bg-blue-50 p-4 text-xs text-blue-800">
    <p class="font-medium mb-1">Status: configuration only</p>
    <p>This page stores AD connection settings. Live LDAP/Kerberos bind for sign-in and Directory sync land in the integration phase. Test returns structural validation; Sync records a stub run.</p>
  </div>

  <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
    {#if loading}
      <div class="p-16 text-center"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div></div>
    {:else if providers.length === 0}
      <div class="p-16 text-center">
        <h3 class="text-sm font-semibold text-neutral-800">No AD configurations</h3>
        <p class="mt-1.5 text-sm text-neutral-500">Click Add configuration to bind a directory.</p>
      </div>
    {:else}
      <ul class="divide-y divide-neutral-100">
        {#each providers as p}
          <li>
            <button onclick={() => openEdit(p)} class="w-full text-left p-5 hover:bg-neutral-50 flex items-start gap-4">
              <div class="w-10 h-10 rounded-lg bg-neutral-100 flex items-center justify-center text-sm font-bold text-neutral-700 shrink-0">AD</div>
              <div class="flex-1 min-w-0">
                <p class="font-semibold text-neutral-900 truncate">{p.name}</p>
                <p class="mt-1 text-xs text-neutral-500 truncate">
                  {(p.config?.server_uri as string) ?? "—"} · {(p.config?.base_dn as string) ?? "—"}
                </p>
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
        <h2 class="text-lg font-bold text-neutral-900">{isNew ? "New AD configuration" : editing?.name}</h2>
        <button onclick={close} class="text-neutral-400 hover:text-neutral-600 text-xl leading-none">×</button>
      </div>

      <div class="p-6 space-y-4">
        <div>
          <label for="ad-name" class="block text-sm font-medium text-neutral-700 mb-1.5">Name <span class="text-red-500">*</span></label>
          <input id="ad-name" type="text" bind:value={form.name} placeholder="e.g. Acme corporate AD"
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
        </div>
        <div>
          <label for="ad-uri" class="block text-sm font-medium text-neutral-700 mb-1.5">Server URI <span class="text-red-500">*</span></label>
          <input id="ad-uri" type="text" bind:value={form.server_uri} placeholder="ldaps://ad.acme.local:636"
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          <p class="mt-1 text-xs text-neutral-500">Use ldaps:// for TLS (recommended).</p>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="ad-domain" class="block text-sm font-medium text-neutral-700 mb-1.5">Domain</label>
            <input id="ad-domain" type="text" bind:value={form.domain} placeholder="acme.local"
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          </div>
          <div>
            <label for="ad-base" class="block text-sm font-medium text-neutral-700 mb-1.5">Base DN <span class="text-red-500">*</span></label>
            <input id="ad-base" type="text" bind:value={form.base_dn} placeholder="DC=acme,DC=local"
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          </div>
        </div>
        <div>
          <label for="ad-bind" class="block text-sm font-medium text-neutral-700 mb-1.5">Bind DN</label>
          <input id="ad-bind" type="text" bind:value={form.bind_dn} placeholder="CN=svc-developeros,CN=Users,DC=acme,DC=local"
            class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800" />
        </div>
        <div>
          <label for="ad-pw" class="block text-sm font-medium text-neutral-700 mb-1.5">
            Bind password
            {#if form.bind_password_set}
              <span class="ml-1 inline-flex items-center rounded-full bg-green-50 px-2 py-0.5 text-[10px] font-medium text-green-700">Set</span>
            {/if}
          </label>
          <input id="ad-pw" type="password" bind:value={form.bind_password}
            placeholder={form.bind_password_set ? "•••••••• (already set; type to replace)" : "Bind account password"}
            class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          <p class="mt-1 text-xs text-neutral-500">Stored write-only. Leave blank to preserve existing.</p>
        </div>

        <label class="flex items-center gap-3 rounded-lg border border-neutral-200 px-4 py-3 cursor-pointer hover:bg-neutral-50">
          <input type="checkbox" bind:checked={form.use_kerberos} class="h-4 w-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-800" />
          <div class="flex-1">
            <p class="text-sm font-medium text-neutral-900">Use Kerberos pass-through</p>
            <p class="text-xs text-neutral-500">When enabled, the platform uses GSSAPI / SPNEGO instead of LDAP simple-bind.</p>
          </div>
        </label>

        <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-4">
          <p class="text-sm font-semibold text-neutral-800 mb-3">Attribute mapping</p>
          <div class="grid grid-cols-3 gap-2">
            {#each [
              { key: "user_attribute", label: "Username" },
              { key: "email_attribute", label: "Email" },
              { key: "name_attribute", label: "Display name" },
            ] as field}
              <div>
                <label for="ad-attr-{field.key}" class="block text-xs font-medium text-neutral-700 mb-1">{field.label}</label>
                <input id="ad-attr-{field.key}" type="text" bind:value={form[field.key as keyof typeof form] as string}
                  class="w-full rounded-lg border border-neutral-300 bg-white px-2 py-1.5 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800" />
              </div>
            {/each}
          </div>
        </div>

        <label class="flex items-center gap-3 rounded-lg border border-neutral-200 px-4 py-3 cursor-pointer hover:bg-neutral-50">
          <input type="checkbox" bind:checked={form.is_enabled} class="h-4 w-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-800" />
          <span class="text-sm text-neutral-800">Enabled (effective once integration phase wires AD into the auth pipeline)</span>
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
        {#if !isNew && editing}
          <button onclick={remove} class="rounded-lg px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 mr-auto">Delete</button>
        {:else}<div class="mr-auto"></div>{/if}
        {#if !isNew && editing}
          <button onclick={runTest} class="rounded-lg border border-neutral-200 px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Test</button>
          <button onclick={runSync} class="rounded-lg border border-neutral-200 px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Sync now</button>
        {/if}
        <button onclick={close} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Close</button>
        <button onclick={save} disabled={saving}
          class="rounded-lg bg-neutral-800 px-5 py-2 text-sm font-semibold text-white hover:bg-neutral-900 disabled:opacity-60">
          {saving ? "Saving..." : (isNew ? "Create" : "Save")}
        </button>
      </div>
    </div>
  </div>
{/if}

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
    server_uri: "", base_dn: "", bind_dn: "",
    bind_password: "", bind_password_set: false,
    user_search_filter: "(uid={username})",
    group_search_filter: "(memberUid={uid})",
    user_attribute: "uid", email_attribute: "mail", name_attribute: "cn",
  });

  async function fetchProviders() {
    loading = true;
    try {
      const res = await api.get<{ count: number; results: IdentityProvider[] }>(
        "/iam/identity-providers/", { kind: "ldap" },
      );
      providers = res.results;
    } catch { providers = []; }
    finally { loading = false; }
  }

  function openNew() {
    isNew = true; editing = null; testResult = null;
    form = {
      name: "", is_enabled: false,
      server_uri: "ldaps://", base_dn: "", bind_dn: "",
      bind_password: "", bind_password_set: false,
      user_search_filter: "(uid={username})",
      group_search_filter: "(memberUid={uid})",
      user_attribute: "uid", email_attribute: "mail", name_attribute: "cn",
    };
  }

  function openEdit(p: IdentityProvider) {
    isNew = false; editing = p; testResult = null;
    const c = p.config || {};
    form = {
      name: p.name, is_enabled: p.is_enabled,
      server_uri: (c.server_uri as string) ?? "",
      base_dn: (c.base_dn as string) ?? "",
      bind_dn: (c.bind_dn as string) ?? "",
      bind_password: "", bind_password_set: !!p.secrets?.bind_password,
      user_search_filter: (c.user_search_filter as string) ?? "(uid={username})",
      group_search_filter: (c.group_search_filter as string) ?? "(memberUid={uid})",
      user_attribute: (c.user_attribute as string) ?? "uid",
      email_attribute: (c.email_attribute as string) ?? "mail",
      name_attribute: (c.name_attribute as string) ?? "cn",
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
        kind: "ldap", name: form.name.trim(), is_enabled: form.is_enabled,
        config: {
          server_uri: form.server_uri.trim(), base_dn: form.base_dn.trim(),
          bind_dn: form.bind_dn.trim(),
          user_search_filter: form.user_search_filter, group_search_filter: form.group_search_filter,
          user_attribute: form.user_attribute, email_attribute: form.email_attribute, name_attribute: form.name_attribute,
        },
      };
      if (form.bind_password.trim()) payload.secrets = { bind_password: form.bind_password.trim() };
      if (isNew) {
        editing = await api.post<IdentityProvider>("/iam/identity-providers/", payload); isNew = false;
        toast.success("Saved", "LDAP configuration created.");
      } else if (editing) {
        editing = await api.patch<IdentityProvider>(`/iam/identity-providers/${editing.id}/`, payload);
        toast.success("Saved", "Updated.");
      }
      form.bind_password = ""; form.bind_password_set = !!editing?.secrets?.bind_password;
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
    try {
      await api.post(`/iam/identity-providers/${editing.id}/sync/`, {}); toast.success("Synced", "");
      await fetchProviders();
    } catch (err) {
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
      <h1 class="text-2xl font-bold text-neutral-900">LDAP</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Generic LDAPv3 directory binding (OpenLDAP, FreeIPA, 389-DS, Oracle Internet Directory).
        For Microsoft AD specifically, use the Active Directory page — it handles AD niceties (Kerberos, RFC 2307 vs 4519).
      </p>
    </div>
    <button onclick={openNew} class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-900">Add configuration</button>
  </div>

  <div class="rounded-lg border border-blue-200 bg-blue-50 p-4 text-xs text-blue-800">
    <p class="font-medium mb-1">Status: configuration only</p>
    <p>Stores LDAP bind config + search filters. Real bind authentication and user/group sync land in the integration phase.</p>
  </div>

  <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
    {#if loading}
      <div class="p-16 text-center"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div></div>
    {:else if providers.length === 0}
      <div class="p-16 text-center">
        <h3 class="text-sm font-semibold text-neutral-800">No LDAP configurations</h3>
      </div>
    {:else}
      <ul class="divide-y divide-neutral-100">
        {#each providers as p}
          <li>
            <button onclick={() => openEdit(p)} class="w-full text-left p-5 hover:bg-neutral-50 flex items-start gap-4">
              <div class="w-10 h-10 rounded-lg bg-neutral-100 flex items-center justify-center text-sm font-bold text-neutral-700 shrink-0">L</div>
              <div class="flex-1 min-w-0">
                <p class="font-semibold text-neutral-900 truncate">{p.name}</p>
                <p class="mt-1 text-xs text-neutral-500 font-mono truncate">{(p.config?.server_uri as string) ?? "—"} · {(p.config?.base_dn as string) ?? "—"}</p>
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
        <h2 class="text-lg font-bold text-neutral-900">{isNew ? "New LDAP configuration" : editing?.name}</h2>
        <button onclick={close} class="text-neutral-400 hover:text-neutral-600 text-xl leading-none">×</button>
      </div>

      <div class="p-6 space-y-4">
        <div>
          <label for="ld-name" class="block text-sm font-medium text-neutral-700 mb-1.5">Name <span class="text-red-500">*</span></label>
          <input id="ld-name" type="text" bind:value={form.name}
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
        </div>
        <div>
          <label for="ld-uri" class="block text-sm font-medium text-neutral-700 mb-1.5">Server URI <span class="text-red-500">*</span></label>
          <input id="ld-uri" type="text" bind:value={form.server_uri} placeholder="ldaps://ldap.acme.com:636"
            class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800" />
        </div>
        <div>
          <label for="ld-base" class="block text-sm font-medium text-neutral-700 mb-1.5">Base DN <span class="text-red-500">*</span></label>
          <input id="ld-base" type="text" bind:value={form.base_dn} placeholder="ou=people,dc=acme,dc=com"
            class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800" />
        </div>
        <div>
          <label for="ld-bind" class="block text-sm font-medium text-neutral-700 mb-1.5">Bind DN</label>
          <input id="ld-bind" type="text" bind:value={form.bind_dn} placeholder="cn=svc,dc=acme,dc=com"
            class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800" />
        </div>
        <div>
          <label for="ld-pw" class="block text-sm font-medium text-neutral-700 mb-1.5">
            Bind password
            {#if form.bind_password_set}<span class="ml-1 inline-flex items-center rounded-full bg-green-50 px-2 py-0.5 text-[10px] font-medium text-green-700">Set</span>{/if}
          </label>
          <input id="ld-pw" type="password" bind:value={form.bind_password}
            placeholder={form.bind_password_set ? "•••••••• (set; type to replace)" : "Bind password"}
            class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
        </div>

        <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-4 space-y-3">
          <p class="text-sm font-semibold text-neutral-800">Search filters</p>
          <div>
            <label for="ld-uf" class="block text-xs font-medium text-neutral-700 mb-1">User search filter</label>
            <input id="ld-uf" type="text" bind:value={form.user_search_filter}
              class="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800" />
            <p class="mt-1 text-[11px] text-neutral-500">Use <code>{"{"}username{"}"}</code> as the placeholder.</p>
          </div>
          <div>
            <label for="ld-gf" class="block text-xs font-medium text-neutral-700 mb-1">Group search filter</label>
            <input id="ld-gf" type="text" bind:value={form.group_search_filter}
              class="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          </div>
        </div>

        <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-4">
          <p class="text-sm font-semibold text-neutral-800 mb-3">Attribute mapping</p>
          <div class="grid grid-cols-3 gap-2">
            {#each [
              { key: "user_attribute", label: "Username" },
              { key: "email_attribute", label: "Email" },
              { key: "name_attribute", label: "Display name" },
            ] as field}
              <div>
                <label for="ld-attr-{field.key}" class="block text-xs font-medium text-neutral-700 mb-1">{field.label}</label>
                <input id="ld-attr-{field.key}" type="text" bind:value={form[field.key as keyof typeof form] as string}
                  class="w-full rounded-lg border border-neutral-300 bg-white px-2 py-1.5 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800" />
              </div>
            {/each}
          </div>
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

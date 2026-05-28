<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";

  type SyncStatus = "never" | "success" | "failed" | "stub";

  type IdentityProvider = {
    id: number;
    kind: "google_workspace" | string;
    kind_display: string;
    name: string;
    is_enabled: boolean;
    config: {
      domain?: string;
      delegated_admin_email?: string;
      service_account_email?: string;
      sync_groups?: boolean;
      restrict_to_domain?: boolean;
    };
    secrets: { service_account_key?: string };
    last_synced_at: string | null;
    last_sync_status: SyncStatus;
    last_sync_status_display: string;
    last_sync_message: string;
    created_at: string;
    updated_at: string;
  };

  let providers = $state<IdentityProvider[]>([]);
  let loading = $state(true);
  let saving = $state(false);
  let testing = $state(false);
  let syncing = $state(false);

  // Drawer state
  let editing = $state<IdentityProvider | null>(null);
  let isNew = $state(false);

  let form = $state({
    name: "",
    is_enabled: false,
    domain: "",
    delegated_admin_email: "",
    service_account_email: "",
    sync_groups: false,
    restrict_to_domain: true,
    service_account_key: "",  // empty unless user enters a new value
    service_account_key_was_set: false,
  });

  // Test feedback inline
  let testResult = $state<null | { ok: boolean; message: string; missing_config?: string[]; missing_secrets?: string[] }>(null);

  function formatDate(d: string | null): string {
    if (!d) return "—";
    return new Date(d).toLocaleString("en-US", {
      month: "short", day: "numeric", year: "numeric",
      hour: "numeric", minute: "2-digit",
    });
  }

  function syncBadgeClasses(s: SyncStatus): string {
    return ({
      never: "bg-neutral-100 text-neutral-600",
      success: "bg-green-50 text-green-700",
      failed: "bg-red-50 text-red-700",
      stub: "bg-blue-50 text-blue-700",
    } as Record<string, string>)[s] ?? "bg-neutral-100 text-neutral-600";
  }

  async function fetchProviders() {
    loading = true;
    try {
      const res = await api.get<{ count: number; results: IdentityProvider[] }>(
        "/iam/identity-providers/", { kind: "google_workspace" },
      );
      providers = res.results;
    } catch {
      providers = [];
    } finally {
      loading = false;
    }
  }

  function openNew() {
    isNew = true;
    editing = null;
    testResult = null;
    form = {
      name: "",
      is_enabled: false,
      domain: "",
      delegated_admin_email: "",
      service_account_email: "",
      sync_groups: false,
      restrict_to_domain: true,
      service_account_key: "",
      service_account_key_was_set: false,
    };
  }

  function openEdit(p: IdentityProvider) {
    isNew = false;
    editing = p;
    testResult = null;
    form = {
      name: p.name,
      is_enabled: p.is_enabled,
      domain: p.config.domain ?? "",
      delegated_admin_email: p.config.delegated_admin_email ?? "",
      service_account_email: p.config.service_account_email ?? "",
      sync_groups: !!p.config.sync_groups,
      restrict_to_domain: p.config.restrict_to_domain ?? true,
      service_account_key: "",  // never pre-fill secret
      service_account_key_was_set: !!p.secrets?.service_account_key,
    };
  }

  function close() {
    editing = null;
    isNew = false;
    testResult = null;
  }

  async function save() {
    if (!form.name.trim()) {
      toast.error("Validation", "Give this configuration a name.");
      return;
    }
    if (!form.domain.trim()) {
      toast.error("Validation", "Domain is required (the workspace's primary domain).");
      return;
    }
    saving = true;
    try {
      const payload: Record<string, unknown> = {
        kind: "google_workspace",
        name: form.name.trim(),
        is_enabled: form.is_enabled,
        config: {
          domain: form.domain.trim(),
          delegated_admin_email: form.delegated_admin_email.trim(),
          service_account_email: form.service_account_email.trim(),
          sync_groups: form.sync_groups,
          restrict_to_domain: form.restrict_to_domain,
        },
      };
      // Only send the secret if the user typed a fresh one
      if (form.service_account_key.trim()) {
        payload.secrets = { service_account_key: form.service_account_key.trim() };
      }

      if (isNew) {
        const created = await api.post<IdentityProvider>("/iam/identity-providers/", payload);
        toast.success("Saved", "Google Workspace configuration created.");
        editing = created;
        isNew = false;
      } else if (editing) {
        const updated = await api.patch<IdentityProvider>(`/iam/identity-providers/${editing.id}/`, payload);
        toast.success("Saved", "Configuration updated.");
        editing = updated;
      }
      form.service_account_key = "";
      form.service_account_key_was_set = !!editing?.secrets?.service_account_key;
      await fetchProviders();
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error("Save failed", "Please review the form.");
      }
    } finally {
      saving = false;
    }
  }

  async function runTest() {
    if (!editing) return;
    testing = true;
    testResult = null;
    try {
      const res = await api.post<{ ok: boolean; stage: string; message: string; missing_config?: string[]; missing_secrets?: string[] }>(
        `/iam/identity-providers/${editing.id}/test/`, {},
      );
      testResult = res;
    } catch (err) {
      // 501 / 400 returns from the test endpoint are useful — show them
      if (err instanceof ApiError && err.data && typeof err.data === "object") {
        testResult = err.data as typeof testResult;
      } else {
        testResult = { ok: false, message: "Test failed unexpectedly." };
      }
    } finally {
      testing = false;
    }
  }

  async function runSync() {
    if (!editing) return;
    syncing = true;
    try {
      await api.post(`/iam/identity-providers/${editing.id}/sync/`, {});
      toast.success("Sync triggered", "See the result on the row.");
      await fetchProviders();
      // Re-fetch the editing record to update last_sync fields
      const refreshed = providers.find((p) => p.id === editing!.id);
      if (refreshed) editing = refreshed;
    } catch (err) {
      // 501 is the expected response in stub mode — surface it as info, not error
      if (err instanceof ApiError && err.status === 501) {
        toast.success("Stub sync recorded", "Live sync runs once the integration phase lands.");
        await fetchProviders();
        const refreshed = providers.find((p) => p.id === editing!.id);
        if (refreshed) editing = refreshed;
      } else {
        toast.error("Sync failed", "Could not trigger sync.");
      }
    } finally {
      syncing = false;
    }
  }

  async function remove() {
    if (!editing) return;
    if (!confirm(`Delete the configuration "${editing.name}"? This is irreversible.`)) return;
    try {
      await api.delete(`/iam/identity-providers/${editing.id}/`);
      toast.success("Deleted", "Configuration removed.");
      close();
      await fetchProviders();
    } catch {
      toast.error("Delete failed", "Could not delete the configuration.");
    }
  }

  $effect(() => { fetchProviders(); });
</script>

<div class="space-y-6">
  <div class="flex items-center justify-between gap-4">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900">Google Workspace</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Per-org Google Workspace federation. Configure a workspace domain, optionally restrict
        sign-in to that domain (the OAuth <code class="text-xs bg-neutral-100 px-1.5 py-0.5 rounded">hd</code>
        hint), and optionally sync directory groups.
      </p>
    </div>
    <button onclick={openNew}
      class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-900 transition-colors">
      Add configuration
    </button>
  </div>

  <div class="rounded-lg border border-blue-200 bg-blue-50 p-4 text-xs text-blue-800">
    <p class="font-medium mb-1">Status: configuration only</p>
    <p>
      This page stores per-org Google Workspace settings. Real sign-in restriction (<code class="bg-white px-1 rounded">hd</code>
      enforcement) and Directory API sync are wired in the next integration phase. The Test and Sync Now
      buttons return structural validation today and will switch to live calls once that phase lands.
    </p>
  </div>

  <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
    {#if loading}
      <div class="p-16 text-center">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
      </div>
    {:else if providers.length === 0}
      <div class="p-16 text-center">
        <div class="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-neutral-100 text-2xl font-bold text-neutral-700">
          G
        </div>
        <h3 class="text-sm font-semibold text-neutral-800">No Google Workspace configurations</h3>
        <p class="mt-1.5 text-sm text-neutral-500">Click Add configuration to set up your first workspace domain.</p>
        <button onclick={openNew} class="mt-5 inline-block rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-900 transition-colors">
          Add configuration
        </button>
      </div>
    {:else}
      <ul class="divide-y divide-neutral-100">
        {#each providers as p}
          <li>
            <button onclick={() => openEdit(p)} class="w-full text-left p-5 hover:bg-neutral-50 transition-colors flex items-start gap-4">
              <div class="w-10 h-10 rounded-lg bg-neutral-100 flex items-center justify-center text-sm font-semibold text-neutral-700 shrink-0">G</div>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <p class="font-semibold text-neutral-900 truncate">{p.name}</p>
                  {#if p.is_enabled}
                    <span class="inline-flex items-center gap-1.5 rounded-full bg-green-50 px-2 py-0.5 text-[10px] font-medium text-green-700">
                      <span class="w-1.5 h-1.5 rounded-full bg-green-500"></span>
                      Enabled
                    </span>
                  {:else}
                    <span class="inline-flex items-center rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] font-medium text-neutral-600">
                      Disabled
                    </span>
                  {/if}
                  <span class="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium {syncBadgeClasses(p.last_sync_status)}">
                    Sync: {p.last_sync_status_display}
                  </span>
                </div>
                <p class="mt-1 text-xs text-neutral-500">
                  Domain: <span class="font-mono text-neutral-700">{p.config.domain || "—"}</span>
                  {#if p.last_synced_at}
                    · last synced {formatDate(p.last_synced_at)}
                  {/if}
                </p>
              </div>
            </button>
          </li>
        {/each}
      </ul>
    {/if}
  </div>
</div>

<!-- Drawer -->
{#if editing || isNew}
  <div class="fixed inset-0 z-50 flex">
    <button class="flex-1 bg-black/40 backdrop-blur-sm" onclick={close} aria-label="Close"></button>
    <div class="w-full max-w-2xl bg-white shadow-2xl border-l border-neutral-200 overflow-y-auto">
      <div class="p-6 border-b border-neutral-100 flex items-start justify-between">
        <div>
          <h2 class="text-lg font-bold text-neutral-900">{isNew ? "New Google Workspace configuration" : editing?.name}</h2>
          <p class="mt-1 text-xs text-neutral-500">
            {isNew ? "All fields can be edited later." : "Saved settings; secrets are masked but preserved on edit."}
          </p>
        </div>
        <button onclick={close} class="text-neutral-400 hover:text-neutral-600 text-xl leading-none">×</button>
      </div>

      <div class="p-6 space-y-5">
        <div>
          <label for="gw-name" class="block text-sm font-medium text-neutral-700 mb-1.5">Name <span class="text-red-500">*</span></label>
          <input id="gw-name" type="text" bind:value={form.name} placeholder="e.g. Acme primary tenant"
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
        </div>

        <div>
          <label for="gw-domain" class="block text-sm font-medium text-neutral-700 mb-1.5">Workspace domain <span class="text-red-500">*</span></label>
          <input id="gw-domain" type="text" bind:value={form.domain} placeholder="acme.com"
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          <p class="mt-1 text-xs text-neutral-500">Used as the OAuth <code class="bg-neutral-100 px-1 rounded">hd</code> hint and for "restrict to domain" enforcement.</p>
        </div>

        <label class="flex items-center gap-3 rounded-lg border border-neutral-200 px-4 py-3 cursor-pointer hover:bg-neutral-50">
          <input type="checkbox" bind:checked={form.restrict_to_domain}
            class="h-4 w-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-800" />
          <div class="flex-1">
            <p class="text-sm font-medium text-neutral-900">Restrict OAuth login to this domain</p>
            <p class="text-xs text-neutral-500">Reject Google OAuth logins from accounts outside the workspace.</p>
          </div>
        </label>

        <label class="flex items-center gap-3 rounded-lg border border-neutral-200 px-4 py-3 cursor-pointer hover:bg-neutral-50">
          <input type="checkbox" bind:checked={form.sync_groups}
            class="h-4 w-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-800" />
          <div class="flex-1">
            <p class="text-sm font-medium text-neutral-900">Sync directory groups</p>
            <p class="text-xs text-neutral-500">Mirror Google Groups into platform UserGroups on a periodic schedule (requires service account).</p>
          </div>
        </label>

        <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-4">
          <p class="text-sm font-semibold text-neutral-800 mb-1">Service account (only if syncing)</p>
          <p class="text-xs text-neutral-500 mb-3">
            Domain-wide-delegation service account. Required for Directory-API group sync; not needed for sign-in alone.
          </p>

          <div class="space-y-3">
            <div>
              <label for="gw-sa-email" class="block text-xs font-medium text-neutral-700 mb-1">Service account email</label>
              <input id="gw-sa-email" type="text" bind:value={form.service_account_email}
                placeholder="sync@acme-12345.iam.gserviceaccount.com"
                class="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800" />
            </div>
            <div>
              <label for="gw-delegated" class="block text-xs font-medium text-neutral-700 mb-1">Delegated admin email</label>
              <input id="gw-delegated" type="text" bind:value={form.delegated_admin_email}
                placeholder="admin@acme.com"
                class="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800" />
              <p class="mt-1 text-[11px] text-neutral-500">Workspace admin to impersonate when reading the directory.</p>
            </div>
            <div>
              <label for="gw-key" class="block text-xs font-medium text-neutral-700 mb-1">
                Service account JSON key
                {#if form.service_account_key_was_set}
                  <span class="ml-1 inline-flex items-center rounded-full bg-green-50 px-2 py-0.5 text-[10px] font-medium text-green-700">Set</span>
                {/if}
              </label>
              <textarea id="gw-key" rows="4" bind:value={form.service_account_key}
                placeholder={form.service_account_key_was_set ? "•••••••• (already set; paste a new key to replace)" : "Paste the JSON key here"}
                class="w-full rounded-lg border border-neutral-300 bg-white px-3 py-2 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800 resize-none"></textarea>
              <p class="mt-1 text-[11px] text-neutral-500">Stored write-only. Leave blank to preserve the existing key.</p>
            </div>
          </div>
        </div>

        <label class="flex items-center gap-3 rounded-lg border border-neutral-200 px-4 py-3 cursor-pointer hover:bg-neutral-50">
          <input type="checkbox" bind:checked={form.is_enabled}
            class="h-4 w-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-800" />
          <div class="flex-1">
            <p class="text-sm font-medium text-neutral-900">Enabled</p>
            <p class="text-xs text-neutral-500">Surfaces this configuration as a sign-in option once the integration phase lands.</p>
          </div>
        </label>

        {#if testResult}
          <div class="rounded-lg p-4 text-sm
                      {testResult.ok ? 'border border-green-200 bg-green-50 text-green-800' : 'border border-red-200 bg-red-50 text-red-800'}">
            <p class="font-semibold mb-1">{testResult.ok ? "Test result" : "Test failed"}</p>
            <p class="text-xs">{testResult.message}</p>
            {#if testResult.missing_config && testResult.missing_config.length > 0}
              <p class="mt-2 text-xs">
                <span class="font-medium">Missing config:</span>
                {testResult.missing_config.join(", ")}
              </p>
            {/if}
            {#if testResult.missing_secrets && testResult.missing_secrets.length > 0}
              <p class="mt-1 text-xs">
                <span class="font-medium">Missing secrets:</span>
                {testResult.missing_secrets.join(", ")}
              </p>
            {/if}
          </div>
        {/if}
      </div>

      <div class="p-6 border-t border-neutral-100 flex items-center gap-2 flex-wrap">
        {#if !isNew && editing}
          <button onclick={remove} class="rounded-lg px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 transition-colors mr-auto">
            Delete
          </button>
        {:else}
          <div class="mr-auto"></div>
        {/if}

        {#if !isNew && editing}
          <button onclick={runTest} disabled={testing}
            class="rounded-lg border border-neutral-200 px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors disabled:opacity-50">
            {testing ? "Testing..." : "Test"}
          </button>
          <button onclick={runSync} disabled={syncing}
            class="rounded-lg border border-neutral-200 px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors disabled:opacity-50">
            {syncing ? "Syncing..." : "Sync now"}
          </button>
        {/if}
        <button onclick={close} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50 transition-colors">
          Close
        </button>
        <button onclick={save} disabled={saving}
          class="rounded-lg bg-neutral-800 px-5 py-2 text-sm font-semibold text-white hover:bg-neutral-900 transition-colors disabled:opacity-60">
          {saving ? "Saving..." : (isNew ? "Create" : "Save")}
        </button>
      </div>
    </div>
  </div>
{/if}

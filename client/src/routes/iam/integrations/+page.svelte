<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";

  type Connector = {
    id: number;
    slug: string;
    name: string;
    vendor: string;
    description: string;
    category: string;
    category_display: string;
    icon_url: string;
    docs_url: string;
    is_available: boolean;
    installation: null | {
      id: number;
      is_enabled: boolean;
      last_synced_at: string | null;
      config: Record<string, unknown>;
    };
  };
  type CatalogueResponse = {
    count: number;
    by_category: Record<string, Connector[]>;
    categories: { value: string; label: string }[];
  };

  let catalogue = $state<CatalogueResponse | null>(null);
  let loading = $state(true);
  let installing = $state<number | null>(null);

  let editingConnector = $state<Connector | null>(null);
  let installation = $state<{ id?: number; is_enabled: boolean; config: Record<string, string>; secrets: Record<string, string> } | null>(null);

  async function fetchCatalogue() {
    loading = true;
    try {
      catalogue = await api.get<CatalogueResponse>("/iam/connectors/");
    } catch {
      catalogue = null;
    } finally {
      loading = false;
    }
  }

  async function toggleInstall(c: Connector) {
    installing = c.id;
    try {
      if (c.installation) {
        // Toggle enable on existing installation
        await api.patch(`/iam/connector-installations/${c.installation.id}/`, {
          is_enabled: !c.installation.is_enabled,
        });
        toast.success("Updated", `${c.name} ${c.installation.is_enabled ? "disabled" : "enabled"}.`);
      } else {
        // Create installation
        await api.post("/iam/connector-installations/", {
          connector_id: c.id,
          is_enabled: true,
        });
        toast.success("Installed", `${c.name} added.`);
      }
      await fetchCatalogue();
    } catch (err) {
      if (err instanceof ApiError) toast.error("Action failed", "Could not update the installation.");
    } finally {
      installing = null;
    }
  }

  async function uninstall(c: Connector) {
    if (!c.installation) return;
    if (!confirm(`Uninstall ${c.name}? Configuration and secrets will be removed.`)) return;
    installing = c.id;
    try {
      await api.delete(`/iam/connector-installations/${c.installation.id}/`);
      toast.success("Uninstalled", `${c.name} removed.`);
      await fetchCatalogue();
    } catch {
      toast.error("Action failed", "Could not uninstall.");
    } finally {
      installing = null;
    }
  }

  function openConfigure(c: Connector) {
    editingConnector = c;
    installation = {
      id: c.installation?.id,
      is_enabled: c.installation?.is_enabled ?? true,
      config: { ...((c.installation?.config ?? {}) as Record<string, string>) },
      secrets: {},
    };
  }

  async function saveConfig() {
    if (!editingConnector || !installation) return;
    installing = editingConnector.id;
    try {
      const payload: Record<string, unknown> = {
        is_enabled: installation.is_enabled,
        config: installation.config,
      };
      if (Object.keys(installation.secrets).length > 0) {
        payload.secrets = installation.secrets;
      }
      if (installation.id) {
        await api.patch(`/iam/connector-installations/${installation.id}/`, payload);
      } else {
        payload.connector_id = editingConnector.id;
        await api.post("/iam/connector-installations/", payload);
      }
      toast.success("Saved", "Configuration updated.");
      editingConnector = null;
      installation = null;
      await fetchCatalogue();
    } catch {
      toast.error("Save failed", "Could not save configuration.");
    } finally {
      installing = null;
    }
  }

  $effect(() => { fetchCatalogue(); });
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Third-party Integrations</h1>
    <p class="mt-1 text-sm text-neutral-500">
      Catalogue of available connectors. Install one to enable per-org configuration; deeper
      auth flows (OAuth, API keys) for each connector are added in their respective integration
      phases. Toggle the install state below; "Configure" opens free-form config + secrets.
    </p>
  </div>

  {#if loading}
    <div class="rounded-xl border border-neutral-200 bg-white p-16 text-center">
      <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
    </div>
  {:else if catalogue && catalogue.count > 0}
    {#each catalogue.categories as cat}
      {@const items = catalogue.by_category[cat.value] ?? []}
      {#if items.length > 0}
        <section>
          <h2 class="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-3">{cat.label}</h2>
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {#each items as c}
              <div class="rounded-xl border border-neutral-200 bg-white p-5">
                <div class="flex items-start gap-3 mb-3">
                  <div class="w-10 h-10 rounded-lg bg-neutral-100 flex items-center justify-center text-sm font-bold text-neutral-700 shrink-0">
                    {c.name[0]}
                  </div>
                  <div class="flex-1 min-w-0">
                    <p class="font-semibold text-neutral-900 truncate">{c.name}</p>
                    <p class="text-xs text-neutral-500 truncate">{c.vendor}</p>
                  </div>
                  {#if c.installation}
                    {#if c.installation.is_enabled}
                      <span class="inline-flex items-center gap-1.5 rounded-full bg-green-50 px-2 py-0.5 text-[10px] font-medium text-green-700 shrink-0">
                        <span class="w-1.5 h-1.5 rounded-full bg-green-500"></span>
                        Enabled
                      </span>
                    {:else}
                      <span class="inline-flex items-center rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] font-medium text-neutral-600 shrink-0">
                        Installed
                      </span>
                    {/if}
                  {/if}
                </div>
                <p class="text-xs text-neutral-600 mb-4 min-h-[2.5rem]">{c.description}</p>
                <div class="flex items-center gap-2">
                  {#if c.installation}
                    <button onclick={() => toggleInstall(c)} disabled={installing === c.id}
                      class="rounded-lg border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50 disabled:opacity-50">
                      {c.installation.is_enabled ? "Disable" : "Enable"}
                    </button>
                    <button onclick={() => openConfigure(c)}
                      class="rounded-lg border border-neutral-200 px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50">
                      Configure
                    </button>
                    <button onclick={() => uninstall(c)} disabled={installing === c.id}
                      class="ml-auto rounded-lg px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 disabled:opacity-50">
                      Uninstall
                    </button>
                  {:else}
                    <button onclick={() => toggleInstall(c)} disabled={installing === c.id}
                      class="rounded-lg bg-neutral-800 px-3 py-1.5 text-xs font-semibold text-white hover:bg-neutral-900 disabled:opacity-50">
                      {installing === c.id ? "..." : "Install"}
                    </button>
                  {/if}
                </div>
              </div>
            {/each}
          </div>
        </section>
      {/if}
    {/each}
  {:else}
    <div class="rounded-xl border border-neutral-200 bg-white p-16 text-center">
      <h3 class="text-sm font-semibold text-neutral-800">No connectors in catalogue</h3>
    </div>
  {/if}
</div>

{#if editingConnector && installation}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => { editingConnector = null; installation = null; }} aria-label="Close"></button>
    <div class="relative w-full max-w-lg rounded-2xl bg-white shadow-2xl border border-neutral-200">
      <div class="p-6 border-b border-neutral-100">
        <h2 class="text-lg font-bold text-neutral-800">Configure {editingConnector.name}</h2>
        <p class="mt-1 text-xs text-neutral-500">Free-form config — exact fields per connector are added during the integration phase.</p>
      </div>
      <div class="p-6 space-y-4">
        <label class="flex items-center gap-3 rounded-lg border border-neutral-200 px-4 py-3 cursor-pointer hover:bg-neutral-50">
          <input type="checkbox" bind:checked={installation.is_enabled} class="h-4 w-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-800" />
          <span class="text-sm text-neutral-800">Enabled</span>
        </label>

        <div>
          <label for="conf-cfg" class="block text-sm font-medium text-neutral-700 mb-1.5">Config (JSON)</label>
          <textarea id="conf-cfg" rows="6"
            value={JSON.stringify(installation.config, null, 2)}
            oninput={(e) => {
              try { installation!.config = JSON.parse((e.target as HTMLTextAreaElement).value); }
              catch { /* ignore until valid */ }
            }}
            class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800 resize-none"></textarea>
          <p class="mt-1 text-xs text-neutral-500">Edits only persist when JSON is valid.</p>
        </div>

        <div>
          <label for="conf-sec" class="block text-sm font-medium text-neutral-700 mb-1.5">Secrets (JSON, write-only)</label>
          <textarea id="conf-sec" rows="4"
            placeholder={'{"api_key": "..."}'}
            oninput={(e) => {
              try { installation!.secrets = JSON.parse((e.target as HTMLTextAreaElement).value || "{}"); }
              catch { /* ignore until valid */ }
            }}
            class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800 resize-none"></textarea>
          <p class="mt-1 text-xs text-neutral-500">Existing secrets are masked; only keys you provide here are updated.</p>
        </div>
      </div>
      <div class="p-6 border-t border-neutral-100 flex items-center justify-end gap-3">
        <button onclick={() => { editingConnector = null; installation = null; }} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
        <button onclick={saveConfig} disabled={installing === editingConnector.id}
          class="rounded-lg bg-neutral-800 px-5 py-2 text-sm font-semibold text-white hover:bg-neutral-900 disabled:opacity-60">
          {installing === editingConnector.id ? "Saving..." : "Save"}
        </button>
      </div>
    </div>
  </div>
{/if}

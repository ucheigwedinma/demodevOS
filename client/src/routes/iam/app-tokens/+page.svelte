<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";

  type AppToken = {
    id: number;
    name: string;
    description: string;
    prefix: string;
    scopes: string[];
    expires_at: string | null;
    last_used_at: string | null;
    is_active: boolean;
    created_at: string;
    token?: string;  // present only on create / regenerate
  };

  let tokens = $state<AppToken[]>([]);
  let loading = $state(true);
  let saving = $state(false);
  let regenerating = $state<number | null>(null);

  let editing = $state<AppToken | null>(null);
  let isNew = $state(false);
  let revealedToken = $state("");

  let form = $state({
    name: "",
    description: "",
    scopes: "",
    expires_at: "",
    is_active: true,
  });

  function formatDate(d: string | null): string {
    if (!d) return "—";
    return new Date(d).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  }

  async function fetchTokens() {
    loading = true;
    try {
      const res = await api.get<{ count: number; results: AppToken[] }>("/iam/app-tokens/");
      tokens = res.results;
    } catch {
      tokens = [];
    } finally {
      loading = false;
    }
  }

  function openNew() {
    isNew = true;
    editing = null;
    revealedToken = "";
    form = { name: "", description: "", scopes: "", expires_at: "", is_active: true };
  }

  function openEdit(t: AppToken) {
    isNew = false;
    editing = t;
    revealedToken = "";
    form = {
      name: t.name,
      description: t.description,
      scopes: (t.scopes ?? []).join(", "),
      expires_at: t.expires_at ? t.expires_at.slice(0, 16) : "",
      is_active: t.is_active,
    };
  }

  function close() {
    editing = null;
    isNew = false;
    revealedToken = "";
  }

  async function save() {
    if (!form.name.trim()) {
      toast.error("Validation", "Name is required.");
      return;
    }
    saving = true;
    try {
      const scopes = form.scopes.split(",").map((s) => s.trim()).filter(Boolean);
      const payload: Record<string, unknown> = {
        name: form.name.trim(),
        description: form.description.trim(),
        scopes,
        is_active: form.is_active,
      };
      if (form.expires_at) payload.expires_at = new Date(form.expires_at).toISOString();
      else payload.expires_at = null;

      let res: AppToken;
      if (isNew) {
        res = await api.post<AppToken>("/iam/app-tokens/", payload);
      } else if (editing) {
        res = await api.patch<AppToken>(`/iam/app-tokens/${editing.id}/`, payload);
      } else {
        return;
      }
      if (res.token) {
        revealedToken = res.token;
        toast.success("Created", "Copy your token now — it will not be shown again.");
      } else {
        toast.success("Saved", "Token updated.");
        close();
      }
      editing = res;
      isNew = false;
      await fetchTokens();
    } catch (err) {
      if (err instanceof ApiError) toast.error("Save failed", "Please review the form.");
    } finally {
      saving = false;
    }
  }

  async function regenerate(t: AppToken) {
    if (!confirm(`Regenerate the token for "${t.name}"? The current token will stop working immediately.`)) return;
    regenerating = t.id;
    try {
      const res = await api.post<AppToken>(`/iam/app-tokens/${t.id}/regenerate/`, {});
      editing = res;
      revealedToken = res.token ?? "";
      toast.success("Regenerated", "Copy the new token now.");
      await fetchTokens();
    } catch {
      toast.error("Regenerate failed", "Could not rotate the token.");
    } finally {
      regenerating = null;
    }
  }

  async function remove() {
    if (!editing) return;
    if (!confirm(`Delete token "${editing.name}"?`)) return;
    try {
      await api.delete(`/iam/app-tokens/${editing.id}/`);
      toast.success("Deleted", "Token removed.");
      close();
      await fetchTokens();
    } catch {
      toast.error("Delete failed", "Could not delete the token.");
    }
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text).then(() => toast.success("Copied", "Token copied to clipboard."));
  }

  $effect(() => { fetchTokens(); });
</script>

<div class="space-y-6">
  <div class="flex items-center justify-between gap-4">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900">Application Tokens</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Long-lived bearer tokens for scripted, mobile, or third-party access. Use as
        <code class="text-xs bg-neutral-100 px-1.5 py-0.5 rounded">Authorization: AppToken &lt;token&gt;</code>.
        Tokens are shown once at creation and only their hash is stored — keep them secret.
      </p>
    </div>
    <button onclick={openNew} class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-900">
      Issue token
    </button>
  </div>

  <div class="rounded-lg border border-blue-200 bg-blue-50 p-4 text-xs text-blue-800">
    <p class="font-medium mb-1">Scope enforcement: storage only in v1</p>
    <p>
      Scopes can be assigned and stored, but per-endpoint enforcement is the integration phase.
      Currently a valid app token grants its caller the same access as a normal authenticated org user.
      Treat tokens with the same care as user passwords until scope-aware enforcement lands.
    </p>
  </div>

  <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
    {#if loading}
      <div class="p-16 text-center"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div></div>
    {:else if tokens.length === 0}
      <div class="p-16 text-center">
        <h3 class="text-sm font-semibold text-neutral-800">No tokens yet</h3>
        <p class="mt-1.5 text-sm text-neutral-500">Issue your first token to enable scripted access.</p>
      </div>
    {:else}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50">
            <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Name</th>
            <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Token prefix</th>
            <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Scopes</th>
            <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Last used</th>
            <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Expires</th>
            <th class="px-5 py-3 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
            <th class="px-5 py-3 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each tokens as t}
            <tr class="hover:bg-neutral-50 transition-colors">
              <td class="px-5 py-4">
                <button onclick={() => openEdit(t)} class="font-medium text-neutral-800 hover:underline">{t.name}</button>
                {#if t.description}<p class="text-xs text-neutral-500 truncate max-w-md">{t.description}</p>{/if}
              </td>
              <td class="px-5 py-4 font-mono text-xs text-neutral-600">{t.prefix}…</td>
              <td class="px-5 py-4 text-neutral-600 text-xs">
                {#if t.scopes.length === 0}<span class="italic text-neutral-400">all</span>{:else}{t.scopes.length}{/if}
              </td>
              <td class="px-5 py-4 text-neutral-600 text-xs">{formatDate(t.last_used_at)}</td>
              <td class="px-5 py-4 text-neutral-600 text-xs">{formatDate(t.expires_at)}</td>
              <td class="px-5 py-4 text-center">
                <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium
                             {t.is_active ? 'bg-green-50 text-green-700' : 'bg-neutral-100 text-neutral-500'}">
                  {t.is_active ? "Active" : "Disabled"}
                </span>
              </td>
              <td class="px-5 py-4 text-right">
                <div class="flex items-center justify-end gap-1">
                  <button onclick={() => regenerate(t)} disabled={regenerating === t.id}
                    class="rounded-lg px-3 py-1.5 text-xs font-medium text-yellow-700 hover:bg-yellow-50 disabled:opacity-50">
                    Rotate
                  </button>
                  <button onclick={() => openEdit(t)}
                    class="rounded-lg px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100">
                    Edit
                  </button>
                </div>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>
</div>

{#if editing || isNew}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={close} aria-label="Close"></button>
    <div class="relative w-full max-w-lg rounded-2xl bg-white shadow-2xl border border-neutral-200">
      <div class="p-6 border-b border-neutral-100">
        <h2 class="text-lg font-bold text-neutral-800">{isNew ? "New application token" : `Edit token: ${editing?.name}`}</h2>
      </div>
      <div class="p-6 space-y-4">
        <div>
          <label for="t-name" class="block text-sm font-medium text-neutral-700 mb-1.5">Name <span class="text-red-500">*</span></label>
          <input id="t-name" type="text" bind:value={form.name}
            placeholder="e.g. Mobile app — production"
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
        </div>
        <div>
          <label for="t-desc" class="block text-sm font-medium text-neutral-700 mb-1.5">Description</label>
          <input id="t-desc" type="text" bind:value={form.description}
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
        </div>
        <div>
          <label for="t-scopes" class="block text-sm font-medium text-neutral-700 mb-1.5">Scopes</label>
          <input id="t-scopes" type="text" bind:value={form.scopes}
            placeholder="read:projects, write:invoices"
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          <p class="mt-1 text-xs text-neutral-500">Comma-separated. Empty = full org scope.</p>
        </div>
        <div>
          <label for="t-exp" class="block text-sm font-medium text-neutral-700 mb-1.5">Expires</label>
          <input id="t-exp" type="datetime-local" bind:value={form.expires_at}
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          <p class="mt-1 text-xs text-neutral-500">Empty = no expiry.</p>
        </div>
        <label class="flex items-center gap-3 rounded-lg border border-neutral-200 px-4 py-3 cursor-pointer hover:bg-neutral-50">
          <input type="checkbox" bind:checked={form.is_active} class="h-4 w-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-800" />
          <span class="text-sm text-neutral-800">Active</span>
        </label>

        {#if revealedToken}
          <div class="rounded-lg border-2 border-green-300 bg-green-50 p-4">
            <p class="text-sm font-semibold text-green-900 mb-2">Token — copy this now</p>
            <p class="text-xs text-green-800 mb-3">Stored as a hash. You will not see this value again.</p>
            <div class="flex items-center gap-2">
              <code class="flex-1 rounded bg-white border border-green-300 px-3 py-2 text-xs font-mono break-all">{revealedToken}</code>
              <button onclick={() => copyToClipboard(revealedToken)}
                class="shrink-0 rounded-lg bg-green-700 px-3 py-2 text-xs font-semibold text-white hover:bg-green-800">
                Copy
              </button>
            </div>
          </div>
        {/if}
      </div>
      <div class="p-6 border-t border-neutral-100 flex items-center gap-3 flex-wrap">
        {#if !isNew && editing}
          <button onclick={remove} class="rounded-lg px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 mr-auto">Delete</button>
        {:else}<div class="mr-auto"></div>{/if}
        <button onclick={close} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Close</button>
        <button onclick={save} disabled={saving}
          class="rounded-lg bg-neutral-800 px-5 py-2 text-sm font-semibold text-white hover:bg-neutral-900 disabled:opacity-60">
          {saving ? "Saving..." : (isNew ? "Issue token" : "Save")}
        </button>
      </div>
    </div>
  </div>
{/if}

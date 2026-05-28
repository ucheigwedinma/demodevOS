<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";

  type Webhook = {
    id: number;
    name: string;
    url: string;
    events: string[];
    is_active: boolean;
    secret_set: boolean;
    last_delivery_at: string | null;
    last_delivery_status: string;
    last_delivery_message: string;
    delivery_count: number;
    failure_count: number;
    created_at: string;
    secret?: string;  // present only on create / rotate response
  };
  type Delivery = {
    id: number;
    event_name: string;
    status: "pending" | "delivered" | "failed";
    response_code: number | null;
    response_body: string;
    attempt_number: number;
    error_message: string;
    created_at: string;
    delivered_at: string | null;
  };

  let webhooks = $state<Webhook[]>([]);
  let loading = $state(true);
  let saving = $state(false);

  let editing = $state<Webhook | null>(null);
  let isNew = $state(false);
  let revealedSecret = $state("");
  let testing = $state(false);
  let lastTest = $state<{ ok: boolean; response_code?: number; response_body?: string; error?: string } | null>(null);
  let deliveries = $state<Delivery[]>([]);
  let deliveriesLoading = $state(false);

  let form = $state({
    name: "",
    url: "",
    events: "",  // comma-separated
    is_active: true,
    rotate_secret: false,
  });

  function formatDate(d: string | null): string {
    if (!d) return "—";
    return new Date(d).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
  }

  async function fetchWebhooks() {
    loading = true;
    try {
      const res = await api.get<{ count: number; results: Webhook[] }>("/iam/webhooks/");
      webhooks = res.results;
    } catch {
      webhooks = [];
    } finally {
      loading = false;
    }
  }

  function openNew() {
    isNew = true;
    editing = null;
    revealedSecret = "";
    lastTest = null;
    deliveries = [];
    form = { name: "", url: "", events: "", is_active: true, rotate_secret: false };
  }

  function openEdit(w: Webhook) {
    isNew = false;
    editing = w;
    revealedSecret = "";
    lastTest = null;
    form = {
      name: w.name,
      url: w.url,
      events: (w.events ?? []).join(", "),
      is_active: w.is_active,
      rotate_secret: false,
    };
    fetchDeliveries(w.id);
  }

  function close() {
    editing = null;
    isNew = false;
    revealedSecret = "";
    lastTest = null;
  }

  async function save() {
    if (!form.name.trim() || !form.url.trim()) {
      toast.error("Validation", "Name and URL are required.");
      return;
    }
    saving = true;
    try {
      const events = form.events.split(",").map((s) => s.trim()).filter(Boolean);
      const payload: Record<string, unknown> = {
        name: form.name.trim(),
        url: form.url.trim(),
        events,
        is_active: form.is_active,
      };
      if (!isNew && form.rotate_secret) payload.rotate_secret = true;

      let res: Webhook;
      if (isNew) {
        res = await api.post<Webhook>("/iam/webhooks/", payload);
      } else if (editing) {
        res = await api.patch<Webhook>(`/iam/webhooks/${editing.id}/`, payload);
      } else {
        return;
      }
      if (res.secret) {
        revealedSecret = res.secret;
        toast.success("Saved", isNew ? "Webhook created — copy the secret now." : "Secret rotated — copy the new value now.");
      } else {
        toast.success("Saved", "Webhook updated.");
        close();
      }
      editing = res;
      isNew = false;
      form.rotate_secret = false;
      await fetchWebhooks();
    } catch (err) {
      if (err instanceof ApiError) toast.error("Save failed", "Please review the form.");
    } finally {
      saving = false;
    }
  }

  async function runTest() {
    if (!editing) return;
    testing = true;
    lastTest = null;
    try {
      const res = await api.post<{ ok: boolean; response_code?: number; response_body?: string; error?: string }>(
        `/iam/webhooks/${editing.id}/test/`, {},
      );
      lastTest = res;
      await fetchDeliveries(editing.id);
      await fetchWebhooks();
    } catch (err) {
      if (err instanceof ApiError && err.data) {
        lastTest = err.data as typeof lastTest;
      } else {
        lastTest = { ok: false, error: "Unknown error" };
      }
    } finally {
      testing = false;
    }
  }

  async function fetchDeliveries(id: number) {
    deliveriesLoading = true;
    try {
      const res = await api.get<{ count: number; results: Delivery[] }>(`/iam/webhooks/${id}/deliveries/`);
      deliveries = res.results;
    } catch {
      deliveries = [];
    } finally {
      deliveriesLoading = false;
    }
  }

  async function remove() {
    if (!editing) return;
    if (!confirm(`Delete webhook "${editing.name}"?`)) return;
    try {
      await api.delete(`/iam/webhooks/${editing.id}/`);
      toast.success("Deleted", "Webhook removed.");
      close();
      await fetchWebhooks();
    } catch {
      toast.error("Delete failed", "Could not delete the webhook.");
    }
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text).then(() => toast.success("Copied", "Secret copied to clipboard."));
  }

  $effect(() => { fetchWebhooks(); });
</script>

<div class="space-y-6">
  <div class="flex items-center justify-between gap-4">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900">Webhooks</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Outbound webhooks for system events. Each delivery is signed with HMAC-SHA256 in the
        <code class="text-xs bg-neutral-100 px-1.5 py-0.5 rounded">X-DeveloperOS-Signature</code> header.
        Live event-driven delivery is the next phase; the Test button below sends a payload
        synchronously so you can validate the receiver during setup.
      </p>
    </div>
    <button onclick={openNew} class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-900">
      Add webhook
    </button>
  </div>

  <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
    {#if loading}
      <div class="p-16 text-center"><div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div></div>
    {:else if webhooks.length === 0}
      <div class="p-16 text-center">
        <h3 class="text-sm font-semibold text-neutral-800">No webhooks yet</h3>
        <p class="mt-1.5 text-sm text-neutral-500">Add a webhook to start receiving events.</p>
      </div>
    {:else}
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50">
            <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Name</th>
            <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">URL</th>
            <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Events</th>
            <th class="px-5 py-3 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Deliveries</th>
            <th class="px-5 py-3 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each webhooks as w}
            <tr class="hover:bg-neutral-50 cursor-pointer transition-colors" onclick={() => openEdit(w)}>
              <td class="px-5 py-4 font-medium text-neutral-800">{w.name}</td>
              <td class="px-5 py-4 text-neutral-600 font-mono text-xs truncate max-w-xs">{w.url}</td>
              <td class="px-5 py-4 text-neutral-600 text-xs">
                {#if w.events.length === 0}
                  <span class="italic text-neutral-400">all events</span>
                {:else}
                  {w.events.length} event{w.events.length === 1 ? "" : "s"}
                {/if}
              </td>
              <td class="px-5 py-4 text-center text-neutral-700">
                {w.delivery_count}
                {#if w.failure_count > 0}
                  <span class="text-red-600">· {w.failure_count} failed</span>
                {/if}
              </td>
              <td class="px-5 py-4 text-center">
                <span class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium
                             {w.is_active ? 'bg-green-50 text-green-700' : 'bg-neutral-100 text-neutral-500'}">
                  <span class="w-1.5 h-1.5 rounded-full {w.is_active ? 'bg-green-500' : 'bg-neutral-400'}"></span>
                  {w.is_active ? "Active" : "Disabled"}
                </span>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </div>
</div>

{#if editing || isNew}
  <div class="fixed inset-0 z-50 flex">
    <button class="flex-1 bg-black/40 backdrop-blur-sm" onclick={close} aria-label="Close"></button>
    <div class="w-full max-w-2xl bg-white shadow-2xl border-l border-neutral-200 overflow-y-auto">
      <div class="p-6 border-b border-neutral-100 flex items-start justify-between">
        <h2 class="text-lg font-bold text-neutral-900">{isNew ? "New webhook" : editing?.name}</h2>
        <button onclick={close} class="text-neutral-400 hover:text-neutral-600 text-xl leading-none">×</button>
      </div>

      <div class="p-6 space-y-5">
        <div>
          <label for="wh-name" class="block text-sm font-medium text-neutral-700 mb-1.5">Name <span class="text-red-500">*</span></label>
          <input id="wh-name" type="text" bind:value={form.name}
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
        </div>
        <div>
          <label for="wh-url" class="block text-sm font-medium text-neutral-700 mb-1.5">Target URL <span class="text-red-500">*</span></label>
          <input id="wh-url" type="text" bind:value={form.url}
            placeholder="https://example.com/webhooks/developer-os"
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800" />
        </div>
        <div>
          <label for="wh-events" class="block text-sm font-medium text-neutral-700 mb-1.5">Subscribed events</label>
          <input id="wh-events" type="text" bind:value={form.events}
            placeholder="user.created, access_request.approved"
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          <p class="mt-1 text-xs text-neutral-500">Comma-separated. Empty = subscribe to all events.</p>
        </div>
        <label class="flex items-center gap-3 rounded-lg border border-neutral-200 px-4 py-3 cursor-pointer hover:bg-neutral-50">
          <input type="checkbox" bind:checked={form.is_active} class="h-4 w-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-800" />
          <span class="text-sm text-neutral-800">Active</span>
        </label>

        {#if !isNew && editing}
          <label class="flex items-center gap-3 rounded-lg border border-yellow-200 bg-yellow-50 px-4 py-3 cursor-pointer">
            <input type="checkbox" bind:checked={form.rotate_secret} class="h-4 w-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-800" />
            <div>
              <p class="text-sm font-medium text-yellow-900">Rotate signing secret on save</p>
              <p class="text-xs text-yellow-800">Receivers using the old secret will start failing verification once you save.</p>
            </div>
          </label>
        {/if}

        {#if revealedSecret}
          <div class="rounded-lg border-2 border-green-300 bg-green-50 p-4">
            <p class="text-sm font-semibold text-green-900 mb-2">Secret — copy this now</p>
            <p class="text-xs text-green-800 mb-3">Stored as a hash. You will not see this value again.</p>
            <div class="flex items-center gap-2">
              <code class="flex-1 rounded bg-white border border-green-300 px-3 py-2 text-xs font-mono break-all">{revealedSecret}</code>
              <button onclick={() => copyToClipboard(revealedSecret)}
                class="shrink-0 rounded-lg bg-green-700 px-3 py-2 text-xs font-semibold text-white hover:bg-green-800">
                Copy
              </button>
            </div>
          </div>
        {/if}

        {#if !isNew && editing}
          <div class="border-t border-neutral-100 pt-5">
            <div class="flex items-center justify-between mb-3">
              <h3 class="text-sm font-semibold text-neutral-800">Recent deliveries</h3>
              <button onclick={runTest} disabled={testing}
                class="rounded-lg bg-neutral-800 px-3 py-1.5 text-xs font-semibold text-white hover:bg-neutral-900 disabled:opacity-50">
                {testing ? "Sending..." : "Send test"}
              </button>
            </div>

            {#if lastTest}
              <div class="rounded-lg p-3 mb-3 text-xs
                          {lastTest.ok ? 'bg-green-50 border border-green-200 text-green-800' : 'bg-red-50 border border-red-200 text-red-800'}">
                <p class="font-semibold">{lastTest.ok ? "Delivered" : "Failed"}</p>
                {#if lastTest.response_code}<p>HTTP {lastTest.response_code}</p>{/if}
                {#if lastTest.response_body}<p class="mt-1 font-mono">{lastTest.response_body.slice(0, 200)}</p>{/if}
                {#if lastTest.error}<p class="mt-1">{lastTest.error}</p>{/if}
              </div>
            {/if}

            {#if deliveriesLoading}
              <p class="text-sm text-neutral-400">Loading…</p>
            {:else if deliveries.length === 0}
              <p class="text-sm text-neutral-500">No deliveries yet.</p>
            {:else}
              <ul class="space-y-1.5">
                {#each deliveries as d}
                  <li class="flex items-center justify-between text-xs px-3 py-2 rounded border border-neutral-200">
                    <div class="min-w-0">
                      <p class="font-medium text-neutral-700">{d.event_name}</p>
                      <p class="text-neutral-500">{formatDate(d.created_at)}</p>
                    </div>
                    <div class="text-right shrink-0 ml-3">
                      <span class="inline-flex items-center rounded-full px-2 py-0.5 font-medium
                                   {d.status === 'delivered' ? 'bg-green-50 text-green-700' :
                                    d.status === 'failed' ? 'bg-red-50 text-red-700' :
                                    'bg-blue-50 text-blue-700'}">
                        {d.status}
                      </span>
                      {#if d.response_code}
                        <p class="text-[10px] text-neutral-500 mt-0.5">{d.response_code}</p>
                      {/if}
                    </div>
                  </li>
                {/each}
              </ul>
            {/if}
          </div>
        {/if}
      </div>

      <div class="p-6 border-t border-neutral-100 flex items-center gap-2 flex-wrap">
        {#if !isNew && editing}
          <button onclick={remove} class="rounded-lg px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 mr-auto">Delete</button>
        {:else}<div class="mr-auto"></div>{/if}
        <button onclick={close} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Close</button>
        <button onclick={save} disabled={saving}
          class="rounded-lg bg-neutral-800 px-5 py-2 text-sm font-semibold text-white hover:bg-neutral-900 disabled:opacity-60">
          {saving ? "Saving..." : (isNew ? "Create" : "Save")}
        </button>
      </div>
    </div>
  </div>
{/if}

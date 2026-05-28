<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import AccessPolicyList from "$lib/components/AccessPolicyList.svelte";
  import type { Policy } from "$lib/components/AccessPolicyList.svelte";

  let listRefresh = $state(0);
  let showModal = $state(false);
  let editing = $state<Policy | null>(null);
  let saving = $state(false);

  let form = $state({
    name: "",
    description: "",
    cidrs: "",  // newline-separated
    action: "deny" as "deny" | "allow" | "require_mfa",
    message: "Access denied — your IP is not on the organisation's allowlist.",
    priority: 100,
    is_active: false,
  });

  // Dev fill
  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);
  const SAMPLES = [
    { name: "Lagos office allowlist", cidrs: "102.89.32.0/24\n102.89.45.10/32" },
    { name: "VPN gateway only", cidrs: "10.20.30.0/24" },
    { name: "Corporate edge ranges", cidrs: "203.0.113.0/24\n198.51.100.0/24" },
  ];
  let devIdx = 0;
  function devFill() {
    const s = SAMPLES[devIdx % SAMPLES.length];
    devIdx++;
    form.name = s.name;
    form.cidrs = s.cidrs;
    form.description = "Restrict access to the listed CIDR ranges.";
  }

  function openCreate() {
    editing = null;
    form = {
      name: "", description: "", cidrs: "",
      action: "deny", message: "Access denied — your IP is not on the organisation's allowlist.",
      priority: 100, is_active: false,
    };
    showModal = true;
  }

  function openEdit(p: Policy) {
    editing = p;
    const cond = (p.conditions ?? []).find((c) => c.condition_type === "ip_restriction");
    const action = (p.actions ?? []).find((a) => a.is_active);
    form = {
      name: p.name,
      description: p.description ?? "",
      cidrs: ((cond?.value?.cidrs as string[]) ?? []).join("\n"),
      action: (action?.action_type ?? "deny") as "deny" | "allow" | "require_mfa",
      message: action?.message ?? "",
      priority: p.priority,
      is_active: p.is_active,
    };
    showModal = true;
  }

  async function save() {
    if (!form.name.trim()) {
      toast.error("Validation", "Name is required.");
      return;
    }
    const cidrs = form.cidrs.split("\n").map((s) => s.trim()).filter(Boolean);
    if (cidrs.length === 0) {
      toast.error("Validation", "Add at least one CIDR.");
      return;
    }
    saving = true;
    try {
      const payload = {
        kind: "ip_restrictions",
        name: form.name.trim(),
        description: form.description.trim(),
        priority: form.priority,
        is_active: form.is_active,
        conditions: [
          { condition_type: "ip_restriction", operator: "cidr", value: { cidrs }, sort_order: 0, is_active: true },
        ],
        actions: [
          { action_type: form.action, message: form.message, sort_order: 0, is_active: true },
        ],
      };
      if (editing) {
        await api.patch(`/iam/access-policies/${editing.id}/`, payload);
        toast.success("Updated", "Policy saved.");
      } else {
        await api.post("/iam/access-policies/", payload);
        toast.success("Created", "Policy added.");
      }
      showModal = false;
      listRefresh++;
    } catch (err) {
      if (err instanceof ApiError) toast.error("Save failed", "Please review the form.");
    } finally {
      saving = false;
    }
  }
</script>

<div class="space-y-6">
  <div class="flex items-center justify-between gap-4">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900">IP Restrictions</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Allow access only from the listed CIDR ranges. The engine reads <code class="text-xs bg-neutral-100 px-1.5 py-0.5 rounded">X-Forwarded-For</code>
        when present (assumes a trusted proxy).
      </p>
    </div>
    <button onclick={openCreate}
      class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-900 transition-colors">
      New IP rule
    </button>
  </div>

  <AccessPolicyList kind="ip_restrictions" onPolicyEdit={openEdit} refreshKey={listRefresh} />
</div>

{#if showModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (showModal = false)} aria-label="Close"></button>
    <div class="relative w-full max-w-lg rounded-2xl bg-white shadow-2xl border border-neutral-200">
      <div class="p-6 border-b border-neutral-100">
        <h2 class="text-lg font-bold text-neutral-800">{editing ? "Edit IP rule" : "New IP rule"}</h2>
      </div>
      <div class="p-6 space-y-4">
        <div>
          <label for="ip-name" class="block text-sm font-medium text-neutral-700 mb-1.5">Name <span class="text-red-500">*</span></label>
          <input id="ip-name" type="text" bind:value={form.name}
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
        </div>
        <div>
          <label for="ip-desc" class="block text-sm font-medium text-neutral-700 mb-1.5">Description</label>
          <input id="ip-desc" type="text" bind:value={form.description}
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
        </div>
        <div>
          <label for="ip-cidrs" class="block text-sm font-medium text-neutral-700 mb-1.5">CIDR ranges <span class="text-red-500">*</span></label>
          <textarea id="ip-cidrs" rows="4" bind:value={form.cidrs}
            placeholder="10.0.0.0/8&#10;192.168.1.0/24"
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800 resize-none"></textarea>
          <p class="mt-1 text-xs text-neutral-500">One per line. Both IPv4 and IPv6 supported.</p>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="ip-action" class="block text-sm font-medium text-neutral-700 mb-1.5">Action when IP doesn't match</label>
            <select id="ip-action" bind:value={form.action}
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800">
              <option value="deny">Deny</option>
              <option value="require_mfa">Require MFA step-up</option>
              <option value="allow">Allow (warning)</option>
            </select>
          </div>
          <div>
            <label for="ip-priority" class="block text-sm font-medium text-neutral-700 mb-1.5">Priority</label>
            <input id="ip-priority" type="number" bind:value={form.priority} min="0" max="10000"
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          </div>
        </div>
        <div>
          <label for="ip-message" class="block text-sm font-medium text-neutral-700 mb-1.5">Message shown to user</label>
          <input id="ip-message" type="text" bind:value={form.message}
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
        </div>
        <label class="flex items-center gap-3 rounded-lg border border-neutral-200 px-4 py-3 cursor-pointer hover:bg-neutral-50">
          <input type="checkbox" bind:checked={form.is_active} class="h-4 w-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-800" />
          <span class="text-sm text-neutral-800">Enable immediately (only effective when middleware is wired)</span>
        </label>
      </div>
      <div class="p-6 border-t border-neutral-100 flex items-center gap-3">
        {#if isDev}
          <button onclick={devFill} class="rounded-lg bg-orange-500 px-3 py-2.5 text-sm font-medium text-white hover:bg-orange-600 mr-auto">Dev Fill</button>
        {/if}
        <button onclick={() => (showModal = false)} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 ml-auto">Cancel</button>
        <button onclick={save} disabled={saving}
          class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-900 disabled:opacity-60">
          {saving ? "Saving..." : (editing ? "Update" : "Create")}
        </button>
      </div>
    </div>
  </div>
{/if}

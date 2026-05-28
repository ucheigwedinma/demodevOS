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
    mode: "allow" as "allow" | "deny",
    countries: "",  // comma-separated ISO-2 codes
    action: "deny" as "deny" | "require_mfa" | "allow",
    message: "Access denied — your location is not permitted.",
    priority: 100,
    is_active: false,
  });

  function openCreate() {
    editing = null;
    form = {
      name: "", description: "", mode: "allow", countries: "",
      action: "deny", message: "Access denied — your location is not permitted.",
      priority: 100, is_active: false,
    };
    showModal = true;
  }

  function openEdit(p: Policy) {
    editing = p;
    const cond = (p.conditions ?? []).find((c) => c.condition_type === "location");
    const action = (p.actions ?? []).find((a) => a.is_active);
    const v = (cond?.value ?? {}) as Record<string, unknown>;
    const allowed = (v.allowed_countries as string[]) ?? [];
    const denied = (v.denied_countries as string[]) ?? [];
    const mode: "allow" | "deny" = denied.length > allowed.length ? "deny" : "allow";
    form = {
      name: p.name,
      description: p.description ?? "",
      mode,
      countries: (mode === "allow" ? allowed : denied).join(", "),
      action: (action?.action_type ?? "deny") as "deny" | "require_mfa" | "allow",
      message: action?.message ?? "",
      priority: p.priority,
      is_active: p.is_active,
    };
    showModal = true;
  }

  async function save() {
    if (!form.name.trim()) { toast.error("Validation", "Name is required."); return; }
    const codes = form.countries.split(",").map((s) => s.trim().toUpperCase()).filter(Boolean);
    if (codes.length === 0) { toast.error("Validation", "Add at least one country code."); return; }
    saving = true;
    try {
      const value: Record<string, unknown> = form.mode === "allow"
        ? { allowed_countries: codes }
        : { denied_countries: codes };
      const payload = {
        kind: "location_restrictions",
        name: form.name.trim(),
        description: form.description.trim(),
        priority: form.priority,
        is_active: form.is_active,
        conditions: [{ condition_type: "location", operator: "in", value, sort_order: 0, is_active: true }],
        actions: [{ action_type: form.action, message: form.message, sort_order: 0, is_active: true }],
      };
      if (editing) await api.patch(`/iam/access-policies/${editing.id}/`, payload);
      else await api.post("/iam/access-policies/", payload);
      toast.success("Saved", "Policy saved.");
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
      <h1 class="text-2xl font-bold text-neutral-900">Location Restrictions</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Country-level allowlist or denylist. Reads <code class="text-xs bg-neutral-100 px-1.5 py-0.5 rounded">CF-IPCountry</code>
        / <code class="text-xs bg-neutral-100 px-1.5 py-0.5 rounded">X-Country</code> headers; without those, location-based policies are no-ops (don't block).
      </p>
    </div>
    <button onclick={openCreate} class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-900">New location rule</button>
  </div>

  <AccessPolicyList kind="location_restrictions" onPolicyEdit={openEdit} refreshKey={listRefresh} />
</div>

{#if showModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (showModal = false)} aria-label="Close"></button>
    <div class="relative w-full max-w-lg rounded-2xl bg-white shadow-2xl border border-neutral-200">
      <div class="p-6 border-b border-neutral-100">
        <h2 class="text-lg font-bold text-neutral-800">{editing ? "Edit location rule" : "New location rule"}</h2>
      </div>
      <div class="p-6 space-y-4">
        <div>
          <label for="loc-name" class="block text-sm font-medium text-neutral-700 mb-1.5">Name <span class="text-red-500">*</span></label>
          <input id="loc-name" type="text" bind:value={form.name}
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
        </div>
        <div>
          <label for="loc-desc" class="block text-sm font-medium text-neutral-700 mb-1.5">Description</label>
          <input id="loc-desc" type="text" bind:value={form.description}
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
        </div>
        <div>
          <label class="block text-sm font-medium text-neutral-700 mb-2">Mode</label>
          <div class="grid grid-cols-2 gap-2">
            <button type="button" onclick={() => (form.mode = "allow")}
              class="rounded-lg border px-3 py-2.5 text-sm transition-colors
                     {form.mode === 'allow' ? 'border-neutral-800 bg-neutral-50 font-semibold text-neutral-900' : 'border-neutral-200 text-neutral-600 hover:border-neutral-400'}">
              Allowlist (only these countries)
            </button>
            <button type="button" onclick={() => (form.mode = "deny")}
              class="rounded-lg border px-3 py-2.5 text-sm transition-colors
                     {form.mode === 'deny' ? 'border-neutral-800 bg-neutral-50 font-semibold text-neutral-900' : 'border-neutral-200 text-neutral-600 hover:border-neutral-400'}">
              Denylist (block these countries)
            </button>
          </div>
        </div>
        <div>
          <label for="loc-countries" class="block text-sm font-medium text-neutral-700 mb-1.5">Country codes <span class="text-red-500">*</span></label>
          <input id="loc-countries" type="text" bind:value={form.countries}
            placeholder="NG, GB, US, CA"
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          <p class="mt-1 text-xs text-neutral-500">ISO 3166-1 alpha-2 codes, comma-separated.</p>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="loc-action" class="block text-sm font-medium text-neutral-700 mb-1.5">Action when blocked</label>
            <select id="loc-action" bind:value={form.action}
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800">
              <option value="deny">Deny</option>
              <option value="require_mfa">Require MFA step-up</option>
              <option value="allow">Allow (warning)</option>
            </select>
          </div>
          <div>
            <label for="loc-priority" class="block text-sm font-medium text-neutral-700 mb-1.5">Priority</label>
            <input id="loc-priority" type="number" bind:value={form.priority} min="0" max="10000"
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          </div>
        </div>
        <div>
          <label for="loc-msg" class="block text-sm font-medium text-neutral-700 mb-1.5">Message</label>
          <input id="loc-msg" type="text" bind:value={form.message}
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
        </div>
        <label class="flex items-center gap-3 rounded-lg border border-neutral-200 px-4 py-3 cursor-pointer hover:bg-neutral-50">
          <input type="checkbox" bind:checked={form.is_active} class="h-4 w-4 rounded border-neutral-300 text-neutral-900 focus:ring-neutral-800" />
          <span class="text-sm text-neutral-800">Enable immediately</span>
        </label>
      </div>
      <div class="p-6 border-t border-neutral-100 flex items-center justify-end gap-3">
        <button onclick={() => (showModal = false)} class="rounded-lg border border-neutral-200 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
        <button onclick={save} disabled={saving}
          class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-900 disabled:opacity-60">
          {saving ? "Saving..." : (editing ? "Update" : "Create")}
        </button>
      </div>
    </div>
  </div>
{/if}

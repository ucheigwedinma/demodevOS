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
    blocked_substrings: "",
    required_substrings: "",
    action: "deny" as "deny" | "require_mfa" | "allow",
    message: "Access denied — device not permitted.",
    priority: 100,
    is_active: false,
  });

  function openCreate() {
    editing = null;
    form = {
      name: "", description: "",
      blocked_substrings: "", required_substrings: "",
      action: "deny", message: "Access denied — device not permitted.",
      priority: 100, is_active: false,
    };
    showModal = true;
  }

  function openEdit(p: Policy) {
    editing = p;
    const cond = (p.conditions ?? []).find((c) => c.condition_type === "device_restriction");
    const action = (p.actions ?? []).find((a) => a.is_active);
    const v = (cond?.value ?? {}) as Record<string, unknown>;
    form = {
      name: p.name,
      description: p.description ?? "",
      blocked_substrings: ((v.blocked_user_agents as string[]) ?? []).join(", "),
      required_substrings: ((v.required_substrings as string[]) ?? []).join(", "),
      action: (action?.action_type ?? "deny") as "deny" | "require_mfa" | "allow",
      message: action?.message ?? "",
      priority: p.priority,
      is_active: p.is_active,
    };
    showModal = true;
  }

  async function save() {
    if (!form.name.trim()) { toast.error("Validation", "Name is required."); return; }
    const blocked = form.blocked_substrings.split(",").map((s) => s.trim()).filter(Boolean);
    const required = form.required_substrings.split(",").map((s) => s.trim()).filter(Boolean);
    if (blocked.length === 0 && required.length === 0) {
      toast.error("Validation", "Add at least one blocked or required substring.");
      return;
    }
    saving = true;
    try {
      const payload = {
        kind: "device_restrictions",
        name: form.name.trim(),
        description: form.description.trim(),
        priority: form.priority,
        is_active: form.is_active,
        conditions: [{
          condition_type: "device_restriction",
          operator: "in",
          value: { blocked_user_agents: blocked, required_substrings: required },
          sort_order: 0, is_active: true,
        }],
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
      <h1 class="text-2xl font-bold text-neutral-900">Device Restrictions</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Block or require specific user-agent substrings. Useful for blocking outdated browsers
        or requiring corporate device markers in the UA. For real device-fingerprint binding,
        a frontend SDK is needed (future phase).
      </p>
    </div>
    <button onclick={openCreate} class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-900">New device rule</button>
  </div>

  <AccessPolicyList kind="device_restrictions" onPolicyEdit={openEdit} refreshKey={listRefresh} />
</div>

{#if showModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (showModal = false)} aria-label="Close"></button>
    <div class="relative w-full max-w-lg rounded-2xl bg-white shadow-2xl border border-neutral-200">
      <div class="p-6 border-b border-neutral-100">
        <h2 class="text-lg font-bold text-neutral-800">{editing ? "Edit device rule" : "New device rule"}</h2>
      </div>
      <div class="p-6 space-y-4">
        <div>
          <label for="d-name" class="block text-sm font-medium text-neutral-700 mb-1.5">Name <span class="text-red-500">*</span></label>
          <input id="d-name" type="text" bind:value={form.name}
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
        </div>
        <div>
          <label for="d-desc" class="block text-sm font-medium text-neutral-700 mb-1.5">Description</label>
          <input id="d-desc" type="text" bind:value={form.description}
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
        </div>
        <div>
          <label for="d-block" class="block text-sm font-medium text-neutral-700 mb-1.5">Blocked UA substrings</label>
          <input id="d-block" type="text" bind:value={form.blocked_substrings}
            placeholder="MSIE 6, OldBrowser, Bot"
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          <p class="mt-1 text-xs text-neutral-500">Comma-separated. Match is case-insensitive substring.</p>
        </div>
        <div>
          <label for="d-req" class="block text-sm font-medium text-neutral-700 mb-1.5">Required UA substrings</label>
          <input id="d-req" type="text" bind:value={form.required_substrings}
            placeholder="AcmeCorpBrowser, ManagedDevice"
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          <p class="mt-1 text-xs text-neutral-500">If set, request must contain at least one of these. Comma-separated.</p>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="d-action" class="block text-sm font-medium text-neutral-700 mb-1.5">Action when blocked</label>
            <select id="d-action" bind:value={form.action}
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800">
              <option value="deny">Deny</option>
              <option value="require_mfa">Require MFA step-up</option>
              <option value="allow">Allow (warning)</option>
            </select>
          </div>
          <div>
            <label for="d-priority" class="block text-sm font-medium text-neutral-700 mb-1.5">Priority</label>
            <input id="d-priority" type="number" bind:value={form.priority} min="0" max="10000"
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          </div>
        </div>
        <div>
          <label for="d-msg" class="block text-sm font-medium text-neutral-700 mb-1.5">Message</label>
          <input id="d-msg" type="text" bind:value={form.message}
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

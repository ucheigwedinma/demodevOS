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
    max_minutes: 480,
    idle_minutes: 30,
    action: "require_mfa" as "deny" | "require_mfa",
    message: "Session expired — please re-authenticate.",
    priority: 100,
    is_active: false,
  });

  function openCreate() {
    editing = null;
    form = {
      name: "", description: "", max_minutes: 480, idle_minutes: 30,
      action: "require_mfa", message: "Session expired — please re-authenticate.",
      priority: 100, is_active: false,
    };
    showModal = true;
  }

  function openEdit(p: Policy) {
    editing = p;
    const cond = (p.conditions ?? []).find((c) => c.condition_type === "mfa_requirement");
    const action = (p.actions ?? []).find((a) => a.is_active);
    const params = (action?.parameters ?? {}) as Record<string, unknown>;
    form = {
      name: p.name,
      description: p.description ?? "",
      max_minutes: (params.max_minutes as number) ?? 480,
      idle_minutes: (params.idle_minutes as number) ?? 30,
      action: (action?.action_type ?? "require_mfa") as "deny" | "require_mfa",
      message: action?.message ?? "",
      priority: p.priority,
      is_active: p.is_active,
    };
    showModal = true;
  }

  async function save() {
    if (!form.name.trim()) { toast.error("Validation", "Name is required."); return; }
    saving = true;
    try {
      const payload = {
        kind: "session_duration",
        name: form.name.trim(),
        description: form.description.trim(),
        priority: form.priority,
        is_active: form.is_active,
        conditions: [{
          condition_type: "mfa_requirement",
          operator: "eq",
          value: { required: true },
          sort_order: 0, is_active: true,
        }],
        actions: [{
          action_type: form.action,
          parameters: { max_minutes: form.max_minutes, idle_minutes: form.idle_minutes },
          message: form.message,
          sort_order: 0, is_active: true,
        }],
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
      <h1 class="text-2xl font-bold text-neutral-900">Session Duration</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Cap how long a sign-in session may last and how long it may sit idle. Enforcement is at the
        JWT layer; this page captures the policy. Issuance-side enforcement code that reads these
        values is part of the integration phase.
      </p>
    </div>
    <button onclick={openCreate} class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-900">New duration rule</button>
  </div>

  <AccessPolicyList kind="session_duration" onPolicyEdit={openEdit} refreshKey={listRefresh} />
</div>

{#if showModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (showModal = false)} aria-label="Close"></button>
    <div class="relative w-full max-w-lg rounded-2xl bg-white shadow-2xl border border-neutral-200">
      <div class="p-6 border-b border-neutral-100">
        <h2 class="text-lg font-bold text-neutral-800">{editing ? "Edit duration rule" : "New duration rule"}</h2>
      </div>
      <div class="p-6 space-y-4">
        <div>
          <label for="s-name" class="block text-sm font-medium text-neutral-700 mb-1.5">Name <span class="text-red-500">*</span></label>
          <input id="s-name" type="text" bind:value={form.name}
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
        </div>
        <div>
          <label for="s-desc" class="block text-sm font-medium text-neutral-700 mb-1.5">Description</label>
          <input id="s-desc" type="text" bind:value={form.description}
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="s-max" class="block text-sm font-medium text-neutral-700 mb-1.5">Max session minutes</label>
            <input id="s-max" type="number" min="5" max="10080" bind:value={form.max_minutes}
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          </div>
          <div>
            <label for="s-idle" class="block text-sm font-medium text-neutral-700 mb-1.5">Idle timeout minutes</label>
            <input id="s-idle" type="number" min="1" max="1440" bind:value={form.idle_minutes}
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="s-action" class="block text-sm font-medium text-neutral-700 mb-1.5">When session expires</label>
            <select id="s-action" bind:value={form.action}
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800">
              <option value="require_mfa">Require MFA re-verification</option>
              <option value="deny">Force re-login</option>
            </select>
          </div>
          <div>
            <label for="s-priority" class="block text-sm font-medium text-neutral-700 mb-1.5">Priority</label>
            <input id="s-priority" type="number" bind:value={form.priority} min="0" max="10000"
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          </div>
        </div>
        <div>
          <label for="s-msg" class="block text-sm font-medium text-neutral-700 mb-1.5">Message</label>
          <input id="s-msg" type="text" bind:value={form.message}
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

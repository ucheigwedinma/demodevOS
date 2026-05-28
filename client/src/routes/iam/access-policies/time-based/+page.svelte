<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import AccessPolicyList from "$lib/components/AccessPolicyList.svelte";
  import type { Policy } from "$lib/components/AccessPolicyList.svelte";

  let listRefresh = $state(0);
  let showModal = $state(false);
  let editing = $state<Policy | null>(null);
  let saving = $state(false);

  const WEEKDAYS = [
    { v: 0, label: "Mon" }, { v: 1, label: "Tue" }, { v: 2, label: "Wed" },
    { v: 3, label: "Thu" }, { v: 4, label: "Fri" }, { v: 5, label: "Sat" }, { v: 6, label: "Sun" },
  ];

  let form = $state({
    name: "",
    description: "",
    start_hour: 8,
    end_hour: 18,
    weekdays: [0, 1, 2, 3, 4],
    timezone: "UTC",
    action: "deny" as "deny" | "require_mfa" | "allow",
    message: "Access denied — outside permitted hours.",
    priority: 100,
    is_active: false,
  });

  function toggleDay(d: number) {
    if (form.weekdays.includes(d)) {
      form.weekdays = form.weekdays.filter((x) => x !== d);
    } else {
      form.weekdays = [...form.weekdays, d].sort();
    }
  }

  function openCreate() {
    editing = null;
    form = {
      name: "", description: "",
      start_hour: 8, end_hour: 18,
      weekdays: [0, 1, 2, 3, 4],
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
      action: "deny", message: "Access denied — outside permitted hours.",
      priority: 100, is_active: false,
    };
    showModal = true;
  }

  function openEdit(p: Policy) {
    editing = p;
    const cond = (p.conditions ?? []).find((c) => c.condition_type === "time_restriction");
    const action = (p.actions ?? []).find((a) => a.is_active);
    const v = (cond?.value ?? {}) as Record<string, unknown>;
    form = {
      name: p.name,
      description: p.description ?? "",
      start_hour: (v.start_hour as number) ?? 8,
      end_hour: (v.end_hour as number) ?? 18,
      weekdays: (v.allowed_weekdays as number[]) ?? [0, 1, 2, 3, 4],
      timezone: (v.timezone as string) ?? "UTC",
      action: (action?.action_type ?? "deny") as "deny" | "require_mfa" | "allow",
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
        kind: "time_based",
        name: form.name.trim(),
        description: form.description.trim(),
        priority: form.priority,
        is_active: form.is_active,
        conditions: [
          {
            condition_type: "time_restriction",
            operator: "between",
            value: {
              start_hour: form.start_hour,
              end_hour: form.end_hour,
              allowed_weekdays: form.weekdays,
              timezone: form.timezone,
            },
            sort_order: 0, is_active: true,
          },
        ],
        actions: [
          { action_type: form.action, message: form.message, sort_order: 0, is_active: true },
        ],
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
      <h1 class="text-2xl font-bold text-neutral-900">Time-based Access</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Allow access only during certain hours and weekdays. Window may cross midnight (e.g. 22:00 → 06:00).
      </p>
    </div>
    <button onclick={openCreate} class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white hover:bg-neutral-900">New time rule</button>
  </div>

  <AccessPolicyList kind="time_based" onPolicyEdit={openEdit} refreshKey={listRefresh} />
</div>

{#if showModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (showModal = false)} aria-label="Close"></button>
    <div class="relative w-full max-w-lg rounded-2xl bg-white shadow-2xl border border-neutral-200">
      <div class="p-6 border-b border-neutral-100">
        <h2 class="text-lg font-bold text-neutral-800">{editing ? "Edit time rule" : "New time rule"}</h2>
      </div>
      <div class="p-6 space-y-4">
        <div>
          <label for="t-name" class="block text-sm font-medium text-neutral-700 mb-1.5">Name <span class="text-red-500">*</span></label>
          <input id="t-name" type="text" bind:value={form.name}
            placeholder="e.g. Business hours only — Lagos office"
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
        </div>
        <div>
          <label for="t-desc" class="block text-sm font-medium text-neutral-700 mb-1.5">Description</label>
          <input id="t-desc" type="text" bind:value={form.description}
            class="w-full rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
        </div>
        <div class="grid grid-cols-3 gap-3">
          <div>
            <label for="t-start" class="block text-xs font-medium text-neutral-700 mb-1">Start hour</label>
            <input id="t-start" type="number" min="0" max="23" bind:value={form.start_hour}
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          </div>
          <div>
            <label for="t-end" class="block text-xs font-medium text-neutral-700 mb-1">End hour</label>
            <input id="t-end" type="number" min="0" max="23" bind:value={form.end_hour}
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          </div>
          <div>
            <label for="t-tz" class="block text-xs font-medium text-neutral-700 mb-1">Timezone</label>
            <input id="t-tz" type="text" bind:value={form.timezone}
              placeholder="Africa/Lagos"
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium text-neutral-700 mb-2">Allowed weekdays</label>
          <div class="flex gap-2">
            {#each WEEKDAYS as d}
              <button type="button" onclick={() => toggleDay(d.v)}
                class="rounded-lg px-3 py-2 text-xs font-medium transition-colors
                       {form.weekdays.includes(d.v) ? 'bg-neutral-800 text-white' : 'bg-white border border-neutral-200 text-neutral-600 hover:bg-neutral-50'}">
                {d.label}
              </button>
            {/each}
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label for="t-action" class="block text-sm font-medium text-neutral-700 mb-1.5">Action outside window</label>
            <select id="t-action" bind:value={form.action}
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800">
              <option value="deny">Deny</option>
              <option value="require_mfa">Require MFA step-up</option>
              <option value="allow">Allow (warning)</option>
            </select>
          </div>
          <div>
            <label for="t-priority" class="block text-sm font-medium text-neutral-700 mb-1.5">Priority</label>
            <input id="t-priority" type="number" bind:value={form.priority} min="0" max="10000"
              class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800" />
          </div>
        </div>
        <div>
          <label for="t-msg" class="block text-sm font-medium text-neutral-700 mb-1.5">Message</label>
          <input id="t-msg" type="text" bind:value={form.message}
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

<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";

  type Action = "allow" | "deny" | "require_mfa" | "require_office_ip" | "require_corporate_device";
  type Condition = {
    id: number;
    condition_type: string;
    operator: string;
    value: Record<string, unknown>;
    sort_order: number;
    is_active: boolean;
  };
  type ActionRow = {
    id: number;
    action_type: Action;
    parameters: Record<string, unknown>;
    message: string;
    sort_order: number;
    is_active: boolean;
  };
  export type Policy = {
    id: number;
    key: string;
    kind: string;
    kind_display: string;
    name: string;
    description: string;
    priority: number;
    is_active: boolean;
    condition_count: number;
    action_summary: string;
    created_at: string;
    updated_at: string;
    conditions?: Condition[];
    actions?: ActionRow[];
  };

  type Props = {
    kind?: string;
    onPolicyEdit?: (p: Policy) => void;
    refreshKey?: number;
    showKindColumn?: boolean;
  };

  let { kind, onPolicyEdit, refreshKey = 0, showKindColumn = false }: Props = $props();

  let policies = $state<Policy[]>([]);
  let loading = $state(true);
  let saving = $state<number | null>(null);
  let testResult = $state<{ policyId: number; data: unknown } | null>(null);
  let confirmDelete = $state<Policy | null>(null);

  function actionClasses(action: string): string {
    return ({
      allow: "bg-green-50 text-green-700",
      deny: "bg-red-50 text-red-700",
      require_mfa: "bg-blue-50 text-blue-700",
      require_office_ip: "bg-yellow-50 text-yellow-700",
      require_corporate_device: "bg-yellow-50 text-yellow-700",
    } as Record<string, string>)[action] ?? "bg-neutral-100 text-neutral-600";
  }

  async function fetchPolicies() {
    loading = true;
    try {
      const params: Record<string, string> = {};
      if (kind) params.kind = kind;
      const res = await api.get<{ count: number; results: Policy[] }>(
        "/iam/access-policies/", params,
      );
      policies = res.results;
    } catch {
      policies = [];
    } finally {
      loading = false;
    }
  }

  async function toggleActive(p: Policy) {
    saving = p.id;
    try {
      await api.patch(`/iam/access-policies/${p.id}/`, { is_active: !p.is_active });
      toast.success(p.is_active ? "Disabled" : "Enabled", `${p.name} ${p.is_active ? "disabled" : "enabled"}.`);
      await fetchPolicies();
    } catch {
      toast.error("Toggle failed", "Could not update policy state.");
    } finally {
      saving = null;
    }
  }

  async function runTest(p: Policy) {
    saving = p.id;
    testResult = null;
    try {
      const res = await api.post(`/iam/access-policies/${p.id}/test/`, {});
      testResult = { policyId: p.id, data: res };
    } catch {
      toast.error("Test failed", "Could not evaluate the policy.");
    } finally {
      saving = null;
    }
  }

  async function doDelete() {
    if (!confirmDelete) return;
    saving = confirmDelete.id;
    try {
      await api.delete(`/iam/access-policies/${confirmDelete.id}/`);
      toast.success("Deleted", "Policy removed.");
      confirmDelete = null;
      await fetchPolicies();
    } catch {
      toast.error("Delete failed", "Could not delete policy.");
    } finally {
      saving = null;
    }
  }

  $effect(() => { void refreshKey; void kind; fetchPolicies(); });

  // Expose a refresh fn for the parent page
  export function refresh() { fetchPolicies(); }
</script>

<div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
  {#if loading}
    <div class="p-16 text-center">
      <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
    </div>
  {:else if policies.length === 0}
    <div class="p-16 text-center">
      <h3 class="text-sm font-semibold text-neutral-800">No policies yet</h3>
      <p class="mt-1.5 text-sm text-neutral-500">Use the button above to add your first one.</p>
    </div>
  {:else}
    <table class="w-full text-sm">
      <thead>
        <tr class="border-b border-neutral-200 bg-neutral-50">
          <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Name</th>
          {#if showKindColumn}
            <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Kind</th>
          {/if}
          <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Action</th>
          <th class="px-5 py-3 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Priority</th>
          <th class="px-5 py-3 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Conditions</th>
          <th class="px-5 py-3 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Status</th>
          <th class="px-5 py-3 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Actions</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-neutral-100">
        {#each policies as p}
          <tr class="hover:bg-neutral-50 transition-colors">
            <td class="px-5 py-4">
              <button onclick={() => onPolicyEdit?.(p)} class="font-medium text-neutral-800 hover:text-neutral-900 underline-offset-2 hover:underline text-left">
                {p.name}
              </button>
              {#if p.description}
                <p class="text-xs text-neutral-500 max-w-md truncate">{p.description}</p>
              {/if}
            </td>
            {#if showKindColumn}
              <td class="px-5 py-4 text-neutral-600 text-xs">{p.kind_display}</td>
            {/if}
            <td class="px-5 py-4">
              <span class="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium {actionClasses(p.action_summary.toLowerCase().split(' ')[0] || 'allow')}">
                {p.action_summary || "—"}
              </span>
            </td>
            <td class="px-5 py-4 text-center text-neutral-700">{p.priority}</td>
            <td class="px-5 py-4 text-center text-neutral-700">{p.condition_count}</td>
            <td class="px-5 py-4 text-center">
              <button onclick={() => toggleActive(p)} disabled={saving === p.id}
                class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors disabled:opacity-50
                       {p.is_active ? 'bg-green-50 text-green-700 hover:bg-green-100' : 'bg-neutral-100 text-neutral-500 hover:bg-neutral-200'}">
                <span class="w-1.5 h-1.5 rounded-full {p.is_active ? 'bg-green-500' : 'bg-neutral-400'}"></span>
                {p.is_active ? "Active" : "Disabled"}
              </button>
            </td>
            <td class="px-5 py-4 text-right">
              <div class="flex items-center justify-end gap-1">
                <button onclick={() => runTest(p)} disabled={saving === p.id}
                  class="rounded-lg px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 transition-colors disabled:opacity-50">
                  Test
                </button>
                {#if onPolicyEdit}
                  <button onclick={() => onPolicyEdit(p)}
                    class="rounded-lg px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 transition-colors">
                    Edit
                  </button>
                {/if}
                <button onclick={() => (confirmDelete = p)}
                  class="rounded-lg px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 transition-colors">
                  Delete
                </button>
              </div>
            </td>
          </tr>
          {#if testResult && testResult.policyId === p.id}
            {@const r = testResult.data as { all_active_conditions_matched: boolean; would_act: boolean; decision_action: string; conditions: Array<{ condition_type: string; matched: boolean | null; error: string }> }}
            <tr class="bg-blue-50/40">
              <td colspan={showKindColumn ? 7 : 6} class="px-5 py-3 text-xs">
                <p class="font-semibold text-neutral-800">
                  Test result:
                  <span class="font-normal">
                    {r.all_active_conditions_matched ? "All conditions matched — would " + r.decision_action : "Conditions did NOT all match — policy would skip"}
                  </span>
                  <button onclick={() => (testResult = null)} class="ml-3 text-neutral-400 hover:text-neutral-600">×</button>
                </p>
                <ul class="mt-1.5 space-y-0.5">
                  {#each r.conditions as c}
                    <li class="flex items-center gap-2">
                      {#if c.matched === true}
                        <span class="text-green-600 font-bold">✓</span>
                      {:else if c.matched === false}
                        <span class="text-red-600 font-bold">✗</span>
                      {:else}
                        <span class="text-neutral-400">?</span>
                      {/if}
                      <span class="text-neutral-700">{c.condition_type}</span>
                      {#if c.error}<span class="text-red-600">— error: {c.error}</span>{/if}
                    </li>
                  {/each}
                </ul>
              </td>
            </tr>
          {/if}
        {/each}
      </tbody>
    </table>
  {/if}
</div>

{#if confirmDelete}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <button class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick={() => (confirmDelete = null)} aria-label="Close"></button>
    <div class="relative w-full max-w-sm rounded-2xl bg-white shadow-2xl border border-neutral-200 p-6">
      <h3 class="text-lg font-bold text-neutral-800">Delete policy</h3>
      <p class="mt-2 text-sm text-neutral-600">Delete <strong>{confirmDelete.name}</strong>? This cannot be undone.</p>
      <div class="mt-6 flex items-center justify-end gap-3">
        <button onclick={() => (confirmDelete = null)} class="rounded-lg border border-neutral-200 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50">Cancel</button>
        <button onclick={doDelete} class="rounded-lg bg-red-600 px-5 py-2 text-sm font-semibold text-white hover:bg-red-700">Delete</button>
      </div>
    </div>
  </div>
{/if}

<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { RoleListItem, PaginatedResponse } from "$lib/types";

  type DataScope = { id: number; key: string; label: string; description: string };
  type RoleScope = {
    id: number;
    role_id: number;
    role_name: string;
    data_scope_id: number;
    data_scope_key: string;
    data_scope_label: string;
    module: string;
    sub_module: string;
    created_at: string;
  };

  let roles = $state<RoleListItem[]>([]);
  let dataScopes = $state<DataScope[]>([]);
  let assignments = $state<RoleScope[]>([]);
  let loading = $state(true);
  let saving = $state(false);

  let selectedRoleId = $state<number | null>(null);
  let selectedRole = $derived(roles.find((r) => r.id === selectedRoleId) ?? null);

  // Add-assignment form
  let form = $state({
    data_scope_id: null as number | null,
    module: "",
    sub_module: "",
  });

  async function load() {
    loading = true;
    try {
      const [rolesRes, scopesRes] = await Promise.all([
        api.get<PaginatedResponse<RoleListItem>>("/settings/roles/", { page_size: "200", ordering: "name" }),
        api.get<{ count: number; results: DataScope[] }>("/iam/data-scopes/"),
      ]);
      roles = rolesRes.results;
      dataScopes = scopesRes.results;
    } catch {
      roles = []; dataScopes = [];
    } finally {
      loading = false;
    }
  }

  async function fetchAssignments(roleId: number) {
    try {
      const res = await api.get<{ count: number; results: RoleScope[] }>(
        "/iam/role-scopes/", { role_id: String(roleId) },
      );
      assignments = res.results;
    } catch {
      assignments = [];
    }
  }

  function onRoleChange(e: Event) {
    const v = (e.target as HTMLSelectElement).value;
    if (!v) { selectedRoleId = null; assignments = []; return; }
    const id = parseInt(v, 10);
    if (!isNaN(id)) {
      selectedRoleId = id;
      fetchAssignments(id);
      form = { data_scope_id: null, module: "", sub_module: "" };
    }
  }

  async function addAssignment() {
    if (!selectedRoleId || !form.data_scope_id) {
      toast.error("Validation", "Pick a role and a scope.");
      return;
    }
    saving = true;
    try {
      await api.post("/iam/role-scopes/", {
        role_id: selectedRoleId,
        data_scope_id: form.data_scope_id,
        module: form.module.trim(),
        sub_module: form.sub_module.trim(),
      });
      toast.success("Added", "Scope assigned.");
      form = { data_scope_id: null, module: "", sub_module: "" };
      await fetchAssignments(selectedRoleId);
    } catch (err) {
      if (err instanceof ApiError) toast.error("Add failed", "Please review the form.");
    } finally {
      saving = false;
    }
  }

  async function removeAssignment(rs: RoleScope) {
    if (!confirm(`Remove ${rs.data_scope_label} scope from this role?`)) return;
    try {
      await api.delete(`/iam/role-scopes/${rs.id}/`);
      toast.success("Removed", "Assignment cleared.");
      if (selectedRoleId) await fetchAssignments(selectedRoleId);
    } catch {
      toast.error("Remove failed", "Could not unassign.");
    }
  }

  $effect(() => { load(); });
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Data Access Scope</h1>
    <p class="mt-1 text-sm text-neutral-500">
      Define what subset of data each role sees — by self, department, project, or organization.
      Assignments are per-(module, sub-module): the same role can have a tighter scope in HR than
      in projects. Enforcement is opt-in per view (call <code class="text-xs bg-neutral-100 px-1.5 py-0.5 rounded">scoped_*_queryset_for_user</code>);
      see <code class="text-xs bg-neutral-100 px-1.5 py-0.5 rounded">apps.settings.data_scopes</code>.
    </p>
  </div>

  <div class="rounded-xl border border-neutral-200 bg-white p-5">
    <label for="ds-role" class="block text-sm font-medium text-neutral-700 mb-2">Pick a role</label>
    <select id="ds-role" onchange={onRoleChange} value={selectedRoleId ?? ""}
      class="w-full max-w-md rounded-lg border border-neutral-300 px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800">
      <option value="">— Pick a role —</option>
      {#if loading}<option disabled>Loading…</option>{/if}
      {#each roles as r}<option value={r.id}>{r.name}{r.is_system ? " · System" : ""}</option>{/each}
    </select>
  </div>

  {#if selectedRoleId !== null && selectedRole}
    <div class="rounded-xl border border-neutral-200 bg-white p-5">
      <h2 class="text-sm font-semibold text-neutral-800 mb-3">Add scope assignment</h2>
      <div class="grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
        <div>
          <label for="ds-scope" class="block text-xs font-medium text-neutral-700 mb-1">Scope <span class="text-red-500">*</span></label>
          <select id="ds-scope" bind:value={form.data_scope_id}
            class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800">
            <option value={null}>— Pick a scope —</option>
            {#each dataScopes as ds}<option value={ds.id}>{ds.label}</option>{/each}
          </select>
        </div>
        <div>
          <label for="ds-module" class="block text-xs font-medium text-neutral-700 mb-1">Module</label>
          <input id="ds-module" type="text" bind:value={form.module} placeholder="(global)"
            class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800" />
        </div>
        <div>
          <label for="ds-sub" class="block text-xs font-medium text-neutral-700 mb-1">Sub-module</label>
          <input id="ds-sub" type="text" bind:value={form.sub_module} placeholder="(any)"
            class="w-full rounded-lg border border-neutral-300 px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-neutral-800" />
        </div>
        <button onclick={addAssignment} disabled={saving}
          class="rounded-lg bg-neutral-800 px-4 py-2 text-sm font-semibold text-white hover:bg-neutral-900 disabled:opacity-60">
          {saving ? "Adding..." : "Add scope"}
        </button>
      </div>
      <p class="mt-2 text-xs text-neutral-500">
        Module / sub-module empty = global default scope for this role. With both set, the assignment
        only applies to that specific area; useful when one role needs different visibility per module.
      </p>
    </div>

    <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
      <div class="px-5 py-3 border-b border-neutral-100">
        <h2 class="text-sm font-semibold text-neutral-800">Current assignments for {selectedRole.name}</h2>
      </div>
      {#if assignments.length === 0}
        <div class="p-12 text-center">
          <p class="text-sm text-neutral-500">No scope assignments yet — defaults apply (typically: organization-wide visibility).</p>
        </div>
      {:else}
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-neutral-200 bg-neutral-50">
              <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Scope</th>
              <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Module</th>
              <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Sub-module</th>
              <th class="px-5 py-3 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each assignments as a}
              <tr class="hover:bg-neutral-50">
                <td class="px-5 py-4 font-medium text-neutral-800">
                  {a.data_scope_label}
                  <span class="ml-2 text-xs text-neutral-400 font-mono">({a.data_scope_key})</span>
                </td>
                <td class="px-5 py-4 text-neutral-600 font-mono text-xs">{a.module || "—"}</td>
                <td class="px-5 py-4 text-neutral-600 font-mono text-xs">{a.sub_module || "—"}</td>
                <td class="px-5 py-4 text-right">
                  <button onclick={() => removeAssignment(a)}
                    class="rounded-lg px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50">
                    Remove
                  </button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </div>
  {:else}
    <div class="rounded-xl border border-dashed border-neutral-200 bg-neutral-50 p-12 text-center">
      <p class="text-sm font-medium text-neutral-700">Pick a role to manage its data-access scope</p>
      <p class="mt-1 text-xs text-neutral-500">
        Each role can have one or more scope assignments — one default plus per-module overrides.
      </p>
    </div>
  {/if}

  <div class="rounded-lg border border-neutral-200 bg-neutral-50 p-4 text-xs text-neutral-600">
    <p class="font-medium text-neutral-700 mb-1">Available scopes</p>
    {#if dataScopes.length === 0}
      <p class="italic">Loading…</p>
    {:else}
      <ul class="space-y-1">
        {#each dataScopes as ds}
          <li><strong class="text-neutral-700">{ds.label}</strong>
            <span class="text-neutral-400 font-mono ml-1">({ds.key})</span>
            {#if ds.description} — {ds.description}{/if}
          </li>
        {/each}
      </ul>
    {/if}
  </div>
</div>

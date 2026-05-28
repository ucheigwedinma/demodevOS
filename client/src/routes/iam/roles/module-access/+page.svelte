<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    RoleDetail,
    RoleListItem,
    PaginatedResponse,
    PermissionRegistryModule,
  } from "$lib/types";

  type ModuleSummary = {
    key: string;
    label: string;
    sub_module_count: number;
    permission_count: number;
    granted: number;
    state: "none" | "partial" | "full";
  };

  let roles = $state<RoleListItem[]>([]);
  let loadingRoles = $state(true);
  let selectedRoleId = $state<number | null>(null);

  let registry = $state<PermissionRegistryModule[]>([]);
  let role = $state<RoleDetail | null>(null);
  let loadingRole = $state(false);
  let saving = $state<string | null>(null);

  // Map of permission key (sub_module.action) → granted
  let permState = $state<Record<string, boolean>>({});

  function permKey(subModule: string, action: string): string {
    return `${subModule}.${action}`;
  }

  // Compute per-module summary from current permState
  let moduleSummaries = $derived.by<ModuleSummary[]>(() => {
    return registry.map((m) => {
      let total = 0;
      let granted = 0;
      for (const sm of m.sub_modules) {
        for (const a of sm.actions) {
          total++;
          if (permState[permKey(sm.key, a)]) granted++;
        }
      }
      const state: ModuleSummary["state"] =
        granted === 0 ? "none" : granted === total ? "full" : "partial";
      return {
        key: m.module,
        label: m.label,
        sub_module_count: m.sub_modules.length,
        permission_count: total,
        granted,
        state,
      };
    });
  });

  async function loadRoles() {
    try {
      const res = await api.get<PaginatedResponse<RoleListItem>>("/settings/roles/", {
        page_size: "200",
        ordering: "name",
      });
      roles = res.results;
    } catch {
      toast.error("Load failed", "Could not load roles.");
    } finally {
      loadingRoles = false;
    }
  }

  async function loadRolePermissions(roleId: number) {
    loadingRole = true;
    try {
      const [roleData, registryData] = await Promise.all([
        api.get<RoleDetail>(`/settings/roles/${roleId}/`),
        registry.length
          ? Promise.resolve(registry)
          : api.get<PermissionRegistryModule[]>("/settings/permission-registry/"),
      ]);

      role = roleData;
      registry = registryData;

      const state: Record<string, boolean> = {};
      for (const mod of registryData) {
        for (const sm of mod.sub_modules) {
          for (const action of sm.actions) {
            state[permKey(sm.key, action)] = false;
          }
        }
      }
      for (const perm of roleData.permissions) {
        const key = permKey(perm.sub_module, perm.action);
        if (key in state) state[key] = true;
      }
      permState = state;
    } catch {
      toast.error("Load failed", "Could not load role permissions.");
    } finally {
      loadingRole = false;
    }
  }

  async function setModuleState(moduleKey: string, granted: boolean) {
    if (!role) return;
    const mod = registry.find((m) => m.module === moduleKey);
    if (!mod) return;

    saving = moduleKey;
    try {
      // Build the FULL matrix to send (current state + the toggled module)
      const next = { ...permState };
      for (const sm of mod.sub_modules) {
        for (const a of sm.actions) {
          next[permKey(sm.key, a)] = granted;
        }
      }

      const permissions: { sub_module: string; action: string; granted: boolean }[] = [];
      for (const m of registry) {
        for (const sm of m.sub_modules) {
          for (const a of sm.actions) {
            permissions.push({
              sub_module: sm.key,
              action: a,
              granted: next[permKey(sm.key, a)],
            });
          }
        }
      }

      await api.put(`/settings/roles/${role.id}/permissions/`, { permissions });
      permState = next;
      toast.success(
        granted ? "Module enabled" : "Module disabled",
        `"${mod.label}" ${granted ? "granted" : "revoked"} for ${role.name}.`,
      );
    } catch {
      toast.error("Save failed", "Could not update module access.");
    } finally {
      saving = null;
    }
  }

  function onRoleChange(e: Event) {
    const value = (e.target as HTMLSelectElement).value;
    if (!value) {
      selectedRoleId = null;
      role = null;
      permState = {};
      return;
    }
    const id = parseInt(value, 10);
    if (!isNaN(id)) {
      selectedRoleId = id;
      loadRolePermissions(id);
    }
  }

  $effect(() => {
    loadRoles();
  });
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Module Access</h1>
    <p class="mt-1 text-sm text-neutral-500">
      Coarse-grained module on/off per role. For finer control over individual features, see
      <a href="/iam/roles/feature-access" class="underline underline-offset-2 hover:text-neutral-800">Feature Access</a>;
      for per-action control, see the
      <a href="/iam/roles/permission-matrix" class="underline underline-offset-2 hover:text-neutral-800">Permission Matrix</a>.
    </p>
  </div>

  <!-- Role picker -->
  <div class="rounded-xl border border-neutral-200 bg-white p-5">
    <label for="role-picker" class="block text-sm font-medium text-neutral-700 mb-2">
      Select role
    </label>
    <select id="role-picker" onchange={onRoleChange} value={selectedRoleId ?? ""}
      class="w-full max-w-md rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800">
      <option value="">— Pick a role —</option>
      {#if loadingRoles}
        <option disabled>Loading…</option>
      {:else}
        {#each roles as r}
          <option value={r.id}>{r.name}{r.is_system ? " · System" : ""}</option>
        {/each}
      {/if}
    </select>
  </div>

  {#if selectedRoleId !== null}
    {#if loadingRole}
      <div class="rounded-xl border border-neutral-200 bg-white p-16 text-center">
        <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
      </div>
    {:else if role}
      <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
        <div class="px-5 py-4 border-b border-neutral-100 flex items-center justify-between">
          <div>
            <h2 class="text-sm font-semibold text-neutral-800">Modules for {role.name}</h2>
            <p class="text-xs text-neutral-500 mt-0.5">{moduleSummaries.length} modules · toggle to grant or revoke all permissions in a module</p>
          </div>
        </div>
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-neutral-200 bg-neutral-50">
              <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Module</th>
              <th class="px-5 py-3 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Sub-modules</th>
              <th class="px-5 py-3 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Permissions granted</th>
              <th class="px-5 py-3 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">State</th>
              <th class="px-5 py-3 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each moduleSummaries as m}
              <tr class="hover:bg-neutral-50 transition-colors">
                <td class="px-5 py-4 font-medium text-neutral-800">{m.label}</td>
                <td class="px-5 py-4 text-center text-neutral-600">{m.sub_module_count}</td>
                <td class="px-5 py-4 text-center">
                  <span class="text-neutral-700">{m.granted}</span>
                  <span class="text-neutral-400"> / {m.permission_count}</span>
                </td>
                <td class="px-5 py-4 text-center">
                  {#if m.state === "full"}
                    <span class="inline-flex items-center rounded-full bg-green-50 px-2.5 py-0.5 text-xs font-medium text-green-700">Full</span>
                  {:else if m.state === "partial"}
                    <span class="inline-flex items-center rounded-full bg-yellow-50 px-2.5 py-0.5 text-xs font-medium text-yellow-700">Partial</span>
                  {:else}
                    <span class="inline-flex items-center rounded-full bg-neutral-100 px-2.5 py-0.5 text-xs font-medium text-neutral-600">None</span>
                  {/if}
                </td>
                <td class="px-5 py-4 text-right">
                  <div class="flex items-center justify-end gap-2">
                    {#if m.state !== "full"}
                      <button onclick={() => setModuleState(m.key, true)} disabled={saving === m.key}
                        class="rounded-lg px-3 py-1.5 text-xs font-medium text-green-700 bg-green-50 hover:bg-green-100 transition-colors disabled:opacity-50">
                        {saving === m.key ? "..." : "Grant all"}
                      </button>
                    {/if}
                    {#if m.state !== "none"}
                      <button onclick={() => setModuleState(m.key, false)} disabled={saving === m.key}
                        class="rounded-lg px-3 py-1.5 text-xs font-medium text-red-600 bg-red-50 hover:bg-red-100 transition-colors disabled:opacity-50">
                        {saving === m.key ? "..." : "Revoke all"}
                      </button>
                    {/if}
                    <a href="/iam/roles/feature-access?role={role.id}&module={m.key}"
                      class="rounded-lg px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-100 transition-colors">
                      Features →
                    </a>
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  {:else}
    <div class="rounded-xl border border-dashed border-neutral-200 bg-neutral-50 p-12 text-center">
      <p class="text-sm font-medium text-neutral-700">Pick a role to begin</p>
      <p class="mt-1 text-xs text-neutral-500">
        Select a role above to see which platform modules it can access.
      </p>
    </div>
  {/if}
</div>

<script lang="ts">
  import { page } from "$app/stores";
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    RoleDetail,
    RoleListItem,
    PaginatedResponse,
    PermissionRegistryModule,
  } from "$lib/types";

  type FeatureSummary = {
    key: string;
    label: string;
    action_count: number;
    granted: number;
    state: "none" | "partial" | "full";
  };

  let roles = $state<RoleListItem[]>([]);
  let loadingRoles = $state(true);
  let selectedRoleId = $state<number | null>(null);
  let selectedModuleKey = $state<string | null>(null);

  let registry = $state<PermissionRegistryModule[]>([]);
  let role = $state<RoleDetail | null>(null);
  let loadingRole = $state(false);
  let saving = $state<string | null>(null);

  let permState = $state<Record<string, boolean>>({});

  function permKey(subModule: string, action: string): string {
    return `${subModule}.${action}`;
  }

  let selectedModule = $derived(
    selectedModuleKey ? registry.find((m) => m.module === selectedModuleKey) ?? null : null,
  );

  let featureSummaries = $derived.by<FeatureSummary[]>(() => {
    if (!selectedModule) return [];
    return selectedModule.sub_modules.map((sm) => {
      let total = sm.actions.length;
      let granted = 0;
      for (const a of sm.actions) {
        if (permState[permKey(sm.key, a)]) granted++;
      }
      const state: FeatureSummary["state"] =
        granted === 0 ? "none" : granted === total ? "full" : "partial";
      return {
        key: sm.key,
        label: sm.label,
        action_count: total,
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

  async function setFeatureState(featureKey: string, granted: boolean) {
    if (!role || !selectedModule) return;
    const sm = selectedModule.sub_modules.find((s) => s.key === featureKey);
    if (!sm) return;

    saving = featureKey;
    try {
      const next = { ...permState };
      for (const a of sm.actions) {
        next[permKey(sm.key, a)] = granted;
      }

      const permissions: { sub_module: string; action: string; granted: boolean }[] = [];
      for (const m of registry) {
        for (const sub of m.sub_modules) {
          for (const a of sub.actions) {
            permissions.push({
              sub_module: sub.key,
              action: a,
              granted: next[permKey(sub.key, a)],
            });
          }
        }
      }

      await api.put(`/settings/roles/${role.id}/permissions/`, { permissions });
      permState = next;
      toast.success(
        granted ? "Feature enabled" : "Feature disabled",
        `"${sm.label}" ${granted ? "granted" : "revoked"} for ${role.name}.`,
      );
    } catch {
      toast.error("Save failed", "Could not update feature access.");
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

  function onModuleChange(e: Event) {
    const value = (e.target as HTMLSelectElement).value;
    selectedModuleKey = value || null;
  }

  // Read query params for deep-linking from module-access ("Features →")
  $effect(() => {
    loadRoles().then(() => {
      const roleQp = $page.url.searchParams.get("role");
      const moduleQp = $page.url.searchParams.get("module");
      if (roleQp) {
        const id = parseInt(roleQp, 10);
        if (!isNaN(id)) {
          selectedRoleId = id;
          loadRolePermissions(id);
        }
      }
      if (moduleQp) {
        selectedModuleKey = moduleQp;
      }
    });
  });
</script>

<div class="space-y-6">
  <div>
    <h1 class="text-2xl font-bold text-neutral-900">Feature Access</h1>
    <p class="mt-1 text-sm text-neutral-500">
      Toggle whole features (sub-modules) on/off per role. Coarser than the
      <a href="/iam/roles/permission-matrix" class="underline underline-offset-2 hover:text-neutral-800">Permission Matrix</a>,
      finer than
      <a href="/iam/roles/module-access" class="underline underline-offset-2 hover:text-neutral-800">Module Access</a>.
    </p>
  </div>

  <!-- Pickers -->
  <div class="rounded-xl border border-neutral-200 bg-white p-5 grid grid-cols-1 md:grid-cols-2 gap-4">
    <div>
      <label for="role-picker" class="block text-sm font-medium text-neutral-700 mb-2">Role</label>
      <select id="role-picker" onchange={onRoleChange} value={selectedRoleId ?? ""}
        class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800">
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
    <div>
      <label for="module-picker" class="block text-sm font-medium text-neutral-700 mb-2">Module</label>
      <select id="module-picker" onchange={onModuleChange} value={selectedModuleKey ?? ""}
        disabled={!registry.length}
        class="w-full rounded-lg border border-neutral-300 bg-white px-3.5 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 disabled:bg-neutral-50 disabled:text-neutral-400">
        <option value="">— Pick a module —</option>
        {#each registry as m}
          <option value={m.module}>{m.label}</option>
        {/each}
      </select>
    </div>
  </div>

  {#if selectedRoleId === null || !selectedModuleKey}
    <div class="rounded-xl border border-dashed border-neutral-200 bg-neutral-50 p-12 text-center">
      <p class="text-sm font-medium text-neutral-700">Pick a role and a module</p>
      <p class="mt-1 text-xs text-neutral-500">
        You'll then see the features (sub-modules) within the chosen module and can grant or revoke
        each one for the chosen role.
      </p>
    </div>
  {:else if loadingRole}
    <div class="rounded-xl border border-neutral-200 bg-white p-16 text-center">
      <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
    </div>
  {:else if role && selectedModule}
    <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
      <div class="px-5 py-4 border-b border-neutral-100">
        <h2 class="text-sm font-semibold text-neutral-800">
          Features in {selectedModule.label} for {role.name}
        </h2>
        <p class="text-xs text-neutral-500 mt-0.5">
          {featureSummaries.length} features · toggle to grant or revoke all actions within a feature
        </p>
      </div>
      {#if featureSummaries.length === 0}
        <div class="p-12 text-center text-sm text-neutral-500">
          This module has no sub-modules registered.
        </div>
      {:else}
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-neutral-200 bg-neutral-50">
              <th class="px-5 py-3 text-left font-medium text-neutral-400 text-xs uppercase tracking-wider">Feature</th>
              <th class="px-5 py-3 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">Actions</th>
              <th class="px-5 py-3 text-center font-medium text-neutral-400 text-xs uppercase tracking-wider">State</th>
              <th class="px-5 py-3 text-right font-medium text-neutral-400 text-xs uppercase tracking-wider">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each featureSummaries as f}
              <tr class="hover:bg-neutral-50 transition-colors">
                <td class="px-5 py-4 font-medium text-neutral-800">{f.label}</td>
                <td class="px-5 py-4 text-center">
                  <span class="text-neutral-700">{f.granted}</span>
                  <span class="text-neutral-400"> / {f.action_count}</span>
                </td>
                <td class="px-5 py-4 text-center">
                  {#if f.state === "full"}
                    <span class="inline-flex items-center rounded-full bg-green-50 px-2.5 py-0.5 text-xs font-medium text-green-700">Full</span>
                  {:else if f.state === "partial"}
                    <span class="inline-flex items-center rounded-full bg-yellow-50 px-2.5 py-0.5 text-xs font-medium text-yellow-700">Partial</span>
                  {:else}
                    <span class="inline-flex items-center rounded-full bg-neutral-100 px-2.5 py-0.5 text-xs font-medium text-neutral-600">None</span>
                  {/if}
                </td>
                <td class="px-5 py-4 text-right">
                  <div class="flex items-center justify-end gap-2">
                    {#if f.state !== "full"}
                      <button onclick={() => setFeatureState(f.key, true)} disabled={saving === f.key}
                        class="rounded-lg px-3 py-1.5 text-xs font-medium text-green-700 bg-green-50 hover:bg-green-100 transition-colors disabled:opacity-50">
                        {saving === f.key ? "..." : "Grant all"}
                      </button>
                    {/if}
                    {#if f.state !== "none"}
                      <button onclick={() => setFeatureState(f.key, false)} disabled={saving === f.key}
                        class="rounded-lg px-3 py-1.5 text-xs font-medium text-red-600 bg-red-50 hover:bg-red-100 transition-colors disabled:opacity-50">
                        {saving === f.key ? "..." : "Revoke all"}
                      </button>
                    {/if}
                    <a href="/iam/roles/permission-matrix?role={role.id}"
                      class="rounded-lg px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-100 transition-colors">
                      Per-action →
                    </a>
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      {/if}
    </div>
  {/if}
</div>

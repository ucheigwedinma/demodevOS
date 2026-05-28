<script lang="ts">
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { RoleDetail, RoleListItem, PaginatedResponse, PermissionRegistryModule, RbacAction } from "$lib/types";

  let loading = $state(true);
  let saving = $state(false);
  let roles = $state<RoleListItem[]>([]);
  let selectedRoleId = $state<number | null>(null);
  let role = $state<RoleDetail | null>(null);
  let registry = $state<PermissionRegistryModule[]>([]);
  let permState = $state<Record<string, boolean>>({});
  let collapsed = $state<Record<string, boolean>>({});

  const ACTION_LABELS: Record<RbacAction, string> = {
    view: "View",
    comment: "Comment",
    create: "Create",
    edit: "Edit",
    upload_version: "Upload Version",
    approve: "Approve",
    archive: "Archive",
    admin_override: "Admin Override",
    delete: "Delete",
    export: "Export",
    assign: "Assign",
    configure: "Configure",
  };

  const ALL_ACTIONS: RbacAction[] = [
    "view", "comment", "create", "edit", "upload_version",
    "approve", "archive", "admin_override", "delete", "export", "assign", "configure",
  ];

  function permKey(subModule: string, action: string): string {
    return `${subModule}.${action}`;
  }

  async function loadRoles() {
    try {
      const res = await api.get<PaginatedResponse<RoleListItem>>("/settings/roles/", { page_size: "200", ordering: "name" });
      roles = res.results;
    } catch {
      toast.error("Load failed", "Could not load roles.");
    }
  }

  async function loadRolePermissions(roleId: number) {
    loading = true;
    try {
      const [roleData, registryData] = await Promise.all([
        api.get<RoleDetail>(`/settings/roles/${roleId}/`),
        registry.length ? Promise.resolve(registry) : api.get<PermissionRegistryModule[]>("/settings/permission-registry/"),
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
      loading = false;
    }
  }

  $effect(() => {
    loadRoles().then(() => {
      const qp = $page.url.searchParams.get("role");
      if (qp) {
        const id = parseInt(qp, 10);
        if (!isNaN(id)) {
          selectedRoleId = id;
          loadRolePermissions(id);
          return;
        }
      }
      loading = false;
    });
  });

  function onRoleChange(e: Event) {
    const value = (e.target as HTMLSelectElement).value;
    if (!value) {
      selectedRoleId = null;
      role = null;
      permState = {};
      goto("/iam/roles/permission-matrix", { replaceState: true });
      return;
    }
    const id = parseInt(value, 10);
    selectedRoleId = id;
    goto(`/iam/roles/permission-matrix?role=${id}`, { replaceState: true });
    loadRolePermissions(id);
  }

  function togglePermission(subModule: string, action: string) {
    const key = permKey(subModule, action);
    permState[key] = !permState[key];
  }

  function isModuleAllChecked(mod: PermissionRegistryModule): boolean {
    for (const sm of mod.sub_modules) {
      for (const action of sm.actions) {
        if (!permState[permKey(sm.key, action)]) return false;
      }
    }
    return true;
  }

  function isModulePartial(mod: PermissionRegistryModule): boolean {
    let has = false;
    let missing = false;
    for (const sm of mod.sub_modules) {
      for (const action of sm.actions) {
        if (permState[permKey(sm.key, action)]) has = true;
        else missing = true;
      }
    }
    return has && missing;
  }

  function toggleModule(mod: PermissionRegistryModule) {
    const allChecked = isModuleAllChecked(mod);
    for (const sm of mod.sub_modules) {
      for (const action of sm.actions) {
        permState[permKey(sm.key, action)] = !allChecked;
      }
    }
  }

  function toggleSubModuleRow(subModule: { key: string; actions: RbacAction[] }) {
    const allChecked = subModule.actions.every((a) => permState[permKey(subModule.key, a)]);
    for (const action of subModule.actions) {
      permState[permKey(subModule.key, action)] = !allChecked;
    }
  }

  function grantedCount(): number {
    return Object.values(permState).filter(Boolean).length;
  }

  function totalPermCount(): number {
    return Object.keys(permState).length;
  }

  async function handleSave() {
    if (!role) return;
    saving = true;
    try {
      const permissions: { sub_module: string; action: string; granted: boolean }[] = [];
      for (const [key, granted] of Object.entries(permState)) {
        const lastDot = key.lastIndexOf(".");
        const subModule = key.substring(0, lastDot);
        const action = key.substring(lastDot + 1);
        permissions.push({ sub_module: subModule, action, granted });
      }
      await api.put(`/settings/roles/${role.id}/permissions/`, { permissions });
      toast.success("Saved", "Permissions updated successfully.");
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error("Save failed", "Could not update permissions.");
      }
    } finally {
      saving = false;
    }
  }
</script>

<div class="space-y-6">
  <!-- Header -->
  <div class="flex items-center justify-between">
    <div>
      <a href="/iam/roles" class="inline-flex items-center gap-1.5 text-sm text-neutral-500 hover:text-neutral-900 transition-colors mb-3">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
        </svg>
        Back to Roles
      </a>
      <h1 class="text-2xl font-bold text-neutral-900">Permission Matrix</h1>
      <p class="mt-1 text-sm text-neutral-500">
        Configure granular permissions for a role across all modules.
        {#if role}
          <span class="ml-2 text-neutral-400">{grantedCount()} / {totalPermCount()} permissions granted</span>
        {/if}
      </p>
    </div>
    {#if role}
      <button
        onclick={handleSave}
        disabled={saving}
        class="rounded-lg bg-neutral-900 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-60"
      >
        {saving ? "Saving..." : "Save Changes"}
      </button>
    {/if}
  </div>

  <!-- Role Selector -->
  <div class="rounded-xl border border-neutral-200 bg-white p-5">
    <div class="flex items-end gap-4">
      <div class="w-80">
        <label for="role-select" class="block text-xs font-medium text-neutral-500 mb-1.5">Select Role</label>
        <select
          id="role-select"
          value={selectedRoleId ?? ""}
          onchange={onRoleChange}
          class="w-full appearance-none px-3.5 py-2.5 border border-neutral-300 rounded-lg text-sm
                 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent transition-shadow"
        >
          <option value="">Choose a role...</option>
          {#each roles as r}
            <option value={r.id}>{r.name}{r.is_system ? " (System)" : ""}</option>
          {/each}
        </select>
      </div>
      {#if role}
        <p class="text-sm text-neutral-500 pb-1">
          {role.description || "No description."}
          <span class="ml-2 inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium {role.is_system ? 'bg-neutral-900 text-white' : 'bg-neutral-100 text-neutral-600'}">
            {role.is_system ? "System" : "Custom"}
          </span>
        </p>
      {/if}
    </div>
  </div>

  <!-- Matrix -->
  {#if loading}
    <div class="flex items-center justify-center py-20">
      <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-900"></div>
    </div>
  {:else if !role}
    <div class="rounded-xl border border-neutral-200 bg-white p-16 text-center">
      <div class="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-neutral-100">
        <svg class="w-6 h-6 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 0 1-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-7.5A1.125 1.125 0 0 1 12 18.375m9.75-12.75c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125m19.5 0v1.5c0 .621-.504 1.125-1.125 1.125M2.25 5.625v1.5c0 .621.504 1.125 1.125 1.125m0 0h17.25m-17.25 0h7.5c.621 0 1.125.504 1.125 1.125M3.375 8.25c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125m17.25-3.75h-7.5c-.621 0-1.125.504-1.125 1.125m8.625-1.125c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125M12 10.875v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 10.875c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125M13.125 12h7.5m-7.5 0c-.621 0-1.125.504-1.125 1.125M20.625 12c.621 0 1.125.504 1.125 1.125v1.5c0 .621-.504 1.125-1.125 1.125m-17.25 0h7.5M12 14.625v-1.5m0 1.5c0 .621-.504 1.125-1.125 1.125M12 14.625c0 .621.504 1.125 1.125 1.125m-2.25 0c.621 0 1.125.504 1.125 1.125m0 0v1.5c0 .621-.504 1.125-1.125 1.125" />
        </svg>
      </div>
      <p class="text-sm font-medium text-neutral-900">Select a role to view its permission matrix</p>
      <p class="mt-1 text-xs text-neutral-400">Choose a role from the dropdown above, or click "Configure" from the Roles Library.</p>
    </div>
  {:else}
    <div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
      <table class="w-full text-sm">
        <thead class="sticky top-0 z-10">
          <tr class="border-b border-neutral-200 bg-neutral-50">
            <th class="px-5 py-3 text-left text-xs font-semibold text-neutral-500 uppercase tracking-wider w-72">
              Module / Sub-module
            </th>
            {#each ALL_ACTIONS as action}
              <th class="px-2 py-3 text-center text-xs font-semibold text-neutral-500 uppercase tracking-wider w-20">
                {ACTION_LABELS[action]}
              </th>
            {/each}
          </tr>
        </thead>
        <tbody>
          {#each registry as mod}
            <!-- Module Header -->
            <tr class="bg-neutral-50/50 border-t border-neutral-200">
              <td class="px-5 py-3">
                <div class="flex items-center gap-3">
                  <button
                    onclick={() => (collapsed[mod.module] = !collapsed[mod.module])}
                    class="text-neutral-400 hover:text-neutral-600 transition-colors"
                    aria-label={collapsed[mod.module] ? `Expand ${mod.label}` : `Collapse ${mod.label}`}
                  >
                    <svg
                      class="w-4 h-4 transition-transform {collapsed[mod.module] ? '-rotate-90' : ''}"
                      fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"
                    >
                      <path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
                    </svg>
                  </button>
                  <button
                    onclick={() => toggleModule(mod)}
                    class="flex items-center gap-2 text-sm font-semibold text-neutral-900 hover:text-neutral-700 transition-colors"
                  >
                    <span
                      class="flex h-4 w-4 items-center justify-center rounded border transition-colors
                             {isModuleAllChecked(mod)
                               ? 'bg-neutral-900 border-neutral-900'
                               : isModulePartial(mod)
                                 ? 'bg-neutral-400 border-neutral-400'
                                 : 'border-neutral-300'}"
                    >
                      {#if isModuleAllChecked(mod) || isModulePartial(mod)}
                        <svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="3">
                          {#if isModuleAllChecked(mod)}
                            <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                          {:else}
                            <path stroke-linecap="round" stroke-linejoin="round" d="M5 12h14" />
                          {/if}
                        </svg>
                      {/if}
                    </span>
                    {mod.label}
                  </button>
                </div>
              </td>
              {#each ALL_ACTIONS as _action}
                <td></td>
              {/each}
            </tr>

            <!-- Sub-module Rows -->
            {#if !collapsed[mod.module]}
              {#each mod.sub_modules as sm}
                <tr class="border-t border-neutral-100 hover:bg-neutral-50/50 transition-colors">
                  <td class="px-5 py-2.5 pl-14">
                    <button
                      onclick={() => toggleSubModuleRow(sm)}
                      class="text-sm text-neutral-700 hover:text-neutral-900 transition-colors"
                    >
                      {sm.label}
                    </button>
                  </td>
                  {#each ALL_ACTIONS as action}
                    <td class="px-2 py-2.5 text-center">
                      {#if sm.actions.includes(action)}
                        <button
                          onclick={() => togglePermission(sm.key, action)}
                          class="inline-flex h-5 w-5 items-center justify-center rounded border transition-colors
                                 {permState[permKey(sm.key, action)]
                                   ? 'bg-neutral-900 border-neutral-900'
                                   : 'border-neutral-300 hover:border-neutral-400'}"
                        >
                          {#if permState[permKey(sm.key, action)]}
                            <svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="3">
                              <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                            </svg>
                          {/if}
                        </button>
                      {:else}
                        <span class="inline-block h-5 w-5"></span>
                      {/if}
                    </td>
                  {/each}
                </tr>
              {/each}
            {/if}
          {/each}
        </tbody>
      </table>
    </div>

    <!-- Bottom Save Bar -->
    <div class="flex items-center justify-between">
      <p class="text-sm text-neutral-500">
        {grantedCount()} of {totalPermCount()} permissions granted
      </p>
      <button
        onclick={handleSave}
        disabled={saving}
        class="rounded-lg bg-neutral-900 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-60"
      >
        {saving ? "Saving..." : "Save Changes"}
      </button>
    </div>
  {/if}
</div>

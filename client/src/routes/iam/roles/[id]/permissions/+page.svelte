<script lang="ts">
  import { page } from "$app/stores";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { RoleDetail, PermissionRegistryModule, RbacAction } from "$lib/types";

  let loading = $state(true);
  let saving = $state(false);
  let role = $state<RoleDetail | null>(null);
  let registry = $state<PermissionRegistryModule[]>([]);

  // Map of "sub_module.action" → boolean
  let permState = $state<Record<string, boolean>>({});

  // Track collapsed modules
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
    "view",
    "comment",
    "create",
    "edit",
    "upload_version",
    "approve",
    "archive",
    "admin_override",
    "delete",
    "export",
    "assign",
    "configure",
  ];

  function permKey(subModule: string, action: string): string {
    return `${subModule}.${action}`;
  }

  async function loadData() {
    const roleId = $page.params.id;
    try {
      const [roleData, registryData] = await Promise.all([
        api.get<RoleDetail>(`/settings/roles/${roleId}/`),
        api.get<PermissionRegistryModule[]>("/settings/permission-registry/"),
      ]);

      role = roleData;
      registry = registryData;

      // Build permission state from existing permissions
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
        if (key in state) {
          state[key] = true;
        }
      }
      permState = state;
    } catch {
      toast.error("Load failed", "Could not load role permissions.");
    } finally {
      loading = false;
    }
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

  function totalCount(): number {
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

  $effect(() => {
    loadData();
  });
</script>

{#if loading}
  <div class="flex items-center justify-center py-20">
    <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-800"></div>
  </div>
{:else if role}
  <!-- Header -->
  <div class="flex items-center justify-between mb-8">
    <div>
      <a href="/iam/roles" class="inline-flex items-center gap-1.5 text-sm text-neutral-500 hover:text-neutral-800 transition-colors mb-3">
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
        </svg>
        Back to Roles
      </a>
      <h2 class="text-xl font-bold text-neutral-800">{role.name}</h2>
      <p class="mt-1 text-sm text-neutral-500">
        {role.description || "Configure granular permissions for this role."}
        <span class="ml-2 text-neutral-400">{grantedCount()} / {totalCount()} permissions granted</span>
      </p>
    </div>
    <button
      onclick={handleSave}
      disabled={saving}
      class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-60"
    >
      {saving ? "Saving..." : "Save Changes"}
    </button>
  </div>

  <!-- Permission Matrix -->
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
          <!-- Module Header Row -->
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
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                    stroke-width="2"
                  >
                    <path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
                  </svg>
                </button>
                <button
                  onclick={() => toggleModule(mod)}
                  class="flex items-center gap-2 text-sm font-semibold text-neutral-800 hover:text-neutral-700 transition-colors"
                >
                  <span
                    class="flex h-4 w-4 items-center justify-center rounded border transition-colors
                           {isModuleAllChecked(mod)
                             ? 'bg-neutral-800 border-neutral-800'
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
                    class="text-sm text-neutral-700 hover:text-neutral-800 transition-colors"
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
                                 ? 'bg-neutral-800 border-neutral-800'
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
  <div class="mt-6 flex items-center justify-between">
    <p class="text-sm text-neutral-500">
      {grantedCount()} of {totalCount()} permissions granted
    </p>
    <button
      onclick={handleSave}
      disabled={saving}
      class="rounded-lg bg-neutral-800 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:opacity-60"
    >
      {saving ? "Saving..." : "Save Changes"}
    </button>
  </div>
{/if}

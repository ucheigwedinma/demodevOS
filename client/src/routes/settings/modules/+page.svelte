<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { FeatureFlagDashboard, FeatureFlagOverride, ModuleOption } from "$lib/types";

  // -------------------------------------------------------------------------
  // State
  // -------------------------------------------------------------------------

  let loading = $state(true);
  let saving = $state(false);
  let savingFlags = $state<Record<string, boolean>>({});

  let dashboard = $state<FeatureFlagDashboard | null>(null);
  let enabledModules = $state<string[]>([]);

  // Group flag definitions by module for display
  let flagsByModule = $derived(() => {
    if (!dashboard) return {};
    const groups: Record<string, typeof dashboard.flag_definitions> = {};
    for (const def of dashboard.flag_definitions) {
      const key = def.module || "_platform";
      if (!groups[key]) groups[key] = [];
      groups[key].push(def);
    }
    return groups;
  });

  let collapsedModules = $state<Record<string, boolean>>({});

  // -------------------------------------------------------------------------
  // Data loading
  // -------------------------------------------------------------------------

  async function loadDashboard() {
    try {
      const data = await api.get<FeatureFlagDashboard>("/settings/feature-flags/dashboard/");
      dashboard = data;
      enabledModules = [...data.enabled_modules];
    } catch (err) {
      toast.error("Failed to load", err instanceof ApiError ? err.message : "Unknown error");
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    loadDashboard();
  });

  // -------------------------------------------------------------------------
  // Module activation
  // -------------------------------------------------------------------------

  function isModuleEnabled(key: string): boolean {
    return enabledModules.includes(key);
  }

  function toggleModule(key: string) {
    if (enabledModules.includes(key)) {
      enabledModules = enabledModules.filter((m) => m !== key);
    } else {
      enabledModules = [...enabledModules, key];
    }
  }

  async function saveModules() {
    saving = true;
    try {
      await api.patch("/settings/module-activation/", {
        enabled_modules: enabledModules,
      });
      toast.success("Modules updated", "Module activation settings saved.");
      await loadDashboard();
    } catch (err) {
      if (err instanceof ApiError) {
        const msgs = Object.values(err.fieldErrors).flat();
        toast.error("Save failed", msgs.join(", ") || err.message);
      } else {
        toast.error("Save failed", "Unknown error");
      }
    } finally {
      saving = false;
    }
  }

  let hasModuleChanges = $derived(
    dashboard
      ? JSON.stringify([...enabledModules].sort()) !==
        JSON.stringify([...dashboard.enabled_modules].sort())
      : false,
  );

  // -------------------------------------------------------------------------
  // Feature flag overrides
  // -------------------------------------------------------------------------

  function getOverrideForFlag(flagKey: string): FeatureFlagOverride | undefined {
    return dashboard?.overrides.find((o) => o.flag_key === flagKey);
  }

  function isFlagEnabled(flagKey: string): boolean {
    return dashboard?.flags[flagKey] ?? false;
  }

  async function toggleFlag(flagKey: string, flagId: number) {
    if (!dashboard) return;
    const currentlyEnabled = isFlagEnabled(flagKey);
    const override = getOverrideForFlag(flagKey);
    savingFlags = { ...savingFlags, [flagKey]: true };

    try {
      if (override) {
        // Update existing override
        await api.patch<FeatureFlagOverride>(
          `/settings/feature-flags/overrides/${override.id}/`,
          { enabled: !currentlyEnabled },
        );
      } else {
        // Create new override
        await api.post<FeatureFlagOverride>("/settings/feature-flags/overrides/", {
          flag: flagId,
          enabled: !currentlyEnabled,
        });
      }
      await loadDashboard();
    } catch (err) {
      toast.error("Toggle failed", err instanceof ApiError ? err.message : "Unknown error");
    } finally {
      savingFlags = { ...savingFlags, [flagKey]: false };
    }
  }

  // -------------------------------------------------------------------------
  // Helpers
  // -------------------------------------------------------------------------

  const tierLabels: Record<string, string> = {
    starter: "Starter",
    professional: "Professional",
    enterprise: "Enterprise",
  };

  const tierColors: Record<string, string> = {
    starter: "bg-neutral-100 text-neutral-600",
    professional: "bg-blue-50 text-blue-700",
    enterprise: "bg-violet-50 text-violet-700",
  };

  const scopeColors: Record<string, string> = {
    global: "bg-emerald-50 text-emerald-700",
    org: "bg-blue-50 text-blue-700",
    project: "bg-amber-50 text-amber-700",
    region: "bg-rose-50 text-rose-700",
  };

  const moduleLabels: Record<string, string> = {
    properties: "Properties",
    projects: "Projects",
    finance: "Finance",
    procurement: "Procurement",
    documents: "Documents",
    analytics: "Analytics",
    crm: "CRM",
    tenants: "Tenants",
    contracts: "Contracts",
    compliance: "Compliance",
    _platform: "Platform-wide",
  };

  function toggleCollapse(key: string) {
    collapsedModules = { ...collapsedModules, [key]: !collapsedModules[key] };
  }
</script>

<!-- Page header -->
<div class="space-y-8">
  <div>
    <h2 class="text-lg font-semibold text-neutral-800">Modules & Features</h2>
    <p class="text-sm text-neutral-500 mt-1">
      Control which platform modules are active and manage feature flag rollouts.
    </p>
  </div>

  {#if loading}
    <div class="flex items-center justify-center py-24">
      <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-800"></div>
    </div>
  {:else if dashboard}
    <!-- ================================================================== -->
    <!-- Section 1: Module Activation                                       -->
    <!-- ================================================================== -->
    <section class="bg-white rounded-xl border border-neutral-200">
      <div class="px-6 py-5 border-b border-neutral-100 flex items-center justify-between">
        <div>
          <h3 class="text-sm font-semibold text-neutral-800">Module Activation</h3>
          <p class="text-xs text-neutral-500 mt-0.5">
            Enable or disable platform modules for your organization.
          </p>
        </div>
        <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium {tierColors[dashboard.tier] ?? 'bg-neutral-100 text-neutral-600'}">
          {tierLabels[dashboard.tier] ?? dashboard.tier_display} Plan
        </span>
      </div>

      <div class="p-6">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {#each dashboard.available_modules as mod (mod.key)}
            {@const enabled = isModuleEnabled(mod.key)}
            {@const locked = !mod.available}
            <button
              type="button"
              class="relative flex items-center gap-3 px-4 py-3 rounded-lg border text-left transition-colors
                     {locked
                       ? 'border-neutral-100 bg-neutral-50 cursor-not-allowed opacity-60'
                       : enabled
                         ? 'border-neutral-200 bg-white hover:border-neutral-300'
                         : 'border-neutral-100 bg-neutral-50/50 hover:border-neutral-200'}"
              onclick={() => !locked && toggleModule(mod.key)}
              disabled={locked}
            >
              <!-- Toggle indicator -->
              <div
                class="w-9 h-5 rounded-full flex items-center transition-colors shrink-0
                       {enabled && !locked ? 'bg-neutral-800' : 'bg-neutral-200'}"
              >
                <div
                  class="w-3.5 h-3.5 rounded-full bg-white shadow-sm transition-transform
                         {enabled && !locked ? 'translate-x-[18px]' : 'translate-x-[3px]'}"
                ></div>
              </div>

              <div class="min-w-0">
                <span class="text-sm font-medium text-neutral-800">{mod.label}</span>
                {#if locked}
                  <p class="text-xs text-neutral-400 mt-0.5 flex items-center gap-1">
                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z" />
                    </svg>
                    Requires upgrade
                  </p>
                {/if}
              </div>
            </button>
          {/each}
        </div>

        <!-- Save bar -->
        {#if hasModuleChanges}
          <div class="mt-6 flex items-center justify-end gap-3 pt-4 border-t border-neutral-100">
            <button
              type="button"
              class="px-3 py-1.5 text-sm text-neutral-600 hover:text-neutral-800 transition-colors"
              onclick={() => { enabledModules = [...(dashboard?.enabled_modules ?? [])]; }}
            >
              Cancel
            </button>
            <button
              type="button"
              class="px-4 py-1.5 text-sm font-medium text-white bg-neutral-800 rounded-lg hover:bg-neutral-800 transition-colors disabled:opacity-50"
              onclick={saveModules}
              disabled={saving}
            >
              {saving ? "Saving..." : "Save Changes"}
            </button>
          </div>
        {/if}
      </div>
    </section>

    <!-- ================================================================== -->
    <!-- Section 2: Feature Flags                                           -->
    <!-- ================================================================== -->
    <section class="bg-white rounded-xl border border-neutral-200">
      <div class="px-6 py-5 border-b border-neutral-100">
        <h3 class="text-sm font-semibold text-neutral-800">Feature Flags</h3>
        <p class="text-xs text-neutral-500 mt-0.5">
          Toggle beta features and pilot rollouts for your organization.
        </p>
      </div>

      <div class="divide-y divide-neutral-100">
        {#each Object.entries(flagsByModule()) as [moduleKey, flags] (moduleKey)}
          {@const collapsed = collapsedModules[moduleKey] ?? false}
          <!-- Module group header -->
          <div>
            <button
              type="button"
              class="w-full px-6 py-3 flex items-center justify-between text-left hover:bg-neutral-50 transition-colors"
              onclick={() => toggleCollapse(moduleKey)}
            >
              <span class="text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                {moduleLabels[moduleKey] ?? moduleKey}
              </span>
              <div class="flex items-center gap-2">
                <span class="text-xs text-neutral-400">{flags.length} flag{flags.length !== 1 ? "s" : ""}</span>
                <svg
                  class="w-4 h-4 text-neutral-400 transition-transform {collapsed ? '' : 'rotate-180'}"
                  fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
                </svg>
              </div>
            </button>

            {#if !collapsed}
              <div class="px-6 pb-4 space-y-2">
                {#each flags as flag (flag.id)}
                  {@const enabled = isFlagEnabled(flag.key)}
                  {@const flagSaving = savingFlags[flag.key] ?? false}
                  {@const tierLocked = (() => {
                    const tierOrder = ["starter", "professional", "enterprise"];
                    return dashboard ? tierOrder.indexOf(flag.minimum_tier) > tierOrder.indexOf(dashboard.tier) : false;
                  })()}

                  <div class="flex items-start gap-3 p-3 rounded-lg border border-neutral-100 {tierLocked ? 'opacity-60' : ''}">
                    <!-- Toggle -->
                    <!-- svelte-ignore a11y_consider_explicit_label -->
                    <button
                      type="button"
                      class="mt-0.5 w-9 h-5 rounded-full flex items-center transition-colors shrink-0
                             {enabled && !tierLocked ? 'bg-neutral-800' : 'bg-neutral-200'}
                             {tierLocked ? 'cursor-not-allowed' : 'cursor-pointer'}"
                      onclick={() => !tierLocked && !flagSaving && toggleFlag(flag.key, flag.id)}
                      disabled={tierLocked || flagSaving}
                    >
                      <div
                        class="w-3.5 h-3.5 rounded-full bg-white shadow-sm transition-transform
                               {enabled && !tierLocked ? 'translate-x-[18px]' : 'translate-x-[3px]'}"
                      ></div>
                    </button>

                    <!-- Content -->
                    <div class="flex-1 min-w-0">
                      <div class="flex items-center gap-2 flex-wrap">
                        <span class="text-sm font-medium text-neutral-800">{flag.name}</span>
                        <!-- Scope badge -->
                        <span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium {scopeColors[flag.scope] ?? 'bg-neutral-100 text-neutral-600'}">
                          {flag.scope_display}
                        </span>
                        <!-- Tier badge (if above starter) -->
                        {#if flag.minimum_tier !== "starter"}
                          <span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium {tierColors[flag.minimum_tier] ?? 'bg-neutral-100 text-neutral-600'}">
                            {tierLabels[flag.minimum_tier]}+
                          </span>
                        {/if}
                        {#if flagSaving}
                          <div class="h-3 w-3 animate-spin rounded-full border border-neutral-300 border-t-neutral-600"></div>
                        {/if}
                      </div>
                      <p class="text-xs text-neutral-500 mt-0.5">{flag.description}</p>
                      {#if tierLocked}
                        <p class="text-xs text-neutral-400 mt-1 flex items-center gap-1">
                          <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z" />
                          </svg>
                          Requires {tierLabels[flag.minimum_tier]} plan or higher
                        </p>
                      {/if}
                    </div>
                  </div>
                {/each}
              </div>
            {/if}
          </div>
        {/each}

        {#if dashboard.flag_definitions.length === 0}
          <div class="px-6 py-12 text-center">
            <p class="text-sm text-neutral-400">No feature flags configured yet.</p>
          </div>
        {/if}
      </div>
    </section>
  {/if}
</div>

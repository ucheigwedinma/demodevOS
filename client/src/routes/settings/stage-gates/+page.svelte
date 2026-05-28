<script lang="ts">
  import { onMount } from "svelte";
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { StageGateRuleListItem, StageGateStage, PaginatedResponse } from "$lib/types";

  let rules = $state<StageGateRuleListItem[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let filterStage = $state<StageGateStage | "all">("all");

  const stageOptions: { value: StageGateStage | "all"; label: string }[] = [
    { value: "all", label: "All Stages" },
    { value: "feasibility", label: "Feasibility" },
    { value: "design", label: "Design" },
    { value: "pre_sales", label: "Pre-Sales" },
    { value: "construction_start", label: "Construction Start" },
    { value: "handover", label: "Handover" },
  ];

  onMount(async () => {
    await loadRules();
  });

  async function loadRules() {
    loading = true;
    error = null;
    try {
      const params: any = {};
      if (filterStage !== "all") {
        params.stage = filterStage;
      }
      const res = await api.get<PaginatedResponse<StageGateRuleListItem>>("/settings/stage-gate-rules/", params);
      rules = res.results;
    } catch (err: any) {
      error = err.response?.data?.detail || "Failed to load stage-gate rules";
    } finally {
      loading = false;
    }
  }

  async function deleteRule(id: number, name: string) {
    if (!confirm(`Delete stage-gate rule "${name}"? This cannot be undone.`)) return;

    try {
      await api.delete(`/settings/stage-gate-rules/${id}/`);
      toast.success("Deleted", "Stage-gate rule deleted successfully");
      loadRules();
    } catch {
      toast.error("Error", "Could not delete stage-gate rule");
    }
  }

  async function toggleActive(rule: StageGateRuleListItem) {
    try {
      await api.patch(`/settings/stage-gate-rules/${rule.id}/`, { is_active: !rule.is_active });
      toast.success("Updated", `Rule ${rule.is_active ? "deactivated" : "activated"}`);
      loadRules();
    } catch {
      toast.error("Error", "Could not update rule status");
    }
  }

  $effect(() => {
    void filterStage;
    loadRules();
  });

  function getStageColor(stage: StageGateStage): string {
    const colors: Record<StageGateStage, string> = {
      feasibility: "bg-blue-100 text-blue-900",
      design: "bg-purple-100 text-purple-900",
      pre_sales: "bg-green-100 text-green-900",
      construction_start: "bg-orange-100 text-orange-900",
      handover: "bg-pink-100 text-pink-900",
    };
    return colors[stage] || "bg-neutral-100 text-neutral-800";
  }
</script>

<div class="max-w-6xl">
  <div class="mb-8 flex items-start justify-between">
    <div>
      <h1 class="text-2xl font-bold text-neutral-800 mb-2">Stage-Gate Rules</h1>
      <p class="text-sm text-neutral-500">
        Define approval checkpoints and requirements for each project stage.
      </p>
    </div>
    <a
      href="/settings/stage-gates/new"
      class="px-4 py-2.5 bg-neutral-800 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
    >
      + New Rule
    </a>
  </div>

  <!-- Filters -->
  <div class="mb-6 flex items-center gap-3">
    <label for="stage-filter" class="text-sm font-medium text-neutral-700">Filter by stage:</label>
    <select
      id="stage-filter"
      bind:value={filterStage}
      class="px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800"
    >
      {#each stageOptions as option}
        <option value={option.value}>{option.label}</option>
      {/each}
    </select>
  </div>

  {#if loading}
    <div class="bg-white rounded-xl border border-neutral-200 p-12 text-center">
      <div class="inline-block w-8 h-8 border-4 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
    </div>
  {:else if error}
    <div class="bg-red-50 border border-red-200 rounded-lg p-4">
      <p class="text-sm text-red-900">{error}</p>
    </div>
  {:else if rules.length === 0}
    <div class="bg-white rounded-xl border border-neutral-200 p-12 text-center">
      <svg class="w-12 h-12 text-neutral-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
      </svg>
      <p class="text-sm text-neutral-500">No stage-gate rules found.</p>
      <a
        href="/settings/stage-gates/new"
        class="mt-4 inline-block text-sm font-medium text-neutral-800 hover:underline"
      >
        Create your first rule
      </a>
    </div>
  {:else}
    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      <table class="w-full">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50">
            <th class="text-left px-6 py-3 text-xs font-semibold text-neutral-600 uppercase tracking-wider">Rule Name</th>
            <th class="text-left px-6 py-3 text-xs font-semibold text-neutral-600 uppercase tracking-wider">Stage</th>
            <th class="text-left px-6 py-3 text-xs font-semibold text-neutral-600 uppercase tracking-wider">Applies To</th>
            <th class="text-left px-6 py-3 text-xs font-semibold text-neutral-600 uppercase tracking-wider">Checklist</th>
            <th class="text-left px-6 py-3 text-xs font-semibold text-neutral-600 uppercase tracking-wider">Status</th>
            <th class="text-right px-6 py-3 text-xs font-semibold text-neutral-600 uppercase tracking-wider">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-200">
          {#each rules as rule}
            <tr class="hover:bg-neutral-50 transition-colors">
              <td class="px-6 py-4">
                <a
                  href="/settings/stage-gates/{rule.id}"
                  class="text-sm font-medium text-neutral-800 hover:text-neutral-700"
                >
                  {rule.name}
                </a>
                <p class="text-xs text-neutral-500 mt-0.5">
                  Created {new Date(rule.created_at).toLocaleDateString()}
                </p>
              </td>
              <td class="px-6 py-4">
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {getStageColor(rule.stage)}">
                  {rule.stage_display}
                </span>
              </td>
              <td class="px-6 py-4">
                <span class="text-sm text-neutral-700">{rule.template_name || "All Projects"}</span>
              </td>
              <td class="px-6 py-4">
                <span class="text-sm text-neutral-800">{rule.checklist_count} items</span>
              </td>
              <td class="px-6 py-4">
                <button
                  onclick={() => toggleActive(rule)}
                  class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium cursor-pointer transition-colors {rule.is_active
                    ? 'bg-green-100 text-green-800 hover:bg-green-200'
                    : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200'}"
                >
                  {rule.is_active ? "Active" : "Inactive"}
                </button>
              </td>
              <td class="px-6 py-4 text-right">
                <div class="flex items-center justify-end gap-3">
                  <a
                    href="/settings/stage-gates/{rule.id}"
                    class="text-sm font-medium text-neutral-700 hover:text-neutral-800"
                  >
                    Edit
                  </a>
                  <button
                    onclick={() => deleteRule(rule.id, rule.name)}
                    class="text-sm font-medium text-red-500 hover:text-red-700 transition-colors"
                  >
                    Delete
                  </button>
                </div>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>

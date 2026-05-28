<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { StageGateRule, StageGateStage, StageGateChecklistItem, ProjectTemplateListItem, PaginatedResponse } from "$lib/types";

  const ruleId = $derived($page.params.id);
  let rule = $state<StageGateRule | null>(null);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let editing = $state(false);
  let saving = $state(false);
  let templates = $state<ProjectTemplateListItem[]>([]);

  let editData = $state({
    name: "",
    stage: "feasibility" as StageGateStage,
    template: null as number | null,
    description: "",
    is_active: true,
  });

  let newChecklistItem = $state("");
  let newItemMandatory = $state(true);

  const stageOptions: { value: StageGateStage; label: string }[] = [
    { value: "feasibility", label: "Feasibility" },
    { value: "design", label: "Design" },
    { value: "pre_sales", label: "Pre-Sales" },
    { value: "construction_start", label: "Construction Start" },
    { value: "handover", label: "Handover" },
  ];

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

  onMount(async () => {
    await Promise.all([loadRule(), loadTemplates()]);
  });

  async function loadRule() {
    loading = true;
    error = null;
    try {
      rule = await api.get<StageGateRule>(`/settings/stage-gate-rules/${ruleId}/`);
      syncEditData();
    } catch (err: any) {
      error = err.response?.data?.detail || "Failed to load stage-gate rule";
    } finally {
      loading = false;
    }
  }

  async function loadTemplates() {
    try {
      const res = await api.get<PaginatedResponse<ProjectTemplateListItem>>("/settings/project-templates/", { is_active: "true", page_size: "100" });
      templates = res.results;
    } catch {
      // Non-critical
    }
  }

  function syncEditData() {
    if (!rule) return;
    editData = {
      name: rule.name,
      stage: rule.stage,
      template: rule.template,
      description: rule.description,
      is_active: rule.is_active,
    };
  }

  function startEditing() {
    syncEditData();
    editing = true;
  }

  function cancelEditing() {
    editing = false;
    syncEditData();
  }

  async function saveChanges() {
    if (!editData.name.trim()) {
      toast.error("Validation Error", "Rule name is required");
      return;
    }

    saving = true;
    try {
      const payload: any = { ...editData };
      if (!payload.template) payload.template = null;
      await api.patch(`/settings/stage-gate-rules/${ruleId}/`, payload);
      toast.success("Updated", "Stage-gate rule updated");
      editing = false;
      await loadRule();
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || "Failed to update rule";
      toast.error("Save Failed", errorMsg);
    } finally {
      saving = false;
    }
  }

  async function deleteRule() {
    if (!rule) return;
    if (!confirm(`Delete stage-gate rule "${rule.name}"? This cannot be undone.`)) return;

    try {
      await api.delete(`/settings/stage-gate-rules/${ruleId}/`);
      toast.success("Deleted", "Stage-gate rule deleted");
      goto("/settings/stage-gates");
    } catch {
      toast.error("Error", "Could not delete stage-gate rule");
    }
  }

  async function addChecklistItem() {
    if (!newChecklistItem.trim()) {
      toast.error("Validation Error", "Checklist item text is required");
      return;
    }

    try {
      await api.post(`/settings/stage-gate-rules/${ruleId}/checklist-items/`, {
        item: newChecklistItem.trim(),
        is_mandatory: newItemMandatory,
        sort_order: rule ? rule.checklist_items.length : 0,
      });
      newChecklistItem = "";
      newItemMandatory = true;
      toast.success("Added", "Checklist item added");
      await loadRule();
    } catch {
      toast.error("Error", "Could not add checklist item");
    }
  }

  async function removeChecklistItem(itemId: number) {
    if (!confirm("Remove this checklist item?")) return;

    try {
      await api.delete(`/settings/stage-gate-rules/${ruleId}/checklist-items/${itemId}/`);
      toast.success("Removed", "Checklist item removed");
      await loadRule();
    } catch {
      toast.error("Error", "Could not remove checklist item");
    }
  }

  async function toggleItemMandatory(item: StageGateChecklistItem) {
    try {
      await api.patch(`/settings/stage-gate-rules/${ruleId}/checklist-items/${item.id}/`, {
        is_mandatory: !item.is_mandatory,
      });
      await loadRule();
    } catch {
      toast.error("Error", "Could not update checklist item");
    }
  }
</script>

<div class="max-w-4xl">
  <div class="mb-8">
    <a
      href="/settings/stage-gates"
      class="inline-flex items-center gap-2 text-sm text-neutral-500 hover:text-neutral-800 mb-4"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
      </svg>
      Back to stage gates
    </a>
  </div>

  {#if loading}
    <div class="bg-white rounded-xl border border-neutral-200 p-12 text-center">
      <div class="inline-block w-8 h-8 border-4 border-neutral-200 border-t-neutral-800 rounded-full animate-spin"></div>
    </div>
  {:else if error}
    <div class="bg-red-50 border border-red-200 rounded-lg p-4">
      <p class="text-sm text-red-900">{error}</p>
    </div>
  {:else if rule}
    <!-- Header -->
    <div class="bg-white rounded-xl border border-neutral-200 p-6 mb-6">
      {#if editing}
        <div class="space-y-5">
          <div>
            <label for="edit-name" class="block text-sm font-medium text-neutral-700 mb-1.5">
              Rule Name <span class="text-red-500">*</span>
            </label>
            <input
              id="edit-name"
              type="text"
              bind:value={editData.name}
              class="w-full rounded-lg border border-neutral-300 bg-white px-4 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
            />
          </div>

          <div>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Stage</span>
            <div class="grid grid-cols-2 sm:grid-cols-5 gap-2">
              {#each stageOptions as option}
                <button
                  type="button"
                  onclick={() => (editData.stage = option.value)}
                  class="px-3 py-2 text-center text-xs font-medium rounded-lg border-2 transition-all
                         {editData.stage === option.value
                           ? 'border-neutral-800 bg-neutral-50 text-neutral-800'
                           : 'border-neutral-200 text-neutral-600 hover:border-neutral-400'}"
                >
                  {option.label}
                </button>
              {/each}
            </div>
          </div>

          <div>
            <label for="edit-template" class="block text-sm font-medium text-neutral-700 mb-1.5">Applies To</label>
            <select
              id="edit-template"
              bind:value={editData.template}
              class="w-full rounded-lg border border-neutral-300 bg-white px-4 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
            >
              <option value={null}>All Projects</option>
              {#each templates as template}
                <option value={template.id}>{template.name}</option>
              {/each}
            </select>
          </div>

          <div>
            <label for="edit-desc" class="block text-sm font-medium text-neutral-700 mb-1.5">Description</label>
            <textarea
              id="edit-desc"
              bind:value={editData.description}
              rows="3"
              class="w-full rounded-lg border border-neutral-300 bg-white px-4 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent resize-none"
            ></textarea>
          </div>

          <div>
            <label class="flex items-center gap-3 cursor-pointer">
              <input
                type="checkbox"
                bind:checked={editData.is_active}
                class="w-4 h-4 text-neutral-800 border-neutral-300 rounded focus:ring-neutral-800 focus:ring-offset-0"
              />
              <span class="text-sm font-medium text-neutral-800">Active</span>
            </label>
          </div>

          <div class="flex items-center justify-end gap-3 pt-2 border-t border-neutral-200">
            <button
              onclick={cancelEditing}
              class="px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              onclick={saveChanges}
              disabled={saving}
              class="px-5 py-2 bg-neutral-800 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </div>
      {:else}
        <div class="flex items-start justify-between mb-4">
          <div>
            <div class="flex items-center gap-3 mb-2">
              <h1 class="text-2xl font-bold text-neutral-800">{rule.name}</h1>
              <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {getStageColor(rule.stage)}">
                {rule.stage_display}
              </span>
              <span
                class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {rule.is_active
                  ? 'bg-green-100 text-green-800'
                  : 'bg-neutral-100 text-neutral-600'}"
              >
                {rule.is_active ? "Active" : "Inactive"}
              </span>
            </div>
            <p class="text-sm text-neutral-500">
              Applies to: {rule.template_name || "All Projects"}
            </p>
          </div>
          <div class="flex items-center gap-2">
            <button
              onclick={startEditing}
              class="px-4 py-2 text-sm font-medium text-neutral-700 border border-neutral-300 rounded-lg hover:bg-neutral-50 transition-colors"
            >
              Edit
            </button>
            <button
              onclick={deleteRule}
              class="px-4 py-2 text-sm font-medium text-red-600 border border-red-200 rounded-lg hover:bg-red-50 transition-colors"
            >
              Delete
            </button>
          </div>
        </div>
        {#if rule.description}
          <p class="text-sm text-neutral-700">{rule.description}</p>
        {/if}
      {/if}
    </div>

    <!-- Checklist -->
    <div class="bg-white rounded-xl border border-neutral-200 p-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-base font-semibold text-neutral-800">Gate Checklist</h2>
        <span class="text-xs text-neutral-500">{rule.checklist_items.length} items</span>
      </div>

      {#if rule.checklist_items.length === 0}
        <p class="text-sm text-neutral-500 mb-4">No checklist items defined yet.</p>
      {:else}
        <ul class="space-y-2 mb-6">
          {#each rule.checklist_items as item}
            <li class="flex items-center gap-3 group px-3 py-2.5 rounded-lg hover:bg-neutral-50 transition-colors">
              <button
                onclick={() => toggleItemMandatory(item)}
                class="flex items-center justify-center w-5 h-5 rounded border-2 shrink-0 transition-colors {item.is_mandatory
                  ? 'border-red-400 bg-red-50'
                  : 'border-neutral-300'}"
                title={item.is_mandatory ? "Click to make optional" : "Click to make mandatory"}
              >
                {#if item.is_mandatory}
                  <svg class="w-3 h-3 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="3">
                    <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                  </svg>
                {/if}
              </button>
              <div class="flex-1 min-w-0">
                <p class="text-sm text-neutral-800">{item.item}</p>
              </div>
              {#if item.is_mandatory}
                <span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
                  Required
                </span>
              {:else}
                <span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-neutral-100 text-neutral-600">
                  Optional
                </span>
              {/if}
              <button
                onclick={() => removeChecklistItem(item.id)}
                class="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-600 transition-all"
                title="Remove item"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
                </svg>
              </button>
            </li>
          {/each}
        </ul>
      {/if}

      <!-- Add New Checklist Item -->
      <div class="border-t border-neutral-200 pt-4">
        <p class="text-sm font-medium text-neutral-700 mb-3">Add Checklist Item</p>
        <div class="flex items-start gap-3">
          <div class="flex-1">
            <input
              type="text"
              bind:value={newChecklistItem}
              placeholder="e.g., Environmental impact assessment completed"
              class="w-full rounded-lg border border-neutral-300 bg-white px-4 py-2.5 text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
              onkeydown={(e) => { if (e.key === "Enter") { e.preventDefault(); addChecklistItem(); } }}
            />
            <label class="flex items-center gap-2 mt-2 cursor-pointer">
              <input
                type="checkbox"
                bind:checked={newItemMandatory}
                class="w-3.5 h-3.5 text-neutral-800 border-neutral-300 rounded focus:ring-neutral-800 focus:ring-offset-0"
              />
              <span class="text-xs text-neutral-600">Required to pass gate</span>
            </label>
          </div>
          <button
            onclick={addChecklistItem}
            class="px-4 py-2.5 bg-neutral-800 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors shrink-0"
          >
            Add
          </button>
        </div>
      </div>
    </div>
  {/if}
</div>

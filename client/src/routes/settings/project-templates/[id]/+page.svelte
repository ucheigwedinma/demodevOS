<script lang="ts">
  import { onMount } from "svelte";
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { ProjectTemplate, TemplateType } from "$lib/types";

  const templateId = $derived($page.params.id);
  let template = $state<ProjectTemplate | null>(null);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let expandedPhases = $state<Set<number>>(new Set());
  let editing = $state(false);
  let saving = $state(false);

  let editData = $state({
    name: "",
    template_type: "residential" as TemplateType,
    description: "",
    is_active: true,
  });

  const templateTypeOptions: { value: TemplateType; label: string }[] = [
    { value: "residential", label: "Residential" },
    { value: "mixed_use", label: "Mixed-Use" },
    { value: "commercial", label: "Commercial" },
    { value: "infrastructure", label: "Infrastructure" },
  ];

  function getTypeColor(type: TemplateType): string {
    const colors: Record<TemplateType, string> = {
      residential: "bg-blue-100 text-blue-900",
      mixed_use: "bg-purple-100 text-purple-900",
      commercial: "bg-green-100 text-green-900",
      infrastructure: "bg-orange-100 text-orange-900",
    };
    return colors[type] || "bg-neutral-100 text-neutral-800";
  }

  onMount(async () => {
    await loadTemplate();
  });

  async function loadTemplate() {
    loading = true;
    error = null;
    try {
      template = await api.get(`/settings/project-templates/${templateId}/`);
      if (template) {
        expandedPhases = new Set(template.phases.map((p) => p.id));
        syncEditData();
      }
    } catch (err: any) {
      error = err.response?.data?.detail || "Failed to load template";
    } finally {
      loading = false;
    }
  }

  function syncEditData() {
    if (!template) return;
    editData = {
      name: template.name,
      template_type: template.template_type,
      description: template.description,
      is_active: template.is_active,
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
      toast.error("Validation Error", "Template name is required");
      return;
    }

    saving = true;
    try {
      await api.patch(`/settings/project-templates/${templateId}/`, editData);
      toast.success("Updated", "Template updated successfully");
      editing = false;
      await loadTemplate();
    } catch (err: any) {
      toast.error("Save Failed", err.response?.data?.detail || "Failed to update template");
    } finally {
      saving = false;
    }
  }

  async function deleteTemplate() {
    if (!template) return;
    if (!confirm(`Delete project template "${template.name}"? This cannot be undone.`)) return;

    try {
      await api.delete(`/settings/project-templates/${templateId}/`);
      toast.success("Deleted", "Project template deleted");
      goto("/settings/project-templates");
    } catch {
      toast.error("Error", "Could not delete template. It may be in use by projects.");
    }
  }

  function togglePhase(phaseId: number) {
    if (expandedPhases.has(phaseId)) {
      expandedPhases.delete(phaseId);
    } else {
      expandedPhases.add(phaseId);
    }
    expandedPhases = expandedPhases;
  }

  function getDocumentIcon(category: string): string {
    const icons: Record<string, string> = {
      permit: "M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25ZM6.75 12h.008v.008H6.75V12Zm0 3h.008v.008H6.75V15Zm0 3h.008v.008H6.75V18Z",
      contract: "M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z",
      plan: "M9 6.75V15m6-6v8.25m.503 3.498 4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 0 0-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0Z",
      report: "M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25ZM6.75 12h.008v.008H6.75V12Zm0 3h.008v.008H6.75V15Zm0 3h.008v.008H6.75V18Z",
      certificate: "M11.48 3.499a.562.562 0 0 1 1.04 0l2.125 5.111a.563.563 0 0 0 .475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 0 0-.182.557l1.285 5.385a.562.562 0 0 1-.84.61l-4.725-2.885a.562.562 0 0 0-.586 0L6.982 20.54a.562.562 0 0 1-.84-.61l1.285-5.386a.562.562 0 0 0-.182-.557l-4.204-3.602a.562.562 0 0 1 .321-.988l5.518-.442a.563.563 0 0 0 .475-.345L11.48 3.5Z",
    };
    return icons[category] || icons.report;
  }
</script>

<div class="max-w-6xl">
  <div class="mb-8">
    <a
      href="/settings/project-templates"
      class="inline-flex items-center gap-2 text-sm text-neutral-500 hover:text-neutral-800 mb-4"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
      </svg>
      Back to templates
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
  {:else if template}
    <!-- Header -->
    <div class="bg-white rounded-xl border border-neutral-200 p-6 mb-6">
      {#if editing}
        <div class="space-y-5">
          <div>
            <label for="edit-name" class="block text-sm font-medium text-neutral-700 mb-1.5">
              Template Name <span class="text-red-500">*</span>
            </label>
            <input
              id="edit-name"
              type="text"
              bind:value={editData.name}
              class="w-full rounded-lg border border-neutral-300 bg-white px-4 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
            />
          </div>

          <div>
            <span class="block text-sm font-medium text-neutral-700 mb-1.5">Template Type</span>
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {#each templateTypeOptions as option}
                <button
                  type="button"
                  onclick={() => (editData.template_type = option.value)}
                  class="px-3 py-2 text-center text-xs font-medium rounded-lg border-2 transition-all
                         {editData.template_type === option.value
                           ? 'border-neutral-800 bg-neutral-50 text-neutral-800'
                           : 'border-neutral-200 text-neutral-600 hover:border-neutral-400'}"
                >
                  {option.label}
                </button>
              {/each}
            </div>
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
              <h1 class="text-2xl font-bold text-neutral-800">{template.name}</h1>
              {#if template.is_system}
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-neutral-100 text-neutral-700">
                  System Template
                </span>
              {/if}
              <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {getTypeColor(template.template_type)}">
                {template.template_type_display}
              </span>
              <span
                class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {template.is_active
                  ? 'bg-green-100 text-green-800'
                  : 'bg-neutral-100 text-neutral-600'}"
              >
                {template.is_active ? "Active" : "Inactive"}
              </span>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <button
              onclick={startEditing}
              class="px-4 py-2 text-sm font-medium text-neutral-700 border border-neutral-300 rounded-lg hover:bg-neutral-50 transition-colors"
            >
              Edit
            </button>
            {#if !template.is_system}
              <button
                onclick={deleteTemplate}
                class="px-4 py-2 text-sm font-medium text-red-600 border border-red-200 rounded-lg hover:bg-red-50 transition-colors"
              >
                Delete
              </button>
            {/if}
          </div>
        </div>
        {#if template.description}
          <p class="text-sm text-neutral-700">{template.description}</p>
        {/if}
      {/if}
    </div>

    <!-- Phases -->
    <div class="space-y-4">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold text-neutral-800">Project Phases ({template.phases.length})</h2>
      </div>

      {#each template.phases as phase, idx}
        <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
          <button
            onclick={() => togglePhase(phase.id)}
            class="w-full px-6 py-4 flex items-center justify-between hover:bg-neutral-50 transition-colors"
          >
            <div class="flex items-center gap-4 text-left">
              <div class="flex items-center justify-center w-8 h-8 rounded-full bg-neutral-800 text-white text-sm font-semibold">
                {idx + 1}
              </div>
              <div>
                <h3 class="text-base font-semibold text-neutral-800">{phase.name}</h3>
                {#if phase.description}
                  <p class="text-sm text-neutral-500 mt-0.5">{phase.description}</p>
                {/if}
                <div class="flex items-center gap-4 mt-2 text-xs text-neutral-500">
                  {#if phase.duration_days}
                    <span>Duration: {phase.duration_days} days</span>
                  {/if}
                  <span>Weight: {phase.weight}</span>
                  <span>{phase.milestones.length} milestones</span>
                  <span>{phase.required_documents.length} documents</span>
                  <span>{phase.compliance_checkpoints.length} compliance items</span>
                </div>
              </div>
            </div>
            <svg
              class="w-5 h-5 text-neutral-400 transition-transform {expandedPhases.has(phase.id) ? 'rotate-180' : ''}"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              stroke-width="2"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
            </svg>
          </button>

          {#if expandedPhases.has(phase.id)}
            <div class="border-t border-neutral-200 p-6 bg-neutral-50">
              <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <!-- Milestones -->
                {#if phase.milestones.length > 0}
                  <div>
                    <h4 class="text-sm font-semibold text-neutral-800 mb-3">Milestones</h4>
                    <ul class="space-y-2">
                      {#each phase.milestones as milestone}
                        <li class="flex items-start gap-2">
                          <svg class="w-4 h-4 text-green-600 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
                          </svg>
                          <div class="flex-1 min-w-0">
                            <p class="text-sm text-neutral-800">{milestone.name}</p>
                            {#if milestone.days_from_phase_start !== null}
                              <p class="text-xs text-neutral-500">Day {milestone.days_from_phase_start}</p>
                            {/if}
                          </div>
                        </li>
                      {/each}
                    </ul>
                  </div>
                {/if}

                <!-- Required Documents -->
                {#if phase.required_documents.length > 0}
                  <div>
                    <h4 class="text-sm font-semibold text-neutral-800 mb-3">Required Documents</h4>
                    <ul class="space-y-2">
                      {#each phase.required_documents as doc}
                        <li class="flex items-start gap-2">
                          <svg class="w-4 h-4 text-blue-600 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                            <path stroke-linecap="round" stroke-linejoin="round" d={getDocumentIcon(doc.category)} />
                          </svg>
                          <div class="flex-1 min-w-0">
                            <p class="text-sm text-neutral-800">{doc.name}</p>
                            <p class="text-xs text-neutral-500">{doc.category_display}</p>
                          </div>
                        </li>
                      {/each}
                    </ul>
                  </div>
                {/if}

                <!-- Compliance Checkpoints -->
                {#if phase.compliance_checkpoints.length > 0}
                  <div>
                    <h4 class="text-sm font-semibold text-neutral-800 mb-3">Compliance</h4>
                    <ul class="space-y-2">
                      {#each phase.compliance_checkpoints as checkpoint}
                        <li class="flex items-start gap-2">
                          <svg class="w-4 h-4 text-orange-600 mt-0.5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z" />
                          </svg>
                          <div class="flex-1 min-w-0">
                            <p class="text-sm text-neutral-800">{checkpoint.name}</p>
                            {#if checkpoint.regulatory_reference}
                              <p class="text-xs text-neutral-500">{checkpoint.regulatory_reference}</p>
                            {/if}
                          </div>
                        </li>
                      {/each}
                    </ul>
                  </div>
                {/if}
              </div>
            </div>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</div>

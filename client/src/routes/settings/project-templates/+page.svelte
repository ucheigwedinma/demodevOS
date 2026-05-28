<script lang="ts">
  import { onMount } from "svelte";
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { ProjectTemplateListItem, TemplateType, PaginatedResponse } from "$lib/types";

  let templates = $state<ProjectTemplateListItem[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let filterType = $state<TemplateType | "all">("all");

  const templateTypeOptions: { value: TemplateType | "all"; label: string }[] = [
    { value: "all", label: "All Templates" },
    { value: "residential", label: "Residential" },
    { value: "mixed_use", label: "Mixed-Use" },
    { value: "commercial", label: "Commercial" },
    { value: "infrastructure", label: "Infrastructure" },
  ];

  onMount(async () => {
    await loadTemplates();
  });

  async function loadTemplates() {
    loading = true;
    error = null;
    try {
      const params: any = {};
      if (filterType !== "all") {
        params.template_type = filterType;
      }
      const res = await api.get<PaginatedResponse<ProjectTemplateListItem>>("/settings/project-templates/", params);
      templates = res.results;
    } catch (err: any) {
      error = err.response?.data?.detail || "Failed to load project templates";
    } finally {
      loading = false;
    }
  }

  async function deleteTemplate(id: number, name: string) {
    if (!confirm(`Delete project template "${name}"? This cannot be undone.`)) return;

    try {
      await api.delete(`/settings/project-templates/${id}/`);
      toast.success("Deleted", "Project template deleted successfully");
      loadTemplates();
    } catch {
      toast.error("Error", "Could not delete template. It may be in use by projects.");
    }
  }

  async function toggleActive(template: ProjectTemplateListItem) {
    try {
      await api.patch(`/settings/project-templates/${template.id}/`, { is_active: !template.is_active });
      toast.success("Updated", `Template ${template.is_active ? "deactivated" : "activated"}`);
      loadTemplates();
    } catch {
      toast.error("Error", "Could not update template status");
    }
  }

  $effect(() => {
    void filterType;
    loadTemplates();
  });

  function getTypeColor(type: TemplateType): string {
    const colors: Record<TemplateType, string> = {
      residential: "bg-blue-100 text-blue-900",
      mixed_use: "bg-purple-100 text-purple-900",
      commercial: "bg-green-100 text-green-900",
      infrastructure: "bg-orange-100 text-orange-900",
    };
    return colors[type] || "bg-neutral-100 text-neutral-800";
  }
</script>

<div class="max-w-6xl">
  <div class="mb-8 flex items-start justify-between">
    <div>
      <h1 class="text-2xl font-bold text-neutral-800 mb-2">Project Templates</h1>
      <p class="text-sm text-neutral-500">
        Pre-defined templates for residential, commercial, mixed-use, and infrastructure projects.
      </p>
    </div>
    <a
      href="/settings/project-templates/new"
      class="px-4 py-2.5 bg-neutral-800 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
    >
      + New Template
    </a>
  </div>

  <!-- Filters -->
  <div class="mb-6 flex items-center gap-3">
    <label for="filter-type" class="text-sm font-medium text-neutral-700">Filter by type:</label>
    <select
      id="filter-type"
      bind:value={filterType}
      class="px-3 py-2 border border-neutral-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800"
    >
      {#each templateTypeOptions as option}
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
  {:else if templates.length === 0}
    <div class="bg-white rounded-xl border border-neutral-200 p-12 text-center">
      <svg class="w-12 h-12 text-neutral-300 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1">
        <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
      </svg>
      <p class="text-sm text-neutral-500">No project templates found.</p>
      <a
        href="/settings/project-templates/new"
        class="mt-4 inline-block text-sm font-medium text-neutral-800 hover:underline"
      >
        Create your first template
      </a>
    </div>
  {:else}
    <div class="bg-white rounded-xl border border-neutral-200 overflow-hidden">
      <table class="w-full">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50">
            <th class="text-left px-6 py-3 text-xs font-semibold text-neutral-600 uppercase tracking-wider">
              Template Name
            </th>
            <th class="text-left px-6 py-3 text-xs font-semibold text-neutral-600 uppercase tracking-wider">
              Type
            </th>
            <th class="text-left px-6 py-3 text-xs font-semibold text-neutral-600 uppercase tracking-wider">
              Phases
            </th>
            <th class="text-left px-6 py-3 text-xs font-semibold text-neutral-600 uppercase tracking-wider">
              Status
            </th>
            <th class="text-right px-6 py-3 text-xs font-semibold text-neutral-600 uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-200">
          {#each templates as template}
            <tr class="hover:bg-neutral-50 transition-colors">
              <td class="px-6 py-4">
                <div>
                  <a
                    href="/settings/project-templates/{template.id}"
                    class="text-sm font-medium text-neutral-800 hover:text-neutral-700"
                  >
                    {template.name}
                  </a>
                  {#if template.is_system}
                    <span class="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-neutral-100 text-neutral-700">
                      System
                    </span>
                  {/if}
                  {#if template.description}
                    <p class="text-sm text-neutral-500 mt-0.5">{template.description}</p>
                  {/if}
                </div>
              </td>
              <td class="px-6 py-4">
                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {getTypeColor(template.template_type)}">
                  {template.template_type_display}
                </span>
              </td>
              <td class="px-6 py-4">
                <span class="text-sm text-neutral-800">{template.phase_count}</span>
              </td>
              <td class="px-6 py-4">
                <button
                  onclick={() => toggleActive(template)}
                  class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium cursor-pointer transition-colors {template.is_active
                    ? 'bg-green-100 text-green-800 hover:bg-green-200'
                    : 'bg-neutral-100 text-neutral-600 hover:bg-neutral-200'}"
                >
                  {template.is_active ? "Active" : "Inactive"}
                </button>
              </td>
              <td class="px-6 py-4 text-right">
                <div class="flex items-center justify-end gap-3">
                  <a
                    href="/settings/project-templates/{template.id}"
                    class="text-sm font-medium text-neutral-700 hover:text-neutral-800"
                  >
                    Edit
                  </a>
                  {#if !template.is_system}
                    <button
                      onclick={() => deleteTemplate(template.id, template.name)}
                      class="text-sm font-medium text-red-500 hover:text-red-700 transition-colors"
                    >
                      Delete
                    </button>
                  {/if}
                </div>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>

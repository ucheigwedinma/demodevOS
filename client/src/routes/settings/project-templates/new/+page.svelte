<script lang="ts">
  import { goto } from "$app/navigation";
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { TemplateType } from "$lib/types";

  let saving = $state(false);
  let formData = $state({
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

  async function handleSubmit() {
    if (!formData.name.trim()) {
      toast.error("Validation Error", "Template name is required");
      return;
    }

    saving = true;
    try {
      const created = await api.post<{ id: number }>("/settings/project-templates/", formData);
      toast.success("Created", "Project template created successfully");
      goto(`/settings/project-templates/${created.id}`);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || "Failed to create template";
      toast.error("Save Failed", errorMsg);
      saving = false;
    }
  }
</script>

<div class="max-w-4xl">
  <div class="mb-8">
    <h1 class="text-2xl font-bold text-neutral-800 mb-2">New Project Template</h1>
    <p class="text-sm text-neutral-500">
      Create a reusable template for real estate development projects.
    </p>
  </div>

  <form class="space-y-6" onsubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
    <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-6">
      <!-- Template Name -->
      <div>
        <label for="name" class="block text-sm font-medium text-neutral-700 mb-2">
          Template Name <span class="text-red-500">*</span>
        </label>
        <input
          id="name"
          type="text"
          bind:value={formData.name}
          placeholder="e.g., Residential Tower Development"
          class="w-full rounded-lg border border-neutral-300 bg-white px-4 py-2.5 text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
          required
        />
      </div>

      <!-- Template Type -->
      <div>
        <span id="template-type-label" class="block text-sm font-medium text-neutral-700 mb-2">
          Template Type <span class="text-red-500">*</span>
        </span>
        <div 
          class="grid grid-cols-2 sm:grid-cols-4 gap-3"
          role="radiogroup"
          aria-labelledby="template-type-label"
        >
          {#each templateTypeOptions as option}
            <button
              type="button"
              onclick={() => (formData.template_type = option.value)}
              role="radio"
              aria-checked={formData.template_type === option.value}
              class="px-4 py-3 text-center text-sm font-medium rounded-lg border-2 transition-all
                     {formData.template_type === option.value
                       ? 'border-neutral-800 bg-neutral-50 text-neutral-800'
                       : 'border-neutral-200 text-neutral-600 hover:border-neutral-400'}"
            >
              {option.label}
            </button>
          {/each}
        </div>
      </div>

      <!-- Description -->
      <div>
        <label for="description" class="block text-sm font-medium text-neutral-700 mb-2">
          Description
        </label>
        <textarea
          id="description"
          bind:value={formData.description}
          rows="4"
          placeholder="Describe when to use this template and what it includes..."
          class="w-full rounded-lg border border-neutral-300 bg-white px-4 py-2.5 text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent resize-none"
        ></textarea>
      </div>

      <!-- Active Status -->
      <div>
        <label class="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            bind:checked={formData.is_active}
            class="w-4 h-4 text-neutral-800 border-neutral-300 rounded focus:ring-neutral-800 focus:ring-offset-0"
          />
          <div>
            <p class="text-sm font-medium text-neutral-800">Active</p>
            <p class="text-xs text-neutral-500">Make this template available for project creation</p>
          </div>
        </label>
      </div>
    </div>

    <!-- Info Box -->
    <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
      <div class="flex gap-3">
        <svg class="w-5 h-5 text-blue-600 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z" />
        </svg>
        <div class="flex-1">
          <p class="text-sm font-medium text-blue-900 mb-1">Next Steps</p>
          <p class="text-sm text-blue-700">
            After creating this template, you can add phases, milestones, required documents, and compliance checkpoints.
          </p>
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div class="flex items-center justify-between pt-2">
      <a
        href="/settings/project-templates"
        class="px-5 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
      >
        Cancel
      </a>
      <button
        type="submit"
        disabled={saving}
        class="px-6 py-2.5 bg-neutral-800 text-white text-sm font-semibold rounded-lg hover:bg-neutral-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {saving ? "Creating..." : "Create Template"}
      </button>
    </div>
  </form>
</div>

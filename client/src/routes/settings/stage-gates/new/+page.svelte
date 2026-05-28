<script lang="ts">
  import { goto } from "$app/navigation";
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { StageGateStage, ProjectTemplateListItem, PaginatedResponse } from "$lib/types";

  let saving = $state(false);
  let templates = $state<ProjectTemplateListItem[]>([]);

  let formData = $state({
    name: "",
    stage: "feasibility" as StageGateStage,
    template: null as number | null,
    description: "",
    is_active: true,
  });

  const stageOptions: { value: StageGateStage; label: string }[] = [
    { value: "feasibility", label: "Feasibility" },
    { value: "design", label: "Design" },
    { value: "pre_sales", label: "Pre-Sales" },
    { value: "construction_start", label: "Construction Start" },
    { value: "handover", label: "Handover" },
  ];

  async function loadTemplates() {
    try {
      const res = await api.get<PaginatedResponse<ProjectTemplateListItem>>("/settings/project-templates/", { is_active: "true", page_size: "100" });
      templates = res.results;
    } catch {
      // Non-critical - template selector will just be empty
    }
  }

  async function handleSubmit() {
    if (!formData.name.trim()) {
      toast.error("Validation Error", "Rule name is required");
      return;
    }

    saving = true;
    try {
      const payload: any = { ...formData };
      if (!payload.template) {
        payload.template = null;
      }
      const created = await api.post<{ id: number }>("/settings/stage-gate-rules/", payload);
      toast.success("Created", "Stage-gate rule created successfully");
      goto(`/settings/stage-gates/${created.id}`);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail || "Failed to create rule";
      toast.error("Save Failed", errorMsg);
      saving = false;
    }
  }

  $effect(() => {
    loadTemplates();
  });
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
    <h1 class="text-2xl font-bold text-neutral-800 mb-2">New Stage-Gate Rule</h1>
    <p class="text-sm text-neutral-500">
      Define an approval checkpoint for a project stage.
    </p>
  </div>

  <form class="space-y-6" onsubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
    <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-6">
      <!-- Rule Name -->
      <div>
        <label for="name" class="block text-sm font-medium text-neutral-700 mb-2">
          Rule Name <span class="text-red-500">*</span>
        </label>
        <input
          id="name"
          type="text"
          bind:value={formData.name}
          placeholder="e.g., Feasibility Study Approval"
          class="w-full rounded-lg border border-neutral-300 bg-white px-4 py-2.5 text-sm text-neutral-800 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
          required
        />
      </div>

      <!-- Stage -->
      <div>
        <span id="stage-label" class="block text-sm font-medium text-neutral-700 mb-2">
          Stage <span class="text-red-500">*</span>
        </span>
        <div
          class="grid grid-cols-2 sm:grid-cols-5 gap-3"
          role="radiogroup"
          aria-labelledby="stage-label"
        >
          {#each stageOptions as option}
            <button
              type="button"
              onclick={() => (formData.stage = option.value)}
              role="radio"
              aria-checked={formData.stage === option.value}
              class="px-4 py-3 text-center text-sm font-medium rounded-lg border-2 transition-all
                     {formData.stage === option.value
                       ? 'border-neutral-800 bg-neutral-50 text-neutral-800'
                       : 'border-neutral-200 text-neutral-600 hover:border-neutral-400'}"
            >
              {option.label}
            </button>
          {/each}
        </div>
      </div>

      <!-- Template -->
      <div>
        <label for="template" class="block text-sm font-medium text-neutral-700 mb-2">
          Applies To
        </label>
        <select
          id="template"
          bind:value={formData.template}
          class="w-full rounded-lg border border-neutral-300 bg-white px-4 py-2.5 text-sm text-neutral-800 focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
        >
          <option value={null}>All Projects</option>
          {#each templates as template}
            <option value={template.id}>{template.name}</option>
          {/each}
        </select>
        <p class="text-xs text-neutral-500 mt-1.5">Leave as "All Projects" to apply this rule universally.</p>
      </div>

      <!-- Description -->
      <div>
        <label for="description" class="block text-sm font-medium text-neutral-700 mb-2">
          Description
        </label>
        <textarea
          id="description"
          bind:value={formData.description}
          rows="3"
          placeholder="Describe what must be completed before passing this gate..."
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
            <p class="text-xs text-neutral-500">Make this rule active for project stage approvals</p>
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
            After creating this rule, you can add checklist items that must be completed before passing the gate.
          </p>
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div class="flex items-center justify-between pt-2">
      <a
        href="/settings/stage-gates"
        class="px-5 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
      >
        Cancel
      </a>
      <button
        type="submit"
        disabled={saving}
        class="px-6 py-2.5 bg-neutral-800 text-white text-sm font-semibold rounded-lg hover:bg-neutral-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {saving ? "Creating..." : "Create Rule"}
      </button>
    </div>
  </form>
</div>

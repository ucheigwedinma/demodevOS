<script lang="ts">
  import { page } from "$app/stores";
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import StepConfigPanel from "$lib/components/workflows/StepConfigPanel.svelte";
  import type { WorkflowTemplateDetail, WorkflowTemplateStep, ContentTypeOption, PaginatedResponse, RoleListItem } from "$lib/types";

  let loading = $state(true);
  let saving = $state(false);
  let template = $state<WorkflowTemplateDetail | null>(null);
  let contentTypes = $state<ContentTypeOption[]>([]);
  let roles = $state<{ slug: string; name: string }[]>([]);
  let selectedStep = $state<Partial<WorkflowTemplateStep> | null>(null);
  let editingName = $state(false);
  let nameInput = $state("");

  const templateId = $derived($page.params.id);

  const MODEL_LABELS: Record<string, string> = {
    "finance.bill": "Bills",
    "finance.invoice": "Invoices",
    "finance.budget": "Budgets",
    "procurement.purchaseorder": "Purchase Orders",
    "procurement.purchaserequisition": "Requisitions",
    "procurement.requestforquotation": "RFQs",
    "documents.document": "Documents",
  };

  const STEP_TYPE_ICONS: Record<string, { path: string; bg: string; ring: string }> = {
    approval: {
      path: "M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
      bg: "bg-neutral-800",
      ring: "ring-neutral-200",
    },
    condition: {
      path: "M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 5.25h.008v.008H12v-.008Z",
      bg: "bg-amber-500",
      ring: "ring-amber-200",
    },
    notification: {
      path: "M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0",
      bg: "bg-blue-500",
      ring: "ring-blue-200",
    },
  };

  async function loadTemplate() {
    loading = true;
    try {
      const [tData, ctData, roleData] = await Promise.all([
        api.get<WorkflowTemplateDetail>(`/workflows/templates/${templateId}/`),
        api.get<ContentTypeOption[]>("/workflows/content-types/"),
        api.get<PaginatedResponse<RoleListItem>>("/settings/roles/"),
      ]);
      template = tData;
      contentTypes = ctData;
      roles = roleData.results.map((r) => ({ slug: r.slug, name: r.name }));
      nameInput = tData.name;
    } catch {
      toast.error("Load failed", "Could not load workflow template.");
    } finally {
      loading = false;
    }
  }

  async function saveTemplateMeta() {
    if (!template) return;
    saving = true;
    try {
      await api.patch(`/workflows/templates/${templateId}/`, {
        name: nameInput,
        default_step_mode: template.default_step_mode,
        is_default: template.is_default,
        is_active: template.is_active,
        applicable_content_types: template.applicable_content_types,
      });
      template.name = nameInput;
      editingName = false;
      toast.success("Saved", "Template updated.");
    } catch {
      toast.error("Error", "Could not save template.");
    } finally {
      saving = false;
    }
  }

  function addStep(type: "approval" | "condition" | "notification") {
    const maxSeq = template?.steps?.length ? Math.max(...template.steps.map((s) => s.sequence)) : 0;
    selectedStep = {
      sequence: maxSeq + 1,
      name: "",
      step_type: type,
      execution_mode: template?.default_step_mode || "sequential",
      approver_role_slug: "",
      sla_hours: null,
      escalation_role_slug: "",
      condition_field: "",
      condition_operator: "gt",
      condition_value: "",
      condition_true_step: null,
      condition_false_step: null,
      is_active: true,
    };
  }

  async function handleSaveStep(step: Partial<WorkflowTemplateStep>) {
    if (!template) return;
    try {
      if (step.id) {
        await api.patch(`/workflows/template-steps/${step.id}/`, step);
        toast.success("Updated", "Step updated.");
      } else {
        await api.post(`/workflows/templates/${templateId}/steps/`, step);
        toast.success("Created", "Step added.");
      }
      selectedStep = null;
      loadTemplate();
    } catch {
      toast.error("Error", "Could not save step.");
    }
  }

  async function handleDeleteStep() {
    if (!selectedStep?.id) return;
    try {
      await api.delete(`/workflows/template-steps/${selectedStep.id}/`);
      toast.success("Deleted", "Step removed.");
      selectedStep = null;
      loadTemplate();
    } catch {
      toast.error("Error", "Could not delete step.");
    }
  }

  async function toggleActive() {
    if (!template) return;
    try {
      await api.patch(`/workflows/templates/${templateId}/`, { is_active: !template.is_active });
      template.is_active = !template.is_active;
      toast.success("Updated", `Template ${template.is_active ? "activated" : "deactivated"}.`);
    } catch {
      toast.error("Error", "Could not update template.");
    }
  }

  function toggleContentType(ctId: number) {
    if (!template) return;
    const idx = template.applicable_content_types.indexOf(ctId);
    if (idx >= 0) {
      template.applicable_content_types = template.applicable_content_types.filter((id) => id !== ctId);
    } else {
      template.applicable_content_types = [...template.applicable_content_types, ctId];
    }
  }

  $effect(() => {
    if (templateId) loadTemplate();
  });
</script>

{#if loading}
  <div class="flex items-center justify-center py-20">
    <div class="w-5 h-5 border-2 border-neutral-300 border-t-neutral-800 rounded-full animate-spin"></div>
  </div>
{:else if template}
  <div>
    <!-- Toolbar -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-4">
        <!-- svelte-ignore a11y_consider_explicit_label -->
        <a href="/settings/workflows" class="text-neutral-400 hover:text-neutral-700 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
          </svg>
        </a>
        {#if editingName}
          <div class="flex items-center gap-2">
            <input
              type="text"
              bind:value={nameInput}
              class="text-xl font-semibold text-neutral-800 border-b-2 border-neutral-800 focus:outline-none bg-transparent"
              onkeydown={(e) => { if (e.key === "Enter") saveTemplateMeta(); if (e.key === "Escape") { editingName = false; nameInput = template?.name || ""; } }}
            />
            <button onclick={saveTemplateMeta} class="text-xs font-medium text-neutral-800">Save</button>
          </div>
        {:else}
          <button onclick={() => editingName = true} class="text-xl font-semibold text-neutral-800 hover:text-neutral-600 transition-colors">
            {template.name}
          </button>
        {/if}
        <span class="text-xs font-mono text-neutral-400">{template.code}</span>
      </div>
      <div class="flex items-center gap-3">
        <button
          onclick={toggleActive}
          class="flex items-center gap-2 group"
          aria-label={template.is_active ? "Deactivate workflow" : "Activate workflow"}
        >
          <span class="text-xs font-medium {template.is_active ? 'text-emerald-600' : 'text-neutral-400'}">
            {template.is_active ? "Active" : "Inactive"}
          </span>
          <span
            class="relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors
                   {template.is_active ? 'bg-emerald-500' : 'bg-neutral-300'}"
          >
            <span
              class="inline-block h-3.5 w-3.5 rounded-full bg-white shadow-sm transition-transform
                     {template.is_active ? 'translate-x-[18px]' : 'translate-x-[3px]'}"
            ></span>
          </span>
        </button>
        <button
          onclick={saveTemplateMeta}
          disabled={saving}
          class="px-4 py-1.5 bg-neutral-800 text-white text-xs font-medium rounded-lg hover:bg-neutral-800 disabled:opacity-40 transition-colors"
        >
          {saving ? "Saving..." : "Save"}
        </button>
      </div>
    </div>

    <!-- Config bar -->
    <div class="bg-white border border-neutral-200 rounded-xl p-4 mb-6 flex items-center gap-6 flex-wrap">
      <div class="flex items-center gap-2">
        <span class="text-xs font-medium text-neutral-500">Mode:</span>
        <select
          bind:value={template.default_step_mode}
          class="border border-neutral-200 rounded-lg px-2.5 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
        >
          <option value="sequential">Sequential</option>
          <option value="parallel">Parallel</option>
        </select>
      </div>
      <div class="border-l border-neutral-100 pl-6 flex items-center gap-2 flex-wrap">
        <span class="text-xs font-medium text-neutral-500">Applies to:</span>
        {#each contentTypes as ct}
          <button
            onclick={() => toggleContentType(ct.id)}
            class="px-2.5 py-1 rounded-full text-xs font-medium border transition-colors
                   {template.applicable_content_types.includes(ct.id) ? 'bg-neutral-800 text-white border-neutral-800' : 'bg-white text-neutral-500 border-neutral-200 hover:border-neutral-300'}"
          >
            {MODEL_LABELS[ct.label] || ct.label}
          </button>
        {/each}
      </div>
      <div class="border-l border-neutral-100 pl-6">
        <label class="flex items-center gap-2 text-xs">
          <input type="checkbox" bind:checked={template.is_default} class="rounded border-neutral-300" />
          <span class="font-medium text-neutral-500">Default template</span>
        </label>
      </div>
    </div>

    <!-- Visual Canvas -->
    <div class="bg-white border border-neutral-200 rounded-xl p-6 mb-6">
      <div class="flex items-center justify-between mb-4">
        <h3 class="text-sm font-semibold text-neutral-800">Workflow Steps</h3>
        <div class="flex items-center gap-2">
          <button
            onclick={() => addStep("approval")}
            class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-neutral-600 bg-neutral-50 border border-neutral-200 rounded-lg hover:bg-neutral-100 transition-colors"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            Approval
          </button>
          <button
            onclick={() => addStep("condition")}
            class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-amber-600 bg-amber-50 border border-amber-200 rounded-lg hover:bg-amber-100 transition-colors"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            Condition
          </button>
          <button
            onclick={() => addStep("notification")}
            class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            Notification
          </button>
        </div>
      </div>

      {#if template.steps.length === 0}
        <div class="text-center py-16 text-neutral-400">
          <svg class="w-10 h-10 mx-auto mb-3 text-neutral-200" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 0 1 0 3.75H5.625a1.875 1.875 0 0 1 0-3.75Z" />
          </svg>
          <p class="text-sm">No steps defined yet. Add an approval, condition, or notification step.</p>
        </div>
      {:else}
        <!-- Node graph -->
        <div class="relative">
          <!-- Start node -->
          <div class="flex items-center gap-4 mb-0">
            <div class="w-10 h-10 rounded-full bg-neutral-100 flex items-center justify-center">
              <svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z" />
              </svg>
            </div>
            <span class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Start</span>
          </div>

          {#each template.steps as step, i}
            {@const icon = STEP_TYPE_ICONS[step.step_type] || STEP_TYPE_ICONS.approval}
            <!-- Connector line -->
            <div class="ml-5 w-0.5 h-6 bg-neutral-200"></div>

            <!-- Step node -->
            <button
              onclick={() => selectedStep = { ...step }}
              class="flex items-center gap-4 w-full text-left group"
            >
              <div class="w-10 h-10 rounded-full {icon.bg} ring-4 {icon.ring} flex items-center justify-center shrink-0 group-hover:ring-neutral-300 transition-all">
                <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d={icon.path} />
                </svg>
              </div>
              <div class="flex-1 min-w-0 bg-neutral-50 group-hover:bg-neutral-100 border border-neutral-200 group-hover:border-neutral-300 rounded-lg px-4 py-3 transition-all">
                <div class="flex items-center gap-2">
                  <span class="text-[10px] font-bold text-neutral-300">#{step.sequence}</span>
                  <span class="text-sm font-medium text-neutral-800">{step.name}</span>
                  {#if step.execution_mode === "parallel"}
                    <span class="text-[10px] px-1.5 py-0.5 bg-blue-50 text-blue-600 rounded font-medium">Parallel</span>
                  {/if}
                  {#if !step.is_active}
                    <span class="text-[10px] px-1.5 py-0.5 bg-neutral-100 text-neutral-400 rounded font-medium">Inactive</span>
                  {/if}
                </div>
                <div class="flex items-center gap-3 mt-1 text-xs text-neutral-400">
                  <span class="capitalize">{step.step_type}</span>
                  {#if step.approver_role_slug}
                    <span>· {step.approver_role_slug.replace(/-/g, " ")}</span>
                  {/if}
                  {#if step.sla_hours}
                    <span>· {step.sla_hours}h SLA</span>
                  {/if}
                  {#if step.step_type === "condition"}
                    <span>· {step.condition_field} {step.condition_operator} {step.condition_value}</span>
                  {/if}
                </div>
              </div>
            </button>

            {#if step.step_type === "condition" && (step.condition_true_step || step.condition_false_step)}
              <!-- Branch indicators -->
              <div class="ml-16 flex gap-6 mt-1 mb-1">
                {#if step.condition_true_step}
                  <span class="text-[10px] font-medium text-emerald-500">✓ → Step #{step.condition_true_step}</span>
                {/if}
                {#if step.condition_false_step}
                  <span class="text-[10px] font-medium text-red-400">✗ → Step #{step.condition_false_step}</span>
                {/if}
              </div>
            {/if}
          {/each}

          <!-- Connector to end -->
          <div class="ml-5 w-0.5 h-6 bg-neutral-200"></div>

          <!-- End node -->
          <div class="flex items-center gap-4">
            <div class="w-10 h-10 rounded-full bg-neutral-100 flex items-center justify-center">
              <svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
              </svg>
            </div>
            <span class="text-xs font-medium text-neutral-400 uppercase tracking-wider">Complete</span>
          </div>
        </div>
      {/if}
    </div>
  </div>

  <!-- Slide-out config panel -->
  <StepConfigPanel
    step={selectedStep}
    {roles}
    onSave={handleSaveStep}
    onDelete={handleDeleteStep}
    onClose={() => selectedStep = null}
  />
{/if}

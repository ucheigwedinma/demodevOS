<script lang="ts">
  import type { WorkflowTemplateStep } from "$lib/types";

  interface Props {
    step: Partial<WorkflowTemplateStep> | null;
    roles: { slug: string; name: string }[];
    onSave: (step: Partial<WorkflowTemplateStep>) => void;
    onDelete: () => void;
    onClose: () => void;
  }

  let { step, roles, onSave, onDelete, onClose }: Props = $props();

  let local = $state<Partial<WorkflowTemplateStep>>({});

  $effect(() => {
    if (step) local = { ...step };
  });
</script>

{#if step}
  <!-- Slide-out backdrop -->
  <div class="fixed inset-0 z-40" onclick={onClose}>
    <!-- Panel -->
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
      class="absolute right-0 top-0 h-full w-[560px] bg-white border-l border-neutral-200 shadow-xl overflow-y-auto"
      onclick={(e) => e.stopPropagation()}
    >
      <div class="px-6 py-5 border-b border-neutral-100 flex items-center justify-between">
        <h3 class="text-sm font-semibold text-neutral-900">
          {local.id ? "Edit Step" : "New Step"}
        </h3>
        <button onclick={onClose} class="text-neutral-400 hover:text-neutral-700 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div class="px-6 py-5 space-y-5">
        <!-- Name -->
        <div>
          <label class="block text-xs font-medium text-neutral-500 mb-1.5">Step Name</label>
          <input
            type="text"
            bind:value={local.name}
            placeholder="e.g. Manager Approval"
            class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          />
        </div>

        <!-- Step Type -->
        <div>
          <label class="block text-xs font-medium text-neutral-500 mb-1.5">Step Type</label>
          <div class="flex gap-2">
            {#each [{ v: "approval", l: "Approval", icon: "M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" }, { v: "condition", l: "Condition", icon: "M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 5.25h.008v.008H12v-.008Z" }, { v: "notification", l: "Notify", icon: "M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0" }] as opt}
              <button
                onclick={() => local.step_type = opt.v as any}
                class="flex-1 flex flex-col items-center gap-1.5 py-3 rounded-lg border text-xs font-medium transition-colors
                       {local.step_type === opt.v ? 'border-neutral-900 bg-neutral-900 text-white' : 'border-neutral-200 text-neutral-500 hover:border-neutral-300'}"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d={opt.icon} />
                </svg>
                {opt.l}
              </button>
            {/each}
          </div>
        </div>

        <!-- Execution Mode -->
        <div>
          <label class="block text-xs font-medium text-neutral-500 mb-1.5">Execution Mode</label>
          <select
            bind:value={local.execution_mode}
            class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            <option value="sequential">Sequential</option>
            <option value="parallel">Parallel</option>
          </select>
        </div>

        {#if local.step_type === "approval" || local.step_type === "notification"}
          <!-- Approver Role -->
          <div>
            <label class="block text-xs font-medium text-neutral-500 mb-1.5">Approver Role</label>
            <select
              bind:value={local.approver_role_slug}
              class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            >
              <option value="">Select role...</option>
              {#each roles as role}
                <option value={role.slug}>{role.name}</option>
              {/each}
            </select>
          </div>

          <!-- SLA -->
          <div>
            <label class="block text-xs font-medium text-neutral-500 mb-1.5">SLA (hours)</label>
            <input
              type="number"
              bind:value={local.sla_hours}
              placeholder="e.g. 24"
              min="1"
              class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
          </div>

          <!-- Escalation Role -->
          <div>
            <label class="block text-xs font-medium text-neutral-500 mb-1.5">Escalation Role</label>
            <select
              bind:value={local.escalation_role_slug}
              class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            >
              <option value="">None</option>
              {#each roles as role}
                <option value={role.slug}>{role.name}</option>
              {/each}
            </select>
          </div>
        {/if}

        {#if local.step_type === "condition"}
          <!-- Condition fields -->
          <div>
            <label class="block text-xs font-medium text-neutral-500 mb-1.5">Field Path</label>
            <input
              type="text"
              bind:value={local.condition_field}
              placeholder="e.g. total_amount"
              class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            />
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-xs font-medium text-neutral-500 mb-1.5">Operator</label>
              <select
                bind:value={local.condition_operator}
                class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
              >
                <option value="gt">Greater than</option>
                <option value="gte">Greater or equal</option>
                <option value="lt">Less than</option>
                <option value="lte">Less or equal</option>
                <option value="eq">Equal</option>
                <option value="in">In list</option>
              </select>
            </div>
            <div>
              <label class="block text-xs font-medium text-neutral-500 mb-1.5">Value</label>
              <input
                type="text"
                bind:value={local.condition_value}
                placeholder="10000"
                class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
              />
            </div>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label class="block text-xs font-medium text-neutral-500 mb-1.5">If True → Step #</label>
              <input
                type="number" bind:value={local.condition_true_step} min="1"
                class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
              />
            </div>
            <div>
              <label class="block text-xs font-medium text-neutral-500 mb-1.5">If False → Step #</label>
              <input
                type="number" bind:value={local.condition_false_step} min="1"
                class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
              />
            </div>
          </div>
        {/if}
      </div>

      <!-- Actions -->
      <div class="px-6 py-4 border-t border-neutral-100 flex items-center justify-between">
        {#if local.id}
          <button onclick={onDelete} class="text-xs font-medium text-red-500 hover:text-red-700 transition-colors">Delete Step</button>
        {:else}
          <div></div>
        {/if}
        <div class="flex gap-3">
          <button onclick={onClose} class="px-4 py-2 text-sm font-medium text-neutral-500 hover:text-neutral-900 transition-colors">Cancel</button>
          <button
            onclick={() => onSave(local)}
            disabled={!local.name}
            class="px-4 py-2 bg-neutral-900 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Save Step
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}

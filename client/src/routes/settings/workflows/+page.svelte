<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type { WorkflowTemplateListItem, PaginatedResponse } from "$lib/types";

  let loading = $state(true);
  let templates = $state<WorkflowTemplateListItem[]>([]);
  let showCreate = $state(false);
  let creating = $state(false);
  let form = $state({ code: "", name: "", description: "", default_step_mode: "sequential" as const, is_default: false });

  async function loadTemplates() {
    loading = true;
    try {
      const data = await api.get<PaginatedResponse<WorkflowTemplateListItem>>("/workflows/templates/");
      templates = data.results;
    } catch {
      toast.error("Load failed", "Could not load workflow templates.");
    } finally {
      loading = false;
    }
  }

  async function createTemplate() {
    creating = true;
    try {
      await api.post("/workflows/templates/", form);
      toast.success("Created", "Workflow template created.");
      showCreate = false;
      form = { code: "", name: "", description: "", default_step_mode: "sequential", is_default: false };
      loadTemplates();
    } catch {
      toast.error("Error", "Could not create template.");
    } finally {
      creating = false;
    }
  }

  async function toggleActive(t: WorkflowTemplateListItem) {
    try {
      await api.patch(`/workflows/templates/${t.id}/`, { is_active: !t.is_active });
      t.is_active = !t.is_active;
      toast.success("Updated", `Template ${t.is_active ? "activated" : "deactivated"}.`);
    } catch {
      toast.error("Error", "Could not update template.");
    }
  }

  $effect(() => {
    loadTemplates();
  });

  const MODEL_LABELS: Record<string, string> = {
    "finance.bill": "Bills",
    "finance.invoice": "Invoices",
    "finance.budget": "Budgets",
    "procurement.purchaseorder": "Purchase Orders",
    "procurement.purchaserequisition": "Requisitions",
    "procurement.requestforquotation": "RFQs",
    "documents.document": "Documents",
  };
</script>

<div>
  <!-- Header -->
  <div class="flex items-center justify-between mb-8">
    <div>
      <h2 class="text-xl font-semibold text-neutral-800">Workflow Builder</h2>
      <p class="text-sm text-neutral-500 mt-1">Design approval workflows with conditional logic, parallel steps, and SLA tracking.</p>
    </div>
    <button
      onclick={() => showCreate = !showCreate}
      class="inline-flex items-center gap-2 px-4 py-2.5 bg-neutral-800 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
      </svg>
      New Template
    </button>
  </div>

  <!-- Create Form -->
  {#if showCreate}
    <div class="bg-white border border-neutral-200 rounded-xl p-6 mb-6">
      <h3 class="text-sm font-semibold text-neutral-800 mb-4">New Workflow Template</h3>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <!-- svelte-ignore a11y_label_has_associated_control -->
          <label class="block text-xs font-medium text-neutral-500 mb-1.5">Code</label>
          <input
            type="text"
            bind:value={form.code}
            placeholder="e.g. bill-approval"
            class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
          />
        </div>
        <div>
          <!-- svelte-ignore a11y_label_has_associated_control -->
          <label class="block text-xs font-medium text-neutral-500 mb-1.5">Name</label>
          <input
            type="text"
            bind:value={form.name}
            placeholder="e.g. Bill Approval Workflow"
            class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
          />
        </div>
        <div class="col-span-2">
          <!-- svelte-ignore a11y_label_has_associated_control -->
          <label class="block text-xs font-medium text-neutral-500 mb-1.5">Description</label>
          <textarea
            bind:value={form.description}
            rows={2}
            class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent resize-none"
          ></textarea>
        </div>
        <div>
          <!-- svelte-ignore a11y_label_has_associated_control -->
          <label class="block text-xs font-medium text-neutral-500 mb-1.5">Default Step Mode</label>
          <select
            bind:value={form.default_step_mode}
            class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
          >
            <option value="sequential">Sequential</option>
            <option value="parallel">Parallel</option>
          </select>
        </div>
        <div class="flex items-end">
          <label class="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" bind:checked={form.is_default} class="rounded border-neutral-300" />
            <span class="text-sm text-neutral-700">Set as default template</span>
          </label>
        </div>
      </div>
      <div class="flex justify-end gap-3 mt-5">
        <button
          onclick={() => showCreate = false}
          class="px-4 py-2 text-sm font-medium text-neutral-600 hover:text-neutral-800 transition-colors"
        >
          Cancel
        </button>
        <button
          onclick={createTemplate}
          disabled={creating || !form.code || !form.name}
          class="px-4 py-2 bg-neutral-800 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {creating ? "Creating..." : "Create Template"}
        </button>
      </div>
    </div>
  {/if}

  <!-- Template Grid -->
  {#if loading}
    <div class="flex items-center justify-center py-20">
      <div class="w-5 h-5 border-2 border-neutral-300 border-t-neutral-800 rounded-full animate-spin"></div>
    </div>
  {:else if templates.length === 0}
    <div class="text-center py-20 bg-white border border-neutral-200 rounded-xl">
      <svg class="w-12 h-12 mx-auto text-neutral-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 0 1 0 3.75H5.625a1.875 1.875 0 0 1 0-3.75Z" />
      </svg>
      <p class="text-sm text-neutral-500">No workflow templates yet. Create one to get started.</p>
    </div>
  {:else}
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      {#each templates as t}
        <a
          href="/settings/workflows/{t.id}"
          class="bg-white border border-neutral-200 rounded-xl p-5 hover:border-neutral-300 hover:shadow-sm transition-all group"
        >
          <div class="flex items-start justify-between mb-3">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <h3 class="text-sm font-semibold text-neutral-800 truncate group-hover:text-neutral-700">{t.name}</h3>
                {#if t.is_default}
                  <span class="inline-flex items-center px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider bg-neutral-100 text-neutral-600 rounded-full">Default</span>
                {/if}
              </div>
              <p class="text-xs text-neutral-400 font-mono mt-0.5">{t.code}</p>
            </div>
            <!-- svelte-ignore a11y_consider_explicit_label -->
            <button
              onclick={(e) => { e.preventDefault(); e.stopPropagation(); toggleActive(t); }}
              class="shrink-0 w-8 h-5 rounded-full transition-colors {t.is_active ? 'bg-neutral-800' : 'bg-neutral-200'} relative"
            >
              <span class="absolute top-0.5 {t.is_active ? 'left-3.5' : 'left-0.5'} w-4 h-4 bg-white rounded-full shadow transition-all"></span>
            </button>
          </div>
          {#if t.description}
            <p class="text-xs text-neutral-500 mb-3 line-clamp-2">{t.description}</p>
          {/if}
          <div class="flex items-center gap-4 text-xs text-neutral-400">
            <span class="flex items-center gap-1">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 0 1 0 3.75H5.625a1.875 1.875 0 0 1 0-3.75Z" />
              </svg>
              {t.step_count} step{t.step_count !== 1 ? "s" : ""}
            </span>
            <span class="capitalize">{t.default_step_mode}</span>
            {#each t.applicable_models as model}
              <span class="px-1.5 py-0.5 bg-neutral-50 rounded text-[10px] font-medium">{MODEL_LABELS[model] || model}</span>
            {/each}
          </div>
        </a>
      {/each}
    </div>
  {/if}
</div>

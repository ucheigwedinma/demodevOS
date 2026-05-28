<script lang="ts">
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import { currency } from "$lib/stores/currency.svelte";
  import type { ApprovalPolicyListItem, WorkflowTemplateListItem, ContentTypeOption, PaginatedResponse } from "$lib/types";

  let loading = $state(true);
  let policies = $state<ApprovalPolicyListItem[]>([]);
  let templates = $state<WorkflowTemplateListItem[]>([]);
  let contentTypes = $state<ContentTypeOption[]>([]);
  let showCreate = $state(false);
  let creating = $state(false);
  let editingId = $state<number | null>(null);

  let form = $state({
    name: "",
    policy_type: "financial_threshold" as string,
    content_type: null as number | null,
    amount_field: "total_amount",
    min_amount: null as number | null,
    max_amount: null as number | null,
    template: null as number | null,
    priority: 100,
    is_active: true,
  });

  const POLICY_TYPE_LABELS: Record<string, string> = {
    financial_threshold: "Financial Threshold",
    procurement_threshold: "Procurement Threshold",
    contract_review: "Contract Review",
    change_order: "Change Order",
  };

  const MODEL_LABELS: Record<string, string> = {
    "finance.bill": "Bill",
    "finance.invoice": "Invoice",
    "finance.budget": "Budget",
    "procurement.purchaseorder": "Purchase Order",
    "procurement.purchaserequisition": "Requisition",
    "procurement.requestforquotation": "RFQ",
    "documents.document": "Document",
  };

  async function loadData() {
    loading = true;
    try {
      const [pRes, tRes, ctRes] = await Promise.all([
        api.get<PaginatedResponse<ApprovalPolicyListItem>>("/workflows/policies/"),
        api.get<PaginatedResponse<WorkflowTemplateListItem>>("/workflows/templates/"),
        api.get<ContentTypeOption[]>("/workflows/content-types/"),
      ]);
      policies = pRes.results;
      templates = tRes.results;
      contentTypes = ctRes;
    } catch {
      toast.error("Load failed", "Could not load approval policies.");
    } finally {
      loading = false;
    }
  }

  function resetForm() {
    form = { name: "", policy_type: "financial_threshold", content_type: null, amount_field: "total_amount", min_amount: null, max_amount: null, template: null, priority: 100, is_active: true };
    editingId = null;
    showCreate = false;
  }

  function startEdit(p: ApprovalPolicyListItem) {
    form = {
      name: p.name,
      policy_type: p.policy_type,
      content_type: p.content_type,
      amount_field: p.amount_field,
      min_amount: p.min_amount ? Number(p.min_amount) : null,
      max_amount: p.max_amount ? Number(p.max_amount) : null,
      template: p.template,
      priority: p.priority,
      is_active: p.is_active,
    };
    editingId = p.id;
    showCreate = true;
  }

  async function savePolicy() {
    creating = true;
    const payload = {
      ...form,
      min_amount: form.min_amount ?? null,
      max_amount: form.max_amount ?? null,
    };
    try {
      if (editingId) {
        await api.patch(`/workflows/policies/${editingId}/`, payload);
        toast.success("Updated", "Approval policy updated.");
      } else {
        await api.post("/workflows/policies/", payload);
        toast.success("Created", "Approval policy created.");
      }
      resetForm();
      loadData();
    } catch {
      toast.error("Error", "Could not save policy.");
    } finally {
      creating = false;
    }
  }

  async function deletePolicy(id: number) {
    try {
      await api.delete(`/workflows/policies/${id}/`);
      toast.success("Deleted", "Approval policy deleted.");
      loadData();
    } catch {
      toast.error("Error", "Could not delete policy.");
    }
  }

  $effect(() => { loadData(); });
</script>

<div>
  <!-- Header -->
  <div class="flex items-center justify-between mb-8">
    <div>
      <h2 class="text-xl font-semibold text-neutral-800">Approval Policies</h2>
      <p class="text-sm text-neutral-500 mt-1">Configure threshold-based routing rules that automatically assign workflows.</p>
    </div>
    <button
      onclick={() => { resetForm(); showCreate = true; }}
      class="inline-flex items-center gap-2 px-4 py-2.5 bg-neutral-800 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 transition-colors"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
      </svg>
      New Policy
    </button>
  </div>

  <!-- Create / Edit Form -->
  {#if showCreate}
    <div class="bg-white border border-neutral-200 rounded-xl p-6 mb-6">
      <h3 class="text-sm font-semibold text-neutral-800 mb-4">{editingId ? "Edit" : "New"} Approval Policy</h3>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <!-- svelte-ignore a11y_label_has_associated_control -->
          <label class="block text-xs font-medium text-neutral-500 mb-1.5">Policy Name</label>
          <input
            type="text" bind:value={form.name} placeholder={`e.g. Bills < ${currency.formatCompact(10000)}`}
            class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
          />
        </div>
        <div>
          <!-- svelte-ignore a11y_label_has_associated_control -->
          <label class="block text-xs font-medium text-neutral-500 mb-1.5">Policy Type</label>
          <select bind:value={form.policy_type} class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent">
            <option value="financial_threshold">Financial Threshold</option>
            <option value="procurement_threshold">Procurement Threshold</option>
            <option value="contract_review">Contract Review</option>
            <option value="change_order">Change Order</option>
          </select>
        </div>
        <div>
          <!-- svelte-ignore a11y_label_has_associated_control -->
          <label class="block text-xs font-medium text-neutral-500 mb-1.5">Target Model</label>
          <select bind:value={form.content_type} class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent">
            <option value={null}>Select model...</option>
            {#each contentTypes as ct}
              <option value={ct.id}>{MODEL_LABELS[ct.label] || ct.label}</option>
            {/each}
          </select>
        </div>
        <div>
          <!-- svelte-ignore a11y_label_has_associated_control -->
          <label class="block text-xs font-medium text-neutral-500 mb-1.5">Amount Field</label>
          <input
            type="text" bind:value={form.amount_field} placeholder="total_amount"
            class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
          />
        </div>
        <div>
          <!-- svelte-ignore a11y_label_has_associated_control -->
          <label class="block text-xs font-medium text-neutral-500 mb-1.5">Min Amount</label>
          <input
            type="number" bind:value={form.min_amount} placeholder="0.00" step="0.01"
            class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
          />
        </div>
        <div>
          <!-- svelte-ignore a11y_label_has_associated_control -->
          <label class="block text-xs font-medium text-neutral-500 mb-1.5">Max Amount</label>
          <input
            type="number" bind:value={form.max_amount} placeholder="No limit" step="0.01"
            class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
          />
        </div>
        <div>
          <!-- svelte-ignore a11y_label_has_associated_control -->
          <label class="block text-xs font-medium text-neutral-500 mb-1.5">Workflow Template</label>
          <select bind:value={form.template} class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent">
            <option value={null}>Select template...</option>
            {#each templates as t}
              <option value={t.id}>{t.name}</option>
            {/each}
          </select>
        </div>
        <div>
          <!-- svelte-ignore a11y_label_has_associated_control -->
          <label class="block text-xs font-medium text-neutral-500 mb-1.5">Priority (lower = first)</label>
          <input
            type="number" bind:value={form.priority} min="1"
            class="w-full border border-neutral-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-800 focus:border-transparent"
          />
        </div>
      </div>
      <div class="flex justify-end gap-3 mt-5">
        <button onclick={resetForm} class="px-4 py-2 text-sm font-medium text-neutral-600 hover:text-neutral-800 transition-colors">Cancel</button>
        <button
          onclick={savePolicy}
          disabled={creating || !form.name || !form.content_type || !form.template}
          class="px-4 py-2 bg-neutral-800 text-white text-sm font-medium rounded-lg hover:bg-neutral-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          {creating ? "Saving..." : editingId ? "Update Policy" : "Create Policy"}
        </button>
      </div>
    </div>
  {/if}

  <!-- Table -->
  {#if loading}
    <div class="flex items-center justify-center py-20">
      <div class="w-5 h-5 border-2 border-neutral-300 border-t-neutral-800 rounded-full animate-spin"></div>
    </div>
  {:else if policies.length === 0}
    <div class="text-center py-20 bg-white border border-neutral-200 rounded-xl">
      <p class="text-sm text-neutral-500">No approval policies configured yet.</p>
    </div>
  {:else}
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-100 text-left">
            <th class="px-5 py-3 text-xs font-semibold text-neutral-400 uppercase tracking-wider">Policy</th>
            <th class="px-5 py-3 text-xs font-semibold text-neutral-400 uppercase tracking-wider">Type</th>
            <th class="px-5 py-3 text-xs font-semibold text-neutral-400 uppercase tracking-wider">Model</th>
            <th class="px-5 py-3 text-xs font-semibold text-neutral-400 uppercase tracking-wider">Threshold</th>
            <th class="px-5 py-3 text-xs font-semibold text-neutral-400 uppercase tracking-wider">Template</th>
            <th class="px-5 py-3 text-xs font-semibold text-neutral-400 uppercase tracking-wider">Priority</th>
            <th class="px-5 py-3"></th>
          </tr>
        </thead>
        <tbody>
          {#each policies as p}
            <tr class="border-b border-neutral-50 hover:bg-neutral-50/50 transition-colors">
              <td class="px-5 py-3">
                <span class="font-medium text-neutral-800">{p.name}</span>
                {#if !p.is_active}
                  <span class="ml-2 text-[10px] uppercase font-semibold text-neutral-400 bg-neutral-100 px-1.5 py-0.5 rounded">Inactive</span>
                {/if}
              </td>
              <td class="px-5 py-3 text-neutral-600">{POLICY_TYPE_LABELS[p.policy_type]}</td>
              <td class="px-5 py-3 text-neutral-600">{MODEL_LABELS[p.content_type_label] || p.content_type_label}</td>
              <td class="px-5 py-3 text-neutral-600 font-mono text-xs">
                {p.min_amount ? currency.formatCompact(p.min_amount) : "0"}
                —
                {p.max_amount ? currency.formatCompact(p.max_amount) : "∞"}
              </td>
              <td class="px-5 py-3 text-neutral-600">{p.template_name}</td>
              <td class="px-5 py-3 text-neutral-400 text-center">{p.priority}</td>
              <td class="px-5 py-3 text-right">
                <button onclick={() => startEdit(p)} class="text-neutral-400 hover:text-neutral-700 text-xs font-medium mr-3">Edit</button>
                <button onclick={() => deletePolicy(p.id)} class="text-neutral-400 hover:text-red-600 text-xs font-medium">Delete</button>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>

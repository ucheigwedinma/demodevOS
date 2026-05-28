<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    DocumentAutomationSettings,
    DocumentConfidentiality,
    DocumentOwnerRoleOption,
    DocumentRetentionPolicyOption,
    DocumentSignatureProvider,
    DocumentWorkflowPhaseOption,
    PaginatedResponse,
  } from "$lib/types";

  type ProviderOption = {
    key: DocumentSignatureProvider;
    label: string;
  };

  const providerOptions: ProviderOption[] = [
    { key: "docusign", label: "DocuSign" },
    { key: "adobe_acrobat_sign", label: "Adobe Acrobat Sign" },
    { key: "dropbox_sign", label: "Dropbox Sign" },
    { key: "signnow", label: "SignNow" },
  ];

  const confidentialityOptions: Array<{ key: DocumentConfidentiality; label: string }> = [
    { key: "public", label: "Public" },
    { key: "internal", label: "Internal" },
    { key: "confidential", label: "Confidential" },
    { key: "restricted", label: "Restricted" },
  ];

  let loading = $state(true);
  let saving = $state(false);

  let ownerRoles = $state<DocumentOwnerRoleOption[]>([]);
  let workflowPhases = $state<DocumentWorkflowPhaseOption[]>([]);
  let retentionPolicies = $state<DocumentRetentionPolicyOption[]>([]);

  let form = $state<DocumentAutomationSettings | null>(null);

  function parseApiError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      const detail = error.data?.detail;
      if (typeof detail === "string" && detail.trim()) return detail;
      const firstFieldError = Object.values(error.fieldErrors)[0]?.[0];
      if (firstFieldError) return firstFieldError;
    }
    return fallback;
  }

  async function fetchAllPages<T>(endpoint: string): Promise<T[]> {
    const allRows: T[] = [];
    let page = 1;
    while (page <= 40) {
      const response = await api.get<PaginatedResponse<T>>(endpoint, {
        page: String(page),
        page_size: "200",
      });
      allRows.push(...response.results);
      if (!response.next) break;
      page += 1;
    }
    return allRows;
  }

  async function loadData() {
    loading = true;
    try {
      const [settingsResponse, ownerRoleRows, phaseRows, retentionRows] = await Promise.all([
        api.get<DocumentAutomationSettings>("/settings/document-automation/"),
        fetchAllPages<DocumentOwnerRoleOption>("/documents/control/lookups/owner-roles/"),
        fetchAllPages<DocumentWorkflowPhaseOption>("/documents/control/lookups/workflow-phases/"),
        fetchAllPages<DocumentRetentionPolicyOption>("/documents/control/lookups/retention-policies/"),
      ]);

      form = settingsResponse;
      ownerRoles = ownerRoleRows;
      workflowPhases = phaseRows;
      retentionPolicies = retentionRows;
    } catch (error) {
      toast.error("Load failed", parseApiError(error, "Could not load document automation settings."));
    }
    loading = false;
  }

  function ensureProviderSelected(provider: DocumentSignatureProvider, checked: boolean) {
    if (!form) return;

    const current = [...(form.enabled_signature_providers ?? [])];
    const exists = current.includes(provider);

    if (checked && !exists) {
      form.enabled_signature_providers = [...current, provider];
      return;
    }

    if (!checked && exists) {
      const next = current.filter((value) => value !== provider);
      if (next.length === 0) {
        toast.error("Validation", "At least one signature provider must remain enabled.");
        return;
      }
      form.enabled_signature_providers = next;
      if (!next.includes(form.default_signature_provider)) {
        form.default_signature_provider = next[0];
      }
    }
  }

  async function saveSettings() {
    if (!form) return;
    saving = true;
    try {
      const parseNullableId = (value: unknown): number | null => {
        if (value === null || value === undefined || value === "") return null;
        const parsed = Number.parseInt(String(value), 10);
        return Number.isFinite(parsed) ? parsed : null;
      };

      const payload = {
        default_signature_provider: form.default_signature_provider,
        enabled_signature_providers: form.enabled_signature_providers,
        default_generation_owner_role: parseNullableId(form.default_generation_owner_role),
        default_generation_phase: parseNullableId(form.default_generation_phase),
        default_generation_retention_policy: parseNullableId(form.default_generation_retention_policy),
        default_generation_confidentiality_level: form.default_generation_confidentiality_level,
        default_generation_template_code: form.default_generation_template_code,
      };
      form = await api.patch<DocumentAutomationSettings>("/settings/document-automation/", payload);
      toast.success("Saved", "Document automation settings updated.");
    } catch (error) {
      toast.error("Save failed", parseApiError(error, "Could not save document automation settings."));
    }
    saving = false;
  }

  $effect(() => {
    void loadData();
  });
</script>

{#if loading}
  <div class="flex items-center justify-center py-20">
    <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-800"></div>
  </div>
{:else if form}
  <div class="space-y-6">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h2 class="text-xl font-bold text-neutral-800">Document Automation</h2>
        <p class="mt-1 text-sm text-neutral-500">
          Configure document-generation and e-signature defaults centrally in Settings. Operational pages only execute these policies.
        </p>
      </div>
      <button
        type="button"
        onclick={saveSettings}
        disabled={saving}
        class="rounded-lg bg-neutral-800 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {saving ? "Saving..." : "Save Settings"}
      </button>
    </div>

    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h3 class="text-sm font-semibold text-neutral-800">E-Signature Providers</h3>
      <p class="mt-1 text-xs text-neutral-500">Choose providers enabled for all users and set the default provider used during request creation.</p>

      <div class="mt-4 grid gap-3 sm:grid-cols-2">
        {#each providerOptions as provider}
          <label class="flex items-center gap-3 rounded-lg border border-neutral-200 px-3 py-2.5">
            <input
              type="checkbox"
              checked={form.enabled_signature_providers.includes(provider.key)}
              onchange={(event) => {
                ensureProviderSelected(provider.key, (event.currentTarget as HTMLInputElement).checked);
              }}
              class="h-4 w-4 rounded border-neutral-300 text-neutral-800 focus:ring-neutral-800"
            />
            <span class="text-sm text-neutral-700">{provider.label}</span>
          </label>
        {/each}
      </div>

      <div class="mt-4 max-w-sm">
        <!-- svelte-ignore a11y_label_has_associated_control -->
        <label class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Default Provider</label>
        <select
          bind:value={form.default_signature_provider}
          class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm"
        >
          {#each providerOptions.filter((item) => (form?.enabled_signature_providers ?? []).includes(item.key)) as item}
            <option value={item.key}>{item.label}</option>
          {/each}
        </select>
      </div>
    </section>

    <section class="rounded-xl border border-neutral-200 bg-white p-6">
      <h3 class="text-sm font-semibold text-neutral-800">Document Generator Defaults</h3>
      <p class="mt-1 text-xs text-neutral-500">These values are applied automatically when users generate contracts, invoices, and reports.</p>

      <div class="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <div>
          <!-- svelte-ignore a11y_label_has_associated_control -->
          <label class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Owner Role</label>
          <select bind:value={form.default_generation_owner_role} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Select owner role</option>
            {#each ownerRoles as option}
              <option value={String(option.id)}>{option.name}</option>
            {/each}
          </select>
        </div>

        <div>
          <!-- svelte-ignore a11y_label_has_associated_control -->
          <label class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Workflow Phase</label>
          <select bind:value={form.default_generation_phase} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Select phase</option>
            {#each workflowPhases as option}
              <option value={String(option.id)}>{option.name}</option>
            {/each}
          </select>
        </div>

        <div>
          <!-- svelte-ignore a11y_label_has_associated_control -->
          <label class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Retention Policy</label>
          <select bind:value={form.default_generation_retention_policy} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            <option value="">Select retention policy</option>
            {#each retentionPolicies as option}
              <option value={String(option.id)}>{option.name}</option>
            {/each}
          </select>
        </div>

        <div>
          <!-- svelte-ignore a11y_label_has_associated_control -->
          <label class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Confidentiality</label>
          <select bind:value={form.default_generation_confidentiality_level} class="w-full rounded-lg border border-neutral-200 bg-white px-3 py-2.5 text-sm">
            {#each confidentialityOptions as option}
              <option value={option.key}>{option.label}</option>
            {/each}
          </select>
        </div>

        <div class="md:col-span-2 xl:col-span-2">
          <!-- svelte-ignore a11y_label_has_associated_control -->
          <label class="mb-1 block text-xs font-semibold uppercase tracking-wide text-neutral-500">Default Template Code</label>
          <input
            type="text"
            bind:value={form.default_generation_template_code}
            placeholder="Optional default template code"
            class="w-full rounded-lg border border-neutral-200 px-3 py-2.5 text-sm"
          />
        </div>
      </div>
    </section>
  </div>
{/if}

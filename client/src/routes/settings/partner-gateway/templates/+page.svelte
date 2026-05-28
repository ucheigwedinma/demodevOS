<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    OnboardingTemplate,
    OnboardingTemplateDocumentRequirement,
    OnboardingTemplateStage,
    PaginatedResponse,
    PartnerIntakeSourceChannel,
  } from "$lib/types";

  let loading = $state(true);
  let savingTemplate = $state(false);
  let savingStage = $state(false);
  let savingRequirement = $state(false);

  let templates = $state<OnboardingTemplate[]>([]);
  let stages = $state<OnboardingTemplateStage[]>([]);
  let requirements = $state<OnboardingTemplateDocumentRequirement[]>([]);
  let selectedTemplateId = $state<number | null>(null);

  let templateForm = $state({
    partner_type: "client",
    code: "",
    name: "",
    description: "",
    is_default: false,
    is_active: true,
    version: "1",
  });

  let stageForm = $state({
    template: "",
    sequence: "1",
    code: "",
    name: "",
    description: "",
    is_required: true,
    approval_required: false,
    approval_role_label: "",
    sla_hours: "",
    auto_complete: false,
  });

  let requirementForm = $state({
    template: "",
    sequence: "1",
    code: "",
    name: "",
    description: "",
    is_required: true,
    applies_to_stage: "",
    accepted_sources: ["secure_upload_link"] as PartnerIntakeSourceChannel[],
    allowed_extensions: "pdf,jpg,jpeg,png",
  });

  function parseApiError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      if (typeof error.data?.detail === "string") return error.data.detail;
      const firstFieldError = Object.values(error.fieldErrors)[0]?.[0];
      if (firstFieldError) return firstFieldError;
    }
    return fallback;
  }

  const sourceOptions: Array<{ value: PartnerIntakeSourceChannel; label: string }> = [
    { value: "physical_scan", label: "Physical Scan" },
    { value: "email", label: "Email" },
    { value: "secure_upload_link", label: "Secure Upload Link" },
    { value: "tender_portal", label: "Tender Portal" },
    { value: "data_room", label: "Data Room" },
    { value: "internal_generated", label: "Internal Generated" },
    { value: "other", label: "Other" },
  ];

  async function fetchAllPages<T>(endpoint: string, params: Record<string, string> = {}): Promise<T[]> {
    const rows: T[] = [];
    let page = 1;
    while (page <= 30) {
      const payload = await api.get<PaginatedResponse<T> | T[]>(endpoint, {
        ...params,
        page: String(page),
      });
      if (Array.isArray(payload)) {
        rows.push(...payload);
        break;
      }
      rows.push(...(payload.results ?? []));
      if (!payload.next || payload.results.length === 0) break;
      page += 1;
    }
    return rows;
  }

  async function loadTemplates() {
    loading = true;
    try {
      templates = await fetchAllPages<OnboardingTemplate>("/partners/templates/", {
        ordering: "partner_type,name",
        page_size: "200",
      });

      if (!selectedTemplateId && templates.length > 0) {
        selectedTemplateId = templates[0].id;
        stageForm.template = String(templates[0].id);
        requirementForm.template = String(templates[0].id);
      }

      if (selectedTemplateId) {
        const [stageRows, requirementRows] = await Promise.all([
          fetchAllPages<OnboardingTemplateStage>(`/partners/templates/${selectedTemplateId}/stages/`, {
            ordering: "sequence",
            page_size: "200",
          }),
          fetchAllPages<OnboardingTemplateDocumentRequirement>(
            `/partners/templates/${selectedTemplateId}/document-requirements/`,
            {
              ordering: "sequence",
              page_size: "200",
            },
          ),
        ]);
        stages = stageRows;
        requirements = requirementRows;
      } else {
        stages = [];
        requirements = [];
      }
    } catch (error) {
      toast.error("Load failed", parseApiError(error, "Could not load onboarding templates."));
    } finally {
      loading = false;
    }
  }

  async function createTemplate(event: Event) {
    event.preventDefault();
    savingTemplate = true;
    try {
      const created = await api.post<OnboardingTemplate>("/partners/templates/", {
        partner_type: templateForm.partner_type,
        code: templateForm.code.trim(),
        name: templateForm.name.trim(),
        description: templateForm.description.trim(),
        version: Number.parseInt(templateForm.version, 10) || 1,
        is_default: templateForm.is_default,
        is_active: templateForm.is_active,
      });
      toast.success("Template created", "Onboarding template created successfully.");
      templateForm = {
        partner_type: "client",
        code: "",
        name: "",
        description: "",
        is_default: false,
        is_active: true,
        version: "1",
      };
      selectedTemplateId = created.id;
      stageForm.template = String(created.id);
      requirementForm.template = String(created.id);
      await loadTemplates();
    } catch (error) {
      toast.error("Create failed", parseApiError(error, "Could not create onboarding template."));
    } finally {
      savingTemplate = false;
    }
  }

  async function createStage(event: Event) {
    event.preventDefault();
    const templateId = Number.parseInt(stageForm.template, 10);
    if (Number.isNaN(templateId)) {
      toast.error("Template required", "Select a template before adding a stage.");
      return;
    }

    savingStage = true;
    try {
      await api.post(`/partners/templates/${templateId}/stages/`, {
        sequence: Number.parseInt(stageForm.sequence, 10) || 1,
        code: stageForm.code.trim(),
        name: stageForm.name.trim(),
        description: stageForm.description.trim(),
        is_required: stageForm.is_required,
        approval_required: stageForm.approval_required,
        approval_role_label: stageForm.approval_role_label.trim(),
        sla_hours: stageForm.sla_hours.trim() ? Number.parseInt(stageForm.sla_hours, 10) : null,
        auto_complete: stageForm.auto_complete,
      });
      toast.success("Stage added", "Template stage saved.");
      stageForm = {
        template: stageForm.template,
        sequence: String(stages.length + 1),
        code: "",
        name: "",
        description: "",
        is_required: true,
        approval_required: false,
        approval_role_label: "",
        sla_hours: "",
        auto_complete: false,
      };
      selectedTemplateId = templateId;
      await loadTemplates();
    } catch (error) {
      toast.error("Save failed", parseApiError(error, "Could not save template stage."));
    } finally {
      savingStage = false;
    }
  }

  function toggleAcceptedSource(source: PartnerIntakeSourceChannel) {
    if (requirementForm.accepted_sources.includes(source)) {
      requirementForm.accepted_sources = requirementForm.accepted_sources.filter((row) => row !== source);
      return;
    }
    requirementForm.accepted_sources = [...requirementForm.accepted_sources, source];
  }

  async function createRequirement(event: Event) {
    event.preventDefault();
    const templateId = Number.parseInt(requirementForm.template, 10);
    if (Number.isNaN(templateId)) {
      toast.error("Template required", "Select a template before adding a requirement.");
      return;
    }

    savingRequirement = true;
    try {
      await api.post(`/partners/templates/${templateId}/document-requirements/`, {
        sequence: Number.parseInt(requirementForm.sequence, 10) || 1,
        code: requirementForm.code.trim(),
        name: requirementForm.name.trim(),
        description: requirementForm.description.trim(),
        is_required: requirementForm.is_required,
        applies_to_stage: requirementForm.applies_to_stage
          ? Number.parseInt(requirementForm.applies_to_stage, 10)
          : null,
        accepted_sources: requirementForm.accepted_sources,
        allowed_extensions: requirementForm.allowed_extensions
          .split(",")
          .map((row) => row.trim().toLowerCase())
          .filter(Boolean),
      });
      toast.success("Requirement added", "Template intake document requirement saved.");
      requirementForm = {
        template: requirementForm.template,
        sequence: String(requirements.length + 1),
        code: "",
        name: "",
        description: "",
        is_required: true,
        applies_to_stage: "",
        accepted_sources: ["secure_upload_link"],
        allowed_extensions: "pdf,jpg,jpeg,png",
      };
      selectedTemplateId = templateId;
      await loadTemplateStages(templateId);
    } catch (error) {
      toast.error("Save failed", parseApiError(error, "Could not save document requirement."));
    } finally {
      savingRequirement = false;
    }
  }

  async function loadTemplateStages(templateId: number) {
    selectedTemplateId = templateId;
    stageForm.template = String(templateId);
    requirementForm.template = String(templateId);
    try {
      const [stageRows, requirementRows] = await Promise.all([
        fetchAllPages<OnboardingTemplateStage>(`/partners/templates/${templateId}/stages/`, {
          ordering: "sequence",
          page_size: "200",
        }),
        fetchAllPages<OnboardingTemplateDocumentRequirement>(
          `/partners/templates/${templateId}/document-requirements/`,
          {
            ordering: "sequence",
            page_size: "200",
          },
        ),
      ]);
      stages = stageRows;
      requirements = requirementRows;
    } catch (error) {
      toast.error("Load failed", parseApiError(error, "Could not load template stages and requirements."));
    }
  }

  $effect(() => {
    loadTemplates();
  });
</script>

<div class="space-y-6">
  <div>
    <h2 class="text-xl font-semibold text-neutral-800">Onboarding Templates</h2>
    <p class="mt-1 text-sm text-neutral-500">Define role-specific flow blueprints for client, contractor, and investor onboarding.</p>
  </div>

  <form onsubmit={createTemplate} class="rounded-xl border border-neutral-200 bg-white p-5">
    <h3 class="text-sm font-semibold text-neutral-800">Create Template</h3>
    <div class="mt-4 grid gap-3 md:grid-cols-3">
      <select bind:value={templateForm.partner_type} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="client">Client</option>
        <option value="contractor">Contractor</option>
        <option value="investor">Investor</option>
      </select>
      <input type="text" bind:value={templateForm.code} placeholder="Template code" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
      <input type="text" bind:value={templateForm.name} placeholder="Template name" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
      <input type="number" min="1" bind:value={templateForm.version} placeholder="Version" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
      <label class="inline-flex items-center gap-2 rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700">
        <input type="checkbox" bind:checked={templateForm.is_default} class="rounded border-neutral-300" />
        Default
      </label>
      <label class="inline-flex items-center gap-2 rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700">
        <input type="checkbox" bind:checked={templateForm.is_active} class="rounded border-neutral-300" />
        Active
      </label>
      <textarea bind:value={templateForm.description} rows="2" placeholder="Description" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm md:col-span-3"></textarea>
    </div>
    <div class="mt-4 flex justify-end">
      <button type="submit" disabled={savingTemplate || !templateForm.code.trim() || !templateForm.name.trim()} class="rounded-lg bg-neutral-800 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50">
        {savingTemplate ? "Saving..." : "Create Template"}
      </button>
    </div>
  </form>

  <form onsubmit={createStage} class="rounded-xl border border-neutral-200 bg-white p-5">
    <h3 class="text-sm font-semibold text-neutral-800">Add Stage</h3>
    <div class="mt-4 grid gap-3 md:grid-cols-3">
      <select bind:value={stageForm.template} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="">Select template</option>
        {#each templates as template}
          <option value={String(template.id)}>{template.name} ({template.partner_type})</option>
        {/each}
      </select>
      <input type="number" min="1" bind:value={stageForm.sequence} placeholder="Sequence" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
      <input type="text" bind:value={stageForm.code} placeholder="Stage code" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
      <input type="text" bind:value={stageForm.name} placeholder="Stage name" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm md:col-span-2" />
      <input type="number" min="1" bind:value={stageForm.sla_hours} placeholder="SLA hours" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
      <textarea bind:value={stageForm.description} rows="2" placeholder="Description" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm md:col-span-3"></textarea>
      <label class="inline-flex items-center gap-2 rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700">
        <input type="checkbox" bind:checked={stageForm.is_required} class="rounded border-neutral-300" />
        Required
      </label>
      <label class="inline-flex items-center gap-2 rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700">
        <input type="checkbox" bind:checked={stageForm.approval_required} class="rounded border-neutral-300" />
        Approval Required
      </label>
      <label class="inline-flex items-center gap-2 rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700">
        <input type="checkbox" bind:checked={stageForm.auto_complete} class="rounded border-neutral-300" />
        Auto Complete
      </label>
      <input type="text" bind:value={stageForm.approval_role_label} placeholder="Approval role label" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm md:col-span-3" />
    </div>
    <div class="mt-4 flex justify-end">
      <button type="submit" disabled={savingStage || !stageForm.code.trim() || !stageForm.name.trim()} class="rounded-lg bg-neutral-800 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50">
        {savingStage ? "Saving..." : "Add Stage"}
      </button>
    </div>
  </form>

  <section class="rounded-xl border border-neutral-200 bg-white">
    {#if loading}
      <div class="flex items-center justify-center py-12">
        <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-800"></div>
      </div>
    {:else}
      <div class="overflow-x-auto">
        <table class="min-w-[1000px] w-full text-sm">
          <thead class="border-b border-neutral-100 bg-neutral-50">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Template</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Type</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Code</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Stages</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Flags</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each templates as template (template.id)}
              <tr class="hover:bg-neutral-50">
                <td class="px-4 py-3 text-neutral-800 font-medium">{template.name}</td>
                <td class="px-4 py-3 text-neutral-600 capitalize">{template.partner_type}</td>
                <td class="px-4 py-3 text-neutral-500 font-mono text-xs">{template.code}</td>
                <td class="px-4 py-3 text-right tabular-nums text-neutral-700">{template.stage_count}</td>
                <td class="px-4 py-3 text-neutral-600">{template.is_default ? "Default" : ""} {template.is_active ? "Active" : "Inactive"}</td>
                <td class="px-4 py-3 text-right">
                  <button onclick={() => loadTemplateStages(template.id)} class="rounded-md border border-neutral-200 px-2.5 py-1 text-xs font-medium text-neutral-700 hover:bg-neutral-100">View Stages</button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </section>

  <section class="rounded-xl border border-neutral-200 bg-white p-5">
    <h3 class="text-sm font-semibold text-neutral-800">Template Stages {selectedTemplateId ? `(Template #${selectedTemplateId})` : ""}</h3>
    {#if stages.length === 0}
      <p class="mt-3 text-sm text-neutral-500">No stages loaded.</p>
    {:else}
      <div class="mt-3 overflow-x-auto">
        <table class="min-w-[900px] w-full text-sm">
          <thead class="border-b border-neutral-100 bg-neutral-50">
            <tr>
              <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">#</th>
              <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Stage</th>
              <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Code</th>
              <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Required</th>
              <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Approval</th>
              <th class="px-3 py-2 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">SLA</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each stages as stage (stage.id)}
              <tr>
                <td class="px-3 py-2 text-neutral-500">{stage.sequence}</td>
                <td class="px-3 py-2 text-neutral-800">{stage.name}</td>
                <td class="px-3 py-2 text-neutral-500 font-mono text-xs">{stage.code}</td>
                <td class="px-3 py-2 text-neutral-600">{stage.is_required ? "Yes" : "No"}</td>
                <td class="px-3 py-2 text-neutral-600">{stage.approval_required ? stage.approval_role_label || "Yes" : "No"}</td>
                <td class="px-3 py-2 text-right tabular-nums text-neutral-600">{stage.sla_hours ?? "--"}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </section>

  <form onsubmit={createRequirement} class="rounded-xl border border-neutral-200 bg-white p-5">
    <h3 class="text-sm font-semibold text-neutral-800">Add Intake Document Requirement</h3>
    <div class="mt-4 grid gap-3 md:grid-cols-3">
      <select
        bind:value={requirementForm.template}
        onchange={(event) => {
          const value = Number.parseInt((event.currentTarget as HTMLSelectElement).value, 10);
          if (!Number.isNaN(value)) loadTemplateStages(value);
        }}
        class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm"
      >
        <option value="">Select template</option>
        {#each templates as template}
          <option value={String(template.id)}>{template.name} ({template.partner_type})</option>
        {/each}
      </select>
      <input type="number" min="1" bind:value={requirementForm.sequence} placeholder="Sequence" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
      <input type="text" bind:value={requirementForm.code} placeholder="Requirement code" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
      <input type="text" bind:value={requirementForm.name} placeholder="Requirement name" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm md:col-span-2" />
      <select bind:value={requirementForm.applies_to_stage} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="">No stage mapping</option>
        {#each stages as stage (stage.id)}
          <option value={String(stage.id)}>{stage.sequence}. {stage.name}</option>
        {/each}
      </select>
      <textarea bind:value={requirementForm.description} rows="2" placeholder="Description" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm md:col-span-3"></textarea>
      <label class="inline-flex items-center gap-2 rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700">
        <input type="checkbox" bind:checked={requirementForm.is_required} class="rounded border-neutral-300" />
        Required for intake gate
      </label>
      <input type="text" bind:value={requirementForm.allowed_extensions} placeholder="Allowed extensions (comma-separated)" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm md:col-span-2" />

      <div class="md:col-span-3">
        <p class="text-xs font-semibold uppercase tracking-wide text-neutral-500">Accepted Sources</p>
        <div class="mt-2 flex flex-wrap gap-2">
          {#each sourceOptions as source}
            <button
              type="button"
              onclick={() => toggleAcceptedSource(source.value)}
              class={`rounded-full border px-3 py-1 text-xs font-medium ${
                requirementForm.accepted_sources.includes(source.value)
                  ? 'border-neutral-800 bg-neutral-800 text-white'
                  : 'border-neutral-200 text-neutral-700 hover:bg-neutral-100'
              }`}
            >
              {source.label}
            </button>
          {/each}
        </div>
      </div>
    </div>
    <div class="mt-4 flex justify-end">
      <button
        type="submit"
        disabled={savingRequirement || !requirementForm.code.trim() || !requirementForm.name.trim()}
        class="rounded-lg bg-neutral-800 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
      >
        {savingRequirement ? "Saving..." : "Add Requirement"}
      </button>
    </div>
  </form>

  <section class="rounded-xl border border-neutral-200 bg-white p-5">
    <h3 class="text-sm font-semibold text-neutral-800">Template Intake Requirements {selectedTemplateId ? `(Template #${selectedTemplateId})` : ""}</h3>
    {#if requirements.length === 0}
      <p class="mt-3 text-sm text-neutral-500">No intake requirements configured.</p>
    {:else}
      <div class="mt-3 overflow-x-auto">
        <table class="min-w-[980px] w-full text-sm">
          <thead class="border-b border-neutral-100 bg-neutral-50">
            <tr>
              <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">#</th>
              <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Requirement</th>
              <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Code</th>
              <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Stage</th>
              <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Sources</th>
              <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Required</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each requirements as requirement (requirement.id)}
              <tr>
                <td class="px-3 py-2 text-neutral-500">{requirement.sequence}</td>
                <td class="px-3 py-2 text-neutral-800">{requirement.name}</td>
                <td class="px-3 py-2 text-neutral-500 font-mono text-xs">{requirement.code}</td>
                <td class="px-3 py-2 text-neutral-600">{requirement.stage_name || "--"}</td>
                <td class="px-3 py-2 text-neutral-600">{requirement.accepted_sources.join(", ") || "--"}</td>
                <td class="px-3 py-2 text-neutral-600">{requirement.is_required ? "Yes" : "No"}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </section>
</div>

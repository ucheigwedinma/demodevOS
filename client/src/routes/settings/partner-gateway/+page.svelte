<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    OnboardingTemplate,
    PaginatedResponse,
    PartnerOnboardingCaseListItem,
    ProjectListItem,
    SPVEntity,
  } from "$lib/types";

  let loading = $state(true);
  let saving = $state(false);
  let cases = $state<PartnerOnboardingCaseListItem[]>([]);
  let templates = $state<OnboardingTemplate[]>([]);
  let projects = $state<ProjectListItem[]>([]);
  let spvs = $state<SPVEntity[]>([]);

  let showCreate = $state(false);
  let partnerFilter = $state("");
  let statusFilter = $state("");
  let search = $state("");

  let form = $state({
    partner_type: "client",
    title: "",
    template: "",
    contact_name: "",
    contact_email: "",
    contact_phone: "",
    project: "",
    spv_entity: "",
    contract_reference: "",
    investment_vehicle_reference: "",
    notes: "",
  });

  function parseApiError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      if (typeof error.data?.detail === "string") return error.data.detail;
      const firstFieldError = Object.values(error.fieldErrors)[0]?.[0];
      if (firstFieldError) return firstFieldError;
    }
    return fallback;
  }

  async function fetchAllPages<T>(
    endpoint: string,
    params: Record<string, string> = {},
    maxPages = 30,
  ): Promise<T[]> {
    const rows: T[] = [];
    let page = 1;

    while (page <= maxPages) {
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

  async function loadData() {
    loading = true;
    try {
      const [caseRows, templateRows, projectRows, spvRows] = await Promise.all([
        fetchAllPages<PartnerOnboardingCaseListItem>("/partners/cases/", { ordering: "-created_at", page_size: "200" }),
        fetchAllPages<OnboardingTemplate>("/partners/templates/", { ordering: "partner_type,name", page_size: "200" }),
        fetchAllPages<ProjectListItem>("/projects/", { ordering: "name", page_size: "200" }),
        fetchAllPages<SPVEntity>("/finance/spv-entities/", { ordering: "name", page_size: "200" }),
      ]);
      cases = caseRows;
      templates = templateRows;
      projects = projectRows;
      spvs = spvRows;
    } catch (error) {
      toast.error("Load failed", parseApiError(error, "Could not load partner onboarding data."));
    } finally {
      loading = false;
    }
  }

  function resetForm() {
    form = {
      partner_type: "client",
      title: "",
      template: "",
      contact_name: "",
      contact_email: "",
      contact_phone: "",
      project: "",
      spv_entity: "",
      contract_reference: "",
      investment_vehicle_reference: "",
      notes: "",
    };
  }

  function parseOptionalInt(value: string): number | null {
    const n = Number.parseInt(value, 10);
    return Number.isNaN(n) ? null : n;
  }

  async function createCase(event: Event) {
    event.preventDefault();
    saving = true;
    try {
      await api.post("/partners/cases/", {
        partner_type: form.partner_type,
        title: form.title.trim(),
        template: parseOptionalInt(form.template),
        contact_name: form.contact_name.trim(),
        contact_email: form.contact_email.trim(),
        contact_phone: form.contact_phone.trim(),
        project: parseOptionalInt(form.project),
        spv_entity: parseOptionalInt(form.spv_entity),
        contract_reference: form.contract_reference.trim(),
        investment_vehicle_reference: form.investment_vehicle_reference.trim(),
        notes: form.notes.trim(),
      });
      toast.success("Case created", "Partner onboarding case created successfully.");
      showCreate = false;
      resetForm();
      await loadData();
    } catch (error) {
      toast.error("Create failed", parseApiError(error, "Could not create onboarding case."));
    } finally {
      saving = false;
    }
  }

  async function submitReview(caseId: number) {
    try {
      await api.post(`/partners/cases/${caseId}/submit-review/`, {});
      toast.success("Submitted", "Case submitted for review.");
      await loadData();
    } catch (error) {
      toast.error("Submit failed", parseApiError(error, "Could not submit case for review."));
    }
  }

  async function grantAccess(caseId: number) {
    try {
      await api.post(`/partners/cases/${caseId}/grant-portal-access/`, {});
      toast.success("Access granted", "Partner portal access granted.");
      await loadData();
    } catch (error) {
      toast.error("Grant failed", parseApiError(error, "Could not grant portal access."));
    }
  }

  const filteredCases = $derived.by(() => {
    return cases.filter((row) => {
      if (partnerFilter && row.partner_type !== partnerFilter) return false;
      if (statusFilter && row.status !== statusFilter) return false;
      if (!search.trim()) return true;
      const needle = search.trim().toLowerCase();
      const haystack = `${row.title} ${row.contact_name} ${row.contact_email} ${row.template_name ?? ""}`.toLowerCase();
      return haystack.includes(needle);
    });
  });

  const templatesForPartner = $derived.by(() =>
    templates.filter((template) => template.partner_type === form.partner_type),
  );

  $effect(() => {
    loadData();
  });
</script>

<div class="space-y-6">
  <div class="flex items-center justify-between">
    <div>
      <h2 class="text-xl font-semibold text-neutral-800">Partner Onboarding Cases</h2>
      <p class="mt-1 text-sm text-neutral-500">Track buyer, contractor, and investor onboarding from source gate to portal access.</p>
    </div>
    <button
      onclick={() => {
        resetForm();
        showCreate = !showCreate;
      }}
      class="rounded-lg bg-neutral-800 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800"
    >
      {showCreate ? "Close Form" : "+ New Case"}
    </button>
  </div>

  {#if showCreate}
    <form onsubmit={createCase} class="rounded-xl border border-neutral-200 bg-white p-5">
      <h3 class="text-sm font-semibold text-neutral-800">Create Onboarding Case</h3>
      <div class="mt-4 grid gap-3 md:grid-cols-3">
        <select bind:value={form.partner_type} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          <option value="client">Client</option>
          <option value="contractor">Contractor</option>
          <option value="investor">Investor</option>
        </select>
        <input type="text" bind:value={form.title} placeholder="Case title" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm md:col-span-2" />

        <select bind:value={form.template} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          <option value="">Default template</option>
          {#each templatesForPartner as template}
            <option value={String(template.id)}>{template.name}</option>
          {/each}
        </select>
        <input type="text" bind:value={form.contact_name} placeholder="Contact name" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
        <input type="email" bind:value={form.contact_email} placeholder="Contact email" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm" />

        <input type="text" bind:value={form.contact_phone} placeholder="Contact phone" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
        <select bind:value={form.project} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          <option value="">No project scope</option>
          {#each projects as project}
            <option value={String(project.id)}>{project.name}</option>
          {/each}
        </select>
        <select bind:value={form.spv_entity} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          <option value="">No SPV scope</option>
          {#each spvs as spv}
            <option value={String(spv.id)}>{spv.name}</option>
          {/each}
        </select>

        <input type="text" bind:value={form.contract_reference} placeholder="Contract reference" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
        <input type="text" bind:value={form.investment_vehicle_reference} placeholder="Investment vehicle reference" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm" />
        <textarea bind:value={form.notes} rows="2" placeholder="Notes" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm md:col-span-3"></textarea>
      </div>
      <div class="mt-4 flex justify-end">
        <button
          type="submit"
          disabled={saving || !form.title.trim()}
          class="rounded-lg bg-neutral-800 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50"
        >
          {saving ? "Saving..." : "Create Case"}
        </button>
      </div>
    </form>
  {/if}

  <section class="rounded-xl border border-neutral-200 bg-white">
    <div class="border-b border-neutral-200 p-4">
      <div class="grid gap-3 md:grid-cols-4">
        <input type="text" bind:value={search} placeholder="Search cases..." class="rounded-lg border border-neutral-200 px-3 py-2 text-sm md:col-span-2" />
        <select bind:value={partnerFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          <option value="">All Partner Types</option>
          <option value="client">Client</option>
          <option value="contractor">Contractor</option>
          <option value="investor">Investor</option>
        </select>
        <select bind:value={statusFilter} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="in_progress">In Progress</option>
          <option value="under_review">Under Review</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
          <option value="active">Active</option>
          <option value="suspended">Suspended</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>
    </div>

    {#if loading}
      <div class="flex items-center justify-center py-12">
        <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-800"></div>
      </div>
    {:else if filteredCases.length === 0}
      <div class="px-6 py-10 text-center text-sm text-neutral-500">No onboarding cases found.</div>
    {:else}
      <div class="overflow-x-auto">
        <table class="min-w-[1220px] w-full text-sm">
          <thead class="border-b border-neutral-100 bg-neutral-50">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Case</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Partner</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Status</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Current Stage</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Progress</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Intake Docs</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">ERP Profile</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Portal Access</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each filteredCases as row (row.id)}
              <tr class="hover:bg-neutral-50">
                <td class="px-4 py-3 text-neutral-800">
                  <p class="font-medium">{row.title}</p>
                  <p class="text-xs text-neutral-500">{row.contact_name || row.contact_email || "--"}</p>
                </td>
                <td class="px-4 py-3 text-neutral-600 capitalize">{row.partner_type}</td>
                <td class="px-4 py-3 text-neutral-600">{row.status_display}</td>
                <td class="px-4 py-3 text-neutral-600">{row.current_stage_name || "--"}</td>
                <td class="px-4 py-3 text-right tabular-nums text-neutral-700">{row.required_stage_completed}/{row.required_stage_total} ({row.completion_percent}%)</td>
                <td class="px-4 py-3 text-right tabular-nums text-neutral-700">
                  {row.approved_document_total}/{row.required_document_total}
                  <p class="text-[11px] text-neutral-500">{row.missing_required_document_count} missing</p>
                </td>
                <td class="px-4 py-3 text-right text-neutral-700">{row.has_erp_profile ? "Yes" : "No"}</td>
                <td class="px-4 py-3 text-right text-neutral-700">{row.portal_access_granted ? "Granted" : "Pending"}</td>
                <td class="px-4 py-3">
                  <div class="flex justify-end gap-2">
                    <button onclick={() => submitReview(row.id)} class="rounded-md border border-neutral-200 px-2.5 py-1 text-xs font-medium text-neutral-700 hover:bg-neutral-100">Submit</button>
                    <button onclick={() => grantAccess(row.id)} class="rounded-md border border-emerald-200 px-2.5 py-1 text-xs font-medium text-emerald-700 hover:bg-emerald-50">Grant Access</button>
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </section>
</div>

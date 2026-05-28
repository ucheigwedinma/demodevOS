<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    PaginatedResponse,
    PartnerEntitlement,
    PartnerOnboardingCaseListItem,
    PartnerPortalRole,
    ProjectListItem,
    SPVEntity,
  } from "$lib/types";

  let loading = $state(true);
  let saving = $state(false);
  let entitlements = $state<PartnerEntitlement[]>([]);
  let cases = $state<PartnerOnboardingCaseListItem[]>([]);
  let projects = $state<ProjectListItem[]>([]);
  let spvs = $state<SPVEntity[]>([]);

  let form = $state({
    case: "",
    portal_role: "",
    project: "",
    spv_entity: "",
    contract_reference: "",
    investment_vehicle_reference: "",
  });

  function parseApiError(error: unknown, fallback: string): string {
    if (error instanceof ApiError) {
      if (typeof error.data?.detail === "string") return error.data.detail;
      const firstFieldError = Object.values(error.fieldErrors)[0]?.[0];
      if (firstFieldError) return firstFieldError;
    }
    return fallback;
  }

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

  async function loadData() {
    loading = true;
    try {
      const [entRows, caseRows, projectRows, spvRows] = await Promise.all([
        fetchAllPages<PartnerEntitlement>("/partners/entitlements/", { ordering: "-created_at", page_size: "200" }),
        fetchAllPages<PartnerOnboardingCaseListItem>("/partners/cases/", { ordering: "-created_at", page_size: "200" }),
        fetchAllPages<ProjectListItem>("/projects/", { ordering: "name", page_size: "200" }),
        fetchAllPages<SPVEntity>("/finance/spv-entities/", { ordering: "name", page_size: "200" }),
      ]);
      entitlements = entRows;
      cases = caseRows;
      projects = projectRows;
      spvs = spvRows;
    } catch (error) {
      toast.error("Load failed", parseApiError(error, "Could not load entitlement data."));
    } finally {
      loading = false;
    }
  }

  function parseOptionalInt(value: string): number | null {
    const parsed = Number.parseInt(value, 10);
    return Number.isNaN(parsed) ? null : parsed;
  }

  async function provision(event: Event) {
    event.preventDefault();
    const caseId = parseOptionalInt(form.case);
    if (!caseId) {
      toast.error("Case required", "Select an onboarding case first.");
      return;
    }
    saving = true;
    try {
      await api.post(`/partners/cases/${caseId}/provision-entitlement/`, {
        portal_role: form.portal_role || undefined,
        project: parseOptionalInt(form.project),
        spv_entity: parseOptionalInt(form.spv_entity),
        contract_reference: form.contract_reference.trim(),
        investment_vehicle_reference: form.investment_vehicle_reference.trim(),
      });
      toast.success("Provisioned", "Entitlement created from matrix rules.");
      form = {
        case: "",
        portal_role: "",
        project: "",
        spv_entity: "",
        contract_reference: "",
        investment_vehicle_reference: "",
      };
      await loadData();
    } catch (error) {
      toast.error("Provision failed", parseApiError(error, "Could not provision entitlement."));
    } finally {
      saving = false;
    }
  }

  async function toggleActive(row: PartnerEntitlement) {
    try {
      await api.patch(`/partners/entitlements/${row.id}/`, { is_active: !row.is_active });
      toast.success("Updated", `Entitlement ${row.is_active ? "deactivated" : "activated"}.`);
      await loadData();
    } catch (error) {
      toast.error("Update failed", parseApiError(error, "Could not update entitlement."));
    }
  }

  $effect(() => {
    loadData();
  });
</script>

<div class="space-y-6">
  <div>
    <h2 class="text-xl font-semibold text-neutral-800">Entitlement Matrix</h2>
    <p class="mt-1 text-sm text-neutral-500">Provision and manage scoped partner visibility by project, SPV, contract, and investment vehicle.</p>
  </div>

  <form onsubmit={provision} class="rounded-xl border border-neutral-200 bg-white p-5">
    <h3 class="text-sm font-semibold text-neutral-800">Provision Entitlement</h3>
    <div class="mt-4 grid gap-3 md:grid-cols-3">
      <select bind:value={form.case} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm md:col-span-2">
        <option value="">Select case</option>
        {#each cases as row}
          <option value={String(row.id)}>{row.title} ({row.partner_type})</option>
        {/each}
      </select>
      <select bind:value={form.portal_role} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="">Default matrix role</option>
        <option value="client">Client</option>
        <option value="contractor">Contractor</option>
        <option value="investor">Investor</option>
        <option value="lead_investor">Lead Investor</option>
      </select>

      <select bind:value={form.project} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="">Case project scope</option>
        {#each projects as project}
          <option value={String(project.id)}>{project.name}</option>
        {/each}
      </select>
      <select bind:value={form.spv_entity} class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm">
        <option value="">Case SPV scope</option>
        {#each spvs as spv}
          <option value={String(spv.id)}>{spv.name}</option>
        {/each}
      </select>
      <input type="text" bind:value={form.contract_reference} placeholder="Contract reference override" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm" />

      <input type="text" bind:value={form.investment_vehicle_reference} placeholder="Investment vehicle override" class="rounded-lg border border-neutral-200 px-3 py-2 text-sm md:col-span-3" />
    </div>
    <div class="mt-4 flex justify-end">
      <button type="submit" disabled={saving} class="rounded-lg bg-neutral-800 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50">
        {saving ? "Provisioning..." : "Provision Entitlement"}
      </button>
    </div>
  </form>

  <section class="rounded-xl border border-neutral-200 bg-white">
    {#if loading}
      <div class="flex items-center justify-center py-12">
        <div class="h-6 w-6 animate-spin rounded-full border-2 border-neutral-300 border-t-neutral-800"></div>
      </div>
    {:else if entitlements.length === 0}
      <div class="px-6 py-10 text-center text-sm text-neutral-500">No entitlements provisioned yet.</div>
    {:else}
      <div class="overflow-x-auto">
        <table class="min-w-[1200px] w-full text-sm">
          <thead class="border-b border-neutral-100 bg-neutral-50">
            <tr>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Case</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Role</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Scopes</th>
              <th class="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Matrix</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Active</th>
              <th class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-neutral-500">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each entitlements as row (row.id)}
              <tr class="hover:bg-neutral-50">
                <td class="px-4 py-3 text-neutral-800">#{row.case}</td>
                <td class="px-4 py-3 text-neutral-600 capitalize">{row.portal_role.replaceAll("_", " ")}</td>
                <td class="px-4 py-3 text-neutral-600 text-xs leading-5">
                  Project: {row.project_name || "--"}<br />
                  SPV: {row.spv_name || "--"}<br />
                  Contract: {row.contract_reference || "--"}<br />
                  Vehicle: {row.investment_vehicle_reference || "--"}
                </td>
                <td class="px-4 py-3 text-neutral-600 text-xs leading-5">
                  Budget: {row.budget_scope}<br />
                  View investors: {row.can_view_other_investors ? "Yes" : "No"}<br />
                  Edit: {row.can_edit ? "Yes" : "No"}<br />
                  Approve: {row.can_approve ? "Yes" : "No"}
                </td>
                <td class="px-4 py-3 text-right text-neutral-700">{row.is_active ? "Yes" : "No"}</td>
                <td class="px-4 py-3 text-right">
                  <button onclick={() => toggleActive(row)} class="rounded-md border border-neutral-200 px-2.5 py-1 text-xs font-medium text-neutral-700 hover:bg-neutral-100">
                    {row.is_active ? "Deactivate" : "Activate"}
                  </button>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </section>
</div>

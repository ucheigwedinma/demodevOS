<script lang="ts">
  import { currency } from "$lib/stores/currency.svelte";
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import Breadcrumb from "$lib/components/Breadcrumb.svelte";
  import type { Project, PropertyListItem, PaginatedResponse, ProjectType, LandStatus } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  const projectId = $derived($page.params.id);

  type OwnershipAllocationRow = {
    investor_id?: number;
    party_name: string;
    ownership_percentage: string;
  };

  function emptyOwnershipAllocationRow(): OwnershipAllocationRow {
    return {
      party_name: "",
      ownership_percentage: "",
    };
  }

  let loading = $state(true);
  let saving = $state(false);
  let errors = $state<Record<string, string[]>>({});
  let projectName = $state("");
  let properties = $state<PropertyListItem[]>([]);

  let form = $state({
    property: 0,
    name: "",
    description: "",
    status: "planning",
    project_type: "residential" as ProjectType,
    location: "",
    spv_entity: "",
    land_status: "" as LandStatus | "",
    start_date: "",
    target_end_date: "",
    actual_end_date: "",
    land_acquisition_date: "",
    permit_approval_date: "",
    construction_start_date: "",
    budget: "",
    target_irr: "",
    project_manager: "",
    risk_rating: "low",
    raci_summary: {} as Record<string, string>,
  });
  let ownershipAllocations = $state<OwnershipAllocationRow[]>([emptyOwnershipAllocationRow()]);
  const ownershipAllocationTotal = $derived.by(() =>
    ownershipAllocations.reduce((sum, row) => {
      const pct = Number(row.ownership_percentage);
      return Number.isFinite(pct) ? sum + pct : sum;
    }, 0),
  );

  // RACI editor
  let newRaciRole = $state("");
  let newRaciLevel = $state("Responsible");

  $effect(() => {
    void projectId;
    loadProject();
    api.get<PaginatedResponse<PropertyListItem>>("/properties/", { page_size: "200" })
      .then((res) => { properties = res.results; })
      .catch(() => {});
  });

  async function loadProject() {
    loading = true;
    try {
      const p = await api.get<Project>(`/projects/${projectId}/`);
      projectName = p.name;
      form = {
        property: p.property ?? 0,
        name: p.name,
        description: p.description,
        status: p.status,
        project_type: p.project_type,
        location: p.location,
        spv_entity: p.spv_entity,
        land_status: p.land_status,
        start_date: p.start_date ?? "",
        target_end_date: p.target_end_date ?? "",
        actual_end_date: p.actual_end_date ?? "",
        land_acquisition_date: p.land_acquisition_date ?? "",
        permit_approval_date: p.permit_approval_date ?? "",
        construction_start_date: p.construction_start_date ?? "",
        budget: p.budget ?? "",
        target_irr: p.target_irr ?? "",
        project_manager: p.project_manager,
        risk_rating: p.risk_rating,
        raci_summary: { ...p.raci_summary },
      };
      ownershipAllocations = (p.ownership_allocations ?? [])
        .sort((a, b) => a.sort_order - b.sort_order)
        .map((row) => ({
          investor_id: row.investor_id,
          party_name: row.party_name,
          ownership_percentage: row.ownership_percentage,
        }));
      if (ownershipAllocations.length === 0) {
        ownershipAllocations = [emptyOwnershipAllocationRow()];
      }
    } catch {
      toast.error("Error", "Could not load project");
      goto("/projects");
    }
    loading = false;
  }

  async function handleSubmit(e: Event) {
    e.preventDefault();
    errors = {};
    saving = true;

    try {
      const payload = {
        ...form,
        property: form.property || null,
        start_date: form.start_date || null,
        target_end_date: form.target_end_date || null,
        actual_end_date: form.actual_end_date || null,
        land_acquisition_date: form.land_acquisition_date || null,
        permit_approval_date: form.permit_approval_date || null,
        construction_start_date: form.construction_start_date || null,
        budget: form.budget || null,
        target_irr: form.target_irr || null,
        land_status: form.land_status || "",
        ownership_allocations: buildOwnershipAllocationsPayload(),
      };
      await api.patch(`/projects/${projectId}/`, payload);
      toast.success("Project updated", `"${form.name}" has been saved`);
      goto(`/projects/${projectId}`);
    } catch (err) {
      if (err instanceof ApiError) {
        errors = err.fieldErrors;
        toast.error("Validation error", "Please fix the highlighted fields below");
      } else {
        toast.error("Something went wrong", "Could not update the project");
      }
      saving = false;
    }
  }

  function fieldError(field: string): string {
    return errors[field]?.[0] ?? "";
  }

  function addOwnershipAllocationRow() {
    ownershipAllocations = [...ownershipAllocations, emptyOwnershipAllocationRow()];
  }

  function removeOwnershipAllocationRow(index: number) {
    if (ownershipAllocations.length <= 1) return;
    ownershipAllocations = ownershipAllocations.filter((_, idx) => idx !== index);
  }

  function buildOwnershipAllocationsPayload() {
    return ownershipAllocations
      .map((row, idx) => ({
        investor_id: row.investor_id,
        party_name: row.party_name.trim(),
        ownership_percentage: row.ownership_percentage,
        sort_order: idx,
      }))
      .filter((row) => row.investor_id || row.party_name || row.ownership_percentage);
  }

  function addRaciEntry() {
    if (!newRaciRole.trim()) return;
    form.raci_summary = { ...form.raci_summary, [newRaciRole.trim()]: newRaciLevel };
    newRaciRole = "";
    newRaciLevel = "Responsible";
  }

  function removeRaciEntry(role: string) {
    const copy = { ...form.raci_summary };
    delete copy[role];
    form.raci_summary = copy;
  }
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
  </div>
{:else}
  <div class="max-w-2xl">
    <Breadcrumb items={[
      { label: "Projects", href: "/projects" },
      { label: projectName, href: `/projects/${projectId}` },
      { label: "Edit" },
    ]} />
    <h1 class="text-2xl font-bold text-neutral-900 mt-3 mb-8">Edit Project</h1>

    <form onsubmit={handleSubmit} class="space-y-6">
      <!-- Basic Info -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-5">
        <div>
          <label for="property" class="block text-xs font-medium text-neutral-500 mb-1.5">Property (Optional)</label>
          <select
            id="property"
            bind:value={form.property}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
          >
            <option value={0}>No linked property</option>
            {#each properties as p}
              <option value={p.id}>{p.name}</option>
            {/each}
          </select>
          {#if fieldError("property")}<p class="mt-1 text-xs text-red-500">{fieldError("property")}</p>{/if}
        </div>

        <div>
          <label for="name" class="block text-xs font-medium text-neutral-500 mb-1.5">Project Name</label>
          <input
            id="name"
            bind:value={form.name}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            placeholder="e.g. Phase 2 Tower Construction"
          />
          {#if fieldError("name")}<p class="mt-1 text-xs text-red-500">{fieldError("name")}</p>{/if}
        </div>

        <div>
          <label for="description" class="block text-xs font-medium text-neutral-500 mb-1.5">Description</label>
          <textarea
            id="description"
            bind:value={form.description}
            rows={3}
            class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm resize-none
                   focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            placeholder="Optional description"
          ></textarea>
        </div>
      </div>

      <!-- Type & Location -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-5">
        <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Type & Location</h3>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="project_type" class="block text-xs font-medium text-neutral-500 mb-1.5">Project Type</label>
            <select
              id="project_type"
              bind:value={form.project_type}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            >
              <option value="residential">Residential</option>
              <option value="mixed_use">Mixed-Use</option>
              <option value="commercial">Commercial</option>
              <option value="infrastructure">Infrastructure</option>
            </select>
          </div>
          <div>
            <label for="location" class="block text-xs font-medium text-neutral-500 mb-1.5">Location</label>
            <input
              id="location"
              bind:value={form.location}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
              placeholder="e.g. 123 Main St, Dubai Marina"
            />
          </div>
        </div>
      </div>

      <!-- Entity & Land -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-5">
        <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Entity & Land</h3>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="spv_entity" class="block text-xs font-medium text-neutral-500 mb-1.5">SPV / Entity</label>
            <input
              id="spv_entity"
              bind:value={form.spv_entity}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
              placeholder="e.g. Tower Holdings LLC"
            />
          </div>
          <div>
            <label for="land_status" class="block text-xs font-medium text-neutral-500 mb-1.5">Land Status</label>
            <select
              id="land_status"
              bind:value={form.land_status}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            >
              <option value="">Not specified</option>
              <option value="freehold">Freehold</option>
              <option value="leasehold">Leasehold</option>
              <option value="under_contract">Under Contract</option>
              <option value="to_acquire">To Acquire</option>
              <option value="joint_venture">Joint Venture</option>
            </select>
          </div>
          <div class="col-span-2">
            <div class="flex items-center justify-between mb-1.5">
              <label class="block text-xs font-medium text-neutral-500">Ownership Structure</label>
              <button
                type="button"
                onclick={addOwnershipAllocationRow}
                class="text-xs font-medium text-neutral-600 hover:text-neutral-900 transition-colors"
              >
                + Add Owner
              </button>
            </div>
            <div class="space-y-2">
              {#each ownershipAllocations as row, idx}
                <div class="grid grid-cols-[1fr_8rem_auto] gap-2">
                  <input
                    bind:value={row.party_name}
                    class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm
                           focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
                    placeholder="e.g. Developer"
                  />
                  <div class="relative">
                    <input
                      type="number"
                      min="0.01"
                      max="100"
                      step="0.01"
                      bind:value={row.ownership_percentage}
                      class="w-full pl-3 pr-6 py-2.5 border border-neutral-200 rounded-lg text-sm tabular-nums
                             focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
                      placeholder="0.00"
                    />
                    <span class="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-neutral-500">%</span>
                  </div>
                  <button
                    type="button"
                    onclick={() => removeOwnershipAllocationRow(idx)}
                    disabled={ownershipAllocations.length <= 1}
                    class="px-3 py-2.5 border border-neutral-200 rounded-lg text-xs font-medium text-neutral-500
                           hover:bg-neutral-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    Remove
                  </button>
                </div>
              {/each}
            </div>
            <div class="mt-2 flex items-center justify-between">
              <p class="text-xs text-neutral-500">
                Ownership inputs sync directly to Finance cap table and distribution calculations.
              </p>
              <span class={`text-xs font-medium ${ownershipAllocationTotal > 100 ? "text-red-600" : "text-neutral-600"}`}>
                Total: {ownershipAllocationTotal.toFixed(2)}%
              </span>
            </div>
            {#if fieldError("ownership_allocations")}
              <p class="mt-1 text-xs text-red-500">{fieldError("ownership_allocations")}</p>
            {/if}
          </div>
        </div>
      </div>

      <!-- Schedule -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-5">
        <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Schedule</h3>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="status" class="block text-xs font-medium text-neutral-500 mb-1.5">Status</label>
            <select
              id="status"
              bind:value={form.status}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            >
              <option value="planning">Planning</option>
              <option value="in_progress">In Progress</option>
              <option value="on_hold">On Hold</option>
              <option value="completed">Completed</option>
            </select>
          </div>
          <div>
            <label for="project_manager" class="block text-xs font-medium text-neutral-500 mb-1.5">Project Manager</label>
            <input
              id="project_manager"
              bind:value={form.project_manager}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
              placeholder="e.g. John Smith"
            />
          </div>
          <div>
            <label for="start_date" class="block text-xs font-medium text-neutral-500 mb-1.5">Start Date</label>
            <DateInput id="start_date" bind:value={form.start_date} />
          </div>
          <div>
            <label for="target_end_date" class="block text-xs font-medium text-neutral-500 mb-1.5">Target End Date</label>
            <DateInput id="target_end_date" bind:value={form.target_end_date} />
          </div>
          <div>
            <label for="actual_end_date" class="block text-xs font-medium text-neutral-500 mb-1.5">Actual End Date</label>
            <DateInput id="actual_end_date" bind:value={form.actual_end_date} />
          </div>
          <div>
            <label for="land_acquisition_date" class="block text-xs font-medium text-neutral-500 mb-1.5">Land Acquisition Date</label>
            <DateInput id="land_acquisition_date" bind:value={form.land_acquisition_date} />
          </div>
          <div>
            <label for="permit_approval_date" class="block text-xs font-medium text-neutral-500 mb-1.5">Permit Approval Date</label>
            <DateInput id="permit_approval_date" bind:value={form.permit_approval_date} />
          </div>
          <div>
            <label for="construction_start_date" class="block text-xs font-medium text-neutral-500 mb-1.5">Construction Start</label>
            <DateInput id="construction_start_date" bind:value={form.construction_start_date} />
          </div>
        </div>
      </div>

      <!-- Budget & Financials -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-5">
        <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">Budget & Financials</h3>
        <div class="grid grid-cols-2 gap-4">
          <div>
            <label for="budget" class="block text-xs font-medium text-neutral-500 mb-1.5">Approved Budget ({currency.config.symbol})</label>
            <input
              id="budget"
              bind:value={form.budget}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm tabular-nums
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
              placeholder="0.00"
            />
            {#if fieldError("budget")}<p class="mt-1 text-xs text-red-500">{fieldError("budget")}</p>{/if}
          </div>
          <div>
            <label for="target_irr" class="block text-xs font-medium text-neutral-500 mb-1.5">Target IRR (%)</label>
            <input
              id="target_irr"
              bind:value={form.target_irr}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm tabular-nums
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
              placeholder="e.g. 18.50"
            />
            {#if fieldError("target_irr")}<p class="mt-1 text-xs text-red-500">{fieldError("target_irr")}</p>{/if}
          </div>
          <div>
            <label for="risk_rating" class="block text-xs font-medium text-neutral-500 mb-1.5">Risk Rating</label>
            <select
              id="risk_rating"
              bind:value={form.risk_rating}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>
        </div>
      </div>

      <!-- RACI Summary -->
      <div class="bg-white rounded-xl border border-neutral-200 p-6 space-y-5">
        <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider">RACI Summary</h3>
        <p class="text-xs text-neutral-500">Define roles and their RACI assignments for this project.</p>

        {#if Object.keys(form.raci_summary).length > 0}
          <div class="space-y-2">
            {#each Object.entries(form.raci_summary) as [role, level]}
              <div class="flex items-center justify-between px-3 py-2 rounded-lg bg-neutral-50">
                <div class="flex items-center gap-3">
                  <span class="text-sm font-medium text-neutral-900">{role}</span>
                  <span class="text-xs text-neutral-500">{level}</span>
                </div>
                <button
                  type="button"
                  onclick={() => removeRaciEntry(role)}
                  class="text-xs text-neutral-400 hover:text-red-600 transition-colors"
                >Remove</button>
              </div>
            {/each}
          </div>
        {/if}

        <div class="flex items-end gap-3">
          <div class="flex-1">
            <label for="raci_role" class="block text-xs font-medium text-neutral-500 mb-1.5">Role</label>
            <input
              id="raci_role"
              bind:value={newRaciRole}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
              placeholder="e.g. Project Manager"
            />
          </div>
          <div class="w-40">
            <label for="raci_level" class="block text-xs font-medium text-neutral-500 mb-1.5">Assignment</label>
            <select
              id="raci_level"
              bind:value={newRaciLevel}
              class="w-full px-3 py-2.5 border border-neutral-200 rounded-lg text-sm
                     focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
            >
              <option value="Responsible">Responsible</option>
              <option value="Accountable">Accountable</option>
              <option value="Consulted">Consulted</option>
              <option value="Informed">Informed</option>
            </select>
          </div>
          <button
            type="button"
            onclick={addRaciEntry}
            class="px-4 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors"
          >Add</button>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex gap-3">
        <button
          type="submit"
          disabled={saving}
          class="px-6 py-2.5 bg-neutral-900 text-white rounded-lg text-sm font-medium
                 hover:bg-neutral-800 disabled:opacity-50 transition-colors"
        >
          {saving ? "Saving..." : "Save Changes"}
        </button>
        <a
          href="/projects/{projectId}"
          class="px-6 py-2.5 border border-neutral-200 rounded-lg text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors"
        >
          Cancel
        </a>
      </div>
    </form>
  </div>
{/if}

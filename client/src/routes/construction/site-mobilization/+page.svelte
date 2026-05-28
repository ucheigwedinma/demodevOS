<script lang="ts">
  import { onMount } from "svelte";
  import { api } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    ConstructionSiteMobilization,
    ConstructionSiteMobilizationResponse,
    SiteMobilizationPreparationStatus,
  } from "$lib/types";
  import DateInput from "$lib/components/DateInput.svelte";

  type SitePreparationKey = keyof ConstructionSiteMobilization["site_preparation"];
  type ChecklistKey =
    | "contractors_mobilized"
    | "equipment_delivered"
    | "material_staging"
    | "survey_control_established"
    | "permits_obtained"
    | "insurance_certificates"
    | "safety_induction";
  type ManualChecklistKey =
    | "survey_control_established"
    | "permits_obtained"
    | "insurance_certificates";

  const sitePreparationItems: Array<{ key: SitePreparationKey; label: string }> = [
    { key: "fencing", label: "Fencing" },
    { key: "site_offices", label: "Site offices" },
    { key: "storage_yards", label: "Storage yards" },
    { key: "worker_welfare_facilities", label: "Worker welfare facilities" },
    { key: "utilities_connection", label: "Utilities connection" },
    { key: "temporary_roads", label: "Temporary roads" },
    { key: "security_deployment", label: "Security deployment" },
  ];

  const checklistItems: Array<{
    key: ChecklistKey;
    label: string;
    source: "procurement" | "hr" | "manual";
    manualDetail?: string;
  }> = [
    { key: "contractors_mobilized", label: "Contractors mobilized", source: "procurement" },
    { key: "equipment_delivered", label: "Equipment delivered", source: "hr" },
    { key: "material_staging", label: "Material staging", source: "procurement" },
    {
      key: "survey_control_established",
      label: "Survey control established",
      source: "manual",
      manualDetail: "Survey benchmarks and control points verified on site.",
    },
    {
      key: "permits_obtained",
      label: "Permits obtained",
      source: "manual",
      manualDetail: "Regulatory permits reviewed and confirmed for mobilization.",
    },
    {
      key: "insurance_certificates",
      label: "Insurance certificates",
      source: "manual",
      manualDetail: "Required insurance certificates validated and on record.",
    },
    { key: "safety_induction", label: "Safety induction", source: "hr" },
  ];

  const statusOptions: Array<{ value: SiteMobilizationPreparationStatus; label: string }> = [
    { value: "not_started", label: "Not Started" },
    { value: "in_progress", label: "In Progress" },
    { value: "completed", label: "Completed" },
    { value: "blocked", label: "Blocked" },
  ];

  const defaultSitePreparation: Record<SitePreparationKey, SiteMobilizationPreparationStatus> = {
    fencing: "not_started",
    site_offices: "not_started",
    storage_yards: "not_started",
    worker_welfare_facilities: "not_started",
    utilities_connection: "not_started",
    temporary_roads: "not_started",
    security_deployment: "not_started",
  };

  const defaultManualChecklist: Record<ManualChecklistKey, boolean> = {
    survey_control_established: false,
    permits_obtained: false,
    insurance_certificates: false,
  };

  let loading = $state(true);
  let refreshing = $state(false);
  let saving = $state(false);
  let error = $state("");
  let payload = $state<ConstructionSiteMobilizationResponse | null>(null);
  let selectedProject = $state("");
  let plannedStartDate = $state("");
  let actualStartDate = $state("");
  let notes = $state("");
  let sitePreparation = $state<Record<SitePreparationKey, SiteMobilizationPreparationStatus>>({
    ...defaultSitePreparation,
  });
  let manualChecklist = $state<Record<ManualChecklistKey, boolean>>({
    ...defaultManualChecklist,
  });

  function hydrateForm(mobilization: ConstructionSiteMobilization | null) {
    if (!mobilization) {
      plannedStartDate = "";
      actualStartDate = "";
      notes = "";
      sitePreparation = { ...defaultSitePreparation };
      manualChecklist = { ...defaultManualChecklist };
      return;
    }

    plannedStartDate = mobilization.planned_start_date ?? "";
    actualStartDate = mobilization.actual_start_date ?? "";
    notes = mobilization.notes ?? "";
    sitePreparation = { ...mobilization.site_preparation };
    manualChecklist = {
      survey_control_established: mobilization.checklist.survey_control_established,
      permits_obtained: mobilization.checklist.permits_obtained,
      insurance_certificates: mobilization.checklist.insurance_certificates,
    };
  }

  function statusLabel(value: SiteMobilizationPreparationStatus): string {
    return statusOptions.find((option) => option.value === value)?.label ?? value;
  }

  function statusBadgeClass(value: SiteMobilizationPreparationStatus): string {
    if (value === "completed") return "bg-emerald-100 text-emerald-800";
    if (value === "blocked") return "bg-rose-100 text-rose-800";
    if (value === "in_progress") return "bg-amber-100 text-amber-800";
    return "bg-neutral-100 text-neutral-700";
  }

  function linkedSourceLabel(source: "procurement" | "hr"): string {
    if (source === "procurement") return "Synced from Procurement";
    return "Synced from HR";
  }

  function checklistItemMeta(item: (typeof checklistItems)[number]): string {
    if (item.source === "manual") {
      return item.manualDetail ?? "Tracked directly on Site Mobilization.";
    }
    return linkedSourceLabel(item.source);
  }

  function checklistValue(key: ChecklistKey): boolean {
    return Boolean(payload?.mobilization?.checklist?.[key]);
  }

  function isManualChecklistKey(key: ChecklistKey): key is ManualChecklistKey {
    return (
      key === "survey_control_established"
      || key === "permits_obtained"
      || key === "insurance_certificates"
    );
  }

  async function fetchMobilization(silent = false) {
    if (silent) {
      refreshing = true;
    } else {
      loading = true;
    }
    error = "";

    try {
      const params: Record<string, string> = {};
      if (selectedProject) {
        params.project = selectedProject;
      }
      const res = await api.get<ConstructionSiteMobilizationResponse>(
        "/projects/construction/site-mobilization/",
        params,
      );
      payload = res;
      selectedProject = res.filters.project ? String(res.filters.project) : "";
      hydrateForm(res.mobilization);
      if (silent) toast.success("Refreshed", "Site mobilization data loaded.");
    } catch {
      payload = null;
      error = "Could not load Site Mobilization.";
      if (silent) toast.error("Load failed", "Could not load site mobilization.");
    } finally {
      loading = false;
      refreshing = false;
    }
  }

  async function saveChanges() {
    if (!selectedProject) return;

    saving = true;
    error = "";
    try {
      const res = await api.patch<{ mobilization: ConstructionSiteMobilization }>(
        "/projects/construction/site-mobilization/",
        {
          project: Number(selectedProject),
          planned_start_date: plannedStartDate || null,
          actual_start_date: actualStartDate || null,
          notes,
          site_preparation: sitePreparation,
          checklist: manualChecklist,
        },
      );
      if (payload) {
        payload = {
          ...payload,
          filters: { project: Number(selectedProject) },
          mobilization: res.mobilization,
        };
      }
      hydrateForm(res.mobilization);
      toast.success("Saved", "Site mobilization updated successfully.");
    } catch {
      error = "Could not save Site Mobilization.";
      toast.error("Save failed", "Could not save site mobilization.");
    } finally {
      saving = false;
    }
  }

  onMount(() => {
    fetchMobilization();
  });
</script>

{#if loading}
  <div class="flex items-center justify-center py-24">
    <div class="inline-block w-6 h-6 border-2 border-neutral-200 border-t-neutral-900 rounded-full animate-spin"></div>
  </div>
{:else if error && !payload}
  <div class="rounded-xl border border-red-200 bg-red-50 px-5 py-4">
    <p class="text-sm font-medium text-red-700">{error}</p>
  </div>
{:else}
  <div class="space-y-6">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div class="flex flex-wrap items-start justify-between gap-4 w-full">
        <div>
          <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-yellow-600">Construction</p>
          <h1 class="mt-2 text-2xl font-bold text-neutral-900 tracking-wide">Site Mobilization</h1>
          <p class="mt-1 text-sm text-neutral-500">From award to site ready: streamline every mobilization step</p>
        </div>
        <button
          onclick={() => fetchMobilization(true)}
          class="rounded-lg border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
        >
          {refreshing ? "Refreshing..." : "Refresh"}
        </button>
      </div>
    </div>

    <div class="rounded-xl border border-neutral-200 bg-white p-4">
      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
        <label class="text-xs text-neutral-500">
          Project
          <select
            bind:value={selectedProject}
            class="mt-1 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
          >
            <option value="">Select project</option>
            {#each payload?.projects ?? [] as project}
              <option value={String(project.id)}>{project.name}</option>
            {/each}
          </select>
        </label>

        <div class="flex items-end gap-2">
          <button
            onclick={() => fetchMobilization(true)}
            class="flex-1 rounded-lg bg-neutral-900 px-3 py-2 text-sm font-medium text-white hover:bg-neutral-800"
          >
            Apply
          </button>
        </div>
      </div>
    </div>

    {#if payload?.mobilization}
      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
        <div class="rounded-xl border border-sky-200 bg-sky-100 p-4 shadow-sm">
          <p class="text-[10px] font-semibold text-sky-800 uppercase tracking-wider">Overall Completion</p>
          <p class="mt-1 text-xl font-bold text-sky-800 tabular-nums">{payload.mobilization.completion.overall_percent.toFixed(1)}%</p>
        </div>
        <div class="rounded-xl border border-emerald-300 bg-emerald-200 p-4 shadow-sm">
          <p class="text-[10px] font-semibold text-emerald-700 uppercase tracking-wider">Blocked Items</p>
          <p class="mt-1 text-xl font-bold text-emerald-700 tabular-nums">{payload.mobilization.completion.blocked_items}</p>
        </div>
        <div class="rounded-xl border border-amber-300 bg-amber-200 p-4 shadow-sm">
          <p class="text-[10px] font-semibold text-amber-600 uppercase tracking-wider">Procurement Links</p>
          <p class="mt-1 text-sm font-semibold text-amber-600">
            Contractors: {payload.mobilization.linked_sources.procurement.contractors_count}
          </p>
          <p class="text-xs text-amber-600">
            Material staging: {payload.mobilization.linked_sources.procurement.material_staging_count}
          </p>
        </div>
        <div class="rounded-xl border border-rose-300 bg-rose-200 p-4 shadow-sm">
          <p class="text-[10px] font-semibold text-rose-600 uppercase tracking-wider">HR Links</p>
          <p class="mt-1 text-sm font-semibold text-rose-600">
            Equipment delivery: {payload.mobilization.linked_sources.hr.equipment_delivery_count}
          </p>
          <p class="text-xs text-rose-600">
            Safety induction: {payload.mobilization.linked_sources.hr.safety_induction_count}
          </p>
        </div>
      </div>

      <div class="rounded-xl border border-neutral-200 bg-white p-5">
        <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Site Preparation</h3>
        <div class="space-y-3">
          {#each sitePreparationItems as item}
            <div class="flex flex-col gap-2 rounded-lg border border-neutral-200 bg-neutral-50 p-3 md:flex-row md:items-center md:justify-between">
              <div class="flex items-center gap-2">
                <p class="text-sm font-medium text-neutral-900">{item.label}</p>
                <span class={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${statusBadgeClass(sitePreparation[item.key])}`}>
                  {statusLabel(sitePreparation[item.key])}
                </span>
              </div>
              <select
                value={sitePreparation[item.key]}
                onchange={(event) => {
                  const next = (event.currentTarget as HTMLSelectElement).value as SiteMobilizationPreparationStatus;
                  sitePreparation = { ...sitePreparation, [item.key]: next };
                }}
                class="w-full md:w-52 rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
              >
                {#each statusOptions as option}
                  <option value={option.value}>{option.label}</option>
                {/each}
              </select>
            </div>
          {/each}
        </div>
      </div>

      <div class="rounded-xl border border-neutral-200 bg-white p-5">
        <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Mobilization Checklist</h3>
        <div class="space-y-3">
          {#each checklistItems as item}
            <div class="flex items-start gap-3 rounded-lg border border-neutral-200 bg-neutral-50 p-3">
              <input
                type="checkbox"
                class="mt-0.5 h-4 w-4 rounded border-neutral-300"
                checked={item.source === "manual" ? manualChecklist[item.key as ManualChecklistKey] : checklistValue(item.key)}
                disabled={item.source !== "manual"}
                onchange={(event) => {
                  if (!isManualChecklistKey(item.key)) return;
                  manualChecklist = {
                    ...manualChecklist,
                    [item.key]: (event.currentTarget as HTMLInputElement).checked,
                  };
                }}
              />
              <div class="min-w-0">
                <p class="text-sm font-medium text-neutral-900">{item.label}</p>
                <p class="mt-0.5 text-xs text-neutral-500">{checklistItemMeta(item)}</p>
              </div>
            </div>
          {/each}
        </div>
      </div>

      <div class="rounded-xl border border-neutral-200 bg-white p-5">
        <h3 class="text-sm font-semibold text-neutral-900 uppercase tracking-wider mb-4">Schedule & Notes</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <label class="text-xs text-neutral-500">
            Planned Mobilization Start
            <DateInput bind:value={plannedStartDate} />
          </label>

          <label class="text-xs text-neutral-500">
            Actual Mobilization Start
            <DateInput bind:value={actualStartDate} />
          </label>
        </div>
        <label class="mt-3 block text-xs text-neutral-500">
          Notes
          <textarea
            bind:value={notes}
            rows={3}
            class="mt-1 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
            placeholder="Mobilization notes..."
          ></textarea>
        </label>
      </div>

      <div class="flex justify-end">
        <button
          onclick={saveChanges}
          disabled={saving || !selectedProject}
          class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? "Saving..." : "Save Site Mobilization"}
        </button>
      </div>
    {:else}
      <div class="rounded-xl border border-neutral-200 bg-white px-5 py-4">
        <p class="text-sm text-neutral-600">Select a project to load Site Mobilization.</p>
      </div>
    {/if}

    {#if error}
      <div class="rounded-xl border border-red-200 bg-red-50 px-5 py-4">
        <p class="text-sm font-medium text-red-700">{error}</p>
      </div>
    {/if}
  </div>
{/if}

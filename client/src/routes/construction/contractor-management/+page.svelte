<script lang="ts">
  import { onMount } from "svelte";
  import { api, ApiError } from "$lib/api";
  import { currency } from "$lib/stores/currency.svelte";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    ConstructionContractorProfile,
    PaginatedResponse,
    ProjectExecutionInspectionStatus,
  } from "$lib/types";

  type ContractorManagementSetupOptions = {
    projects: { id: number; name: string }[];
    contractors: {
      id: number;
      name: string;
      category: string;
      contact_person: string;
      email: string;
      phone: string;
      compliance_status: string;
      performance_rating: string;
    }[];
    work_packages: {
      id: number;
      project: number;
      project_name: string;
      package_id: string | null;
      name: string;
      contractor_id: number | null;
      contractor_name: string | null;
      budget: string;
    }[];
    rfis: {
      id: number;
      project: number;
      project_name: string;
      title: string;
      status: string;
      issue_date: string;
      severity: string;
    }[];
    inspections: {
      id: number;
      project: number;
      project_name: string;
      inspection_number: string;
      status: string;
      inspected_on: string;
      overall_score: string | null;
    }[];
  };

  type ContractorFormState = {
    project_id: string;
    contractor_id: string;
    company_profile: string;
    trade_specialization: string;
    contract_value: string;
    insurance: string;
    licenses: string;
    performance_rating: string;
    payment_history: string;
    safety_record: string;
    quality_record: string;
    site_instructions: string;
    work_packages: number[];
    rfis: number[];
    inspection_results: number[];
  };

  const emptySetupOptions: ContractorManagementSetupOptions = {
    projects: [],
    contractors: [],
    work_packages: [],
    rfis: [],
    inspections: [],
  };

  const emptyFormState: ContractorFormState = {
    project_id: "",
    contractor_id: "",
    company_profile: "",
    trade_specialization: "",
    contract_value: "",
    insurance: "",
    licenses: "",
    performance_rating: "",
    payment_history: "",
    safety_record: "",
    quality_record: "",
    site_instructions: "",
    work_packages: [],
    rfis: [],
    inspection_results: [],
  };

  let loading = $state(true);
  let setupLoading = $state(true);
  let saving = $state(false);
  let deletingProfileId = $state<number | null>(null);
  let expandedRows = $state<Set<number>>(new Set());
  let drawerProfile = $state<ConstructionContractorProfile | null>(null);

  let profiles = $state<ConstructionContractorProfile[]>([]);
  let setupOptions = $state<ContractorManagementSetupOptions>({ ...emptySetupOptions });

  let totalCount = $state(0);
  let currentPage = $state(1);
  let pageSize = $state(20);

  let projectFilter = $state("");
  let contractorFilter = $state("");
  let searchInput = $state("");
  let searchQuery = $state("");
  let ordering = $state("-updated_at");

  let showModal = $state(false);
  let editingProfile = $state<ConstructionContractorProfile | null>(null);
  let formState = $state<ContractorFormState>({ ...emptyFormState });

  const totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  const startItem = $derived(totalCount === 0 ? 0 : (currentPage - 1) * pageSize + 1);
  const endItem = $derived(Math.min(currentPage * pageSize, totalCount));

  const formWorkPackageOptions = $derived.by(() => {
    if (!formState.project_id) return [] as ContractorManagementSetupOptions["work_packages"];
    const projectId = Number(formState.project_id);
    return setupOptions.work_packages.filter((row) => row.project === projectId);
  });

  const formRfiOptions = $derived.by(() => {
    if (!formState.project_id) return [] as ContractorManagementSetupOptions["rfis"];
    const projectId = Number(formState.project_id);
    return setupOptions.rfis.filter((row) => row.project === projectId);
  });

  const formInspectionOptions = $derived.by(() => {
    if (!formState.project_id) return [] as ContractorManagementSetupOptions["inspections"];
    const projectId = Number(formState.project_id);
    return setupOptions.inspections.filter((row) => row.project === projectId);
  });

  const totalContractValue = $derived(
    profiles.reduce((sum, row) => sum + Number(row.contract_value || 0), 0),
  );
  const averageRating = $derived(
    profiles.length
      ? profiles.reduce((sum, row) => sum + Number(row.performance_rating || 0), 0) / profiles.length
      : 0,
  );
  const totalAssignedWorkPackages = $derived(
    profiles.reduce((sum, row) => sum + row.work_package_records.length, 0),
  );
  const totalReceivedItems = $derived(
    profiles.reduce(
      (sum, row) =>
        sum
        + row.received_items.site_instructions.count
        + row.received_items.rfis.count
        + row.received_items.inspection_results.count,
      0,
    ),
  );

  function listRows<T>(payload: PaginatedResponse<T> | T[]): T[] {
    if (Array.isArray(payload)) return payload;
    return payload.results ?? [];
  }

  function apiErrorDetail(err: unknown, fallback = "Please try again later"): string {
    if (err instanceof ApiError) {
      const detail = err.data?.detail;
      if (typeof detail === "string" && detail.trim().length > 0) return detail;
      if (err.fieldErrors) {
        const first = Object.entries(err.fieldErrors)[0];
        if (first) return `${first[0]}: ${first[1][0]}`;
      }
    }
    return fallback;
  }

  function formatDate(value: string): string {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return value;
    return parsed.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  function inspectionStatusLabel(status: ProjectExecutionInspectionStatus | string): string {
    return status
      .split("_")
      .map((chunk) => chunk.charAt(0).toUpperCase() + chunk.slice(1))
      .join(" ");
  }

  function toggleRow(id: number) {
    const next = new Set(expandedRows);
    if (next.has(id)) next.delete(id); else next.add(id);
    expandedRows = next;
  }

  function openDrawer(profile: ConstructionContractorProfile) {
    drawerProfile = profile;
  }

  function closeDrawer() {
    drawerProfile = null;
  }

  function buildListParams(page = currentPage): Record<string, string> {
    const params: Record<string, string> = {
      page: String(page),
      page_size: String(pageSize),
      ordering,
    };
    if (projectFilter) params.project = projectFilter;
    if (contractorFilter) params.contractor = contractorFilter;
    if (searchQuery) params.search = searchQuery;
    return params;
  }

  async function fetchProfiles(page = currentPage) {
    loading = true;
    try {
      const payload = await api.get<PaginatedResponse<ConstructionContractorProfile>>(
        "/projects/contractor-management/",
        buildListParams(page),
      );
      profiles = listRows(payload);
      totalCount = payload.count ?? profiles.length;
      currentPage = page;
    } catch (err) {
      toast.error("Could not load contractor profiles", apiErrorDetail(err));
      profiles = [];
      totalCount = 0;
    } finally {
      loading = false;
    }
  }

  async function fetchSetupOptions(projectId?: string) {
    setupLoading = true;
    try {
      const params: Record<string, string> = {};
      if (projectId) params.project = projectId;
      setupOptions = await api.get<ContractorManagementSetupOptions>(
        "/projects/contractor-management/setup-options/",
        params,
      );
    } catch (err) {
      toast.error("Could not load setup options", apiErrorDetail(err));
      setupOptions = { ...emptySetupOptions };
    } finally {
      setupLoading = false;
    }
  }

  function resetForm() {
    formState = { ...emptyFormState };
    editingProfile = null;
  }

  const isDev = $derived(typeof window !== "undefined" && window.location.hostname === "localhost");

  function devFillContractor() {
    const trades = ["Civil Works", "Electrical Installation", "Plumbing & Drainage", "Structural Steel", "HVAC & Mechanical", "Roofing & Waterproofing", "Finishing & Interiors", "Landscaping & External Works"];
    const companies = ["Zenith Construction Ltd", "Pioneer Building Services", "Atlas Engineering Corp", "Meridian Contractors", "Summit Works Nigeria Ltd", "Delta Infrastructure Group"];
    const idx = Math.floor(Math.random() * trades.length);

    formState = {
      ...formState,
      company_profile: `${companies[idx % companies.length]} — Tier-1 contractor specialising in ${trades[idx].toLowerCase()} for commercial and residential developments. Established 2012, ISO 9001 certified, 150+ completed projects.`,
      trade_specialization: trades[idx],
      contract_value: String(Math.floor(Math.random() * 450_000_000 + 50_000_000)),
      insurance: "Comprehensive All-Risk Policy (CAR) — NGN 500M cover. Professional Indemnity — NGN 200M. Workers' Compensation active. Expiry: Dec 2026.",
      licenses: "COREN registered. NIS certified. Lagos State Building Permit (LASBCA). Federal Ministry of Works Category A.",
      performance_rating: (Math.random() * 2 + 3).toFixed(1),
      payment_history: "12 milestone payments completed on time. No deductions. Retention: 5% held, 2.5% released at practical completion.",
      safety_record: "Zero LTI in last 18 months. Weekly toolbox talks. Full PPE compliance. HSE officer on site. OSHA-aligned safety management system.",
      quality_record: "3 NCRs raised (all closed). Monthly quality audits passed. Material test certificates on file. Concrete cube test compliance: 100%.",
      site_instructions: "SI-001: Excavation depth revised to 2.4m per geotechnical report.\nSI-002: Rebar spacing adjusted to 150mm c/c for raft foundation.\nSI-003: Waterproofing membrane specification upgraded to Sika.",
    };
  }

  function openCreateModal() {
    resetForm();
    showModal = true;
  }

  function openEditModal(profile: ConstructionContractorProfile) {
    editingProfile = profile;
    formState = {
      project_id: String(profile.project),
      contractor_id: String(profile.contractor),
      company_profile: profile.company_profile ?? "",
      trade_specialization: profile.trade_specialization ?? "",
      contract_value: profile.contract_value ?? "",
      insurance: profile.insurance ?? "",
      licenses: profile.licenses ?? "",
      performance_rating: profile.performance_rating ?? "",
      payment_history: profile.payment_history ?? "",
      safety_record: profile.safety_record ?? "",
      quality_record: profile.quality_record ?? "",
      site_instructions: profile.site_instructions ?? "",
      work_packages: [...profile.work_packages],
      rfis: [...profile.rfis],
      inspection_results: [...profile.inspection_results],
    };
    showModal = true;
  }

  function closeModal() {
    showModal = false;
    resetForm();
  }

  function parseSelectedNumbers(event: Event): number[] {
    const select = event.currentTarget as HTMLSelectElement;
    return Array.from(select.selectedOptions)
      .map((option) => Number(option.value))
      .filter((value) => Number.isInteger(value) && value > 0);
  }

  function onFormProjectChange(nextProjectId: string) {
    if (formState.project_id === nextProjectId) return;
    formState = {
      ...formState,
      project_id: nextProjectId,
      contractor_id: "",
      work_packages: [],
      rfis: [],
      inspection_results: [],
    };
    if (nextProjectId) fetchSetupOptions(nextProjectId);
  }

  async function saveProfile() {
    if (!formState.project_id || !formState.contractor_id) {
      toast.error("Missing required fields", "Project and contractor are required.");
      return;
    }

    saving = true;
    const profileProjectId = formState.project_id;
    try {
      const payload = {
        project: Number(formState.project_id),
        contractor: Number(formState.contractor_id),
        company_profile: formState.company_profile,
        trade_specialization: formState.trade_specialization,
        contract_value: formState.contract_value || "0",
        insurance: formState.insurance,
        licenses: formState.licenses,
        performance_rating: formState.performance_rating || "0",
        payment_history: formState.payment_history,
        safety_record: formState.safety_record,
        quality_record: formState.quality_record,
        site_instructions: formState.site_instructions,
        work_packages: formState.work_packages,
        rfis: formState.rfis,
        inspection_results: formState.inspection_results,
      };

      if (editingProfile) {
        await api.patch(`/projects/contractor-management/${editingProfile.id}/`, payload);
        toast.success("Contractor profile updated", "Changes were saved successfully.");
      } else {
        await api.post("/projects/contractor-management/", payload);
        toast.success("Contractor profile created", "Contractor management record added.");
      }

      closeModal();
      await fetchProfiles(currentPage);
      await fetchSetupOptions(projectFilter || profileProjectId);
    } catch (err) {
      toast.error("Could not save contractor profile", apiErrorDetail(err));
    } finally {
      saving = false;
    }
  }

  async function deleteProfile(profile: ConstructionContractorProfile) {
    const confirmed = confirm(`Delete contractor profile for ${profile.contractor_name}?`);
    if (!confirmed) return;
    deletingProfileId = profile.id;
    try {
      await api.delete(`/projects/contractor-management/${profile.id}/`);
      toast.success("Contractor profile deleted", `${profile.contractor_name} was removed.`);

      const nextPage =
        currentPage > 1 && profiles.length === 1
          ? currentPage - 1
          : currentPage;
      await fetchProfiles(nextPage);
      await fetchSetupOptions(projectFilter);
    } catch (err) {
      toast.error("Could not delete contractor profile", apiErrorDetail(err));
    } finally {
      deletingProfileId = null;
    }
  }

  async function applyFilters() {
    currentPage = 1;
    searchQuery = searchInput.trim();
    await fetchProfiles(1);
    await fetchSetupOptions(projectFilter);
  }

  async function clearFilters() {
    projectFilter = "";
    contractorFilter = "";
    searchInput = "";
    searchQuery = "";
    currentPage = 1;
    await fetchProfiles(1);
    await fetchSetupOptions();
  }

  onMount(async () => {
    await Promise.all([fetchSetupOptions(), fetchProfiles(1)]);
  });
</script>

<div class="space-y-6">
  <div class="flex flex-wrap items-start justify-between gap-4">
    <div class="flex flex-wrap items-start justify-between gap-4 w-full">
      <div>
        <p class="text-[11px] font-semibold uppercase tracking-[0.35em] text-green-500">Construction</p>
        <h1 class="mt-2 text-2xl font-bold tracking-wide text-neutral-800">Contractor Management</h1>
        <p class="mt-1 text-sm text-neutral-500">Manages all site contractors.</p>
      </div>
      <button
        onclick={openCreateModal}
        class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-60"
        disabled={setupLoading}
      >
        New Contractor Profile
      </button>
    </div>
  </div>

  <div class="rounded-xl border border-neutral-200 bg-white p-4">
    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-3">
      <label class="text-xs text-neutral-500">
        Project
        <select
          bind:value={projectFilter}
          class="mt-1 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
        >
          <option value="">All projects</option>
          {#each setupOptions.projects as project}
            <option value={String(project.id)}>{project.name}</option>
          {/each}
        </select>
      </label>

      <label class="text-xs text-neutral-500">
        Contractor
        <select
          bind:value={contractorFilter}
          class="mt-1 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
        >
          <option value="">All contractors</option>
          {#each setupOptions.contractors as contractor}
            <option value={String(contractor.id)}>{contractor.name}</option>
          {/each}
        </select>
      </label>

      <label class="text-xs text-neutral-500 xl:col-span-2">
        Search
        <input
          bind:value={searchInput}
          type="search"
          placeholder="Search contractor, trade, profile..."
          class="mt-1 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
        />
      </label>

      <div class="flex items-end gap-2">
        <button
          onclick={applyFilters}
          class="flex-1 rounded-lg bg-neutral-900 px-3 py-2 text-sm font-medium text-white hover:bg-neutral-800"
        >
          Apply
        </button>
        <button
          onclick={clearFilters}
          class="rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
        >
          Reset
        </button>
      </div>
    </div>
  </div>

  <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
    <div class="rounded-xl border border-red-200 bg-red-100 p-4">
      <p class="text-[10px] font-semibold uppercase tracking-wider text-red-900">Profiles</p>
      <p class="mt-1 text-xl font-bold text-red-950 tabular-nums">{totalCount}</p>
    </div>
    <div class="rounded-xl border border-yellow-200 bg-yellow-100 p-4">
      <p class="text-[10px] font-semibold uppercase tracking-wider text-yellow-900">Contract Value</p>
      <p class="mt-1 text-xl font-bold text-yellow-950 tabular-nums">{currency.formatCompact(totalContractValue)}</p>
    </div>
    <div class="rounded-xl border border-green-200 bg-green-100 p-4">
      <p class="text-[10px] font-semibold uppercase tracking-wider text-green-900">Avg Performance</p>
      <p class="mt-1 text-xl font-bold text-green-950 tabular-nums">{averageRating.toFixed(2)} / 5.00</p>
    </div>
    <div class="rounded-xl border border-blue-200 bg-blue-100 p-4">
      <p class="text-[10px] font-semibold uppercase tracking-wider text-blue-900">Assigned + Received</p>
      <p class="mt-1 text-xl font-bold text-blue-950 tabular-nums">{totalAssignedWorkPackages + totalReceivedItems}</p>
    </div>
  </div>

  <section class="rounded-xl border border-neutral-200 bg-white p-5">
    <div class="flex items-center justify-between">
      <h3 class="text-sm font-semibold uppercase tracking-wider text-neutral-900">Contractor Register</h3>
      <p class="text-xs text-neutral-500">
        {startItem}-{endItem} of {totalCount}
      </p>
    </div>

    {#if loading}
      <div class="flex items-center justify-center py-16">
        <div class="inline-block h-6 w-6 animate-spin rounded-full border-2 border-neutral-200 border-t-neutral-900"></div>
      </div>
    {:else if profiles.length === 0}
      <p class="mt-4 rounded-lg border border-dashed border-neutral-300 bg-neutral-50 px-4 py-8 text-center text-sm text-neutral-500">
        No contractor profiles found for the selected filters.
      </p>
    {:else}
      <div class="mt-4 overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-neutral-100 bg-neutral-50/80">
              <th class="w-8 px-2 py-2.5"></th>
              <th class="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Contractor</th>
              <th class="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Project</th>
              <th class="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Trade</th>
              <th class="px-4 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Contract Value</th>
              <th class="px-4 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Rating</th>
              <th class="px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Updated</th>
              <th class="px-4 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-neutral-500">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-neutral-100">
            {#each profiles as profile}
              <tr class="group">
                <td class="px-2 py-3 align-top">
                  <button
                    onclick={() => toggleRow(profile.id)}
                    class="rounded p-0.5 text-neutral-400 hover:text-neutral-700 transition-transform"
                    aria-label={expandedRows.has(profile.id) ? "Collapse" : "Expand"}
                  >
                    <svg class="w-4 h-4 transition-transform {expandedRows.has(profile.id) ? 'rotate-90' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="m9 5 7 7-7 7" />
                    </svg>
                  </button>
                </td>
                <td class="px-4 py-3 align-top">
                  <button onclick={() => openDrawer(profile)} class="text-left hover:underline">
                    <p class="font-medium text-neutral-900">{profile.contractor_name}</p>
                    <p class="text-xs text-neutral-500">{profile.company_snapshot.category}</p>
                  </button>
                </td>
                <td class="px-4 py-3 align-top text-neutral-700">{profile.project_name}</td>
                <td class="px-4 py-3 align-top text-neutral-700">{profile.trade_specialization || "--"}</td>
                <td class="px-4 py-3 align-top text-right tabular-nums text-neutral-800">
                  {currency.formatCompact(Number(profile.contract_value || 0))}
                </td>
                <td class="px-4 py-3 align-top text-right tabular-nums text-neutral-800">
                  {Number(profile.performance_rating || 0).toFixed(2)}
                </td>
                <td class="px-4 py-3 align-top text-neutral-600">{formatDate(profile.updated_at)}</td>
                <td class="px-4 py-3 align-top">
                  <div class="flex justify-end gap-2">
                    <button
                      class="rounded-md border border-neutral-200 bg-white px-2.5 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50"
                      onclick={() => openEditModal(profile)}
                    >
                      Edit
                    </button>
                    <button
                      class="rounded-md border border-rose-200 bg-rose-50 px-2.5 py-1.5 text-xs font-medium text-rose-700 hover:bg-rose-100 disabled:opacity-60"
                      disabled={deletingProfileId === profile.id}
                      onclick={() => deleteProfile(profile)}
                    >
                      {deletingProfileId === profile.id ? "..." : "Delete"}
                    </button>
                  </div>
                </td>
              </tr>

              <!-- Expanded row -->
              {#if expandedRows.has(profile.id)}
                <tr>
                  <td colspan="8" class="bg-neutral-50/60 px-6 py-4">
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <!-- Work Packages -->
                      <div>
                        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500 mb-2">Work Packages ({profile.work_package_records.length})</p>
                        {#if profile.work_package_records.length === 0}
                          <p class="text-xs text-neutral-400 italic">None assigned</p>
                        {:else}
                          <div class="space-y-1">
                            {#each profile.work_package_records as wp}
                              <div class="rounded-md border border-neutral-200 bg-white px-3 py-2">
                                <p class="text-xs font-medium text-neutral-800">{wp.package_id ?? "WP"} — {wp.name}</p>
                                <p class="text-[11px] text-neutral-500">Budget: {currency.formatCompact(Number(wp.budget || 0))}{wp.start_date ? ` · ${formatDate(wp.start_date)}` : ""}{wp.end_date ? ` – ${formatDate(wp.end_date)}` : ""}</p>
                              </div>
                            {/each}
                          </div>
                        {/if}
                      </div>

                      <!-- RFIs -->
                      <div>
                        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500 mb-2">RFIs ({profile.rfi_records.length})</p>
                        {#if profile.rfi_records.length === 0}
                          <p class="text-xs text-neutral-400 italic">None received</p>
                        {:else}
                          <div class="space-y-1">
                            {#each profile.rfi_records as rfi}
                              <div class="rounded-md border border-neutral-200 bg-white px-3 py-2">
                                <p class="text-xs font-medium text-neutral-800">{rfi.title}</p>
                                <p class="text-[11px] text-neutral-500">{formatDate(rfi.issue_date)} · {rfi.severity} · {inspectionStatusLabel(rfi.status)}</p>
                              </div>
                            {/each}
                          </div>
                        {/if}
                      </div>

                      <!-- Inspections -->
                      <div>
                        <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500 mb-2">Inspections ({profile.inspection_result_records.length})</p>
                        {#if profile.inspection_result_records.length === 0}
                          <p class="text-xs text-neutral-400 italic">None received</p>
                        {:else}
                          <div class="space-y-1">
                            {#each profile.inspection_result_records as insp}
                              <div class="rounded-md border border-neutral-200 bg-white px-3 py-2">
                                <p class="text-xs font-medium text-neutral-800">{insp.inspection_number}</p>
                                <p class="text-[11px] text-neutral-500">{formatDate(insp.inspected_on)} · {inspectionStatusLabel(insp.status)}{insp.overall_score ? ` · Score: ${insp.overall_score}` : ""}</p>
                              </div>
                            {/each}
                          </div>
                        {/if}
                      </div>

                      <!-- Site Instructions -->
                      {#if profile.received_items.site_instructions.count > 0}
                        <div class="md:col-span-3">
                          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-500 mb-2">Site Instructions ({profile.received_items.site_instructions.count})</p>
                          <div class="rounded-md border border-neutral-200 bg-white px-3 py-2 space-y-1">
                            {#each profile.received_items.site_instructions.items as si}
                              <p class="text-xs text-neutral-700">{si}</p>
                            {/each}
                          </div>
                        </div>
                      {/if}
                    </div>
                  </td>
                </tr>
              {/if}
            {/each}
          </tbody>
        </table>
      </div>
    {/if}

    <div class="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-neutral-100 pt-4">
      <p class="text-xs text-neutral-500">Page {currentPage} of {totalPages}</p>
      <div class="flex items-center gap-2">
        <button
          class="rounded-md border border-neutral-200 bg-white px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50 disabled:opacity-50"
          disabled={currentPage <= 1 || loading}
          onclick={() => fetchProfiles(currentPage - 1)}
        >
          Previous
        </button>
        <button
          class="rounded-md border border-neutral-200 bg-white px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50 disabled:opacity-50"
          disabled={currentPage >= totalPages || loading}
          onclick={() => fetchProfiles(currentPage + 1)}
        >
          Next
        </button>
      </div>
    </div>
  </section>
</div>

{#if showModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
    <div class="max-h-[92vh] w-full max-w-5xl overflow-y-auto rounded-2xl border border-neutral-200 bg-white p-6 shadow-2xl">
      <div class="flex items-start justify-between gap-3">
        <div>
          <h2 class="text-lg font-semibold text-neutral-900">
            {editingProfile ? "Edit Contractor Profile" : "New Contractor Profile"}
          </h2>
          <p class="mt-1 text-sm text-neutral-500">Company profile, work packages, and received records.</p>
        </div>
        <button
          class="rounded-md border border-neutral-200 bg-white px-3 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50"
          onclick={closeModal}
        >
          Close
        </button>
      </div>

      <div class="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
        <label class="text-xs text-neutral-500">
          Project *
          <select
            value={formState.project_id}
            onchange={(event) => onFormProjectChange((event.currentTarget as HTMLSelectElement).value)}
            class="mt-1 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
          >
            <option value="">Select project</option>
            {#each setupOptions.projects as project}
              <option value={String(project.id)}>{project.name}</option>
            {/each}
          </select>
        </label>

        <label class="text-xs text-neutral-500">
          Contractor *
          <select
            bind:value={formState.contractor_id}
            class="mt-1 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
          >
            <option value="">Select contractor</option>
            {#each setupOptions.contractors as contractor}
              <option value={String(contractor.id)}>{contractor.name}</option>
            {/each}
          </select>
        </label>

        <label class="text-xs text-neutral-500 md:col-span-2">
          Company profile
          <textarea
            bind:value={formState.company_profile}
            rows={2}
            placeholder="Company profile for this project..."
            class="mt-1 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
          ></textarea>
        </label>

        <label class="text-xs text-neutral-500">
          Trade specialization
          <input
            bind:value={formState.trade_specialization}
            type="text"
            placeholder="e.g. Structural concrete"
            class="mt-1 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
          />
        </label>

        <label class="text-xs text-neutral-500">
          Contract value
          <input
            bind:value={formState.contract_value}
            type="number"
            min="0"
            step="0.01"
            class="mt-1 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
          />
        </label>

        <label class="text-xs text-neutral-500">
          Performance rating (0-5)
          <input
            bind:value={formState.performance_rating}
            type="number"
            min="0"
            max="5"
            step="0.01"
            class="mt-1 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
          />
        </label>

        <label class="text-xs text-neutral-500 md:col-span-2">
          Insurance
          <textarea
            bind:value={formState.insurance}
            rows={2}
            placeholder="Insurance details..."
            class="mt-1 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
          ></textarea>
        </label>

        <label class="text-xs text-neutral-500 md:col-span-2">
          Licenses
          <textarea
            bind:value={formState.licenses}
            rows={2}
            placeholder="Licenses and certificates..."
            class="mt-1 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
          ></textarea>
        </label>

        <label class="text-xs text-neutral-500 md:col-span-2">
          Payment history
          <textarea
            bind:value={formState.payment_history}
            rows={2}
            placeholder="Payment history details..."
            class="mt-1 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
          ></textarea>
        </label>

        <label class="text-xs text-neutral-500">
          Safety record
          <textarea
            bind:value={formState.safety_record}
            rows={2}
            placeholder="Safety record summary..."
            class="mt-1 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
          ></textarea>
        </label>

        <label class="text-xs text-neutral-500">
          Quality record
          <textarea
            bind:value={formState.quality_record}
            rows={2}
            placeholder="Quality record summary..."
            class="mt-1 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
          ></textarea>
        </label>

        <label class="text-xs text-neutral-500 md:col-span-2">
          Site instructions (one per line)
          <textarea
            bind:value={formState.site_instructions}
            rows={3}
            placeholder="Issue instructions line-by-line..."
            class="mt-1 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
          ></textarea>
        </label>

        <label class="text-xs text-neutral-500">
          Work packages assigned
          <select
            multiple
            class="mt-1 h-36 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
            onchange={(event) => {
              formState = { ...formState, work_packages: parseSelectedNumbers(event) };
            }}
          >
            {#each formWorkPackageOptions as workPackage}
              <option
                value={String(workPackage.id)}
                selected={formState.work_packages.includes(workPackage.id)}
              >
                {(workPackage.package_id ?? "WP")} - {workPackage.name}
              </option>
            {/each}
          </select>
        </label>

        <label class="text-xs text-neutral-500">
          RFIs received
          <select
            multiple
            class="mt-1 h-36 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
            onchange={(event) => {
              formState = { ...formState, rfis: parseSelectedNumbers(event) };
            }}
          >
            {#each formRfiOptions as rfi}
              <option value={String(rfi.id)} selected={formState.rfis.includes(rfi.id)}>
                {formatDate(rfi.issue_date)} - {rfi.title}
              </option>
            {/each}
          </select>
        </label>

        <label class="text-xs text-neutral-500 md:col-span-2">
          Inspection results received
          <select
            multiple
            class="mt-1 h-36 w-full rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-900"
            onchange={(event) => {
              formState = { ...formState, inspection_results: parseSelectedNumbers(event) };
            }}
          >
            {#each formInspectionOptions as inspection}
              <option
                value={String(inspection.id)}
                selected={formState.inspection_results.includes(inspection.id)}
              >
                {inspection.inspection_number} - {inspectionStatusLabel(inspection.status)}
              </option>
            {/each}
          </select>
        </label>
      </div>

      <div class="mt-5 flex items-center justify-end gap-2 border-t border-neutral-100 pt-4">
        <button
          class="rounded-lg border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
          onclick={closeModal}
          disabled={saving}
        >
          Cancel
        </button>
        {#if isDev}
          <button type="button" onclick={devFillContractor} class="rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600">Dev Fill</button>
        {/if}
        <button
          class="rounded-lg bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 disabled:opacity-60"
          onclick={saveProfile}
          disabled={saving}
        >
          {saving ? "Saving..." : editingProfile ? "Save Changes" : "Create Profile"}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- Detail drawer -->
{#if drawerProfile}
  {@const p = drawerProfile}
  {@const snap = p.company_snapshot}
  {@const rating = Number(p.performance_rating || 0)}
  {@const ratingColor = rating >= 4 ? "text-emerald-600" : rating >= 3 ? "text-amber-600" : "text-red-600"}
  {@const complianceColor = snap.compliance_status === "compliant" ? "bg-emerald-100 text-emerald-800" : snap.compliance_status === "pending_review" ? "bg-amber-100 text-amber-800" : "bg-red-100 text-red-800"}
  <div class="fixed inset-0 z-50 flex justify-end">
    <button class="absolute inset-0 bg-black/20" onclick={closeDrawer} aria-label="Close drawer"></button>
    <div class="relative z-10 flex h-full w-full max-w-xl flex-col bg-white shadow-2xl">
      <!-- Header -->
      <div class="bg-linear-to-br from-neutral-900 to-neutral-800 px-6 py-5">
        <div class="flex items-start justify-between">
          <div>
            <h2 class="text-lg font-semibold text-white">{p.contractor_name}</h2>
            <p class="mt-0.5 text-sm text-neutral-400">{p.project_name}</p>
            <div class="mt-2 flex items-center gap-2">
              <span class="inline-flex items-center rounded-full bg-white/10 px-2.5 py-0.5 text-[11px] font-medium text-neutral-300">{snap.category}</span>
              <span class="inline-flex items-center rounded-full {complianceColor} px-2.5 py-0.5 text-[11px] font-medium">{inspectionStatusLabel(snap.compliance_status)}</span>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <button
              class="rounded-md border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-medium text-white hover:bg-white/20"
              onclick={() => { closeDrawer(); openEditModal(p); }}
            >
              Edit
            </button>
            <button class="rounded-md p-1.5 text-neutral-400 hover:text-white" onclick={closeDrawer} aria-label="Close">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12"/></svg>
            </button>
          </div>
        </div>
      </div>

      <!-- Key figures strip -->
      <div class="grid grid-cols-3 divide-x divide-neutral-100 border-b border-neutral-100">
        <div class="px-4 py-3 text-center">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Contract Value</p>
          <p class="mt-0.5 text-base font-bold tabular-nums text-blue-700">{currency.formatCompact(Number(p.contract_value || 0))}</p>
        </div>
        <div class="px-4 py-3 text-center">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Rating</p>
          <p class="mt-0.5 text-base font-bold tabular-nums {ratingColor}">{rating.toFixed(1)} / 5.0</p>
        </div>
        <div class="px-4 py-3 text-center">
          <p class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400">Work Pkgs</p>
          <p class="mt-0.5 text-base font-bold tabular-nums text-violet-700">{p.work_package_records.length}</p>
        </div>
      </div>

      <!-- Scrollable body -->
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-6">
        <!-- Snapshot -->
        <section>
          <h3 class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-3">Company Snapshot</h3>
          <div class="grid grid-cols-2 gap-3 rounded-xl border border-neutral-100 bg-neutral-50/50 p-4">
            <div>
              <p class="text-[11px] text-neutral-500">Contact Person</p>
              <p class="text-sm text-neutral-900">{snap.contact_person || "--"}</p>
            </div>
            <div>
              <p class="text-[11px] text-neutral-500">Email</p>
              <p class="text-sm text-neutral-900">{snap.email || "--"}</p>
            </div>
            <div>
              <p class="text-[11px] text-neutral-500">Phone</p>
              <p class="text-sm text-neutral-900">{snap.phone || "--"}</p>
            </div>
            <div>
              <p class="text-[11px] text-neutral-500">Address</p>
              <p class="text-sm text-neutral-900">{snap.address || "--"}</p>
            </div>
            <div>
              <p class="text-[11px] text-neutral-500">Trade</p>
              <p class="text-sm text-neutral-900">{p.trade_specialization || "--"}</p>
            </div>
            <div>
              <p class="text-[11px] text-neutral-500">Updated</p>
              <p class="text-sm text-neutral-900">{formatDate(p.updated_at)}</p>
            </div>
          </div>
        </section>

        <!-- Company profile -->
        {#if p.company_profile}
          <section>
            <h3 class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-2">Company Profile</h3>
            <div class="rounded-xl border-l-4 border-blue-400 bg-blue-50/40 px-4 py-3">
              <p class="text-sm text-neutral-700 whitespace-pre-line">{p.company_profile}</p>
            </div>
          </section>
        {/if}

        <!-- Insurance & Licenses -->
        <section class="grid grid-cols-1 md:grid-cols-2 gap-3">
          {#if p.insurance}
            <div class="rounded-xl border border-emerald-200 bg-emerald-50/40 p-4">
              <h3 class="text-[10px] font-semibold uppercase tracking-wider text-emerald-700 mb-2">Insurance</h3>
              <p class="text-xs text-neutral-700 whitespace-pre-line">{p.insurance}</p>
            </div>
          {/if}
          {#if p.licenses}
            <div class="rounded-xl border border-violet-200 bg-violet-50/40 p-4">
              <h3 class="text-[10px] font-semibold uppercase tracking-wider text-violet-700 mb-2">Licenses</h3>
              <p class="text-xs text-neutral-700 whitespace-pre-line">{p.licenses}</p>
            </div>
          {/if}
        </section>

        <!-- Records: Safety, Quality, Payment -->
        <section class="grid grid-cols-1 md:grid-cols-3 gap-3">
          {#if p.safety_record}
            <div class="rounded-xl border border-amber-200 bg-amber-50/40 p-3">
              <h3 class="text-[10px] font-semibold uppercase tracking-wider text-amber-700 mb-2">Safety</h3>
              <p class="text-xs text-neutral-700 whitespace-pre-line">{p.safety_record}</p>
            </div>
          {/if}
          {#if p.quality_record}
            <div class="rounded-xl border border-sky-200 bg-sky-50/40 p-3">
              <h3 class="text-[10px] font-semibold uppercase tracking-wider text-sky-700 mb-2">Quality</h3>
              <p class="text-xs text-neutral-700 whitespace-pre-line">{p.quality_record}</p>
            </div>
          {/if}
          {#if p.payment_history}
            <div class="rounded-xl border border-teal-200 bg-teal-50/40 p-3">
              <h3 class="text-[10px] font-semibold uppercase tracking-wider text-teal-700 mb-2">Payment History</h3>
              <p class="text-xs text-neutral-700 whitespace-pre-line">{p.payment_history}</p>
            </div>
          {/if}
        </section>

        <!-- Work packages -->
        <section>
          <h3 class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-2">Work Packages ({p.work_package_records.length})</h3>
          {#if p.work_package_records.length === 0}
            <p class="text-xs text-neutral-400 italic">None assigned</p>
          {:else}
            <div class="space-y-1.5">
              {#each p.work_package_records as wp}
                <div class="rounded-lg border border-indigo-100 bg-indigo-50/30 px-3 py-2">
                  <p class="text-xs font-medium text-indigo-900">{wp.package_id ?? "WP"} — {wp.name}</p>
                  <p class="text-[11px] text-indigo-600/70">Budget: {currency.formatCompact(Number(wp.budget || 0))}{wp.start_date ? ` · ${formatDate(wp.start_date)}` : ""}{wp.end_date ? ` – ${formatDate(wp.end_date)}` : ""}</p>
                </div>
              {/each}
            </div>
          {/if}
        </section>

        <!-- RFIs -->
        <section>
          <h3 class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-2">RFIs ({p.rfi_records.length})</h3>
          {#if p.rfi_records.length === 0}
            <p class="text-xs text-neutral-400 italic">None received</p>
          {:else}
            <div class="space-y-1.5">
              {#each p.rfi_records as rfi}
                <div class="rounded-lg border border-orange-100 bg-orange-50/30 px-3 py-2">
                  <p class="text-xs font-medium text-orange-900">{rfi.title}</p>
                  <p class="text-[11px] text-orange-600/70">{formatDate(rfi.issue_date)} · {rfi.severity} · {inspectionStatusLabel(rfi.status)}</p>
                </div>
              {/each}
            </div>
          {/if}
        </section>

        <!-- Inspections -->
        <section>
          <h3 class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-2">Inspections ({p.inspection_result_records.length})</h3>
          {#if p.inspection_result_records.length === 0}
            <p class="text-xs text-neutral-400 italic">None received</p>
          {:else}
            <div class="space-y-1.5">
              {#each p.inspection_result_records as insp}
                {@const score = Number(insp.overall_score || 0)}
                {@const scoreColor = score >= 80 ? "text-emerald-700" : score >= 50 ? "text-amber-700" : "text-red-700"}
                <div class="rounded-lg border border-cyan-100 bg-cyan-50/30 px-3 py-2">
                  <div class="flex items-center justify-between">
                    <p class="text-xs font-medium text-cyan-900">{insp.inspection_number}</p>
                    {#if insp.overall_score}
                      <span class="text-xs font-bold tabular-nums {scoreColor}">{insp.overall_score}%</span>
                    {/if}
                  </div>
                  <p class="text-[11px] text-cyan-600/70">{formatDate(insp.inspected_on)} · {inspectionStatusLabel(insp.status)}</p>
                </div>
              {/each}
            </div>
          {/if}
        </section>

        <!-- Site Instructions -->
        {#if p.received_items.site_instructions.count > 0}
          <section>
            <h3 class="text-[10px] font-semibold uppercase tracking-wider text-neutral-400 mb-2">Site Instructions ({p.received_items.site_instructions.count})</h3>
            <div class="rounded-xl border-l-4 border-neutral-400 bg-neutral-50/60 px-4 py-3 space-y-1">
              {#each p.received_items.site_instructions.items as si}
                <p class="text-xs text-neutral-700">{si}</p>
              {/each}
            </div>
          </section>
        {/if}
      </div>
    </div>
  </div>
{/if}

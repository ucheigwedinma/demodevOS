<script lang="ts">
  import { api, ApiError } from "$lib/api";
  import { toast } from "$lib/stores/toast.svelte";
  import type {
    HRTeam,
    HRTeamAutomationTriggers,
    HRTeamListItem,
    HRTeamMemberPickerEmployee,
    HRTeamMemberPickerPayload,
    HRTeamMemberRosterItem,
    HRTeamOperationalPerformance,
    HRTeamType,
    PaginatedResponse,
  } from "$lib/types";

  let teams = $state<HRTeamListItem[]>([]);
  let totalCount = $state(0);
  let loading = $state(true);
  let currentPage = $state(1);
  const pageSize = 25;

  let searchQuery = $state("");
  let filterTeamType = $state("");
  let filterActive = $state("");

  // Slide-over
  let showSlideOver = $state(false);
  let saving = $state(false);
  let fieldErrors = $state<Record<string, string[]>>({});
  let editingId = $state<number | null>(null);
  let expandedTeamId = $state<number | null>(null);
  let expandedTeamLoading = $state(false);
  let expandedTeamRoster = $state<HRTeamMemberRosterItem[]>([]);
  let expandedTeamPerformance = $state<HRTeamOperationalPerformance | null>(null);
  let expandedTeamAutomation = $state<HRTeamAutomationTriggers | null>(null);
  let memberPickerLoading = $state(false);
  let memberPickerSaving = $state(false);
  let memberPickerSearch = $state("");
  let memberPicker = $state<HRTeamMemberPickerPayload | null>(null);
  let draggingMemberUserId = $state<number | null>(null);
  let form = $state({
    name: "",
    code: "",
    department: "" as string,
    team_type: "permanent" as HRTeamType,
    lead: "" as string,
    description: "",
    is_active: true,
    sort_order: 0,
  });

  // Department options for the form
  let departmentOptions = $state<
    { id: number; name: string; parent_business_unit_name?: string }[]
  >([]);
  let leadOptions = $state<{ id: number; full_name: string; employee_id?: string }[]>([]);

  let totalPages = $derived(Math.max(1, Math.ceil(totalCount / pageSize)));
  let isEditing = $derived(editingId !== null);

  async function fetchTeams() {
    loading = true;
    try {
      const params: Record<string, string> = { page: String(currentPage), page_size: String(pageSize) };
      if (searchQuery) params.search = searchQuery;
      if (filterTeamType) params.team_type = filterTeamType;
      if (filterActive) params.is_active = filterActive;
      const res = await api.get<PaginatedResponse<HRTeamListItem>>("/hr/teams/", params);
      teams = res.results;
      totalCount = res.count;
    } catch {
      teams = [];
      totalCount = 0;
    } finally {
      loading = false;
    }
  }

  async function fetchDepartments() {
    try {
      const res = await api.get<{
        results: { id: number; name: string; parent_business_unit_name?: string }[];
      }>("/settings/departments/", { page_size: "200" });
      departmentOptions = res.results;
    } catch {
      departmentOptions = [];
    }
  }

  async function fetchLeadOptions() {
    try {
      const res = await api.get<{
        results: { id: number; full_name: string; employee_id: string }[];
      }>("/iam/users/", { page_size: "200" });
      leadOptions = res.results;
    } catch {
      leadOptions = [];
    }
  }

  function resetForm() {
    form = {
      name: "",
      code: "",
      department: "",
      team_type: "permanent",
      lead: "",
      description: "",
      is_active: true,
      sort_order: 0,
    };
    fieldErrors = {};
    editingId = null;
  }

  function openCreate() {
    resetForm();
    fetchDepartments();
    fetchLeadOptions();
    showSlideOver = true;
  }

  async function openEdit(team: HRTeamListItem) {
    resetForm();
    editingId = team.id;
    form.name = team.name;
    form.code = team.code;
    form.department = String(team.department);
    form.team_type = team.team_type;
    form.lead = team.lead ? String(team.lead) : "";
    form.is_active = team.is_active;
    form.sort_order = team.sort_order;
    await Promise.all([fetchDepartments(), fetchLeadOptions()]);
    // Fetch detail for description
    try {
      const detail = await api.get<{ description: string; team_type: HRTeamType }>(
        `/hr/teams/${team.id}/`,
      );
      form.description = detail.description;
      form.team_type = detail.team_type;
    } catch { /* ignore */ }
    showSlideOver = true;
  }

  async function handleSave() {
    saving = true;
    fieldErrors = {};
    try {
      const payload: Record<string, unknown> = {
        name: form.name,
        code: form.code || undefined,
        department: form.department ? Number(form.department) : undefined,
        team_type: form.team_type,
        description: form.description,
        is_active: form.is_active,
        sort_order: form.sort_order,
      };
      if (form.lead) payload.lead = Number(form.lead);

      if (isEditing) {
        await api.patch(`/hr/teams/${editingId}/`, payload);
        toast.success("Team updated");
      } else {
        await api.post("/hr/teams/", payload);
        toast.success("Team created");
      }
      showSlideOver = false;
      resetForm();
      fetchTeams();
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        fieldErrors = err.fieldErrors;
      } else {
        toast.error("Failed to save team");
      }
    } finally {
      saving = false;
    }
  }

  let debounceTimer: ReturnType<typeof setTimeout>;
  function handleSearch(value: string) {
    searchQuery = value;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => { currentPage = 1; fetchTeams(); }, 300);
  }

  function goToPage(page: number) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    fetchTeams();
  }

  function fieldError(field: string): string {
    return fieldErrors[field]?.[0] ?? "";
  }

  function selectedDepartmentOption() {
    return departmentOptions.find((dept) => String(dept.id) === form.department) ?? null;
  }

  function availabilityPillClass(status: string) {
    if (status === "on_leave") return "bg-amber-100 text-amber-800";
    if (status === "reassigned") return "bg-blue-100 text-blue-800";
    return "bg-emerald-100 text-emerald-800";
  }

  function availabilityDotClass(status: string) {
    if (status === "on_leave") return "bg-amber-500";
    if (status === "reassigned") return "bg-blue-500";
    return "bg-emerald-500";
  }

  function workloadHeatClass(heatLevel: string) {
    if (heatLevel === "critical") return "text-red-700";
    if (heatLevel === "high") return "text-amber-700";
    if (heatLevel === "medium") return "text-blue-700";
    return "text-emerald-700";
  }

  function workloadBarClass(heatLevel: string) {
    if (heatLevel === "critical") return "bg-red-500";
    if (heatLevel === "high") return "bg-amber-500";
    if (heatLevel === "medium") return "bg-blue-500";
    return "bg-emerald-500";
  }

  function milestoneHealthClass(health: string) {
    if (health === "delayed") return "bg-red-100 text-red-700";
    if (health === "at_risk") return "bg-amber-100 text-amber-700";
    if (health === "on_track") return "bg-emerald-100 text-emerald-700";
    return "bg-neutral-100 text-neutral-600";
  }

  function triggerStatusPillClass(status: string) {
    if (status === "triggered") return "bg-emerald-100 text-emerald-700";
    if (status === "not_applicable") return "bg-neutral-100 text-neutral-600";
    return "bg-amber-100 text-amber-700";
  }

  function triggerStatusLabel(status: string) {
    if (status === "triggered") return "Triggered";
    if (status === "not_applicable") return "N/A";
    return "Pending";
  }

  function initials(name: string) {
    const trimmed = (name || "").trim();
    if (!trimmed) return "??";
    return trimmed
      .split(/\s+/)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase() ?? "")
      .join("") || "??";
  }

  function statusLabel(status: string) {
    if (status === "active") return "Active";
    if (status === "on_leave") return "On Leave";
    if (status === "probation") return "Probation";
    if (status === "notice_period") return "Notice";
    if (status === "terminated") return "Terminated";
    if (status === "resigned") return "Resigned";
    return status;
  }

  function filteredMemberPickerAvailable() {
    if (!memberPicker) return [];
    const q = memberPickerSearch.trim().toLowerCase();
    if (!q) return memberPicker.available;
    return memberPicker.available.filter((item) =>
      `${item.full_name} ${item.employee_id} ${item.job_title}`.toLowerCase().includes(q),
    );
  }

  function sortMemberPickerEntries(items: HRTeamMemberPickerEmployee[]) {
    return [...items].sort((a, b) => (a.full_name || "").localeCompare(b.full_name || ""));
  }

  async function fetchMemberPicker(teamId: number, search = "") {
    memberPickerLoading = true;
    try {
      const params = search ? { search } : undefined;
      memberPicker = await api.get<HRTeamMemberPickerPayload>(
        `/hr/teams/${teamId}/member-picker/`,
        params,
      );
    } catch {
      memberPicker = null;
      toast.error("Member picker failed", "Could not load team members for drag-and-drop.");
    } finally {
      memberPickerLoading = false;
    }
  }

  async function syncMemberPickerSelection() {
    if (!expandedTeamId || !memberPicker) return;
    memberPickerSaving = true;
    try {
      memberPicker = await api.post<HRTeamMemberPickerPayload>(
        `/hr/teams/${expandedTeamId}/sync-member-picker/`,
        {
          user_ids: memberPicker.assigned.map((item) => item.user_id),
        },
      );
      const detail = await api.get<HRTeam>(`/hr/teams/${expandedTeamId}/`);
      expandedTeamRoster = detail.member_roster ?? [];
      expandedTeamPerformance = detail.operational_performance ?? null;
      expandedTeamAutomation = detail.automation_triggers ?? null;
      toast.success("Team members updated");
    } catch (err) {
      if (err instanceof ApiError && err.message) {
        toast.error("Update blocked", err.message);
      } else {
        toast.error("Update failed", "Could not sync team membership.");
      }
      await fetchMemberPicker(expandedTeamId);
    } finally {
      memberPickerSaving = false;
    }
  }

  async function moveMemberPickerUser(userId: number, targetList: "assigned" | "available") {
    if (!memberPicker) return;
    const assigned = [...memberPicker.assigned];
    const available = [...memberPicker.available];

    const assignedIndex = assigned.findIndex((item) => item.user_id === userId);
    const availableIndex = available.findIndex((item) => item.user_id === userId);
    const currentList = assignedIndex >= 0 ? "assigned" : (availableIndex >= 0 ? "available" : null);
    if (!currentList || currentList === targetList) return;

    const item =
      currentList === "assigned"
        ? assigned[assignedIndex]
        : available[availableIndex];
    if (!item) return;
    if (targetList === "available" && item.is_locked) {
      toast.error("Locked member", "This member is tied to a role assignment and cannot be removed here.");
      return;
    }

    if (currentList === "assigned") {
      assigned.splice(assignedIndex, 1);
      available.push(item);
    } else {
      available.splice(availableIndex, 1);
      assigned.push(item);
    }

    memberPicker = {
      ...memberPicker,
      assigned: sortMemberPickerEntries(assigned),
      available: sortMemberPickerEntries(available),
    };
    await syncMemberPickerSelection();
  }

  async function handleMemberDrop(targetList: "assigned" | "available") {
    if (!memberPicker || draggingMemberUserId === null) return;
    const movedUserId = draggingMemberUserId;
    draggingMemberUserId = null;
    await moveMemberPickerUser(movedUserId, targetList);
  }

  async function toggleRoster(team: HRTeamListItem) {
    if (expandedTeamId === team.id) {
      expandedTeamId = null;
      expandedTeamRoster = [];
      expandedTeamPerformance = null;
      expandedTeamAutomation = null;
      memberPicker = null;
      memberPickerSearch = "";
      draggingMemberUserId = null;
      memberPickerLoading = false;
      memberPickerSaving = false;
      expandedTeamLoading = false;
      return;
    }

    expandedTeamId = team.id;
    expandedTeamRoster = [];
    expandedTeamPerformance = null;
    expandedTeamAutomation = null;
    memberPicker = null;
    memberPickerSearch = "";
    draggingMemberUserId = null;
    memberPickerLoading = false;
    memberPickerSaving = false;
    expandedTeamLoading = true;
    try {
      const [detail, picker] = await Promise.all([
        api.get<HRTeam>(`/hr/teams/${team.id}/`),
        api.get<HRTeamMemberPickerPayload>(`/hr/teams/${team.id}/member-picker/`),
      ]);
      expandedTeamRoster = detail.member_roster ?? [];
      expandedTeamPerformance = detail.operational_performance ?? null;
      expandedTeamAutomation = detail.automation_triggers ?? null;
      memberPicker = picker;
    } catch {
      expandedTeamRoster = [];
      expandedTeamPerformance = null;
      expandedTeamAutomation = null;
      memberPicker = null;
      toast.error("Load failed", "Could not load team member roster.");
    } finally {
      expandedTeamLoading = false;
    }
  }

  // ── Dev fill ──
  const isDev = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);

  const TEAM_SAMPLES = [
    {
      name: "Structural Works",
      code: "TM-STR",
      team_type: "project_based" as HRTeamType,
      description: "On-site team responsible for reinforced concrete works, formwork, rebar fixing, concrete pours, and post-tension operations across all active project phases.",
      is_active: true,
      sort_order: 1,
    },
    {
      name: "Sales Operations",
      code: "TM-SALES",
      team_type: "project_based" as HRTeamType,
      description: "Handles off-plan sales pipeline management, broker coordination, show-unit tours, reservation agreements, and CRM data hygiene for all residential projects.",
      is_active: true,
      sort_order: 2,
    },
    {
      name: "Accounts Payable",
      code: "TM-AP",
      team_type: "permanent" as HRTeamType,
      description: "Processes vendor invoices, contractor interim payment certificates, retention releases, and reconciles supplier statements against purchase orders.",
      is_active: true,
      sort_order: 3,
    },
  ];

  let teamDevIdx = 0;

  function devFillTeam() {
    const sample = TEAM_SAMPLES[teamDevIdx % TEAM_SAMPLES.length];
    teamDevIdx++;
    form.name = sample.name;
    form.code = sample.code;
    form.team_type = sample.team_type;
    form.description = sample.description;
    form.is_active = sample.is_active;
    form.sort_order = sample.sort_order;
    form.department = departmentOptions.length > 0 ? String(departmentOptions[teamDevIdx % departmentOptions.length].id) : "";
    form.lead = "";
  }

  $effect(() => {
    fetchTeams();
  });
</script>

<div class="max-w-7xl mx-auto">
  <!-- Header -->
  <div class="flex items-center justify-between mb-8">
    <div>
      <h1 class="text-2xl font-bold text-neutral-900 tracking-tight">Teams</h1>
      <p class="mt-1 text-sm text-neutral-500">Agile delivery teams for HR and project operations</p>
    </div>
    <button
      onclick={openCreate}
      class="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 transition-colors"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" /></svg>
      Add Team
    </button>
  </div>

  <!-- Filters -->
  <div class="flex items-center gap-3 mb-6">
    <div class="relative flex-1 max-w-sm">
      <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
      <input
        type="text"
        placeholder="Search teams..."
        value={searchQuery}
        oninput={(e) => handleSearch(e.currentTarget.value)}
        class="w-full pl-9 pr-4 py-2 text-sm border border-neutral-200 rounded-lg bg-white placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-neutral-900 focus:border-transparent"
      />
    </div>
    <select
      value={filterTeamType}
      onchange={(e) => { filterTeamType = e.currentTarget.value; currentPage = 1; fetchTeams(); }}
      class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
    >
      <option value="">All Team Types</option>
      <option value="permanent">Permanent</option>
      <option value="project_based">Project-Based</option>
    </select>
    <select
      value={filterActive}
      onchange={(e) => { filterActive = e.currentTarget.value; currentPage = 1; fetchTeams(); }}
      class="px-3 py-2 text-sm border border-neutral-200 rounded-lg bg-white text-neutral-700 focus:outline-none focus:ring-2 focus:ring-neutral-900"
    >
      <option value="">All Status</option>
      <option value="true">Active</option>
      <option value="false">Inactive</option>
    </select>
  </div>

  <!-- Table -->
  {#if loading}
    <div class="flex items-center justify-center py-24">
      <div class="h-6 w-6 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div>
    </div>
  {:else if teams.length === 0}
    <div class="text-center py-24">
      <p class="text-sm text-neutral-500">{searchQuery || filterTeamType || filterActive ? "No teams match your filters" : "No teams created yet"}</p>
    </div>
  {:else}
    <div class="bg-white border border-neutral-200 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-neutral-200 bg-neutral-50/50">
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Team</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Code</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Functional Parent</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Team Type</th>
            <th class="text-left px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Lead</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Members</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Status</th>
            <th class="text-center px-5 py-3 font-medium text-neutral-500 text-xs uppercase tracking-wider">Member Roster</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-neutral-100">
          {#each teams as team}
            <tr class="hover:bg-neutral-50 transition-colors cursor-pointer" onclick={() => openEdit(team)}>
              <td class="px-5 py-3.5 font-medium text-neutral-900">{team.name}</td>
              <td class="px-5 py-3.5 font-mono text-xs text-neutral-500">{team.code || "\u2014"}</td>
              <td class="px-5 py-3.5">
                <a
                  href="/hr/departments"
                  onclick={(event) => event.stopPropagation()}
                  class="text-sm font-semibold text-neutral-800 hover:text-blue-700"
                >
                  {team.department_name}
                </a>
                <div class="text-xs text-neutral-500 mt-0.5">
                  <a
                    href="/hr/business-units"
                    onclick={(event) => event.stopPropagation()}
                    class="hover:text-blue-700"
                  >
                    {team.business_unit_name}
                  </a>
                </div>
              </td>
              <td class="px-5 py-3.5 text-neutral-600">{team.team_type_display}</td>
              <td class="px-5 py-3.5 text-neutral-600">{team.lead_name ?? "\u2014"}</td>
              <td class="px-5 py-3.5 text-center text-neutral-600">{team.member_count}</td>
              <td class="px-5 py-3.5 text-center">
                <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium {team.is_active ? 'bg-neutral-900 text-white' : 'bg-neutral-100 text-neutral-400'}">
                  {team.is_active ? "Active" : "Inactive"}
                </span>
              </td>
              <td class="px-5 py-3.5 text-center">
                <button
                  onclick={(event) => { event.stopPropagation(); toggleRoster(team); }}
                  class="inline-flex items-center gap-2 rounded-lg border border-neutral-200 px-3 py-1.5 text-xs font-semibold text-neutral-700 hover:border-neutral-300 hover:bg-neutral-100"
                >
                  {expandedTeamId === team.id ? "Hide" : "View"} Members
                </button>
              </td>
            </tr>
            {#if expandedTeamId === team.id}
              <tr>
                <td colspan="8" class="px-5 py-4 bg-neutral-50/70">
                  {#if expandedTeamLoading}
                    <div class="flex items-center justify-center py-8">
                      <div class="h-5 w-5 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div>
                    </div>
                  {:else}
                    <div class="space-y-4">
                      <section class="rounded-lg border border-neutral-200 bg-white p-4">
                        <div class="mb-3 flex flex-wrap items-center justify-between gap-3">
                          <div>
                            <h3 class="text-sm font-semibold text-neutral-900">Dynamic Member Picker</h3>
                            <p class="text-xs text-neutral-500">
                              Drag and drop employees between lists to update the team.
                            </p>
                          </div>
                          <div class="flex items-center gap-2">
                            <input
                              type="text"
                              placeholder="Search available..."
                              value={memberPickerSearch}
                              oninput={(event) => {
                                memberPickerSearch = event.currentTarget.value;
                              }}
                              class="w-48 rounded-lg border border-neutral-200 px-2.5 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-neutral-900"
                            />
                            {#if memberPickerSaving}
                              <span class="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-xs font-semibold text-blue-700">
                                Syncing...
                              </span>
                            {/if}
                          </div>
                        </div>

                        {#if memberPickerLoading}
                          <div class="flex items-center justify-center py-8">
                            <div class="h-5 w-5 border-2 border-neutral-300 border-t-neutral-900 rounded-full animate-spin"></div>
                          </div>
                        {:else if !memberPicker}
                          <p class="rounded-lg border border-dashed border-neutral-300 bg-neutral-50 px-4 py-4 text-sm text-neutral-500">
                            Member picker unavailable for this team.
                          </p>
                        {:else}
                          <div class="mb-2 flex flex-wrap items-center gap-2 text-xs text-neutral-600">
                            <span class="rounded-full bg-neutral-100 px-2 py-0.5">
                              Assigned: {memberPicker.assigned.length}
                            </span>
                            <span class="rounded-full bg-neutral-100 px-2 py-0.5">
                              Available: {memberPicker.available.length}
                            </span>
                            <span class="rounded-full bg-amber-100 px-2 py-0.5 text-amber-700">
                              Locked: {memberPicker.locked_assigned_count}
                            </span>
                          </div>
                          <div class="grid grid-cols-1 gap-3 lg:grid-cols-2">
                            <div
                              role="listbox"
                              tabindex="0"
                              aria-label="Assigned team members drop zone"
                              class="rounded-lg border border-neutral-200 bg-neutral-50 p-3"
                              ondragover={(event) => event.preventDefault()}
                              ondrop={async (event) => {
                                event.preventDefault();
                                await handleMemberDrop("assigned");
                              }}
                            >
                              <div class="mb-2 flex items-center justify-between">
                                <p class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Assigned Team Members</p>
                                <span class="text-[11px] text-neutral-500">Drop Here</span>
                              </div>
                              <div class="space-y-2">
                                {#if memberPicker.assigned.length === 0}
                                  <p class="rounded border border-dashed border-neutral-300 bg-white px-3 py-3 text-xs text-neutral-500">
                                    No assigned members yet.
                                  </p>
                                {:else}
                                  {#each memberPicker.assigned as member}
                                    <div
                                      role="option"
                                      aria-label="{member.full_name}"
                                      draggable={!member.is_locked}
                                      ondragstart={() => {
                                        if (member.is_locked) return;
                                        draggingMemberUserId = member.user_id;
                                      }}
                                      ondragend={() => {
                                        draggingMemberUserId = null;
                                      }}
                                      class="rounded-lg border border-neutral-200 bg-white px-3 py-2 {member.is_locked ? 'opacity-90' : 'cursor-grab'}"
                                    >
                                      <div class="flex items-start justify-between gap-2">
                                        <div class="min-w-0">
                                          <p class="truncate text-sm font-semibold text-neutral-900">{member.full_name}</p>
                                          <p class="truncate text-xs text-neutral-500">
                                            {member.employee_id || "\u2014"} · {member.job_title || "No title"}
                                          </p>
                                          <p class="text-[11px] text-neutral-500">{statusLabel(member.employment_status)}</p>
                                        </div>
                                        <div class="flex items-center gap-1">
                                          {#if member.is_locked}
                                            <span class="inline-flex rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-700">
                                              Locked
                                            </span>
                                          {:else}
                                            <button
                                              class="rounded border border-neutral-200 px-2 py-1 text-[11px] font-semibold text-neutral-700 hover:bg-neutral-100"
                                              onclick={async (event) => {
                                                event.stopPropagation();
                                                await moveMemberPickerUser(member.user_id, "available");
                                              }}
                                            >
                                              Remove
                                            </button>
                                          {/if}
                                        </div>
                                      </div>
                                    </div>
                                  {/each}
                                {/if}
                              </div>
                            </div>

                            <div
                              role="listbox"
                              tabindex="0"
                              aria-label="Available employees drop zone"
                              class="rounded-lg border border-neutral-200 bg-neutral-50 p-3"
                              ondragover={(event) => event.preventDefault()}
                              ondrop={async (event) => {
                                event.preventDefault();
                                await handleMemberDrop("available");
                              }}
                            >
                              <div class="mb-2 flex items-center justify-between">
                                <p class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Available Employees</p>
                                <span class="text-[11px] text-neutral-500">Drop Here</span>
                              </div>
                              <div class="space-y-2">
                                {#if filteredMemberPickerAvailable().length === 0}
                                  <p class="rounded border border-dashed border-neutral-300 bg-white px-3 py-3 text-xs text-neutral-500">
                                    No available employees for current filter.
                                  </p>
                                {:else}
                                  {#each filteredMemberPickerAvailable() as member}
                                    <div
                                      role="option"
                                      aria-label="{member.full_name}"
                                      draggable={true}
                                      ondragstart={() => {
                                        draggingMemberUserId = member.user_id;
                                      }}
                                      ondragend={() => {
                                        draggingMemberUserId = null;
                                      }}
                                      class="rounded-lg border border-neutral-200 bg-white px-3 py-2 cursor-grab"
                                    >
                                      <div class="flex items-start justify-between gap-2">
                                        <div class="min-w-0">
                                          <p class="truncate text-sm font-semibold text-neutral-900">{member.full_name}</p>
                                          <p class="truncate text-xs text-neutral-500">
                                            {member.employee_id || "\u2014"} · {member.job_title || "No title"}
                                          </p>
                                          <p class="text-[11px] text-neutral-500">{statusLabel(member.employment_status)}</p>
                                        </div>
                                        <button
                                          class="rounded border border-neutral-200 px-2 py-1 text-[11px] font-semibold text-neutral-700 hover:bg-neutral-100"
                                          onclick={async (event) => {
                                            event.stopPropagation();
                                            await moveMemberPickerUser(member.user_id, "assigned");
                                          }}
                                        >
                                          Add
                                        </button>
                                      </div>
                                    </div>
                                  {/each}
                                {/if}
                              </div>
                            </div>
                          </div>
                        {/if}
                      </section>

                      <section class="rounded-lg border border-neutral-200 bg-white p-4">
                        <div class="mb-3 flex items-center justify-between">
                          <h3 class="text-sm font-semibold text-neutral-900">Member Roster</h3>
                          <span class="text-xs text-neutral-500">{expandedTeamRoster.length} member{expandedTeamRoster.length === 1 ? "" : "s"}</span>
                        </div>
                        {#if expandedTeamRoster.length === 0}
                          <p class="rounded-lg border border-dashed border-neutral-300 bg-neutral-50 px-4 py-4 text-sm text-neutral-500">
                            No active members in this team yet.
                          </p>
                        {:else}
                          <div class="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
                            {#each expandedTeamRoster as member}
                              <article class="rounded-lg border border-neutral-200 bg-white p-4">
                                <div class="flex items-start gap-3">
                                  {#if member.profile_photo_url}
                                    <img src={member.profile_photo_url} alt={member.full_name} class="h-10 w-10 rounded-full object-cover border border-neutral-200" />
                                  {:else}
                                    <div class="flex h-10 w-10 items-center justify-center rounded-full bg-neutral-100 text-xs font-semibold text-neutral-700 border border-neutral-200">
                                      {initials(member.full_name)}
                                    </div>
                                  {/if}
                                  <div class="min-w-0 flex-1">
                                    <p class="truncate text-sm font-semibold text-neutral-900">{member.full_name}</p>
                                    <p class="truncate text-xs text-neutral-500">{member.role_title || "Team Member"}</p>
                                  </div>
                                  <span class="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold {availabilityPillClass(member.availability_status)}">
                                    <span class="h-1.5 w-1.5 rounded-full {availabilityDotClass(member.availability_status)}"></span>
                                    {member.availability_label}
                                  </span>
                                </div>
                                {#if member.role_titles.length > 1}
                                  <p class="mt-2 text-xs text-neutral-500">
                                    Roles: {member.role_titles.join(", ")}
                                  </p>
                                {/if}
                                {#if member.is_cross_functional}
                                  <p class="mt-2 inline-flex rounded-md bg-blue-50 px-2 py-1 text-xs font-medium text-blue-800">
                                    Home Department: {member.home_department_name}
                                  </p>
                                {/if}
                              </article>
                            {/each}
                          </div>
                        {/if}
                      </section>

                      {#if expandedTeamPerformance}
                        <section class="rounded-lg border border-neutral-200 bg-white p-4">
                          <h3 class="mb-3 text-sm font-semibold text-neutral-900">Operational Performance & Capacity</h3>
                          <div class="grid grid-cols-1 gap-3 lg:grid-cols-3">
                            <article class="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
                              <p class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Team Workload</p>
                              <p class="mt-1 text-xl font-bold {workloadHeatClass(expandedTeamPerformance.workload.heat_level)}">
                                {expandedTeamPerformance.workload.workload_percent.toFixed(1)}%
                              </p>
                              <p class="text-xs text-neutral-500">
                                {expandedTeamPerformance.workload.booked_hours.toFixed(1)}h booked / {expandedTeamPerformance.workload.capacity_hours.toFixed(1)}h capacity
                              </p>
                              <div class="mt-2 h-2 w-full rounded-full bg-neutral-200">
                                <div
                                  class="h-2 rounded-full {workloadBarClass(expandedTeamPerformance.workload.heat_level)}"
                                  style={`width: ${Math.min(100, expandedTeamPerformance.workload.workload_percent)}%`}
                                ></div>
                              </div>
                              <p class="mt-2 text-xs text-neutral-500">
                                {expandedTeamPerformance.workload.heat_label} load · {expandedTeamPerformance.workload.period_label}
                              </p>
                            </article>

                            <article class="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
                              <p class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Milestone Progress</p>
                              <div class="mt-1 flex items-center gap-2">
                                <span class="inline-flex rounded-full px-2 py-0.5 text-xs font-semibold {milestoneHealthClass(expandedTeamPerformance.milestone_progress.health)}">
                                  {expandedTeamPerformance.milestone_progress.health_label}
                                </span>
                                <span class="text-xs text-neutral-500">
                                  {expandedTeamPerformance.milestone_progress.completed_milestones}/{expandedTeamPerformance.milestone_progress.total_milestones} complete
                                </span>
                              </div>
                              <p class="mt-2 text-xs text-neutral-600">
                                Completion: {expandedTeamPerformance.milestone_progress.completion_percent.toFixed(1)}%
                              </p>
                              <p class="text-xs text-neutral-600">
                                On-time: {expandedTeamPerformance.milestone_progress.on_time_completion_percent.toFixed(1)}%
                              </p>
                              <p class="mt-1 text-xs text-neutral-500">
                                {expandedTeamPerformance.milestone_progress.overdue_milestones} overdue · {expandedTeamPerformance.milestone_progress.due_soon_milestones} due soon
                              </p>
                            </article>

                            <article class="rounded-lg border border-neutral-200 bg-neutral-50 p-3">
                              <p class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Active Projects</p>
                              <p class="mt-1 text-xl font-bold text-neutral-900">
                                {expandedTeamPerformance.active_project_links.length}
                              </p>
                              <p class="text-xs text-neutral-500">
                                Projects currently linked through team assignments
                              </p>
                            </article>
                          </div>

                          <div class="mt-3 rounded-lg border border-neutral-200">
                            <div class="border-b border-neutral-200 bg-neutral-50 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-neutral-500">
                              Active Project Links
                            </div>
                            {#if expandedTeamPerformance.active_project_links.length === 0}
                              <p class="px-3 py-3 text-sm text-neutral-500">No active project links yet.</p>
                            {:else}
                              <ul class="divide-y divide-neutral-100">
                                {#each expandedTeamPerformance.active_project_links as project}
                                  <li class="flex items-center justify-between gap-3 px-3 py-2 text-sm">
                                    <a href={project.project_href} class="font-medium text-neutral-800 hover:text-blue-700">
                                      {project.project_name}
                                    </a>
                                    <span class="text-xs text-neutral-500">
                                      {project.open_task_count} open · {project.overdue_open_task_count} overdue · {project.booked_hours.toFixed(1)}h
                                    </span>
                                  </li>
                                {/each}
                              </ul>
                            {/if}
                          </div>
                        </section>
                      {/if}

                      {#if expandedTeamAutomation}
                        <section class="rounded-lg border border-neutral-200 bg-white p-4">
                          <h3 class="mb-3 text-sm font-semibold text-neutral-900">HR & Finance Triggers (Automation)</h3>
                          <div class="overflow-x-auto rounded-lg border border-neutral-200">
                            <table class="min-w-full text-sm">
                              <thead class="bg-neutral-50">
                                <tr>
                                  <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Feature</th>
                                  <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Data Field</th>
                                  <th class="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wider text-neutral-500">Trigger / Automation</th>
                                </tr>
                              </thead>
                              <tbody class="divide-y divide-neutral-100">
                                <tr class="align-top">
                                  <td class="px-3 py-3">
                                    <p class="font-semibold text-neutral-900">{expandedTeamAutomation.timesheets.feature}</p>
                                    <p class="mt-1 text-xs text-neutral-600">
                                      Total Logged: {expandedTeamAutomation.timesheets.total_hours_logged.toFixed(2)}h
                                    </p>
                                    <p class="text-xs text-neutral-600">
                                      Billable: {expandedTeamAutomation.timesheets.billable_hours.toFixed(2)}h
                                    </p>
                                  </td>
                                  <td class="px-3 py-3 text-neutral-700">{expandedTeamAutomation.timesheets.data_field}</td>
                                  <td class="px-3 py-3">
                                    <p class="text-neutral-700">{expandedTeamAutomation.timesheets.trigger_automation}</p>
                                    <p class="mt-1 text-xs text-neutral-600">{expandedTeamAutomation.timesheets.trigger_message}</p>
                                    {#if expandedTeamAutomation.timesheets.project_budget_allocations.length > 0}
                                      <div class="mt-2 space-y-1">
                                        {#each expandedTeamAutomation.timesheets.project_budget_allocations as allocation}
                                          <p class="text-xs text-neutral-600">
                                            <span class="font-semibold text-neutral-800">{allocation.project_name}</span>:
                                            {allocation.allocated_billable_hours.toFixed(2)}h
                                            {#if allocation.budget_name}
                                              -> {allocation.budget_name}
                                            {/if}
                                          </p>
                                        {/each}
                                      </div>
                                    {/if}
                                    <span class="mt-2 inline-flex rounded-full px-2 py-0.5 text-xs font-semibold {triggerStatusPillClass(expandedTeamAutomation.timesheets.trigger_status)}">
                                      {triggerStatusLabel(expandedTeamAutomation.timesheets.trigger_status)}
                                    </span>
                                  </td>
                                </tr>
                                <tr class="align-top">
                                  <td class="px-3 py-3">
                                    <p class="font-semibold text-neutral-900">{expandedTeamAutomation.expense_claims.feature}</p>
                                    <p class="mt-1 text-xs text-neutral-600">
                                      Petty Cash: {expandedTeamAutomation.expense_claims.team_petty_cash.toFixed(2)}
                                    </p>
                                    <p class="text-xs text-neutral-600">
                                      Items: {expandedTeamAutomation.expense_claims.reimbursement_item_count}
                                    </p>
                                  </td>
                                  <td class="px-3 py-3 text-neutral-700">{expandedTeamAutomation.expense_claims.data_field}</td>
                                  <td class="px-3 py-3">
                                    <p class="text-neutral-700">{expandedTeamAutomation.expense_claims.trigger_automation}</p>
                                    <p class="mt-1 text-xs text-neutral-600">{expandedTeamAutomation.expense_claims.trigger_message}</p>
                                    <span class="mt-2 inline-flex rounded-full px-2 py-0.5 text-xs font-semibold {triggerStatusPillClass(expandedTeamAutomation.expense_claims.trigger_status)}">
                                      {triggerStatusLabel(expandedTeamAutomation.expense_claims.trigger_status)}
                                    </span>
                                  </td>
                                </tr>
                                <tr class="align-top">
                                  <td class="px-3 py-3">
                                    <p class="font-semibold text-neutral-900">{expandedTeamAutomation.kpis.feature}</p>
                                    <p class="mt-1 text-xs text-neutral-600">
                                      Success Rate: {expandedTeamAutomation.kpis.team_success_rate.toFixed(2)}%
                                    </p>
                                    <p class="text-xs text-neutral-600">
                                      Threshold: {expandedTeamAutomation.kpis.high_performance_threshold.toFixed(0)}%
                                    </p>
                                  </td>
                                  <td class="px-3 py-3 text-neutral-700">{expandedTeamAutomation.kpis.data_field}</td>
                                  <td class="px-3 py-3">
                                    <p class="text-neutral-700">{expandedTeamAutomation.kpis.trigger_automation}</p>
                                    <p class="mt-1 text-xs text-neutral-600">{expandedTeamAutomation.kpis.trigger_message}</p>
                                    <div class="mt-2 flex items-center gap-2">
                                      <span class="inline-flex rounded-full px-2 py-0.5 text-xs font-semibold {expandedTeamAutomation.kpis.high_performance_tag ? 'bg-blue-100 text-blue-700' : 'bg-neutral-100 text-neutral-600'}">
                                        {expandedTeamAutomation.kpis.high_performance_tag ? "High Performance" : "No Tag"}
                                      </span>
                                      <span class="inline-flex rounded-full px-2 py-0.5 text-xs font-semibold {triggerStatusPillClass(expandedTeamAutomation.kpis.trigger_status)}">
                                        {triggerStatusLabel(expandedTeamAutomation.kpis.trigger_status)}
                                      </span>
                                    </div>
                                  </td>
                                </tr>
                              </tbody>
                            </table>
                          </div>
                        </section>
                      {/if}
                    </div>
                  {/if}
                </td>
              </tr>
            {/if}
          {/each}
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    {#if totalPages > 1}
      <div class="flex items-center justify-between mt-4 text-sm text-neutral-500">
        <span>{totalCount} team{totalCount !== 1 ? 's' : ''}</span>
        <div class="flex items-center gap-1">
          <button onclick={() => goToPage(currentPage - 1)} disabled={currentPage <= 1} class="px-2 py-1 rounded hover:bg-neutral-100 disabled:opacity-30 disabled:cursor-not-allowed">&laquo;</button>
          {#each Array.from({ length: totalPages }, (_, i) => i + 1) as p}
            <button onclick={() => goToPage(p)} class="px-2.5 py-1 rounded text-sm {p === currentPage ? 'bg-neutral-900 text-white' : 'hover:bg-neutral-100'}">{p}</button>
          {/each}
          <button onclick={() => goToPage(currentPage + 1)} disabled={currentPage >= totalPages} class="px-2 py-1 rounded hover:bg-neutral-100 disabled:opacity-30 disabled:cursor-not-allowed">&raquo;</button>
        </div>
      </div>
    {/if}
  {/if}
</div>

<!-- Slide-over -->
{#if showSlideOver}
  <div class="fixed inset-0 z-50 flex justify-end">
    <button class="absolute inset-0 bg-black/30 backdrop-blur-sm" onclick={() => { showSlideOver = false; resetForm(); }} aria-label="Close"></button>
    <div class="relative w-full max-w-md bg-white shadow-2xl flex flex-col animate-slide-in-right">
      <div class="flex items-center justify-between px-6 py-4 border-b border-neutral-200">
        <h2 class="text-lg font-bold text-neutral-900">{isEditing ? "Edit Team" : "Create Team"}</h2>
        <button onclick={() => { showSlideOver = false; resetForm(); }} aria-label="Close team editor" class="p-1 rounded hover:bg-neutral-100">
          <svg class="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" /></svg>
        </button>
      </div>
      <div class="flex-1 overflow-y-auto px-6 py-5 space-y-4">
        <div>
          <label for="team-name" class="block text-sm font-medium text-neutral-700 mb-1">Name <span class="text-red-500">*</span></label>
          <input id="team-name" type="text" bind:value={form.name} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 {fieldError('name') ? 'border-red-400' : ''}" />
          {#if fieldError("name")}<p class="text-xs text-red-500 mt-1">{fieldError("name")}</p>{/if}
        </div>
        <div>
          <label for="team-code" class="block text-sm font-medium text-neutral-700 mb-1">Code</label>
          <input id="team-code" type="text" bind:value={form.code} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 font-mono" />
          {#if fieldError("code")}<p class="text-xs text-red-500 mt-1">{fieldError("code")}</p>{/if}
        </div>
        <div>
          <label for="team-dept" class="block text-sm font-medium text-neutral-700 mb-1">Department <span class="text-red-500">*</span></label>
          <select id="team-dept" bind:value={form.department} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
            <option value="">Select department</option>
            {#each departmentOptions as dept}
              <option value={String(dept.id)}>
                {dept.name}{dept.parent_business_unit_name ? ` (${dept.parent_business_unit_name})` : ""}
              </option>
            {/each}
          </select>
          {#if fieldError("department")}<p class="text-xs text-red-500 mt-1">{fieldError("department")}</p>{/if}
        </div>
        <div>
          <label for="team-type" class="block text-sm font-medium text-neutral-700 mb-1">Team Type <span class="text-red-500">*</span></label>
          <select id="team-type" bind:value={form.team_type} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
            <option value="permanent">Permanent</option>
            <option value="project_based">Project-Based</option>
          </select>
          {#if fieldError("team_type")}<p class="text-xs text-red-500 mt-1">{fieldError("team_type")}</p>{/if}
        </div>
        <div>
          <label for="team-lead" class="block text-sm font-medium text-neutral-700 mb-1">Team Lead / Supervisor</label>
          <select id="team-lead" bind:value={form.lead} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900">
            <option value="">Unassigned</option>
            {#each leadOptions as lead}
              <option value={String(lead.id)}>
                {lead.full_name}{lead.employee_id ? ` (${lead.employee_id})` : ""}
              </option>
            {/each}
          </select>
          {#if fieldError("lead")}<p class="text-xs text-red-500 mt-1">{fieldError("lead")}</p>{/if}
        </div>
        {#if form.department}
          <div class="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-2">
            <p class="text-xs font-semibold uppercase tracking-wider text-neutral-500">Functional Parent</p>
            <p class="mt-1 text-sm text-neutral-800">{selectedDepartmentOption()?.name ?? "Department not found"}</p>
            {#if selectedDepartmentOption()?.parent_business_unit_name}
              <p class="text-xs text-neutral-500">Business Unit: {selectedDepartmentOption()?.parent_business_unit_name}</p>
            {/if}
          </div>
        {/if}
        <div>
          <label for="team-desc" class="block text-sm font-medium text-neutral-700 mb-1">Team Purpose</label>
          <textarea id="team-desc" bind:value={form.description} rows={3} class="w-full px-3 py-2 text-sm border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-neutral-900 resize-none"></textarea>
        </div>
        <div class="flex items-center gap-2">
          <input id="team-active" type="checkbox" bind:checked={form.is_active} class="rounded border-neutral-300" />
          <label for="team-active" class="text-sm text-neutral-700">Active</label>
        </div>
      </div>
      <div class="px-6 py-4 border-t border-neutral-200 flex items-center gap-3">
        {#if isDev}
          <button onclick={devFillTeam} class="rounded-lg bg-orange-500 px-3 py-2 text-sm font-medium text-white hover:bg-orange-600 transition-colors mr-auto">Dev Fill</button>
        {/if}
        <button onclick={() => { showSlideOver = false; resetForm(); }} class="px-4 py-2 text-sm font-medium text-neutral-600 hover:text-neutral-900 transition-colors ml-auto">Cancel</button>
        <button onclick={handleSave} disabled={saving} class="px-4 py-2 text-sm font-semibold text-white bg-neutral-900 rounded-lg hover:bg-neutral-800 disabled:opacity-50 transition-colors">
          {saving ? "Saving..." : isEditing ? "Update" : "Create"}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  @keyframes slideInRight {
    from { transform: translateX(100%); }
    to { transform: translateX(0); }
  }
  .animate-slide-in-right {
    animation: slideInRight 0.25s ease-out both;
  }
</style>
